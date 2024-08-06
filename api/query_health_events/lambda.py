import boto3
import json
from datetime import datetime, timezone

# 表名常量 (保持和 deploy/data_collection/cdk_infra/infra_stack.py 一致)
NAME_PREFIX = 'AwsHealthDashboard'
HEALTH_EVENTS_TABLE_NAME = f'{NAME_PREFIX}HealthEvents'
USERS_TABLE_NAME = f'{NAME_PREFIX}Users'

# 初始化 DynamoDB 客户端
dynamodb = boto3.resource('dynamodb')
dynamodb_client = boto3.client('dynamodb')
events_table = dynamodb.Table(HEALTH_EVENTS_TABLE_NAME)
users_table = dynamodb.Table(USERS_TABLE_NAME)

# 初始化 STS 客户端
sts_client = boto3.client('sts')

def get_allowed_accounts(user_id):
    """调用另一个Lambda函数获取当前用户允许访问的账户。"""
    lambda_client = boto3.client('lambda')
    response = lambda_client.invoke(
        FunctionName='get_allowed_accounts',
        InvocationType='RequestResponse',
        Payload=json.dumps({'user_id': user_id})
    )
    result = json.loads(response['Payload'].read())
    return result['allowed_accounts']

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
    filter_expression = None
    expression_attribute_values = {}

    if 'eventTypeCodes' in event_filters:
        filter_expression = boto3.dynamodb.conditions.Attr('EventTypeCode').is_in(event_filters['eventTypeCodes'])
    
    if 'awsAccountIds' in event_filters:
        condition = boto3.dynamodb.conditions.Attr('AccountId').is_in(event_filters['awsAccountIds'])
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
    
    if 'endTime' in event_filters:
        from_time = event_filters['endTime']['from'].isoformat()
        to_time = event_filters['endTime'].get('to', datetime.now(timezone.utc)).isoformat()
        condition = boto3.dynamodb.conditions.Attr('EndTime').between(from_time, to_time)
        filter_expression = condition if not filter_expression else filter_expression & condition
    
    if 'lastUpdatedTime' in event_filters:
        from_time = event_filters['lastUpdatedTime']['from'].isoformat()
        to_time = event_filters['lastUpdatedTime'].get('to', datetime.now(timezone.utc)).isoformat()
        condition = boto3.dynamodb.conditions.Attr('LastUpdatedTime').between(from_time, to_time)
        filter_expression = condition if not filter_expression else filter_expression & condition
    
    if 'entityArns' in event_filters:
        condition = boto3.dynamodb.conditions.Attr('EntityArn').is_in(event_filters['entityArns'])
        filter_expression = condition if not filter_expression else filter_expression & condition
    
    if 'entityValues' in event_filters:
        condition = boto3.dynamodb.conditions.Attr('EntityValue').is_in(event_filters['entityValues'])
        filter_expression = condition if not filter_expression else filter_expression & condition
    
    if 'eventTypeCategories' in event_filters:
        condition = boto3.dynamodb.conditions.Attr('EventTypeCategory').is_in(event_filters['eventTypeCategories'])
        filter_expression = condition if not filter_expression else filter_expression & condition
    
    if 'eventStatusCodes' in event_filters:
        condition = boto3.dynamodb.conditions.Attr('StatusCode').is_in(event_filters['eventStatusCodes'])
        filter_expression = condition if not filter_expression else filter_expression & condition
    
    return filter_expression, expression_attribute_values

def fetch_health_events_from_db(event_filters):
    """从 DynamoDB 中获取指定过滤条件的健康事件。"""
    filter_expression, expression_attribute_values = build_dynamodb_filter_expression(event_filters)
    
    if not filter_expression:
        return []

    response = events_table.scan(
        FilterExpression=filter_expression,
        ExpressionAttributeValues=expression_attribute_values
    )
    return response.get('Items', [])

def check_update_allowed_accounts(user_id, accounts):
    """检查用户是否有权限访问指定的账户，并合并过滤条件中的 awsAccountIds。"""
    allowed_accounts = get_allowed_accounts(user_id)
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
        print(f"Warning: User {user_id} is not authorized to access accounts: {unauthorized_accounts}")

    return accounts

def query_events_from_db(accounts):
    """从数据库中查询健康事件。"""
    all_events = []
    for account_id, account_info in accounts.items():
        event_filters = account_info['event_filter']
        events = fetch_health_events_from_db(event_filters)
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
    from_db = event.get('from_db', False)

    # 检查用户权限，并合并过滤条件
    accounts = check_update_allowed_accounts(user_id, accounts)

    if from_db:
        # 从数据库中查询健康事件
        all_events = query_events_from_db(accounts)
    else:
        # 从 API 查询健康事件
        all_events = query_events_from_api(accounts)

    return {
        'statusCode': 200,
        'body': json.dumps(all_events)
    }