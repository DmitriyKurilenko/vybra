# Переносимый промт: добавить гейты валидации ruff + Playwright в Docker-проект

> Назначение: вставлять этот промт в любой проект с Docker, Python-бэкендом и JS/TS-фронтендом,
> чтобы агент добавил локально запускаемый статанализ (ruff) и сквозную браузерную проверку
> (Playwright) как обязательные гейты. Сформулирован по факту реального внедрения.

---

## Промт (копировать целиком)

Добавь в этот проект два локально запускаемых гейта валидации и сделай их частью ритуала
проверки. Не клади dev-инструменты в production-образ. Перед интеграцией прочитай реальные
конфиги проекта (Dockerfile, docker-compose, pyproject.toml/cargo.toml/package.json, CI) и
оперируй обнаруженными фактами, а не догадками.

### 0. Определи стек проекта

Перед любыми изменениями выясни:

| Что | Где смотреть |
|-----|--------------|
| Пакетный менеджер Python | `pyproject.toml` → `build-system`; `requirements*.txt`; `uv.lock` |
| Базовая команда установки зависимостей | `Dockerfile` (pip install / uv sync / poetry install ...) |
| Версия Python | `Dockerfile`, `.python-version`, `pyproject.toml` |
| Пакетный менеджер Node | `package.json` → `"packageManager"` или `pnpm-lock.yaml` / `yarn.lock` / `package-lock.json` |
| Структура каталогов | Где лежит бэкенд (backend/, src/, apps/) и фронтенд (frontend/, client/, src/) |
| Уже есть ruff? | `pyproject.toml` → `tool.ruff`; `requirements-dev.txt` |
| Уже есть playwright? | `package.json` → `devDependencies["@playwright/test"]` |

---

### 1. ruff (статанализ Python), без загрязнения прод-образа

- Если ruff уже пиннится в `pyproject.toml` (group `dev`) или `requirements-dev.txt` —
  используй найденную версию; иначе добавь в `dependency-groups.dev` / `requirements-dev.txt`.
- Создай отдельный `Dockerfile.dev` (FROM того же python-базового образа, что и основной,
  без multi-stage target `runtime`). Ставь только dev-зависимости и запускай `ruff check .`.
- Добавь в `docker-compose.yml` сервис `lint` под профилем `tools`
  (чтобы не поднимался обычным `up`):
  ```yaml
  lint:
    build:
      context: .          # или путь к бэкенду, если он в подкаталоге
      dockerfile: Dockerfile.dev
    profiles: [tools]
    volumes:
      - ./backend:/app    # путь по факту
    command: ["ruff", "check", "."]
  ```
- Запуск: `docker compose run --rm lint`. Конфиг ruff бери из `pyproject.toml`
  (тот же, что в CI, если есть).
- Прогони и доведи до «All checks passed!». Реальные находки — чини в коде, не подавляй вслепую.

---

### 2. Playwright (сквозная проверка SPA в реальном браузере)

#### 2.1. Определи версию и установи пакет
- Проверь, есть ли `@playwright/test` в `devDependencies` фронтенда.
  Если нет — запроси актуальную стабильную версию (`npm view @playwright/test version`
  или аналог для pnpm/yarn) и добавь в `devDependencies`.
- **Тег официального Docker-образа обязан совпадать с версией пакета:**
  `mcr.microsoft.com/playwright:vX.Y.Z-jammy`

#### 2.2. Конфигурация Playwright
Создай `playwright.config.ts` в корне фронтенда:
```ts
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  reporter: [['blob', { outputDir: 'test-results' }], ['html', { outputDir: 'playwright-report' }]],
  use: {
    baseURL: 'http://web:3000',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'npm run build && npm run preview',
    url: 'http://web:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
})
```

Добавь npm-скрипт:
```json
"test:e2e": "playwright test"
```

#### 2.3. Same-origin контур (критично для cookie и CSRF)

1. В `vite.config.ts` / `vite.config.js` добавь секцию `preview` с proxy на backend:
   ```ts
   preview: {
     port: 3000,
     proxy: {
       '/api': { target: 'http://backend:8000', changeOrigin: true },
       '/ws': { target: 'http://backend:8000', ws: true, changeOrigin: true },
     },
   }
   ```
   Если проект не на Vite — аналогично настрой `next dev --port 3000` / `nuxt dev` и т.д.
   Главное: SPA на `:3000` проксирует `/api` и `/ws` на бэкенд внутри compose-сети.

2. При сборке SPA передай `VITE_API_URL=/api` (относительный), чтобы фронтенд
   не ходил на внешний origin.

#### 2.4. Docker-сервисы для e2e

```yaml
services:
  # статика SPA (preview-сервер)
  web:
    build:
      context: .
      dockerfile: docker/frontend.Dockerfile
      target: builder      # или как в проекте называется stage со статикой
    profiles: [tools]
    environment:
      VITE_API_URL: /api
    command: sh -c "npm run preview -- --port 3000"
    ports:
      - "3000:3000"
    depends_on:
      backend:
        condition: service_healthy

  # одноразовый сид тестовых данных
  seed:
    build:
      context: .
      dockerfile: docker/backend.Dockerfile   # dev-образ не нужен, нужен только Django
    profiles: [tools]
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    env_file:
      - path: .env
        required: false
    # идемпотентное создание тестового пользователя (адаптируй под свой auth)
    command: >
      python -c
      "import django; django.setup();
       from django.contrib.auth import get_user_model;
       User = get_user_model();
       User.objects.filter(username='testuser').exists() or
       User.objects.create_superuser('testuser', 'test@test.test', 'testpass123')"

  # сам Playwright
  e2e:
    image: mcr.microsoft.com/playwright:vX.Y.Z-jammy   # замени на актуальную версию
    profiles: [tools]
    depends_on:
      seed:
        condition: service_completed_successfully
      web:
        condition: service_started
    volumes:
      - ./frontend:/app
      - pw-node-modules:/app/node_modules
    command: sh -c "cd /app && npm install && npx playwright test"
    extra_hosts:
      - "host.docker.internal:host-gateway"

volumes:
  pw-node-modules:
```

#### 2.5. Минимальный e2e-тест

Создай `frontend/e2e/smoke.spec.ts`:
```ts
import { test, expect } from '@playwright/test'

test('homepage loads', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading')).toBeVisible()
})

test('login flow', async ({ page }) => {
  await page.goto('/login')
  await page.getByPlaceholder(/email|почта|e-mail/i).fill('test@test.test')
  await page.getByPlaceholder(/пароль|password/i).fill('testpass123')
  await page.getByRole('button', { name: /войти|login|sign in/i }).click()
  // адаптируй ожидаемый URL под свой роутер
  await expect(page).toHaveURL(/\/(cabinet|listings|dashboard)/)
})
```

---

### Грабли, которые надо обойти (проверено на практике)

- **In-memory access-токен теряется при `page.goto`.** Полная перезагрузка страницы
  разлогинивает SPA, guard уводит на `/login`. Между разделами навигируй кликами
  по меню (клиентский роутинг), а не `page.goto` на защищённый путь. Сам вход
  делай через форму `/login`.
- **Свежий тенант открывает онбординг.** Проверь, не перехватывает ли мастер
  настройки работу; если да — пройди/пропусти его в начале сценария.
- **Диагностируй падения по артефактам, а не перебором.** Читай ARIA-снимок из
  `test-results/<...>/error-context.md` и исходник компонентов; делай прицельный
  фикс по факту.
- **Селекторы по доступному имени/тексту**, а не по случайным классам
  (`getByRole`, `getByPlaceholder`, `getByText`).
- **Время сборки.** Если `npm run build` в web-сервисе работает долго, кэшируй
  `node_modules` через named volume или mount.

---

### Ритуал

Внеси оба шага в Validation Baseline проекта (`AGENTS.md` / `README` / `CONTRIBUTING.md`):
```
docker compose run --rm lint         # ruff — при изменениях Python
docker compose --profile tools run --rm e2e   # e2e — при изменениях UI
```
«Зелёные unit-тесты» без ruff и e2e не считаются «работает».

---

### Критерий приёмки

- `docker compose run --rm lint` → «All checks passed!»
- `docker compose --profile tools run --rm e2e` → хотя бы один сквозной сценарий
  `passed` в headless-браузере (вход → ключевой пользовательский поток → проверка
  результата на экране)

---

### Чеклист адаптации под новый проект

- [ ] Определён пакетный менеджер Python (pip / uv / poetry / pdm)
- [ ] Определена структура каталогов (бэкенд и фронтенд)
- [ ] Определён пакетный менеджер Node (npm / pnpm / yarn)
- [ ] `Dockerfile.dev` использует тот же base image, что и prod
- [ ] `lint` сервис монтирует только бэкенд-код в `/app`
- [ ] `seed` сервис адаптирован под модель пользователя проекта
- [ ] `playwright.config.ts` → `baseURL` и `webServer.url` указывают на `web:3000`
- [ ] `preview.proxy` настроен для `/api` и `/ws` на backend внутри compose-сети
- [ ] `VITE_API_URL=/api` при сборке через `environment` в compose
- [ ] Артефакты (`test-results/`, `playwright-report/`, `blob-report/`) в `.gitignore`