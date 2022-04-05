"""Модуль работы с объектами в базе"""
import uuid as std_uuid
from typing import Union

from smartyard.db.database import create_db_connection
from smartyard.db.temps import Temps
from smartyard.db.users import Users


class Storage:
    """Класс работы с объектами в базе данных"""

    def __init__(self) -> None:
        self.datebase = create_db_connection()

    def save(self, raw_object: Union[Temps, Users]):
        """Сохранение объекта в базе

        Параметры:
        - raw_object - объект Temps или Users
        """
        with self.datebase.session.begin:
            self.datebase.session.add(raw_object)
            self.datebase.session.commit()

    def user_by_uuid(self, _uuid: Union[str, std_uuid.UUID]) -> Users:
        """Поиск номера телефона по uuid пользователя

        Параметры:
        - uuid - идентификатор пользователя
        """
        return self.datebase.session.query(Users).filter_by(uuid=_uuid).first()

    def user_by_phone(self, phone: int) -> Users:
        """Поиск номера телефона по uuid пользователя

        Параметры:
        - phone - номер телефона
        """
        return self.datebase.session.query(Users).filter_by(userphone=phone).first()

    def auth_by_phone_and_code(self, phone: int, code: int) -> Temps:
        """Проверка аутенификации

        Параметры:
        - phone - номер телефона
        - code - код аутентификации из SMS
        """
        return (
            self.datebase.session.query(Temps)
            .filter_by(userphone=phone, smscode=code)
            .first()
        )

    def clear_codes_for_phone(self, phone: int) -> None:
        """Чистка кодов аутентификации по номеру телефона

        Параметры:
        - phone - номер телефона
        """
        self.datebase.session.query(Temps).filter_by(
            userphone=phone
        ).delete()
