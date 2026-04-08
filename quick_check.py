#!/usr/bin/env python
"""快速检查实验进度"""
import requests
import sys

BASE_URL = 'http://localhost:8000'

def check():
    try:
        r = requests.get(f'{BASE_URL}/api/v1/benchmark/progress', timeout=10)
        p = r.json()
        status = p.get('status')
        current = p.get('current', 0)
        total = p.get('total', 0)
        exp_id = p.get('experiment_id', 'N/A')
        
        print(f"[{status.upper()}] {current}/{total} ({current/total*100:.1f}%) - Exp: {exp_id}")
        
        if status == 'running':
            return 0
        elif status == 'completed':
            return 1
        elif status == 'error':
            return 2
        else:
            return 3
    except Exception as e:
        print(f"[ERROR] {e}")
        return -1

if __name__ == '__main__':
    sys.exit(check())
