FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies including Chromium for Selenium
RUN apt-get update && apt-get install -y \
    postgresql-client \
    gcc \
    wget \
    curl \
    unzip \
    # Chromium and runtime dependencies (нужны для celery-воркера с Selenium)
    chromium \
    chromium-driver \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app/

# Collect static files at build time.
# SECRET_KEY и JWT_SECRET_KEY нужны только чтобы Django запустился —
# для collectstatic реальные секреты не требуются.
ARG SECRET_KEY=build-time-dummy-key-not-used-in-production
ARG JWT_SECRET_KEY=build-time-dummy-jwt-key-not-used-in-production
RUN SECRET_KEY="$SECRET_KEY" JWT_SECRET_KEY="$JWT_SECRET_KEY" \
    python manage.py collectstatic --noinput

# Создаём непривилегированного пользователя для запуска приложения
RUN groupadd --gid 1001 appgroup \
    && useradd --uid 1001 --gid appgroup --shell /bin/bash --no-create-home appuser \
    && chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

CMD ["gunicorn", "vybra.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "2", "--timeout", "120"]
