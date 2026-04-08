import psycopg2
from datetime import datetime

conn = psycopg2.connect(
    host='localhost',
    port=15432,
    database='edu_qa',
    user='postgres',
    password='password'
)
cursor = conn.cursor()

# 查看表结构
cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'benchmark_results'")
print('benchmark_results columns:', [c[0] for c in cursor.fetchall()])

cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'sessions'")
print('sessions columns:', [c[0] for c in cursor.fetchall()])

# 直接从benchmark_results获取实验统计 - 按experiment_config分组
cursor.execute('''
SELECT experiment_config, 
       COUNT(*) as total,
       SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct,
       ROUND(100.0 * SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) / COUNT(*), 2) as accuracy
FROM benchmark_results 
WHERE experiment_config IS NOT NULL AND experiment_config != ''
GROUP BY experiment_config
ORDER BY accuracy DESC
''')

print('\n=== 按配置分组的实验统计 ===')
results = cursor.fetchall()
for r in results:
    print(f'配置:{r[0][:40]:40} | 题目:{r[1]:4} | 正确:{r[2]:4} | 准确率:{r[3]}%')

# 获取最近的详细实验结果
print('\n=== 最近20条实验记录 ===')
cursor.execute('''
SELECT br.created_at, br.experiment_config, br.is_correct, br.experiment_id
FROM benchmark_results br
WHERE br.experiment_config IS NOT NULL
ORDER BY br.created_at DESC
LIMIT 20
''')
for r in cursor.fetchall():
    config = r[1] if r[1] else 'N/A'
    correct = '✓' if r[2] else '✗'
    print(f'{str(r[0])[:19]} | {config[:35]:35} | {correct}')

cursor.close()
conn.close()
