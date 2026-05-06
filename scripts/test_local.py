#!/usr/bin/env python
"""
Script to run tests locally with the same configuration as GitHub Actions
"""
import subprocess
import sys
from pathlib import Path

# Set UTF-8 encoding for output
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'


def run_command(cmd, description, fail_fast=False, cwd=None):
    """Run a command and report status"""
    print(f"\n{'=' * 80}")
    print(f"[CHECK] {description}")
    print(f"{'=' * 80}\n")
    
    try:
        result = subprocess.run(cmd, cwd=cwd)
        if result.returncode != 0 and fail_fast:
            print(f"\n[FAILED] {description}")
            return False
        return result.returncode == 0
    except FileNotFoundError:
        print(f"\n[WARNING] Command not found")
        return False


def main():
    """Run all checks"""
    project_root = Path(__file__).parent.parent
    
    all_passed = True
    
    # 1. Format checks
    print("\n" + "=" * 80)
    print("[START] RUNNING LOCAL TEST SUITE")
    print("=" * 80)
    
    # Black check
    all_passed &= run_command(
        [sys.executable, "-m", "black", "--check", "--diff", "src", "tests"],
        "1. Format check with Black",
        cwd=project_root,
    )
    
    # isort check
    all_passed &= run_command(
        [sys.executable, "-m", "isort", "--check-only", "--diff", "src", "tests"],
        "2. Import sorting check with isort",
        cwd=project_root,
    )
    
    # flake8 - critical errors
    all_passed &= run_command(
        [sys.executable, "-m", "flake8", "src", "tests", 
         "--select=E9,F63,F7,F82", "--show-source"],
        "3. Critical errors check (flake8)",
        fail_fast=True,
        cwd=project_root,
    )
    
    # flake8 - all warnings
    run_command(
        [sys.executable, "-m", "flake8", "src", "tests",
         "--max-complexity=10", "--max-line-length=120", "--statistics"],
        "4. Full linting check (flake8)",
        cwd=project_root,
    )
    
    # 2. Unit tests
    all_passed &= run_command(
        [sys.executable, "-m", "pytest", "tests/",
         "-v", "--tb=short",
         "--cov=src", "--cov-report=html", "--cov-report=term-missing",
         "--cov-fail-under=80"],
        "5. Unit tests with coverage (pytest)",
        cwd=project_root,
    )
    
    # 3. Security checks
    run_command(
        [sys.executable, "-m", "bandit", "-r", "src", "-v"],
        "6. Security scan (bandit)",
        cwd=project_root,
    )
    
    # 4. Summary
    print("\n" + "=" * 80)
    if all_passed:
        print("[PASS] ALL CHECKS PASSED!")
        print("=" * 80)
        return 0
    else:
        print("[FAIL] SOME CHECKS FAILED!")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
