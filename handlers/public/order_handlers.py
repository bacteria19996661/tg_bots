from telebot.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from loader import bot

from models import User, Orders

from states.custom_states import States
from config_data.config import MAIN_MENU, NO_PROGRAM_MESSAGE, SEND_CONTACT, CALL_BACK, CANCEL, SKIP, ADMIN_CHAT_IDS

from handlers.public.main_menu_handler import show_main_menu
from handlers.common.utils import get_or_create_user, proceed_to_next_state
from handlers.common.validators import validate_phone, validate_order_input

from datetime import datetime

import logging

logger = logging.getLogger(__name__)


# ============== ВСПМОГАТЕЛЬНЫЕ ФУНКЦИИ ЗАЯВКИ ====================
def order_init(message: Message, program_title: str = None) -> None:
    """
    Инициализирует процесс заявки
    """
    try:
        # Создает/обновляет пользователя
        get_or_create_user(message)

        # Сначала установите состояние
        bot.set_state(message.from_user.id, States.order_phone, message.chat.id)

        # Сохраняет выбранную программу, если есть
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['selected_program'] = program_title or NO_PROGRAM_MESSAGE

        # Запрос номера телефона
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(
            KeyboardButton(SEND_CONTACT, request_contact=True),
            KeyboardButton(CANCEL)
        )

        message_text = "ЗАЯВКА на ОБРАТНЫЙ ЗВОНОК\n\n" \
                       "ВНИМАНИЕ! Введя номер телефона, вы соглашаетесь на обработку персональных данных.\n\n" \
                       f"Нажмите «{SEND_CONTACT}» или ведите номер телефона:"

        if program_title:
            message_text = f"Предварительная ЗАПИСЬ на программу «{program_title}»\n\n" + message_text

        bot.send_message(
            message.chat.id,
            message_text,
            reply_markup=markup,
            parse_mode='Markdown'
        )

        # bot.set_state(message.from_user.id, States.order_phone, message.chat.id)

    except Exception as e:
        logger.error(f"Ошибка при инициализации заявки: {e}")
        bot.send_message(message.chat.id, "Ошибка. Попробуйте позже")


def forward_order_to_admin(order):
    if not ADMIN_CHAT_IDS:
        logger.warning("ADMIN_CHAT_IDS не установлен, уведомление не отправлено")
        return

    try:
        order_info = [
            f"Поступила НОВАЯ ЗАЯВКА №{order.order_id}",
            f"Имя: {order.name}",
            f"Телефон: {order.phone}",
            f"Услуга: {order.service_type or 'Не указана'}",
            f"Дата: {order.created_date.strftime('%Y-%m-%d %H:%M:%S')}",
        ]

        if order.comment:
            order_info.append(f"Комментарий: {order.comment}")

        user_info = f"ID пользователя: {order.user.user_id}"
        if order.user.username:
            user_info += f" (@{order.user.username})"
        order_info.append(user_info)

        order_text = "\n".join(order_info)

        # Отправка каждому администратору
        for admin_id in ADMIN_CHAT_IDS:
            bot.send_message(admin_id, order_text)

        logger.info(f"Заявка №{order.order_id} переслана администраторам")

    except Exception as e:
        logger.error(f"Ошибка при пересылке заявки: {e}")


def forward_order_to_user(message: Message, order: Orders, user_data: dict):
    """
    Отправляет подтверждение заявки пользователю
    """
    selected_program = user_data.get('selected_program', NO_PROGRAM_MESSAGE)

    if selected_program and selected_program != NO_PROGRAM_MESSAGE:
        # Запись на конкретную программу
        service_info = selected_program
    else:
        # Общая запись - показывает выбранный тип услуги
        service_info = user_data.get('service_type', 'Не указана')

    confirmation_text = (
        f"Заявка №{order.order_id} отправлена!\n"
        f"Имя: {user_data['name']}\n"
        f"Телефон: {user_data['phone']}\n"
        f"Услуга: {service_info}"
    )

    if user_data.get('comment'):
        confirmation_text += f"\nКомментарий: {user_data['comment']}"

    confirmation_text += "\n\nМы свяжемся с вами в ближайшее время для подтверждения записи"

    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton(CALL_BACK), KeyboardButton(MAIN_MENU))

    bot.send_message(message.chat.id, confirmation_text, reply_markup=markup)


# =======================================================================
# ======================== ОБРАБОТЧИКИ ЗАЯВКИ ===========================
# =======================================================================

@bot.message_handler(commands=['order'])
@bot.message_handler(func=lambda message: message.text == CALL_BACK)
def handle_order(message: Message) -> None:
    """
    Запускает процесс ОБЩЕЙ ЗАПИСИ
    """
    order_init(message)


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

            proceed_to_next_state(
                message,
                States.order_name,
                "Введите ваше имя:"
            )
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
    if not validate_order_input(message, validate_phone):
        return

    phone = message.text.strip()
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['phone'] = phone

    proceed_to_next_state(
        message,
        States.order_name,
        "Введите ваше имя:"
    )


@bot.message_handler(state=States.order_name)
def get_name(message: Message) -> None:
    """
    Обрабатывает ввод имени
    """
    if not validate_order_input(message, lambda x: (len(x) >= 2, "Пожалуйста, введите корректное имя")):
        return

    name = message.text.strip()
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['name'] = name
        selected_program = data.get('selected_program')

    if selected_program and selected_program != NO_PROGRAM_MESSAGE:
        # Переход к комментарию
        proceed_to_next_state(
            message,
            States.order_comment,
            f"Запись на программу: {selected_program}\n\nМожете добавить комментарий:",
            skip_button=True
        )
    else:
        # Выбор типа услуги
        proceed_to_next_state(
            message,
            States.order_service,
            "Выберите тип занятия:",
            ["Групповое занятие", "Персональное занятие", "Занятие у Топ Мастера", "Другое"]
        )


@bot.message_handler(state=States.order_service)
def get_service_type(message: Message) -> None:
    """
    Обрабатывает выбор услуги
    """
    if not validate_order_input(message):
        return

    service_type = message.text.strip()
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['service_type'] = service_type

    # Запрос комментария
    proceed_to_next_state(
        message,
        States.order_comment,
        "Можете добавить комментарий:",
        skip_button=True
    )


@bot.message_handler(state=States.order_comment)
def get_comment_and_save(message: Message) -> None:
    """
    Обрабатывает комментарий и сохраняет заявку с информацией о программе
    """
    if not validate_order_input(message):
        return

    try:
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            user = User.get(User.user_id == message.from_user.id)
            comment = None if message.text == SKIP else message.text.strip()

            selected_program = data.get('selected_program', NO_PROGRAM_MESSAGE)

            if selected_program and selected_program != NO_PROGRAM_MESSAGE:
                service_to_save = selected_program  # Запись на конкретную программу
            else:
                service_to_save = data.get('service_type', NO_PROGRAM_MESSAGE)  # Общая запись

            order = Orders.create(
                user=user,
                phone=data['phone'],
                name=data['name'],
                service_type=service_to_save,  # Сохранение (программа / тип услуги)
                comment=comment,
                created_date=datetime.now().replace(microsecond=0)
            )

            logger.info(
                f"Создана заявка №{order.order_id} на услугу '{service_to_save}' от пользователя {user.user_id}")

            # Очистка данных заявки из состояния
            data.pop('selected_program', None)
            data.pop('service_type', None)

            # ВЫХОД из контекста with - данные сохранены

        forward_order_to_admin(order)  # Пересылка заявки администратору
        forward_order_to_user(message, order, data)  # Инфа для пользователя

        # Сброс состояния
        bot.delete_state(message.from_user.id, message.chat.id)
        show_main_menu(message)

    except Exception as e:
        logger.error(f"Ошибка при сохранении заявки: {e}", exc_info=True)  # полный traceback
        logger.error(f"User ID: {message.from_user.id}, Chat ID: {message.chat.id}")

        # Логирует данные состояния
        try:
            with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
                logger.error(f"Данные состояния: {data}")
        except Exception as state_error:
            logger.error(f"Ошибка получения состояния: {state_error}")

        bot.send_message(
            message.chat.id,
            "Произошла ошибка при сохранении заявки. Попробуйте позже.",
            reply_markup=ReplyKeyboardRemove()
        )
        bot.delete_state(message.from_user.id, message.chat.id)
        logger.info(f"Состояние удалено.")
