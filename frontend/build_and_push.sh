#!/bin/bash

region="${1:-us-east-1}"  # 默认区域为 'us-east-1'
tag="${2:-latest}"  # 默认标签为 'latest'

# 获取当前 IAM 凭证的账户号
account=$(aws sts get-caller-identity --query Account --output text)
if [ "$?" -ne 0 ]; then
    exit 255
fi

echo $region
echo $account
echo $tag

function build_and_push_image() {
    local account="$1"
    local region="$2"
    local image_name="$3"
    local docker_file="$4"
    local policy_file="$5"

    if [[ $region == *cn* ]]; then
       image_fullname="${account}.dkr.ecr.${region}.amazonaws.com.cn/${image_name}:${tag}"
       ecr_repo_uri="${account}.dkr.ecr.${region}.amazonaws.com.cn"
    else
       image_fullname="${account}.dkr.ecr.${region}.amazonaws.com/${image_name}:${tag}"
       ecr_repo_uri="${account}.dkr.ecr.${region}.amazonaws.com"
    fi

    # 如果 ECR 仓库不存在，则创建它
    aws ecr describe-repositories --repository-names "${image_name}" --region "${region}" > /dev/null 2>&1 || aws ecr create-repository --repository-name "${image_name}" --region "${region}"

    # 从 ECR 获取登录命令并直接执行
    aws ecr get-login-password --region "${region}" | \
	docker login --username AWS --password-stdin "${ecr_repo_uri}"

    # 设置 ECR 仓库的策略
    aws ecr set-repository-policy \
        --repository-name "${image_name}" \
        --policy-text "file://${policy_file}" \
        --region "${region}"

    # 构建 Docker 镜像并推送到 ECR
    docker build --platform linux/amd64 -t "${image_name}" -f ${docker_file} .
    docker tag "${image_name}" "${image_fullname}"
    docker push "${image_fullname}"
}

script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
echo $script_dir

image_name="awshealthdashboardfrontend"
docker_file="$script_dir/Dockerfile"
policy_file="$script_dir/ecr-policy.json"

echo "Image: $mage_name"
build_and_push_image "${account}" "${region}" "${image_name}" "${docker_file}" "${policy_file}"
