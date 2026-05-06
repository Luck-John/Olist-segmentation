# 🔧 Troubleshooting & FAQ

## Common Issues & Solutions

### 🔴 Tests Fail Locally

#### Issue: Import errors when running tests
```
ModuleNotFoundError: No module named 'src'
```

**Solution:**
```bash
# Make sure you're in project root
cd /path/to/Projet_2026

# Reinstall dependencies
python -m pip install -r requirements.txt

# Run tests with correct path
pytest tests/ -v
```

#### Issue: Coverage below 80%
```
FAILED - coverage: 75% - failed lower bound (0%)
```

**Solution:**
```bash
# Check which parts aren't covered
pytest tests/ --cov=src --cov-report=term-missing

# Generate HTML report
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html

# Write more tests to cover missing lines
```

#### Issue: Fixture errors
```
ERROR fixture 'sample_raw_data' not found
```

**Solution:**
```bash
# Make sure conftest.py exists in tests/
ls tests/conftest.py

# Check conftest.py is valid Python
python -m py_compile tests/conftest.py

# Clear pytest cache
rm -rf .pytest_cache
pytest tests/ -v
```

---

### 🔴 Code Quality Failures

#### Issue: Black formatting errors
```
FAILED - 2 files would be reformatted
```

**Solution:**
```bash
# Auto-format with Black
black src tests

# Or use project script
python project.py format

# Verify formatting
black --check src tests
```

#### Issue: isort import errors
```
FAILED - 5 files would be reformatted
```

**Solution:**
```bash
# Auto-sort imports
isort src tests

# Or use project script
python project.py format

# Verify
isort --check-only src tests
```

#### Issue: flake8 linting errors
```
src/features/engineering.py:45:1: E501 line too long (125 > 120 characters)
```

**Solution:**
```bash
# View all linting errors
flake8 src tests

# Fix line length issues
# Edit files manually to stay under 120 characters
# Or use Black to auto-format
black src tests

# Verify
flake8 src tests
```

#### Issue: Complexity too high
```
src/clustering/models.py:120:1: C901 function is too complex (15)
```

**Solution:**
```bash
# Refactor function to be simpler
# Split into smaller functions
# Use helper methods

# Example: Instead of one long function
# Break it into: validate_input() → process() → finalize()

# Verify
flake8 src tests --max-complexity=10
```

---

### 🔴 Pre-commit Hooks Issues

#### Issue: Hooks block commit
```
FAILED - Black would reformat this file
```

**Solution:**
```bash
# Auto-fix automatically
python project.py format

# Or manually
black src tests
isort src tests

# Try commit again
git add .
git commit -m "style: auto-format code"
```

#### Issue: Mypy type checking fails
```
error: Need type annotation for "variable"
```

**Solution:**
```bash
# Add type hints
# Before:
config = load_config()

# After:
from typing import Dict, Any
config: Dict[str, Any] = load_config()

# Or skip type check for this file
# Add to setup.cfg: [mypy]
#                   ignore_errors = True

# Skip for one commit
SKIP=mypy git commit -m "feat: add new feature"
```

#### Issue: Bandit security warning
```
>> Issue: [B101:assert_used] Use of "assert" detected
```

**Solution:**
```bash
# Replace assert with proper validation
# Before:
assert len(data) > 0

# After:
if len(data) == 0:
    raise ValueError("Data is empty")

# Or skip for specific lines
data.append(item)  # nosec
```

---

### 🔴 GitHub Actions Failures

#### Issue: Workflow doesn't run after push
```
No workflows were triggered
```

**Solution:**
```bash
# Check workflow file exists
ls .github/workflows/ci.yml

# Verify workflow syntax
cat .github/workflows/ci.yml

# View Actions tab on GitHub
# GitHub → Actions → You should see your workflow

# If still not working:
# 1. Verify file is in correct location: .github/workflows/ci.yml
# 2. Verify file has valid YAML syntax
# 3. Check branch protection rules aren't blocking
```

#### Issue: Coverage check fails on GitHub
```
FAILED - Coverage percentage (75%) below threshold (80%)
```

**Solution:**
```bash
# Increase coverage locally first
python project.py test-local

# View coverage report
open htmlcov/index.html

# Write more tests
# Add tests to tests/test_*.py

# Verify locally
pytest tests/ --cov=src --cov-fail-under=80

# Push to GitHub
git push origin main
```

#### Issue: Python version incompatibility
```
ERROR - py39: command not found
```

**Solution:**
```bash
# GitHub Actions tests on 3.9, 3.10, 3.11
# Make sure code works on all versions

# Test locally with specific version
python3.10 -m pytest tests/

# Or install tox
pip install tox
tox

# Fix compatibility issues
# Example: Use Union instead of | for type hints (< 3.10)
# Before:
def foo(x: int | str) -> None:

# After:
from typing import Union
def foo(x: Union[int, str]) -> None:
```

---

### 🔴 Pipeline Execution Failures

#### Issue: Data file not found
```
FileNotFoundError: data/base_final.csv not found
```

**Solution:**
```bash
# Check data files exist
ls data/

# Update config to correct path
# Edit config/config.yaml:
# data_path: "data/base_final.csv"

# Or check if using different data file name
# base_final.csv vs Base.csv
```

#### Issue: Memory error during feature engineering
```
MemoryError: Unable to allocate memory
```

**Solution:**
```bash
# Use smaller dataset for testing
# In config/config.yaml:
# sample_fraction: 0.1  # Use 10% of data

# Or increase available memory:
# Use machine with more RAM
# Or run in Docker which has more resources
```

#### Issue: Clustering fails
```
ValueError: n_clusters must be less than n_samples
```

**Solution:**
```bash
# Too few samples for clustering
# Check data preprocessing
python -m pytest tests/test_data.py -v

# Or:
# 1. Use smaller k value
# 2. Use more data
# 3. Check preprocessing isn't removing too many rows
```

---

### 🔴 MLFlow Issues

#### Issue: MLFlow directory not found
```
FileNotFoundError: [Errno 2] No such file or directory: 'mlruns'
```

**Solution:**
```bash
# Create mlruns directory
mkdir -p mlruns

# Or run pipeline which creates it
python project.py pipeline
```

#### Issue: Can't access MLFlow UI
```
Error: Cannot connect to http://localhost:5000
```

**Solution:**
```bash
# Start MLFlow server
python project.py mlflow

# Or specify port
mlflow server --host 0.0.0.0 --port 5000

# Check if port is in use
# Windows:
netstat -ano | findstr :5000

# Kill process and retry
# Or use different port:
mlflow server --host 0.0.0.0 --port 5001
```

#### Issue: Model registry not showing models
```
No models in registry
```

**Solution:**
```bash
# Run pipeline first to generate runs
python project.py pipeline

# Then promote best model
python scripts/register_model.py --action promote

# Verify
python scripts/register_model.py --action list
```

---

### 🔴 Docker Issues

#### Issue: Docker image build fails
```
ERROR: failed to solve with frontend dockerfile.v0
```

**Solution:**
```bash
# Check Dockerfile syntax
cat docker/Dockerfile

# Verify base image exists
docker pull python:3.10-slim

# Build with verbose output
docker build -f docker/Dockerfile -t olist-segmentation:test --progress=plain .

# Common issues:
# 1. Typo in Dockerfile
# 2. Base image not available
# 3. File path incorrect
```

#### Issue: Docker compose fails
```
ERROR: No such service: pipeline
```

**Solution:**
```bash
# Check docker-compose.yml syntax
cat docker/docker-compose.yml

# Verify services are defined
# Should have: mlflow, pipeline, dashboard, jupyter

# Fix and retry
docker-compose up -d
```

#### Issue: Port already in use
```
ERROR: Port 5000 is already allocated
```

**Solution:**
```bash
# Stop existing containers
docker-compose down

# Or use different port
# Edit docker-compose.yml:
# ports: ["5001:5000"]  # Map to different port

# Retry
docker-compose up -d
```

---

### 🔴 Performance Issues

#### Issue: Tests take too long
```
Test suite takes 5+ minutes
```

**Solution:**
```bash
# Run specific tests only
pytest tests/test_features.py -v

# Skip slow tests
pytest tests/ -m "not slow" -v

# Run in parallel
pytest tests/ -n 4  # Requires pytest-xdist

# Profile which tests are slow
pytest tests/ --durations=10

# Optimize slow tests:
# - Use smaller fixtures
# - Mock external calls
# - Cache expensive computations
```

#### Issue: Pipeline takes too long
```
Pipeline execution > 30 minutes
```

**Solution:**
```bash
# Profile the pipeline
python -m cProfile -s cumulative scripts/run_pipeline.py

# Identify bottleneck and optimize:
# - Reduce data size for testing
# - Use fewer clustering algorithms
# - Cache feature engineering results
```

---

### 🔴 Deployment Issues

#### Issue: Can't install dependencies
```
ERROR: Failed building wheel for package
```

**Solution:**
```bash
# Upgrade pip
python -m pip install --upgrade pip

# Try installing with compatible versions
pip install -r requirements.txt

# If specific package fails:
pip install --force-reinstall package-name==version

# Check Python version compatibility
python --version  # Should be 3.9+
```

#### Issue: GitHub Container Registry authentication fails
```
ERROR: failed to authenticate with registry
```

**Solution:**
```bash
# This is configured in .github/workflows/ci.yml
# GitHub Actions uses GITHUB_TOKEN automatically

# For manual Docker push (not needed for CI):
# 1. Create personal access token on GitHub
# 2. Login locally:
echo $PAT | docker login ghcr.io -u USERNAME --password-stdin

# Push image:
docker push ghcr.io/username/repo:tag
```

---

### 🟡 Performance Optimization

#### Slow Tests?
```bash
# Find slow tests
pytest tests/ --durations=10

# Solutions:
# 1. Use mocks instead of real data
# 2. Use smaller fixtures
# 3. Cache expensive computations
# 4. Mark slow tests with @pytest.mark.slow
```

#### Large Coverage Reports?
```bash
# Reduce report size
pytest tests/ --cov=src --cov-report=term-missing

# Generate HTML but smaller
pytest tests/ --cov=src --cov-report=html --cov-report=term
```

#### Slow Pipeline?
```bash
# Profile code
python -m cProfile -s cumulative scripts/run_pipeline.py

# Optimize based on profile
# Common bottlenecks:
# - Data loading
# - Feature engineering loops
# - Distance calculations in clustering
```

---

## 📞 Getting Help

### Check These First
1. **Documentation**: README.md, TESTING.md, DEPLOYMENT.md
2. **Logs**: `cat logs/app.log`
3. **Error traceback**: Full error message with line numbers
4. **Verify basics**: 
   ```bash
   python --version  # Should be 3.9+
   pip list | grep -E "pytest|black|mlflow"
   ```

### Getting More Info
```bash
# Verbose output
python project.py test -vv

# With traceback
pytest tests/ -vv --tb=long

# Full configuration
flake8 --version
black --version
python -c "import sys; print(sys.version)"
```

### Common Debug Commands
```bash
# Check Python path
python -c "import sys; print(sys.path)"

# Check imports
python -c "import src; print(src.__file__)"

# Check config
python -c "from src.utils.config import load_config; c = load_config(); print(c.get('clustering'))"

# Test fixtures
pytest tests/conftest.py -v
```

---

**Still stuck?** Check error traceback for exact line number and file. Read that file carefully. Use `python -m pdb` for interactive debugging.

Good luck! 🚀
