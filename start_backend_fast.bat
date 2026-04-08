@echo off
chcp 65001 >nul

:: 设置 HuggingFace 环境变量
set HF_ENDPOINT=https://hf-mirror.com
set TOKENIZERS_PARALLELISM=false
set SENTENCE_TRANSFORMERS_HOME=%USERPROFILE%\.cache\torch\sentence_transformers

echo 🚀 启动教育系统（快速模式）...
echo.

:: 启动后端服务（模型会在首次使用时自动加载）...
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
