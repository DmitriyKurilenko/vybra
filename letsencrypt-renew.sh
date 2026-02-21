#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ENV_FILE=${ENV_FILE:-".env.prod"}
PRIMARY_COMPOSE_FILE=${PRIMARY_COMPOSE_FILE:-"docker-compose.yml"}
SECONDARY_COMPOSE_FILE=${SECONDARY_COMPOSE_FILE:-"docker-compose.prod.yml"}

COMPOSE_ARGS=(-f "$PRIMARY_COMPOSE_FILE")
if [[ -n "$SECONDARY_COMPOSE_FILE" ]] && [[ -f "$SECONDARY_COMPOSE_FILE" ]]; then
  COMPOSE_ARGS+=(-f "$SECONDARY_COMPOSE_FILE")
fi

compose_cmd() {
  docker compose --env-file "$ENV_FILE" "${COMPOSE_ARGS[@]}" "$@"
}

if ! command -v certbot >/dev/null 2>&1; then
  echo "certbot is not installed."
  exit 1
fi

echo "==> Renewing Let's Encrypt certificates"
sudo certbot renew --webroot -w /var/www/certbot --quiet --deploy-hook "systemctl reload nginx || true"

echo "==> Restarting web service to pick up fresh certificates (if mounted)"
compose_cmd restart web

echo "==> Renewal done"
