#!/usr/bin/env bash
# init.sh — Первоначальная установка сервера «под ключ»
#
# Выполняет всё необходимое на чистом Ubuntu/Debian сервере:
#   1. Установка системных зависимостей (git, docker, nginx, certbot)
#   2. Клонирование репозитория (если запущен не из него)
#   3. Настройка nginx в HTTP-режиме (для certbot-challenge)
#   4. Получение TLS-сертификата Let's Encrypt
#   5. Переключение nginx в HTTPS-режим
#   6. Первый деплой приложения (docker compose up + migrate + collectstatic)
#
# Использование:
#   sudo bash <(curl -fsSL https://raw.githubusercontent.com/.../scripts/init.sh)
#
#   — или, из уже склонированного репозитория —
#
#   sudo ./scripts/init.sh
#
set -Eeuo pipefail

# ─── Цвета ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BOLD='\033[1m'; RESET='\033[0m'
log()  { echo -e "${GREEN}==>${RESET} ${BOLD}$*${RESET}"; }
warn() { echo -e "${YELLOW}[WARN]${RESET} $*" >&2; }
die()  { echo -e "${RED}[FAIL]${RESET} $*" >&2; exit 1; }
step() { echo -e "\n${BOLD}━━━  $* ${RESET}"; }

# ─── Root ─────────────────────────────────────────────────────────────────────
[[ "$EUID" -eq 0 ]] || die "Запустите от root: sudo ./scripts/init.sh"

# ─── Корень проекта ───────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

# ─── Загрузка .env ────────────────────────────────────────────────────────────
ENV_FILE="$ROOT_DIR/.env"
[[ -f "$ENV_FILE" ]] || die ".env не найден в $ROOT_DIR\nСоздайте его: cp .env.example .env && nano .env"
# shellcheck source=/dev/null
set -a; source "$ENV_FILE"; set +a

# ─── Валидация обязательных переменных ────────────────────────────────────────
errors=()
[[ -z "${DOMAIN:-}"          ]] && errors+=("DOMAIN не задан")
[[ -z "${CERTBOT_EMAIL:-}"   ]] && errors+=("CERTBOT_EMAIL не задан")
[[ -z "${SECRET_KEY:-}"      ]] && errors+=("SECRET_KEY не задан")
[[ -z "${JWT_SECRET_KEY:-}"  ]] && errors+=("JWT_SECRET_KEY не задан")
[[ -z "${DB_PASSWORD:-}"     ]] && errors+=("DB_PASSWORD не задан")

# Проверка что не осталось заглушек CHANGE_ME
while IFS='=' read -r key val; do
  [[ "$key" =~ ^[[:space:]]*# ]] && continue
  [[ -z "$key" ]] && continue
  key="${key%%#*}"; key="${key// /}"
  val="${val%%#*}"; val="${val# }"
  [[ "$val" == CHANGE_ME* ]] && errors+=("$key содержит незаполненный шаблон CHANGE_ME")
done < "$ENV_FILE"

if [[ ${#errors[@]} -gt 0 ]]; then
  echo -e "${RED}ОШИБКА: заполните в .env:${RESET}"
  for e in "${errors[@]}"; do echo "  • $e"; done
  exit 1
fi

DOMAIN="${DOMAIN}"
WWW_DOMAIN="${WWW_DOMAIN:-}"
CERTBOT_EMAIL="${CERTBOT_EMAIL}"
CERTBOT_WEBROOT="${CERTBOT_WEBROOT:-/var/www/certbot}"

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║            Vybra — первоначальная установка              ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════════════════════╝${RESET}"
echo "  Домен   : $DOMAIN${WWW_DOMAIN:+ / $WWW_DOMAIN}"
echo "  E-mail  : $CERTBOT_EMAIL"
echo "  Каталог : $ROOT_DIR"
echo ""

# ─── ШАГ 1: Системные зависимости ────────────────────────────────────────────
step "1/6  Системные зависимости"

apt-get update -qq

if ! command -v curl >/dev/null 2>&1; then
  apt-get install -y curl
fi

if ! command -v git >/dev/null 2>&1; then
  log "Установка git..."
  apt-get install -y git
fi

if ! command -v nginx >/dev/null 2>&1; then
  log "Установка nginx (official repo)..."
  curl -fsSL https://nginx.org/keys/nginx_signing.key | gpg --dearmor -o /usr/share/keyrings/nginx.gpg
  echo "deb [signed-by=/usr/share/keyrings/nginx.gpg] https://nginx.org/packages/mainline/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) nginx" \
    > /etc/apt/sources.list.d/nginx.list
  apt-get update -qq && apt-get install -y nginx
fi

if ! command -v certbot >/dev/null 2>&1; then
  log "Установка certbot..."
  if command -v snap >/dev/null 2>&1; then
    snap install --classic certbot
    ln -sf /snap/bin/certbot /usr/bin/certbot
  else
    apt-get install -y certbot
  fi
fi

if ! command -v docker >/dev/null 2>&1; then
  log "Установка Docker..."
  curl -fsSL https://get.docker.com | sh
  systemctl enable --now docker
fi

docker info >/dev/null 2>&1 || die "Docker daemon не запущен"
log "Все зависимости установлены"

# ─── ШАГ 2: Подготовка директорий ────────────────────────────────────────────
step "2/6  Подготовка"

mkdir -p \
  "$CERTBOT_WEBROOT" \
  "${BACKUP_DIR:-$ROOT_DIR/backups}" \
  "$ROOT_DIR/staticfiles" \
  "$ROOT_DIR/media"

# Убираем дефолтный конфиг nginx если есть
if [[ -f /etc/nginx/sites-enabled/default ]]; then
  rm -f /etc/nginx/sites-enabled/default
  systemctl reload nginx
fi

log "Директории созданы"

# ─── ШАГ 3: Nginx в HTTP-режиме (для certbot) ────────────────────────────────
step "3/6  Nginx (HTTP-режим для сертификата)"

bash "$SCRIPT_DIR/nginx-setup.sh" --mode pre
log "Nginx настроен в HTTP-режиме"

# ─── ШАГ 4: Получение TLS-сертификата ────────────────────────────────────────
step "4/6  TLS-сертификат Let's Encrypt"

bash "$SCRIPT_DIR/cert-init.sh"
log "Сертификат получен"

# ─── ШАГ 5: Nginx в HTTPS-режиме ─────────────────────────────────────────────
step "5/6  Nginx (HTTPS-режим)"

bash "$SCRIPT_DIR/nginx-setup.sh" --mode post
log "Nginx переключён в HTTPS-режим"

# Systemd таймер для автообновления сертификата
TIMER_PATH=/etc/systemd/system/certbot-renew.service
if [[ ! -f "$TIMER_PATH" ]]; then
  cat > "$TIMER_PATH" <<EOF
[Unit]
Description=Certbot Renewal

[Service]
Type=oneshot
ExecStart=$ROOT_DIR/scripts/cert-renew.sh
WorkingDirectory=$ROOT_DIR
EOF

  cat > /etc/systemd/system/certbot-renew.timer <<EOF
[Unit]
Description=Run certbot-renew twice daily

[Timer]
OnCalendar=*-*-* 03,15:00:00
RandomizedDelaySec=1800
Persistent=true

[Install]
WantedBy=timers.target
EOF
  systemctl daemon-reload
  systemctl enable --now certbot-renew.timer
  log "Автообновление сертификата настроено (systemd timer)"
fi

# ─── ШАГ 6: Первый деплой ─────────────────────────────────────────────────────
step "6/6  Деплой приложения"

bash "$SCRIPT_DIR/deploy.sh" --skip-pull --no-backup

# ─── Готово ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════════════╗${RESET}"
echo -e "${GREEN}${BOLD}║  ✓  Установка завершена                                  ║${RESET}"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════════════╝${RESET}"
echo -e "  Сайт   : ${BOLD}https://$DOMAIN${RESET}"
echo -e "  Логи   : docker compose logs -f"
echo -e "  Деплой : ./scripts/deploy.sh"
echo ""
