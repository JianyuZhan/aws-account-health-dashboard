import os
import sys
import boto3
import argparse

# 将 common 目录添加到 sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../common'))

# 从 constants 模块中导入 LAMBDA_ROLE
from constants import LAMBDA_ROLE

# 获取 AWS 区域
def get_aws_region():
    region = os.getenv('AWS_HEALTH_DASHBOARD_REGION') or os.getenv('AWS_REGION')
    if not region:
        print("Environment variable AWS_HEALTH_DASHBOARD_REGION or AWS_REGION must be set.")
        sys.exit(1)
    return region

# 构建 IAM Role ARN
def build_role_arn(account_id, role_name):
    arn = f"arn:aws:iam::{account_id}:role/{role_name}"
    return arn

def create_stack(client, stack_name, data_collection_account_id, management_account_role_name, data_collection_lambda_role_arn):
    try:
        response = client.create_stack(
            StackName=stack_name,
            TemplateBody=open(os.path.join(SCRIPT_DIR, 'CrossAccountRole.yaml')).read(),
            Parameters=[
                {
                    'ParameterKey': 'DataCollectionAccountID',
                    'ParameterValue': data_collection_account_id
                },
                {
                    'ParameterKey': 'ManagementAccountRoleName',
                    'ParameterValue': management_account_role_name
                },
                {
                    'ParameterKey': 'DataCollectionLambdaRoleArn',
                    'ParameterValue': data_collection_lambda_role_arn 
                }
            ],
            Capabilities=['CAPABILITY_NAMED_IAM']
        )
        print(f"Stack creation initiated, StackId: {response['StackId']}")
    except Exception as e:
        print(f"Failed to create stack: {str(e)}")
        sys.exit(1)

# 等待堆栈创建完成
def wait_for_stack_creation(client, stack_name):
    print(f"Waiting for stack creation...")
    try:
        waiter = client.get_waiter('stack_create_complete')
        waiter.wait(StackName=stack_name)
        print(f"Stack {stack_name} created successfully.")
    except Exception as e:
        print(f"Failed to create stack {stack_name}: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Deploy AWS CloudFormation stack for cross-account IAM roles.')
    parser.add_argument('data_collection_account_id', type=str, help='The AWS Account ID of the Data Collection Account')
    parser.add_argument('--stack-name', type=str, default='AwsHealthCrossAccountRoleStack', help='The name of the CloudFormation stack')
    parser.add_argument('--role-name', type=str, default='DataCollectionCrossAccountRole', help='The name of the IAM role to be created for the management account')
    parser.add_argument('--lambda-role', type=str, default=LAMBDA_ROLE, help='The name of the IAM role in the data collection account')

    args = parser.parse_args()

    # 获取当前脚本的目录
    SCRIPT_DIR = os.path.dirname(__file__)

    # 构建 IAM Role ARN
    lambda_role_arn = build_role_arn(args.data_collection_account_id, args.lambda_role)

    # 创建 boto3 客户端
    region = get_aws_region()
    cloudformation_client = boto3.client('cloudformation', region_name=region)

    # 创建堆栈
    create_stack(
        client=cloudformation_client,
        stack_name=args.stack_name,
        data_collection_account_id=args.data_collection_account_id,
        management_account_role_name=args.role_name,
        data_collection_lambda_role_arn=lambda_role_arn
    )

    # 等待堆栈创建完成
    wait_for_stack_creation(cloudformation_client, args.stack_name)