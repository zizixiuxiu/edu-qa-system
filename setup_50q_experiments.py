"""设置50题一组的6组对比实验"""
import requests
import json
import time

BASE_URL = 'http://localhost:8000'

# 6组实验配置
EXPERIMENTS = [
    {"name": "Baseline", "preset": "baseline", "description": "基线组：单模型 + 无RAG + 无专家路由"},
    {"name": "RAG Only", "preset": "rag_only", "description": "RAG组：单模型 + 静态知识库"},
    {"name": "Expert Routing", "preset": "expert_routing", "description": "专家路由组：多专家 + 动态路由 + RAG"},
    {"name": "Full System", "preset": "full_system", "description": "完整系统：专家路由 + RAG + 自我迭代"},
    {"name": "Ablation No Iteration", "preset": "ablation_no_iteration", "description": "消融实验：无自我迭代"},
    {"name": "Ablation No Finetune", "preset": "ablation_no_finetune", "description": "消融实验：无微调"},
]

print('=== Setting up 50-Question Experiment Queue ===\n')

# 1. 重置实验状态
print('1. Resetting benchmark state...')
r = requests.post(f'{BASE_URL}/api/v1/benchmark/reset', timeout=10)
if r.status_code == 200:
    print(f'   ✓ Reset successful')
else:
    print(f'   ✗ Reset failed: {r.text[:200]}')

# 2. 配置实验预设
print('\n2. Configuring experiment presets...')
for exp in EXPERIMENTS:
    r = requests.post(
        f'{BASE_URL}/api/v1/experiments/config',
        json={"preset": exp["preset"]},
        timeout=10
    )
    if r.status_code == 200:
        print(f'   ✓ {exp["name"]}: {exp["preset"]}')
    else:
        print(f'   ✗ {exp["name"]}: {r.text[:200]}')

# 3. 启动6组实验（每组50题）
print('\n3. Starting 6 experiments (50 questions each)...')
started_experiments = []

for i, exp in enumerate(EXPERIMENTS, 1):
    print(f'\n   [{i}/6] Starting {exp["name"]}...')
    
    r = requests.post(
        f'{BASE_URL}/api/v1/benchmark/start',
        json={
            "experiment_mode": exp["preset"],
            "question_limit": 50,
            "subjects": ["Physics", "Chemistry", "Biology"],  # 多科目混合
            "enable_iteration": False,
            "experiment_id": f"exp_{exp['preset']}_{time.strftime('%Y%m%d_%H%M%S')}"
        },
        timeout=10
    )
    
    if r.status_code == 200:
        result = r.json()
        if result.get('success'):
            print(f'       ✓ Started: {result.get("message", "OK")}')
            started_experiments.append(exp)
        else:
            print(f'       ✗ Failed: {result.get("message")}')
    else:
        print(f'       ✗ HTTP Error {r.status_code}: {r.text[:200]}')
    
    # 短暂延迟，避免冲突
    time.sleep(1)

print(f'\n4. Experiment Queue Summary')
print(f'   Total experiments: {len(started_experiments)}/6')
print(f'   Questions per experiment: 50')
print(f'   Total questions to process: {len(started_experiments) * 50}')

print('\n5. Experiments in queue:')
for i, exp in enumerate(started_experiments, 1):
    print(f'   {i}. {exp["name"]} ({exp["preset"]})')

print('\n=== Setup Complete ===')
print('Use the following command to monitor progress:')
print('  python monitor_experiments.py')
