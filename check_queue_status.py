"""检查实验队列状态"""
import requests
import json

BASE_URL = 'http://localhost:8000'

print('=== Current Experiment Status ===')

# 检查进度
r = requests.get(f'{BASE_URL}/api/v1/benchmark/progress', timeout=10)
print(f'Progress Status: {r.status_code}')
if r.status_code == 200:
    print(json.dumps(r.json(), indent=2))
else:
    print(f'Error: {r.text[:200]}')

print()

# 检查结果
r = requests.get(f'{BASE_URL}/api/v1/benchmark/results', timeout=10)
print(f'Results Status: {r.status_code}')
if r.status_code == 200:
    results = r.json().get('results', [])
    print(f'Total completed: {len(results)}')
    for i, res in enumerate(results, 1):
        exp = res.get('experiment_mode', 'unknown')
        correct = 'YES' if res.get('is_correct') else 'NO'
        score = res.get('score', 0)
        print(f'  {i}. {exp}: Correct={correct}, Score={score:.1f}')
else:
    print(f'Error: {r.text[:200]}')
