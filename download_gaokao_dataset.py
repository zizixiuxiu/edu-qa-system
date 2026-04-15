#!/usr/bin/env python3
"""
下载GAOKAO-Bench完整数据集
来源: Hugging Face - MXEdu/GAOKAO-Bench
"""

import os
import json
import requests
from pathlib import Path
from tqdm import tqdm

# 数据集配置
DATASET_NAME = "MXEdu/GAOKAO-Bench"
BASE_URL = "https://huggingface.co/datasets/MXEdu/GAOKAO-Bench/resolve/main/data"

# 学科文件列表
SUBJECTS = {
    "语文": "chinese.json",
    "数学": "math.json", 
    "英语": "english.json",
    "物理": "physics.json",
    "化学": "chemistry.json",
    "生物": "biology.json",
    "历史": "history.json",
    "地理": "geography.json",
    "政治": "politics.json"
}

def download_file(url: str, output_path: Path, desc: str = ""):
    """下载文件并显示进度"""
    if output_path.exists():
        print(f"  ⏭️  已存在: {output_path.name}")
        return True
    
    try:
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        with open(output_path, 'wb') as f, tqdm(
            desc=desc or output_path.name,
            total=total_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
        ) as pbar:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))
        
        return True
    except Exception as e:
        print(f"  ❌ 下载失败: {e}")
        if output_path.exists():
            output_path.unlink()
        return False

def download_gaokao_dataset(output_dir: str = "./backend/data/GAOKAO-Bench-Full"):
    """下载完整GAOKAO数据集"""
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print("=" * 70)
    print("🚀 下载 GAOKAO-Bench 完整数据集")
    print("=" * 70)
    print(f"来源: {DATASET_NAME}")
    print(f"保存路径: {output_path.absolute()}")
    print()
    
    # 创建子目录
    raw_dir = output_path / "raw"
    raw_dir.mkdir(exist_ok=True)
    
    # 下载各学科数据
    downloaded_files = []
    total_questions = 0
    
    print("📥 下载各学科数据...")
    for subject_cn, filename in SUBJECTS.items():
        # 尝试多种可能的URL格式
        urls_to_try = [
            f"{BASE_URL}/{filename}",
            f"https://huggingface.co/datasets/MXEdu/GAOKAO-Bench/raw/main/data/{filename}",
            f"https://cdn.jsdelivr.net/gh/openbmb/GAOKAO-Bench@main/data/{filename}",
        ]
        
        output_file = raw_dir / filename
        success = False
        
        for url in urls_to_try:
            if download_file(url, output_file, desc=f"{subject_cn}"):
                success = True
                break
        
        if success:
            downloaded_files.append(output_file)
            # 统计题目数量
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    count = len(data) if isinstance(data, list) else len(data.get('examples', []))
                    total_questions += count
                    print(f"  ✅ {subject_cn}: {count} 题")
            except:
                print(f"  ✅ {subject_cn}: 已下载")
    
    # 创建合并版本（用于系统导入）
    print("\n📦 创建合并数据集...")
    merge_gaokao_data(raw_dir, output_path / "gaokao_merged.json")
    
    print("\n" + "=" * 70)
    print("✅ 下载完成!")
    print("=" * 70)
    print(f"原始数据: {raw_dir}")
    print(f"合并数据: {output_path / 'gaokao_merged.json'}")
    print(f"\n总计约 {total_questions} 道题目")
    print("\n使用说明:")
    print("  1. 运行后端导入脚本将数据导入数据库")
    print("  2. 或使用 gaokao_merged.json 作为评测数据集")

def merge_gaokao_data(raw_dir: Path, output_file: Path):
    """合并各学科数据为一个文件"""
    
    all_questions = []
    subject_map = {
        "chinese": "语文",
        "math": "数学",
        "english": "英语",
        "physics": "物理",
        "chemistry": "化学",
        "biology": "生物",
        "history": "历史",
        "geography": "地理",
        "politics": "政治"
    }
    
    for json_file in raw_dir.glob("*.json"):
        subject_en = json_file.stem
        subject_cn = subject_map.get(subject_en, subject_en)
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # 处理不同格式
            if isinstance(data, list):
                questions = data
            elif isinstance(data, dict):
                questions = data.get('examples', data.get('questions', []))
            else:
                continue
            
            # 添加学科标签
            for q in questions:
                if isinstance(q, dict):
                    q['subject'] = subject_cn
                    all_questions.append(q)
                    
        except Exception as e:
            print(f"  警告: 无法处理 {json_file.name}: {e}")
    
    # 保存合并文件
    output_data = {
        "dataset_name": "GAOKAO-Bench-Full",
        "description": "中国高考题目完整数据集",
        "total_questions": len(all_questions),
        "subjects": list(subject_map.values()),
        "questions": all_questions
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"  ✅ 合并完成: {len(all_questions)} 题 -> {output_file.name}")

def download_from_github_mirror(output_dir: str = "./backend/data/GAOKAO-Bench-Full"):
    """从GitHub镜像下载（备用方案）"""
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # GitHub原始文件URL
    github_base = "https://raw.githubusercontent.com/OpenBMB/GAOKAO-Bench/main/data"
    
    print("📥 尝试从GitHub下载...")
    
    for subject_cn, filename in SUBJECTS.items():
        url = f"{github_base}/{filename}"
        output_file = output_path / "raw" / filename
        download_file(url, output_file, desc=f"{subject_cn}")

if __name__ == "__main__":
    import sys
    
    # 检查依赖
    try:
        import requests
        from tqdm import tqdm
    except ImportError:
        print("安装依赖: pip install requests tqdm")
        sys.exit(1)
    
    # 设置输出目录
    output_dir = sys.argv[1] if len(sys.argv) > 1 else "./backend/data/GAOKAO-Bench-Full"
    
    # 尝试下载
    download_gaokao_dataset(output_dir)
