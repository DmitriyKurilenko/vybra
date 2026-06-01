# Known Issues

## Resolved

### Traefik router not registered due to missing network
**Symptom:** 404 from Traefik after deployment
**Cause:** `web` service had Traefik labels but was not attached to the `traefik` external network
**Fix:** Added `networks: - traefik` to `web` and `networks: traefik: external: true` to compose file

### Implicit image tag causing pull failures
**Symptom:** `celery-beat` or workers fail to start with "pull access denied"
**Cause:** Services reused the `web` image without an explicit tag; Docker tried to pull from Docker Hub
**Fix:** Set explicit `image: vybra-web:latest` on `web` and `celery-beat`

### Missing collectstatic
**Symptom:** `/static/` returns 404 in production
**Cause:** `collectstatic` was not run on container startup; static files were only built into the image but not collected to the shared volume
**Fix:** Added `python manage.py collectstatic --noinput` to the `web` startup command

## Open
- None
