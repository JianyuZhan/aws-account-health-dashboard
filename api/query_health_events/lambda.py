import boto3
from botocore.exceptions import BotoCoreError, ClientError
import json
from datetime import datetime, timezone

# 在deploy/data_collection/cdk_infra/backend_stack.py中把common/打包为
# Lambda Layer, 导致最终的layer是没有common/这一层目录. 所以，使用
# try...except... 这种技巧
try:
    # 本地开发时使用
    from common.utils import create_response, parse_event
    from common.constants import NAME_PREFIX, HEALTH_EVENTS_TABLE_NAME, USERS_TABLE_NAME
except ImportError:
    # 部署到 Lambda 时使用
    from utils import create_response, parse_event
    from constants import NAME_PREFIX, HEALTH_EVENTS_TABLE_NAME, USERS_TABLE_NAME


# 初始化 DynamoDB 客户端
dynamodb = boto3.resource('dynamodb')
dynamodb_client = boto3.client('dynamodb')
events_table = dynamodb.Table(HEALTH_EVENTS_TABLE_NAME)
users_table = dynamodb.Table(USERS_TABLE_NAME)

# 初始化 STS 客户端
sts_client = boto3.client('sts')

ALLOW_ACCOUNTS_LAMBDA_FUNC_NAME = f'{NAME_PREFIX}GetAllowedAccounts'
def get_allowed_accounts(user_id):
    """调用另一个Lambda函数获取当前用户允许访问的账户，并进行错误处理。"""
    lambda_client = boto3.client('lambda')
    
    try:
        response = lambda_client.invoke(
            FunctionName=ALLOW_ACCOUNTS_LAMBDA_FUNC_NAME,
            InvocationType='RequestResponse',
            Payload=json.dumps({'user_id': user_id})
        )
        
        # 检查调用Lambda的HTTP状态码
        status_code = response.get('StatusCode')
        if status_code != 200:
            raise Exception(f"Failed to invoke Lambda function. StatusCode: {status_code}")

        # 读取并解析响应负载
        payload = response['Payload'].read()
        result = json.loads(payload)
        print(f"Invoke lambda ALLOW_ACCOUNTS_LAMBDA_FUNC_NAME result: {result}")

        body = json.loads(result['body'])

        # 检查响应中是否包含错误信息
        if 'FunctionError' in response:
            raise Exception(f"Lambda function error: {result.get('errorMessage', 'Unknown error')}")

        # 检查响应是否包含预期的字段
        if 'allowed_accounts' not in body:
            raise Exception("Unexpected response format: 'allowed_accounts' not found")

        return body['allowed_accounts']

    except (BotoCoreError, ClientError) as e:
        # 处理调用Lambda API时的Boto3客户端错误
        print(f"Error invoking Lambda function: {str(e)}")
        raise Exception(f"Error invoking Lambda function: {str(e)}")
    except json.JSONDecodeError as e:
        # 处理JSON解析错误
        print(f"Error parsing Lambda function response: {str(e)}")
        raise Exception(f"Error parsing Lambda function response: {str(e)}")
    except Exception as e:
        # 处理其他所有错误
        print(f"An error occurred: {str(e)}")
        raise Exception(f"An error occurred: {str(e)}")

def assume_role(account_id, role_name):
    """获取指定账户的临时凭证。"""
    assumed_role = sts_client.assume_role(
        RoleArn=f"arn:aws:iam::{account_id}:role/{role_name}",
        RoleSessionName="CrossAccountHealthEvents"
    )
    return assumed_role['Credentials']

def fetch_health_events_from_api(credentials, event_filters):
    """从 AWS Health API 拉取指定过滤条件的健康事件。"""
    health_client = boto3.client(
        'health',
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretAccessKey'],
        aws_session_token=credentials['SessionToken']
    )
    events = []
    paginator = health_client.get_paginator('describe_events_for_organization')

    for page in paginator.paginate(filter=event_filters):
        events.extend(page['events'])
    return events

def build_dynamodb_filter_expression(event_filters):
    """构建 DynamoDB 查询的过滤表达式。"""
    if not event_filters:
        return None, {}

    filter_expression = None
    expression_attribute_values = {}

    # 处理 awsAccountIds 过滤器
    if 'awsAccountIds' in event_filters:
        filter_expression = boto3.dynamodb.conditions.Attr('AccountId').is_in(event_filters['awsAccountIds'])
    
    # 处理其他过滤器
    if 'eventTypeCodes' in event_filters:
        condition = boto3.dynamodb.conditions.Attr('EventTypeCode').is_in(event_filters['eventTypeCodes'])
        filter_expression = condition if not filter_expression else filter_expression & condition
    
    if 'services' in event_filters:
        condition = boto3.dynamodb.conditions.Attr('Service').is_in(event_filters['services'])
        filter_expression = condition if not filter_expression else filter_expression & condition
    
    if 'regions' in event_filters:
        condition = boto3.dynamodb.conditions.Attr('Region').is_in(event_filters['regions'])
        filter_expression = condition if not filter_expression else filter_expression & condition
    
    if 'startTime' in event_filters:
        from_time = event_filters['startTime']['from'].isoformat()
        to_time = event_filters['startTime'].get('to', datetime.now(timezone.utc)).isoformat()
        condition = boto3.dynamodb.conditions.Attr('StartTime').between(from_time, to_time)
        filter_expression = condition if not filter_expression else filter_expression & condition
        expression_attribute_values[':start_time_from'] = from_time
        expression_attribute_values[':start_time_to'] = to_time
    
    if 'endTime' in event_filters:
        from_time = event_filters['endTime']['from'].isoformat()
        to_time = event_filters['endTime'].get('to', datetime.now(timezone.utc)).isoformat()
        condition = boto3.dynamodb.conditions.Attr('EndTime').between(from_time, to_time)
        filter_expression = condition if not filter_expression else filter_expression & condition
        expression_attribute_values[':end_time_from'] = from_time
        expression_attribute_values[':end_time_to'] = to_time
    
    if 'lastUpdatedTime' in event_filters:
        from_time = event_filters['lastUpdatedTime']['from'].isoformat()
        to_time = event_filters['lastUpdatedTime'].get('to', datetime.now(timezone.utc)).isoformat()
        condition = boto3.dynamodb.conditions.Attr('LastUpdatedTime').between(from_time, to_time)
        filter_expression = condition if not filter_expression else filter_expression & condition
        expression_attribute_values[':last_updated_time_from'] = from_time
        expression_attribute_values[':last_updated_time_to'] = to_time
    
    if 'entityArns' in event_filters:
        condition = boto3.dynamodb.conditions.Attr('EventArn').is_in(event_filters['entityArns'])
        filter_expression = condition if not filter_expression else filter_expression & condition
    
    if 'eventTypeCategories' in event_filters:
        condition = boto3.dynamodb.conditions.Attr('EventTypeCategory').is_in(event_filters['eventTypeCategories'])
        filter_expression = condition if not filter_expression else filter_expression & condition
    
    if 'eventStatusCodes' in event_filters:
        condition = boto3.dynamodb.conditions.Attr('StatusCode').is_in(event_filters['eventStatusCodes'])
        filter_expression = condition if not filter_expression else filter_expression & condition
    
    return filter_expression, expression_attribute_values

def fetch_health_events_from_db(event_filter):
    """从 DynamoDB 中获取指定过滤条件的健康事件。"""
    
    # 如果 event_filter 为空，直接查询所有记录
    if not event_filter:
        print("No filter provided, scanning all items in the table.")
        response = events_table.scan()  # 不使用 FilterExpression，扫描整个表
        return response.get('Items', [])
    
    # 构建 FilterExpression
    filter_expression, expression_attribute_values = build_dynamodb_filter_expression(event_filter)
    
    if not filter_expression:
        print("No filter expression generated. Returning empty list.")
        return []  # 如果没有生成有效的过滤条件，返回空列表

    print(f"Scan events_table using \nfilter expression: {filter_expression}\nexpression attribute values: {expression_attribute_values}")
    response = events_table.scan(
        FilterExpression=filter_expression,
        ExpressionAttributeValues=expression_attribute_values
    )
    return response.get('Items', [])

def check_update_allowed_accounts(user_id, accounts):
    """检查用户是否有权限访问指定的账户，并合并过滤条件中的 awsAccountIds。"""
    allowed_accounts = get_allowed_accounts(user_id)

    if not allowed_accounts:
        print(f"No allowed accounts specified for user {user_id}. Assuming access to all accounts.")
        allowed_account_ids = set(accounts.keys())  # 允许访问所有传入的账户
    else:
        allowed_account_ids = {acc['AccountId'] for acc in allowed_accounts}

    unauthorized_accounts = []
    for account_id, account_info in accounts.items():
        if account_id not in allowed_account_ids:
            unauthorized_accounts.append(account_id)

        if 'event_filter' not in account_info:
            continue
        
        event_filters = account_info['event_filter']
        if 'awsAccountIds' in event_filters:
            disallowed_account_ids = set(event_filters['awsAccountIds']) - allowed_account_ids
            if disallowed_account_ids:
                print(f"Warning: User {user_id} is not authorized to access awsAccountIds: {disallowed_account_ids}")
            event_filters['awsAccountIds'] = list(set(event_filters['awsAccountIds']) & allowed_account_ids)
        else:
            event_filters['awsAccountIds'] = list(allowed_account_ids)
        account_info['event_filter'] = event_filters

    if unauthorized_accounts:
        print(f"Warning: Skipped {unauthorized_accounts}. Because User {user_id} is not authorized to access these accounts.")

    return accounts


def query_events_from_db(accounts):
    """从数据库中查询健康事件。"""
    all_events = []
    for account_id, account_info in accounts.items():
        event_filter = account_info['event_filter']
        events = fetch_health_events_from_db(event_filter)
        all_events.extend(events)
    return all_events

def query_events_from_api(accounts):
    """从 API 查询健康事件。"""
    all_events = []
    for account_id, account_info in accounts.items():
        role_name = account_info['cross_account_role']
        event_filters = account_info['event_filter']
        credentials = assume_role(account_id, role_name)
        events = fetch_health_events_from_api(credentials, event_filters)
        all_events.extend(events)
    return all_events

def parse_event(event):
    """
    解析事件，根据不同来源进行解析。

    参数:
    event (dict): 原始事件字典

    返回:
    dict: 解析后的事件字典
    """
    if 'body' in event:
        try:
            body = json.loads(event['body'])
            if 'body' in body:
                body = json.loads(body['body'])
            return body
        except json.JSONDecodeError:
            return {}
    return event

def lambda_handler(event, context):
    """
    Lambda 函数入口，用于查询健康事件。

    请求格式：
    {
        "user_id": "用户ID",
        "accounts": {
            "management_account1": {
                "cross_account_role": "角色名称",
                "event_filter": {
                    // 过滤条件，参考 AWS Health API 文档
                }
            },
            "management_account2": { ... }
        },
        "from_db": true 或 false
    }

    响应格式：
    {
        "statusCode": 200,
        "body": "事件列表的 JSON 字符串"
    }
    """
    # 解析事件
    event = parse_event(event)
    print("Parsed event:", json.dumps(event, indent=2))

    user_id = event['user_id']
    accounts = event['accounts']
    from_db = event.get('from_db', True)

    # 检查用户权限，并合并过滤条件
    accounts = check_update_allowed_accounts(user_id, accounts)
    print(f"Fetching events for {accounts}")

    if from_db:
        # 从数据库中查询健康事件
        all_events = query_events_from_db(accounts)
    else:
        # 从 API 查询健康事件
        all_events = query_events_from_api(accounts)

    print(f"Fetched {len(all_events)} health events")
    return create_response(200, 
                           "Fetched health events data successfully",
                           {
                            "all_events": all_events
                           })