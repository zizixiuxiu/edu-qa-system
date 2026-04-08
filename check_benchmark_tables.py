"""检查 benchmark 相关表"""
import psycopg2

conn = psycopg2.connect(
    host='localhost', port=15432, database='edu_qa',
    user='postgres', password='password'
)
cur = conn.cursor()

# 检查表是否存在
cur.execute("""
    SELECT table_name FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_name IN ('benchmark_dataset', 'benchmark_result')
""")
print("Existing benchmark tables:")
for row in cur.fetchall():
    print(f"  - {row[0]}")

# 检查 benchmark_result 表结构
cur.execute("""
    SELECT column_name, data_type FROM information_schema.columns 
    WHERE table_name = 'benchmark_result' ORDER BY ordinal_position
""")
print("\nbenchmark_result columns:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

cur.close()
conn.close()
