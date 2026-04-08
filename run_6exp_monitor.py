#!/usr/bin/env python
"""运行6组实验并持续监控 - 前台运行版"""
import requests
import time
import sys
from datetime import datetime

BASE_URL = 'http://localhost:8000'

EXPERIMENTS = [
    {"name": "1.Baseline", "use_rag": False, "use_expert_routing": False, "enable_iteration": False},
    {"name": "2.RAG Only", "use_rag": True, "use_expert_routing": False, "enable_iteration": False},
    {"name": "3.Expert Routing", "use_rag": False, "use_expert_routing": True, "enable_iteration": False},
    {"name": "4.Full System", "use_rag": True, "use_expert_routing": True, "enable_iteration": False},
    {"name": "5.Ablation No Iteration", "use_rag": True, "use_expert_routing": True, "enable_iteration": False},
    {"name": "6.Ablation No Finetune", "use_rag": True, "use_expert_routing": True, "enable_iteration": True},
]

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    sys.stdout.flush()

def check_progress():
    try:
        r = requests.get(f'{BASE_URL}/api/v1/benchmark/progress', timeout=10)
        return r.json()
    except Exception as e:
        return None

def wait_for_completion(exp_name, timeout=600):
    """等待实验完成，超时600秒（10分钟）"""
    start = time.time()
    last_current = -1
    stagnant_count = 0
    
    while time.time() - start < timeout:
        p = check_progress()
        if not p:
            log(f"  {exp_name}: 无法连接后端")
            time.sleep(5)
            continue
        
        status = p.get('status', 'unknown')
        current = p.get('current', 0)
        total = p.get('total', 50)
        
        if status == 'completed':
            log(f"  ✅ {exp_name}: 完成! {current}/{total}")
            return True
        elif status == 'error':
            log(f"  ❌ {exp_name}: 错误! {current}/{total}")
            return False
        elif status == 'running':
            # 检测是否卡住
            if current == last_current:
                stagnant_count += 1
            else:
                stagnant_count = 0
                last_current = current
                progress = current/total*100 if total > 0 else 0
                log(f"  ⏳ {exp_name}: {current}/{total} ({progress:.0f}%)")
            
            # 如果卡住超过2分钟，认为出错
            if stagnant_count > 24:  # 24 * 5s = 120s
                log(f"  ⚠️ {exp_name}: 似乎卡住，超时")
                return False
        
        time.sleep(5)
    
    log(f"  ⏰ {exp_name}: 总体超时")
    return False

def run_experiment(exp_config):
    """运行单组实验"""
    log(f"\n{'='*60}")
    log(f"启动实验: {exp_config['name']}")
    log(f"配置: RAG={exp_config['use_rag']}, Routing={exp_config['use_expert_routing']}, Iteration={exp_config['enable_iteration']}")
    log(f"{'='*60}")
    
    # 重置
    try:
        requests.post(f'{BASE_URL}/api/v1/benchmark/reset', timeout=5)
        time.sleep(2)
    except:
        pass
    
    # 启动实验
    payload = {
        'mode': 'random',
        'subject': '物理',
        'max_questions': 50,
        'use_rag': exp_config['use_rag'],
        'use_expert_routing': exp_config['use_expert_routing'],
        'enable_iteration': exp_config['enable_iteration']
    }
    
    try:
        r = requests.post(f'{BASE_URL}/api/v1/benchmark/start', json=payload, timeout=10)
        if r.status_code != 200:
            log(f"  启动失败: {r.status_code} - {r.text}")
            return False
    except Exception as e:
        log(f"  启动异常: {e}")
        return False
    
    log(f"  实验已启动，开始监控...")
    return wait_for_completion(exp_config['name'])

def main():
    log("="*60)
    log("开始运行6组对比实验 (每组50题)")
    log("预计总时间: 约25-30分钟")
    log("="*60)
    
    results = []
    total_start = time.time()
    
    for exp in EXPERIMENTS:
        exp_start = time.time()
        success = run_experiment(exp)
        exp_time = time.time() - exp_start
        results.append({
            'name': exp['name'],
            'success': success,
            'time': exp_time
        })
        log(f"  耗时: {exp_time/60:.1f}分钟")
    
    total_time = time.time() - total_start
    
    log("\n" + "="*60)
    log("实验完成总结")
    log("="*60)
    for r in results:
        status = "✅ 成功" if r['success'] else "❌ 失败"
        log(f"  {r['name']}: {status} ({r['time']/60:.1f}分钟)")
    log(f"\n总耗时: {total_time/60:.1f}分钟")
    log("="*60)

if __name__ == '__main__':
    main()
