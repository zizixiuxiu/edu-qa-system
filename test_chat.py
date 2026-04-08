"""测试问答功能"""
import requests
import json

BASE_URL = 'http://localhost:8000'

# 测试问答功能
print('=== Testing Chat API ===')
try:
    r = requests.post(
        f'{BASE_URL}/api/v1/chat/send',
        json={'query': '勾股定理是什么？', 'session_id': 'test-001'},
        timeout=30
    )
    print(f'Status: {r.status_code}')
    if r.status_code == 200:
        data = r.json()
        print(f'Code: {data.get("code")}')
        print(f'Message: {data.get("message")}')
        if data.get('data'):
            d = data['data']
            print(f'Expert: {d.get("expert_name")} ({d.get("expert_subject")})')
            print(f'Answer preview: {d.get("answer", "")[:200]}...')
            print(f'Used knowledges: {len(d.get("used_knowledges", []))}')
    else:
        print(f'Error: {r.text[:500]}')
except Exception as e:
    print(f'Exception: {e}')
