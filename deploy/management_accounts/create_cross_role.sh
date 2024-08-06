#!/bin/bash

# 检查输入参数
if [ "$#" -lt 1 ] || [ "$#" -gt 3 ]; then
  echo "Usage: $0 <data-collection-account-id> [stack-name] [role-name]"
  exit 1
fi

DATA_COLLECTION_ACCOUNT_ID=$1
STACK_NAME=${2:-DefaultStackName}
ROLE_NAME=${3:-DataCollectionCrossAccountRole}

# 获取当前脚本的目录
SCRIPT_DIR=$(dirname "$0")

# 创建CloudFormation栈
aws cloudformation create-stack --stack-name $STACK_NAME \
  --template-body file://$SCRIPT_DIR/CrossAccountRole.yaml \
  --parameters ParameterKey=DataCollectionAccountID,ParameterValue=$DATA_COLLECTION_ACCOUNT_ID ParameterKey=RoleName,ParameterValue=$ROLE_NAME \
  --capabilities CAPABILITY_NAMED_IAM

# 等待栈创建完成
aws cloudformation wait stack-create-complete --stack-name $STACK_NAME

if [ $? -eq 0 ]; then
  echo "Stack $STACK_NAME created successfully."
else
  echo "Failed to create stack $STACK_NAME."
fi
