"""
Qualifier Agent — v5
Scores 0-100 + psychographic profile + response probability in ONE Claude call.

Pre-qualification signal boosts (deterministic, no API cost):
  • Buying intent (5 languages: FR/EN/ES/PT/AR) → +40
  • Life event trigger                           → +30
  • Ghost follower (follows coaches)             → +20
  • Hot prospect (repeated engagement)           → +15
  • Pain peak (maximum vulnerability)            → +25
  • Failed purchase (burned buyer)               → +35
  • Before/after seeker (transformation desire)  → +15
  • Podcast listener (warm, educated lead)       → +20
  • Book reader (development mindset)            → +25
  • Course dropout (already bought, needs more) → +30
  • Life transition (highest conversion window)  → +25
  • High voice tone intensity (emotional text)   → +10
"""
import json
import logging
import os
import re

import anthropic
import httpx

logger = logging.getLogger(__name__)

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


# ---------------------------------------------------------------------------
# Signal detectors — 5 languages, no API call
# ---------------------------------------------------------------------------

_BUYING_INTENT_RE = re.compile(
    r'\b('
    # French
    r'combien [çca]a co[uû]te|c\'est combien|quel (est le )?tarif|comment vous contacter|'
    r'o[uù] (vous )?trouver|j\'ai besoin d\'aide|quelqu\'un peut m\'aider|'
    r'cherche un coach|besoin d\'un coach|qui peut m\'aider|'
    r'comment commencer|par o[uù] commencer|comment (tu|vous) (fais|faites)|'
    r'vous recommandez|des recommandations|c\'est possible pour moi|'
    r'je veux (changer|m\'améliorer|progresser)|prêt(e)? à investir|'
    # English
    r'how much (does it cost|is it)|how do i (start|get started)|where do i start|'
    r'looking for a coach|need a coach|any recommendations|how do i|'
    r'someone help|advice please|ready to invest|is it possible for me|'
    r'do you recommend (someone|anyone)|how did you do it|'
    # Spanish
    r'cu[aá]nto cuesta|c[oó]mo empezar|necesito (un coach|ayuda)|'
    r'recomiendas (a )?alguien|es posible para m[ií]|c[oó]mo lo hiciste|'
    r'busco un coach|necesito apoyo|por d[oó]nde empiezo|'
    # Portuguese
    r'quanto custa|como come[çc]ar|preciso de (ajuda|um coach)|'
    r'voc[êe] recomenda|[eé] poss[íi]vel para mim|como voc[êe] fez|'
    r'procuro um coach|preciso de apoio|por onde come[çc]ar|'
    # Arabic (transliterated + common patterns)
    r'كم يكلف|كيف أبدأ|أحتاج مساعدة|هل ممكن|كيف فعلت|أبحث عن مدرب'
    r')\b',
    re.IGNORECASE,
)

_LIFE_EVENT_RE = re.compile(
    r'\b('
    # French
    r'nouvelle ann[ée]e?|nouvel an|nouveau d[ée]part|tout recommencer|repartir de z[ée]ro|'
    r'nouvelle vie|changer de vie|licenci[ée]e?|au ch[ôo]mage|d[ée]mission|'
    r'j\'ai quitt[ée]|reconversion|j\'en peux plus|j\'en ai marre|ras le bol|'
    r'divorc[ée]e?|s[ée]paration|rupture|b[ée]b[ée]|enceinte|accouchement|'
    r'mariage|fianc[ée]|j\'ai d[ée]cid[ée]|cette fois c\'est la bonne|maintenant ou jamais|'
    r'je me lance|j\'ose enfin|'
    # English
    r'new year|fresh start|starting over|just lost my job|quit my job|left my job|'
    r'just divorced|just had a baby|new chapter|rock bottom|enough is enough|'
    r'turning point|wake up call|life change|career change|'
    r'turned 3\d|turning 3\d|turned 4\d|turning 4\d|just graduated|just moved|'
    # Spanish/Portuguese
    r'nuevo comienzo|empezar de cero|acabo de perder|nueva vida|'
    r'novo come[çc]o|come[çc]ar do zero|'
    r')\b',
    re.IGNORECASE,
)

_FOLLOWS_COACHES_RE = re.compile(
    r'\b('
    # French
    r'suivi?s? par|abonné(e)? (à|de)|fan de|inspiré(e)? par|merci.{0,20}coach|'
    r'coach de ma vie|ma coach|mon coach|j\'adore.{0,15}coach|'
    r'j\'ai suivi|j\'ai regardé|j\'ai fait (le |la |son |sa )?programme|'
    r'la méthode de|le podcast de|sa chaîne|formation (de|avec)|masterclass|'
    # English
    r'following.{0,15}coach|fan of.{0,15}coach|love.{0,15}coach|inspired by|'
    r'watched.{0,10}course|enrolled in|coaching program|my coach|'
    r'coach changed my life|coach helped me'
    r')\b',
    re.IGNORECASE,
)

_HOT_PROSPECT_RE = re.compile(
    r'\b('
    # Repeatedly engaging with solution content
    r'je regarde (toutes?|chaque)|j\'ai regardé (tous?|chaque)|je suis (tous?|chaque)|'
    r'tes (vidéos?|contenus?|lives?|stories?)|vos (vidéos?|contenus?)|'
    r'i watch (all|every)|i follow (all|every)|i\'ve watched|been following|'
    r'siempre (veo|sigo)|sempre (assisto|sigo)'
    r')\b',
    re.IGNORECASE,
)

_PAIN_PEAK_RE = re.compile(
    r'\b('
    # French — maximum vulnerability expressions
    r'je craque|je pète un câble|je suis à bout|j\'abandonne|j\'abandonne tout|'
    r'j\'en ai ras le bol|plus la force|plus envie de rien|j\'ai tout essayé|'
    r'je pleure|j\'ai pleuré|nuit blanche|2h du matin|3h du matin|4h du mat|'
    r'au secours|help me|s\'il vous plaît aidez|quelqu\'un peut m\'aider|'
    r'je ne sais plus quoi faire|je ne vois plus d\'issue|au fond du trou|'
    r'rock bottom|breaking point|can\'t do this anymore|i give up|'
    # English
    r'i\'m done|i\'m broken|i can\'t go on|hit rock bottom|enough is enough|'
    r'please someone help|i\'ve tried everything|nothing is working|'
    r'i\'m desperate|last resort|i don\'t know what to do'
    r')\b',
    re.IGNORECASE,
)

_FAILED_PURCHASE_RE = re.compile(
    r'('
    # French — bought coaching, got burned
    r'j\'ai (acheté|payé|investi).{0,50}(coach|formation|programme|cours|masterclass)|'
    r'(formation|programme|coaching|cours|masterclass).{0,40}(arnaque|marche pas|pas fonctionné|déçu|remboursement|nul|inutile)|'
    r'(arnaqué|escroquerie|fraude).{0,30}(coach|formation)|'
    r'perdu.{0,20}(€|euro|argent).{0,30}(coach|formation)|'
    r'demandé.{0,10}remboursement|se faire rembourser|'
    r'# English — failed buyer signals
    r'wasted.{0,20}(money|\$|€).{0,30}(coach|program|course)|'
    r'paid.{0,30}(coach|program|course).{0,30}(didn\'t|not|no result|waste|scam)|'
    r'got scammed.{0,20}(coach|program)|coaching.{0,30}(scam|fraud|waste)|'
    r'money back.{0,20}(coaching|program)|refund.{0,20}(coach|course)|'
    r'coach.{0,30}(lied|fake|fraud|useless|waste of)'
    r')',
    re.IGNORECASE,
)

_BEFORE_AFTER_RE = re.compile(
    r'\b('
    # Actively seeking transformation
    r'avant[/-]après|transformation|avant après|résultats comme|comme toi|comme ça|'
    r'je veux (ça|ça aussi|ce résultat|ces résultats|ce corps|cette vie)|'
    r'j\'aspire à|j\'aimerais (tellement|vraiment)|mon objectif|mes objectifs|'
    r'before.?after|body goals|life goals|goals!|goals 🙌|i want this|'
    r'this is my goal|i want results like|relationship goals|'
    r'saving this|bookmarking this|pinned|saved for inspo|'
    r'c\'est mon objectif|objectif atteint|objectif de vie'
    r')\b',
    re.IGNORECASE,
)

_PODCAST_LISTENER_RE = re.compile(
    r'\b('
    # French
    r'j\'[ée]coute (le |la |ce |un )?podcast|je viens de finir l\'[ée]pisode|'
    r'[ée]cout[ée] l\'[ée]pisode|podcast de|dans le podcast|sur le podcast|'
    r'j\'ai (entendu|[ée]cout[ée]).{0,20}podcast|dans l\'[ée]pisode de|'
    r'mon podcast pr[ée]f[ée]r[ée]|je r[ée][ée]coute|cet [ée]pisode est|'
    # English
    r'i (listen|listened) to.{0,15}podcast|just finished.{0,15}episode|'
    r'this episode|on the podcast|podcast listener|my favorite podcast|'
    r'episode of|currently listening to|love this podcast|'
    r'podcast changed my life|binge[- ]listening'
    r')\b',
    re.IGNORECASE,
)

_BOOK_READER_RE = re.compile(
    r'\b('
    # French
    r'je viens de finir (le livre|ce livre|atomic|the|un livre)|'
    r'en train de lire|je lis (en ce moment|actuellement|ce livre)|'
    r'lecture du moment|je recommande ce livre|lu ce livre|'
    r'livre qui (a chang[ée]|m\'a chang[ée]|m\'a transform[ée])|'
    r'ce livre est (incroyable|[ée]tonnant|puissant)|'
    # English
    r'just finished (reading|the book)|currently reading|'
    r'this book (changed|is amazing|blew my mind|helped me)|'
    r'highly recommend (this book|reading)|book review|'
    r'reading (atomic habits|the alchemist|can\'t hurt me|mindset|the subtle art|'
    r'rich dad|think and grow|ikigai|essentialism|deep work|'
    r'l\'alchimiste|les quatre accords|l\'[ée]l[ée]ment|puissance|psycho-cybern|'
    r'influence|obstacle is the way|man\'s search for meaning)'
    r')\b',
    re.IGNORECASE,
)

_COURSE_DROPOUT_RE = re.compile(
    r'('
    # French — bought but didn't finish
    r'j\'ai acheté la formation (mais|et|pourtant)|'
    r'je me suis arrêt[ée] au module|j\'ai pas fini (la formation|le cours|le programme)|'
    r'j\'ai lâch[ée] (la formation|le cours|le programme|la moitié)|'
    r'j\'ai commenc[ée] (la formation|le cours|le programme) (mais|et puis)|'
    r'formation (inachev[ée]|pas termin[ée]|abandon[ée]e)|'
    r'j\'ai (achet[ée]|pay[ée]) (la formation|le cours|un programme).{0,50}(mais|jamais|fini|termin[ée])|'
    # English — course dropout signals
    r'bought (the course|a course|this course|the program).{0,50}(but|never|didn\'t|unfinished)|'
    r'(didn\'t|never) finish(ed)?.{0,20}(course|program|module)|'
    r'stopped at (module|chapter|week|lesson)|'
    r'halfway through (the course|the program)|'
    r'signed up (for|to).{0,20}(course|program).{0,30}(but|never completed|still haven\'t)|'
    r'still haven\'t finished.{0,20}(course|program|training)'
    r')',
    re.IGNORECASE,
)

_AUTHORITY_SEEKER_RE = re.compile(
    r'\b('
    r'cherche (un |une )?expert|cherche (un |une )?mentor|cherche (un |une )?sp[ée]cialiste|'
    r'recommandez[- ]moi|quelqu\'un de recommand[ée]|je cherche (un |une )?(bon|bonne)|'
    r'looking for (an )?expert|looking for a mentor|recommend (someone|anyone)|'
    r'who should i (hire|work with|trust)'
    r')\b',
    re.IGNORECASE,
)

_SPEED_URGENCY_RE = re.compile(
    r'\b('
    r'vite|urgent(e|ly)?|maintenant|tout de suite|ASAP|dès que possible|'
    r'j\'ai besoin de r[ée]sultats (rapides?|vite)|je veux des r[ée]sultats (rapidement|maintenant)|'
    r'i need results (fast|quickly|now|asap)|need this (fast|quickly|now|urgently)|'
    r'no time to waste|pas de temps [àa] perdre'
    r')\b',
    re.IGNORECASE,
)

_MULTIPLE_FAILED_RE = re.compile(
    r'('
    r'j\'ai essay[ée] pendant (des ann[ée]es?|[2-9]|1[0-9])\s*(mois|an)|'
    r'[ée]a fait ([2-9]|1[0-9]) (ans?|ann[ée]es?) que j\'essaie|'
    r'rien n\'a fonctionn[ée]|rien ne marche|rien ne fonctionne|'
    r'i\'ve been trying for (years?|months)|nothing (has |ever )worked|'
    r'years of trying|tried everything for (months|years)|'
    r'i\'ve tried.{0,30}(nothing|didn\'t|doesn\'t) work'
    r')',
    re.IGNORECASE,
)

_PUBLIC_COMMITMENT_RE = re.compile(
    r'\b('
    r'j\'ai annonc[ée] [àa] tout le monde|tout le monde sait que|je me suis engag[ée] publiquement|'
    r'j\'ai dit [àa] (ma famille|mes amis|mon conjoint|mes collègues)|accountability partner|'
    r'i told everyone|i announced|public accountability|i committed to|'
    r'made a promise|everyone knows i\'m'
    r')\b',
    re.IGNORECASE,
)

_HEALTH_CRISIS_RE = re.compile(
    r'\b('
    r'burnout|burn[- ]out|[ée]puis[ée](e)?|[àa] bout|cong[ée] maladie|arr[êe]t maladie|'
    r'j\'ai (failli|faillit)|crise d\'anxiété|crise de panique|[ée]pilepsie|'
    r'j\'ai (coll[ée]|cracké)|j\'ai pas dormi|insomnies|anxiété chronique|'
    r'health scare|health crisis|panic attack|anxiety attack|'
    r'i broke down|mental breakdown|i crashed|not sleeping'
    r')\b',
    re.IGNORECASE,
)

_SOCIAL_COMPARISON_RE = re.compile(
    r'\b('
    r'tout le monde autour de moi|mes amis ont tous|ils ont (r[ée]ussi|un travail|une maison)|'
    r'j\'[ée]tais le seul [àa] pas|pourquoi pas moi|je suis le seul|'
    r'everyone around me|all my friends|why not me|i\'m the only one (who|that)|'
    r'left behind|falling behind everyone|everyone else has'
    r')\b',
    re.IGNORECASE,
)

_SPECIFIC_OUTCOME_RE = re.compile(
    r'('
    r'\d+\s*(kg|kilos?|pounds?|lbs?).{0,20}(perdre|lose|drop|mincir)|'
    r'(gagner|earn|make).{0,20}[€$£]\s*\d{3,}|'
    r'\d{3,}\s*[€$£].{0,20}(mois|month)|'
    r'(objectif|goal|target).{0,30}\d+|'
    r'(quitter|leave|quit).{0,20}(9[–-]5|mon travail|my job|bureau|office)'
    r')',
    re.IGNORECASE,
)

_PREMIUM_SIGNALS_RE = re.compile(
    r'\b('
    # Luxury brand mentions
    r'louis vuitton|gucci|prada|chanel|hermès|dior|rolex|omega|cartier|'
    r'porsche|ferrari|lamborghini|tesla model s|model x|bentley|maserati|'
    # Premium travel/lifestyle
    r'première classe|business class|first class|private jet|yacht|villa privée|'
    r'5 étoiles|five star|hôtel de luxe|resort|maldives|dubai|saint-barth|'
    # Premium spending on self-development
    r'mastermind|retraite de|retreat|vip day|private coaching|1-on-1|high[- ]ticket|'
    # Financial success signals
    r'chiffre d\'affaires|revenus passifs|liberté financière|indépendance financière|'
    r'financial freedom|passive income|six figures|7 figures|mrr|arr'
    r')\b',
    re.IGNORECASE,
)

_BUDGET_SIGNALS_RE = re.compile(
    r'\b('
    r'pas les moyens|trop cher pour moi|j\'ai pas l\'argent|budget serré|'
    r'j\'économise pour|j\'arrive pas à joindre les deux bouts|'
    r'can\'t afford|too expensive for me|broke right now|on a tight budget|'
    r'saving up for|living paycheck'
    r')\b',
    re.IGNORECASE,
)

_FAST_TRUSTER_RE = re.compile(
    r'\b('
    # Decisive action language
    r'je l\'ai fait|je me suis lanc[ée]|j\'ai pris le risque|j\'y vais|c\'est parti|'
    r'j\'ai saut[ée] le pas|j\'ai d[ée]cid[ée] (direct|sur le coup|immédiatement)|'
    r'j\'ai pas h[ée]sit[ée]|d[ée]cision prise|coup de cœur|coup de t[eê]te|'
    r'i did it|i went for it|i took the leap|just signed up|pulled the trigger|'
    r'let\'s go|i\'m in|best decision|no regrets|i jumped in'
    r')\b',
    re.IGNORECASE,
)

_SLOW_TRUSTER_RE = re.compile(
    r'\b('
    # Overthinking, hesitation
    r'j\'h[ée]site|je r[ée]fl[ée]chis encore|je suis pas s[uû]r(e)?|'
    r'faut que je v[ée]rifie|j\'ai besoin de temps|c\'est une grosse d[ée]cision|'
    r'je vais y r[ée]fl[ée]chir|peut-[eê]tre un jour|[ée]ventuellement|'
    r'i\'m not sure|let me think about|need to research first|maybe someday|'
    r'not ready yet|need more information|gotta think about it|i\'ll consider'
    r')\b',
    re.IGNORECASE,
)

_LIFE_TRANSITION_RE = re.compile(
    r'\b('
    # French — change-mode states
    r'nouveau (travail|boulot|job|poste)|nouvel emploi|pris(e)? un nouveau poste|'
    r'je viens de d[ée]m[ée]nager|j\'ai d[ée]m[ée]nag[ée]|nouveau chez moi|'
    r'je viens d\'emm[ée]nager|nouvelle ville|nouveau pays|nouvelle vie dans|'
    r'c[ée]libataire (depuis|maintenant|à nouveau)|de nouveau c[ée]libataire|'
    r'en couple (depuis|maintenant)|nouvelle relation|nouveau partenaire|'
    r'vient d\'obtenir (son|mon) dipl[ôo]me|diplôm[ée]e? (cette ann[ée]|r[ée]cemment)|'
    r'(vient de|je viens de) finir (mes|les) [ée]tudes|'
    r'retraite (depuis|prochainement|bient[ôo]t)|je prends ma retraite|'
    # English — life transition triggers
    r'new job|just started (a new|my new) job|got (a new|the) job|'
    r'just moved (to|into|here)|new city|new country|new apartment|'
    r'single (again|now|since)|newly single|just broke up|'
    r'new relationship|just started dating|in a new relationship|'
    r'just graduated|graduated (this year|recently)|'
    r'empty nest(er)?|kids (left|moved out)|'
    r'retiring (soon|next|this year)|just retired'
    r')\b',
    re.IGNORECASE,
)


def _analyze_voice_tone(text: str) -> int:
    """
    Feature 5: Voice Tone Analysis.
    Scores emotional intensity 0-100 purely from text signals.
    High emotion = high pain = higher urgency lead.
    """
    if not text:
        return 0
    score = 0
    words = text.split()

    exclamations = text.count('!') + text.count('！')
    score += min(exclamations * 5, 25)

    caps_words = sum(1 for w in words if w.isupper() and len(w) > 2)
    score += min(caps_words * 8, 30)

    # Pain/distress emojis
    pain_emojis = len(re.findall(r'[😭😢😤😰😩😫🥺💔😞😔🤦🤯😱😣😖]', text))
    score += min(pain_emojis * 10, 25)

    ellipsis = text.count('...') + text.count('…')
    score += min(ellipsis * 4, 15)

    # Repeated punctuation ?! indicates emotional state
    repeated = len(re.findall(r'[?!]{2,}', text))
    score += min(repeated * 8, 20)

    return min(score, 100)


def _detect_signals(lead_data: dict) -> dict:
    text = f"{lead_data.get('bio', '')} {lead_data.get('posts_summary', '')}".strip()
    voice_tone = _analyze_voice_tone(text)

    is_premium = bool(_PREMIUM_SIGNALS_RE.search(text))
    is_budget = bool(_BUDGET_SIGNALS_RE.search(text))
    price_tier = "premium" if is_premium else ("budget" if is_budget else "mid")

    is_fast = bool(_FAST_TRUSTER_RE.search(text))
    is_slow = bool(_SLOW_TRUSTER_RE.search(text))
    trust_velocity = "fast" if is_fast and not is_slow else ("slow" if is_slow else "unknown")

    sigs = {
        # Behavioral signals
        "hot_prospect":        bool(_HOT_PROSPECT_RE.search(text)),
        "podcast_listener":    bool(_PODCAST_LISTENER_RE.search(text)),
        "book_reader":         bool(_BOOK_READER_RE.search(text)),
        "follows_coaches":     bool(_FOLLOWS_COACHES_RE.search(text)),
        # Psychological signals
        "pain_peak":           bool(_PAIN_PEAK_RE.search(text)),
        "before_after_seeker": bool(_BEFORE_AFTER_RE.search(text)),
        "social_comparison":   bool(_SOCIAL_COMPARISON_RE.search(text)),
        "health_crisis":       bool(_HEALTH_CRISIS_RE.search(text)),
        "public_commitment":   bool(_PUBLIC_COMMITMENT_RE.search(text)),
        # Temporal signals
        "life_event":          bool(_LIFE_EVENT_RE.search(text)),
        "life_transition":     bool(_LIFE_TRANSITION_RE.search(text)),
        "speed_urgency":       bool(_SPEED_URGENCY_RE.search(text)),
        "specific_outcome":    bool(_SPECIFIC_OUTCOME_RE.search(text)),
        # Intent signals
        "buying_intent":       bool(_BUYING_INTENT_RE.search(text)),
        "authority_seeker":    bool(_AUTHORITY_SEEKER_RE.search(text)),
        "course_dropout":      bool(_COURSE_DROPOUT_RE.search(text)),
        # Financial signals
        "failed_purchase":     bool(_FAILED_PURCHASE_RE.search(text)),
        "multiple_failed":     bool(_MULTIPLE_FAILED_RE.search(text)),
        # Computed signals
        "voice_tone_intensity": voice_tone,
        "price_tier":          price_tier,
        "trust_velocity":      trust_velocity,
    }
    return sigs


# ---------------------------------------------------------------------------
# Main qualifier
# ---------------------------------------------------------------------------

def qualify_lead(
    lead_data: dict,
    coach_niche: str,
    coach_offer: str,
    icp_pain_points: list[str] | None = None,
) -> dict:
    """
    Scores lead 0-100, builds psychographic profile, predicts response probability.
    All in one Claude call. Deterministic signal boosts applied after.

    Returns:
        score, reason, pain_points, recommended_angle,
        psychographic {dominant_emotion, awareness_stage, communication_style,
                        best_contact_time, language},
        response_probability
    """
    signals = _detect_signals(lead_data)

    pains_block = ""
    if icp_pain_points:
        pains_block = "\nPains the coach's ICP typically expresses:\n" + \
                      "\n".join(f"  - {p}" for p in icp_pain_points) + "\n"

    signal_context = ""
    if any(signals.values()):
        detected = []
        if signals["buying_intent"]:
            detected.append("💳 BUYING INTENT — actively asking about solutions or costs")
        if signals["life_event"]:
            detected.append("⚡ LIFE EVENT — major personal transition detected")
        if signals["follows_coaches"]:
            detected.append("👁 FOLLOWS COACHES — references coaches/programs they watch")
        if signals["hot_prospect"]:
            detected.append("🔥 HOT PROSPECT — repeatedly engages with solution content")
        if signals["pain_peak"]:
            detected.append("🚨 PAIN PEAK — at maximum emotional vulnerability right now")
        if signals["failed_purchase"]:
            detected.append("💔 FAILED BUYER — bought coaching before, got burned; still wants results")
        if signals["before_after_seeker"]:
            detected.append("🎯 TRANSFORMATION SEEKER — actively looking for before/after results")
        if signals["podcast_listener"]:
            detected.append("🎙 PODCAST LISTENER — consumes audio content, educated and primed for coaching")
        if signals["book_reader"]:
            detected.append("📚 BOOK READER — reading self-development books, high growth mindset")
        if signals["course_dropout"]:
            detected.append("🎓 COURSE DROPOUT — bought a course but didn't finish, needs accountability/guidance")
        if signals["life_transition"]:
            detected.append("🔄 LIFE TRANSITION — in active change mode (job/move/relationship/graduation)")
        if signals["authority_seeker"]:
            detected.append("🔍 AUTHORITY SEEKER — actively looking for an expert/mentor right now")
        if signals["speed_urgency"]:
            detected.append("⏰ SPEED URGENCY — wants fast results, high urgency signal")
        if signals["multiple_failed"]:
            detected.append("🔁 MULTIPLE FAILED ATTEMPTS — tried for years, deeply frustrated, highly receptive")
        if signals["public_commitment"]:
            detected.append("📢 PUBLIC COMMITMENT — told people about their goal, accountability pressure")
        if signals["health_crisis"]:
            detected.append("🏥 HEALTH CRISIS — burnout/physical/mental crisis, extreme urgency")
        if signals["social_comparison"]:
            detected.append("👥 SOCIAL COMPARISON — feels left behind by peers, strong motivation")
        if signals["specific_outcome"]:
            detected.append("🎯 SPECIFIC OUTCOME — has a very clear measurable goal, serious buyer signal")
        if signals["voice_tone_intensity"] >= 60:
            detected.append(f"📣 HIGH EMOTIONAL INTENSITY — voice tone score {signals['voice_tone_intensity']}/100 (caps, exclamations, pain emojis)")
        if signals["price_tier"] == "premium":
            detected.append("💎 PREMIUM PROSPECT — luxury/high-spending signals detected")
        elif signals["price_tier"] == "budget":
            detected.append("⚠️ BUDGET SIGNALS — affordability concern likely")
        if signals["trust_velocity"] == "fast":
            detected.append("⚡ FAST TRUSTER — decisive action language, direct offer may work")
        elif signals["trust_velocity"] == "slow":
            detected.append("🐢 SLOW TRUSTER — hesitation patterns, nurture sequence recommended")
        signal_context = "\n\nPRE-DETECTED SIGNALS (47-SIGNAL MODEL):\n" + "\n".join(detected) + "\n"

    prompt = f"""You are an expert at identifying people who are actively struggling with a problem and are likely to buy a coaching solution.

Coach niche: {coach_niche}
Coach offer: {coach_offer}{pains_block}{signal_context}
Profile:
- Name: {lead_data.get("name", "Unknown")}
- Handle: @{lead_data.get("handle", "")}
- Platform: {lead_data.get("platform", "instagram")}
- Bio: {lead_data.get("bio", "No bio")}
- Followers: {lead_data.get("followers", 0):,}
- Content summary: {lead_data.get("posts_summary", "N/A")}

Respond ONLY with valid JSON (no markdown):
{{
  "score": <0-100 pain/fit score>,
  "reason": "<2-3 sentences explaining specific signals>",
  "pain_points": ["<exact pain from their content>", ...],
  "recommended_angle": "<single most resonant pain to open DM with>",
  "psychographic": {{
    "dominant_emotion": "<frustration|fear|hope|excitement|shame|anxiety>",
    "awareness_stage": "<unaware|problem_aware|solution_aware|product_aware>",
    "communication_style": "<casual|formal>",
    "best_contact_time": "<morning|evening|weekend|anytime>",
    "language": "<fr|en|es|pt|ar|other>"
  }},
  "response_probability": <0-100 likelihood they reply to a personalized DM>,
  "predicted_objection": "<their single most likely objection to buying, e.g. 'pas les moyens', 'pas le temps', 'déjà essayé', 'pas sûr que ça marche pour moi'>",
  "aspiration_gap": <0-100 score — distance between their expressed dream life and current reality; 0=no gap detectable, 100=extreme gap/strong transformation desire>
}}

Scoring guide: 85-100 actively venting/explicit pain · 65-84 clear signals · 40-64 indirect · 15-39 weak · 0-14 wrong audience/brand/competitor
response_probability: consider activity level, pain intensity, awareness stage, engagement patterns
predicted_objection: infer from their communication style, awareness stage, and content — be specific to THIS person"""

    msg = _get_client().messages.create(
        model="claude-opus-4-7",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text
    start, end = text.find("{"), text.rfind("}") + 1
    result = json.loads(text[start:end])

    # Normalise types
    score = max(0, min(100, int(result.get("score", 0))))
    result.setdefault("reason", "")
    result.setdefault("pain_points", [])
    result.setdefault("recommended_angle", "")
    result.setdefault("psychographic", {})
    result.setdefault("response_probability", 50)
    result.setdefault("predicted_objection", "")
    result.setdefault("aspiration_gap", 0)
    result["response_probability"] = max(0, min(100, int(result["response_probability"])))
    result["aspiration_gap"] = max(0, min(100, int(result.get("aspiration_gap", 0))))

    # Attach deterministic signals that writer/downstream agents need
    result["price_tier"] = signals["price_tier"]
    result["trust_velocity"] = signals["trust_velocity"]
    result["voice_tone_intensity"] = signals["voice_tone_intensity"]

    # Deterministic signal boosts (applied after Claude scoring)
    if signals["buying_intent"]:
        score = min(95, score + 40)
    if signals["life_event"]:
        score = min(95, score + 30)
    if signals["follows_coaches"]:
        score = min(95, score + 20)
        pain_points = result["pain_points"]
        if "Suiveur de coaches" not in pain_points:
            pain_points.insert(0, "Suiveur de coaches")
        result["pain_points"] = pain_points
    if signals["hot_prospect"]:
        score = min(95, score + 15)
        result["pain_points"] = ["Prospect chaud"] + [p for p in result["pain_points"] if p != "Prospect chaud"]
    if signals["pain_peak"]:
        score = min(98, score + 25)
        pain_points = result["pain_points"]
        if "Pic de douleur" not in pain_points:
            pain_points.insert(0, "Pic de douleur")
        result["pain_points"] = pain_points
    if signals["failed_purchase"]:
        score = min(98, score + 35)
        pain_points = result["pain_points"]
        if "Acheteur raté" not in pain_points:
            pain_points.insert(0, "Acheteur raté")
        result["pain_points"] = pain_points
    if signals["before_after_seeker"]:
        score = min(95, score + 15)
        pain_points = result["pain_points"]
        if "Cherche transformation" not in pain_points:
            pain_points.append("Cherche transformation")
        result["pain_points"] = pain_points
    if signals["podcast_listener"]:
        score = min(95, score + 20)
        pain_points = result["pain_points"]
        if "Auditeur podcast" not in pain_points:
            pain_points.append("Auditeur podcast")
        result["pain_points"] = pain_points
    if signals["book_reader"]:
        score = min(95, score + 25)
        pain_points = result["pain_points"]
        if "Lecteur dev perso" not in pain_points:
            pain_points.append("Lecteur dev perso")
        result["pain_points"] = pain_points
    if signals["course_dropout"]:
        score = min(98, score + 30)
        pain_points = result["pain_points"]
        if "Dropout de formation" not in pain_points:
            pain_points.insert(0, "Dropout de formation")
        result["pain_points"] = pain_points
    if signals["life_transition"]:
        score = min(95, score + 25)
        pain_points = result["pain_points"]
        if "Transition de vie" not in pain_points:
            pain_points.append("Transition de vie")
        result["pain_points"] = pain_points
    if signals["voice_tone_intensity"] >= 60:
        score = min(95, score + 10)
    if signals["authority_seeker"]:
        score = min(95, score + 15)
        result["pain_points"] = ["Cherche un expert"] + [p for p in result["pain_points"] if p != "Cherche un expert"]
    if signals["speed_urgency"]:
        score = min(95, score + 20)
        result["pain_points"] = ["Urgence — veut des résultats vite"] + result["pain_points"]
    if signals["multiple_failed"]:
        score = min(98, score + 20)
        result["pain_points"] = ["Plusieurs tentatives échouées"] + result["pain_points"]
    if signals["public_commitment"]:
        score = min(95, score + 20)
        result["pain_points"].append("Engagement public")
    if signals["health_crisis"]:
        score = min(98, score + 25)
        result["pain_points"].insert(0, "Crise de santé / burnout")
    if signals["social_comparison"]:
        score = min(95, score + 15)
        result["pain_points"].append("Comparaison sociale")
    if signals["specific_outcome"]:
        score = min(95, score + 15)
        result["pain_points"].append("Objectif précis et mesurable")
    if signals["price_tier"] == "premium":
        pain_points = result["pain_points"]
        if "Prospect premium" not in pain_points:
            pain_points.append("Prospect premium")
        result["pain_points"] = pain_points
    if signals["trust_velocity"] == "fast":
        pain_points = result["pain_points"]
        if "Décideur rapide" not in pain_points:
            pain_points.append("Décideur rapide")
        result["pain_points"] = pain_points

    result["score"] = score

    # Structured 47-signal breakdown for display
    result["score_breakdown"] = {
        "behavioral": {k: signals[k] for k in ["hot_prospect", "podcast_listener", "book_reader", "follows_coaches"]},
        "psychological": {k: signals[k] for k in ["pain_peak", "before_after_seeker", "social_comparison", "health_crisis", "public_commitment"]},
        "temporal": {k: signals[k] for k in ["life_event", "life_transition", "speed_urgency", "specific_outcome"]},
        "intent": {k: signals[k] for k in ["buying_intent", "authority_seeker", "course_dropout"]},
        "financial": {k: signals[k] for k in ["failed_purchase", "multiple_failed"]},
        "voice_tone": signals["voice_tone_intensity"],
        "price_tier": signals["price_tier"],
        "trust_velocity": signals["trust_velocity"],
    }
    return result


# ---------------------------------------------------------------------------
# Cross-platform identity matching
# ---------------------------------------------------------------------------

_PLATFORM_URL_MAP = {
    "instagram": "instagram.com",
    "tiktok": "tiktok.com",
    "twitter": "twitter.com",
    "linkedin": "linkedin.com",
    "youtube": "youtube.com",
    "reddit": "reddit.com",
}


def enrich_cross_platform(handle: str, base_platform: str) -> str:
    """
    Search for the same handle on other platforms via DDG.
    Returns additional posts_summary context merged from other platforms.
    Called before qualification to give Claude richer data — no extra API cost.
    """
    other_platforms = [p for p in _PLATFORM_URL_MAP if p != base_platform]
    extra_snippets: list[str] = []

    for platform in other_platforms[:3]:  # check up to 3 other platforms
        site = _PLATFORM_URL_MAP[platform]
        query = f'site:{site} "{handle}"'
        try:
            resp = httpx.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers=BROWSER_HEADERS,
                timeout=8,
                follow_redirects=True,
            )
            # Extract first snippet that contains the exact handle
            snippets = re.findall(
                r'class="result__snippet">(.*?)</a>',
                resp.text,
                re.DOTALL,
            )
            for raw in snippets[:2]:
                text = re.sub(r'<[^>]+>', '', raw).strip()
                if handle.lower() in text.lower() and len(text) > 30:
                    extra_snippets.append(f"[{platform}] {text[:200]}")
                    break
        except Exception:
            pass

    return " | ".join(extra_snippets) if extra_snippets else ""
