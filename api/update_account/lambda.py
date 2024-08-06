import json
import boto3
import re
from boto3.dynamodb.conditions import Key

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
dynamodb_resource = boto3.resource('dynamodb')
dynamodb_client = boto3.client('dynamodb')
accounts_table = dynamodb_resource.Table(ACCOUNTS_TABLE_NAME)
users_table = dynamodb_resource.Table(USERS_TABLE_NAME)

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
    response = accounts_table.get_item(Key={'AccountId': account_id})
    return response.get('Item')

def get_user(user_id):
    """
    从DynamoDB中获取用户信息。

    参数:
    user_id (str): 用户ID

    返回:
    dict: 用户信息
    """
    response = users_table.get_item(Key={'UserId': user_id})
    return response.get('Item')

def create_user_update_transaction(user_id, account_id, action, username=None):
    """
    创建用户更新事务项目。

    参数:
    user_id (str): 用户ID
    account_id (str): 账户ID
    action (str): 操作类型 ("add", "delete", "update")
    username (str): 用户名 (可选)

    返回:
    dict: 更新事务项目
    """
    if action == 'add':
        update_expression = "ADD AllowedAccountIds :account_id SET UserName = if_not_exists(UserName, :user_name)"
        expression_attribute_values = {':account_id': {'SS': [account_id]}, ':user_name': {'S': username}}
    elif action == 'delete':
        update_expression = "DELETE AllowedAccountIds :account_id"
        expression_attribute_values = {':account_id': {'SS': [account_id]}}
    else:
        update_expression = "SET AllowedAccountIds = :account_id, UserName = :user_name"
        expression_attribute_values = {':account_id': {'SS': [account_id]}, ':user_name': {'S': username}}

    return {
        'Update': {
            'TableName': USERS_TABLE_NAME,
            'Key': {'UserId': {'S': user_id}},
            'UpdateExpression': update_expression,
            'ExpressionAttributeValues': expression_attribute_values,
        }
    }

def handle_user_updates(user_ids, account_id, add_users, delete_users, update_users):
    """
    处理用户更新，生成事务项目。

    参数:
    user_ids (set): 用户ID集合
    account_id (str): 账户ID
    add_users (dict): 添加的用户字典
    delete_users (dict): 删除的用户字典
    update_users (dict): 更新的用户字典

    返回:
    list: 事务项目列表
    """
    transactions = []
    for user_id in user_ids:
        user = get_user(user_id)
        if not user:
            if user_id in delete_users:
                print(f"User {user_id} not found, skipping delete.")
                continue  # 如果是删除操作且用户不存在，跳过
            print(f"User {user_id} not found, creating new entry.")

        if user_id in add_users:
            transactions.append(create_user_update_transaction(user_id, account_id, 'add', add_users[user_id]))
        elif user_id in delete_users:
            transactions.append(create_user_update_transaction(user_id, account_id, 'delete'))
        elif user_id in update_users:
            transactions.append(create_user_update_transaction(user_id, account_id, 'update', update_users[user_id]))

    return transactions

def update_account_users(account_id, users):
    """
    更新账户的AllowedUsers。

    参数:
    account_id (str): 账户ID
    users (dict): 更新后的用户字典

    返回:
    dict: 更新事务项目
    """
    if users:
        expression_attribute_values = {':val': {'M': {k: {'S': v} for k, v in users.items()}}}
    else:
        expression_attribute_values = {':val': {'M': {}}}
    
    print(f"Updating AllowedUsers for account {account_id} with: {expression_attribute_values}")

    return {
        'Update': {
            'TableName': ACCOUNTS_TABLE_NAME,
            'Key': {'AccountId': {'S': account_id}},
            'UpdateExpression': 'SET AllowedUsers = :val',
            'ExpressionAttributeValues': expression_attribute_values,
        }
    }

def handle_account_update(account_id, existing_account, params):
    """
    处理账户更新，生成事务项目。

    参数:
    account_id (str): 账户ID
    existing_account (dict): 表中的accout_id对应的对象
    params (dict): 更新参数，包含add, delete, update字典

    返回:
    list: 事务项目列表
    """
    existing_users = existing_account.get('AllowedUsers', {})
    print(f"Existing AllowedUsers: {existing_users}")

    add_users = params.get('add', {})
    delete_users = params.get('delete', {})
    update_users = params.get('update', {})

    user_ids = set(add_users.keys()).union(delete_users.keys()).union(update_users.keys())
    if len(user_ids) != len(add_users) + len(delete_users) + len(update_users):
        return create_response(400, "A user can't be in add/update/delete at the same time.")

    for user_id, username in add_users.items():
        if user_id in existing_users:
            print(f"User {user_id} already exists in AllowedUsers, skipping add.")
            continue
        existing_users[user_id] = username

    for user_id in delete_users.keys():
        if user_id not in existing_users:
            print(f"User {user_id} not found in AllowedUsers, skipping delete.")
            continue
        del existing_users[user_id]

    for user_id, username in update_users.items():
        existing_users[user_id] = username

    account_update_transaction = update_account_users(account_id, existing_users)
    user_update_transactions = handle_user_updates(user_ids, account_id, add_users, delete_users, update_users)
    
    return [account_update_transaction] + user_update_transactions

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
    # 解析事件
    event = parse_event(event)
    print("Parsed event:", json.dumps(event, indent=2))

    account_id = event.get('account_id')
    params = event.get('params', {})

    if not account_id or not account_id.isdigit() or len(account_id) != 12:
        print(f"Invalid account ID format: {account_id}")
        return create_response(400, 'Invalid account ID format.')

    existing_account = get_account(account_id)
    if not existing_account:
        print(f"Account ID {account_id} not found.")
        return create_response(404, f'Account ID {account_id} not found.')

    transactions = handle_account_update(account_id, existing_account, params)
    if isinstance(transactions, dict):  # 检查是否返回错误响应
        return transactions
    
    if transactions:
        try:
            for i in range(0, len(transactions), 25):  # DynamoDB事务写入每次最多处理25个项目
                batch = transactions[i:i+25]
                print(f"Processing batch: {json.dumps(batch, indent=2)}")
                response = dynamodb_client.transact_write_items(TransactItems=batch)
                print(f"Batch of {len(batch)} items stored successfully. Response: {response}")
        except Exception as e:
            print(f"Transaction failed: {e}")
            return create_response(500, 'Failed to update account and user information.')

    return create_response(200, 'Account and user information updated successfully.')
