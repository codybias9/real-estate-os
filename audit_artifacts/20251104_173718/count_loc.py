#!/usr/bin/env python3
"""Count lines of code by language"""
import os
import json
from pathlib import Path
from collections import defaultdict

exclude_dirs = {'node_modules', '.next', 'htmlcov', '__pycache__', '.pytest_cache', '.git', 'venv', 'dist', 'build', '.mypy_cache'}
exclude_files = {'.pyc', '.pyo', '.so', '.dylib'}

language_map = {
    '.py': 'Python',
    '.ts': 'TypeScript',
    '.tsx': 'TypeScript',
    '.js': 'JavaScript',
    '.jsx': 'JavaScript',
    '.md': 'Markdown',
    '.json': 'JSON',
    '.yml': 'YAML',
    '.yaml': 'YAML',
    '.sh': 'Shell',
    '.sql': 'SQL',
    '.css': 'CSS',
    '.html': 'HTML',
    '.txt': 'Text',
}

def count_lines(file_path):
    """Count lines in a file"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            total = len(lines)
            blank = sum(1 for line in lines if line.strip() == '')
            comment = 0
            # Simple comment detection
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('#') or stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('*'):
                    comment += 1
            code = total - blank - comment
            return {'total': total, 'blank': blank, 'comment': comment, 'code': code}
    except:
        return {'total': 0, 'blank': 0, 'comment': 0, 'code': 0}

def main():
    root = Path('.')
    stats = defaultdict(lambda: {'files': 0, 'total': 0, 'blank': 0, 'comment': 0, 'code': 0})
    
    for file_path in root.rglob('*'):
        if not file_path.is_file():
            continue
        
        # Check if in excluded directory
        if any(exc in file_path.parts for exc in exclude_dirs):
            continue
        
        # Check extension
        ext = file_path.suffix
        if ext not in language_map:
            continue
        
        lang = language_map[ext]
        counts = count_lines(file_path)
        
        stats[lang]['files'] += 1
        stats[lang]['total'] += counts['total']
        stats[lang]['blank'] += counts['blank']
        stats[lang]['comment'] += counts['comment']
        stats[lang]['code'] += counts['code']
    
    # Calculate totals
    totals = {'files': 0, 'total': 0, 'blank': 0, 'comment': 0, 'code': 0}
    for lang_stats in stats.values():
        totals['files'] += lang_stats['files']
        totals['total'] += lang_stats['total']
        totals['blank'] += lang_stats['blank']
        totals['comment'] += lang_stats['comment']
        totals['code'] += lang_stats['code']
    
    result = {
        'by_language': dict(stats),
        'totals': totals
    }
    
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
