"""读取论文docx文件"""
import sys
sys.path.insert(0, 'backend')

try:
    from docx import Document
except ImportError:
    print("需要安装 python-docx: pip install python-docx")
    sys.exit(1)

# 读取论文
doc_path = r"D:\下载\智能科学与技术-22智科1班-王美镪-229990230-基于专家模型路由的多模态教育知识问答系统设计与实现 (2).docx"

doc = Document(doc_path)

print("=" * 80)
print("论文内容提取")
print("=" * 80)

# 提取所有段落
full_text = []
for para in doc.paragraphs[:100]:  # 只取前100段避免太长
    if para.text.strip():
        full_text.append(para.text)

# 打印关键部分
for i, text in enumerate(full_text):
    print(f"{i+1}. {text[:150]}")

print("\n\n" + "=" * 80)
print("查找功能相关段落")
print("=" * 80)

# 查找功能相关关键词
keywords = [
    "功能", "模块", "系统架构", "总体架构", "设计", "实现",
    "知识库", "RAG", "专家", "路由", "评测", "实验",
    "迭代", "微调", "多模态", "问答", "训练"
]

for i, text in enumerate(full_text):
    for kw in keywords:
        if kw in text and len(text) < 200:
            print(f"- {text}")
            break
