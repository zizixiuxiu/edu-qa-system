# EduQA V2 启动命令

**快速启动指南** - 2026-04-07

---

## 🚀 一键启动（推荐）

### Windows (PowerShell)
```powershell
# 1. 启动 LM Studio（手动打开图形界面）
# 2. 加载 qwen3-vl-4b 模型
# 3. 启动本地服务器（端口1234）

# 4. 启动后端（新终端）
cd d:\kimi_code\edu_qa_system\ copy\v2\backend
python -m app.main

# 5. 启动前端（新终端）
cd d:\kimi_code\edu_qa_system\ copy\v2\frontend
npm run dev
```

### 简化批处理脚本

创建 `start_v2.ps1`:
```powershell
# start_v2.ps1
Write-Host "🎓 启动 EduQA V2..." -ForegroundColor Green

# 检查 LM Studio
$lmstudio = Get-Process | Where-Object {$_.ProcessName -like "*LM Studio*"}
if (-not $lmstudio) {
    Write-Host "⚠️ 请先启动 LM Studio 并加载模型!" -ForegroundColor Yellow
    exit 1
}

# 启动后端
Start-Process powershell -ArgumentList "-Command", "cd 'd:\kimi_code\edu_qa_system copy\v2\backend'; python -m app.main"

# 等待后端启动
Start-Sleep -Seconds 3

# 启动前端
Start-Process powershell -ArgumentList "-Command", "cd 'd:\kimi_code\edu_qa_system copy\v2\frontend'; npm run dev"

Write-Host "✅ 启动完成!" -ForegroundColor Green
Write-Host "📚 API文档: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "🌐 前端界面: http://localhost:3000" -ForegroundColor Cyan
```

运行:
```powershell
.\start_v2.ps1
```

---

## 📋 分步启动

### 步骤 1: 启动 LM Studio（必须）

```
1. 打开 LM Studio 应用程序
2. 点击左侧 "AI Chat"
3. 选择模型: qwen3-vl-4b
4. 点击右上角 "Start Server"
5. 确认端口号: 1234
6. 等待状态变为 "Server is running"
```

**验证LM Studio运行**:
```powershell
curl http://localhost:1234/v1/models
```

---

### 步骤 2: 启动后端服务

#### 方式1: 直接启动
```powershell
cd "d:\kimi_code\edu_qa_system copy\v2\backend"
python -m app.main
```

#### 方式2: 使用 uvicorn（开发模式）
```powershell
cd "d:\kimi_code\edu_qa_system copy\v2\backend"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 方式3: 生产模式
```powershell
cd "d:\kimi_code\edu_qa_system copy\v2\backend"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**后端启动成功标志**:
```
🎓 EduQA V2 启动
=================
环境: development
调试: True
版本: 2.0.0

API文档: http://0.0.0.0:8000/docs
```

**验证后端运行**:
```powershell
curl http://localhost:8000/health
# 预期返回: {"status": "healthy", "version": "2.0.0"}
```

---

### 步骤 3: 启动前端服务

```powershell
cd "d:\kimi_code\edu_qa_system copy\v2\frontend"
npm install  # 首次运行需要
npm run dev
```

**前端启动成功标志**:
```
VITE v5.x.x  ready in xxx ms

➜  Local:   http://localhost:3000/
➜  Network: http://192.168.x.x:3000/
```

---

## 🔧 完整启动脚本

### Windows 批处理 (`start_all.bat`)

```batch
@echo off
chcp 65001 >nul
echo 🎓 启动 EduQA V2...

:: 检查端口占用
echo 检查端口...
netstat -ano | findstr :8000 >nul && (
    echo ⚠️ 端口8000被占用，请先关闭占用进程
    exit /b 1
)

:: 启动后端
echo 启动后端服务...
start "EduQA Backend" cmd /k "cd /d "%~dp0backend" && python -m app.main"

:: 等待后端启动
timeout /t 5 /nobreak >nul

:: 启动前端
echo 启动前端服务...
start "EduQA Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo ✅ 启动完成!
echo 📚 API文档: http://localhost:8000/docs
echo 🌐 前端界面: http://localhost:3000
echo.
pause
```

### Python 启动脚本 (`start_v2.py`)

```python
#!/usr/bin/env python3
"""EduQA V2 启动脚本"""

import subprocess
import sys
import time
import os

def check_lmstudio():
    """检查LM Studio是否运行"""
    try:
        import urllib.request
        urllib.request.urlopen("http://localhost:1234/v1/models", timeout=2)
        print("✅ LM Studio 运行正常")
        return True
    except:
        print("❌ LM Studio 未启动或未加载模型")
        print("   请手动启动 LM Studio 并加载 qwen3-vl-4b 模型")
        return False

def start_backend():
    """启动后端"""
    print("🚀 启动后端服务...")
    backend_dir = os.path.join(os.path.dirname(__file__), "v2", "backend")
    
    proc = subprocess.Popen(
        [sys.executable, "-m", "app.main"],
        cwd=backend_dir,
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    return proc

def start_frontend():
    """启动前端"""
    print("🎨 启动前端服务...")
    frontend_dir = os.path.join(os.path.dirname(__file__), "v2", "frontend")
    
    proc = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=frontend_dir,
        shell=True,
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    return proc

def main():
    print("=" * 50)
    print("🎓 EduQA V2 启动脚本")
    print("=" * 50)
    
    # 检查LM Studio
    if not check_lmstudio():
        input("\n按回车键退出...")
        return
    
    # 启动服务
    backend_proc = start_backend()
    time.sleep(5)  # 等待后端启动
    
    frontend_proc = start_frontend()
    
    print("\n" + "=" * 50)
    print("✅ 所有服务已启动!")
    print("=" * 50)
    print("📚 API文档: http://localhost:8000/docs")
    print("🌐 前端界面: http://localhost:3000")
    print("🔌 LM Studio: http://localhost:1234")
    print("=" * 50)
    
    input("\n按回车键停止所有服务...")
    
    # 停止服务
    backend_proc.terminate()
    frontend_proc.terminate()
    print("👋 服务已停止")

if __name__ == "__main__":
    main()
```

运行:
```powershell
python start_v2.py
```

---

## 🐳 Docker 启动（可选）

### docker-compose.yml

```yaml
version: '3.8'

services:
  postgres:
    image: ankane/pgvector:latest
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
      POSTGRES_DB: edu_qa
    ports:
      - "15432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  backend:
    build: ./v2/backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:password@postgres:5432/edu_qa
      - LLM_BASE_URL=http://host.docker.internal:1234/v1
    depends_on:
      - postgres

  frontend:
    build: ./v2/frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend

volumes:
  postgres_data:
```

启动:
```bash
docker-compose up -d
```

---

## 🧪 验证命令

### 验证所有服务

```powershell
# 1. 验证 LM Studio
curl http://localhost:1234/v1/models

# 2. 验证后端健康
curl http://localhost:8000/health

# 3. 验证后端API
curl http://localhost:8000/api/v1/experts/list

# 4. 验证前端
curl http://localhost:3000
```

### 完整验证脚本

```powershell
# check_services.ps1
Write-Host "🔍 检查 EduQA V2 服务状态..." -ForegroundColor Cyan

$services = @(
    @{Name="LM Studio"; Url="http://localhost:1234/v1/models"},
    @{Name="后端服务"; Url="http://localhost:8000/health"},
    @{Name="前端服务"; Url="http://localhost:3000"}
)

foreach ($svc in $services) {
    try {
        $response = Invoke-WebRequest -Uri $svc.Url -TimeoutSec 3 -ErrorAction Stop
        Write-Host "✅ $($svc.Name): 运行正常" -ForegroundColor Green
    } catch {
        Write-Host "❌ $($svc.Name): 未启动" -ForegroundColor Red
    }
}
```

---

## 🛑 停止命令

### 停止后端
```powershell
# 查找Python进程并停止
taskkill /F /IM python.exe
```

### 停止前端
```powershell
# 在运行前端的终端按 Ctrl+C
# 或者查找Node进程
taskkill /F /IM node.exe
```

### 停止所有
```powershell
# 一键停止所有服务
taskkill /F /IM python.exe
taskkill /F /IM node.exe
```

---

## 📞 常见问题

### Q: LM Studio 无法连接
```
检查:
1. LM Studio 是否已打开
2. 模型是否已加载
3. 服务器是否已启动 (端口1234)
4. 防火墙是否拦截
```

### Q: 后端启动失败
```
检查:
1. Python环境: python --version
2. 依赖安装: pip install -r requirements.txt
3. 数据库连接: PostgreSQL是否运行
4. 端口占用: netstat -ano | findstr :8000
```

### Q: 前端启动失败
```
检查:
1. Node.js安装: node --version
2. 依赖安装: npm install
3. 端口占用: netstat -ano | findstr :3000
```

---

## 📝 端口列表

| 服务 | 端口 | 用途 |
|------|------|------|
| LM Studio | 1234 | VLM/LLM推理 |
| 后端API | 8000 | FastAPI服务 |
| 前端界面 | 3000 | Vue3应用 |
| PostgreSQL | 15432 | 数据库 |

---

## ✅ 启动检查清单

- [ ] LM Studio 已启动
- [ ] qwen3-vl-4b 模型已加载
- [ ] 本地服务器运行在端口1234
- [ ] PostgreSQL 数据库已启动
- [ ] 后端服务启动成功 (端口8000)
- [ ] 前端服务启动成功 (端口3000)
- [ ] 可以访问 http://localhost:3000

---

**快速启动命令**:
```powershell
# 终端1: 确保LM Studio运行
# 终端2: 
cd "d:\kimi_code\edu_qa_system copy\v2\backend"; python -m app.main
# 终端3:
cd "d:\kimi_code\edu_qa_system copy\v2\frontend"; npm run dev
```
