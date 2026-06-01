# Release Notes

## v0.2.0 — Shared Traefik Integration

**Deployment change required.**

This release replaces the per-project nginx reverse proxy with integration into a shared Traefik instance.

### What changed
- The `web` service no longer exposes ports on the host. Traefik routes traffic directly to the container via Docker labels.
- SSL certificates are now managed by the shared Traefik container (Let's Encrypt ACME). No more Certbot scripts in this repo.
- `deploy.sh` has been moved to the repository root and stripped of one-time setup logic (Docker, Git, npm installation).

### Action required for operators
1. Ensure a shared Traefik container is running on the host and attached to a Docker network named `traefik`.
2. Set `TRAEFIK_HOST` in your `.env` to the domain Traefik should route to this project.
3. Remove any leftover nginx configs or Certbot hooks from the server.

### Internal
- `celery-beat` now explicitly uses the same image tag as `web` (`vybra-web:latest`).
- Static files are collected automatically on container startup.
