import json
import boto3
import re
from collections import defaultdict

# 在deploy/data_collection/cdk_infra/backend_stack.py中把common/打包为
# Lambda Layer, 导致最终的layer是没有common/这一层目录. 所以，使用
# try...except... 这种技巧
try:
    # 本地开发时使用
    from common.utils import create_response, parse_event
    from common.constants import ACCOUNTS_TABLE_NAME, USERS_TABLE_NAME, LAMBDA_ROLE
except ImportError:
    # 部署到 Lambda 时使用
    from utils import create_response, parse_event
    from constants import ACCOUNTS_TABLE_NAME, USERS_TABLE_NAME, LAMBDA_ROLE


iam_client = boto3.client('iam')

# 初始化DynamoDB客户端
dynamodb = boto3.resource('dynamodb')
dynamodb_client = boto3.client('dynamodb')
accounts_table = dynamodb.Table(ACCOUNTS_TABLE_NAME)
users_table = dynamodb.Table(USERS_TABLE_NAME)

# 邮箱格式校验的正则表达式
email_regex = re.compile(r"[^@]+@[^@]+\.[^@]+")

def validate_email(email):
    """
    使用正则表达式校验邮箱格式。

    参数:
    email (str): 需要校验的邮箱地址

    返回:
    bool: 如果邮箱格式有效则返回True，否则返回False
    """
    return email_regex.match(email) is not None

def account_exists(account_id):
    """
    检查账户是否已存在。

    参数:
    account_id (str): 账户ID

    返回:
    bool: 如果账户已存在则返回True，否则返回False
    """
    response = accounts_table.get_item(Key={'AccountId': account_id})
    return 'Item' in response

def prepare_transact_items(account_id, cross_account_role, valid_emails, user_updates):
    """
    准备DynamoDB的事务写入项。

    参数:
    account_id (str): 账户ID
    cross_account_role (str): 跨账户角色名称
    valid_emails (dict): 有效的邮箱信息
    user_updates (dict): 用户更新信息

    返回:
    list: 事务写入项列表
    """
    transact_items = [
        {
            'Put': {
                'TableName': ACCOUNTS_TABLE_NAME,
                'Item': {
                    'AccountId': {'S': account_id},
                    'CrossAccountRole': {'S': cross_account_role},
                    'AllowedUsers': {'M': {email: {'S': name} for email, name in valid_emails.items()}}
                },
                'ConditionExpression': 'attribute_not_exists(AccountId)'
            }
        }
    ]
    
    for email, name in valid_emails.items():
        if email not in user_updates:
            user_updates[email] = {'account_ids': set(), 'name': name}
        user_updates[email]['account_ids'].add(account_id)
    
    return transact_items

def update_lambda_assume_role_policy(account_id, cross_account_role):
    try:
        role_arn = f"arn:aws:iam::{account_id}:role/{cross_account_role}"
        
        policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": "sts:AssumeRole",
                    "Resource": [role_arn]
                }
            ]
        }

        existing_policies = iam_client.list_role_policies(RoleName=LAMBDA_ROLE)
        print(f"Existing policy for role {LAMBDA_ROLE}: {existing_policies}")
        
        if 'AssumeRolePolicy' in existing_policies['PolicyNames']:
            existing_policy = iam_client.get_role_policy(
                RoleName=LAMBDA_ROLE,
                PolicyName='AssumeRolePolicy'
            )
            existing_policy_document = existing_policy['PolicyDocument']
            print(f"Existing policy document: {existing_policy_document}")
            
            for statement in existing_policy_document['Statement']:
                if statement['Action'] == "sts:AssumeRole" and role_arn in statement['Resource']:
                    print(f"AssumeRole policy already includes {role_arn}")
                    return True

            existing_policy_document['Statement'][0]['Resource'].append(role_arn)
            policy_document = existing_policy_document
        
        print(f"New policy document: {policy_document}")

        iam_client.put_role_policy(
            RoleName=LAMBDA_ROLE,
            PolicyName='AssumeRolePolicy',
            PolicyDocument=json.dumps(policy_document)
        )
        print(f"Successfully updated policy to allow {LAMBDA_ROLE} to assume {role_arn}")
        return True
    except Exception as e:
        print(f"Failed to update Lambda assume role policy. Reason: {str(e)}")
        return False

def lambda_handler(event, context):
    """
    处理注册账户信息的Lambda函数。

    输入事件的格式应为：
    {
        "123456789012": {
            "cross_account_role": "RoleName",
            "allowed_users": {
                "email1@example.com": "John Doe",
                "email2@example.com": "Jane Doe"
            }
        },
        "098765432109": {
            "cross_account_role": "AnotherRoleName",
            "allowed_users": {
                "email1@example.com": "John Doe",
                "email3@example.com": "Alice",
                "email4@example.com": "Bob"
            }
        }
    }

    参数:
    event (dict): 包含账户ID、角色名称和邮箱信息的事件字典
    context (LambdaContext): Lambda执行环境的上下文对象

    返回:
    dict: 包含状态码和处理结果的字典
    """
    # 解析事件
    event = parse_event(event)
    print("Parsed event:", json.dumps(event, indent=2))

    transact_items = []
    assume_roles = {}
    user_updates = defaultdict(lambda: {'account_ids': set(), 'name': ''})

    for account_id, account_info in event.items():
        print(f"Processing account_id: {account_id}")
        
        # 校验AccountId是否为12位数字
        if not account_id.isdigit() or len(account_id) != 12:
            message = f'Invalid AccountId: {account_id}'
            print(message)
            return create_response(400, message)

        # 检查AccountId是否已存在
        if account_exists(account_id):
            message = f'AccountId already exists: {account_id}'
            print(message)
            return create_response(400, message)

        cross_account_role = account_info.get('cross_account_role')
        if not cross_account_role:
            message = f'Missing cross_account_role for AccountId: {account_id}'
            print(message)
            return create_response(400, message)

        allowed_users = account_info.get('allowed_users', {})
        valid_emails = {}
        for email, name in allowed_users.items():
            if validate_email(email):
                valid_emails[email] = name
            else:
                message = f"Invalid email format: {email}"
                print(message)
                return create_response(400, message)

        transact_items.extend(prepare_transact_items(account_id, cross_account_role, valid_emails, user_updates))
        assume_roles[account_id] = cross_account_role

    # 先更新IAM assume role policy，失败了提前退出, 不做后面的注册动作
    for account_id, cross_account_role in assume_roles.items():
        if not update_lambda_assume_role_policy(account_id, cross_account_role):
            return create_response(500, f"Failed to update IAM assume_role policy for account {account_id}'s role {cross_account_role}.")
        
    # 添加用户更新项到事务中
    for email, data in user_updates.items():
        account_ids = list(data['account_ids'])
        user_name = data['name']
        transact_items.append({
            'Update': {
                'TableName': USERS_TABLE_NAME,
                'Key': {'UserId': {'S': email}}, # 这个key必须与backend_stack.py中创建表时的key一致
                'UpdateExpression': 'ADD AllowedAccountIds :account_ids SET UserName = if_not_exists(UserName, :user_name)',
                'ExpressionAttributeValues': {
                    ':account_ids': {'SS': account_ids},  # 确保 AllowedAccountIds 是 String Set 类型
                    ':user_name': {'S': user_name}
                }
            }
        })

    print(f"Prepared {len(transact_items)} transact items.")

    if transact_items:
        try:
            for i in range(0, len(transact_items), 25):
                batch = transact_items[i:i+25]
                print(f"Processing batch: {batch}")
                response = dynamodb_client.transact_write_items(TransactItems=batch)
                print(f"Batch of {len(batch)} items stored successfully. Response: {response}")
        except Exception as e:
            print(f"Failed to store data. Reason: {str(e)}")
            return create_response(500, 'Failed to store data.')

    return create_response(200, 'Accounts registered successfully.')
