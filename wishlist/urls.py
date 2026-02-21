from django.urls import path
from . import views

app_name = 'wishlist'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('compare/', views.compare, name='compare'),
    path('items/', views.items, name='items'),
    path('profile/', views.profile, name='profile'),
    path('legal/<slug:doc>/', views.legal_document, name='legal_document'),
]
