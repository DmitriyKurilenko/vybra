# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.2] - 2026-06-02

### Added
- `docker-compose.parsing.yml` — optional overlay for celery worker, celery-beat, and selenium
- `deploy.sh --with-parsing` flag to start/stop parsing services alongside core stack
- Inline documentation and `--help` to `deploy.sh`

### Fixed
- `docker-compose.prod.yml`: removed `celery`, `celery-beat`, and `selenium` from default stack; they now start only when explicitly requested
- `docker-compose.prod.yml`: bumped `web` memory limit from `128m` to `512m` to prevent OOM kills
- `docker-compose.prod.yml`: removed redundant `collectstatic` from startup command (already handled in Dockerfile)
- `docker-compose.yml` (dev): removed `celery`, `celery-beat`, and `selenium` from default dev stack

## [0.2.1] - 2026-06-01

### Fixed
- `docker-compose.prod.yml`: missing `image` tags for `db` (`postgres:17`) and `redis` (`redis:7-alpine`)
- `docker-compose.prod.yml`: missing `build: .` for `web` service, preventing image build for reuse by `celery-beat`
- `docker-compose.prod.yml`: missing named volume `postgres_data` for `db`, causing data loss on `down`
- `docker-compose.yml`: aligned `postgres` version with prod (`postgres:15` → `postgres:17`)
- `.gitignore`: added `*.ini` to prevent accidental commits of config files containing secrets

## [0.2.0] - 2026-06-01

### Added
- Traefik Docker labels to `web` service for shared reverse proxy integration
- External `traefik` network in `docker-compose.prod.yml`
- `collectstatic --noinput` to the `web` startup command
- Explicit `image: vybra-web:latest` for `web` and `celery-beat` services to prevent implicit image pulls
- `TRAEFIK_HOST` environment variable in `.env.example`
- New minimal `deploy.sh` in project root

### Changed
- Simplified `deploy.sh`: removed Docker/Git/npm installation logic, Traefik pre-flight checks added

### Removed
- `scripts/nginx-setup.sh`, `scripts/cert.sh`, `scripts/init.sh`, `scripts/create_admin.sh`, `scripts/deploy.sh`
- Nginx-related environment variables from `.env.example` (`APP_UPSTREAM`, `NGINX_CONF_PATH`, `NGINX_ENABLED_PATH`)

## [0.1.0] - YYYY-MM-DD

### Added
- Initial release
