"""创建均衡实验数据集 - 多科目按比例随机抽取"""
import psycopg2
import random

conn = psycopg2.connect(
    host='localhost', port=15432, database='edu_qa',
    user='postgres', password='password'
)
cur = conn.cursor()

print('='*60)
print('创建均衡实验数据集')
print('='*60)

# 设置随机种子保证可重复
random.seed(42)

# 目标题目数
TARGET_TOTAL = 50

# 学科抽取比例（根据题目数量和重要性）
subject_distribution = {
    '数学': 10,
    '物理': 8, 
    '化学': 7,
    '生物': 7,
    '历史': 6,
    '地理': 6,
    '政治': 6
}

print(f'\n目标: 共{TARGET_TOTAL}题')
print('抽取分布:')
for subject, count in subject_distribution.items():
    print(f'  {subject}: {count}题')

# 创建实验数据集表
cur.execute("""
    DROP TABLE IF EXISTS experiment_dataset CASCADE;
    CREATE TABLE experiment_dataset (
        id SERIAL PRIMARY KEY,
        original_id INTEGER REFERENCES benchmark_datasets(id),
        question TEXT NOT NULL,
        correct_answer TEXT NOT NULL,
        subject VARCHAR NOT NULL,
        year VARCHAR,
        category VARCHAR,
        analysis TEXT
    )
""")

# 从各学科随机抽取
print('\n抽取题目...')
total_inserted = 0

for subject, count in subject_distribution.items():
    # 检查该科目有多少题
    cur.execute("SELECT COUNT(*) FROM benchmark_datasets WHERE subject = %s", (subject,))
    available = cur.fetchone()[0]
    
    if available < count:
        print(f'  ⚠ {subject}: 只有{available}题，抽取全部')
        count = available
    
    # 随机抽取
    cur.execute("""
        SELECT id, question, correct_answer, subject, year, category, analysis
        FROM benchmark_datasets 
        WHERE subject = %s
        ORDER BY RANDOM()
        LIMIT %s
    """, (subject, count))
    
    rows = cur.fetchall()
    for row in rows:
        cur.execute("""
            INSERT INTO experiment_dataset 
            (original_id, question, correct_answer, subject, year, category, analysis)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, row)
        total_inserted += 1
    
    print(f'  ✓ {subject}: 抽取{len(rows)}题')

conn.commit()

# 验证结果
print('\n' + '='*60)
print('数据集验证:')
cur.execute("SELECT subject, COUNT(*) FROM experiment_dataset GROUP BY subject ORDER BY COUNT(*) DESC")
for row in cur.fetchall():
    print(f'  {row[0]}: {row[1]}题')

cur.execute("SELECT COUNT(*) FROM experiment_dataset")
final_count = cur.fetchone()[0]

# 显示样本
print('\n样本题目预览:')
cur.execute("SELECT subject, question FROM experiment_dataset LIMIT 3")
for i, row in enumerate(cur.fetchall(), 1):
    preview = row[1][:80] + '...' if len(row[1]) > 80 else row[1]
    print(f'  {i}. [{row[0]}] {preview}')

print('\n' + '='*60)
print(f'✅ 实验数据集创建完成!')
print(f'   表名: experiment_dataset')
print(f'   总数: {final_count}题')
print(f'   学科: {len(subject_distribution)}个')
print('='*60)

cur.close()
conn.close()
