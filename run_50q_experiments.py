"""顺序运行6组50题对比实验"""
import requests
import time
import json

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

print('=== 6x50 Questions Experiment Queue ===\n')
print('Configuration:')
print(f'  Total experiments: 6')
print(f'  Questions per experiment: 50')
print(f'  Total questions: 300')
print(f'  Estimated time: ~150 minutes (30s per question)')
print()

results_summary = []

for exp_idx, exp in enumerate(EXPERIMENTS, 1):
    print(f'\n{"="*60}')
    print(f'Experiment {exp_idx}/6: {exp["name"]}')
    print(f'Mode: {exp["preset"]}')
    print(f'{"="*60}')
    
    # 1. 启动实验
    print('\n[1/3] Starting experiment...')
    start_time = time.time()
    
    r = requests.post(
        f'{BASE_URL}/api/v1/benchmark/start',
        json={
            "experiment_mode": exp["preset"],
            "question_limit": 50,
            "subjects": ["Physics"],
            "enable_iteration": False
        },
        timeout=10
    )
    
    if r.status_code != 200:
        print(f'   ✗ Failed to start: {r.text[:200]}')
        continue
    
    print(f'   ✓ Started: {r.json().get("message")}')
    
    # 2. 监控进度
    print('\n[2/3] Monitoring progress...')
    completed = False
    max_wait = 1800  # 最多等30分钟
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
                status = p.get('status', 'unknown')
                
                # 只打印有变化的时候
                if current != last_current or waited % 60 == 0:
                    elapsed = time.time() - start_time
                    qps = current / elapsed if elapsed > 0 else 0
                    eta = (total - current) / qps if qps > 0 else 0
                    print(f'   [{elapsed:.0f}s] {current}/{total} ({current*100//total}%) - '
                          f'QPS: {qps:.2f} - ETA: {eta/60:.1f}min - {status}')
                    last_current = current
                
                if status in ['completed', 'idle'] or current >= total:
                    completed = True
                    print(f'   ✓ Experiment completed!')
                    break
                    
        except Exception as e:
            print(f'   Error: {e}')
    
    if not completed:
        print(f'   ⚠ Timeout, stopping experiment...')
        requests.post(f'{BASE_URL}/api/v1/benchmark/stop', timeout=10)
    
    # 3. 收集结果
    print('\n[3/3] Collecting results...')
    time.sleep(2)  # 等待结果写入
    
    try:
        r = requests.get(
            f'{BASE_URL}/api/v1/benchmark/results?page_size=100',
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            items = data.get('items', [])
            total = data.get('total', 0)
            
            # 统计本次实验的结果
            correct = sum(1 for item in items if item.get('is_correct'))
            accuracy = correct / len(items) * 100 if items else 0
            
            result = {
                'name': exp['name'],
                'preset': exp['preset'],
                'completed': len(items),
                'correct': correct,
                'accuracy': accuracy,
                'time': time.time() - start_time
            }
            results_summary.append(result)
            
            print(f'   ✓ Results: {correct}/{len(items)} correct ({accuracy:.1f}%)')
            print(f'   ✓ Time: {result["time"]/60:.1f} minutes')
    except Exception as e:
        print(f'   ✗ Error: {e}')
    
    # 短暂休息
    if exp_idx < len(EXPERIMENTS):
        print(f'\n   Waiting 5s before next experiment...')
        time.sleep(5)

# 汇总报告
print(f'\n\n{"="*60}')
print('FINAL SUMMARY')
print(f'{"="*60}')

for i, res in enumerate(results_summary, 1):
    print(f'{i}. {res["name"]:25} | {res["correct"]}/{res["completed"]} ({res["accuracy"]:.1f}%) | {res["time"]/60:.1f}min')

print(f'\nTotal experiments completed: {len(results_summary)}/6')
print(f'Total questions processed: {sum(r["completed"] for r in results_summary)}')

# 保存报告
with open('50Q_EXPERIMENT_RESULTS.json', 'w', encoding='utf-8') as f:
    json.dump(results_summary, f, ensure_ascii=False, indent=2)
print(f'\n✓ Results saved to 50Q_EXPERIMENT_RESULTS.json')
