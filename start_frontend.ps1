# 启动前端服务
$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Green
Write-Host "  🚀 启动 EduQA 前端服务" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""

# 进入前端目录
Set-Location -Path "$PSScriptRoot\frontend"

# 检查Node.js
$nodeVersion = node --version 2>&1
Write-Host "✅ Node.js: $nodeVersion" -ForegroundColor Green

# 检查依赖
if (-not (Test-Path "node_modules")) {
    Write-Host "⚠️  未找到 node_modules，正在安装依赖..." -ForegroundColor Yellow
    npm install
    Write-Host "✅ 依赖安装完成" -ForegroundColor Green
}

# 启动服务
Write-Host "🚀 启动 Vite 开发服务器..." -ForegroundColor Yellow
Write-Host "   地址: http://localhost:5173" -ForegroundColor Gray
Write-Host ""

npm run dev
