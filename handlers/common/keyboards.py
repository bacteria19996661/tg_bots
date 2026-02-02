from telebot.types import ReplyKeyboardMarkup, KeyboardButton

from config_data.config import MAIN_MENU, BACK

import logging

logger = logging.getLogger(__name__)


# ============= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ СОЗДАНИЯ КЛАВИАТУРЫ =============

def create_keyboard(button_titles: list[str], row_width: int = 2, add_back_button: bool = True,
                    back_button_text: str = None) -> ReplyKeyboardMarkup:
    """
    Создает клавиатуру с кнопками
    """
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=row_width)
    buttons = [KeyboardButton(title) for title in button_titles]

    if add_back_button:
        if back_button_text:
            buttons.append(KeyboardButton(back_button_text))
        else:
            buttons.append(KeyboardButton(BACK if len(button_titles) <= 4 else MAIN_MENU))

    markup.add(*buttons)
    return markup


def create_programs_keyboard(programs, back_button_text=MAIN_MENU):
    """
    Создает клавиатуру для списка программ
    """
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [KeyboardButton(program.program_title) for program in programs]
    buttons.append(KeyboardButton(back_button_text))
    markup.add(*buttons)
    return markup
