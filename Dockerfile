FROM python:3.9-slim AS backend

WORKDIR /app

# System dependencies (libpq-dev for psycopg2-binary)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first for Docker layer caching
COPY requirements.txt requirements-prod.txt ./
RUN pip install --no-cache-dir -r requirements-prod.txt

# Copy backend code and migration files only (frontend in separate Nginx container)
COPY backend/ backend/
COPY alembic/ alembic/
COPY alembic.ini ./

# Create uploads directory
RUN mkdir -p uploads

EXPOSE 8011

# Production: gunicorn + uvicorn worker (per DEPLOY-03)
# --workers 4: default worker count, tune via WEB_CONCURRENCY env var
# --timeout 120: AI/LLM calls may take longer
# --access-logfile -: stdout for docker logs
CMD ["gunicorn", "backend.app.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "4", \
     "--bind", "0.0.0.0:8011", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
