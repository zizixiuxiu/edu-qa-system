"""
数据库迁移脚本 - 为现有知识添加knowledge_type字段
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_engine
from app.models.database import Knowledge, Expert
from sqlmodel import select
from sqlalchemy import text


async def migrate_knowledge_type():
    """为现有知识库数据自动分类knowledge_type"""
    
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker
    
    async_session = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # 检查是否需要添加列（如果没有knowledge_type列）
        try:
            result = await session.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_name='knowledge' AND column_name='knowledge_type'")
            )
            if not result.scalar_one_or_none():
                print("添加knowledge_type列...")
                await session.execute(
                    text("ALTER TABLE knowledge ADD COLUMN knowledge_type VARCHAR(20) DEFAULT 'qa'")
                )
                await session.execute(
                    text("CREATE INDEX idx_knowledge_type ON knowledge(knowledge_type)")
                )
                await session.commit()
                print("列添加完成")
        except Exception as e:
            print(f"列检查/添加出错（可能已存在）: {e}")
        
        # 获取所有知识
        result = await session.execute(select(Knowledge))
        knowledges = result.scalars().all()
        
        print(f"\n共有 {len(knowledges)} 条知识需要分类")
        print("=" * 50)
        
        # 分类统计
        type_counts = {"qa": 0, "concept": 0, "formula": 0, "template": 0, "step": 0}
        
        for knowledge in knowledges:
            content = knowledge.content.lower()
            
            # 简单的规则分类
            if any(kw in content for kw in ["公式", "=", "定理", "定律", "计算"]):
                knowledge_type = "formula"
            elif any(kw in content for kw in ["定义", "概念", "是什么", "含义"]):
                knowledge_type = "concept"
            elif any(kw in content for kw in ["步骤", "第一步", "流程", "方法"]):
                knowledge_type = "step"
            elif any(kw in content for kw in ["模板", "格式", "范文", "示例"]):
                knowledge_type = "template"
            else:
                knowledge_type = "qa"
            
            # 更新知识类型
            knowledge.knowledge_type = knowledge_type
            type_counts[knowledge_type] += 1
            
            print(f"ID {knowledge.id}: {knowledge_type} - {knowledge.content[:40]}...")
        
        # 提交更新
        await session.commit()
        
        print("\n" + "=" * 50)
        print("迁移完成！分类统计：")
        for ktype, count in type_counts.items():
            print(f"  {ktype}: {count} 条")


if __name__ == "__main__":
    asyncio.run(migrate_knowledge_type())
