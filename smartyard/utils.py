"""Модуль функций-утилит и декораторов сервиса"""
import secrets
from functools import wraps
from typing import Callable, Iterable, Union

from flask import abort, request

from smartyard.logic.users import Users
from smartyard.logic.users_bank import UsersBank


def access_verification(endpoint: Callable):
    """Декоратор для проверки аутентификации пользователя"""

    @wraps(endpoint)
    def _wrapper(*args, **kwargs):
        auth_key = request.headers.get("Authorization")
        if not auth_key:
            abort(
                422,
                {
                    "code": 422,
                    "name": "Отсутствует токен авторизации",
                    "message": "Отсутствует токен авторизации",
                },
            )
        user = Users().user_by_uuid(auth_key[7:])
        if not user:
            abort(
                401,
                {"code": 401, "name": "Не авторизован", "message": "Не авторизован"},
            )
        request.environ["USER_PHONE"] = user.userphone
        return endpoint(*args, **kwargs)

    return _wrapper


def json_verification(fields_or_endpoint: Union[Callable, Iterable]):
    """Декоратор для проверки наличия присланных в виде JSON параметров"""
    fields = ()

    def _wrapper(endpoint: Callable):
        @wraps(endpoint)
        def __wrapper(*args, **kwargs):
            request_data = request.get_json()
            if not request_data or any((field not in request_data for field in fields)):
                abort(
                    422,
                    {
                        "code": 422,
                        "name": "Unprocessable Entity",
                        "message": "Необрабатываемый экземпляр",
                    },
                )
            return endpoint(*args, **kwargs)

        return __wrapper

    if callable(fields_or_endpoint):
        return _wrapper(fields_or_endpoint)
    fields = fields_or_endpoint
    return _wrapper


def generate_video_token(user_phone: int, strims: Iterable) -> str:
    """Формирование токена для видео-потоков"""
    token = secrets.token_hex(16)
    UsersBank().update_video_token(user_phone, token, strims)
    return token
