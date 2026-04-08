"""运行并监控6组50题实验"""
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
print('6组50题对比实验 - 顺序执行')
print(f'开始时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
print('='*70)

all_results = []

for idx, exp in enumerate(EXPERIMENTS, 1):
    print(f'\n{"="*70}')
    print(f'实验 {idx}/6: {exp["name"]}')
    print(f'配置: RAG={exp["use_rag"]}, Expert={exp["use_expert_routing"]}, Iteration={exp["enable_iteration"]}')
    print(f'{"="*70}')
    
    # 1. 重置
    print('\n[1/4] 重置实验状态...')
    r = requests.post(f'{BASE_URL}/api/v1/benchmark/reset', timeout=10)
    print(f'   {r.json().get("message")}')
    
    # 2. 启动
    print('\n[2/4] 启动实验...')
    start_time = time.time()
    
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
        print(f'   ✗ 启动失败: {r.text[:200]}')
        continue
    print(f'   ✓ {r.json().get("message")}')
    
    # 3. 监控进度
    print('\n[3/4] 监控进度...')
    completed = False
    prev_current = 0
    
    for attempt in range(120):  # 最多20分钟
        time.sleep(10)
        
        try:
            r = requests.get(f'{BASE_URL}/api/v1/benchmark/progress', timeout=10)
            if r.status_code == 200:
                p = r.json()
                current = p.get('current', 0)
                total = p.get('total', 50)
                status = p.get('status', '')
                elapsed = p.get('elapsed_time', 0)
                
                # 打印进度（每5题或状态变化）
                if current != prev_current and (current % 5 == 0 or status in ['completed', 'error']):
                    pct = current * 100 // total if total > 0 else 0
                    bar = '█' * (pct // 5) + '░' * (20 - pct // 5)
                    print(f'   [{elapsed//60:02d}:{elapsed%60:02d}] [{bar}] {current}/{total} ({pct}%) - {status}')
                    prev_current = current
                
                if status == 'completed':
                    print(f'   ✓ 实验完成!')
                    completed = True
                    break
                elif status == 'error':
                    print(f'   ⚠ 实验出错')
                    break
                    
        except Exception as e:
            print(f'   监控异常: {e}')
    
    if not completed:
        print('   ⚠ 超时或未完成')
    
    # 4. 收集结果
    print('\n[4/4] 收集结果...')
    time.sleep(2)
    
    try:
        r = requests.get(f'{BASE_URL}/api/v1/benchmark/results?page_size=100', timeout=10)
        if r.status_code == 200:
            data = r.json()
            items = data.get('items', [])
            
            if items:
                correct = sum(1 for item in items if item.get('is_correct'))
                total = len(items)
                accuracy = correct / total * 100 if total > 0 else 0
                elapsed = time.time() - start_time
                
                result = {
                    'experiment': exp['name'],
                    'completed': total,
                    'correct': correct,
                    'accuracy': accuracy,
                    'time_minutes': elapsed / 60
                }
                all_results.append(result)
                
                print(f'   完成: {total}题')
                print(f'   正确: {correct}题 ({accuracy:.1f}%)')
                print(f'   用时: {elapsed/60:.1f}分钟')
            else:
                print('   无结果数据')
    except Exception as e:
        print(f'   获取结果失败: {e}')
    
    # 组间休息
    if idx < 6:
        print(f'\n   等待5秒后开始下一组...')
        time.sleep(5)

# 生成汇总报告
print(f'\n\n{"="*70}')
print('实验结果汇总')
print(f'{"="*70}')

print(f'\n{"实验名称":<25} | {"完成":>4} | {"正确":>4} | {"准确率":>8} | {"用时":>8}')
print(f'{"-"*70}')
for r in all_results:
    print(f'{r["experiment"]:<25} | {r["completed"]:>4} | {r["correct"]:>4} | {r["accuracy"]:>7.1f}% | {r["time_minutes"]:>7.1f}分')

# 计算统计
if all_results:
    total_completed = sum(r['completed'] for r in all_results)
    total_correct = sum(r['correct'] for r in all_results)
    avg_accuracy = total_correct / total_completed * 100 if total_completed > 0 else 0
    total_time = sum(r['time_minutes'] for r in all_results)
    
    print(f'\n{"="*70}')
    print(f'总计: {total_correct}/{total_completed} ({avg_accuracy:.1f}%) | 总用时: {total_time:.1f}分钟')
    
    # 对比分析
    if len(all_results) >= 2:
        baseline = next((r for r in all_results if 'Baseline' in r['experiment']), None)
        full_system = next((r for r in all_results if 'Full System' in r['experiment']), None)
        
        if baseline and full_system:
            improvement = full_system['accuracy'] - baseline['accuracy']
            print(f'\nBaseline → Full System 提升: {improvement:+.1f}%')

# 保存结果
report = {
    'timestamp': datetime.now().isoformat(),
    'experiments': all_results
}
with open('6x50_experiment_report.json', 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print(f'\n✓ 详细报告已保存: 6x50_experiment_report.json')
print(f'\n{"="*70}')
