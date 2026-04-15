"""
按比例采样导入数据集
策略：
1. 每个学科最多导入指定数量（避免过多）
2. 选择题和简答题按比例平衡
3. 优先高质量数据源
"""
import asyncio
import json
import random
import sys
import os
from pathlib import Path
from typing import List, Dict
from datetime import datetime

# 设置离线模式，避免网络请求
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import AsyncSessionLocal
from app.models.database import Expert, Knowledge
from app.services.experts.expert_pool import expert_pool
from app.utils.embedding import embedding_service
from sqlalchemy import select


class SampledDatasetImporter:
    """采样导入器"""
    
    # 每个学科的最大导入数量
    SUBJECT_LIMITS = {
        "数学": 3000,
        "物理": 2000,
        "化学": 500,
        "生物": 500,
        "地理": 200,
        "历史": 500,
        "语文": 2000,
        "英语": 3000,
        "通用": 1000,
        "综合": 500
    }
    
    # 题型比例：选择题 : 简答题
    TYPE_RATIO = (0.6, 0.4)
    
    def __init__(self, data_dir: str = "D:/毕设数据集/processed"):
        self.data_dir = Path(data_dir)
        self.stats = {}
    
    async def import_all(self):
        """导入所有学科（按比例采样）"""
        print("=" * 70)
        print("🚀 按比例采样导入数据集")
        print("=" * 70)
        print(f"数据来源: {self.data_dir}")
        print("\n采样策略:")
        print(f"  - 选择题占比: {self.TYPE_RATIO[0]*100:.0f}%")
        print(f"  - 简答题占比: {self.TYPE_RATIO[1]*100:.0f}%")
        print("\n各学科配额:")
        for subject, limit in sorted(self.SUBJECT_LIMITS.items()):
            print(f"  {subject}: {limit} 条")
        print()
        
        start_time = datetime.now()
        total_imported = 0
        
        # 遍历所有学科
        for subject_dir in sorted(self.data_dir.iterdir()):
            if not subject_dir.is_dir():
                continue
            
            subject = subject_dir.name
            if subject not in self.SUBJECT_LIMITS:
                continue
            
            limit = self.SUBJECT_LIMITS[subject]
            count = await self._import_subject_sampled(subject_dir, subject, limit)
            total_imported += count
        
        # 统计
        elapsed = (datetime.now() - start_time).total_seconds()
        print("\n" + "=" * 70)
        print("📊 导入完成")
        print("=" * 70)
        print(f"总导入数量: {total_imported:,} 条")
        print(f"耗时: {elapsed:.1f} 秒")
        print("=" * 70)
        
        # 打印各学科详情
        print("\n各学科导入详情:")
        for subject, stat in sorted(self.stats.items()):
            print(f"  {subject}: {stat['imported']:,} 条 "
                  f"(选择{stat['choice']}, 简答{stat['open']}, 跳过{stat['skipped']})")
    
    async def _import_subject_sampled(self, subject_dir: Path, subject: str, limit: int) -> int:
        """按比例采样导入单个学科"""
        print(f"📚 [{subject}] 采样导入 (上限 {limit} 条)...")
        
        # 读取所有数据
        all_records = self._load_subject_data(subject_dir)
        
        if not all_records:
            print(f"  ⚠️ 无数据")
            return 0
        
        # 分离选择题和简答题
        choice_records = [r for r in all_records if r['type'] == 'choice']
        open_records = [r for r in all_records if r['type'] == 'open']
        
        # 计算采样数量
        choice_limit = int(limit * self.TYPE_RATIO[0])
        open_limit = int(limit * self.TYPE_RATIO[1])
        
        # 随机采样
        sampled_choice = self._sample_records(choice_records, choice_limit)
        sampled_open = self._sample_records(open_records, open_limit)
        
        # 合并并打乱
        sampled = sampled_choice + sampled_open
        random.shuffle(sampled)
        
        # 限制总数
        sampled = sampled[:limit]
        
        print(f"  原数据: {len(all_records):,} 条 (选择{len(choice_records)}, 简答{len(open_records)})")
        print(f"  采样后: {len(sampled)} 条 (选择{len(sampled_choice)}, 简答{len(sampled_open)})")
        
        # 导入到数据库
        imported = await self._import_records(subject, sampled)
        
        self.stats[subject] = {
            'imported': imported,
            'choice': len(sampled_choice),
            'open': len(sampled_open),
            'skipped': len(sampled) - imported
        }
        
        print(f"  ✅ 成功导入 {imported} 条\n")
        return imported
    
    def _load_subject_data(self, subject_dir: Path) -> List[Dict]:
        """加载学科所有数据"""
        records = []
        
        for jsonl_file in subject_dir.glob("*.jsonl"):
            if jsonl_file.name == 'statistics.json':
                continue
            
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        item = json.loads(line.strip())
                        
                        question = item.get('question', '')
                        answer = item.get('answer', '')
                        
                        if not question or not answer:
                            continue
                        
                        # 构建内容 - 只包含问题（用于RAG检索，避免泄露答案）
                        content = f"问题: {question}"
                        
                        # 选择题添加选项（不含正确答案）
                        choices = item.get('choices', [])
                        if item.get('type') == 'choice' and choices:
                            choices_text = ' | '.join(str(c) for c in choices[:4])
                            content += f"\n选项: {choices_text}"
                        
                        # 答案和元数据（用于评估，不用于RAG）
                        meta_data = {
                            'answer': answer,
                            'choices': choices,
                            'full_content': f"问题: {question}\n答案: {answer}",
                            'answer_idx': item.get('answer_idx')
                        }
                        
                        records.append({
                            'content': content,
                            'meta_data': meta_data,
                            'type': item.get('type', 'open'),
                            'source': item.get('dataset', 'unknown'),
                            'quality': 0.9 if item.get('type') == 'choice' else 0.8
                        })
                        
                    except:
                        continue
        
        return records
    
    def _sample_records(self, records: List[Dict], limit: int) -> List[Dict]:
        """采样记录"""
        if len(records) <= limit:
            return records
        
        # 随机采样
        return random.sample(records, limit)
    
    async def _import_records(self, subject: str, records: List[Dict]) -> int:
        """导入记录到数据库"""
        if not records:
            return 0
        
        imported = 0
        batch_size = 50
        
        async with AsyncSessionLocal() as session:
            # 获取专家
            expert = await expert_pool.get_or_create_expert(session, subject)
            
            # 批量导入
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                
                for record in batch:
                    try:
                        # 检查重复
                        is_dup = await self._check_duplicate(session, expert.id, record['content'])
                        if is_dup:
                            continue
                        
                        # 生成embedding
                        embedding = embedding_service.encode(record['content'])
                        
                        # 创建知识（content只含问题，meta_data存答案）
                        knowledge = Knowledge(
                            expert_id=expert.id,
                            content=record['content'],
                            meta_data=record.get('meta_data'),
                            embedding=embedding,
                            source_type=record['source'],
                            quality_score=record['quality']
                        )
                        session.add(knowledge)
                        imported += 1
                        
                    except Exception as e:
                        print(f"    ⚠️ 导入失败: {e}")
                        continue
                
                # 提交批次
                await session.commit()
                print(f"    进度: {min(i + batch_size, len(records))}/{len(records)}", end='\r')
            
            # 更新专家计数
            expert.knowledge_count += imported
            await session.commit()
        
        return imported
    
    async def _check_duplicate(self, session, expert_id: int, content: str) -> bool:
        """检查重复"""
        preview = content[:50]
        statement = select(Knowledge).where(
            Knowledge.expert_id == expert_id,
            Knowledge.content.like(f"%{preview}%")
        ).limit(1)
        result = await session.execute(statement)
        return result.scalar_one_or_none() is not None


async def main():
    """主函数"""
    importer = SampledDatasetImporter()
    await importer.import_all()
    
    print("\n🎉 采样导入完成！")
    print("\n现在可以启动服务:")
    print("  后端: uvicorn app.main:app --reload")
    print("  前端: cd frontend && npm run dev")


if __name__ == "__main__":
    asyncio.run(main())
