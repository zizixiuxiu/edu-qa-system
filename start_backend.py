#!/usr/bin/env python3
"""启动后端服务"""
import sys
import os

# 设置环境变量
os.environ.setdefault("GAOKAO_BENCH_PATH", "/Users/zizixiuixu/Downloads/GAOKAO-Bench-main")

# 添加backend到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 启动 EduQA 后端服务...")
    print(f"📁 GAOKAO_BENCH_PATH: {os.environ.get('GAOKAO_BENCH_PATH')}")
    print("🔗 访问: http://localhost:8000")
    print("📖 API文档: http://localhost:8000/docs")
    print("-" * 50)
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["backend/app"]
    )
