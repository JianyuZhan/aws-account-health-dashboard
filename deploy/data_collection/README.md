# 使用 AWS CDK 部署基础设施

这个目录里，使用 AWS Cloud Development Kit (CDK) 来定义和部署整个项目的aws基础设施，以实现所有的API及UI部署。

## 前提条件

1. **Node.js 和 npm**：安装了 Node.js 14.x 或更高版本。 [下载 Node.js](https://nodejs.org/)
2. **AWS CLI**：安装并配置AWS CLI： [下载 AWS CLI](https://aws.amazon.com/cli/)

## 初始设置

### 安装 AWS CDK CLI

在终端运行以下命令：

```sh
npm install -g aws-cdk
```

### 配置 AWS CLI

运行以下命令并按照提示输入信息：

```sh
aws configure
```

### 创建和激活 Python 虚拟环境

在 `deploy` 目录下：

```sh
cd deploy/data_collection
python -m venv .venv
source .venv/bin/activate  # Windows 使用 `.venv\Scripts\activate`
```

### 安装项目依赖

运行以下命令：

```sh
pip install -r requirements.txt
```

### 引导 CDK 环境

如果是第一次，运行以下命令：

```sh
cdk bootstrap
```

### 部署 CDK 栈

然后运行以下命令（之后更新了相关cdk逻辑后，也需要运行）：

```sh
cdk deploy
```