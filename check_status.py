"""检查实验状态"""
import requests
import json

BASE_URL = 'http://localhost:8000'

# 检查进度
r = requests.get(f'{BASE_URL}/api/v1/benchmark/progress', timeout=10)
print('=== Experiment Progress ===')
if r.status_code == 200:
    data = r.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))
else:
    print(f'Error: {r.status_code}')

# 检查结果
print('\n=== Experiment Results ===')
r = requests.get(f'{BASE_URL}/api/v1/benchmark/results?page_size=10', timeout=10)
if r.status_code == 200:
    data = r.json()
    print(f'Total: {data.get("total", 0)}')
    for item in data.get('items', [])[:5]:
        correct = 'YES' if item.get('is_correct') else 'NO'
        print(f'  - {item.get("subject", "?")}: Correct={correct}, Score={item.get("overall_score", 0):.1f}')
else:
    print(f'Error: {r.status_code}')
