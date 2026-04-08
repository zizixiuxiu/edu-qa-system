# EduQA V2 API 配置文档

**配置日期**: 2026-04-07  
**版本**: v2.1

---

## 🎯 服务架构

```
┌─────────────────────────────────────────────────────────────┐
│                      EduQA V2 系统                           │
├─────────────────────────────────────────────────────────────┤
│  本地服务 (Local)           │  云端服务 (Cloud)              │
│  ─────────────────          │  ────────────────              │
│  LM Studio @ :1234          │  Moonshot API                  │
│  ├── Qwen3-VL-4B (VLM)      │  └── Kimi K2.5 (质检)          │
│  └── Qwen3.5 (LLM)          │                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 配置详情

### 1. VLM 视觉语言模型 (本地)

| 配置项 | 值 | 说明 |
|--------|-----|------|
| **模型** | `qwen/qwen3-vl-4b` | 多模态学科分类 |
| **服务URL** | `http://127.0.0.1:1234/v1` | LM Studio本地服务 |
| **超时** | 30秒 | 图片识别超时 |

**功能**:
- 图片学科分类（九大学科）
- 图文混合输入理解
- OCR文字提取
- 三级降级策略（VLM→关键词→通用）

**学科映射**:
```python
{
    "math": "数学",
    "physics": "物理",
    "chemistry": "化学",
    "biology": "生物",
    "chinese": "语文",
    "english": "英语",
    "history": "历史",
    "geography": "地理",
    "politics": "政治",
    "general": "通用"
}
```

---

### 2. LLM 主模型 (本地)

| 配置项 | 值 | 说明 |
|--------|-----|------|
| **模型** | `qwen/qwen3-vl-4b` | 主语言模型 |
| **服务URL** | `http://127.0.0.1:1234/v1` | LM Studio本地服务 |
| **超时** | 120秒 | 生成超时 |
| **重试** | 3次 | 失败重试 |

**功能**:
- 问答生成
- RAG上下文理解
- 多轮对话

---

### 3. 云端质检服务 (Moonshot)

| 配置项 | 值 | 说明 |
|--------|-----|------|
| **模型** | `kimi-k2-5` | 高质量评估模型 |
| **服务URL** | `https://api.moonshot.cn/v1` | Moonshot API |
| **API Key** | `sk-exe...K8b6` | 已配置 |
| **超时** | 60秒 | 质检超时 |

**功能**:
- 答案质量评估 (0-5分)
- 差异化权重评分
- 知识类型自动识别
- 入库决策 (阈值≥4.0)

**评分维度**:
| 知识类型 | 准确性 | 完整性 | 清晰度 | 教育性 |
|---------|--------|--------|--------|--------|
| formula | 40% | 25% | 20% | 15% |
| concept | 30% | 30% | 20% | 20% |
| step | 35% | 30% | 25% | 10% |
| template | 30% | 25% | 25% | 20% |
| qa | 40% | 30% | 20% | 10% |

---

## 📝 配置文件

### 环境变量 (.env)
```bash
# 本地服务
LLM_BASE_URL=http://127.0.0.1:1234/v1
VL_BASE_URL=http://127.0.0.1:1234/v1

# 云端服务
KIMI_BASE_URL=https://api.moonshot.cn/v1
KIMI_API_KEY=sk-exeOu7RTp3Z01hjyOjkMJ22XeiFU3PaTWUrm6Q7AiabeK8b6
```

### 代码配置 (config.py)
```python
class Settings(BaseSettings):
    # VLM配置
    VL_MODEL: str = "qwen/qwen3-vl-4b"
    VL_BASE_URL: str = "http://127.0.0.1:1234/v1"
    VL_TIMEOUT: float = 30.0
    
    # LLM配置
    LLM_BASE_URL: str = "http://127.0.0.1:1234/v1"
    LLM_MODEL: str = "qwen/qwen3-vl-4b"
    LLM_TIMEOUT: float = 120.0
    
    # 云端质检
    KIMI_BASE_URL: str = "https://api.moonshot.cn/v1"
    KIMI_API_KEY: str = "sk-exeOu7RTp3Z01hjyOjkMJ22XeiFU3PaTWUrm6Q7AiabeK8b6"
    KIMI_MODEL: str = "kimi-k2-5"
```

---

## 🚀 使用示例

### VLM 学科分类
```python
from app.infrastructure.llm.vlm_service import vlm_service

# 分类图片
subject_en, confidence = await vlm_service.classify_image(
    image_data=image_bytes,
    text="求解这个方程"
)
subject_zh = vlm_service.to_chinese(subject_en)
# 返回: ("数学", 0.9)
```

### 云端质量评估
```python
from app.infrastructure.llm.quality_service import cloud_quality_service

# 评估答案质量
overall, details, feedback = await cloud_quality_service.evaluate_answer(
    question="什么是牛顿第二定律？",
    answer="F=ma，力等于质量乘以加速度",
    subject="物理",
    knowledge_type="formula"
)
# 返回: (4.5, {"accuracy": 5, ...}, "解释清晰")

# 判断是否入库
should_add, score = await cloud_quality_service.should_add_to_knowledge_base(
    question="...",
    answer="...",
    threshold=4.0
)
```

---

## ⚠️ 注意事项

### 本地服务启动
确保 LM Studio 已启动并加载模型：
```
1. 打开 LM Studio
2. 加载 qwen3-vl-4b 模型
3. 启动本地服务器 (端口1234)
```

### 云端服务配额
Moonshot API 有调用配额限制：
- 免费额度：有限制
- 付费升级：联系Moonshot

### 降级策略
如果服务不可用，系统会自动降级：
1. VLM失败 → 关键词匹配
2. 云端质检失败 → 本地规则评分

---

## ✅ 验证命令

```bash
cd v2/backend

# 验证配置
python -c "
from app.core.config import get_settings
settings = get_settings()
print(f'VL模型: {settings.VL_MODEL}')
print(f'云端模型: {settings.KIMI_MODEL}')
print(f'API Key: {settings.KIMI_API_KEY[:10]}...')
"
```

---

## 🔗 相关文档

- [论文对齐报告](./THESIS_ALIGNMENT_REPORT.md)
- [Bug修复确认](./BUGFIX_CONFIRMATION.md)
- [VLM服务源码](./backend/app/infrastructure/llm/vlm_service.py)
- [质检服务源码](./backend/app/infrastructure/llm/quality_service.py)

---

**配置状态**: ✅ 已完成  
**最后更新**: 2026-04-07
