## 1. **Мета-информация**

| Поле | Значение |
|---|---|
| Название | Vybra |
| Версия | 0.5.0 |
| Дата сводки | 2026-06-23 |
| Production URL | https://vybra.prvms.ru |
| Статус | Production-ready продукт для портфолио; актуальная инфраструктурная версия v0.5.0 |
| Язык продукта | Русский (`LANGUAGE_CODE = ru-ru`, `TIME_ZONE = Europe/Moscow`) |
| Тип проекта | Web-приложение для сравнения и ранжирования товаров из wishlist |

## 2. **Product Overview**

Vybra — это веб-приложение для осознанного выбора товаров из личного списка желаний. Пользователь добавляет товары вручную, по ссылке маркетплейса или массово импортирует избранное Wildberries, после чего сравнивает товары попарно. Система превращает субъективные ответы пользователя в рейтинг на базе ELO и показывает, какие товары действительно выигрывают в личном выборе.

Основной сценарий рассчитан на покупателей, которые сохраняют много товаров в избранном и теряются между похожими вариантами. Вместо обычного списка приложение предлагает последовательные сравнения "что выбрать из двух", учитывает количество побед и поражений, считает уверенность рейтинга и строит дашборд с топом товаров, включая отдельные подборки до 1 000 ₽ и до 10 000 ₽.

Бизнес-логика строится вокруг глобального каталога `Product` и пользовательских записей `Item`. Один товар может существовать в каталоге один раз, а у каждого пользователя хранится собственное состояние: активность, ELO-рейтинг, история сравнений и статистика. Для Wildberries реализованы импорт избранного, обогащение данных, обновление цен и хранение истории цен.

## 3. **Технологический стек**

| Компонент | Технология | Обоснование |
|---|---|---|
| Backend | Python 3.11, Django `>=5.0,<5.1` | Зрелый monolith-фреймворк с ORM, миграциями, admin и встроенными security middleware. |
| API | django-ninja `>=1.1.0` | Типизированные API-схемы, OpenAPI/Swagger UI и компактная маршрутизация `/api/auth/*`, `/api/wishlist/*`. |
| База данных | PostgreSQL 17 | Реляционная модель для товаров, сравнений, истории цен и импортов; индексы и транзакции для консистентности. |
| Cache / broker | Redis 7 Alpine | Кэш парсинга, кэш пары сравнения и брокер/результат backend для Celery. |
| Async jobs | Celery `>=5.3.4`, Celery Beat | Фоновый парсинг, импорт избранного, обновление цен, очистка старой истории цен и nightly recovery. |
| Парсинг | requests, BeautifulSoup, lxml, Selenium 4, standalone Chromium | Быстрый API-парсинг Wildberries с Selenium fallback для антибот-защиты и динамических страниц. |
| Frontend | Vite + React 18 SPA (`front_redesign/`), served by WhiteNoise under `/static/spa/` | Decoupled SPA with client-side routing; landing page remains server-rendered for SEO. |
| Auth | JWT через PyJWT, HttpOnly cookies, optional Google OAuth2 | Stateless API-auth для frontend и защищённые cookie-сессии; Google OAuth включается переменными окружения. |
| Static files | WhiteNoise `>=6.7.0`, Brotli | Сжатая manifest-статика без отдельного nginx в контейнере приложения. |
| Runtime | Gunicorn `>=21.2.0`, Docker, Docker Compose | Предсказуемый production runtime, healthchecks, лимиты CPU/RAM и воспроизводимый деплой. |
| Reverse proxy | Shared Traefik + Let's Encrypt ACME | Общий TLS-терминатор для нескольких проектов без конфликтов портов 80/443. |
| Browser extension | Chrome Extension Manifest V3 | Экспорт избранного Wildberries в формат, совместимый с bulk import Vybra. |

## 4. **Архитектура**

Проект реализован как Django-монолит с двумя локальными bounded contexts:

| Context | Ответственность |
|---|---|
| `authentication` | Регистрация, login/logout, refresh token, `/api/auth/me`, Google OAuth2, профиль пользователя через `UserProfile`. |
| `wishlist` | Каталог товаров, пользовательский wishlist, ELO-сравнения, импорт Wildberries, парсинг, история цен, dashboard и профильные операции. |

Основные паттерны:

- Fat Model для доменных вычислений рейтинга: `Item.calculate_elo_change()`, `Item.update_elo()`, `confidence`, `confidence_level`.
- Service / Task Layer в `wishlist.tasks`: фоновые операции вынесены из HTTP-request flow в Celery.
- Parser abstraction: `MarketplaceParser`, `WildberriesParser`, `OzonParser`, `get_parser()`.
- Schema-first API на Django Ninja: Pydantic-схемы в `wishlist/schemas.py` и `authentication/schemas.py`.
- Transaction Script для критичных операций API: `transaction.atomic()` и `select_for_update()` при сохранении результата сравнения.
- Soft delete для товаров пользователя через `Item.is_active`.

Схема потока данных:

```text
Browser / SPA (front_redesign)
  -> /api/auth/* или /api/wishlist/*
  -> Django Ninja routers
  -> Django ORM models: User, UserProfile, Product, Item, Comparison, PriceHistory, ImportRun
  -> PostgreSQL 17

Async path:
Browser action
  -> API returns task_id
  -> Celery worker via Redis
  -> Wildberries API / Selenium standalone Chromium
  -> Product / Item / PriceHistory / ImportRun updates
  -> /api/wishlist/tasks/{task_id} and /api/wishlist/imports/* show progress/results

Production ingress:
HTTPS request
  -> shared Traefik network
  -> web container on port 8000
  -> Gunicorn
  -> Django application (SPA shell via /app/*, API via /api/*, landing via /)
```

## 5. **Ключевые функции**

- Регистрация и вход: `/api/auth/register`, `/api/auth/login`, `/api/auth/refresh`, `/api/auth/logout`, `/api/auth/me`; access/refresh JWT выставляются в cookies `vybra_access_token` и `vybra_refresh_token`.
- Google OAuth2: маршруты `/google/login/` и `/google/callback/` реализуют Authorization Code Flow, проверку `state`, получение userinfo и создание пользователя с unusable password.
- Управление wishlist: `/api/wishlist/items`, `/api/wishlist/items/{item_id}`, manual create/update, soft delete и восстановление ранее удалённых товаров при повторном импорте.
- Добавление товара по URL: `/api/wishlist/items/add-from-url` запускает Celery task, определяет marketplace, извлекает артикул, ищет товар в глобальном каталоге и парсит данные при необходимости.
- Массовый импорт Wildberries: `/api/wishlist/items/import-favorites-bulk` принимает текст `name + url`, быстро создаёт `Product`/`Item`, пишет `ImportRun`, публикует progress и запускает batch enrichment.
- Browser extension: `browser-extension/wb-favorites-exporter` собирает видимое избранное Wildberries, умеет auto-scroll, copy for Vybra и export в `.txt`/`.json`.
- Попарное сравнение: `/api/wishlist/compare/pair` подбирает валидную пару с учётом категории или цены ±10%, поддерживает режимы `all`, `top50`, `bottom50` и кэширует пару.
- ELO-рейтинг: `/api/wishlist/compare` сохраняет победителя, блокирует обе строки `Item` через `select_for_update()`, симметрично пересчитывает рейтинг и пишет историю `Comparison`.
- Дашборд: `/api/wishlist/dashboard` показывает total/week/day/active items, число сравнений и топы товаров с высокой уверенностью рейтинга.
- История цен: `PriceHistory` хранит изменения цены; `/api/wishlist/items/{item_id}/price-history` отдаёт последние 30 точек.
- Профиль: `/api/wishlist/profile`, `/api/wishlist/profile/reset-stats`, `/api/wishlist/profile/delete-all-items` управляют данными пользователя, сбросом рейтингов и массовым soft delete.
- Юридические страницы: `/legal/terms/`, `/legal/privacy/`, `/legal/contacts/`.
- Админка: `/admin/` подключена стандартным Django admin.

## 6. **DevOps & Инфраструктура**

| Направление | Реализация |
|---|---|
| Контейнеризация | `Dockerfile` для web и `Dockerfile.worker` для Celery worker; оба на `python:3.11-slim`, с непривилегированным `appuser`. |
| Production compose | `docker-compose.prod.yml`: `db`, `redis`, `web`; healthchecks, `restart: unless-stopped`, CPU/RAM limits, json-file log rotation. |
| Parsing overlay | `docker-compose.parsing.yml`: optional `celery`, `celery-beat`, `selenium/standalone-chromium:4`; включается через `./deploy.sh --with-parsing`. |
| Reverse proxy | Traefik labels на `web`, внешний Docker network `traefik`, TLS через `letsencrypt`, router `vybra-web`, host из `TRAEFIK_HOST`. |
| Database persistence | Named volume `postgres_data:/var/lib/postgresql/data`; отдельный `media_data` для `/app/media`. |
| Deploy | `deploy.sh` проверяет `.env`, Docker, `vm.overcommit_memory`, наличие сети и контейнера Traefik, делает `git pull --ff-only`, backup, build и `docker compose up -d`. |
| Backups | Перед деплоем `deploy.sh` делает `pg_dump | gzip` в `BACKUP_DIR`, хранит `BACKUP_KEEP` последних файлов. |
| CI/CD | Workflow-файлы в репозитории не обнаружены; автоматизация поставки реализована через root-level `deploy.sh`; локальный baseline включает Docker-only gates `lint` (Ruff) и `e2e` (Playwright) под compose profile `tools`. |
| Monitoring / health | Docker healthchecks для PostgreSQL, Redis, web и Selenium; приложение логирует в stdout с настраиваемыми `LOG_LEVEL` и `DJANGO_LOG_LEVEL`. |
| Static build | Tailwind собирается командой `npm run build:css`; Django `collectstatic` выполняется во время Docker build. |

## 7. **Безопасность**

| Мера | Реализация |
|---|---|
| Обязательные секреты | `SECRET_KEY` и `JWT_SECRET_KEY` читаются через `os.environ[...]`, приложение падает при отсутствии ключей. |
| Раздельная ротация JWT | `JWT_SECRET_KEY` отделён от Django `SECRET_KEY`; алгоритм `HS256`, access lifetime 1 час, refresh lifetime 7 дней. |
| HttpOnly cookies | Access и refresh токены ставятся в `HttpOnly`, `SameSite=Lax`; `secure` определяется HTTPS/`X-Forwarded-Proto`. |
| Auth marker без секрета | Cookie `vybra_logged_in` не HttpOnly и хранит только маркер `1`, чтобы frontend мог быстро понять состояние входа. |
| CSRF | Включён `django.middleware.csrf.CsrfViewMiddleware`; `CSRF_TRUSTED_ORIGINS` строится из `ALLOWED_HOSTS`. |
| HTTPS hardening | В production включены `SECURE_SSL_REDIRECT`, secure cookies, HSTS 31536000 секунд, preload, includeSubDomains, content type nosniff и referrer policy. |
| Reverse proxy awareness | `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')` для работы за Traefik. |
| Password validation | Django validators: similarity, minimum length 8, common password, numeric password. |
| Case-insensitive email uniqueness | Миграция создаёт unique index `auth_user_email_ci_unique_idx` на `LOWER(email)` для непустых email. |
| OAuth CSRF protection | Google OAuth flow хранит и проверяет `google_oauth_state` в Django session. |
| Data isolation | Все wishlist API фильтруют данные по `request.auth`; операции с item/comparison ограничены текущим пользователем. |
| Consistency under concurrency | `/api/wishlist/compare` использует `transaction.atomic()` и `select_for_update()` для парного обновления рейтингов. |
| Secret leakage prevention | `.gitignore` содержит `*.ini`, `.env`, `.env.local`, `.env.*.local`; resolved issue описывает удаление файла с OAuth-секретами. |
| Non-root containers | Docker images создают `appuser`/`appgroup` и запускают web/worker без root. |

## 8. **Производительность**

- Redis cache используется для пар результатов парного сравнения (`COMPARE_PAIR_CACHE_TTL`, по умолчанию 20 секунд) и для результатов парсинга товаров (`PARSED_PRODUCT_CACHE_TTL`, по умолчанию 172800 секунд).
- Долгие операции вынесены в Celery: добавление товара по URL, импорт избранного, batch enrichment, обновление цен, очистка истории цен и nightly recovery.
- Массовый импорт Wildberries разделён на быстрый этап создания записей без Selenium и фоновое обогащение только для товаров с неполными или устаревшими данными.
- ORM-запросы используют `select_related('product')`, `only(...)`, пагинацию и ограничение `limit` на API-методах.
- Dashboard считает основные метрики одним `aggregate()` с `Count(..., filter=Q(...))`.
- PostgreSQL модели содержат индексы по `article_code`, `marketplace`, `category`, `price`, `last_updated`, `user/is_active`, `elo_rating`, `comparisons_count` и истории сравнений/цен.
- Для сравнения отбрасываются невалидные товары: без цены, с пустым названием или с маркерами "товар не найден".
- Production PostgreSQL и Redis настроены под малый VPS: сниженные `shared_buffers`, `work_mem`, `max_connections`, Redis `maxmemory` и `allkeys-lru`.
- Gunicorn ограничивает ресурсные утечки через `--max-requests` и `--max-requests-jitter`; web использует 1 worker и 2 threads в production compose.
- WhiteNoise `CompressedManifestStaticFilesStorage` отдаёт сжатую версионированную статику без отдельного nginx.

## 9. **Сложные технические решения**

- Персональный ELO-рейтинг вместо простого списка. Проблема: пользователю трудно ранжировать десятки товаров вручную. Решение: попарные сравнения с адаптивным K-factor (`64`, `32`, `16`) и расчётом confidence по количеству сравнений.
- Консистентное обновление двух рейтингов. Проблема: результат одного сравнения одновременно меняет два `Item`, и конкурентные запросы могут повредить рейтинг. Решение: `transaction.atomic()`, `select_for_update()`, snapshot рейтингов до изменения и симметричный расчёт обеих дельт.
- Быстрый импорт избранного Wildberries. Проблема: Selenium-парсинг каждого товара делает импорт медленным и дорогим по памяти. Решение: сначала извлекать article codes и создавать товары из текста `name + url`, сразу показывать результат пользователю, а Selenium/API enrichment запускать только для устаревших или неполных товаров.
- Устойчивость к антибот-защите Wildberries. Проблема: часть данных недоступна через обычные HTTP-запросы. Решение: parser abstraction, несколько публичных WB API endpoints, Selenium fallback, remote Selenium container, user-agent rotation, optional proxies, cookies и retry/backoff настройки.
- Экономичная production-инфраструктура. Проблема: Celery, Beat и Selenium потребляют память даже без активного парсинга. Решение: core stack (`db`, `redis`, `web`) отделён от parsing overlay; тяжёлые сервисы запускаются только через `--with-parsing`.

## 10. **Ссылки и артефакты**

| Артефакт | Ссылка / путь |
|---|---|
| Production | https://vybra.prvms.ru |
| Landing page | `/` (server-rendered) |
| App (SPA) | `/app/*` (client-side routing) |
| Compare UI | `/app/compare/` |
| Items UI | `/app/items/` |
| Profile UI | `/app/profile/` |
| API base | `/api/` |
| API docs | `/api/docs` |
| Admin | `/admin/` |
| Legal pages | `/legal/terms/`, `/legal/privacy/`, `/legal/contacts/` |
| Browser extension | `browser-extension/wb-favorites-exporter/` |
| Production compose | `docker-compose.prod.yml` |
| Parsing overlay | `docker-compose.parsing.yml` |
| Deploy script | `deploy.sh` |
| Repository | Текущий Git-репозиторий; публичный URL не указан в файлах проекта. |

## 11. **Моя роль**

Full-stack разработка и эксплуатационная упаковка проекта:

- Backend: Django-модели, Django Ninja API, JWT-auth, Google OAuth2, profile endpoints, ELO-логика, статистика и история цен.
- Data layer: PostgreSQL-схема, индексы, уникальные constraints, case-insensitive email index, транзакционная логика сравнений.
- Async / parsing: Celery tasks, Redis broker/cache, Wildberries import pipeline, Selenium parser, batch enrichment, nightly recovery и task progress API.
- Frontend: Vite SPA (`front_redesign/`), client-side routing, landing page server-rendered for SEO.
- DevOps: Dockerfile, Dockerfile.worker, production/dev compose, optional parsing overlay, Traefik integration, deploy script, backups, healthchecks, resource limits и staticfiles build.
- Security hardening: secure cookies, HSTS, CSRF trusted origins, proxy SSL header, non-root containers и защита от случайного коммита секретных config-файлов.
