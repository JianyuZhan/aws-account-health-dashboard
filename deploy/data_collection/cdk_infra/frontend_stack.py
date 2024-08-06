from aws_cdk import (
    Stack,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_ecr as ecr,
    CfnOutput
)
from constructs import Construct
import random
import string

APP_NAME = 'AwsHealthDashboardFrontend'


class FrontendApp(Stack):

    def __init__(self, scope: Construct, id: str, api_endpoint: str, force_update: bool = False, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        
        # 如果 force_update 为 True，则生成一个长度为 8 的随机字符串
        # 用于强制拉取新的Image
        random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=8)) if force_update else None

        # 获取已有的 ECR 仓库
        repository = ecr.Repository.from_repository_name(
            self, f'{APP_NAME}Repository', repository_name=f'{APP_NAME.lower()}'
        )

        # 创建 ECS 集群和 Fargate 服务
        cluster = ecs.Cluster(self, f"{APP_NAME}Cluster")
        fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(self, f"{APP_NAME}FargateService",
            cluster=cluster,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_ecr_repository(repository, "latest"),
                environment={
                    "API_ENDPOINT": api_endpoint,
                    **({"FORCE_UPDATE": random_string} if random_string else {}) # 用于强制拉取新的Image
                }
            ),
            desired_count=1,
            public_load_balancer=True
        )

        # 输出服务的 URL
        CfnOutput(self, "FrontendURL", value=fargate_service.load_balancer.load_balancer_dns_name)
