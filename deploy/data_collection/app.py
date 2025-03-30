import aws_cdk as cdk
from cdk_infra.backend_stack import AwsHealthDashboard
from cdk_infra.frontend_stack import FrontendApp

import argparse
import os

# 解析命令行参数
parser = argparse.ArgumentParser(description="CDK deploy options")
parser.add_argument("--pull-ui-image", action="store_true", help="Force ECS to pull the latest Docker image")
parser.add_argument("--region", type=str, help="AWS region to deploy to")
args = parser.parse_args()

# 通过环境变量控制是否部署前端
DEPLOY_FRONTEND = os.getenv("DEPLOY_FRONTEND", "True") == "True"

# 设置环境参数，包括区域
env = cdk.Environment(
    account=os.environ.get('CDK_DEFAULT_ACCOUNT'),
    region=args.region if args.region else os.environ.get('CDK_DEFAULT_REGION')
)

app = cdk.App()

# 创建后端栈，传入环境参数
backend_stack = AwsHealthDashboard(app, "AwsHealthDashboardStack", env=env)

if DEPLOY_FRONTEND:
    # 创建前端栈，传递 API Gateway 的 URL 和可选的构建参数
    frontend_stack = FrontendApp(
        app, 
        "FrontendStack", 
        api_endpoint=backend_stack.api.url,
        force_update=args.pull_ui_image,
        env=env
    )

app.synth()
