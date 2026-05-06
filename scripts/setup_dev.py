#!/usr/bin/env python
"""
Setup script for development environment
"""
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command"""
    print(f"\n📋 {description}...")
    try:
        result = subprocess.run(cmd, check=True)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"⚠️  {description} failed: {e}")
        return False


def setup_dev_environment():
    """Setup development environment"""
    print("\n" + "=" * 80)
    print("🔧 SETTING UP DEVELOPMENT ENVIRONMENT")
    print("=" * 80)
    
    project_root = Path(__file__).parent.parent
    
    # 1. Install dependencies
    run_command(
        [sys.executable, "-m", "pip", "install", "-r", str(project_root / "requirements.txt")],
        "Installing project dependencies"
    )
    
    # 2. Install dev dependencies
    dev_deps = [
        "black",
        "isort",
        "flake8",
        "flake8-docstrings",
        "flake8-bugbear",
        "mypy",
        "bandit",
        "pytest",
        "pytest-cov",
        "pytest-xdist",
        "pytest-mock",
        "pre-commit",
    ]
    
    run_command(
        [sys.executable, "-m", "pip", "install"] + dev_deps,
        "Installing development dependencies"
    )
    
    # 3. Setup pre-commit hooks
    print("\n" + "=" * 80)
    print("🪝 SETTING UP PRE-COMMIT HOOKS")
    print("=" * 80)
    
    run_command(
        ["pre-commit", "install"],
        "Installing pre-commit hooks"
    )
    
    run_command(
        ["pre-commit", "run", "--all-files"],
        "Running pre-commit hooks on all files"
    )
    
    # 4. Create necessary directories
    print("\n📁 Creating necessary directories...")
    directories = [
        project_root / "logs",
        project_root / "models",
        project_root / "reports",
        project_root / "data" / "output",
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"✅ Created {directory}")
    
    print("\n" + "=" * 80)
    print("✅ DEVELOPMENT ENVIRONMENT SETUP COMPLETE!")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Run tests: python -m pytest tests/ -v")
    print("2. Run pipeline: python scripts/run_pipeline.py")
    print("3. View MLFlow: python project.py mlflow")
    print("4. View Dashboard: streamlit run notebooks/dashboard.py")


if __name__ == "__main__":
    setup_dev_environment()
