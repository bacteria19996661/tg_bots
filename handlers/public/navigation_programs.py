from telebot.types import Message, ReplyKeyboardMarkup, KeyboardButton
from loader import bot

from models import (Menu, Programs, PriceDetail)

from states.custom_states import States
from config_data.config import (MENU_STRUCTURE, MAIN_MENU, MAIN_MENU_ITEMS, BACK, BACK_FAQ, CALL_BACK,
                                ADMIN_PANEL, ADMIN_BUTTONS, USER_MENU)


from handlers.admin.handlers import handle_admin_panel
from handlers.public.order_handlers import order_init
from handlers.public.main_menu_handler import show_main_menu
from handlers.public.navigation_info import display_faq_menu, show_information_menu, display_info_content
from handlers.common.admin_only import is_admin
from handlers.common.keyboards import create_keyboard, create_programs_keyboard

from peewee import DoesNotExist

from typing import Dict, Any

import logging


logger = logging.getLogger(__name__)


# =======================================================================
# ====================== ОБРАЮОТЧИКИ  НАВИГАЦИИ =========================
# =======================================================================

@bot.message_handler(func=lambda msg: msg.text == USER_MENU)
def handle_user_menu(message: Message) -> None:
    """
    Обрабатывает кнопку USER_MENU из админ-панели (доступно всем)
    """
    show_main_menu(message)
    if is_admin(message.from_user.id):
        logger.info(f"Администратор {message.from_user.id} вернулся в главное меню")
    else:
        logger.info(f"Пользователь {message.from_user.id} вернулся в главное меню")


# =======================================================================
# ================ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ НАВИГАЦИИ ====================
# =======================================================================

def navigate_to_menu(message: Message, menu_key: str = None, menu_id: int = None, menu_title: str = None) -> None:
    """
    Универсальная функция навигации по меню
    """
    try:
        if menu_key:
            target_menu_id = MENU_STRUCTURE[menu_key]
            menu_item = Menu.get(Menu.menu_id == target_menu_id)
        elif menu_id:
            menu_item = Menu.get(Menu.menu_id == menu_id)
        elif menu_title:
            menu_item = Menu.get(Menu.menu_title == menu_title)
        else:
            show_main_menu(message)
            return

        handle_menu_navigation_programs(message, menu_item)

    except DoesNotExist:
        logger.error(f"Меню не найдено: key={menu_key}, id={menu_id}, title={menu_title}")
        bot.send_message(message.chat.id, "Раздел временно недоступен")
        show_main_menu(message)
    except Exception as e:
        logger.error(f"Ошибка навигации: {e}")
        bot.send_message(message.chat.id, "Ошибка при загрузке раздела")
        show_main_menu(message)

# =======================================================================
# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ НАВИГАЦИИ ПО ПРОГРАММАМ ============
# =======================================================================


def handle_menu_selection(message: Message) -> None:
    """
    Обрабатывает выбор пользователя из меню с учетом многоуровневой навигации
    """
    user_choice = message.text
    logger.info(f"handle_menu_selection: '{user_choice}' от {message.from_user.id}")

    try:
        # ================== СПЕЦИАЛЬНЫЕ КНОПКИ ==================
        special_buttons = {
            ADMIN_PANEL: lambda: handle_admin_panel(message),
            CALL_BACK: lambda: order_init(message),
            MAIN_MENU: lambda: show_main_menu(message),
            BACK: lambda: handle_back_navigation(message),
            BACK_FAQ: lambda: display_faq_menu(message),
        }

        if user_choice in special_buttons:
            special_buttons[user_choice]()
            return

        # ================== АДМИН-КНОПКИ ==================
        if is_admin(message.from_user.id) and user_choice in ADMIN_BUTTONS:
            logger.info(f"Админ-кнопка '{user_choice}' будет обработана отдельно")
            return

        # ================== ЗАПИСЬ НА ПРОГРАММУ ==================
        if user_choice.startswith('Записаться на «'):
            program_title = user_choice.replace('Записаться на «', '').replace('»', '')
            order_init(message, program_title)
            return

        # ================== ПОИСК ПРОГРАММЫ ИЛИ МЕНЮ ==================
        result = find_program_or_menu(user_choice)

        match result['type']:
            case 'menu':
                handle_menu_navigation_programs(message, result['item'])

            case 'program':
                show_program_details(message, result['item'].program_title)

            case 'partial_menu':
                handle_menu_navigation_programs(message, result['item'])

            case 'partial_program':
                show_program_details(message, result['item'].program_title)

            case _:
                bot.send_message(
                    message.chat.id,
                    "Пожалуйста, выберите пункт из меню ниже:"
                )
                show_main_menu(message)

    except Exception as e:
        logger.error(f"Ошибка при обработке выбора меню '{user_choice}': {e}", exc_info=True)
        bot.send_message(message.chat.id, "Ошибка при обработке запроса. Попробуйте позже.")
        show_main_menu(message)


def find_program_or_menu(user_choice: str) -> Dict[str, Any]:
    from peewee import DoesNotExist

    # 1. Точное совпадение МЕНЮ
    try:
        menu_item = Menu.get(Menu.menu_title == user_choice)
        return {'type': 'menu', 'item': menu_item}
    except DoesNotExist:
        pass

    # 2. Точное совпадение ПРОГРАММЫ
    try:
        program = Programs.get(Programs.program_title == user_choice)
        return {'type': 'program', 'item': program}
    except DoesNotExist:
        pass

    # 3. Частичное совпадение МЕНЮ
    menu_items = Menu.select().where(Menu.menu_title.contains(user_choice))
    if menu_items.count() == 1:
        return {'type': 'partial_menu', 'item': menu_items[0]}

    # 4. Частичное совпадение ПРОГРАММ
    programs = Programs.select().where(Programs.program_title.contains(user_choice))
    if programs.count() == 1:
        return {'type': 'partial_program', 'item': programs[0]}

    # 5. Ничего не найдено
    return {'type': 'not_found', 'item': None}


def handle_no_programs_found(message: Message, menu_item: Menu) -> None:
    """
    ОСОБЫЙ СЛУЧАЙ! Универсальная обработка случая, когда программ не найдено.
    Показывает описание раздела и кнопку для общей записи.
    """
    try:
        response = f"{menu_item.menu_title}"
        if menu_item.menu_description:
            response += f"\n\n{menu_item.menu_description}"

        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            KeyboardButton(f'Записаться на «{menu_item.menu_title}»'),
            KeyboardButton(MAIN_MENU)
        )

        bot.send_message(message.chat.id, response, reply_markup=markup)

        # Сохраняет выбранную программу для формы записи
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['selected_program'] = menu_item.menu_title

        bot.set_state(message.from_user.id, States.program_selection, message.chat.id)

    except Exception as e:
        logger.error(f"Ошибка при обработке отсутствия программ: {e}")
        bot.send_message(message.chat.id, "Ошибка при загрузке информации")


def show_general_programs_menu(message: Message) -> None:
    """
    Показывает подменю для 'Общие программы' с форматами занятий
    """
    try:
        # Описание раздела
        menu_item = Menu.get(Menu.menu_id == MENU_STRUCTURE['general'])
        response = f"{menu_item.menu_title}\n\n{menu_item.menu_description}"

        # Форматы занятий
        format_items = Menu.select().where(
            Menu.menu_id.in_([4, 5, 20])  # Персональные, Групповые, ТОП-Мастер
        ).order_by(Menu.menu_id)

        button_titles = [item.menu_title for item in format_items]
        markup = create_keyboard(button_titles, add_back_button=True, back_button_text=MAIN_MENU)

        # Отправляет описание, потом меню
        bot.send_message(message.chat.id, response)
        bot.send_message(
            message.chat.id,
            'Выберите формат занятий:',
            reply_markup=markup
        )

        bot.set_state(message.from_user.id, States.submenu_selection, message.chat.id)

    except Exception as e:
        logger.error(f"Ошибка при загрузке общих программ: {e}")
        bot.send_message(message.chat.id, "Ошибка при загрузке информации о программах")


def show_program_details(message: Message, program_title: str) -> None:
    """
    ОСОБЫЙ СЛУЧАЙ! Показывает описание программы и кнопку записи
    """
    try:
        # program = Programs.get(Programs.program_title == program_title)

        program = Programs.get_or_none(Programs.program_title == program_title)

        if not program:
            logger.warning(f"Попытка открыть программу, которой нет: {program_title}")
            bot.send_message(message.chat.id, "Эта программа временно недоступна")
            show_main_menu(message)
            return

        # Формирует ответ
        response = f"{program.program_title}\n\n{program.program_description}"

        # Длительность
        if program.program_duration:
            response += f"\n\nДлительность: {program.program_duration}"

        # Стоимость
        prices = get_program_prices(program)

        if prices:
            response += "\n\nСтоимость:"
            for p in prices:
                response += f"\n• {p}"

        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            KeyboardButton(f'Записаться на «{program.program_title}»'),
            KeyboardButton(BACK)
        )

        bot.send_message(message.chat.id, response, reply_markup=markup)

        # Сохраняет выбранную программу в состоянии
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['selected_program'] = program.program_title

        bot.set_state(message.from_user.id, States.program_selection, message.chat.id)

    except DoesNotExist:
        logger.error(f"Программа не найдена: {program_title}")
        bot.send_message(message.chat.id, "Программа не найдена")
        show_main_menu(message)
    except Exception as e:
        logger.error(f"Ошибка при загрузке программы {program_title}: {e}")
        bot.send_message(message.chat.id, "Ошибка при загрузке программы")


def get_program_prices(program: Programs) -> list[str]:
    """
    Возвращает список строк с ценами программы
    """
    if not program.price_detail_ids:
        return []

    try:
        ids = [
            int(pid.strip())
            for pid in program.price_detail_ids.split(',')
            if pid.strip().isdigit()
        ]
    except Exception:
        return []

    details = PriceDetail.select().where(
        PriceDetail.price_detail_id.in_(ids)
    )

    prices = []
    for d in details:
        line = f"{d.price_detail_title}: {d.price_detail_price}"
        if d.price_detail_duration:
            line += f" ({d.price_detail_duration})"
        prices.append(line)

    return prices


def show_programs_by_type(message: Message, menu_id: int, choice_text: str = 'Выберите программу:') -> None:
    """
    Процедура поиска и отображения программ по типу
    """
    try:
        menu_item = Menu.get(Menu.menu_id == menu_id)
        response = f"{menu_item.menu_title}"
        if menu_item.menu_description:
            response += f"\n\n{menu_item.menu_description}"

        programs = Programs.select().where(Programs.menu == menu_id)

        # Логика для групповых программ по длительности
        if menu_id == 5:
            with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
                duration_filter = data.get('duration_filter')
                if duration_filter == '60min':
                    programs = [p for p in programs if p.program_duration == '60 мин']
                    choice_text = 'Выберите программу (60 минут):'
                elif duration_filter == '90_120min':
                    programs = [p for p in programs if p.program_duration in ['90 мин', '120 мин']]
                    choice_text = 'Выберите программу (90-120 минут):'

        markup = create_programs_keyboard(programs, BACK)

        bot.send_message(message.chat.id, response)
        bot.send_message(message.chat.id, choice_text, reply_markup=markup)
        bot.set_state(message.from_user.id, States.program_selection, message.chat.id)

    except Exception as e:
        logger.error(f"Ошибка при загрузке программ menu_id {menu_id}: {e}")
        bot.send_message(message.chat.id, "Ошибка при загрузке программ")


def show_group_programs_format(message: Message) -> None:
    """
    Показывает подменю для групповых занятий по длительности
    """
    try:
        menu_item = Menu.get(Menu.menu_id == 5)
        response = f"{menu_item.menu_title}\n\n{menu_item.menu_description}"

        duration_items = Menu.select().where(Menu.menu_id.in_([21, 22]))

        button_titles = [item.menu_title for item in duration_items]
        markup = create_keyboard(button_titles, add_back_button=True, back_button_text=BACK)

        bot.send_message(message.chat.id, response)
        bot.send_message(message.chat.id, 'Выберите длительность занятий:', reply_markup=markup)
        bot.set_state(message.from_user.id, States.submenu_selection, message.chat.id)

    except Exception as e:
        logger.error(f"Ошибка при загрузке форматов групповых занятий: {e}")
        bot.send_message(message.chat.id, "Ошибка при загрузке форматов занятий")


def show_group_programs_by_duration(message: Message, menu_id: int) -> None:
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['duration_filter'] = '60min' if menu_id == 21 else '90_120min'
    show_programs_by_type(message, 5)


def show_programs_by_menu_id(message: Message, menu_key: str, target_menu_id: int) -> None:
    """
    Процедура показа программ по menu_id
    """
    try:
        menu_item = Menu.get(Menu.menu_id == MENU_STRUCTURE[menu_key])

        # Поиск программы по мульти-идентификаторам (target_menu_id)
        found_programs = Programs.select().where(
            (Programs.menu == target_menu_id) |
            (Programs.multiple_menu_ids.contains(str(target_menu_id)))
        )

        # Если программ не найдено
        if len(found_programs) == 0:
            handle_no_programs_found(message, menu_item)
            return

        # Показывает список программ, если они найдены
        response = f"{menu_item.menu_title}"
        if menu_item.menu_description:
            response += f"\n\n{menu_item.menu_description}"

        markup = create_programs_keyboard(found_programs, MAIN_MENU)

        bot.send_message(message.chat.id, response)
        bot.send_message(
            message.chat.id,
            'Выберите программу:',
            reply_markup=markup
        )

        bot.set_state(message.from_user.id, States.program_selection, message.chat.id)

    except Exception as e:
        logger.error(f"Ошибка при загрузке программ для {menu_key}: {e}")
        bot.send_message(message.chat.id, "Ошибка при загрузке программ")


def show_spare_menu(message: Message, menu_item: Menu) -> None:
    """
    Показывает страховочное меню для пунктов без обработчиков
    """
    try:
        handle_no_programs_found(message, menu_item)
    except Exception as e:
        logger.error(f"Ошибка при загрузке универсального меню: {e}")
        bot.send_message(message.chat.id, "Ошибка при загрузке информации")


def handle_menu_navigation_programs(message: Message, menu_item: Menu) -> None:
    """
    Обрабатывает навигацию по меню
    """
    menu_id = menu_item.menu_id

    # logger.info(f"handle_menu_navigation_programs: menu_id={menu_id}, menu_title='{menu_item.menu_title}'")
    # logger.info(f"MAIN_MENU_ITEMS: {MAIN_MENU_ITEMS}")
    # logger.info(f"MENU_STRUCTURE: {MENU_STRUCTURE}")

    # Основное меню
    if menu_id in MAIN_MENU_ITEMS:
        if menu_id == MENU_STRUCTURE['general']:  # Общие программы
            show_general_programs_menu(message)
        elif menu_id == MENU_STRUCTURE['pregnancy']:  # Для беременных
            show_programs_by_menu_id(message, 'pregnancy', 15)
        elif menu_id == MENU_STRUCTURE['weight']:  # Коррекция веса
            show_programs_by_menu_id(message, 'weight', 16)
        elif menu_id == MENU_STRUCTURE['kids']:  # Для детей
            show_programs_by_menu_id(message, 'kids', 17)
        elif menu_id == MENU_STRUCTURE['rehabilitation']:  # Реабилитация
            show_programs_by_menu_id(message, 'rehabilitation', 18)
        elif menu_id == MENU_STRUCTURE['all_company']:  # Контакты и расписание
            show_information_menu(message)
        elif menu_id == MENU_STRUCTURE['schedule']:  # Расписание
            # show_schedule_week_selection(message)    # если без альтернативного показа
            display_info_content(message, menu_item)
        else:
            show_spare_menu(message, menu_item)

    # Подменю форматов занятий
    elif menu_id in [4, 5, 20]:  # Персональные, Групповые, ТОП-Мастер
        if menu_id == 4:  # Персональные
            show_programs_by_type(message, 4)  # было show_personal_programs(message)
        elif menu_id == 5:  # Групповые
            show_group_programs_format(message)
        elif menu_id == 20:  # ТОП-Мастер
            show_programs_by_type(message, 20, 'Выберите программу с ТОП-Мастером:')
            # было show_top_master_programs(message)

    # Подменю групповых занятий по длительности
    elif menu_id in [21, 22]:  # 60 минут, 90-120 минут
        show_group_programs_by_duration(message, menu_id)

    # Информационные разделы (из Контакты и расписание)
    elif menu_id in [1, 2, 3, 6, 7, 8, 9, 10, 11, 12, 13, 23]:
        display_info_content(message, menu_item)

    else:
        # Универсальный обработчик для остальных пунктов
        show_spare_menu(message, menu_item)


def handle_back_navigation(message: Message) -> None:
    """
    Обрабатывает навигацию BACK
    """
    try:
        current_state = bot.get_state(message.from_user.id, message.chat.id)

        if current_state == States.program_selection:
            # Возврат из программы в общие программы
            show_general_programs_menu(message)
        elif current_state == States.submenu_selection:
            # Возврат из подменю в главное меню
            show_general_programs_menu(message)
            # show_main_menu(message)
        else:
            # По умолчанию в главное меню
            show_main_menu(message)

    except Exception as e:
        logger.error(f"Ошибка при обработке навигации BACK: {e}")
        show_main_menu(message)
