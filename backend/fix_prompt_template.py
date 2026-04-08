from sqlalchemy import create_engine, text

engine = create_engine('postgresql://postgres:password@localhost:15432/edu_qa')

with engine.connect() as conn:
    # 修改 prompt_template 列为可空
    conn.execute(text("""
        ALTER TABLE experts 
        ALTER COLUMN prompt_template DROP NOT NULL;
    """))
    conn.commit()
    print("✅ 已修改 prompt_template 列为可空")
