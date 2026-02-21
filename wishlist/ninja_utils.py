"""
Django Ninja utilities - exceptions and authentication
"""
from ninja.security import HttpBearer
from ninja.errors import HttpError
from django.contrib.auth.models import User
from django.conf import settings
import jwt


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
class JWTAuth(HttpBearer):
    """
    JWT Bearer token authentication для Django Ninja

    Автоматически валидирует JWT токен и возвращает User объект
    """

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
            # Токен истёк
            return None
        except jwt.InvalidTokenError:
            # Невалидный токен
            return None
        except User.DoesNotExist:
            # Пользователь не существует
            return None
        except Exception:
            # Любая другая ошибка
            return None
