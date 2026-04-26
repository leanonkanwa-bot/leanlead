# syntax=docker/dockerfile:1.7

# ===== Build stage ===========================================================
# Installs all Python deps into a venv we'll copy out. Uses CPU-only torch
# (saves ~3 GB of nvidia/cuda libraries we don't need on Railway/Render/Fly).
FROM python:3.12-slim AS build

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

# build-essential only here so the runtime image stays clean.
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Older setuptools that still ships pkg_resources (openai-whisper needs it).
RUN pip install --no-cache-dir "setuptools<70" wheel

COPY backend/requirements.txt /tmp/requirements.txt

# 1. Install CPU-only torch FIRST so the next pip resolution doesn't pull in
#    the cuda variant from PyPI. ~200 MB instead of ~2.5 GB.
# 2. Then install everything else (whisper, fastapi, anthropic, …) without
#    build isolation so the openai-whisper sdist build can see setuptools.
# 3. Aggressively clean __pycache__, *.pyc, tests, .a static libs, debug symbols.
RUN pip install --no-cache-dir \
      --index-url https://download.pytorch.org/whl/cpu \
      "torch>=2.4,<3" \
 && pip install --no-cache-dir --no-build-isolation -r /tmp/requirements.txt \
 && find /opt/venv -depth -type d -name "__pycache__" -exec rm -rf {} + \
 && find /opt/venv -type f -name "*.pyc" -delete \
 && find /opt/venv -type f -name "*.pyo" -delete \
 && find /opt/venv -type d -name "tests" -path "*/site-packages/*" -exec rm -rf {} + 2>/dev/null || true \
 && find /opt/venv -type f -name "*.a" -delete \
 && find /opt/venv -type f -name "*.so*" -exec strip --strip-unneeded {} + 2>/dev/null || true

# ===== Runtime stage =========================================================
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8000

# Only ffmpeg + ca-certificates at runtime. No build tools, no apt cache.
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/* /var/log/*

COPY --from=build /opt/venv /opt/venv

WORKDIR /app
COPY backend /app/backend
COPY frontend /app/frontend

WORKDIR /app/backend
RUN mkdir -p storage/uploads storage/outputs storage/work

EXPOSE 8000

# Cloud platforms (Railway, Render, Fly) inject $PORT — honor it.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
