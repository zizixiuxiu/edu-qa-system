"""最终系统测试"""
import requests
import json

BASE_URL = 'http://localhost:8000'
print('=== Final System Test ===\n')

tests = {
    'Root API': '/',
    'Health Check': '/health',
    'Experts List': '/api/v1/experts/list',
    'Subjects': '/api/v1/experts/subjects',
    'Knowledge Stats': '/api/v1/knowledge/stats/overview',
    'Experiment Presets': '/api/v1/experiments/presets',
    'Benchmark Stats': '/api/v1/benchmark/stats',
}

results = {}
for name, path in tests.items():
    try:
        r = requests.get(f'{BASE_URL}{path}', timeout=10)
        results[name] = r.status_code == 200
        status = '✓' if results[name] else '✗'
        print(f'{status} {name}: {r.status_code}')
    except Exception as e:
        results[name] = False
        print(f'✗ {name}: Error - {e}')

# 测试问答
print('\nTesting Chat API...')
try:
    r = requests.post(
        f'{BASE_URL}/api/v1/chat/send',
        json={'query': '什么是牛顿第一定律？', 'session_id': 'final-test'},
        timeout=30
    )
    if r.status_code == 200:
        data = r.json()
        if data.get('code') == 200:
            d = data.get('data', {})
            results['Chat API'] = True
            expert = d.get('expert_subject', 'unknown')
            print(f'✓ Chat API: OK (Expert: {expert})')
        else:
            results['Chat API'] = False
            print(f'✗ Chat API: {data.get("message")}')
    else:
        results['Chat API'] = False
        print(f'✗ Chat API: HTTP {r.status_code}')
except Exception as e:
    results['Chat API'] = False
    print(f'✗ Chat API: Error - {e}')

# 汇总
passed = sum(1 for v in results.values() if v)
total = len(results)
print(f'\n=== Test Summary ===')
print(f'Passed: {passed}/{total} ({passed*100//total}%)')

# 写入报告
with open('TEST_REPORT.md', 'w', encoding='utf-8') as f:
    f.write('# EduQA 系统测试报告\n\n')
    f.write(f'## 测试时间\n{__import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n')
    f.write('## 测试结果\n\n')
    f.write(f'**总体通过率: {passed}/{total} ({passed*100//total}%)**\n\n')
    f.write('### 详细结果\n\n')
    for name, ok in results.items():
        status = '✅ 通过' if ok else '❌ 失败'
        f.write(f'- {status}: {name}\n')
    f.write('\n### 系统状态\n\n')
    f.write('- 后端服务: http://localhost:8000\n')
    f.write('- 前端服务: http://localhost:3002\n')
    f.write('- API文档: http://localhost:8000/docs\n')

print('\n✅ Test report saved to TEST_REPORT.md')
