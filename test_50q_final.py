"""最终测试50题实验"""
import requests
import time

BASE_URL = 'http://localhost:8000'

print('=== 测试50题实验 ===')

# 停止并重置
print('\n1. 停止并重置...')
requests.post(f'{BASE_URL}/api/v1/benchmark/stop', timeout=5)
requests.post(f'{BASE_URL}/api/v1/benchmark/reset', timeout=5)

# 启动实验
print('\n2. 启动实验...')
payload = {
    'mode': 'random',
    'max_questions': 50,
    'use_experiment_dataset': True
}

r = requests.post(f'{BASE_URL}/api/v1/benchmark/start', json=payload, timeout=10)
print(f'Response: {r.json()}')

# 检查进度
print('\n3. 检查进度...')
time.sleep(2)
r = requests.get(f'{BASE_URL}/api/v1/benchmark/progress', timeout=10)
p = r.json()
print(f"Status: {p.get('status')}")
print(f"Progress: {p.get('current')}/{p.get('total')}")
print(f"Question: {p.get('current_question', '')[:50]}...")
