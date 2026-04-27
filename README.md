# AI Video Editor Agent

Upload your raw talking-head video. Drop your instructions. The agent
transcribes, decides what to keep, what to cut, where to zoom, where to
caption, and renders a high-retention edit — short form (Reels/TikTok/Shorts)
or long form (YouTube cinematic).

The agent's brain is Claude. The editing engine is FFmpeg. The transcription
is Whisper. The retention rules are encoded in `backend/app/agent/rules.py` and
include the storytelling laws (Pixar, McKee), the cinema laws (eye trace,
silence, zoom), and the packaging rules (title curiosity gap, one-word
thumbnail, end caption).

## What it does, end to end

1. You upload a raw video and (optionally) instructions.
2. Whisper transcribes it with word-level timestamps.
3. Claude reads the transcript + the rules and emits an `EditPlan`:
   - what to keep, what to drop (fillers, repeats, weak takes)
   - the zoom plan (drift, punch-in, pull-out)
   - the caption emphasis words
   - B-roll suggestions
   - the packaging — title, one-word thumbnail, end caption
4. FFmpeg cuts, concatenates, applies the zoom via `zoompan`, burns the
   styled `.ass` captions.
5. You download the edited mp4.

## Project layout

```
leanlead/
├── backend/
│   ├── requirements.txt
│   ├── .env.example
│   └── app/
│       ├── main.py              # FastAPI entrypoint
│       ├── core/config.py       # settings + paths
│       ├── api/
│       │   ├── jobs.py          # in-memory job store
│       │   └── pipeline.py      # transcribe → plan → render
│       ├── agent/
│       │   ├── rules.py         # the retention/storytelling system prompt
│       │   └── planner.py       # Claude call → EditPlan
│       └── engine/
│           ├── transcribe.py    # Whisper
│           ├── captions.py      # ASS subtitle builder
│           └── render.py        # FFmpeg pipeline
├── frontend/                    # static HTML/CSS/JS, served by FastAPI
│   ├── index.html
│   ├── style.css
│   └── app.js
└── README.md
```

## Prerequisites

- **Python 3.11+**
- **FFmpeg** in your `PATH` — `ffmpeg -version` must work
- **An Anthropic API key** — https://console.anthropic.com
- ~2 GB free disk for Whisper's `base` model on first run

## Run it locally

```bash
git clone <this repo>
cd leanlead/backend

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# open .env and paste your ANTHROPIC_API_KEY

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 — that's the editor UI.

## Setup in VS Code (with Claude Code)

You said you want to develop this in VS Code with Claude Code. Here's the
fastest path:

1. **Install VS Code** if you haven't.
2. **Install the "Claude Code" extension** from the VS Code Marketplace
   (publisher: Anthropic).
3. Open this folder in VS Code: `File → Open Folder…` → pick `leanlead/`.
4. **Recommended extensions** (VS Code will offer them automatically):
   - Python (Microsoft)
   - Pylance
   - Live Preview (optional, for the frontend)
5. Open the integrated terminal (`Ctrl+\``) and run the steps above
   (`venv`, `pip install`, `uvicorn`).
6. Open the Claude Code panel (`Ctrl+Shift+P` → "Claude Code: Open"). From
   there you can chat with Claude inside the project, ask it to extend
   `backend/app/agent/rules.py`, add new agent modules, or refactor the
   FFmpeg engine. Claude Code already sees the whole repo.

To extend the agent's rules: open `backend/app/agent/rules.py`, ask Claude
Code "add a rule for handling B-roll on emotional peaks", and it will edit
the file in place.

## How to use it

1. Open the UI at http://localhost:8000.
2. Drop your raw video (mp4, mov, webm…).
3. Pick a format: **Auto / Short / Long**.
4. (Optional) Write instructions:
   > "Hook must be the line about temptation. Keep only the strongest takes.
   > End on the principle. Punch-in on every emphasis word."
5. Click **Edit my video**.
6. The status bar shows `transcribing → planning → rendering → done`.
7. Preview & download the result. The packaging block shows the suggested
   title, the one-word thumbnail, and the end caption.

## Tuning the agent

Everything the agent "knows" lives in `backend/app/agent/rules.py`:

- `SHORT_FORM_STRUCTURE` — the 10-beat short structure.
- `LONG_FORM_STRUCTURE` — the cinematic long-form acts.
- `STORY_LAWS` — Pixar pattern, tension, specificity, pattern interrupt.
- `CINEMA_LAWS` — eye trace, cut rhythm, silence, 180° rule.
- `ZOOM_PLAN_SHORT` — 100% → 130% progressive.
- `ZOOM_PLAN_LONG` — invisible cinematic drift, max 110%.
- `BROLL_RULES` — placement and discipline.
- `CAPTION_RULES` — short = big centered, long = lower-third soft.
- `PACKAGING_RULES` — title / thumbnail word / end caption.

To change the agent's behavior, edit those blocks. No code changes needed.

## Deploy as a public website

The repo ships with a `Dockerfile`, `render.yaml`, `railway.json` and
`fly.toml`. Pick the platform that fits.

### Render.com (one-click)

1. Push this repo to GitHub (already done if you cloned it).
2. Click **New → Blueprint** on Render and pick this repo.
3. Render reads `render.yaml`, generates `ACCESS_PASSWORD` for you, and
   asks you for `ANTHROPIC_API_KEY`. Paste it.
4. Wait ~5 min for the Docker build. The site is live at
   `https://leanlead.onrender.com` (or your custom domain).

### Railway.app

1. Click **Deploy from GitHub repo** on Railway, pick this repo.
2. Railway uses `railway.json` + `Dockerfile` automatically.
3. Add env vars in Settings → Variables:
   - `ANTHROPIC_API_KEY` — your key
   - `ACCESS_PASSWORD` — pick a long random string
4. Generate a domain. Done.

### Fly.io (CLI)

```bash
brew install flyctl
fly auth login
fly launch --copy-config --no-deploy            # uses fly.toml
fly secrets set ANTHROPIC_API_KEY=sk-ant-... ACCESS_PASSWORD=$(openssl rand -hex 24)
fly deploy
```

### Anywhere else (raw Docker)

```bash
docker build -t leanlead .
docker run -p 8000:8000 \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -e ACCESS_PASSWORD=$(openssl rand -hex 24) \
  leanlead
```

### Important — `ACCESS_PASSWORD`

If you leave `ACCESS_PASSWORD` empty, the site is **public** and anyone
who knows the URL can spend your Anthropic credits. Always set a strong
password before exposing the URL.

### Important — pick the right plan size

The hardest constraint is **RAM**. Whisper + torch hold the model in memory:

| Whisper model | RAM you need | Notes |
|---|---|---|
| `tiny` (default) | ~1 GB total | Default in `.env.example`. Fast, OK quality for clear speech. |
| `base` | ~1.5 GB total | Better punctuation. Set `WHISPER_MODEL=base`. |
| `small` | ~3 GB total | Multilingual robustness. |
| `medium` | ~6 GB total | Best ROI for accuracy. Won't fit on Railway Trial. |

The slim Docker image itself fits in ~1 GB resident; the rest is the
loaded Whisper model + the working buffers during inference.

Recommended starting plans:

- **Railway Hobby ($5/mo)** — 8 GB RAM, 8 vCPU. Comfortably runs `base`
  or `small`.
- **Railway Trial / Free** — limited; default to `tiny`.
- **Render Starter** — 512 MB RAM, won't fit anything beyond `tiny` and
  even then is tight; bump to Standard for `base+`.
- **Fly.io shared-cpu-1x@2gb** — runs `tiny` / `base`. Bump to 4–8 GB for
  larger models.

**If you see `502 Bad Gateway` mid-job** the container OOM'd. Either
bump your plan's RAM, or downgrade `WHISPER_MODEL` to `tiny`.

### Important — persistent storage (mount a Volume)

The container's filesystem is **ephemeral** on every cloud platform
listed above. Without a persistent disk mount, every deploy or crash
wipes uploads + the job log, and any in-flight render is lost.

The app stores everything that needs to survive at
`/app/backend/storage` (uploads, intermediate clips, finished mp4s,
the job log `jobs.json`). Mount a persistent disk there.

- **Railway**: project → service → **Settings → Volumes →
  + Add Volume**. Mount path: `/app/backend/storage`. Pick the smallest
  size that fits your largest expected video (e.g. 5 GB for short-form,
  50 GB if you handle hours of long form).
- **Render**: blueprint → service → **Disks → Add Disk**. Mount path
  `/app/backend/storage`, size to taste.
- **Fly**: `fly volumes create leanlead_storage --size 10` and add to
  `fly.toml`:

  ```toml
  [[mounts]]
    source = "leanlead_storage"
    destination = "/app/backend/storage"
  ```

Without a Volume the app still runs, but every redeploy turns active
jobs into a "Server restarted — please re-upload" error.

## Roadmap

- [ ] **Multi-take support** — accept multiple raw clips, transcribe in
      parallel, let the agent pick the best take of each beat. Adopt
      video-use's EDL JSON format at that point.
- [ ] **HTML B-roll renderer** — instantiate HyperFrames compositions with
      the user's brand palette and overlay them on the timeline (see
      `docs/INTEGRATIONS.md`).
- [ ] Replace in-memory job store with Redis (multi-worker safe).
- [ ] Auto-export 9:16, 1:1, 16:9 versions in one run.
- [ ] Voice-intensity detection for silence-before-impact placement.
- [ ] User accounts + per-user style presets (the SaaS layer).

See **[`docs/INTEGRATIONS.md`](./docs/INTEGRATIONS.md)** for what we
borrowed from `browser-use/video-use` and how `heygen-com/hyperframes`
fits into the roadmap.

## License

Private — internal build.
