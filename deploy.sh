#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

# ── Pre-flight checks ─────────────────────────────────────────────────────────

if ! command -v docker &>/dev/null; then
  echo -e "${RED}ERROR: docker is not installed.${NC}"
  exit 1
fi

if ! docker compose version &>/dev/null; then
  echo -e "${RED}ERROR: docker compose (v2) is not available.${NC}"
  exit 1
fi

if [ ! -f .env ]; then
  echo -e "${YELLOW}No .env file found. Creating one from .env.example…${NC}"
  cp .env.example .env
  echo -e "${RED}IMPORTANT: Edit .env and set your ANTHROPIC_API_KEY and JWT_SECRET, then re-run this script.${NC}"
  exit 1
fi

# Warn if critical vars are still placeholders
if grep -qE "^ANTHROPIC_API_KEY=sk-ant-xxx" .env; then
  echo -e "${RED}ERROR: ANTHROPIC_API_KEY in .env is still the placeholder value. Set a real key.${NC}"
  exit 1
fi
if grep -qE "^JWT_SECRET=change-me" .env; then
  echo -e "${YELLOW}WARNING: JWT_SECRET is still the default. Generate one with: openssl rand -hex 32${NC}"
fi

# ── Build & launch ────────────────────────────────────────────────────────────

echo -e "${GREEN}Building images…${NC}"
docker compose build --pull

echo -e "${GREEN}Starting services…${NC}"
docker compose up -d

# ── Health check ──────────────────────────────────────────────────────────────

echo -n "Waiting for backend"
for i in $(seq 1 30); do
  if docker compose exec -T backend \
       python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" \
       &>/dev/null; then
    echo -e " ${GREEN}OK${NC}"
    break
  fi
  echo -n "."
  sleep 2
done

echo ""
echo -e "${GREEN}✓ LeanLead is live at http://localhost${NC}"
echo ""
echo "  Useful commands:"
echo "    docker compose logs -f          # follow logs"
echo "    docker compose down             # stop"
echo "    docker compose down -v          # stop + delete database volume"
echo "    docker compose pull && ./deploy.sh  # upgrade"
