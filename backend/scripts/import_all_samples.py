"""
一键导入所有示例知识点

使用:
    python scripts/import_all_samples.py
"""

import asyncio
import sys
from pathlib import Path

# 添加backend到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.import_knowledge import KnowledgeImporter


async def main():
    """导入所有示例知识点"""
    
    print("🚀 开始导入示例知识点...\n")
    
    importer = KnowledgeImporter()
    
    # 示例文件列表
    samples = [
        ("data/knowledge_samples/数学_函数.json", "数学"),
        ("data/knowledge_samples/物理_力学.json", "物理"),
        ("data/knowledge_samples/化学_基础.json", "化学"),
        ("data/knowledge_samples/语文_文言文.md", "语文"),
    ]
    
    total_count = 0
    
    for file_path, subject in samples:
        full_path = Path(__file__).parent.parent / file_path
        
        if not full_path.exists():
            print(f"⚠️ 文件不存在: {file_path}")
            continue
        
        print(f"📖 正在导入 {subject} 知识点...")
        result = await importer.import_file(str(full_path), subject)
        
        if result['success']:
            print(f"  ✅ 成功导入 {result['count']} 条知识点\n")
            total_count += result['count']
        else:
            print(f"  ❌ 导入失败: {result.get('error')}\n")
    
    print(f"🎉 全部完成！共导入 {total_count} 条知识点")
    print("\n现在可以:")
    print("  1. 启动后端: python start_backend.py")
    print("  2. 启动前端: cd frontend && npm run dev")
    print("  3. 访问 http://localhost:3000 查看知识库")


if __name__ == '__main__':
    asyncio.run(main())
