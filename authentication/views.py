from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.models import User
import os
import secrets
import requests
from urllib.parse import urlencode

from .api import create_tokens, build_unique_username_from_email, normalize_email, set_auth_cookies


def landing(request):
    """Посадочная страница"""
    return render(request, 'landing.html')


def login_view(request):
    """Страница входа"""
    return render(request, 'authentication/login.html', {
        'google_enabled': bool(os.environ.get('GOOGLE_CLIENT_ID') and os.environ.get('GOOGLE_CLIENT_SECRET')),
    })


def register_view(request):
    """Страница регистрации"""
    return render(request, 'authentication/register.html', {
        'google_enabled': bool(os.environ.get('GOOGLE_CLIENT_ID') and os.environ.get('GOOGLE_CLIENT_SECRET')),
    })


def google_login_start(request):
    """Начало авторизации через Google (OAuth2 Authorization Code Flow)"""
    client_id = os.environ.get('GOOGLE_CLIENT_ID')
    client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')

    if not client_id or not client_secret:
        return HttpResponse('Google login is not configured', status=500)

    state = secrets.token_urlsafe(24)
    request.session['google_oauth_state'] = state

    redirect_uri = request.build_absolute_uri(reverse('authentication:google_callback'))

    params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'openid email profile',
        'state': state,
        'access_type': 'online',
        'prompt': 'select_account',
    }

    query = urlencode(params)
    return HttpResponse(status=302, headers={'Location': f"https://accounts.google.com/o/oauth2/v2/auth?{query}"})


def google_login_callback(request):
    """Callback авторизации через Google"""
    expected_state = request.session.pop('google_oauth_state', None)
    received_state = request.GET.get('state')
    code = request.GET.get('code')

    if not expected_state or not received_state or expected_state != received_state:
        return HttpResponse('Invalid OAuth state', status=400)

    if not code:
        return HttpResponse('Missing OAuth code', status=400)

    client_id = os.environ.get('GOOGLE_CLIENT_ID')
    client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
    redirect_uri = request.build_absolute_uri(reverse('authentication:google_callback'))

    try:
        token_response = requests.post(
            'https://oauth2.googleapis.com/token',
            data={
                'code': code,
                'client_id': client_id,
                'client_secret': client_secret,
                'redirect_uri': redirect_uri,
                'grant_type': 'authorization_code',
            },
            timeout=10,
        )
        token_response.raise_for_status()
        token_data = token_response.json()
    except requests.RequestException:
        return HttpResponse('Google token exchange failed', status=502)

    access_token = token_data.get('access_token')
    if not access_token:
        return HttpResponse('Google access token missing', status=502)

    try:
        userinfo_response = requests.get(
            'https://openidconnect.googleapis.com/v1/userinfo',
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=10,
        )
        userinfo_response.raise_for_status()
        userinfo = userinfo_response.json()
    except requests.RequestException:
        return HttpResponse('Google userinfo request failed', status=502)

    email = userinfo.get('email')
    email_verified = userinfo.get('email_verified', False)
    if not email or not email_verified:
        return HttpResponse('Google email is not verified', status=403)
    email = normalize_email(email)

    user = User.objects.filter(email__iexact=email).order_by('id').first()
    if not user:
        user = User.objects.create_user(
            username=build_unique_username_from_email(email),
            email=email,
        )
        user.set_unusable_password()
        user.first_name = userinfo.get('given_name', '') or ''
        user.last_name = userinfo.get('family_name', '') or ''
        user.save(update_fields=['password', 'first_name', 'last_name'])

    tokens = create_tokens(user)
    response = HttpResponseRedirect('/dashboard/')
    set_auth_cookies(response, tokens, request=request)
    return response
