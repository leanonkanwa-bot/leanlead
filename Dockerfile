# syntax=docker/dockerfile:1.7

# ===== Build stage ===========================================================
# Install Python deps into a venv we'll copy out. faster-whisper uses
# CTranslate2 (C++) for inference, so we don't need torch/cuda/triton at all
# — image fits comfortably under 1 GB.
FROM python:3.12-slim AS build

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir "setuptools<70" wheel

COPY backend/requirements.txt /tmp/requirements.txt

RUN pip install --no-cache-dir -r /tmp/requirements.txt \
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
    PORT=8000 \
    HF_HOME=/app/backend/storage/.cache/huggingface

# Only ffmpeg + ca-certificates at runtime. No build tools, no apt cache.
# Fonts: roboto+inter+montserrat from apt where available, Poppins Bold +
# ExtraBold pulled directly from upstream (the user spec mandates Poppins
# Bold as the default caption font).
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        ffmpeg ca-certificates curl fontconfig \
        fonts-roboto fonts-montserrat fonts-inter \
 && mkdir -p /usr/local/share/fonts/leanlead \
 && cd /usr/local/share/fonts/leanlead \
 && curl -fsSL -O https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Bold.ttf \
 && curl -fsSL -O https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-ExtraBold.ttf \
 && curl -fsSL -O https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-SemiBold.ttf \
 && curl -fsSL -O https://github.com/google/fonts/raw/main/ofl/montserrat/static/Montserrat-Black.ttf \
 && curl -fsSL -O https://github.com/google/fonts/raw/main/ofl/bebasneue/BebasNeue-Regular.ttf \
 && curl -fsSL -O https://github.com/google/fonts/raw/main/ofl/dmsans/DMSans%5Bopsz%2Cwght%5D.ttf \
 && curl -fsSL -O https://github.com/google/fonts/raw/main/ofl/spacegrotesk/SpaceGrotesk%5Bwght%5D.ttf \
 && fc-cache -f > /dev/null \
 && apt-get purge -y curl \
 && apt-get autoremove -y \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/* /var/log/*

COPY --from=build /opt/venv /opt/venv

WORKDIR /app
COPY backend /app/backend
COPY frontend /app/frontend

WORKDIR /app/backend
RUN mkdir -p storage/uploads storage/outputs storage/work storage/.cache/huggingface

EXPOSE 8000

# Cloud platforms (Railway, Render, Fly) inject $PORT — honor it.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
