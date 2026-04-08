"""检查代码"""
copy_path = 'd:/kimi_code/edu_qa_system copy/backend/app/api/benchmark.py'
target_path = 'd:/kimi_code/edu_qa_system/backend/app/api/benchmark.py'

with open(copy_path, 'r', encoding='utf-8') as f:
    copy_content = f.read()

with open(target_path, 'r', encoding='utf-8') as f:
    target_content = f.read()

print(f'Copy 目录包含 use_experiment_dataset: {"use_experiment_dataset" in copy_content}')
print(f'Target 目录包含 use_experiment_dataset: {"use_experiment_dataset" in target_content}')

# 如果 copy 有但 target 没有，复制过去
if "use_experiment_dataset" in copy_content and "use_experiment_dataset" not in target_content:
    with open(target_path, 'w', encoding='utf-8') as f:
        f.write(copy_content)
    print('✓ 已复制代码到 target 目录')
else:
    print('✗ 未复制')
