"""
知识库导入工具
支持格式: JSON, TXT, PDF, Markdown

使用示例:
    python scripts/import_knowledge.py --file data/数学知识点.json --subject 数学
    python scripts/import_knowledge.py --dir data/知识点/ --subject 物理
"""

import asyncio
import json
import os
import re
import argparse
from pathlib import Path
from typing import List, Dict, Optional

# 添加backend到路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import AsyncSessionLocal
from app.models.database import Expert, Knowledge
from app.utils.embedding import embedding_service


class KnowledgeImporter:
    """知识库导入器"""
    
    def __init__(self):
        self.supported_formats = ['.json', '.txt', '.md', '.pdf']
    
    async def import_file(
        self, 
        file_path: str, 
        subject: str,
        source_type: str = "imported"
    ) -> Dict:
        """
        导入单个文件到知识库
        
        Args:
            file_path: 文件路径
            subject: 学科名称
            source_type: 来源类型
        
        Returns:
            {"success": True, "count": 导入数量}
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            return {"success": False, "error": f"文件不存在: {file_path}"}
        
        suffix = file_path.suffix.lower()
        
        if suffix == '.json':
            knowledges = self._parse_json(file_path)
        elif suffix == '.txt':
            knowledges = self._parse_txt(file_path)
        elif suffix == '.md':
            knowledges = self._parse_markdown(file_path)
        elif suffix == '.pdf':
            knowledges = self._parse_pdf(file_path)
        else:
            return {"success": False, "error": f"不支持的文件格式: {suffix}"}
        
        # 导入到数据库
        async with AsyncSessionLocal() as session:
            # 获取或创建专家
            from app.services.experts.expert_pool import expert_pool
            expert = await expert_pool.get_or_create_expert(session, subject)
            
            count = 0
            for content in knowledges:
                if len(content) < 20:  # 过滤太短的
                    continue
                
                # 检查重复
                existing = await self._check_duplicate(session, expert.id, content)
                if existing:
                    continue
                
                # 生成embedding
                embedding = embedding_service.encode(content)
                
                # 创建知识条目
                knowledge = Knowledge(
                    expert_id=expert.id,
                    content=content,
                    embedding=embedding,
                    source_type=source_type,
                    quality_score=0.8  # 默认质量分
                )
                session.add(knowledge)
                count += 1
            
            await session.commit()
            
            # 更新专家知识计数
            expert.knowledge_count += count
            await session.commit()
        
        return {"success": True, "count": count, "subject": subject}
    
    async def import_directory(
        self, 
        dir_path: str, 
        subject: Optional[str] = None
    ) -> List[Dict]:
        """
        导入整个目录
        
        Args:
            dir_path: 目录路径
            subject: 学科名称，如果为None则从文件名推断
        """
        dir_path = Path(dir_path)
        results = []
        
        for file_path in dir_path.rglob('*'):
            if file_path.suffix.lower() in self.supported_formats:
                # 从文件名或目录推断学科
                file_subject = subject or self._infer_subject(file_path)
                
                result = await self.import_file(file_path, file_subject)
                results.append({
                    "file": str(file_path),
                    **result
                })
        
        return results
    
    def _parse_json(self, file_path: Path) -> List[str]:
        """解析JSON文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        knowledges = []
        
        # 支持多种JSON格式
        if isinstance(data, list):
            for item in data:
                if isinstance(item, str):
                    knowledges.append(item)
                elif isinstance(item, dict):
                    # 尝试提取内容字段
                    content = item.get('content') or item.get('text') or item.get('knowledge') or item.get('知识点')
                    if content:
                        knowledges.append(content)
        elif isinstance(data, dict):
            # 处理嵌套结构
            for key, value in data.items():
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, str):
                            knowledges.append(item)
                        elif isinstance(item, dict):
                            content = item.get('content') or item.get('text') or item.get('knowledge')
                            if content:
                                knowledges.append(content)
        
        return knowledges
    
    def _parse_txt(self, file_path: Path) -> List[str]:
        """解析TXT文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 按段落或编号分割
        # 支持格式：1. xxx 或 - xxx 或 换行分割
        patterns = [
            r'\d+[\.、]\s*([^\n]+)',  # 1. xxx 或 1、xxx
            r'[-•]\s*([^\n]+)',        # - xxx 或 • xxx
        ]
        
        knowledges = []
        for pattern in patterns:
            matches = re.findall(pattern, content)
            if len(matches) >= 3:  # 如果匹配到3个以上，认为有效
                knowledges.extend(matches)
                break
        
        # 如果没有匹配到，按段落分割
        if not knowledges:
            paragraphs = [p.strip() for p in content.split('\n\n') if len(p.strip()) > 20]
            knowledges = paragraphs
        
        return knowledges
    
    def _parse_markdown(self, file_path: Path) -> List[str]:
        """解析Markdown文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        knowledges = []
        
        # 提取标题和内容
        # 匹配 ## 标题 和下面的内容
        sections = re.split(r'\n##+\s*', content)
        
        for section in sections:
            if len(section.strip()) > 20:
                # 清理markdown标记
                clean = re.sub(r'[#*_`\[\]()]', '', section)
                clean = re.sub(r'\n+', '\n', clean)
                knowledges.append(clean.strip())
        
        return knowledges
    
    def _parse_pdf(self, file_path: Path) -> List[str]:
        """解析PDF文件"""
        try:
            import PyPDF2
        except ImportError:
            print("请先安装 PyPDF2: pip install PyPDF2")
            return []
        
        knowledges = []
        
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    # 按句子或段落分割
                    paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 30]
                    knowledges.extend(paragraphs)
        
        return knowledges
    
    def _infer_subject(self, file_path: Path) -> str:
        """从文件名推断学科"""
        filename = file_path.name.lower()
        
        # 学科关键词映射
        subject_map = {
            '数学': ['math', '数学', 'algebra', 'geometry', 'calculus'],
            '物理': ['physics', '物理', '力学', '电磁'],
            '化学': ['chemistry', '化学', '元素', '化合物'],
            '生物': ['biology', '生物', '细胞', '基因'],
            '语文': ['chinese', '语文', '文学', '文言文'],
            '英语': ['english', '英语', 'grammar'],
            '历史': ['history', '历史', '朝代'],
            '地理': ['geography', '地理', '地图'],
            '政治': ['politics', '政治', '思政'],
        }
        
        for subject, keywords in subject_map.items():
            if any(kw in filename for kw in keywords):
                return subject
        
        # 从父目录推断
        parent = file_path.parent.name.lower()
        for subject, keywords in subject_map.items():
            if any(kw in parent for kw in keywords):
                return subject
        
        return "通用"
    
    async def _check_duplicate(
        self, 
        session, 
        expert_id: int, 
        content: str
    ) -> bool:
        """检查是否重复（简单对比）"""
        from sqlalchemy import select
        
        # 简化：检查内容相似度
        statement = select(Knowledge).where(
            Knowledge.expert_id == expert_id
        )
        
        result = await session.execute(statement)
        existing = result.scalars().all()
        
        for k in existing:
            # 简单对比，如果内容相似度>80%认为是重复
            if self._similarity(content, k.content) > 0.8:
                return True
        
        return False
    
    def _similarity(self, s1: str, s2: str) -> float:
        """计算两个字符串的相似度（简化版）"""
        # 使用Jaccard相似度
        set1 = set(s1.lower())
        set2 = set(s2.lower())
        
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0


async def main():
    parser = argparse.ArgumentParser(description='导入知识点到知识库')
    parser.add_argument('--file', '-f', help='单个文件路径')
    parser.add_argument('--dir', '-d', help='目录路径')
    parser.add_argument('--subject', '-s', required=True, help='学科名称')
    
    args = parser.parse_args()
    
    if not args.file and not args.dir:
        parser.print_help()
        return
    
    importer = KnowledgeImporter()
    
    if args.file:
        print(f"📖 正在导入文件: {args.file}")
        result = await importer.import_file(args.file, args.subject)
        
        if result['success']:
            print(f"✅ 成功导入 {result['count']} 条知识点")
        else:
            print(f"❌ 导入失败: {result.get('error')}")
    
    elif args.dir:
        print(f"📁 正在导入目录: {args.dir}")
        results = await importer.import_directory(args.dir, args.subject)
        
        total = sum(r['count'] for r in results if r.get('success'))
        print(f"✅ 共导入 {total} 条知识点")


if __name__ == '__main__':
    asyncio.run(main())
