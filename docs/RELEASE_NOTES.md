# Release Notes

## v0.5.0 — Validation gates

**Ruff and Playwright are now part of the local Docker validation baseline.**

### What changed
- Added `docker compose --profile tools run --rm lint` for Python static analysis with Ruff
- Added `docker compose --profile tools run --rm e2e` for Chromium e2e validation of the SPA through Django `/app/`
- The e2e smoke flow registers a unique test user through the UI and creates a manual wishlist item
- Frontend Docker build now uses `npm ci` and committed `front_redesign/package-lock.json`

### Action required for developers
- Run the full AGENTS.md baseline before closing non-trivial tasks
- Keep `@playwright/test` and `mcr.microsoft.com/playwright:vX.Y.Z-jammy` on the same version

## v0.4.1 — Parsing fix + bulk import

**Fixed WB/Ozon parsing, items-by-link flow, and added bulk import UI.**

### What changed
- Added "Массово" tab to the Add Item sheet for bulk importing Wildberries share text
- Improved Ozon parser: JSON-LD/page-source extraction plus Selenium fallback
- Improved Wildberries URL recognition and Selenium stability
- Production now runs with the parsing overlay (celery + selenium) so link parsing actually executes
- Fixed `add_item_from_url` to avoid `IntegrityError` on duplicate article codes

### Action required for operators
- Deploy with parsing overlay: `docker compose -f docker-compose.prod.yml -f docker-compose.parsing.yml up -d --build`
- Ensure the host has enough memory for `selenium` (limit raised to 1024m) and `celery` (512m)

### Internal
- `wishlist/tasks.py`: `get_or_create` for `Product`, conditional placeholder creation
- `wishlist/parsers.py`: Ozon requests parser, broader WB article extraction
- `wishlist/selenium_parser.py`: Ozon source extraction, driver timeouts
- `front_redesign/src/screens/AddSheet.jsx`, `api/client.js`, `state/useApp.js`: bulk import UI
- `docker-compose.parsing.yml`: increased resource limits and session timeout

## v0.4.0 — Mobile viewport fix + PWA installable app

**Two major improvements: mobile layout and installability. No breaking changes to the API.**

### What changed

#### Mobile viewport fix
- All screens now fit within the visible viewport on iOS and Android — no more page-level scroll to reach off-screen elements
- Bottom tab bar is always visible and accessible, regardless of content height
- Bottom sheets (add item, item details) use `position: fixed` with `maxHeight` and respect safe-area insets
- Onboarding visual elements flex to available space instead of using fixed heights
- `100vh` replaced with `100dvh` (dynamic viewport height) — correctly handles iOS Safari address bar
- Safe-area insets honored for notched devices (status bar, home indicator)

#### PWA — installable app
- Vybra is now installable as a standalone app on iOS (Add to Home Screen) and Android (Install App prompt)
- Web manifest at `/manifest.webmanifest` with app name, icons, display mode, theme colors
- Service worker at `/sw.js` provides offline support: SPA shell and cached assets load without network
- App icons generated at build time from a single SVG source (vermillion + two white cards motif)
- Apple PWA meta tags: `apple-mobile-web-app-capable`, status bar style, app title, touch icon
- Theme color adapts to system preference (light/dark)

### Action required for operators
- **Rebuild the image:** `docker compose build` — the build now generates icons via `sharp` before `vite build`
- **No URL changes:** `/sw.js` and `/manifest.webmanifest` are new Django routes; existing routes unchanged
- **No new env vars:** PWA works out of the box

### Internal
- `front_redesign/src/index.css`: `--app-height`, `--safe-*` CSS variables, overflow lock
- `front_redesign/src/App.jsx`, `Shell.jsx`, screens: `height: var(--app-height)` instead of `minHeight: 100vh`
- `front_redesign/assets/icon.svg`, `scripts/generate-icons.mjs`: icon generation pipeline
- `front_redesign/public/manifest.webmanifest`, `public/sw.js`: PWA assets
- `front_redesign/src/main.jsx`: runtime manifest injection, SW registration
- `vybra/views.py`: `service_worker`, `manifest` views
- `vybra/urls.py`: `/sw.js`, `/manifest.webmanifest` routes

## v0.3.0 — SPA Frontend (front_redesign)

**Major frontend architecture change. No breaking changes to the API.**

### What changed
- The application UI (dashboard, compare, items, profile) is now a standalone SPA served under `/app` instead of server-rendered Django templates
- Marketing landing page (`/`) remains server-rendered for SEO
- OAuth callback now redirects to `/app` (SPA) instead of `/dashboard/`
- `UserProfile.budget` field added to track user's selection budget
- New `/api/wishlist/state` endpoint aggregates items, matches count, and budget in one request for SPA initialization
- New `/api/wishlist/budget` GET/PUT endpoints for budget management
- Multi-stage Dockerfile builds the SPA during image creation; no separate build step required

### Action required for operators
- **Update deployed image:** The SPA is built inside the Docker image. Rebuild with `docker compose build`.
- **No URL changes for users:** All old URLs (`/dashboard/`, `/compare/`, etc.) are now handled by the SPA client-side routing. The landing page (`/`) and legal pages (`/legal/*`) remain unchanged.
- **First run:** If the SPA bundle is missing, the app returns a clear 500 error pointing to the build step.

### Internal
- `front_redesign/` — Vite-based SPA project
- Removed templates: `login.html`, `register.html`, `base.html`, `dashboard.html`, `compare.html`, `items.html`, `profile.html`
- Removed auth views: `login_view`, `register_view`
- Removed wishlist views: `dashboard`, `compare`, `items`, `profile`

## v0.2.2 — Parsing Services as Optional Overlay

**Behavioral change for operators running parsing tasks.**

### What changed
- `celery`, `celery-beat`, and `selenium` are no longer part of the default production stack. They live in a new `docker-compose.parsing.yml` overlay.
- `deploy.sh` now accepts `--with-parsing` to start the full stack including parsing services.
- `deploy.sh` now has `--help` and inline documentation.
- `web` memory limit increased from `128m` to `512m` to prevent OOM kills.
- Redundant `collectstatic` removed from `web` startup command (already runs during image build).

### Action required for operators
- **Normal deploy:** `./deploy.sh` (unchanged)
- **Deploy with parsing:** `./deploy.sh --with-parsing`
- If you are currently running `celery`/`selenium` from a previous deploy, stop them manually (`docker compose -f docker-compose.parsing.yml down`) or simply redeploy with the new flag.

## v0.2.1 — Compose Fixes

**Infrastructure fixes only. No breaking changes.**

### What changed
- `docker-compose.prod.yml` now correctly declares `image` for `db` (`postgres:17`) and `redis` (`redis:7-alpine`).
- `web` service has both `build: .` and `image: vybra-web:latest`, so `docker compose build` works and `celery-beat` reuses the built image.
- Added named Docker volume `postgres_data` for the database. Data now survives `docker compose down`.
- Aligned development compose (`docker-compose.yml`) to use `postgres:17`.
- Added `*.ini` to `.gitignore` to prevent accidental commits of config files containing secrets.

### Action required for operators
- Run `./deploy.sh --skip-build` first to bring up the new volume mapping safely, then run `./deploy.sh` normally on the next deploy.
- If you previously ran `docker-compose.prod.yml` without a named `postgres_data` volume, your old data is in an anonymous volume. Migrate it manually if needed before destroying the old container.

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
