# syntax=docker/dockerfile:1.7

# ===== Build stage ===========================================================
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
 && find /opt/venv -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete

# ===== Runtime stage =========================================================
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8000 \
    HF_HOME=/app/backend/storage/.cache/huggingface

# ffmpeg + fonts — fonts-inter is not in Debian slim so we skip it;
# Poppins Bold/ExtraBold/SemiBold are fetched directly from Google Fonts.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        ffmpeg ca-certificates curl fontconfig \
        fonts-roboto fonts-dejavu-core \
 && mkdir -p /usr/local/share/fonts/leanlead \
 && cd /usr/local/share/fonts/leanlead \
 && for url in \
      "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Bold.ttf" \
      "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-ExtraBold.ttf" \
      "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-SemiBold.ttf" \
      "https://github.com/google/fonts/raw/main/ofl/montserrat/static/Montserrat-Black.ttf" \
      "https://github.com/google/fonts/raw/main/ofl/bebasneue/BebasNeue-Regular.ttf" ; do \
      curl -fsSL --retry 3 --max-time 30 -O "$url" || echo "warn: failed $url"; \
    done \
 && fc-cache -f > /dev/null \
 && apt-get purge -y curl \
 && apt-get autoremove -y \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/* /var/log/*

COPY --from=build /opt/venv /opt/venv

# Copy backend (required) and frontend (optional — served as static files).
WORKDIR /app
COPY backend /app/backend
COPY frontend /app/frontend

# Working dir is backend/ so `uvicorn app.main:app` finds the app package.
WORKDIR /app/backend
RUN mkdir -p storage/uploads storage/outputs storage/work storage/.cache/huggingface

EXPOSE 8000

# Railway / Render / Fly inject $PORT — fall back to 8000 locally.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
