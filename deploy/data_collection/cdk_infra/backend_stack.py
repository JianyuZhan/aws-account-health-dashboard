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
import re
import sys

# 将 common 目录添加到 sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../common'))

# common/constants
from constants import (
    NAME_PREFIX, LAMBDA_ROLE,
    ACCOUNTS_TABLE_NAME,
    USERS_TABLE_NAME,
    HEALTH_EVENTS_TABLE_NAME,
    EVENT_DETAILS_TABLE_NAME,
    AFFECTED_ACCOUNTS_TABLE_NAME,
    AFFECTED_ENTITIES_TABLE_NAME,
)

DEPLOY_ENVIRONMENT = os.getenv('DEPLOY_ENVIRONMENT', 'dev')  # 开发用'dev'， 生产用'prod'
REMOVAL_POLICY = RemovalPolicy.DESTROY if DEPLOY_ENVIRONMENT == 'dev' else RemovalPolicy.RETAIN

def pascal_case(string):
    words = re.split(r'_', string)
    capitalized_words = [word.capitalize() for word in words]
    return ''.join(capitalized_words)

class AwsHealthDashboard(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # 创建DynamoDB表
        self.accounts_table = self.create_management_accounts_table()
        self.user_table = self.create_users_table()
        # 几个健康事件相关的表
        self.health_table = self.create_health_events_table()
        self.event_details_table = self.create_event_details_table()
        self.affected_accounts_table = self.create_affected_accounts_table()
        self.affected_entities_table = self.create_affected_entities_table()

        # 创建Lambda角色，并授予访问DynamoDB表的权限
        self.lambda_role = self.create_lambda_role()

        # 创建API Gateway
        self.api = apigw.RestApi(
            self, f'{NAME_PREFIX}Api',
            rest_api_name=f'{NAME_PREFIX} Service',
            description='AWS Health Dashboard API'
        )

        # 注册Lambda函数及其方法
        # 创建公共层
        self.common_layer = _lambda.LayerVersion(
            self, f'{NAME_PREFIX}CommonLayer',
            code=_lambda.Code.from_asset(os.path.join(os.path.dirname(__file__), '../../../common')),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_11],
            description='A layer for common utilities'
        )

        # 帐号相关
        self.register_lambda('register_accounts', 'register_accounts', ['POST'])
        self.register_lambda('deregister_accounts', 'deregister_accounts', ['DELETE'])
        self.register_lambda('update_account', 'update_account', ['PUT'])
        self.register_lambda('get_allowed_accounts', 'get_allowed_accounts', ['POST'])

        #
        # 表相关
        #
        # 注册拉取健康事件的Lambda函数
        self.fetch_health_events_lambda = self.register_lambda(
            'fetch_health_events',
            'fetch_health_events',
            methods=['POST'],
            environment={
                'LOOKBACK_DAYS': '90'
            },
            timeout=Duration.minutes(15)   # 设置Lambda函数的超时时间为15分钟
        )

        # 注册查询健康事件的Lambda函数
        self.query_health_events_lambda = self.register_lambda(
            'query_health_events',
            'query_health_events',
            methods=['POST'],
            timeout=Duration.minutes(15)
        )

        # 注册查询事件详情的Lambda函数
        self.query_event_details_lambda = self.register_lambda(
            'query_event_details',
            'query_event_details',
            methods=['POST'],
            timeout=Duration.minutes(15)
        )

        # 注册查询受影响账户的Lambda函数
        self.query_affected_accounts_lambda = self.register_lambda(
            'query_affected_accounts',
            'query_affected_accounts',
            methods=['POST'],
            timeout=Duration.minutes(15)
        )

        # 注册查询受影响实体的Lambda函数
        self.query_affected_entities_lambda = self.register_lambda(
            'query_affected_entities',
            'query_affected_entities',
            methods=['POST'],
            timeout=Duration.minutes(15)
        )

        self.query_bedrock = self.register_lambda(
            'query_bedrock',
            'query_bedrock',
            methods=['POST'],
            timeout=Duration.minutes(15)
        )

        # 创建EventBridge规则以触发fetch_health_events Lambda函数
        self.create_eventbridge_rule()

    def create_health_events_table(self):
        """创建用于存储健康事件的DynamoDB表，并启用TTL特性。"""
        table = dynamodb.Table(
            self, f'{NAME_PREFIX}HealthEventsTable',
            table_name=HEALTH_EVENTS_TABLE_NAME,
            partition_key=dynamodb.Attribute(name='AccountId', type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name='EventArn', type=dynamodb.AttributeType.STRING),
            removal_policy=REMOVAL_POLICY,
            time_to_live_attribute='ExpirationTime',  # 启用TTL特性
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST  # 按需计费
        )

        # 定义全局二级索引 (GSI)
        # 这里只加一个GSI，一次加多个会报错：
        # Cannot perform more than one GSI creation or deletion in a single update
        # 剩下的放在 deploy/data_collection/add_events_table_gsi.py中
        gsi_definitions = [
            ('GSI1', 'AccountId', 'StartTime'),
            # ('GSI2', 'awsAccountIds', 'StartTime'),
            # ('GSI3', 'EventTypeCode', 'StartTime'),
            # ('GSI4', 'Region', 'StartTime'),
            # ('GSI5', 'Service', 'StartTime'),
            # ('GSI6', 'EventStatusCode', 'StartTime'),
            # ('GSI7', 'EventTypeCategory', 'StartTime')
        ]

        for index_name, partition_key, sort_key in gsi_definitions:
            table.add_global_secondary_index(
                index_name=index_name,
                partition_key=dynamodb.Attribute(name=partition_key, type=dynamodb.AttributeType.STRING),
                sort_key=dynamodb.Attribute(name=sort_key, type=dynamodb.AttributeType.STRING),
                projection_type=dynamodb.ProjectionType.ALL
            )

        return table

    def create_event_details_table(self):
        """创建用于存储事件详细信息的DynamoDB表。"""
        table = dynamodb.Table(
            self, f'{NAME_PREFIX}EventDetailsTable',
            table_name=EVENT_DETAILS_TABLE_NAME,
            partition_key=dynamodb.Attribute(name='EventArn', type=dynamodb.AttributeType.STRING),
            removal_policy=REMOVAL_POLICY,
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST  # 按需计费
        )

        return table

    def create_affected_accounts_table(self):
        """创建用于存储受影响账户的DynamoDB表。"""
        table = dynamodb.Table(
            self, f'{NAME_PREFIX}AffectedAccountsTable',
            table_name=AFFECTED_ACCOUNTS_TABLE_NAME,
            partition_key=dynamodb.Attribute(name='EventArn', type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name='AccountId', type=dynamodb.AttributeType.STRING),
            removal_policy=REMOVAL_POLICY,
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST  # 按需计费
        )

        return table

    def create_affected_entities_table(self):
        """创建用于存储受影响实体的DynamoDB表。"""
        table = dynamodb.Table(
            self, f'{NAME_PREFIX}AffectedEntitiesTable',
            table_name=AFFECTED_ENTITIES_TABLE_NAME,
            partition_key=dynamodb.Attribute(name='EventArn', type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name='AccountId', type=dynamodb.AttributeType.STRING),
            removal_policy=REMOVAL_POLICY,
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST  # 按需计费
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
            partition_key=dynamodb.Attribute(name='UserId', type=dynamodb.AttributeType.STRING),
            removal_policy=REMOVAL_POLICY
        )
        return table

    def create_lambda_role(self):
        """创建Lambda函数的IAM角色，并授予访问DynamoDB表的权限。"""
        role = iam.Role(
            self, f'{NAME_PREFIX}LambdaRole',
            role_name=LAMBDA_ROLE,
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com')
        )

        role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole')
        )

        # 添加调用其他Lambda函数的权限
        role.add_to_policy(iam.PolicyStatement(
            actions=["lambda:InvokeFunction"],
            resources=["*"]
        ))

        # 添加IAM操作的权限(用来注册帐号时，增加给assume帐号的cross_account_role的权限)
        role.add_to_policy(iam.PolicyStatement(
                actions=["iam:*"],
                resources=["*"]
            )
        )

        self.accounts_table.grant_read_write_data(role)
        self.user_table.grant_read_write_data(role)
        self.health_table.grant_read_write_data(role)
        self.event_details_table.grant_read_write_data(role)
        self.affected_accounts_table.grant_read_write_data(role)
        self.affected_entities_table.grant_read_write_data(role)

        # 添加DynamoDB TTL操作的权限
        role.add_to_policy(iam.PolicyStatement(
                actions=[
                    "dynamodb:DescribeTimeToLive",
                    "dynamodb:UpdateTimeToLive"
                ],
                resources=[
                    self.accounts_table.table_arn, 
                    self.user_table.table_arn,
                    self.health_table.table_arn, 
                    self.event_details_table.table_arn,
                    self.affected_accounts_table.table_arn,
                    self.affected_entities_table.table_arn
                ]
            )
        )

        # 添加Bedrock的权限
        role.add_to_policy(iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                resources=[
                    "*"
                ]
            )
        )

        return role

    def register_lambda(self, resource_name: str, directory_name: str, methods: list, environment: dict = None, timeout: Duration = None):
        """注册Lambda函数并将其集成到API Gateway，并处理CORS问题。"""
        
        # 创建Lambda函数
        lambda_function = _lambda.Function(
            self, f'{NAME_PREFIX}{resource_name.capitalize()}Function',
            function_name=f'{NAME_PREFIX}{pascal_case(resource_name)}',
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler=f"lambda.lambda_handler",
            code=_lambda.Code.from_asset(os.path.join(os.path.dirname(__file__), f'../../../api/{directory_name}')),
            role=self.lambda_role,
            environment={
                **(environment or {}),
                "PYTHONPATH": "/opt"  # 设置 PYTHONPATH 指向 Lambda Layer 的挂载点
            },
            timeout=timeout or Duration.seconds(300),
            layers=[self.common_layer]  # 添加共用的 Lambda Layer
        )

        # 创建API Gateway资源
        resource = self.api.root.add_resource(resource_name)

        # 为 OPTIONS 方法配置 CORS 响应
        resource.add_method(
            "OPTIONS",
            apigw.MockIntegration(
                integration_responses=[apigw.IntegrationResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Headers": "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
                        "method.response.header.Access-Control-Allow-Origin": "'*'",
                        "method.response.header.Access-Control-Allow-Methods": "'" + ",".join(methods) + "'"
                    }
                )],
                request_templates={"application/json": '{"statusCode": 200}'}
            ),
            method_responses=[apigw.MethodResponse(
                status_code="200",
                response_parameters={
                    "method.response.header.Access-Control-Allow-Headers": True,
                    "method.response.header.Access-Control-Allow-Origin": True,
                    "method.response.header.Access-Control-Allow-Methods": True
                }
            )]
        )

        if methods:
            # 设置Lambda集成请求
            integration = apigw.LambdaIntegration(
                lambda_function,
                proxy=True
            )

            for method in methods:
                # 为每个方法设置集成和响应
                resource.add_method(
                    method,
                    integration,
                    method_responses=[
                        apigw.MethodResponse(
                            status_code="200",
                            response_models={
                                "application/json": apigw.Model.EMPTY_MODEL
                            },
                            response_parameters={
                                "method.response.header.Access-Control-Allow-Origin": True
                            }
                        )
                    ]
                )

            # 授予API Gateway调用Lambda函数的权限
            lambda_function.add_permission(
                f'{NAME_PREFIX}ApiInvokePermission',
                principal=iam.ServicePrincipal('apigateway.amazonaws.com'),
                action='lambda:InvokeFunction',
                source_arn=f'arn:aws:execute-api:{self.region}:{self.account}:{self.api.rest_api_id}/*/*/{resource_name}'
            )

        # 输出API Gateway URL
        CfnOutput(self, f'{resource_name.capitalize()}ApiUrl', value=f'{self.api.url}{resource_name}')

        return lambda_function
    
    def create_eventbridge_rule(self):
        """创建EventBridge规则以触发fetch_health_events Lambda函数。"""
        rule = events.Rule(
            self, f'{NAME_PREFIX}FetchHealthEventsRule',
            # 默认每天凌晨2点触发， 注意！是指部署本cdk的地方时凌晨2点
            schedule=events.Schedule.cron(minute='0', hour='2'),  
        )

        rule.add_target(targets.LambdaFunction(self.fetch_health_events_lambda))

        # 输出EventBridge规则的ARN
        CfnOutput(self, 'FetchHealthEventsRuleArn', value=rule.rule_arn)