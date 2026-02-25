#!/usr/bin/env python3
"""
Script to clean requisition_detail and related tables.
This will remove all records from:
- langgraph_checkpoints
- requisition_detail
- requisition_requests
- llm_request_log (optional, but recommended if tied to requests)
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def clean_requisition_data(db_url: str, dry_run: bool = False):
    """Cleans requisition data from the database."""
    print(f"Connecting to database...")
    engine = create_engine(db_url)
    
    tables_to_clean = [
        "langgraph_checkpoints",
        "requisition_detail",
        "requisition_requests",
        "llm_request_log"
    ]
    
    try:
        with engine.connect() as conn:
            # Check counts first
            print("\nCurrent record counts:")
            for table in tables_to_clean:
                try:
                    res = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = res.scalar()
                    print(f"- {table}: {count}")
                except Exception as e:
                    print(f"- {table}: Error checking count ({e})")

            if dry_run:
                print("\n[DRY RUN] No records will be deleted.")
                return

            print("\nStarting cleanup...")
            # We use TRUNCATE for speed and to reset identities, 
            # but we need to handle dependencies.
            # CASCADE will handle foreign keys.
            
            # Delete in order of dependencies if not using CASCADE TRUNCATE
            # 1. langgraph_checkpoints (references requisition_requests.request_id)
            # 2. requisition_detail (references requisition_requests.id)
            # 3. requisition_requests
            # 4. llm_request_log (loosely related by request_id string)
            
            for table in tables_to_clean:
                print(f"Cleaning {table}...")
                conn.execute(text(f"DELETE FROM {table}"))
            
            conn.commit()
            print("\n✅ Cleanup successful!")
            
            # Verify counts again
            print("\nUpdated record counts:")
            for table in tables_to_clean:
                try:
                    res = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = res.scalar()
                    print(f"- {table}: {count}")
                except Exception as e:
                    print(f"- {table}: Error checking count ({e})")
                    
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        sys.exit(1)

def main():
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    
    if not db_url:
        print("❌ Error: DATABASE_URL not found in environment.")
        sys.exit(1)
        
    dry_run = "--dry-run" in sys.argv
    force = "--force" in sys.argv
    
    if not dry_run and not force:
        confirm = input("⚠️  This will delete ALL requisition data. Are you sure? (y/n): ")
        if confirm.lower() != 'y':
            print("Aborted.")
            return

    clean_requisition_data(db_url, dry_run=dry_run)

if __name__ == "__main__":
    main()
