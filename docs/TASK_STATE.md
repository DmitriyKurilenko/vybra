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
