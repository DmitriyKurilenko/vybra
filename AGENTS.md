# AGENTS.md — Operating Manual

Этот файл — единый источник правды для любого агента (человека или LLM),
работающего над проектом Vybra. Соблюдение разделов обязательно.

## Mandatory Read Order

Перед любой нетривиальной работой агент обязан прочитать:

1. `docs/PROJECT_SUMMARY.md` — архитектура, стек, bounded contexts.
2. `docs/DECISIONS.md` — принятые архитектурные решения (ADR).
3. `docs/TASK_STATE.md` — текущий статус задач.
4. `docs/KNOWN_ISSUES.md` — открытые и закрытые баги.
5. `docs/DEV_LOG.md` — история изменений сессии.
6. `docs/RELEASE_NOTES.md` — пользовательски видимые изменения.
7. Соответствующие модули кода: `vybra/`, `authentication/`, `wishlist/`,
   `front_redesign/src/`, `Dockerfile`, `docker-compose*.yml`.

Только после этого формируется план и согласуется с ведущим разработчиком.

## Validation Baseline

Любое изменение проверяется по единому basеline'у. Частичная проверка
не считается выполненной. Если любой шаг падает — фиксим и прогоняем заново.

1. `docker compose down`
2. `docker compose up -d --build`
3. `docker compose run --rm web python manage.py check`
4. Targeted-тесты для затронутых модулей (если тестов нет —
   `python manage.py check` + ручная HTTP-проверка затронутых страниц).
5. Ручная проверка HTTP/рендера затронутых страниц:
   - `curl -sI http://localhost:8000/` → 200
   - `curl -sI http://localhost:8000/app/` → 200
   - `curl -sI http://localhost:8000/api/docs` → 200
   - прочие эндпоинты, затронутые изменением

Проект работает только в Docker. Локальный запуск без Docker не гарантирует
повторяемости и не принимается как валидация.

## Update Ritual

После любого нетривиального изменения агент обязан обновить документацию:

- `docs/DECISIONS.md` — если изменилось поведение или инвариант (новый ADR).
- `docs/TASK_STATE.md` — статус задачи (done / in-progress / blocked).
- `docs/DEV_LOG.md` — дата, файлы, валидация, риски.
- `docs/KNOWN_ISSUES.md` — если баг найден или закрыт.
- `docs/RELEASE_NOTES.md` — если изменение видно пользователю.
- `CHANGELOG.md` — запись в формате Keep a Changelog.
- `VERSION` — bump версии при пользовательски видимом релизе.

Документация — часть Definition of Done. Без неё задача не закрыта.

## Decision Rules

1. **Качество — приоритет.** Никаких уступок в сторону скорости или простоты
   решения. Никаких заплаток и точечных костылей. Комплексный подход.
2. **Не гадай и не действуй наугад.** Изучай документацию и принимай решения
   со знанием дела. При сомнениях — остановись и спроси.
3. **Правило самоограничения:** если что-то непонятно, есть несколько вариантов
   решения или задача не закрывается за 2 итерации — остановись и спроси,
   не зацикливайся.
4. **Порядок выполнения:**
   1. Глубокий анализ задачи (с учётом Mandatory Read Order).
   2. Детальный план реализации.
   3. Остановка и ожидание одобрения плана.
   4. Реализация — только после явного одобрения.
5. **Диагностика:** если нужна диагностика — составь максимально подробный
   и самодостаточный скрипт или набор инструкций, чтобы собрать все логи
   за один прогон.
6. **Никаких частичных решений.** Частичная проверка ≠ выполнено.
7. **Docker only.** Проект работает только в Docker.
8. **Код без комментариев**, если обратное не запрошено явно.
9. **Ведущий разработчик** подходит к задаче с максимальной ответственностью.
   Отвечай грамотным техническим языком, без телеграфного стиля и сленга.

## Architecture Snapshot

- Backend: Django 5 + django-ninja, PostgreSQL 17, Redis 7, Celery.
- Frontend: Vite + React SPA (`front_redesign/`), отдаётся Django под `/app/*`.
- Static: WhiteNoise `CompressedManifestStaticFilesStorage` под `/static/`,
  SPA-ассеты под `/static/spa/`.
- Auth: JWT в HttpOnly cookies + optional Google OAuth2.
- PWA: service worker под `/sw.js` (scope `/`), manifest под
  `/manifest.webmanifest`. Иконки — `/static/spa/icons/`.
- Deploy: Docker Compose, shared Traefik reverse proxy, `deploy.sh`.

## Conventions

- Python: PEP 8, типы через django-ninja Pydantic-схемы.
- JS: React 18, функциональные компоненты, хуки, inline-styles через
  tokens (`theme/tokens.js`). CSS — только глобальные анимации в `index.css`.
- Именование: camelCase для JS, snake_case для Python.
- Секреты — только через `os.environ[...]` (обязательные) или
  `os.environ.get(...)` (опциональные). Никогда не коммитить секреты.
- Миграции — только через `makemigrations` + `migrate`.
- Коммиты — только когда явно запрошено пользователем.
