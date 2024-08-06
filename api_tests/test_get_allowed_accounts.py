import json
import pytest
import requests
from common import get_user_data, clean_table, users_table, get_api_url

@pytest.fixture
def setup_dynamodb():
    # 开始测试前清理已有的表
    clean_table(users_table)
    yield
    # 完成测试后清理创建的表
    clean_table(users_table)

def get_allowed_accounts(user_id):
    GET_ALLOWED_ACCOUNTS_API_URL = get_api_url(f'get_allowed_accounts?user_id={user_id}')
    response = requests.get(GET_ALLOWED_ACCOUNTS_API_URL)
    return response.json(), response.status_code

def test_get_allowed_accounts_success(setup_dynamodb):
    # 预先在 DynamoDB 中添加测试用户数据
    test_user_id = "test_user"
    test_user_data = {
        'UserId': test_user_id,
        'AllowedAccountIds': ['123456789012', '098765432109']
    }
    users_table.put_item(Item=test_user_data)

    response, status_code = get_allowed_accounts(test_user_id)
    print("Full response:", response)
    assert status_code == 200

    response_body = response['body'] if 'body' in response else response
    print("Response body:", response_body)

    response_json = json.loads(response_body) if isinstance(response_body, str) else response_body
    allowed_accounts = [{'AccountId': '123456789012'}, {'AccountId': '098765432109'}]
    assert response_json.get('allowed_accounts') == allowed_accounts

def test_get_allowed_accounts_no_allowed_ids(setup_dynamodb):
    # 预先在 DynamoDB 中添加测试用户数据，但不包含 AllowedAccountIds
    test_user_id = "test_user_no_ids"
    test_user_data = {
        'UserId': test_user_id
    }
    users_table.put_item(Item=test_user_data)

    response, status_code = get_allowed_accounts(test_user_id)
    print("Full response:", response)
    assert status_code == 200

    response_body = response['body'] if 'body' in response else response
    print("Response body:", response_body)

    response_json = json.loads(response_body) if isinstance(response_body, str) else response_body
    assert response_json.get('allowed_accounts') == []

def test_get_allowed_accounts_user_not_found(setup_dynamodb):
    response, status_code = get_allowed_accounts("non_existent_user")
    print("Full response:", response)
    assert status_code == 200

    response_body = response['body'] if 'body' in response else response
    print("Response body:", response_body)

    response_json = json.loads(response_body) if isinstance(response_body, str) else response_body
    assert response_json.get('allowed_accounts') == []

if __name__ == "__main__":
    pytest.main()
