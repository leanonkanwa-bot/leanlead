"""
Local launcher — run from the project root:

    python app.py

Then open http://localhost:8000 in your browser.

Before first run, make sure backend/.env contains your ANTHROPIC_API_KEY.
Copy backend/.env.example to backend/.env and fill in the key.
"""
import sys
import os
from pathlib import Path

# Put backend/ on the import path so `from app.xxx import ...` works.
backend_dir = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(backend_dir))

# Change working dir to backend/ so relative storage paths resolve correctly.
os.chdir(backend_dir)

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        # Allow chunk bodies up to 250 MB (supports 20 GB+ files via chunked upload).
        # h11's default is 16 KB which would silently drop large PUT bodies.
        h11_max_incomplete_event_size=250 * 1024 * 1024,
    )
