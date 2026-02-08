#!/usr/bin/env python3
"""
Database Migration Helper Script

Provides utilities for zero-downtime database migrations including:
- Schema validation
- Migration rollback
- Data verification
- Migration timing analysis
"""

import argparse
import json
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


class MigrationHelper:
    """Helper for zero-downtime database migrations"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.conn = None
    
    def connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(self.database_url)
            self.conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            print("✓ Connected to database")
        except Exception as e:
            print(f"✗ Failed to connect to database: {e}")
            sys.exit(1)
    
    def disconnect(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            print("✓ Disconnected from database")
    
    def check_migration_safety(self) -> Dict[str, any]:
        """
        Check if database is ready for migration
        
        Returns safety report with:
        - Active connections
        - Long-running queries
        - Lock status
        - Replication lag
        """
        cursor = self.conn.cursor()
        
        # Check active connections
        cursor.execute("""
            SELECT count(*) as active_connections
            FROM pg_stat_activity
            WHERE state = 'active'
            AND query NOT LIKE '%pg_stat_activity%'
        """)
        active_connections = cursor.fetchone()[0]
        
        # Check long-running queries
        cursor.execute("""
            SELECT 
                pid,
                now() - query_start AS duration,
                query
            FROM pg_stat_activity
            WHERE state = 'active'
            AND query NOT LIKE '%pg_stat_activity%'
            AND now() - query_start > interval '1 minute'
            ORDER BY duration DESC
        """)
        long_queries = cursor.fetchall()
        
        # Check for locks
        cursor.execute("""
            SELECT 
                count(*) as lock_count
            FROM pg_locks
            WHERE NOT granted
        """)
        lock_count = cursor.fetchone()[0]
        
        # Check replication lag (if replicas exist)
        try:
            cursor.execute("""
                SELECT 
                    client_addr,
                    state,
                    sync_state,
                    COALESCE(replay_lag, '0 seconds'::interval) as lag
                FROM pg_stat_replication
            """)
            replication_status = cursor.fetchall()
        except:
            replication_status = []
        
        cursor.close()
        
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "active_connections": active_connections,
            "long_running_queries": len(long_queries),
            "pending_locks": lock_count,
            "replication_lag_seconds": max([r[3].total_seconds() for r in replication_status], default=0),
            "safe_to_migrate": True
        }
        
        # Determine safety
        if active_connections > 50:
            report["safe_to_migrate"] = False
            report["warning"] = f"High connection count: {active_connections}"
        
        if len(long_queries) > 0:
            report["safe_to_migrate"] = False
            report["warning"] = f"Long-running queries detected: {len(long_queries)}"
        
        if lock_count > 10:
            report["safe_to_migrate"] = False
            report["warning"] = f"High lock contention: {lock_count}"
        
        if report["replication_lag_seconds"] > 30:
            report["safe_to_migrate"] = False
            report["warning"] = f"Replication lag too high: {report['replication_lag_seconds']}s"
        
        return report
    
    def validate_schema_changes(self, migration_file: str) -> Dict[str, any]:
        """
        Validate that schema changes are backward-compatible
        
        Checks for dangerous operations:
        - DROP COLUMN
        - ALTER COLUMN TYPE
        - ADD NOT NULL without DEFAULT
        - Non-concurrent index creation
        """
        with open(migration_file, 'r') as f:
            migration_sql = f.read().upper()
        
        dangerous_operations = []
        warnings = []
        
        # Check for DROP COLUMN
        if 'DROP COLUMN' in migration_sql:
            dangerous_operations.append("DROP COLUMN detected - use 3-phase approach")
        
        # Check for ALTER COLUMN TYPE
        if 'ALTER COLUMN' in migration_sql and 'TYPE' in migration_sql:
            dangerous_operations.append("ALTER COLUMN TYPE detected - may lock table")
        
        # Check for ADD NOT NULL without DEFAULT
        if 'ADD COLUMN' in migration_sql and 'NOT NULL' in migration_sql:
            if 'DEFAULT' not in migration_sql:
                dangerous_operations.append("ADD COLUMN NOT NULL without DEFAULT - will fail on existing rows")
        
        # Check for non-concurrent index creation
        if 'CREATE INDEX' in migration_sql and 'CONCURRENTLY' not in migration_sql:
            warnings.append("CREATE INDEX without CONCURRENTLY - will lock table")
        
        # Check for RENAME COLUMN
        if 'RENAME COLUMN' in migration_sql:
            dangerous_operations.append("RENAME COLUMN detected - use 3-phase approach")
        
        return {
            "migration_file": migration_file,
            "dangerous_operations": dangerous_operations,
            "warnings": warnings,
            "safe_to_apply": len(dangerous_operations) == 0
        }
    
    def create_index_concurrently(self, table: str, column: str, index_name: Optional[str] = None):
        """Create index concurrently without locking table"""
        if not index_name:
            index_name = f"idx_{table}_{column}"
        
        cursor = self.conn.cursor()
        
        print(f"Creating index {index_name} on {table}({column}) CONCURRENTLY...")
        start_time = time.time()
        
        try:
            cursor.execute(f"""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS {index_name}
                ON {table} ({column})
            """)
            
            elapsed = time.time() - start_time
            print(f"✓ Index created in {elapsed:.2f} seconds")
            
        except Exception as e:
            print(f"✗ Failed to create index: {e}")
            raise
        finally:
            cursor.close()
    
    def add_column_safe(self, table: str, column: str, column_type: str, default: any = None):
        """Add column safely with optional default"""
        cursor = self.conn.cursor()
        
        # Step 1: Add nullable column
        print(f"Adding column {table}.{column} ({column_type})...")
        cursor.execute(f"""
            ALTER TABLE {table}
            ADD COLUMN IF NOT EXISTS {column} {column_type}
        """)
        print(f"✓ Column added (nullable)")
        
        # Step 2: Set default if provided
        if default is not None:
            print(f"Setting default value: {default}")
            cursor.execute(f"""
                ALTER TABLE {table}
                ALTER COLUMN {column} SET DEFAULT {default}
            """)
            print(f"✓ Default set")
            
            # Step 3: Backfill existing rows (in batches)
            print(f"Backfilling existing rows...")
            cursor.execute(f"""
                UPDATE {table}
                SET {column} = {default}
                WHERE {column} IS NULL
            """)
            print(f"✓ Backfill complete")
        
        cursor.close()
    
    def verify_migration(self, expected_tables: List[str] = None, 
                        expected_columns: Dict[str, List[str]] = None) -> Dict[str, any]:
        """
        Verify migration completed successfully
        
        Args:
            expected_tables: List of table names that should exist
            expected_columns: Dict mapping table names to column lists
        """
        cursor = self.conn.cursor()
        
        # Get all tables
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
        """)
        actual_tables = [row[0] for row in cursor.fetchall()]
        
        # Get all columns by table
        cursor.execute("""
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
            ORDER BY table_name, ordinal_position
        """)
        actual_columns = {}
        for table_name, column_name in cursor.fetchall():
            if table_name not in actual_columns:
                actual_columns[table_name] = []
            actual_columns[table_name].append(column_name)
        
        cursor.close()
        
        verification = {
            "timestamp": datetime.utcnow().isoformat(),
            "tables_found": len(actual_tables),
            "verification_passed": True,
            "missing_tables": [],
            "missing_columns": {}
        }
        
        # Check expected tables
        if expected_tables:
            missing_tables = set(expected_tables) - set(actual_tables)
            if missing_tables:
                verification["verification_passed"] = False
                verification["missing_tables"] = list(missing_tables)
        
        # Check expected columns
        if expected_columns:
            for table, columns in expected_columns.items():
                if table not in actual_columns:
                    verification["verification_passed"] = False
                    verification["missing_columns"][table] = columns
                else:
                    missing = set(columns) - set(actual_columns[table])
                    if missing:
                        verification["verification_passed"] = False
                        verification["missing_columns"][table] = list(missing)
        
        return verification
    
    def estimate_migration_time(self, table: str, operation: str) -> Dict[str, any]:
        """
        Estimate how long a migration operation will take
        
        Args:
            table: Table name
            operation: Operation type (add_column, create_index, backfill)
        """
        cursor = self.conn.cursor()
        
        # Get table size
        cursor.execute(f"""
            SELECT 
                pg_size_pretty(pg_total_relation_size('{table}')) as size,
                pg_total_relation_size('{table}') as bytes,
                n_live_tup as row_count
            FROM pg_stat_user_tables
            WHERE relname = '{table}'
        """)
        
        result = cursor.fetchone()
        if not result:
            return {"error": f"Table {table} not found"}
        
        size_pretty, size_bytes, row_count = result
        cursor.close()
        
        # Estimate based on operation and table size
        estimates = {
            "add_column": 0.001,  # Very fast
            "create_index": size_bytes / (100 * 1024 * 1024),  # ~100MB/s
            "backfill": row_count / 10000  # ~10k rows/s
        }
        
        estimated_seconds = estimates.get(operation, 60)
        
        return {
            "table": table,
            "operation": operation,
            "table_size": size_pretty,
            "row_count": row_count,
            "estimated_duration_seconds": estimated_seconds,
            "estimated_duration_minutes": estimated_seconds / 60
        }
    
    def generate_rollback_sql(self, migration_type: str, **kwargs) -> str:
        """Generate rollback SQL for common migration types"""
        
        if migration_type == "add_column":
            table = kwargs.get("table")
            column = kwargs.get("column")
            return f"ALTER TABLE {table} DROP COLUMN IF EXISTS {column};"
        
        elif migration_type == "create_index":
            index_name = kwargs.get("index_name")
            return f"DROP INDEX IF EXISTS {index_name};"
        
        elif migration_type == "create_table":
            table = kwargs.get("table")
            return f"DROP TABLE IF EXISTS {table} CASCADE;"
        
        elif migration_type == "add_constraint":
            table = kwargs.get("table")
            constraint_name = kwargs.get("constraint_name")
            return f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {constraint_name};"
        
        else:
            return f"-- No automatic rollback for {migration_type}"


def main():
    parser = argparse.ArgumentParser(description="Database migration helper")
    parser.add_argument("--database-url", required=True, help="PostgreSQL connection URL")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Safety check command
    safety_parser = subparsers.add_parser("check-safety", help="Check if database is ready for migration")
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate migration file for safety")
    validate_parser.add_argument("migration_file", help="Path to migration SQL file")
    
    # Create index command
    index_parser = subparsers.add_parser("create-index", help="Create index concurrently")
    index_parser.add_argument("--table", required=True, help="Table name")
    index_parser.add_argument("--column", required=True, help="Column name")
    index_parser.add_argument("--index-name", help="Index name (optional)")
    
    # Add column command
    column_parser = subparsers.add_parser("add-column", help="Add column safely")
    column_parser.add_argument("--table", required=True, help="Table name")
    column_parser.add_argument("--column", required=True, help="Column name")
    column_parser.add_argument("--type", required=True, help="Column type")
    column_parser.add_argument("--default", help="Default value")
    
    # Verify command
    verify_parser = subparsers.add_parser("verify", help="Verify migration completed")
    verify_parser.add_argument("--config", help="JSON config with expected schema")
    
    # Estimate command
    estimate_parser = subparsers.add_parser("estimate", help="Estimate migration time")
    estimate_parser.add_argument("--table", required=True, help="Table name")
    estimate_parser.add_argument("--operation", required=True, 
                                choices=["add_column", "create_index", "backfill"],
                                help="Operation type")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    helper = MigrationHelper(args.database_url)
    helper.connect()
    
    try:
        if args.command == "check-safety":
            report = helper.check_migration_safety()
            print("\n" + "="*60)
            print("DATABASE SAFETY CHECK")
            print("="*60)
            print(json.dumps(report, indent=2))
            
            if report["safe_to_migrate"]:
                print("\n✓ Database is ready for migration")
                sys.exit(0)
            else:
                print(f"\n✗ Database is NOT ready: {report.get('warning')}")
                sys.exit(1)
        
        elif args.command == "validate":
            report = helper.validate_schema_changes(args.migration_file)
            print("\n" + "="*60)
            print("MIGRATION VALIDATION")
            print("="*60)
            print(json.dumps(report, indent=2))
            
            if report["safe_to_apply"]:
                print("\n✓ Migration is safe to apply")
                sys.exit(0)
            else:
                print("\n✗ Migration contains dangerous operations")
                sys.exit(1)
        
        elif args.command == "create-index":
            helper.create_index_concurrently(
                args.table, 
                args.column, 
                args.index_name
            )
        
        elif args.command == "add-column":
            helper.add_column_safe(
                args.table,
                args.column,
                args.type,
                args.default
            )
        
        elif args.command == "verify":
            if args.config:
                with open(args.config, 'r') as f:
                    config = json.load(f)
                    expected_tables = config.get("tables")
                    expected_columns = config.get("columns")
            else:
                expected_tables = None
                expected_columns = None
            
            report = helper.verify_migration(expected_tables, expected_columns)
            print("\n" + "="*60)
            print("MIGRATION VERIFICATION")
            print("="*60)
            print(json.dumps(report, indent=2))
            
            if report["verification_passed"]:
                print("\n✓ Migration verification passed")
                sys.exit(0)
            else:
                print("\n✗ Migration verification failed")
                sys.exit(1)
        
        elif args.command == "estimate":
            estimate = helper.estimate_migration_time(args.table, args.operation)
            print("\n" + "="*60)
            print("MIGRATION TIME ESTIMATE")
            print("="*60)
            print(json.dumps(estimate, indent=2))
    
    finally:
        helper.disconnect()


if __name__ == "__main__":
    main()
