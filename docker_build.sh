#!/bin/bash
set -euo pipefail

# =============================
# docker_build.sh
#
# 用法:
#   ./docker_build.sh <version>
# 例如:
#   ./docker_build.sh v1.0.0
#
# 说明:
# - 构建并打标签镜像: rustdesk_api:<version> 与 rustdesk_api:latest
# - 兼容 macOS、Linux、Windows(WSL2) 终端环境
# =============================

IMAGE_NAME="rustdesk_api"

###
# 构建并打标签镜像
#
# :param str version: 要构建并标记的镜像版本号（例如 v1.0.0 或 1.0.0）
# :raises RuntimeError: 当构建失败时抛出
###
build_image() {
  local version="$1"
  echo "开始构建 Docker 镜像: ${IMAGE_NAME}:${version}"
  docker build -t "${IMAGE_NAME}:${version}" -f Dockerfile .

  echo "为镜像添加 latest 标签: ${IMAGE_NAME}:latest"
  docker tag "${IMAGE_NAME}:${version}" "${IMAGE_NAME}:latest"

  echo "构建完成 -> ${IMAGE_NAME}:${version} 与 ${IMAGE_NAME}:latest"
}

###
# 打印脚本用法
#
# :returns: 无
###
print_usage() {
  echo "用法: $0 <version>"
  echo "示例: $0 v1.0.0"
}

###
# 脚本入口
#
# :returns: 以状态码指示成功或失败
###
main() {
  if [ $# -ne 1 ]; then
    print_usage
    exit 1
  fi

  local version="$1"

  if [ -z "$version" ]; then
    echo "错误: 版本号不能为空"
    print_usage
    exit 1
  fi

  build_image "$version"
}

main "$@"


