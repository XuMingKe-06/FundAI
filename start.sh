#!/bin/bash

echo "========================================"
echo "  FundAI - 多智能体场外基金分析决策系统"
echo "========================================"
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到 Python3，请先安装 Python 3.12+"
    exit 1
fi

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "[错误] 未找到 Node.js，请先安装 Node.js 22+"
    exit 1
fi

# 检查是否首次运行
if [ ! -d ".venv" ]; then
    echo "[信息] 首次运行，正在安装后端依赖..."
    python3 -m venv .venv
    if [ -f ".venv/Scripts/activate" ]; then
        source .venv/Scripts/activate
    else
        source .venv/bin/activate
    fi
    pip install -r requirements.txt
else
    if [ -f ".venv/Scripts/activate" ]; then
        source .venv/Scripts/activate
    else
        source .venv/bin/activate
    fi
fi

if [ ! -d "frontend/node_modules" ]; then
    echo "[信息] 首次运行，正在安装前端依赖..."
    cd frontend && npm install && cd ..
fi

# 创建数据目录
mkdir -p data/cache data/chroma

echo ""
echo "[信息] 正在启动后端服务..."
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo "[信息] 正在启动前端服务..."
cd frontend && npm run dev &
FRONTEND_PID=$!

echo ""
echo "========================================"
echo "  FundAI 已启动！"
echo "  后端地址: http://localhost:8000"
echo "  前端地址: http://localhost:3000"
echo "  API文档:  http://localhost:8000/docs"
echo "========================================"
echo ""
echo "按 Ctrl+C 停止所有服务..."

# 等待任意子进程结束
wait
