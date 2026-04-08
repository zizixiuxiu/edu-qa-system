"""检查 knowledge 表结构"""
import psycopg2

conn = psycopg2.connect(
    host='localhost', port=15432, database='edu_qa',
    user='postgres', password='password'
)
cur = conn.cursor()

cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'knowledge' ORDER BY ordinal_position")
print("Knowledge table columns:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

cur.close()
conn.close()
