#!/usr/bin/env python3
"""
验证 GAOKAO-Bench 数据集配置
测试数据读取和系统绑定是否正常
"""

import json
import sys
from pathlib import Path

# 数据集路径
GAOKAO_PATH = "/Users/zizixiuixu/Downloads/GAOKAO-Bench-main"
OBJECTIVE_PATH = Path(GAOKAO_PATH) / "Data" / "Objective_Questions"
SUBJECTIVE_PATH = Path(GAOKAO_PATH) / "Data" / "Subjective_Questions"

# 学科映射
SUBJECTS = {
    "数学": ["2010-2022_Math_I_MCQs.json", "2010-2022_Math_II_MCQs.json"],
    "物理": ["2010-2022_Physics_MCQs.json"],
    "化学": ["2010-2022_Chemistry_MCQs.json"],
    "生物": ["2010-2022_Biology_MCQs.json"],
    "语文": ["2010-2022_Chinese_Lang_and_Usage_MCQs.json", "2010-2022_Chinese_Modern_Lit.json"],
    "英语": ["2010-2013_English_MCQs.json", "2010-2022_English_Fill_in_Blanks.json", "2010-2022_English_Reading_Comp.json"],
    "历史": ["2010-2022_History_MCQs.json"],
    "地理": ["2010-2022_Geography_MCQs.json"],
    "政治": ["2010-2022_Political_Science_MCQs.json"]
}

def verify_dataset():
    """验证数据集"""
    print("=" * 70)
    print("🔍 GAOKAO-Bench 数据集验证")
    print("=" * 70)
    print(f"数据集路径: {GAOKAO_PATH}")
    print()
    
    # 检查路径
    if not Path(GAOKAO_PATH).exists():
        print("❌ 数据集路径不存在!")
        return False
    
    if not OBJECTIVE_PATH.exists():
        print(f"❌ 客观题目录不存在: {OBJECTIVE_PATH}")
        return False
    
    print("✅ 数据集路径正常")
    print(f"✅ 客观题目录: {OBJECTIVE_PATH}")
    print()
    
    # 检查各学科数据
    print("📊 数据详情:")
    total_questions = 0
    
    for subject, files in SUBJECTS.items():
        subject_count = 0
        found_files = []
        
        for file in files:
            file_path = OBJECTIVE_PATH / file
            if file_path.exists():
                found_files.append(file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        count = len(data.get('example', []))
                        subject_count += count
                except Exception as e:
                    print(f"  ⚠️  {file}: 读取失败 - {e}")
        
        if found_files:
            print(f"  ✅ {subject}: {subject_count} 题 ({len(found_files)} 个文件)")
            total_questions += subject_count
        else:
            print(f"  ⚠️  {subject}: 未找到数据文件")
    
    print(f"\n📈 总计: {total_questions} 道客观题")
    return True

def show_sample():
    """显示示例题目"""
    print("\n" + "=" * 70)
    print("📝 示例题目")
    print("=" * 70)
    
    # 找一个数学题目作为示例
    sample_file = OBJECTIVE_PATH / "2010-2022_Math_I_MCQs.json"
    
    if not sample_file.exists():
        print("示例文件不存在")
        return
    
    try:
        with open(sample_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            questions = data.get('example', [])
            
        if questions:
            q = questions[0]
            print(f"\n学科: 数学")
            print(f"年份: {q.get('year', 'N/A')}")
            print(f"类型: {q.get('category', 'N/A')}")
            print(f"分值: {q.get('score', 'N/A')}")
            print(f"\n题目:\n{q.get('question', 'N/A')[:300]}...")
            print(f"\n答案: {q.get('answer', 'N/A')}")
            
    except Exception as e:
        print(f"读取示例失败: {e}")

def check_system_integration():
    """检查系统集成"""
    print("\n" + "=" * 70)
    print("⚙️  系统集成检查")
    print("=" * 70)
    
    # 检查 benchmark.py
    benchmark_file = Path("backend/app/api/benchmark.py")
    if benchmark_file.exists():
        content = benchmark_file.read_text(encoding='utf-8')
        if GAOKAO_PATH in content:
            print("✅ benchmark.py 已配置正确路径")
        else:
            print("⚠️  benchmark.py 路径配置可能需要更新")
    
    # 检查导入脚本
    import_script = Path("backend/scripts/import_gaokao_full.py")
    if import_script.exists():
        print("✅ 导入脚本存在")
    else:
        print("❌ 导入脚本不存在")
    
    # 检查环境变量配置
    env_file = Path("backend/.env.gaokao")
    if env_file.exists():
        print(f"✅ 环境配置文件: {env_file}")
        content = env_file.read_text()
        if GAOKAO_PATH in content:
            print("  ✅ 环境变量配置正确")
    
    print("\n💡 启动后端前，请运行:")
    print(f"   export GAOKAO_BENCH_PATH={GAOKAO_PATH}")

def main():
    """主函数"""
    print("\n")
    
    if verify_dataset():
        show_sample()
        check_system_integration()
        
        print("\n" + "=" * 70)
        print("✅ 验证通过! 数据集已成功绑定到系统")
        print("=" * 70)
        print("""
下一步操作:
  1. 确保 PostgreSQL 数据库已启动
  2. 导入数据: cd backend && python scripts/import_gaokao_full.py
  3. 启动后端: export GAOKAO_BENCH_PATH={path} && python start_backend.py
  4. 访问前端进行评测
        """.format(path=GAOKAO_PATH))
        return 0
    else:
        print("\n" + "=" * 70)
        print("❌ 验证失败")
        print("=" * 70)
        return 1

if __name__ == "__main__":
    sys.exit(main())
