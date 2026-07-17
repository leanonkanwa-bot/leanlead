#!/usr/bin/env python3
"""
Wave 7 + Wave 8 structural verification — replaces manual per-pack visual checking.

Checks performed:
  1. HTML/JS selector integrity  (JS targets ⊆ HTML ids) — 48 combos
  2. Smoke render                (both HTML and JS build without exception,
                                  type-specific CSS wrapper class present,
                                  required content fields appear in HTML)
  3. Grounding guard membership  (4 trigger types IN _TRIGGER_STYLES,
                                  silent_beat_pause NOT IN _TRIGGER_STYLES)
  4. _TRIGGER_TEXT_FIELD mapping  (each trigger type maps to its key field)

Run:  python -X utf8 backend/test_wave7_verification.py
Exit 0 = all checks pass.  Exit 1 = failures found.
"""
import re, sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app.engine.compose import (
    _LEAN_GLASS, _LEAN_PAPER, _LEAN_VIBE,
    _LEAN_LEDGER, _LEAN_CRAFT, _LEAN_CINEMA,
    _build_graphic_card_html, _build_timeline_js,
)
from app.engine.storyboard import _TRIGGER_STYLES, _TRIGGER_TEXT_FIELD

PACKS = [
    ("lean_glass",  _LEAN_GLASS),
    ("lean_paper",  _LEAN_PAPER),
    ("lean_vibe",   _LEAN_VIBE),
    ("lean_ledger", _LEAN_LEDGER),
    ("lean_craft",  _LEAN_CRAFT),
    ("lean_cinema", _LEAN_CINEMA),
]

CARD_ID = "c1"

# ── Wave 7 type definitions ───────────────────────────────────────────────────
# Each entry: (content_style, hints, required_wrapper_class, required_content_snippet)

W7_TYPES = [
    ("live_reaction_split",
     {"expected_text": "Le SEO est mort",
      "reality_text":  "Le SEO génère encore 40% de notre trafic"},
     "lrs-wrap",
     "génère encore"),

    ("hidden_cost_reveal",
     {"sticker_price": "19€/mois",
      "real_cost":     "228€ par an au total"},
     "hcr-wrap",
     "228"),

    ("social_proof_counter",
     {"counter_final_value": "47 382",
      "counter_label":       "entrepreneurs formés"},
     "spc-wrap",
     "47 382"),

    ("timeline_prediction",
     {"confirmed_steps": ["Lancement produit Jan 2024", "10k clients Mai 2024"],
      "predicted_steps": ["100k clients Q2 2025",      "Expansion US Q4 2025"]},
     "tp-wrap",
     "Lancement produit"),

    ("red_thread_connector",
     {"connector_points": ["Le problème initial",
                            "La solution découverte",
                            "Le résultat final"]},
     "rtc-wrap",
     "problème initial"),

    ("silent_beat_pause",
     {"pause_symbol": "…"},
     "sbp-wrap",
     "…"),

    ("comment_reply_style",
     {"comment_text": "Mais ça fonctionne vraiment pour les débutants ?",
      "reply_text":   "Oui — voici 3 preuves concrètes"},
     "crs-wrap",
     "3 preuves concrètes"),

    ("before_you_scroll",
     {"hook_text": "Attends — lis ça avant de continuer"},
     "bys-wrap",
     "lis ça"),
    # ── Wave 8 ────────────────────────────────────────────────────────────────
    ("traffic_light_status",
     {"status_color": "green", "status_label": "Stratégie validée"},
     "tls-wrap",
     "Stratégie validée"),
    ("day_in_life_schedule",
     {"schedule_items": ["6h - Réveil", "9h - Deep work", "12h - Pause"]},
     "dls-wrap",
     "6h - Réveil"),
    ("skill_tree_unlock",
     {"unlocked_milestones": ["Maîtrise Notion", "Premier client", "Zapier automatisé"]},
     "stu-wrap",
     "Maîtrise Notion"),
    ("audience_poll_result",
     {"poll_options": ["Oui, c'est possible", "Non, c'est trop dur"],
      "poll_percentages": [73.0, 27.0]},
     "apr-wrap",
     "Oui"),
    ("broken_promise_tracker",
     {"promises": ["Poster chaque jour", "Répondre aux DM", "Lancer en mars"],
      "kept_status": [True, False, False]},
     "bpt-wrap",
     "Poster chaque jour"),
    ("ingredient_list",
     {"ingredients": ["Une offre claire", "Un tunnel de vente", "Du contenu régulier"]},
     "igl-wrap",
     "offre claire"),
    ("resource_allocation",
     {"resource_labels": ["Temps", "Énergie", "Budget"],
      "resource_values": [40.0, 35.0, 25.0]},
     "ral-wrap",
     "Temps"),
    ("fill_in_the_blank",
     {"sentence_with_blank": "La clé du succès c'est ___", "blank_word": "la régularité"},
     "fitb-wrap",
     "la régularité"),
]

# ── Trigger-guard spec ────────────────────────────────────────────────────────

TRIGGER_TYPES = {
    # Wave 7
    "live_reaction_split": "reality_text",
    "hidden_cost_reveal":  "real_cost",
    "comment_reply_style": "reply_text",
    "before_you_scroll":   "hook_text",
    # Wave 8
    "broken_promise_tracker": "promises",
}
NOT_TRIGGER = "silent_beat_pause"

# ── Helpers ───────────────────────────────────────────────────────────────────

def make_card(style: str, hints: dict) -> dict:
    h = {"style": style}
    h.update(hints)
    return {"id": CARD_ID, "type": "graphic", "startSec": 2.0, "endSec": 8.0,
            "zone": "fullscreen", "contentHints": h}

def html_ids(html: str) -> set[str]:
    return set(re.findall(rf'id="{re.escape(CARD_ID)}-([^"]+)"', html))

def js_targets(js: str) -> set[str]:
    raw  = re.findall(rf"['\"]#{re.escape(CARD_ID)}-([^'\"]+)['\"]", js)
    raw += re.findall(rf"querySelector\(['\"]#{re.escape(CARD_ID)}-([^'\"]+)['\"]", js)
    return set(raw)

# ── Check 1 + 2: 48-combo sweep ───────────────────────────────────────────────

W = 20  # column width for type name
PW = 12  # pack column width

pack_names = [p for p, _ in PACKS]

print(f"\n{'='*78}")
print("  WAVE 7 STRUCTURAL VERIFICATION")
print(f"{'='*78}")

print(f"\n── Check 1+2: HTML/JS integrity + smoke render  ({len(W7_TYPES)} types × 6 packs = {len(W7_TYPES)*6}) ──\n")

header = f"{'TYPE':<{W}} " + "  ".join(f"{p[:10]:<{PW}}" for p in pack_names)
print(header)
print("-" * len(header))

total = 0
failures: list[tuple[str, str, str]] = []

for style, hints, wrapper_cls, content_snippet in W7_TYPES:
    card   = make_card(style, hints)
    row    = f"{style:<{W}}"
    ok_row = True

    for pack_name, pack in PACKS:
        total += 1
        cell_ok = True
        issues  = []

        try:
            html = _build_graphic_card_html(card, pack=pack)
            js   = _build_timeline_js([card], pack=pack)
        except Exception as exc:
            issues.append(f"EXCEPTION: {exc}")
            cell_ok = False
            ok_row  = False
            failures.append((style, pack_name, issues[0]))
            row += f"  {'ERR':<{PW}}"
            continue

        # a. non-empty output
        if not html.strip():
            issues.append("HTML empty")
        if not js.strip():
            issues.append("JS empty")

        # b. type-specific CSS wrapper present
        if f'class="{wrapper_cls}"' not in html and f'class="{wrapper_cls} ' not in html:
            issues.append(f".{wrapper_cls} missing")

        # c. content snippet in HTML
        if content_snippet not in html:
            issues.append(f"content '{content_snippet[:20]}' absent")

        # d. JS/HTML ID integrity
        ids  = html_ids(html)
        refs = js_targets(js)
        miss = refs - ids
        if miss:
            issues.append(f"drift:{sorted(miss)}")

        if issues:
            cell_ok = False
            ok_row  = False
            for iss in issues:
                failures.append((style, pack_name, iss))

        row += f"  {'OK' if cell_ok else 'FAIL':<{PW}}"

    print(row)

print()

# ── Check 3: grounding guard membership ──────────────────────────────────────

print("── Check 3: grounding guard (_TRIGGER_STYLES) ──────────────────────────────\n")

guard_results: list[tuple[str, bool, str]] = []

for t_style, t_field in TRIGGER_TYPES.items():
    in_ts  = t_style in _TRIGGER_STYLES
    in_ttf = _TRIGGER_TEXT_FIELD.get(t_style) == t_field
    ok     = in_ts and in_ttf
    status = "OK" if ok else "FAIL"
    detail = ""
    if not in_ts:
        detail += " NOT in _TRIGGER_STYLES;"
    if not in_ttf:
        actual = _TRIGGER_TEXT_FIELD.get(t_style, "<missing>")
        detail += f" _TRIGGER_TEXT_FIELD={actual!r}, expected {t_field!r};"
    guard_results.append((t_style, ok, detail.strip()))
    if not ok:
        failures.append(("grounding", t_style, detail))
    print(f"  {'OK' if ok else 'FAIL'}  {t_style:<30}  in _TRIGGER_STYLES={in_ts}  "
          f"_TRIGGER_TEXT_FIELD={_TRIGGER_TEXT_FIELD.get(t_style, '<missing>')!r}")

print()

# ── Check 4: silent_beat_pause excluded from grounding ───────────────────────

print("── Check 4: silent_beat_pause grounding exclusion ──────────────────────────\n")

sbp_absent = NOT_TRIGGER not in _TRIGGER_STYLES
sbp_status = "OK" if sbp_absent else "FAIL"
if not sbp_absent:
    failures.append(("grounding", NOT_TRIGGER, "incorrectly IN _TRIGGER_STYLES"))
print(f"  {sbp_status}  {NOT_TRIGGER} NOT in _TRIGGER_STYLES = {sbp_absent}")
print()

# ── Summary table ─────────────────────────────────────────────────────────────

print(f"{'='*78}")
passed = total + len(TRIGGER_TYPES) + 1 - len(failures)
total_checks = total + len(TRIGGER_TYPES) + 1

if not failures:
    print(f"  ALL {total_checks} CHECKS PASSED")
    print(f"  {total} render combos clean  ·  {len(TRIGGER_TYPES)} trigger types guarded  ·  "
          f"silent_beat_pause unguarded")
    print(f"  Wave 7 + Wave 8 structurally launch-ready.")
else:
    print(f"  {len(failures)} FAILURE(S)  ({passed}/{total_checks} passed)")
    print()
    for f_type, f_pack, f_detail in failures:
        print(f"  FAIL  [{f_type}] [{f_pack}]  {f_detail}")

print(f"{'='*78}\n")
sys.exit(0 if not failures else 1)
