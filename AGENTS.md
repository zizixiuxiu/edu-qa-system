# EduQA System - 开发注意事项

本文档记录开发过程中遇到的常见错误和最佳实践，供后续开发参考。

## 🔴 关键错误防范清单

### 1. 数据库模型与表结构同步

#### 问题描述
- **错误**: `column "xxx" does not exist` 或 `null value in column "xxx" violates not-null constraint`
- **场景**: 修改了 SQLModel 模型，但没有同步更新数据库表结构

#### 检查清单
- [ ] 新增字段时，确认是否需要数据库迁移
- [ ] 删除字段时，确认数据库表是否还有该列
- [ ] 修改字段约束时（如 nullable），检查现有数据兼容性

#### 快速诊断脚本
```python
# 检查模型与数据库表结构是否一致
from sqlalchemy import create_engine, inspect
engine = create_engine('postgresql+psycopg2://postgres:password@localhost:15432/edu_qa')
inspector = inspect(engine)
columns = inspector.get_columns('table_name')
for col in columns:
    print(f"{col['name']}: {col['type']} (nullable={col['nullable']})")
```

#### 解决方案
1. **开发环境**: 直接删除表让 SQLModel 自动重建（会丢失数据）
2. **生产环境**: 使用 Alembic 进行数据库迁移
3. **临时方案**: 注释掉模型中不存在的字段

---

### 2. API 响应格式统一

#### 问题描述
- **错误**: 前端无法解析响应数据，或收到 500 错误
- **场景**: API 函数直接返回 dict 而不是 ResponseBase

#### 标准格式
```python
from app.models.schemas import ResponseBase

# ✅ 正确
return ResponseBase(data={"items": [], "total": 0})

# ❌ 错误
return {"items": [], "total": 0}
```

#### 检查清单
- [ ] 所有 API 函数返回 ResponseBase
- [ ] 导入 ResponseBase（容易遗漏）
- [ ] 错误处理也使用 ResponseBase: `ResponseBase(code=500, message=str(e), data={})`

---

### 3. SQL 查询字段验证

#### 问题描述
- **错误**: `column "xxx" does not exist`
- **场景**: SQL 语句中引用了数据库表中没有的字段

#### 检查清单
- [ ] 手写 SQL 时，先确认字段存在（使用诊断脚本）
- [ ] 避免使用模型中有但数据库中没有的字段
- [ ] 使用 SQLAlchemy ORM 查询代替手写 SQL 可减少此类错误

#### 示例
```python
# ❌ 错误 - 假设 additional_score 字段存在
sql = """
    SELECT s.id, s.additional_score  -- 可能不存在
    FROM sessions s
"""

# ✅ 正确 - 先验证字段存在
# 或直接使用 ORM
result = await session.execute(select(Session.id, Session.overall_score))
```

---

### 4. 数据库连接配置

#### 问题描述
- **错误**: `Connection refused` 或连接超时
- **场景**: 数据库端口、主机或凭据配置错误

#### 配置检查
```python
# backend/app/core/config.py
DATABASE_URL: str = "postgresql://postgres:password@localhost:15432/edu_qa"
# 注意端口：Docker PostgreSQL 使用 15432，本地安装使用 5432
```

#### 检查清单
- [ ] 确认 PostgreSQL 服务运行在哪个端口
- [ ] Docker 环境: `docker ps | findstr postgres`
- [ ] 本地环境: 检查服务状态

---

### 5. 前端数据解析

#### 问题描述
- **错误**: 页面显示 "No Data" 或数据 undefined
- **场景**: API 返回的数据结构是 `{code: 200, data: {...}}`，但前端直接访问了 `res.items`

#### 标准处理
```typescript
// ❌ 错误 - 假设 res 直接包含数据
const items = res.items

// ✅ 正确 - 处理嵌套结构
const data = res.data || res  // 兼容两种格式
const items = data.items || []
```

#### 检查清单
- [ ] 查看后端 API 实际返回格式
- [ ] 使用浏览器 DevTools Network 面板验证响应
- [ ] 处理可能的 null/undefined 值

---

### 6. 知识库内容精简策略

#### 问题描述
- **错误**: 入库的知识内容质量太差，缺少关键信息
- **场景**: 过度精简导致 `content` 字段丢失重要内容

#### 解决方案
**原则：质量优先，精简次之**

```python
# ❗错误做法 - 过度精简
content = search_content[:200]  # 只保留200字，质量下降

# ✅正确做法 - 保存完整高质量内容
content = corrected_answer  # 完整答案，保证质量

# embedding可以基于摘要生成，但存储要完整
embedding = embedding_service.encode(
    f"问题：{question}\n答案：{answer[:500]}"  # 检索上下文可精简
)
```

#### 检查清单
- [ ] `content` 字段存储完整高质量回答
- [ ] `meta_data` 保存原始问题和完整答案
- [ ] `embedding` 基于检索上下文生成（可精简）
- [ ] 确保入库内容在前端展示时完整可读

---

### 7. CORS 跨域请求失败

#### 问题描述
- **错误**: `Access to XMLHttpRequest at '...' from origin '...' has been blocked by CORS policy`
- **场景**: 前端请求被浏览器阻止，因为后端没有返回正确的 CORS 头

#### 解决方案
在 `backend/app/main.py` 中添加全局 CORS 处理：

```python
# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# 全局处理 OPTIONS 请求（预检请求）
from fastapi.responses import Response

@app.options("/{full_path:path}")
async def preflight_handler(full_path: str):
    response = Response(status_code=200)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Max-Age"] = "3600"
    return response

@app.middleware("http")
async def add_cors_headers(request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response
```

#### 检查清单
- [ ] 确认 `allow_origins` 包含前端地址
- [ ] 确认 `OPTIONS` 请求被正确处理
- [ ] 使用浏览器 DevTools 查看响应头

---

### 8. 服务启动顺序

#### 问题描述
- **错误**: API 请求超时或无响应
- **场景**: 后端服务未完全启动就进行测试

#### 推荐启动流程
```bash
# 1. 确保 PostgreSQL 运行
docker ps | findstr postgres

# 2. 启动后端（等待 "Application startup complete"）
python start_backend.py

# 3. 测试 API
 curl http://localhost:8000/api/v1/experts/list

# 4. 启动前端
cd frontend && npm run dev
```

---

### 9. Python 导入路径

#### 问题描述
- **错误**: `ModuleNotFoundError: No module named 'app'`
- **场景**: 在根目录运行脚本时路径问题

#### 解决方案
```python
# 在脚本开头添加
import sys
sys.path.insert(0, 'backend')
# 或
sys.path.insert(0, '.')  # 如果在 backend 目录
```

---

## 🟡 警告和最佳实践

### 模型定义
```python
class MyModel(SQLModel, table=True):
    # 始终设置默认值
    status: str = Field(default="pending")
    count: int = Field(default=0)
    
    # 可选字段使用 Optional
    description: Optional[str] = None
    
    # 外键字段始终设置索引
    expert_id: int = Field(foreign_key="experts.id", index=True)
```

### API 路由
```python
@router.get("/items", response_model=ResponseBase)
async def get_items(
    session: AsyncSession = Depends(get_session)
) -> ResponseBase:
    try:
        # 业务逻辑
        return ResponseBase(data=result)
    except Exception as e:
        # 始终返回统一格式
        return ResponseBase(code=500, message=str(e), data=None)
```

### 前端 API 调用
```typescript
const res: any = await api.get('/endpoint')
if (res.code === 200) {
    const data = res.data || {}
    // 处理数据
} else {
    ElMessage.error(res.message || '请求失败')
}
```

---

## 🔧 常用调试命令

```powershell
# 检查 Python 进程
tasklist | findstr python

# 强制结束所有 Python 进程
taskkill /F /IM python.exe

# 检查端口占用
netstat -ano | findstr 8000

# 检查数据库表结构
python check_db.py

# 测试 API
 curl http://localhost:8000/api/v1/experiments/dashboard

# 构建前端
cd frontend && npx vite build
```


## 📋 代码审查检查表

提交代码前检查：

- [ ] 新增/修改的模型字段是否已同步到数据库
- [ ] API 是否返回统一的 ResponseBase 格式
- [ ] 所有导入是否已添加
- [ ] 手写 SQL 的字段是否存在于数据库
- [ ] 前端是否正确处理 API 响应结构
- [ ] 配置（特别是数据库 URL）是否正确


- [ ] 知识库 content 是否保存完整高质量内容（非精简版）


---

### 10. 实验队列无限循环 Bug（2026-04-05）

#### 问题描述
- **错误**: 实验进度条在切换实验时无限循环跳动，系统卡在"实验完成"状态
- **场景**: 一键运行6组实验时，FullSystem实验完成后切换到下一个实验时卡住
- **根本原因**: 多层次的竞态条件和状态污染
  1. **后端**: 自动入库操作阻塞了实验完成通知
  2. **前端**: `loadQueue()` 替换整个 `currentRunningExperiment` 对象，导致状态引用丢失
  3. **全局状态**: 新实验启动时立即重置 `current_test_task`，覆盖了完成状态

#### 修复方案（多层防御）

**1. 后端: 异步自动入库**
```python
# ✅ 正确 - 后台异步执行，不阻塞实验流程
if enable_iteration:
    async def background_auto_add():
        await auto_add_wrong_answers_to_knowledge(session, expert_id)
    
    # 启动后台任务，不等待完成
    asyncio.create_task(background_auto_add())
```

**2. 前端: 保持对象引用（关键）**
```typescript
// ✅ 正确 - 只更新字段，不替换整个对象
const loadQueue = async () => {
  const currentId = currentRunningExperiment.value?.id
  experimentQueue.value = res.queue
  
  if (currentId && currentRunningExperiment.value) {
    const updatedRunning = experimentQueue.value.find(e => e.id === currentId)
    if (updatedRunning) {
      // 只更新状态字段，保持对象引用不变！
      currentRunningExperiment.value.status = updatedRunning.status
      currentRunningExperiment.value.progress = updatedRunning.progress
      // 不要替换整个对象！
    }
  }
}
```

**3. 前端: 防重入锁**
```typescript
let isSwitchingExperiment = false
let completedExperimentIds = new Set<string>()

const startPolling = () => {
  pollTimer = window.setInterval(async () => {
    // 防重入锁
    if (isSwitchingExperiment) return
    // 去重检查
    if (completedExperimentIds.has(currentExp.id)) return
    
    isSwitchingExperiment = true
    try {
      // 处理实验切换...
    } finally {
      isSwitchingExperiment = false
    }
  }, 2000)
}
```

**4. 默认参数: 禁用迭代**
```python
class StartTestRequest(BaseModel):
    enable_iteration: bool = False  # 默认禁用，防止意外启用

async def run_benchmark_test(
    # ...
    enable_iteration: bool = False  # 必须显式启用
):
```

#### 检查清单
- [ ] 后台耗时操作使用 `asyncio.create_task()` 异步执行
- [ ] 前端状态更新时保持对象引用（使用 `Object.assign` 或字段赋值）
- [ ] 添加防重入锁防止竞态条件
- [ ] 使用集合(Set)进行完成去重
- [ ] 危险功能（如自动入库）默认禁用

#### 调试技巧
```typescript
// 添加详细日志追踪状态变化
console.log(`[Experiment] 轮询: 实验 ${currentExp.id} 已完成，准备切换`)
console.log(`[Experiment] 下一个实验:`, runningExp?.name)

// 检查对象引用
console.log('currentRunningExperiment === runningExp:', 
  currentRunningExperiment.value === runningExp)
```

---

*最后更新: 2026-04-05*


