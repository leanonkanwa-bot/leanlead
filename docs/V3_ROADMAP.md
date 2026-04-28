# V3 Roadmap — what's deliberately deferred

The user spec for v0.3 covers a much larger surface than what's
in the running product today. We shipped what fits without breaking
the OOM constraint on Railway Trial. This document is the honest list
of what's NOT in v0.2 and why, plus how each one would land.

## v0.3 ships (today)

- **PIL motion graphics renderer.** Three of the user-spec graphics now
  render as RGBA PNGs and composite onto the timeline via FFmpeg
  filter_complex with slide-in animation:
  - **Lower Third Title** — white title + accent-coloured second line,
    slides in from the left over 0.3s with smoothstep easing. Match for
    the "Building Your / Content Machine" reference.
  - **Stat Circle** — blue donut chart with bold "<N>%" in the centre +
    a sub-label below. Match for the "80% of your time" reference.
  - **Checklist Reveal** — stacked rounded pill buttons, red ✗ or green
    ✓ icons, white labels. Match for the "Not a Demo / Not Theory /
    Real Automations" reference.
- Agent prompt rewritten so it actively schedules these three graphics
  on the right beats (lower_third on every section transition,
  stat_circle on every spoken statistic, checklist on every wrong-vs-
  right contrast).
- The renderer keeps planning (but doesn't yet draw) `split`, `quote`,
  `highlight`, `flow`. They surface in the JSON output as a brief.

## v0.2 ships

- Smoothstep-eased zoom (no shake) with center-locked anchor.
- B-roll duration clamped to [2.5s, 4s] in the renderer + the agent
  prompt explicitly told to match b-roll to spoken context, not
  random intervals.
- Caption sizes bumped to 9% (standard) / 12% (emphasis) of video
  height.
- 10 fonts available (Poppins Bold/ExtraBold/SemiBold, Montserrat
  Bold/Black, Inter Bold, Roboto Bold, Bebas Neue, DM Sans Bold,
  Space Grotesk Bold).
- 5 caption colors (white, electric yellow, clean red, electric blue,
  orange flash).
- 4 caption positions (center, bottom, side-left, side-right).
- 2 caption styles: `impact` (default) and `kinetic` (dark bar).
- 3 color theme presets in the UI (Dark Pro / High Energy / Faith &
  Gold) — drives caption color suggestions; the agent reads
  brand_color so motion graphics match.
- Hyperframes (full-screen flash cards every 20–30s).
- Output contract emits `optimized_script`, `key_lines`,
  `motion_graphics`, `hyperframes`, `zoom_plan` with `on_word`,
  `silences_to_protect`.

## Deferred to v0.3 — explicit rationale

### 1. Face position movement system (LEFT / RIGHT / BOTTOM / CENTER panels)

**What was asked:** dynamically move the talking head around the
screen — center full, left panel, right panel, bottom-left, bottom-
center — and have the agent change position every section transition.

**Why deferred:** This needs face/body detection on every frame so the
renderer knows where to crop+translate the speaker. Two options exist:

- **Mediapipe / OpenCV + Haar cascade**: ~250 MB additional Python
  deps + native libs. Doubles our image size and pushes RAM usage
  past Railway Trial's ceiling. Not viable on the current plan.
- **Subject detection via Claude Vision on sampled keyframes**: pass
  5–10 keyframes plus the structure beats to Claude, ask "where is the
  speaker in each beat — center, left third, right third?" Cheap
  (~$0.05/video), no extra deps. **This is the right path** but
  requires a new code path in `planner.py` for image inputs and a new
  filter graph (per-segment crop+translate) in `render.py`.

**To ship this:** add `face_position_plan` to the agent output, where
each entry is `{at, end, position: "center|left|right|bottom_left|bottom_center"}`.
Renderer applies a `crop` filter with x/y expressions that follow the
plan. Estimate: 2–3 days of focused work after the platform RAM is
sorted.

### 2. Photo input system

**What was asked:** user uploads photos with text labels; agent reads
transcript and places each photo where the spoken content semantically
matches the label.

**Why deferred:** It's a real feature that deserves its own iteration:

- **Storage**: photos go to `storage/photos/{job_id}/...`, mounted
  Volume required.
- **Matching**: take the photo's label, ask Claude (with the
  transcript) which sentence start it should land on. New step in
  `planner.py`.
- **Rendering**: 3 placement modes (full-screen, side panel, overlay
  card) require new filter graphs.
- **UI**: drag-and-drop zone with per-photo label input, preview of
  where each photo will land.

**To ship this:** budget 4–5 days. Best done after face position so
the placement logic shares helpers.

### 3. Rich motion graphics renderer (partial in v0.3)

**Now shipped:** Lower Third Title, Stat Circle, Checklist Reveal.

**Still deferred (v0.3.1):**

- **Split Comparison** — left half red-tinted "wrong way" / right half
  green-tinted "right way". Two PIL renders + ffmpeg `xfade=hslice` or
  two overlays positioned 0–w/2 and w/2–w. ~1 day.
- **Flow Diagram** — connected icon nodes with curved drawn lines (the
  starburst → document → 3 play icons reference). FFmpeg can't draw
  curves easily; needs PIL Bezier strokes + arrow rendering. ~1 day.
- **Arrow Callout** — curved white arrow + label. Same constraint as
  Flow. ~0.5 day.
- **Stat Circle count-up animation** — currently shows the final
  percent immediately. Animating 0→N requires either a PNG sequence
  or a programmatic ffmpeg `geq` arc, both ~0.5 day.

**Approach:** stay on PIL — the headless-Chromium path is still too
heavy. Each graphic is one Python function returning a PNG (or PNG
sequence for animated ones).

### 4. Caption styles 2 (Split Float) and 3 (Full Screen Word)

**What was asked:**
- Split Float: words appear simultaneously on left and right of the
  speaker, like conversation around them.
- Full Screen Word: single word slams into center over a flat color
  flash, 25% video height, holds for the spoken duration.

**Why deferred:**
- Split Float requires multiple simultaneous Dialogue events with
  alternating Alignment. Doable in pure ASS — it's real work but not
  blocked by anything.
- Full Screen Word is essentially a hyperframe held for a full word
  duration. The hyperframe primitive already covers the visuals; we
  just need a code path that promotes a word + its emphasis to a
  hyperframe. **Half a day of work.**

**To ship these:** call it 1.5 days for both.

### 5. Multi-take support + b-roll auto-fetch

Same shape as v0.1's roadmap — see `INTEGRATIONS.md`. Multi-take
needs the EDL JSON format from `browser-use/video-use`; b-roll
auto-fetch needs Pexels/Storyblocks API keys + a fetch step in the
pipeline.

## Order of operations for v0.3

If we get more RAM (Railway Hobby or migration to Fly with a real
machine), the priority order is:

1. **Face position plan** (small but high visual impact; sample
   keyframes via Claude Vision).
2. **Full-screen word caption style** (cheap reuse of hyperframe
   primitive, big readability win on Principle/Payoff lines).
3. **Photo input system** (makes the editor genuinely usable for
   real talking-head storytelling).
4. **Rich motion graphics renderer** (PIL path — 1 graphic type per
   day for a week).
5. **Multi-take + b-roll auto-fetch** (the long tail).
