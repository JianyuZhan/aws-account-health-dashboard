# deploy/cdk_infra/cdk_infra_stack.py
from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    aws_iam as iam,
    CfnOutput
)
from constructs import Construct
import os

NAME_PREFIX = 'AwsHealthDashboard'

class AwsHealthDashboard(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # API Gateway
        self.api = apigw.RestApi(
            self, f'{NAME_PREFIX}Api',
            rest_api_name=f'{NAME_PREFIX} Service',
            description='This service serves multiple functions.'
        )

        # Register Lambda functions with methods
        self.register_lambda('register_accounts', 'register_accounts', ['POST'])
        self.register_lambda('deregister_accounts', 'deregister_accounts', ['DELETE'])
        self.register_lambda('update_account', 'update_account', ['PUT'])

    def register_lambda(self, resource_name: str, directory_name: str, methods: list):
        # Lambda function
        lambda_function = _lambda.Function(
            self, f'{NAME_PREFIX}{resource_name.capitalize()}Function',
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler='lambda.handler',  # 注意这里的handler路径
            code=_lambda.Code.from_asset(os.path.join(os.path.dirname(__file__), f'../../api/{directory_name}'))
        )

        # Grant API Gateway permission to invoke the Lambda function
        lambda_function.add_permission(
            f'{NAME_PREFIX}ApiInvokePermission',
            principal=iam.ServicePrincipal('apigateway.amazonaws.com'),
            action='lambda:InvokeFunction',
            source_arn=f'arn:aws:execute-api:{self.region}:{self.account}:{self.api.rest_api_id}/*/*/{resource_name}'
        )

        # API Gateway integration
        lambda_integration = apigw.LambdaIntegration(lambda_function)
        resource = self.api.root.add_resource(resource_name)
        for method in methods:
            resource.add_method(method, lambda_integration)

        # Output the API Gateway URL for this resource
        CfnOutput(self, f'{resource_name.capitalize()}ApiUrl', value=f'{self.api.url}{resource_name}')

    def register_method(self, resource_name: str, method: str):
        resource = self.api.root.get_resource(resource_name)
        if resource is not None:
            # We assume that the Lambda function associated with the resource has the same name
            lambda_function_name = f'{NAME_PREFIX}{resource_name.capitalize()}Function'
            lambda_function = _lambda.Function.from_function_name(self, lambda_function_name, lambda_function_name)
            
            # Ensure the Lambda function has permission for the new method
            lambda_function.add_permission(
                f'{NAME_PREFIX}{method}InvokePermission',
                principal=iam.ServicePrincipal('apigateway.amazonaws.com'),
                action='lambda:InvokeFunction',
                source_arn=f'arn:aws:execute-api:{self.region}:{self.account}:{self.api.rest_api_id}/*/*/{resource_name}'
            )
            
            # API Gateway integration
            lambda_integration = apigw.LambdaIntegration(lambda_function)
            resource.add_method(method, lambda_integration)
        else:
            raise ValueError(f"Resource '{resource_name}' not found in API Gateway.")
