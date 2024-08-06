import json

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

def create_response(status_code, message, data=None):
    """
    创建API响应。

    参数:
    status_code (int): HTTP状态码
    message (str): 响应消息
    data (dict, optional): 包含其他信息的可选字典

    返回:
    dict: 包含状态码、消息和可选数据的字典
    """
    body = {"message": message}

    # 如果提供了 data 参数，将其合并到 body 中
    if data is not None:
        body.update(data)

    def json_dump_default(obj):
        from decimal import Decimal
        if isinstance(obj, Decimal):
            if obj.to_integral_value() == obj:
                return int(obj)
            else:
                return float(obj)
        return obj
    
    return {
        'statusCode': status_code,
        'headers': {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",  # 允许所有来源访问
            "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
            "Access-Control-Allow-Methods": "OPTIONS,GET,POST",  # 允许的HTTP方法
        },
        'body': json.dumps(body, default=json_dump_default)
    }