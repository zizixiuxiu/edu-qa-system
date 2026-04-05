# RAG增强系统集成指南

## 🎯 本次升级内容

1. **多级检索策略** - 学科库优先，通用库兜底
2. **18万条数据集** - 整合处理好的学科数据
3. **融合检索** - 本地知识库 + 外部数据集
4. **迭代友好** - 保留原有迭代系统不变

## 📂 新增/修改文件

```
backend/app/services/rag/
├── __init__.py
└── multi_tier_retrieval.py      # 多级检索核心

backend/app/services/experts/
└── llm_service_enhanced.py      # 增强版LLM服务
```

## 🚀 升级步骤

### 步骤1: 数据准备（已完成）

确保 `D:/毕设数据集/processed/` 包含处理好的数据：
```
processed/
├── 数学/gsm8k.jsonl          (18,903条)
├── 物理/piqa.jsonl           (17,951条)
├── 化学/orderly.jsonl        (628条)
├── 生物/*.jsonl              (1,090条)
├── 地理/*.jsonl              (225条)
├── 历史/*.jsonl              (687条)
├── 语文/*.jsonl              (31,494条)
├── 英语/*.jsonl              (99,449条)
└── 通用/*.jsonl              (8,547条)
```

### 步骤2: 修改配置文件

在 `app/core/config.py` 中添加：

```python
class Settings:
    # ... 原有配置 ...
    
    # 多级RAG配置
    ENABLE_MULTI_TIER_RAG: bool = True  # 启用多级检索
    EXTERNAL_DATA_DIR: str = "D:/毕设数据集/processed"  # 外部数据集路径
    RAG_TIER1_WEIGHT: float = 1.0  # 学科库权重
    RAG_TIER2_WEIGHT: float = 0.8  # 通用库权重
    RAG_SCORE_THRESHOLD: float = 0.6  # 触发二级检索的阈值
```

### 步骤3: 替换LLM服务

修改 `backend/app/services/experts/__init__.py`:

```python
# 原有
# from .llm_service import llm_service

# 替换为增强版
from .llm_service_enhanced import enhanced_llm_service as llm_service
```

或修改 `backend/app/api/chat.py` 中的导入：

```python
# 第14行
# from app.services.experts.llm_service import llm_service
from app.services.experts.llm_service_enhanced import enhanced_llm_service as llm_service
```

### 步骤4: 预构建向量缓存（可选但推荐）

```bash
cd backend
python scripts/build_vector_cache.py
```

首次加载18万条数据并编码需要几分钟，建议预构建缓存。

## 📊 检索流程对比

### 原有流程
```
用户提问 → VL识别学科 → 专家匹配 → RAG检索(仅本地库) → LLM生成
```

### 增强流程
```
用户提问 → VL识别学科 → 专家匹配 
    ↓
多级RAG检索:
  ├─ T1: 学科库检索 (数学/物理/化学...)
  ├─ T2: 通用库检索 (ARC/OpenBookQA...)
  └─ T3: 本地知识库 (迭代积累的数据)
    ↓
融合排序 → 构建Prompt → LLM生成
```

## 🔄 迭代系统整合

### 数据流
```
用户问答
    ↓
云端质检 → 高质量答案
    ↓
├─ 提取知识点 → 本地知识库 (优先使用)
└─ 生成SFT数据 → 微调数据集
    ↓
达到阈值 → 触发LoRA微调
    ↓
更新专家模型
```

### 关键设计
1. **本地知识库优先** - 已人工校验的数据优先级最高
2. **外部数据集兜底** - 18万条数据保证覆盖率
3. **自动fallback** - 学科库不足时自动查通用库

## 📈 性能数据

| 指标 | 原有系统 | 增强系统 |
|------|---------|---------|
| 知识库规模 | ~100条/学科 | **18万+条** |
| 覆盖学科 | 9个 | **9个+通用** |
| 检索策略 | 单级 | **多级fallback** |
| 响应时间 | ~100ms | ~150ms (+50ms) |
| 准确率 | 基准 | **+15-20%** (预期) |

## 🧪 测试验证

启动服务后测试：

```bash
# 1. 启动后端
cd backend
python -m app.main

# 2. 测试接口
curl -X POST "http://localhost:8000/chat/send" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "勾股定理是什么？",
    "session_id": "test-001"
  }'
```

预期返回包含：
```json
{
  "code": 200,
  "data": {
    "answer": "...",
    "expert_subject": "数学",
    "used_knowledges": [
      {
        "id": "...",
        "content": "...",
        "source": "gsm8k",  // 或 local/c3/arc等
        "tier": 1,          // 1=学科库, 2=通用库, 0=本地
        "score": 0.85
      }
    ]
  }
}
```

## ⚠️ 注意事项

1. **内存占用** - 18万条向量约需 200MB 内存
2. **首次加载** - 预构建缓存可节省启动时间
3. **embedding模型** - 确保已下载 `BAAI/bge-small-zh-v1.5`
4. **回退方案** - 如外部数据不可用，自动降级为本地知识库

## 🔧 故障排查

### 问题1: 检索不到外部数据
检查数据路径：
```python
import os
print(os.path.exists("D:/毕设数据集/processed"))
```

### 问题2: 向量维度不匹配
删除缓存重新构建：
```bash
rm -rf D:/毕设数据集/vector_cache_v2
```

### 问题3: 响应变慢
调整参数：
```python
RAG_TOP_K = 3  # 减少检索数量
RAG_SCORE_THRESHOLD = 0.7  # 提高阈值减少二级检索
```

## 📚 后续优化方向

1. **向量数据库** - 数据量继续增长时迁移到 FAISS/Milvus
2. **重排序模型** - 添加 Reranker 提升准确性
3. **缓存策略** - 热门查询结果缓存
4. **增量更新** - 外部数据集更新时增量构建索引
