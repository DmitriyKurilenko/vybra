# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.1] - 2026-06-21

### Added
- `front_redesign/src/screens/AddSheet.jsx`: third "Массово" tab for bulk import of Wildberries share text
- `front_redesign/src/api/client.js`: `importFavorites` method calling `/api/wishlist/items/import-favorites-bulk`
- `front_redesign/src/state/useApp.js`: `importBulk` action that reloads app state after bulk import
- `wishlist/parsers.py`: `OzonParser.parse` implementation using JSON-LD/regex with Selenium fallback path
- `wishlist/selenium_parser.py`: `_extract_ozon_from_page_source` helper and improved `parse_ozon_product_with_selenium`
- `docker-compose.parsing.yml`: raised `selenium` memory limit to `1024m`, `celery` to `512m`, `SE_NODE_SESSION_TIMEOUT` to `300`, `shm_size` to `256m`

### Changed
- `wishlist/tasks.py::add_item_from_url`: uses `Product.objects.get_or_create` by `article_code`; no longer creates placeholder products when parsing fails
- `wishlist/tasks.py::add_item_from_url`: enriches existing products only when fresh parsed data is available
- `wishlist/parsers.py`: extended `WildberriesParser.extract_product_id` to support more WB URL formats
- `wishlist/selenium_parser.py`: added page load/script/implicit timeouts to reduce Selenium session timeouts
- Production is now deployed with parsing overlay (`docker-compose.prod.yml` + `docker-compose.parsing.yml`)

### Fixed
- Parsing (WB/Ozon) not working because `celery` and `selenium` containers were not running in production
- Items not being added by URL due to missing worker and `Product.objects.create` causing `IntegrityError` on duplicate article codes
- Selenium "tab crashed" errors due to insufficient container memory
- Missing bulk import UI in SPA

## [0.4.0] - 2026-06-21

### Added
- PWA support: installable app for iOS (Add to Home Screen) and Android (Install App)
- `front_redesign/public/manifest.webmanifest` — web app manifest with name, icons, display mode, theme colors
- `front_redesign/public/sw.js` — service worker with offline support (network-first navigation, stale-while-revalidate static, network-only API)
- `front_redesign/assets/icon.svg` — SVG source for app icons (vermillion + two white cards)
- `front_redesign/scripts/generate-icons.mjs` — `sharp`-based PNG icon generator (192/256/384/512/180/32)
- `vybra/views.py`: `service_worker` view serving `/sw.js` with `Service-Worker-Allowed: /` header
- `vybra/views.py`: `manifest` view serving `/manifest.webmanifest` with `application/manifest+json` content type
- `vybra/urls.py`: `/sw.js` and `/manifest.webmanifest` routes
- `front_redesign/index.html`: PWA meta tags (Apple, theme-color, viewport-fit=cover)
- `front_redesign/src/main.jsx`: runtime manifest link injection and service worker registration
- `AGENTS.md`: operating manual for agents (Mandatory Read Order, Validation Baseline, Update Ritual, Decision Rules)

### Changed
- `front_redesign/src/index.css`: `100vh` → `100dvh` via `--app-height` CSS variable with `@supports` fallback; added `--safe-*` env vars; `overflow: hidden` on html/body/#root
- `front_redesign/src/App.jsx`: Frame and Splash use `height: var(--app-height)` with safe-area padding
- `front_redesign/src/components/Shell.jsx`: mobile layout restructured — content and tab bar are siblings (tab bar always visible); `100vh` → `var(--app-height)`
- `front_redesign/src/screens/Onboarding.jsx`: visual elements flex to available space instead of fixed `minHeight`
- `front_redesign/src/screens/AddSheet.jsx`, `ItemSheet.jsx`: `position: absolute` → `position: fixed` with `maxHeight` and safe-area padding
- `front_redesign/src/screens/Auth.jsx`: added `overflowY: auto` safety-net for small screens
- `front_redesign/package.json`: `sharp` devDependency; `build` runs `generate-icons` before `vite build`
- `front_redesign/index.html`: viewport now includes `viewport-fit=cover, user-scalable=no`

### Fixed
- Mobile viewport overflow: screens not fitting in visible height on iOS Safari due to `100vh` including address bar
- Bottom tab bar pushed off-screen when content overflowed (was inside scrollable container with `position: sticky`)
- Bottom sheets overlapping tab bar and lacking `maxHeight` constraints

## [0.3.0] - 2026-06-20

### Added
- `front_redesign/` — new SPA frontend built with Vite, replacing server-rendered Django templates
- Multi-stage Dockerfile: Stage 1 builds the SPA, Stage 2 packages it into the runtime image
- `vybra/views.py`: SPA shell view that serves the compiled frontend on `/app/*`
- `/api/wishlist/state` endpoint: aggregated state for SPA (items, matches, budget) in one request
- `/api/wishlist/budget` GET/PUT endpoints for user budget management
- `UserProfile.budget` field (PositiveIntegerField, default 15000) — tracks user's selection budget
- `authentication/migrations/0003_userprofile_budget.py`: adds budget field to UserProfile

### Changed
- Application routes (`/dashboard/`, `/compare/`, `/items/`, `/profile/`) now served by SPA under `/app`
- `/` landing page links updated to point to `/app` instead of removed template pages
- OAuth callback redirects to `/app` (SPA) instead of `/dashboard/`
- `vybra/urls.py`: SPA route `re_path(r'^app(?:/.*)?$', spa_index)` added
- `vybra/settings.py`: `FRONTEND_DIST` and `FRONTEND_INDEX` settings; SPA assets mounted under `/static/spa/`
- `wishlist/urls.py`: removed server-rendered page routes (dashboard, compare, items, profile)
- `wishlist/views.py`: removed server-rendered view functions; only `legal_document` remains
- `authentication/urls.py`: removed `login/` and `register/` routes
- `authentication/views.py`: removed `login_view` and `register_view` functions
- `Dockerfile`: Node.js stage builds SPA, final image serves it via WhiteNoise

### Removed
- `templates/authentication/login.html` — login page (now in SPA)
- `templates/authentication/register.html` — registration page (now in SPA)
- `templates/base.html` — base template (replaced by SPA)
- `templates/wishlist/dashboard.html` — dashboard page (now in SPA)
- `templates/wishlist/compare.html` — compare page (now in SPA)
- `templates/wishlist/items.html` — items page (now in SPA)
- `templates/wishlist/profile.html` — profile page (now in SPA)

## [0.2.2] - 2026-06-02

### Added
- `docker-compose.parsing.yml` — optional overlay for celery worker, celery-beat, and selenium
- `deploy.sh --with-parsing` flag to start/stop parsing services alongside core stack
- Inline documentation and `--help` to `deploy.sh`

### Fixed
- `docker-compose.prod.yml`: removed `celery`, `celery-beat`, and `selenium` from default stack; they now start only when explicitly requested
- `docker-compose.prod.yml`: bumped `web` memory limit from `128m` to `512m` to prevent OOM kills
- `docker-compose.prod.yml`: removed redundant `collectstatic` from startup command (already handled in Dockerfile)
- `docker-compose.yml` (dev): removed `celery`, `celery-beat`, and `selenium` from default dev stack

## [0.2.1] - 2026-06-01

### Fixed
- `docker-compose.prod.yml`: missing `image` tags for `db` (`postgres:17`) and `redis` (`redis:7-alpine`)
- `docker-compose.prod.yml`: missing `build: .` for `web` service, preventing image build for reuse by `celery-beat`
- `docker-compose.prod.yml`: missing named volume `postgres_data` for `db`, causing data loss on `down`
- `docker-compose.yml`: aligned `postgres` version with prod (`postgres:15` → `postgres:17`)
- `.gitignore`: added `*.ini` to prevent accidental commits of config files containing secrets

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
