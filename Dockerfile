FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Older setuptools that still ships pkg_resources (openai-whisper needs it).
RUN pip install "setuptools<70" wheel

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-build-isolation -r /app/backend/requirements.txt

COPY backend /app/backend
COPY frontend /app/frontend

WORKDIR /app/backend

RUN mkdir -p storage/uploads storage/outputs storage/work

ENV PORT=8000
EXPOSE 8000

# Cloud platforms (Railway, Render, Fly) inject $PORT — honor it.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
