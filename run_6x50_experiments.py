"""运行6组50题对比实验并生成分析报告"""
import requests
import time
import json
from datetime import datetime

BASE_URL = 'http://localhost:8000'

# 6组实验配置
EXPERIMENTS = [
    {"name": "Baseline", "preset": "baseline", "use_rag": False, "use_expert_routing": False, "enable_iteration": False},
    {"name": "RAG Only", "preset": "rag_only", "use_rag": True, "use_expert_routing": False, "enable_iteration": False},
    {"name": "Expert Routing", "preset": "expert_routing", "use_rag": True, "use_expert_routing": True, "enable_iteration": False},
    {"name": "Full System", "preset": "full_system", "use_rag": True, "use_expert_routing": True, "enable_iteration": True},
    {"name": "Ablation No Iteration", "preset": "ablation_no_iteration", "use_rag": True, "use_expert_routing": True, "enable_iteration": False},
    {"name": "Ablation No Finetune", "preset": "ablation_no_finetune", "use_rag": True, "use_expert_routing": True, "enable_iteration": True},
]

print('='*70)
print('6组50题对比实验队列')
print('='*70)
print(f'配置: 每组50题 | 共300题 | 预计时间: ~150分钟')
print(f'科目: 物理 | 数据集: GAOKAO-Bench')
print(f'开始时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
print('='*70)

results_summary = []

for idx, exp in enumerate(EXPERIMENTS, 1):
    print(f'\n{"="*70}')
    print(f'实验 {idx}/6: {exp["name"]}')
    print(f'配置: RAG={exp["use_rag"]} | Expert={exp["use_expert_routing"]} | Iteration={exp["enable_iteration"]}')
    print(f'{"="*70}')
    
    # 重置实验状态
    print(f'\n[1/4] 重置状态...')
    r = requests.post(f'{BASE_URL}/api/v1/benchmark/reset', timeout=10)
    if r.status_code != 200:
        print(f'  重置失败: {r.text}')
        continue
    print(f'  重置完成')
    
    # 启动实验
    print(f'\n[2/4] 启动实验 (50题)...')
    start_time = time.time()
    
    # 根据实验预设设置参数
    if exp["preset"] == "baseline":
        payload = {"mode": "random", "subject": "物理", "max_questions": 50}
    elif exp["preset"] == "rag_only":
        payload = {"mode": "random", "subject": "物理", "max_questions": 50, "use_rag": True, "use_expert_routing": False}
    elif exp["preset"] == "expert_routing":
        payload = {"mode": "random", "subject": "物理", "max_questions": 50, "use_rag": True, "use_expert_routing": True}
    elif exp["preset"] == "full_system":
        payload = {"mode": "random", "subject": "物理", "max_questions": 50, "use_rag": True, "use_expert_routing": True, "enable_iteration": True}
    else:
        payload = {"mode": "random", "subject": "物理", "max_questions": 50, "use_rag": exp["use_rag"], "use_expert_routing": exp["use_expert_routing"], "enable_iteration": exp["enable_iteration"]}
    
    r = requests.post(f'{BASE_URL}/api/v1/benchmark/start', json=payload, timeout=10)
    if r.status_code != 200:
        print(f'  启动失败: {r.text[:200]}')
        continue
    print(f'  启动成功: {r.json().get("message")}')
    
    # 监控进度
    print(f'\n[3/4] 运行中...')
    completed = False
    max_wait = 1800  # 30分钟
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
                    qps = current / elapsed if elapsed > 0 else 0
                    print(f'  [{elapsed//60:02d}:{elapsed%60:02d}] {current}/{total} ({pct}%) | QPS={qps:.2f}')
                    last_current = current
                
                if status in ['completed', 'idle'] or current >= total:
                    print(f'  实验完成!')
                    completed = True
                    break
        except Exception as e:
            print(f'  监控错误: {e}')
    
    if not completed:
        print('  超时，停止实验')
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
                    'preset': exp['preset'],
                    'completed': total,
                    'correct': correct,
                    'accuracy': accuracy,
                    'time_seconds': elapsed,
                    'time_minutes': elapsed / 60,
                    'qps': total / elapsed if elapsed > 0 else 0
                }
                results_summary.append(result)
                
                print(f'  完成: {total}题')
                print(f'  正确: {correct}题 ({accuracy:.1f}%)')
                print(f'  用时: {elapsed/60:.1f}分钟')
            else:
                print(f'  无结果数据')
    except Exception as e:
        print(f'  收集结果错误: {e}')
    
    # 组间休息
    if idx < 6:
        print(f'\n  等待5秒后开始下一组...')
        time.sleep(5)

# 生成分析报告
print(f'\n\n{"="*70}')
print('实验结果分析报告')
print(f'{"="*70}')

print(f'\n1. 实验完成情况')
print(f'   完成实验: {len(results_summary)}/6')
print(f'   总题目数: {sum(r["completed"] for r in results_summary)}')
print(f'   总正确数: {sum(r["correct"] for r in results_summary)}')
print(f'   平均准确率: {sum(r["correct"] for r in results_summary) / sum(r["completed"] for r in results_summary) * 100:.1f}%')

print(f'\n2. 各组实验详细结果')
print(f'   {"实验名称":<25} | {"完成":>4} | {"正确":>4} | {"准确率":>8} | {"用时(分)":>8}')
print(f'   {"-"*70}')
for r in results_summary:
    print(f'   {r["experiment"]:<25} | {r["completed"]:>4} | {r["correct"]:>4} | {r["accuracy"]:>7.1f}% | {r["time_minutes"]:>8.1f}')

if len(results_summary) >= 2:
    print(f'\n3. 对比分析')
    baseline = next((r for r in results_summary if r['preset'] == 'baseline'), None)
    full_system = next((r for r in results_summary if r['preset'] == 'full_system'), None)
    
    if baseline and full_system:
        improvement = full_system['accuracy'] - baseline['accuracy']
        print(f'   Baseline → Full System 提升: {improvement:+.1f}%')
        print(f'   相对提升: {improvement/baseline["accuracy"]*100:+.1f}%')

# 保存完整报告
report = {
    'timestamp': datetime.now().isoformat(),
    'configuration': {
        'questions_per_experiment': 50,
        'subject': '物理',
        'total_experiments': 6
    },
    'summary': {
        'completed': len(results_summary),
        'total_questions': sum(r['completed'] for r in results_summary),
        'total_correct': sum(r['correct'] for r in results_summary),
        'average_accuracy': sum(r['correct'] for r in results_summary) / sum(r['completed'] for r in results_summary) * 100
    },
    'results': results_summary
}

with open('6x50_experiment_report.json', 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print(f'\n4. 报告文件')
print(f'   详细报告: 6x50_experiment_report.json')

print(f'\n{"="*70}')
print('实验队列执行完毕!')
print(f'{"="*70}')
