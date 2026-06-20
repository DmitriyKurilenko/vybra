from django.urls import path
from . import views

app_name = 'wishlist'

# Страницы приложения (dashboard/compare/items/profile) теперь обслуживает SPA
# (front_redesign). Server-rendered остаются только юридические документы.
urlpatterns = [
    path('legal/<slug:doc>/', views.legal_document, name='legal_document'),
]
