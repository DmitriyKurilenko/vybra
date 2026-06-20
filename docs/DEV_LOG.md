# Development Log

## 2026-06-20 (session 5)

### Files changed
- `front_redesign/` (new)
  - Vite-based SPA frontend with `src/`, `vite.config.js`, `package.json`, `index.html`, `BACKEND.md`, `README.md`
  - Built with Vite, serves assets under `/static/spa/` with content hashing
- `Dockerfile`
  - Added multi-stage build: Stage 1 (`node:20-slim`) builds SPA, Stage 2 (`python:3.11-slim`) packages it
  - `COPY --from=frontend /frontend/dist /app/front_redesign/dist`
- `vybra/views.py` (new)
  - `spa_index` view serves compiled SPA shell; `FRONTEND_INDEX` setting points to `front_redesign/dist/index.html`
- `authentication/models.py`
  - Added `budget = PositiveIntegerField(default=15000)` to `UserProfile`
- `authentication/migrations/0003_userprofile_budget.py` (new)
- `authentication/urls.py`
  - Removed `login/` and `register/` routes
- `authentication/views.py`
  - Removed `login_view` and `register_view` functions
  - `google_login_callback` now redirects to `/app` (SPA) instead of `/dashboard/`
- `templates/landing.html`
  - All links updated from `/login/`, `/register/` to `/app`
- `vybra/settings.py`
  - Added `FRONTEND_DIST` and `FRONTEND_INDEX` settings
  - `STATICFILES_DIRS` now includes `('spa', FRONTEND_DIST)`
- `vybra/urls.py`
  - Added `re_path(r'^app(?:/.*)?$', spa_index)` for SPA routes
- `wishlist/api.py`
  - Added `get_state` (aggregated items + matches + budget)
  - Added `get_budget` and `update_budget` endpoints
- `wishlist/schemas.py`
  - Added `StateSchema`, `BudgetSchema`, `BudgetUpdateSchema`
- `wishlist/urls.py`
  - Removed `dashboard/`, `compare/`, `items/`, `profile/` routes
- `wishlist/views.py`
  - Removed `dashboard`, `compare`, `items`, `profile` views; only `legal_document` remains
- Deleted `templates/authentication/login.html`, `templates/authentication/register.html`, `templates/base.html`, `templates/wishlist/dashboard.html`, `templates/wishlist/compare.html`, `templates/wishlist/items.html`, `templates/wishlist/profile.html`

### Validation
- `python -m py_compile vybra/views.py` passed
- `python -m py_compile wishlist/api.py` passed
- `python -m py_compile authentication/views.py` passed
- `python -m py_compile authentication/models.py` passed
- `python manage.py check` (dry-run; settings may need env vars)

### Risks
- If `front_redesign/dist/index.html` is not present at startup, `spa_index` returns 500 with a clear error message; the build must run before `collectstatic`
- SPA must implement its own JWT cookie-based auth state management (existing API unchanged)
- Users with existing sessions will be redirected to `/app` after OAuth callback, which is the intended behavior

---

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

---

## 2026-06-02 (session 3)

### Files changed
- `docker-compose.prod.yml`
  - Removed `celery`, `celery-beat`, and `selenium` services
  - Removed `collectstatic` from `web` startup command
  - Bumped `web` `mem_limit` from `128m` to `512m`
- `docker-compose.yml`
  - Removed `celery`, `celery-beat`, and `selenium` services
- `docker-compose.parsing.yml` (new)
  - Extracted `celery`, `celery-beat`, and `selenium` from prod compose
- `deploy.sh`
  - Added `--with-parsing` flag to overlay `docker-compose.parsing.yml`
  - Added `--help` / `-h` flag
  - Added inline documentation (header comment + `_usage` function)

### Validation
- `bash -n deploy.sh` passed
- `docker compose -f docker-compose.prod.yml --env-file .env.example config` passed
- `docker compose -f docker-compose.parsing.yml --env-file .env.example config` passed
- `docker compose -f docker-compose.prod.yml -f docker-compose.parsing.yml --env-file .env.example config` passed

### Risks
- Existing deployments that relied on `celery`/`selenium` being in `docker-compose.prod.yml` will no longer start those services unless `--with-parsing` is passed. This is intentional but is a behavioral change.
- `web` now has 512m RAM; verify host has enough memory for the full stack when parsing is enabled.

---

## 2026-06-02 (session 4)

### Files changed
- `docker-compose.prod.yml`
  - Added internal `backend` network (bridge)
  - Connected `db`, `redis`, `web` to `backend`
  - `web` remains connected to `traefik` (external)
- `docker-compose.parsing.yml`
  - Connected `celery`, `selenium`, `celery-beat` to `backend`
  - Declared `backend` network in file (required for overlay compatibility)

### Validation
- `docker compose -f docker-compose.prod.yml --env-file .env.example config` passed
- `docker compose -f docker-compose.prod.yml -f docker-compose.parsing.yml --env-file .env.example config` passed

### Risks
- None. All services now share the same internal `backend` network and can resolve each other by service name.
