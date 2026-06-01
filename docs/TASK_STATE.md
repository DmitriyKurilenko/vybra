# Task State

## Active

## Done
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
