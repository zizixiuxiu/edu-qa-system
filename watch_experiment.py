"""持续监控实验直到第一组完成"""
import requests
import time
from datetime import datetime

BASE_URL = 'http://localhost:8000'

print('=== 监控第一组实验完成 ===\n')

prev_current = 0
completed_shown = False

while True:
    try:
        r = requests.get(f'{BASE_URL}/api/v1/benchmark/progress', timeout=10)
        if r.status_code == 200:
            p = r.json()
            status = p.get('status', '')
            current = p.get('current', 0)
            total = p.get('total', 50)
            elapsed = p.get('elapsed_time', 0)
            
            # 打印进度（当有变化或每30秒）
            if current != prev_current:
                pct = current * 100 // total if total > 0 else 0
                print(f'[{datetime.now().strftime("%H:%M:%S")}] {current}/{total} ({pct}%) | {elapsed//60}m{elapsed%60}s | {status}')
                prev_current = current
            
            # 检测完成
            if status in ['completed', 'idle'] and not completed_shown:
                print('\n' + '='*60)
                print('✅ 第一组实验完成！')
                print('='*60)
                completed_shown = True
                
                # 获取结果
                r2 = requests.get(f'{BASE_URL}/api/v1/benchmark/results?page_size=100', timeout=10)
                if r2.status_code == 200:
                    data = r2.json()
                    items = data.get('items', [])
                    if items:
                        correct = sum(1 for item in items if item.get('is_correct'))
                        print(f'\n结果: {correct}/{len(items)} 正确 ({correct/len(items)*100:.1f}%)')
                break
                
    except Exception as e:
        print(f'Error: {e}')
    
    time.sleep(5)
