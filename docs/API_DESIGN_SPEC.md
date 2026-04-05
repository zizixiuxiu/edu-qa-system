# 📡 EduQA API 设计规范

> RESTful API 设计标准，确保接口一致性、可维护性和可扩展性

---

## 📋 目录

1. [设计原则](#设计原则)
2. [URL 规范](#url-规范)
3. [请求规范](#请求规范)
4. [响应规范](#响应规范)
5. [错误处理](#错误处理)
6. [版本控制](#版本控制)
7. [认证授权](#认证授权)
8. [API 端点定义](#api-端点定义)

---

## 🎯 设计原则

### RESTful 原则

| 原则 | 说明 | 示例 |
|------|------|------|
| **资源导向** | URL 表示资源，而非动作 | `/experts` 而非 `/getExperts` |
| **HTTP 动词** | 使用标准 HTTP 方法 | GET/POST/PUT/DELETE/PATCH |
| **无状态** | 请求自包含，不依赖上下文 | 每个请求带认证信息 |
| **可缓存** | 响应可被缓存 | 使用 Cache-Control 头 |

### 设计哲学

```
┌─────────────────────────────────────────────────────────────┐
│                     API First Design                         │
├─────────────────────────────────────────────────────────────┤
│  1. 消费者驱动 (Consumer-Driven)                             │
│     - 从消费者视角设计API                                    │
│     - 提供清晰的用例和示例                                   │
│                                                              │
│  2. 一致性 (Consistency)                                     │
│     - 统一的命名规范                                         │
│     - 统一的响应格式                                         │
│     - 统一的错误处理                                         │
│                                                              │
│  3. 可演化性 (Evolvability)                                  │
│     - 向后兼容                                               │
│     - 版本控制                                               │
│     - 废弃策略                                               │
│                                                              │
│  4. 可发现性 (Discoverability)                               │
│     - HATEOAS 链接                                           │
│     - 清晰的文档                                             │
│     - OpenAPI 规范                                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔗 URL 规范

### 基本结构

```
https://api.eduqa.io/{version}/{service}/{resource}/{id}?{query_params}

示例:
https://api.eduqa.io/v1/chat/sessions/123?include=messages
```

### 命名规则

```yaml
规范:
  - 使用小写字母
  - 使用连字符 (-) 分隔单词
  - 使用复数名词表示集合
  - 避免动词，使用 HTTP 方法表达动作

正确示例:
  GET    /api/v1/experts              # 获取专家列表
  GET    /api/v1/experts/123          # 获取特定专家
  POST   /api/v1/experts              # 创建专家
  PUT    /api/v1/experts/123          # 更新专家
  DELETE /api/v1/experts/123          # 删除专家
  GET    /api/v1/experts/123/stats    # 获取专家统计

错误示例:
  GET    /api/v1/getExperts           # 包含动词
  GET    /api/v1/expert_list          # 使用下划线
  GET    /api/v1/Expert               # 大写字母
  POST   /api/v1/experts/create       # 冗余动词
```

### 资源层级

```
# 单层资源
/api/v1/experts
/api/v1/knowledges

# 嵌套资源 (表示从属关系)
/api/v1/experts/{expert_id}/knowledges    # 专家的知识
/api/v1/sessions/{session_id}/messages    # 会话的消息

# 动作资源 (特殊情况使用动词)
POST /api/v1/sessions/{id}/send           # 发送消息
POST /api/v1/experts/{id}/route           # 路由问题
POST /api/v1/training/{id}/cancel         # 取消训练
```

### 查询参数

```yaml
# 分页
page:       页码 (默认 1)
page_size:  每页数量 (默认 20, 最大 100)

# 排序
sort:       排序字段 (例如: created_at)
order:      排序方向 (asc/desc)

# 过滤
subject:    学科过滤
status:     状态过滤
start_date: 开始日期
end_date:   结束日期

# 包含关系
include:    关联资源 (例如: messages,expert)
fields:     指定字段 (例如: id,name,subject)

# 示例
GET /api/v1/experts?page=1&page_size=20&subject=数学&sort=created_at&order=desc
GET /api/v1/sessions/123?include=messages,expert&fields=id,status
```

---

## 📤 请求规范

### HTTP 方法使用

| 方法 | 用途 | 幂等性 | 示例 |
|------|------|--------|------|
| GET | 获取资源 | 是 | 获取专家列表 |
| POST | 创建资源 | 否 | 创建新会话 |
| PUT | 全量更新 | 是 | 更新专家信息 |
| PATCH | 部分更新 | 是 | 修改专家状态 |
| DELETE | 删除资源 | 是 | 删除知识 |

### 请求头

```http
# 必需头
Content-Type: application/json
Authorization: Bearer {jwt_token}
X-Request-ID: {uuid}              # 请求追踪ID

# 可选头
Accept: application/json
Accept-Language: zh-CN
X-Client-Version: 1.0.0
X-Experiment-Mode: full_system    # 实验模式
```

### 请求体格式

```json
// POST /api/v1/chat/sessions
{
  "query": "勾股定理是什么？",
  "image": "base64_encoded_image_data",
  "expert_id": 1,
  "session_id": "optional_session_uuid"
}

// PATCH /api/v1/experts/123
{
  "is_active": false,
  "config": {
    "temperature": 0.8
  }
}
```

### 批量操作

```http
# 批量创建
POST /api/v1/knowledges/batch
Content-Type: application/json

{
  "items": [
    {"content": "知识1", "expert_id": 1},
    {"content": "知识2", "expert_id": 1}
  ]
}

# 批量删除
DELETE /api/v1/knowledges/batch
Content-Type: application/json

{
  "ids": [1, 2, 3]
}
```

---

## 📥 响应规范

### 标准响应格式

```json
{
  "code": 200,
  "message": "success",
  "data": { ... },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2026-03-13T10:30:00Z"
  }
}
```

### 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 业务状态码 (HTTP 状态码保持一致) |
| message | string | 状态描述 |
| data | any | 响应数据 |
| meta | object | 元数据 (分页、追踪等) |

### 列表响应

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {"id": 1, "name": "数学专家"},
      {"id": 2, "name": "物理专家"}
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 100,
      "total_pages": 5
    }
  },
  "meta": {
    "request_id": "uuid"
  }
}
```

### 分页元数据

```json
{
  "pagination": {
    "page": 1,              // 当前页码
    "page_size": 20,        // 每页数量
    "total": 100,           // 总记录数
    "total_pages": 5,       // 总页数
    "has_next": true,       // 是否有下一页
    "has_prev": false       // 是否有上一页
  }
}
```

### HATEOAS 链接

```json
{
  "data": {
    "id": 123,
    "name": "数学专家",
    "_links": {
      "self": "/api/v1/experts/123",
      "knowledges": "/api/v1/experts/123/knowledges",
      "stats": "/api/v1/experts/123/stats",
      "update": "/api/v1/experts/123",
      "delete": "/api/v1/experts/123"
    }
  }
}
```

---

## ❌ 错误处理

### 错误响应格式

```json
{
  "code": 400,
  "message": "请求参数错误",
  "error": {
    "type": "ValidationError",
    "code": "E001",
    "detail": {
      "field": "email",
      "message": "无效的邮箱格式"
    },
    "errors": [
      {"field": "email", "message": "无效的邮箱格式"},
      {"field": "age", "message": "年龄必须大于0"}
    ]
  },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2026-03-13T10:30:00Z"
  }
}
```

### HTTP 状态码

| 状态码 | 含义 | 使用场景 |
|--------|------|----------|
| 200 | OK | 成功响应 |
| 201 | Created | 资源创建成功 |
| 204 | No Content | 删除成功，无返回内容 |
| 400 | Bad Request | 请求参数错误 |
| 401 | Unauthorized | 未认证 |
| 403 | Forbidden | 无权限 |
| 404 | Not Found | 资源不存在 |
| 409 | Conflict | 资源冲突 |
| 422 | Unprocessable | 业务逻辑错误 |
| 429 | Too Many Requests | 限流 |
| 500 | Internal Error | 服务器内部错误 |
| 503 | Service Unavailable | 服务不可用 |

### 业务错误码

```python
# shared/errors.py

class ErrorCode:
    # 通用错误 (E001-E099)
    UNKNOWN_ERROR = ("E001", 500, "未知错误")
    INVALID_PARAMETER = ("E002", 400, "参数错误")
    UNAUTHORIZED = ("E003", 401, "未授权")
    FORBIDDEN = ("E004", 403, "禁止访问")
    NOT_FOUND = ("E005", 404, "资源不存在")
    
    # 专家服务错误 (E100-E199)
    EXPERT_NOT_FOUND = ("E100", 404, "专家不存在")
    EXPERT_EXISTS = ("E101", 409, "专家已存在")
    EXPERT_INACTIVE = ("E102", 422, "专家未激活")
    
    # 问答服务错误 (E200-E299)
    SESSION_NOT_FOUND = ("E200", 404, "会话不存在")
    EMPTY_QUERY = ("E201", 400, "查询内容不能为空")
    SUBJECT_NOT_IDENTIFIED = ("E202", 422, "无法识别学科")
    
    # RAG 服务错误 (E300-E399)
    KNOWLEDGE_NOT_FOUND = ("E300", 404, "知识不存在")
    EMBEDDING_FAILED = ("E301", 500, "向量化失败")
    RETRIEVE_FAILED = ("E302", 500, "检索失败")
    
    # 训练服务错误 (E400-E499)
    TRAINING_JOB_NOT_FOUND = ("E400", 404, "训练任务不存在")
    TRAINING_FAILED = ("E401", 500, "训练失败")
    INSUFFICIENT_DATA = ("E402", 422, "训练数据不足")
```

### 错误示例

```json
// 400 Bad Request
{
  "code": 400,
  "message": "请求参数错误",
  "error": {
    "type": "ValidationError",
    "code": "E002",
    "errors": [
      {"field": "query", "message": "查询内容不能为空"},
      {"field": "expert_id", "message": "专家ID必须是正整数"}
    ]
  }
}

// 401 Unauthorized
{
  "code": 401,
  "message": "认证失败",
  "error": {
    "type": "AuthenticationError",
    "code": "E003",
    "detail": "Token已过期"
  }
}

// 429 Rate Limited
{
  "code": 429,
  "message": "请求过于频繁",
  "error": {
    "type": "RateLimitError",
    "code": "E010",
    "detail": "请等待60秒后重试",
    "retry_after": 60
  }
}
```

---

## 📦 版本控制

### URL 版本控制 (推荐)

```
/api/v1/experts
/api/v2/experts
```

### Header 版本控制 (备选)

```http
GET /api/experts
Accept: application/vnd.eduqa.v1+json

# 或
X-API-Version: v1
```

### 版本策略

```yaml
版本规则:
  - 破坏性变更必须升级主版本 (v1 → v2)
  - 新功能添加升级次版本 (v1.1 → v1.2)
  - Bug 修复升级修订版本 (v1.1.0 → v1.1.1)

支持策略:
  - 同时维护两个主版本
  - 旧版本提供 6 个月过渡期
  - 通过 Header 提示版本弃用

弃用通知:
  Deprecation: true
  Sunset: Wed, 13 Sep 2026 00:00:00 GMT
  Link: </api/v2/experts>; rel="successor-version"
```

---

## 🔐 认证授权

### JWT 认证

```http
# 登录获取 Token
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "password"
}

# 响应
{
  "code": 200,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "Bearer",
    "expires_in": 3600
  }
}

# 使用 Token
GET /api/v1/experts
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### 权限控制

```yaml
权限模型: RBAC (Role-Based Access Control)

角色定义:
  - super_admin: 超级管理员
  - admin: 管理员
  - researcher: 研究员
  - user: 普通用户

权限示例:
  experts:read      # 查看专家
  experts:write     # 创建/修改专家
  experts:delete    # 删除专家
  benchmark:run     # 运行基准测试
  training:manage   # 管理训练任务
```

### API Key 认证 (服务间)

```http
GET /api/v1/internal/stats
X-API-Key: internal_service_key_xxx
X-Service-Name: rag-service
```

---

## 📋 API 端点定义

### 聊天服务 (Chat Service)

```yaml
# 发送消息
POST /api/v1/chat/send
Summary: 发送消息并获取回答
Request:
  query: string (required)
  image?: string (base64)
  session_id?: string
  expert_id?: int
Response:
  answer: string
  session_id: string
  expert_name: string
  expert_subject: string
  used_knowledges: KnowledgeItem[]
  response_time: float
  rag_stats: object

# 上传图片
POST /api/v1/chat/upload-image
Content-Type: multipart/form-data
Request:
  file: File (required)
Response:
  filename: string
  url: string
  size: int

# 获取会话列表
GET /api/v1/chat/sessions
Query:
  page?: int (default: 1)
  page_size?: int (default: 20)
  expert_id?: int
Response:
  items: Session[]
  pagination: Pagination

# 获取会话详情
GET /api/v1/chat/sessions/{session_id}
Query:
  include?: string (messages)
Response:
  id: string
  expert: Expert
  messages: Message[]
  created_at: datetime
```

### 专家服务 (Expert Service)

```yaml
# 获取专家列表
GET /api/v1/experts
Query:
  subject?: string
  is_active?: bool
  page?: int
  page_size?: int
  sort?: string
Response:
  items: Expert[]
  pagination: Pagination

# 创建专家
POST /api/v1/experts
Request:
  subject: string (required)
  name?: string
  config?: object
Response:
  id: int
  subject: string
  name: string
  created_at: datetime

# 获取专家详情
GET /api/v1/experts/{expert_id}
Response:
  id: int
  subject: string
  name: string
  model_type: string
  knowledge_count: int
  sft_data_count: int
  total_qa_count: int
  avg_response_time: float
  accuracy_rate: float
  is_active: bool
  created_at: datetime

# 更新专家
PUT /api/v1/experts/{expert_id}
Request:
  name?: string
  config?: object
  is_active?: bool
Response:
  Expert

# 删除专家
DELETE /api/v1/experts/{expert_id}
Response:
  204 No Content

# 获取专家统计
GET /api/v1/experts/{expert_id}/stats
Query:
  start_date?: date
  end_date?: date
Response:
  total_questions: int
  avg_response_time: float
  accuracy_rate: float
  daily_stats: DailyStat[]

# 路由问题到专家
POST /api/v1/experts/route
Request:
  query: string (required)
  image?: string
Response:
  expert_id: int
  expert_name: string
  confidence: float
  alternatives: AlternativeExpert[]
```

### RAG 服务 (RAG Service)

```yaml
# 检索知识
POST /api/v1/rag/retrieve
Request:
  query: string (required)
  expert_id?: int
  top_k?: int (default: 5)
  threshold?: float (default: 0.6)
Response:
  results: RetrievalResult[]
  stats:
    expert_searched: bool
    general_searched: bool
    total_found: int
    query_time_ms: float

# 批量检索
POST /api/v1/rag/batch-retrieve
Request:
  queries: string[] (required)
  expert_id?: int
  top_k?: int
Response:
  items: 
    - query: string
      results: RetrievalResult[]

# 获取检索统计
GET /api/v1/rag/stats
Query:
  expert_id?: int
  start_date?: date
  end_date?: date
Response:
  total_queries: int
  avg_query_time: float
  cache_hit_rate: float
  top_queries: QueryStat[]
```

### 知识服务 (Knowledge Service)

```yaml
# 获取知识列表
GET /api/v1/knowledges
Query:
  expert_id?: int
  source_type?: string
  quality_score_min?: float
  page?: int
  page_size?: int
Response:
  items: Knowledge[]
  pagination: Pagination

# 创建知识
POST /api/v1/knowledges
Request:
  content: string (required)
  expert_id: int (required)
  answer?: string
  source_type?: string (default: "manual")
  metadata?: object
Response:
  id: int
  content: string
  expert_id: int
  quality_score: float
  created_at: datetime

# 批量导入知识
POST /api/v1/knowledges/import
Content-Type: multipart/form-data
Request:
  file: File (json/csv)
  expert_id: int
Response:
  imported_count: int
  failed_count: int
  errors: ImportError[]

# 触发向量化
POST /api/v1/knowledges/{knowledge_id}/embed
Response:
  task_id: string
  status: string

# 执行去重
POST /api/v1/knowledges/deduplicate
Request:
  expert_id?: int
  threshold?: float (default: 0.92)
Response:
  duplicates_found: int
  duplicates_merged: int
```

### 基准测试服务 (Benchmark Service)

```yaml
# 获取数据集统计
GET /api/v1/benchmark/stats
Response:
  total_questions: int
  correct_count: int
  wrong_count: int
  accuracy_rate: float
  avg_score: float
  by_subject: object

# 导入数据集
POST /api/v1/benchmark/import
Request:
  source: string (local/github)
  path?: string
  subject?: string
Response:
  imported_count: int

# 启动基准测试
POST /api/v1/benchmark/start
Request:
  expert_id?: int
  mode: string (all/wrong/random/by_subject)
  subject?: string
  year?: string
Response:
  task_id: string
  status: string
  total: int

# 获取测试进度
GET /api/v1/benchmark/progress
Query:
  task_id: string
Response:
  status: string
  current: int
  total: int
  current_question: string
  elapsed_time: int
  recent_results: BenchmarkResult[]

# 获取测试结果
GET /api/v1/benchmark/results
Query:
  page?: int
  page_size?: int
  filter?: string (all/correct/wrong/low_score)
  subject?: string
Response:
  items: BenchmarkResult[]
  pagination: Pagination

# 生成测试报告
GET /api/v1/benchmark/report
Query:
  expert_id?: int
Response:
  experiment_info: object
  summary: object
  by_subject: object
  by_year: object
  score_distribution: object
  wrong_questions: WrongQuestion[]

# 导出报告
GET /api/v1/benchmark/report/export
Query:
  format: string (json/csv/pdf)
  expert_id?: int
Response:
  download_url: string
  expires_at: datetime
```

### 训练服务 (Training Service)

```yaml
# 创建训练任务
POST /api/v1/training/jobs
Request:
  expert_id: int (required)
  data_count?: int
  epochs?: int (default: 3)
  batch_size?: int (default: 4)
  learning_rate?: float (default: 0.0001)
Response:
  id: int
  expert_id: int
  status: string
  created_at: datetime

# 获取训练任务列表
GET /api/v1/training/jobs
Query:
  expert_id?: int
  status?: string
  page?: int
Response:
  items: TrainingJob[]
  pagination: Pagination

# 获取训练任务详情
GET /api/v1/training/jobs/{job_id}
Response:
  id: int
  expert_id: int
  status: string
  data_count: int
  epochs: int
  current_epoch: int
  loss_history: float[]
  output_path: string
  started_at: datetime
  completed_at: datetime

# 取消训练任务
POST /api/v1/training/jobs/{job_id}/cancel
Response:
  success: bool
  message: string

# 部署模型
POST /api/v1/training/models/{model_id}/deploy
Request:
  expert_id: int
Response:
  success: bool
  deployed_at: datetime
```

### 实验配置服务 (Experiment Service)

```yaml
# 获取实验模式列表
GET /api/v1/experiments/presets
Response:
  presets: 
    - name: string
      description: string
      config: object

# 获取当前配置
GET /api/v1/experiments/config
Response:
  mode: string
  expert_routing: bool
  rag: bool
  self_iteration: bool
  finetune: bool

# 切换实验模式
POST /api/v1/experiments/config
Request:
  preset: string (baseline/rag_only/expert_routing/full_system/...)
Response:
  previous: object
  current: object
  applied_at: datetime

# 导出实验数据
GET /api/v1/experiments/export-data
Query:
  format: string (json/csv)
  start_date?: date
  end_date?: date
Response:
  download_url: string
  expires_at: datetime
```

---

## 📖 OpenAPI 规范

### 生成 OpenAPI 文档

```python
# FastAPI 自动生成
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

app = FastAPI(
    title="EduQA API",
    description="教育问答系统 API 文档",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="EduQA API",
        version="1.0.0",
        description="教育问答系统 API 文档",
        routes=app.routes,
    )
    
    # 添加安全方案
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

---

**文档版本**: v1.0  
**最后更新**: 2026-03-13  
**维护者**: API Team
