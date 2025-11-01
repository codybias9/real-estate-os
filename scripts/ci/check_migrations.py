#!/usr/bin/env python3
"""
CI Script: Check that new database migrations include tenant_id and RLS

Validates that all new tables have:
1. tenant_id column (UUID, NOT NULL)
2. Row-Level Security (RLS) enabled
3. tenant_isolation policy

Part of Wave 1.7 - CI checks for tenant_id presence.
"""

import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple

# Tables that should be exempt from tenant_id requirement
EXEMPT_TABLES = [
    'alembic_version',
    'spatial_ref_sys',
    'tenant',  # The tenant table itself
]


def extract_tables(migration_content: str) -> List[str]:
    """Extract all CREATE TABLE statements"""
    # Match: CREATE TABLE table_name
    pattern = r"(?:op\.)?create_table\s*\(\s*['\"](\w+)['\"]"
    matches = re.findall(pattern, migration_content, re.IGNORECASE | re.MULTILINE)
    return [table for table in matches if table not in EXEMPT_TABLES]


def has_tenant_id_column(migration_content: str, table_name: str) -> bool:
    """Check if table has tenant_id column"""
    # Look for tenant_id column in the create_table block for this table
    # Pattern: sa.Column('tenant_id', ...UUID...)
    patterns = [
        rf"create_table\s*\(\s*['\"{table_name}\"'].*?tenant_id.*?UUID",
        rf"Column\s*\(\s*['\"]tenant_id['\"].*?UUID",
    ]

    for pattern in patterns:
        if re.search(pattern, migration_content, re.DOTALL | re.IGNORECASE):
            return True

    return False


def has_rls_enabled(migration_content: str, table_name: str) -> bool:
    """Check if RLS is enabled for table"""
    patterns = [
        rf"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY",
        rf"ENABLE ROW LEVEL SECURITY.*?{table_name}",
        rf"{table_name}.*?ENABLE ROW LEVEL SECURITY",
    ]

    for pattern in patterns:
        if re.search(pattern, migration_content, re.IGNORECASE):
            return True

    return False


def has_tenant_isolation_policy(migration_content: str, table_name: str) -> bool:
    """Check if tenant_isolation policy exists"""
    patterns = [
        rf"CREATE POLICY.*?{table_name}_tenant_isolation.*?ON {table_name}",
        rf"CREATE POLICY.*?tenant_isolation.*?ON {table_name}",
    ]

    for pattern in patterns:
        if re.search(pattern, migration_content, re.IGNORECASE):
            return True

    return False


def check_migration(migration_file: Path) -> Dict[str, List[str]]:
    """
    Check a migration file for tenant_id requirements

    Returns:
        Dict with 'errors' and 'warnings' lists
    """
    result = {'errors': [], 'warnings': []}

    try:
        content = migration_file.read_text()
        tables = extract_tables(content)

        if not tables:
            return result  # No tables created, skip

        for table in tables:
            issues = []

            # Check tenant_id column
            if not has_tenant_id_column(content, table):
                issues.append(f"Missing tenant_id column")

            # Check RLS enabled
            if not has_rls_enabled(content, table):
                issues.append(f"RLS not enabled")

            # Check tenant_isolation policy
            if not has_tenant_isolation_policy(content, table):
                issues.append(f"Missing tenant_isolation policy")

            if issues:
                error_msg = (
                    f"{migration_file.name}: Table '{table}'\n"
                    f"  Issues: {', '.join(issues)}"
                )
                result['errors'].append(error_msg)

    except Exception as e:
        result['errors'].append(f"{migration_file.name}: Error reading file: {e}")

    return result


def main():
    """Main entry point"""
    project_root = Path(__file__).parent.parent.parent
    migrations_dir = project_root / 'db' / 'versions'

    if not migrations_dir.exists():
        print("⚠️  No migrations directory found")
        sys.exit(0)

    all_errors = []
    all_warnings = []

    # Check all migration files
    for migration_file in sorted(migrations_dir.glob('*.py')):
        if migration_file.name == '__init__.py':
            continue

        result = check_migration(migration_file)
        all_errors.extend(result['errors'])
        all_warnings.extend(result['warnings'])

    # Print results
    if all_errors:
        print("❌ Migration Check Failed\n")
        print("The following migrations have tenant_id or RLS issues:\n")
        for error in all_errors:
            print(error)
            print()

        print("\n" + "=" * 80)
        print("FIX INSTRUCTIONS:")
        print("=" * 80)
        print()
        print("All new tables must include:")
        print()
        print("1. tenant_id column:")
        print("   sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False)")
        print()
        print("2. Enable RLS:")
        print("   op.execute('ALTER TABLE <table_name> ENABLE ROW LEVEL SECURITY')")
        print()
        print("3. Create tenant_isolation policy:")
        print("   op.execute('''")
        print("       CREATE POLICY <table>_tenant_isolation ON <table>")
        print("       FOR ALL")
        print("       USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)")
        print("   ''')")
        print()
        print("4. Add foreign key to tenant table:")
        print("   sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'])")
        print()
        print("Example migration: db/versions/003_provenance_foundation.py")
        print()
        print("Tables exempt from tenant_id:")
        for table in EXEMPT_TABLES:
            print(f"  - {table}")
        print()

        sys.exit(1)
    elif all_warnings:
        print("⚠️  Migration Check Warnings\n")
        for warning in all_warnings:
            print(warning)
            print()
        sys.exit(0)
    else:
        print("✅ All migrations properly include tenant_id and RLS")
        sys.exit(0)


if __name__ == '__main__':
    main()
