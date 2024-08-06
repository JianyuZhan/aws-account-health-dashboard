from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    aws_iam as iam,
    aws_dynamodb as dynamodb,
    aws_events as events,
    aws_events_targets as targets,
    Duration,
    RemovalPolicy,
    CfnOutput
)
from constructs import Construct
import os

NAME_PREFIX = 'AwsHealthDashboard'

ACCOUNTS_TABLE_NAME = f'{NAME_PREFIX}ManagementAccounts'
HEALTH_EVENTS_TABLE_NAME = f'{NAME_PREFIX}HealthEvents'
USERS_TABLE_NAME = f'{NAME_PREFIX}Users'

ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev')  # 默认值为'dev'
REMOVAL_POLICY = RemovalPolicy.DESTROY if ENVIRONMENT == 'dev' else RemovalPolicy.RETAIN

class AwsHealthDashboard(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # 创建DynamoDB表
        self.health_table = self.create_health_events_table()
        self.accounts_table = self.create_management_accounts_table()
        self.user_table = self.create_users_table()

        # 创建Lambda角色，并授予访问DynamoDB表的权限
        self.lambda_role = self.create_lambda_role()

        # 创建API Gateway
        self.api = apigw.RestApi(
            self, f'{NAME_PREFIX}Api',
            rest_api_name=f'{NAME_PREFIX} 服务',
            description='此服务提供多种功能。'
        )

        # 注册Lambda函数及其方法
        self.register_lambda('register_accounts', 'register_accounts', ['POST'])
        self.register_lambda('deregister_accounts', 'deregister_accounts', ['DELETE'])
        self.register_lambda('update_account', 'update_account', ['PUT'])

        # 创建并单独注册fetch_health_events Lambda函数
        self.fetch_health_events_lambda = self.register_lambda(
            'fetch_health_events',
            'fetch_health_events',
            methods=['POST'],
            environment={
                'LOOKBACK_DAYS': '90'
            },
            timeout=Duration.minutes(15)
        )

        # 创建EventBridge规则以触发fetch_health_events Lambda函数
        self.create_eventbridge_rule()

    def create_health_events_table(self):
        """创建用于存储健康事件的DynamoDB表，并启用TTL特性。"""
        table = dynamodb.Table(
            self, f'{NAME_PREFIX}HealthEventsTable',
            table_name=HEALTH_EVENTS_TABLE_NAME,  # 指定表名
            partition_key=dynamodb.Attribute(name='AccountId', type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name='EventArn', type=dynamodb.AttributeType.STRING),
            removal_policy=REMOVAL_POLICY,
            time_to_live_attribute='ExpirationTime'  # 启用TTL特性
        )
        return table

    def create_management_accounts_table(self):
        """创建用于存储管理账户的DynamoDB表。"""
        table = dynamodb.Table(
            self, f'{NAME_PREFIX}ManagementAccountsTable',
            table_name=ACCOUNTS_TABLE_NAME,  # 指定表名
            partition_key=dynamodb.Attribute(name='AccountId', type=dynamodb.AttributeType.STRING),
            removal_policy=REMOVAL_POLICY
        )
        return table

    def create_users_table(self):
        """创建用于存储用户信息的DynamoDB表。"""
        table = dynamodb.Table(
            self, f'{NAME_PREFIX}UsersTable',
            table_name=USERS_TABLE_NAME,  # 指定表名
            partition_key=dynamodb.Attribute(name='user_id', type=dynamodb.AttributeType.STRING),
            removal_policy=REMOVAL_POLICY
        )
        return table

    def create_lambda_role(self):
        """创建Lambda函数的IAM角色，并授予访问DynamoDB表的权限。"""
        role = iam.Role(
            self, f'{NAME_PREFIX}LambdaRole',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com')
        )

        role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole')
        )

        self.health_table.grant_read_write_data(role)
        self.accounts_table.grant_read_write_data(role)
        self.user_table.grant_read_write_data(role)

        return role

    def register_lambda(self, resource_name: str, directory_name: str, methods: list, environment: dict = None, timeout: Duration = None):
        """注册Lambda函数并将其集成到API Gateway。"""
        # 创建Lambda函数
        lambda_function = _lambda.Function(
            self, f'{NAME_PREFIX}{resource_name.capitalize()}Function',
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler='lambda.lambda_handler',  # 注意这里的handler路径
            code=_lambda.Code.from_asset(os.path.join(os.path.dirname(__file__), f'../../../api/{directory_name}')),
            role=self.lambda_role,
            environment=environment or {},  # 设置环境变量
            timeout=timeout or Duration.seconds(300)  # 设置超时时间
        )

        if methods:
            # 授予API Gateway调用Lambda函数的权限
            lambda_function.add_permission(
                f'{NAME_PREFIX}ApiInvokePermission',
                principal=iam.ServicePrincipal('apigateway.amazonaws.com'),
                action='lambda:InvokeFunction',
                source_arn=f'arn:aws:execute-api:{self.region}:{self.account}:{self.api.rest_api_id}/*/*/{resource_name}'
            )

            # API Gateway集成
            lambda_integration = apigw.LambdaIntegration(lambda_function)
            resource = self.api.root.add_resource(resource_name)
            for method in methods:
                resource.add_method(method, lambda_integration)

            # 输出API Gateway URL
            CfnOutput(self, f'{resource_name.capitalize()}ApiUrl', value=f'{self.api.url}{resource_name}')

        return lambda_function

    def create_eventbridge_rule(self):
        """创建EventBridge规则以触发fetch_health_events Lambda函数。"""
        rule = events.Rule(
            self, f'{NAME_PREFIX}FetchHealthEventsRule',
            schedule=events.Schedule.cron(minute='0', hour='2'),  # 默认每天凌晨2点触发
        )

        rule.add_target(targets.LambdaFunction(self.fetch_health_events_lambda))

        # 输出EventBridge规则的ARN
        CfnOutput(self, 'FetchHealthEventsRuleArn', value=rule.rule_arn)
