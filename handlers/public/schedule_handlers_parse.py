from telebot.types import Message, ReplyKeyboardMarkup, KeyboardButton
from loader import bot

from models import Menu

from states.custom_states import States
from config_data.config import MAIN_MENU, BACK, SCHEDULE_FILE_PATH

from handlers.public.order_handlers import order_init
from handlers.public.main_menu_handler import show_main_menu

import json

import time
from datetime import datetime, timedelta

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
    """Загружает и группирует данные расписания по датам"""
    try:
        schedule_path = SCHEDULE_FILE_PATH

        if not schedule_path.exists():
            logger.error(f"Файл расписания не найден: {schedule_path}")
            return None

        with open(schedule_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            activities_count = len(data.get('activities', []))
            logger.info(f"Успешно загружено расписание: {activities_count} занятий")

            # Группировка занятий по датам
            schedule_by_date = {}
            for activity in data['activities']:
                date_str = activity.get('date')
                if not date_str:
                    continue

                if date_str not in schedule_by_date:
                    schedule_by_date[date_str] = []

                schedule_by_date[date_str].append(activity)

            # Сортировка занятий внутри каждой даты по времени начала
            for date in schedule_by_date:
                schedule_by_date[date].sort(
                    key=lambda x: x.get('start_time', '00:00')
                )

            logger.info(f"Создано {len(schedule_by_date)} уникальных дат с занятиями")
            return schedule_by_date

    except Exception as e:
        logger.error(f"Ошибка загрузки расписания: {e}")
        return None


def get_week_dates():
    """Возвращает даты текущей и следующей недели, начиная с понедельника"""
    today = datetime.now().date()

    # Находит понедельник текущей недели
    # Понедельник = 0, воскресенье = 6
    current_monday = today - timedelta(days=today.weekday())

    # Даты текущей недели (7 дней с понедельника)
    current_week = [current_monday + timedelta(days=i) for i in range(7)]

    # Даты следующей недели
    next_monday = current_monday + timedelta(days=7)
    next_week = [next_monday + timedelta(days=i) for i in range(7)]

    return {
        1: current_week,  # Текущая неделя
        2: next_week  # Следующая неделя
    }


def show_schedule_week_selection(message: Message):
    """Показывает выбор недели для расписания"""
    try:
        # Загружаем данные
        schedule_data = load_grouped_schedule_data()
        if not schedule_data:
            logger.error("Не удалось загрузить данные расписания")
            bot.send_message(message.chat.id, "Расписание временно недоступно")
            show_main_menu(message)
            return

        # Даты недель
        week_dates = get_week_dates()

        # Описание недель
        week1_start = week_dates[1][0].strftime('%d.%m')
        week1_end = week_dates[1][-1].strftime('%d.%m')
        week2_start = week_dates[2][0].strftime('%d.%m')
        week2_end = week_dates[2][-1].strftime('%d.%m')

        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            KeyboardButton(f"Неделя 1 ({week1_start} - {week1_end})"),
            KeyboardButton(f"Неделя 2 ({week2_start} - {week2_end})"),
            KeyboardButton(MAIN_MENU)
        )

        bot.send_message(
            message.chat.id,
            f"Расписание занятий\n\n"
            f"Выберите неделю для просмотра расписания:",
            reply_markup=markup
        )

        # Сохраняет данные в состоянии
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['schedule_data'] = schedule_data
            data['week_dates'] = week_dates

        bot.set_state(message.from_user.id, States.schedule_week_selection, message.chat.id)

    except Exception as e:
        logger.error(f"Ошибка при загрузке выбора недели: {e}")
        bot.send_message(message.chat.id, "Ошибка при загрузке расписания")
        show_main_menu(message)


def show_schedule_dates(message: Message, week_num: int):
    """Показывает даты выбранной недели"""
    try:
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            schedule_data = data.get('schedule_data')
            week_dates = data.get('week_dates')

        if not schedule_data or not week_dates:
            bot.send_message(message.chat.id, "Данные расписания устарели")
            show_schedule_week_selection(message)
            return

        # Даты выбранной недели
        selected_week_dates = week_dates.get(week_num, [])

        if not selected_week_dates:
            bot.send_message(message.chat.id, "Неверный выбор недели")
            show_schedule_week_selection(message)
            return

        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        buttons = []

        day_names = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс']

        for i, day_date in enumerate(selected_week_dates):
            date_str = day_date.strftime('%d.%m')
            day_name = day_names[i]
            button_text = f"{date_str} ({day_name})"

            # Проверка занятий на эту дату
            date_key = day_date.strftime('%Y-%m-%d')
            has_activities = date_key in schedule_data

            if has_activities:
                activity_count = len(schedule_data[date_key])
                button_text += f" [{activity_count}]"

            buttons.append(KeyboardButton(button_text))

        for i in range(0, len(buttons), 2):
            if i + 1 < len(buttons):
                markup.add(buttons[i], buttons[i + 1])
            else:
                markup.add(buttons[i])

        markup.add(KeyboardButton(BACK))

        bot.send_message(
            message.chat.id,
            f"Неделя {week_num}\n\n"
            f"Выберите дату для просмотра расписания:\n"
            f"[цифра] - количество занятий в этот день",
            reply_markup=markup
        )

        # Сохранение номера недели в состоянии
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['selected_week'] = week_num

        bot.set_state(message.from_user.id, States.schedule_date_selection, message.chat.id)

    except Exception as e:
        logger.error(f"Ошибка при загрузке дат недели {week_num}: {e}")
        bot.send_message(message.chat.id, "Ошибка при загрузке дат")
        show_schedule_week_selection(message)


def format_schedule_response(activities, target_date_str, day_name):
    """Форматирует ответ с расписанием на день"""
    if not activities:
        return f"{target_date_str} ({day_name})\n\nНа этот день занятий не запланировано."

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
    """Показывает расписание на выбранную дату"""
    try:
        # Извлекает дату из строки вида "24.12 (ср) [3]"
        date_part = selected_date_str.split(' (')[0]
        selected_date = datetime.strptime(date_part + f".{datetime.now().year}", '%d.%m.%Y').date()

        day_names_full = ['понедельник', 'вторник', 'среду', 'четверг', 'пятницу', 'субботу', 'воскресенье']
        day_of_week = selected_date.weekday()
        day_name = day_names_full[day_of_week]

        date_key = selected_date.strftime('%Y-%m-%d')
        formatted_date = selected_date.strftime('%d.%m.%Y')

        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            schedule_data = data.get('schedule_data')

        if not schedule_data:
            bot.send_message(message.chat.id, "Данные расписания устарели")
            show_schedule_week_selection(message)
            return

        # Занятия на выбранную дату
        activities = schedule_data.get(date_key, [])

        response = format_schedule_response(activities, formatted_date, day_name)

        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

        if activities:
            booking_buttons = []
            for activity in activities:
                title = activity.get('title', 'Без названия')
                start_time = activity.get('start_time', '')
                end_time = activity.get('end_time', '')
                time_range = f"{start_time}-{end_time}"

                button_text = f"Запись: {title} {time_range}"
                booking_buttons.append(KeyboardButton(button_text))

            for i in range(0, len(booking_buttons), 2):
                if i + 1 < len(booking_buttons):
                    markup.add(booking_buttons[i], booking_buttons[i + 1])
                else:
                    markup.add(booking_buttons[i])

        markup.add(KeyboardButton(BACK))

        # Сохранение данных для записи
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['selected_date'] = formatted_date
            data['selected_date_obj'] = selected_date
            data['current_activities'] = activities

        # Отправка сообщения
        if len(response) > 4000:
            parts = [response[i:i + 4000] for i in range(0, len(response), 4000)]
            for part in parts[:-1]:
                bot.send_message(message.chat.id, part)
            bot.send_message(message.chat.id, parts[-1], reply_markup=markup)
        else:
            bot.send_message(message.chat.id, response, reply_markup=markup)

        bot.set_state(message.from_user.id, States.schedule_activity_selection, message.chat.id)

    except Exception as e:
        logger.error(f"Ошибка при загрузке расписания на дату: {e}")
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

        # Это кнопка записи?
        if message.text.startswith('Запись:'):
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
                bot.send_message(message.chat.id, "Не удалось найти выбранное занятие")
                show_schedule_week_selection(message)

            return

        # Если команд не распознана, возврат к расписанию
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            selected_week = data.get('selected_week', 1)
        show_schedule_dates(message, selected_week)

    except Exception as e:
        logger.error(f"Ошибка при обработке выбора занятия: {e}")
        bot.send_message(message.chat.id, "Ошибка при обработке выбора")
        show_schedule_week_selection(message)
