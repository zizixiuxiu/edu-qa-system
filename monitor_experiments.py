"""实时监控实验进度"""
import requests
import time
import json
from datetime import datetime

BASE_URL = 'http://localhost:8000'

print('=== Experiment Monitor ===\n')
print('Press Ctrl+C to exit\n')

try:
    while True:
        # 获取进度
        r = requests.get(f'{BASE_URL}/api/v1/benchmark/progress', timeout=10)
        
        if r.status_code == 200:
            p = r.json()
            status = p.get('status', 'unknown')
            current = p.get('current', 0)
            total = p.get('total', 50)
            elapsed = p.get('elapsed_time', 0)
            
            # 计算统计
            progress_pct = current * 100 // total if total > 0 else 0
            qps = current / elapsed if elapsed > 0 else 0
            eta = (total - current) / qps if qps > 0 else 0
            
            # 清屏并打印
            print('\033[2J\033[H')  # 清屏
            print(f'=== Experiment Monitor - {datetime.now().strftime("%H:%M:%S")} ===\n')
            
            print(f'Status: {status.upper()}')
            print(f'Progress: {current}/{total} ({progress_pct}%)')
            print(f'Elapsed: {elapsed//60}m {elapsed%60}s')
            print(f'Speed: {qps:.2f} q/s')
            print(f'ETA: {eta/60:.1f} minutes')
            
            # 进度条
            bar_len = 50
            filled = int(bar_len * current / total) if total > 0 else 0
            bar = '█' * filled + '░' * (bar_len - filled)
            print(f'\n[{bar}] {progress_pct}%')
            
            # 当前题目
            current_q = p.get('current_question', '')
            if current_q:
                print(f'\nCurrent: {current_q[:100]}...')
            
            # 最近结果
            recent = p.get('recent_results', [])
            if recent:
                print(f'\nRecent Results:')
                for i, res in enumerate(recent[:3], 1):
                    correct = '✓' if res.get('is_correct') else '✗'
                    print(f'  {i}. [{correct}] {res.get("subject", "?")} - Score: {res.get("overall_score", 0):.1f}')
            
            # 获取统计
            try:
                r2 = requests.get(f'{BASE_URL}/api/v1/benchmark/stats', timeout=5)
                if r2.status_code == 200:
                    stats = r2.json()
                    print(f'\nOverall Stats:')
                    print(f'  Total tested: {stats.get("correct_count", 0) + stats.get("wrong_count", 0)}')
                    print(f'  Correct: {stats.get("correct_count", 0)}')
                    print(f'  Wrong: {stats.get("wrong_count", 0)}')
                    print(f'  Accuracy: {stats.get("accuracy_rate", 0):.1f}%')
            except:
                pass
        else:
            print(f'Error: {r.status_code}')
        
        time.sleep(10)
        
except KeyboardInterrupt:
    print('\n\nMonitor stopped.')
except Exception as e:
    print(f'\nError: {e}')
