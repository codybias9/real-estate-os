#!/usr/bin/env python3
"""
CI Script: Check that all database queries include tenant_id filters

Scans Python files for SQLAlchemy queries and ensures tenant isolation.
Part of Wave 1.7 - CI checks for tenant_id presence.
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple

# Models that require tenant_id filtering
TENANT_SCOPED_MODELS = [
    'Property',
    'OwnerEntity',
    'PropertyOwnerLink',
    'FieldProvenance',
    'Scorecard',
    'ScoreExplainability',
    'Deal',
    'PacketEvent',
    'ContactSuppression',
    'EvidenceEvent',
]

# Patterns to detect queries
QUERY_PATTERNS = [
    r'db\.query\((\w+)\)',
    r'session\.query\((\w+)\)',
    r'select\((\w+)\)',
    r'db\.execute\(.*?select\((\w+)\)',
]

# Patterns that indicate tenant_id is used
TENANT_ID_PATTERNS = [
    r'tenant_id\s*=',
    r'filter.*tenant_id',
    r'filter_by.*tenant_id',
    r'SET\s+.*?app\.current_tenant_id',
    r'current_setting.*app\.current_tenant_id',
]

# Files/patterns to skip
SKIP_PATTERNS = [
    '/migrations/',
    '/tests/',
    '/test_',
    'check_tenant',  # Skip this file
    'check_migrations',
]


def should_skip_file(file_path: str) -> bool:
    """Check if file should be skipped"""
    for pattern in SKIP_PATTERNS:
        if pattern in file_path:
            return True
    return False


def extract_queries(content: str, file_path: str) -> List[Tuple[int, str, str]]:
    """Extract all database queries with their line numbers and models"""
    queries = []

    for line_num, line in enumerate(content.split('\n'), 1):
        for pattern in QUERY_PATTERNS:
            matches = re.finditer(pattern, line)
            for match in matches:
                model = match.group(1)
                if model in TENANT_SCOPED_MODELS:
                    queries.append((line_num, line.strip(), model))

    return queries


def check_tenant_context(content: str, query_line_num: int, context_lines: int = 10) -> bool:
    """
    Check if tenant_id is used within N lines before/after the query

    Args:
        content: Full file content
        query_line_num: Line number of the query
        context_lines: Number of lines to check before/after
    """
    lines = content.split('\n')
    start_line = max(0, query_line_num - context_lines - 1)
    end_line = min(len(lines), query_line_num + context_lines)

    context = '\n'.join(lines[start_line:end_line])

    # Check if tenant_id appears in context
    for pattern in TENANT_ID_PATTERNS:
        if re.search(pattern, context, re.IGNORECASE):
            return True

    return False


def check_file(file_path: Path) -> List[str]:
    """Check a single file for tenant_id usage"""
    errors = []

    try:
        content = file_path.read_text()
        queries = extract_queries(content, str(file_path))

        for line_num, line, model in queries:
            if not check_tenant_context(content, line_num):
                errors.append(
                    f"{file_path}:{line_num}: Query on tenant-scoped model '{model}' "
                    f"without tenant_id filter\n  → {line}"
                )

    except Exception as e:
        errors.append(f"{file_path}: Error reading file: {e}")

    return errors


def main():
    """Main entry point"""
    project_root = Path(__file__).parent.parent.parent
    errors = []

    # Check API files
    api_dir = project_root / 'api'
    if api_dir.exists():
        for py_file in api_dir.rglob('*.py'):
            if should_skip_file(str(py_file)):
                continue
            file_errors = check_file(py_file)
            errors.extend(file_errors)

    # Check DAG files
    dags_dir = project_root / 'dags'
    if dags_dir.exists():
        for py_file in dags_dir.rglob('*.py'):
            if should_skip_file(str(py_file)):
                continue
            file_errors = check_file(py_file)
            errors.extend(file_errors)

    # Print results
    if errors:
        print("❌ Tenant ID Check Failed\n")
        print("The following queries on tenant-scoped models are missing tenant_id filters:\n")
        for error in errors:
            print(error)
            print()

        print("\n" + "=" * 80)
        print("FIX INSTRUCTIONS:")
        print("=" * 80)
        print()
        print("Ensure all queries on tenant-scoped models include tenant_id:")
        print()
        print("Option 1: RLS (Row-Level Security) - Set tenant context:")
        print("  db.execute(f\"SET LOCAL app.current_tenant_id = '{tenant_id}'\")")
        print()
        print("Option 2: Explicit filter:")
        print("  db.query(Property).filter(Property.tenant_id == tenant_id)")
        print()
        print("Option 3: Filter by:")
        print("  db.query(Property).filter_by(tenant_id=tenant_id)")
        print()
        print("Tenant-scoped models:")
        for model in TENANT_SCOPED_MODELS:
            print(f"  - {model}")
        print()

        sys.exit(1)
    else:
        print("✅ All tenant-scoped queries include tenant_id filters")
        sys.exit(0)


if __name__ == '__main__':
    main()
