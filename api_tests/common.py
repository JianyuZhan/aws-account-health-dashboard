import json
import boto3
import re
import os
import requests

# 表名常量 (保持和deploy/data_collection/cdk_infra/backend_stack.py一致)
NAME_PREFIX = 'AwsHealthDashboard'
ACCOUNTS_TABLE_NAME = f'{NAME_PREFIX}ManagementAccounts'
USERS_TABLE_NAME = f'{NAME_PREFIX}Users'
HEALTH_EVENTS_TABLE_NAME = f'{NAME_PREFIX}HealthEvents'

# 初始化DynamoDB客户端
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
accounts_table = dynamodb.Table(ACCOUNTS_TABLE_NAME)
users_table = dynamodb.Table(USERS_TABLE_NAME)
health_table = dynamodb.Table(HEALTH_EVENTS_TABLE_NAME)

# 邮箱格式校验的正则表达式
email_regex = re.compile(r"[^@]+@[^@]+\.[^@]+")

# 从 api_url.txt 文件中读取 URL 并拼接最终的 API URL
def get_api_url(api_name):
    file_path = os.path.join(os.path.dirname(__file__), 'api_url.txt')
    if not os.path.exists(file_path):
        raise FileNotFoundError("The 'api_url.txt' file is missing. Please create it with the base API URL. Example content:\nhttps://your-api-id.execute-api.us-east-1.amazonaws.com/prod")

    with open(file_path, 'r') as file:
        base_url = ''
        for line in file:
            if not line.startswith("#"):
                base_url = line.strip()
                break

    if not base_url:
        raise ValueError("The 'api_url.txt' file is empty or incorrectly formatted. Please add the base API URL. Example content:\nhttps://your-api-id.execute-api.us-east-1.amazonaws.com/prod")

    return f"{base_url}/{api_name}"

def validate_email(email):
    """
    使用正则表达式校验邮箱格式。

    参数:
    email (str): 需要校验的邮箱地址

    返回:
    bool: 如果邮箱格式有效则返回True，否则返回False
    """
    return email_regex.match(email) is not None

def get_account_data(account_id):
    """
    从DynamoDB中获取账户数据。

    参数:
    account_id (str): 账户ID

    返回:
    dict: 账户数据
    """
    response = accounts_table.get_item(Key={'AccountId': account_id})
    return response.get('Item')

def get_user_data(user_id):
    """
    从DynamoDB中获取用户数据。

    参数:
    user_id (str): 用户ID

    返回:
    dict: 用户数据
    """
    response = users_table.get_item(Key={'UserId': user_id})
    return response.get('Item')

def register_accounts(payload):
    """
    注册账户。

    参数:
    payload (dict): 要传递给API Gateway的事件字典

    返回:
    dict: API Gateway的响应
    """
    REGISTER_API_URL = get_api_url('register_accounts')
    response = requests.post(REGISTER_API_URL, json={"body": json.dumps(payload)})
    return response.json(), response.status_code

def clean_table(table):
    """
    清理表中的所有数据。

    参数:
    table: DynamoDB 表实例
    """
    scan = table.scan()
    key_names = [key['AttributeName'] for key in table.key_schema]
    with table.batch_writer() as batch:
        for each in scan['Items']:
            batch.delete_item(
                Key={key: each[key] for key in key_names}
            )
