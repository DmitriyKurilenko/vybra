# Vybra - Умное управление списком желаний 🎯

Веб-приложение для управления списком желаний с использованием системы парного сравнения и алгоритма ELO для приоритизации покупок.

## Возможности

- **Парное сравнение**: Интуитивное сравнение товаров в стиле dating-приложений
- **ELO рейтинг**: Автоматический расчет приоритетов на основе ваших предпочтений
- **Интеграция с маркетплейсами**: Поддержка Ozon и Wildberries
- **Отслеживание цен**: Автоматическое обновление и история цен
- **Статистика**: Визуализация данных и аналитика
- **Режимы сравнения**: Все товары, топ 50%, нижние 50%

## Технологии

- **Backend**: Django 5.0, Django Ninja API
- **Frontend**: AlpineJS, DaisyUI (Tailwind CSS)
- **База данных**: PostgreSQL
- **Фоновые задачи**: Celery + Redis
- **Контейнеризация**: Docker, docker-compose

## Быстрый старт

### Вариант 1: С Docker (рекомендуется)

```bash
# Клонировать репозиторий
git clone <repository-url>
cd vybra

# Создать .env файл
cp .env.example .env

# Запустить все сервисы
docker-compose up -d

# Выполнить миграции
docker-compose exec web python manage.py migrate

# Создать суперпользователя
docker-compose exec web python manage.py createsuperuser

# Приложение доступно на http://localhost:8000
```

### Вариант 2: Локальная разработка

#### Требования

- Python 3.11+
- PostgreSQL 15+
- Redis 7+

#### Установка

```bash
# Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # На Windows: venv\Scripts\activate

# Установить зависимости
pip install -r requirements.txt

# Создать .env файл
cp .env.example .env

# Отредактировать .env с вашими настройками
# Убедитесь, что PostgreSQL и Redis запущены

# Выполнить миграции
python manage.py migrate

# Создать суперпользователя
python manage.py createsuperuser

# Собрать статические файлы
python manage.py collectstatic --noinput

# Запустить сервер разработки
python manage.py runserver
```

#### Запуск Celery (в отдельных терминалах)

```bash
# Worker
celery -A vybra worker -l info

# Beat scheduler (для периодических задач)
celery -A vybra beat -l info
```

## Использование

### 1. Дашборд
- Просмотр статистики
- Топ-товары по рейтингу
- Быстрый доступ к функциям

### 2. Добавление товаров
- Перейти в раздел "Товары"
- Нажать "Добавить товар"
- Указать название, URL, магазин, цену
- Для Ozon и Wildberries цены будут обновляться автоматически

### 3. Сравнение
- Перейти в раздел "Сравнение"
- Выбрать режим (все товары / топ 50% / нижние 50%)
- Выбрать предпочтительный товар
- Рейтинги обновятся автоматически

### 4. API

Документация API доступна на `/api/docs`

Основные эндпоинты:
- `GET /api/wishlist/items` - список товаров
- `POST /api/wishlist/items` - создать товар
- `GET /api/wishlist/compare/pair` - получить пару для сравнения
- `POST /api/wishlist/compare` - сохранить результат сравнения
- `GET /api/wishlist/stats` - статистика

## Структура проекта

```
vybra/
├── vybra/              # Главный модуль Django
│   ├── settings.py     # Настройки
│   ├── urls.py         # URL конфигурация
│   └── celery.py       # Celery конфигурация
├── wishlist/           # Приложение wishlist
│   ├── models.py       # Модели (Item, Comparison, PriceHistory)
│   ├── api.py          # API endpoints (Django Ninja)
│   ├── views.py        # HTML views
│   ├── tasks.py        # Celery tasks
│   └── admin.py        # Django admin
├── authentication/     # Приложение аутентификации
│   └── api.py          # JWT auth endpoints
├── templates/          # HTML шаблоны
│   ├── base.html       # Базовый шаблон
│   └── wishlist/       # Шаблоны wishlist
├── static/             # Статические файлы
├── requirements.txt    # Python зависимости
├── docker-compose.yml  # Docker конфигурация
└── Dockerfile          # Docker образ
```

## Celery задачи

### Автоматическое обновление цен

```python
# Вручную запустить обновление
python manage.py shell
>>> from wishlist.tasks import update_prices
>>> update_prices.delay()
```

### Настройка периодических задач

В Django admin (`/admin/`) настройте периодические задачи:
- Обновление цен: каждый день
- Очистка старой истории: каждую неделю

## Разработка

### Миграции

```bash
# Создать миграции
python manage.py makemigrations

# Применить миграции
python manage.py migrate
```

### Тестирование

```bash
# Запустить тесты
pytest

# С покрытием
pytest --cov=wishlist --cov=authentication
```

### Линтинг

```bash
# Black форматирование
black .

# Flake8 проверка
flake8
```

## Переменные окружения

Смотрите `.env.example` для полного списка.

Основные переменные:
- `DEBUG` - режим отладки (True/False)
- `SECRET_KEY` - секретный ключ Django
- `DB_NAME`, `DB_USER`, `DB_PASSWORD` - настройки PostgreSQL
- `REDIS_URL` - URL Redis сервера
- `REDIS_CACHE_URL` - Redis для кэша (по умолчанию можно использовать тот же Redis)
- `GOOGLE_CLIENT_ID` - OAuth Client ID для входа через Google
- `GOOGLE_CLIENT_SECRET` - OAuth Client Secret для серверного обмена кода
- `COMPARE_PRICE_TOLERANCE` - допуск для подбора пары по цене (по умолчанию `0.10` = ±10%)
- `COMPARE_PAIR_CACHE_TTL` - TTL кэша пары сравнения в секундах (по умолчанию `20`)

### Вход через Google

1. Создайте OAuth 2.0 Client ID в Google Cloud Console (тип: Web application)
2. Добавьте Authorized JavaScript origins:
	- `http://localhost:8000` (dev)
	- `https://your-domain.com` (prod)
3. Добавьте Authorized redirect URI:
	- `http://localhost:8000/google/callback/` (dev)
	- `https://your-domain.com/google/callback/` (prod)
4. Пропишите `GOOGLE_CLIENT_ID` и `GOOGLE_CLIENT_SECRET` в `.env` / `.env.prod`
5. Пересоберите приложение (`./deploy.sh` или `docker compose up -d --build`)

После этого кнопка входа через Google будет доступна на страницах `/login/` и `/register/`.

## Продакшн

### Важные настройки для продакшна:

1. Установить `DEBUG=False`
2. Изменить `SECRET_KEY` и `JWT_SECRET_KEY`
3. Настроить `ALLOWED_HOSTS`
4. Использовать реальную БД PostgreSQL
5. Настроить SMTP для email
6. Использовать HTTPS
7. Настроить брандмауэр и безопасность

### Режим для сервера 1 CPU / 1 GB / 10 GB

Для малоресурсного сервера используйте two-file compose (базовый + prod override):

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

HTTPS-only прод:

```bash
cp .env.prod.example .env.prod
# заполните SECRET_KEY и ALLOWED_HOSTS
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Что включает `docker-compose.prod.yml`:
- лимиты памяти/CPU для `db`, `redis`, `web`, `celery`
- `restart: unless-stopped`
- `healthcheck` для зависимостей
- ротацию логов Docker (`max-size`, `max-file`)

Остановка:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml down
```

Проверка состояния:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs --tail=100 web
```

### Сбор статики

```bash
python manage.py collectstatic --noinput
```

### Скрипты деплоя и Let's Encrypt

В проекте добавлены готовые скрипты:

- `deploy.sh` — production деплой (по умолчанию использует `docker-compose.yml` + `docker-compose.prod.yml`)
- `letsencrypt-init.sh` — первичный выпуск сертификата Let's Encrypt (standalone)
- `letsencrypt-renew.sh` — продление сертификатов и перезапуск web

Примеры:

```bash
# Деплой
./deploy.sh

# Первичный выпуск сертификата
./letsencrypt-init.sh admin@example.com example.com www.example.com

# Продление сертификатов
./letsencrypt-renew.sh
```

По умолчанию скрипты берут `.env.prod`. Можно переопределить:

```bash
ENV_FILE=.env.prod ./deploy.sh
ENV_FILE=.env.prod ./letsencrypt-renew.sh
```

### HTTPS-only setup (один раз, без повторов)

```bash
# 1) Подготовить env
cp .env.prod.example .env.prod
# заполните SECRET_KEY и ALLOWED_HOSTS

# 2) Поднять приложение
ENV_FILE=.env.prod ./deploy.sh

# 3) Подготовить nginx под ACME challenge (HTTP)
sudo ./nginx-setup.sh --mode pre --domain example.com --www www.example.com

# 4) Выпустить сертификат
./letsencrypt-init.sh admin@example.com example.com www.example.com

# 5) Переключить nginx в HTTPS-only
sudo ./nginx-setup.sh --mode post --domain example.com --www www.example.com
```

После этого приложение работает только по HTTPS.

Для автопродления добавьте cron:

```bash
0 3 * * * /path/to/vybra/letsencrypt-renew.sh >> /var/log/letsencrypt-renew.log 2>&1
```

## Поддержка

Для вопросов и предложений создайте issue в репозитории.

## Лицензия

MIT License

---

Разработано с ❤️ для умного управления списком желаний
