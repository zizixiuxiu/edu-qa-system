"""测试多学科路由"""
import requests

BASE_URL = 'http://localhost:8000'

questions = [
    ("勾股定理是什么？", "数学"),
    ("牛顿第一定律是什么？", "物理"),
    ("光合作用需要什么条件？", "生物"),
]

print("=== Testing Multi-Subject Routing ===\n")
for query, expected_subject in questions:
    print(f"Question: {query}")
    print(f"Expected: {expected_subject}")
    try:
        r = requests.post(
            f'{BASE_URL}/api/v1/chat/send',
            json={'query': query, 'session_id': f'test-{expected_subject}'},
            timeout=30
        )
        if r.status_code == 200:
            data = r.json()
            if data.get('code') == 200:
                d = data.get('data', {})
                actual_subject = d.get('expert_subject', 'unknown')
                match = "✓" if actual_subject == expected_subject else "✗"
                print(f"Actual: {actual_subject} {match}")
            else:
                print(f"Error: {data.get('message')}")
        else:
            print(f"HTTP Error: {r.status_code}")
    except Exception as e:
        print(f"Exception: {e}")
    print()
