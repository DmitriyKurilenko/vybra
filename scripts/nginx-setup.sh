#!/usr/bin/env bash
set -Eeuo pipefail

# ─── Корень проекта ───────────────────────────────────────────────────────────
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# ─── Загрузка .env ────────────────────────────────────────────────────
SCRIPTS_ENV="$ROOT_DIR/.env"
if [[ -f "$SCRIPTS_ENV" ]]; then
  # shellcheck source=/dev/null
  set -a; source "$SCRIPTS_ENV"; set +a
fi

# ─── Переменные с дефолтами из .env ──────────────────────────────────
MODE=""
DOMAIN="${DOMAIN:-}"
WWW_DOMAIN="${WWW_DOMAIN:-}"
APP_UPSTREAM="${APP_UPSTREAM:-127.0.0.1:8000}"
NGINX_CONF_PATH="${NGINX_CONF_PATH:-/etc/nginx/sites-available/vybra.conf}"
NGINX_ENABLED_PATH="${NGINX_ENABLED_PATH:-/etc/nginx/sites-enabled/vybra.conf}"
CERTBOT_WEBROOT="${CERTBOT_WEBROOT:-/var/www/certbot}"

# ─── CLI-аргументы (переопределяют .env) ─────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)    MODE="${2:-}"; shift 2 ;;
    --domain)  DOMAIN="${2:-}"; shift 2 ;;
    --www)     WWW_DOMAIN="${2:-}"; shift 2 ;;
    --upstream) APP_UPSTREAM="${2:-}"; shift 2 ;;
    *)         echo "Unknown argument: $1"; exit 1 ;;
  esac
done

if [[ -z "$MODE" || -z "$DOMAIN" ]]; then
  echo "Usage: sudo $0 --mode <pre|post> [--domain <domain>] [--www <www.domain>]"
  echo "       DOMAIN and WWW_DOMAIN can also be set in .env"
  exit 1
fi

if [[ "$MODE" != "pre" && "$MODE" != "post" ]]; then
  echo "--mode must be pre or post"
  exit 1
fi

if [[ "$DOMAIN" == "localhost" || "$DOMAIN" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Domain must be a real DNS name"
  exit 1
fi

if [[ -n "$WWW_DOMAIN" ]] && [[ "$WWW_DOMAIN" == "$DOMAIN" ]]; then
  WWW_DOMAIN=""
fi

SERVER_NAMES="$DOMAIN"
if [[ -n "$WWW_DOMAIN" ]]; then
  SERVER_NAMES="$SERVER_NAMES $WWW_DOMAIN"
fi

SITE_PATH="$NGINX_CONF_PATH"
ENABLED_PATH="$NGINX_ENABLED_PATH"

sudo mkdir -p "$CERTBOT_WEBROOT"

# ─── Установка nginx если нет ──────────────────────────────────────────────
if ! command -v nginx >/dev/null 2>&1; then
  echo "nginx не найден — устанавливаю..."
  apt-get update -qq && apt-get install -y nginx
fi

mkdir -p "$(dirname "$SITE_PATH")" "$(dirname "$ENABLED_PATH")"

if [[ "$MODE" == "pre" ]]; then
  sudo tee "$SITE_PATH" >/dev/null <<EOF
server {
    listen 80;
    server_name $SERVER_NAMES;

    location /.well-known/acme-challenge/ {
        root $CERTBOT_WEBROOT;
    }

    location / {
        proxy_pass http://$APP_UPSTREAM;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto http;
    }
}
EOF
else
  sudo tee "$SITE_PATH" >/dev/null <<EOF
server {
    listen 80;
    server_name $SERVER_NAMES;

    location /.well-known/acme-challenge/ {
        root $CERTBOT_WEBROOT;
    }

    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl;
    http2 on;
    server_name $SERVER_NAMES;

    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:10m;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options DENY always;
    add_header Referrer-Policy strict-origin-when-cross-origin always;

    location / {
        proxy_pass http://$APP_UPSTREAM;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }
}
EOF
fi

if [[ -f /etc/nginx/sites-enabled/default ]]; then
  sudo rm -f /etc/nginx/sites-enabled/default
fi

sudo ln -sfn "$SITE_PATH" "$ENABLED_PATH"
sudo nginx -t
sudo systemctl reload nginx

echo "nginx config applied successfully ($MODE mode)"
