from telebot.types import Message, ReplyKeyboardMarkup
from loader import bot

from models import Menu

from config_data.config import ADMIN_PANEL, MAIN_MENU_ITEMS, CALL_BACK, CANCEL
from handlers.common.admin_only import is_admin

import logging


logger = logging.getLogger(__name__)


@bot.message_handler(commands=['menu'])
def show_main_menu(message: Message) -> None:
    """
    Показывает главное меню (с админ-панелью для администраторов)
    """
    try:
        # Сброс состояния бота
        bot.delete_state(message.from_user.id, message.chat.id)

        logger.info(f"Запрос меню от user_id: {message.from_user.id}")

        text, markup = create_user_menu(message.from_user.id, message.chat.id)

        # Админ-кнопка для администраторов
        if is_admin(message.from_user.id):
            markup.keyboard.insert(0, [ADMIN_PANEL])
            logger.info(f"Добавлена админ-панель для администратора {message.from_user.id}")

        bot.send_message(
            message.chat.id,
            text,
            reply_markup=markup
        )

    except Exception as e:
        logger.error(f"Ошибка при загрузке меню: {e}")
        bot.send_message(message.chat.id, "Ошибка при загрузке меню. Попробуйте позже")


def create_user_menu(user_id: int, chat_id: int) -> tuple[str, ReplyKeyboardMarkup]:
    """
    Создает меню для пользователя
    Возвращает (текст, клавиатура)
    """
    # Получение основных пунктов меню
    main_menu_items = Menu.select().where(
        Menu.menu_id.in_(MAIN_MENU_ITEMS)
    ).order_by(Menu.menu_id)

    button_titles = [item.menu_title for item in main_menu_items]

    # Проверка активного состояния заявки
    current_state = bot.get_state(user_id, chat_id)
    if current_state and current_state.startswith('States:order'):
        button_titles.append(CANCEL)
    else:
        button_titles.append(CALL_BACK)

    from handlers.common.keyboards import create_keyboard

    markup = create_keyboard(button_titles, add_back_button=False)

    return 'Выберите раздел ниже:', markup
