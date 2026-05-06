FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
  && rm -rf /var/lib/apt/lists/*

# Dépendances légères (évite mlflow/sphinx/streamlit dans l’image API)
COPY requirements-api.txt .
RUN pip install --no-cache-dir --upgrade pip \
  && pip install --no-cache-dir -r requirements-api.txt

COPY src/ ./src/
COPY scripts/ ./scripts/
COPY config/ ./config/
COPY templates/ ./templates/
COPY project.py setup.cfg ./

# Tout le dossier notebooks/ (models + reports si versionnés ; sinon le build ne casse pas)
COPY notebooks/ ./notebooks/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    API_HOST=0.0.0.0 \
    API_PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD sh -c "curl -fsS http://127.0.0.1:$${PORT:-8000}/health || exit 1"

CMD ["sh", "-c", "python -m uvicorn scripts.api:app --host 0.0.0.0 --port ${PORT:-8000} --log-level info"]
