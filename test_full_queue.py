"""测试完整实验队列 - 6组实验各跑1题"""
import requests
import time
import json

BASE_URL = 'http://localhost:8000'

# 6种实验预设
EXPERIMENTS = [
    {"name": "Baseline", "preset": "baseline"},
    {"name": "RAG Only", "preset": "rag_only"},
    {"name": "Expert Routing", "preset": "expert_routing"},
    {"name": "Full System", "preset": "full_system"},
    {"name": "Ablation No Iteration", "preset": "ablation_no_iteration"},
    {"name": "Ablation No Finetune", "preset": "ablation_no_finetune"},
]

print('=== Full Queue Test (6 experiments x 1 question each) ===\n')

# 1. 创建实验队列
print('1. Creating experiment queue...')
for exp in EXPERIMENTS:
    r = requests.post(
        f'{BASE_URL}/api/v1/benchmark/start',
        json={
            "experiment_mode": exp["preset"],
            "question_limit": 1,
            "subjects": ["Physics"],
            "enable_iteration": False
        },
        timeout=10
    )
    if r.status_code == 200:
        print(f'   Added: {exp["name"]} ({exp["preset"]})')
    else:
        print(f'   Failed: {exp["name"]} - {r.text[:100]}')

# 2. 监控队列执行
print('\n2. Monitoring queue execution...')
completed_experiments = set()
max_wait = 600  # 最多等10分钟
waited = 0

while waited < max_wait and len(completed_experiments) < 6:
    time.sleep(5)
    waited += 5
    
    # 获取进度
    r = requests.get(f'{BASE_URL}/api/v1/benchmark/progress', timeout=10)
    if r.status_code == 200:
        p = r.json()
        current = p.get('current', 0)
        total = p.get('total', 1)
        status = p.get('status', 'unknown')
        exp_mode = p.get('experiment_mode', 'unknown')
        
        print(f'   [{waited}s] {exp_mode}: {current}/{total} - {status}')
        
        if status in ['completed', 'idle'] and current >= total:
            completed_experiments.add(exp_mode)
            print(f'   >>> {exp_mode} COMPLETED ({len(completed_experiments)}/6)')
            
            # 获取结果
            r2 = requests.get(f'{BASE_URL}/api/v1/benchmark/results', timeout=10)
            if r2.status_code == 200:
                results = r2.json().get('results', [])
                if results:
                    last = results[-1]
                    correct = 'YES' if last.get('is_correct') else 'NO'
                    print(f'       Result: Correct={correct}, Score={last.get("score", 0):.1f}')

print(f'\n3. Queue execution finished')
print(f'   Completed: {len(completed_experiments)}/6 experiments')
for exp in EXPERIMENTS:
    status = 'DONE' if exp['preset'] in completed_experiments else 'MISSED'
    print(f'   - {exp["name"]}: {status}')

# 4. 最终统计
print('\n4. Final statistics...')
r = requests.get(f'{BASE_URL}/api/v1/benchmark/stats', timeout=10)
if r.status_code == 200:
    stats = r.json()
    print(f'   Total tested: {stats.get("correct_count", 0) + stats.get("wrong_count", 0)}')
    print(f'   Correct: {stats.get("correct_count", 0)}')
    print(f'   Accuracy: {stats.get("accuracy_rate", 0):.1f}%')

print('\n=== Test Complete ===')
