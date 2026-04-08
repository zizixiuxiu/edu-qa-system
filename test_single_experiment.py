"""测试单组实验"""
import requests
import time

BASE_URL = 'http://localhost:8000'

print('=== Single Experiment Test (1 question) ===\n')

# 启动测试
print('1. Starting experiment...')
r = requests.post(
    f'{BASE_URL}/api/v1/benchmark/start',
    json={
        "experiment_mode": "full_system",
        "question_limit": 1,
        "subjects": ["Physics"],
        "enable_iteration": False
    },
    timeout=10
)
print(f'   Status: {r.status_code}')
if r.status_code != 200:
    print(f'   Error: {r.text[:300]}')
    exit(1)
print(f'   Response: {r.json()}')

# 等待完成
print('\n2. Waiting for completion...')
for i in range(60):
    time.sleep(5)
    r = requests.get(f'{BASE_URL}/api/v1/benchmark/progress', timeout=10)
    if r.status_code == 200:
        p = r.json()
        print(f'   [{i*5}s] {p.get("current", 0)}/{p.get("total", 1)} - {p.get("status")}')
        if p.get('status') in ['completed', 'idle']:
            print('   Completed!')
            break

# 获取结果
print('\n3. Results:')
r = requests.get(f'{BASE_URL}/api/v1/benchmark/results', timeout=10)
if r.status_code == 200:
    results = r.json()
    items = results.get('items', [])
    print(f'   Total: {len(items)}')
    for item in items:
        correct = 'YES' if item.get('is_correct') else 'NO'
        print(f'   - Subject: {item.get("subject")}')
        print(f'     Correct: {correct}')
        print(f'     Overall Score: {item.get("overall_score", 0):.1f}')

print('\n=== Test Complete ===')
