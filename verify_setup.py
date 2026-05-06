#!/usr/bin/env python
"""
Simple verification script to ensure everything is set up correctly
"""

import os
import sys
from pathlib import Path

def check_python_env():
    """Check Python environment"""
    print("\n📍 Python Environment Check")
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  Executable: {sys.executable}")
    return True

def check_required_files():
    """Check if required files exist"""
    print("\n📍 Required Files Check")
    
    required = {
        "scripts/full_pipeline.py": "Pipeline script",
        "scripts/api.py": "API script",
        "scripts/start_api.py": "API starter script",
        "notebooks/models/final_pipeline.pkl": "Trained model",
        "notebooks/reports/clustering_comparison.csv": "Results",
        "requirements.txt": "Dependencies"
    }
    
    all_exist = True
    for path, description in required.items():
        exists = Path(path).exists()
        status = "✅" if exists else "⚠️"
        print(f"  {status} {path} ({description})")
        all_exist = all_exist and exists
    
    return all_exist

def check_dependencies():
    """Check if required packages are installed"""
    print("\n📍 Dependencies Check")
    
    packages = [
        ("pandas", "Data processing"),
        ("sklearn", "Machine learning"),
        ("fastapi", "API framework"),
        ("uvicorn", "ASGI server"),
        ("pydantic", "Data validation"),
        ("requests", "HTTP client"),
    ]
    
    all_installed = True
    for package, description in packages:
        try:
            __import__(package)
            print(f"  ✅ {package} ({description})")
        except ImportError:
            print(f"  ❌ {package} ({description}) - NOT INSTALLED")
            all_installed = False
    
    return all_installed

def check_pipeline_outputs():
    """Check if pipeline has been run"""
    print("\n📍 Pipeline Outputs Check")
    
    outputs = {
        "notebooks/models/final_pipeline.pkl": "Pipeline model",
        "notebooks/reports/clustering_comparison.csv": "Comparison metrics",
        "notebooks/reports/cluster_profiles_mean.csv": "Mean profiles",
        "notebooks/reports/cluster_profiles_median.csv": "Median profiles",
        "notebooks/reports/segmentation_finale_olist.csv": "Final results",
    }
    
    all_exist = True
    for path, description in outputs.items():
        exists = Path(path).exists()
        status = "✅" if exists else "❌"
        size = f"({Path(path).stat().st_size / 1024 / 1024:.1f}MB)" if exists else ""
        print(f"  {status} {description}: {path} {size}")
        all_exist = all_exist and exists
    
    if not all_exist:
        print("\n  💡 Run: python scripts/full_pipeline.py")
    
    return all_exist

def main():
    print("=" * 70)
    print("🔍 SYSTEM VERIFICATION")
    print("=" * 70)
    
    results = {
        "Python": check_python_env(),
        "Files": check_required_files(),
        "Dependencies": check_dependencies(),
        "Pipeline": check_pipeline_outputs(),
    }
    
    print("\n" + "=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    
    for check, passed in results.items():
        status = "✅" if passed else "⚠️"
        print(f"{status} {check}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n✨ Everything is ready!")
        print("\n🚀 Next steps:")
        print("  1. python scripts/start_api.py   (in terminal 1)")
        print("  2. python scripts/test_suite.py  (in terminal 2)")
        print("  3. Open http://127.0.0.1:8000/docs in browser")
    else:
        print("\n⚠️  Some checks failed. See above for details.")
        
        if not results.get("Pipeline"):
            print("\n   Missing pipeline outputs:")
            print("   → Run: python scripts/full_pipeline.py")
        
        if not results.get("Dependencies"):
            print("\n   Missing dependencies:")
            print("   → Run: pip install -r requirements.txt")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
