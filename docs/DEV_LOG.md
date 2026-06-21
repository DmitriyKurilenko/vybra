# Development Log

## 2026-06-21 (session 7)

### Task
1. Fix WB/Ozon parsing not working in production.
2. Fix items not being added by URL.
3. Add bulk import UI for products.

### Files changed
- `wishlist/tasks.py`
  - `add_item_from_url`: use `Product.objects.get_or_create` by `article_code`
  - Avoid creating placeholder products when parsing fails
  - Enrich existing products only with fresh parsed data
- `wishlist/parsers.py`
  - Extended `WildberriesParser.extract_product_id` for more URL formats
  - Implemented `OzonParser.parse` with JSON-LD/regex extraction
- `wishlist/selenium_parser.py`
  - Added `_extract_ozon_from_page_source` helper
  - Improved `parse_ozon_product_with_selenium` with JSON-LD + visible-text fallback
  - Added page load/script/implicit timeouts to reduce session timeouts
- `front_redesign/src/screens/AddSheet.jsx`
  - Added "Массово" tab with textarea, link counter, and result display
- `front_redesign/src/api/client.js`
  - Added `importFavorites` calling `/api/wishlist/items/import-favorites-bulk`
- `front_redesign/src/state/useApp.js`
  - Added `importBulk` action
- `front_redesign/src/App.jsx`
  - Wired `importBulk` into `AddSheet`
- `docker-compose.parsing.yml`
  - `selenium` memory limit: 384m → 1024m
  - `celery` memory limit: 256m → 512m
  - `SE_NODE_SESSION_TIMEOUT`: 120 → 300
  - `shm_size`: 128m → 256m
- `VERSION`: 0.4.0 → 0.4.1
- `CHANGELOG.md`, `docs/RELEASE_NOTES.md`, `docs/KNOWN_ISSUES.md`, `docs/TASK_STATE.md`

### Validation
- Backup created: `backups/vybra_pre_20260621_162341.sql.gz`
- `docker compose -f docker-compose.prod.yml -f docker-compose.parsing.yml down`
- `docker compose -f docker-compose.prod.yml -f docker-compose.parsing.yml up -d --build`
- `docker compose run --rm web python manage.py check` → 0 issues
- HTTPS checks:
  - `https://vybra.prvms.ru/` → 200
  - `https://vybra.prvms.ru/app/` → 200
  - `https://vybra.prvms.ru/api/docs` → 200
  - `https://vybra.prvms.ru/sw.js` → 200
  - `https://vybra.prvms.ru/manifest.webmanifest` → 200
- End-to-end:
  - `/api/wishlist/items/add-from-url` for non-existent WB product → task FAILED as expected
  - `/api/wishlist/items/import-favorites-bulk` → 2 items imported successfully
  - Selenium driver init in celery container succeeds
  - Built SPA JS contains "Массово" bulk-import tab

### Issues found and fixed during validation
- Parsing overlay was not running; starting it fixed the 504/502 errors on add-by-URL.
- `add_item_from_url` created placeholder products even when parsing failed; fixed by moving product creation after successful parse.
- Selenium tab crashed due to 384m memory limit; raised to 1024m.

### Risks
- Anti-bot protection on WB/Ozon may still intermittently block headless Selenium; monitor celery logs.
- Higher memory footprint with parsing overlay (selenium 1024m, celery 512m).
- Bulk import currently optimized for Wildberries share text; Ozon bulk import not yet supported.

---

## 2026-06-21 (session 6)

### Task
1. Fix mobile viewport overflow — screens not fitting in visible height, elements accessible only via scroll.
2. Add PWA support — installable app for iOS and Android.
3. Create `AGENTS.md` operating manual.

### Files changed
- `AGENTS.md` (new)
  - Mandatory Read Order, Validation Baseline, Update Ritual, Decision Rules, Architecture Snapshot, Conventions
- `front_redesign/src/index.css`
  - Added `--app-height: 100dvh` with `@supports` fallback to `100vh`
  - Added `--safe-top/bottom/left/right` mapped to `env(safe-area-inset-*)`
  - `html`, `body`, `#root`: `height: var(--app-height)`, `overflow: hidden`, `overscroll-behavior: none`
  - `-webkit-tap-highlight-color: transparent`, `touch-action: manipulation`
- `front_redesign/src/App.jsx`
  - `Frame`: `minHeight: 100vh` → `height: var(--app-height)`, `overflow: hidden`, safe-area padding
  - `Splash`: `minHeight: 100vh` → `height: var(--app-height)`
- `front_redesign/src/components/Shell.jsx`
  - Desktop: `minHeight: 100vh` → `height: var(--app-height)`, `overflow: hidden`
  - Mobile: restructured — content (`flex: 1, overflow: hidden`) and tab bar (`flex: 0 0 auto`) are siblings
  - Tab bar: `position: sticky` inside scrollable → `flex: 0 0 auto` outside scrollable
  - Tab bar padding: `calc(14px + env(safe-area-inset-bottom))` → `calc(14px + var(--safe-bottom))`
  - Outer container: added `paddingTop/Left/Right: var(--safe-*)`
- `front_redesign/src/screens/Onboarding.jsx`
  - Visual container: `minHeight: wide ? 280 : 0` → `minHeight: 0, flex: 1`
  - `OnbPile`: `minHeight: 230` → `minHeight: 0`
  - `OnbVS`: `minHeight: 200` → `minHeight: 0`; card heights `180` → `'70%'`
  - Font sizes slightly reduced for small screens: 32→28 (title), 14→13.5 (body)
  - Top padding: `22px` → `0` (Frame provides horizontal padding)
- `front_redesign/src/screens/Auth.jsx`
  - Added `overflowY: auto` safety-net for small screens
  - Removed duplicate horizontal padding (Frame provides it)
- `front_redesign/src/screens/Connect.jsx`
  - Removed duplicate horizontal padding (Frame provides it)
- `front_redesign/src/screens/AddSheet.jsx`
  - Mobile sheet: `position: absolute` → `position: fixed`
  - Added `maxHeight: calc(var(--app-height) - 48px)`, `overflowY: auto`
  - `paddingBottom: 26px` → `calc(26px + var(--safe-bottom))`
  - Desktop dialog: `maxHeight: 90vh` → `calc(var(--app-height) - 48px)`
- `front_redesign/src/screens/ItemSheet.jsx`
  - Same fixes as AddSheet
- `front_redesign/assets/icon.svg` (new)
  - SVG source: 512×512, vermillion (#FF4D2E) background, two white rounded rectangles (pairwise comparison motif)
- `front_redesign/scripts/generate-icons.mjs` (new)
  - Node script using `sharp` to render SVG to 6 PNG sizes
- `front_redesign/package.json`
  - Added `sharp` devDependency
  - Added `generate-icons` script
  - `build`: `vite build` → `npm run generate-icons && vite build`
- `front_redesign/.gitignore`
  - Added `public/icons` (build artifact)
- `front_redesign/public/manifest.webmanifest` (new)
  - Name, short_name, description, lang, start_url, scope, id, display, orientation, theme_color, background_color, categories, 4 icons (192/256/384/512, purpose "any maskable")
- `front_redesign/public/sw.js` (new)
  - Install: cache SPA shell `/app/`
  - Activate: clean old caches, `clients.claim()`
  - Fetch: network-first for navigation (offline fallback), stale-while-revalidate for `/static/`, network-only for `/api/`
- `front_redesign/index.html`
  - `viewport`: added `viewport-fit=cover, user-scalable=no`
  - Added `<meta name="description">`, theme-color (light/dark), Apple PWA meta tags, apple-touch-icon, favicon
  - Removed `<link rel="manifest">` (injected at runtime to prevent Vite URL rewriting)
- `front_redesign/src/main.jsx`
  - Runtime injection of `<link rel="manifest" href="/manifest.webmanifest">`
  - SW registration in production only (`import.meta.env.PROD`), on `window.load`
- `vybra/views.py`
  - Added `_serve_dist_file` helper
  - Added `service_worker` view: serves `dist/sw.js` with `Content-Type: application/javascript` and `Service-Worker-Allowed: /`
  - Added `manifest` view: serves `dist/manifest.webmanifest` with `Content-Type: application/manifest+json`
- `vybra/urls.py`
  - Added `path('sw.js', service_worker, name='sw')`
  - Added `path('manifest.webmanifest', manifest, name='manifest')`

### Validation
- `docker compose down` — passed
- `docker compose up -d --build` — passed (icons generated, vite build OK, collectstatic OK)
- `docker compose run --rm web python manage.py check` — passed (0 issues)
- HTTP checks:
  - `curl -sI http://localhost:8000/` → 200
  - `curl -sI http://localhost:8000/app/` → 200
  - `curl -sI http://localhost:8000/api/docs` → 200
  - `curl -sI http://localhost:8000/sw.js` → 200, `application/javascript`, `Service-Worker-Allowed: /`
  - `curl -sI http://localhost:8000/manifest.webmanifest` → 200, `application/manifest+json`
  - `curl -sI http://localhost:8000/static/spa/icons/icon-192.png` → 200, `image/png`
  - `curl -sI http://localhost:8000/static/spa/icons/icon-512.png` → 200, `image/png`
  - `curl -sI http://localhost:8000/static/spa/icons/apple-touch-icon.png` → 200, `image/png`
  - `curl -sI http://localhost:8000/static/spa/icons/favicon-32.png` → 200, `image/png`
  - manifest JSON validated via `python3 -m json.tool` — valid

### Issues found and fixed during validation
- **Vite URL rewriting**: Vite with `base: '/static/spa/'` rewrote `<link rel="manifest" href="/manifest.webmanifest">` in index.html to `href="/static/spa/manifest.webmanifest"`. WhiteNoise served it with `Content-Type: application/octet-stream` (wrong). Fixed by removing the `<link>` from HTML and injecting it at runtime via JS in `main.jsx`, pointing to `/manifest.webmanifest` (Django view with correct Content-Type).

### Risks
- `dvh` requires iOS 15.4+ / Chrome 108+; older browsers fall back to `vh` via `@supports` (may still overflow on old iOS Safari)
- `sharp` reports 2 npm vulnerabilities (1 moderate, 1 high) during `npm install` — these are in sharp's transitive deps and don't affect the build output; sharp is a devDependency, not shipped to runtime
- iOS keyboard may overlap bottom sheets; mitigated by `maxHeight` + `overflowY: auto` inside sheets
- OAuth in PWA standalone mode opens an in-app browser; callback redirects to `/app` and works correctly
- `public/icons/` is gitignored — if someone builds without `npm run generate-icons`, icons will be missing; the `build` script chain prevents this

---

## 2026-06-20 (session 5)

### Files changed
- `front_redesign/` (new)
  - Vite-based SPA frontend with `src/`, `vite.config.js`, `package.json`, `index.html`, `BACKEND.md`, `README.md`
  - Built with Vite, serves assets under `/static/spa/` with content hashing
- `Dockerfile`
  - Added multi-stage build: Stage 1 (`node:20-slim`) builds SPA, Stage 2 (`python:3.11-slim`) packages it
  - `COPY --from=frontend /frontend/dist /app/front_redesign/dist`
- `vybra/views.py` (new)
  - `spa_index` view serves compiled SPA shell; `FRONTEND_INDEX` setting points to `front_redesign/dist/index.html`
- `authentication/models.py`
  - Added `budget = PositiveIntegerField(default=15000)` to `UserProfile`
- `authentication/migrations/0003_userprofile_budget.py` (new)
- `authentication/urls.py`
  - Removed `login/` and `register/` routes
- `authentication/views.py`
  - Removed `login_view` and `register_view` functions
  - `google_login_callback` now redirects to `/app` (SPA) instead of `/dashboard/`
- `templates/landing.html`
  - All links updated from `/login/`, `/register/` to `/app`
- `vybra/settings.py`
  - Added `FRONTEND_DIST` and `FRONTEND_INDEX` settings
  - `STATICFILES_DIRS` now includes `('spa', FRONTEND_DIST)`
- `vybra/urls.py`
  - Added `re_path(r'^app(?:/.*)?$', spa_index)` for SPA routes
- `wishlist/api.py`
  - Added `get_state` (aggregated items + matches + budget)
  - Added `get_budget` and `update_budget` endpoints
- `wishlist/schemas.py`
  - Added `StateSchema`, `BudgetSchema`, `BudgetUpdateSchema`
- `wishlist/urls.py`
  - Removed `dashboard/`, `compare/`, `items/`, `profile/` routes
- `wishlist/views.py`
  - Removed `dashboard`, `compare`, `items`, `profile` views; only `legal_document` remains
- Deleted `templates/authentication/login.html`, `templates/authentication/register.html`, `templates/base.html`, `templates/wishlist/dashboard.html`, `templates/wishlist/compare.html`, `templates/wishlist/items.html`, `templates/wishlist/profile.html`

### Validation
- `python -m py_compile vybra/views.py` passed
- `python -m py_compile wishlist/api.py` passed
- `python -m py_compile authentication/views.py` passed
- `python -m py_compile authentication/models.py` passed
- `python manage.py check` (dry-run; settings may need env vars)

### Risks
- If `front_redesign/dist/index.html` is not present at startup, `spa_index` returns 500 with a clear error message; the build must run before `collectstatic`
- SPA must implement its own JWT cookie-based auth state management (existing API unchanged)
- Users with existing sessions will be redirected to `/app` after OAuth callback, which is the intended behavior

---

## 2026-06-01

### Files changed
- `docker-compose.prod.yml`
  - Added `image: vybra-web:latest` to `web` and `celery-beat`
  - Added Traefik labels to `web`
  - Added `networks: - traefik` to `web`
  - Appended `networks: traefik: external: true`
  - Added `collectstatic --noinput` to startup command
- `.env.example`
  - Added `TRAEFIK_HOST`
  - Removed/commented nginx variables
- `deploy.sh` (new in root)
  - Minimal script: checks, backup, build, up, healthcheck
- Deleted `scripts/nginx-setup.sh`, `scripts/cert.sh`, `scripts/init.sh`, `scripts/create_admin.sh`, `scripts/deploy.sh`

### Validation
- `bash -n deploy.sh` passed
- Docker Compose file syntax reviewed manually

### Risks
- Router name `vybra-web` must remain globally unique on the host
- `celery-beat` now reuses `vybra-web:latest` image; ensure `web` is built before `celery-beat` starts
- Healthcheck on `web` may still fail if Traefik passes `X-Forwarded-Proto: https` but gunicorn expects plain HTTP; current test uses `curl` with that header and should pass
- If shared Traefik container or network is missing, deployment fails fast with a clear message

---

## 2026-06-01 (session 2)

### Files changed
- `docker-compose.prod.yml`
  - Added `image: postgres:17` to `db`
  - Added `image: redis:7-alpine` to `redis`
  - Added `build: .` to `web` (was missing, preventing local build)
  - Added `volumes: - postgres_data:/var/lib/postgresql/data` to `db`
  - Added `postgres_data:` to top-level `volumes`
- `docker-compose.yml`
  - Bumped `db` image from `postgres:15` to `postgres:17`
- `.gitignore`
  - Added `*.ini`
- Removed `vybra/Untitled-2.ini` from repository and history

### Validation
- `docker compose -f docker-compose.prod.yml --env-file .env.example config` passed

### Risks
- `postgres_data` volume is now named and persistent; if an anonymous volume existed before, the old data is orphaned and must be migrated manually if needed
- `docker compose build` now builds `web` image locally; `celery-beat` reuses it correctly

---

## 2026-06-02 (session 3)

### Files changed
- `docker-compose.prod.yml`
  - Removed `celery`, `celery-beat`, and `selenium` services
  - Removed `collectstatic` from `web` startup command
  - Bumped `web` `mem_limit` from `128m` to `512m`
- `docker-compose.yml`
  - Removed `celery`, `celery-beat`, and `selenium` services
- `docker-compose.parsing.yml` (new)
  - Extracted `celery`, `celery-beat`, and `selenium` from prod compose
- `deploy.sh`
  - Added `--with-parsing` flag to overlay `docker-compose.parsing.yml`
  - Added `--help` / `-h` flag
  - Added inline documentation (header comment + `_usage` function)

### Validation
- `bash -n deploy.sh` passed
- `docker compose -f docker-compose.prod.yml --env-file .env.example config` passed
- `docker compose -f docker-compose.parsing.yml --env-file .env.example config` passed
- `docker compose -f docker-compose.prod.yml -f docker-compose.parsing.yml --env-file .env.example config` passed

### Risks
- Existing deployments that relied on `celery`/`selenium` being in `docker-compose.prod.yml` will no longer start those services unless `--with-parsing` is passed. This is intentional but is a behavioral change.
- `web` now has 512m RAM; verify host has enough memory for the full stack when parsing is enabled.

---

## 2026-06-02 (session 4)

### Files changed
- `docker-compose.prod.yml`
  - Added internal `backend` network (bridge)
  - Connected `db`, `redis`, `web` to `backend`
  - `web` remains connected to `traefik` (external)
- `docker-compose.parsing.yml`
  - Connected `celery`, `selenium`, `celery-beat` to `backend`
  - Declared `backend` network in file (required for overlay compatibility)

### Validation
- `docker compose -f docker-compose.prod.yml --env-file .env.example config` passed
- `docker compose -f docker-compose.prod.yml -f docker-compose.parsing.yml --env-file .env.example config` passed

### Risks
- None. All services now share the same internal `backend` network and can resolve each other by service name.
