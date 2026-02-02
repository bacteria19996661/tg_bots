from telebot.types import Message
from loader import bot

from config_data.config import ADMIN_PANEL, ADMIN_BUTTONS

from handlers.common.admin_only import admin_required
from handlers.common.keyboards import create_keyboard

import logging


logger = logging.getLogger(__name__)


# =======================================================================
# ========================= МЕНЮ АДМИНИСТРАТОРА =========================
# =======================================================================

@bot.message_handler(commands=['admin_panel'])
@bot.message_handler(func=lambda msg: msg.text == ADMIN_PANEL)
@admin_required
def handle_admin_panel(message: Message) -> None:
    """
    Показывает Панель Администратора.
    Обрабатывает:
      - Команду /admin_panel
      - Кнопку ADMIN_PANEL в меню
    """
    show_admin_panel(message)
    logger.info(f"Отображена панель администратора для пользователя {message.from_user.id}")


def show_admin_panel(message: Message) -> None:
    """
    Показывает Панель Администратора (команда /admin_panel - только для Админов)
    """
    markup = create_keyboard(ADMIN_BUTTONS, add_back_button=False, row_width=2)

    bot.send_message(
        message.chat.id,
        f"{ADMIN_PANEL}\n\nВыберите действие:",
        parse_mode='Markdown',
        reply_markup=markup
    )
    logger.info(f"Отображена панель администратора для пользователя {message.from_user.id}")
