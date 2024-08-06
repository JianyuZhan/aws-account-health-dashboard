# Cross Account Role 创建指南

## 目的

这个目录的工具作用是： 在**每个**需要收集健康数据（Health Events）的 AWS 组织 (Organization) 的管理账户 (Management Account) 中，创建一个 IAM 角色，使数据收集账户（Data Collection Account，简称 DCA）能够跨账户访问这些管理账户中的健康事件数据。通过这个 IAM 角色，DCA 可以假设管理账户的角色并收集相关数据。

## 文件说明

- `CrossAccountRole.yaml`: CloudFormation 模板，用于在管理账户中创建允许 DCA 假设的 IAM 角色。
- `create_cross_account_role.sh`: 用于创建 CloudFormation 栈的 AWS CLI 脚本。

## 操作步骤

### 1. 准备工作

确保已经安装并配置了 AWS CLI 工具，并且拥有在管理账户中创建 CloudFormation 栈的权限。

### 2. 赋予脚本执行权限

在终端中运行以下命令赋予脚本执行权限：

```bash
chmod +x create_cross_account_role.sh
```

###  3. 执行脚本创建 IAM 角色

运行脚本来创建 CloudFormation 栈。你可以传入 `stack-name` 和 `role-name` 参数，也可以使用默认值。

#### 示例 1：使用默认值

如果不传入 `stack-name` 和 `role-name` 参数，脚本将使用默认值 `DefaultStackName` 和 `DataCollectionCrossAccountRole`。

```bash
./create_cross_account_role.sh <data-collection-account-id>
```

#### 示例 2：指定 `stack-name`

如果需要指定 `stack-name`，可以传入第二个参数：

```bash
./create_cross_account_role.sh <data-collection-account-id> <stack-name>
```

#### 示例 3：指定 `stack-name` 和 `role-name`

如果需要指定 `stack-name` 和 `role-name`，可以传入第二个和第三个参数：

```bash
./create_cross_account_role.sh <data-collection-account-id> <stack-name> <role-name>
```

### 参数说明

- `<data-collection-account-id>`: 数据收集账户的 AWS 账户 ID。
- `<stack-name>` (可选): CloudFormation 栈的名称。如果未指定，将使用默认值 `DefaultStackName`。
- `<role-name>` (可选): 创建的 IAM 角色的名称。如果未指定，将使用默认值 `DataCollectionCrossAccountRole`。