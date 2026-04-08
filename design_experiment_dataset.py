"""设计实验数据集 - 多科目按比例抽取，难度合理分布"""
import psycopg2
import random

conn = psycopg2.connect(
    host='localhost', port=15432, database='edu_qa',
    user='postgres', password='password'
)
cur = conn.cursor()

print('='*60)
print('实验数据集设计')
print('='*60)

# 1. 检查各科目题目数量和难度分布
print('\n1. 各科目题目数量及难度分布:')
cur.execute("""
    SELECT subject, difficulty, COUNT(*) 
    FROM benchmark_datasets 
    GROUP BY subject, difficulty 
    ORDER BY subject, difficulty
""")

subject_stats = {}
for row in cur.fetchall():
    subject, difficulty, count = row
    if subject not in subject_stats:
        subject_stats[subject] = {}
    subject_stats[subject][difficulty] = count

for subject, difficulties in sorted(subject_stats.items(), key=lambda x: sum(x[1].values()), reverse=True):
    total = sum(difficulties.values())
    easy = difficulties.get('easy', 0)
    medium = difficulties.get('medium', 0)
    hard = difficulties.get('hard', 0)
    print(f'  {subject}: 总计{total}题 (简单{easy}/中等{medium}/困难{hard})')

# 2. 设计抽取策略
print('\n2. 题目抽取策略:')
print('   目标: 每组实验50题')
print('   分布: 多科目混合 + 难度均衡')
print('   比例: 简单30% + 中等50% + 困难20%')

# 3. 按比例从主要科目抽取
TARGET_TOTAL = 50  # 每组50题
DIFFICULTY_RATIO = {'easy': 0.3, 'medium': 0.5, 'hard': 0.2}

# 选择主要科目（排除英语细分，合并为一个）
main_subjects = ['数学', '物理', '化学', '生物', '历史', '地理', '政治']
subject_weights = {
    '数学': 0.20,      # 10题
    '物理': 0.16,      # 8题
    '化学': 0.14,      # 7题
    '生物': 0.14,      # 7题
    '历史': 0.12,      # 6题
    '地理': 0.12,      # 6题
    '政治': 0.12,      # 6题
}

print('\n3. 各科抽取数量:')
selected_questions = []
for subject, weight in subject_weights.items():
    subject_total = int(TARGET_TOTAL * weight)
    easy_count = max(1, int(subject_total * DIFFICULTY_RATIO['easy']))
    medium_count = max(1, int(subject_total * DIFFICULTY_RATIO['medium']))
    hard_count = max(1, subject_total - easy_count - medium_count)
    
    print(f'   {subject}: {subject_total}题 (简单{easy_count}/中等{medium_count}/困难{hard_count})')
    
    # 从数据库抽取
    for difficulty, count in [('easy', easy_count), ('medium', medium_count), ('hard', hard_count)]:
        cur.execute("""
            SELECT id, question, correct_answer, subject, difficulty 
            FROM benchmark_datasets 
            WHERE subject = %s AND difficulty = %s
            ORDER BY RANDOM() LIMIT %s
        """, (subject, difficulty, count))
        
        for row in cur.fetchall():
            selected_questions.append({
                'id': row[0],
                'question': row[1][:100] + '...' if len(row[1]) > 100 else row[1],
                'answer': row[2][:50] + '...' if len(row[2]) > 50 else row[2],
                'subject': row[3],
                'difficulty': row[4]
            })

# 4. 保存到新的实验数据集表
print('\n4. 创建实验数据集...')

# 创建实验专用数据集表
cur.execute("""
    DROP TABLE IF EXISTS experiment_dataset CASCADE;
    CREATE TABLE experiment_dataset (
        id SERIAL PRIMARY KEY,
        original_id INTEGER REFERENCES benchmark_datasets(id),
        question TEXT,
        correct_answer TEXT,
        subject VARCHAR,
        difficulty VARCHAR,
        experiment_group INTEGER DEFAULT 1
    )
""")

# 插入抽取的题目
for q in selected_questions:
    cur.execute("""
        INSERT INTO experiment_dataset (original_id, question, correct_answer, subject, difficulty)
        VALUES (%s, %s, %s, %s, %s)
    """, (q['id'], q['question'], q['answer'], q['subject'], q['difficulty']))

conn.commit()

# 5. 验证结果
print('\n5. 实验数据集验证:')
cur.execute("SELECT subject, difficulty, COUNT(*) FROM experiment_dataset GROUP BY subject, difficulty ORDER BY subject, difficulty")
for row in cur.fetchall():
    print(f'   {row[0]} ({row[1]}): {row[2]}题')

cur.execute("SELECT COUNT(*) FROM experiment_dataset")
total = cur.fetchone()[0]
print(f'\n   总计: {total}题')

cur.close()
conn.close()

print('\n' + '='*60)
print(f'✅ 实验数据集创建完成！')
print(f'   数据集表: experiment_dataset')
print(f'   题目总数: {total}')
print(f'   涵盖科目: {len(subject_weights)}个')
print('='*60)
