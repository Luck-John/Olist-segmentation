# Deployment & Operations Guide

## 🚀 Quick Start

### 1. Local Development

```bash
# Setup
python project.py install
python project.py pipeline
python project.py mlflow

# Access MLFlow UI
open http://localhost:5000
```

### 2. Docker Deployment

```bash
# Start all services
cd docker
docker-compose up -d

# Services will be available at:
# - MLFlow: http://localhost:5000
# - Dashboard: http://localhost:8501
# - Jupyter: http://localhost:8888
```

### 3. Testing

```bash
python project.py test
python project.py lint
python project.py format
```

## 📋 Environment Variables

Create a `.env` file in the `docker/` directory:

```env
# MLFlow
MLFLOW_PORT=5000

# Streamlit Dashboard
STREAMLIT_PORT=8501

# Jupyter Notebook
JUPYTER_PORT=8888

# Database (optional)
DB_HOST=localhost
DB_USER=admin
DB_PASSWORD=secure_password
```

## 🔧 Configuration

### Main Configuration File

Edit `config/config.yaml` to customize:

```yaml
# Clustering parameters
clustering:
  kmeans:
    k_min: 2           # Minimum clusters to test
    k_max: 10          # Maximum clusters to test
    init: "k-means++"
    n_init: 10

# Feature engineering
feature_engineering:
  sao_paulo_coords: [-23.55, -46.63]  # Reference location
  top_categories_count: 5              # Top categories to track

# MLFlow
mlflow:
  experiment_name: "Olist_Segmentation"
  tracking_uri: "file:./mlruns"        # Local or remote
```

## 📊 Pipeline Execution

### Full Pipeline

```bash
python scripts/run_pipeline.py
```

This runs:
1. Data loading and preprocessing
2. Feature engineering
3. Scaling and normalization
4. Clustering (KMeans, DBSCAN, Hierarchical)
5. Model evaluation
6. Results saving
7. MLFlow logging

### MLFlow Operations

```bash
# Start UI server
python project.py mlflow

# Register model to production
python scripts/register_model.py --action promote

# List model versions
python scripts/register_model.py --action list

# Load production model
python scripts/register_model.py --action load
```

## 📈 Monitoring

### MLFlow UI

Access at `http://localhost:5000` to:
- View all experiments
- Compare run metrics
- Review artifacts
- Manage model registry
- Track parameter changes

### Docker Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f pipeline
docker-compose logs -f mlflow

# Real-time tail
tail -f logs/segmentation.log
```

## 🧪 Testing & Quality

### Run All Tests

```bash
python project.py test
```

### Code Quality Checks

```bash
python project.py lint      # Check code style
python project.py format    # Format code automatically
```

### Coverage Report

```bash
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

## 🐳 Docker Commands

### Build

```bash
python project.py docker-build

# Or manually
docker build -t olist-segmentation:latest -f docker/Dockerfile .
```

### Run Services

```bash
# Start
python project.py docker-up
# or
cd docker && docker-compose up -d

# Stop
python project.py docker-down
# or
cd docker && docker-compose down

# View logs
docker-compose logs -f
```

### Clean Up

```bash
# Stop containers
docker-compose down

# Remove containers
docker-compose rm -f

# Remove images
docker rmi olist-segmentation:latest

# Clean up volumes
docker volume prune
```

## 📤 Deployment Checklist

- [ ] All tests passing (`pytest tests/`)
- [ ] Code quality checks passed (`flake8`, `black`, `isort`)
- [ ] Coverage >80%
- [ ] Configuration updated in `config/config.yaml`
- [ ] Docker image builds successfully
- [ ] All services start in docker-compose
- [ ] MLFlow tracking working
- [ ] Model registry initialized
- [ ] Documentation updated
- [ ] Logs configured

## 🔍 Troubleshooting

### Tests Failing

```bash
# Run with verbose output
pytest tests/ -v -s

# Run specific test
pytest tests/test_features.py::TestRFM::test_rfm_calculation -v

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing
```

### Docker Issues

```bash
# Remove dangling containers
docker container prune -f

# Check logs
docker-compose logs pipeline

# Rebuild without cache
docker-compose build --no-cache
```

### MLFlow Issues

```bash
# Check tracking URI
mlflow ui --backend-store-uri file:./mlruns

# View experiments
python -c "import mlflow; client = mlflow.tracking.MlflowClient(); print(client.search_experiments())"

# Clean up old runs
rm -rf mlruns/
```

## 📚 Additional Resources

- [Project README](README.md)
- [Logging Guide](LOGGING.md)
- [Configuration Reference](config/config.yaml)
- [Test Documentation](tests/)
- [MLFlow Documentation](https://mlflow.org/docs/latest/)
- [Scikit-learn Clustering](https://scikit-learn.org/stable/modules/clustering.html)

## 🤝 Support

For issues:
1. Check logs: `logs/segmentation.log`
2. Review configuration: `config/config.yaml`
3. Run tests: `python project.py test`
4. Check Docker: `docker-compose logs`

---

**Last Updated**: December 2024
