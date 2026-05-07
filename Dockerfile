FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
  && rm -rf /var/lib/apt/lists/*

# Dépendances légères (évite mlflow/sphinx/streamlit dans l’image API)
ENV PIP_DEFAULT_TIMEOUT=180 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY requirements-api.txt .
RUN pip install --no-cache-dir --upgrade pip \
  && pip install --no-cache-dir --prefer-binary -r requirements-api.txt

COPY src/ ./src/
COPY scripts/ ./scripts/
COPY config/ ./config/
COPY templates/ ./templates/
COPY project.py setup.cfg ./

# Seulement ce que l’API charge (évite ~15 .pkl + PNG inutiles → build Railway plus fiable)
RUN mkdir -p notebooks/models notebooks/reports
COPY notebooks/models/final_pipeline.pkl ./notebooks/models/
COPY notebooks/models/cluster_names.json ./notebooks/models/
COPY notebooks/reports/ ./notebooks/reports/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    API_HOST=0.0.0.0 \
    API_PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
  CMD sh -c "curl -fsS http://127.0.0.1:$${PORT:-8000}/health || exit 1"

CMD ["sh", "-c", "python -m uvicorn scripts.api:app --host 0.0.0.0 --port ${PORT:-8000} --log-level info"]
