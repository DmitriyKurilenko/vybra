#!/usr/bin/env bash
# cert.sh — Управление TLS-сертификатом Let's Encrypt
#
# Использование:
#   sudo ./scripts/cert.sh init   — получить сертификат (standalone, ~30 сек)
#   sudo ./scripts/cert.sh renew  — обновить сертификат
#
# Конфигурация из .env: CERTBOT_EMAIL, DOMAIN, WWW_DOMAIN
#
set -Eeuo pipefail

[[ "$EUID" -eq 0 ]] || { echo "[FAIL] Запустите от root: sudo $0" >&2; exit 1; }

# ─── Корень проекта ───────────────────────────────────────────────────────────
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# ─── Загрузка .env ────────────────────────────────────────────────────────────
SCRIPTS_ENV="$ROOT_DIR/.env"
if [[ -f "$SCRIPTS_ENV" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$SCRIPTS_ENV"
  set +a
fi

# ─── Переменные ───────────────────────────────────────────────────────────────
CERTBOT_EMAIL="${CERTBOT_EMAIL:-}"
DOMAIN="${DOMAIN:-}"
WWW_DOMAIN="${WWW_DOMAIN:-}"

# ─── Утилиты ──────────────────────────────────────────────────────────────────
log()  { echo "==> $*"; }
die()  { echo "[FAIL] $*" >&2; exit 1; }

# ─── Справка ──────────────────────────────────────────────────────────────────
_usage() {
  cat <<EOF
Использование: sudo $0 <init|renew> [опции]

Подкоманды:
  init    Получить новый сертификат (standalone, nginx кратко останавливается)
  renew   Обновить существующий сертификат

Опции (для init):
  --email  <email>   E-mail для уведомлений Let's Encrypt
  --domain <domain>  Основной домен
  --www    <www>     www-вариант домена

Переменные .env: CERTBOT_EMAIL, DOMAIN, WWW_DOMAIN
EOF
}

# ─── Подкоманда ────────────────────────────────────────────────────────────────
SUBCOMMAND="${1:-}"
shift || true

if [[ -z "$SUBCOMMAND" || "$SUBCOMMAND" == "-h" || "$SUBCOMMAND" == "--help" ]]; then
  _usage; exit 0
fi

# ─── Установка certbot ────────────────────────────────────────────────────────
_ensure_certbot() {
  if command -v certbot >/dev/null 2>&1; then
    return
  fi
  log "certbot не найден — устанавливаю..."
  if command -v snap >/dev/null 2>&1; then
    snap install --classic certbot
    ln -sf /snap/bin/certbot /usr/bin/certbot
  elif command -v apt-get >/dev/null 2>&1; then
    apt-get update -qq && apt-get install -y certbot
  else
    die "Не удалось установить certbot (нет snap и apt-get)"
  fi
  log "certbot установлен"
}

# ─── INIT: получение нового сертификата ────────────────────────────────────────
_cmd_init() {
  # CLI-аргументы
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --email)   CERTBOT_EMAIL="${2:?Укажите email после --email}";  shift 2 ;;
      --domain)  DOMAIN="${2:?Укажите домен после --domain}";        shift 2 ;;
      --www)     WWW_DOMAIN="${2:?Укажите www-домен после --www}";   shift 2 ;;
      -h|--help) _usage; exit 0 ;;
      *) die "Неизвестный аргумент: $1" ;;
    esac
  done

  # Валидация
  [[ -n "$CERTBOT_EMAIL" ]] || die "CERTBOT_EMAIL обязателен (--email или .env)"
  [[ -n "$DOMAIN" ]]        || die "DOMAIN обязателен (--domain или .env)"

  if [[ "$DOMAIN" == "localhost" || "$DOMAIN" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    die "'$DOMAIN' не является реальным DNS-именем"
  fi

  if [[ ! "$CERTBOT_EMAIL" =~ ^[^@]+@[^@]+\.[^@]+$ ]]; then
    die "'$CERTBOT_EMAIL' не похоже на корректный e-mail"
  fi

  _ensure_certbot

  # Аргументы certbot
  CERTBOT_DOMAIN_ARGS=("-d" "$DOMAIN")
  if [[ -n "$WWW_DOMAIN" && "$WWW_DOMAIN" != "$DOMAIN" ]]; then
    CERTBOT_DOMAIN_ARGS+=("-d" "$WWW_DOMAIN")
  fi

  log "Получение TLS-сертификата Let's Encrypt"
  echo "  Домен(ы) : ${CERTBOT_DOMAIN_ARGS[*]//-d /}"
  echo "  E-mail   : $CERTBOT_EMAIL"
  echo "  Метод    : standalone (nginx кратко останавливается)"
  echo ""

  # Останавливаем nginx, гарантируем рестарт при выходе
  NGINX_WAS_RUNNING=0
  if systemctl is-active --quiet nginx 2>/dev/null; then
    NGINX_WAS_RUNNING=1
    log "Останавливаю nginx..."
    systemctl stop nginx
  fi

  trap '{
    if [[ "$NGINX_WAS_RUNNING" -eq 1 ]]; then
      log "Запускаю nginx обратно..."
      systemctl start nginx || true
    fi
  }' EXIT

  # Получение сертификата
  certbot certonly \
    --standalone \
    --non-interactive \
    --agree-tos \
    --email "$CERTBOT_EMAIL" \
    "${CERTBOT_DOMAIN_ARGS[@]}"

  echo ""
  log "Сертификат получен"
  echo "  Fullchain : /etc/letsencrypt/live/$DOMAIN/fullchain.pem"
  echo "  Privkey   : /etc/letsencrypt/live/$DOMAIN/privkey.pem"
  echo ""
  echo "Следующий шаг: настройте nginx в HTTPS-режиме:"
  echo "  sudo ./scripts/nginx-setup.sh --mode post"
}

# ─── RENEW: обновление сертификата ─────────────────────────────────────────────
_cmd_renew() {
  _ensure_certbot

  log "Обновление Let's Encrypt сертификата"

  certbot renew \
    --quiet \
    --pre-hook  "systemctl stop nginx  || true" \
    --post-hook "systemctl start nginx || true"

  log "Обновление завершено"
}

# ─── Диспетчер подкоманд ───────────────────────────────────────────────────────
case "$SUBCOMMAND" in
  init)   _cmd_init "$@" ;;
  renew)  _cmd_renew "$@" ;;
  *)      echo "Неизвестная подкоманда: $SUBCOMMAND"; _usage; exit 1 ;;
esac
