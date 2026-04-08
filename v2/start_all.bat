@echo off
echo ========================================
echo   EduQA V2 一键启动脚本
echo ========================================
echo.

echo 启动后端服务...
start "EduQA Backend" cmd /c "cd /d "%~dp0backend" && if exist venv\Scripts\activate.bat (call venv\Scripts\activate.bat) && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload && pause"

timeout /t 3 /nobreak >nul

echo 启动前端服务...
start "EduQA Frontend" cmd /c "cd /d "%~dp0frontend" && npm run dev && pause"

echo.
echo ========================================
echo   服务启动完成！
echo   后端地址: http://localhost:8000
echo   前端地址: http://localhost:3000
echo   API文档: http://localhost:8000/docs
echo ========================================
echo.

echo 按任意键关闭此窗口（服务将继续运行）...
pause >nul
