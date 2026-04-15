"""
批量导入处理好的数据集到知识库
支持18万条数据高效导入
"""
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import List, Dict
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import AsyncSessionLocal
from app.models.database import Expert, Knowledge
from app.services.experts.expert_pool import expert_pool
from app.utils.embedding import embedding_service
from sqlalchemy import select


class DatasetImporter:
    """数据集批量导入器"""
    
    def __init__(self, data_dir: str = "D:/毕设数据集/processed"):
        self.data_dir = Path(data_dir)
        self.batch_size = 100  # 每批处理数量
        self.stats = {
            "total_files": 0,
            "total_records": 0,
            "imported": 0,
            "skipped": 0,
            "failed": 0
        }
    
    async def import_all(self):
        """导入所有学科数据"""
        print("=" * 60)
        print("🚀 批量导入数据集到知识库")
        print("=" * 60)
        print(f"数据来源: {self.data_dir}")
        print(f"批量大小: {self.batch_size}")
        print()
        
        start_time = datetime.now()
        
        # 遍历所有学科目录
        for subject_dir in sorted(self.data_dir.iterdir()):
            if not subject_dir.is_dir():
                continue
            
            subject = subject_dir.name
            
            # 跳过非学科目录
            if subject in ['statistics.json']:
                continue
            
            await self._import_subject(subject_dir, subject)
        
        # 打印统计
        elapsed = (datetime.now() - start_time).total_seconds()
        print("\n" + "=" * 60)
        print("📊 导入统计")
        print("=" * 60)
        print(f"总文件数: {self.stats['total_files']}")
        print(f"总记录数: {self.stats['total_records']:,}")
        print(f"成功导入: {self.stats['imported']:,}")
        print(f"跳过重复: {self.stats['skipped']:,}")
        print(f"失败: {self.stats['failed']:,}")
        print(f"耗时: {elapsed:.1f} 秒 ({elapsed/60:.1f} 分钟)")
        print("=" * 60)
    
    async def _import_subject(self, subject_dir: Path, subject: str):
        """导入单个学科的数据"""
        print(f"\n📚 导入 [{subject}] ...")
        
        # 查找所有JSONL文件
        jsonl_files = list(subject_dir.glob("*.jsonl"))
        
        if not jsonl_files:
            print(f"  ⚠️ 未找到数据文件")
            return
        
        async with AsyncSessionLocal() as session:
            # 获取或创建专家
            expert = await expert_pool.get_or_create_expert(session, subject)
            
            subject_imported = 0
            subject_skipped = 0
            
            for jsonl_file in jsonl_files:
                self.stats['total_files'] += 1
                
                # 读取并处理文件
                records = await self._process_jsonl(jsonl_file)
                
                if not records:
                    continue
                
                # 批量导入
                for i in range(0, len(records), self.batch_size):
                    batch = records[i:i + self.batch_size]
                    
                    for record in batch:
                        try:
                            # 检查重复
                            is_duplicate = await self._check_duplicate(
                                session, expert.id, record['content']
                            )
                            
                            if is_duplicate:
                                self.stats['skipped'] += 1
                                subject_skipped += 1
                                continue
                            
                            # 生成embedding
                            embedding = embedding_service.encode(record['content'])
                            
                            # 创建知识条目
                            knowledge = Knowledge(
                                expert_id=expert.id,
                                content=record['content'],
                                embedding=embedding,
                                source_type=record.get('source', 'dataset'),
                                quality_score=record.get('quality', 0.8)
                            )
                            session.add(knowledge)
                            subject_imported += 1
                            self.stats['imported'] += 1
                            
                        except Exception as e:
                            self.stats['failed'] += 1
                            print(f"  ⚠️ 导入失败: {e}")
                    
                    # 每批提交
                    await session.commit()
                    print(f"  进度: {min(i + self.batch_size, len(records))}/{len(records)}", end='\r')
            
            # 更新专家计数
            expert.knowledge_count += subject_imported
            await session.commit()
            
            print(f"  ✅ 导入 {subject_imported} 条, 跳过 {subject_skipped} 条")
    
    async def _process_jsonl(self, file_path: Path) -> List[Dict]:
        """处理JSONL文件"""
        records = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        item = json.loads(line.strip())
                        
                        # 构建知识内容
                        question = item.get('question', '')
                        answer = item.get('answer', '')
                        
                        if not question or not answer:
                            continue
                        
                        # 格式化内容
                        content = f"问题: {question}\n答案: {answer}"
                        
                        # 选择题添加选项信息
                        if item.get('type') == 'choice' and item.get('choices'):
                            choices = item['choices'][:4]
                            content += f"\n选项: {' | '.join(str(c) for c in choices)}"
                        
                        records.append({
                            'content': content,
                            'source': item.get('dataset', file_path.stem),
                            'quality': 0.9 if item.get('type') == 'choice' else 0.8
                        })
                        
                        self.stats['total_records'] += 1
                        
                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        print(f"  ⚠️ 第 {line_num} 行处理失败: {e}")
                        continue
                        
        except Exception as e:
            print(f"  ❌ 文件读取失败 {file_path}: {e}")
        
        return records
    
    async def _check_duplicate(self, session, expert_id: int, content: str) -> bool:
        """检查是否重复"""
        # 简化：只检查前100个字符
        content_preview = content[:100]
        
        statement = select(Knowledge).where(
            Knowledge.expert_id == expert_id,
            Knowledge.content.like(f"%{content_preview}%")
        ).limit(1)
        
        result = await session.execute(statement)
        return result.scalar_one_or_none() is not None


async def main():
    """主函数"""
    importer = DatasetImporter()
    await importer.import_all()
    
    print("\n💡 提示:")
    print("  现在可以启动服务测试: uvicorn app.main:app --reload")


if __name__ == "__main__":
    asyncio.run(main())
