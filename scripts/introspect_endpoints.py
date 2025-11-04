#!/usr/bin/env python3
"""
Endpoint Introspection Script

Introspects FastAPI app routes to generate canonical endpoints.json
Provides evidence of all 118 API endpoints claimed in audit.

Usage:
    python scripts/introspect_endpoints.py > audit_artifacts/<ts>/endpoints.json
"""
import json
import sys
from typing import List, Dict, Any
from collections import defaultdict


def introspect_endpoints() -> Dict[str, Any]:
    """
    Introspect FastAPI application routes

    Returns:
        Dict with endpoints, grouped by router, with HTTP methods and paths
    """
    try:
        # Import FastAPI app
        from api.main import app

        endpoints = []
        routers = defaultdict(list)
        method_counts = defaultdict(int)

        # Iterate through all routes
        for route in app.routes:
            if hasattr(route, 'methods') and hasattr(route, 'path'):
                methods = list(route.methods)
                path = route.path
                name = getattr(route, 'name', 'unknown')

                # Extract router from path
                router = path.split('/')[1] if len(path.split('/')) > 1 else 'root'

                endpoint_info = {
                    'path': path,
                    'methods': sorted(methods),
                    'name': name,
                    'router': router
                }

                endpoints.append(endpoint_info)
                routers[router].append(endpoint_info)

                for method in methods:
                    if method != 'HEAD' and method != 'OPTIONS':  # Skip automatic methods
                        method_counts[method] += 1

        # Sort endpoints by path
        endpoints.sort(key=lambda x: x['path'])

        # Calculate statistics
        total_endpoints = sum(method_counts.values())
        unique_paths = len(set(ep['path'] for ep in endpoints))

        result = {
            'metadata': {
                'generated_at': __import__('datetime').datetime.utcnow().isoformat(),
                'source': 'api.main.app',
                'introspection_method': 'FastAPI route reflection'
            },
            'statistics': {
                'total_endpoints': total_endpoints,
                'unique_paths': unique_paths,
                'routers': len(routers),
                'by_method': dict(method_counts)
            },
            'endpoints': endpoints,
            'by_router': {
                router: {
                    'count': len(eps),
                    'endpoints': eps
                }
                for router, eps in sorted(routers.items())
            }
        }

        return result

    except Exception as e:
        return {
            'error': str(e),
            'traceback': __import__('traceback').format_exc()
        }


def main():
    """Main entry point"""
    result = introspect_endpoints()

    # Pretty print JSON to stdout
    print(json.dumps(result, indent=2, sort_keys=False))

    # Print summary to stderr for logging
    if 'error' not in result:
        stats = result['statistics']
        print(f"\n✅ Endpoint Introspection Complete", file=sys.stderr)
        print(f"   Total Endpoints: {stats['total_endpoints']}", file=sys.stderr)
        print(f"   Unique Paths: {stats['unique_paths']}", file=sys.stderr)
        print(f"   Routers: {stats['routers']}", file=sys.stderr)
        print(f"   By Method: {stats['by_method']}", file=sys.stderr)
    else:
        print(f"\n❌ Endpoint Introspection Failed", file=sys.stderr)
        print(f"   Error: {result['error']}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
