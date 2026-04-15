# EduQA V2 - 企业级重构版

## 🏗️ 架构概览

EduQA V2 采用**领域驱动设计 (DDD)** 和**分层架构**，实现高内聚、低耦合、可测试、可扩展的企业级系统。

```
┌─────────────────────────────────────────────────────────────┐
│                    接口适配层 (Interfaces)                    │
│  - HTTP API (FastAPI)                                       │
│  - WebSocket (实时通信)                                      │
│  - CLI / Admin                                              │
├─────────────────────────────────────────────────────────────┤
│                    应用层 (Application)                     │
│  - 应用服务 (用例编排)                                       │
│  - DTO (数据传输对象)                                        │
│  - 事务控制                                                 │
├─────────────────────────────────────────────────────────────┤
│                    领域层 (Domain)                          │
│  - 领域模型 (Expert, Knowledge, Session)                    │
│  - 领域服务 (Routing, Retrieval)                            │
│  - 领域事件 (QualityCheckCompleted)                         │
│  - 仓储接口 (Repository)                                    │
├─────────────────────────────────────────────────────────────┤
│                  基础设施层 (Infrastructure)                │
│  - 数据库 (PostgreSQL + pgvector)                           │
│  - 缓存 (Redis)                                             │
│  - LLM客户端                                                │
│  - Embedding服务                                            │
│  - 文件存储                                                 │
├─────────────────────────────────────────────────────────────┤
│                    核心层 (Core)                            │
│  - 配置管理 (Pydantic Settings)                             │
│  - 结构化日志 (structlog)                                    │
│  - 异常体系                                                 │
│  - 事件总线                                                 │
└─────────────────────────────────────────────────────────────┘
```

## 📁 目录结构

```
v2/
├── backend/
│   ├── app/
│   │   ├── core/                    # 核心层
│   │   │   ├── config.py           # 配置管理
│   │   │   ├── exceptions.py       # 异常体系
│   │   │   ├── logging.py          # 结构化日志
│   │   │   └── events.py           # 事件总线
│   │   ├── domain/                  # 领域层
│   │   │   ├── base/               # 领域基类
│   │   │   │   ├── entity.py       # 实体基类
│   │   │   │   └── repository.py   # 仓储接口
│   │   │   ├── models/             # 领域模型
│   │   │   │   ├── expert.py       # 专家模型
│   │   │   │   ├── knowledge.py    # 知识模型
│   │   │   │   └── session.py      # 会话模型
│   │   │   ├── services/           # 领域服务
│   │   │   │   ├── routing_service.py
│   │   │   │   └── retrieval_service.py
│   │   │   └── events/             # 领域事件
│   │   ├── infrastructure/          # 基础设施层
│   │   │   ├── database/           # 数据库
│   │   │   │   ├── connection.py   # 连接管理
│   │   │   │   ├── models.py       # 数据库模型
│   │   │   │   └── repositories/   # 仓储实现
│   │   │   ├── cache/              # 缓存
│   │   │   ├── embedding/          # Embedding服务
│   │   │   └── llm/                # LLM客户端
│   │   ├── application/             # 应用层
│   │   │   ├── services/           # 应用服务
│   │   │   └── dto/                # 数据传输对象
│   │   ├── interfaces/              # 接口层
│   │   │   └── http/               # HTTP API
│   │   │       ├── routers/        # 路由
│   │   │       └── middleware/     # 中间件
│   │   └── main.py                  # 应用入口
│   ├── tests/                       # 测试
│   ├── alembic/                     # 数据库迁移
│   └── requirements.txt
├── frontend/                        # Vue3前端 (待实现)
└── docs/                            # 文档
    └── architecture/               # 架构文档
```

## 🎯 核心改进

### 1. 架构改进
| 方面 | V1 | V2 |
|------|-----|-----|
| 架构模式 | 贫血模型 | 领域驱动设计 |
| 依赖方向 | 混乱 | 单向依赖（内层稳定） |
| 测试性 | 差 | 易于单元测试 |
| 扩展性 | 有限 | 插件化扩展 |

### 2. 代码质量
- ✅ **类型安全**: 完整的类型注解
- ✅ **结构化日志**: JSON格式，便于监控
- ✅ **统一异常**: 分层异常体系
- ✅ **配置分离**: 环境配置独立管理

### 3. 企业级特性
- ✅ **连接池**: 数据库连接池管理
- ✅ **事务控制**: 工作单元模式
- ✅ **事件驱动**: 领域事件解耦
- ✅ **健康检查**: /health 端点

## 🚀 快速开始

### 1. 安装依赖
```bash
cd v2/backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 配置环境
```bash
cp .env.example .env
# 编辑 .env 配置数据库和API密钥
```

### 3. 启动服务
```bash
python -m uvicorn app.main:app --reload
```

## 📊 与原系统对比

| 功能 | V1 实现 | V2 架构 |
|------|---------|---------|
| 专家路由 | 混合在API中 | 独立领域服务 |
| 知识检索 | 直接SQL | 仓储模式 + 接口隔离 |
| 实验控制 | 全局变量 | 状态机 + 领域模型 |
| 日志记录 | print | 结构化日志 |
| 异常处理 | 分散 | 统一异常体系 |
| 配置管理 | 硬编码 | Pydantic Settings |

## 📝 待完成工作

### 已实现
- ✅ 核心层 (配置、日志、异常、事件)
- ✅ 领域层模型 (Expert, Knowledge, Session)
- ✅ 领域服务接口 (Routing, Retrieval)
- ✅ 基础设施层 (数据库模型、连接、仓储)
- ✅ 基础API框架

### 待实现
- [ ] LLM/Embedding 客户端实现
- [ ] 应用服务 (Chat, Experiment, Training)
- [ ] API路由 (chat, experts, knowledge, experiments)
- [ ] 前端重构 (Vue3 + TypeScript)
- [ ] 测试用例
- [ ] Docker部署配置

## 🔗 V1 迁移指南

1. **数据迁移**: 使用 Alembic 迁移脚本
2. **配置迁移**: .env 文件格式兼容
3. **API兼容**: 保持原有API路径
4. **逐步替换**: 可以 V1/V2 并行运行

---

**架构设计**: 企业级 DDD + 分层架构  
**目标**: 高内聚、低耦合、可测试、可扩展
