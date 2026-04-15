#!/bin/bash
# EduQA 系统快速启动脚本

echo "🚀 启动 EduQA 系统..."

# 检查并启动数据库
if ! pg_isready > /dev/null 2>&1; then
    echo "📦 启动 PostgreSQL..."
    brew services start postgresql@14
    sleep 3
fi

# 设置环境变量
export GAOKAO_BENCH_PATH=/Users/zizixiuixu/Downloads/GAOKAO-Bench-main
export DATABASE_URL="postgresql://postgres:password@localhost:15432/edu_qa"

# 启动后端
echo "🔧 启动后端..."
cd "$(dirname "$0")/backend"
source .venv/bin/activate
python start_backend.py &
BACKEND_PID=$!

# 等待后端
sleep 5
echo "✅ 后端已启动: http://localhost:8000"

# 启动前端
echo "🎨 启动前端..."
cd "../frontend"
npm run dev

# 清理
trap "kill $BACKEND_PID 2>/dev/null; exit" INT
