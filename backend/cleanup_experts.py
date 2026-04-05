"""
清理脚本 - 删除非标准学科专家及其关联数据
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_engine
from app.models.database import Expert
from sqlmodel import select
from sqlalchemy import text


async def cleanup_experts():
    """删除非标准学科的专家及其关联数据，只保留固定的10个"""
    
    # 固定的10个学科
    valid_subjects = ["数学", "物理", "化学", "语文", "英语", "生物", "历史", "地理", "政治", "通用"]
    
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker
    
    async_session = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # 查询所有专家
        result = await session.execute(select(Expert))
        all_experts = result.scalars().all()
        
        print(f"当前共有 {len(all_experts)} 个专家")
        print("=" * 50)
        
        # 显示所有专家
        for expert in all_experts:
            status = "✓ 保留" if expert.subject in valid_subjects else "✗ 删除"
            print(f"{status} - ID: {expert.id}, 学科: {expert.subject}, 名称: {expert.name}")
        
        # 删除非标准学科的专家
        to_delete = [e for e in all_experts if e.subject not in valid_subjects]
        
        if not to_delete:
            print("\n没有需要删除的非标准专家")
            return
        
        print("\n" + "=" * 50)
        print(f"正在删除 {len(to_delete)} 个非标准专家及其关联数据...")
        
        for expert in to_delete:
            expert_id = expert.id
            
            # 1. 删除关联的sft_data数据
            await session.execute(
                text("DELETE FROM sft_data WHERE expert_id = :expert_id"),
                {"expert_id": expert_id}
            )
            
            # 2. 删除关联的knowledge数据
            await session.execute(
                text("DELETE FROM knowledge WHERE expert_id = :expert_id"),
                {"expert_id": expert_id}
            )
            
            # 3. 删除关联的sessions数据
            await session.execute(
                text("DELETE FROM sessions WHERE expert_id = :expert_id"),
                {"expert_id": expert_id}
            )
            
            # 4. 最后删除专家
            await session.delete(expert)
            
            print(f"已删除: {expert.name} ({expert.subject})")
        
        await session.commit()
        print("\n删除完成！")
        
        # 显示剩余专家
        result = await session.execute(select(Expert))
        remaining = result.scalars().all()
        print(f"\n剩余 {len(remaining)} 个专家:")
        for expert in remaining:
            print(f"  - {expert.name} ({expert.subject})")


if __name__ == "__main__":
    asyncio.run(cleanup_experts())
