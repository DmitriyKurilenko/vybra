#!/usr/bin/env bash
# create_admin.sh — Создание Django superuser в запущенном контейнере web
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ENV_FILE="${ENV_FILE:-.env}"
PRIMARY_COMPOSE_FILE="${PRIMARY_COMPOSE_FILE:-docker-compose.yml}"
SECONDARY_COMPOSE_FILE="${SECONDARY_COMPOSE_FILE:-docker-compose.prod.yml}"

# Загружаем .env если есть
if [[ -f "$ROOT_DIR/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ROOT_DIR/.env"
  set +a
fi

compose_args=(-f "$PRIMARY_COMPOSE_FILE")
if [[ -f "$SECONDARY_COMPOSE_FILE" ]]; then
  compose_args+=(-f "$SECONDARY_COMPOSE_FILE")
fi

compose_cmd() {
  docker compose --env-file "$ENV_FILE" "${compose_args[@]}" "$@"
}

# Проверяем что контейнер web запущен
if ! compose_cmd ps web | grep -q "running"; then
  echo "[FAIL] Контейнер web не запущен. Сначала выполните deploy."
  exit 1
fi

# Интерактивный ввод
read -r -p "Username [admin]: " USERNAME
USERNAME="${USERNAME:-admin}"

read -r -p "Email: " EMAIL
if [[ -z "$EMAIL" ]]; then
  echo "[FAIL] Email обязателен."
  exit 1
fi

# Пароль с подтверждением
while true; do
  read -r -s -p "Password: " PASSWORD
  echo
  read -r -s -p "Password (confirm): " PASSWORD2
  echo
  if [[ "$PASSWORD" == "$PASSWORD2" ]]; then
    break
  fi
  echo "Пароли не совпадают, попробуйте снова."
done

if [[ ${#PASSWORD} -lt 8 ]]; then
  echo "[WARN] Пароль короче 8 символов."
fi

# Создаём superuser через Python
compose_cmd exec web python - <<PYEOF
import sys, os
os.environ['DJANGO_SETTINGS_MODULE'] = 'vybra.settings'
import django
django.setup()
from django.contrib.auth.models import User

username = ${USERNAME@Q}
email    = ${EMAIL@Q}
password = ${PASSWORD@Q}

if User.objects.filter(username=username).exists():
    u = User.objects.get(username=username)
    u.set_password(password)
    u.is_staff = True
    u.is_superuser = True
    u.save()
    print(f"[OK] Пароль обновлён для существующего пользователя: {username}")
else:
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f"[OK] Создан superuser: {username} / {email}")
PYEOF
