from sqlalchemy import create_engine, text

engine = create_engine('postgresql://postgres:password@localhost:15432/edu_qa')

with engine.connect() as conn:
    # 修复所有字段约束
    fixes = [
        ("prompt_template", "VARCHAR"),
        ("total_qa", "INTEGER"),
        ("lora_path", "VARCHAR"),
    ]
    
    for column, dtype in fixes:
        try:
            conn.execute(text(f"""
                ALTER TABLE experts 
                ALTER COLUMN {column} DROP NOT NULL;
            """))
            print(f"✅ {column} 已修改为可空")
        except Exception as e:
            print(f"⚠️ {column}: {e}")
    
    conn.commit()
    print("\n🎉 数据库约束修复完成！")
