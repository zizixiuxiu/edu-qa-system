"""修补 benchmark.py 支持实验数据集"""
with open('backend/app/api/benchmark.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到需要替换的行范围
start_line = None
end_line = None

for i, line in enumerate(lines):
    if '# 构建查询' in line and start_line is None:
        start_line = i
    if '# 应用随机种子打乱顺序' in line and start_line is not None:
        end_line = i
        break

if start_line is None or end_line is None:
    print(f'未找到标记行: start={start_line}, end={end_line}')
    exit(1)

print(f'找到代码块: 行 {start_line+1} 到 {end_line}')

# 新代码块
new_code = '''    # 构建查询 - 支持实验数据集
    if request.use_experiment_dataset:
        # 从实验数据集读取
        from sqlalchemy import text
        result = await session.execute(text("SELECT id, question, correct_answer, subject, year, category, analysis FROM experiment_dataset ORDER BY RANDOM()"))
        rows = result.fetchall()
        questions = []
        for row in rows:
            # 创建临时的BenchmarkDataset对象
            q = BenchmarkDataset(
                id=row[0],
                question=row[1],
                correct_answer=row[2],
                subject=row[3],
                year=row[4],
                category=row[5],
                analysis=row[6],
                difficulty="medium",
                question_type="objective"
            )
            questions.append(q)
        print(f"[Benchmark] 从实验数据集读取 {len(questions)} 题")
    else:
        # 从标准数据集读取
        query = select(BenchmarkDataset)
        
        if request.subject:
            query = query.where(BenchmarkDataset.subject == request.subject)
        if request.year:
            query = query.where(BenchmarkDataset.year == request.year)
        
        # 先获取所有符合条件的题目（不限制数量）
        result = await session.execute(query)
        questions = list(result.scalars().all())
    
    # 应用随机种子打乱顺序（Python层面实现）
'''

# 替换代码
new_lines = lines[:start_line] + [new_code] + lines[end_line:]

with open('backend/app/api/benchmark.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('✓ benchmark.py 已更新')
