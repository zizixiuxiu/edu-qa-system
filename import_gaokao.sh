#!/bin/bash
# GAOKAO-Bench 数据导入脚本

echo "导入 GAOKAO-Bench 数据集到系统..."
echo "路径: /Users/zizixiuixu/Downloads/GAOKAO-Bench-main"
echo ""

# 设置环境变量
export GAOKAO_BENCH_PATH="/Users/zizixiuixu/Downloads/GAOKAO-Bench-main"

cd backend

# 导入客观题（选择题）
echo "📥 导入客观题数据..."
python scripts/import_gaokao_full.py

echo ""
echo "✅ 导入完成!"
echo "启动后端服务: python start_backend.py"
