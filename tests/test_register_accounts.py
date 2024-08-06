import json
import boto3
import re
import pytest
import requests

# 表名常量 (保持和deploy/data_collection/cdk_infr/infra_stack.py一致)
NAME_PREFIX = 'AwsHealthDashboard'
ACCOUNTS_TABLE_NAME = f'{NAME_PREFIX}ManagementAccounts'
USERS_TABLE_NAME = f'{NAME_PREFIX}Users'

# 初始化DynamoDB客户端
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
dynamodb_client = boto3.client('dynamodb', region_name='us-east-1')
accounts_table = dynamodb.Table(ACCOUNTS_TABLE_NAME)
users_table = dynamodb.Table(USERS_TABLE_NAME)

# 邮箱格式校验的正则表达式
email_regex = re.compile(r"[^@]+@[^@]+\.[^@]+")

API_GATEWAY_URL = 'https://su8suqixml.execute-api.us-east-1.amazonaws.com/prod/register_accounts'

def validate_email(email):
    """
    使用正则表达式校验邮箱格式。

    参数:
    email (str): 需要校验的邮箱地址

    返回:
    bool: 如果邮箱格式有效则返回True，否则返回False
    """
    return email_regex.match(email) is not None

def invoke_api_gateway(payload):
    """
    调用API Gateway并返回响应。

    参数:
    payload (dict): 要传递给API Gateway的事件字典

    返回:
    dict: API Gateway的响应
    """
    response = requests.post(API_GATEWAY_URL, json=payload)
    return response.json(), response.status_code

def get_account_data(account_id):
    """
    从DynamoDB中获取账户数据。

    参数:
    account_id (str): 账户ID

    返回:
    dict: 账户数据
    """
    response = accounts_table.get_item(Key={'account_id': account_id})
    return response.get('Item')

def get_user_data(user_id):
    """
    从DynamoDB中获取用户数据。

    参数:
    user_id (str): 用户ID

    返回:
    dict: 用户数据
    """
    response = users_table.get_item(Key={'user_id': user_id})
    return response.get('Item')

@pytest.fixture
def setup_dynamodb():
    # 清理表中的所有数据
    accounts_table.scan()['Items']
    users_table.scan()['Items']

    yield

    # 测试完成后清理表中的所有数据
    for item in accounts_table.scan()['Items']:
        accounts_table.delete_item(Key={'account_id': item['account_id']})
    for item in users_table.scan()['Items']:
        users_table.delete_item(Key={'user_id': item['user_id']})

def test_register_accounts_success(setup_dynamodb):
    """
    测试成功注册账户的情况
    """
    test_payload = {
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

    response, status_code = invoke_api_gateway(test_payload)
    assert status_code == 200
    assert response['statusCode'] == 200

    for account_id in test_payload.keys():
        account_data = get_account_data(account_id)
        assert account_data is not None
        assert account_data['account_id'] == account_id
        assert account_data['cross_account_role'] == test_payload[account_id]['cross_account_role']

        allowed_users = test_payload[account_id]['allowed_users']
        for email in allowed_users.keys():
            user_data = get_user_data(email)
            assert user_data is not None
            assert account_id in user_data['allowed_accounts']

def test_register_accounts_invalid_account_id(setup_dynamodb):
    """
    测试注册账户时提供无效账户ID的情况
    """
    test_payload = {
        "invalid_account_id": {
            "cross_account_role": "RoleName",
            "allowed_users": {
                "email1@example.com": "John Doe"
            }
        }
    }

    response, status_code = invoke_api_gateway(test_payload)
    assert status_code == 400

def test_register_accounts_missing_cross_account_role(setup_dynamodb):
    """
    测试注册账户时缺少cross_account_role的情况
    """
    test_payload = {
        "123456789012": {
            "allowed_users": {
                "email1@example.com": "John Doe"
            }
        }
    }

    response, status_code = invoke_api_gateway(test_payload)
    assert status_code == 400

def test_register_accounts_invalid_email_format(setup_dynamodb):
    """
    测试注册账户时提供无效邮箱格式的情况
    """
    test_payload = {
        "123456789012": {
            "cross_account_role": "RoleName",
            "allowed_users": {
                "invalid_email_format": "John Doe"
            }
        }
    }

    response, status_code = invoke_api_gateway(test_payload)
    assert status_code == 200

    account_data = get_account_data("123456789012")
    assert account_data is not None
    assert "invalid_email_format" not in account_data['allowed_users']

if __name__ == "__main__":
    pytest.main()
