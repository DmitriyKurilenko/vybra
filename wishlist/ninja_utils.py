"""
Django Ninja utilities - exceptions and authentication
"""
import logging

from ninja.errors import HttpError
from django.contrib.auth.models import User
from django.conf import settings
import jwt

logger = logging.getLogger(__name__)


# Custom Exceptions
class AuthenticationError(HttpError):
    """Ошибка аутентификации"""
    def __init__(self, message: str = "Not authenticated"):
        super().__init__(401, message)


class ValidationError(HttpError):
    """Ошибка валидации данных"""
    def __init__(self, message: str):
        super().__init__(400, message)


class NotFoundError(HttpError):
    """Ресурс не найден"""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(404, message)


# JWT Authentication
class JWTAuth:
    """
    JWT Bearer token authentication для Django Ninja

    Автоматически валидирует JWT токен и возвращает User объект
    """

    def __call__(self, request):
        token = None

        auth_header = request.headers.get('Authorization', '')
        if auth_header and auth_header.lower().startswith('bearer '):
            token = auth_header.split(' ', 1)[1].strip()

        if not token:
            token = request.COOKIES.get('vybra_access_token')

        if not token:
            return None

        return self.authenticate(request, token)

    def authenticate(self, request, token: str):
        """
        Валидирует JWT токен и возвращает пользователя

        Args:
            request: Django request object
            token: JWT токен из Authorization header

        Returns:
            User объект если токен валидный, None если нет
        """
        try:
            # Декодируем токен
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )

            # Проверяем тип токена
            if payload.get('type') != 'access':
                return None

            # Получаем пользователя
            user = User.objects.get(id=payload['user_id'])
            return user

        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
        except User.DoesNotExist:
            return None
        except Exception:
            # Непредвиденная ошибка (напр., отрыв Redis/DB) — логируем, не глотаем молча
            logger.exception('Unexpected error in JWTAuth.authenticate')
            return None
