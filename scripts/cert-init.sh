#!/usr/bin/env bash
# cert-init.sh — Получить TLS-сертификат Let's Encrypt (метод standalone)
#
# certbot временно поднимает свой HTTP-сервер на порту 80,
# nginx кратко останавливается на время получения сертификата.
#
# Использование:
#   sudo ./scripts/cert-init.sh [--email <e>] [--domain <d>] [--www <w>]
#
# Если CERTBOT_EMAIL, DOMAIN, WWW_DOMAIN заданы в .env — аргументы
# можно не передавать.
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

# ─── Справка ──────────────────────────────────────────────────────────────────
_usage() {
  cat <<EOF
Использование: sudo $0 [--email <email>] [--domain <domain>] [--www <www>]

  --email    E-mail для уведомлений Let's Encrypt
  --domain   Основной домен, например: example.com
  --www      www-вариант, например: www.example.com

Можно задать через .env: CERTBOT_EMAIL, DOMAIN, WWW_DOMAIN

Пример:
  sudo $0 --email admin@example.com --domain example.com --www www.example.com
EOF
}

# ─── CLI-аргументы ────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --email)   CERTBOT_EMAIL="${2:?Укажите email после --email}";  shift 2 ;;
    --domain)  DOMAIN="${2:?Укажите домен после --domain}";        shift 2 ;;
    --www)     WWW_DOMAIN="${2:?Укажите www-домен после --www}";   shift 2 ;;
    -h|--help) _usage; exit 0 ;;
    *) echo "Неизвестный аргумент: $1"; _usage; exit 1 ;;
  esac
done

# ─── Валидация ────────────────────────────────────────────────────────────────
if [[ -z "$CERTBOT_EMAIL" || -z "$DOMAIN" ]]; then
  echo "ОШИБКА: CERTBOT_EMAIL и DOMAIN обязательны."
  _usage; exit 1
fi

if [[ "$DOMAIN" == "localhost" || "$DOMAIN" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "ОШИБКА: '$DOMAIN' не является реальным DNS-именем."; exit 1
fi

if [[ ! "$CERTBOT_EMAIL" =~ ^[^@]+@[^@]+\.[^@]+$ ]]; then
  echo "ОШИБКА: '$CERTBOT_EMAIL' не похоже на корректный e-mail."; exit 1
fi

# ─── Установка certbot ────────────────────────────────────────────────────────
if ! command -v certbot >/dev/null 2>&1; then
  echo "certbot не найден — устанавливаю..."
  if command -v apt-get >/dev/null 2>&1; then
    apt-get update -qq && apt-get install -y certbot
  elif command -v snap >/dev/null 2>&1; then
    snap install --classic certbot
    ln -sf /snap/bin/certbot /usr/bin/certbot
  else
    echo "ОШИБКА: не знаю как установить certbot" >&2; exit 1
  fi
  echo "✓ certbot установлен"
fi

# ─── Аргументы certbot ────────────────────────────────────────────────────────
CERTBOT_DOMAIN_ARGS=("-d" "$DOMAIN")
if [[ -n "$WWW_DOMAIN" && "$WWW_DOMAIN" != "$DOMAIN" ]]; then
  CERTBOT_DOMAIN_ARGS+=("-d" "$WWW_DOMAIN")
fi

echo "╔══════════════════════════════════════════════════════╗"
echo "║  Получение TLS-сертификата Let's Encrypt             ║"
echo "╚══════════════════════════════════════════════════════╝"
echo "  Домен(ы) : ${CERTBOT_DOMAIN_ARGS[*]//-d /}"
echo "  E-mail   : $CERTBOT_EMAIL"
echo "  Метод    : standalone (на ~30 секунд nginx остановится)"
echo ""

# ─── Останавливаем nginx, гарантируем рестарт при выходе ─────────────────────
NGINX_WAS_RUNNING=0
if systemctl is-active --quiet nginx 2>/dev/null; then
  NGINX_WAS_RUNNING=1
  echo "→ Останавливаю nginx..."
  systemctl stop nginx
fi

trap '{
  if [[ "$NGINX_WAS_RUNNING" -eq 1 ]]; then
    echo "→ Запускаю nginx обратно..."
    systemctl start nginx || true
  fi
}' EXIT

# ─── Получение сертификата ────────────────────────────────────────────────────
certbot certonly \
  --standalone \
  --non-interactive \
  --agree-tos \
  --email "$CERTBOT_EMAIL" \
  "${CERTBOT_DOMAIN_ARGS[@]}"

echo ""
echo "✓ Сертификат получен"
echo "  Fullchain : /etc/letsencrypt/live/$DOMAIN/fullchain.pem"
echo "  Privkey   : /etc/letsencrypt/live/$DOMAIN/privkey.pem"
echo ""
echo "Следующий шаг: переключите nginx в HTTPS-режим:"
echo "  sudo ./scripts/nginx-setup.sh --mode post"
