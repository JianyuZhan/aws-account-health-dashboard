import json
import boto3
from boto3.dynamodb.conditions import Key

# 表名常量 (保持和deploy/data_collection/cdk_infr/infra_stack.py一致)
NAME_PREFIX = 'AwsHealthDashboard'
ACCOUNTS_TABLE_NAME = f'{NAME_PREFIX}ManagementAccounts'
USERS_TABLE_NAME = f'{NAME_PREFIX}Users'

# 初始化DynamoDB客户端
dynamodb = boto3.resource('dynamodb')
dynamodb_client = boto3.client('dynamodb')
accounts_table = dynamodb.Table(ACCOUNTS_TABLE_NAME)
users_table = dynamodb.Table(USERS_TABLE_NAME)

def get_accounts(account_ids):
    """
    从DynamoDB中批量获取账户信息。

    参数:
    account_ids (list): 账户ID列表

    返回:
    dict: 账户信息字典，键为账户ID，值为账户详情
    """
    keys = [{'account_id': {'S': account_id}} for account_id in account_ids]
    response = dynamodb_client.batch_get_item(
        RequestItems={
            ACCOUNTS_TABLE_NAME: {
                'Keys': keys
            }
        }
    )
    return {item['account_id']['S']: item for item in response['Responses'][ACCOUNTS_TABLE_NAME]}

def prepare_transact_items(account_ids, existing_accounts):
    """
    准备DynamoDB的事务写入项。

    参数:
    account_ids (list): 账户ID列表
    existing_accounts (dict): 现有的账户信息字典

    返回:
    list: 事务写入项列表
    """
    transact_items = []

    for account_id in account_ids:
        if account_id in existing_accounts:
            allowed_users = existing_accounts[account_id].get('allowed_users', {}).keys()

            # 删除管理账户表中的记录
            transact_items.append({
                'Delete': {
                    'TableName': ACCOUNTS_TABLE_NAME,
                    'Key': {'account_id': {'S': account_id}}
                }
            })

            # 更新用户表
            for email in allowed_users:
                transact_items.append({
                    'Update': {
                        'TableName': USERS_TABLE_NAME,
                        'Key': {'user_id': {'S': email}},
                        'UpdateExpression': 'DELETE allowed_accounts :account_id',
                        'ExpressionAttributeValues': {':account_id': {'SS': [account_id]}}
                    }
                })
        else:
            print(f"Account ID {account_id} not found.")
            return create_response(404, f'Account ID {account_id} not found.')

    return transact_items

def execute_transact_items(transact_items):
    """
    执行DynamoDB事务写入操作。

    参数:
    transact_items (list): 事务写入项列表

    返回:
    dict: 包含状态码和处理结果的字典
    """
    try:
        dynamodb_client.transact_write_items(TransactItems=transact_items)
        return create_response(200, 'Accounts deregistered successfully.')
    except Exception as e:
        print(f"Failed to delete data: {e}")
        return create_response(500, 'Failed to delete data due to an internal error.')

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
    批量注销DynamoDB中账户信息的Lambda函数。
    
    输入事件的格式应为：
    {
        "account_ids": ["123456789012", "098765432109"]
    }

    参数:
    event (dict): 包含账户ID列表的事件字典
    context (LambdaContext): Lambda执行环境的上下文对象

    返回:
    dict: 包含状态码和处理结果的字典
    """
    account_ids = event.get('account_ids')

    if not account_ids or not all(acc_id.isdigit() and len(acc_id) == 12 for acc_id in account_ids):
        return create_response(400, 'Invalid account ID format.')

    existing_accounts = get_accounts(account_ids)
    transact_items = prepare_transact_items(account_ids, existing_accounts)

    return execute_transact_items(transact_items)
