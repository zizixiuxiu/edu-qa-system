"""详细读取论文关键章节"""
import sys
sys.path.insert(0, 'backend')

from docx import Document

doc_path = r"D:\下载\智能科学与技术-22智科1班-王美镪-229990230-基于专家模型路由的多模态教育知识问答系统设计与实现 (2).docx"
doc = Document(doc_path)

# 读取所有段落
all_paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

print("=" * 80)
print("论文详细功能点分析")
print("=" * 80)

# 查找关键章节
sections = {
    "功能需求": [],
    "系统架构": [],
    "专家网络": [],
    "多模态": [],
    "RAG/知识库": [],
    "自我迭代": [],
    "实验/评测": [],
    "数据库": []
}

keywords_map = {
    "功能需求": ["功能需求", "用例", "功能模块", "系统功能"],
    "系统架构": ["系统架构", "总体设计", "分层架构", "微服务"],
    "专家网络": ["专家", "路由", "学科", "专家池"],
    "多模态": ["多模态", "图片", "图像", "Qwen3-VL", "ViT"],
    "RAG/知识库": ["RAG", "知识库", "检索", "向量", "pgvector", "BGE"],
    "自我迭代": ["自我迭代", "自我进化", "云端质检", "知识蒸馏", "微调"],
    "实验/评测": ["实验", "评测", "准确率", "对比", "消融"],
    "数据库": ["数据库", "表结构", "数据模型"]
}

for para in all_paragraphs:
    for section, keywords in keywords_map.items():
        for kw in keywords:
            if kw in para and len(para) < 300:
                sections[section].append(para)
                break

# 打印各分类的关键点（去重）
for section, contents in sections.items():
    print(f"\n【{section}】")
    seen = set()
    for c in contents[:10]:  # 每类最多10条
        if c not in seen:
            print(f"  - {c[:100]}")
            seen.add(c)

print("\n\n" + "=" * 80)
print("完整段落列表（前150段）")
print("=" * 80)
for i, para in enumerate(all_paragraphs[:150]):
    if len(para) > 20:
        print(f"{i+1:3d}. {para[:120]}")
