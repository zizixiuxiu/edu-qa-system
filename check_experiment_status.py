"""检查实验状态"""
import requests
import json

BASE_URL = 'http://localhost:8000'

print('=== Check Experiment Status ===')
r = requests.get(f'{BASE_URL}/api/v1/benchmark/progress', timeout=10)
print(f'Progress Status: {r.status_code}')
if r.status_code == 200:
    print(json.dumps(r.json(), indent=2))

print('\n=== Check Results ===')
r = requests.get(f'{BASE_URL}/api/v1/benchmark/results', timeout=10)
print(f'Results Status: {r.status_code}')
if r.status_code == 200:
    results = r.json()
    result_list = results.get('results', [])
    print(f'Total results: {len(result_list)}')
    
    if result_list:
        print('\nLast 3 results:')
        for i, res in enumerate(result_list[-3:], 1):
            correct = 'YES' if res.get('is_correct') else 'NO'
            print(f'  {i}. Subject: {res.get("subject")}, Correct: {correct}, Score: {res.get("score", 0):.1f}')
