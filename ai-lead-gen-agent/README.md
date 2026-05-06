# 🤖 AI Lead Gen — Coachs Francophones

Système multi-agents de prospection automatique sur les réseaux sociaux,
conçu pour les coachs francophones (business, fitness, mindset, spirituel).

---

## Architecture

```
POST /qualify  ──►  qualifier_agent  ──►  writer_agent  ──►  Airtable (CRM)
POST /reply    ──►  reply_agent      ──►  Airtable (CRM)
GET  /pipeline ──►  Airtable stats
POST /webhook  ──►  routage automatique (ManyChat / Instagram)
```

### Les 4 agents

| Agent | Rôle |
|---|---|
| `qualifier_agent` | Scrape un profil social, score le lead (0-100) via Claude |
| `writer_agent` | Génère un opener DM personnalisé + séquence J2/J4/J7 |
| `reply_agent` | Classifie une réponse et génère la réplique contextuelle |
| `crm_agent` | Synchronise tout dans Airtable, envoie le résumé quotidien |

---

## Prérequis

- Python 3.11+
- Compte [Anthropic](https://console.anthropic.com/) (clé API)
- Compte [Apify](https://apify.com/) (scraping TikTok / Instagram / YouTube)
- Base [Airtable](https://airtable.com/) configurée (voir ci-dessous)
- Lien [Calendly](https://calendly.com/) actif

---

## Installation

### 1. Cloner et installer les dépendances

```bash
git clone <repo-url>
cd ai-lead-gen-agent
python -m venv .venv
source .venv/bin/activate      # Windows : .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configurer les variables d'environnement

```bash
cp .env.example .env
```

Éditer `.env` avec vos clés :

```env
ANTHROPIC_API_KEY=sk-ant-...
AIRTABLE_API_KEY=pat...
AIRTABLE_BASE_ID=app...
AIRTABLE_TABLE_NAME=Leads
APIFY_API_KEY=apify_api_...
CALENDLY_LINK=https://calendly.com/votre-nom/30min
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...   # optionnel
```

### 3. Préparer la base Airtable

Créer une table `Leads` avec les champs suivants :

| Nom du champ | Type Airtable |
|---|---|
| Name | Texte court |
| Platform | Texte court |
| Profile URL | URL |
| Niche | Texte court |
| Score | Nombre |
| Stage | Texte court (ou champ Statut) |
| Last Message | Texte long |
| Next Action | Texte long |
| Calendly Sent | Case à cocher |
| Flag Human | Case à cocher |
| Reason | Texte long |
| Last Updated | Date |

### 4. Lancer l'API

```bash
cd ai-lead-gen-agent
uvicorn api.main:app --reload --port 8000
```

L'API est accessible sur `http://localhost:8000`.
Documentation interactive : `http://localhost:8000/docs`

---

## Utilisation

### Qualifier un profil

```bash
curl -X POST http://localhost:8000/qualify \
  -H "Content-Type: application/json" \
  -d '{
    "profile_url": "https://www.instagram.com/toncoach_exemple",
    "auto_write_dm": true
  }'
```

Réponse (score >= 70) :
```json
{
  "score": 84,
  "niche": "business",
  "icp_match": true,
  "passed_threshold": true,
  "dm_sequence": {
    "opener": "...",
    "followup_d2": "...",
    "followup_d4": "...",
    "followup_d7": "..."
  },
  "airtable_record_id": "recXXXXXXXX"
}
```

### Traiter une réponse entrante

```bash
curl -X POST http://localhost:8000/reply \
  -H "Content-Type: application/json" \
  -d '{
    "record_id": "recXXXXXXXX",
    "incoming_message": "C'\''est quoi exactement ce que tu proposes ?",
    "conversation_history": [
      {"role": "agent", "content": "Salut Marie, j'\''ai vu ton post sur..."},
      {"role": "lead", "content": "Merci ! Oui c'\''est un sujet qui me tient à cœur"}
    ],
    "exchange_count": 3
  }'
```

Réponse (signal d'achat détecté) :
```json
{
  "reply": "Super question ! En gros je... Voici mon lien pour qu'\''on se parle : https://calendly.com/...",
  "classification": "BUYING_SIGNAL",
  "inject_calendly": true,
  "flag_human": false,
  "airtable_updated": true
}
```

### Voir les stats du pipeline

```bash
curl http://localhost:8000/pipeline
```

### Webhook ManyChat / Instagram

```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"event_type": "new_lead", "profile_url": "https://tiktok.com/@coach_exemple"}'
```

### Résumé quotidien (Discord)

```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"event_type": "daily_summary"}'
```

---

## Pipeline CRM

```
NEW → CONTACTED → REPLIED → BOOKED → CLOSED
```

- **NEW** : lead détecté, pas encore contacté
- **CONTACTED** : opener DM envoyé
- **REPLIED** : le prospect a répondu
- **BOOKED** : lien Calendly injecté / call réservé
- **CLOSED** : deal gagné

---

## Automatisation du résumé quotidien

Pour recevoir le résumé Discord chaque jour, configurer un cron qui appelle
le webhook à l'heure souhaitée :

```bash
# Crontab — résumé à 18h00 chaque jour
0 18 * * * curl -s -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"event_type": "daily_summary"}'
```

---

## Modèle Claude utilisé

Tous les agents utilisent `claude-sonnet-4-20250514`.
Changer le modèle dans `config.py` → `CLAUDE_MODEL`.

---

## Sécurité

- Ne jamais versionner le fichier `.env`
- Le fichier `.gitignore` inclut déjà `*.env`
- Utiliser des variables d'environnement en production (Railway, Fly.io, etc.)

---

## Contribution

Issues et PRs bienvenus. Pour toute question, ouvrir une issue GitHub.
