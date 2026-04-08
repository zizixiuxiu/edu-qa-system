"""简单测试50题实验"""
import requests
import time

BASE_URL = 'http://localhost:8000'

print('=== 测试50题实验 ===')

# 检查健康状态
r = requests.get(f'{BASE_URL}/health', timeout=5)
print(f'后端状态: {r.json()}')

# 重置实验
print('\n1. 重置实验...')
r = requests.post(f'{BASE_URL}/api/v1/benchmark/reset', timeout=5)
print(f'   {r.json()}')

# 启动实验 - 使用实验数据集
print('\n2. 启动实验（use_experiment_dataset=True）...')
payload = {
    'mode': 'random',
    'max_questions': 50,
    'use_experiment_dataset': True
}

r = requests.post(f'{BASE_URL}/api/v1/benchmark/start', json=payload, timeout=10)
print(f'   状态: {r.status_code}')
if r.status_code == 200:
    data = r.json()
    print(f'   响应: {data}')
    
    # 检查进度
    print('\n3. 检查进度...')
    time.sleep(2)
    r = requests.get(f'{BASE_URL}/api/v1/benchmark/progress', timeout=10)
    p = r.json()
    print(f'   题目数: {p.get("total")}')
    print(f'   进度: {p.get("current")}/{p.get("total")}')
    print(f'   状态: {p.get("status")}')
else:
    print(f'   错误: {r.text}')

print('\n=== 测试完成 ===')
