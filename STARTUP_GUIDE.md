# 完整启动和测试指南

## 🚀 启动命令

### 1. 启动后端服务

```powershell
# 进入后端目录
cd D:/kimi_code/edu_qa_system/backend

# 方式1: 直接启动（推荐测试用）
python -m app.main

# 方式2: 使用 uvicorn（生产环境）
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**预期输出：**
```
📚 初始化多级检索...
  从缓存加载...
✅ 从缓存加载: 8 个学科库，总计 186870 条
[EmbeddingService] 正在加载模型: BAAI/bge-small-zh-v1.5
[EmbeddingService] 模型加载完成
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### 2. 启动前端服务（新开一个终端）

```powershell
# 进入前端目录
cd D:/kimi_code/edu_qa_system/frontend

# 安装依赖（如果还没装）
npm install

# 启动开发服务器
npm run dev
```

**预期输出：**
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
  ➜  press h + enter to show help
```

---

## 🧪 测试流程

### 测试1: 检查服务状态

```powershell
# 测试后端是否运行
curl http://localhost:8000/

# 预期返回:
{"message": "欢迎使用教育问答系统API"}
```

### 测试2: 查看API文档

浏览器访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 测试3: 学科列表API

```powershell
curl http://localhost:8000/experts/subjects

# 预期返回:
{
  "code": 200,
  "data": [
    {"subject": "数学", "has_expert": true, ...},
    {"subject": "物理", "has_expert": true, ...},
    ...
  ]
}
```

### 测试4: 核心问答测试

```powershell
# 测试数学问题
curl -X POST "http://localhost:8000/chat/send" `
  -H "Content-Type: application/json" `
  -d '{"query": "勾股定理是什么？", "session_id": "test-001"}'
```

**预期返回：**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "answer": "【数学专家专家解答 - 增强版】...",
    "session_id": "test-001",
    "expert_name": "数学专家",
    "expert_subject": "数学",
    "used_knowledges": [
      {
        "id": "gsm8k_train_xxx",
        "content": "A rectangle has a length...",
        "source": "gsm8k",
        "tier": 1,
        "score": 0.458
      }
    ],
    "response_time": 1250
  }
}
```

### 测试5: 多学科测试

```powershell
# 物理问题
curl -X POST "http://localhost:8000/chat/send" `
  -H "Content-Type: application/json" `
  -d '{"query": "牛顿第一定律是什么？"}'

# 生物问题
curl -X POST "http://localhost:8000/chat/send" `
  -H "Content-Type: application/json" `
  -d '{"query": "光合作用需要什么条件？"}'

# 语文问题
curl -X POST "http://localhost:8000/chat/send" `
  -H "Content-Type: application/json" `
  -d '{"query": "解释文言文\"学而时习之\""}'
```

### 测试6: 带图片的问题（如果支持）

```powershell
# 先上传图片
curl -X POST "http://localhost:8000/chat/upload-image" `
  -F "file=@test_image.jpg"

# 然后发送带图片的问题
curl -X POST "http://localhost:8000/chat/send" `
  -H "Content-Type: application/json" `
  -d '{"query": "这道题怎么做？", "image": "base64编码..."}'
```

---

## 📝 前端测试

### 访问前端页面

浏览器打开：http://localhost:5173

### 测试步骤：

1. **选择学科** - 点击学科标签（数学/物理/化学等）
2. **输入问题** - 在输入框输入问题
3. **查看回答** - 观察回答和引用来源
4. **检查知识来源** - 展开"参考知识点"查看检索结果

---

## 🔍 高级测试

### 测试RAG效果对比

```powershell
# 创建测试脚本 test_rag.ps1

# 测试1: 有明确学科的问题
Write-Host "=== 测试1: 数学问题 ==="
curl -X POST "http://localhost:8000/chat/send" `
  -H "Content-Type: application/json" `
  -d '{"query": "三角形面积公式"}' | ConvertFrom-Json | Select-Object -ExpandProperty data | Select-Object expert_subject, used_knowledges

# 测试2: 模糊问题
Write-Host "=== 测试2: 模糊问题 ==="
curl -X POST "http://localhost:8000/chat/send" `
  -H "Content-Type: application/json" `
  -d '{"query": "为什么天是蓝的？"}' | ConvertFrom-Json | Select-Object -ExpandProperty data | Select-Object expert_subject, used_knowledges
```

### 检查数据库

```powershell
# 查看会话记录（需要sqlite3）
sqlite3 D:/kimi_code/edu_qa_system/backend/data/edu_qa.db "SELECT * FROM sessions ORDER BY id DESC LIMIT 5;"

# 查看知识库
sqlite3 D:/kimi_code/edu_qa_system/backend/data/edu_qa.db "SELECT subject, COUNT(*) FROM experts GROUP BY subject;"
```

---

## ⚠️ 故障排查

### 问题1: 端口被占用

```powershell
# 查找占用8000端口的进程
netstat -ano | findstr :8000

# 或者更换端口启动
python -m app.main --port 8001
```

### 问题2: 向量缓存加载失败

```powershell
# 删除缓存重新构建
Remove-Item -Recurse -Force D:/毕设数据集/vector_cache_v2

# 重新运行缓存构建
python scripts/build_vector_cache.py
```

### 问题3: Embedding模型下载失败

```powershell
# 手动下载模型
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-zh-v1.5')"
```

### 问题4: 前端无法连接后端

检查 `frontend/.env` 文件：
```
VITE_API_BASE_URL=http://localhost:8000
```

---

## 📊 性能监控

### 查看日志

后端日志会显示：
```
[VL] 学科识别: 数学 (耗时: 0.2s)
[RAG] 检索到 5 条知识 (T1: 3, T2: 2)
[LLM] 生成完成 (耗时: 1.5s)
[Total] 总耗时: 1.8s
```

### 压力测试

```powershell
# 使用ab工具进行压力测试（需要安装Apache Bench）
ab -n 100 -c 10 -T application/json -p post.json http://localhost:8000/chat/send
```

---

## ✅ 测试完成检查清单

- [ ] 后端启动无报错
- [ ] 前端启动无报错
- [ ] 首页可以访问
- [ ] 学科列表正常显示
- [ ] 数学问题能正确识别学科
- [ ] 能检索到相关知识
- [ ] 答案包含知识来源
- [ ] 响应时间在2秒内

全部通过则系统运行正常！🎉
