"""检查实验数据集表结构"""
import psycopg2

conn = psycopg2.connect(
    host='localhost', port=15432, database='edu_qa',
    user='postgres', password='password'
)
cur = conn.cursor()

cur.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'experiment_dataset' 
    ORDER BY ordinal_position
""")
print('experiment_dataset 表结构:')
for row in cur.fetchall():
    print(f'  {row[0]}: {row[1]}')

cur.execute("SELECT COUNT(*) FROM experiment_dataset")
print(f'\n总题目数: {cur.fetchone()[0]}')

cur.close()
conn.close()
