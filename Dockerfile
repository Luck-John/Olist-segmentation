FROM python:3.10-slim

WORKDIR /app

# System deps (keep minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
  && rm -rf /var/lib/apt/lists/*

# Python deps - copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
  && pip install --no-cache-dir -r requirements.txt

# Copy source code first (excluding heavy data files)
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY config/ ./config/
COPY templates/ ./templates/
COPY project.py setup.cfg ./

# Copy model and reports (required for API)
COPY notebooks/models/ ./notebooks/models/
COPY notebooks/reports/ ./notebooks/reports/

# Copy remaining files
COPY *.md *.txt ./

# Railway provides $PORT; default to 8000 locally
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    API_HOST=0.0.0.0 \
    API_PORT=8000

EXPOSE 8000

# Healthcheck with better error handling
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD python -c "import requests; requests.get(f'http://127.0.0.1:${PORT:-8000}/health', timeout=5)" || exit 1

# Start command with proper error handling
CMD ["sh", "-c", "python -m uvicorn scripts.api:app --host 0.0.0.0 --port ${PORT:-8000} --log-level info"]
