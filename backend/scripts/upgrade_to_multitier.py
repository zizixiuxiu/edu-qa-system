"""
一键升级脚本：启用多级RAG
"""
import os
import sys
import shutil

# 路径配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPERTS_DIR = os.path.join(BASE_DIR, "app", "services", "experts")
RAG_DIR = os.path.join(BASE_DIR, "app", "services", "rag")

def check_data():
    """检查数据是否就绪"""
    data_dir = "D:/毕设数据集/processed"
    
    if not os.path.exists(data_dir):
        print(f"❌ 数据目录不存在: {data_dir}")
        print("请先运行数据处理脚本")
        return False
    
    # 统计文件
    subjects = []
    for item in os.listdir(data_dir):
        item_path = os.path.join(data_dir, item)
        if os.path.isdir(item_path):
            jsonl_files = [f for f in os.listdir(item_path) if f.endswith('.jsonl')]
            if jsonl_files:
                subjects.append(item)
    
    print(f"✅ 找到 {len(subjects)} 个学科数据: {', '.join(subjects)}")
    return True

def backup_original():
    """备份原始文件"""
    original_file = os.path.join(EXPERTS_DIR, "llm_service.py")
    backup_file = os.path.join(EXPERTS_DIR, "llm_service.py.bak")
    
    if os.path.exists(original_file) and not os.path.exists(backup_file):
        shutil.copy2(original_file, backup_file)
        print("✅ 已备份原始 llm_service.py")

def switch_to_enhanced():
    """切换到增强版"""
    original_file = os.path.join(EXPERTS_DIR, "llm_service.py")
    enhanced_file = os.path.join(EXPERTS_DIR, "llm_service_enhanced.py")
    
    if not os.path.exists(enhanced_file):
        print(f"❌ 增强版文件不存在: {enhanced_file}")
        return False
    
    # 修改导入（可选）
    # 方法1: 重命名文件
    # shutil.move(original_file, os.path.join(EXPERTS_DIR, "llm_service_original.py"))
    # shutil.copy2(enhanced_file, original_file)
    
    # 方法2: 修改 __init__.py（推荐）
    init_file = os.path.join(EXPERTS_DIR, "__init__.py")
    
    if os.path.exists(init_file):
        with open(init_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否已经修改
        if "llm_service_enhanced" not in content:
            # 添加注释和导入
            new_content = '''# 使用增强版LLM服务（多级RAG）
# from .llm_service import llm_service
from .llm_service_enhanced import enhanced_llm_service as llm_service

__all__ = ["llm_service"]
'''
            with open(init_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print("✅ 已修改 __init__.py 使用增强版服务")
        else:
            print("ℹ️ 已经是增强版配置")
    else:
        # 创建 __init__.py
        with open(init_file, 'w', encoding='utf-8') as f:
            f.write('from .llm_service_enhanced import enhanced_llm_service as llm_service\n')
        print("✅ 创建 __init__.py 使用增强版服务")
    
    return True

def check_rag_service():
    """检查RAG服务是否存在"""
    if not os.path.exists(RAG_DIR):
        print(f"❌ RAG目录不存在: {RAG_DIR}")
        print("请确保 rag/ 目录已创建")
        return False
    
    required_files = ["__init__.py", "multi_tier_retrieval.py"]
    for f in required_files:
        file_path = os.path.join(RAG_DIR, f)
        if not os.path.exists(file_path):
            print(f"❌ 缺少文件: {file_path}")
            return False
    
    print("✅ RAG服务文件检查通过")
    return True

def print_next_steps():
    """打印下一步操作"""
    print("\n" + "="*60)
    print("🎉 升级完成！")
    print("="*60)
    print("\n下一步操作:")
    print("1. 安装依赖 (如果需要):")
    print("   pip install sentence-transformers")
    print("\n2. 预构建向量缓存 (推荐):")
    print("   python scripts/build_vector_cache.py")
    print("\n3. 启动服务测试:")
    print("   python -m app.main")
    print("\n4. 访问测试:")
    print("   POST http://localhost:8000/chat/send")
    print("   Body: {\"query\": \"勾股定理是什么？\"}")
    print("\n" + "="*60)

def main():
    print("🚀 多级RAG升级脚本")
    print("="*60)
    
    # 检查数据
    if not check_data():
        sys.exit(1)
    
    # 备份
    backup_original()
    
    # 检查RAG服务
    if not check_rag_service():
        sys.exit(1)
    
    # 切换
    if not switch_to_enhanced():
        sys.exit(1)
    
    print_next_steps()

if __name__ == "__main__":
    main()
