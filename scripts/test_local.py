#!/usr/bin/env python
"""
Script to run tests locally with the same configuration as GitHub Actions
"""
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description, fail_fast=False):
    """Run a command and report status"""
    print(f"\n{'=' * 80}")
    print(f"🔍 {description}")
    print(f"{'=' * 80}\n")
    
    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent)
        if result.returncode != 0 and fail_fast:
            print(f"\n❌ FAILED: {description}")
            return False
        return result.returncode == 0
    except FileNotFoundError:
        print(f"\n⚠️  Command not found")
        return False


def main():
    """Run all checks"""
    project_root = Path(__file__).parent
    
    all_passed = True
    
    # 1. Format checks
    print("\n" + "=" * 80)
    print("🚀 RUNNING LOCAL TEST SUITE")
    print("=" * 80)
    
    # Black check
    all_passed &= run_command(
        [sys.executable, "-m", "black", "--check", "--diff", "src", "tests"],
        "1️⃣  Format check with Black",
    )
    
    # isort check
    all_passed &= run_command(
        [sys.executable, "-m", "isort", "--check-only", "--diff", "src", "tests"],
        "2️⃣  Import sorting check with isort",
    )
    
    # flake8 - critical errors
    all_passed &= run_command(
        [sys.executable, "-m", "flake8", "src", "tests", 
         "--select=E9,F63,F7,F82", "--show-source"],
        "3️⃣  Critical errors check (flake8)",
        fail_fast=True,
    )
    
    # flake8 - all warnings
    run_command(
        [sys.executable, "-m", "flake8", "src", "tests",
         "--max-complexity=10", "--max-line-length=120", "--statistics"],
        "4️⃣  Full linting check (flake8)",
    )
    
    # 2. Unit tests
    all_passed &= run_command(
        [sys.executable, "-m", "pytest", "tests/",
         "-v", "--tb=short",
         "--cov=src", "--cov-report=html", "--cov-report=term-missing",
         "--cov-fail-under=80"],
        "5️⃣  Unit tests with coverage (pytest)",
    )
    
    # 3. Security checks
    run_command(
        [sys.executable, "-m", "bandit", "-r", "src", "-v"],
        "6️⃣  Security scan (bandit)",
    )
    
    # 4. Summary
    print("\n" + "=" * 80)
    if all_passed:
        print("✅ ALL CHECKS PASSED!")
        print("=" * 80)
        return 0
    else:
        print("❌ SOME CHECKS FAILED!")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
