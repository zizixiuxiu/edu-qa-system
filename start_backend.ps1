# 启动后端服务
$ErrorActionPreference = "Stop"

# 设置环境变量
$env:HF_ENDPOINT = "https://hf-mirror.com"
$env:TOKENIZERS_PARALLELISM = "false"
$env:SENTENCE_TRANSFORMERS_HOME = "$env:USERPROFILE\.cache\torch\sentence_transformers"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  🚀 启动 EduQA 后端服务" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# 进入后端目录
Set-Location -Path "$PSScriptRoot\backend"

# 检查Python
$pythonVersion = python --version 2>&1
Write-Host "✅ Python: $pythonVersion" -ForegroundColor Green

# 启动服务
Write-Host "🚀 启动 FastAPI 服务..." -ForegroundColor Yellow
Write-Host "   地址: http://localhost:8000" -ForegroundColor Gray
Write-Host "   文档: http://localhost:8000/docs" -ForegroundColor Gray
Write-Host ""

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
