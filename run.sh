#!/usr/bin/env bash
# 一键启动脚本
set -e
cd "$(dirname "$0")/backend"

if [ ! -d ".venv" ]; then
  echo "==> 创建虚拟环境"
  python3 -m venv .venv
fi
source .venv/bin/activate

echo "==> 安装依赖"
pip install -q -r requirements.txt

if [ ! -f ".env" ]; then
  echo "==> 未发现 .env，已从 .env.example 复制（请填入 LLM_API_KEY）"
  cp .env.example .env
fi

echo "==> 启动服务  http://127.0.0.1:8000"
uvicorn app.main:app --reload --port 8000
