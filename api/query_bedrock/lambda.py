import json
import os
import re

import boto3
from botocore.exceptions import ClientError


# 在deploy/data_collection/cdk_infra/backend_stack.py中把common/打包为
# Lambda Layer, 导致最终的layer是没有common/这一层目录. 所以，使用
# try...except... 这种技巧
try:
    # 本地开发时使用
    from common.utils import create_response, parse_event
except ImportError:
    # 部署到 Lambda 时使用
    from utils import create_response, parse_event

DEFAULT_MODEL = "anthropic.claude-3-5-sonnet-20240620-v1:0"
aws_region = os.environ.get("AWS_REGION", "us-west-2")

# Prompt 模板
HE_PROMPT = """
你是一个AWS Health Event的解读专家。
Summary：
根据AWS健康事件{health_event}的内容，请总结以下几个方面：

1. 发生了什么问题？
2. 客户需要采取什么行动？如果不需要采取行动，请说明"无需采取行动"。
3. 此事件可能造成的影响或后果。

总结时请简洁扼要, 不需要重复每点的问题，直接说答案。点与点之间要分行。

Action：
如果需要客户采取行动，请按照以下要求给出AWS CLI指令步骤：

1. 根据所给{resource}资源信息，提供明确的CLI指令。
2. 如果所给资源信息不完整，请给出通用的带变量的CLI指令，使用ACCOUNT变量代表相关AWS账户。
3. 步骤之间的逻辑关系要自然流畅，易于客户理解和操作。

如果不需要客户采取行动，直接回复“客户无需采取行动”。

以面向客户的友好口吻撰写CLI指令步骤说。

<Output>
    <Summary>按上述要求的总结</Summary>
    <Action>按上述要求的行动步骤(如果有的话)</Action>
</Output>
"""

def replace_account_in_arn(prompt):
    arn_regex = re.compile(r'(arn:aws:[a-z0-9\-]+:[a-z0-9\-]*:)([0-9]+)(:[a-z0-9\-:/]*)')
    return arn_regex.sub(r'\1ACCOUNT\3', prompt)

def interpret_health_event(event_desc, affected_entities, model_id=DEFAULT_MODEL):
    """
    使用 Claude 模型生成健康事件的摘要和行动建议。
    
    参数:
    event_desc (str): 健康事件的描述。
    affected_entities (list): 受影响的实体列表。
    model_id (str): 使用的模型ID。

    返回:
    str: 模型生成的结果。
    """
    prompt = HE_PROMPT.format(health_event=event_desc, resource=affected_entities)
    prompt = replace_account_in_arn(prompt)
    result = invoke_claude_model(prompt, model_id=model_id)
    return result

def get_available_models():
    """
    返回所有可用的Anthropic模型ID。
    """
    return [
        "anthropic.claude-3-sonnet-20240229-v1:0:28k",
        "anthropic.claude-3-sonnet-20240229-v1:0:200k",
        "anthropic.claude-3-sonnet-20240229-v1:0",
        "anthropic.claude-3-haiku-20240307-v1:0:48k",
        "anthropic.claude-3-haiku-20240307-v1:0:200k",
        "anthropic.claude-3-haiku-20240307-v1:0",
        "anthropic.claude-3-5-sonnet-20240620-v1:0:18k",
        "anthropic.claude-3-5-sonnet-20240620-v1:0:51k",
        "anthropic.claude-3-5-sonnet-20240620-v1:0:200k",
        "anthropic.claude-3-5-sonnet-20240620-v1:0"
    ]

# 主函数
def invoke_claude_model(query, model_id=DEFAULT_MODEL, max_token=2000, temperature=None, top_p=None, top_k=None):
    """
    调用Claude模型并返回结果。

    参数:
    query (str): 用户输入的查询文本。
    model_id (str): 使用的模型ID，默认为DEFAULT_MODEL。
    max_token (int): 生成的最大token数量，默认为2000。
    temperature (float, optional): 生成文本时使用的温度参数。
    top_p (float, optional): nucleus采样的top-p值。
    top_k (int, optional): top-k采样的top-k值。

    返回:
    str: Claude模型生成的文本应答或错误信息
    boolen: 成功与否
    """
    bedrock = boto3.client(service_name="bedrock-runtime", region_name=aws_region)

    if not model_id:
        model_id = DEFAULT_MODEL

    messages = [{"role": 'user', "content": [{'type': 'text', 'text': query}]}]
    body = {
        "messages": messages,
        "max_tokens": max_token,
        "anthropic_version": "bedrock-2023-05-31",
    }
    if temperature is not None:
        body['temperature'] = temperature
    if top_p is not None:
        body['top_p'] = top_p
    if top_k is not None:
        body['top_k'] = top_k

    try:
        response = bedrock.invoke_model(body=json.dumps(body), modelId=model_id)
        response_body = json.loads(response.get("body").read())
        result = response_body.get("content")[0]['text']
        print(f"Model ID: {model_id}, Prompt: {query}, Result: {result}")
        return result, True
    except ClientError as e:
        # 捕获ThrottlingException错误，并返回适当的响应
        if e.response['Error']['Code'] == 'ThrottlingException':
            print(f"ThrottlingException: {e}")
            return "ThrottlingException: Too many requests, please wait before trying again.", False
        else:
            print(f"Unexpected error: {e}")
            return f"Unexpected error: {e}", False

def lambda_handler(event, context):
    """
    Lambda函数的入口，处理事件描述和受影响实体的请求。

    参数:
    event (dict): 包含事件信息的字典。
    context (object): Lambda执行上下文对象。

    返回:
    dict: API的响应信息。
    """
    parsed_event = parse_event(event)
    event_desc = parsed_event.get('event_desc', '')
    affected_entities = parsed_event.get('affected_entities', [])
    model_id = parsed_event.get('model_id', DEFAULT_MODEL)

    # 验证传入的 model_id 是否在可用模型列表中
    available_models = get_available_models()
    if model_id and model_id not in available_models:
        return create_response(400, f"Invalid model_id: {model_id}. Must be one of {available_models}")

    # 调用解释健康事件的函数
    result, ok = interpret_health_event(event_desc, affected_entities, model_id=model_id)

    if ok:
        return create_response(200, "Model invocation successful", {"result": result})
    else:
        return create_response(400, result)

