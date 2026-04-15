#!/usr/bin/env python3
"""
GAOKAO-Bench 数据集配置脚本
验证并配置系统使用下载的数据集
"""

import os
import sys
from pathlib import Path

# 数据集路径
GAOKAO_DATASET_PATH = "/Users/zizixiuixu/Downloads/GAOKAO-Bench-main"
DATA_OBJECTIVE = Path(GAOKAO_DATASET_PATH) / "Data" / "Objective_Questions"
DATA_SUBJECTIVE = Path(GAOKAO_DATASET_PATH) / "Data" / "Subjective_Questions"

# 学科映射
SUBJECT_FILES = {
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

def check_dataset():
    """检查数据集是否完整"""
    print("=" * 70)
    print("🔍 检查 GAOKAO-Bench 数据集")
    print("=" * 70)
    print(f"数据集路径: {GAOKAO_DATASET_PATH}")
    print()
    
    if not Path(GAOKAO_DATASET_PATH).exists():
        print("❌ 数据集路径不存在!")
        print(f"   请确认数据集已下载到: {GAOKAO_DATASET_PATH}")
        return False
    
    print("✅ 数据集目录存在")
    
    # 检查客观题目录
    if DATA_OBJECTIVE.exists():
        print(f"✅ 客观题目录: {DATA_OBJECTIVE}")
    else:
        print(f"❌ 客观题目录不存在: {DATA_OBJECTIVE}")
        return False
    
    # 检查各学科文件
    print("\n📚 检查各学科数据文件:")
    total_questions = 0
    
    for subject, files in SUBJECT_FILES.items():
        found = False
        subject_questions = 0
        
        for file in files:
            file_path = DATA_OBJECTIVE / file
            if file_path.exists():
                found = True
                # 统计题目数量
                try:
                    import json
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        count = len(data.get('example', []))
                        subject_questions += count
                except:
                    pass
        
        if found:
            print(f"  ✅ {subject}: ~{subject_questions} 题")
            total_questions += subject_questions
        else:
            print(f"  ⚠️  {subject}: 未找到")
    
    print(f"\n📊 总计约 {total_questions} 道客观题")
    return True

def update_config():
    """更新系统配置"""
    print("\n" + "=" * 70)
    print("⚙️  更新系统配置")
    print("=" * 70)
    
    # 检查 benchmark.py 配置
    benchmark_file = Path("backend/app/api/benchmark.py")
    if benchmark_file.exists():
        content = benchmark_file.read_text(encoding='utf-8')
        if GAOKAO_DATASET_PATH in content:
            print(f"✅ benchmark.py 已配置正确路径")
        else:
            print(f"⚠️  benchmark.py 可能需要手动检查")
    
    # 设置环境变量（临时）
    os.environ["GAOKAO_BENCH_PATH"] = GAOKAO_DATASET_PATH
    print(f"✅ 环境变量 GAOKAO_BENCH_PATH 已设置")
    
    # 创建 .env 配置
    env_content = f"""# GAOKAO-Bench 数据集路径
GAOKAO_BENCH_PATH={GAOKAO_DATASET_PATH}
"""
    
    env_file = Path("backend/.env.gaokao")
    env_file.write_text(env_content, encoding='utf-8')
    print(f"✅ 环境配置已保存到: {env_file}")
    
    print("\n💡 提示: 启动后端前，运行以下命令加载环境变量:")
    print(f"   export GAOKAO_BENCH_PATH={GAOKAO_DATASET_PATH}")

def create_import_script():
    """创建便捷导入脚本"""
    print("\n" + "=" * 70)
    print("📝 创建导入脚本")
    print("=" * 70)
    
    script_content = f'''#!/bin/bash
# GAOKAO-Bench 数据导入脚本

echo "导入 GAOKAO-Bench 数据集到系统..."
echo "路径: {GAOKAO_DATASET_PATH}"
echo ""

# 设置环境变量
export GAOKAO_BENCH_PATH="{GAOKAO_DATASET_PATH}"

cd backend

# 导入客观题（选择题）
echo "📥 导入客观题数据..."
python scripts/import_gaokao_full.py

echo ""
echo "✅ 导入完成!"
echo "启动后端服务: python start_backend.py"
'''
    
    script_file = Path("import_gaokao.sh")
    script_file.write_text(script_content, encoding='utf-8')
    script_file.chmod(0o755)
    print(f"✅ 导入脚本已创建: {script_file}")

def print_usage():
    """打印使用说明"""
    print("\n" + "=" * 70)
    print("📖 使用说明")
    print("=" * 70)
    
    print("""
1️⃣  验证数据集配置:
    python setup_gaokao_dataset.py

2️⃣  导入数据到数据库（需要PostgreSQL运行）:
    ./import_gaokao.sh
    或
    cd backend && python scripts/import_gaokao_full.py

3️⃣  启动后端服务:
    export GAOKAO_BENCH_PATH=/Users/zizixiuixu/Downloads/GAOKAO-Bench-main
    python start_backend.py

4️⃣  访问评测页面:
    打开前端 http://localhost:3000
    进入 Benchmark 页面开始评测

📁 数据集结构:
   {path}
   ├── Data/
   │   ├── Objective_Questions/    # 客观题（已配置使用）
   │   └── Subjective_Questions/   # 主观题
   └── Bench/                      # 评测prompt
""".format(path=GAOKAO_DATASET_PATH))

def main():
    """主函数"""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "     🎓 GAOKAO-Bench 数据集配置工具".center(58) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "=" * 68 + "╝")
    print()
    
    # 检查数据集
    if check_dataset():
        update_config()
        create_import_script()
        print_usage()
        
        print("\n" + "=" * 70)
        print("✅ 配置完成! 系统已绑定 GAOKAO-Bench 数据集")
        print("=" * 70)
        return 0
    else:
        print("\n" + "=" * 70)
        print("❌ 数据集检查失败，请确认数据集已正确下载")
        print("=" * 70)
        return 1

if __name__ == "__main__":
    sys.exit(main())
