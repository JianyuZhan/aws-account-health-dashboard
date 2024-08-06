import json
import boto3
from boto3.dynamodb.types import TypeDeserializer

# 在deploy/data_collection/cdk_infra/backend_stack.py中把common/打包为
# Lambda Layer, 导致最终的layer是没有common/这一层目录. 所以，使用
# try...except... 这种技巧
try:
    # 本地开发时使用
    from common.utils import create_response, parse_event
    from common.constants import ACCOUNTS_TABLE_NAME, USERS_TABLE_NAME
except ImportError:
    # 部署到 Lambda 时使用
    from utils import create_response, parse_event
    from constants import ACCOUNTS_TABLE_NAME, USERS_TABLE_NAME


# 初始化DynamoDB客户端
dynamodb = boto3.resource('dynamodb')
dynamodb_client = boto3.client('dynamodb')
accounts_table = dynamodb.Table(ACCOUNTS_TABLE_NAME)
users_table = dynamodb.Table(USERS_TABLE_NAME)

deserializer = TypeDeserializer()

def deserialize_item(item):
    """
    反序列化DynamoDB项目

    参数:
    item (dict): 原始DynamoDB项目

    返回:
    dict: 反序列化后的项目
    """
    return {k: deserializer.deserialize(v) for k, v in item.items()}

def get_accounts(account_ids):
    """
    从DynamoDB中批量获取账户信息。

    参数:
    account_ids (list): 账户ID列表

    返回:
    dict: 账户信息字典，键为账户ID，值为账户详情
    """
    keys = [{'AccountId': {'S': account_id}} for account_id in account_ids]
    response = dynamodb_client.batch_get_item(
        RequestItems={
            ACCOUNTS_TABLE_NAME: {
                'Keys': keys
            }
        }
    )
    print("Batch get item response:", response)
    return {deserialize_item(item)['AccountId']: deserialize_item(item) for item in response['Responses'][ACCOUNTS_TABLE_NAME]}

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
    user_updates = {}

    for account_id in account_ids:
        if account_id in existing_accounts:
            allowed_users = list(existing_accounts[account_id]['AllowedUsers'].keys())
            print(f"Allowed users for account {account_id}: {allowed_users}")

            # 删除管理账户表中的记录
            transact_items.append({
                'Delete': {
                    'TableName': ACCOUNTS_TABLE_NAME,
                    'Key': {'AccountId': {'S': account_id}}
                }
            })

            # 合并对用户表的更新操作
            for email in allowed_users:
                if email not in user_updates:
                    user_updates[email] = set()
                user_updates[email].add(account_id)
        else:
            print(f"Account ID {account_id} not found.")
            # 不再返回错误响应，返回空列表
            return []

    print(f"user_updates: {user_updates}")

    for email, account_id_set in user_updates.items():
        print(f"Preparing to update {email} to delete account IDs {list(account_id_set)}")
        transact_items.append({
            'Update': {
                'TableName': USERS_TABLE_NAME,
                'Key': {'UserId': {'S': email}},
                'UpdateExpression': 'DELETE AllowedAccountIds :account_ids',
                'ExpressionAttributeValues': {':account_ids': {'SS': list(account_id_set)}}
            }
        })

    print("Prepared transaction items:", transact_items)
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
    # 解析事件
    event = parse_event(event)
    print("Parsed event:", json.dumps(event, indent=2))

    account_ids = event.get('account_ids')

    if not account_ids or not all(acc_id.isdigit() and len(acc_id) == 12 for acc_id in account_ids):
        return create_response(400, 'Invalid account ID format.')

    existing_accounts = get_accounts(account_ids)
    transact_items = prepare_transact_items(account_ids, existing_accounts)

    if not transact_items:  # 如果事务项为空，返回找不到账户ID的响应
        return create_response(404, 'One or more Account IDs not found.')

    return execute_transact_items(transact_items)
