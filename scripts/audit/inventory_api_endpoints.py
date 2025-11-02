#!/usr/bin/env python3
"""
Inventory all API endpoints from router files.
"""
import re
import sys
from pathlib import Path

def extract_endpoints(file_path):
    """Extract endpoint definitions from a router file."""
    endpoints = []

    with open(file_path, 'r') as f:
        content = f.read()

    # Find all @router.METHOD patterns followed by async def or def
    pattern = r'@router\.(get|post|put|delete|patch)\((.*?)\).*?(?:async )?def\s+(\w+)'
    matches = re.findall(pattern, content, re.DOTALL)

    for method, params, func_name in matches:
        # Extract path from params
        path_match = re.search(r'["\']([^"\']+)["\']', params)
        path = path_match.group(1) if path_match else "unknown"

        endpoints.append({
            'file': file_path.name,
            'method': method.upper(),
            'path': path,
            'function': func_name
        })

    return endpoints

def main():
    router_dir = Path('api/routers')

    if not router_dir.exists():
        print("Error: api/routers directory not found", file=sys.stderr)
        sys.exit(1)

    all_endpoints = []

    for py_file in sorted(router_dir.glob('*.py')):
        if py_file.name.startswith('__'):
            continue

        endpoints = extract_endpoints(py_file)
        all_endpoints.extend(endpoints)

    # Output as CSV
    print("Router,Method,Path,Function")
    for ep in all_endpoints:
        print(f"{ep['file']},{ep['method']},{ep['path']},{ep['function']}")

    print(f"\n# Total endpoints: {len(all_endpoints)}", file=sys.stderr)

if __name__ == '__main__':
    main()
