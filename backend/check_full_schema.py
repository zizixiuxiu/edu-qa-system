from sqlalchemy import create_engine, inspect

engine = create_engine('postgresql://postgres:password@localhost:15432/edu_qa')
inspector = inspect(engine)

print("=== Knowledge Table Schema ===")
columns = inspector.get_columns('knowledge')
for c in columns:
    print(f"  {c['name']}: {c['type']}")

print("\n=== Tier0Knowledge Table Schema ===")
try:
    columns = inspector.get_columns('tier0_knowledge')
    for c in columns:
        print(f"  {c['name']}: {c['type']}")
except:
    print("  Table not found")
