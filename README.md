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

## Roadmap

- [ ] Replace in-memory job store with Redis (multi-worker safe).
- [ ] Real B-roll fetcher (Pexels / Storyblocks API).
- [ ] Auto-export 9:16, 1:1, 16:9 versions in one run.
- [ ] Voice-intensity detection for silence-before-impact placement.
- [ ] User accounts + per-user style presets (the SaaS layer).

## License

Private — internal build.
