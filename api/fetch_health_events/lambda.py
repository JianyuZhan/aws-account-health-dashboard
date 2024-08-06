import boto3
from botocore.exceptions import ClientError
import os
import json
from datetime import datetime, timedelta, timezone

# 表名常量 (保持和 deploy/data_collection/cdk_infra/infra_stack.py 一致)
NAME_PREFIX = 'AwsHealthDashboard'
ACCOUNTS_TABLE_NAME = f'{NAME_PREFIX}ManagementAccounts'
HEALTH_EVENTS_TABLE_NAME = f'{NAME_PREFIX}HealthEvents'
EVENT_DETAILS_TABLE_NAME = f'{NAME_PREFIX}EventDetails'
AFFECTED_ACCOUNTS_TABLE_NAME = f'{NAME_PREFIX}AffectedAccounts'
AFFECTED_ENTITIES_TABLE_NAME = f'{NAME_PREFIX}AffectedEntities'

# 初始化 DynamoDB 客户端
dynamodb = boto3.resource('dynamodb')
dynamodb_client = boto3.client('dynamodb')
accounts_table = dynamodb.Table(ACCOUNTS_TABLE_NAME)
events_table = dynamodb.Table(HEALTH_EVENTS_TABLE_NAME)
event_details_table = dynamodb.Table(EVENT_DETAILS_TABLE_NAME)
affected_accounts_table = dynamodb.Table(AFFECTED_ACCOUNTS_TABLE_NAME)
affected_entities_table = dynamodb.Table(AFFECTED_ENTITIES_TABLE_NAME)

# 初始化 STS 客户端
sts_client = boto3.client('sts')

LOOKBACK_DAYS = int(os.environ.get('LOOKBACK_DAYS', '90'))

def get_assumed_role_credentials(account_id, role_name):
    """获取指定账户的临时凭证。"""
    assumed_role = sts_client.assume_role(
        RoleArn=f"arn:aws:iam::{account_id}:role/{role_name}",
        RoleSessionName="CrossAccountHealthEvents"
    )
    return assumed_role['Credentials']

def fetch_health_events(health_client, start_time, end_time, event_filters=None):
    """从 AWS Health API 拉取指定时间范围内的健康事件。"""
    events = []
    paginator = health_client.get_paginator('describe_events_for_organization')
    filters = {
        'startTime': {'from': start_time, 'to': end_time},
        'eventStatusCodes': ['open', 'upcoming']  # 不包含 'closed'
    }
    if event_filters:
        filters.update(event_filters)

    for page in paginator.paginate(filter=filters):
        events.extend(page['events'])
    return events

def fetch_event_details(health_client, event_arns):
    """从 AWS Health API 拉取事件详细信息。"""
    details = []
    for i in range(0, len(event_arns), 10):
        batch = event_arns[i:i+10]
        response = health_client.describe_event_details_for_organization(
            organizationEventDetailFilters=[{'eventArn': arn} for arn in batch]
        )
        details.extend(response['successfulSet'])
    return details

def fetch_affected_accounts(health_client, event_arn):
    """从 AWS Health API 拉取受影响的账户信息。"""
    accounts = []
    paginator = health_client.get_paginator('describe_affected_accounts_for_organization')
    for page in paginator.paginate(eventArn=event_arn):
        accounts.extend(page['affectedAccounts'])
    return accounts

def fetch_affected_entities(health_client, event_arn, account_id):
    """从 AWS Health API 拉取受影响的实体信息。"""
    entities = []
    paginator = health_client.get_paginator('describe_affected_entities_for_organization')
    for page in paginator.paginate(filter={'eventArn': event_arn, 'awsAccountId': account_id}):
        entities.extend(page['entities'])
    return entities

def update_dynamodb(account_id, events, event_details, affected_accounts, affected_entities):
    """将健康事件及其详细信息写入 DynamoDB。"""
    if not events:
        return 0, 0, 0, 0

    expiration_time = int((datetime.now(timezone.utc) + timedelta(days=LOOKBACK_DAYS)).timestamp())

    events_count = 0
    with events_table.batch_writer() as batch:
        for event in events:
            start_time = event['startTime'].isoformat() if isinstance(event['startTime'], datetime) else event['startTime']
            end_time = event.get('endTime', '')
            end_time = end_time.isoformat() if isinstance(end_time, datetime) else end_time
            last_updated_time = event['lastUpdatedTime'].isoformat() if isinstance(event['lastUpdatedTime'], datetime) else event['lastUpdatedTime']

            item = {
                'AccountId': account_id,
                'EventArn': event['arn'],
                'Service': event['service'],
                'EventTypeCode': event['eventTypeCode'],
                'EventTypeCategory': event['eventTypeCategory'],
                'Region': event['region'],
                'AvailabilityZone': event.get('availabilityZone', ''),
                'StartTime': start_time,
                'EndTime': end_time,
                'LastUpdatedTime': last_updated_time,
                'StatusCode': event['statusCode'],
                'EventScopeCode': event['eventScopeCode'],
                'ExpirationTime': expiration_time  # 设置过期时间
            }
            batch.put_item(Item=item)
            events_count += 1

    event_details_count = 0
    with event_details_table.batch_writer() as batch:
        for detail in event_details:
            item = {
                'EventArn': detail['event']['arn'],
                'Detail': detail
            }
            batch.put_item(Item=item)
            event_details_count += 1

    affected_accounts_count = 0
    with affected_accounts_table.batch_writer() as batch:
        for account in affected_accounts:
            item = {
                'EventArn': account['eventArn'],
                'AccountId': account['awsAccountId']
            }
            batch.put_item(Item=item)
            affected_accounts_count += 1

    affected_entities_count = 0
    with affected_entities_table.batch_writer() as batch:
        for entity in affected_entities:
            item = {
                'EventArn': entity['eventArn'],
                'EntityId': entity['entityValue'],
                'EntityType': entity['entityType'],
                'StatusCode': entity['statusCode']
            }
            batch.put_item(Item=item)
            affected_entities_count += 1

    # 更新 ManagementAccounts 表中的 LastEventTime 字段
    latest_event_time = max(event['startTime'] for event in events).isoformat()
    accounts_table.update_item(
        Key={'AccountId': account_id},
        UpdateExpression='SET LastEventTime = :val',
        ExpressionAttributeValues={':val': latest_event_time}
    )

    print(f"Updated DynamoDB with {events_count} events, {event_details_count} details, {affected_accounts_count} accounts, and {affected_entities_count} entities for account {account_id}.")
    return events_count, event_details_count, affected_accounts_count, affected_entities_count

def get_registered_accounts():
    """从 DynamoDB 中获取所有已注册的管理账户 ID 及其角色名称。"""
    response = accounts_table.scan()
    accounts = response.get('Items', [])
    print(f"Retrieved {len(accounts)} registered accounts: {[account['AccountId'] for account in accounts]}")
    return [{'AccountId': account['AccountId'], 'RoleName': account['CrossAccountRole']} for account in accounts]

def get_last_event_times():
    """获取所有账户的最后一个健康事件的时间。"""
    last_event_times = {}
    response = accounts_table.scan()
    items = response.get('Items', [])

    for item in items:
        account_id = item['AccountId']
        last_event_time = item.get('LastEventTime')
        if last_event_time:
            last_event_times[account_id] = datetime.fromisoformat(last_event_time)

    return last_event_times

def enable_ttl(table_name, ttl_attribute_name):
    """启用 DynamoDB 表上的 TTL 特性。"""
    try:
        # 获取当前 TTL 配置
        response = dynamodb_client.describe_time_to_live(TableName=table_name)
        ttl_status = response['TimeToLiveDescription']['TimeToLiveStatus']
        
        if ttl_status == 'ENABLED':
            print(f"TTL is already enabled on table {table_name}")
            return
        elif ttl_status == 'DISABLING' or ttl_status == 'DISABLED':
            # 启用 TTL
            response = dynamodb_client.update_time_to_live(
                TableName=table_name,
                TimeToLiveSpecification={
                    'Enabled': True,
                    'AttributeName': ttl_attribute_name
                }
            )
            print(f"TTL enabled on table {table_name} with attribute {ttl_attribute_name}")
        else:
            print(f"Unexpected TTL status for table {table_name}: {ttl_status}")
    except ClientError as e:
        print(f"Failed to enable TTL on table {table_name}. Reason: {e.response['Error']['Message']}")

def fetch_and_update_health_events(accounts, start_time, end_time):
    """从 API 获取所有管理账户的健康事件及其详细信息并更新到 DynamoDB。"""
    last_event_times = get_last_event_times()
    earliest_event_time = None
    total_event_count = 0
    total_details_count = 0
    total_affected_accounts_count = 0
    total_affected_entities_count = 0

    for account in accounts:
        account_id = account['AccountId']
        role_name = account['RoleName']
        last_event_time = last_event_times.get(account_id, start_time)
        credentials = get_assumed_role_credentials(account_id, role_name)
        health_client = boto3.client(
            'health',
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken']
        )
        events = fetch_health_events(health_client, last_event_time, end_time)
        
        if events:
            event_arns = [event['arn'] for event in events]
            event_details = fetch_event_details(health_client, event_arns)
            
            affected_accounts = []
            for event_arn in event_arns:
                accounts = fetch_affected_accounts(health_client, event_arn)
                for account in accounts:
                    affected_accounts.append({'eventArn': event_arn, 'awsAccountId': account})
                    
            affected_entities = []
            for account in affected_accounts:
                entities = fetch_affected_entities(health_client, account['eventArn'], account['awsAccountId'])
                affected_entities.extend(entities)
                
            events_count, event_details_count, affected_accounts_count, affected_entities_count = update_dynamodb(account_id, events, event_details, affected_accounts, affected_entities)
            print(f"Fetched and stored health events, details, accounts, and entities for account {account_id}。")

            total_event_count += events_count
            total_details_count += event_details_count
            total_affected_accounts_count += affected_accounts_count
            total_affected_entities_count += affected_entities_count

            account_earliest_event_time = min(event['startTime'] for event in events)
            if earliest_event_time is None or account_earliest_event_time < earliest_event_time:
                earliest_event_time = account_earliest_event_time

    # 把HEALTH_EVENTS_TABLE_NAME表中的'ExpirationTime'设为TTL字段，dynamodb到期会自动删除条目
    enable_ttl(HEALTH_EVENTS_TABLE_NAME, 'ExpirationTime')

    return earliest_event_time, total_event_count, total_details_count, total_affected_accounts_count, total_affected_entities_count

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
    Lambda 函数入口，用于拉取所有管理账户的健康事件并写入 DynamoDB。

    参数：
    event (dict): 事件字典，包含可选的 account_ids 列表

    响应格式：
    {
        "statusCode": 200,
        "body": {
            "earliest_event_time": "此次更新最早一条事件的时间",
            "total_event_count": "总条数",
            "total_details_count": "事件详情总条数",
            "total_affected_accounts_count": "受影响账户总条数",
            "total_affected_entities_count": "受影响实体总条数"
        }
    }
    """
    # 解析事件
    event = parse_event(event)
    print("Parsed event:", json.dumps(event, indent=2))

    account_ids = event.get('account_ids', None)

    # 获取所有注册的管理账户
    registered_accounts = get_registered_accounts()

    if account_ids:
        # 过滤仅包含指定 account_ids 的账户
        accounts = [account for account in registered_accounts if account['AccountId'] in account_ids]
    else:
        accounts = registered_accounts

    if len(accounts) == 0:
        return {
            'statusCode': 200,
            'body': json.dumps({
                "message": "No accounts to fetch"
            })
        }
    print(f'Fetching health events for accounts: {accounts}')

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=LOOKBACK_DAYS)

    # 获取所有管理账户的健康事件并更新到 DynamoDB
    earliest_event_time, \
    total_event_count, \
    total_details_count, \
    total_affected_accounts_count, \
    total_affected_entities_count = fetch_and_update_health_events(accounts, start_time, end_time)

    return {
        'statusCode': 200,
        'body': json.dumps({
            'earliest_event_time': earliest_event_time.isoformat(),  # 将 datetime 转换为字符串
            'total_event_count': total_event_count,
            'total_details_count': total_details_count,
            'total_affected_accounts_count': total_affected_accounts_count,
            'total_affected_entities_count': total_affected_entities_count
        })
    }
