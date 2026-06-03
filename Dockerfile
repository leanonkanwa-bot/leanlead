FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    fonts-open-sans \
    && rm -rf /var/lib/apt/lists/*

# Custom fonts (SF Compact Bold, etc.) — drop TTF files into fonts/ before building.
COPY fonts/ /usr/local/share/fonts/leanlead/
RUN fc-cache -f -v 2>/dev/null || true

WORKDIR /app/backend

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY editor_frontend/ /app/editor_frontend/
COPY frontend/ /app/frontend/

EXPOSE 8000

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
