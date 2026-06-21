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

## DEC-005: Mobile viewport fix — dvh + safe-area + structural layout

**Date:** 2026-06-21
**Status:** Accepted

### Context
The SPA mobile layout used `minHeight: 100vh` throughout (`App.jsx` Frame, `Shell.jsx`, screens). On iOS Safari, `100vh` includes the address bar area — content overflows the visible viewport and becomes accessible only via scroll. The bottom tab bar was inside a `position: sticky` container within the scrollable content area, causing it to be pushed off-screen when content overflowed. Bottom sheets (`AddSheet`, `ItemSheet`) used `position: absolute` relative to the content area rather than `position: fixed` relative to the viewport, and lacked `maxHeight` constraints.

### Decision
Replace `100vh` with `100dvh` (dynamic viewport height) via a CSS custom property `--app-height` with `@supports` fallback to `100vh` for older browsers. Lock `html`, `body`, and `#root` to `overflow: hidden` to prevent page-level scroll. Introduce `--safe-top`, `--safe-bottom`, `--safe-left`, `--safe-right` CSS variables mapped to `env(safe-area-inset-*)` for viewport-fit=cover support.

Restructure `Shell.jsx` mobile layout: content area (`flex: 1, overflow: hidden`) and tab bar (`flex: 0 0 auto`) are siblings, not nested — the tab bar is always visible regardless of content height. Per-screen scroll areas use `overflowY: auto` within `flex: 1, minHeight: 0` containers.

Bottom sheets (`AddSheet`, `ItemSheet`) use `position: fixed` with `maxHeight: calc(var(--app-height) - 48px)` and `paddingBottom: calc(26px + var(--safe-bottom))`.

### Consequences
- All screens fit within the visible viewport on iOS and Android; no page-level scroll
- Tab bar is always visible and accessible; content scrolls independently within each screen
- Bottom sheets overlay the tab bar and respect safe-area insets
- `dvh` requires iOS 15.4+ / Chrome 108+; older browsers fall back to `vh` via `@supports`
- Onboarding visual elements no longer have fixed `minHeight` — they flex to available space

## DEC-006: PWA — service worker, manifest, installable app

**Date:** 2026-06-21
**Status:** Accepted

### Context
The SPA had no PWA support — no manifest, no service worker, no Apple touch icon, no installable app experience. Users could only access Vybra via the browser address bar. For a mobile-first comparison tool, installability (Add to Home Screen on iOS, Install App on Android) is a core UX requirement.

### Decision
Add full PWA infrastructure:
- **Manifest** (`/manifest.webmanifest`): served by a Django view with `Content-Type: application/manifest+json`; defines app name ("Выбра"), `start_url: /app/`, `scope: /app/`, `display: standalone`, `orientation: portrait`, theme colors for light/dark, and 4 icon sizes (192/256/384/512) with `purpose: "any maskable"`
- **Service worker** (`/sw.js`): served by a Django view with `Content-Type: application/javascript` and `Service-Worker-Allowed: /` header; scope `/` controls both `/app/*` (navigation) and `/static/spa/*` (assets). Strategies: network-first for navigation (offline fallback to cached SPA shell), stale-while-revalidate for static assets, network-only for API
- **Icons**: generated from a single SVG source (`assets/icon.svg`) via `sharp` at build time; 6 PNGs (192/256/384/512 for manifest, 180 for apple-touch-icon, 32 for favicon); output to `public/icons/` (gitignored), served by WhiteNoise under `/static/spa/icons/`
- **Apple meta tags**: `apple-mobile-web-app-capable`, `mobile-web-app-capable`, `apple-mobile-web-app-status-bar-style: black-translucent`, `apple-mobile-web-app-title`, `theme-color` (light/dark via `media` queries)
- **Manifest link injection**: done at runtime via JS (`document.createElement('link')`) instead of HTML `<link rel="manifest">` to prevent Vite from rewriting the absolute URL to `/static/spa/manifest.webmanifest` (which WhiteNoise would serve with wrong `Content-Type`)
- **SW registration**: in `main.jsx`, only in production (`import.meta.env.PROD`), on `window.load`

### Consequences
- Vybra is installable as a standalone app on iOS (Add to Home Screen) and Android (Install App prompt)
- The app works offline: SPA shell and cached assets load without network; API calls require connectivity
- `sharp` added as devDependency — prebuilt binaries work in `node:20-slim` Docker image without system dependencies
- Icon generation runs before `vite build` via `npm run build` script (`generate-icons && vite build`)
- `public/icons/` is gitignored — icons are a build artifact, regenerated from `assets/icon.svg` on every build
- The Django views for `/sw.js` and `/manifest.webmanifest` read from `front_redesign/dist/`; if the frontend build hasn't run, they return 500 with a clear error message
- `viewport-fit=cover` + `user-scalable=no` in index.html enables full-bleed display with safe-area insets on notched devices
