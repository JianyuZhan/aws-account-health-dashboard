import json
import boto3

# 在deploy/data_collection/cdk_infra/backend_stack.py中把common/打包为
# Lambda Layer, 导致最终的layer是没有common/这一层目录. 所以，使用
# try...except... 这种技巧
try:
    # 本地开发时使用
    from common.utils import create_response, parse_event
    from common.constants import EVENT_DETAILS_TABLE_NAME
except ImportError:
    # 部署到 Lambda 时使用
    from utils import create_response, parse_event
    from constants import EVENT_DETAILS_TABLE_NAME


# 初始化 DynamoDB 客户端
dynamodb_client = boto3.client('dynamodb')


def fetch_event_details(event_arns):
    """
    批量获取指定的事件ARN列表对应的详情。

    参数:
    event_arns (list): 事件ARN的列表

    返回:
    tuple: 包含成功结果列表和失败事件ARN列表的元组
    """
    result = []
    failed_event_arns = []

    try:
        # 批量获取
        print(f"Fetching event details for len({event_arns} ARNs:\n{event_arns}")
        response = dynamodb_client.batch_get_item(
            RequestItems={
                EVENT_DETAILS_TABLE_NAME: {
                    'Keys': [{'EventArn': {'S': arn}} for arn in event_arns]
                }
            }
        )
        # print(f"Received response from DynamoDB: {json.dumps(response, indent=2)}")

        # 获取成功的项目
        if 'Responses' in response and EVENT_DETAILS_TABLE_NAME in response['Responses']:
            for item in response['Responses'][EVENT_DETAILS_TABLE_NAME]:
                # 请保持跟lambda /fetch_health_events中写入event_details表的结构一样
                event_detail = {
                    'event_arn': item['EventArn']['S'],
                    'event_type_category': item.get('EventTypeCategory', {}).get('S', ''),
                    'region': item.get('Region', {}).get('S', ''),
                    'service': item.get('Service', {}).get('S', ''),
                    'end_time': item.get('EndTime', {}).get('S', ''),
                    'availability_zone': item.get('AvailabilityZone', {}).get('S', ''),
                    'status_code': item.get('StatusCode', {}).get('S', ''),
                    'event_scope_code': item.get('EventScopeCode', {}).get('S', ''),
                    'aws_account_id': item.get('AwsAccountId', {}).get('S', ''),
                    'last_updated_time': item.get('LastUpdatedTime', {}).get('S', ''),
                    'event_type_code': item.get('EventTypeCode', {}).get('S', ''),
                    'start_time': item.get('StartTime', {}).get('S', ''),
                    'latest_description': item.get('LatestDescription', {}).get('S', ''),
                    'event_metadata': item.get('EventMetadata', {}).get('M', {})
                }
                result.append(event_detail)
            print(f"Successfully retrieved items: {result}")

        # 获取失败的项目
        if 'UnprocessedKeys' in response and EVENT_DETAILS_TABLE_NAME in response['UnprocessedKeys']:
            for key in response['UnprocessedKeys'][EVENT_DETAILS_TABLE_NAME]['Keys']:
                failed_event_arns.append({
                    'event_arn': key['EventArn']['S'],
                    'reason': '未处理的键，可能是由于请求容量限制'
                })
            print(f"Unprocessed ARNs: {failed_event_arns}")

        # 添加因找不到而失败的项目
        for arn in event_arns:
            if arn not in [item['event_arn'] for item in result]:
                failed_event_arns.append({'event_arn': arn, 'reason': '未找到对应的项'})
                print(f"Event ARN not found: {arn}")

    except Exception as e:
        error_message = str(e)
        failed_event_arns.extend([{'event_arn': arn, 'reason': error_message} for arn in event_arns])
        print(f"Exception occurred: {error_message}")

    return result, failed_event_arns

def lambda_handler(event, context):
    """
    Lambda函数，用于批量获取指定的事件ARN列表对应的详情。

    参数:
    event (dict): 输入事件，包含一个键 'event_arns'，其值为事件ARN的列表。
    context: AWS Lambda上下文对象（此处未使用）。

    返回:
    dict: 包含状态码、消息以及结果或错误的响应。
    """
    # 解析事件
    parsed_event = parse_event(event)
    print("Parsed event:", json.dumps(parsed_event, indent=2))

    event_arns = parsed_event.get('event_arns', [])

    if not event_arns:
        print("Error: 'event_arns' is empty.")
        return create_response(400, "'event_arns' is empty, no event details to query.")

    # 获取事件详情
    event_details, failed_event_arns = fetch_event_details(event_arns)

    # 返回最终响应
    final_response = create_response(200, "Fetched event details successfully.", {
        "event_details": event_details,
        "failed_event_arns": failed_event_arns
    })
    print(f"Final response: {json.dumps(final_response, ensure_ascii=False)}")

    return final_response
