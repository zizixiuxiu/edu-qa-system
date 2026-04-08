"""运行6组50题对比实验 - 使用均衡数据集"""
import requests
import time
import json
from datetime import datetime

BASE_URL = 'http://localhost:8000'

EXPERIMENTS = [
    {"name": "Baseline", "preset": "baseline", "use_rag": False, "use_expert_routing": False, "enable_iteration": False},
    {"name": "RAG Only", "preset": "rag_only", "use_rag": True, "use_expert_routing": False, "enable_iteration": False},
    {"name": "Expert Routing", "preset": "expert_routing", "use_rag": True, "use_expert_routing": True, "enable_iteration": False},
    {"name": "Full System", "preset": "full_system", "use_rag": True, "use_expert_routing": True, "enable_iteration": True},
    {"name": "Ablation No Iteration", "preset": "ablation_no_iteration", "use_rag": True, "use_expert_routing": True, "enable_iteration": False},
    {"name": "Ablation No Finetune", "preset": "ablation_no_finetune", "use_rag": True, "use_expert_routing": True, "enable_iteration": True},
]

print('='*70)
print('6组50题对比实验 - 使用均衡数据集')
print('='*70)
print(f'数据集: 50题 (数学10/物理8/化学7/生物7/历史6/地理6/政治6)')
print(f'开始时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
print('='*70)

results_summary = []

for idx, exp in enumerate(EXPERIMENTS, 1):
    print(f'\n{"="*70}')
    print(f'实验 {idx}/6: {exp["name"]}')
    print(f'{"="*70}')
    
    # 重置
    print(f'\n[1/4] 重置状态...')
    r = requests.post(f'{BASE_URL}/api/v1/benchmark/reset', timeout=10)
    print(f'   {r.json().get("message")}')
    
    # 启动实验 - 使用实验数据集
    print(f'\n[2/4] 启动实验 (使用均衡数据集)...')
    start_time = time.time()
    
    payload = {
        "mode": "random",
        "max_questions": 50,
        "use_experiment_dataset": True,  # 关键：使用实验数据集
        "use_rag": exp["use_rag"],
        "use_expert_routing": exp["use_expert_routing"],
        "enable_iteration": exp["enable_iteration"]
    }
    
    r = requests.post(f'{BASE_URL}/api/v1/benchmark/start', json=payload, timeout=10)
    if r.status_code != 200:
        print(f'   ✗ 启动失败: {r.text[:200]}')
        continue
    print(f'   ✓ {r.json().get("message")}')
    
    # 监控进度
    print(f'\n[3/4] 运行中...')
    completed = False
    max_wait = 1800
    waited = 0
    last_current = 0
    
    while waited < max_wait and not completed:
        time.sleep(10)
        waited += 10
        
        try:
            r = requests.get(f'{BASE_URL}/api/v1/benchmark/progress', timeout=10)
            if r.status_code == 200:
                p = r.json()
                current = p.get('current', 0)
                total = p.get('total', 50)
                status = p.get('status', '')
                
                if current != last_current or waited % 60 == 0:
                    pct = current * 100 // total if total > 0 else 0
                    elapsed = p.get('elapsed_time', waited)
                    print(f'   [{elapsed//60:02d}:{elapsed%60:02d}] {current}/{total} ({pct}%) - {status}')
                    last_current = current
                
                if status in ['completed', 'idle'] or current >= total:
                    print(f'   ✓ 完成!')
                    completed = True
                    break
        except Exception as e:
            print(f'   错误: {e}')
    
    if not completed:
        print('   ⚠ 超时，停止')
        requests.post(f'{BASE_URL}/api/v1/benchmark/stop', timeout=10)
    
    # 收集结果
    print(f'\n[4/4] 收集结果...')
    time.sleep(2)
    
    try:
        r = requests.get(f'{BASE_URL}/api/v1/benchmark/results?page_size=100', timeout=10)
        if r.status_code == 200:
            data = r.json()
            items = data.get('items', [])
            
            if items:
                correct = sum(1 for item in items if item.get('is_correct'))
                total = len(items)
                accuracy = correct / total * 100
                elapsed = time.time() - start_time
                
                result = {
                    'experiment': exp['name'],
                    'completed': total,
                    'correct': correct,
                    'accuracy': accuracy,
                    'time_minutes': elapsed / 60
                }
                results_summary.append(result)
                
                print(f'   完成: {total}题 | 正确: {correct} ({accuracy:.1f}%) | 用时: {elapsed/60:.1f}分')
    except Exception as e:
        print(f'   错误: {e}')
    
    if idx < 6:
        print(f'\n   等待5秒...')
        time.sleep(5)

# 汇总
print(f'\n\n{"="*70}')
print('实验结果汇总')
print(f'{"="*70}')

print(f'\n{"实验名称":<25} | {"完成":>4} | {"正确":>4} | {"准确率":>8} | {"用时":>8}')
print(f'{"-"*70}')
for r in results_summary:
    print(f'{r["experiment"]:<25} | {r["completed"]:>4} | {r["correct"]:>4} | {r["accuracy"]:>7.1f}% | {r["time_minutes"]:>7.1f}分')

# 保存
with open('6experiments_50q_results.json', 'w', encoding='utf-8') as f:
    json.dump({
        'timestamp': datetime.now().isoformat(),
        'dataset': '50题均衡数据集',
        'results': results_summary
    }, f, ensure_ascii=False, indent=2)

print(f'\n✓ 结果已保存: 6experiments_50q_results.json')
print(f'\n{"="*70}')
