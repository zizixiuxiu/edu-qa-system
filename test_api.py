"""测试后端API"""
import requests
import json
import time

BASE_URL = 'http://localhost:8000'

def test_endpoint(name, method, path, data=None):
    try:
        url = f'{BASE_URL}{path}'
        print(f'\n=== Testing: {name} ===')
        
        if method == 'GET':
            r = requests.get(url, timeout=10)
        elif method == 'POST':
            r = requests.post(url, json=data, timeout=10)
        
        print(f'Status: {r.status_code}')
        if r.status_code == 200:
            try:
                result = r.json()
                print(f'Response: {json.dumps(result, ensure_ascii=False, indent=2)[:600]}')
                return True
            except:
                print(f'Response: {r.text[:300]}')
                return True
        else:
            print(f'Error: {r.text[:200]}')
            return False
    except Exception as e:
        print(f'Exception: {e}')
        return False

if __name__ == "__main__":
    # 等待服务启动
    print("Waiting for service to start...")
    time.sleep(5)
    
    # 测试核心端点
    results = {}
    results['root'] = test_endpoint('Root', 'GET', '/')
    results['health'] = test_endpoint('Health', 'GET', '/health')
    results['experts_list'] = test_endpoint('Experts List', 'GET', '/api/v1/experts/list')
    results['subjects'] = test_endpoint('Subjects', 'GET', '/api/v1/experts/subjects')
    results['knowledge_stats'] = test_endpoint('Knowledge Stats', 'GET', '/api/v1/knowledge/stats/overview')
    results['experiment_presets'] = test_endpoint('Experiment Presets', 'GET', '/api/v1/experiments/presets')
    results['dashboard'] = test_endpoint('Dashboard', 'GET', '/api/v1/experiments/dashboard')
    results['benchmark_stats'] = test_endpoint('Benchmark Stats', 'GET', '/api/v1/benchmark/stats')
    
    print('\n\n=== Test Summary ===')
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f'Passed: {passed}/{total}')
    for name, ok in results.items():
        status = "PASS" if ok else "FAIL"
        print(f'  [{status}] {name}')
