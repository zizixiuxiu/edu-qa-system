"""创建 benchmark 相关表"""
import psycopg2

conn = psycopg2.connect(
    host='localhost', port=15432, database='edu_qa',
    user='postgres', password='password'
)
cur = conn.cursor()

# 创建 benchmark_dataset 表
cur.execute("""
CREATE TABLE IF NOT EXISTS benchmark_dataset (
    id SERIAL PRIMARY KEY,
    filename VARCHAR NOT NULL,
    subject VARCHAR NOT NULL,
    question_count INTEGER DEFAULT 0,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
)
""")
print("Created benchmark_dataset table")

# 创建 benchmark_result 表
cur.execute("""
CREATE TABLE IF NOT EXISTS benchmark_result (
    id SERIAL PRIMARY KEY,
    dataset_id INTEGER REFERENCES benchmark_dataset(id),
    question_id VARCHAR NOT NULL,
    question_text TEXT,
    correct_answer TEXT,
    expert_answer TEXT,
    is_correct BOOLEAN DEFAULT FALSE,
    score FLOAT DEFAULT 0.0,
    overall_score FLOAT DEFAULT 0.0,
    accuracy_score FLOAT DEFAULT 0.0,
    completeness_score FLOAT DEFAULT 0.0,
    educational_score FLOAT DEFAULT 0.0,
    expert_id INTEGER,
    used_knowledge_ids JSONB,
    response_time_ms FLOAT DEFAULT 0.0,
    experiment_mode VARCHAR DEFAULT 'unknown',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print("Created benchmark_result table")

conn.commit()
print("✅ Benchmark tables created successfully!")

cur.close()
conn.close()
