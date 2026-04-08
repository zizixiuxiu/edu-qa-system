"""检查 sessions 表完整结构"""
import psycopg2

conn = psycopg2.connect(
    host='localhost', port=15432, database='edu_qa',
    user='postgres', password='password'
)
cur = conn.cursor()

# 获取所有列
cur.execute("SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = 'sessions' ORDER BY ordinal_position")
print("Sessions table columns:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]} (nullable={row[2]})")

# 获取一列示例数据
cur.execute("SELECT * FROM sessions LIMIT 1")
if cur.description:
    print("\nColumn names from SELECT *:")
    for desc in cur.description:
        print(f"  {desc.name}")

cur.close()
conn.close()
