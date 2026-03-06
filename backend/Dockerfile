FROM python:3.11-slim

WORKDIR /app

# System deps for asyncpg (libpq)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE ${PORT:-8000}
CMD sh -c "alembic upgrade head 2>&1 || echo 'Alembic migration warning (non-fatal)'; uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"

