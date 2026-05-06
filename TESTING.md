# 🧪 Testing & CI/CD Guide

## Overview

This project follows best practices for code quality, testing, and continuous integration:

- ✅ **Automated Testing**: Pytest with >80% coverage
- ✅ **Code Quality**: PEP8 compliance with Black, isort, flake8
- ✅ **CI/CD Pipeline**: GitHub Actions on every push/PR
- ✅ **Pre-commit Hooks**: Automatic checks before commits
- ✅ **MLFlow Tracking**: Experiment tracking and model registry
- ✅ **Security Scanning**: Bandit for security issues

---

## 🧪 Local Testing

### Quick Start

```bash
# Setup development environment (one-time)
python scripts/setup_dev.py

# Run all checks (like GitHub Actions)
python scripts/test_local.py

# Or run individual tests
pytest tests/ -v
```

### Run Specific Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_features.py -v

# Run specific test function
pytest tests/test_features.py::TestRFM::test_rfm_calculation -v

# Run with markers
pytest tests/ -m "not slow" -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html --cov-report=term-missing
```

### Code Quality Checks

```bash
# Format code
black src tests
isort src tests

# Check formatting
black --check src tests
isort --check-only src tests

# Lint code
flake8 src tests --max-line-length=120

# Security check
bandit -r src/
```

---

## 📊 GitHub Actions Workflow

### Triggered On

- ✅ Push to `main` or `develop` branches
- ✅ Pull requests to `main` or `develop`
- ✅ Manual workflow dispatch

### Jobs

#### 1. **Code Quality** (`code-quality`)
- Runs: Black, isort, flake8, pylint
- Status: Must pass for tests to run
- Duration: ~2 minutes

```yaml
✓ Format check with Black
✓ Import sorting with isort
✓ Lint with flake8 (critical errors)
✓ Lint with flake8 (all)
✓ Lint with pylint
```

#### 2. **Unit Tests** (`test`)
- Runs: Python 3.9, 3.10, 3.11 (parallel)
- Tests: pytest with coverage >80%
- Artifacts: Coverage reports, test results
- Duration: ~5 minutes per Python version

```yaml
✓ Run tests with pytest
✓ Calculate coverage (must be >80%)
✓ Upload to Codecov
✓ Comment PR with coverage
```

#### 3. **Docker Build** (`docker-build`)
- Builds: Multi-stage Docker image
- Pushes: To GitHub Container Registry
- Only on: Push to main branch
- Duration: ~10 minutes

#### 4. **Security Scan** (`security`)
- Runs: Bandit (security), Safety (dependencies)
- Reports: Potential vulnerabilities
- Duration: ~2 minutes

---

## 🎯 Coverage Requirements

### Minimum Coverage: **80%**

Coverage report is generated and checked in each run:

```
src/data/preprocessing.py       120     12    90%    ✓
src/features/engineering.py     180     18    90%    ✓
src/clustering/models.py        250     25    90%    ✓
src/utils/config.py              45      3    93%    ✓
─────────────────────────────────────────────────────
TOTAL                            595     58    90%    ✓ PASS
```

### View Coverage Reports

```bash
# HTML report (local)
open htmlcov/index.html

# Or view in CI/CD
# GitHub → Actions → Latest Run → Artifacts
```

---

## 📋 PEP8 Compliance

### Standards Enforced

- **Line Length**: 120 characters (Black default)
- **Complexity**: Max 10 (flake8)
- **Import Sorting**: Black-compatible (isort)
- **Docstrings**: Required for public functions
- **Type Hints**: Recommended (checked by mypy)

### Configuration Files

- **Black**: `setup.cfg` [black]
- **isort**: `setup.cfg` [isort]
- **flake8**: `setup.cfg` [flake8]
- **pytest**: `pytest.ini`
- **pre-commit**: `.pre-commit-config.yaml`

### Auto-fix Code

```bash
# Auto-format with Black
black src tests

# Auto-sort imports with isort
isort src tests

# Then commit
git add .
git commit -m "style: auto-format code with black/isort"
```

---

## 🪝 Pre-commit Hooks

### Setup

```bash
# Install pre-commit
pip install pre-commit

# Install git hooks
pre-commit install

# Run on all files
pre-commit run --all-files
```

### What Gets Checked

✓ Trailing whitespace  
✓ End-of-file fixes  
✓ YAML syntax  
✓ Large file detection  
✓ JSON/TOML validation  
✓ Merge conflict detection  
✓ Black formatting  
✓ isort import sorting  
✓ flake8 linting  
✓ mypy type checking  
✓ Bandit security checks  

### Skip a Check

```bash
# Skip a specific check
SKIP=black git commit -m "quick fix"

# Or run without hooks
git commit --no-verify -m "urgent fix"
```

---

## 🚀 Pytest Configuration

### Test Discovery

- Files: `test_*.py` and `*_test.py`
- Classes: `Test*`
- Functions: `test_*`

### Markers

```bash
# Run unit tests only
pytest tests/ -m unit

# Skip slow tests
pytest tests/ -m "not slow"

# Run integration tests
pytest tests/ -m integration

# Run regression tests
pytest tests/ -m regression
```

### Fixtures

Located in `tests/conftest.py`:

```python
@pytest.fixture
def sample_raw_data():
    """Create sample raw data for testing"""
    ...

@pytest.fixture
def sample_engineered_features(sample_raw_data):
    """Create sample engineered features"""
    ...

@pytest.fixture
def sample_scaled_data(sample_engineered_features):
    """Create scaled feature data"""
    ...
```

---

## 📈 Codecov Integration

### View Coverage

- **Online**: [codecov.io](https://codecov.io) → GitHub → your repo
- **Badge**: In GitHub README
- **PR Comments**: Automatic coverage comparison

### Coverage Thresholds

```yaml
coverage:
  precision: 2
  round: down
  range: "70...100"
```

---

## 🔐 Security Scanning

### Tools

1. **Bandit**: Python security issues
2. **Safety**: Vulnerable dependencies

### Run Locally

```bash
# Security check
bandit -r src/

# Dependency check
safety check
```

### Common Issues

- ❌ Hardcoded credentials
- ❌ Use of unsafe functions (eval, exec)
- ❌ Vulnerable dependencies
- ❌ SQL injection risks

---

## 🐳 Docker in CI/CD

### Multi-stage Build

1. **Builder Stage**: Install dependencies
2. **Runtime Stage**: Minimal final image

### Image Tagging

```
ghcr.io/username/olist-segmentation:latest
ghcr.io/username/olist-segmentation:develop
ghcr.io/username/olist-segmentation:v1.0.0
```

### Test Docker Image

```bash
# Build locally
docker build -f docker/Dockerfile -t olist-segmentation:test .

# Test with pytest
docker run --rm olist-segmentation:test python -m pytest tests/
```

---

## 📊 MLFlow Tracking in CI/CD

### Automatic Logging

Pipeline automatically logs to MLFlow:

```python
mlflow.log_param("algorithm", "KMeans")
mlflow.log_metric("silhouette_score", 0.542)
mlflow.log_artifact("models/kmeans_k4.pkl")
```

### View Results

```bash
# Local MLFlow UI
mlflow ui --backend-store-uri file:./mlruns

# Access at http://localhost:5000
```

### Model Registry

```python
# Register model
mlflow.sklearn.log_model(
    model,
    artifact_path="model",
    registered_model_name="olist_clustering"
)

# Promote to Production
python scripts/register_model.py --action promote
```

---

## ✅ Pre-Deployment Checklist

- [ ] All tests passing locally: `pytest tests/ -v`
- [ ] Code formatted: `black src tests`
- [ ] Imports sorted: `isort src tests`
- [ ] No linting errors: `flake8 src tests`
- [ ] Coverage >80%: `pytest --cov=src --cov-fail-under=80`
- [ ] No security issues: `bandit -r src/`
- [ ] Docker builds: `docker build -f docker/Dockerfile .`
- [ ] Pre-commit hooks pass: `pre-commit run --all-files`
- [ ] Commit message is clear
- [ ] Push to feature branch, create PR

---

## 🔍 Troubleshooting

### Tests Fail Locally but Pass on CI

```bash
# Run with same Python version as CI
python3.10 -m pytest tests/

# Or use tox to test multiple versions
pip install tox
tox
```

### Coverage Below 80%

```bash
# Find uncovered lines
pytest --cov=src --cov-report=term-missing

# Generate HTML report
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

### Pre-commit Hooks Block Commit

```bash
# See what failed
pre-commit run --all-files

# Auto-fix with Black/isort
black src tests
isort src tests

# Then commit
git add .
git commit -m "style: auto-format code"
```

### Docker Build Fails

```bash
# Build without cache
docker build --no-cache -f docker/Dockerfile .

# Check Dockerfile syntax
docker run --rm -i hadolint/hadolint < docker/Dockerfile
```

---

## 📚 References

- [Pytest Documentation](https://docs.pytest.org/)
- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Black Code Formatter](https://black.readthedocs.io/)
- [isort Documentation](https://pycqa.github.io/isort/)
- [flake8 Documentation](https://flake8.pycqa.org/)
- [Bandit Security](https://bandit.readthedocs.io/)
- [Pre-commit Framework](https://pre-commit.com/)

---

**Last Updated**: May 5, 2026
