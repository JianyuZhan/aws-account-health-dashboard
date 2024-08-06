# 使用 AWS CDK 部署基础设施

本项目使用 AWS Cloud Development Kit (CDK) 来定义和部署基础设施。本指南涵盖了初始设置和基础设施栈的后续更新。

## 前提条件

1. **Node.js 和 npm**：AWS CDK 需要 Node.js。确保你有 Node.js 14.x 或更高版本。你可以从 [Node.js 官方网站](https://nodejs.org/) 下载和安装。
2. **AWS CLI**：确保你已经安装并配置了 AWS CLI。你可以从 [AWS CLI 官方网站](https://aws.amazon.com/cli/) 下载和安装。

## 初始设置

### 步骤1：安装 AWS CDK CLI

打开终端并运行以下命令来安装 AWS CDK CLI：

```sh
npm install -g aws-cdk
```

### 步骤2：配置 AWS CLI

运行以下命令来配置 AWS CLI：

```sh
aws configure
```

按照提示输入你的 AWS Access Key ID、Secret Access Key、默认区域和输出格式。

### 步骤3：创建和激活 Python 虚拟环境（可选但推荐）

导航到 `deploy` 目录并创建一个虚拟环境：

```sh
cd deploy/
python -m venv .venv
source .venv/bin/activate  # 在 Windows 上使用 `.venv\Scripts\activate`
```

### 步骤4：安装项目依赖

运行以下命令来安装所需的 Python 包：

```sh
pip install -r requirements.txt
```

### 步骤5：引导 CDK 环境

运行以下命令来引导 CDK 环境：

```sh
cdk bootstrap
```

### 步骤6：部署 CDK 栈

运行以下命令来部署 CDK 栈：

```sh
cdk deploy
```

## 更新基础设施栈

每当你对基础设施栈进行更改时，请按照以下步骤更新已部署的资源：

### 步骤1：激活虚拟环境（如果尚未激活）

如果你还没有激活虚拟环境，请现在激活：

```sh
cd deploy/
source .venv/bin/activate  # 在 Windows 上使用 `.venv\Scripts\activate`
```

### 步骤2：安装更新的依赖（如果有）

如果你添加了新的依赖，请确保安装它们：

```sh
pip install -r requirements.txt
```

### 步骤3：部署更新后的栈

运行以下命令来部署更新后的栈：

```sh
cdk init app --language python
cdk deploy
```

这将更新你在 CDK 栈中所做的更改的基础设施。

## 其他命令

- **cdk synth**：生成合成的 CloudFormation 模板。
- **cdk diff**：比较指定的栈与已部署的栈（或已保存的模板）。