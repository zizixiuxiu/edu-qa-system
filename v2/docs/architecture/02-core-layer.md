# 核心层 (Core Layer) 设计

## 1. 配置管理

### 1.1 配置分层
```python
# 配置继承层次
BaseConfig (通用配置)
    ├── DevelopmentConfig (开发)
    ├── TestingConfig (测试)
    └── ProductionConfig (生产)
```

### 1.2 环境变量
| 变量 | 说明 | 默认值 |
|------|------|--------|
| `APP_ENV` | 环境标识 | `development` |
| `DEBUG` | 调试模式 | `True` |
| `DATABASE_URL` | 数据库连接 | - |
| `REDIS_URL` | 缓存连接 | - |
| `LLM_BASE_URL` | LLM API地址 | `http://localhost:1234/v1` |
| `VL_MODEL` | 视觉模型 | `qwen/qwen3-vl-4b` |
| `EMBEDDING_MODEL` | Embedding模型 | `BAAI/bge-small-zh-v1.5` |

## 2. 异常体系

### 2.1 异常层次
```
EduQAException (基类)
├── DomainException (领域异常)
│   ├── ExpertNotFoundError
│   ├── KnowledgeNotFoundError
│   ├── RoutingFailedError
│   └── InvalidAnswerError
├── ApplicationException (应用异常)
│   ├── ValidationError
│   ├── UnauthorizedError
│   └── RateLimitError
└── InfrastructureException (基础设施异常)
    ├── DatabaseError
    ├── LLMServiceError
    └── EmbeddingServiceError
```

### 2.2 异常处理原则
- 领域异常：业务逻辑错误，返回 400/422
- 应用异常：权限/限流等，返回 401/429
- 基础设施异常：系统错误，返回 500

## 3. 日志系统

### 3.1 日志格式
```json
{
  "timestamp": "2026-04-07T10:30:00Z",
  "level": "info",
  "logger": "edu_qa.chat_service",
  "message": "Question processed",
  "context": {
    "session_id": "sess_123",
    "expert_id": 1,
    "latency_ms": 1200
  },
  "trace_id": "trace_abc123"
}
```

### 3.2 日志级别
- **DEBUG**: 开发调试信息
- **INFO**: 业务流程记录
- **WARNING**: 潜在问题
- **ERROR**: 错误但可恢复
- **CRITICAL**: 系统级错误

## 4. 事件总线

### 4.1 领域事件
```python
# 定义领域事件
@dataclass
class KnowledgeCreated(DomainEvent):
    knowledge_id: int
    expert_id: int
    created_at: datetime

@dataclass
class QualityCheckCompleted(DomainEvent):
    session_id: str
    score: float
    is_passed: bool
```

### 4.2 事件处理
- 异步事件处理器
- 支持事件持久化
- 失败重试机制

## 5. DI容器

### 5.1 容器配置
```python
class Container(containers.DeclarativeContainer):
    # 配置
    config = providers.Configuration()
    
    # 基础设施
    db = providers.Singleton(Database, config.DATABASE_URL)
    cache = providers.Singleton(CacheManager, config.REDIS_URL)
    llm = providers.Singleton(LLMClient, config.LLM_BASE_URL)
    
    # 仓储
    expert_repo = providers.Factory(ExpertRepository, db=db)
    knowledge_repo = providers.Factory(KnowledgeRepository, db=db)
    
    # 领域服务
    routing_service = providers.Factory(RoutingService, llm=llm)
    retrieval_service = providers.Factory(RetrievalService, cache=cache)
    
    # 应用服务
    chat_service = providers.Factory(
        ChatApplicationService,
        expert_repo=expert_repo,
        knowledge_repo=knowledge_repo,
        routing_service=routing_service,
    )
```
