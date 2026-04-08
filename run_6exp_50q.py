"""运行6组50题对比实验"""
import requests
import time
import json
from datetime import datetime

BASE_URL = 'http://localhost:8000'

EXPERIMENTS = [
    {"name": "Baseline", "use_rag": False, "use_expert_routing": False, "enable_iteration": False},
    {"name": "RAG Only", "use_rag": True, "use_expert_routing": False, "enable_iteration": False},
    {"name": "Expert Routing", "use_rag": True, "use_expert_routing": True, "enable_iteration": False},
    {"name": "Full System", "use_rag": True, "use_expert_routing": True, "enable_iteration": True},
    {"name": "Ablation No Iteration", "use_rag": True, "use_expert_routing": True, "enable_iteration": False},
    {"name": "Ablation No Finetune", "use_rag": True, "use_expert_routing": True, "enable_iteration": True},
]

print('='*70)
print('6组50题对比实验')
print(f'开始时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
print('='*70)

results = []

for idx, exp in enumerate(EXPERIMENTS, 1):
    print(f'\n{"="*70}')
    print(f'实验 {idx}/6: {exp["name"]}')
    print(f'{"="*70}')
    
    # 重置
    requests.post(f'{BASE_URL}/api/v1/benchmark/reset', timeout=5)
    
    # 启动
    payload = {
        'mode': 'random',
        'max_questions': 50,
        'use_experiment_dataset': True,
        'use_rag': exp['use_rag'],
        'use_expert_routing': exp['use_expert_routing'],
        'enable_iteration': exp['enable_iteration']
    }
    
    r = requests.post(f'{BASE_URL}/api/v1/benchmark/start', json=payload, timeout=10)
    if r.status_code != 200:
        print(f'启动失败: {r.text}')
        continue
    
    print(f'启动: {r.json().get("message")}')
    
    # 监控进度
    completed = False
    for _ in range(60):  # 最多等10分钟
        time.sleep(10)
        r = requests.get(f'{BASE_URL}/api/v1/benchmark/progress', timeout=10)
        if r.status_code == 200:
            p = r.json()
            current = p.get('current', 0)
            total = p.get('total', 50)
            status = p.get('status', '')
            
            if current % 10 == 0 or status in ['completed', 'error']:
                print(f'  {current}/{total} ({current*100//total}%) - {status}')
            
            if status == 'completed':
                completed = True
                break
            elif status == 'error':
                print('  实验出错')
                break
    
    # 获取结果
    r = requests.get(f'{BASE_URL}/api/v1/benchmark/results?page_size=100', timeout=10)
    if r.status_code == 200:
        data = r.json()
        items = data.get('items', [])
        if items:
            correct = sum(1 for i in items if i.get('is_correct'))
            accuracy = correct / len(items) * 100
            results.append({
                'name': exp['name'],
                'completed': len(items),
                'correct': correct,
                'accuracy': accuracy
            })
            print(f'结果: {correct}/{len(items)} ({accuracy:.1f}%)')
    
    if idx < 6:
        time.sleep(5)

# 汇总
print(f'\n{"="*70}')
print('实验结果汇总')
print(f'{"="*70}')
for r in results:
    print(f'{r["name"]:25} | {r["correct"]}/{r["completed"]} | {r["accuracy"]:.1f}%')

print('\n' + '='*70)
