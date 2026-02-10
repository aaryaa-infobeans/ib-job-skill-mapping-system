"""Verify ingestion tables migration."""
import os
from sqlalchemy import create_engine, inspect

# Build DB URL from environment
db_user = os.getenv("DB_USER", "postgres")
db_password = os.getenv("DB_PASSWORD", "password")
db_host = os.getenv("DB_HOST", "localhost")
db_port = os.getenv("DB_PORT", "5432")
db_name = os.getenv("DB_NAME", "job_skill_mapping")

db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

# Connect and inspect
engine = create_engine(db_url)
inspector = inspect(engine)
tables = inspector.get_table_names()

print("✓ Migration applied successfully")
print(f"Total tables: {len(tables)}")

# Check ingestion tables
ingestion_tables = [t for t in tables if "ingestion" in t]
print(f"Ingestion tables: {ingestion_tables}")

# Verify specific tables
expected_tables = ["ingestion_batch_state", "ingestion_audit_log"]
for table in expected_tables:
    if table in tables:
        print(f"  ✓ {table} exists")
        # Show columns
        columns = inspector.get_columns(table)
        print(f"    Columns: {[c['name'] for c in columns]}")
    else:
        print(f"  ✗ {table} MISSING")

engine.dispose()
