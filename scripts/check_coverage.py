#!/usr/bin/env python3
"""
Check coverage per file and ensure core logic files meet 90% threshold.
This script runs after pytest to validate individual file coverage.
"""
import sys
import re
from pathlib import Path
from typing import Tuple, List, Dict

# Core logic files that must have >= 70% coverage
# Only checking: services (excluding orchestrator and claude_client), auth, database (connection/queries), tools, routes
CORE_FILES = {
    # Routes
    'src/api/routes/reasoning.py': 70,
    'src/api/routes/mcp.py': 70,
    'src/api/routes/metrics.py': 70,
    # Services (excluding orchestrator.py and claude_client.py)
    'src/services/mock_orchestrator.py': 70,
    'src/services/risk_analyzer.py': 70,
    'src/services/streaming.py': 70,
    # MCP Tools
    'src/mcp/tools.py': 70,
    # Database (connection and queries only)
    'src/database/queries.py': 70,
    'src/database/connection.py': 70,
    # Auth
    'src/auth/jwt_auth.py': 70,
    'src/auth/rbac.py': 70,
    'src/auth/permissions.py': 70,
    'src/auth/utils.py': 70,
}

# Files excluded from coverage (don't need to meet threshold)
EXCLUDED_FILES = {
    'src/api/main.py',
    'src/api/dependencies.py',
    'src/mcp/server.py',
    'src/database/seed.py',
}


def parse_coverage_report(coverage_output: str) -> dict:
    """Parse pytest coverage output and extract per-file coverage."""
    file_coverage = {}
    lines = coverage_output.split('\n')
    
    # Find the coverage table
    in_table = False
    for line in lines:
        # Skip header lines
        if 'Name' in line and 'Stmts' in line:
            in_table = True
            continue
        if in_table and line.strip().startswith('---'):
            continue
        if in_table and line.strip() == '':
            continue
        if in_table and line.strip().startswith('TOTAL'):
            break
        
        if in_table and line.strip():
            # Parse coverage line: "src/path/to/file.py    100    50   50.00%   10-60"
            # Or: "src/path/to/file.py    100     0 100.00%" (no missing column when 100%)
            parts = line.split()
            if len(parts) >= 4:
                file_path = parts[0]
                try:
                    # Coverage percentage is typically in the 4th column (index 3)
                    # But when 100%, format might be: "file.py    100     0 100.00%"
                    # Find the column with percentage sign
                    coverage_pct = None
                    for part in parts:
                        if '%' in part:
                            coverage_pct = float(part.rstrip('%'))
                            break
                    
                    if coverage_pct is not None:
                        file_coverage[file_path] = coverage_pct
                except (ValueError, IndexError):
                    continue
    
    return file_coverage


def check_file_coverage(coverage_output: str) -> Tuple[bool, List[Dict]]:
    """Check if all core files meet their coverage thresholds."""
    file_coverage = parse_coverage_report(coverage_output)
    failures = []
    
    for file_path, threshold in CORE_FILES.items():
        if file_path in file_coverage:
            coverage = file_coverage[file_path]
            if coverage < threshold:
                failures.append({
                    'file': file_path,
                    'coverage': coverage,
                    'threshold': threshold,
                    'missing': threshold - coverage
                })
        else:
            # File not found in coverage report (might be excluded or not tested)
            failures.append({
                'file': file_path,
                'coverage': 0,
                'threshold': threshold,
                'missing': threshold,
                'error': 'File not found in coverage report'
            })
    
    return len(failures) == 0, failures


def main():
    """Main function to check coverage."""
    # Read coverage output from stdin or file
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            coverage_output = f.read()
    else:
        coverage_output = sys.stdin.read()
    
    passed, failures = check_file_coverage(coverage_output)
    
    if failures:
        print("\n" + "=" * 80)
        print("❌ COVERAGE CHECK FAILED - Core logic files below 70% threshold")
        print("=" * 80)
        print(f"\nFound {len(failures)} file(s) below 70% coverage:\n")
        
        for failure in failures:
            print(f"  📄 {failure['file']}")
            print(f"     Current: {failure['coverage']:.2f}% | Required: {failure['threshold']}% | Missing: {failure['missing']:.2f}%")
            if 'error' in failure:
                print(f"     ⚠️  {failure['error']}")
            print()
        
        print("=" * 80)
        print("\n💡 To fix: Write tests for the missing lines shown in the coverage report.")
        print("   Run: make test  (to see detailed missing line numbers)\n")
        return 1
    else:
        print("\n" + "=" * 80)
        print("✅ COVERAGE CHECK PASSED - All core logic files meet 70% threshold")
        print("=" * 80 + "\n")
        return 0


if __name__ == '__main__':
    sys.exit(main())

