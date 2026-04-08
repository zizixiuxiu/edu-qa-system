"""快速5题实验测试"""
import requests
import time

BASE_URL = 'http://localhost:8000'

print('=== Quick 5-Question Experiment Test ===\n')

# 启动测试
print('1. Starting test...')
r = requests.post(
    f'{BASE_URL}/api/v1/benchmark/start',
    json={
        "experiment_mode": "expert_routing",
        "question_limit": 3,
        "subjects": ["Physics"]
    },
    timeout=10
)
print(f'   Status: {r.status_code}')
if r.status_code != 200:
    print(f'   Error: {r.text[:300]}')
    exit(1)
print(f'   Started: {r.json()}')

# 等待测试完成
print('\n2. Waiting for completion...')
for i in range(60):  # 最多等5分钟
    time.sleep(5)
    r = requests.get(f'{BASE_URL}/api/v1/benchmark/progress', timeout=10)
    if r.status_code == 200:
        p = r.json()
        print(f'   {p.get("current", 0)}/{p.get("total", 3)} - {p.get("status")}')
        if p.get('status') in ['completed', 'idle']:
            break

# 获取结果
print('\n3. Results:')
r = requests.get(f'{BASE_URL}/api/v1/benchmark/results', timeout=10)
if r.status_code == 200:
    results = r.json().get('results', [])
    print(f'   Total: {len(results)}')
    for res in results:
        correct = 'YES' if res.get('is_correct') else 'NO'
        print(f'   - {res.get("subject")}: Correct={correct}, Score={res.get("score", 0):.1f}')

print('\n=== Test Complete ===')
