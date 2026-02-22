"""
Authentication API endpoints - Django Ninja
"""
import logging

from ninja import Router
from django.contrib.auth.models import User
from django.utils import timezone
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
)


router = Router(tags=["Authentication"])
auth = JWTAuth()


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
    if User.objects.filter(email=payload.email).exists():
        raise ValidationError("User with this email already exists")

    # Используем build_unique_username_from_email — гарантирует уникальность
    username = build_unique_username_from_email(payload.username or payload.email)
    user = User.objects.create_user(
        username=username,
        email=payload.email,
        password=payload.password
    )

    # Создаем токены
    return create_tokens(user)


@router.post("/login", response=TokenSchema)
def login(request, payload: LoginSchema):
    """Вход пользователя"""
    # Ищем пользователя по email
    try:
        user = User.objects.get(email=payload.email)
    except User.DoesNotExist:
        raise AuthenticationError("Invalid credentials")

    # Проверяем пароль
    if not user.check_password(payload.password):
        raise AuthenticationError("Invalid credentials")

    # Создаем токены
    return create_tokens(user)


@router.post("/refresh", response=TokenSchema)
def refresh_token(request, payload: RefreshTokenSchema):
    """Обновить access token используя refresh token"""
    try:
        token_payload = jwt.decode(
            payload.refresh_token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        if token_payload['type'] != 'refresh':
            raise ValidationError("Invalid token type")

        user = User.objects.get(id=token_payload['user_id'])
        return create_tokens(user)

    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token expired")
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid token")
    except User.DoesNotExist:
        raise AuthenticationError("User not found")


@router.get("/me", response=UserSchema, auth=auth)
def get_current_user(request):
    """Получить информацию о текущем пользователе"""
    return request.auth
