#!/usr/bin/env python3
"""
Validate Test Coverage Report

Parses coverage.xml and generates a detailed coverage report with validation.

Usage:
    python scripts/validate_coverage.py <coverage.xml> [--threshold 70] [--output coverage_report.json]

Exit Codes:
    0: Coverage meets threshold
    1: Coverage below threshold
    2: Error parsing coverage file
"""

import sys
import argparse
import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import xml.etree.ElementTree as ET


def parse_coverage_xml(coverage_file: Path) -> Dict[str, Any]:
    """
    Parse coverage.xml and extract coverage statistics

    Returns:
        dict with coverage statistics
    """
    try:
        tree = ET.parse(coverage_file)
        root = tree.getroot()
    except Exception as e:
        print(f"Error parsing coverage file: {e}", file=sys.stderr)
        sys.exit(2)

    # Extract overall coverage
    line_rate = float(root.attrib.get('line-rate', 0))
    branch_rate = float(root.attrib.get('branch-rate', 0))
    lines_covered = int(root.attrib.get('lines-covered', 0))
    lines_valid = int(root.attrib.get('lines-valid', 0))
    branches_covered = int(root.attrib.get('branches-covered', 0))
    branches_valid = int(root.attrib.get('branches-valid', 0))

    # Extract per-package coverage
    packages = []
    for package in root.findall('.//package'):
        package_name = package.attrib.get('name', 'unknown')
        package_line_rate = float(package.attrib.get('line-rate', 0))
        package_branch_rate = float(package.attrib.get('branch-rate', 0))

        # Extract classes in package
        classes = []
        for cls in package.findall('.//class'):
            class_name = cls.attrib.get('name', 'unknown')
            class_filename = cls.attrib.get('filename', 'unknown')
            class_line_rate = float(cls.attrib.get('line-rate', 0))
            class_branch_rate = float(cls.attrib.get('branch-rate', 0))

            classes.append({
                'name': class_name,
                'filename': class_filename,
                'line_coverage': class_line_rate * 100,
                'branch_coverage': class_branch_rate * 100
            })

        packages.append({
            'name': package_name,
            'line_coverage': package_line_rate * 100,
            'branch_coverage': package_branch_rate * 100,
            'classes': classes
        })

    return {
        'overall': {
            'line_coverage': line_rate * 100,
            'branch_coverage': branch_rate * 100,
            'lines_covered': lines_covered,
            'lines_valid': lines_valid,
            'branches_covered': branches_covered,
            'branches_valid': branches_valid
        },
        'packages': packages
    }


def validate_coverage(coverage_data: Dict[str, Any], threshold: float) -> Dict[str, Any]:
    """
    Validate coverage against threshold

    Returns:
        dict with validation results
    """
    line_coverage = coverage_data['overall']['line_coverage']
    branch_coverage = coverage_data['overall']['branch_coverage']

    passed = line_coverage >= threshold

    # Find low-coverage files
    low_coverage_files = []
    for package in coverage_data['packages']:
        for cls in package['classes']:
            if cls['line_coverage'] < threshold:
                low_coverage_files.append({
                    'file': cls['filename'],
                    'coverage': cls['line_coverage']
                })

    # Sort by coverage (lowest first)
    low_coverage_files.sort(key=lambda x: x['coverage'])

    return {
        'passed': passed,
        'threshold': threshold,
        'line_coverage': line_coverage,
        'branch_coverage': branch_coverage,
        'gap': threshold - line_coverage if not passed else 0,
        'low_coverage_files': low_coverage_files[:10]  # Top 10 worst files
    }


def generate_report(
    coverage_data: Dict[str, Any],
    validation_result: Dict[str, Any],
    output_file: Path = None
) -> None:
    """
    Generate coverage report
    """
    report = {
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'source': str(output_file) if output_file else 'coverage.xml',
        'overall': coverage_data['overall'],
        'validation': validation_result,
        'packages': coverage_data['packages']
    }

    if output_file:
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"✓ Coverage report written to {output_file}")

    # Print summary
    print("\n" + "=" * 80)
    print("  Coverage Report Summary")
    print("=" * 80 + "\n")

    print(f"Overall Coverage:")
    print(f"  Line Coverage:   {coverage_data['overall']['line_coverage']:.1f}%")
    print(f"  Branch Coverage: {coverage_data['overall']['branch_coverage']:.1f}%")
    print(f"  Lines Covered:   {coverage_data['overall']['lines_covered']} / {coverage_data['overall']['lines_valid']}")
    print(f"  Branches Covered: {coverage_data['overall']['branches_covered']} / {coverage_data['overall']['branches_valid']}")
    print()

    print(f"Validation:")
    print(f"  Threshold: {validation_result['threshold']}%")

    if validation_result['passed']:
        print(f"  Status:    ✓ PASSED")
        print(f"  Margin:    +{validation_result['line_coverage'] - validation_result['threshold']:.1f}%")
    else:
        print(f"  Status:    ✗ FAILED")
        print(f"  Gap:       -{validation_result['gap']:.1f}%")

    print()

    if validation_result['low_coverage_files']:
        print("Files Below Threshold (Top 10):")
        for i, file_info in enumerate(validation_result['low_coverage_files'], 1):
            print(f"  {i:2d}. {file_info['file']:<60s} {file_info['coverage']:5.1f}%")
        print()

    print("Package Coverage:")
    for package in coverage_data['packages']:
        print(f"  {package['name']:<40s} {package['line_coverage']:5.1f}%")

    print()
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description='Validate test coverage report',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        'coverage_file',
        type=Path,
        help='Path to coverage.xml file'
    )

    parser.add_argument(
        '--threshold',
        type=float,
        default=70.0,
        help='Coverage threshold percentage (default: 70.0)'
    )

    parser.add_argument(
        '--output',
        type=Path,
        help='Output file for JSON report (optional)'
    )

    args = parser.parse_args()

    # Check if coverage file exists
    if not args.coverage_file.exists():
        print(f"Error: Coverage file not found: {args.coverage_file}", file=sys.stderr)
        sys.exit(2)

    # Parse coverage
    print(f"Parsing coverage file: {args.coverage_file}")
    coverage_data = parse_coverage_xml(args.coverage_file)

    # Validate coverage
    validation_result = validate_coverage(coverage_data, args.threshold)

    # Generate report
    generate_report(coverage_data, validation_result, args.output)

    # Exit with appropriate code
    if validation_result['passed']:
        print("\n✅ Coverage validation passed!")
        sys.exit(0)
    else:
        print("\n❌ Coverage validation failed!")
        print(f"   Coverage is {validation_result['gap']:.1f}% below threshold")
        print(f"   Need to improve coverage from {validation_result['line_coverage']:.1f}% to {validation_result['threshold']:.1f}%")
        sys.exit(1)


if __name__ == '__main__':
    main()
