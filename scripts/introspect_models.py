#!/usr/bin/env python3
"""
Database Model Introspection Script

Reflects SQLAlchemy models to generate canonical models.json
Provides evidence of all 35+ database models claimed in audit.

Usage:
    python scripts/introspect_models.py > audit_artifacts/<ts>/models.json
"""
import json
import sys
from typing import Dict, Any, List
from collections import defaultdict


def get_column_info(column) -> Dict[str, Any]:
    """Extract column metadata"""
    return {
        'name': column.name,
        'type': str(column.type),
        'nullable': column.nullable,
        'primary_key': column.primary_key,
        'unique': column.unique,
        'default': str(column.default) if column.default else None,
        'foreign_key': str(column.foreign_keys) if column.foreign_keys else None
    }


def introspect_models() -> Dict[str, Any]:
    """
    Introspect SQLAlchemy models

    Returns:
        Dict with models, columns, relationships, and statistics
    """
    try:
        # Import SQLAlchemy Base
        from db.models import Base
        import sqlalchemy as sa

        models = []
        table_names = []
        total_columns = 0
        column_types = defaultdict(int)

        # Iterate through all mapped classes
        for mapper in sa.inspect(Base).registry.mappers:
            model_class = mapper.class_
            table = mapper.mapped_table

            # Get columns
            columns = []
            for column in table.columns:
                col_info = get_column_info(column)
                columns.append(col_info)
                total_columns += 1
                column_types[col_info['type']] += 1

            # Get relationships
            relationships = []
            for rel in mapper.relationships:
                relationships.append({
                    'name': rel.key,
                    'target': rel.target.name if hasattr(rel.target, 'name') else str(rel.target),
                    'uselist': rel.uselist,
                    'back_populates': rel.back_populates
                })

            model_info = {
                'name': model_class.__name__,
                'table_name': table.name,
                'module': model_class.__module__,
                'columns': columns,
                'relationships': relationships,
                'column_count': len(columns),
                'has_primary_key': any(col['primary_key'] for col in columns),
                'has_foreign_keys': any(col['foreign_key'] for col in columns)
            }

            models.append(model_info)
            table_names.append(table.name)

        # Sort models by name
        models.sort(key=lambda x: x['name'])

        result = {
            'metadata': {
                'generated_at': __import__('datetime').datetime.utcnow().isoformat(),
                'source': 'db.models.Base',
                'introspection_method': 'SQLAlchemy mapper reflection'
            },
            'statistics': {
                'total_models': len(models),
                'total_tables': len(table_names),
                'total_columns': total_columns,
                'avg_columns_per_model': round(total_columns / len(models), 1) if models else 0,
                'models_with_relationships': sum(1 for m in models if m['relationships']),
                'column_types': dict(column_types)
            },
            'models': models,
            'table_names': sorted(table_names)
        }

        return result

    except Exception as e:
        return {
            'error': str(e),
            'traceback': __import__('traceback').format_exc()
        }


def main():
    """Main entry point"""
    result = introspect_models()

    # Pretty print JSON to stdout
    print(json.dumps(result, indent=2, sort_keys=False))

    # Print summary to stderr for logging
    if 'error' not in result:
        stats = result['statistics']
        print(f"\n✅ Model Introspection Complete", file=sys.stderr)
        print(f"   Total Models: {stats['total_models']}", file=sys.stderr)
        print(f"   Total Tables: {stats['total_tables']}", file=sys.stderr)
        print(f"   Total Columns: {stats['total_columns']}", file=sys.stderr)
        print(f"   Avg Columns/Model: {stats['avg_columns_per_model']}", file=sys.stderr)
        print(f"   Models with Relationships: {stats['models_with_relationships']}", file=sys.stderr)
    else:
        print(f"\n❌ Model Introspection Failed", file=sys.stderr)
        print(f"   Error: {result['error']}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
