"""检查数据分析相关数据"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_engine
from app.models.database import Session as ChatSession, Knowledge, Expert
from sqlmodel import select, func


async def check_data():
    from sqlalchemy.orm import sessionmaker
    
    async_session = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # 检查会话数据
        total_sessions = await session.execute(select(func.count(ChatSession.id)))
        print(f"总会话数: {total_sessions.scalar()}")
        
        # 按实验模式统计
        modes = ["baseline", "rag_only", "expert_routing", "full_system"]
        for mode in modes:
            count = await session.execute(
                select(func.count(ChatSession.id)).where(ChatSession.experiment_mode == mode)
            )
            print(f"  {mode}: {count.scalar()}")
        
        # 检查知识库数据
        total_knowledge = await session.execute(select(func.count(Knowledge.id)))
        print(f"\n知识库条目数: {total_knowledge.scalar()}")
        
        # 检查专家数据
        experts = await session.execute(select(Expert))
        expert_list = experts.scalars().all()
        print(f"\n专家数量: {len(expert_list)}")
        for e in expert_list:
            print(f"  - {e.name} (QA次数: {e.total_qa_count})")


if __name__ == "__main__":
    asyncio.run(check_data())
