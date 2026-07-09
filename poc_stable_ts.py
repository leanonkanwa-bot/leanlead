# REFERENCE_FILE = "4d9673bf66de428a9f258b978ed2d526.mp4" — le seul juge
"""POC: compare faster-whisper vs stable-ts word timestamps on the reference file.

Focus tokens:
  - 'retiens' (le 're-' attendu à 27.52-27.84, Whisper dit silence)
  - 'il' fusionné (durée ~1.06s sans silence détectable)
  - 'il faut il faut' sequence

Usage:
    pip install stable-ts
    python poc_stable_ts.py [path/to/video.mp4]

Requires faster-whisper >= 1.0 (compatible with stable-ts 2.x).
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

REFERENCE = Path(r"C:\Users\KANWAGI\Downloads\4d9673bf66de428a9f258b978ed2d526.mp4")
VIDEO = Path(sys.argv[1]) if len(sys.argv) > 1 else REFERENCE

MODEL_SIZE = "tiny"          # swap to "large-v3" on Railway; tiny is fast locally
TARGET_TOKENS = {"retiens", "il", "faut"}  # tokens to highlight in the diff table

# ── helpers ──────────────────────────────────────────────────────────────────

def _strip(t: str) -> str:
    return re.sub(r"\W", "", t).lower()

def _extract_wav(video: Path) -> Path:
    import subprocess, shutil
    ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
    wav = video.with_suffix(".tmp_16k.wav")
    subprocess.run(
        [ffmpeg, "-y", "-loglevel", "error", "-i", str(video),
         "-vn", "-ac", "1", "-ar", "16000", str(wav)],
        check=True,
    )
    return wav

def _run_faster_whisper(wav: Path):
    from faster_whisper import WhisperModel
    m = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    segs, _ = m.transcribe(
        str(wav),
        word_timestamps=True,
        beam_size=5,
        best_of=5,
        temperature=[0.0, 0.2, 0.4],
        condition_on_previous_text=False,
        suppress_tokens=[],
        initial_prompt="Euh, bah, ben, hein, ouais, hm, enfin voilà. Je je pense, il il faut, parce que parce que, c'est c'est.",
        no_speech_threshold=0.6,
        compression_ratio_threshold=2.4,
        language=None,
        vad_filter=False,
    )
    words = []
    for seg in segs:
        for w in (seg.words or []):
            if w.start is None or w.end is None:
                continue
            text = (w.word or "").strip()
            if text:
                words.append({"text": text, "start": round(w.start, 3), "end": round(w.end, 3)})
    return words

def _run_stable_ts(wav: Path):
    try:
        import stable_whisper
    except ImportError:
        print("stable-ts not installed — run: pip install stable-ts")
        return None
    m = stable_whisper.load_faster_whisper(MODEL_SIZE, device="cpu", compute_type="int8")
    result = m.transcribe(
        str(wav),
        word_timestamps=True,
        beam_size=5,
        best_of=5,
        temperature=[0.0, 0.2, 0.4],
        condition_on_previous_text=False,
        suppress_tokens=[],
        initial_prompt="Euh, bah, ben, hein, ouais, hm, enfin voilà. Je je pense, il il faut, parce que parce que, c'est c'est.",
        no_speech_threshold=0.6,
        compression_ratio_threshold=2.4,
        language=None,
        vad_filter=False,
    )
    words = []
    for seg in result.segments:
        for w in (getattr(seg, "words", None) or []):
            text = getattr(w, "word", "") or ""
            text = text.strip()
            if text:
                words.append({
                    "text": text,
                    "start": round(float(w.start), 3),
                    "end": round(float(w.end), 3),
                })
    return words

def _print_table(fw_words, st_words, label: str):
    """Print side-by-side comparison for tokens that appear in TARGET_TOKENS."""
    print(f"\n{'='*70}")
    print(f"  {label}")
    print(f"{'='*70}")
    print(f"{'#':<4} {'token':<14} {'faster-whisper':>20}   {'stable-ts':>20}")
    print(f"{'-'*70}")

    # Align by token text (zip if equal length, else best-effort)
    max_len = max(len(fw_words), len(st_words) if st_words else 0)
    st_map = {i: w for i, w in enumerate(st_words or [])}

    for i, fw in enumerate(fw_words):
        st = st_map.get(i, {})
        tok = fw["text"]
        norm = _strip(tok)
        if norm not in TARGET_TOKENS:
            continue
        fw_str = f"{fw['start']:.3f}-{fw['end']:.3f}s ({fw['end']-fw['start']:.3f}s)"
        if st:
            st_str = f"{st['start']:.3f}-{st['end']:.3f}s ({st['end']-st['start']:.3f}s)"
            delta_s = st['start'] - fw['start']
            delta_e = st['end'] - fw['end']
            diff = f"Δstart={delta_s:+.3f} Δend={delta_e:+.3f}"
        else:
            st_str = "(no match)"
            diff = ""
        print(f"[{i:>2}] {tok:<14} {fw_str:>22}   {st_str:>22}  {diff}")

    print()

def _print_context_window(words, label: str, center_tok: str, window: float = 3.0):
    """Print all words in a time window around a target token."""
    center_words = [w for w in words if _strip(w["text"]) == center_tok]
    if not center_words:
        print(f"  [{label}] token '{center_tok}' not found")
        return
    for cw in center_words:
        t0, t1 = cw["start"] - window, cw["end"] + window
        nearby = [w for w in words if w["start"] >= t0 and w["end"] <= t1]
        print(f"\n  [{label}] context around '{center_tok}' ({cw['start']:.3f}-{cw['end']:.3f}s):")
        for w in nearby:
            marker = " ◄" if _strip(w["text"]) == center_tok else ""
            dur = w["end"] - w["start"]
            print(f"    {w['start']:7.3f}-{w['end']:7.3f}s  ({dur:.3f}s)  {w['text']!r}{marker}")

# ── main ─────────────────────────────────────────────────────────────────────

print(f"Video: {VIDEO}")
print(f"Extracting 16kHz WAV…")
wav = _extract_wav(VIDEO)

print(f"Running faster-whisper/{MODEL_SIZE}…")
fw = _run_faster_whisper(wav)
print(f"  → {len(fw)} words")

print(f"Running stable-ts/{MODEL_SIZE}…")
st = _run_stable_ts(wav)
if st is not None:
    print(f"  → {len(st)} words")

wav.unlink(missing_ok=True)

# ── Context windows for the three problem tokens ──
for backend, wlist in [("faster-whisper", fw), ("stable-ts", st or [])]:
    print(f"\n{'─'*70}")
    print(f"BACKEND: {backend}")
    _print_context_window(wlist, backend, "retiens", window=2.0)
    _print_context_window(wlist, backend, "il",      window=1.5)

# ── Side-by-side table for all target tokens ──
_print_table(fw, st, "SIDE-BY-SIDE: faster-whisper vs stable-ts (target tokens only)")

# ── Sequence 'il faut il faut' ──
print("\n── Sequence 'il faut il faut' ──────────────────────────────────────────")
for backend, wlist in [("faster-whisper", fw), ("stable-ts", st or [])]:
    print(f"\n[{backend}]")
    for i, w in enumerate(wlist):
        if _strip(w["text"]) in {"il", "faut"}:
            dur = w["end"] - w["start"]
            print(f"  [{i:>2}] {w['start']:7.3f}-{w['end']:7.3f}s ({dur:.3f}s)  {w['text']!r}")

print("\nDone.")
