import pytest
from common import (
    accounts_table,
    users_table,
    register_accounts,
    get_account_data,
    get_user_data,
    clean_table,
    get_api_url
)
import requests
import json

UPDATE_API_URL = get_api_url('update_account')
print(f"URL: {UPDATE_API_URL}")

def invoke_update_api_gateway(payload):
    """
    调用更新账户的API Gateway并返回响应。

    参数:
    payload (dict): 要传递给API Gateway的事件字典

    返回:
    dict: API Gateway的响应
    """
    response = requests.put(UPDATE_API_URL, json={"body": json.dumps(payload)})
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

def test_update_account_success_add_update_delete(setup_dynamodb):
    """
    测试成功更新账户，包括添加、更新和删除用户
    """
    # 先注册账户以便后续更新
    register_payload = {
        "123456789012": {
            "cross_account_role": "RoleName",
            "allowed_users": {
                "email1@example.com": "John Doe",
                "email2@example.com": "Jane Doe"
            }
        }
    }
    register_response, status_code = register_accounts(register_payload)
    assert status_code == 200

    # 准备更新payload
    update_payload = {
        "account_id": "123456789012",
        "params": {
            "add": {
                "email3@example.com": "Alice",
                "email4@example.com": "Bob"
            },
            "update": {
                "email1@example.com": "John Smith"
            },
            "delete": {
                "email2@example.com": None
            }
        }
    }

    update_response, status_code = invoke_update_api_gateway(update_payload)
    assert status_code == 200

    # 验证更新结果
    account_data = get_account_data("123456789012")
    assert account_data is not None
    assert account_data['AllowedUsers']['email1@example.com'] == "John Smith"
    assert "email2@example.com" not in account_data['AllowedUsers']
    assert account_data['AllowedUsers']['email3@example.com'] == "Alice"
    assert account_data['AllowedUsers']['email4@example.com'] == "Bob"

    # 验证用户表
    user_data = get_user_data("email1@example.com")
    assert user_data is not None
    assert "123456789012" in user_data['AllowedAccountIds']
    assert user_data['UserName'] == "John Smith"

    # email2@example.com被删除了，所以AllowedAccountIds要么不存在了（为空这个key会
    # 被删除），或对应的accoutId不在其中了
    user_data = get_user_data("email2@example.com")
    assert user_data is not None
    assert 'AllowedAccountIds' not in user_data or \
        "123456789012" not in user_data['AllowedAccountIds']

    user_data = get_user_data("email3@example.com")
    assert user_data is not None
    assert "123456789012" in user_data['AllowedAccountIds']
    assert user_data['UserName'] == "Alice"

    user_data = get_user_data("email4@example.com")
    assert user_data is not None
    assert "123456789012" in user_data['AllowedAccountIds']
    assert user_data['UserName'] == "Bob"

def test_update_account_conflict(setup_dynamodb):
    """
    测试当用户在add, update, delete中同时存在时的冲突处理
    """
    # 先注册账户以便后续更新
    register_payload = {
        "123456789012": {
            "cross_account_role": "RoleName",
            "allowed_users": {
                "email1@example.com": "John Doe"
            }
        }
    }
    register_response, status_code = register_accounts(register_payload)
    assert status_code == 200

    # 准备有冲突的更新payload
    update_payload = {
        "account_id": "123456789012",
        "params": {
            "add": {
                "email1@example.com": "John Smith"
            },
            "delete": {
                "email1@example.com": None
            }
        }
    }

    update_response, status_code = invoke_update_api_gateway(update_payload)
    print(f'test_update_account_conflict res: {update_response}')
    assert status_code == 400  # 应该返回冲突错误

def test_update_account_invalid_account_id(setup_dynamodb):
    """
    测试无效的账户ID
    """
    update_payload = {
        "account_id": "invalid_account_id",
        "params": {
            "add": {
                "email1@example.com": "John Doe"
            }
        }
    }

    update_response, status_code = invoke_update_api_gateway(update_payload)
    print(f'test_update_account_invalid_account_id res: {update_response}')
    assert status_code == 400  # 应该返回无效账户ID错误

def test_update_account_not_found(setup_dynamodb):
    """
    测试找不到的账户ID
    """
    update_payload = {
        "account_id": "123456789012",
        "params": {
            "add": {
                "email1@example.com": "John Doe"
            }
        }
    }

    update_response, status_code = invoke_update_api_gateway(update_payload)
    print(f'test_update_account_not_found res: {update_response}')
    assert status_code == 404  # 应该返回找不到账户ID错误
