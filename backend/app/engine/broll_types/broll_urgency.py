"""
urgency_clock — compact countdown display for remaining-time urgency expressions.

Matches phrases that convey remaining-time urgency without duplicating
calendar_date's "dans N jours" / full-date patterns (handled by broll_temporal.py):

  Tier-1 (confidence 0.92):
    "il reste X jours/heures/semaines/minutes"
    "il vous reste X ..."
    "plus que X jours/heures"
    "seulement X jours/heures"
    "X jours/heures restants/restantes"

  Tier-2 English equivalents (confidence 0.88):
    "only X days/hours/weeks left"
    "X days/hours remaining"
    "just X days left"

Visual: "IL RESTE" label → large accent number (count-up) → unit uppercase.
No SVG ring — distinct from calendar_date's countdown display.
"""
from __future__ import annotations

import re

from app.engine.broll_registry import BRollType, register


# ── Unit helpers ──────────────────────────────────────────────────────────────

_UNITS_FR = r"jours?|heures?|minutes?|semaines?|mois"
_UNITS_EN = r"days?|hours?|minutes?|weeks?|months?"
_UNITS_ALL = f"{_UNITS_FR}|{_UNITS_EN}"


def _norm_unit(raw: str) -> tuple[str, str]:
    """(unit_key, display_uppercase) from raw matched unit string."""
    u = raw.lower()
    if u.startswith("heure") or u.startswith("hour"):
        return "heure", "HEURES"
    if u.startswith("minute") or u.startswith("minut"):
        return "minute", "MINUTES"
    if u.startswith("semaine") or u.startswith("week"):
        return "semaine", "SEMAINES"
    if u in ("mois", "month", "months"):
        return "mois", "MOIS"
    return "jour", "JOURS"


# ── Patterns ──────────────────────────────────────────────────────────────────

# "il reste / il vous reste / il te reste / il m'en reste X [unité]"
_IL_RESTE = re.compile(
    r"\bil\s+(?:(?:vous|te|lui|leur|m'?en|en|nous)\s+)?reste\s+"
    r"(?P<n>\d+)\s+(?P<unit>" + _UNITS_ALL + r")\b",
    re.IGNORECASE,
)

# "plus que X [unité]" / "plus qu'X [unité]"
_PLUS_QUE = re.compile(
    r"\bplus\s+qu?[e']?\s+(?P<n>\d+)\s+(?P<unit>" + _UNITS_ALL + r")\b",
    re.IGNORECASE,
)

# "seulement X [unité]"
_SEULEMENT = re.compile(
    r"\bseulement\s+(?P<n>\d+)\s+(?P<unit>" + _UNITS_ALL + r")\b",
    re.IGNORECASE,
)

# "X [unité] restant(e)(s)"
_N_RESTANTS = re.compile(
    r"\b(?P<n>\d+)\s+(?P<unit>" + _UNITS_ALL + r")\s+restant(?:e)?s?\b",
    re.IGNORECASE,
)

# English: "only X days left" / "just X hours remaining"
_ONLY_N = re.compile(
    r"\b(?:only|just)\s+(?P<n>\d+)\s+(?P<unit>" + _UNITS_EN + r")"
    r"(?:\s+(?:left|remaining|to\s+go))?\b",
    re.IGNORECASE,
)

# "X days/hours left / remaining"
_N_LEFT = re.compile(
    r"\b(?P<n>\d+)\s+(?P<unit>" + _UNITS_EN + r")\s+(?:left|remaining)\b",
    re.IGNORECASE,
)

_ALL_PATTERNS = [_IL_RESTE, _PLUS_QUE, _SEULEMENT, _N_RESTANTS, _ONLY_N, _N_LEFT]

# Negative context: "après" / time-ago expressions should not trigger urgency
_NEGATIVE_CTX = re.compile(
    r"\b(après\s+(?:la|le|les|cette|cet)|since|ago|auparavant|"
    r"il\s+y\s+a\s+\d+|there\s+were|there\s+have\s+been)\b",
    re.IGNORECASE,
)


def _ctx_words(words: list, word_idx: int, radius: int = 5) -> str:
    n = len(words)
    return " ".join(
        getattr(words[i], "text", "")
        for i in range(max(0, word_idx - radius), min(n, word_idx + radius + 1))
    )


# ── Extractor ─────────────────────────────────────────────────────────────────

def _extractor(match, words, word_idx: int) -> tuple[dict, float]:
    gd = match.groupdict()
    n_raw  = gd.get("n")
    unit_raw = gd.get("unit", "jours")

    if n_raw is None:
        return {}, 0.0

    n = int(n_raw)
    if n <= 0 or n > 3650:          # sanity: 0-3650 (10 years) range
        return {}, 0.0

    ctx = _ctx_words(words, word_idx, 5)
    if _NEGATIVE_CTX.search(ctx):
        return {}, 0.0

    unit_key, unit_display = _norm_unit(unit_raw)

    # Higher confidence for French tier-1 patterns
    conf = 0.88 if match.re in (_ONLY_N, _N_LEFT) else 0.92

    return {
        "n": n,
        "unit": unit_key,
        "unit_display": unit_display,
    }, conf


# ── HTML / CSS helpers ────────────────────────────────────────────────────────

def _e(s: str) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _ej(s: str) -> str:
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")


def _render_html(params: dict, pack: dict, card_id: str) -> str:
    p   = pack or {}
    bg      = p.get("bg", "#1a1a1a")
    text_c  = p.get("text", "#f1f1f1")
    text_s  = p.get("text_secondary", "rgba(255,255,255,0.45)")
    accent  = p.get("accent", "#4cc9f0")
    font    = p.get("font", '"Inter", sans-serif')
    fw      = p.get("font_weight", "800")
    radius  = p.get("radius", "20px")
    shadow  = p.get("shadow", "0 8px 32px rgba(0,0,0,0.4)")
    shadow_i = p.get("shadow_inset", "")
    shadow_v = f"{shadow}, {shadow_i}" if shadow_i else shadow
    glow    = p.get("title_glow_intense", "")

    n            = params.get("n", 0)
    unit_display = _e(params.get("unit_display", "JOURS"))

    css = f"""\
.card[data-card-id="{card_id}"] .root {{
  width:100%; height:100%; display:flex; align-items:center; justify-content:center;
}}
.card[data-card-id="{card_id}"] .ur-panel {{
  background:{bg}; border-radius:{radius};
  padding:32px 48px; display:flex; flex-direction:column;
  align-items:center; gap:6px;
  box-shadow:{shadow_v}; position:relative; overflow:hidden;
}}
.card[data-card-id="{card_id}"] .ur-label {{
  font-family:{font}; font-size:14px; font-weight:700;
  color:{text_s}; letter-spacing:0.18em; text-transform:uppercase;
  opacity:0;
}}
.card[data-card-id="{card_id}"] .ur-number {{
  font-family:{font}; font-size:96px; font-weight:{fw};
  color:{accent}; font-variant-numeric:tabular-nums; line-height:1;
  opacity:0;{(" text-shadow:" + _e(glow) + ";") if glow else ""}
}}
.card[data-card-id="{card_id}"] .ur-unit {{
  font-family:{font}; font-size:26px; font-weight:700;
  color:{accent}; letter-spacing:0.14em; text-transform:uppercase;
  opacity:0;
}}
.card[data-card-id="{card_id}"] .ur-line {{
  width:0; height:3px; background:{accent}; border-radius:2px; margin-top:4px;
  {"box-shadow:" + _e(glow.replace("text-shadow:","")) + ";" if glow else ""}
}}"""

    inner = f"""\
  <div class="ur-label" id="{card_id}-ur-label">IL RESTE</div>
  <div class="ur-number" id="{card_id}-ur-n">{n}</div>
  <div class="ur-unit" id="{card_id}-ur-unit">{unit_display}</div>
  <div class="ur-line" id="{card_id}-ur-line"></div>"""

    return f"""\
<div class="card" data-card-id="{card_id}">
<style>
{css}
</style>
<div class="root">
  <div class="ur-panel">
{inner}
  </div>
</div>
</div>"""


# ── GSAP ──────────────────────────────────────────────────────────────────────

def _render_gsap(params: dict, pack: dict, card_id: str,
                 start: float, end: float) -> list[str]:
    p   = pack or {}
    cid = _ej(card_id)
    n   = params.get("n", 0)

    t_in      = round(start + 0.18, 4)
    dur_total = max(0.5, end - start)
    count_dur = round(min(1.2, max(0.45, dur_total * 0.30)), 3)

    is_ledger = p.get("id") == "lean_ledger"
    is_cinema = p.get("id") == "lean_cinema"
    is_vibe   = p.get("id") == "lean_vibe"
    is_craft  = p.get("id") == "lean_craft"

    lines: list[str] = []

    # 1. Label fades in
    lines.append(
        f"  tl.to('#{cid}-ur-label',"
        f"{{opacity:1,duration:0.25,ease:'power1.out'}},{t_in:.4f});"
    )

    # 2. Number appears then counts up
    t_num = round(t_in + 0.12, 4)
    obj   = f"_uc_{cid.replace('-','_')}"

    if is_cinema:
        # Slow fade-in, no count-up — just reveals the final number
        lines.append(
            f"  tl.to('#{cid}-ur-n',"
            f"{{opacity:1,duration:0.60,ease:'power2.in'}},{t_num:.4f});"
        )
    elif is_ledger:
        # Immediate set + linear count-up (terminal aesthetic)
        lines.append(
            f"  tl.to('#{cid}-ur-n',{{opacity:1,duration:0.10}},{t_num:.4f});"
        )
        lines.append(
            f"  (function(){{ var {obj}={{v:0}};"
            f" tl.to({obj},{{v:{n},duration:{count_dur:.3f},ease:'none',"
            f"onUpdate:function(){{var el=document.querySelector('#{cid}-ur-n');"
            f"if(el) el.textContent=Math.round({obj}.v);}}}},{t_num:.4f}); }})();"
        )
    else:
        # Count-up from 0 → n, accent flash at lock
        lines.append(
            f"  tl.to('#{cid}-ur-n',{{opacity:1,duration:0.20,ease:'power1.out'}},{t_num:.4f});"
        )
        lines.append(
            f"  (function(){{ var {obj}={{v:0}};"
            f" tl.to({obj},{{v:{n},duration:{count_dur:.3f},ease:'power2.out',"
            f"onUpdate:function(){{var el=document.querySelector('#{cid}-ur-n');"
            f"if(el) el.textContent=Math.round({obj}.v);}}}},{t_num:.4f}); }})();"
        )
        # Pop + accent flash at count end
        t_lock = round(t_num + count_dur, 4)
        pop_s  = "1.12" if is_vibe else "1.07"
        lines.append(
            f"  tl.to('#{cid}-ur-n',"
            f"{{scale:{pop_s},duration:0.12,ease:'power2.in'}},{t_lock:.4f});"
        )
        lines.append(
            f"  tl.to('#{cid}-ur-n',"
            f"{{scale:1,duration:0.18,ease:'power2.out'}},{round(t_lock+0.12,4):.4f});"
        )

    # 3. Unit label fades in
    t_unit = round(t_num + count_dur * 0.6, 4)
    lines.append(
        f"  tl.to('#{cid}-ur-unit',"
        f"{{opacity:1,duration:0.25,ease:'power1.out'}},{t_unit:.4f});"
    )

    # 4. Accent line draws
    t_line = round(t_unit + 0.10, 4)
    line_w = "60px" if is_cinema else "80px"
    lines.append(
        f"  tl.to('#{cid}-ur-line',"
        f"{{width:'{line_w}',duration:0.35,ease:'power2.out'}},{t_line:.4f});"
    )

    return lines


# ── Register ──────────────────────────────────────────────────────────────────

register(BRollType(
    name="urgency_clock",
    patterns=_ALL_PATTERNS,
    extractor=_extractor,
    render_html=_render_html,
    render_gsap=_render_gsap,
    default_duration=3.5,
    preferred_zone="upper-right",
    min_confidence=0.78,
))
