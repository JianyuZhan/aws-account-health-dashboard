import boto3
import json

# 在deploy/data_collection/cdk_infra/backend_stack.py中把common/打包为
# Lambda Layer, 导致最终的layer是没有common/这一层目录. 所以，使用
# try...except... 这种技巧
try:
    # 本地开发时使用
    from common.utils import create_response, parse_event
    from common.constants import USERS_TABLE_NAME
except ImportError:
    # 部署到 Lambda 时使用
    from utils import create_response, parse_event
    from constants import USERS_TABLE_NAME
    

# 初始化 DynamoDB 客户端
dynamodb = boto3.resource('dynamodb')
users_table = dynamodb.Table(USERS_TABLE_NAME)

def get_user(user_id):
    """
    从 DynamoDB 中获取用户信息。
    
    参数:
    user_id (str): 用户 ID
    
    返回:
    dict: 用户信息
    """
    response = users_table.get_item(
        Key={
            'UserId': user_id  # 确保与表定义中的主键名称一致
        }
    )
    return response.get('Item')

def get_allowed_accounts(user_id):
    """
    获取用户允许访问的账户信息。
    
    参数:
    user_id (str): 用户 ID
    
    返回:
    list: 允许访问的账户信息列表，每个元素是一个包含 AccountId 的字典
    """
    user_item = get_user(user_id)
    if not user_item or 'AllowedAccountIds' not in user_item:
        print(f"User {user_id} does not exist or has no AllowedAccountIds.")
        return []

    allowed_accounts = [{'AccountId': account_id} for account_id in user_item['AllowedAccountIds']]
    print(f"Allowed accounts for user {user_id}: {allowed_accounts}")
    return allowed_accounts

def lambda_handler(event, context):
    """
    Lambda 函数入口，用于获取用户允许访问的账户信息。

    请求格式：
    {
        "user_id": "用户ID"
    }

    响应格式：
    {
        "statusCode": 200,
        "body": {
            "allowed_accounts": "允许访问的账户信息列表"
        }
    }
    """
    # 解析事件
    event = parse_event(event)
    print("Parsed event:", json.dumps(event, indent=2))

    user_id = event['user_id']

    # 获取用户允许访问的账户信息
    allowed_accounts = get_allowed_accounts(user_id)

    return create_response(200, 
                           "Get allowed_accounts successfully",
                           {'allowed_accounts': allowed_accounts})