import json
import boto3

# 在deploy/data_collection/cdk_infra/backend_stack.py中把common/打包为
# Lambda Layer, 导致最终的layer是没有common/这一层目录. 所以，使用
# try...except... 这种技巧
try:
    # 本地开发时使用
    from common.utils import create_response, parse_event
    from common.constants import ACCOUNTS_TABLE_NAME, AFFECTED_ACCOUNTS_TABLE_NAME
except ImportError:
    # 部署到 Lambda 时使用
    from utils import create_response, parse_event
    from constants import ACCOUNTS_TABLE_NAME, AFFECTED_ACCOUNTS_TABLE_NAME


# 初始化 DynamoDB 客户端
dynamodb = boto3.resource('dynamodb')
dynamodb_client = boto3.client('dynamodb')
accounts_table = dynamodb.Table(ACCOUNTS_TABLE_NAME)
affected_accounts_table = dynamodb.Table(AFFECTED_ACCOUNTS_TABLE_NAME)

def get_affected_accounts(event_arns):
    """
    根据给定的事件ARN列表，从DynamoDB中查询相关的受影响账户。

    参数:
    event_arns (list): 事件ARN的列表

    返回:
    dict: 包含事件ARN和相关的受影响账户ID列表的字典
    """
    affected_accounts_dict = {}

    for arn in event_arns:
        try:
            # 查询指定的 EventArn 相关的所有 AccountId
            response = affected_accounts_table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('EventArn').eq(arn)
            )

            # 获取所有相关的 AccountId 并存储在字典中
            accounts = [item['AccountId'] for item in response.get('Items', [])]
            affected_accounts_dict[arn] = accounts

            print(f"Fetched {len(accounts)} accounts for EventArn: {arn}")

        except Exception as e:
            print(f"Error fetching accounts for EventArn {arn}: {str(e)}")
            affected_accounts_dict[arn] = []

    return affected_accounts_dict

def lambda_handler(event, context):
    """
    Lambda函数入口，用于根据事件ARN列表查询相关的受影响账户，并返回结果。

    参数:
    event (dict): 输入事件，包含一个键 'event_arns'，其值为事件ARN的列表。
        
        接受的参数格式示例：
        {
            "event_arns": [
                "arn:aws:health:example:event-id-1",
                "arn:aws:health:example:event-id-2",
                "arn:aws:health:example:event-id-3"
            ]
        }
        
        - event_arns: (必需) 字符串列表，表示事件的唯一标识符。如果提供，则查询这些事件影响的所有账户。
        
        - 这个列表中的每个 ARN 对应 DynamoDB 表中的 EventArn 分区键。
        - 对于每个 EventArn，系统会查询相关的受影响账户（AccountId），并返回这些账户的列表。

    context: AWS Lambda上下文对象（此处未使用）。

    返回:
    dict: 包含状态码、消息以及查询结果或错误的响应。
    """
    # 解析事件
    parsed_event = parse_event(event)
    print("Parsed event:", json.dumps(parsed_event, indent=2))

    # 获取事件ARN列表
    event_arns = parsed_event.get('event_arns', [])

    if not event_arns:
        print("Error: 'event_arns' is empty.")
        return create_response(400, "错误: 'event_arns' 不能为空。")

    # 查询受影响的账户
    affected_accounts = get_affected_accounts(event_arns)

    # 返回最终响应
    return create_response(200, "Affected accounts retrieved successfully.", 
                           {"affected_accounts": affected_accounts})