# Architecture Decisions

## DEC-001: Switch to shared Traefik reverse proxy

**Date:** 2026-06-01
**Status:** Accepted

### Context
The project previously used a per-project nginx container with SSL certificates managed by Certbot. This caused port conflicts (80/443), certificate duplication, and complex `scripts/nginx-setup.sh` / `scripts/cert.sh` maintenance.

### Decision
Move to a shared Traefik reverse proxy managed outside this repository.
- Traefik listens on 80/443 and terminates TLS via Let's Encrypt (ACME)
- The `web` service exposes no host ports; instead it declares Docker labels for Traefik discovery
- The `web` service connects to the external `traefik` Docker network

### Consequences
- No more nginx inside the project
- `docker-compose.prod.yml` must include `traefik` labels and the external network
- `deploy.sh` must verify that the `traefik` network and container exist before deploying
- Router names must be globally unique; we use `vybra-web`

## DEC-002: Persistent database volume in production

**Date:** 2026-06-01
**Status:** Accepted

### Context
The initial Traefik migration removed the `docker-compose.yml` overlay that previously provided `postgres_data` volume. The `docker-compose.prod.yml` was left without a named volume for the database, meaning `docker compose down` would destroy data.

### Decision
Always declare a named Docker volume `postgres_data` in `docker-compose.prod.yml` and mount it into the `db` service at `/var/lib/postgresql/data`.

### Consequences
- Database survives container recreation
- Volume must be explicitly managed if migration or wipe is needed
