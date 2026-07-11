"""
B-roll semantic type registry.

Each BRollType describes a detectable semantic concept and provides two
render callables:

  render_html(params, pack, card_id) -> str
      Returns the inner HTML for the card (.card, .root, .card-panel structure).
      compose.py's _build_graphic_card_html() calls this instead of its own
      content-style switch.

  render_gsap(params, pack, card_id, start, end) -> list[str]
      Returns GSAP timeline lines (strings) targeting elements by ID.
      compose.py's _build_timeline_js() inserts these after standard card
      entry animations (visibility + host fade-in + pack panel entry).

Auto-discovery: every module in app.engine.broll_types/ is imported at
startup via pkgutil.iter_modules. Adding a new type requires only one file
in that package ending with register(BRollType(...)). Zero other changes.
"""
from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class BRollType:
    name: str
    patterns: list                 # list[re.Pattern] — scanned over flat word text
    extractor: Callable            # (match, words, word_start_idx) -> (params: dict, confidence: float)
    render_html: Callable          # (params, pack, card_id) -> str
    render_gsap: Callable          # (params, pack, card_id, start, end) -> list[str]
    default_duration: float = 5.0
    preferred_zone: str = "upper-data"
    min_confidence: float = 0.75


REGISTRY: dict[str, BRollType] = {}


def register(t: BRollType) -> None:
    REGISTRY[t.name] = t
    print(f"[BROLL-REGISTRY] registered {t.name!r}", flush=True)


def _autodiscover() -> None:
    """Import every module in app.engine.broll_types so register() calls fire."""
    try:
        from app.engine import broll_types as _pkg
        for _finder, _name, _ispkg in pkgutil.iter_modules(_pkg.__path__):
            if _name.startswith("_"):
                continue
            try:
                importlib.import_module(f"app.engine.broll_types.{_name}")
            except Exception as _e:
                print(
                    f"[BROLL-REGISTRY] failed to load broll_types.{_name}: {_e}",
                    flush=True,
                )
    except Exception as _e:
        print(f"[BROLL-REGISTRY] autodiscover error: {_e}", flush=True)


_autodiscover()
