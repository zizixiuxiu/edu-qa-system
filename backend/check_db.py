from sqlalchemy import create_engine, inspect
engine = create_engine('postgresql://postgres:password@localhost:15432/edu_qa')
inspector = inspect(engine)
columns = inspector.get_columns('experts')
print("Experts table columns:")
for c in columns:
    print(f"  {c['name']}: {c['type']}")
