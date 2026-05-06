# 📚 Documentation Index

Welcome to the Olist Customer Segmentation project! This page helps you navigate all available documentation.

---

## 🚀 Quick Start (Choose Your Path)

### 👤 New to the Project?
Start here to understand what this project does.
- **→ [README.md](README.md)** - Project overview, architecture, quick start

### 🧑‍💻 Developer Setup?
Ready to code and contribute?
- **→ [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)** - Development workflow, branching strategy, common tasks
- **→ [setup_dev.py](scripts/setup_dev.py)** - Run this first: `python project.py setup`

### 🚢 First Deployment?
About to push to GitHub for the first time?
- **→ [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** - Pre-push validation, step-by-step checklist
- **→ [test_local.py](scripts/test_local.py)** - Run: `python project.py test-local`

### 🎓 Academic Presentation?
Preparing for your defense or demo?
- **→ [ACADEMIC_PRESENTATION.md](ACADEMIC_PRESENTATION.md)** - Demo sequence, talking points, what to show

### 🆘 Something Broken?
Errors or issues?
- **→ [TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues, solutions, debugging tips

---

## 📖 Complete Documentation

### Core Documentation

| Document | Purpose | Audience |
|----------|---------|----------|
| **[README.md](README.md)** | Project overview, features, setup | Everyone |
| **[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)** | Development workflow, commands | Developers |
| **[TESTING.md](TESTING.md)** | Testing framework, CI/CD pipeline | QA/Developers |
| **[DEPLOYMENT.md](DEPLOYMENT.md)** | Production deployment, monitoring | DevOps/Operations |
| **[LOGGING.md](LOGGING.md)** | Logging configuration, log files | Developers/Operations |

### Specialized Guides

| Document | Purpose | Audience |
|----------|---------|----------|
| **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** | Pre-push validation | Developers |
| **[ACADEMIC_PRESENTATION.md](ACADEMIC_PRESENTATION.md)** | Demo for defense | Students |
| **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** | Problem solving | Everyone |
| **[DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)** | This file | Everyone |

---

## 🛠️ Common Tasks

### Setup & Installation

```bash
# First time setup (installs all dependencies + pre-commit)
python project.py setup

# Install only project dependencies
python project.py install

# Install development tools (testing, linting, etc.)
python project.py install-dev
```

**→ See [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md#getting-started) for details**

---

### Running Tests

```bash
# Run all tests locally (like GitHub Actions)
python project.py test-local

# Run specific tests
pytest tests/test_features.py -v

# Run with coverage report
pytest tests/ --cov=src --cov-report=html
```

**→ See [TESTING.md](TESTING.md#running-tests) for details**

---

### Code Quality

```bash
# Format code with Black and isort
python project.py format

# Check code quality
python project.py lint

# Auto-fix and check
black src tests && isort src tests && flake8 src tests
```

**→ See [TESTING.md](TESTING.md#code-style) for details**

---

### Running Pipeline

```bash
# Execute full data processing → clustering → tracking pipeline
python project.py pipeline

# Output includes:
# - Preprocessed data
# - Engineered features
# - Clustering results
# - MLFlow experiment logs
```

**→ See [README.md](README.md#running-the-pipeline) for details**

---

### Experiment Tracking

```bash
# Start MLFlow UI
python project.py mlflow
# Access at http://localhost:5000

# View experiments, runs, metrics
# Compare models side-by-side
# Register and promote models
```

**→ See [TESTING.md](TESTING.md#mlflow-tracking-in-ci-cd) for details**

---

### Dashboard & Visualization

```bash
# Start Streamlit dashboard
python project.py dashboard
# Access at http://localhost:8501

# Interactive visualization of:
# - Experiment metrics
# - Model performance
# - Parameters analysis
# - Best runs
```

**→ See [ACADEMIC_PRESENTATION.md](ACADEMIC_PRESENTATION.md#6-interactive-dashboard-) for demo**

---

### Docker Deployment

```bash
# Build Docker image
python project.py docker-build

# Start all services (MLFlow, Dashboard, Jupyter, Pipeline)
python project.py docker-up

# Stop all services
python project.py docker-down
```

**→ See [DEPLOYMENT.md](DEPLOYMENT.md) for full Docker guide**

---

## 📊 Project Structure

```
Projet_2026/
├── src/                         # Source code (production)
│   ├── data/preprocessing.py
│   ├── features/engineering.py
│   ├── clustering/models.py
│   └── utils/config.py
│
├── tests/                       # Unit tests
│   ├── conftest.py             # Pytest fixtures
│   ├── test_data.py
│   ├── test_features.py
│   └── test_clustering.py
│
├── scripts/                     # Utility scripts
│   ├── run_pipeline.py         # Main pipeline
│   ├── register_model.py       # MLFlow model registry
│   ├── test_local.py           # Local test runner
│   └── setup_dev.py            # Dev environment setup
│
├── notebooks/                   # Jupyter & Dashboard
│   ├── dashboard.py            # Streamlit dashboard
│   └── figures/                # Generated plots
│
├── docker/                      # Containerization
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── config/                      # Configuration
│   └── config.yaml             # All parameters
│
├── .github/workflows/
│   └── ci.yml                  # GitHub Actions
│
├── data/                        # Datasets
│
└── [Documentation Files]
    ├── README.md
    ├── TESTING.md
    ├── DEPLOYMENT.md
    ├── LOGGING.md
    ├── DEVELOPER_GUIDE.md
    ├── ACADEMIC_PRESENTATION.md
    ├── DEPLOYMENT_CHECKLIST.md
    ├── TROUBLESHOOTING.md
    └── DOCUMENTATION_INDEX.md
```

---

## 🎯 Quick Reference

### Command Line Tool

```bash
python project.py [command]

# Setup
python project.py setup          # First time
python project.py install        # Install dependencies
python project.py install-dev    # Install dev tools

# Development
python project.py test           # Run tests
python project.py test-local     # Run like GitHub Actions
python project.py lint           # Check code quality
python project.py format         # Auto-format code

# Pipeline & Tracking
python project.py pipeline       # Run clustering pipeline
python project.py mlflow         # Start MLFlow UI
python project.py dashboard      # Start Streamlit dashboard

# Docker
python project.py docker-build   # Build image
python project.py docker-up      # Start services
python project.py docker-down    # Stop services

# Help
python project.py help           # Show all commands
```

---

## 📈 Testing & Quality Metrics

### Test Coverage
- **Minimum Required**: 80%
- **Target**: >90%
- **Command**: `pytest tests/ --cov=src --cov-fail-under=80`

### Code Quality Standards
- **Line Length**: 120 characters (Black)
- **Complexity**: Max 10 (flake8)
- **Style**: PEP8 (enforced with pre-commit)
- **Security**: Bandit scanning

### CI/CD Pipeline
- **Trigger**: Every push to main/develop
- **Jobs**: 5 (code quality → test → docker build → security → status)
- **Python Versions**: 3.9, 3.10, 3.11
- **Duration**: ~20 minutes total

---

## 🔍 Key Technologies

| Category | Tools |
|----------|-------|
| **Data Processing** | Pandas, NumPy, Scikit-learn |
| **Clustering** | KMeans, DBSCAN, Hierarchical |
| **Experiment Tracking** | MLFlow |
| **Visualization** | Streamlit, Plotly |
| **Testing** | Pytest, pytest-cov |
| **Code Quality** | Black, isort, flake8, pylint |
| **CI/CD** | GitHub Actions |
| **Containerization** | Docker, Docker Compose |
| **Configuration** | PyYAML, Singleton pattern |

---

## 🎓 For Academic Defense

Start with **[ACADEMIC_PRESENTATION.md](ACADEMIC_PRESENTATION.md)** to learn:
- Key points to demonstrate
- Demo sequence options
- Talking points
- Common questions
- What files to show

---

## ❓ Frequently Asked Questions

**Q: Where do I start?**
A: Run `python project.py setup` then `python project.py test-local`

**Q: How do I run the pipeline?**
A: Use `python project.py pipeline`

**Q: How do I view experiment results?**
A: Use `python project.py mlflow` and open http://localhost:5000

**Q: How do I deploy?**
A: Read [DEPLOYMENT.md](DEPLOYMENT.md) or [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)

**Q: Something's broken, what do I do?**
A: Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

**Q: Where's the code?**
A: Production code is in `src/`, tests are in `tests/`

**Q: How do I contribute?**
A: Read [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) and create a feature branch

---

## 🔗 External Links

- [Pytest Documentation](https://docs.pytest.org/)
- [GitHub Actions](https://docs.github.com/en/actions)
- [MLFlow Documentation](https://mlflow.org/docs/latest/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Docker Documentation](https://docs.docker.com/)
- [Black Code Formatter](https://black.readthedocs.io/)
- [flake8 Documentation](https://flake8.pycqa.org/)

---

## 📞 Support

1. Check relevant documentation
2. Search [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
3. Read error traceback carefully
4. Use verbose flags (-vv, --tb=long)
5. Check GitHub Issues

---

**Last Updated:** May 5, 2026  
**Project Version:** 1.0.0  
**Python Support:** 3.9, 3.10, 3.11

---

## 📋 Documentation Checklist

- ✅ [README.md](README.md) - Project overview
- ✅ [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) - Development guide
- ✅ [TESTING.md](TESTING.md) - Testing & CI/CD
- ✅ [DEPLOYMENT.md](DEPLOYMENT.md) - Production deployment
- ✅ [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) - First deployment
- ✅ [LOGGING.md](LOGGING.md) - Logging configuration
- ✅ [ACADEMIC_PRESENTATION.md](ACADEMIC_PRESENTATION.md) - Defense demo
- ✅ [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Issue resolution
- ✅ [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) - This file

All documentation is complete and up-to-date! 📚
