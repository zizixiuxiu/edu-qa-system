#!/bin/bash
# GAOKAO-Bench 数据集下载脚本

set -e

echo "=================================="
echo " 下载 GAOKAO-Bench 数据集"
echo "=================================="

# 设置目录
DATA_DIR="./backend/data"
GAOKAO_DIR="$DATA_DIR/GAOKAO-Bench-Full"

echo ""
echo "📁 目标目录: $GAOKAO_DIR"
mkdir -p "$GAOKAO_DIR"

# 方式1: 直接克隆GitHub仓库
echo ""
echo "📥 方式1: 从 GitHub 克隆..."
if [ -d "/tmp/GAOKAO-Bench" ]; then
    rm -rf /tmp/GAOKAO-Bench
fi

git clone --depth 1 https://github.com/OpenBMB/GAOKAO-Bench.git /tmp/GAOKAO-Bench 2>/dev/null || {
    echo "   GitHub克隆失败，尝试使用代理..."
    git clone --depth 1 https://ghproxy.com/https://github.com/OpenBMB/GAOKAO-Bench.git /tmp/GAOKAO-Bench 2>/dev/null || {
        echo "   代理也失败，尝试其他方式..."
    }
}

# 如果克隆成功，复制数据
if [ -d "/tmp/GAOKAO-Bench/data" ]; then
    echo "✅ 克隆成功!"
    
    # 复制原始数据
    cp -r /tmp/GAOKAO-Bench/data "$GAOKAO_DIR/raw"
    
    # 统计题目数量
    echo ""
    echo "📊 数据集统计:"
    total=0
    for file in "$GAOKAO_DIR"/raw/*.json; do
        if [ -f "$file" ]; then
            count=$(cat "$file" | grep -o '"year"' | wc -l)
            subject=$(basename "$file" .json)
            echo "   $subject: $count 题"
            total=$((total + count))
        fi
    done
    echo "   -------------------"
    echo "   总计: $total 题"
    
    # 清理临时文件
    rm -rf /tmp/GAOKAO-Bench
    
    echo ""
    echo "✅ 下载完成!"
    echo "数据保存在: $GAOKAO_DIR/raw/"
    
else
    echo "❌ GitHub下载失败，尝试使用现有数据..."
    
    # 检查是否已有示例数据
    if [ -d "$DATA_DIR/GAOKAO-Bench" ]; then
        echo "✅ 使用已有示例数据: $DATA_DIR/GAOKAO-Bench"
        echo "   (示例数据每个学科只有5道题，用于测试)"
    else
        echo "❌ 没有找到数据，请手动下载:"
        echo "   https://github.com/OpenBMB/GAOKAO-Bench"
    fi
fi

echo ""
echo "=================================="
echo "使用说明:"
echo "  1. 导入数据库: python backend/scripts/import_gaokao.py"
echo "  2. 运行评测: python run_benchmark.py"
echo "=================================="
