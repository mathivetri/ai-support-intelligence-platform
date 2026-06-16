# syntax=docker/dockerfile:1
#
# Backend image — FastAPI + async SQLAlchemy.
# Build context is the REPO ROOT (so requirements.txt and backend/ are both
# available); see docker-compose.yml: build.context = ".".
#
#     docker build -f backend/Dockerfile -t support-backend .

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first so this layer is cached across code changes.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend application code (alembic.ini, alembic/, app/).
COPY backend/ ./

# Run as an unprivileged user.
RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Apply migrations, then start the API. Binds to $PORT when the host provides
# one (e.g. Render), falling back to 8000 for local compose. The DB host is
# reachable as `db` inside the compose network; depends_on waits for its health.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
