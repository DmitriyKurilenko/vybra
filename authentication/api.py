"""
Authentication API endpoints - Django Ninja
"""
import logging

from ninja import Router
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.http import JsonResponse
import jwt
from django.conf import settings

logger = logging.getLogger(__name__)

from wishlist.ninja_utils import JWTAuth, ValidationError, AuthenticationError
from .schemas import (
    RegisterSchema,
    LoginSchema,
    TokenSchema,
    UserSchema,
    RefreshTokenSchema,
    AuthMessageSchema,
)


router = Router(tags=["Authentication"])
auth = JWTAuth()

ACCESS_COOKIE_NAME = "vybra_access_token"
REFRESH_COOKIE_NAME = "vybra_refresh_token"
AUTH_MARKER_COOKIE_NAME = "vybra_logged_in"


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def _is_secure_request(request) -> bool:
    forwarded_proto = (request.META.get('HTTP_X_FORWARDED_PROTO') or '').lower()
    return request.is_secure() or forwarded_proto == 'https'


def set_auth_cookies(response, tokens: dict, request=None):
    secure_cookie = _is_secure_request(request) if request is not None else (not settings.DEBUG)
    access_max_age = int(settings.JWT_ACCESS_TOKEN_LIFETIME.total_seconds())
    refresh_max_age = int(settings.JWT_REFRESH_TOKEN_LIFETIME.total_seconds())
    common = {
        'path': '/',
        'secure': secure_cookie,
        'samesite': 'Lax',
    }

    response.set_cookie(
        ACCESS_COOKIE_NAME,
        tokens['access_token'],
        max_age=access_max_age,
        httponly=True,
        **common,
    )
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        tokens['refresh_token'],
        max_age=refresh_max_age,
        httponly=True,
        **common,
    )
    response.set_cookie(
        AUTH_MARKER_COOKIE_NAME,
        '1',
        max_age=refresh_max_age,
        httponly=False,
        **common,
    )


def clear_auth_cookies(response):
    response.delete_cookie(ACCESS_COOKIE_NAME, path='/')
    response.delete_cookie(REFRESH_COOKIE_NAME, path='/')
    response.delete_cookie(AUTH_MARKER_COOKIE_NAME, path='/')


def create_tokens(user):
    """Создать access и refresh токены"""
    now = timezone.now()
    access_payload = {
        'user_id': user.id,
        'email': user.email,
        'exp': now + settings.JWT_ACCESS_TOKEN_LIFETIME,
        'type': 'access'
    }

    refresh_payload = {
        'user_id': user.id,
        'email': user.email,
        'exp': now + settings.JWT_REFRESH_TOKEN_LIFETIME,
        'type': 'refresh'
    }

    access_token = jwt.encode(
        access_payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    refresh_token = jwt.encode(
        refresh_payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'bearer'
    }


def _cookie_auth_response() -> dict:
    return {
        'success': True,
        'token_type': 'bearer',
        'access_token': None,
        'refresh_token': None,
    }


def build_unique_username_from_email(email: str) -> str:
    base_username = (email.split('@')[0] or 'user').strip()[:25] or 'user'
    username = base_username
    suffix = 1

    while User.objects.filter(username=username).exists():
        username = f"{base_username[:20]}{suffix}"
        suffix += 1

    return username


@router.post("/register", response=TokenSchema)
def register(request, payload: RegisterSchema):
    """Регистрация нового пользователя"""
    email = normalize_email(payload.email)
    if not email:
        raise ValidationError("Email is required")

    if User.objects.filter(email__iexact=email).exists():
        raise ValidationError("User with this email already exists")

    username_source = (payload.username or email).strip()
    username = build_unique_username_from_email(username_source)

    try:
        validate_password(payload.password, user=User(username=username, email=email))
    except DjangoValidationError as exc:
        raise ValidationError("; ".join(exc.messages))

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                email=email,
                password=payload.password
            )
    except IntegrityError:
        raise ValidationError("User with this email already exists")

    tokens = create_tokens(user)
    response = JsonResponse(_cookie_auth_response())
    set_auth_cookies(response, tokens, request=request)
    return response


@router.post("/login", response=TokenSchema)
def login(request, payload: LoginSchema):
    """Вход пользователя"""
    email = normalize_email(payload.email)
    users = list(User.objects.filter(email__iexact=email).order_by('id')[:2])
    if not users:
        raise AuthenticationError("Invalid credentials")
    if len(users) > 1:
        logger.error("Multiple users found with the same email: %s", email)
        raise AuthenticationError("Invalid credentials")
    user = users[0]

    if not user.check_password(payload.password):
        raise AuthenticationError("Invalid credentials")

    tokens = create_tokens(user)
    response = JsonResponse(_cookie_auth_response())
    set_auth_cookies(response, tokens, request=request)
    return response


@router.post("/refresh", response=TokenSchema)
def refresh_token(request, payload: RefreshTokenSchema):
    """Обновить access token используя refresh token"""
    refresh_token_value = payload.refresh_token or request.COOKIES.get(REFRESH_COOKIE_NAME)
    if not refresh_token_value:
        raise AuthenticationError("Refresh token missing")

    try:
        token_payload = jwt.decode(
            refresh_token_value,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        if token_payload['type'] != 'refresh':
            raise ValidationError("Invalid token type")

        user = User.objects.get(id=token_payload['user_id'])
        tokens = create_tokens(user)
        response = JsonResponse(_cookie_auth_response())
        set_auth_cookies(response, tokens, request=request)
        return response

    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token expired")
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid token")
    except User.DoesNotExist:
        raise AuthenticationError("User not found")


@router.post("/logout", response=AuthMessageSchema)
def logout(request):
    response = JsonResponse({"success": True, "message": "Logged out"})
    clear_auth_cookies(response)
    return response


@router.get("/me", response=UserSchema, auth=auth)
def get_current_user(request):
    """Получить информацию о текущем пользователе"""
    return request.auth
