#!/usr/bin/env bash
# cert-renew.sh — Обновление TLS-сертификата Let's Encrypt
#
# Запускайте вручную или добавьте в cron (обычно certbot обновляет сам через systemd/cron):
#   0 3 * * 1 /path/to/vybra/scripts/cert-renew.sh >> /var/log/cert-renew.log 2>&1
#
# Переменные окружения (опциональные):
#   ENV_FILE               Путь к env-файлу (по умолчанию .env)
#   PRIMARY_COMPOSE_FILE   Базовый compose-файл (по умолчанию docker-compose.yml)
#   SECONDARY_COMPOSE_FILE Override compose    (по умолчанию docker-compose.prod.yml)
#
set -Eeuo pipefail

# ─── Определяем корень проекта (скрипт лежит в scripts/) ──────────────────
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# ─── Загрузка .env ────────────────────────────────────────────────────
SCRIPTS_ENV="$ROOT_DIR/.env"
if [[ -f "$SCRIPTS_ENV" ]]; then
  # shellcheck source=/dev/null
  set -a; source "$SCRIPTS_ENV"; set +a
fi

CERTBOT_WEBROOT="${CERTBOT_WEBROOT:-/var/www/certbot}"
ENV_FILE="${ENV_FILE:-.env}"
PRIMARY_COMPOSE_FILE="${PRIMARY_COMPOSE_FILE:-docker-compose.yml}"
SECONDARY_COMPOSE_FILE="${SECONDARY_COMPOSE_FILE:-docker-compose.prod.yml}"

COMPOSE_ARGS=(-f "$PRIMARY_COMPOSE_FILE")
if [[ -f "$SECONDARY_COMPOSE_FILE" ]]; then
  COMPOSE_ARGS+=(-f "$SECONDARY_COMPOSE_FILE")
fi

compose_cmd() {
  docker compose --env-file "$ENV_FILE" "${COMPOSE_ARGS[@]}" "$@"
}

log() { echo "==> [$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

# ─── Проверки ─────────────────────────────────────────────────────────────────
if ! command -v certbot >/dev/null 2>&1; then
  log "certbot не найден — устанавливаю..."
  if command -v apt-get >/dev/null 2>&1; then
    apt-get update -qq && apt-get install -y certbot
  elif command -v snap >/dev/null 2>&1; then
    snap install --classic certbot
    ln -sf /snap/bin/certbot /usr/bin/certbot
  else
    echo "ОШИБКА: не знаю как установить certbot (нет apt-get и snap)" >&2
    exit 1
  fi
fi

# ─── Обновление сертификата ───────────────────────────────────────────────────
log "Обновление Let's Encrypt сертификата"
sudo certbot renew \
  --webroot \
  -w "$CERTBOT_WEBROOT" \
  --quiet \
  --deploy-hook "systemctl reload nginx || true"

log "Certbot завершил работу (exit: $?)"

# ─── Опциональный рестарт web-контейнера ─────────────────────────────────────
# Нужен только если сертификаты монтируются внутрь контейнера (nginx-in-docker).
# При host-level nginx — этот шаг не требуется, certbot --deploy-hook уже перезагружает nginx.
#
# Раскомментируйте строку ниже, если используете nginx внутри Docker:
# compose_cmd restart web && log "web-контейнер перезапущен"

log "Обновление завершено"
