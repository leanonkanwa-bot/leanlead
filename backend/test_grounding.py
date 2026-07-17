#!/usr/bin/env python3
"""
Grounding guard test suite — stopword-stripped overlap logic + 40% threshold.

Tests 15 canonical cases (true positives + true negatives) plus the new
stopword-inflation false-negative scenario observed in job f366e990.

Run:  python test_grounding.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app.engine.storyboard import (
    _grounding_overlap,
    _content_words,
    _FR_STOPWORDS,
    _GROUNDING_OVERLAP_THRESHOLD,
    _TRIGGER_TEXT_FIELD,
)
from app.engine.captions import WordTiming

THRESHOLD = _GROUNDING_OVERLAP_THRESHOLD   # 0.40


def make_words(text: str, t_start: float, t_end: float | None = None) -> list[WordTiming]:
    """Split text into one WordTiming per word, evenly distributed across [t_start, t_end]."""
    words = text.split()
    if not words:
        return []
    end = t_end or (t_start + len(words) * 0.4)
    step = (end - t_start) / len(words)
    return [WordTiming(text=w, start=t_start + i * step, end=t_start + (i + 1) * step)
            for i, w in enumerate(words)]


def card(style: str, trigger_field: str, trigger_text: str, start: float = 5.0) -> dict:
    return {
        "id": "test",
        "startSec": start,
        "contentHints": {"style": style, trigger_field: trigger_text},
    }


def check(label: str, c: dict, words: list[WordTiming], expect_pass: bool) -> bool:
    overlap = _grounding_overlap(c, words)
    passed = overlap >= THRESHOLD
    ok = passed == expect_pass
    status = "OK  " if ok else "FAIL"
    verb = "PASS" if passed else "FAIL"
    print(f"  [{status}] {label:<52} overlap={overlap:.0%}  → {verb}  (expected {'PASS' if expect_pass else 'REJECT'})")
    return ok


failures = 0
cases = 0

print(f"\n{'='*70}")
print(f"  Grounding guard — threshold={THRESHOLD:.0%} — stopword count={len(_FR_STOPWORDS)}")
print(f"{'='*70}\n")

# ── TRUE POSITIVES: genuine content match → should PASS ──────────────────────
print("TRUE POSITIVES (genuine match, expect PASS ≥ 40%)")

# 1. Exact content-word hit — product + price
c1 = card("warning_soft", "warning_text", "Stripe refuse les paiements internationaux")
w1 = make_words("Stripe refuse paiements internationaux disponibles", 4.6, 8.0)
cases += 1; failures += 0 if check("1. exact content match (Stripe/refuse/paiements)", c1, w1, True) else 1

# 2. Strong partial match — 4/5 content words present
c2 = card("contrarian_take", "take_text", "Netflix a perdu trois millions abonnés ce trimestre")
w2 = make_words("netflix abonnés millions trimestre résultats", 4.7, 8.0)
cases += 1; failures += 0 if check("2. 4/5 content words match (Netflix)", c2, w2, True) else 1

# 3. Verb-heavy but meaningful content survives
c3 = card("action_step_cta", "cta_text", "télécharge l'outil gratuitement maintenant")
w3 = make_words("télécharge outil gratuitement lien description", 4.6, 8.0)
cases += 1; failures += 0 if check("3. action CTA — outil/gratuit match", c3, w3, True) else 1

# 4. Numbers as content words
c4 = card("warning_soft", "warning_text", "cent mille euros perdus chaque mois")
w4 = make_words("cent mille euros perdus impôts", 4.5, 8.0)
cases += 1; failures += 0 if check("4. numbers as content words (cent/mille/euros)", c4, w4, True) else 1

# 5. Business vocabulary — full match
c5 = card("myth_vs_fact", "myth_text", "croissance exponentielle stratégie investissement")
w5 = make_words("stratégie croissance exponentielle investissement rentabilité", 4.5, 8.0)
cases += 1; failures += 0 if check("5. business vocab — full content match", c5, w5, True) else 1

# 6. Borderline: 2/3 content words present (67%)
c6 = card("secret_reveal", "secret_text", "algorithme favorise vidéos courtes monétisées")
w6 = make_words("algorithme vidéos courtes engagement", 4.5, 8.0)
cases += 1; failures += 0 if check("6. 2/3 content match — algorithme/vidéos/courtes", c6, w6, True) else 1

# 7. Card in a different window but within range (speech 0.4s before startSec)
c7 = card("objection_response", "objection_text", "produit trop cher marché accessible", start=6.0)
w7 = make_words("produit cher marché accessible qualité", 5.65, 9.0)
cases += 1; failures += 0 if check("7. speech starts 0.35s before startSec (in window)", c7, w7, True) else 1

# 8. Red flag list — joined list, content words still match
c8 = card("red_flag_list", "flags", ["arnaque", "faux témoignages", "promesses irréalistes"])
w8 = make_words("arnaque témoignages irréalistes signaux attention", 4.5, 8.0)
cases += 1; failures += 0 if check("8. red_flag_list joined list — arnaque/témoignages", c8, w8, True) else 1

print()

# ── TRUE NEGATIVES: no genuine match → should REJECT ─────────────────────────
print("TRUE NEGATIVES (fabricated content, expect REJECT < 40%)")

# 9. Completely unrelated card and speech
c9 = card("contrarian_take", "take_text", "révolution industrielle automatisation chômage")
w9 = make_words("recette poulet rôti légumes four", 4.5, 8.0)
cases += 1; failures += 0 if check("9. completely unrelated content", c9, w9, False) else 1

# 10. Card mentions a topic not in the speech window at all
c10 = card("warning_soft", "warning_text", "bitcoin effondrement crypto monnaie risque")
w10 = make_words("instagram followers engagement stories reels", 4.5, 8.0)
cases += 1; failures += 0 if check("10. crypto card vs social-media speech", c10, w10, False) else 1

# 11. Speech is outside the window (after +3s) — should produce empty spoken set
c11 = card("myth_vs_fact", "myth_text", "algorithme pénalise publications régulières", start=5.0)
w11 = make_words("algorithme pénalise publications régulières", 9.0, 12.0)   # starts at +4s
cases += 1; failures += 0 if check("11. matching words but outside ±window", c11, w11, False) else 1

# 12. Only 1 content word matches (25%) — below 40%
c12 = card("secret_reveal", "secret_text", "contrat exclusif partenariat marque négociation")
w12 = make_words("contrat signature formulaire administratif dossier", 4.5, 8.0)
cases += 1; failures += 0 if check("12. 1/4 content match (25%) — below threshold", c12, w12, False) else 1

print()

# ── STOPWORD-INFLATION FALSE NEGATIVES (old bug, new logic must catch) ────────
print("STOPWORD-INFLATION — would have PASSED old 20% logic, must REJECT new logic")

# 13. Classic false-negative: trigger shares only function verbs with speech
#     OLD: {je,vais,que,une} ∩ {je,vais,vous} → {je,vais} → 2/7 = 28.6% → OLD PASS (>20%)
#     NEW: trigger content={mauvaise,idée,truc} speech content={montrer,comment,truc...}
#     Expected: 0% if speech has no matching content words
c13 = card("contrarian_take", "take_text",
           "je vais te dire que c'est une mauvaise idée")
w13 = make_words("je vais vous montrer comment faire ça proprement", 4.5, 8.0)
overlap_old_13 = len(
    frozenset(t for t in __import__('re').sub(r"[^\w\s]","","je vais te dire que c'est une mauvaise idée".lower()).split() if len(t)>=2)
    & frozenset(t for t in __import__('re').sub(r"[^\w\s]","","je vais vous montrer comment faire ça proprement".lower()).split() if len(t)>=2)
) / len(frozenset(t for t in __import__('re').sub(r"[^\w\s]","","je vais te dire que c'est une mauvaise idée".lower()).split() if len(t)>=2))
print(f"         old overlap (no stopwords stripped) = {overlap_old_13:.0%}  {'→ FALSE NEGATIVE with old 20% threshold' if overlap_old_13 >= 0.20 else '→ would have been caught'}")
cases += 1; failures += 0 if check("13. je/vais/te/dire shared — only function words", c13, w13, False) else 1

# 14. "on va voir si c'est vrai" near "on va parler de ce sujet ensemble"
#     OLD shared: {on, va, voir, si, vrai} ∩ {on,va,donc,parler,de,ce,sujet,ensemble} = {on,va} → 2/5=40% PASS
#     NEW: content trigger={voir,vrai} content speech={parler,sujet} → 0% REJECT
c14 = card("myth_vs_fact", "myth_text", "on va voir ensemble si c'est vraiment vrai")
w14 = make_words("on va donc parler de ce sujet avec vous maintenant", 4.5, 8.0)
overlap_old_14 = len(
    frozenset(t for t in __import__('re').sub(r"[^\w\s]","","on va voir ensemble si c'est vraiment vrai".lower()).split() if len(t)>=2)
    & frozenset(t for t in __import__('re').sub(r"[^\w\s]","","on va donc parler de ce sujet avec vous maintenant".lower()).split() if len(t)>=2)
) / len(frozenset(t for t in __import__('re').sub(r"[^\w\s]","","on va voir ensemble si c'est vraiment vrai".lower()).split() if len(t)>=2))
print(f"         old overlap (no stopwords stripped) = {overlap_old_14:.0%}  {'→ FALSE NEGATIVE with old 20% threshold' if overlap_old_14 >= 0.20 else '→ would have been caught'}")
cases += 1; failures += 0 if check("14. on/va/voir/vrai — discourse-word inflation", c14, w14, False) else 1

# 15. NEW — the specific pattern from job f366e990 card-01:
#     contrarian_take at startSec=1.0s, first nearby word='hui,'@0.96s (part of "aujourd'hui")
#     Reconstructed: take_text="je vais dire un truc que personne ne veut entendre"
#     Speech window: "aujourd'hui on va parler des outils qui changent tout"
#     OLD: shared tokens {vais,dire,que,veut}? check… vais/on overlap?
#     Exact user-specified test from the brief: "je vais dire un truc impopulaire" vs "voici mes outils"
c15 = card("contrarian_take", "take_text",
           "je vais dire un truc impopulaire", start=1.0)
w15 = make_words("voici mes outils préférés pour gagner du temps", 0.6, 4.5)
overlap_old_15 = len(
    frozenset(t for t in __import__('re').sub(r"[^\w\s]","","je vais dire un truc impopulaire".lower()).split() if len(t)>=2)
    & frozenset(t for t in __import__('re').sub(r"[^\w\s]","","voici mes outils préférés pour gagner du temps".lower()).split() if len(t)>=2)
) / max(1, len(frozenset(t for t in __import__('re').sub(r"[^\w\s]","","je vais dire un truc impopulaire".lower()).split() if len(t)>=2)))
print(f"         old overlap (no stopwords stripped) = {overlap_old_15:.0%}  (this case: 0% even with old logic — was already caught)")
cases += 1; failures += 0 if check("15. f366e990-like: 'je vais dire un truc impopulaire'", c15, w15, False) else 1

# 16. NEW — stopword-inflation variant that WOULD have been a false negative:
#     warning_soft: "je vais te montrer que cette méthode ne fonctionne pas"
#     speech: "je vais maintenant vous présenter cette stratégie incroyable"
#     OLD shared (>=2 chars): {je,vais,te,montrer,que,cette,méthode,ne,fonctionne,pas}
#              ∩ {je,vais,maintenant,vous,présenter,cette,stratégie,incroyable}
#            = {je,vais,cette} → 3/10 = 30% → OLD PASS (>20%) — FALSE NEGATIVE
#     NEW: trigger content={montrer,méthode,fonctionne}; speech content={maintenant,présenter,stratégie,incroyable}
#          → 0% → REJECT ✓
c16 = card("warning_soft", "warning_text",
           "je vais te montrer que cette méthode ne fonctionne pas")
w16 = make_words("je vais maintenant vous présenter cette stratégie incroyable", 4.5, 8.0)
overlap_old_16 = len(
    frozenset(t for t in __import__('re').sub(r"[^\w\s]","","je vais te montrer que cette méthode ne fonctionne pas".lower()).split() if len(t)>=2)
    & frozenset(t for t in __import__('re').sub(r"[^\w\s]","","je vais maintenant vous présenter cette stratégie incroyable".lower()).split() if len(t)>=2)
) / len(frozenset(t for t in __import__('re').sub(r"[^\w\s]","","je vais te montrer que cette méthode ne fonctionne pas".lower()).split() if len(t)>=2))
print(f"         old overlap (no stopwords stripped) = {overlap_old_16:.0%}  {'→ FALSE NEGATIVE with old 20% threshold' if overlap_old_16 >= 0.20 else '→ would have been caught'}")
cases += 1; failures += 0 if check("16. 'je/vais/cette' inflation — warning false-neg", c16, w16, False) else 1

print()

# ── Job f366e990 card-02 reconstruction ──────────────────────────────────────
print("JOB f366e990 CARD RECONSTRUCTION")
print("  card-02 warning_soft @ 6.52s, overlap=16% with old logic, first word='Stripe,'")
print("  Reconstructed trigger: 'attention je vais vous dire quelque chose sur Stripe'")
print("  Reconstructed speech:  'Stripe accepte les paiements dans le monde entier'")
import re as _re

def _tok(t): return frozenset(x for x in _re.sub(r"[^\w\s]","",t.lower()).split() if len(x)>=2)

trig_text = "attention je vais vous dire quelque chose sur Stripe"
speech_text = "Stripe accepte les paiements dans le monde entier"
old_trig = _tok(trig_text)
old_speech = _tok(speech_text)
old_ov = len(old_trig & old_speech) / len(old_trig)
new_trig = old_trig - _FR_STOPWORDS
new_speech = old_speech - _FR_STOPWORDS
new_ov = len(new_trig & new_speech) / len(new_trig) if new_trig else 1.0

print(f"  OLD logic:  trigger tokens={sorted(old_trig)}")
print(f"              speech  tokens={sorted(old_speech)}")
print(f"              overlap = {old_ov:.0%}  → {'PASS (FALSE NEG)' if old_ov >= 0.20 else 'REJECT'} @ 20% threshold")
print(f"  NEW logic:  trigger content={sorted(new_trig)}")
print(f"              speech  content={sorted(new_speech)}")
print(f"              overlap = {new_ov:.0%}  → {'PASS' if new_ov >= 0.40 else 'REJECT'} @ 40% threshold")

print()
print(f"{'='*70}")
print(f"  RESULTS: {cases - failures}/{cases} passed   {'ALL OK' if failures == 0 else str(failures) + ' FAILURE(S)'}")
print(f"{'='*70}\n")
sys.exit(0 if failures == 0 else 1)
