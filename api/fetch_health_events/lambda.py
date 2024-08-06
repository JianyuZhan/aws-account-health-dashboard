import boto3
import os
import json
from datetime import datetime, timedelta, timezone

# 表名常量 (保持和deploy/data_collection/cdk_infr/infra_stack.py一致)
NAME_PREFIX = 'AwsHealthDashboard'
ACCOUNTS_TABLE_NAME = f'{NAME_PREFIX}ManagementAccounts'
HEALTH_EVENTS_TABLE_NAME = f'{NAME_PREFIX}HealthEvents'

# 初始化DynamoDB客户端
dynamodb = boto3.resource('dynamodb')
dynamodb_client = boto3.client('dynamodb')
accounts_table = dynamodb.Table(ACCOUNTS_TABLE_NAME)
events_table = dynamodb.Table(HEALTH_EVENTS_TABLE_NAME)

# 初始化STS客户端
sts_client = boto3.client('sts')

LOOKBACK_DAYS = int(os.environ.get('LOOKBACK_DAYS', '90'))

def get_assumed_role_credentials(account_id, role_name):
    """
    获取指定账户的临时凭证。

    参数:
    account_id (str): 账户ID
    role_name (str): 角色名称

    返回:
    dict: 临时凭证
    """
    assumed_role = sts_client.assume_role(
        RoleArn=f"arn:aws:iam::{account_id}:role/{role_name}",
        RoleSessionName="CrossAccountHealthEvents"
    )

    return assumed_role['Credentials']

def fetch_health_events(health_client, start_time, end_time, event_filters=None):
    """
    拉取指定时间范围内的健康事件。

    参数:
    health_client (boto3.client): Health客户端
    start_time (datetime): 开始时间
    end_time (datetime): 结束时间
    event_filters (dict): 可选的事件过滤器

    返回:
    list: 健康事件列表
    """
    events = []
    paginator = health_client.get_paginator('describe_events')
    filters = {
        'startTimes': [{'from': start_time, 'to': end_time}],
        'eventStatusCodes': ['open', 'upcoming', 'closed']
    }
    if event_filters:
        filters.update(event_filters)
    
    for page in paginator.paginate(filter=filters):
        events.extend(page['events'])
    return events

def update_dynamodb(account_id, events):
    """
    将健康事件写入DynamoDB，并更新LastEventTime字段。

    参数:
    account_id (str): 账户ID
    events (list): 健康事件列表
    """
    if not events:
        return

    expiration_time = int((datetime.now(timezone.utc) + timedelta(days=LOOKBACK_DAYS)).timestamp())
    
    with events_table.batch_writer() as batch:
        for event in events:
            batch.put_item(
                Item={
                    'AccountId': account_id,
                    'EventArn': event['arn'],
                    'EventType': event['eventTypeCode'],
                    'StartTime': event['startTime'].isoformat(),
                    'EndTime': event.get('endTime', '').isoformat(),
                    'LastUpdatedTime': event['lastUpdatedTime'].isoformat(),
                    'StatusCode': event['statusCode'],
                    'ExpirationTime': expiration_time  # 设置过期时间
                }
            )
    
    # 更新ManagementAccounts表中的LastEventTime字段
    latest_event_time = max(event['startTime'] for event in events)
    accounts_table.update_item(
        Key={'AccountId': account_id},
        UpdateExpression='SET LastEventTime = :val',
        ExpressionAttributeValues={':val': latest_event_time}
    )
    print(f"Updated DynamoDB with {len(events)} events for account {account_id}.")

def get_registered_accounts():
    """
    从DynamoDB中获取所有已注册的管理账户ID及其角色名称。

    返回:
    list: 管理账户信息列表
    """
    response = accounts_table.scan()
    accounts = response.get('Items', [])
    print(f"Retrieved {len(accounts)} registered accounts.")
    return [{'AccountId': account['AccountId'], 'RoleName': account['CROSS_ACCOUNT_ROLE_NAME']} for account in accounts]

def get_last_event_times():
    """
    获取所有账户的最后一个健康事件的时间。

    返回:
    dict: 每个账户ID对应的最后一个事件时间
    """
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
    """
    启用DynamoDB表上的TTL特性。

    参数:
    table_name (str): 表名
    ttl_attribute_name (str): 用作TTL的属性名称
    """
    try:
        response = dynamodb_client.update_time_to_live(
            TableName=table_name,
            TimeToLiveSpecification={
                'Enabled': True,
                'AttributeName': ttl_attribute_name
            }
        )
        print(f"TTL enabled on table {table_name} with attribute {ttl_attribute_name}")
    except dynamodb_client.exceptions.ValidationException as e:
        if "TTL is already enabled" in str(e):
            print(f"TTL is already enabled on table {table_name}")
        else:
            raise

def lambda_handler(event, context):
    """
    Lambda函数入口，用于拉取健康事件并写入DynamoDB。
    """
    management_account_ids = event.get('ManagementAccountIDs')
    event_filters = event.get('EventFilters')

    if not management_account_ids:
        accounts = get_registered_accounts()
    else:
        response = accounts_table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('AccountId').is_in(management_account_ids)
        )
        accounts = response.get('Items', [])
        accounts = [{'AccountId': account['AccountId'], 'RoleName': account['CROSS_ACCOUNT_ROLE_NAME']} for account in accounts]

    end_time = datetime.now(timezone.utc)
    
    # 获取所有账户的最后一个事件时间
    last_event_times = get_last_event_times()

    for account in accounts:
        account_id = account['AccountId']
        role_name = account['RoleName']
        start_time = last_event_times.get(account_id)
        
        if not start_time:
            start_time = end_time - timedelta(days=LOOKBACK_DAYS)

        credentials = get_assumed_role_credentials(account_id, role_name)
        health_client = boto3.client(
            'health',
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken']
        )

        existing_events = fetch_health_events(health_client, start_time, end_time, event_filters)
        update_dynamodb(account_id, existing_events)
        print(f"Fetched and stored health events for account {account_id}.")

    return {
        'statusCode': 200,
        'body': json.dumps('Health events collected and stored in DynamoDB')
    }
