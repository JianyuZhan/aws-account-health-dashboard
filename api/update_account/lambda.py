import json
import boto3
import re
from boto3.dynamodb.conditions import Key

# 表名常量 (保持和deploy/data_collection/cdk_infr/infra_stack.py一致)
NAME_PREFIX = 'AwsHealthDashboard'
ACCOUNTS_TABLE_NAME = f'{NAME_PREFIX}ManagementAccounts'
USERS_TABLE_NAME = f'{NAME_PREFIX}Users'

# 初始化DynamoDB客户端
dynamodb = boto3.resource('dynamodb')
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

def get_account(account_id):
    """
    从DynamoDB中获取账户信息。

    参数:
    account_id (str): 账户ID

    返回:
    dict: 账户信息
    """
    response = accounts_table.get_item(
        Key={
            'account_id': account_id
        }
    )
    return response.get('Item')

def prepare_transact_items(account_id, existing_emails, params):
    """
    准备DynamoDB的事务写入项。

    参数:
    account_id (str): 账户ID
    existing_emails (dict): 现有的邮箱信息
    params (dict): 包含添加、删除和更新操作的参数

    返回:
    list: 事务写入项列表
    """
    transact_items = []

    if 'add' in params:
        add_emails(existing_emails, params['add'], transact_items, account_id)

    if 'delete' in params:
        delete_emails(existing_emails, params['delete'], transact_items, account_id)

    if 'update' in params:
        update_emails(existing_emails, params['update'])

    # 更新管理账户表
    transact_items.append({
        'Update': {
            'TableName': ACCOUNTS_TABLE_NAME,
            'Key': {'account_id': {'S': account_id}},
            'UpdateExpression': 'SET allowed_users = :emails',
            'ExpressionAttributeValues': {
                ':emails': {'M': {email: {'S': name} for email, name in existing_emails.items()}}
            }
        }
    })

    return transact_items

def add_emails(existing_emails, emails_to_add, transact_items, account_id):
    """
    向现有邮箱字典中添加新邮箱，并准备事务项。

    参数:
    existing_emails (dict): 现有的邮箱信息字典
    emails_to_add (dict): 需要添加的邮箱信息字典
    transact_items (list): 事务项列表
    account_id (str): 账户ID
    """
    for email, name in emails_to_add.items():
        if validate_email(email):
            if email not in existing_emails:
                existing_emails[email] = name
                print(f"Added email: {email}")
                # 更新用户表
                transact_items.append({
                    'Update': {
                        'TableName': USERS_TABLE_NAME,
                        'Key': {'user_id': {'S': email}},
                        'UpdateExpression': 'ADD allowed_accounts :account_id SET user_name = if_not_exists(user_name, :user_name)',
                        'ExpressionAttributeValues': {
                            ':account_id': {'SS': [account_id]},
                            ':user_name': {'S': name}
                        }
                    }
                })
            else:
                print(f"Email already exists, not adding: {email}")
        else:
            print(f"Invalid email format: {email}")

def delete_emails(existing_emails, emails_to_delete, transact_items, account_id):
    """
    从现有邮箱字典中删除指定的邮箱，并准备事务项。

    参数:
    existing_emails (dict): 现有的邮箱信息字典
    emails_to_delete (dict): 需要删除的邮箱信息字典
    transact_items (list): 事务项列表
    account_id (str): 账户ID
    """
    for email in emails_to_delete:
        if email in existing_emails:
            del existing_emails[email]
            print(f"Deleted email: {email}")
            # 更新用户表
            transact_items.append({
                'Update': {
                    'TableName': USERS_TABLE_NAME,
                    'Key': {'user_id': {'S': email}},
                    'UpdateExpression': 'DELETE allowed_accounts :account_id',
                    'ExpressionAttributeValues': {':account_id': {'SS': [account_id]}}
                }
            })
        else:
            print(f"Email not found, not deleting: {email}")

def update_emails(existing_emails, emails_to_update):
    """
    更新现有邮箱字典中的邮箱对应的名字。

    参数:
    existing_emails (dict): 现有的邮箱信息字典
    emails_to_update (dict): 需要更新的邮箱信息字典
    """
    for email, name in emails_to_update.items():
        if validate_email(email):
            if email in existing_emails:
                existing_emails[email] = name
                print(f"Updated email: {email}")
            else:
                print(f"Email not found, cannot update: {email}")
        else:
            print(f"Invalid email format: {email}")

def execute_transact_items(transact_items):
    """
    执行DynamoDB事务写入操作。

    参数:
    transact_items (list): 事务写入项列表

    返回:
    dict: 包含状态码和处理结果的字典
    """
    try:
        dynamodb.meta.client.transact_write_items(TransactItems=transact_items)
        return create_response(200, 'Account updated successfully.')
    except Exception as e:
        print(f"Failed to store data: {e}")
        return create_response(500, 'Failed to store data due to an internal error.')

def create_response(status_code, message):
    """
    创建API响应。

    参数:
    status_code (int): HTTP状态码
    message (str): 响应消息

    返回:
    dict: 包含状态码和消息的字典
    """
    return {
        'statusCode': status_code,
        'body': json.dumps(message)
    }

def lambda_handler(event, context):
    """
    更新DynamoDB中账户信息的Lambda函数。
    
    输入事件的格式应为：
    {
        "account_id": "123456789012",
        "params": {
            "add": { "email1@example.com": "Name1", ... },
            "delete": { "email2@example.com": null, ... },
            "update": { "email3@example.com": "Name3", ... }
        }
    }

    参数:
    event (dict): 包含账户ID和邮箱信息的事件字典
    context (LambdaContext): Lambda执行环境的上下文对象

    返回:
    dict: 包含状态码和处理结果的字典
    """
    account_id = event.get('account_id')
    params = event.get('params', {})

    if not account_id or not account_id.isdigit() or len(account_id) != 12:
        return create_response(400, 'Invalid account ID format.')

    existing_account = get_account(account_id)
    if not existing_account:
        print(f"Account ID {account_id} not found.")
        return create_response(404, f'Account ID {account_id} not found.')

    existing_emails = existing_account.get('allowed_users', {})

    transact_items = prepare_transact_items(account_id, existing_emails, params)

    return execute_transact_items(transact_items)
