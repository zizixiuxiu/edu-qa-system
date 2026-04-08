"""检查可用数据集"""
import requests

BASE_URL = 'http://localhost:8000'

r = requests.get(f'{BASE_URL}/api/v1/benchmark/datasets/info', timeout=10)
if r.status_code == 200:
    data = r.json()
    print('Available subjects:')
    for f in data.get('files', []):
        print(f"  - {f['subject_en']} ({f['subject_cn']}): {f['count']} questions")
