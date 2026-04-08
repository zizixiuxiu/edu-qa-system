"""运行5题实验控制测试"""
import requests
import time
import json

BASE_URL = 'http://localhost:8000'

print('=== 5-Question Experiment Control Test ===\n')

# 1. 启动测试
print('1. Starting benchmark test with 5 questions...')
start_payload = {
    "experiment_mode": "full_system",
    "question_limit": 5,
    "subjects": ["Physics"],
    "enable_iteration": False
}

try:
    r = requests.post(
        f'{BASE_URL}/api/v1/benchmark/start',
        json=start_payload,
        timeout=10
    )
    print(f'   Status: {r.status_code}')
    if r.status_code == 200:
        data = r.json()
        print(f'   Response: {json.dumps(data, ensure_ascii=False, indent=2)}')
    else:
        print(f'   Error: {r.text[:500]}')
        exit(1)
except Exception as e:
    print(f'   Exception: {e}')
    exit(1)

# 2. 监控进度
print('\n2. Monitoring test progress...')
max_wait = 300
waited = 0
completed = False

while waited < max_wait and not completed:
    try:
        r = requests.get(f'{BASE_URL}/api/v1/benchmark/progress', timeout=10)
        if r.status_code == 200:
            progress = r.json()
            current = progress.get('current_question', 0)
            total = progress.get('total_questions', 5)
            status = progress.get('status', 'unknown')
            
            print(f'   Progress: {current}/{total} - Status: {status}')
            
            if status in ['completed', 'idle'] or current >= total:
                completed = True
                print('   Test completed!')
                break
        else:
            print(f'   Error getting progress: {r.status_code}')
    except Exception as e:
        print(f'   Exception: {e}')
    
    time.sleep(5)
    waited += 5

if not completed:
    print('   Test did not complete within timeout')

# 3. 获取结果
print('\n3. Getting test results...')
try:
    r = requests.get(f'{BASE_URL}/api/v1/benchmark/results', timeout=10)
    print(f'   Status: {r.status_code}')
    if r.status_code == 200:
        results = r.json()
        print(f'   Total results: {len(results.get("results", []))}')
        
        if results.get('results'):
            correct = sum(1 for r in results['results'] if r.get('is_correct'))
            total = len(results['results'])
            accuracy = correct / total * 100 if total > 0 else 0
            print(f'   Accuracy: {correct}/{total} ({accuracy:.1f}%)')
            
            print('\n   Question Details:')
            for i, result in enumerate(results['results'][:5], 1):
                q = result.get('question', {}) 
                correct_mark = "YES" if result.get('is_correct') else "NO"
                score = result.get('score', 0)
                subject = result.get('subject', '?')
                print(f'   Q{i}: [{subject}] Correct: {correct_mark} | Score: {score:.1f}')
    else:
        print(f'   Error: {r.text[:500]}')
except Exception as e:
    print(f'   Exception: {e}')

# 4. 获取统计
print('\n4. Getting benchmark stats...')
try:
    r = requests.get(f'{BASE_URL}/api/v1/benchmark/stats', timeout=10)
    if r.status_code == 200:
        stats = r.json()
        print(f'   Total questions in dataset: {stats.get("total_questions", 0)}')
        print(f'   Correct count: {stats.get("correct_count", 0)}')
        print(f'   Wrong count: {stats.get("wrong_count", 0)}')
        print(f'   Accuracy rate: {stats.get("accuracy_rate", 0):.2f}%')
except Exception as e:
    print(f'   Exception: {e}')

print('\n=== Experiment Test Complete ===')
