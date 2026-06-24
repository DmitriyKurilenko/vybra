"""
Project-level views.

SPA shell: отдаёт собранную оболочку front_redesign/dist/index.html на все
клиентские маршруты. Ассеты (хешированные Vite) обслуживает WhiteNoise под
/static/spa/, поэтому здесь только HTML-оболочка без длительного кэширования —
при каждом деплое она ссылается на новые хешированные бандлы.

PWA: /sw.js — service worker со scope "/", /manifest.webmanifest — веб-манифест.
Оба файла собираются Vite из front_redesign/public/ и отдаются из dist/ с
заголовками, разрешающими установку как PWA на iOS и Android.
"""
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.http import (
    HttpResponse,
    HttpResponseServerError,
)


@lru_cache(maxsize=1)
def _read_index() -> str:
    """Прочитать собранную оболочку один раз за процесс."""
    with open(settings.FRONTEND_INDEX, encoding='utf-8') as fh:
        return fh.read()


def spa_index(request):
    """Отдать оболочку SPA. Клиентский роутинг обрабатывается на фронте."""
    try:
        html = _read_index()
    except FileNotFoundError:
        return HttpResponseServerError(
            'SPA bundle not found. Run the frontend build (front_redesign) '
            'before collectstatic.'
        )

    response = HttpResponse(html, content_type='text/html; charset=utf-8')
    # Оболочка не кэшируется: ссылается на хешированные ассеты, меняется при деплое.
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response


def _serve_dist_file(filename: str, content_type: str):
    """Отдать статический файл из front_redesign/dist/ с no-cache.

    Service worker и manifest меняются при каждом деплое вместе с бандлом,
    поэтому no-cache безопасно — браузер всегда забирает свежую версию.
    """
    path: Path = settings.FRONTEND_DIST / filename
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        return HttpResponseServerError(
            f'{filename} not found. Run the frontend build (front_redesign) '
            'before collectstatic.'
        )
    response = HttpResponse(data, content_type=content_type)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response


def service_worker(request):
    """Отдать service worker со scope "/".

    Service-Worker-Allowed: / позволяет SW контролировать весь origin,
    а не только директорию, в которой он лежит. Так /sw.js контролирует
    и /app/* (navigation), и /static/spa/* (ассеты).
    """
    response = _serve_dist_file('sw.js', 'application/javascript; charset=utf-8')
    response['Service-Worker-Allowed'] = '/'
    return response


def manifest(request):
    """Отдать веб-манифест PWA."""
    return _serve_dist_file('manifest.webmanifest', 'application/manifest+json; charset=utf-8')
