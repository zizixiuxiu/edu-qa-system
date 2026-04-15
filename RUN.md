# 启动命令

## 后端

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

或：

```bash
cd backend
source .venv/bin/activate
python start_backend.py
```

## 前端

```bash
cd frontend
npm install
npm run dev
```

## 一键启动

```bash
./quick_start.sh
```

---

**访问地址**
- 前端：http://localhost:5173
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs
