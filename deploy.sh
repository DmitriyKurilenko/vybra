#!/usr/bin/env bash
# deploy.sh — Боевой деплой приложения Vybra
#
# Использование:
#   ./deploy.sh [--skip-pull] [--skip-build] [--no-backup] [--with-parsing]
#
# По умолчанию запускает только core-сервисы (db, redis, web).
# Флаг --with-parsing дополнительно поднимает celery, celery-beat и selenium.
#
# Требования перед запуском:
#   - Docker daemon запущен
#   - Сеть traefik создана (docker network create traefik)
#   - Контейнер traefik запущен
#   - Файл .env существует в корне проекта
#
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

ENV_FILE="${ENV_FILE:-.env}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/backups}"
BACKUP_KEEP="${BACKUP_KEEP:-5}"
DB_USER="${DB_USER:-postgres}"
DB_NAME="${DB_NAME:-vybra}"
SKIP_PULL="${SKIP_PULL:-0}"
SKIP_BUILD="${SKIP_BUILD:-0}"
NO_BACKUP="${NO_BACKUP:-0}"
WITH_PARSING="${WITH_PARSING:-0}"

log()  { echo "==> $*"; }
warn() { echo "[WARN] $*" >&2; }
die()  { echo "[FAIL] $*" >&2; exit 1; }

_usage() {
  cat <<EOF
Использование: $0 [OPTIONS]

OPTIONS:
  --skip-pull      Не обновлять git-репозиторий
  --skip-build     Не пересобирать Docker-образы
  --no-backup      Пропустить резервную копию БД
  --with-parsing   Запустить celery + selenium для парсинга
  -h, --help       Показать эту справку
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-pull)    SKIP_PULL=1; shift ;;
    --skip-build)   SKIP_BUILD=1; shift ;;
    --no-backup)    NO_BACKUP=1; shift ;;
    --with-parsing) WITH_PARSING=1; shift ;;
    -h|--help)      _usage; exit 0 ;;
    *) die "Неизвестный аргумент: $1" ;;
  esac
done

[[ -f "$ENV_FILE" ]] || die "Файл окружения не найден: $ENV_FILE"

docker info >/dev/null 2>&1 || die "Docker не доступен"

docker network ls --format '{{.Name}}' | grep -q "^traefik$" || die "Сеть traefik не найдена"
docker ps --format '{{.Names}}' | grep -q "^traefik$" || die "Контейнер traefik не запущен"

COMPOSE_ARGS="-f $COMPOSE_FILE"
if [[ "$WITH_PARSING" == "1" ]]; then
  COMPOSE_ARGS="$COMPOSE_ARGS -f docker-compose.parsing.yml"
fi

log "Деплой $(date '+%Y-%m-%d %H:%M:%S')"

if [[ "$SKIP_PULL" != "1" && -d .git ]]; then
  git pull --ff-only -q || die "git pull завершился с ошибкой"
  log "Коммит: $(git log -1 --oneline)"
fi

if [[ "$NO_BACKUP" != "1" ]]; then
  if docker compose $COMPOSE_ARGS ps --status running db 2>/dev/null | grep -q "db"; then
    mkdir -p "$BACKUP_DIR"
    BACKUP_FILE="$BACKUP_DIR/pre-deploy-$(date '+%Y%m%d_%H%M%S').sql.gz"
    docker compose $COMPOSE_ARGS exec -T db pg_dump -U "$DB_USER" "$DB_NAME" | gzip -9 > "$BACKUP_FILE" \
      && log "Бэкап: $(du -sh "$BACKUP_FILE" | cut -f1)" \
      || warn "Бэкап не удался"
    (cd "$BACKUP_DIR" && ls -t pre-deploy-*.sql.gz 2>/dev/null | tail -n +"$(( BACKUP_KEEP + 1 ))" | xargs -r rm --)
  fi
fi

if [[ "$SKIP_BUILD" != "1" ]]; then
  log "Сборка образов"
  docker compose $COMPOSE_ARGS build
fi

log "Запуск сервисов"
docker compose $COMPOSE_ARGS up -d --remove-orphans

MAX_RETRIES=30
for i in $(seq 1 $MAX_RETRIES); do
  if docker compose $COMPOSE_ARGS exec -T db pg_isready -U "$DB_USER" -q 2>/dev/null; then
    break
  fi
  if [[ $i -eq $MAX_RETRIES ]]; then
    die "БД недоступна"
  fi
  sleep 2
done

docker compose $COMPOSE_ARGS exec -T web python manage.py check --deploy 2>&1 | grep -E "^(System check|WARNINGS|ERROR)" || true

log "Готово"
docker compose $COMPOSE_ARGS ps
