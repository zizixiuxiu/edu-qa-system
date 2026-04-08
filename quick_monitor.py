"""快速监控实验状态"""
import requests
import time
import sys

BASE_URL = 'http://localhost:8000'

print('监控实验状态 (按Ctrl+C停止)')
print('='*60)

try:
    while True:
        r = requests.get(f'{BASE_URL}/api/v1/benchmark/progress', timeout=10)
        if r.status_code == 200:
            p = r.json()
            status = p.get('status', '')
            current = p.get('current', 0)
            total = p.get('total', 50)
            elapsed = p.get('elapsed_time', 0)
            
            pct = current * 100 // total if total > 0 else 0
            print(f'\r[{elapsed//60:02d}:{elapsed%60:02d}] {current}/{total} ({pct}%) - {status:<10}', end='', flush=True)
            
            if status in ['completed', 'error']:
                print(f'\n状态: {status.upper()}')
                break
        
        time.sleep(5)
        
except KeyboardInterrupt:
    print('\n监控停止')
except Exception as e:
    print(f'\n错误: {e}')
