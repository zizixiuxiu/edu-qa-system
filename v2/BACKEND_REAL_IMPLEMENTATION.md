# EduQA V2 后端真实实现说明

**更新时间**: 2026-04-07  
**说明**: 所有模拟实现已替换为真实实现

---

## ✅ 已实现的真实模块

### 1. LLM 客户端 (真实实现)

**文件**: `app/infrastructure/llm/client.py`

**功能**:
- ✅ 真实 OpenAI API 调用 (支持 LM Studio、Ollama 等)
- ✅ 异步 HTTP 请求 (aiohttp)
- ✅ 聊天补全 API
- ✅ 多模态生成 (图片+文本)
- ✅ 流式生成支持
- ✅ 错误处理和超时控制

**配置**:
```env
LLM_BASE_URL=http://127.0.0.1:1234/v1
LLM_API_KEY=not-needed
LLM_MODEL=qwen/qwen3.5-9b
LLM_TIMEOUT=120.0
```

**使用**:
```python
from app.infrastructure.llm.client import get_llm_client

client = get_llm_client()
response = await client.generate("解释牛顿第一定律")
# 返回: 真实的LLM生成文本
```

---

### 2. VLM 服务 (真实实现)

**文件**: `app/infrastructure/llm/vlm_service.py`

**功能**:
- ✅ 真实 VLM API 调用 (Qwen3-VL-4B)
- ✅ 图片学科分类
- ✅ 三级降级策略 (VLM→关键词→通用)
- ✅ OCR 文字提取
- ✅ 九大学科关键词库

**配置**:
```env
VL_BASE_URL=http://127.0.0.1:1234/v1
VL_MODEL=qwen/qwen3-vl-4b
VL_TIMEOUT=30.0
```

**使用**:
```python
from app.infrastructure.llm.vlm_service import vlm_service

subject, confidence = await vlm_service.classify_image(
    image_data=image_bytes,
    text="求解这个方程"
)
# 返回: ("math", 0.92) - 真实的VLM分类结果
```

---

### 3. BGE Embedding 编码器 (真实实现)

**文件**: `app/infrastructure/embedding/bge_encoder.py`

**功能**:
- ✅ 真实 BGE-small-zh-v1.5 模型加载
- ✅ 384维向量生成
- ✅ 余弦相似度计算
- ✅ 异步编码 (线程池)
- ✅ 向量归一化
- ⚠️ 需要 transformers + torch

**配置**:
```env
EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5
EMBEDDING_DIMENSION=384
EMBEDDING_DEVICE=cpu  # 或 cuda
```

**依赖安装**:
```bash
pip install torch transformers numpy sentencepiece protobuf
```

**使用**:
```python
from app.infrastructure.embedding.bge_encoder import encode_text

vectors = await encode_text(["一元二次方程", "牛顿第二定律"])
# 返回: 真实的384维向量
```

---

### 4. RAG 检索服务 (真实实现)

**文件**: `app/domain/services/rag_service.py`

**功能**:
- ✅ 真实 pgvector 向量检索
- ✅ 三级知识库 (Tier0/Tier1/Tier2)
- ✅ 余弦相似度计算 (embedding <=> query)
- ✅ 加权融合排序
- ✅ 向量去重检查
- ✅ 质量分加权

**数据库**:
```sql
-- 使用 pgvector 扩展
CREATE EXTENSION vector;

-- 向量检索示例
SELECT 1 - (embedding <=> query_embedding) as similarity
FROM knowledge_items
WHERE tier = 'tier0'
ORDER BY similarity DESC
LIMIT 5;
```

**使用**:
```python
from app.domain.services.rag_service import get_retriever

retriever = get_retriever()
results = await retriever.retrieve(
    query="一元二次方程求根公式",
    expert_id=1,
    top_k=5
)
# 返回: 真实的检索结果 [RetrievalResult(...), ...]
```

---

### 5. 云端质检服务 (真实实现)

**文件**: `app/application/services/quality_service.py`

**功能**:
- ✅ 真实 Kimi/Moonshot API 调用
- ✅ 5类知识自动识别 (formula/concept/template/step/qa)
- ✅ 差异化评估权重
- ✅ 质量评分 (0-5分)
- ✅ 自动入库流程
- ✅ 向量去重
- ⚠️ 需要配置有效的 KIMI_API_KEY

**配置**:
```env
KIMI_BASE_URL=https://api.moonshot.cn/v1
KIMI_API_KEY=sk-your-key-here
KIMI_MODEL=kimi-k2-5
KNOWLEDGE_QUALITY_THRESHOLD=4.0
```

**使用**:
```python
from app.application.services.quality_service import get_quality_checker

checker = get_quality_checker()
result = await checker.check_quality(
    question="什么是牛顿第二定律？",
    answer="F=ma，力等于质量乘以加速度...",
    subject="physics"
)
# 返回: 真实的质量评分 QualityCheckResult(...)
```

---

### 6. 实验引擎 (真实实现)

**文件**: `app/application/services/benchmark_engine.py`

**功能**:
- ✅ 真实 LLM 答题
- ✅ 真实 RAG 检索增强
- ✅ 真实云端质检评估
- ✅ 自我迭代入库
- ✅ 按学科统计
- ✅ 详细的实验报告

**使用**:
```python
from app.application.services.benchmark_engine import BenchmarkEngine

engine = BenchmarkEngine()
report = await engine.run_experiment(
    experiment_id="exp_001",
    config={
        "subject": "physics",
        "max_questions": 50,
        "enable_rag": True,
        "enable_iteration": True
    }
)
# 返回: 真实的实验报告，包含准确率、评分等
```

---

## 🔧 依赖要求

### 基础依赖
```bash
pip install -r requirements.txt
```

### ML依赖 (用于Embedding)
```bash
pip install torch transformers numpy sentencepiece protobuf
```

### 模型下载
首次使用时会自动下载模型：
- `BAAI/bge-small-zh-v1.5` (约200MB)

---

## ⚙️ 本地服务部署

### 1. LLM/VLM 服务 (LM Studio)

```bash
# 启动 LM Studio 本地服务器
# 1. 打开 LM Studio
# 2. 加载模型: qwen/qwen3.5-9b
# 3. 启动本地服务器 (端口 1234)
```

### 2. PostgreSQL + pgvector

```bash
# Docker 启动
docker run -d \
  --name edu-qa-db \
  -e POSTGRES_PASSWORD=password \
  -p 15432:5432 \
  ankane/pgvector:latest

# 创建数据库
docker exec -it edu-qa-db psql -U postgres -c "CREATE DATABASE edu_qa;"
```

---

## 📝 配置检查清单

### 必需配置
- [ ] LLM_BASE_URL - 本地LLM服务地址
- [ ] DATABASE_URL - PostgreSQL连接
- [ ] KIMI_API_KEY - 云端质检API密钥 (可选，用于真实质检)

### 可选配置
- [ ] EMBEDDING_DEVICE - cuda/cpu (默认cpu)
- [ ] RAG_SIMILARITY_THRESHOLD - 相似度阈值 (默认0.7)
- [ ] KNOWLEDGE_QUALITY_THRESHOLD - 入库阈值 (默认4.0)

---

## 🚀 快速开始

### 1. 启动后端

```bash
cd v2/backend

# 安装依赖
pip install -r requirements.txt
pip install torch transformers

# 配置环境变量
copy .env.example .env
# 编辑 .env 文件

# 启动服务
python -m app.main
```

### 2. 测试 API

```bash
# 测试健康检查
curl http://localhost:8000/api/v1/health

# 测试专家列表
curl http://localhost:8000/api/v1/experts/list

# 测试RAG检索
curl -X POST http://localhost:8000/api/v1/knowledge/search \
  -H "Content-Type: application/json" \
  -d '{"query": "牛顿第二定律", "top_k": 3}'
```

---

## ⚠️ 注意事项

### 1. Embedding 模型加载
- 首次使用时会自动下载 BGE 模型
- 需要约 200MB 磁盘空间
- 加载时可能需要几秒钟

### 2. LLM 服务依赖
- 所有 LLM 调用依赖本地 LM Studio 服务
- 确保 LM Studio 已启动并加载模型
- 如果服务不可用会抛出异常

### 3. Kimi API 限制
- 云端质检需要有效的 API Key
- 如果 API 不可用会降级到本地规则评分
- 本地规则评分准确性较低

### 4. 数据库依赖
- RAG 检索需要 PostgreSQL + pgvector
- 确保数据库已正确配置
- 向量维度必须是 384

---

## 🐛 故障排除

### 问题: `ImportError: No module named 'transformers'`
**解决**: `pip install transformers torch`

### 问题: `无法连接到LLM服务`
**解决**: 检查 LM Studio 是否启动，端口是否正确

### 问题: `pgvector 扩展未安装`
**解决**: 
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 问题: `Kimi API 返回错误`
**解决**: 检查 KIMI_API_KEY 是否有效，或等待降级到本地评分

---

## ✅ 验证真实实现

运行以下命令验证所有模块:

```bash
cd v2/backend
python -c "
from app.infrastructure.llm.client import get_llm_client
from app.infrastructure.llm.vlm_service import vlm_service
from app.infrastructure.embedding.bge_encoder import get_encoder
from app.domain.services.rag_service import get_retriever
from app.application.services.quality_service import get_quality_checker
from app.application.services.benchmark_engine import BenchmarkEngine

print('✅ 所有真实实现模块导入成功!')
"
```

---

**所有模块已替换为真实实现，系统已准备好进行端到端测试!** 🎉
