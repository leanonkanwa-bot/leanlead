# Integrations — what we borrowed and what comes next

## browser-use/video-use

**Repo:** https://github.com/browser-use/video-use

A Claude Code "skill" that edits videos by conversation. It is the closest
prior art to what we are building, and its **production-correctness rules**
are battle-tested. We integrated the gold:

| What we took | Where it landed |
|---|---|
| Hard Rules (cut on word boundary, pad 30–200ms, 30ms audio fades, subtitles last, etc.) | `backend/app/agent/rules.py` (`HARD_RULES` block) |
| Per-segment extract → lossless `-c copy` concat → single re-encode for filters | `backend/app/engine/render.py` |
| 30ms `afade=t=in/out` at every segment boundary | `backend/app/engine/render.py:_cut_segment` |
| Word-boundary snapping for cut edges | `backend/app/engine/render.py:_snap_to_word_boundary` |
| Pad-the-edges convention (50ms short, 150ms long) | `backend/app/engine/render.py` constants |
| "Audio is primary, visuals follow" philosophy | reflected in agent prompt |

What we did NOT take (different scope):

- Their **EDL JSON format** is multi-source and rich. Our v1 takes ONE source
  per job, so we use a slimmer `EditPlan` JSON. We can adopt their EDL shape
  the day we do multi-take editing.
- **ElevenLabs Scribe** transcription. We use Whisper because we want
  no-extra-API-key local-first. Scribe is faster and better-normalized;
  swap is a future option.
- The **packed-transcript markdown** view (`takes_packed.md`). Useful when
  the LLM has many takes to read; overkill for one-take v1.
- **Manim** integration for diagrams and **Remotion** for branded
  typography. These belong in our future "B-roll generator".

## heygen-com/hyperframes

**Repo:** https://github.com/heygen-com/hyperframes

HyperFrames treats HTML+CSS+GSAP as the source of truth for a video. You
write a composition like a webpage and the framework renders it into mp4
with audio sync, transcribed captions, audio-reactive visuals, and shader
transitions.

We did NOT vendor any code from it — it's a TypeScript/web stack that does
not match our Python/FFmpeg backend. **But the role it plays in our
roadmap is concrete:**

> **Phase 2 — Animated B-roll & lower-thirds, on demand.**
>
> When the agent decides "drop a B-roll concept card here", instead of
> pulling generic stock footage we will spin up a HyperFrames composition
> from a template (palette + font from the user's brand), render it
> headless, and overlay it on the timeline. That gives us:
>
> - Brand-coherent overlays (palette, typography pulled from the user's
>   DESIGN.md if they have one).
> - Audio-reactive accents (beat-sync glow, pulse on emphasis words).
> - Caption cards / lower-thirds / number reveals without paying a stock
>   library.
> - GSAP timing primitives that map cleanly onto our `broll_suggestions`
>   schema (`{at, duration, concept}`).

Their `skills/hyperframes/SKILL.md` and `house-style.md` are also good
reading for animation design defaults (cubic easing, hero-frame-first
layout, no parallel reveals of independent elements). Those rules will
inform our overlay generator when we build it.

## Roadmap implication

Today's pipeline (one source → cut → zoom → captions) is solid for the
talking-head short/long form workflow. The next two things to add, both
informed by the above, are:

1. **Multi-take support** — accept multiple uploads, transcribe each,
   build a `takes_packed.md`-style view for the planner, let it pick the
   best take of each beat. Adopt video-use's EDL format at that point.
2. **HTML B-roll renderer** — a worker that takes a `broll_suggestion`,
   instantiates a HyperFrames composition with the user's brand palette,
   renders it, and the editor overlays it at the requested timestamp.
