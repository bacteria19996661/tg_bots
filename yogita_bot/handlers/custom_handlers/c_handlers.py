from telebot.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

from loader import bot
from models import (User, Date, Orders, Menu, Price, PriceDetail, Contacts,
                    Events, Mentors, Retreats, Reviews, Programs, FAQ)

from peewee import DoesNotExist
import re

from states.custom_states import States
from config_data.config import MENU_STRUCTURE, MAIN_MENU_ITEMS, ADMIN_CHAT_ID
from datetime import datetime

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
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name

    try:
        user = User.get(User.user_id == user_id)

        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        user.save()    # Обновляет информацию в DB

        bot.reply_to(message, f"Рад вас снова видеть, {first_name}!")
        logger.info(f"Перезапуск бота пользователем {user_id} ({first_name})")

        # Запись повторного визита
        Date.create(
            user=user,
            title="Повторный визит",
            description="Пользователь снова запустил бота",
            due_date=datetime.now().replace(microsecond=0)
        )

    except DoesNotExist:
        user = User.create(
            user_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
        )
        # Запись времени первого визита
        Date.create(
            user=user,
            title="Первичный визит",
            description="Новый пользователь запустил бота",
            due_date=datetime.now()
        )
        bot.reply_to(message, f"Добро пожаловать, {first_name}!")
        logger.info(f"Запуск бота новым пользователем: {user_id} ({first_name})")

    bot.send_message(
        message.chat.id,
        'Официальный помощник сайта yogita.ru\n\n'
        'Выберите пункт меню или введите команду /menu'
    )

    show_main_menu(message)


# ------------------- ОБРАБОТЧИКИ НАВИГАЦИИ ----------------------
@bot.message_handler(commands=['menu'])
def show_main_menu(message: Message) -> None:
    """
    Показывает главное меню с основными разделами из базы данных
    """
    try:
        # Получение основных пунктов меню из database.db
        main_menu_items = Menu.select().where(
            Menu.menu_id.in_(MAIN_MENU_ITEMS)
        ).order_by(Menu.menu_id)

        button_titles = [item.menu_title for item in main_menu_items]
        button_titles.append('Записаться на занятие')
        markup = create_keyboard(button_titles, add_back_button=False)  # В главном меню нет кнопки "Назад"

        bot.send_message(
            message.chat.id,
            'Выберите интересующий вас раздел ниже:',
            reply_markup=markup
        )

    except Exception as e:
        logger.error(f"Ошибка при загрузке меню: {e}")
        bot.send_message(message.chat.id, "Ошибка при загрузке меню. Попробуйте позже")


@bot.message_handler(state=States.submenu_selection)
def handle_submenu_selection(message: Message) -> None:
    """
    Обрабатывает выбор в подменю (включая FAQ)
    """
    if message.text == 'Назад':
        handle_back_navigation(message)
        return

    try:
        faq_item = FAQ.get(FAQ.question == message.text)
        display_faq_answer(message, faq_item)
        return
    except DoesNotExist:
        pass

    # Обычная обработка для подстраховки
    handle_menu_selection(message)


# -------------------- ОБРАБОТЧИКИ ЗАЯВКИ -----------------------

@bot.message_handler(func=lambda message: message.text == 'Записаться на занятие')
def handle_order_button(message: Message) -> None:
    """
    Обрабатывает нажатие кнопки "Записаться на занятие"
    """
    start_order(message)


@bot.message_handler(commands=['order'])
def start_order(message: Message) -> None:
    """
    Начинает процесс записи на занятие (общая запись)
    """
    try:
        # Проверяем, есть ли пользователь в базе
        user_id = message.from_user.id
        try:
            user = User.get(User.user_id == user_id)
        except DoesNotExist:
            # Если пользователя нет, создаем временную запись
            user = User.create(
                user_id=user_id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name
            )

        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['selected_program'] = 'Программа не выбрана'

        # Запрос номера телефона
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(
            KeyboardButton("Отправить: Я согласн(а) на обработку данных", request_contact=True),
            KeyboardButton("Отмена")
        )

        bot.send_message(
            message.chat.id,
            "ЗАЯВКА на ОБРАТНЫЙ ЗВОНОК\n\n"
            "ВНИМАНИЕ! Введя номер телефона, вы соглашаетесь на обработку персональных данных."
            "\nВведите ваш номер телефона:",
            reply_markup=markup,
            parse_mode='Markdown'
        )

        bot.set_state(message.from_user.id, States.order_phone, message.chat.id)

    except Exception as e:
        logger.error(f"Ошибка при записи (вводился номер телефона): {e}")
        bot.send_message(message.chat.id, "Ошибка. Попробуйте позже")


@bot.message_handler(content_types=['contact'], state=States.order_phone)
def get_phone_contact(message: Message) -> None:
    """
    Обрабатывает отправленный контакт
    """
    try:
        if message.contact:
            phone = message.contact.phone_number
            with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
                data['phone'] = phone

            # Запрос имени
            markup = ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(KeyboardButton("Отмена"))

            bot.send_message(
                message.chat.id,
                "Введите ваше имя:",
                reply_markup=markup
            )

            bot.set_state(message.from_user.id, States.order_name, message.chat.id)
        else:
            bot.send_message(message.chat.id, "Введите номер телефона")

    except Exception as e:
        logger.error(f"Ошибка при получении номера: {e}")
        bot.send_message(message.chat.id, "Ошибка. Попробуйте снова")


@bot.message_handler(state=States.order_phone)
def get_phone_text(message: Message) -> None:
    """
    Обрабатывает номер телефона, введенный текстом
    """
    if message.text == "Отмена":
        cancel_order(message)
        return

    phone = message.text.strip()

    # Валидация номера
    def validate_phone(phone):
        if not re.match(r'^[\d\s()+.-]+$', phone):
            return False, "Номер содержит недопустимые символы. Допустимы: цифры, пробелы, (), +, -, ."

        # Убирает все нецифровые символы для проверки длины
        digits_only = re.sub(r'[^\d]', '', phone)

        if len(digits_only) < 10:
            return False, "Номер должен быть не менее 10 цифр."

        if len(digits_only) >= 11:
            if not digits_only.startswith(('7', '8')):
                return False, "Номер должен начинаться с 7, 8 или +7"

        return True, phone

    is_valid, result = validate_phone(phone)

    if not is_valid:
        bot.send_message(
            message.chat.id,
            f"{result}\n\n"
        )
        return

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['phone'] = phone

    # Запрос имени
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("Отмена"))

    bot.send_message(
        message.chat.id,
        "\nВведите ваше имя:",
        reply_markup=markup
    )

    bot.set_state(message.from_user.id, States.order_name, message.chat.id)


@bot.message_handler(state=States.order_name)
def get_name(message: Message) -> None:
    """
    Обрабатывает ввод имени
    """
    if message.text == "Отмена":
        cancel_order(message)
        return

    name = message.text.strip()

    if len(name) < 2:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректное имя")
        return

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['name'] = name

    # Проверка наличия выбранной программы
    selected_program = data.get('selected_program')

    if selected_program and selected_program != 'Программа не выбрана':
        # Переход к комментарию, если программа определена автоматически
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(KeyboardButton("Пропустить"), KeyboardButton("Отмена"))

        bot.send_message(
            message.chat.id,
            f"Запись на программу: {selected_program}\n\n"
            "Можете добавить комментарий или нажмите 'Пропустить':",
            reply_markup=markup
        )

        bot.set_state(message.from_user.id, States.order_comment, message.chat.id)
    else:
        # Если программа не выбрана (запись из главного меню), тогда выбираем услугу
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            KeyboardButton("Групповое занятие"),
            KeyboardButton("Персональное занятие"),
            KeyboardButton("Занятие у Топ Мастера"),
            KeyboardButton("Мероприятие или Ретрит"),
            KeyboardButton("Другое"),
            KeyboardButton("Отмена")
        )

        bot.send_message(
            message.chat.id,
            "\nВыберите тип занятия:",
            reply_markup=markup
        )

        bot.set_state(message.from_user.id, States.order_service, message.chat.id)


@bot.message_handler(state=States.order_service)
def get_service_type(message: Message) -> None:
    """
    Обрабатывает выбор услуги
    """
    if message.text == "Отмена":
        cancel_order(message)
        return

    service_type = message.text.strip()

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['service_type'] = service_type

    # Запрос комментария
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("Пропустить"), KeyboardButton("Отмена"))

    bot.send_message(
        message.chat.id,
        "Можете добавить комментарий или нажмите 'Пропустить':",
        reply_markup=markup
    )

    bot.set_state(message.from_user.id, States.order_comment, message.chat.id)


@bot.message_handler(state=States.order_comment)
def get_comment_and_save(message: Message) -> None:
    """
    Обрабатывает комментарий и сохраняет заявку с информацией о программе
    """
    if message.text == "Отмена":
        cancel_order(message)
        return

    try:
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            user = User.get(User.user_id == message.from_user.id)
            comment = None if message.text == "Пропустить" else message.text.strip()

            # Получаем выбранную программу (если есть)
            selected_program = data.get('selected_program', 'Программа не выбрана')

            order = Orders.create(
                user=user,
                phone=data['phone'],
                name=data['name'],
                service_type=selected_program,  # Сохраняем название программы
                comment=comment,
                created_date=datetime.now().replace(microsecond=0)
            )

            logger.info(
                f"Создана заявка №{order.order_id} на программу '{selected_program}' от пользователя {user.user_id}")

            forward_order_to_admin(order)  # Пересылка заявки администратору

            # Подтверждение для пользователя
            confirmation_parts = [
                f"Заявка №{order.order_id} отправлена!",
                f"Имя: {data['name']}",
                f"Телефон: {data['phone']}",
                f"Программа: {selected_program}",
            ]

            if comment:
                confirmation_parts.append(f"Комментарий: {comment}")

            confirmation_parts.append("\nМы свяжемся с вами в ближайшее время для подтверждения записи")

            # Отправка подтверждения
            bot.send_message(
                message.chat.id,
                "\n".join(confirmation_parts),
                reply_markup=ReplyKeyboardRemove()
            )

            # Очищаем выбранную программу
            data.pop('selected_program', None)

            # Сброс состояния
            bot.delete_state(message.from_user.id, message.chat.id)
            show_main_menu(message)

    except Exception as e:
        logger.error(f"Ошибка при сохранении заявки в DB: {e}")
        bot.send_message(
            message.chat.id,
            "Произошла ошибка при сохранении заявки. Попробуйте позже.",
            reply_markup=ReplyKeyboardRemove()
        )
        bot.delete_state(message.from_user.id, message.chat.id)


# -------------------- ВСПОМОГАТЕЛЬНЫЕ ОБРАБОТЧИКИ -----------------------

@bot.message_handler(func=lambda message: message.text == 'Назад к вопросам')
def back_to_faq_menu(message: Message) -> None:
    """
    Возвращает к меню FAQ
    """
    display_faq_menu(message)


@bot.message_handler(commands=['help'])
def help_command(message: Message) -> None:
    """
    Показывает справку по командам
    """
    help_text = """
Доступные команды:

/start - Запустить бота
/menu - Открыть меню ссылок 
/order - Записаться

    """
    bot.send_message(message.chat.id, help_text)


@bot.message_handler(func=lambda message: message.text == 'Помощь')
def show_help(message: Message) -> None:
    """
    Показывает справку
    """
    help_command(message)


def handle_menu_selection(message: Message) -> None:
    """
    Обрабатывает выбор пользователя из меню с учетом многоуровневой навигации
    """
    user_choice = message.text

    try:
        # Проверяем специальные кнопки
        if user_choice == 'Записаться на занятие':
            start_order(message)
            return

        elif user_choice == 'Назад в меню':
            show_main_menu(message)
            return

        elif user_choice == 'Назад':
            handle_back_navigation(message)
            return

        elif user_choice == 'Назад к вопросам':
            display_faq_menu(message)
            return

        # Проверяем, является ли выбор записью на конкретную программу
        if user_choice.startswith('Записаться на "'):
            program_title = user_choice.replace('Записаться на "', '').replace('"', '')
            start_program_order(message, program_title)
            return

        # Проверяем в программах
        try:
            program = Programs.get(Programs.program_title == user_choice)
            show_program_details(message, program.program_title)
            return

        except DoesNotExist:
            pass

        # Проверяем в основном меню
        try:
            menu_item = Menu.get(Menu.menu_title == user_choice)
            handle_menu_navigation(message, menu_item)
            return

        except DoesNotExist:
            pass

        # Если не нашли точного совпадения, проверяем частичное совпадение в программах
        programs = Programs.select().where(Programs.program_title.contains(user_choice))
        if programs.count() == 1:
            show_program_details(message, programs[0].program_title)
            return

        # Если не нашли в программах, проверяем частичное совпадение в основном меню
        menu_items = Menu.select().where(Menu.menu_title.contains(user_choice))
        if menu_items.count() == 1:
            handle_menu_navigation(message, menu_items[0])
            return

        # Если ничего не найдено - показываем главное меню
        bot.send_message(message.chat.id, "Пожалуйста, выберите пункт из меню ниже:")
        show_main_menu(message)

    except Exception as e:
        logger.error(f"Ошибка при обработке выбора меню '{user_choice}': {e}")
        bot.send_message(message.chat.id, "Ошибка при обработке запроса. Попробуйте позже.")
        show_main_menu(message)


# Обработчик текстовых сообщений
@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_all_messages(message: Message) -> None:
    """
    Обработчик всех текстовых сообщений
    """
    if message.text.startswith('/'):
        bot.send_message(
            message.chat.id,
            "Такой команды нет. Введите /help для списка команд."
        )
    else:
        # Обрабатываем выбор из меню
        handle_menu_selection(message)


# =======================================================================
# ============================ НАВИГАЦИЯ ================================
# =======================================================================
def handle_no_programs_found(message: Message, menu_item: Menu) -> None:
    """
    Универсальная обработка случая, когда программ не найдено
    Показывает описание раздела и кнопку для общей записи
    """
    try:
        response = f"{menu_item.menu_title}"
        if menu_item.menu_description:
            response += f"\n\n{menu_item.menu_description}"

        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            KeyboardButton(f'Записаться на "{menu_item.menu_title}"'),
            KeyboardButton('Назад в меню')
        )

        bot.send_message(message.chat.id, response, reply_markup=markup)

        # Сохраняем выбранную программу для формы записи
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['selected_program'] = menu_item.menu_title

        bot.set_state(message.from_user.id, States.program_selection, message.chat.id)

        logger.info(f"Показана общая запись для раздела: {menu_item.menu_title}")

    except Exception as e:
        logger.error(f"Ошибка при обработке отсутствия программ: {e}")
        bot.send_message(message.chat.id, "Ошибка при загрузке информации")


def show_generic_program_menu(message: Message, menu_item: Menu) -> None:
    """
    Показывает страховочное меню для пунктов без обработчиков: описание и кнопка для общей записи
    """
    try:
        handle_no_programs_found(message, menu_item)

    except Exception as e:
        logger.error(f"Ошибка при загрузке универсального меню: {e}")
        bot.send_message(message.chat.id, "Ошибка при загрузке информации")


def show_general_programs_menu(message: Message) -> None:
    """
    Показывает подменю для 'Общие программы' с форматами занятий - ОПТИМИЗИРОВАТЬ (потом объединить в процедуру)
    """
    try:
        # Получаем описание раздела
        menu_item = Menu.get(Menu.menu_id == MENU_STRUCTURE['general'])
        response = f"{menu_item.menu_title}\n\n{menu_item.menu_description}"

        # Показываем форматы занятий
        format_items = Menu.select().where(
            Menu.menu_id.in_([4, 5, 20])    # Персональные, Групповые, ТОП-Мастер
        ).order_by(Menu.menu_id)

        button_titles = [item.menu_title for item in format_items]
        markup = create_keyboard(button_titles, back_button_text='Назад в меню')

        # Сначала отправляем описание, потом меню
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
    Показывает описание программы и кнопку записи
    """
    try:
        program = Programs.get(Programs.program_title == program_title)

        # Формируем ответ
        response = f"{program.program_title}\n\n{program.program_description}"

        # Добавляем длительность и стоимость если есть
        if program.program_duration:
            response += f"\n\nДлительность: {program.program_duration}"
        if program.program_price:
            response += f"\nСтоимость: {program.program_price}"

        # Создаем кнопки
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            KeyboardButton(f'Записаться на "{program.program_title}"'),
            KeyboardButton('Назад')
        )

        bot.send_message(message.chat.id, response, reply_markup=markup)

        # Сохраняем выбранную программу в состоянии
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

        button_titles = [program.program_title for program in programs]
        markup = create_keyboard(button_titles, back_button_text='Назад')

        bot.send_message(message.chat.id, response)
        bot.send_message(message.chat.id, choice_text, reply_markup=markup)
        bot.set_state(message.from_user.id, States.program_selection, message.chat.id)

    except Exception as e:
        logger.error(f"Ошибка при загрузке программ menu_id {menu_id}: {e}")
        bot.send_message(message.chat.id, "Ошибка при загрузке программ")


def show_group_programs_format(message: Message) -> None:
    """Показывает подменю для групповых занятий по длительности"""
    try:
        menu_item = Menu.get(Menu.menu_id == 5)
        response = f"{menu_item.menu_title}\n\n{menu_item.menu_description}"

        duration_items = Menu.select().where(Menu.menu_id.in_([21, 22]))

        button_titles = [item.menu_title for item in duration_items]
        markup = create_keyboard(button_titles, back_button_text='Назад')

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

        # Ищем программы по target_menu_id
        found_programs = []
        all_programs = Programs.select()

        for program in all_programs:
            # Проверяем основную привязку
            if program.menu_id == target_menu_id:
                found_programs.append(program)
                continue

            # Проверяем multiple_menu_ids
            if program.multiple_menu_ids:
                multiple_ids = [id_str.strip() for id_str in program.multiple_menu_ids.split(',')]
                if str(target_menu_id) in multiple_ids:
                    found_programs.append(program)

        logger.info(f"Найдено программ для {menu_key} (menu_id {target_menu_id}): {len(found_programs)}")
        for prog in found_programs:
            logger.info(
                f"Программа: {prog.program_title}, menu_id: {prog.menu_id}, multiple_ids: {prog.multiple_menu_ids}")

        # Если программ не найдено
        if len(found_programs) == 0:
            handle_no_programs_found(message, menu_item)
            return

        # Если программы найдены - показываем список
        response = f"{menu_item.menu_title}"
        if menu_item.menu_description:
            response += f"\n\n{menu_item.menu_description}"

        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        buttons = []

        for program in found_programs:
            buttons.append(KeyboardButton(program.program_title))

        buttons.append(KeyboardButton('Назад в меню'))
        markup.add(*buttons)

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


def show_information_menu(message: Message) -> None:
    """
    Показывает подменю с информационными разделами
    """
    try:
        # Получаем информационные пункты меню
        info_items = Menu.select().where(
            Menu.menu_id.in_([1, 2, 3, 6, 8, 9, 10, 11, 12, 13, 23])  # Все информационные разделы
        ).order_by(Menu.menu_id)

        button_titles = [item.menu_title for item in info_items]
        markup = create_keyboard(button_titles, back_button_text='Назад в меню')

        bot.send_message(
            message.chat.id,
            'Выберите информационный раздел:',
            reply_markup=markup
        )

        bot.set_state(message.from_user.id, States.submenu_selection, message.chat.id)

    except Exception as e:
        logger.error(f"Ошибка при загрузке информационного меню: {e}")
        bot.send_message(message.chat.id, "Ошибка при загрузке меню")


def handle_back_navigation(message: Message) -> None:
    """
    Обрабатывает навигацию 'Назад'
    """
    try:
        current_state = bot.get_state(message.from_user.id, message.chat.id)

        if current_state == States.program_selection:
            # Возврат из программы в общие программы
            show_general_programs_menu(message)
        elif current_state == States.submenu_selection:
            # Возврат из подменю в главное меню
            show_main_menu(message)
        else:
            # По умолчанию в главное меню
            show_main_menu(message)

    except Exception as e:
        logger.error(f"Ошибка при обработке навигации 'Назад': {e}")
        show_main_menu(message)


def handle_menu_navigation(message: Message, menu_item: Menu) -> None:
    """
    Обрабатывает навигацию по меню
    """
    menu_id = menu_item.menu_id

    # logger.info(f"handle_menu_navigation: menu_id={menu_id}, menu_title='{menu_item.menu_title}'")
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
        else:
            # Используем универсальный обработчик
            show_generic_program_menu(message, menu_item)

    # Подменю форматов занятий
    elif menu_id in [4, 5, 20]:  # Персональные, Групповые, ТОП-Мастер
        if menu_id == 4:  # Персональные
            show_programs_by_type(message, 4)    # было show_personal_programs(message)
        elif menu_id == 5:  # Групповые
            show_group_programs_format(message)
        elif menu_id == 20:  # ТОП-Мастер
            show_programs_by_type(message, 20, 'Выберите программу с ТОП-Мастером:')
            # было show_top_master_programs(message)

    # Подменю групповых занятий по длительности
    elif menu_id in [21, 22]:  # 60 минут, 90-120 минут
        show_group_programs_by_duration(message, menu_id)

    # Информационные разделы (из Контакты и расписание)
    elif menu_id in [1, 2, 3, 6, 8, 9, 10, 11, 12, 13, 23]:
        display_info_content(message, menu_item)

    else:
        # Для всех остальных пунктов используем универсальный обработчик
        show_generic_program_menu(message, menu_item)


# =======================================================================
# =========================== ИНФО-РАЗДЕЛЫ ==============================
# =======================================================================

def display_info_content(message: Message, menu_item: Menu) -> None:
    """
    Отображает контент информационных разделов
    """
    menu_id = menu_item.menu_id

    try:
        # Простые информационные разделы (только заголовок и описание)
        if menu_id in [MENU_STRUCTURE['about'], MENU_STRUCTURE['services'], MENU_STRUCTURE['schedule']]:
            display_info_m(message, menu_item)

        elif menu_id == MENU_STRUCTURE['events']:  # Мероприятия
            display_info_tab(
                message,
                model=Events,
                title="Мероприятия",
                fields=["event_title", "event_description", "event_duration", "event_price"],
                empty_message="На данный момент мероприятий нет.",
                error_prefix="Ошибка при загрузке информации о мероприятиях"
            )

        elif menu_id == MENU_STRUCTURE['mentors']:  # Наставники
            display_info_tab(
                message,
                model=Mentors,
                title="Наставники",
                fields=["mentor_title", "mentor_description"],
                empty_message="Информация о наставниках недоступна",
                error_prefix="Ошибка загрузки информации о наставниках"
            )

        elif menu_id == MENU_STRUCTURE['retreats']:  # Ретриты
            display_info_tab(
                message,
                model=Retreats,
                title="Ретриты",
                fields=["retreat_title", "retreat_description"],
                empty_message="Сейчас ретритов нет",
                error_prefix="Ошибка при загрузке информации о ретритах"
            )

        elif menu_id == MENU_STRUCTURE['reviews']:  # Отзывы
            try:
                reviews = Reviews.select()
                logger.info(f"Отладка: найдено {reviews.count()} записей")
                for review in reviews:
                    logger.info(f"Отзыв: id={review.review_id}, menu_id={review.menu_id}, img_link={review.img_link}")
            except Exception as e:
                logger.error(f"Ошибка при отладке отзывов: {e}")

            display_info_tab(
                message,
                model=Reviews,
                title="Отзывы",
                fields=["img_link"],
                empty_message="Отзывы временно недоступны",
                error_prefix="Ошибка при загрузке отзывов"
            )

        elif menu_id == MENU_STRUCTURE['contacts']:  # Контакты
            display_info_tab(
                message,
                model=Contacts,
                title="Контакты",
                fields=["contacts_title", "contacts_description"],
                empty_message="Контакты недоступны",
                error_prefix="Ошибка при загрузке контактов"
            )

        elif menu_id == MENU_STRUCTURE['location']:  # Схема проезда
            display_location(message, menu_item)

        elif menu_id == MENU_STRUCTURE['all_programs']:  # Все программы
            display_all_programs(message)

        elif menu_id == MENU_STRUCTURE['faq']:  # FAQ
            display_faq_menu(message)

        else:
            response = f"{menu_item.menu_title}\n\n{menu_item.menu_description}"
            bot.send_message(message.chat.id, response)

    except Exception as e:
        logger.error(f"Ошибка при загрузке информационного контента {menu_id}: {e}")
        bot.send_message(message.chat.id, "Ошибка при загрузке информации")


def display_info_m(message: Message, menu_item: Menu) -> None:
    """Процедура отображения пунктов инфо-меню из таблицы Menu"""
    try:
        response = f"{menu_item.menu_title}\n\n{menu_item.menu_description}"
        bot.send_message(message.chat.id, response)
    except Exception as e:
        logger.error(f"Ошибка при отображении меню '{menu_item.menu_title}': {e}")
        bot.send_message(message.chat.id, "Ошибка при отображении информации")


def display_info_tab(message: Message, model, title: str, fields: list[str],
                     empty_message: str, error_prefix: str) -> None:
    """Процедура отображения пунктов инфо-меню из индивидуальных таблиц"""
    try:
        items = model.select()

        logger.info(f"Отладка {title}: найдено {items.count()} записей, модель: {model}")
        for item in items:
            logger.info(f"Запись: {item.__dict__}")

        if items.count() > 0:
            response = f"{title}\n\n"
            for item in items:
                for field in fields:
                    value = getattr(item, field, None)
                    if value is not None:
                        response += f"{value}\n"
                response += "\n"
            bot.send_message(message.chat.id, response)
        else:
            bot.send_message(message.chat.id, empty_message)

    except Exception as e:
        logger.error(f"{error_prefix}: {e}")
        bot.send_message(message.chat.id, f"{error_prefix}")


# -------------------------- ПРАЙС ----------------------------

def display_pricing(message: Message) -> None:
    """Отображает стоимость занятий"""
    try:
        prices = Price.select()
        response = "Стоимость занятий\n\n"

        for price in prices:
            response += f"{price.price_title}\n"
            if price.price_description:
                response += f"{price.price_description}\n"

            # Детали стоимости
            details = PriceDetail.select().where(PriceDetail.price == price)
            for detail in details:
                response += f"- {detail.price_detail_title}: {detail.price_detail_price}\n"
                if detail.price_detail_duration:
                    response += f"  ({detail.price_detail_duration})\n"

            response += "\n"

        bot.send_message(message.chat.id, response)

    except Exception as e:
        logger.error(f"Ошибка при загрузке стоимости: {e}")
        bot.send_message(message.chat.id, "Ошибка при загрузке стоимости")


# ------------------------- CХЕМА ПРОЕЗДА ---------------------------
def parse_coordinates(coord_string):
    """Парсит координаты из строки в формате 'lat,lon'"""
    if not coord_string:
        return None, None

    try:
        coords = coord_string.replace(' ', '').split(',')
        if len(coords) == 2:
            latitude = float(coords[0])
            longitude = float(coords[1])
            return latitude, longitude
    except (ValueError, AttributeError, IndexError) as e:
        logger.error(f"Ошибка парсинга координат '{coord_string}': {e}")

    return None, None


def display_location(message: Message, menu_item: Menu = None) -> None:
    """Отображает схему проезда"""
    try:
        contacts = Contacts.select().where(Contacts.menu == MENU_STRUCTURE['contacts'])

        address = None
        coordinates_str = None

        for contact in contacts:
            if contact.contacts_title == 'Адрес':
                address = contact.contacts_description
            elif contact.contacts_title == 'Координаты':
                coordinates_str = contact.contacts_description

        # Получает координаты из базы данных
        latitude, longitude = parse_coordinates(coordinates_str)

        # Если координаты не получены, используются дефолтные
        if latitude is None or longitude is None:
            latitude, longitude = 55.831903, 37.330881
            logger.warning("Использованы дефолтные координаты")

        # Ссылки на карты
        yandex_maps_url = f"https://yandex.ru/maps/?text={address}"
        static_map_url = (f"https://static-maps.yandex.ru/1.x/?ll="
                          f"{longitude},{latitude}&size=450,450&z=16&l=map&pt={longitude},{latitude},pm2rdm")

        response = f"{menu_item.menu_title}\n\n"
        response += f"Адрес: {address}\n\n"
        response += "Навигация:\n"
        response += f"Яндекс.Карты: {yandex_maps_url}\n"
        response += ("Как добраться:\nОт метро 'Мякинино' 10 минут на автобусе\n"
                     "От метро 'Тушинская' 15 минут на маршрутке\nЕсть парковка")

        bot.send_message(message.chat.id, response)

        # Отправляет карту
        try:
            bot.send_photo(message.chat.id, static_map_url, caption="Расположение студии Yogita")
        except Exception as photo_error:
            logger.error(f"Ошибка при отправке карты: {photo_error}")
            # Если не удалось отправить фото, отправляется дополнительная информация
            bot.send_message(message.chat.id, "Для построения маршрута используйте ссылки выше")

    except Exception as e:
        logger.error(f"Ошибка при загрузке схемы проезда: {e}")
        bot.send_message(message.chat.id, "Ошибка загрузки схемы проезда")


# --------------------------- FAQ -----------------------------
def display_faq_menu(message: Message) -> None:
    """
    Показывает меню FAQ с вопросами из базы данных
    """
    try:
        faqs = FAQ.select()
        if faqs.count() > 0:
            # Создаем меню с вопросами
            markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
            buttons = []

            for faq in faqs:
                # Используем полный текст вопроса из базы
                buttons.append(KeyboardButton(faq.question))

            buttons.append(KeyboardButton('Назад'))
            markup.add(*buttons)

            bot.send_message(
                message.chat.id,
                "Часто задаваемые вопросы:\nВыберите вопрос для просмотра ответа:",
                reply_markup=markup
            )

            bot.set_state(message.from_user.id, States.submenu_selection, message.chat.id)
        else:
            bot.send_message(message.chat.id, "FAQ временно недоступны")

    except Exception as e:
        logger.error(f"Ошибка при загрузке FAQ: {e}")
        bot.send_message(message.chat.id, "Ошибка при загрузке FAQ")


def display_faq_answer(message: Message, faq_item: FAQ) -> None:
    """
    Показывает ответ на выбранный вопрос FAQ
    """
    try:
        response = f"ВОПРОС: {faq_item.question}\n\n"
        response += f"ОТВЕТ: {faq_item.answer}\n\n"

        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            KeyboardButton('Назад к вопросам'),
            KeyboardButton('Записаться на занятие')
        )

        bot.send_message(message.chat.id, response, reply_markup=markup)

    except Exception as e:
        logger.error(f"Ошибка при загрузке ответа FAQ: {e}")
        bot.send_message(message.chat.id, "Ошибка при загрузке ответа")
        display_faq_menu(message)


# ------------------------ ВСЕ ПРОГРАММЫ -----------------------------

def display_all_programs(message: Message) -> None:
    """
    Показывает все программы, сгруппированные по типам
    """
    try:
        logger.info(f"Начинаем вывод всех программ")

        # Группируем программы по menu_id согласно структуре базы
        personal_programs = Programs.select().where(Programs.menu == 4)  # Персональные
        group_programs = Programs.select().where(Programs.menu == 5)  # Групповые
        top_programs = Programs.select().where(Programs.menu == 20)  # ТОП-Мастер
        massage_programs = Programs.select().where(Programs.menu == 3)  # Массаж

        response = "Все программы студии\n\n"

        # Персональные занятия
        if personal_programs.count() > 0:
            logger.info(f"Найдены Персональные занятия")
            response += "Персональные занятия:\n"
            for program in personal_programs:
                response += f"• {program.program_title}\n"
            response += "\n"

        # Групповые занятия
        if group_programs.count() > 0:
            logger.info(f"Найдены Групповые занятия")
            response += "Групповые занятия:\n"
            for program in group_programs:
                duration = program.program_duration if program.program_duration else ""
                price = program.program_price if program.program_price else ""
                response += f"• {program.program_title}"
                if duration:
                    response += f" - {duration}"
                if price:
                    response += f" - {price}"
                response += "\n"
            response += "\n"

        # ТОП-Мастер
        if top_programs.count() > 0:
            logger.info(f"Найдены занятия с ТОП-Мастером")
            response += "Занятия с ТОП-Мастером:\n"
            for program in top_programs:
                response += f"• {program.program_title}\n"
            response += "\n"

        # Массаж
        if massage_programs.count() > 0:
            logger.info(f"Найден Массаж")
            response += "Массаж:\n"
            for program in massage_programs:
                response += f"• {program.program_title}\n"
                if program.program_description:
                    # Берем только первую строку описания
                    desc_lines = program.program_description.split('\n')
                    if desc_lines:
                        response += f"  {desc_lines[0]}\n"
            response += "\n"

        # Если ничего не найдено
        if response == "Все программы студии\n\n":
            response += "На данный момент программы отсутствуют."

        button_titles = ['Записаться на занятие']
        markup = create_keyboard(button_titles, back_button_text='Назад в меню')

        # Отправляем сообщение пользователю
        bot.send_message(
            message.chat.id,
            response,
            reply_markup=markup
        )

        logger.info("Все программы успешно отправлены пользователю")

    except Exception as e:
        logger.error(f"Ошибка при загрузке всех программ: {e}")
        bot.send_message(message.chat.id, "Ошибка при загрузке списка программ")


# =======================================================================
# ========================== ПРОЦЕСС ЗАЯВКИ =============================
# =======================================================================

def start_program_order(message: Message, program_title: str) -> None:
    """
    Начинает процесс записи на конкретную программу
    """
    try:
        # Сохраняем выбранную программу
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['selected_program'] = program_title

        # Проверяем, есть ли пользователь в базе
        user_id = message.from_user.id
        try:
            user = User.get(User.user_id == user_id)
        except DoesNotExist:
            # Если пользователя нет, создаем временную запись
            user = User.create(
                user_id=user_id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name
            )

        # Запрос номера телефона с указанием программы
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            KeyboardButton("Отправить контакт", request_contact=True),
            KeyboardButton("Отмена")
        )

        bot.send_message(
            message.chat.id,
            f"ЗАПИСЬ на программу: {program_title}\n\n"
            "ВНИМАНИЕ! Введя номер телефона, вы соглашаетесь на обработку персональных данных.\n"
            "Введите ваш номер телефона:",
            reply_markup=markup,
            parse_mode='Markdown'
        )

        bot.set_state(message.from_user.id, States.order_phone, message.chat.id)

    except Exception as e:
        logger.error(f"Ошибка при записи на программу {program_title}: {e}")
        bot.send_message(message.chat.id, "Ошибка. Попробуйте позже")


def forward_order_to_admin(order):
    """
    Пересылает информацию о заказе администратору в Telegram
    """
    if not ADMIN_CHAT_ID:
        logger.warning("ADMIN_CHAT_ID не установлен, уведомление не отправлено")
        return

    try:
        order_info = [
            f"ВАМ НОВАЯ ЗАЯВКА №{order.order_id}",
            f"Имя: {order.name}",
            f"Телефон: {order.phone}",
            f"Услуга: {order.service_type or 'Не указана'}",
            f"Дата: {order.created_date.strftime('%Y-%m-%d %H:%M:%S')}",
        ]

        if order.comment:
            order_info.append(f"Комментарий: {order.comment}")

        # Информация о пользователе
        user_info = f"ID пользователя: {order.user.user_id}"
        if order.user.username:
            user_info += f" (@{order.user.username})"
        order_info.append(user_info)

        order_text = "\n".join(order_info)

        # Отправка сообщение
        bot.send_message(ADMIN_CHAT_ID, order_text)
        logger.info(f"Заявка №{order.order_id} переслана администратору")

    except Exception as e:
        logger.error(f"Ошибка при пересылке заявки: {e}")


def cancel_order(message: Message) -> None:
    """
    Отменяет процесс записи
    """
    bot.send_message(
        message.chat.id,
        "Запись отменена.",
        reply_markup=ReplyKeyboardRemove()
    )
    bot.delete_state(message.from_user.id, message.chat.id)
    show_main_menu(message)

# ====================== КОНЕЦ ПРОЦЕССА ЗАЯВКИ ==========================


def create_keyboard(button_titles: list[str], row_width: int = 2, add_back_button: bool = True,
                    back_button_text: str = None) -> ReplyKeyboardMarkup:
    """Создает клавиатуру с кнопками"""
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=row_width)
    buttons = [KeyboardButton(title) for title in button_titles]

    if add_back_button:
        if back_button_text:
            buttons.append(KeyboardButton(back_button_text))
        else:
            buttons.append(KeyboardButton('Назад' if len(button_titles) <= 4 else 'Назад в меню'))

    markup.add(*buttons)
    return markup
