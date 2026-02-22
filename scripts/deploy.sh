#!/usr/bin/env bash
# deploy.sh — Боевой деплой приложения Vybra
#
# Использование:
#   ./scripts/deploy.sh [--skip-pull] [--skip-build] [--no-backup]
#
# Конфигурация читается из .env (корень проекта).
# Любую переменную можно переопределить через shell:
#   ENV_FILE=.env.staging ./scripts/deploy.sh
#
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

# ─── Переменные (.env → defaults) ───────────────────────────────────────────
ENV_FILE="${ENV_FILE:-.env}"
PRIMARY_COMPOSE_FILE="${PRIMARY_COMPOSE_FILE:-docker-compose.yml}"
SECONDARY_COMPOSE_FILE="${SECONDARY_COMPOSE_FILE:-docker-compose.prod.yml}"
BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/backups}"
BACKUP_KEEP="${BACKUP_KEEP:-5}"
DB_CONTAINER_USER="${DB_CONTAINER_USER:-postgres}"
DB_CONTAINER_NAME="${DB_CONTAINER_NAME:-vybra}"
SKIP_PULL=${SKIP_PULL:-0}
SKIP_BUILD=${SKIP_BUILD:-0}
NO_BACKUP=${NO_BACKUP:-0}

# ─── Справка ─────────────────────────────────────────────────────────────────
_usage() {
  cat <<EOF
Использование: $0 [--skip-pull] [--skip-build] [--no-backup]

  --skip-pull   Не обновлять git-репозиторий
  --skip-build  Не пересобирать Docker-образы
  --no-backup   Пропустить резервную копию БД

Конфигурация (из .env или переменных окружения):
  ENV_FILE              = $ENV_FILE
  PRIMARY_COMPOSE_FILE  = $PRIMARY_COMPOSE_FILE
  SECONDARY_COMPOSE_FILE= $SECONDARY_COMPOSE_FILE
  BACKUP_DIR            = $BACKUP_DIR
  BACKUP_KEEP           = $BACKUP_KEEP
  DB_CONTAINER_USER     = $DB_CONTAINER_USER
  DB_CONTAINER_NAME     = $DB_CONTAINER_NAME
EOF
}

# ─── CLI-аргументы (переопределяют .env) ─────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-pull)  SKIP_PULL=1;   shift ;;
    --skip-build) SKIP_BUILD=1;  shift ;;
    --no-backup)  NO_BACKUP=1;   shift ;;
    -h|--help)    _usage; exit 0 ;;
    *) echo "Неизвестный аргумент: $1"; _usage; exit 1 ;;
  esac
done

# ─── Compose helper ───────────────────────────────────────────────────────────
COMPOSE_ARGS=(-f "$PRIMARY_COMPOSE_FILE")
if [[ -f "$SECONDARY_COMPOSE_FILE" ]]; then
  COMPOSE_ARGS+=(-f "$SECONDARY_COMPOSE_FILE")
fi

compose_cmd() {
  docker compose --env-file "$ENV_FILE" "${COMPOSE_ARGS[@]}" "$@"
}

# ─── Утилиты ──────────────────────────────────────────────────────────────────
log()  { echo "==> [$(date '+%H:%M:%S')] $*"; }
warn() { echo "==> [WARN] $*" >&2; }
die()  { echo "==> [FAIL] $*" >&2; exit 1; }

# ─── Предварительные проверки ─────────────────────────────────────────────────
log "Деплой запущен: $(date '+%Y-%m-%d %H:%M:%S')"
log "Рабочая директория: $ROOT_DIR"

[[ -f "$ENV_FILE" ]] || die "Файл окружения не найден: $ENV_FILE
Заполните $ENV_FILE (см. комментарии CHANGE_ME внутри)"  

if ! command -v docker >/dev/null 2>&1; then
  log "Docker не найден — устанавливаю..."
  if ! command -v curl >/dev/null 2>&1; then
    apt-get update -qq && apt-get install -y curl
  fi
  curl -fsSL https://get.docker.com | sh
  systemctl enable --now docker
fi
docker info >/dev/null 2>&1 || die "Docker daemon не запущен. Запустите: systemctl start docker"

if ! command -v git >/dev/null 2>&1; then
  apt-get update -qq && apt-get install -y git
fi

# ─── 1. Обновление репозитория ────────────────────────────────────────────────
if [[ "$SKIP_PULL" != "1" && -d .git ]]; then
  log "Обновление репозитория"
  git fetch --all --prune
  git pull --ff-only || die "git pull завершился с ошибкой"
  log "Текущий коммит: $(git log -1 --oneline)"
fi

# ─── 2. Сборка frontend-ассетов ───────────────────────────────────────────────
if [[ -f package.json ]]; then
  if ! command -v npm >/dev/null 2>&1; then
    log "Node.js не найден — устанавливаю LTS..."
    curl -fsSL https://deb.nodesource.com/setup_lts.x | bash -
    apt-get install -y nodejs
  fi
  log "Сборка frontend-ассетов"
  npm ci --silent
  npm run build:css
fi

# ─── 3. Резервная копия БД ────────────────────────────────────────────────────
if [[ "$NO_BACKUP" != "1" ]]; then
  if compose_cmd ps --status running db 2>/dev/null | grep -q "db"; then
    mkdir -p "$BACKUP_DIR"
    BACKUP_FILE="$BACKUP_DIR/pre-deploy-$(date '+%Y%m%d_%H%M%S').sql.gz"
    log "Создание резервной копии БД → $BACKUP_FILE"
    compose_cmd exec -T db \
      pg_dump -U "$DB_CONTAINER_USER" "$DB_CONTAINER_NAME" \
      | gzip -9 > "$BACKUP_FILE" \
      && log "Резервная копия создана: $(du -sh "$BACKUP_FILE" | cut -f1)" \
      || warn "Не удалось создать резервную копию (продолжаем)"
    # Хранить только последние $BACKUP_KEEP бэкапов
    (cd "$BACKUP_DIR" && ls -t pre-deploy-*.sql.gz 2>/dev/null | tail -n +"$(( BACKUP_KEEP + 1 ))" | xargs -r rm --)
  else
    warn "Контейнер БД не запущен — пропускаем бэкап"
  fi
fi

# ─── 4. Сборка образов ────────────────────────────────────────────────────────
if [[ "$SKIP_BUILD" != "1" ]]; then
  log "Сборка Docker-образов"
  # DOCKER_BUILDKIT=0 — legacy builder, меньше RAM чем BuildKit (важно для VPS)
  DOCKER_BUILDKIT=0 compose_cmd build --progress=plain 2>&1 | tee /tmp/docker-build.log \
    || { echo ""; echo "=== ПОСЛЕДНИЕ СТРОКИ ЛОГА ==="; tail -30 /tmp/docker-build.log; die "Сборка образов завершилась с ошибкой"; }
fi

# ─── 5. Запуск сервисов ───────────────────────────────────────────────────────
log "Запуск контейнеров"
compose_cmd up -d --remove-orphans

# ─── 6. Ожидание готовности БД ────────────────────────────────────────────────
log "Ожидание готовности базы данных"
MAX_RETRIES=30
for i in $(seq 1 $MAX_RETRIES); do
  if compose_cmd exec -T db pg_isready -U "$DB_CONTAINER_USER" -q 2>/dev/null; then
    log "База данных готова"
    break
  fi
  if [[ $i -eq $MAX_RETRIES ]]; then
    die "База данных не стала доступна за ${MAX_RETRIES} попыток"
  fi
  echo -n "."
  sleep 2
done

# ─── 7. Проверка конфигурации Django ─────────────────────────────────────────
log "Проверка конфигурации Django (--deploy)"
compose_cmd exec -T web python manage.py check --deploy \
  || warn "Django check --deploy выявил предупреждения"

# ─── 8. Статус ────────────────────────────────────────────────────────────────
log "Состояние контейнеров"
compose_cmd ps

log "Деплой завершён: $(date '+%Y-%m-%d %H:%M:%S')"
