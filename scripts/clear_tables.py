import boto3

def clear_table(table_name):
    """
    清空指定的DynamoDB表。

    参数:
    table_name (str): 要清空的表名
    """
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table(table_name)
    scan = table.scan()

    key_names = [key['AttributeName'] for key in table.key_schema]

    with table.batch_writer() as batch:
        for each in scan['Items']:
            key_dict = {key: each[key] for key in key_names}
            batch.delete_item(Key=key_dict)

    print(f"Table {table_name} has been cleared.")


def clear_all_tables():
    """
    清空所有给定的DynamoDB表。
    """
    table_names = [
        'AwsHealthDashboardAffectedAccounts',
        'AwsHealthDashboardAffectedEntities',
        'AwsHealthDashboardEventDetails',
        'AwsHealthDashboardHealthEvents',
        'AwsHealthDashboardManagementAccounts',
        'AwsHealthDashboardUsers'
    ]

    for table_name in table_names:
        clear_table(table_name)


if __name__ == "__main__":
    clear_all_tables()

