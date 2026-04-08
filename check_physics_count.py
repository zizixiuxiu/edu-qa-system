"""检查物理科目题目数量"""
import psycopg2

conn = psycopg2.connect(
    host='localhost', port=15432, database='edu_qa',
    user='postgres', password='password'
)
cur = conn.cursor()

# 统计各科目题目数
cur.execute("SELECT subject, COUNT(*) FROM benchmark_datasets GROUP BY subject ORDER BY COUNT(*) DESC")
print('各科目题目数量:')
for row in cur.fetchall():
    print(f'  {row[0]}: {row[1]}')

cur.close()
conn.close()
