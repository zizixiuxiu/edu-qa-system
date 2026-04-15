"""
导入完整GAOKAO-Bench数据集到系统
支持从下载的 GAOKAO-Bench-main/Data/Objective_Questions 目录导入
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import List, Dict
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import AsyncSessionLocal
from app.models.database import Knowledge
from app.utils.embedding import embedding_service
from sqlalchemy import select


class GaokaoImporter:
    """GAOKAO数据集导入器"""
    
    # 默认数据集路径
    DEFAULT_DATA_DIR = "/Users/zizixiuixu/Downloads/GAOKAO-Bench-main/Data/Objective_Questions"
    
    # 学科文件映射（支持一个学科多个文件）
    SUBJECT_FILES = {
        "数学": ["2010-2022_Math_I_MCQs.json", "2010-2022_Math_II_MCQs.json"],
        "物理": ["2010-2022_Physics_MCQs.json"],
        "化学": ["2010-2022_Chemistry_MCQs.json"],
        "生物": ["2010-2022_Biology_MCQs.json"],
        "语文": ["2010-2022_Chinese_Lang_and_Usage_MCQs.json", "2010-2022_Chinese_Modern_Lit.json"],
        "英语": ["2010-2013_English_MCQs.json", "2010-2022_English_Fill_in_Blanks.json", "2010-2022_English_Reading_Comp.json", "2012-2022_English_Cloze_Test.json"],
        "历史": ["2010-2022_History_MCQs.json"],
        "地理": ["2010-2022_Geography_MCQs.json"],
        "政治": ["2010-2022_Political_Science_MCQs.json"]
    }
    
    def __init__(self, data_dir: str = None):
        """
        初始化导入器
        
        Args:
            data_dir: 数据目录路径，默认使用 GAOKAO-Bench-main/Data/Objective_Questions
        """
        if data_dir is None:
            data_dir = self.DEFAULT_DATA_DIR
        self.data_dir = Path(data_dir)
        self.stats = {subject: 0 for subject in self.SUBJECT_FILES.keys()}
        
    async def import_all(self):
        """导入所有学科数据"""
        print("=" * 70)
        print("🚀 导入 GAOKAO-Bench 数据集到知识库")
        print("=" * 70)
        print(f"数据目录: {self.data_dir}")
        print()
        
        if not self.data_dir.exists():
            print(f"❌ 数据目录不存在: {self.data_dir}")
            print("请确认数据集已下载到正确位置")
            return
        
        start_time = datetime.now()
        total_imported = 0
        
        # 遍历所有学科
        for subject, files in self.SUBJECT_FILES.items():
            count = await self._import_subject(subject, files)
            total_imported += count
            self.stats[subject] = count
        
        # 打印统计
        elapsed = (datetime.now() - start_time).total_seconds()
        print("\n" + "=" * 70)
        print("📊 导入完成")
        print("=" * 70)
        print(f"总导入数量: {total_imported:,} 条")
        print(f"耗时: {elapsed:.1f} 秒")
        print("\n各学科详情:")
        for subject, count in sorted(self.stats.items()):
            status = "✅" if count > 0 else "⚠️"
            print(f"  {status} {subject}: {count:,} 条")
    
    async def _import_subject(self, subject: str, files: List[str]) -> int:
        """导入单个学科的数据（可能分布在多个文件中）"""
        print(f"📚 导入 {subject}...", end=" ")
        
        imported = 0
        all_questions = []
        
        # 从所有文件收集题目
        for file in files:
            file_path = self.data_dir / file
            if file_path.exists():
                questions = self._load_questions_from_file(file_path)
                all_questions.extend(questions)
        
        if not all_questions:
            print("⚠️ 无数据")
            return 0
        
        # 批量导入
        async with AsyncSessionLocal() as session:
            for q in all_questions:
                knowledge = await self._create_knowledge(session, q, subject)
                if knowledge:
                    imported += 1
                    
                # 每50条提交一次
                if imported % 50 == 0:
                    await session.commit()
            
            await session.commit()
        
        print(f"✅ {imported} 条")
        return imported
    
    def _load_questions_from_file(self, file_path: Path) -> List[Dict]:
        """从JSON文件加载题目"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # GAOKAO-Bench格式: {"example": [...]}
            if isinstance(data, dict) and 'example' in data:
                return data['example']
            elif isinstance(data, list):
                return data
            else:
                return []
                
        except Exception as e:
            print(f"\n  警告: 读取 {file_path.name} 失败: {e}")
            return []
    
    async def _create_knowledge(self, session, question: Dict, subject: str) -> Knowledge:
        """创建知识库条目"""
        try:
            # 提取问题内容
            content = question.get('question', '').strip()
            if not content:
                return None
            
            # 提取答案（可能是列表或字符串）
            answer = question.get('answer', [])
            if isinstance(answer, list):
                answer = ', '.join(str(a) for a in answer)
            else:
                answer = str(answer)
            
            # 提取解析
            analysis = question.get('analysis', '').strip()
            
            # 构建完整内容
            full_content = f"【{subject}高考题】\n\n问题:\n{content}\n\n答案: {answer}"
            if analysis:
                full_content += f"\n\n解析:\n{analysis}"
            
            # 生成embedding
            try:
                embedding = await embedding_service.get_embedding(full_content)
            except Exception as e:
                print(f"\n  警告: embedding生成失败: {e}")
                embedding = None
            
            # 创建知识条目
            knowledge = Knowledge(
                content=full_content,
                subject=subject,
                source="GAOKAO-Bench",
                difficulty=self._calculate_difficulty(question),
                embedding=embedding,
                metadata={
                    "year": question.get('year', ''),
                    "category": question.get('category', ''),
                    "type": "objective",
                    "score": question.get('score', 0),
                    "index": question.get('index', 0)
                }
            )
            
            session.add(knowledge)
            return knowledge
            
        except Exception as e:
            print(f"\n  警告: 创建知识条目失败: {e}")
            return None
    
    def _calculate_difficulty(self, question: Dict) -> float:
        """根据分数和年份估算难度"""
        score = question.get('score', 5)
        year = question.get('year', '2020')
        
        # 基础难度（基于分数）
        if score <= 3:
            base_difficulty = 0.3
        elif score <= 5:
            base_difficulty = 0.5
        elif score <= 8:
            base_difficulty = 0.7
        else:
            base_difficulty = 0.9
        
        # 年份因子（新题目可能略难）
        try:
            year_int = int(str(year)[:4])
            if year_int >= 2020:
                year_factor = 0.1
            elif year_int >= 2015:
                year_factor = 0.05
            else:
                year_factor = 0
        except:
            year_factor = 0
        
        return min(1.0, base_difficulty + year_factor)


async def main():
    """主函数"""
    # 支持命令行参数指定路径
    data_dir = sys.argv[1] if len(sys.argv) > 1 else None
    
    importer = GaokaoImporter(data_dir)
    await importer.import_all()


if __name__ == "__main__":
    asyncio.run(main())
