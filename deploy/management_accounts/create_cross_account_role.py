import os
import sys
import boto3
import argparse
import json

def get_aws_region():
    region = os.getenv('AWS_HEALTH_DASHBOARD_REGION') or os.getenv('AWS_REGION')
    if not region:
        print("Environment variable AWS_HEALTH_DASHBOARD_REGION or AWS_REGION must be set.")
        sys.exit(1)
    return region

def get_region_prefix(region):
    """将区域名转换为驼峰命名格式的前缀"""
    # 移除 '-'
    parts = region.split('-')
    # 首字母大写
    return ''.join(part.capitalize() for part in parts)

def check_role_exists(iam_client, role_name):
    """检查角色是否存在"""
    try:
        iam_client.get_role(RoleName=role_name)
        return True
    except iam_client.exceptions.NoSuchEntityException:
        return False

def create_stack(client, stack_name, data_collection_account_id, management_account_role_name, region):
    try:
        # 创建 IAM 客户端
        iam_client = boto3.client('iam', region_name=region)
        
        # 检查角色是否存在
        if check_role_exists(iam_client, management_account_role_name):
            print(f"Role {management_account_role_name} already exists. Skipping creation.")
            return None

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
                }
            ],
            Capabilities=['CAPABILITY_NAMED_IAM']
        )
        print(f"Stack creation initiated, StackId: {response['StackId']}")
        return response['StackId']
    except Exception as e:
        print(f"Failed to create stack: {str(e)}")
        sys.exit(1)

def wait_for_stack_creation(client, stack_name):
    # 如果 stack_id 为 None，说明角色已存在，直接返回
    if stack_name is None:
        return

    try:
        waiter = client.get_waiter('stack_create_complete')
        print(f"Waiting for stack {stack_name} to be created...")
        waiter.wait(StackName=stack_name)
        print(f"Stack {stack_name} created successfully.")
    except Exception as e:
        # 获取详细的失败信息
        try:
            stack_events = client.describe_stack_events(StackName=stack_name)
            failed_events = [
                event for event in stack_events['StackEvents'] 
                if event.get('ResourceStatus') == 'CREATE_FAILED'
            ]
            
            if failed_events:
                print("Detailed Failure Information:")
                for event in failed_events:
                    print(f"Resource: {event.get('LogicalResourceId')}")
                    print(f"Status Reason: {event.get('ResourceStatusReason')}")
            
            # 获取完整的堆栈描述
            stack_description = client.describe_stacks(StackName=stack_name)
            print("\nFull Stack Description:")
            # 使用 json.dumps 处理不可序列化的对象
            print(json.dumps({k: str(v) for k, v in stack_description['Stacks'][0].items()}, indent=2))
        except Exception as detail_error:
            print(f"Unable to retrieve detailed error: {str(detail_error)}")
        
        print(f"\nFailed to create stack {stack_name}: {str(e)}")
        sys.exit(1)

def validate_template(client, template_path):
    """验证CloudFormation模板"""
    try:
        with open(template_path, 'r') as template_file:
            template_body = template_file.read()
        
        response = client.validate_template(TemplateBody=template_body)
        print("Template validation successful.")
        return True
    except Exception as e:
        print(f"Template validation failed: {str(e)}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Deploy AWS CloudFormation stack for cross-account IAM roles.')
    parser.add_argument('data_collection_account_id', type=str, help='The AWS Account ID of the Data Collection Account')
    parser.add_argument('--stack-name', type=str, default='AwsHealthCrossAccountRoleStack', help='The name of the CloudFormation stack')
    parser.add_argument('--role-name', type=str, help='The name of the IAM role to be created for the management account')
    parser.add_argument('--region', type=str, help='AWS Region to deploy the CloudFormation stack')
    parser.add_argument('--validate-only', action='store_true', help='Only validate the template without creating the stack')

    args = parser.parse_args()

    # 获取当前脚本的目录
    SCRIPT_DIR = os.path.dirname(__file__)

    # 处理区域
    region = args.region or get_aws_region()
    
    # 生成区域前缀
    region_prefix = get_region_prefix(region)

    # 如果没有提供角色名，则使用带区域前缀的默认名称
    role_name = args.role_name or f'{region_prefix}DataCollectionCrossAccountRole'
    stack_name = args.stack_name or f'{region_prefix}AwsHealthCrossAccountRoleStack'

    # 创建 boto3 客户端
    cloudformation_client = boto3.client('cloudformation', region_name=region)

    # 验证模板
    template_path = os.path.join(SCRIPT_DIR, 'CrossAccountRole.yaml')
    is_valid = validate_template(cloudformation_client, template_path)
    
    if not is_valid:
        sys.exit(1)
    
    # 如果只是验证模板
    if args.validate_only:
        print("Template validation complete.")
        sys.exit(0)

    # 创建堆栈
    stack_id = create_stack(
        client=cloudformation_client,
        stack_name=stack_name,
        data_collection_account_id=args.data_collection_account_id,
        management_account_role_name=role_name,
        region=region
    )

    # 等待堆栈创建完成
    wait_for_stack_creation(cloudformation_client, stack_name)
