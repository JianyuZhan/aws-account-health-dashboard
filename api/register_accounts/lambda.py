import json
import boto3
import re

# 表名常量 (保持和deploy/data_collection/cdk_infr/infra_stack.py一致)
NAME_PREFIX = 'AwsHealthDashboard'
ACCOUNTS_TABLE_NAME = f'{NAME_PREFIX}ManagementAccounts'
USERS_TABLE_NAME = f'{NAME_PREFIX}Users'

# 初始化DynamoDB客户端
dynamodb = boto3.resource('dynamodb')
dynamodb_client = boto3.client('dynamodb')
accounts_table = dynamodb.Table(ACCOUNTS_TABLE_NAME)
users_table = dynamodb.Table(USERS_TABLE_NAME)

# 邮箱格式校验的正则表达式
email_regex = re.compile(r"[^@]+@[^@]+\.[^@]+")

def validate_email(email):
    """
    使用正则表达式校验邮箱格式。

    参数:
    email (str): 需要校验的邮箱地址

    返回:
    bool: 如果邮箱格式有效则返回True，否则返回False
    """
    return email_regex.match(email) is not None

def prepare_transact_items(account_id, cross_account_role, valid_emails):
    """
    准备DynamoDB的事务写入项。

    参数:
    account_id (str): 账户ID
    cross_account_role (str): 跨账户角色名称
    valid_emails (dict): 有效的邮箱信息

    返回:
    list: 事务写入项列表
    """
    transact_items = [
        {
            'Put': {
                'TableName': ACCOUNTS_TABLE_NAME,
                'Item': {
                    'account_id': {'S': account_id},
                    'cross_account_role': {'S': cross_account_role},
                    'allowed_users': {'M': {email: {'S': name} for email, name in valid_emails.items()}}
                }
            }
        }
    ]
    
    for email, name in valid_emails.items():
        transact_items.append({
            'Update': {
                'TableName': USERS_TABLE_NAME,
                'Key': {'user_id': {'S': email}},
                'UpdateExpression': 'ADD allowed_accounts :account_id SET user_name = if_not_exists(user_name, :user_name)',
                'ExpressionAttributeValues': {
                    ':account_id': {'SS': [account_id]},
                    ':user_name': {'S': name}
                },
                'ExpressionAttributeNames': {
                    '#allowed_accounts': 'allowed_accounts'
                }
            }
        })
    
    return transact_items

def create_response(status_code, message):
    """
    创建HTTP响应。

    参数:
    status_code (int): HTTP状态码
    message (str): 响应消息

    返回:
    dict: 包含状态码和消息的响应字典
    """
    return {
        'statusCode': status_code,
        'body': json.dumps(message)
    }

def lambda_handler(event, context):
    """
    处理注册账户信息的Lambda函数。

    输入事件的格式应为：
    {
        "123456789012": {
            "cross_account_role": "RoleName",
            "allowed_users": {
                "email1@example.com": "John Doe",
                "email2@example.com": "Jane Doe"
            }
        },
        "098765432109": {
            "cross_account_role": "AnotherRoleName",
            "allowed_users": {
                "email3@example.com": "Alice",
                "email4@example.com": "Bob"
            }
        }
    }

    参数:
    event (dict): 包含账户ID、角色名称和邮箱信息的事件字典
    context (LambdaContext): Lambda执行环境的上下文对象

    返回:
    dict: 包含状态码和处理结果的字典
    """
    transact_items = []

    for account_id, account_info in event.items():
        # 校验AccountId是否为12位数字
        if not account_id.isdigit() or len(account_id) != 12:
            return create_response(400, f'Invalid AccountId: {account_id}')

        cross_account_role = account_info.get('cross_account_role')
        if not cross_account_role:
            return create_response(400, f'Missing cross_account_role for AccountId: {account_id}')

        allowed_users = account_info.get('allowed_users', {})
        valid_emails = {}
        for email, name in allowed_users.items():
            if validate_email(email):
                valid_emails[email] = name
            else:
                print(f"Invalid email format: {email}")

        transact_items.extend(prepare_transact_items(account_id, cross_account_role, valid_emails))

    if transact_items:
        try:
            for i in range(0, len(transact_items), 25):
                batch = transact_items[i:i+25]
                dynamodb_client.transact_write_items(TransactItems=batch)
                print(f"Batch of {len(batch)} items stored successfully.")
        except Exception as e:
            print(f"Failed to store data: {str(e)}")
            return create_response(500, 'Failed to store data.')

    return create_response(200, 'Accounts registered successfully.')
