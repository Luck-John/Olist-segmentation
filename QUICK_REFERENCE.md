# 🎯 Quick Reference Card

**Quick lookup for most common commands and procedures.**

Print this page and keep it handy! 📋

---

## 🚀 Most Important Commands

```bash
# Setup everything (ONE TIME)
python project.py setup

# Daily: Check everything is ok
python project.py test-local

# Run the ML pipeline
python project.py pipeline

# View experiments
python project.py mlflow

# View dashboard
python project.py dashboard

# Deploy with Docker
python project.py docker-up
```

---

## 📝 Git Workflow

```bash
# Create feature branch
git checkout -b feature/my-feature

# Make changes...

# Check everything
python project.py test-local

# Format code
python project.py format

# Commit with clear message
git commit -m "feat: add new feature"

# Push to GitHub
git push origin feature/my-feature

# Create Pull Request on GitHub
```

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific file
pytest tests/test_features.py -v

# Run specific test
pytest tests/test_features.py::TestRFM::test_rfm_calculation -v

# See coverage
pytest tests/ --cov=src --cov-report=term-missing

# View coverage in browser
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

---

## 🎨 Code Quality

```bash
# Auto-format
python project.py format
# or: black src tests && isort src tests

# Check formatting
black --check src tests
isort --check-only src tests

# Run linting
python project.py lint
# or: flake8 src tests

# Run all checks
python project.py test-local
```

---

## 🐳 Docker

```bash
# Build image
python project.py docker-build
# or: docker build -f docker/Dockerfile -t olist-segmentation:latest .

# Start services
python project.py docker-up
# or: cd docker && docker-compose up -d

# Stop services
python project.py docker-down
# or: cd docker && docker-compose down

# View logs
docker-compose logs -f pipeline
```

---

## 📊 MLFlow

```bash
# Start MLFlow UI
python project.py mlflow

# Access at: http://localhost:5000

# Register model
python scripts/register_model.py --action promote

# List models
python scripts/register_model.py --action list

# Load model
python scripts/register_model.py --action load
```

---

## 📈 Dashboard

```bash
# Start Streamlit dashboard
python project.py dashboard

# Access at: http://localhost:8501

# Press Ctrl+C to stop
```

---

## 🛠️ Setup & Installation

```bash
# First time setup (includes pre-commit)
python project.py setup

# Install dependencies only
python project.py install

# Install dev tools (pytest, black, etc)
python project.py install-dev

# Setup pre-commit hooks (if not done)
pre-commit install

# Run pre-commit on all files
pre-commit run --all-files
```

---

## 🔍 Debugging

```bash
# Check Python version
python --version

# Check installed packages
pip list | grep -E "pytest|black|mlflow"

# Verify configuration
python -c "from src.utils.config import load_config; print(load_config())"

# Run test with verbose output
pytest tests/ -vv --tb=long

# Run test with print statements
pytest tests/ -s -vv

# Profile code
python -m cProfile -s cumulative scripts/run_pipeline.py
```

---

## 📂 Project Structure

```
Projet_2026/
├── src/                    # Production code
│   ├── data/              # Data preprocessing
│   ├── features/          # Feature engineering
│   ├── clustering/        # Clustering models
│   └── utils/             # Utilities (config, logging)
├── tests/                 # Tests
│   └── test_*.py         # Test files
├── scripts/               # Utility scripts
├── notebooks/             # Jupyter notebooks + dashboard
├── docker/                # Docker files
├── config/                # Configuration
├── .github/workflows/     # GitHub Actions
├── data/                  # Datasets
└── [Documentation files]
```

---

## 📚 Documentation Files

| File | Purpose |
|------|---------|
| **README.md** | Project overview |
| **TESTING.md** | Testing guide |
| **DEVELOPER_GUIDE.md** | Development workflow |
| **DEPLOYMENT.md** | Production deployment |
| **DEPLOYMENT_CHECKLIST.md** | First deployment |
| **ACADEMIC_PRESENTATION.md** | Defense demo |
| **TROUBLESHOOTING.md** | Problem solving |
| **DEMO_SCRIPT.md** | 5-min demo |
| **PRE_PUSH_VALIDATION.md** | Pre-push checklist |
| **DOCUMENTATION_INDEX.md** | Navigation hub |

---

## 🚨 Common Issues & Quick Fixes

| Problem | Solution |
|---------|----------|
| Import errors | Run: `python project.py setup` |
| Tests fail | Run: `pytest tests/ -vv --tb=short` |
| Code formatting wrong | Run: `python project.py format` |
| Port 5000 in use | Use: `mlflow server --port 5001` |
| Coverage below 80% | Check: `pytest --cov=src --cov-report=term-missing` |
| Docker won't start | Check: `docker ps` and `docker logs` |
| Pre-commit blocks | Run: `pre-commit run --all-files` |
| Can't find data | Check: data/ directory exists |

---

## ✅ Pre-Push Checklist

Before pushing to GitHub:

```bash
# 1. Format code
python project.py format

# 2. Run linting
python project.py lint

# 3. Run tests
python project.py test

# 4. Final check
python project.py test-local

# 5. If all green, push!
git push origin main
```

---

## 🎓 For Academic Defense

```bash
# Demo sequence (5 min):

# 1. Show structure
ls src/ tests/ scripts/

# 2. Run tests
python project.py test-local

# 3. Start MLFlow
python project.py mlflow
# Open: http://localhost:5000

# 4. Start dashboard  
python project.py dashboard
# Open: http://localhost:8501

# 5. Show GitHub Actions
# Go to: GitHub → Actions → Recent runs
```

---

## 🔧 Configuration Files

| File | Purpose |
|------|---------|
| **setup.cfg** | Black, isort, flake8, pylint config |
| **pytest.ini** | Pytest configuration |
| **.pre-commit-config.yaml** | Pre-commit hooks |
| **config/config.yaml** | Project parameters |
| **.github/workflows/ci.yml** | GitHub Actions |
| **.gitignore** | Git ignore patterns |

---

## 📊 Key Metrics

- **Test Coverage**: Must be >80%
- **Line Length**: Max 120 characters
- **Complexity**: Max 10
- **Python Versions**: 3.9, 3.10, 3.11
- **CI/CD Time**: ~20 minutes

---

## 🎯 Environment Variables

For Docker/production:

```bash
# MLFlow
MLFLOW_TRACKING_URI=file:./mlruns

# Data paths
DATA_PATH=./data/
OUTPUT_PATH=./models/

# Logging
LOG_LEVEL=INFO
LOG_PATH=./logs/

# Ports (Docker)
MLFLOW_PORT=5000
DASHBOARD_PORT=8501
JUPYTER_PORT=8888
```

---

## 🔐 Security

- No hardcoded secrets
- Use environment variables
- Bandit scans for security issues
- Safety checks dependencies

```bash
# Security check
bandit -r src/
safety check
```

---

## 📞 Getting Help

1. **Quick help**: `python project.py help`
2. **Documentation index**: See DOCUMENTATION_INDEX.md
3. **Specific issue**: Check TROUBLESHOOTING.md
4. **Development help**: See DEVELOPER_GUIDE.md
5. **Deployment help**: See DEPLOYMENT.md

---

## 🎯 Success = Green Checkmarks

```
✅ Code formatted
✅ Tests passing
✅ Coverage >80%
✅ Linting clean
✅ Security passed
✅ Pre-commit passed
✅ Ready to push!
```

---

## 📱 Ports Reference

| Service | Port | URL |
|---------|------|-----|
| MLFlow | 5000 | http://localhost:5000 |
| Dashboard | 8501 | http://localhost:8501 |
| Jupyter | 8888 | http://localhost:8888 |
| API | 8000 | http://localhost:8000 |

---

## 💡 Pro Tips

1. **Run tests frequently** - Don't wait until push
2. **Format as you go** - Use `black src tests` regularly
3. **Read error messages** - They tell you exactly what's wrong
4. **Use verbose mode** - `pytest -vv` shows more details
5. **Check GitHub Actions** - Run same checks as your machine

---

**Print this card and keep it on your desk!** 📋✨

**Last Updated:** May 5, 2026 | **Version:** 1.0.0
