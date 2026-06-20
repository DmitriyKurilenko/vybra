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

## DEC-003: Parsing services as optional overlay

**Date:** 2026-06-02
**Status:** Accepted

### Context
`celery`, `celery-beat`, and `selenium` were included in `docker-compose.prod.yml` by default, consuming RAM and CPU even when no parsing tasks were active. This caused unnecessary resource pressure and OOM kills on small VPS instances.

### Decision
Extract parsing-related services into a separate `docker-compose.parsing.yml` overlay file. Core production (`docker-compose.prod.yml`) runs only `db`, `redis`, and `web`. Parsing is started only when explicitly requested via `deploy.sh --with-parsing` or by manually overlaying `docker-compose.parsing.yml`.

### Consequences
- Reduced baseline resource usage in production
- `deploy.sh` must support multiple compose files when `--with-parsing` is passed
- Operators must explicitly opt-in to run selenium and background workers

## DEC-004: SPA frontend (front_redesign) replacing server-rendered templates

**Date:** 2026-06-20
**Status:** Accepted

### Context
The previous frontend used Django templates (server-rendered HTML with Alpine.js and Tailwind). This tight coupling between backend and frontend made development slower, required full page reloads for navigation, and complicated the use of modern frontend tooling. The marketing landing page was the only page that needed server rendering for SEO; the application itself (dashboard, compare, items, profile) is a purely client-side experience.

### Decision
Replace the Django template-based frontend with a standalone SPA built with Vite. The backend remains a Django monolith with Django Ninja API.
- Marketing landing (`/`) remains server-rendered via `templates/landing.html` for SEO
- Application routes (`/app/*`) are served by a single Django view (`spa_index`) that returns the compiled SPA shell (`front_redesign/dist/index.html`)
- SPA assets (hashed by Vite) are served by WhiteNoise under `/static/spa/`
- The SPA communicates with the backend exclusively via `/api/*` endpoints
- A multi-stage Dockerfile builds the SPA first (Node.js stage), then packages it into the runtime image

### Consequences
- Frontend and backend are now decoupled: frontend team can work independently with `npm run dev` proxying to the Django API
- Application navigation is fully client-side with no server roundtrips
- SPA must implement its own auth state management using the existing JWT cookie-based auth
- OAuth callback redirects to `/app` (SPA) instead of `/dashboard/`
- Old server-rendered page templates (`login.html`, `register.html`, `dashboard.html`, `compare.html`, `items.html`, `profile.html`, `base.html`) are removed
- `UserProfile.budget` field added to support SPA's "budget for top screen" feature
