@echo off
echo ========================================
echo   EduQA V2 Frontend 启动脚本
echo ========================================
echo.

REM 检查Node.js环境
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js未安装或未添加到PATH
    pause
    exit /b 1
)

cd /d "%~dp0frontend"

echo [1/3] 检查依赖...
if not exist "node_modules" (
    echo [INFO] 首次运行，安装依赖...
    call npm install
    if errorlevel 1 (
        echo [ERROR] 依赖安装失败
        pause
        exit /b 1
    )
)

echo [2/3] 检查环境配置...
if not exist ".env" (
    echo [INFO] 创建默认环境配置...
    echo VITE_API_URL=http://localhost:8000/api/v1 > .env
)

echo [3/3] 启动前端开发服务器...
echo.
echo ========================================
echo   前端服务启动中...
echo   访问地址: http://localhost:3000
echo ========================================
echo.

call npm run dev

pause
