from django.urls import path
from . import views

app_name = 'authentication'

urlpatterns = [
    path('', views.landing, name='landing'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('google/login/', views.google_login_start, name='google_login_start'),
    path('google/callback/', views.google_login_callback, name='google_callback'),
]
