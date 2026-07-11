"""
Deterministic semantic scanner for B-roll triggers.

Scans remapped_words (already on the output timeline) for patterns
registered in broll_registry. Returns SemanticHit list sorted by start_sec.

This module is intentionally independent of LLM calls and storyboard logic.
It reads words, matches patterns, calls extractors, and returns hits.
Merging with LLM graphic cards happens in storyboard.py via _merge_cards().
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SemanticHit:
    broll_type: str
    start_sec: float       # when the trigger word begins (output timeline)
    end_sec: float         # raw word end time (before card duration is added)
    params: dict
    confidence: float
    text_span: str = ""    # matched text, for logging


def scan_words(words: list) -> list[SemanticHit]:
    """Scan remapped_words for registered semantic B-roll patterns.

    Returns only hits whose confidence >= the type's min_confidence.

    words: list of WordTiming (or any objects with .text, .start, .end attributes).
    """
    from app.engine import broll_registry as _reg

    if not words or not _reg.REGISTRY:
        return []

    # Build flat text + character-to-word-index map.
    # Words joined by single space so patterns can span word boundaries.
    parts: list[str] = []
    char_to_word: list[int] = []

    for i, w in enumerate(words):
        wt = getattr(w, "text", str(w)).strip()
        if not wt:
            continue
        if parts:
            char_to_word.append(i)   # space char → associated with next word
            parts.append(" ")
        for _ in wt:
            char_to_word.append(i)
        parts.append(wt)

    full_text = "".join(parts)
    n_chars = len(char_to_word)

    hits: list[SemanticHit] = []
    seen_spans: set[tuple[int, int]] = set()  # deduplicate by char span

    for btype in _reg.REGISTRY.values():
        for pattern in btype.patterns:
            for match in pattern.finditer(full_text):
                ms = match.start()
                me = max(match.start(), match.end() - 1)
                span_key = (ms, me)
                if span_key in seen_spans:
                    continue
                seen_spans.add(span_key)

                w_start_idx = char_to_word[ms] if ms < n_chars else len(words) - 1
                w_end_idx   = char_to_word[me] if me < n_chars else len(words) - 1

                w_s = words[w_start_idx]
                w_e = words[w_end_idx]
                start_sec = float(getattr(w_s, "start", 0.0))
                end_sec   = float(getattr(w_e, "end",   start_sec + 0.3))

                try:
                    params, confidence = btype.extractor(match, words, w_start_idx)
                except Exception as exc:
                    print(
                        f"[BROLL-SCANNER] extractor error {btype.name}: {exc}",
                        flush=True,
                    )
                    continue

                if confidence < btype.min_confidence:
                    print(
                        f"[BROLL-SCANNER] skip {btype.name} at {start_sec:.2f}s"
                        f" — conf={confidence:.2f} < min={btype.min_confidence:.2f}"
                        f" ('{match.group()}')",
                        flush=True,
                    )
                    continue

                hits.append(SemanticHit(
                    broll_type=btype.name,
                    start_sec=start_sec,
                    end_sec=end_sec,
                    params=params,
                    confidence=confidence,
                    text_span=match.group(),
                ))

    hits.sort(key=lambda h: h.start_sec)
    print(
        f"[BROLL-SCANNER] {len(hits)} hit(s) from {len(words)} words",
        flush=True,
    )
    return hits
