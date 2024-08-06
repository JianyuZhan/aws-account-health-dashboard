# 健康事件管理平台

这是一个跨帐号管理其它 AWS 组织帐号健康事件的管理平台，它提供了相关的 API 接口以及简洁的 UI 实现。通过本项目，可以轻松管理多个组织帐号下的所有授权帐号的 AWS 健康事件，并提供一个整合的管理界面对所有事件进行可视化及操作。

## 部署指南

### 前置要求

每个组织（Organization）的管理帐号（Management Account）都应该先获得授权，以便查看和管理该组织下所有帐号的健康事件。同时，需要有一个部署本项目的帐号，这个帐号也将作为收集所有组织帐号健康事件的数据收集帐号。

### 组织帐号端

需要部署本项目的 AWS 帐号记为：`AWS_DATA_COLLECTION_ACCOUNT`。

1. 在**每个**组织的管理帐号中，运行 `deploy/management_accounts/create_cross_role.sh` 脚本。
   - 该脚本将创建允许 `AWS_DATA_COLLECTION_ACCOUNT` 拉取相关组织及其成员健康事件的 IAM 角色及权限。
   - 请参考 `deploy/management_accounts/README.md` 了解详细用法。
   - 记下每个管理帐号及其对应创建的 IAM 角色信息。

### 数据收集端

`deploy/data_collection/cdk_infra/infra_stack.py` 包含了整个基础设施的 CDK 定义，它会搭建相关健康事件收集和帐号管理的 API 接口、健康事件存储及自动化拉取，以及 UI 前端的逻辑。请按以下步骤操作来搭建基础设施：

1. **安装 AWS CDK**：
   - 请确保已经安装了 AWS CDK。可以使用以下命令安装：
     ```bash
     npm install -g aws-cdk
     ```

2. **安装依赖**：
   - 进入 `deploy/data_collection` 目录，安装所需的 Python 依赖：
     ```bash
     pip install -r requirements.txt
     ```

3. **配置 AWS 凭证**：
   - 确保已配置好 AWS 凭证，并且使用的是 `AWS_DATA_COLLECTION_ACCOUNT` 的凭证。

4. **部署基础设施**：
   - 在 `deploy/data_collection/cdk_infra` 目录下运行以下命令来部署 CDK 堆栈：
     ```bash
     cdk deploy
     ```

5. **记录 API 端点**：
   - 部署完成后，CDK 的输出将包含一个类似于 `https://su8suqixml.execute-api.us-east-1.amazonaws.com/prod/` 的值，记为 `AwsHealthDashboardApiEndpoint`。将其记录下来，记为 `API_ENDPOINT`。

## API 使用指南

部署完成后，可以选择使用 API 进行操作，也可以选择使用 UI 操作。如果选择 UI 操作，请跳过本节，直接查看下一节。

### 注册组织帐号

1. 发送一个 POST 请求到 `$API_ENDPOINT/register_accounts` 注册所有组织帐号。请求体包含要注册的帐号 ID、跨账户角色名称和允许用户的信息。请求示例如下：

   ```bash
   curl -X POST $API_ENDPOINT/register_accounts  \
        -H "Content-Type: application/json" \
        -d '{
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
        }'
   ```

    - `123456789012` 和 `098765432109`：这是需要注册的 AWS 帐号 ID，每个 ID 应为 12 位数字。
    - `cross_account_role`：跨账户角色的名称，用于访问其他组织的健康事件数据。
    - `allowed_users`：允许访问该帐号的用户列表，以键值对形式表示，键为用户的电子邮件地址，值为用户的姓名。这个字段可以不填，之后有需要增加再用下文讲的 /update_account 接口更新。

#### 示例解释

- **注册帐号 123456789012**：
  ```json
  "123456789012": {
      "cross_account_role": "RoleName",
      "allowed_users": {
          "email1@example.com": "John Doe",
          "email2@example.com": "Jane Doe"
      }
  }
  ```
  注册 AWS 帐号 `123456789012`，使用角色 `RoleName` 进行跨账户访问，并允许 `email1@example.com` 和 `email2@example.com` 这两个用户访问该帐号的数据，分别对应的用户名为 `John Doe` 和 `Jane Doe`。

- **注册帐号 098765432109**：
  ```json
  "098765432109": {
      "cross_account_role": "AnotherRoleName",
      "allowed_users": {
          "email1@example.com": "John Doe",
          "email3@example.com": "Alice",
          "email4@example.com": "Bob"
      }
  }
  ```
  注册 AWS 帐号 `098765432109`，使用角色 `AnotherRoleName` 进行跨账户访问，并允许 `email1@example.com`、`email3@example.com` 和 `email4@example.com` 这三个用户访问该帐号的数据，分别对应的用户名为 `John Doe`、`Alice` 和 `Bob`。

### 拉取健康事件

1. 完成注册后，在本项目部署区域的当地时间每天凌晨 2 点将自动触发拉取所有组织帐号关联的所有健康事件的操作。
2. 如需立即拉取，可以发送一个 POST 请求到 `$API_ENDPOINT/fetch_health_events`。该操作将拉取所有组织帐号相关的健康事件并存储到 DynamoDB 中，以备后续查询（默认拉取过去 90 天的事件）。请求示例如下：

   ```bash
   curl -X POST $API_ENDPOINT/fetch_health_events  \
        -H "Content-Type: application/json" \
        -d '{"account_ids": ["123456789012", "098765432109"]}'
   ```
    - "account_ids"列表是前面刚注册的帐号列表。也可以不传，那这会触发全量帐号的拉取操作(不只是刚注册的帐号)

### （可选）更新帐号信息

在完成健康事件的拉取之后，你还可以选择更新帐号的用户信息，这个操作主要用于确保只有授权用户可以访问帐号相关数据。以下是更新帐号的 API 描述和示例：

1. 发送一个 PUT 请求到 `$API_ENDPOINT/update_account` 更新帐号的用户信息。请求体包含 `account_id` 和 `params` 字段，`params` 字段可以包含三个子字段：`add`、`delete` 和 `update`，用于添加、删除和更新用户信息。请求示例如下：

    ```bash
    curl -X PUT $API_ENDPOINT/update_account  \
        -H "Content-Type: application/json" \
        -d '{
            "account_id": "123456789012",
            "params": {
                "add": {
                    "email1@example.com": "John Doe"
                },
                "delete": {
                    "email2@example.com": null
                },
                "update": {
                    "email3@example.com": "Jane Doe"
                }
            }
        }'
    ```

    - `account_id`：要更新的 AWS 帐号 ID。
    - `params`：
      - `add`：需要添加的用户，格式为 `{"用户邮箱": "用户名"}`。
      - `delete`：需要删除的用户，格式为 `{"用户邮箱": null}`。
      - `update`：需要更新的用户，格式为 `{"用户邮箱": "新用户名"}`。

#### 示例解释

- **添加用户**：
  ```json
  "add": {
      "email1@example.com": "John Doe"
  }
  ```
  将用户 `email1@example.com` 添加到允许访问此帐号的用户列表中，并设置用户名为 `John Doe`。

- **删除用户**：
  ```json
  "delete": {
      "email2@example.com": null
  }
  ```
  将用户 `email2@example.com` 从允许访问此帐号的用户列表中删除。

- **更新用户**：
  ```json
  "update": {
      "email3@example.com": "Jane Doe"
  }
  ```
  更新用户 `email3@example.com` 的用户名为 `Jane Doe`。

通过上述 API，你可以方便地管理和更新能够查看 AWS 帐号健康事件的用户信息，从而确保只有授权用户可以访问相关数据。

### （可选）解除注册帐号

如果某个帐号停用，你还可以选择解除某些帐号的注册。以下是解除注册帐号的 API 描述和示例：

1. 发送一个 DELETE 请求到 `$API_ENDPOINT/deregister_accounts` 来批量解除注册多个帐号。请求体包含一个 `account_ids` 字段，字段值为需要解除注册的帐号 ID 列表。请求示例如下：

    ```bash
    curl -X DELETE $API_ENDPOINT/deregister_accounts \
        -H "Content-Type: application/json" \
        -d '{
            "account_ids": ["123456789012", "098765432109"]
        }'
    ```

    - `account_ids`：需要解除注册的 AWS 帐号 ID 列表。

通过上述 API，你可以方便地批

量解除多个 AWS 帐号的注册，确保不再处理这些帐号的健康事件数据。

## 前端 UI 使用

TODO

请参考上述 API 操作指南，通过 UI 界面进行相应的操作。