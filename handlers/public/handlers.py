from telebot.types import Message
from loader import bot

from models import User, FAQ

from states.custom_states import States
from config_data.config import DEFAULT_COMMANDS, BACK, BACK_FAQ, ADMIN_COMMANDS, ADMIN_BUTTONS

from handlers.common.utils import get_or_create_user
from handlers.public.main_menu_handler import show_main_menu
from handlers.public.navigation_programs import handle_menu_selection, handle_back_navigation
from handlers.public.navigation_info import display_faq_menu, display_faq_answer
from handlers.common.admin_only import is_admin

from peewee import DoesNotExist

import logging


logger = logging.getLogger(__name__)


# =======================================================================
# ====================== ОБРАБОТЧИКИ СООБЩЕНИЙ ==========================
# =======================================================================

@bot.message_handler(commands=['start'])
def start(message: Message) -> None:
    """
    Функция отправляет приветственное сообщение
    """
    user = get_or_create_user(message)

    greeting = f"Рад вас снова видеть, {user.first_name}!" if User.select().where(
        User.user_id == user.user_id).count() > 1 else f"Добро пожаловать, {user.first_name}!"

    bot.reply_to(message, greeting)
    bot.send_message(
        message.chat.id,
        'Официальный помощник сайта yogita.ru\n\n'
        'Выберите пункт меню или введите команду /menu'
    )
    show_main_menu(message)


@bot.message_handler(state=States.submenu_selection)
def handle_submenu_selection(message: Message) -> None:
    """
    Обрабатывает выбор в подменю, включая FAQ
    """
    if message.text == BACK:

        handle_back_navigation(message)
        return

    try:
        faq_item = FAQ.get(FAQ.question == message.text)
        display_faq_answer(message, faq_item)
        return
    except DoesNotExist:
        pass

    # Обычная обработка для остальных элементов меню
    handle_menu_selection(message)


@bot.message_handler(commands=['help'])
@bot.message_handler(func=lambda message: message.text == 'Помощь')
def helper(_show_help) -> None:
    """
    Обрабатывает отображение справки
    """


def _show_help(message: Message) -> None:
    """
    Внутренняя функция обработчика: Показывает справку
    """
    help_text = "Доступные команды:\n\n"

    for command, description in DEFAULT_COMMANDS:
        help_text += f"/{command} - {description}\n"

    if is_admin(message.from_user.id):
        help_text += "\nКоманды Администратора:\n"
        for command, description in ADMIN_COMMANDS:
            help_text += f"/{command} - {description}\n"

    bot.send_message(message.chat.id, help_text)


# ========================================================================
# ===================== ВСПОМОГАТЕЛЬНЫЕ ОБРАБОТЧИКИ ======================
# ========================================================================

@bot.message_handler(func=lambda message: message.text == BACK_FAQ)
def back_to_faq_menu(message: Message) -> None:
    """
    Возвращает к меню FAQ
    """
    display_faq_menu(message)
    # handle_menu_selection()

    # ========================================================================
    # =========================== ОБЩИЙ ОБРАБОТЧИК ===========================
    # ========================================================================


@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_all_text(message: Message) -> None:
    """
    Обрабатывает ВСЕ текстовые сообщения
    """
    # Отладка
    logger.info(f"Получено: '{message.text}'")

    # Пропускаем админ-кнопки для администратора, их обработают специальные обработчики
    if is_admin(message.from_user.id) and message.text in ADMIN_BUTTONS:
        return

    # Если это неизвестная команда
    if message.text.startswith('/'):
        bot.send_message(
            message.chat.id,
            "Такой команды нет. Введите /help для списка команд."
        )
    else:
        handle_menu_selection(message)
