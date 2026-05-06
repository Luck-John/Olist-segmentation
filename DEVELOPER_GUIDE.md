# 👨‍💻 Developer Guide

## 🎯 Development Workflow

### Getting Started

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Projet_2026
   ```

2. **Setup development environment (first time only)**
   ```bash
   python project.py setup
   ```
   This installs all dependencies and setup pre-commit hooks.

3. **Verify everything works**
   ```bash
   python project.py test-local
   ```

### Daily Workflow

```bash
# 1. Create a feature branch
git checkout -b feature/my-feature

# 2. Make your changes to code
# (Edit files in src/, tests/, etc.)

# 3. Before commit, run tests locally
python project.py test-local

# 4. Auto-format code
python project.py format

# 5. Commit your changes
git commit -m "feat: add new feature"
# Pre-commit hooks will run automatically

# 6. Push to GitHub
git push origin feature/my-feature

# 7. Create Pull Request on GitHub
# (CI/CD will run automatically)
```

---

## 📂 Project Structure

```
Projet_2026/
├── src/                          # Main source code
│   ├── data/
│   │   └── preprocessing.py      # Data loading & cleaning
│   ├── features/
│   │   └── engineering.py        # Feature creation
│   ├── clustering/
│   │   └── models.py            # Clustering algorithms
│   └── utils/
│       └── config.py            # Configuration management
│
├── tests/                        # Test suite
│   ├── conftest.py              # Pytest configuration
│   ├── test_data.py             # Data tests
│   ├── test_features.py         # Feature tests
│   └── test_clustering.py       # Clustering tests
│
├── scripts/                      # Utility scripts
│   ├── run_pipeline.py          # Main pipeline
│   ├── register_model.py        # MLFlow model registry
│   ├── test_local.py            # Local test runner
│   └── setup_dev.py             # Development setup
│
├── notebooks/                    # Jupyter notebooks & dashboard
│   ├── *.ipynb                  # Analysis notebooks
│   ├── dashboard.py             # Streamlit MLFlow dashboard
│   └── figures/                 # Generated plots
│
├── docker/                       # Docker configuration
│   ├── Dockerfile               # Multi-stage build
│   └── docker-compose.yml       # Service orchestration
│
├── config/                       # Configuration files
│   └── config.yaml              # Project parameters
│
├── .github/
│   └── workflows/
│       └── ci.yml               # GitHub Actions workflow
│
└── data/                         # Data files
    └── *.csv                    # Raw datasets
```

---

## 🧪 Testing

### Running Tests

```bash
# All tests with coverage
python project.py test

# Run local validation (same as GitHub Actions)
python project.py test-local

# Run specific test file
pytest tests/test_features.py -v

# Run specific test function
pytest tests/test_features.py::TestRFM::test_rfm_calculation -v

# Run tests with markers
pytest tests/ -m "not slow" -v

# Run with coverage report
pytest tests/ --cov=src --cov-report=html --cov-report=term-missing
```

### Writing Tests

Tests are in `tests/` directory with this pattern:
- `test_*.py` - Test files (or `*_test.py`)
- `Test*` - Test classes
- `test_*` - Test functions

Example:

```python
# tests/test_features.py
import pytest
from src.features.engineering import FeatureEngineer

class TestRFM:
    def test_rfm_calculation(self, sample_raw_data, config_dict):
        """Test RFM calculation"""
        engineer = FeatureEngineer(config_dict)
        result = engineer.calculate_rfm(sample_raw_data)
        
        assert 'recency' in result.columns
        assert 'frequency' in result.columns
        assert 'monetary' in result.columns
        assert len(result) > 0
```

### Coverage Requirements

- **Minimum:** 80% coverage required
- **Target:** >90% coverage
- **View locally:** `open htmlcov/index.html`

---

## 🎨 Code Style

### Standards

- **Line length:** 120 characters (Black)
- **Imports:** Sorted with isort (Black profile)
- **Formatting:** Black auto-formatter
- **Linting:** flake8 with complexity 10
- **Type hints:** Recommended

### Auto-Format Code

```bash
# Format with Black
black src tests

# Sort imports with isort
isort src tests

# Or use project script
python project.py format
```

### Check Code Quality

```bash
# Run all checks
python project.py lint

# Run specific checks
black --check src tests
isort --check-only src tests
flake8 src tests
```

### Configuration Files

- **Black**: `setup.cfg` [black]
- **isort**: `setup.cfg` [isort]  
- **flake8**: `setup.cfg` [flake8]
- **pytest**: `pytest.ini`
- **pre-commit**: `.pre-commit-config.yaml`

---

## 🪝 Pre-commit Hooks

Pre-commit hooks run automatically before each commit.

### Setup (first time)

```bash
python project.py setup
# or
pre-commit install
```

### What Gets Checked

✅ Trailing whitespace  
✅ End-of-file fixes  
✅ JSON/YAML syntax  
✅ Large file detection  
✅ Black formatting  
✅ isort import sorting  
✅ flake8 linting  
✅ mypy type checking  
✅ Bandit security checks  

### Skip Hooks (if necessary)

```bash
# Skip all hooks
git commit --no-verify -m "urgent fix"

# Skip specific hook
SKIP=black,mypy git commit -m "quick fix"

# Run hooks manually
pre-commit run --all-files
```

---

## 📊 Running the Pipeline

```bash
# Run complete pipeline
python project.py pipeline

# This will:
# 1. Load and preprocess data
# 2. Engineer features
# 3. Scale features
# 4. Run clustering (KMeans, DBSCAN, Hierarchical)
# 5. Evaluate models
# 6. Save results
# 7. Log to MLFlow
```

---

## 📈 MLFlow Tracking

### Start MLFlow UI

```bash
python project.py mlflow
# Open http://localhost:5000
```

### View Experiments

1. Go to MLFlow UI (http://localhost:5000)
2. Select experiment
3. View runs with metrics and parameters
4. Compare runs side-by-side

### Register Models

```bash
# Promote best model to Production
python scripts/register_model.py --action promote

# List all models
python scripts/register_model.py --action list

# Load a model
python scripts/register_model.py --action load
```

---

## 📊 Dashboard

### Start Streamlit Dashboard

```bash
python project.py dashboard
# Open http://localhost:8501
```

### Features

- Real-time experiment comparison
- Metrics visualization
- Parameters analysis
- Best run highlighting
- Model registry status
- Interactive Plotly charts

---

## 🐳 Docker Development

### Build Image

```bash
python project.py docker-build
```

### Run Services

```bash
python project.py docker-up
# Services: MLFlow (5000), Dashboard (8501), Jupyter (8888)

python project.py docker-down
# Stop all services
```

### Useful Commands

```bash
# View logs
docker-compose logs -f pipeline

# Run command in container
docker-compose exec pipeline python -m pytest tests/

# Rebuild without cache
docker build --no-cache -f docker/Dockerfile .
```

---

## 🔄 Git Workflow

### Branch Naming

```
feature/description      # New feature
bugfix/description       # Bug fix
docs/description         # Documentation
refactor/description     # Code refactoring
test/description         # Tests
```

### Commit Messages

```
feat: add new clustering algorithm
fix: resolve data preprocessing bug
docs: update README
style: format code with black
test: add tests for feature engineering
refactor: simplify feature calculation
chore: update dependencies
```

### Pull Request Process

1. Create feature branch: `git checkout -b feature/my-feature`
2. Make changes and test: `python project.py test-local`
3. Commit: `git commit -m "feat: description"`
4. Push: `git push origin feature/my-feature`
5. Create PR on GitHub
6. Wait for GitHub Actions to pass
7. Request review
8. Merge when approved

---

## 🆘 Common Issues

### Import Errors

```bash
# Make sure you're in the project directory
cd /path/to/Projet_2026

# Reinstall dependencies
python -m pip install -r requirements.txt
```

### Tests Fail

```bash
# Run verbose test output
pytest tests/ -vv --tb=long

# Run specific test with debugging
pytest tests/test_features.py::TestRFM -vvv
```

### Pre-commit Blocks Commit

```bash
# See what failed
pre-commit run --all-files

# Auto-fix
black src tests
isort src tests

# Try again
git commit -m "fix: formatting"
```

### Coverage Below 80%

```bash
# Find uncovered lines
pytest --cov=src --cov-report=term-missing

# Generate HTML report
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

---

## 📚 Useful Commands

```bash
# Setup (first time)
python project.py setup

# Daily checks
python project.py test-local

# Format code before commit
python project.py format

# Run pipeline
python project.py pipeline

# Start MLFlow UI
python project.py mlflow

# Start dashboard
python project.py dashboard

# Docker
python project.py docker-up
python project.py docker-down

# Help
python project.py help
```

---

## 📖 Documentation

- **README.md** - Project overview
- **TESTING.md** - Testing & CI/CD guide
- **DEPLOYMENT.md** - Production deployment
- **DEPLOYMENT_CHECKLIST.md** - First deployment steps
- **LOGGING.md** - Logging configuration
- **DEVELOPER_GUIDE.md** - This file

---

## 🎓 For Academic Defense

Show these capabilities:

1. **Automated Testing**
   ```bash
   python project.py test-local
   ```

2. **Code Quality Enforcement**
   - Show GitHub Actions workflow
   - Demonstrate PEP8 compliance
   - Show pre-commit hooks

3. **ML Pipeline Automation**
   ```bash
   python project.py pipeline
   ```

4. **Experiment Tracking**
   ```bash
   python project.py mlflow
   ```

5. **Results Dashboard**
   ```bash
   python project.py dashboard
   ```

6. **Docker Containerization**
   ```bash
   python project.py docker-up
   ```

---

**Happy coding!** 🚀

If you have questions, check the documentation files or GitHub Issues.
