# 🏗️ EduQA 微服务架构设计文档

> 从单体架构到微服务的演进方案，实现高可用、高扩展、易维护的系统架构

---

## 📋 目录

1. [架构演进策略](#架构演进策略)
2. [服务拆分方案](#服务拆分方案)
3. [服务通信设计](#服务通信设计)
4. [数据管理策略](#数据管理策略)
5. [部署架构](#部署架构)
6. [服务治理](#服务治理)
7. [迁移路线图](#迁移路线图)

---

## 🔄 架构演进策略

### 演进原则

```
单体架构 → 模块化单体 → 服务化拆分 → 微服务架构
    ↓           ↓            ↓             ↓
  快速迭代    边界清晰     独立部署      弹性伸缩
```

### 演进阶段

| 阶段 | 目标 | 时间 | 风险 |
|------|------|------|------|
| Phase 1 | 模块化重构 | 2周 | 低 |
| Phase 2 | 提取公共服务 | 2周 | 低 |
| Phase 3 | 核心服务拆分 | 4周 | 中 |
| Phase 4 | 完善治理体系 | 持续 | 低 |

---

## 🧩 服务拆分方案

### 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Gateway (Kong/Nginx)                 │
│                    路由 / 限流 / 认证 / 日志                      │
└─────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
┌───────▼──────┐      ┌────────▼────────┐    ┌────────▼────────┐
│  Web Gateway │      │  Mobile Gateway │    │  Admin Gateway  │
│  (Web前端)   │      │  (App/小程序)   │    │  (管理后台)      │
└──────────────┘      └─────────────────┘    └─────────────────┘
                                │
    ┌───────────────────────────┼───────────────────────────┐
    │                           │                           │
┌───▼────────────┐  ┌───────────▼────────┐  ┌───────────────▼──┐
│  业务服务层      │  │     核心服务层      │  │    支撑服务层     │
├────────────────┤  ├────────────────────┤  ├──────────────────┤
│ Chat Service   │  │ Expert Service     │  │ Gateway Service  │
│ Benchmark Svc  │  │ RAG Service        │  │ Auth Service     │
│ Experiment Svc │  │ Iteration Service  │  │ Config Service   │
│ Training Svc   │  │ Knowledge Service  │  │ Monitor Service  │
└────────────────┘  └────────────────────┘  └──────────────────┘
    │                           │                           │
    └───────────────────────────┼───────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────┐
│                      基础设施层                                │
├───────────────────────────────────────────────────────────────┤
│  PostgreSQL │ Redis │ MinIO │ Elasticsearch │ RabbitMQ/Kafka │
└───────────────────────────────────────────────────────────────┘
```

### 服务详细设计

#### 1. API Gateway 服务

```yaml
Service: api-gateway
Responsibility: 统一入口、路由、限流、认证
Technology: Kong / Nginx + Lua / Spring Cloud Gateway
Ports: 
  - 80/443: 外部访问
  - 8001: Admin API
Endpoints:
  - /api/v1/chat/* → chat-service
  - /api/v1/experts/* → expert-service
  - /api/v1/rag/* → rag-service
  - /api/v1/benchmark/* → benchmark-service
Plugins:
  - rate-limiting: 100 req/min per IP
  - jwt: 认证验证
  - cors: 跨域处理
  - prometheus: 指标收集
```

#### 2. 认证服务 (Auth Service)

```yaml
Service: auth-service
Responsibility: 用户认证、授权、Token管理
Technology: FastAPI + PostgreSQL + Redis
Database:
  - auth_users: 用户表
  - auth_tokens: Token记录
  - auth_permissions: 权限表
APIs:
  - POST /auth/login
  - POST /auth/logout
  - POST /auth/refresh
  - GET /auth/verify
  - GET /auth/permissions
Integration:
  - JWT Token (HS256)
  - Refresh Token rotation
  - OAuth2 / LDAP (optional)
```

#### 3. 聊天服务 (Chat Service)

```yaml
Service: chat-service
Responsibility: 问答对话、会话管理、消息处理
Technology: FastAPI + PostgreSQL + WebSocket
Database:
  - chat_sessions: 会话表
  - chat_messages: 消息表
  - chat_history: 历史记录
Events:
  - chat.message.created
  - chat.session.ended
Dependencies:
  - expert-service: 获取专家信息
  - rag-service: 知识检索
  - vl-service: 图片识别
Communication:
  - HTTP: 同步调用
  - WebSocket: 实时推送
Scaling:
  - Stateless
  - WebSocket sticky session
```

#### 4. 专家服务 (Expert Service)

```yaml
Service: expert-service
Responsibility: 专家管理、学科路由、专家配置
Technology: FastAPI + PostgreSQL
Database:
  - experts: 专家表
  - expert_configs: 配置表
  - expert_stats: 统计表
APIs:
  - CRUD /experts
  - POST /experts/{id}/route
  - GET /experts/{id}/stats
  - POST /experts/{id}/upgrade
Events:
  - expert.created
  - expert.updated
  - expert.model.upgraded
Cache:
  - Redis: 专家信息缓存 (TTL: 5min)
```

#### 5. RAG 检索服务 (RAG Service)

```yaml
Service: rag-service
Responsibility: 向量检索、知识检索、检索策略
Technology: FastAPI + pgvector / Milvus + Redis
Storage:
  - Vector DB: 向量存储 (384维)
  - Redis: 检索缓存
Components:
  - Embedding Service: 文本向量化
  - Retrieval Engine: 多级检索
  - Reranker: 结果重排序
APIs:
  - POST /rag/retrieve
  - POST /rag/batch-retrieve
  - GET /rag/stats
Performance:
  - P99 < 200ms
  - Cache Hit Rate > 80%
Scaling:
  - Vector DB 水平分片
  - 只读副本扩展
```

#### 6. 知识服务 (Knowledge Service)

```yaml
Service: knowledge-service
Responsibility: 知识库管理、知识点CRUD、向量化
Technology: FastAPI + PostgreSQL + Celery
Database:
  - knowledges: 知识表
  - knowledge_categories: 分类表
  - knowledge_embeddings: 向量表
Async Tasks:
  - knowledge.embed: 向量化任务
  - knowledge.deduplicate: 去重任务
APIs:
  - CRUD /knowledges
  - POST /knowledges/import
  - POST /knowledges/{id}/embed
  - POST /knowledges/deduplicate
Events:
  - knowledge.created
  - knowledge.embedded
  - knowledge.duplicate_detected
```

#### 7. 自我迭代服务 (Iteration Service)

```yaml
Service: iteration-service
Responsibility: 质量检查、知识提取、数据生成
Technology: FastAPI + Celery + PostgreSQL
Workflow:
  - Quality Check → Knowledge Extract → SFT Generate
Database:
  - iteration_queue: 任务队列
  - iteration_results: 结果表
  - sft_datasets: 微调数据
Integrations:
  - Cloud API: 质量检查
  - knowledge-service: 知识入库
  - training-service: 触发训练
Events:
  - iteration.quality_checked
  - iteration.knowledge_extracted
  - iteration.sft_generated
```

#### 8. 基准测试服务 (Benchmark Service)

```yaml
Service: benchmark-service
Responsibility: 测试集管理、批量测试、报告生成
Technology: FastAPI + PostgreSQL + Celery
Database:
  - benchmark_datasets: 数据集
  - benchmark_results: 结果
  - benchmark_reports: 报告
Features:
  - 批量测试执行
  - 进度实时监控
  - 对比分析报告
APIs:
  - POST /benchmark/start
  - GET /benchmark/progress
  - GET /benchmark/report
  - POST /benchmark/compare
Events:
  - benchmark.started
  - benchmark.completed
```

#### 9. 训练服务 (Training Service)

```yaml
Service: training-service
Responsibility: 微调训练、模型管理、LoRA适配
Technology: FastAPI + PyTorch + Celery + MinIO
Storage:
  - MinIO: 模型权重存储
  - PostgreSQL: 任务记录
Components:
  - Training Worker: 训练执行
  - Model Registry: 模型版本
  - LoRA Manager: 适配器管理
APIs:
  - POST /training/jobs
  - GET /training/jobs/{id}/status
  - POST /models/{id}/deploy
  - GET /models/versions
Resources:
  - GPU: NVIDIA A100 / V100
  - CPU: 高内存实例
Scaling:
  - K8s GPU operator
  - 训练任务队列
```

#### 10. 视觉语言服务 (VL Service)

```yaml
Service: vl-service
Responsibility: 图片识别、学科分类、OCR
Technology: FastAPI + Transformers + vLLM
Models:
  - Qwen3-VL-4B: 视觉语言理解
  - PaddleOCR: 文字识别
APIs:
  - POST /vl/classify
  - POST /vl/ocr
  - POST /vl/analyze
Performance:
  - 模型预热
  - Batch推理优化
  - GPU显存管理
```

#### 11. 配置服务 (Config Service)

```yaml
Service: config-service
Responsibility: 配置管理、实验模式、动态配置
Technology: FastAPI + etcd / Consul
Features:
  - 配置版本控制
  - 灰度发布
  - 实时推送
APIs:
  - GET /config/{service}
  - POST /config/{service}
  - PUT /config/{service}/experiment
Events:
  - config.updated
Integration:
  - 配置变更监听
  - 热更新支持
```

#### 12. 监控服务 (Monitor Service)

```yaml
Service: monitor-service
Responsibility: 指标收集、日志聚合、告警管理
Technology: Prometheus + Grafana + ELK + Jaeger
Components:
  - Metrics: Prometheus
  - Logging: ELK Stack
  - Tracing: Jaeger
  - Alerting: AlertManager
Dashboards:
  - 系统大盘
  - 业务指标
  - 服务拓扑
Alerts:
  - 高错误率
  - 响应时间异常
  - 服务不可用
```

---

## 🌐 服务通信设计

### 通信方式选择

| 场景 | 协议 | 原因 |
|------|------|------|
| 同步调用 | HTTP/REST | 简单、易调试 |
| 异步通知 | RabbitMQ | 可靠、支持重试 |
| 实时推送 | WebSocket | 双向通信 |
| 流式数据 | gRPC | 高性能、类型安全 |

### 事件总线设计

```
┌─────────────────────────────────────────────────────┐
│                  Message Broker                      │
│                 (RabbitMQ / Kafka)                   │
└─────────────────────────────────────────────────────┘
         │                      │
    ┌────▼────┐            ┌────▼────┐
    │ Exchange│            │ Exchange│
    │  events │            │  tasks  │
    └───┬─────┘            └───┬─────┘
        │                      │
   ┌────┴────┐            ┌────┴────┐
   ▼         ▼            ▼         ▼
┌──────┐  ┌──────┐    ┌──────┐  ┌──────┐
│Queue1│  │Queue2│    │Queue1│  │Queue2│
│chat.*│  │rag.* │    │embed │  │train │
└──────┘  └──────┘    └──────┘  └──────┘
```

### 事件定义示例

```python
# shared/events.py

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class DomainEvent:
    """领域事件基类"""
    event_id: str
    event_type: str
    timestamp: datetime
    aggregate_id: str
    payload: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ChatMessageCreated(DomainEvent):
    """聊天消息创建事件"""
    session_id: str
    expert_id: int
    query: str
    response_time_ms: float


@dataclass
class KnowledgeEmbedded(DomainEvent):
    """知识向量化完成事件"""
    knowledge_id: int
    expert_id: int
    embedding_model: str
    vector_dimension: int


@dataclass
class ExpertModelUpgraded(DomainEvent):
    """专家模型升级事件"""
    expert_id: int
    old_model_version: str
    new_model_version: str
    lora_path: str
```

---

## 💾 数据管理策略

### 数据库拆分

| 服务 | 数据库 | 数据 |
|------|--------|------|
| auth-service | auth_db | 用户、权限 |
| chat-service | chat_db | 会话、消息 |
| expert-service | expert_db | 专家、配置 |
| knowledge-service | knowledge_db | 知识、分类 |
| benchmark-service | benchmark_db | 数据集、结果 |
| iteration-service | iteration_db | 任务、SFT数据 |
| training-service | training_db | 训练任务、模型版本 |

### 共享数据策略

```
┌────────────────────────────────────────────────────┐
│              共享数据 (通过事件同步)                  │
├────────────────────────────────────────────────────┤
│  experts (只读副本)                                │
│  - chat-service: 获取专家信息                       │
│  - rag-service: 专家知识库路由                      │
├────────────────────────────────────────────────────┤
│  knowledges (通过事件同步)                          │
│  - knowledge-service: 主写                         │
│  - rag-service: 向量索引                           │
└────────────────────────────────────────────────────┘
```

### 分布式事务

使用 **Saga 模式**处理分布式事务：

```python
# 创建知识并触发向量化 (Saga 示例)

class CreateKnowledgeSaga:
    """创建知识 Saga 协调器"""
    
    def __init__(self):
        self.steps = []
        self.compensations = []
    
    async def execute(self, knowledge_data: dict):
        try:
            # Step 1: 创建知识记录
            knowledge = await knowledge_service.create(knowledge_data)
            self.compensations.append(
                lambda: knowledge_service.delete(knowledge.id)
            )
            
            # Step 2: 向量化
            embedding = await embedding_service.embed(knowledge.content)
            self.compensations.append(
                lambda: embedding_service.delete(knowledge.id)
            )
            
            # Step 3: 更新向量索引
            await rag_service.update_index(knowledge.id, embedding)
            
            return knowledge
            
        except Exception as e:
            # 执行补偿
            for compensation in reversed(self.compensations):
                try:
                    await compensation()
                except:
                    # 记录补偿失败，人工介入
                    await alert_service.notify(
                        f"Compensation failed: {knowledge.id}"
                    )
            raise
```

---

## 🚀 部署架构

### Kubernetes 部署拓扑

```
┌─────────────────────────────────────────────────────────────────┐
│                        Kubernetes Cluster                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                      Ingress Controller                    │  │
│  │                    (Nginx / Traefik)                       │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────┼───────────────────────────────┐  │
│  │                           │                               │  │
│  ▼                           ▼                               ▼  │
│ ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐│
│ │ api-gateway  │    │  web-static  │    │  websocket-ingress   ││
│ │  3 replicas  │    │   (Nginx)    │    │     (Socket.IO)      ││
│ └──────────────┘    └──────────────┘    └──────────────────────┘│
│                              │                                   │
│  ┌───────────────────────────┼───────────────────────────────┐  │
│  │                           │                               │  │
│  ▼                           ▼                               ▼  │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐│
│ │  chat    │ │  expert  │ │   rag    │ │ knowledge│ │ benchmark││
│ │  svc     │ │  svc     │ │  svc     │ │  svc     │ │  svc     ││
│ │2 replicas│ │2 replicas│ │3 replicas│ │2 replicas│ │1 replica ││
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘│
│                              │                                   │
│  ┌───────────────────────────┼───────────────────────────────┐  │
│  │                           │                               │  │
│  ▼                           ▼                               ▼  │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐│
│ │ PostgreSQL│ │  Redis   │ │  MinIO   │ │RabbitMQ  │ │Prometheus││
│ │  Primary │ │ Cluster  │ │  Object  │ │  Queue   │ │  +       │
│ │ + Replica│ │          │ │  Storage │ │          │ │ Grafana  ││
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### Helm Chart 结构

```
helm-charts/
├── eduqa/
│   ├── Chart.yaml
│   ├── values.yaml
│   ├── values-production.yaml
│   └── templates/
│       ├── _helpers.tpl
│       ├── ingress.yaml
│       ├── services/
│       │   ├── api-gateway.yaml
│       │   ├── chat-service.yaml
│       │   ├── expert-service.yaml
│       │   ├── rag-service.yaml
│       │   └── ...
│       ├── databases/
│       │   ├── postgres.yaml
│       │   ├── redis.yaml
│       │   └── rabbitmq.yaml
│       └── monitoring/
│           ├── prometheus.yaml
│           └── grafana.yaml
```

---

## 🎛️ 服务治理

### 服务注册与发现

```yaml
# Consul / Eureka 配置
consul:
  host: consul-server
  port: 8500
  
service:
  name: chat-service
  tags:
    - v1
    - python
  port: 8000
  health_check:
    interval: 10s
    timeout: 5s
    path: /health
```

### 熔断与限流

```python
# 使用 circuitbreaker 库

from circuitbreaker import circuit
import redis

# Redis 限流器
rate_limiter = redis.Redis(host='redis')

def check_rate_limit(user_id: str, max_requests: int = 100, window: int = 60):
    """滑动窗口限流"""
    key = f"rate_limit:{user_id}"
    current = rate_limiter.get(key)
    
    if current and int(current) >= max_requests:
        raise RateLimitExceeded()
    
    pipe = rate_limiter.pipeline()
    pipe.incr(key)
    pipe.expire(key, window)
    pipe.execute()

# 熔断器
@circuit(failure_threshold=5, recovery_timeout=60, expected_exception=Exception)
async def call_external_api(params: dict):
    """外部API调用（带熔断）"""
    async with httpx.AsyncClient() as client:
        response = await client.post("https://api.external.com", json=params)
        response.raise_for_status()
        return response.json()
```

### 链路追踪

```python
# OpenTelemetry 集成

from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

# 配置
provider = TracerProvider()
jaeger_exporter = JaegerExporter(
    agent_host_name="jaeger-agent",
    agent_port=6831,
)
provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
trace.set_tracer_provider(provider)

# 应用
app = FastAPI()
FastAPIInstrumentor.instrument_app(app)

# 自定义Span
@app.get("/api/v1/chat/send")
async def send_message(request: ChatRequest):
    tracer = trace.get_tracer(__name__)
    
    with tracer.start_as_current_span("chat.send") as span:
        span.set_attribute("user.id", request.user_id)
        span.set_attribute("expert.id", request.expert_id)
        
        with tracer.start_as_current_span("rag.retrieve"):
            knowledges = await rag_service.retrieve(request.query)
            span.set_attribute("knowledge.count", len(knowledges))
        
        with tracer.start_as_current_span("llm.generate"):
            answer = await llm_service.generate(request.query, knowledges)
        
        return {"answer": answer}
```

---

## 🗺️ 迁移路线图

### Phase 1: 模块化重构 (Week 1-2)

```
目标: 在单体应用内划分清晰模块边界

Tasks:
  - [ ] 创建清晰的目录结构
  - [ ] 提取共享组件 (events, models, utils)
  - [ ] 定义模块间接口
  - [ ] 消除循环依赖
  
Success Criteria:
  - 模块间依赖图无循环
  - 每个模块有明确职责
  - 单元测试覆盖率 > 80%
```

### Phase 2: 公共服务提取 (Week 3-4)

```
目标: 将通用能力提取为独立服务

Services to Extract:
  1. Auth Service
     - 用户认证逻辑抽离
     - JWT 验证中间件
     
  2. Config Service
     - 配置集中管理
     - 动态配置推送
     
  3. Monitor Service
     - 指标收集
     - 日志聚合

Migration Strategy:
  - 双写模式 (Dual-write)
  - 逐步切流
  - 回滚预案
```

### Phase 3: 核心服务拆分 (Week 5-8)

```
目标: 拆分业务服务

Services:
  1. Chat Service
     - 会话管理
     - 消息处理
     
  2. Expert Service
     - 专家管理
     - 学科路由
     
  3. RAG Service
     - 向量检索
     - 知识检索
     
  4. Knowledge Service
     - 知识库管理
     - 向量化任务

Database Migration:
  - 按服务拆分数据库
  - 数据同步策略
  - 一致性保证
```

### Phase 4: 完善治理 (Week 9+)

```
目标: 建立完整的服务治理体系

Tasks:
  - [ ] 完善监控告警
  - [ ] 优化自动扩缩容
  - [ ] 完善 CI/CD 流水线
  - [ ] 编写运维手册
  - [ ] 灾难恢复演练
```

---

## 📊 成本估算

### 基础设施成本 (月度)

| 资源 | 规格 | 数量 | 单价 | 月度成本 |
|------|------|------|------|----------|
| K8s Node | 4C8G | 6 | ¥400 | ¥2,400 |
| GPU Node | V100 | 2 | ¥3,000 | ¥6,000 |
| PostgreSQL | 4C16G | 2 | ¥800 | ¥1,600 |
| Redis | 2C4G | 2 | ¥300 | ¥600 |
| Object Storage | 1TB | 1 | ¥100 | ¥100 |
| Load Balancer | - | 1 | ¥200 | ¥200 |
| **总计** | | | | **¥10,900** |

### 人力成本

| 角色 | 人数 | 周期 | 投入 |
|------|------|------|------|
| 架构师 | 1 | 8周 | 全职 |
| 后端开发 | 2 | 8周 | 全职 |
| DevOps | 1 | 4周 | 全职 |
| 测试 | 1 | 4周 | 兼职 |

---

**文档版本**: v1.0  
**最后更新**: 2026-03-13  
**架构师**: AI Code Assistant
