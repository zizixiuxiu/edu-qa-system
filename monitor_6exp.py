"""监控6组实验进度"""
import requests
import time
import json
from datetime import datetime

BASE_URL = 'http://localhost:8000'

print('='*70)
print(f'6组实验监控 - {datetime.now().strftime("%H:%M:%S")}')
print('='*70)

# 获取进度
try:
    r = requests.get(f'{BASE_URL}/api/v1/benchmark/progress', timeout=10)
    if r.status_code == 200:
        p = r.json()
        print(f'\n当前状态: {p.get("status", "unknown").upper()}')
        print(f'进度: {p.get("current", 0)}/{p.get("total", 0)} ({p.get("current", 0)*100//max(p.get("total", 1), 1)}%)')
        print(f'已用时: {p.get("elapsed_time", 0)//60}分{p.get("elapsed_time", 0)%60}秒')
        
        current_q = p.get('current_question', '')
        if current_q:
            print(f'\n当前题目: {current_q[:100]}...')
    else:
        print(f'获取进度失败: {r.status_code}')
except Exception as e:
    print(f'错误: {e}')

# 获取结果统计
try:
    r = requests.get(f'{BASE_URL}/api/v1/benchmark/results?page_size=100', timeout=10)
    if r.status_code == 200:
        data = r.json()
        items = data.get('items', [])
        total = data.get('total', 0)
        
        print(f'\n结果统计:')
        print(f'  已完成: {total}题')
        
        if items:
            correct = sum(1 for item in items if item.get('is_correct'))
            accuracy = correct / len(items) * 100
            print(f'  正确: {correct}题 ({accuracy:.1f}%)')
            
            # 按科目统计
            by_subject = {}
            for item in items:
                sub = item.get('subject', 'Unknown')
                if sub not in by_subject:
                    by_subject[sub] = {'total': 0, 'correct': 0}
                by_subject[sub]['total'] += 1
                if item.get('is_correct'):
                    by_subject[sub]['correct'] += 1
            
            if by_subject:
                print(f'\n  按科目分布:')
                for sub, stats in sorted(by_subject.items(), key=lambda x: x[1]['total'], reverse=True):
                    acc = stats['correct'] / stats['total'] * 100
                    print(f'    {sub}: {stats["correct"]}/{stats["total"]} ({acc:.1f}%)')
except Exception as e:
    print(f'获取结果错误: {e}')

print('\n' + '='*70)
