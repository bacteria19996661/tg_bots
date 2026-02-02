from telebot.types import Message
from loader import bot

from config_data.config import ADMIN_CHAT_IDS

from functools import wraps

import logging


logger = logging.getLogger(__name__)

# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ИДЕНТИФИКАЦИИ АДМИНИСТРАТОРА ===


def is_admin(user_id: int) -> bool:
    """
    Проверяет, является ли пользователь администратором
    """
    return user_id in ADMIN_CHAT_IDS


def admin_required(func):
    """
    Декоратор для функций, требующих прав администратора.
    """
    @wraps(func)
    def wrapper(message: Message, *args, **kwargs):
        if not is_admin(message.from_user.id):
            logger.warning(f"Отказ в доступе для user_id: {message.from_user.id}")
            bot.send_message(message.chat.id, "Эта функция доступна только администраторам.")
            return None

        return func(message, *args, **kwargs)
    return wrapper
