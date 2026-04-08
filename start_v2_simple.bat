@echo off
chcp 65001 >nul
echo.
echo ==========================================
echo  🎓 EduQA V2 启动脚本
echo ==========================================
echo.

:: 检查LM Studio
echo 🔍 检查 LM Studio...
curl -s http://localhost:1234/v1/models >nul 2>&1
if errorlevel 1 (
    echo ❌ LM Studio 未启动!
    echo    请按以下步骤操作:
    echo    1. 打开 LM Studio
    echo    2. 加载 qwen3-vl-4b 模型
    echo    3. 点击 Start Server (端口1234)
    echo.
    pause
    exit /b 1
)
echo ✅ LM Studio 运行正常
echo.

:: 启动后端
echo 🚀 启动后端服务 (端口8000)...
start "EduQA Backend" cmd /k "cd /d "%~dp0v2\backend" && echo 正在启动后端... && python -m app.main"

:: 等待后端启动
timeout /t 5 /nobreak >nul

:: 启动前端
echo 🎨 启动前端服务 (端口3000)...
start "EduQA Frontend" cmd /k "cd /d "%~dp0v2\frontend" && echo 正在启动前端... && npm run dev"

echo.
echo ==========================================
echo ✅ 启动命令已执行!
echo ==========================================
echo.
echo 📚 API文档:     http://localhost:8000/docs
echo 🌐 前端界面:     http://localhost:3000
echo 🔌 LM Studio:   http://localhost:1234
echo.
echo 注意: 请等待3-5秒让服务完全启动
echo.
pause
