"""
money_counter — animated count-up to a currency amount.

Triggers on patterns like:
  "50k€", "50 000 euros", "$200", "200 000 dollars", "1,5M€"

Does NOT trigger on:
  - ZIP codes / phone numbers (5+ consecutive digits without currency marker)
  - Percentages (handled separately if ever needed)
  - Vague amounts without a currency marker ("50 personnes")

render_html: card with .card-panel (gets standard pack entry animation),
             counter span + unit span, accent underline.
render_gsap: count-up via GSAP object tween, unit pop at count end,
             accent line draw. Inherits pack easing via _eIn/_eOut already
             defined in the timeline IIFE.
"""
from __future__ import annotations

import re
from app.engine.broll_registry import BRollType, register


# ── Patterns ──────────────────────────────────────────────────────────────────
# Alternation 1: number [multiplier] currency   →  "50k€"  "50 000 euros"
# Alternation 2: currency number [multiplier]   →  "$200"  "£1.5M"
_MONEY_RE = re.compile(
    r'(?:'
    # alt-1: amount then currency
    r'(?P<a1_num>[\d][\d\s ]*(?:[.,]\d{1,3})*(?:[.,]\d{1,2})?)'
    r'\s*(?P<a1_mult>[kKmM]?)\s*'
    r'(?P<a1_cur>€|\$|£|euros?|dollars?|USD|EUR|GBP)'
    r'|'
    # alt-2: currency then amount
    r'(?P<a2_cur>€|\$|£)'
    r'\s*(?P<a2_num>[\d][\d\s ]*(?:[.,]\d{1,3})*(?:[.,]\d{1,2})?)'
    r'\s*(?P<a2_mult>[kKmM]?)'
    r')',
    re.IGNORECASE,
)

# Reject if this looks like a phone number or ZIP (5+ plain digits no currency close)
_ZIPPHONE_RE = re.compile(r'^\d{5,}$')


def _parse_amount(num_str: str, mult_str: str) -> float:
    """Parse raw number string + optional k/K/m/M suffix to a float."""
    # Normalise: strip non-breaking spaces, regular spaces, thousands separators
    s = num_str.replace(" ", "").replace(" ", "")
    # Detect decimal separator: last separator followed by ≤2 digits is decimal
    m = re.search(r'[,.](\d{1,2})$', s)
    if m:
        integer_part = s[:m.start()].replace(",", "").replace(".", "")
        decimal_part = m.group(1)
        clean = f"{integer_part}.{decimal_part}"
    else:
        clean = s.replace(",", "").replace(".", "")

    try:
        val = float(clean)
    except ValueError:
        return 0.0

    mult = mult_str.lower()
    if mult == "k":
        val *= 1_000
    elif mult == "m":
        val *= 1_000_000
    return val


def _display_format(amount: float, currency_char: str) -> tuple[float, str, int]:
    """Return (display_value, unit_label, decimal_places) for the counter."""
    if amount >= 1_000_000:
        dv = amount / 1_000_000
        unit = f"M{currency_char}"
        decimals = 1 if dv < 10 else 0
    elif amount >= 1_000:
        dv = amount / 1_000
        unit = f"k{currency_char}"
        decimals = 1 if dv < 10 else 0
    else:
        dv = amount
        unit = currency_char
        decimals = 0
    return dv, unit, decimals


_KICKER_PATTERNS = [
    (re.compile(r'\b(revenue|CA|chiffre d.affaires|revenu|income|gagn|earn|vente|chiffre)\b', re.I), "Résultat"),
    (re.compile(r'\b(client|customer|résultat|result|témoignage)\b', re.I), "Résultat client"),
    (re.compile(r'\b(économis|saved|épargn|économie)\b', re.I), "Économies"),
    (re.compile(r'\b(investiss|invest)\b', re.I), "Investissement"),
    (re.compile(r'\b(salaire|salary|pay|paie|rémunération)\b', re.I), "Salaire"),
]


def _e(s: str) -> str:
    """Minimal HTML escape."""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _ej(s: str) -> str:
    """Minimal JS string escape."""
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")


# ── Extractor ─────────────────────────────────────────────────────────────────

def _extractor(match, words, word_idx: int) -> tuple[dict, float]:
    gd = match.groupdict()

    if gd.get("a1_num") is not None:
        num_str, mult, cur_raw = gd["a1_num"], gd["a1_mult"] or "", gd["a1_cur"]
    else:
        num_str, mult, cur_raw = gd["a2_num"], gd["a2_mult"] or "", gd["a2_cur"]

    # Reject bare long integers (phone/ZIP)
    clean_num = num_str.replace(" ", "").replace(" ", "").replace(",", "").replace(".", "")
    if _ZIPPHONE_RE.match(clean_num) and not mult and cur_raw in ("USD", "EUR", "GBP"):
        return {}, 0.0

    amount = _parse_amount(num_str, mult)
    if amount <= 0:
        return {}, 0.0

    # Normalise currency to a single char
    cur_map = {"€": "€", "$": "$", "£": "£", "USD": "$", "EUR": "€", "GBP": "£"}
    cur_lower = cur_raw.lower()
    if "euro" in cur_lower:
        currency_char = "€"
    elif "dollar" in cur_lower:
        currency_char = "$"
    else:
        currency_char = cur_map.get(cur_raw, cur_raw[0].upper())

    display_val, unit_label, decimals = _display_format(amount, currency_char)

    # Context kicker: look ±6 words around the match
    n = len(words)
    ctx = " ".join(
        getattr(words[i], "text", "") for i in range(max(0, word_idx - 6), min(n, word_idx + 7))
    )
    kicker = ""
    for pat, label in _KICKER_PATTERNS:
        if pat.search(ctx):
            kicker = label
            break

    params = {
        "amount": amount,
        "display_val": display_val,
        "unit_label": unit_label,
        "decimals": decimals,
        "kicker": kicker,
        "raw": match.group(),
    }
    return params, 0.88


# ── Render HTML ───────────────────────────────────────────────────────────────

def _render_html(params: dict, pack: dict, card_id: str) -> str:
    p = pack or {}
    bg       = p.get("bg",          "#1a1a1a")
    text_c   = p.get("text",        "#f1f1f1")
    accent   = p.get("accent",      "#4cc9f0")
    font     = p.get("font",        '"Inter", sans-serif')
    fw       = p.get("font_weight", "800")
    radius   = p.get("radius",      "20px")
    shadow   = p.get("shadow",      "0 8px 32px rgba(0,0,0,0.4)")
    shadow_i = p.get("shadow_inset","")
    shadow_v = f"{shadow}, {shadow_i}" if shadow_i else shadow

    unit_label  = _e(params.get("unit_label", "€"))
    kicker_text = _e(params.get("kicker", ""))

    kicker_html = (
        f'<span id="{card_id}-kicker" class="kicker mc-kicker">{kicker_text}</span>'
        if kicker_text else ""
    )

    grain_html = ""
    if p.get("has_grain"):
        grain_html = f'<div class="mc-grain"></div>'

    return f"""\
<div class="card" data-card-id="{card_id}">
<style>
.card[data-card-id="{card_id}"] .root {{
  width:100%; height:100%; display:flex; align-items:center; justify-content:center;
}}
.card[data-card-id="{card_id}"] .card-panel {{
  background:{bg}; border-radius:{radius}; padding:40px 56px;
  display:flex; flex-direction:column; align-items:center; gap:14px;
  box-shadow:{shadow_v}; position:relative; overflow:hidden;
}}
.card[data-card-id="{card_id}"] .mc-grain {{
  position:absolute; inset:0; pointer-events:none; border-radius:{radius};
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cfilter id='g'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23g)' opacity='0.04'/%3E%3C/svg%3E");
  background-repeat:repeat;
}}
.card[data-card-id="{card_id}"] .mc-kicker {{
  font-family:{font}; font-size:18px; font-weight:700;
  letter-spacing:0.14em; text-transform:uppercase; color:{accent}; opacity:0;
}}
.card[data-card-id="{card_id}"] .mc-amount-row {{
  display:flex; align-items:baseline; gap:4px;
}}
.card[data-card-id="{card_id}"] #{card_id}-mc-counter {{
  font-family:{font}; font-size:96px; font-weight:{fw};
  color:{text_c}; font-variant-numeric:tabular-nums; line-height:1;
}}
.card[data-card-id="{card_id}"] #{card_id}-mc-unit {{
  font-family:{font}; font-size:54px; font-weight:{fw};
  color:{accent}; opacity:0; display:inline-block; transform:scale(0.6);
}}
.card[data-card-id="{card_id}"] #{card_id}-mc-line {{
  width:0; height:3px; background:{accent}; border-radius:2px;
  margin-top:4px;
}}
</style>
<div class="root">
  <div class="card-panel">
    {grain_html}
    {kicker_html}
    <div class="mc-amount-row">
      <span id="{card_id}-mc-counter" class="mc-counter">0</span>
      <span id="{card_id}-mc-unit" class="mc-unit">{unit_label}</span>
    </div>
    <div id="{card_id}-mc-line"></div>
  </div>
</div>
</div>"""


# ── Render GSAP ───────────────────────────────────────────────────────────────

def _render_gsap(params: dict, pack: dict, card_id: str, start: float, end: float) -> list[str]:
    display_val = float(params.get("display_val", 0))
    decimals    = int(params.get("decimals", 0))
    kicker      = params.get("kicker", "")
    dur         = max(0.5, end - start)
    count_dur   = round(min(1.8, max(0.7, dur * 0.40)), 3)
    t_in        = round(start + 0.20, 4)   # after pack panel entry (~0.15-0.35s)

    p  = pack or {}
    p_id = p.get("id", "lean_glass")

    # Pack-specific count easing
    count_ease = {
        "lean_ledger": "none",
        "lean_cinema": "power2.in",
    }.get(p_id, "power2.out")

    # Object name: safe JS identifier from card_id
    obj_name = f"_mc_{card_id.replace('-', '_')}"

    lines: list[str] = []

    if kicker:
        lines.append(
            f"  tl.to('#{_ej(card_id)}-kicker', "
            f"{{opacity:1, duration:0.25, ease:'power1.out'}}, {t_in:.4f});"
        )

    # Count-up: animate an object, update textContent on each frame
    t_count = round(t_in + 0.05, 4)
    fmt = f".toFixed({decimals})" if decimals else ".toLocaleString()"
    lines.append(
        f"  (function(){{ "
        f"var {obj_name}={{v:0}}; "
        f"tl.to({obj_name}, {{"
        f"v:{display_val:.{decimals}f}, "
        f"duration:{count_dur:.3f}, ease:'{_ej(count_ease)}', "
        f"onUpdate:function(){{"
        f"var el=document.querySelector('#{_ej(card_id)}-mc-counter');"
        f"if(el) el.textContent=({obj_name}.v){fmt};"
        f"}}}}, {t_count:.4f}); }})();"
    )

    # Unit pop-in just before count ends
    t_unit = round(t_count + count_dur - 0.15, 4)
    lines.append(
        f"  tl.to('#{_ej(card_id)}-mc-unit', "
        f"{{opacity:1, scale:1, duration:0.30, ease:'back.out(1.7)'}}, {t_unit:.4f});"
    )

    # Accent line draw
    t_line = round(t_in + 0.15, 4)
    lines.append(
        f"  tl.to('#{_ej(card_id)}-mc-line', "
        f"{{width:'80%', duration:0.40, ease:'power2.out'}}, {t_line:.4f});"
    )

    return lines


# ── Register ──────────────────────────────────────────────────────────────────

register(BRollType(
    name="money_counter",
    patterns=[_MONEY_RE],
    extractor=_extractor,
    render_html=_render_html,
    render_gsap=_render_gsap,
    default_duration=5.5,
    preferred_zone="upper-data",
    min_confidence=0.80,
))
