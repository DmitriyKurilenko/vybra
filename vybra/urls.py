"""
URL configuration for vybra project.

Раздача single-origin: «/» — маркетинговый лендинг, приложение (SPA
front_redesign) — под /app, API на /api, админка на /admin, юридические
страницы и Google OAuth — server-rendered. Клиентский роутинг SPA — на фронте.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from ninja import NinjaAPI

from wishlist.api import router as wishlist_router
from authentication.api import router as auth_router
from .views import spa_index, service_worker, manifest

# Create main API instance
api = NinjaAPI(title="Vybra API", version="1.0.0")

# Register routers
api.add_router("/wishlist/", wishlist_router)
api.add_router("/auth/", auth_router)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),
    path('', include('authentication.urls')),  # Лендинг на «/» + Google OAuth
    path('', include('wishlist.urls')),         # Legal pages
    # PWA: service worker со scope "/" и веб-манифест.
    path('sw.js', service_worker, name='sw'),
    path('manifest.webmanifest', manifest, name='manifest'),
    # Приложение (SPA) под /app и любыми вложенными путями.
    re_path(r'^app(?:/.*)?$', spa_index, name='spa'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
