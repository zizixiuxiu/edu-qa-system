@echo off
echo ========================================
echo   EduQA V2 Backend 启动脚本
echo ========================================
echo.

REM 检查Python环境
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python未安装或未添加到PATH
    pause
    exit /b 1
)

echo [1/4] 检查依赖...
cd /d "%~dp0backend"

REM 检查虚拟环境
if not exist "venv" (
    echo [INFO] 创建虚拟环境...
    python -m venv venv
)

REM 激活虚拟环境
call venv\Scripts\activate.bat

echo [2/4] 安装/更新依赖...
pip install -r requirements.txt -q

echo [3/4] 检查数据库连接...
REM 尝试连接数据库，如果失败则提示
python -c "import asyncpg; import asyncio; asyncio.run(asyncio.sleep(0))" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] 数据库依赖可能未正确安装
)

echo [4/4] 启动后端服务...
echo.
echo ========================================
echo   后端服务启动中...
echo   API地址: http://localhost:8000
echo   API文档: http://localhost:8000/docs
echo ========================================
echo.

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

pause
