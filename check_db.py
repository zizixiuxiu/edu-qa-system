"""检查数据库"""
import psycopg2

conn = psycopg2.connect(
    host='localhost', port=15432, database='edu_qa',
    user='postgres', password='password'
)
cur = conn.cursor()

# 检查表是否存在
cur.execute("""
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_name = 'experiment_dataset'
    );
""")
exists = cur.fetchone()[0]
print(f'experiment_dataset 表存在: {exists}')

if exists:
    cur.execute('SELECT COUNT(*) FROM experiment_dataset')
    print(f'题目数量: {cur.fetchone()[0]}')
else:
    print('表不存在，需要创建')

cur.close()
conn.close()
