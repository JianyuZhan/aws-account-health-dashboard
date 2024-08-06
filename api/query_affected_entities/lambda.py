import json
import boto3
from boto3.dynamodb.conditions import Key

# 在deploy/data_collection/cdk_infra/backend_stack.py中把common/打包为
# Lambda Layer, 导致最终的layer是没有common/这一层目录. 所以，使用
# try...except... 这种技巧
try:
    # 本地开发时使用
    from common.utils import create_response, parse_event
    from common.constants import AFFECTED_ENTITIES_TABLE_NAME
except ImportError:
    # 部署到 Lambda 时使用
    from utils import create_response, parse_event
    from constants import AFFECTED_ENTITIES_TABLE_NAME
    
# 表名常量 (保持和 deploy/data_collection/cdk_infra/backend_stack.py 一致)
NAME_PREFIX = 'AwsHealthDashboard'
AFFECTED_ENTITIES_TABLE_NAME = f'{NAME_PREFIX}AffectedEntities'

# 初始化 DynamoDB 客户端
dynamodb = boto3.resource('dynamodb')
affected_entities_table = dynamodb.Table(AFFECTED_ENTITIES_TABLE_NAME)

def query_affected_entities(filters):
    """
    根据给定的过滤条件从 DynamoDB 中查询受影响的实体。

    参数:
    filters (list): 过滤条件的列表，每个元素是一个包含 EventArn 和/或 AccountId 的字典。

    返回:
    list: 符合条件的所有实体项列表
    """
    matched_entities = []

    for filter_item in filters:
        try:
            # 根据 filters 构建查询条件
            key_condition = Key('EventArn').eq(filter_item['EventArn']) if 'EventArn' in filter_item else None
            account_condition = Key('AccountId').eq(filter_item['AccountId']) if 'AccountId' in filter_item else None
            
            # 构建查询表达式
            if key_condition and account_condition:
                response = affected_entities_table.query(
                    KeyConditionExpression=key_condition & account_condition
                )
            elif key_condition:
                response = affected_entities_table.query(
                    KeyConditionExpression=key_condition
                )
            else:
                continue

            # 添加查询到的实体到结果集中
            matched_entities.extend(response.get('Items', []))
            print(f"Query successful for filter: {filter_item}. Retrieved {len(response.get('Items', []))} items.")

        except Exception as e:
            print(f"Error querying entities for filter {filter_item}: {str(e)}")

    return matched_entities

def lambda_handler(event, context):
    """
    Lambda函数入口，用于根据 entity_filters 查询相关的受影响实体，并返回结果。

    参数:
    event (dict): 输入事件，包含一个键 'entity_filters'，其值为过滤条件的列表。
        'entity_filters' 是一个列表，其中的每个元素都是一个字典，用于指定查询条件。
        
        接受的参数格式示例：
        {
            "entity_filters": [
                {
                    "EventArn": "arn:aws:health:example:event-id",
                    "AccountId": "123456789012"
                },
                {
                    "AccountId": "123456789012"
                },
                {
                    "EventArn": "arn:aws:health:example:event-id"
                }
            ]
        }
        
        - EventArn: (可选) 字符串，表示事件的唯一标识符。如果提供，则查询该事件影响的实体。
        - AccountId: (可选) 字符串，表示账户ID。如果提供，则查询该账户受到的影响。
        - 如果同时提供 EventArn 和 AccountId，则查询该事件下特定账户受影响的实体。
        - 如果只提供 EventArn，则查询该事件影响的所有实体。
        - 如果只提供 AccountId，则查询所有事件中该账户受影响的所有实体。

    context: AWS Lambda上下文对象（此处未使用）。

    返回:
    dict: 包含状态码、消息以及查询结果或错误的响应。
    """
    # 解析事件
    parsed_event = parse_event(event)
    print("Parsed event:", json.dumps(parsed_event, indent=2))

    # 获取过滤条件列表
    entity_filters = parsed_event.get('entity_filters', [])

    if not entity_filters:
        print("Error: 'entity_filters' is empty.")
        return create_response(400, "错误: 'entity_filters' 不能为空。")

    # 查询受影响的实体
    affected_entities = query_affected_entities(entity_filters)

    # 返回最终响应
    return create_response(200, "Affected entities retrieved successfully.", {"affected_entities": affected_entities})