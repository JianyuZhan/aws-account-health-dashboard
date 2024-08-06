import boto3
from botocore.exceptions import ClientError
import os
import json
from datetime import datetime, timedelta, timezone
import time

# 在deploy/data_collection/cdk_infra/backend_stack.py中把common/打包为
# Lambda Layer, 导致最终的layer是没有common/这一层目录. 所以，使用
# try...except... 这种技巧
try:
    # 本地开发时使用
    from common.utils import create_response, parse_event
    from common.constants import  (ACCOUNTS_TABLE_NAME, HEALTH_EVENTS_TABLE_NAME,
        EVENT_DETAILS_TABLE_NAME, AFFECTED_ACCOUNTS_TABLE_NAME, AFFECTED_ENTITIES_TABLE_NAME)            
except ImportError:
    # 部署到 Lambda 时使用
    from utils import create_response, parse_event
    from constants import  (ACCOUNTS_TABLE_NAME, HEALTH_EVENTS_TABLE_NAME,
        EVENT_DETAILS_TABLE_NAME, AFFECTED_ACCOUNTS_TABLE_NAME, AFFECTED_ENTITIES_TABLE_NAME)  
        

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
        'eventStatusCodes': ['open', 'upcoming', 'closed']
    }
    if event_filters:
        filters.update(event_filters)

    for page in paginator.paginate(filter=filters):
        events.extend(page['events'])
    return events

def fetch_event_details(health_client, event_arns):
    """从 AWS Health API 拉取事件详细信息。"""
    s = time.time()
    details = []
    for i in range(0, len(event_arns), 10):
        batch = event_arns[i:i+10]
        response = health_client.describe_event_details_for_organization(
            organizationEventDetailFilters=[{
                'eventArn': arn,
            } for arn in batch]
        )
        details.extend(response['successfulSet'])
    e = time.time()
    return details, e - s 

def fetch_affected_accounts(health_client, event_arns):
    """从 AWS Health API 拉取受影响的账户信息，返回一个包含事件ARN和相应受影响账户的列表。"""
    s = time.time()
    affected_accounts = []
    paginator = health_client.get_paginator('describe_affected_accounts_for_organization')
    
    for event_arn in event_arns:
        count = 0
        for page in paginator.paginate(eventArn=event_arn):
            for account in page['affectedAccounts']:
                affected_accounts.append({'eventArn': event_arn, 'awsAccountId': account})
                count += 1
        print(f"Fetch {count} affected_accounts for event_arn {event_arn}")
    
    e = time.time()
    return affected_accounts, e - s

def fetch_affected_entities(health_client, affected_accounts):
    """
    从 AWS Health API 拉取受影响的实体信息，返回一个包含事件ARN、账户ID和实体信息的列表，以及执行时间。

    参数:
    - health_client: 用于调用 AWS Health API 的客户端。
    - affected_accounts: 一个包含事件ARN和相应受影响账户ID的列表，每个元素是一个字典，形如：
      [{'eventArn': 'arn:example', 'awsAccountId': '123456789012'}, ...]

    返回:
    - affected_entities: 受影响实体的列表，每个元素包含事件ARN、账户ID和完整的实体信息。
    - cost_time: 执行时间，单位为秒。
    """
    affected_entities = []
    start_time = time.time()
    paginator = health_client.get_paginator('describe_affected_entities_for_organization')
    
    for account in affected_accounts:
        event_arn = account['eventArn']
        account_id = account['awsAccountId']
        count = 0
        
        for page in paginator.paginate(
            organizationEntityFilters=[
                {'eventArn': event_arn, 'awsAccountId': account_id}
            ]
        ):
            entities = page.get('entities', [])
            if len(entities) > 0:
                affected_entities.extend(
                    [{'eventArn': event_arn, 'awsAccountId': account_id, **entity} for entity in entities]
                )
                count += len(entities)
        
        print(f"Fetched {count} affected_entities for event_arn {event_arn} and account_id {account_id}")

    cost_time = time.time() - start_time
    return affected_entities, cost_time

def convert_datetime_to_string(obj):
    """
    递归地将 datetime 对象转换为字符串。
    """
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, datetime):
                obj[key] = value.isoformat()  # 转换为 ISO 格式的字符串
            elif isinstance(value, (dict, list)):
                convert_datetime_to_string(value)
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            if isinstance(value, datetime):
                obj[index] = value.isoformat()
            elif isinstance(value, (dict, list)):
                convert_datetime_to_string(value)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    
    return obj

def insert_events(events, account_id, expiration_time):
    start_time = time.time()
    events_count = 0
    
    # API文档
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/health/client/describe_events_for_organization.html
    with events_table.batch_writer() as batch:
        for event in events:
            item = {
                'AccountId': account_id, # 分区键
                'EventArn': event['arn'], # 排序键
                'Service': event['service'],
                'EventTypeCode': event['eventTypeCode'],
                'EventTypeCategory': event['eventTypeCategory'],
                'EventScopeCode': event['eventScopeCode'],
                'Region': event['region'],
                'AvailabilityZone': event.get('availabilityZone', ''),
                'StartTime': convert_datetime_to_string(event['startTime']),
                'EndTime': convert_datetime_to_string(event.get('endTime', '')),
                'LastUpdatedTime': convert_datetime_to_string(event['lastUpdatedTime']),
                'StatusCode': event['statusCode'],
                 # 表示这个item过期的时间（dynamodb会自动清除）， 通过enable_ttl注册这个字段
                'ExpirationTime': expiration_time
            }
            batch.put_item(Item=item)
            events_count += 1

    cost_time = time.time() - start_time
    print(f"Inserted {events_count} events into DynamoDB for management account {account_id} in {cost_time:.2f} seconds.")
    return events_count

def insert_event_details(event_details):
    start_time = time.time()
    event_details_count = 0

    # API文档
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/health/client/describe_event_details_for_organization.html
    with event_details_table.batch_writer() as batch:
        for detail in event_details:
            converted_detail = convert_datetime_to_string(detail)
            # print(f'converted_detail: {converted_detail}')
            event = converted_detail['event']
            event_description = converted_detail.get('eventDescription', {})
            event_metadata = converted_detail.get('eventMetadata', {})

            item = {
                'EventArn': event['arn'],  # 分区键
                'AwsAccountId': converted_detail.get('awsAccountId', ''),
                'Service': event['service'],
                'EventTypeCode': event['eventTypeCode'],
                'EventTypeCategory': event['eventTypeCategory'],
                'Region': event['region'],
                'AvailabilityZone': event.get('availabilityZone', ''),
                'StartTime': event.get('startTime'),
                'EndTime': event.get('endTime', ''),
                'LastUpdatedTime': event.get('lastUpdatedTime'),
                'StatusCode': event['statusCode'],
                'EventScopeCode': event['eventScopeCode'],
                'LatestDescription': event_description.get('latestDescription', ''),
                'EventMetadata': event_metadata,  # 这里直接存储整个 eventMetadata 字典
            }
            batch.put_item(Item=item)
            event_details_count += 1

    cost_time = time.time() - start_time
    print(f"Inserted {event_details_count} event details into DynamoDB in {cost_time:.2f} seconds.")
    return event_details_count

def insert_affected_accounts(affected_accounts):
    start_time = time.time()
    affected_accounts_count = 0

    # API文档
    # https://boto3.amazonaws.com/v1/documentation/api/1.26.93/reference/services/health/client/describe_affected_accounts_for_organization.html
    with affected_accounts_table.batch_writer() as batch:
        for account in affected_accounts:
            item = {
                'EventArn': account['eventArn'], # 分区键
                'AccountId': account['awsAccountId'] # 排序键
            }
            batch.put_item(Item=item)
            affected_accounts_count += 1

    cost_time = time.time() - start_time
    print(f"Inserted {affected_accounts_count} affected accounts into DynamoDB in {cost_time:.2f} seconds.")
    return affected_accounts_count

def insert_affected_entities(affected_entities):
    start_time = time.time()
    affected_entities_count = 0

    # API文档
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/health/client/describe_affected_entities_for_organization.html
    with affected_entities_table.batch_writer() as batch:
        for entity in affected_entities:
            item = {
                'EventArn': entity['eventArn'],  # 分区键
                'AccountId': entity.get('awsAccountId'),  # 排序键
                'EntityId': entity['entityArn'],
                'EntityValue': entity['entityValue'],
                'EntityUrl': entity.get('entityUrl', ''),
                'LastUpdatedTime': convert_datetime_to_string(entity.get('lastUpdatedTime', '')),
                'EntityType': entity.get('entityType', ''), 
                'StatusCode': entity.get('statusCode', ''),
                'Tags': entity.get('tags', {})
            }
            batch.put_item(Item=item)
            affected_entities_count += 1

    cost_time = time.time() - start_time
    print(f"Inserted {affected_entities_count} affected entities into DynamoDB in {cost_time:.2f} seconds.")
    return affected_entities_count

def update_last_event_time(account_id, events):
    latest_event_time = max(event['startTime'] for event in events).isoformat()
    accounts_table.update_item(
        Key={'AccountId': account_id},
        UpdateExpression='SET LastEventTime = :val',
        ExpressionAttributeValues={':val': latest_event_time}
    )

def update_dynamodb(account_id, events, event_details, affected_accounts, affected_entities):
    """将健康事件及其详细信息写入 DynamoDB。"""

    if not events:
        return 0, 0, 0, 0

    expiration_time = int((datetime.now(timezone.utc) + timedelta(days=LOOKBACK_DAYS)).timestamp())
    start_time = time.time()

    events_count = insert_events(events, account_id, expiration_time)
    event_details_count = insert_event_details(event_details)
    affected_accounts_count = insert_affected_accounts(affected_accounts)
    affected_entities_count = insert_affected_entities(affected_entities)

    update_last_event_time(account_id, events)

    total_cost_time = time.time() - start_time
    print(f"Updated DynamoDB for management account {account_id} in {total_cost_time:.2f} seconds. "
          f"Events: {events_count}, Details: {event_details_count}, "
          f"Accounts: {affected_accounts_count}, Entities: {affected_entities_count}.")

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
    start = time.time()
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
        # 拉取该管理帐号下的所有健康事件
        events = fetch_health_events(health_client, last_event_time, end_time)
        print(f"Fetched {len(events)} events for management account {account} from {last_event_time} to {end_time}")
        
        if events:
            event_arns = [event['arn'] for event in events]

            # 拉取该管理帐号下的所有事件详情
            event_details, cost_time = fetch_event_details(health_client, event_arns)
            print(f"Fetched {len(event_arns)} event_arns for management account {account_id}, cost_time: {cost_time:.2f}s")
            
            # 拉取该管理帐号下的每一个事件所有受影响的帐号（返回[{'eventArn': event_arn, 'awsAccountId': account}])
            affected_accounts, cost_time = fetch_affected_accounts(health_client, event_arns)
            print(f"Fetched {len(affected_accounts)} affected_accounts for management account {account_id}, cost_time: {cost_time:.2f}s")
                    
            # 获取受影响的实体
            affected_entities, cost_time = fetch_affected_entities(health_client, affected_accounts)
            print(f"Fetched {len(affected_entities)} affected_entities for management account {account_id}, cost_time: {cost_time:.2f}s")
                
            # 写入dynamodb
            events_count, \
            event_details_count, \
            affected_accounts_count, \
            affected_entities_count = \
                update_dynamodb(account_id, events, event_details, affected_accounts, affected_entities)
            
            print(f"Fetched and stored health events, details, accounts, and entities for management account {account_id}")

            total_event_count += events_count
            total_details_count += event_details_count
            total_affected_accounts_count += affected_accounts_count
            total_affected_entities_count += affected_entities_count

            account_earliest_event_time = min(event['startTime'] for event in events)
            if earliest_event_time is None or account_earliest_event_time < earliest_event_time:
                earliest_event_time = account_earliest_event_time

    end = time.time()
    print(f"fetch_and_update_health_events cost {end-start:.2f}s for {len(accounts)} management accounts")

    # 把HEALTH_EVENTS_TABLE_NAME表中的'ExpirationTime'设为TTL字段，dynamodb到期会自动删除条目
    enable_ttl(HEALTH_EVENTS_TABLE_NAME, 'ExpirationTime')

    return earliest_event_time, total_event_count, total_details_count, total_affected_accounts_count, total_affected_entities_count

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
        return create_response(200, "No accounts to fetch")
    
    print(f'Fetching health events for accounts: {accounts}')

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=LOOKBACK_DAYS)

    # 获取所有管理账户的健康事件并更新到 DynamoDB
    earliest_event_time, \
    total_event_count, \
    total_details_count, \
    total_affected_accounts_count, \
    total_affected_entities_count = fetch_and_update_health_events(accounts, start_time, end_time)

    return create_response(
        200, 
        "Fetched successfully",
        {
            'earliest_event_time': earliest_event_time.isoformat(),
            'total_event_count': total_event_count,
            'total_details_count': total_details_count,
            'total_affected_accounts_count': total_affected_accounts_count,
            'total_affected_entities_count': total_affected_entities_count
        }
    )