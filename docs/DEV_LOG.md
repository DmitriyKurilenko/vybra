# Development Log

## 2026-06-01

### Files changed
- `docker-compose.prod.yml`
  - Added `image: vybra-web:latest` to `web` and `celery-beat`
  - Added Traefik labels to `web`
  - Added `networks: - traefik` to `web`
  - Appended `networks: traefik: external: true`
  - Added `collectstatic --noinput` to startup command
- `.env.example`
  - Added `TRAEFIK_HOST`
  - Removed/commented nginx variables
- `deploy.sh` (new in root)
  - Minimal script: checks, backup, build, up, healthcheck
- Deleted `scripts/nginx-setup.sh`, `scripts/cert.sh`, `scripts/init.sh`, `scripts/create_admin.sh`, `scripts/deploy.sh`

### Validation
- `bash -n deploy.sh` passed
- Docker Compose file syntax reviewed manually

### Risks
- Router name `vybra-web` must remain globally unique on the host
- `celery-beat` now reuses `vybra-web:latest` image; ensure `web` is built before `celery-beat` starts
- Healthcheck on `web` may still fail if Traefik passes `X-Forwarded-Proto: https` but gunicorn expects plain HTTP; current test uses `curl` with that header and should pass
- If shared Traefik container or network is missing, deployment fails fast with a clear message

---

## 2026-06-01 (session 2)

### Files changed
- `docker-compose.prod.yml`
  - Added `image: postgres:17` to `db`
  - Added `image: redis:7-alpine` to `redis`
  - Added `build: .` to `web` (was missing, preventing local build)
  - Added `volumes: - postgres_data:/var/lib/postgresql/data` to `db`
  - Added `postgres_data:` to top-level `volumes`
- `docker-compose.yml`
  - Bumped `db` image from `postgres:15` to `postgres:17`
- `.gitignore`
  - Added `*.ini`
- Removed `vybra/Untitled-2.ini` from repository and history

### Validation
- `docker compose -f docker-compose.prod.yml --env-file .env.example config` passed

### Risks
- `postgres_data` volume is now named and persistent; if an anonymous volume existed before, the old data is orphaned and must be migrated manually if needed
- `docker compose build` now builds `web` image locally; `celery-beat` reuses it correctly
