# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
