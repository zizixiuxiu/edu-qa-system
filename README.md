# 🎓 EduQA - 基于专家模型路由的多模态教育知识问答系统

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![Vue 3](https://img.shields.io/badge/Vue-3.4+-4FC08D.svg)](https://vuejs.org/)

## 📋 项目简介

本系统是**毕业设计项目**，实现了一个基于专家模型路由的多模态教育知识问答系统，核心创新点包括：

- 🔀 **专家模型路由**: 使用VLM自动识别学科，动态路由到对应专家池
- 🔄 **自我迭代更新**: 云端质检纠正 → 知识提取 → 向量库自动更新
- 📊 **微调数据生成**: 自动构建Instruction格式训练数据
- 🧪 **完整实验支持**: 一键切换消融实验/对比实验配置，自动生成论文图表

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端 (Vue3 + Element Plus)                 │
│                  孟菲斯风格设计 (Memphis Design)                   │
└─────────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────────┐
│                     API层 (FastAPI)                              │
│  /chat/send    /experts/list    /experiments/config              │
└─────────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────────┐
│                      核心服务层                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ VL学科识别    │  │ 专家池管理    │  │ 自我迭代飞轮系统      │  │
│  │ (Qwen3-VL)   │  │ (动态创建)    │  │ (质检→去重→更新)     │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────────┐
│                    数据层 (PostgreSQL + pgvector)                │
│  experts / knowledge / sft_data / sessions / experiment_metrics │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 1. 环境准备

```bash
# Python 3.9+
# PostgreSQL 14+ (需安装pgvector扩展)
# Node.js 18+
# LMStudio (本地模型服务)
```

### 2. 数据库配置

```bash
# 创建数据库
createdb edu_qa

# 安装pgvector扩展
psql -d edu_qa -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 3. 后端启动

```bash
# 进入项目目录
cd edu_qa_system

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r backend/requirements.txt

# 配置环境变量
cp backend/.env.example backend/.env
# 编辑 .env 文件，配置你的数据库和API密钥

# 启动后端
python start_backend.py
```

后端服务将在 http://localhost:8000 启动，API文档访问 http://localhost:8000/docs

### 4. 前端启动

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端将在 http://localhost:3000 启动

### 5. 模型配置 (LMStudio)

1. 下载并安装 [LMStudio](https://lmstudio.ai/)
2. 下载模型:
   - Qwen3-VL-4B (视觉语言模型 - 学科识别)
   - Qwen2.5-7B (基础大模型 - 问答推理)
3. 启动本地服务器 (默认端口 1234)

## 🧪 实验配置 (论文核心)

系统内置6种实验模式，支持一键切换：

| 模式 | 专家路由 | RAG | 自我迭代 | 微调 | 用途 |
|------|---------|-----|---------|------|------|
| `baseline` | ❌ | ❌ | ❌ | ❌ | 基线对比 |
| `rag_only` | ❌ | ✅ | ❌ | ❌ | 验证RAG效果 |
| `expert_routing` | ✅ | ✅ | ❌ | ❌ | 验证专家路由 |
| `full_system` | ✅ | ✅ | ✅ | ✅ | 完整系统 |
| `ablation_no_iteration` | ✅ | ✅ | ❌ | ✅ | 消融实验 |
| `ablation_no_finetune` | ✅ | ✅ | ✅ | ❌ | 消融实验 |

切换方式:
- 前端: 访问 `/experiments` 页面
- API: `POST /api/v1/experiments/config` {"preset": "full_system"}

## 📊 论文数据导出

系统自动收集以下实验数据：

```bash
# 导出JSON格式
GET /api/v1/experiments/export-data?format=json

# 导出CSV格式  
GET /api/v1/experiments/export-data?format=csv
```

数据包含:
- 响应时间分布
- 准确率统计
- 专家路由记录
- 知识库增长曲线
- 云端成本趋势

## 📁 项目结构

```
edu_qa_system/
├── backend/
│   ├── app/
│   │   ├── api/              # API路由
│   │   ├── core/             # 配置、数据库
│   │   ├── models/           # 数据模型
│   │   ├── services/         # 业务逻辑
│   │   │   ├── router/       # 专家路由
│   │   │   ├── experts/      # 专家池
│   │   │   ├── iteration/    # 自我迭代
│   │   │   └── monitoring/   # 监控
│   │   └── main.py           # 入口
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── views/            # 页面组件
│   │   ├── api/              # API封装
│   │   ├── stores/           # Pinia状态
│   │   └── styles/           # 孟菲斯风格
│   └── package.json
└── README.md
```

## 🎨 前端设计

采用**孟菲斯设计风格 (Memphis Design)**:
- 高饱和度撞色 (蓝/黄/粉/青/桃色)
- 粗黑边框 + 硬阴影
- 几何装饰元素
- 点状图案背景

设计灵感源自80年代意大利孟菲斯设计小组，体现复古与现代的碰撞。

## ⚙️ 核心配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `FINETUNE_THRESHOLD` | 200 | 触发微调的SFT数据阈值 |
| `QUALITY_THRESHOLD` | 4.0 | 入知识库的质量评分阈值(0-5) |
| `DEDUP_THRESHOLD` | 0.92 | 去重相似度阈值(余弦) |
| `RAG_TOP_K` | 5 | RAG检索Top-K |

配置文件: `backend/.env`

## 📝 开发计划

- [x] 基础框架搭建
- [x] VL学科识别
- [x] 专家池动态管理
- [x] RAG知识检索
- [x] 云端质检纠正
- [x] 向量去重
- [x] 微调数据生成
- [x] 实验控制模块
- [x] 数据可视化
- [ ] 语音功能 (预留接口)
- [ ] 微调训练 pipeline
- [ ] 高等教育领域扩展

## 📄 许可证

MIT License - 仅供毕业设计使用

---

**作者**: 毕业设计项目组  
**指导教师**: [待填写]  
**学校**: [待填写]
