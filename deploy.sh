#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PRIMARY_COMPOSE_FILE=${PRIMARY_COMPOSE_FILE:-"docker-compose.yml"}
SECONDARY_COMPOSE_FILE=${SECONDARY_COMPOSE_FILE:-"docker-compose.prod.yml"}
ENV_FILE=${ENV_FILE:-".env.prod"}
SKIP_PULL=${SKIP_PULL:-0}

COMPOSE_ARGS=(-f "$PRIMARY_COMPOSE_FILE")
if [[ -n "$SECONDARY_COMPOSE_FILE" ]] && [[ -f "$SECONDARY_COMPOSE_FILE" ]]; then
  COMPOSE_ARGS+=(-f "$SECONDARY_COMPOSE_FILE")
fi

compose_cmd() {
  docker compose --env-file "$ENV_FILE" "${COMPOSE_ARGS[@]}" "$@"
}

echo "==> Deploy started: $(date '+%Y-%m-%d %H:%M:%S')"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: env file not found: $ENV_FILE"
  echo "Create it (copy from .env.prod.example) and rerun deploy."
  exit 1
fi

if [[ "$SKIP_PULL" != "1" ]] && [[ -d .git ]]; then
  echo "==> Updating repository"
  git fetch --all --prune
  git pull --ff-only
fi

if command -v npm >/dev/null 2>&1; then
  echo "==> Building frontend static assets"
  npm ci
  npm run build:css
else
  echo "==> npm not found, skipping frontend build"
fi

echo "==> Building and starting containers"
compose_cmd build --pull
compose_cmd up -d --remove-orphans

echo "==> Running Django checks"
compose_cmd exec -T web python manage.py check --deploy

echo "==> Showing container status"
compose_cmd ps

echo "==> Deploy completed: $(date '+%Y-%m-%d %H:%M:%S')"
