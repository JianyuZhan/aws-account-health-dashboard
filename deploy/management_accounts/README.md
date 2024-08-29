# Cross Account Role 创建指南

## 目的

这个工具的作用是：在**每个**需要收集健康数据（Health Events）的 AWS 组织 (Organization) 的管理账户 (Management Account) 中，创建一个 IAM 角色，使数据收集账户（Data Collection Account，简称 DCA）能够跨账户访问这些管理账户中的健康事件数据。通过这个 IAM 角色，DCA 可以假设管理账户的角色并收集相关数据。

## 文件说明

- `CrossAccountRole.yaml`: CloudFormation 模板，用于在管理账户中创建允许 DCA 假设的 IAM 角色。
- `create_cross_account_role.py`: 用于创建 CloudFormation 栈的 Python 脚本。

## 操作步骤

### 1. 准备工作

确保已经安装并配置了 AWS CLI 工具，并且拥有在管理账户中创建 CloudFormation 栈的权限。此外，确保你的 Python 环境中已安装了 `boto3` 库：

```bash
pip install boto3
```

### 2. 环境变量设置

如果需要指定 AWS 区域，脚本会从环境变量 `AWS_HEALTH_DASHBOARD_REGION` 或 `AWS_REGION` 中读取。如果这两个环境变量都未设置，脚本将无法运行。你可以使用以下命令设置环境变量：

```bash
export AWS_HEALTH_DASHBOARD_REGION=us-east-1  # 示例区域
```

确保在运行脚本前已正确设置这些环境变量，以保证脚本能在正确的区域执行。

### 3. 执行脚本创建 IAM 角色

运行 Python 脚本来创建 CloudFormation 栈。你可以传入 `stack-name` 和 `role-name` 参数，也可以使用默认值。

#### 示例 1：使用默认值

如果不传入 `stack-name` 和 `role-name` 参数，脚本将使用默认值 `AwsHealthCrossAccountRoleStack` 和 `DataCollectionCrossAccountRole`。

```bash
python create_cross_account_role.py <data-collection-account-id>
```

#### 示例 2：指定 `stack-name`

如果需要指定 `stack-name`，可以传入 `--stack-name` 参数：

```bash
python create_cross_account_role.py <data-collection-account-id> --stack-name <stack-name>
```

#### 示例 3：指定 `stack-name` 和 `role-name`

如果需要指定 `stack-name` 和 `role-name`，可以传入 `--stack-name` 和 `--role-name` 参数：

```bash
python create_cross_account_role.py <data-collection-account-id> --stack-name <stack-name> --role-name <role-name>
```

### 参数说明

- `<data-collection-account-id>`: 数据收集账户的 AWS 账户 ID。
- `--stack-name` (可选): CloudFormation 栈的名称。如果未指定，将使用默认值 `AwsHealthCrossAccountRoleStack`。
- `--role-name` (可选): 创建的 IAM 角色的名称。如果未指定，将使用默认值 `DataCollectionCrossAccountRole`。