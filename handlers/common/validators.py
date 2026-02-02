from telebot.types import Message
from loader import bot

from config_data.config import CANCEL_COMMANDS

from handlers.admin.news_handlers import handle_cancel

import re

import logging


logger = logging.getLogger(__name__)


# ============= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ПРОВЕРКИ ВВОДА ДАННЫХ =============

def validate_phone(phone):
    """
    Валидация номера телефона
    """
    e_num_text = ("ВЫ НЕ ЗАВЕРШИЛИ ПРОЦЕСС ЗАЯВКИ или ввели некорректный номер.\n"
                  "Введите номер в формате +7900 ... или 8900... от 10 цифр.\n"
                  "ЕСЛИ ПЕРЕДУМАЛИ, выберите команду /cancel или напишите «ОТМЕНА»")

    # Проверка на допустимые символы
    if not re.match(r'^[\d\s()+.-]+$', phone):
        return False, e_num_text

    # Убирает все нецифровые символы для проверки длины
    digits_only = re.sub(r'\D', '', phone)

    # Проверка длины и начала номера
    if len(digits_only) < 10 or len(digits_only) > 11 or not digits_only.startswith(('7', '8')):
        return False, e_num_text

    return True, phone


def validate_order_input(message: Message, validation_func: callable = None) -> bool:
    """
    Проверяет ввод в процессе заявки
    """
    if message.text.lower() in CANCEL_COMMANDS:
        handle_cancel(message)
        return False

    if validation_func:
        is_valid, result = validation_func(message.text.strip())
        if not is_valid:
            bot.send_message(message.chat.id, result)
            return False

    return True
