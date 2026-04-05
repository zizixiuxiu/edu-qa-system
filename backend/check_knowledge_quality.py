"""检查知识库数据质量分布"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_engine
from app.models.database import Knowledge, Expert
from sqlmodel import select, func


async def check_knowledge():
    from sqlalchemy.orm import sessionmaker
    
    async_session = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # 总体统计
        total = await session.execute(select(func.count(Knowledge.id)))
        print(f"知识库总量: {total.scalar()} 条")
        
        # 按来源类型统计
        print("\n按来源类型:")
        for source in ["generated", "wrong_answer_extracted", "manual"]:
            count = await session.execute(
                select(func.count(Knowledge.id)).where(Knowledge.source_type == source)
            )
            print(f"  {source}: {count.scalar()} 条")
        
        # 按质量分统计
        print("\n按质量分分布:")
        high = await session.execute(
            select(func.count(Knowledge.id)).where(Knowledge.quality_score >= 4)
        )
        medium = await session.execute(
            select(func.count(Knowledge.id)).where(
                Knowledge.quality_score >= 3, 
                Knowledge.quality_score < 4
            )
        )
        low = await session.execute(
            select(func.count(Knowledge.id)).where(Knowledge.quality_score < 3)
        )
        print(f"  高质量(>=4.0): {high.scalar()} 条")
        print(f"  中等(3.0-4.0): {medium.scalar()} 条")
        print(f"  低质量(<3.0): {low.scalar()} 条")
        
        # 按专家统计
        print("\n各学科知识库数量:")
        result = await session.execute(
            select(Expert.name, Expert.subject, func.count(Knowledge.id))
            .join(Knowledge, Knowledge.expert_id == Expert.id)
            .group_by(Expert.id)
        )
        for name, subject, count in result.all():
            print(f"  {name} ({subject}): {count} 条")
        
        # 显示几条示例
        print("\n最近添加的知识示例:")
        result = await session.execute(
            select(Knowledge, Expert.name)
            .join(Expert, Knowledge.expert_id == Expert.id)
            .order_by(Knowledge.created_at.desc())
            .limit(3)
        )
        for k, expert_name in result.all():
            print(f"\n  [{expert_name}] 质量分: {k.quality_score}")
            content = k.content[:200] + "..." if len(k.content) > 200 else k.content
            print(f"  {content}")


if __name__ == "__main__":
    asyncio.run(check_knowledge())
