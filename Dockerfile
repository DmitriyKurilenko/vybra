# ─── Stage 1: сборка SPA (front_redesign) ────────────────────────────────────
# Node нужен только на этапе сборки; в runtime-образ не попадает.
FROM node:20-slim AS frontend

WORKDIR /frontend

# Зависимости отдельным слоем — кэшируются, пока не меняется package.json.
COPY front_redesign/package.json ./
RUN npm install

# Исходники и сборка: Vite пишет в /frontend/dist с base=/static/spa/.
COPY front_redesign/ ./
RUN npm run build


# ─── Stage 2: runtime ────────────────────────────────────────────────────────
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    HOME=/tmp

WORKDIR /app

# Только runtime-зависимости — gcc и Chromium убраны.
# Chromium нужен только celery-worker → см. Dockerfile.worker
RUN echo '#!/bin/sh\nexit 101' > /usr/sbin/policy-rc.d && chmod +x /usr/sbin/policy-rc.d \
    && apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    && rm -f /usr/sbin/policy-rc.d \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
# Python-зависимости
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Исходники
COPY . /app/

# Собранный SPA из стадии frontend (front_redesign/dist готовится npm run build).
COPY --from=frontend /frontend/dist /app/front_redesign/dist

# Staticfiles собираются во время сборки образа (включая SPA под /static/spa/).
# Реальные секреты для collectstatic не нужны.
ARG SECRET_KEY=build-time-dummy-key-not-used-in-production
ARG JWT_SECRET_KEY=build-time-dummy-jwt-key-not-used-in-production
RUN SECRET_KEY="$SECRET_KEY" JWT_SECRET_KEY="$JWT_SECRET_KEY" \
    python manage.py collectstatic --noinput

# Непривилегированный пользователь
RUN groupadd --gid 1001 appgroup \
    && useradd --uid 1001 --gid appgroup --shell /bin/bash --no-create-home appuser \
    && chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

CMD ["gunicorn", "vybra.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "2", "--timeout", "120"]
