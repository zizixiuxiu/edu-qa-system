"""正确启动50题实验"""
import requests
import time

BASE_URL = 'http://localhost:8000'

print('=== 启动50题实验（使用实验数据集）===')

# 启动实验
payload = {
    "mode": "random",
    "max_questions": 50,
    "use_experiment_dataset": True,  # 使用50题均衡数据集
    "use_rag": False,
    "use_expert_routing": False,
    "enable_iteration": False
}

r = requests.post(f'{BASE_URL}/api/v1/benchmark/start', json=payload, timeout=10)
print(f'Status: {r.status_code}')
print(f'Response: {r.json()}')

# 等待几秒后检查
print('\n等待3秒后检查...')
time.sleep(3)

r = requests.get(f'{BASE_URL}/api/v1/benchmark/progress', timeout=10)
if r.status_code == 200:
    p = r.json()
    print(f'\n当前进度: {p.get("current", 0)}/{p.get("total", 0)}')
    print(f'状态: {p.get("status")}')
