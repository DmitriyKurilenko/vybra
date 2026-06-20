"""
Project-level views.

SPA shell: отдаёт собранную оболочку front_redesign/dist/index.html на все
клиентские маршруты. Ассеты (хешированные Vite) обслуживает WhiteNoise под
/static/spa/, поэтому здесь только HTML-оболочка без длительного кэширования —
при каждом деплое она ссылается на новые хешированные бандлы.
"""
from functools import lru_cache

from django.conf import settings
from django.http import HttpResponse, HttpResponseServerError


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
