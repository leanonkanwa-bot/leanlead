#!/usr/bin/env python3
"""
Segment-boundary clamp test suite.

Validates _apply_segment_clamp — the hard deterministic floor applied AFTER all
anchoring passes (title-anchor, trigger-anchor, grounding guard).

Key invariants:
  A. Card before any speech → clamped to first segment start
  B. Card in silence gap between two segments → clamped to NEXT segment start
  C. Card inside a speech segment → NOT clamped (already within speech)
  D. Card after all speech → NOT clamped
  E. Paraphrase edge case: title-anchor can't fire (zero word overlap), but card is
     in pre-speech silence → segment clamp still prevents early appearance
  F. Already-correct card (startSec == segment start) → NOT moved (floor == startSec,
     floor > startSec is False)
  G. endSec extended when it would be < startSec + 1.5s after clamp
  H. No-segments edge case (empty list) → nothing crashes, nothing clamped

Run:  python -X utf8 backend/test_segment_clamp.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app.engine.storyboard import _apply_segment_clamp

ok = 0
fail = 0


def check(label: str, got, expected, *, approx: bool = False, tol: float = 0.005):
    global ok, fail
    passed = (abs(got - expected) <= tol) if approx else (got == expected)
    if passed:
        ok += 1
        print(f"  [OK  ] {label}  → {got!r}")
    else:
        fail += 1
        print(f"  [FAIL] {label}")
        print(f"         expected={expected!r}  got={got!r}")


def gc(card_id: str, start: float, end: float, title: str = "") -> dict:
    return {
        "id": card_id,
        "startSec": start,
        "endSec": end,
        "contentHints": {"style": "key_phrase", "title": title},
    }


print(f"\n{'='*68}")
print("  Segment-boundary clamp — deterministic floor tests")
print(f"{'='*68}\n")

# Speech segments used in most tests:
#   Segment 0: [3.0, 8.0]   (first speech)
#   Segment 1: [10.0, 15.0] (second speech)
#   Segment 2: [18.0, 25.0] (third speech)
SEG_OUT = [(3.0, 8.0), (10.0, 15.0), (18.0, 25.0)]

# ── A. Card before all speech ─────────────────────────────────────────────────
print("A. Card placed before first speech segment (t=1.5s, first segment at 3.0s)")
card_a = gc("c-A", start=1.5, end=4.5)
n = _apply_segment_clamp([card_a], SEG_OUT)
check("A. clamp fires (count=1)", n, 1)
check("A. startSec clamped to 3.0", card_a["startSec"], 3.0)
check("A. endSec unchanged (4.5 == startSec+1.5, guard uses <)", card_a["endSec"], 4.5)

# ── B. Card in silence gap between segment 0 and 1 ───────────────────────────
print("\nB. Card in silence gap between segments (t=9.0s, gap [8.0, 10.0])")
card_b = gc("c-B", start=9.0, end=12.0)
n = _apply_segment_clamp([card_b], SEG_OUT)
check("B. clamp fires (count=1)", n, 1)
check("B. startSec clamped to start of next segment = 10.0", card_b["startSec"], 10.0)
check("B. endSec kept (was 12.0, still ≥ startSec+1.5)", card_b["endSec"], 12.0)

# ── C. Card inside speech segment → NOT clamped ──────────────────────────────
print("\nC. Card inside segment [3.0, 8.0] at t=5.5s")
card_c = gc("c-C", start=5.5, end=8.5)
n = _apply_segment_clamp([card_c], SEG_OUT)
check("C. no clamp (count=0)", n, 0)
check("C. startSec unchanged", card_c["startSec"], 5.5)

# ── D. Card after all speech → NOT clamped ───────────────────────────────────
print("\nD. Card after all speech (t=27.0s, last segment ends at 25.0s)")
card_d = gc("c-D", start=27.0, end=30.0)
n = _apply_segment_clamp([card_d], SEG_OUT)
check("D. no clamp (count=0)", n, 0)
check("D. startSec unchanged", card_d["startSec"], 27.0)

# ── E. Paraphrase edge case — title-anchor would find nothing ─────────────────
# Simulates: card title "Habitudes du matin" is a full paraphrase of speech
# "Je commence ma journée à 6h du matin" — no word overlap with nearby Whisper
# words, so title-anchor returns nothing.  But card is in pre-speech silence
# (startSec=0.8s), so segment clamp still fires and protects against early display.
print("\nE. Paraphrase edge case: card at t=0.8s (pre-speech), title has zero word overlap")
print("   (title-anchor simulation: no match → card stays at LLM's 0.8s → clamp fires)")
card_e = gc("c-E", start=0.8, end=3.8, title="Habitudes du matin")
# Simulate title-anchor finding NO match (nothing to do — card_e.startSec stays at 0.8s)
# Now apply the segment clamp:
n = _apply_segment_clamp([card_e], SEG_OUT)
check("E. clamp fires even with paraphrased title (count=1)", n, 1)
check("E. startSec clamped to first segment start = 3.0", card_e["startSec"], 3.0)

# ── F. Card exactly at segment boundary → NOT moved ──────────────────────────
print("\nF. Card exactly at segment start (t=3.0s == seg[0] start)")
card_f = gc("c-F", start=3.0, end=6.0)
n = _apply_segment_clamp([card_f], SEG_OUT)
check("F. no clamp (floor == startSec, not strictly greater)", n, 0)
check("F. startSec unchanged", card_f["startSec"], 3.0)

# ── G. endSec extended when short after clamp ─────────────────────────────────
print("\nG. endSec too short after clamp → extended to startSec+3.0")
card_g = gc("c-G", start=0.5, end=2.0)   # endSec=2.0, after clamp startSec=3.0
n = _apply_segment_clamp([card_g], SEG_OUT)
check("G. clamp fires", n, 1)
check("G. startSec = 3.0", card_g["startSec"], 3.0)
check("G. endSec extended to 6.0 (3.0+3.0)", card_g["endSec"], 6.0)

# ── H. No segments → nothing clamped, no crash ───────────────────────────────
print("\nH. Empty segment list → no crash, nothing moved")
card_h = gc("c-H", start=1.0, end=4.0)
n = _apply_segment_clamp([card_h], [])
check("H. no clamp (count=0)", n, 0)
check("H. startSec unchanged", card_h["startSec"], 1.0)

# ── Multi-card: only out-of-segment cards clamped ─────────────────────────────
print("\nI. Multi-card: cards at t=0.5s, t=5.0s, t=9.5s, t=22.0s, t=30.0s")
cards_i = [
    gc("i-pre",   start=0.5,  end=3.5),   # before speech → clamp to 3.0
    gc("i-in0",   start=5.0,  end=8.0),   # inside seg[0] → no clamp
    gc("i-gap01", start=9.5,  end=12.5),  # gap [8,10] → clamp to 10.0
    gc("i-in2",   start=22.0, end=25.0),  # inside seg[2] → no clamp
    gc("i-post",  start=30.0, end=33.0),  # after speech → no clamp
]
n = _apply_segment_clamp(cards_i, SEG_OUT)
check("I. 2 cards clamped", n, 2)
check("I. i-pre → 3.0", cards_i[0]["startSec"], 3.0)
check("I. i-in0 unchanged → 5.0", cards_i[1]["startSec"], 5.0)
check("I. i-gap01 → 10.0", cards_i[2]["startSec"], 10.0)
check("I. i-in2 unchanged → 22.0", cards_i[3]["startSec"], 22.0)
check("I. i-post unchanged → 30.0", cards_i[4]["startSec"], 30.0)

# ── Summary ───────────────────────────────────────────────────────────────────
total = ok + fail
print(f"\n{'='*68}")
print(f"  RESULTS: {ok}/{total} passed", "✓" if fail == 0 else f"— {fail} FAILED")
print(f"{'='*68}\n")
sys.exit(0 if fail == 0 else 1)
