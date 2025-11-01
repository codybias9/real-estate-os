#!/usr/bin/env python3
"""
CI Script: Lint for proper tenant context usage patterns

Checks for:
1. FastAPI endpoints include tenant_id parameter
2. DAGs set tenant context before queries
3. Models have tenant_id column for tenant-scoped tables
4. No hardcoded tenant IDs (except default)

Part of Wave 1.7 - CI checks for tenant_id presence.
"""

import re
import sys
from pathlib import Path
from typing import List

# Patterns to detect FastAPI route definitions
FASTAPI_ROUTE_PATTERNS = [
    r'@router\.(get|post|put|patch|delete)\(',
    r'@app\.(get|post|put|patch|delete)\(',
]

# Hardcoded UUID that should not be used (except for default tenant)
DEFAULT_TENANT_ID = '00000000-0000-0000-0000-000000000001'


def check_fastapi_endpoints(file_path: Path, content: str) -> List[str]:
    """Check that FastAPI endpoints include tenant_id parameter"""
    errors = []

    lines = content.split('\n')

    for i, line in enumerate(lines, 1):
        # Check if this is a route decorator
        is_route = any(re.search(pattern, line) for pattern in FASTAPI_ROUTE_PATTERNS)

        if is_route:
            # Look for the function definition in next few lines
            func_lines = []
            for j in range(i, min(i + 10, len(lines))):
                func_lines.append(lines[j])
                if 'def ' in lines[j]:
                    break

            func_block = '\n'.join(func_lines)

            # Check if tenant_id is in parameters
            if 'def ' in func_block and 'tenant_id' not in func_block:
                # Skip if it's a health check or root endpoint
                if any(skip in line for skip in ['/', '/health', '/metrics', '/docs']):
                    continue

                errors.append(
                    f"{file_path}:{i}: FastAPI endpoint missing tenant_id parameter\n"
                    f"  → {line.strip()}"
                )

    return errors


def check_hardcoded_tenant_ids(file_path: Path, content: str) -> List[str]:
    """Check for hardcoded tenant IDs (except default)"""
    errors = []

    # Pattern to match UUIDs
    uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'

    for i, line in enumerate(content.split('\n'), 1):
        # Skip comments
        if line.strip().startswith('#'):
            continue

        # Find UUIDs
        matches = re.finditer(uuid_pattern, line, re.IGNORECASE)
        for match in matches:
            uuid_val = match.group(0)

            # Skip if it's the default tenant ID or in a comment
            if uuid_val == DEFAULT_TENANT_ID:
                continue

            # Skip if it's in a string context (likely an example/test)
            if "'#'" in line or '"#"' in line:
                continue

            # Skip if in docstring or comment
            if '"""' in line or "'''" in line or '#' in line:
                continue

            errors.append(
                f"{file_path}:{i}: Hardcoded tenant ID detected: {uuid_val}\n"
                f"  → {line.strip()}\n"
                f"  Use parameter or environment variable instead"
            )

    return errors


def check_dag_tenant_context(file_path: Path, content: str) -> List[str]:
    """Check that DAG tasks set tenant context before queries"""
    errors = []

    # Look for SQLAlchemy operations without tenant context
    lines = content.split('\n')

    for i, line in enumerate(lines, 1):
        # Check for db operations
        if any(op in line for op in ['db.query(', 'db.execute(', 'session.query(']):
            # Look back 20 lines for SET tenant context
            context_start = max(0, i - 20)
            context_lines = '\n'.join(lines[context_start:i])

            if 'app.current_tenant_id' not in context_lines and 'tenant_id' not in context_lines:
                errors.append(
                    f"{file_path}:{i}: Database operation without tenant context\n"
                    f"  → {line.strip()}"
                )

    return errors


def check_sqlalchemy_models(file_path: Path, content: str) -> List[str]:
    """Check that SQLAlchemy models have tenant_id for tenant-scoped tables"""
    errors = []

    # Detect class definitions that extend Base
    class_pattern = r'class\s+(\w+)\(.*Base.*\):'
    matches = re.finditer(class_pattern, content, re.MULTILINE)

    for match in matches:
        class_name = match.group(1)
        class_start = match.start()

        # Extract class body (next 100 lines or until next class)
        lines = content[class_start:].split('\n')[:100]
        class_body = '\n'.join(lines)

        # Skip if this is Tenant table itself or a non-tenant-scoped table
        exempt_classes = ['Tenant', 'Base', 'AlembicVersion']
        if class_name in exempt_classes:
            continue

        # Check if tenant_id column exists
        if 'tenant_id' not in class_body:
            # Check if this is documented as a global table
            if 'global table' in class_body.lower() or 'not tenant-scoped' in class_body.lower():
                continue

            line_num = content[:class_start].count('\n') + 1
            errors.append(
                f"{file_path}:{line_num}: Model '{class_name}' missing tenant_id column\n"
                f"  All tenant-scoped models must include tenant_id"
            )

    return errors


def should_skip_file(file_path: str) -> bool:
    """Check if file should be skipped"""
    skip_patterns = [
        '/tests/',
        '/test_',
        '__pycache__',
        '.pyc',
        'check_tenant',
        'check_migrations',
        'lint_tenant',
    ]

    for pattern in skip_patterns:
        if pattern in file_path:
            return True

    return False


def main():
    """Main entry point"""
    project_root = Path(__file__).parent.parent.parent
    all_errors = []

    # Check API files
    api_dir = project_root / 'api'
    if api_dir.exists():
        for py_file in api_dir.rglob('*.py'):
            if should_skip_file(str(py_file)):
                continue

            content = py_file.read_text()

            # Check FastAPI endpoints
            errors = check_fastapi_endpoints(py_file, content)
            all_errors.extend(errors)

            # Check hardcoded IDs
            errors = check_hardcoded_tenant_ids(py_file, content)
            all_errors.extend(errors)

    # Check DAG files
    dags_dir = project_root / 'dags'
    if dags_dir.exists():
        for py_file in dags_dir.rglob('*.py'):
            if should_skip_file(str(py_file)):
                continue

            content = py_file.read_text()

            # Check tenant context
            errors = check_dag_tenant_context(py_file, content)
            all_errors.extend(errors)

            # Check hardcoded IDs
            errors = check_hardcoded_tenant_ids(py_file, content)
            all_errors.extend(errors)

    # Check model files
    db_dir = project_root / 'db'
    if db_dir.exists():
        for py_file in db_dir.rglob('*.py'):
            if should_skip_file(str(py_file)) or 'versions' in str(py_file):
                continue

            content = py_file.read_text()

            # Check models
            errors = check_sqlalchemy_models(py_file, content)
            all_errors.extend(errors)

    # Print results
    if all_errors:
        print("❌ Tenant Usage Lint Failed\n")
        print("The following tenant usage issues were found:\n")
        for error in all_errors:
            print(error)
            print()

        print("\n" + "=" * 80)
        print("BEST PRACTICES:")
        print("=" * 80)
        print()
        print("1. FastAPI endpoints should include tenant_id:")
        print("   @router.get('/properties/{id}')")
        print("   def get_property(id: str, tenant_id: UUID = Query(...)): ...")
        print()
        print("2. Set tenant context in DAGs:")
        print("   db.execute(f\"SET LOCAL app.current_tenant_id = '{tenant_id}'\")")
        print()
        print("3. Models should have tenant_id column:")
        print("   tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenant.id'))")
        print()
        print("4. Never hardcode tenant IDs - use parameters or env vars")
        print()

        sys.exit(1)
    else:
        print("✅ Tenant usage patterns look good")
        sys.exit(0)


if __name__ == '__main__':
    main()
