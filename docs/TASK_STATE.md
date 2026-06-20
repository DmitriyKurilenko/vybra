# Task State

## Active

## Done
- [x] Replace server-rendered templates with SPA frontend (front_redesign)
  - Added `front_redesign/` — Vite-based SPA with src/, vite.config.js, package.json
  - Multi-stage Dockerfile: Node stage builds SPA, Python stage packages it
  - `vybra/views.py`: `spa_index` view serves compiled SPA shell under `/app/*`
  - Added `/api/wishlist/state` aggregated endpoint for SPA
  - Added `/api/wishlist/budget` GET/PUT endpoints
  - Added `UserProfile.budget` field (migration `0003`)
  - Removed old Django template pages (login, register, dashboard, compare, items, profile, base)
  - Updated landing page links to point to `/app`
  - OAuth callback now redirects to `/app` (SPA)
- [x] Configure project to work through shared Traefik reverse proxy
  - Traefik labels on `web` service
  - External `traefik` network
  - Remove nginx scripts and references
  - Simplify `deploy.sh` and move to root
  - Add `collectstatic` to startup command
  - Set explicit `image` tags for reuse by `celery-beat`
- [x] Fix missing image tags and build context in `docker-compose.prod.yml`
  - `db`: `postgres:17`
  - `redis`: `redis:7-alpine`
  - `web`: `build: .` + `image: vybra-web:latest`
- [x] Add persistent `postgres_data` volume to `docker-compose.prod.yml`
- [x] Align `postgres` version in dev compose (`docker-compose.yml`: 15 → 17)
- [x] Add `*.ini` to `.gitignore` to prevent secret leakage
- [x] Extract parsing services into optional overlay
  - Create `docker-compose.parsing.yml` with celery, celery-beat, selenium
  - Remove parsing services from `docker-compose.prod.yml`
  - Remove parsing services from `docker-compose.yml`
  - Add `--with-parsing` flag to `deploy.sh`
  - Add `--help` and inline documentation to `deploy.sh`
- [x] Fix OOM issues in production
  - Bump `web` memory limit from 128m to 512m
  - Remove redundant `collectstatic` from `web` startup (handled in Dockerfile)
