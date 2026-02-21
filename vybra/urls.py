"""
URL configuration for vybra project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from ninja import NinjaAPI

from wishlist.api import router as wishlist_router
from authentication.api import router as auth_router

# Create main API instance
api = NinjaAPI(title="Vybra API", version="1.0.0")

# Register routers
api.add_router("/wishlist/", wishlist_router)
api.add_router("/auth/", auth_router)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),
    path('', include('authentication.urls')),  # Authentication pages
    path('', include('wishlist.urls')),  # Frontend URLs
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
