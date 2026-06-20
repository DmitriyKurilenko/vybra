from django.urls import path
from . import views

app_name = 'authentication'

# «/» — публичный маркетинговый лендинг. Вход/регистрация — в SPA (/app).
# Здесь же server-side поток Google OAuth.
urlpatterns = [
    path('', views.landing, name='landing'),
    path('google/login/', views.google_login_start, name='google_login_start'),
    path('google/callback/', views.google_login_callback, name='google_callback'),
]
