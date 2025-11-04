#!/usr/bin/env python3
"""
Coverage Validation Script

Validates test coverage meets minimum threshold
Generates detailed coverage report
"""
import sys
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple
import json
from datetime import datetime


class CoverageValidator:
    """Coverage validation and reporting"""

    def __init__(self, coverage_file: Path, threshold: float = 70.0):
        self.coverage_file = coverage_file
        self.threshold = threshold
        self.coverage_data = None

    def load_coverage(self) -> bool:
        """Load coverage XML file"""
        if not self.coverage_file.exists():
            print(f"❌ Coverage file not found: {self.coverage_file}")
            return False

        try:
            tree = ET.parse(self.coverage_file)
            self.coverage_data = tree.getroot()
            return True
        except ET.ParseError as e:
            print(f"❌ Error parsing coverage file: {e}")
            return False

    def get_total_coverage(self) -> float:
        """Get overall coverage percentage"""
        if self.coverage_data is None:
            return 0.0

        # Get coverage from XML
        lines_valid = int(self.coverage_data.attrib.get("lines-valid", 0))
        lines_covered = int(self.coverage_data.attrib.get("lines-covered", 0))

        if lines_valid == 0:
            return 0.0

        return (lines_covered / lines_valid) * 100

    def get_package_coverage(self) -> List[Dict]:
        """Get coverage per package/module"""
        if self.coverage_data is None:
            return []

        packages = []

        for package in self.coverage_data.findall(".//package"):
            name = package.attrib.get("name", "unknown")
            lines_valid = int(package.attrib.get("line-rate", 0) * 100)

            packages.append({
                "name": name,
                "coverage": round(lines_valid, 2)
            })

        return sorted(packages, key=lambda x: x["coverage"])

    def get_uncovered_files(self) -> List[Dict]:
        """Get files with low coverage"""
        if self.coverage_data is None:
            return []

        low_coverage_files = []

        for class_elem in self.coverage_data.findall(".//class"):
            filename = class_elem.attrib.get("filename", "")
            line_rate = float(class_elem.attrib.get("line-rate", 0))
            coverage = line_rate * 100

            if coverage < self.threshold:
                # Count uncovered lines
                uncovered_lines = []
                for line in class_elem.findall(".//line"):
                    hits = int(line.attrib.get("hits", 0))
                    if hits == 0:
                        uncovered_lines.append(int(line.attrib.get("number", 0)))

                low_coverage_files.append({
                    "file": filename,
                    "coverage": round(coverage, 2),
                    "uncovered_lines": len(uncovered_lines),
                    "sample_lines": uncovered_lines[:10]  # First 10 uncovered lines
                })

        return sorted(low_coverage_files, key=lambda x: x["coverage"])

    def validate(self) -> Tuple[bool, Dict]:
        """
        Validate coverage meets threshold

        Returns:
            (passed, report_dict)
        """
        if not self.load_coverage():
            return False, {"error": "Failed to load coverage file"}

        total_coverage = self.get_total_coverage()
        packages = self.get_package_coverage()
        uncovered = self.get_uncovered_files()

        report = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "coverage_file": str(self.coverage_file),
            "threshold": self.threshold,
            "total_coverage": round(total_coverage, 2),
            "passed": total_coverage >= self.threshold,
            "packages": packages,
            "low_coverage_files": uncovered[:20],  # Top 20 worst files
            "recommendations": self._generate_recommendations(total_coverage, uncovered)
        }

        return total_coverage >= self.threshold, report

    def _generate_recommendations(self, coverage: float, uncovered: List[Dict]) -> List[str]:
        """Generate recommendations for improving coverage"""
        recommendations = []

        if coverage < 50:
            recommendations.append(
                "🚨 CRITICAL: Coverage is below 50%. Prioritize writing tests for core functionality."
            )
        elif coverage < 70:
            recommendations.append(
                "⚠️  Coverage is below 70% threshold. Focus on testing business logic and API endpoints."
            )

        if uncovered:
            worst_file = uncovered[0]
            recommendations.append(
                f"📝 Start with: {worst_file['file']} ({worst_file['coverage']:.1f}% coverage)"
            )

        # Check for completely uncovered files
        zero_coverage = [f for f in uncovered if f['coverage'] == 0]
        if zero_coverage:
            recommendations.append(
                f"🎯 {len(zero_coverage)} files have 0% coverage. Add basic smoke tests for these files."
            )

        return recommendations

    def print_report(self, report: Dict):
        """Print human-readable coverage report"""
        print("\n" + "=" * 70)
        print("📊 COVERAGE VALIDATION REPORT")
        print("=" * 70)
        print()

        # Summary
        coverage = report["total_coverage"]
        threshold = report["threshold"]
        status = "✅ PASSED" if report["passed"] else "❌ FAILED"

        print(f"  Total Coverage:  {coverage:.2f}%")
        print(f"  Threshold:       {threshold:.2f}%")
        print(f"  Status:          {status}")
        print()

        # Package breakdown
        if report["packages"]:
            print("📦 Package Coverage:")
            print()
            for pkg in report["packages"][:10]:  # Top 10
                bar = self._make_progress_bar(pkg["coverage"], width=30)
                print(f"  {pkg['name']:<40} {bar} {pkg['coverage']:>6.2f}%")
            print()

        # Low coverage files
        if report["low_coverage_files"]:
            print(f"⚠️  Files Below {threshold:.0f}% Coverage:")
            print()
            for file_info in report["low_coverage_files"][:10]:  # Top 10 worst
                print(f"  {file_info['file']:<50} {file_info['coverage']:>6.2f}%")
                if file_info['sample_lines']:
                    lines = ', '.join(str(l) for l in file_info['sample_lines'][:5])
                    print(f"    Uncovered lines: {lines}...")
            print()

        # Recommendations
        if report["recommendations"]:
            print("💡 Recommendations:")
            print()
            for rec in report["recommendations"]:
                print(f"  {rec}")
            print()

        print("=" * 70)
        print()

    def _make_progress_bar(self, percentage: float, width: int = 30) -> str:
        """Create ASCII progress bar"""
        filled = int((percentage / 100) * width)
        empty = width - filled

        # Color based on percentage
        if percentage >= 80:
            color = "\033[92m"  # Green
        elif percentage >= 60:
            color = "\033[93m"  # Yellow
        else:
            color = "\033[91m"  # Red

        reset = "\033[0m"

        return f"{color}[{'█' * filled}{'░' * empty}]{reset}"

    def save_report(self, report: Dict, output_file: Path):
        """Save report to JSON file"""
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"📄 Report saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Validate test coverage meets minimum threshold"
    )
    parser.add_argument(
        "coverage_file",
        type=Path,
        help="Path to coverage.xml file"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=70.0,
        help="Minimum coverage threshold (default: 70%%)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output JSON report file"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print pass/fail, no detailed report"
    )

    args = parser.parse_args()

    # Validate coverage
    validator = CoverageValidator(args.coverage_file, args.threshold)
    passed, report = validator.validate()

    # Print report
    if not args.quiet:
        validator.print_report(report)

    # Save report if requested
    if args.output:
        validator.save_report(report, args.output)

    # Exit with appropriate code
    if passed:
        if not args.quiet:
            print(f"✅ Coverage validation PASSED: {report['total_coverage']:.2f}% >= {args.threshold:.2f}%\n")
        sys.exit(0)
    else:
        if not args.quiet:
            print(f"❌ Coverage validation FAILED: {report['total_coverage']:.2f}% < {args.threshold:.2f}%\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
