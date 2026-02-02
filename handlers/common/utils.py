from telebot.types import Message, ReplyKeyboardMarkup, KeyboardButton
from loader import bot

from models import User, Date

from states.custom_states import States
from config_data.config import CANCEL, SKIP

from peewee import DoesNotExist

from datetime import datetime

import logging

logger = logging.getLogger(__name__)


# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С БАЗОЙ ДАННЫХ И СОСТОЯНИЯМИ ===

def get_or_create_user(message: Message) -> User:
    """
    Создает или обновляет пользователя в базе данных
    """
    try:
        user_id = message.from_user.id
        username = message.from_user.username or ""
        first_name = message.from_user.first_name or ""
        last_name = message.from_user.last_name or ""
    except AttributeError as e:
        logger.error(f"Ошибка получения данных из message: {e}")
        # Если нет необходимых атрибутов, возвращаем None или вызываем исключение
        raise ValueError("Некорректный объект message")

    try:
        # Поиск пользователя
        user = User.get(User.user_id == user_id)

        # Обновление существующего пользователя
        if user.username != username or user.first_name != first_name or user.last_name != last_name:
            user.username = username
            user.first_name = first_name
            user.last_name = last_name
            user.save()

        # Запись повторного визита
        Date.create(
            user=user,
            title="Повторный визит",
            description="Пользователь снова запустил бота",
            due_date=datetime.now().replace(microsecond=0)
        )
        logger.info(f"Перезапуск бота пользователем {user_id} ({first_name})")

        # Проверка наличия состояния после создания/обновления пользователя
        if not bot.current_states.data.get(message.from_user.id):
            bot.current_states.set_state(message.from_user.id, message.chat.id, None)

        return user

    except DoesNotExist:
        # Создается новый пользователь
        user = User.create(
            user_id=user_id,
            username=username or "",
            first_name=first_name or "",
            last_name=last_name or "",
        )
        # Запись времени первого визита
        Date.create(
            user=user,
            title="Первичный визит",
            description="Новый пользователь запустил бота",
            due_date=datetime.now()
        )
        logger.info(f"Запуск бота новым пользователем: {user_id} ({first_name})")
        return user

    except Exception as e:
        logger.error(f"Ошибка в get_or_create_user: {e}")
        try:
            return User.create(
                user_id=user_id,
                username=username or "",
                first_name=first_name or "",
                last_name=last_name or "",
            )
        except Exception as create_error:
            logger.error(f"Не удалось создать пользователя даже в упрощенном режиме: {create_error}")
            raise


def proceed_to_next_state(message: Message, next_state: States, message_text: str,
                          keyboard_buttons: list = None, skip_button: bool = False) -> None:
    """
    Переход к следующему состоянию заявки
    """
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

    # Добавляет основные кнопки
    if keyboard_buttons:
        buttons = [KeyboardButton(button) for button in keyboard_buttons]
        markup.add(*buttons)

    # Строка SKIP + CANCEL
    action_buttons = []
    if skip_button:
        action_buttons.append(KeyboardButton(SKIP))
    action_buttons.append(KeyboardButton(CANCEL))

    markup.add(*action_buttons)

    bot.send_message(message.chat.id, message_text, reply_markup=markup)
    bot.set_state(message.from_user.id, next_state, message.chat.id)
