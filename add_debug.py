"""添加调试打印"""
with open('backend/app/api/benchmark.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 添加调试打印
old_code = 'if request.use_experiment_dataset:'
new_code = '''print(f"[DEBUG] use_experiment_dataset={request.use_experiment_dataset}")
    if request.use_experiment_dataset:'''

if old_code in content and '[DEBUG]' not in content:
    content = content.replace(old_code, new_code)
    with open('backend/app/api/benchmark.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('✓ 添加调试打印')
else:
    print('✗ 未添加或已存在')
