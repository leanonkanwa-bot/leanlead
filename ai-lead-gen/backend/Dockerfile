# syntax=docker/dockerfile:1.7
# ── Build: install deps into a venv ──────────────────────────────────────────
FROM python:3.12-slim AS build

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
 && find /venv -depth -type d -name "__pycache__" -exec rm -rf {} + \
 && find /venv -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete

# ── Runtime ───────────────────────────────────────────────────────────────────
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/venv/bin:$PATH"

COPY --from=build /venv /venv

WORKDIR /app
COPY app ./app

# Persistent data directory – mount a volume here to survive container restarts
RUN mkdir -p /app/data

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
