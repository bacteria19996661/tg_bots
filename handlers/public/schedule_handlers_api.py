from telebot.types import Message, ReplyKeyboardMarkup, KeyboardButton
from loader import bot

from models import Menu

from states.custom_states import States
from config_data.config import MAIN_MENU, BACK, SCHEDULE_FILE_PATH

from handlers.public.order_handlers import order_init
from handlers.public.main_menu_handler import show_main_menu

import json

import time
from datetime import datetime

import logging


logger = logging.getLogger(__name__)


# =======================================================================
# ================ ОБРАБОТЧИКИ СОСТОЯНИЙ РАСПИСАНИЯ =====================
# =======================================================================

@bot.message_handler(state=States.schedule_week_selection)
def handle_schedule_week_selection(message: Message):
    """
    Обрабатывает выбор недели расписания
    """
    # logger.info(f"Пользователь выбрал: {message.text}\n"
    #             f"Текущее состояние: {bot.get_state(message.from_user.id, message.chat.id)}")

    if message.text == MAIN_MENU:
        # logger.info("Возврат в главное меню")
        show_main_menu(message)
        return

    if "Неделя 1" in message.text:
        # logger.info("Пользователь выбрал неделю 1")
        show_schedule_dates(message, 1)
    elif "Неделя 2" in message.text:
        # logger.info("Пользователь выбрал неделю 2")
        show_schedule_dates(message, 2)
    else:
        # logger.warning(f"Неизвестный выбор недели: {message.text}")
        bot.send_message(message.chat.id, "Пожалуйста, выберите неделю из предложенных вариантов")


@bot.message_handler(state=States.schedule_date_selection)
def handle_schedule_date_selection(message: Message):
    """
    Обрабатывает выбор даты расписания
    """
    if message.text == BACK:
        show_schedule_week_selection(message)
        return

    # Проверка формата даты
    if '.' in message.text and '(' in message.text:
        show_schedule_for_date(message, message.text)
    else:
        bot.send_message(message.chat.id, "Пожалуйста, выберите дату из предложенных вариантов")


@bot.message_handler(state=States.schedule_activity_selection)
def handle_schedule_activity_selection_wrapper(message: Message):
    """
    Обертка для обработки выбора занятия
    """
    handle_schedule_activity_selection(message)


# ================ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ РАСПИСАНИЯ ==================

def is_schedule_file_fresh(file_path, max_age_hours=24):
    """
    Проверяет дату последнего обновления файла с расписанием
    """
    try:
        if not file_path.exists():
            return False

        file_mtime = file_path.stat().st_mtime
        file_age_hours = (time.time() - file_mtime) / 3600

        return file_age_hours <= max_age_hours

    except Exception as e:
        logger.error(f"Ошибка при проверке файла расписания: {e}")
        return False


def get_schedule_handler(message: Message, menu_item: Menu):
    """
    Определяет какой обработчик использовать для расписания
    """
    if is_schedule_file_fresh(SCHEDULE_FILE_PATH):
        # logger.info("Файл расписания актуален. Используется интерактивное расписание")
        return lambda: show_schedule_week_selection(message)
    else:
        from handlers.public.navigation_info import display_info_menu_item

        logger.warning("Файл расписания устарел или отсутствует! Используется статическое описание раздела")
        return lambda: display_info_menu_item(message, menu_item)


def load_grouped_schedule_data():
    """
    Сортировка
    :return:
    """
    try:
        with open(SCHEDULE_FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)

        grouped = {1: {}, 2: {}}

        for activity in data.get("activities", []):
            week = activity.get("week")
            date = activity.get("date")

            if week not in grouped or not date:
                continue

            grouped.setdefault(week, {})
            grouped[week].setdefault(date, [])
            grouped[week][date].append(activity)

        # сортировка по времени
        for week in grouped:
            for date in grouped[week]:
                grouped[week][date].sort(
                    key=lambda x: x.get("start_time", "00:00")
                )

        return grouped

    except Exception as e:
        logger.error(f"Ошибка загрузки расписания: {e}")
        return None


def show_schedule_week_selection(message: Message):
    """
    Показывает выбор недели для расписания.
    """
    try:
        schedule_data = load_grouped_schedule_data()
        if not schedule_data:
            bot.send_message(message.chat.id, "Расписание временно недоступно")
            show_main_menu(message)
            return

        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            KeyboardButton("Неделя 1"),
            KeyboardButton("Неделя 2"),
            KeyboardButton(MAIN_MENU)
        )

        bot.send_message(
            message.chat.id,
            "Расписание занятий\n\nВыберите неделю:",
            reply_markup=markup
        )

        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['schedule_data'] = schedule_data

        bot.set_state(message.from_user.id, States.schedule_week_selection, message.chat.id)

    except Exception as e:
        logger.error(f"Ошибка выбора недели: {e}")
        bot.send_message(message.chat.id, "Ошибка при загрузке расписания")
        show_main_menu(message)


def show_schedule_dates(message: Message, week_num: int):
    try:
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            schedule_data = data.get('schedule_data')

        week_data = schedule_data.get(week_num)
        if not week_data:
            bot.send_message(message.chat.id, "На эту неделю занятий нет")
            show_schedule_week_selection(message)
            return

        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        buttons = []

        day_names = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс']

        # Сортировка дат
        for date_str in sorted(week_data.keys()):
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            day_name = day_names[date_obj.weekday()]
            activity_count = len(week_data[date_str])

            button_text = f"{date_obj.strftime('%d.%m')} ({day_name}) [{activity_count}]"
            buttons.append(KeyboardButton(button_text))

        for i in range(0, len(buttons), 2):
            markup.add(*buttons[i:i + 2])

        markup.add(KeyboardButton(BACK))

        bot.send_message(
            message.chat.id,
            f"Неделя {week_num}\n\nВыберите дату:",
            reply_markup=markup
        )

        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['selected_week'] = week_num

        bot.set_state(message.from_user.id, States.schedule_date_selection, message.chat.id)

    except Exception as e:
        logger.error(f"Ошибка отображения дат недели: {e}")
        bot.send_message(message.chat.id, "Ошибка при загрузке дат")
        show_schedule_week_selection(message)


def format_schedule_response(activities, target_date_str, day_name):
    """Форматирует ответ с расписанием на день"""
    if not activities:
        return f"{target_date_str} ({day_name})\n\nВ этот день занятий нет."

    response = f"Расписание на {target_date_str} ({day_name})\n\n"

    for i, activity in enumerate(activities, 1):
        title = activity.get('title', 'Без названия')
        start_time = activity.get('start_time', '')
        end_time = activity.get('end_time', '')
        time_range = f"{start_time}-{end_time}" if start_time and end_time else ""
        trainers = ', '.join(activity.get('trainers', [])) or 'тренер не указан'

        response += f"Занятие {i}:\n"
        response += f"Время: {time_range}\n"
        response += f"Программа: {title}\n"
        response += f"Тренер: {trainers}\n"
        response += "―" * 20 + "\n\n"

    return response


def show_schedule_for_date(message: Message, selected_date_str: str):
    """
    Показывает расписание на выбранную дату.
    """
    try:
        date_part = selected_date_str.split(' (')[0]
        selected_date = datetime.strptime(
            date_part + f".{datetime.now().year}", "%d.%m.%Y"
        ).date()

        date_key = selected_date.strftime('%Y-%m-%d')

        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            schedule_data = data.get('schedule_data')
            selected_week = data.get('selected_week')

        week_data = schedule_data.get(selected_week, {})
        activities = week_data.get(date_key, [])

        day_names_full = [
            'понедельник', 'вторник', 'среду',
            'четверг', 'пятницу', 'субботу', 'воскресенье'
        ]
        day_name = day_names_full[selected_date.weekday()]
        formatted_date = selected_date.strftime('%d.%m.%Y')

        response = format_schedule_response(activities, formatted_date, day_name)

        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

        if activities:
            buttons = []
            for a in activities:
                buttons.append(
                    KeyboardButton(
                        f"Запись: {a['title']} {a['start_time']}-{a['end_time']}"
                    )
                )
            for i in range(0, len(buttons), 2):
                markup.add(*buttons[i:i + 2])

        markup.add(KeyboardButton(BACK))

        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['selected_date'] = formatted_date
            data['current_activities'] = activities

        bot.send_message(message.chat.id, response, reply_markup=markup)
        bot.set_state(message.from_user.id, States.schedule_activity_selection, message.chat.id)

    except Exception as e:
        logger.error(f"Ошибка отображения расписания: {e}")
        bot.send_message(message.chat.id, "Ошибка при загрузке расписания")
        show_schedule_week_selection(message)


def handle_schedule_activity_selection(message: Message):
    """Обрабатывает выбор занятия для записи"""
    try:
        if message.text == BACK:
            # Возврат к выбору даты
            with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
                week_num = data.get('selected_week', 1)
            show_schedule_dates(message, week_num)
            return

        if message.text.startswith('Запись:'):
            # Извлечение названия занятия и времени
            activity_text = message.text.replace('Запись:', '').strip()

            with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
                date_str = data.get('selected_date', '')
                activities = data.get('current_activities', [])

            # Поиск выбранного занятия
            selected_activity = None
            for activity in activities:
                title = activity.get('title', '')
                start_time = activity.get('start_time', '')
                end_time = activity.get('end_time', '')
                time_range = f"{start_time}-{end_time}"

                if f"{title} {time_range}" in activity_text:
                    selected_activity = activity
                    break

            if selected_activity and date_str:
                # Название программы для записи
                program_title = f"{selected_activity.get('title')} ({date_str})"
                order_init(message, program_title)
            else:
                bot.send_message(message.chat.id, "Выбранное занятие не найдено")
                show_schedule_week_selection(message)

            return

        # Если команда не распознана, возврат к расписанию
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            selected_week = data.get('selected_week', 1)
        show_schedule_dates(message, selected_week)

    except Exception as e:
        logger.error(f"Ошибка при обработке выбора занятия: {e}")
        bot.send_message(message.chat.id, "Ошибка при обработке выбора")
        show_schedule_week_selection(message)
