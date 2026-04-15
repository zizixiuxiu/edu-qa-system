# Tier 0 本地迭代知识库 + 自动入库功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现完整的 Tier 0 本地迭代知识库，支持云端质检后自动入库（质量≥4.0），包含三级检索架构（Tier 0/1/2）

**Architecture:** 新增独立 tier0_knowledge 表（PostgreSQL + pgvector），异步自动入库流程，两级去重机制（SimHash快速去重 + 向量相似度精确去重），检索时按权重(0.5, 0.3, 0.2)融合三级结果

**Tech Stack:** FastAPI, SQLModel, PostgreSQL, pgvector, BGE-Small embedding, asyncio

---

## 文件结构映射

| 文件 | 责任 | 操作 |
|-----|------|-----|
| `backend/app/models/database.py` | 新增 Tier0Knowledge 模型，补充 Session 字段 | 修改 |
| `backend/app/services/tier0/tier0_ingest_service.py` | 自动入库核心逻辑，去重检查 | 创建 |
| `backend/app/services/tier0/__init__.py` | 服务导出 | 创建 |
| `backend/app/services/rag/multi_tier_retrieval.py` | 集成 Tier 0 检索，三级融合 | 修改 |
| `backend/app/api/chat.py` | 触发自动入库的异步流程 | 修改 |
| `backend/app/api/tier0.py` | Tier 0 管理 API | 创建 |
| `backend/app/main.py` | 注册新路由 | 修改 |
| `backend/migrations/create_tier0_table.py` | 数据库迁移脚本 | 创建 |
| `backend/tests/test_tier0_ingest.py` | 入库服务单元测试 | 创建 |

---

## 前置准备

### Task 0: 确认开发环境

**检查清单：**
- [ ] PostgreSQL 运行正常，pgvector 扩展已安装
- [ ] 后端虚拟环境已激活
- [ ] 现有数据库有备份（或可在需要时重建）

---

## Phase 1: 数据库层

### Task 1: 创建数据库迁移脚本

**Files:**
- Create: `backend/migrations/create_tier0_table.py`

- [ ] **Step 1: 编写迁移脚本**

```python
"""
数据库迁移脚本：创建 tier0_knowledge 表，补充 sessions 字段
"""

from sqlalchemy import create_engine, text
import sys
import os

# 添加backend到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def migrate():
    # 数据库连接
    DATABASE_URL = "postgresql://postgres:password@localhost:15432/edu_qa"
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        print("🔄 开始数据库迁移...")
        
        # 1. 创建 tier0_knowledge 表
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS tier0_knowledge (
                id SERIAL PRIMARY KEY,
                expert_id INTEGER NOT NULL REFERENCES experts(id) ON DELETE CASCADE,
                content TEXT NOT NULL,
                embedding VECTOR(384),
                metadata JSONB DEFAULT '{}',
                quality_score FLOAT NOT NULL,
                accuracy_score FLOAT,
                completeness_score FLOAT,
                educational_score FLOAT,
                additional_score FLOAT,
                dedup_hash VARCHAR(64),
                usage_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        print("✅ tier0_knowledge 表创建成功")
        
        # 2. 创建索引
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_tier0_expert_id ON tier0_knowledge(expert_id);
            CREATE INDEX IF NOT EXISTS idx_tier0_quality_score ON tier0_knowledge(quality_score);
            CREATE INDEX IF NOT EXISTS idx_tier0_dedup_hash ON tier0_knowledge(dedup_hash);
            CREATE INDEX IF NOT EXISTS idx_tier0_created_at ON tier0_knowledge(created_at DESC);
        """))
        print("✅ 基础索引创建成功")
        
        # 3. 创建 pgvector 索引（如果数据量小，可以后续再创建）
        try:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_tier0_embedding ON tier0_knowledge 
                USING ivfflat (embedding vector_cosine_ops) 
                WITH (lists = 100);
            """))
            print("✅ 向量索引创建成功")
        except Exception as e:
            print(f"⚠️ 向量索引创建失败（数据量可能太小）: {e}")
        
        # 4. 补充 sessions 表字段
        conn.execute(text("""
            ALTER TABLE sessions 
            ADD COLUMN IF NOT EXISTS knowledge_type VARCHAR(20),
            ADD COLUMN IF NOT EXISTS additional_score FLOAT;
        """))
        print("✅ sessions 表字段补充成功")
        
        # 5. 补充 experts 表字段（tier0_count）
        conn.execute(text("""
            ALTER TABLE experts 
            ADD COLUMN IF NOT EXISTS tier0_count INTEGER DEFAULT 0;
        """))
        print("✅ experts 表 tier0_count 字段添加成功")
        
        conn.commit()
        print("🎉 数据库迁移完成！")

if __name__ == "__main__":
    migrate()
```

- [ ] **Step 2: 运行迁移脚本**

```bash
cd d:\kimi_code\edu_qa_system copy\backend
python migrations/create_tier0_table.py
```

**Expected Output:**
```
🔄 开始数据库迁移...
✅ tier0_knowledge 表创建成功
✅ 基础索引创建成功
⚠️ 向量索引创建失败（数据量可能太小）: ...
✅ sessions 表字段补充成功
✅ experts 表 tier0_count 字段添加成功
🎉 数据库迁移完成！
```

- [ ] **Step 3: 验证表结构**

```bash
# 使用psql或任意数据库工具查询
psql -h localhost -p 15432 -U postgres -d edu_qa -c "\dt"
psql -h localhost -p 15432 -U postgres -d edu_qa -c "\d tier0_knowledge"
```

**Expected:** 显示 tier0_knowledge 表及字段

- [ ] **Step 4: Commit**

```bash
cd d:\kimi_code\edu_qa_system copy
git add backend/migrations/create_tier0_table.py
git commit -m "feat: 添加Tier 0数据库迁移脚本"
```

---

### Task 2: 更新数据模型

**Files:**
- Modify: `backend/app/models/database.py`

- [ ] **Step 1: 在 Expert 模型添加 tier0_count 字段**

找到 `class Expert(SQLModel, table=True):`，在统计字段区域添加：

```python
class Expert(SQLModel, table=True):
    """专家池表 - 按学科划分，支持动态扩展"""
    __tablename__ = "experts"
    
    # ... 现有字段 ...
    
    # 统计字段（现有）
    knowledge_count: int = Field(default=0)  # Tier 1/2 知识数量
    sft_data_count: int = Field(default=0)
    total_qa_count: int = Field(default=0)
    avg_response_time: float = Field(default=0.0)
    accuracy_rate: float = Field(default=0.0)
    
    # 新增：Tier 0 知识数量
    tier0_count: int = Field(default=0)
    
    # ... 其余字段 ...
```

- [ ] **Step 2: 新增 Tier0Knowledge 模型类**

在文件末尾（BenchmarkResult 类之后）添加：

```python
class Tier0Knowledge(SQLModel, table=True):
    """Tier 0 本地迭代知识库 - 高质量质检知识"""
    __tablename__ = "tier0_knowledge"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    expert_id: int = Field(foreign_key="experts.id", index=True)
    
    # 检索内容（简化后的问题，用于embedding匹配）
    content: str
    embedding: List[float] = Field(sa_column=Column(Vector(384)))
    
    # 完整问答对
    meta_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column("metadata", JSON))
    # meta_data格式: {
    #   "question": "原始问题",
    #   "answer": "云端纠正后的答案",
    #   "local_answer": "本地生成的答案",
    #   "knowledge_type": "formula|concept|template|step|qa",
    #   "source_session_id": 123,
    #   "improvement_suggestions": "改进建议"
    # }
    
    # 质量评分（5维度）
    quality_score: float  # 加权总分 0-5
    accuracy_score: Optional[float] = None
    completeness_score: Optional[float] = None
    educational_score: Optional[float] = None
    additional_score: Optional[float] = None
    
    # 去重哈希（问题前100字符的MD5）
    dedup_hash: Optional[str] = Field(default=None, index=True)
    
    # 统计
    usage_count: int = Field(default=0)
    
    # 时间戳
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 关系
    expert: Optional[Expert] = Relationship()
```

- [ ] **Step 3: 补充 Session 模型字段**

找到 `class Session(SQLModel, table=True):`，在质量评分区域添加：

```python
class Session(SQLModel, table=True):
    """对话历史表"""
    __tablename__ = "sessions"
    
    # ... 现有字段 ...
    
    # 质量评分（现有）
    accuracy_score: Optional[float] = None
    completeness_score: Optional[float] = None
    educational_score: Optional[float] = None
    overall_score: Optional[float] = None
    
    # 新增字段（与论文一致）
    additional_score: Optional[float] = None  # 额外维度评分
    knowledge_type: Optional[str] = None      # formula/concept/template/step/qa
    
    # ... 其余字段 ...
```

- [ ] **Step 4: 验证模型加载**

```bash
cd d:\kimi_code\edu_qa_system copy\backend
python -c "from app.models.database import Tier0Knowledge, Session, Expert; print('✅ 模型加载成功')"
```

**Expected:** 无报错，显示"模型加载成功"

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/database.py
git commit -m "feat: 添加Tier0Knowledge模型，补充Session和Expert字段"
```

---

## Phase 2: 核心服务层

### Task 3: 创建 Tier 0 自动入库服务

**Files:**
- Create: `backend/app/services/tier0/__init__.py`
- Create: `backend/app/services/tier0/tier0_ingest_service.py`

- [ ] **Step 1: 创建 __init__.py**

```python
"""Tier 0 服务模块"""
from .tier0_ingest_service import tier0_ingest_service

__all__ = ["tier0_ingest_service"]
```

- [ ] **Step 2: 编写入库服务核心代码**

```python
"""
Tier 0 自动入库服务 - 高质量知识自动入库
"""
import hashlib
import numpy as np
from typing import Optional, Dict, List, Tuple, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from pgvector.sqlalchemy import cosine_distance

from app.models.database import Tier0Knowledge, Expert
from app.core.config import settings


class Tier0IngestService:
    """Tier 0 自动入库服务"""
    
    SIMILARITY_THRESHOLD = 0.92  # 向量去重阈值
    QUALITY_THRESHOLD = 4.0      # 质量入库阈值
    
    async def auto_ingest(
        self,
        session: AsyncSession,
        session_id: int,
        question: str,
        local_answer: str,
        cloud_corrected: str,
        quality_result: Dict[str, Any],
        expert_id: int
    ) -> Dict[str, Any]:
        """
        自动入库到 Tier 0
        
        Args:
            session_id: 会话ID
            question: 原始问题
            local_answer: 本地生成的答案
            cloud_corrected: 云端纠正的答案（入库用这个）
            quality_result: 质检结果字典
            expert_id: 专家ID
            
        Returns:
            {"status": "success|rejected", "knowledge_id": int|None, "reason": str}
        """
        try:
            # 1. 质量阈值检查
            overall_score = quality_result.get("overall_score", 0)
            if overall_score < self.QUALITY_THRESHOLD:
                return {
                    "status": "rejected",
                    "reason": f"quality_too_low ({overall_score:.2f} < {self.QUALITY_THRESHOLD})"
                }
            
            # 2. 生成embedding
            from app.utils.embedding import embedding_service
            content_for_embedding = f"问题：{question}\n答案：{cloud_corrected[:300]}"
            embedding = embedding_service.encode(content_for_embedding)
            
            # 3. 去重检查
            duplicate_check = await self._check_duplicate(
                session, embedding, question, overall_score
            )
            
            if duplicate_check["is_duplicate"]:
                return {
                    "status": "rejected",
                    "reason": f"duplicate (similarity: {duplicate_check['similarity']:.3f})"
                }
            
            # 4. 生成去重哈希
            dedup_hash = hashlib.md5(question[:100].encode('utf-8')).hexdigest()
            
            # 5. 创建 Tier0Knowledge 记录
            knowledge_type = quality_result.get("knowledge_type", "qa")
            
            knowledge = Tier0Knowledge(
                expert_id=expert_id,
                content=question[:500],  # 存储问题作为检索内容
                embedding=embedding.tolist(),
                meta_data={
                    "question": question,
                    "answer": cloud_corrected,
                    "local_answer": local_answer,
                    "knowledge_type": knowledge_type,
                    "source_session_id": session_id,
                    "improvement_suggestions": quality_result.get("improvement_suggestions", "")
                },
                quality_score=overall_score,
                accuracy_score=quality_result.get("accuracy_score"),
                completeness_score=quality_result.get("completeness_score"),
                educational_score=quality_result.get("educational_score"),
                additional_score=quality_result.get("additional_score"),
                dedup_hash=dedup_hash
            )
            
            session.add(knowledge)
            await session.commit()
            await session.refresh(knowledge)
            
            # 6. 更新专家统计
            await self._update_expert_tier0_count(session, expert_id)
            
            print(f"[Tier0] ✅ 成功入库 (ID: {knowledge.id}): {question[:50]}... (质量: {overall_score:.2f})")
            
            return {
                "status": "success",
                "knowledge_id": knowledge.id,
                "reason": None
            }
            
        except Exception as e:
            await session.rollback()
            print(f"[Tier0] ❌ 入库失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "rejected",
                "reason": f"exception: {str(e)}"
            }
    
    async def _check_duplicate(
        self,
        session: AsyncSession,
        new_embedding: np.ndarray,
        question: str,
        new_score: float
    ) -> Dict[str, Any]:
        """
        两级去重检查
        
        Returns:
            {
                "is_duplicate": bool,
                "similarity": float,
                "existing_id": int|None,
                "action": "keep_new|keep_old"
            }
        """
        # 第一层：SimHash快速去重
        dedup_hash = hashlib.md5(question[:100].encode('utf-8')).hexdigest()
        
        hash_stmt = select(Tier0Knowledge).where(
            Tier0Knowledge.dedup_hash == dedup_hash
        )
        hash_result = await session.execute(hash_stmt)
        hash_matches = hash_result.scalars().all()
        
        if hash_matches:
            existing = hash_matches[0]
            # SimHash匹配，认为是重复
            return {
                "is_duplicate": True,
                "similarity": 1.0,
                "existing_id": existing.id,
                "action": "keep_old"
            }
        
        # 第二层：向量相似度精确去重
        # 使用pgvector的 cosine_distance
        vector_stmt = select(
            Tier0Knowledge,
            (1 - cosine_distance(Tier0Knowledge.embedding, new_embedding.tolist())).label("similarity")
        ).order_by(
            cosine_distance(Tier0Knowledge.embedding, new_embedding.tolist())
        ).limit(1)
        
        vector_result = await session.execute(vector_stmt)
        closest = vector_result.first()
        
        if closest:
            knowledge, similarity = closest
            similarity = float(similarity)
            
            if similarity >= self.SIMILARITY_THRESHOLD:
                # 相似度超过阈值
                if new_score > knowledge.quality_score:
                    # 新记录质量更高，删除旧记录
                    await session.delete(knowledge)
                    await session.commit()
                    print(f"[Tier0] 🔄 替换旧记录 (ID: {knowledge.id}): 新质量 {new_score:.2f} > 旧质量 {knowledge.quality_score:.2f}")
                    return {
                        "is_duplicate": False,  # 允许新记录入库
                        "similarity": similarity,
                        "existing_id": None,
                        "action": "replaced"
                    }
                else:
                    # 旧记录质量更高，丢弃新记录
                    return {
                        "is_duplicate": True,
                        "similarity": similarity,
                        "existing_id": knowledge.id,
                        "action": "keep_old"
                    }
        
        # 无重复
        return {
            "is_duplicate": False,
            "similarity": 0.0,
            "existing_id": None,
            "action": "new"
        }
    
    async def _update_expert_tier0_count(self, session: AsyncSession, expert_id: int):
        """更新专家的Tier 0知识数量统计"""
        from sqlalchemy import func
        
        # 统计该专家的Tier 0知识数量
        count_stmt = select(func.count()).where(
            Tier0Knowledge.expert_id == expert_id
        )
        count_result = await session.execute(count_stmt)
        count = count_result.scalar()
        
        # 更新专家表
        expert = await session.get(Expert, expert_id)
        if expert:
            expert.tier0_count = count
            await session.commit()
            print(f"[Tier0] 📊 更新专家 {expert.subject} 的Tier 0数量: {count}")


# 全局实例
tier0_ingest_service = Tier0IngestService()
```

- [ ] **Step 3: 验证服务导入**

```bash
cd d:\kimi_code\edu_qa_system copy\backend
python -c "from app.services.tier0 import tier0_ingest_service; print('✅ 入库服务加载成功')"
```

**Expected:** 无报错

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/tier0/
git commit -m "feat: 实现Tier 0自动入库服务，含两级去重机制"
```

---

### Task 4: 修改聊天API触发自动入库

**Files:**
- Modify: `backend/app/api/chat.py`

- [ ] **Step 1: 导入入库服务**

在文件顶部导入区域添加：

```python
from app.services.iteration.quality_checker import quality_checker
from app.services.tier0 import tier0_ingest_service  # 新增
```

- [ ] **Step 2: 修改 _async_quality_check 函数**

找到 `async def _async_quality_check(...)` 函数，替换整个函数：

```python
async def _async_quality_check(
    session: AsyncSession,
    session_id: int,
    question: str,
    local_answer: str,
    subject: str
):
    """
    异步质量检查 + 自动入库到 Tier 0
    
    流程:
    1. 调用云端质检
    2. 更新会话质检结果
    3. 质量≥4.0时自动入库到Tier 0
    """
    try:
        # 1. 调用云端质检
        quality_result = await quality_checker.check_answer(
            question, local_answer, subject
        )
        
        if not quality_result:
            print(f"[Chat] ⚠️ 质检无结果 (会话{session_id})")
            return
        
        # 2. 获取会话和专家信息
        from app.models.database import Session as ChatSession, Expert
        
        current_session = await session.get(ChatSession, session_id)
        if not current_session:
            print(f"[Chat] ⚠️ 会话不存在 (ID: {session_id})")
            return
        
        expert = await session.get(Expert, current_session.expert_id)
        if not expert:
            print(f"[Chat] ⚠️ 专家不存在 (ID: {current_session.expert_id})")
            return
        
        # 3. 更新会话的质检结果（补充所有字段）
        current_session.cloud_corrected = quality_result["corrected_answer"]
        current_session.accuracy_score = quality_result["accuracy_score"]
        current_session.completeness_score = quality_result["completeness_score"]
        current_session.educational_score = quality_result["educational_score"]
        current_session.additional_score = quality_result.get("additional_score")
        current_session.overall_score = quality_result["overall_score"]
        current_session.knowledge_type = quality_result.get("knowledge_type", "qa")
        
        await session.commit()
        
        print(f"[Chat] ✅ 质检完成 (会话{session_id}): 类型={current_session.knowledge_type}, 质量={quality_result['overall_score']:.2f}")
        
        # 4. 自动入库到 Tier 0（核心新增逻辑）
        ingest_result = await tier0_ingest_service.auto_ingest(
            session=session,
            session_id=session_id,
            question=question,
            local_answer=local_answer,
            cloud_corrected=quality_result["corrected_answer"],
            quality_result=quality_result,
            expert_id=expert.id
        )
        
        if ingest_result["status"] == "success":
            print(f"[Chat] ✅ 自动入库成功 (知识ID: {ingest_result['knowledge_id']})")
        else:
            print(f"[Chat] ⚠️ 未入库: {ingest_result['reason']}")
        
    except Exception as e:
        print(f"[Chat] ❌ 异步质检/入库失败: {e}")
        import traceback
        traceback.print_exc()
```

- [ ] **Step 3: 验证API加载**

```bash
cd d:\kimi_code\edu_qa_system copy\backend
python -c "from app.api.chat import router; print('✅ Chat API加载成功')"
```

**Expected:** 无导入错误

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/chat.py
git commit -m "feat: 聊天API集成Tier 0自动入库流程"
```

---

## Phase 3: 检索层集成

### Task 5: 修改多级检索器支持Tier 0

**Files:**
- Modify: `backend/app/services/rag/multi_tier_retrieval.py`

- [ ] **Step 1: 添加 SQLAlchemy 导入**

在文件顶部添加：

```python
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import json
import pickle
import os

# 新增：数据库相关导入
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from pgvector.sqlalchemy import cosine_distance
```

- [ ] **Step 2: 修改 retrieve 方法签名**

找到 `def retrieve(...)` 方法，修改为异步方法并添加 session 参数：

```python
async def retrieve(
    self,
    session: AsyncSession,  # 新增：数据库会话
    query: str,
    subject: Optional[str] = None,
    top_k: int = 5,
    tier_weights: Tuple[float, float, float] = (0.5, 0.3, 0.2),  # Tier 0/1/2
    score_threshold: float = 0.5
) -> List[RetrievalResult]:
    """
    三级检索 - Tier 0 > Tier 1 > Tier 2
    
    Args:
        session: 数据库会话（用于Tier 0检索）
        query: 查询文本
        subject: 学科名称
        top_k: 返回结果数量
        tier_weights: 三级权重，默认(0.5, 0.3, 0.2)
        score_threshold: 分数阈值
    """
    from app.utils.embedding import embedding_service
    query_embedding = embedding_service.encode(query)
    
    all_results = []
    
    # T0: Tier 0 本地高质量知识库（新增）
    if subject:
        t0_results = await self._search_tier0(
            session, query_embedding, subject, top_k=top_k
        )
        for knowledge, score in t0_results:
            weighted_score = score * tier_weights[0]
            all_results.append((knowledge, weighted_score, 0))  # tier=0
    
    # T1: 学科库检索（现有）
    if subject and subject in self.subject_stores:
        store = self.subject_stores[subject]
        search_results = store.search(query_embedding, top_k=top_k * 2)
        
        for idx, score in search_results:
            doc = store.docs[idx]
            weighted_score = score * tier_weights[1]
            all_results.append((doc, weighted_score, 1))  # tier=1
    
    # T2: 通用库检索（现有）
    need_t2 = not all_results or all_results[0][1] < score_threshold
    if need_t2 and len(self.general_store.docs) > 0:
        search_results = self.general_store.search(query_embedding, top_k=top_k)
        
        for idx, score in search_results:
            doc = self.general_store.docs[idx]
            weighted_score = score * tier_weights[2]
            
            # 去重检查
            doc_id = doc.get('id', '')
            if not any(
                (isinstance(r[0], dict) and r[0].get('id') == doc_id) or
                (hasattr(r[0], 'id') and r[0].id == doc_id)
                for r in all_results
            ):
                all_results.append((doc, weighted_score, 2))  # tier=2
    
    # 排序并取 top_k
    all_results.sort(key=lambda x: x[1], reverse=True)
    
    # 转换为 RetrievalResult
    results = []
    for item, score, tier in all_results[:top_k]:
        if tier == 0:
            # Tier 0: Tier0Knowledge 对象
            results.append(RetrievalResult(
                id=f"t0_{item.id}",
                question=item.meta_data.get('question', item.content),
                answer=item.meta_data.get('answer', ''),
                subject=subject or '通用',
                dataset='tier0_local',
                type=item.meta_data.get('knowledge_type', 'qa'),
                score=score,
                tier=tier,
                metadata={
                    'quality_score': item.quality_score,
                    'accuracy_score': item.accuracy_score,
                    'source': 'tier0_local'
                }
            ))
        else:
            # Tier 1/2: dict 格式
            results.append(RetrievalResult(
                id=item['id'],
                question=item['question'],
                answer=item['answer'],
                subject=item['subject'],
                dataset=item['dataset'],
                type=item['type'],
                score=score,
                tier=tier,
                metadata=item.get('metadata', {})
            ))
    
    return results
```

- [ ] **Step 3: 添加 _search_tier0 方法**

在 `MultiTierRetriever` 类中添加新方法：

```python
async def _search_tier0(
    self,
    session: AsyncSession,
    query_embedding: np.ndarray,
    subject: str,
    top_k: int = 3
) -> List[Tuple[Any, float]]:
    """
    搜索 Tier 0 本地高质量知识库
    
    Returns:
        List[(Tier0Knowledge, similarity_score)]
    """
    from app.models.database import Tier0Knowledge, Expert
    
    # 获取专家ID
    expert_stmt = select(Expert).where(Expert.subject == subject)
    expert_result = await session.execute(expert_stmt)
    expert = expert_result.scalar_one_or_none()
    
    if not expert:
        return []
    
    # 使用 pgvector 进行相似度搜索
    # cosine_distance 返回 0-2 的值，0表示完全相同
    stmt = select(
        Tier0Knowledge,
        (1 - cosine_distance(Tier0Knowledge.embedding, query_embedding.tolist())).label("similarity")
    ).where(
        Tier0Knowledge.expert_id == expert.id
    ).order_by(
        cosine_distance(Tier0Knowledge.embedding, query_embedding.tolist())
    ).limit(top_k)
    
    result = await session.execute(stmt)
    return [(row[0], float(row[1])) for row in result.all()]
```

- [ ] **Step 4: 更新 format_context 方法**

找到 `format_context` 方法，修改以支持 Tier 0：

```python
def format_context(self, results: List[RetrievalResult]) -> str:
    """格式化检索结果 - 用于构建Prompt上下文"""
    if not results:
        return ""
    
    contexts = []
    for i, r in enumerate(results, 1):
        tier_label = {0: "[高质量]", 1: "[学科库]", 2: "[通用库]"}.get(r.tier, "")
        
        ctx = f"{tier_label}[{i}] {r.question}"
        
        # 对于Tier 0，显示质量分
        if r.tier == 0 and r.metadata.get('quality_score'):
            ctx += f" (质量分: {r.metadata['quality_score']:.1f})"
        
        if r.type == 'choice' and r.metadata.get('choices'):
            choices = r.metadata['choices'][:4]
            ctx += f"\n选项: {', '.join(str(c) for c in choices)}"
        
        contexts.append(ctx)
    
    return "\n\n".join(contexts)
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/rag/multi_tier_retrieval.py
git commit -m "feat: 多级检索器集成Tier 0支持，实现三级检索架构"
```

---

## Phase 4: API层与路由

### Task 6: 创建 Tier 0 管理 API

**Files:**
- Create: `backend/app/api/tier0.py`

- [ ] **Step 1: 编写完整 API 代码**

```python
"""Tier 0 知识库管理 API"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional

from app.core.database import get_session
from app.models.schemas import ResponseBase
from app.models.database import Tier0Knowledge, Expert

router = APIRouter(prefix="/tier0", tags=["Tier 0知识库"])


@router.get("/list", response_model=ResponseBase)
async def list_tier0_knowledge(
    expert_id: Optional[int] = Query(None, description="专家ID筛选"),
    subject: Optional[str] = Query(None, description="学科名称筛选"),
    knowledge_type: Optional[str] = Query(None, description="知识类型: formula/concept/template/step/qa"),
    min_score: float = Query(0.0, ge=0, le=5, description="最低质量分"),
    limit: int = Query(50, ge=1, le=200, description="返回数量"),
    session: AsyncSession = Depends(get_session)
):
    """获取 Tier 0 知识列表（管理用）"""
    
    stmt = select(Tier0Knowledge)
    
    # 筛选条件
    if expert_id:
        stmt = stmt.where(Tier0Knowledge.expert_id == expert_id)
    elif subject:
        # 通过subject查找expert_id
        expert_stmt = select(Expert).where(Expert.subject == subject)
        expert_result = await session.execute(expert_stmt)
        expert = expert_result.scalar_one_or_none()
        if expert:
            stmt = stmt.where(Tier0Knowledge.expert_id == expert.id)
    
    if knowledge_type:
        stmt = stmt.where(
            Tier0Knowledge.meta_data["knowledge_type"].astext == knowledge_type
        )
    
    if min_score > 0:
        stmt = stmt.where(Tier0Knowledge.quality_score >= min_score)
    
    # 排序和限制
    stmt = stmt.order_by(Tier0Knowledge.created_at.desc()).limit(limit)
    
    result = await session.execute(stmt)
    knowledges = result.scalars().all()
    
    # 构建响应
    items = []
    for k in knowledges:
        items.append({
            "id": k.id,
            "expert_id": k.expert_id,
            "content": k.content[:200] + "..." if len(k.content) > 200 else k.content,
            "quality_score": k.quality_score,
            "knowledge_type": k.meta_data.get("knowledge_type") if k.meta_data else None,
            "usage_count": k.usage_count,
            "created_at": k.created_at.isoformat() if k.created_at else None,
            "answer_preview": k.meta_data.get("answer", "")[:100] + "..." 
                             if k.meta_data and len(k.meta_data.get("answer", "")) > 100 
                             else k.meta_data.get("answer", "") if k.meta_data else ""
        })
    
    return ResponseBase(data={
        "items": items,
        "total": len(items),
        "filters": {
            "expert_id": expert_id,
            "subject": subject,
            "knowledge_type": knowledge_type,
            "min_score": min_score
        }
    })


@router.get("/stats", response_model=ResponseBase)
async def get_tier0_stats(
    session: AsyncSession = Depends(get_session)
):
    """获取 Tier 0 统计信息"""
    
    # 总体统计
    total_stmt = select(func.count()).select_from(Tier0Knowledge)
    total_result = await session.execute(total_stmt)
    total_count = total_result.scalar()
    
    # 平均质量分
    avg_score_stmt = select(func.avg(Tier0Knowledge.quality_score))
    avg_score_result = await session.execute(avg_score_stmt)
    avg_score = avg_score_result.scalar() or 0
    
    # 按学科统计
    subject_stats_stmt = select(
        Expert.subject,
        func.count(Tier0Knowledge.id).label("count"),
        func.avg(Tier0Knowledge.quality_score).label("avg_score")
    ).join(
        Tier0Knowledge, Expert.id == Tier0Knowledge.expert_id
    ).group_by(Expert.subject)
    
    subject_stats_result = await session.execute(subject_stats_stmt)
    subject_stats = [
        {
            "subject": row.subject,
            "count": row.count,
            "avg_score": round(row.avg_score or 0, 2)
        }
        for row in subject_stats_result.all()
    ]
    
    # 按类型统计
    type_stmt = select(
        Tier0Knowledge.meta_data["knowledge_type"].astext.label("ktype"),
        func.count().label("count")
    ).group_by("ktype")
    
    type_result = await session.execute(type_stmt)
    type_stats = [
        {"type": row.ktype, "count": row.count}
        for row in type_result.all()
    ]
    
    return ResponseBase(data={
        "total_count": total_count,
        "avg_quality_score": round(avg_score, 2),
        "by_subject": subject_stats,
        "by_type": type_stats
    })


@router.get("/{knowledge_id}", response_model=ResponseBase)
async def get_tier0_knowledge(
    knowledge_id: int,
    session: AsyncSession = Depends(get_session)
):
    """获取单个 Tier 0 知识详情"""
    
    knowledge = await session.get(Tier0Knowledge, knowledge_id)
    if not knowledge:
        return ResponseBase(code=404, message="知识不存在")
    
    # 获取专家信息
    expert = await session.get(Expert, knowledge.expert_id)
    
    return ResponseBase(data={
        "id": knowledge.id,
        "expert": {
            "id": expert.id if expert else None,
            "subject": expert.subject if expert else None,
            "name": expert.name if expert else None
        },
        "content": knowledge.content,
        "meta_data": knowledge.meta_data,
        "quality_score": knowledge.quality_score,
        "accuracy_score": knowledge.accuracy_score,
        "completeness_score": knowledge.completeness_score,
        "educational_score": knowledge.educational_score,
        "additional_score": knowledge.additional_score,
        "usage_count": knowledge.usage_count,
        "created_at": knowledge.created_at.isoformat() if knowledge.created_at else None,
        "updated_at": knowledge.updated_at.isoformat() if knowledge.updated_at else None
    })


@router.delete("/{knowledge_id}", response_model=ResponseBase)
async def delete_tier0_knowledge(
    knowledge_id: int,
    session: AsyncSession = Depends(get_session)
):
    """删除 Tier 0 知识（管理用）"""
    
    knowledge = await session.get(Tier0Knowledge, knowledge_id)
    if not knowledge:
        return ResponseBase(code=404, message="知识不存在")
    
    expert_id = knowledge.expert_id
    await session.delete(knowledge)
    await session.commit()
    
    # 更新专家统计
    from app.services.tier0 import tier0_ingest_service
    await tier0_ingest_service._update_expert_tier0_count(session, expert_id)
    
    return ResponseBase(message="删除成功")
```

- [ ] **Step 2: 注册路由**

修改 `backend/app/main.py`，在路由注册区域添加：

```python
from app.api import chat, experts, experiments, benchmark, training, knowledge
from app.api import tier0  # 新增

# ... 现有路由 ...
app.include_router(tier0.router, prefix=settings.API_V1_STR)
```

- [ ] **Step 3: 验证API加载**

```bash
cd d:\kimi_code\edu_qa_system copy\backend
python -c "from app.main import app; print('✅ 应用加载成功'); print([r.path for r in app.routes if hasattr(r, 'path') and 'tier0' in str(r.path)])"
```

**Expected:** 显示包含 `/api/v1/tier0` 的路径列表

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/tier0.py backend/app/main.py
git commit -m "feat: 添加Tier 0管理API，支持列表/统计/详情/删除"
```

---

## Phase 5: 测试与验证

### Task 7: 创建单元测试

**Files:**
- Create: `backend/tests/test_tier0_ingest.py`

- [ ] **Step 1: 编写完整测试代码**

```python
"""Tier 0 自动入库服务单元测试"""
import pytest
import numpy as np
from unittest.mock import Mock, patch, AsyncMock

from app.services.tier0.tier0_ingest_service import Tier0IngestService


@pytest.fixture
def service():
    return Tier0IngestService()


@pytest.fixture
def mock_session():
    """模拟数据库会话"""
    session = Mock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def sample_quality_result():
    """样本质检结果"""
    return {
        "overall_score": 4.5,
        "accuracy_score": 4.5,
        "completeness_score": 4.0,
        "educational_score": 4.5,
        "additional_score": 4.2,
        "knowledge_type": "formula",
        "corrected_answer": "纠正后的答案",
        "improvement_suggestions": "改进建议"
    }


class TestQualityThreshold:
    """测试质量阈值过滤"""
    
    @pytest.mark.asyncio
    async def test_low_quality_rejected(self, service, mock_session):
        """低质量应该被拒绝入库"""
        result = await service.auto_ingest(
            session=mock_session,
            session_id=1,
            question="测试问题",
            local_answer="本地答案",
            cloud_corrected="纠正答案",
            quality_result={"overall_score": 3.5},  # < 4.0
            expert_id=1
        )
        
        assert result["status"] == "rejected"
        assert "quality_too_low" in result["reason"]
    
    @pytest.mark.asyncio
    async def test_high_quality_accepted(self, service, mock_session, sample_quality_result):
        """高质量应该被接受"""
        # Mock embedding_service
        with patch('app.services.tier0.tier0_ingest_service.embedding_service') as mock_emb:
            mock_emb.encode.return_value = np.random.randn(384)
            
            # Mock _check_duplicate 返回无重复
            with patch.object(service, '_check_duplicate', new=AsyncMock(return_value={
                "is_duplicate": False, "similarity": 0.0, "existing_id": None
            })):
                # Mock _update_expert_tier0_count
                with patch.object(service, '_update_expert_tier0_count', new=AsyncMock()):
                    result = await service.auto_ingest(
                        session=mock_session,
                        session_id=1,
                        question="测试问题",
                        local_answer="本地答案",
                        cloud_corrected="纠正答案",
                        quality_result=sample_quality_result,
                        expert_id=1
                    )
                    
                    assert result["status"] == "success"


class TestDuplicateDetection:
    """测试去重逻辑"""
    
    @pytest.mark.asyncio
    async def test_exact_duplicate_by_hash(self, service, mock_session):
        """SimHash完全匹配应该被视为重复"""
        # Mock 数据库返回SimHash匹配的结果
        mock_knowledge = Mock()
        mock_knowledge.id = 123
        
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_knowledge]
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        result = await service._check_duplicate(
            session=mock_session,
            new_embedding=np.random.randn(384),
            question="相同的问题内容",
            new_score=4.5
        )
        
        assert result["is_duplicate"] is True
        assert result["similarity"] == 1.0
    
    @pytest.mark.asyncio
    async def test_vector_duplicate(self, service, mock_session):
        """向量相似度超过阈值应该被视为重复"""
        # Mock SimHash不匹配
        mock_result1 = Mock()
        mock_result1.scalars.return_value.all.return_value = []
        
        # Mock 向量搜索返回高相似度结果
        mock_knowledge = Mock()
        mock_knowledge.id = 456
        mock_knowledge.quality_score = 4.0  # 旧记录质量较低
        
        mock_result2 = Mock()
        mock_result2.first.return_value = (mock_knowledge, 0.95)  # 相似度0.95
        
        mock_session.execute = AsyncMock(side_effect=[mock_result1, mock_result2])
        mock_session.delete = AsyncMock()
        mock_session.commit = AsyncMock()
        
        # 新记录质量更高(4.5 > 4.0)，应该替换
        result = await service._check_duplicate(
            session=mock_session,
            new_embedding=np.random.randn(384),
            question="不同的问题",
            new_score=4.5
        )
        
        # 新记录质量更高，应该允许入库（旧记录被删除）
        assert result["is_duplicate"] is False


class TestIngestSuccess:
    """测试成功入库场景"""
    
    @pytest.mark.asyncio
    async def test_successful_ingest(self, service, mock_session, sample_quality_result):
        """完整成功入库流程"""
        with patch('app.services.tier0.tier0_ingest_service.embedding_service') as mock_emb:
            mock_emb.encode.return_value = np.random.randn(384)
            
            with patch.object(service, '_check_duplicate', new=AsyncMock(return_value={
                "is_duplicate": False
            })):
                with patch.object(service, '_update_expert_tier0_count', new=AsyncMock()):
                    # Mock 数据库操作
                    mock_knowledge = Mock()
                    mock_knowledge.id = 999
                    mock_session.add = Mock()
                    mock_session.refresh = AsyncMock()
                    
                    result = await service.auto_ingest(
                        session=mock_session,
                        session_id=42,
                        question="测试数学题：2+2=?",
                        local_answer="4",
                        cloud_corrected="答案是4",
                        quality_result=sample_quality_result,
                        expert_id=1
                    )
                    
                    assert result["status"] == "success"
                    assert result["knowledge_id"] is not None
                    mock_session.add.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

- [ ] **Step 2: 运行测试**

```bash
cd d:\kimi_code\edu_qa_system copy\backend
python -m pytest tests/test_tier0_ingest.py -v
```

**Expected:** 所有测试通过

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_tier0_ingest.py
git commit -m "test: 添加Tier 0入库服务单元测试"
```

---

## Phase 6: 集成验证

### Task 8: 端到端测试

**手动验证步骤：**

- [ ] **Step 1: 启动后端服务**

```bash
cd d:\kimi_code\edu_qa_system copy\backend
python start_backend.py
```

- [ ] **Step 2: 发送测试请求**

使用curl或Postman：

```bash
# 1. 发送一个数学题，触发质检和入库
curl -X POST http://localhost:8000/api/v1/chat/send \
  -H "Content-Type: application/json" \
  -d '{
    "query": "解方程：2x + 5 = 13",
    "session_id": null
  }'
```

- [ ] **Step 3: 等待异步质检完成**

查看后端日志，确认：
```
[Chat] ✅ 质检完成 (会话X): 类型=formula, 质量=4.X
[Chat] ✅ 自动入库成功 (知识ID: Y)
```

- [ ] **Step 4: 查询Tier 0知识列表**

```bash
curl http://localhost:8000/api/v1/tier0/list?subject=数学
```

**Expected:** 返回刚才入库的知识条目

- [ ] **Step 5: 再次发送相似问题，验证检索**

```bash
curl -X POST http://localhost:8000/api/v1/chat/send \
  -H "Content-Type: application/json" \
  -d '{
    "query": "求解方程 2x+5=13",
    "session_id": null
  }'
```

**Expected:** 返回结果中 `used_knowledges` 包含 Tier 0 知识

---

## 验收清单

### 功能验收

- [ ] Tier 0 表创建成功，包含所有字段
- [ ] Sessions 表补充 `knowledge_type` 和 `additional_score` 字段
- [ ] Experts 表补充 `tier0_count` 字段
- [ ] 质检评分≥4.0的知识自动入库到 Tier 0
- [ ] SimHash相同的知识被去重
- [ ] 向量相似度≥0.92的知识被去重
- [ ] 高质量新记录可替换低质量旧记录
- [ ] 检索时优先使用 Tier 0 知识
- [ ] 专家统计正确更新
- [ ] 管理API可查询/删除 Tier 0 知识

### 代码质量

- [ ] 单元测试通过率 100%
- [ ] 代码符合项目现有风格
- [ ] 异常处理完善
- [ ] 日志输出清晰

### 论文符合度

- [ ] 三级检索架构实现（Tier 0/1/2）
- [ ] 异步自动入库流程
- [ ] 质量阈值触发机制（≥4.0）
- [ ] 向量去重机制（相似度≥0.92）
- [ ] 5维质量评分存储

---

## Plan Self-Review

### Spec Coverage
- ✅ Tier 0 表设计 - Task 1
- ✅ 自动入库流程 - Task 3, 4
- ✅ 两级去重机制 - Task 3
- ✅ 三级检索集成 - Task 5
- ✅ 管理API - Task 6
- ✅ 测试 - Task 7

### Placeholder Scan
- ✅ 无TBD/TODO
- ✅ 所有代码完整
- ✅ 所有命令具体

### Type Consistency
- ✅ `Tier0Knowledge` 模型字段一致
- ✅ `RetrievalResult` tier标记一致
- ✅ 权重顺序一致 (0.5, 0.3, 0.2)

---

**Plan complete and saved to `docs/2025-04-05-tier0-implementation-plan.md`.**

## 执行选项

**1. Subagent-Driven (推荐)** - 我分派专门的子代理逐个任务实现，每步审核，快速迭代

**2. Inline Execution** - 在当前会话中批量执行任务，设置检查点进行审核

**您选择哪种执行方式？** 建议选 **1**，因为任务较多且有依赖关系，子代理执行更高效。
