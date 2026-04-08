"""启动50题实验 - 使用正确的科目名称"""
import requests
import time
import json

BASE_URL = 'http://localhost:8000'

print('=== Starting 50-Question Experiment ===\n')

# 重置
print('1. Resetting benchmark...')
r = requests.post(f'{BASE_URL}/api/v1/benchmark/reset', timeout=10)
print(f'   {r.json()}')

# 启动实验 - 使用英文科目名
print('\n2. Starting experiment (50 questions)...')
r = requests.post(
    f'{BASE_URL}/api/v1/benchmark/start',
    json={
        "mode": "random",
        "subject": "物理",
        "max_questions": 50
    },
    timeout=10
)
print(f'   Status: {r.status_code}')
if r.status_code == 200:
    print(f'   Response: {r.json()}')
else:
    print(f'   Error: {r.text}')
    exit(1)

# 监控进度
print('\n3. Monitoring progress (up to 30 minutes)...')
print('   Press Ctrl+C to stop monitoring\n')

try:
    max_wait = 1800  # 30分钟
    waited = 0
    last_current = -1
    
    while waited < max_wait:
        time.sleep(10)
        waited += 10
        
        r = requests.get(f'{BASE_URL}/api/v1/benchmark/progress', timeout=10)
        if r.status_code == 200:
            p = r.json()
            current = p.get('current', 0)
            total = p.get('total', 50)
            status = p.get('status', 'unknown')
            
            # 只打印有变化的时候
            if current != last_current or waited % 60 == 0:
                pct = current * 100 // total if total > 0 else 0
                elapsed = p.get('elapsed_time', waited)
                qps = current / elapsed if elapsed > 0 else 0
                eta = (total - current) / qps if qps > 0 else 0
                
                print(f'   [{elapsed//60:02d}:{elapsed%60:02d}] {current:3d}/{total} ({pct:3d}%) | '
                      f'QPS: {qps:.2f} | ETA: {eta/60:5.1f}min | {status}')
                last_current = current
            
            if status in ['completed', 'idle'] or current >= total:
                print('\n   ✅ Experiment completed!')
                break
        else:
            print(f'   Error: {r.status_code}')
            
    else:
        print('\n   ⚠ Timeout reached')
        
except KeyboardInterrupt:
    print('\n   Stopped by user')

# 获取结果
print('\n4. Getting results...')
r = requests.get(f'{BASE_URL}/api/v1/benchmark/results?page_size=100', timeout=10)
if r.status_code == 200:
    data = r.json()
    items = data.get('items', [])
    total = data.get('total', 0)
    
    print(f'   Total results: {total}')
    
    if items:
        correct = sum(1 for item in items if item.get('is_correct'))
        accuracy = correct / len(items) * 100
        
        print(f'   Correct: {correct}/{len(items)} ({accuracy:.1f}%)')
        
        # 保存结果
        with open('experiment_50q_results.json', 'w', encoding='utf-8') as f:
            json.dump({
                'total': len(items),
                'correct': correct,
                'accuracy': accuracy,
                'items': items
            }, f, ensure_ascii=False, indent=2)
        print(f'   ✅ Results saved to experiment_50q_results.json')

print('\n=== Experiment Complete ===')
