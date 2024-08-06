import boto3
import time

'''
这是一个幂等的脚本，用于给HEALTH_EVENTS_TABLE_NAME加二级索引
'''

dynamodb_client = boto3.client('dynamodb')

# 表名常量 (保持和 deploy/data_collection/cdk_infra/backend_stack.py 一致)
NAME_PREFIX = 'AwsHealthDashboard'
HEALTH_EVENTS_TABLE_NAME = f'{NAME_PREFIX}HealthEvents'

# 根据查询场景需求，给HEALTH_EVENTS_TABLE_NAME加二级索引
GSI_DEFINITIONS = [
    {
        'IndexName': 'GSI2',
        'KeySchema': [
            {'AttributeName': 'awsAccountIds', 'KeyType': 'HASH'},
            {'AttributeName': 'StartTime', 'KeyType': 'RANGE'}
        ],
        'Projection': {
            'ProjectionType': 'ALL'
        }
    },
    {
        'IndexName': 'GSI3',
        'KeySchema': [
            {'AttributeName': 'EventTypeCode', 'KeyType': 'HASH'},
            {'AttributeName': 'StartTime', 'KeyType': 'RANGE'}
        ],
        'Projection': {
            'ProjectionType': 'ALL'
        }
    },
    {
        'IndexName': 'GSI4',
        'KeySchema': [
            {'AttributeName': 'Region', 'KeyType': 'HASH'},
            {'AttributeName': 'StartTime', 'KeyType': 'RANGE'}
        ],
        'Projection': {
            'ProjectionType': 'ALL'
        }
    },
    {
        'IndexName': 'GSI5',
        'KeySchema': [
            {'AttributeName': 'Service', 'KeyType': 'HASH'},
            {'AttributeName': 'StartTime', 'KeyType': 'RANGE'}
        ],
        'Projection': {
            'ProjectionType': 'ALL'
        }
    },
    {
        'IndexName': 'GSI6',
        'KeySchema': [
            {'AttributeName': 'EventStatusCode', 'KeyType': 'HASH'},
            {'AttributeName': 'StartTime', 'KeyType': 'RANGE'}
        ],
        'Projection': {
            'ProjectionType': 'ALL'
        }
    },
    {
        'IndexName': 'GSI7',
        'KeySchema': [
            {'AttributeName': 'EventTypeCategory', 'KeyType': 'HASH'},
            {'AttributeName': 'StartTime', 'KeyType': 'RANGE'}
        ],
        'Projection': {
            'ProjectionType': 'ALL'
        }
    }
]

def add_gsi_if_not_exists(table_name, gsi_definition):
    existing_gsi_names = get_existing_gsi_names(table_name)
    if gsi_definition['IndexName'] in existing_gsi_names:
        print(f"GSI {gsi_definition['IndexName']} already exists. Skipping.")
        return

    response = dynamodb_client.update_table(
        TableName=table_name,
        AttributeDefinitions=[
            {'AttributeName': 'awsAccountIds', 'AttributeType': 'S'},
            {'AttributeName': 'EventTypeCode', 'AttributeType': 'S'},
            {'AttributeName': 'Region', 'AttributeType': 'S'},
            {'AttributeName': 'Service', 'AttributeType': 'S'},
            {'AttributeName': 'EventStatusCode', 'AttributeType': 'S'},
            {'AttributeName': 'EventTypeCategory', 'AttributeType': 'S'},
            {'AttributeName': 'StartTime', 'AttributeType': 'S'},
        ],
        GlobalSecondaryIndexUpdates=[
            {
                'Create': gsi_definition
            }
        ]
    )
    print(f"Adding GSI {gsi_definition['IndexName']} to table {table_name}")
    return response

def get_existing_gsi_names(table_name):
    response = dynamodb_client.describe_table(TableName=table_name)
    return [gsi['IndexName'] for gsi in response['Table'].get('GlobalSecondaryIndexes', [])]

def wait_for_gsi_activation(table_name, gsi_name):
    while True:
        response = dynamodb_client.describe_table(TableName=table_name)
        for gsi in response['Table']['GlobalSecondaryIndexes']:
            if gsi['IndexName'] == gsi_name:
                status = gsi['IndexStatus']
                if status == 'ACTIVE':
                    print(f"GSI {gsi_name} is active")
                    return
                else:
                    print(f"GSI {gsi_name} is in status {status}")
        time.sleep(10)

def main():
    for gsi_definition in GSI_DEFINITIONS:
        add_gsi_if_not_exists(HEALTH_EVENTS_TABLE_NAME, gsi_definition)
        wait_for_gsi_activation(HEALTH_EVENTS_TABLE_NAME, gsi_definition['IndexName'])

if __name__ == "__main__":
    main()
