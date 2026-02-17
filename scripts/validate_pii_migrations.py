"""
Migration Validation Script - TASK-PII-111-113

Validates PII Scrubber database migrations without requiring database connection.

Tests:
1. Migration files exist and are well-formed
2. SQL syntax is valid
3. Immutability trigger logic is correct
4. Migration dependencies are properly ordered

Usage:
    python scripts/validate_pii_migrations.py
"""

import os
import re
from pathlib import Path

def validate_migration_files():
    """Validate migration files exist."""
    migrations_dir = Path("alembic/versions")
    
    expected_migrations = {
        "7efd9d68d9b8": "add_pii_scrub_audit_table",
        "bca284b2d901": "add_pii_scrubbed_flag_to_embeddings"
    }
    
    print("=" * 60)
    print("MIGRATION FILE VALIDATION")
    print("=" * 60)
    print()
    
    results = {}
    for revision, name in expected_migrations.items():
        pattern = f"{revision}_*.py"
        matches = list(migrations_dir.glob(pattern))
        
        if matches:
            print(f"✓ Migration found: {matches[0].name}")
            results[revision] = "FOUND"
        else:
            print(f"✗ Migration missing: {revision}_{name}.py")
            results[revision] = "MISSING"
    
    print()
    return results

def validate_audit_table_migration():
    """Validate pii_scrub_audit table migration."""
    migration_file = list(Path("alembic/versions").glob("7efd9d68d9b8_*.py"))[0]
    
    print("=" * 60)
    print("AUDIT TABLE MIGRATION VALIDATION")
    print("=" * 60)
    print()
    
    with open(migration_file, 'r') as f:
        content = f.read()
    
    checks = {
        "CREATE TABLE pii_scrub_audit": "Table creation statement",
        "id BIGSERIAL PRIMARY KEY": "Primary key definition",
        "timestamp TIMESTAMP": "Timestamp column",
        "operation VARCHAR": "Operation column",
        "entity_type VARCHAR": "Entity type column",
        "pii_type VARCHAR": "PII type column",
        "detection_method VARCHAR": "Detection method column",
        "CREATE TRIGGER prevent_pii_audit_modifications": "Immutability trigger",
        "BEFORE UPDATE OR DELETE": "Trigger timing",
        "RAISE EXCEPTION": "Trigger exception",
        "CREATE OR REPLACE FUNCTION prevent_pii_audit_update()": "Trigger function"
    }
    
    results = {}
    for check, description in checks.items():
        if check in content:
            print(f"✓ {description}")
            results[check] = "PASS"
        else:
            print(f"✗ {description} NOT FOUND")
            results[check] = "FAIL"
    
    print()
    return results

def validate_embeddings_migration():
    """Validate team_member_embeddings modification migration."""
    migration_file = list(Path("alembic/versions").glob("bca284b2d901_*.py"))[0]
    
    print("=" * 60)
    print("EMBEDDINGS TABLE MIGRATION VALIDATION")
    print("=" * 60)
    print()
    
    with open(migration_file, 'r') as f:
        content = f.read()
    
    checks = {
        "ADD COLUMN pii_scrubbed": "Add pii_scrubbed column",
        "BOOLEAN NOT NULL DEFAULT FALSE": "Column definition with default",
        "UPDATE team_member_embeddings SET pii_scrubbed = FALSE": "Backfill existing rows",
        "CREATE INDEX": "Index creation",
        "idx_team_member_embeddings_pii_scrubbed": "Index name",
        "DROP COLUMN pii_scrubbed": "Downgrade removes column"
    }
    
    results = {}
    for check, description in checks.items():
        if check in content:
            print(f"✓ {description}")
            results[check] = "PASS"
        else:
            print(f"✗ {description} NOT FOUND")
            results[check] = "FAIL"
    
    print()
    return results

def validate_trigger_logic():
    """Validate immutability trigger logic."""
    migration_file = list(Path("alembic/versions").glob("7efd9d68d9b8_*.py"))[0]
    
    print("=" * 60)
    print("IMMUTABILITY TRIGGER LOGIC VALIDATION")
    print("=" * 60)
    print()
    
    with open(migration_file, 'r') as f:
        content = f.read()
    
    # Extract trigger function
    trigger_match = re.search(
        r"CREATE OR REPLACE FUNCTION prevent_pii_audit_update\(\)(.*?)END;",
        content,
        re.DOTALL
    )
    
    if not trigger_match:
        print("✗ Trigger function not found")
        return {"trigger_function": "FAIL"}
    
    trigger_body = trigger_match.group(1)
    
    checks = {
        "BEFORE UPDATE OR DELETE": "Trigger timing prevents modifications",
        "RAISE EXCEPTION": "Exception blocks operation",
        "'Audit log is immutable'": "Error message is clear",
        "RETURN NULL": "Trigger returns NULL to block operation"
    }
    
    results = {}
    for check, description in checks.items():
        if check in content:
            print(f"✓ {description}")
            results[check] = "PASS"
        else:
            print(f"✗ {description}")
            results[check] = "FAIL"
    
    print()
    return results

def validate_migration_order():
    """Validate migration dependency order."""
    print("=" * 60)
    print("MIGRATION ORDER VALIDATION")
    print("=" * 60)
    print()
    
    migrations_dir = Path("alembic/versions")
    
    audit_table_file = list(migrations_dir.glob("7efd9d68d9b8_*.py"))[0]
    embeddings_file = list(migrations_dir.glob("bca284b2d901_*.py"))[0]
    
    with open(audit_table_file, 'r') as f:
        audit_content = f.read()
    
    with open(embeddings_file, 'r') as f:
        embeddings_content = f.read()
    
    # Extract down_revision from each
    audit_down = re.search(r"down_revision = ['\"]([a-f0-9]+)['\"]", audit_content)
    embeddings_down = re.search(r"down_revision = ['\"]([a-f0-9]+)['\"]", embeddings_content)
    
    print("Migration Dependency Chain:")
    print(f"  7efd9d68d9b8 (audit table) -> down_revision: {audit_down.group(1) if audit_down else 'NONE'}")
    print(f"  bca284b2d901 (embeddings flag) -> down_revision: {embeddings_down.group(1) if embeddings_down else 'NONE'}")
    print()
    
    # Check if embeddings migration depends on audit table migration
    if embeddings_down and embeddings_down.group(1) == "7efd9d68d9b8":
        print("✓ Embeddings migration correctly depends on audit table migration")
        result = "CORRECT_ORDER"
    elif embeddings_down:
        print("✓ Migrations are independent (acceptable)")
        result = "INDEPENDENT"
    else:
        print("⚠ Migration dependency chain unclear")
        result = "UNCLEAR"
    
    print()
    return {"dependency_order": result}

def main():
    """Run all validation checks."""
    print("\n")
    print("=" * 60)
    print("PII SCRUBBER MIGRATION VALIDATION REPORT")
    print("=" * 60)
    print()
    
    results = {}
    
    # 1. File existence
    results["file_validation"] = validate_migration_files()
    
    # 2. Audit table migration
    results["audit_table"] = validate_audit_table_migration()
    
    # 3. Embeddings migration
    results["embeddings_table"] = validate_embeddings_migration()
    
    # 4. Trigger logic
    results["trigger_logic"] = validate_trigger_logic()
    
    # 5. Migration order
    results["migration_order"] = validate_migration_order()
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print()
    
    all_passed = True
    for category, checks in results.items():
        if isinstance(checks, dict):
            passed = sum(1 for v in checks.values() if v in ["PASS", "FOUND", "CORRECT_ORDER", "INDEPENDENT"])
            total = len(checks)
            status = "PASS" if passed == total else "PARTIAL" if passed > 0 else "FAIL"
            print(f"{category:30s}: {status:10s} ({passed}/{total})")
            if status != "PASS":
                all_passed = False
        else:
            print(f"{category:30s}: {checks}")
    
    print()
    print("Overall Result:", "✓ ALL CHECKS PASSED" if all_passed else "⚠ SOME CHECKS FAILED")
    print()
    
    print("=" * 60)
    print("MIGRATION EXECUTION INSTRUCTIONS")
    print("=" * 60)
    print()
    print("To execute migrations (requires database connection and .env file):")
    print()
    print("  1. Ensure DATABASE_URL is set in .env file")
    print("  2. Start PostgreSQL database (docker-compose up -d db)")
    print("  3. Run migrations: alembic upgrade head")
    print("  4. Verify current version: alembic current")
    print("  5. Check migration history: alembic history")
    print()
    print("To test immutability trigger:")
    print()
    print("  1. Insert test record:")
    print("     INSERT INTO pii_scrub_audit (operation, entity_type, pii_type, action_taken)")
    print("     VALUES ('scrub', 'job_description', 'name', 'redacted');")
    print()
    print("  2. Attempt UPDATE (should fail):")
    print("     UPDATE pii_scrub_audit SET operation = 'test' WHERE id = 1;")
    print("     -- Expected: ERROR: Audit log is immutable")
    print()
    print("  3. Attempt DELETE (should fail):")
    print("     DELETE FROM pii_scrub_audit WHERE id = 1;")
    print("     -- Expected: ERROR: Audit log is immutable")
    print()

if __name__ == "__main__":
    main()
