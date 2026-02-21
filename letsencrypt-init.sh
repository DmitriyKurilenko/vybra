#!/usr/bin/env bash
set -Eeuo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <email> <domain> [domain2 ...]"
  echo "Example: $0 admin@example.com vybra.app www.vybra.app"
  exit 1
fi

EMAIL="$1"
shift
DOMAINS=("$@")

for domain in "${DOMAINS[@]}"; do
  if [[ "$domain" == "localhost" || "$domain" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Invalid domain for Let's Encrypt: $domain"
    exit 1
  fi
done

if ! command -v certbot >/dev/null 2>&1; then
  echo "certbot is not installed. Install it first (snap/apt/yum)."
  exit 1
fi

CERTBOT_DOMAIN_ARGS=()
for domain in "${DOMAINS[@]}"; do
  CERTBOT_DOMAIN_ARGS+=("-d" "$domain")
done

echo "==> Requesting Let's Encrypt certificate for: ${DOMAINS[*]}"
echo "==> Using webroot challenge path: /var/www/certbot"
echo "==> Make sure nginx serves /.well-known/acme-challenge/ from /var/www/certbot"
sudo certbot certonly \
  --webroot \
  -w /var/www/certbot \
  --non-interactive \
  --agree-tos \
  --email "$EMAIL" \
  "${CERTBOT_DOMAIN_ARGS[@]}"

echo "==> Certificate issued"
echo "Fullchain: /etc/letsencrypt/live/${DOMAINS[0]}/fullchain.pem"
echo "Privkey:   /etc/letsencrypt/live/${DOMAINS[0]}/privkey.pem"
echo "Use these paths in your reverse proxy (nginx/caddy/traefik)."
echo "If nginx is used: sudo systemctl reload nginx"
