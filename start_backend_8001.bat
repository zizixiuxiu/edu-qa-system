@echo off
chcp 65001 >nul

:: 设置 HuggingFace 环境变量
set HF_ENDPOINT=https://hf-mirror.com
set TOKENIZERS_PARALLELISM=false
set SENTENCE_TRANSFORMERS_HOME=%USERPROFILE%\.cache\torch\sentence_transformers

echo 🚀 启动教育系统（端口8001）...
echo.

cd backend
echo 🔄 启动后端服务 on port 8001...
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
