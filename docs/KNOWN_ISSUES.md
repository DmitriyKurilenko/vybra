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

### Missing image and build context in production compose
**Symptom:** `docker compose build` skipped `web`; `docker compose up` tried to pull non-existent image
**Cause:** `docker-compose.prod.yml` had only `image: vybra-web:latest` without `build: .`
**Fix:** Added `build: .` to `web` service so `docker compose build` produces the image locally

### Missing named volume for PostgreSQL
**Symptom:** Database data lost after `docker compose down`
**Cause:** `docker-compose.prod.yml` did not declare a named volume for `db`
**Fix:** Added `postgres_data:/var/lib/postgresql/data` to `db` service and declared `postgres_data` volume

### Secret leakage via `.ini` file
**Symptom:** GitHub push protection blocked push due to Google OAuth credentials
**Cause:** `vybra/Untitled-2.ini` contained secrets and was committed to repository
**Fix:** Removed file from repository and history; added `*.ini` to `.gitignore`

### OOM kills on `web` container
**Symptom:** `web` container repeatedly killed during startup
**Cause:** `mem_limit: 128m` was too low for Django + Gunicorn; redundant `collectstatic` on startup also spiked memory usage
**Fix:** Bumped `web` `mem_limit` to `512m`; removed `collectstatic` from startup command (already handled in Dockerfile)

## Open
- None
