# 🚀 系统启动命令行

## 📋 前置要求

- PostgreSQL 已安装并启动
- Redis 已启动（可选，用于缓存）
- Node.js 18+ 
- Python 3.9+

---

## 方式一：单终端启动（推荐开发测试）

### 步骤1：启动数据库（如未启动）

```bash
# macOS (使用 Homebrew)
brew services start postgresql@14

# 或手动启动
pg_ctl -D /usr/local/var/postgresql@14 start

# 检查数据库状态
pg_isready
```

### 步骤2：启动后端服务

```bash
cd /Users/zizixiuixu/Code/LLM_Project/Edu-System/edu-qa-system

# 激活虚拟环境（如有）
source backend/.venv/bin/activate

# 设置环境变量并启动
export GAOKAO_BENCH_PATH=/Users/zizixiuixu/Downloads/GAOKAO-Bench-main
export DATABASE_URL="postgresql://postgres:password@localhost:15432/edu_qa"

cd backend

# 方式A: 直接启动
python start_backend.py

# 方式B: 使用 uvicorn（如需更多控制）
# uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

后端启动后访问：
- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

### 步骤3：启动前端（新开终端）

```bash
cd /Users/zizixiuixu/Code/LLM_Project/Edu-System/edu-qa-system/frontend

# 安装依赖（首次）
npm install

# 启动开发服务器
npm run dev
```

前端访问：http://localhost:3000

---

## 方式二：多终端启动（推荐日常开发）

### 终端 1：数据库
```bash
brew services start postgresql@14
```

### 终端 2：后端
```bash
cd /Users/zizixiuixu/Code/LLM_Project/Edu-System/edu-qa-system
source backend/.venv/bin/activate
export GAOKAO_BENCH_PATH=/Users/zizixiuixu/Downloads/GAOKAO-Bench-main
cd backend
python start_backend.py
```

### 终端 3：前端
```bash
cd /Users/zizixiuixu/Code/LLM_Project/Edu-System/edu-qa-system/frontend
npm run dev
```

---

## 方式三：使用一键启动脚本

### 创建启动脚本

```bash
# 保存为 start_all.sh
cat > start_all.sh << 'EOF'
#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}  EduQA 系统启动脚本${NC}"
echo -e "${GREEN}================================${NC}"

# 检查数据库
echo -e "\n${YELLOW}[1/3] 检查数据库...${NC}"
if pg_isready > /dev/null 2>&1; then
    echo "✅ PostgreSQL 已启动"
else
    echo "⚠️  正在启动 PostgreSQL..."
    brew services start postgresql@14
    sleep 3
fi

# 设置环境变量
export GAOKAO_BENCH_PATH=/Users/zizixiuixu/Downloads/GAOKAO-Bench-main
echo -e "\n${YELLOW}[2/3] 环境变量设置完成${NC}"
echo "   GAOKAO_BENCH_PATH=$GAOKAO_BENCH_PATH"

# 启动后端（后台）
echo -e "\n${YELLOW}[3/3] 启动后端服务...${NC}"
cd backend
source .venv/bin/activate
python start_backend.py &
BACKEND_PID=$!
echo "   后端 PID: $BACKEND_PID"

# 等待后端启动
sleep 5
echo -e "${GREEN}   后端已启动: http://localhost:8000${NC}"

# 启动前端
echo -e "\n${YELLOW}启动前端...${NC}"
cd ../frontend
npm run dev

# 清理后台进程
trap "kill $BACKEND_PID 2>/dev/null; exit" INT
EOF

chmod +x start_all.sh
```

### 运行一键启动
```bash
cd /Users/zizixiuixu/Code/LLM_Project/Edu-System/edu-qa-system
./start_all.sh
```

---

## 方式四：使用 Makefile（高级用户）

创建 `Makefile`:

```makefile
.PHONY: start stop restart db backend frontend

# 默认启动全部
start: db backend frontend

# 启动数据库
db:
	@brew services start postgresql@14 2>/dev/null || true
	@echo "✅ PostgreSQL 已启动"

# 启动后端
backend:
	@export GAOKAO_BENCH_PATH=/Users/zizixiuixu/Downloads/GAOKAO-Bench-main && \
	cd backend && \
	source .venv/bin/activate && \
	python start_backend.py &
	@echo "✅ 后端已启动: http://localhost:8000"

# 启动前端
frontend:
	@cd frontend && npm run dev

# 停止服务
stop:
	@pkill -f "python start_backend.py" 2>/dev/null || true
	@echo "✅ 后端已停止"

# 重启
restart: stop start
```

使用命令：
```bash
make start   # 启动全部
make stop    # 停止
make backend # 仅启动后端
```

---

## 🔧 常用命令速查

### 数据库操作
```bash
# 连接数据库
psql -h localhost -p 15432 -U postgres -d edu_qa

# 查看表
\dt

# 查看知识库数量
SELECT subject, COUNT(*) FROM knowledge GROUP BY subject;

# 导入 GAOKAO 数据
cd backend && python scripts/import_gaokao_full.py
```

### 后端调试
```bash
# 检查后端是否运行
curl http://localhost:8000/health

# 查看 API 文档
open http://localhost:8000/docs

# 查看日志
tail -f backend/logs/app.log
```

### 前端调试
```bash
# 检查前端构建
npm run build

# 代码检查
npm run lint

# 查看依赖
npm list
```

---

## 📝 完整启动流程示例

```bash
# ========== 第1步：确认数据库 ==========
$ pg_isready
localhost:15432 - accepting connections

# ========== 第2步：启动后端 ==========
$ cd /Users/zizixiuixu/Code/LLM_Project/Edu-System/edu-qa-system/backend
$ source .venv/bin/activate
$ export GAOKAO_BENCH_PATH=/Users/zizixiuixu/Downloads/GAOKAO-Bench-main
$ python start_backend.py

2024-01-10 10:00:00 - INFO - 数据库连接成功
2024-01-10 10:00:01 - INFO - 专家池初始化完成
2024-01-10 10:00:02 - INFO - 系统启动完成: http://0.0.0.0:8000

# ========== 第3步：启动前端（新开终端）==========
$ cd /Users/zizixiuixu/Code/LLM_Project/Edu-System/edu-qa-system/frontend
$ npm run dev

> edu-qa-frontend@0.0.0 dev
> vite

  VITE v4.x.x  ready in 500 ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: use --host to expose

# ========== 第4步：访问系统 ==========
# 浏览器打开 http://localhost:3000
# 进入 Benchmark 页面开始测试
```

---

## ⚠️ 常见问题

### 1. 端口被占用
```bash
# 检查端口占用
lsof -i :8000
lsof -i :3000

# 结束占用进程
kill -9 <PID>
```

### 2. 环境变量未生效
```bash
# 检查环境变量
echo $GAOKAO_BENCH_PATH

# 如未设置，手动设置
export GAOKAO_BENCH_PATH=/Users/zizixiuixu/Downloads/GAOKAO-Bench-main
```

### 3. 虚拟环境未激活
```bash
# 确认虚拟环境
which python
# 应显示: .../edu-qa-system/backend/.venv/bin/python

# 如未激活
source backend/.venv/bin/activate
```

---

## 🎯 快速命令（复制粘贴使用）

```bash
# ==== 后端 ====
cd /Users/zizixiuixu/Code/LLM_Project/Edu-System/edu-qa-system && source backend/.venv/bin/activate && export GAOKAO_BENCH_PATH=/Users/zizixiuixu/Downloads/GAOKAO-Bench-main && cd backend && python start_backend.py

# ==== 前端 ====
cd /Users/zizixiuixu/Code/LLM_Project/Edu-System/edu-qa-system/frontend && npm run dev

# ==== 导入数据 ====
cd /Users/zizixiuixu/Code/LLM_Project/Edu-System/edu-qa-system/backend && source .venv/bin/activate && python scripts/import_gaokao_full.py
```
