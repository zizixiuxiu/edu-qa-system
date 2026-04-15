# Tier 0 本地迭代知识库 + 自动入库功能设计文档

**日期**: 2025-04-05  
**状态**: 待实现  
**优先级**: P0 (高优先级)

---

## 1. 概述

### 1.1 背景
论文中描述的"三级知识检索架构"（Tier 0/1/2）在实际代码中缺失 Tier 0 层。当前系统只有 Tier 1（学科库）和 Tier 2（通用库）。

### 1.2 目标
实现完整的 Tier 0 本地迭代知识库，支持云端质检后的自动入库功能。

### 1.3 设计原则
- **符合论文**: 严格遵循论文3.5.1、3.6.1、3.6.4节的描述
- **异步非阻塞**: 入库过程不影响用户响应
- **数据持久化**: 使用 PostgreSQL + pgvector
- **自动去重**: 相似度≥0.92的不入库

---

## 2. 数据库设计

### 2.1 新表: tier0_knowledge

```sql
CREATE TABLE tier0_knowledge (
    id SERIAL PRIMARY KEY,
    expert_id INTEGER NOT NULL REFERENCES experts(id),
    
    -- 核心内容
    content TEXT NOT NULL,  -- 检索内容（问题摘要）
    embedding VECTOR(384),  -- BGE-Small向量
    
    -- 完整问答对（存储在meta_data中）
    meta_data JSONB DEFAULT '{}',
    -- meta_data格式:
    -- {
    --   "question": "原始问题",
    --   "answer": "云端纠正后的答案",
    --   "knowledge_type": "formula|concept|template|step|qa",
    --   "source_session_id": 123,
    --   "improvement_suggestions": "改进建议"
    -- }
    
    -- 质量评分
    quality_score FLOAT NOT NULL,  -- 总分 (0-5)
    accuracy_score FLOAT,          -- 准确性
    completeness_score FLOAT,      -- 完整性
    educational_score FLOAT,       -- 教育性
    additional_score FLOAT,        -- 额外维度（规范性/实用性/逻辑性）
    
    -- 去重相关
    dedup_hash VARCHAR(64),  -- 问题内容的SimHash，用于快速去重
    
    -- 统计
    usage_count INTEGER DEFAULT 0,
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_tier0_expert_id ON tier0_knowledge(expert_id);
CREATE INDEX idx_tier0_quality_score ON tier0_knowledge(quality_score);
CREATE INDEX idx_tier0_dedup_hash ON tier0_knowledge(dedup_hash);
CREATE INDEX idx_tier0_knowledge_type ON tier0_knowledge((meta_data->>'knowledge_type'));

-- pgvector 相似度搜索索引
CREATE INDEX idx_tier0_embedding ON tier0_knowledge 
    USING ivfflat (embedding vector_cosine_ops) 
    WITH (lists = 100);
```

### 2.2 现有表字段补充

#### sessions 表添加字段
```sql
-- 这些字段在代码中有注释说明不存在，需要添加
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS knowledge_type VARCHAR(20);
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS additional_score FLOAT;
```

---

## 3. 数据模型变更

### 3.1 新增 SQLModel 类

```python
# backend/app/models/database.py

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
    
    # 质量评分（5维度）
    quality_score: float  # 加权总分
    accuracy_score: Optional[float] = None
    completeness_score: Optional[float] = None
    educational_score: Optional[float] = None
    additional_score: Optional[float] = None
    
    # 去重哈希
    dedup_hash: Optional[str] = Field(default=None, index=True)
    
    # 统计
    usage_count: int = Field(default=0)
    
    # 时间戳
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 关系
    expert: Optional[Expert] = Relationship()
```

### 3.2 Session 模型补充字段

```python
class Session(SQLModel, table=True):
    # ... 现有字段 ...
    
    # 新增字段（与论文一致）
    knowledge_type: Optional[str] = None  # formula/concept/template/step/qa
    additional_score: Optional[float] = None  # 额外维度评分
```

---

## 4. 自动入库流程

### 4.1 流程图

```
用户提问
    │
    ▼
本地生成答案 ◄───────────────────┐
    │                            │
    ▼                            │
返回给用户（响应结束）            │
    │                            │
    ▼                            │
异步触发质检                      │
    │                            │
    ▼                            │
云端质检评分                      │
    │                            │
    ├── 评分 < 4.0 ──► 丢弃      │
    │                            │
    └── 评分 ≥ 4.0               │
            │                    │
            ▼                    │
    向量去重检查                  │
            │                    │
            ├── 相似度 ≥ 0.92    │
            │       │            │
            │       ▼            │
            │   比较质量分        │
            │       │            │
            │       ├── 新更高 ──► 替换旧记录
            │       │
            │       └── 旧更高 ──► 丢弃
            │
            └── 相似度 < 0.92
                    │
                    ▼
            入库到 Tier 0
                    │
                    ▼
            更新专家统计
                    │
                    ▼
            流程结束
```

### 4.2 核心代码实现

#### 4.2.1 自动入库服务

```python
# backend/app/services/tier0/tier0_ingest_service.py

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
import numpy as np

class Tier0IngestService:
    """Tier 0 自动入库服务"""
    
    SIMILARITY_THRESHOLD = 0.92  # 去重阈值
    QUALITY_THRESHOLD = 4.0      # 质量阈值
    
    async def auto_ingest(
        self,
        session: AsyncSession,
        session_id: int,
        question: str,
        local_answer: str,
        cloud_corrected: str,
        quality_result: dict,
        expert_id: int
    ) -> Optional[dict]:
        """
        自动入库到 Tier 0
        
        Args:
            session_id: 会话ID
            question: 原始问题
            local_answer: 本地生成的答案
            cloud_corrected: 云端纠正的答案
            quality_result: 质检结果
            expert_id: 专家ID
            
        Returns:
            入库结果 {"status": "success|rejected", "knowledge_id": int, "reason": str}
        """
        
        # 1. 质量阈值检查
        overall_score = quality_result.get("overall_score", 0)
        if overall_score < self.QUALITY_THRESHOLD:
            return {
                "status": "rejected",
                "reason": f"quality_too_low ({overall_score:.2f} < {self.QUALITY_THRESHOLD})"
            }
        
        # 2. 准备入库内容
        knowledge_type = quality_result.get("knowledge_type", "qa")
        
        # 检索内容：问题 + 答案摘要（用于embedding）
        content_for_embedding = f"问题：{question}\n答案：{cloud_corrected[:200]}"
        
        # 生成embedding
        from app.utils.embedding import embedding_service
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
        
        # 4. 创建 Tier0Knowledge 记录
        from app.models.database import Tier0Knowledge
        import hashlib
        
        # 生成去重哈希（基于问题前100字符）
        dedup_hash = hashlib.md5(question[:100].encode()).hexdigest()
        
        knowledge = Tier0Knowledge(
            expert_id=expert_id,
            content=question,  # 存储原始问题作为检索内容
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
        
        # 5. 更新专家统计
        await self._update_expert_stats(session, expert_id)
        
        print(f"[Tier0] 成功入库 (ID: {knowledge.id}): {question[:50]}... (质量: {overall_score:.2f})")
        
        return {
            "status": "success",
            "knowledge_id": knowledge.id,
            "reason": None
        }
    
    async def _check_duplicate(
        self,
        session: AsyncSession,
        new_embedding: np.ndarray,
        question: str,
        new_score: float
    ) -> dict:
        """
        向量去重检查
        
        Returns:
            {"is_duplicate": bool, "similarity": float, "existing_id": int}
        """
        from app.models.database import Tier0Knowledge
        from pgvector.sqlalchemy import cosine_distance
        
        # 方法1: 使用SimHash快速筛选
        import hashlib
        dedup_hash = hashlib.md5(question[:100].encode()).hexdigest()
        
        stmt = select(Tier0Knowledge).where(
            Tier0Knowledge.dedup_hash == dedup_hash
        )
        result = await session.execute(stmt)
        hash_matches = result.scalars().all()
        
        if hash_matches:
            # SimHash匹配，直接认为是重复
            existing = hash_matches[0]
            return {
                "is_duplicate": True,
                "similarity": 1.0,
                "existing_id": existing.id
            }
        
        # 方法2: 向量相似度搜索
        # 使用pgvector的 <=> 运算符（余弦距离）
        stmt = select(
            Tier0Knowledge,
            cosine_distance(Tier0Knowledge.embedding, new_embedding.tolist()).label("distance")
        ).order_by("distance").limit(1)
        
        result = await session.execute(stmt)
        closest = result.first()
        
        if closest:
            knowledge, distance = closest
            similarity = 1 - distance  # 距离转相似度
            
            if similarity >= self.SIMILARITY_THRESHOLD:
                # 检查质量分，保留更高的
                if new_score <= knowledge.quality_score:
                    return {
                        "is_duplicate": True,
                        "similarity": similarity,
                        "existing_id": knowledge.id
                    }
                else:
                    # 新记录质量更高，删除旧记录
                    await session.delete(knowledge)
                    await session.commit()
                    print(f"[Tier0] 替换旧记录 (ID: {knowledge.id}): 新质量 {new_score:.2f} > 旧质量 {knowledge.quality_score:.2f}")
        
        return {
            "is_duplicate": False,
            "similarity": 0.0,
            "existing_id": None
        }
    
    async def _update_expert_stats(self, session: AsyncSession, expert_id: int):
        """更新专家的Tier 0知识数量统计"""
        from app.models.database import Expert, Tier0Knowledge
        from sqlalchemy import func
        
        # 统计该专家的Tier 0知识数量
        stmt = select(func.count()).where(Tier0Knowledge.expert_id == expert_id)
        result = await session.execute(stmt)
        count = result.scalar()
        
        # 更新专家表
        expert = await session.get(Expert, expert_id)
        if expert:
            # 将Tier 0数量存入 knowledge_count（或新增字段）
            expert.knowledge_count = count
            await session.commit()


# 全局实例
tier0_ingest_service = Tier0IngestService()
```

#### 4.2.2 修改质检后的处理逻辑

```python
# backend/app/api/chat.py

async def _async_quality_check(
    session: AsyncSession,
    session_id: int,
    question: str,
    local_answer: str,
    subject: str
):
    """异步质量检查 + 自动入库"""
    try:
        # 1. 调用云端质检
        quality_result = await quality_checker.check_answer(
            question, local_answer, subject
        )
        
        if not quality_result:
            return
        
        # 2. 获取会话信息
        from app.models.database import Session as ChatSession, Expert
        current_session = await session.get(ChatSession, session_id)
        if not current_session:
            return
        
        expert = await session.get(Expert, current_session.expert_id)
        if not expert:
            return
        
        # 3. 更新会话的质检结果（补充缺失字段）
        current_session.cloud_corrected = quality_result["corrected_answer"]
        current_session.accuracy_score = quality_result["accuracy_score"]
        current_session.completeness_score = quality_result["completeness_score"]
        current_session.educational_score = quality_result["educational_score"]
        current_session.additional_score = quality_result.get("additional_score")
        current_session.overall_score = quality_result["overall_score"]
        current_session.knowledge_type = quality_result.get("knowledge_type", "qa")
        
        await session.commit()
        
        # 4. 自动入库到 Tier 0（新增）
        from app.services.tier0.tier0_ingest_service import tier0_ingest_service
        
        ingest_result = await tier0_ingest_service.auto_ingest(
            session=session,
            session_id=session_id,
            question=question,
            local_answer=local_answer,
            cloud_corrected=quality_result["corrected_answer"],
            quality_result=quality_result,
            expert_id=expert.id
        )
        
        print(f"[Chat] 质检入库结果: {ingest_result}")
        
    except Exception as e:
        print(f"[Chat] 异步质检/入库失败: {e}")
        import traceback
        traceback.print_exc()
```

---

## 5. 检索服务集成

### 5.1 修改多级检索器

```python
# backend/app/services/rag/multi_tier_retrieval.py

class MultiTierRetriever:
    """三级检索器 - 支持 Tier 0/1/2"""
    
    def __init__(self, data_dir: str = "D:/毕设数据集/processed"):
        self.data_dir = data_dir
        self.cache_dir = "D:/毕设数据集/vector_cache_v2"
        
        # Tier 1: 学科库（内存）
        self.subject_stores: Dict[str, VectorStore] = {}
        # Tier 2: 通用库（内存）
        self.general_store = VectorStore("general")
        # Tier 0: 将在检索时从数据库加载（或通过缓存）
        
        self._load_data()
    
    async def retrieve(
        self,
        session: AsyncSession,  # 添加session参数
        query: str,
        subject: Optional[str] = None,
        top_k: int = 5,
        tier_weights: Tuple[float, float, float] = (0.5, 0.3, 0.2),  # Tier 0/1/2
        score_threshold: float = 0.5
    ) -> List[RetrievalResult]:
        """
        三级检索
        
        检索优先级: Tier 0 > Tier 1 > Tier 2
        """
        from app.utils.embedding import embedding_service
        query_embedding = embedding_service.encode(query)
        
        all_results = []
        
        # T0: Tier 0 本地高质量知识库（新增）
        if subject:
            t0_results = await self._search_tier0(
                session, query_embedding, subject, top_k=top_k
            )
            for doc, score in t0_results:
                weighted_score = score * tier_weights[0]
                all_results.append((doc, weighted_score, 0))  # tier=0
        
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
                
                # 去重
                if not any(r[0].get('id') == doc['id'] for r in all_results if isinstance(r[0], dict)):
                    all_results.append((doc, weighted_score, 2))  # tier=2
        
        # 排序并取 top_k
        all_results.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for doc, score, tier in all_results[:top_k]:
            if isinstance(doc, dict):
                # Tier 1/2 的数据格式
                results.append(RetrievalResult(
                    id=doc['id'],
                    question=doc['question'],
                    answer=doc['answer'],
                    subject=doc['subject'],
                    dataset=doc['dataset'],
                    type=doc['type'],
                    score=score,
                    tier=tier,
                    metadata=doc['metadata']
                ))
            else:
                # Tier 0 的数据格式（Tier0Knowledge对象）
                results.append(RetrievalResult(
                    id=f"t0_{doc.id}",
                    question=doc.meta_data.get('question', doc.content),
                    answer=doc.meta_data.get('answer', ''),
                    subject=subject or '通用',
                    dataset='tier0_local',
                    type=doc.meta_data.get('knowledge_type', 'qa'),
                    score=score,
                    tier=tier,
                    metadata={
                        'quality_score': doc.quality_score,
                        'source': 'tier0_local'
                    }
                ))
        
        return results
    
    async def _search_tier0(
        self,
        session: AsyncSession,
        query_embedding: np.ndarray,
        subject: str,
        top_k: int = 3
    ) -> List[Tuple[Any, float]]:
        """
        搜索 Tier 0 本地知识库
        
        Returns:
            List[(Tier0Knowledge, similarity_score)]
        """
        from app.models.database import Tier0Knowledge, Expert
        from pgvector.sqlalchemy import cosine_distance
        from sqlalchemy import select
        
        # 获取专家ID
        expert_stmt = select(Expert).where(Expert.subject == subject)
        expert_result = await session.execute(expert_stmt)
        expert = expert_result.scalar_one_or_none()
        
        if not expert:
            return []
        
        # 使用pgvector进行相似度搜索
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

---

## 6. API 变更

### 6.1 新增接口

```python
# backend/app/api/tier0.py（新增文件）

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_session
from app.models.schemas import ResponseBase
from app.models.database import Tier0Knowledge

router = APIRouter(prefix="/tier0", tags=["Tier 0知识库"])

@router.get("/list", response_model=ResponseBase)
async def list_tier0_knowledge(
    expert_id: Optional[int] = None,
    knowledge_type: Optional[str] = None,
    min_score: float = 0.0,
    limit: int = 50,
    session: AsyncSession = Depends(get_session)
):
    """获取 Tier 0 知识列表（管理用）"""
    from sqlalchemy import select
    
    stmt = select(Tier0Knowledge)
    
    if expert_id:
        stmt = stmt.where(Tier0Knowledge.expert_id == expert_id)
    if knowledge_type:
        stmt = stmt.where(Tier0Knowledge.meta_data["knowledge_type"].astext == knowledge_type)
    if min_score > 0:
        stmt = stmt.where(Tier0Knowledge.quality_score >= min_score)
    
    stmt = stmt.order_by(Tier0Knowledge.created_at.desc()).limit(limit)
    
    result = await session.execute(stmt)
    knowledges = result.scalars().all()
    
    return ResponseBase(data={
        "items": [{
            "id": k.id,
            "expert_id": k.expert_id,
            "content": k.content,
            "quality_score": k.quality_score,
            "knowledge_type": k.meta_data.get("knowledge_type") if k.meta_data else None,
            "usage_count": k.usage_count,
            "created_at": k.created_at.isoformat()
        } for k in knowledges],
        "total": len(knowledges)
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
    
    await session.delete(knowledge)
    await session.commit()
    
    return ResponseBase(message="删除成功")
```

### 6.2 注册路由

```python
# backend/app/main.py

from app.api import chat, experts, experiments, benchmark, training, knowledge
from app.api import tier0  # 新增

# ... 现有路由 ...
app.include_router(tier0.router, prefix=settings.API_V1_STR)
```

---

## 7. 前端变更（最小化）

### 7.1 知识引用显示

在 Chat.vue 中， Tier 0 知识的显示标签：

```vue
<el-tag size="small" type="success" effect="light">
  Tier 0 (高质量)
</el-tag>
```

### 7.2 新增管理页面（可选）

如果需要管理 Tier 0 知识，可新增 Knowledge.vue 中的标签页：
- 显示已入库的高质量知识
- 支持删除操作

---

## 8. 数据库迁移脚本

```python
# backend/migrations/create_tier0_table.py

"""
数据库迁移脚本：创建 tier0_knowledge 表
"""

from sqlalchemy import create_engine, text
from app.core.config import settings

def migrate():
    engine = create_engine(settings.DATABASE_URL.replace('+psycopg2', ''))
    
    with engine.connect() as conn:
        # 创建表
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS tier0_knowledge (
                id SERIAL PRIMARY KEY,
                expert_id INTEGER NOT NULL REFERENCES experts(id),
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
        
        # 创建索引
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_tier0_expert_id ON tier0_knowledge(expert_id);
            CREATE INDEX IF NOT EXISTS idx_tier0_quality_score ON tier0_knowledge(quality_score);
            CREATE INDEX IF NOT EXISTS idx_tier0_dedup_hash ON tier0_knowledge(dedup_hash);
            CREATE INDEX IF NOT EXISTS idx_tier0_knowledge_type ON tier0_knowledge((metadata->>'knowledge_type'));
        """))
        
        # pgvector索引（如果数据量大时创建）
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_tier0_embedding ON tier0_knowledge 
            USING ivfflat (embedding vector_cosine_ops) 
            WITH (lists = 100);
        """))
        
        # 添加 sessions 表字段
        conn.execute(text("""
            ALTER TABLE sessions ADD COLUMN IF NOT EXISTS knowledge_type VARCHAR(20);
            ALTER TABLE sessions ADD COLUMN IF NOT EXISTS additional_score FLOAT;
        """))
        
        conn.commit()
        print("✅ Tier 0 表迁移完成")

if __name__ == "__main__":
    migrate()
```

---

## 9. 测试策略

### 9.1 单元测试

```python
# backend/tests/test_tier0_ingest.py

import pytest
from app.services.tier0.tier0_ingest_service import Tier0IngestService

@pytest.mark.asyncio
async def test_quality_threshold():
    """测试质量阈值过滤"""
    service = Tier0IngestService()
    
    # 低质量应该被拒绝
    result = await service.auto_ingest(
        session=mock_session,
        session_id=1,
        question="测试问题",
        local_answer="测试答案",
        cloud_corrected="纠正答案",
        quality_result={"overall_score": 3.5},  # < 4.0
        expert_id=1
    )
    
    assert result["status"] == "rejected"
    assert "quality_too_low" in result["reason"]

@pytest.mark.asyncio
async def test_duplicate_detection():
    """测试去重逻辑"""
    service = Tier0IngestService()
    
    # 先入库一条
    result1 = await service.auto_ingest(..., quality_result={"overall_score": 4.5})
    assert result1["status"] == "success"
    
    # 相同问题再次入库应该被拒绝
    result2 = await service.auto_ingest(..., quality_result={"overall_score": 4.2})
    assert result2["status"] == "rejected"
    assert "duplicate" in result2["reason"]
```

### 9.2 集成测试

1. 完整流程测试：提问 → 质检 → 自动入库 → 检索使用
2. 并发测试：多个会话同时触发入库
3. 边界测试：空内容、超长内容、特殊字符

---

## 10. 实施计划

### 阶段1：数据库（1天）
- [ ] 创建 tier0_knowledge 表
- [ ] 添加 sessions 表字段
- [ ] 运行迁移脚本

### 阶段2：后端核心（2天）
- [ ] 创建 Tier0Knowledge 模型
- [ ] 实现 Tier0IngestService
- [ ] 修改 _async_quality_check 触发入库
- [ ] 修改 MultiTierRetriever 支持Tier 0检索

### 阶段3：API与测试（1天）
- [ ] 新增 tier0.py 路由
- [ ] 注册路由
- [ ] 单元测试
- [ ] 集成测试

### 阶段4：验证（1天）
- [ ] 端到端测试
- [ ] 性能测试
- [ ] 论文数据验证

**总计：约5天**

---

## 11. 验收标准

- [ ] Tier 0 表创建成功，包含所有字段
- [ ] 质检评分≥4.0的知识自动入库
- [ ] 相似度≥0.92的知识被去重
- [ ] 检索时优先使用 Tier 0 知识
- [ ] 专家统计正确更新
- [ ] 单元测试覆盖率≥80%

---

**设计者**: AI Assistant  
**审核状态**: 待审核  
**下一步**: 用户审核通过后，编写详细实现计划
