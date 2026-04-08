@echo off
chcp 65001 >nul
echo.
echo ==========================================
echo  🎓 EduQA 教育问答系统 - 完整启动脚本
echo ==========================================
echo.

:: 设置环境变量
set HF_ENDPOINT=https://hf-mirror.com
set TOKENIZERS_PARALLELISM=false
set SENTENCE_TRANSFORMERS_HOME=%USERPROFILE%\.cache\torch\sentence_transformers

:: 启动后端（在新窗口）
echo 🚀 [1/2] 正在启动后端服务...
echo    地址: http://localhost:8000
echo    API文档: http://localhost:8000/docs
echo.
start "后端服务" cmd /k "cd /d %~dp0backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

:: 等待后端启动
timeout /t 5 /nobreak >nul

:: 启动前端（在新窗口）
echo 🚀 [2/2] 正在启动前端服务...
echo    地址: http://localhost:5173
echo.
start "前端服务" cmd /k "cd /d %~dp0frontend && npm run dev"

echo ==========================================
echo ✅ 启动完成！
echo.
echo 📍 访问地址:
echo    前端: http://localhost:5173
echo    后端: http://localhost:8000
echo    API文档: http://localhost:8000/docs
echo.
echo ⚠️  关闭方式:
echo    直接关闭两个命令行窗口
echo ==========================================
echo.
pause
