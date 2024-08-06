import json
import pytest
from common import get_account_data, get_user_data, register_accounts, clean_table, accounts_table, users_table

@pytest.fixture
def setup_dynamodb():
    # 开始测试前清理已经有的表
    clean_table(accounts_table)
    clean_table(users_table)

    yield

    # 完成测试后清理创建的表
    clean_table(accounts_table)
    clean_table(users_table)

def test_register_accounts_success(setup_dynamodb):
    test_payload = {
        "123456789033": {
            "cross_account_role": "RoleName",
            "allowed_users": {
                "email1@example.com": "John Doe",
                "email2@example.com": "Jane Doe"
            }
        },
        "098765432188": {
            "cross_account_role": "AnotherRoleName",
            "allowed_users": {
                "email3@example.com": "Alice",
                "email4@example.com": "Bob"
            }
        }
    }

    response, status_code = register_accounts(test_payload)
    print("Full response:", response)
    assert status_code == 200

    response_body = response['body'] if 'body' in response else response
    print("Response body:", response_body)

    response_json = json.loads(response_body) if isinstance(response_body, str) else response_body
    assert response_json.get('message') == 'Accounts registered successfully.'

    for account_id in test_payload.keys():
        account_data = get_account_data(account_id)
        assert account_data is not None
        assert account_data['AccountId'] == account_id
        assert account_data['CrossAccountRole'] == test_payload[account_id]['cross_account_role']

        allowed_users = test_payload[account_id]['allowed_users']
        for email in allowed_users.keys():
            user_data = get_user_data(email)
            assert user_data is not None
            assert account_id in user_data['AllowedAccountIds']

def test_register_accounts_invalid_account_id(setup_dynamodb):
    test_payloads = [
        {
            "invalid_account_id": {
                "cross_account_role": "RoleName",
                "allowed_users": {
                    "email1@example.com": "John Doe"
                }
            }
        },
        {
            "123": {
                "cross_account_role": "RoleName",
                "allowed_users": {
                    "email1@example.com": "John Doe"
                }
            }
        }
    ]

    for test_payload in test_payloads:
        response, status_code = register_accounts(test_payload)
        assert status_code == 400

def test_register_accounts_missing_cross_account_role(setup_dynamodb):
    test_payload = {
        "123456789012": {
            "allowed_users": {
                "email1@example.com": "John Doe"
            }
        }
    }

    response, status_code = register_accounts(test_payload)
    assert status_code == 400

def test_register_accounts_invalid_email_format(setup_dynamodb):
    test_payload = {
        "123456789012": {
            "cross_account_role": "RoleName",
            "allowed_users": {
                "invalid_email_format": "John Doe",
                "email2@.com": "Jane Doe",
                "email3@com": "Alice"
            }
        }
    }

    response, status_code = register_accounts(test_payload)
    assert status_code == 200

    account_data = get_account_data("123456789012")
    assert account_data is not None
    assert "invalid_email_format" not in account_data['AllowedUsers']
    assert "email2@.com" not in account_data['AllowedUsers']
    assert "email3@com" not in account_data['AllowedUsers']

def test_register_accounts_duplicate_account_id(setup_dynamodb):
    test_payload = {
        "123456789033": {
            "cross_account_role": "RoleName",
            "allowed_users": {
                "email1@example.com": "John Doe"
            }
        }
    }

    response, status_code = register_accounts(test_payload)
    assert status_code == 200

    response, status_code = register_accounts(test_payload)
    assert status_code == 400
    response_body = response['body'] if 'body' in response else response
    response_json = json.loads(response_body) if isinstance(response_body, str) else response_body
    assert response_json.get('message') == 'AccountId already exists: 123456789033'

def test_register_accounts_existing_user_with_non_empty_allowedaccountids(setup_dynamodb):
    initial_payload = {
        "123456789012": {
            "cross_account_role": "RoleName",
            "allowed_users": {
                "email1@example.com": "John Doe"
            }
        }
    }
    
    response, status_code = register_accounts(initial_payload)
    assert status_code == 200

    user_data = get_user_data("email1@example.com")
    assert user_data is not None
    assert "123456789012" in user_data['AllowedAccountIds']

    new_payload = {
        "098765432109": {
            "cross_account_role": "AnotherRoleName",
            "allowed_users": {
                "email1@example.com": "John Doe"
            }
        }
    }

    response, status_code = register_accounts(new_payload)
    assert status_code == 200

    user_data = get_user_data("email1@example.com")
    assert user_data is not None
    assert "123456789012" in user_data['AllowedAccountIds']
    assert "098765432109" in user_data['AllowedAccountIds']

if __name__ == "__main__":
    pytest.main()
