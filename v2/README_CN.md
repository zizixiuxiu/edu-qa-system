# EduQA V2 - 基于专家模型路由的多模态教育知识问答系统

## 项目概述

EduQA V2 是一个企业级教育问答系统，采用专家模型路由、多模态理解和检索增强生成(RAG)技术，为K12教育提供高质量的智能问答服务。

## 核心特性

### 1. 异构专家网络
- 九大学科专家（数学、物理、化学、生物、语文、英语、历史、地理、政治）
- 基于Qwen3-VL-4B的多模态学科路由
- 个性化Prompt工程

### 2. 多级知识检索
- **Tier 0**: 本地迭代知识库（最高质量）
- **Tier 1**: 学科专属知识库（领域知识）
- **Tier 2**: 通用知识库（兜底知识）
- BGE-384维向量化 + pgvector相似度检索

### 3. 自我进化闭环
- 云端Kimi API质量检查
- 五类知识自动识别（formula/concept/template/step/qa）
- 差异化质量评估权重
- 向量去重机制

## 技术架构

### 后端技术栈
- **框架**: FastAPI + SQLModel
- **数据库**: PostgreSQL + pgvector
- **向量模型**: BAAI/bge-small-zh-v1.5 (384维)
- **视觉模型**: Qwen3-VL-4B (本地部署)
- **语言模型**: Kimi-K2.5 (云端质检)

### 前端技术栈
- **框架**: Vue 3 + TypeScript
- **UI库**: Element Plus
- **状态管理**: Pinia
- **Markdown渲染**: marked + katex
- **图表**: ECharts

## 快速启动

### 前置要求

1. **Python 3.9+**
2. **Node.js 18+**
3. **PostgreSQL 15+** (带pgvector扩展)
4. **LM Studio** (用于本地部署Qwen3-VL-4B)
5. **Kimi API Key** (可选，用于云端质检)

### 数据库配置

```sql
-- 创建数据库
CREATE DATABASE edu_qa;

-- 启用pgvector扩展
\c edu_qa
CREATE EXTENSION vector;
```

### 环境变量配置

编辑 `backend/.env` 文件：

```bash
# 数据库配置
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:15432/edu_qa

# 主LLM配置 (本地LM Studio)
LLM_BASE_URL=http://127.0.0.1:1234/v1
LLM_API_KEY=not-needed
LLM_MODEL=qwen/qwen3.5-9b

# VL模型配置
VL_MODEL=qwen/qwen3-vl-4b

# Kimi云端质检 (可选)
KIMI_BASE_URL=https://api.moonshot.cn/v1
KIMI_API_KEY=your-kimi-api-key
KIMI_MODEL=moonshot-v1-8k

# Embedding配置
EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5
EMBEDDING_DIMENSION=384
```

### 启动服务

#### 方式一：一键启动（推荐）

```bash
# Windows
start_all.bat
```

#### 方式二：分别启动

**后端服务:**
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**前端服务:**
```bash
cd frontend
npm install
npm run dev
```

### 访问系统

- **前端界面**: http://localhost:3000
- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

## 系统架构图

```
┌─────────────────────────────────────────────────────────┐
│                     前端 (Vue 3)                         │
│  ┌─────────┬─────────┬─────────┬─────────┬───────────┐  │
│  │ 聊天界面 │ 专家管理 │ 知识库 │ 实验控制 │ 数据分析 │  │
│  └─────────┴─────────┴─────────┴─────────┴───────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                  后端 (FastAPI)                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │              API 路由层                            │   │
│  ├──────────────────────────────────────────────────┤   │
│  │              应用服务层                            │   │
│  │  - ChatApplicationService                        │   │
│  │  - ExpertApplicationService                      │   │
│  │  - QualityChecker                                │   │
│  ├──────────────────────────────────────────────────┤   │
│  │              领域服务层                            │   │
│  │  - RoutingService (VLM路由)                       │   │
│  │  - MultiTierRetriever (三级RAG)                  │   │
│  ├──────────────────────────────────────────────────┤   │
│  │              基础设施层                            │   │
│  │  - LLMClient (本地LM Studio)                     │   │
│  │  - VLMService (Qwen3-VL-4B)                      │   │
│  │  - BGEEncoder (BGE向量化)                        │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  PostgreSQL  │  │ LM Studio    │  │ Kimi API     │
│  + pgvector  │  │ Qwen3-VL-4B  │  │ 云端质检     │
└──────────────┘  └──────────────┘  └──────────────┘
```

## 核心功能模块

### 1. 聊天服务 (`/chat/send`)
- 多模态输入（文本+图片）
- VLM学科分类
- 专家路由
- RAG检索
- 流式响应

### 2. 专家管理 (`/experts`)
- 创建/更新专家
- 专家状态管理
- 知识库统计

### 3. 知识库管理 (`/knowledge`)
- 知识CRUD
- 向量检索
- 质量评分

### 4. 实验控制 (`/experiments`)
- 消融实验配置
- 一键运行6组实验
- 进度追踪

## API文档

### 聊天接口
```http
POST /api/v1/chat/send
Content-Type: application/json

{
  "message": "解方程: 2x + 5 = 13",
  "image_url": "data:image/jpeg;base64,...",
  "session_id": "optional-session-id",
  "force_expert": "数学"
}
```

### 专家列表
```http
GET /api/v1/experts/list
```

### 知识检索
```http
POST /api/v1/knowledge/search
Content-Type: application/json

{
  "query": "一元二次方程",
  "expert_id": 1,
  "top_k": 5
}
```

## 开发指南

### 添加新的学科专家
```python
# 在 ExpertApplicationService.ensure_default_experts() 中添加
default_subjects = [
    "数学", "物理", "化学", "生物",
    "语文", "英语", "历史", "地理", "政治",
    "新学科"  # 添加新学科
]
```

### 自定义RAG权重
```python
# 在 MultiTierRetriever 中修改权重
RUNTIME_WEIGHTS = {
    "tier0": 0.95,  # 调整权重
    "tier1": 1.0,
    "tier2": 0.7
}
```

## 故障排查

### 数据库连接失败
- 检查PostgreSQL是否运行
- 确认pgvector扩展已安装
- 验证DATABASE_URL配置

### LLM服务无响应
- 确认LM Studio正在运行
- 检查模型是否已加载
- 验证LLM_BASE_URL配置

### 向量检索报错
- 确认embedding表已创建向量索引
- 检查pgvector扩展版本
- 验证EMBEDDING_DIMENSION配置

## 项目结构

```
v2/
├── backend/
│   ├── app/
│   │   ├── application/     # 应用服务层
│   │   ├── domain/          # 领域模型层
│   │   ├── infrastructure/  # 基础设施层
│   │   ├── interfaces/      # 接口层
│   │   └── core/            # 核心配置
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── api/            # API客户端
│   │   ├── components/     # Vue组件
│   │   ├── stores/         # Pinia状态
│   │   ├── views/          # 页面视图
│   │   └── router/         # 路由配置
│   └── package.json
├── start_all.bat           # 一键启动
├── start_backend.bat       # 后端启动
└── start_frontend.bat      # 前端启动
```

## 论文对齐

本系统实现与论文《基于专家模型路由的多模态教育知识问答系统设计与实现》完全对齐：

- ✅ 异构专家网络 (第3.3节)
- ✅ 多模态学科路由 (第3.4节)
- ✅ 三级知识检索架构 (第3.5节)
- ✅ 自我进化闭环 (第3.6节)
- ✅ 实验与评测系统 (第5章)

## 许可证

本项目仅供学习研究使用。

## 联系方式

如有问题，请提交Issue或联系开发团队。
