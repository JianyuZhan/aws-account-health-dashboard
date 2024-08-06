import pytest
import requests
import json
from common import (
    accounts_table,
    users_table,
    register_accounts,
    get_account_data,
    get_user_data,
    clean_table,
    get_api_url
)

DEREGISTER_API_URL = get_api_url('deregister_accounts')
print(f"URL: {DEREGISTER_API_URL}")

def invoke_deregister_api_gateway(payload):
    """
    调用注销账户的API Gateway并返回响应。

    参数:
    payload (dict): 要传递给API Gateway的事件字典

    返回:
    dict: API Gateway的响应
    """
    response = requests.delete(DEREGISTER_API_URL, json={"body": json.dumps(payload)})
    return response.json(), response.status_code

@pytest.fixture
def setup_dynamodb():
    # 清理表中的所有数据
    clean_table(accounts_table)
    clean_table(users_table)

    yield

    # 测试完成后清理表中的所有数据
    clean_table(accounts_table)
    clean_table(users_table)

def test_deregister_account_success(setup_dynamodb):
    """
    测试成功注销账户，包括删除用户的相关信息
    """
    # 先注册账户以便后续注销
    register_payload = {
        "123456789012": {
            "cross_account_role": "RoleName",
            "allowed_users": {
                "email1@example.com": "John Doe",
                "email2@example.com": "Jane Doe"
            }
        },
        "098765432109": {
            "cross_account_role": "RoleName2",
            "allowed_users": {
                "email1@example.com": "John Doe",
                "email3@example.com": "Alice",
                "email4@example.com": "Bob"
            }
        }
    }
    register_response, status_code = register_accounts(register_payload)
    assert status_code == 200

    # 准备注销payload
    deregister_payload = {
        "account_ids": ["123456789012", "098765432109"]
    }

    deregister_response, status_code = invoke_deregister_api_gateway(deregister_payload)
    print(f'test_deregister_account_success res: {deregister_response}')
    assert status_code == 200

    # 验证注销结果
    account_data = get_account_data("123456789012")
    assert account_data is None

    account_data = get_account_data("098765432109")
    assert account_data is None

    # 验证用户表
    user_data = get_user_data("email1@example.com")
    assert user_data is not None
    assert "AllowedAccounts" not in user_data or "123456789012" not in user_data['AllowedAccounts']

    user_data = get_user_data("email2@example.com")
    assert user_data is not None
    assert "AllowedAccounts" not in user_data or "123456789012" not in user_data['AllowedAccounts']

    user_data = get_user_data("email3@example.com")
    assert user_data is not None
    assert "AllowedAccounts" not in user_data or "098765432109" not in user_data['AllowedAccounts']

    user_data = get_user_data("email4@example.com")
    assert user_data is not None
    assert "AllowedAccounts" not in user_data or "098765432109" not in user_data['AllowedAccounts']

def test_deregister_account_invalid_id(setup_dynamodb):
    """
    测试无效的账户ID
    """
    deregister_payload = {
        "account_ids": ["invalid_account_id"]
    }

    deregister_response, status_code = invoke_deregister_api_gateway(deregister_payload)
    print(f'test_deregister_account_success res: {deregister_response}')
    assert status_code == 400  # 应该返回无效账户ID错误

def test_deregister_account_not_found(setup_dynamodb):
    """
    测试找不到的账户ID
    """
    deregister_payload = {
        "account_ids": ["123456789012"]
    }

    deregister_response, status_code = invoke_deregister_api_gateway(deregister_payload)
    print(f'test_deregister_account_not_found res: {deregister_response}')
    assert status_code == 404  # 应该返回找不到账户ID错误
