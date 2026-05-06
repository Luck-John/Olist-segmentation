FROM python:3.10-slim

WORKDIR /app

# System deps (keep minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
  && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
  && pip install --no-cache-dir -r requirements.txt

# App code + artifacts (model + reports must be in repo/workdir)
COPY . .

# Render/Railway provide $PORT; default to 8000 locally
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    API_HOST=0.0.0.0 \
    API_PORT=8000

EXPOSE 8000

# Simple healthcheck (Railway sets $PORT)
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT:-8000}/health" || exit 1

CMD ["sh", "-c", "python -m uvicorn scripts.api:app --host 0.0.0.0 --port ${PORT:-8000} --log-level info"]
