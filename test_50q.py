"""测试50题实验"""
import requests
import time

BASE_URL = 'http://localhost:8000'

print('=== Test 50-Question Experiment ===\n')

# 重置
print('Resetting...')
r = requests.post(f'{BASE_URL}/api/v1/benchmark/reset', timeout=10)
print(f'Reset: {r.json()}')

# 启动50题实验
print('\nStarting 50-question experiment...')
r = requests.post(
    f'{BASE_URL}/api/v1/benchmark/start',
    json={
        "mode": "random",
        "subject": "Physics",
        "max_questions": 50
    },
    timeout=10
)
print(f'Status: {r.status_code}')
print(f'Response: {r.json()}')

# 监控进度
print('\nMonitoring progress...')
for i in range(30):
    time.sleep(10)
    r = requests.get(f'{BASE_URL}/api/v1/benchmark/progress', timeout=10)
    if r.status_code == 200:
        p = r.json()
        current = p.get('current', 0)
        total = p.get('total', 50)
        print(f'  [{i*10+10}s] {current}/{total} ({current*100//total}%) - {p.get("status")}')
        if current >= total or p.get('status') == 'completed':
            print('  Completed!')
            break

print('\n=== Done ===')
