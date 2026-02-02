from telebot.types import Message, ReplyKeyboardMarkup, KeyboardButton
from loader import bot

from models import (Menu, Price, PriceDetail, Contacts,
                    Events, Mentors, Retreats, Reviews, Programs, FAQ)

from states.custom_states import States
from config_data.config import (MENU_STRUCTURE, MAIN_MENU, BACK, BACK_FAQ,
                                CALL_BACK, ADRESS, COORDINATES, DEFAULT_COORDINATES, ADRESS_DESCRIPTION)

from handlers.common.keyboards import create_keyboard
from handlers.public.schedule_handlers import get_schedule_handler
import logging


logger = logging.getLogger(__name__)


# =======================================================================
# ============= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ИНФО-НАВИГАЦИИ ==================
# =======================================================================

def show_information_menu(message: Message) -> None:
    """
    Показывает подменю с информационными разделами
    """
    try:
        # Информационные пункты меню
        info_items = Menu.select().where(
            Menu.menu_id.in_([1, 2, 3, 6, 7, 8, 9, 10, 11, 12, 13, 23])  # Все информационные разделы
        ).order_by(Menu.menu_id)

        button_titles = [item.menu_title for item in info_items]
        markup = create_keyboard(button_titles, add_back_button=True, back_button_text=MAIN_MENU)

        bot.send_message(
            message.chat.id,
            'Выберите информационный раздел:',
            reply_markup=markup
        )

        bot.set_state(message.from_user.id, States.submenu_selection, message.chat.id)

    except Exception as e:
        logger.error(f"Ошибка при загрузке информационного меню: {e}")
        bot.send_message(message.chat.id, "Ошибка при загрузке меню")


def display_info_content(message: Message, menu_item: Menu) -> None:
    """
    Отображает контент информационных разделов через словарь обработчиков
    """
    menu_id = menu_item.menu_id

    logger.info(
        f"[INFO_CONTENT] menu_id={menu_id}, "
        f"pricing_id={MENU_STRUCTURE['pricing']}"
    )

    try:
        # Словарь обработчиков для информационных разделов
        info_handlers = {
            # Простые разделы (заголовок + описание)
            MENU_STRUCTURE['about']: lambda: display_info_menu_item(message, menu_item),
            MENU_STRUCTURE['services']: lambda: display_info_menu_item(message, menu_item),

            # MENU_STRUCTURE['pricing']: lambda: get_pricing(message, menu_item)(),
            MENU_STRUCTURE['pricing']: get_pricing(message, menu_item),

            # РАСПИСАНИЕ - динамический выбор обработчика
            MENU_STRUCTURE['schedule']: get_schedule_handler(message, menu_item),

            # Разделы с индивидуальными таблицами
            MENU_STRUCTURE['events']: lambda: display_info_tab(
                message, Events, "Мероприятия",
                ["event_title", "event_description", "event_duration", "event_price"],
                "На данный момент мероприятий нет.",
                "Ошибка при загрузке информации о мероприятиях"
            ),

            MENU_STRUCTURE['mentors']: lambda: display_info_tab(
                message, Mentors, "Наставники",
                ["mentor_title", "mentor_description"],
                "Информация о наставниках недоступна",
                "Ошибка загрузки информации о наставниках"
            ),

            MENU_STRUCTURE['retreats']: lambda: display_info_tab(
                message, Retreats, "Ретриты",
                ["retreat_title", "retreat_description"],
                "Сейчас ретритов нет",
                "Ошибка при загрузке информации о ретритах"
            ),

            MENU_STRUCTURE['reviews']: lambda: display_reviews(message),

            MENU_STRUCTURE['contacts']: lambda: display_info_tab(
                message, Contacts, "Контакты",
                ["contacts_title", "contacts_description"],
                "Контакты недоступны",
                "Ошибка при загрузке контактов"
            ),

            # Специальные разделы
            MENU_STRUCTURE['location']: lambda: display_location(message, menu_item),
            MENU_STRUCTURE['all_programs']: lambda: display_all_programs(message),
            MENU_STRUCTURE['faq']: lambda: display_faq_menu(message),
        }

        # Поиск обработчика в словаре
        handler = info_handlers.get(menu_id)

        if handler:
            # Вызов специального обработчика
            handler()
        else:
            # Раздел по умолчанию (просто заголовок и описание)
            response = f"{menu_item.menu_title}\n\n{menu_item.menu_description}"
            bot.send_message(message.chat.id, response)

    except Exception as e:
        logger.error(f"Ошибка при загрузке информационного контента {menu_id}: {e}")
        bot.send_message(message.chat.id, "Ошибка при загрузке информации")


def display_info_menu_item(message: Message, menu_item: Menu) -> None:
    """
    Процедура отображения пунктов инфо-меню из таблицы Menu
    """
    try:
        response = f"{menu_item.menu_title}\n\n{menu_item.menu_description}"
        bot.send_message(message.chat.id, response)
    except Exception as e:
        logger.error(f"Ошибка при отображении меню '{menu_item.menu_title}': {e}")
        bot.send_message(message.chat.id, "Ошибка при отображении информации")


def display_info_tab(message: Message, model, title: str, fields: list[str],
                     empty_message: str, error_prefix: str) -> None:
    """
    Процедура отображения пунктов инфо-меню из индивидуальных таблиц
    """
    try:
        items = model.select()

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


def get_pricing(message: Message, menu_item: Menu):
    def handler():
        try:
            prices = Price.select()

            if prices.count() == 0:
                bot.send_message(message.chat.id, "Информация о ценах временно недоступна")
                return

            response = f"{menu_item.menu_title}\n\n"
            if menu_item.menu_description:
                response += f"{menu_item.menu_description}\n\n"

            for price in prices:
                response += f"{price.price_title}\n"
                if price.price_description:
                    response += f"{price.price_description}\n"

                details = PriceDetail.select().where(PriceDetail.price == price)
                for detail in details:
                    response += f"- {detail.price_detail_title}: {detail.price_detail_price}"
                    if detail.price_detail_duration:
                        response += f" ({detail.price_detail_duration})"
                    response += "\n"

                response += "\n"

            bot.send_message(message.chat.id, response)

        except Exception as e:
            logger.error(f"Ошибка при загрузке стоимости: {e}", exc_info=True)
            bot.send_message(message.chat.id, "Ошибка при загрузке стоимости")

    return handler


def display_reviews(message: Message) -> None:
    """
    Отображает отзывы в виде картинок
    """
    try:
        reviews = Reviews.select()

        if reviews.count() == 0:
            bot.send_message(message.chat.id, "Отзывы временно недоступны")
            return

        bot.send_message(message.chat.id, "Отзывы наших клиентов:")

        for review in reviews:
            img_url = review.img_link

            if not img_url:
                continue

            try:
                # Отправка картинки по URL
                bot.send_photo(
                    message.chat.id,
                    img_url
                )
            except Exception as e:
                logger.error(f"Ошибка отправки отзыва {review.review_id}: {e}")
                bot.send_message(message.chat.id, img_url)

    except Exception as e:
        logger.error(f"Ошибка при загрузке отзывов: {e}")
        bot.send_message(message.chat.id, "Ошибка при загрузке отзывов")


def parse_coordinates(coord_string):
    """
    Парсит координаты из строки в формате 'lat, lon'
    """
    if not coord_string:
        return None, None

    try:
        # Упрощенный парсинг
        coordinates = coord_string.replace(' ', '').split(',')
        if len(coordinates) == 2:
            return float(coordinates[0]), float(coordinates[1])
    except (ValueError, AttributeError, IndexError) as e:
        logger.error(f"Ошибка парсинга координат '{coord_string}': {e}")

    return None, None


def display_location(message: Message, menu_item: Menu = None) -> None:
    """
    Отображает схему проезда
    """
    try:
        contacts = Contacts.select().where(Contacts.menu == MENU_STRUCTURE['contacts'])

        address = None
        coordinates_str = None

        for contact in contacts:
            if contact.contacts_title == ADRESS:
                address = contact.contacts_description
            elif contact.contacts_title == COORDINATES:
                coordinates_str = contact.contacts_description

        # Получает координаты из базы данных
        latitude, longitude = parse_coordinates(coordinates_str)

        # Если координаты не получены, используются дефолтные из конфига
        if latitude is None or longitude is None:
            latitude, longitude = DEFAULT_COORDINATES
            logger.warning("Использованы дефолтные координаты из конфига")

        # Ссылки на карты
        yandex_maps_url = f"https://yandex.ru/maps/?text={address}"
        static_map_url = (f"https://static-maps.yandex.ru/1.x/?ll="
                          f"{longitude},{latitude}&size=450,450&z=16&l=map&pt={longitude},{latitude},pm2rdm")

        response = f"{menu_item.menu_title}\n\n"
        response += f"Адрес: {address}\n\n"
        response += "Как добраться?\n\n"
        response += f"Яндекс.Карты: {yandex_maps_url}\n"
        response += ADRESS_DESCRIPTION

        bot.send_message(message.chat.id, response)

        # Отправка карты
        try:
            bot.send_photo(message.chat.id, static_map_url, caption="Расположение студии Yogita")
        except Exception as photo_error:
            logger.error(f"Ошибка при отправке карты: {photo_error}")
            bot.send_message(message.chat.id, "Для построения маршрута используйте ссылки выше")

    except Exception as e:
        logger.error(f"Ошибка при загрузке схемы проезда: {e}")
        bot.send_message(message.chat.id, "Ошибка загрузки схемы проезда")


def display_faq_menu(message: Message) -> None:
    """Показывает меню FAQ с вопросами из базы данных"""
    try:
        faqs = FAQ.select()
        if faqs.count() > 0:
            # Меню с вопросами
            markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
            buttons = []

            for faq in faqs:
                # Полный текст вопроса из DB
                buttons.append(KeyboardButton(faq.question))

            buttons.append(KeyboardButton(BACK))
            markup.add(*buttons)

            bot.send_message(
                message.chat.id,
                "FAQ\n\nВыберите вопрос:",
                reply_markup=markup
            )

            bot.set_state(message.from_user.id, States.submenu_selection, message.chat.id)
        else:
            bot.send_message(message.chat.id, "FAQ временно недоступны")

    except Exception as e:
        logger.error(f"Ошибка при загрузке FAQ: {e}")
        bot.send_message(message.chat.id, "Ошибка при загрузке FAQ")


def display_faq_answer(message: Message, faq_item: FAQ) -> None:
    """Показывает ответ на выбранный вопрос FAQ"""
    try:
        response = f"{faq_item.answer}\n\n"

        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            KeyboardButton(BACK_FAQ),
            KeyboardButton(MAIN_MENU)
        )

        bot.send_message(message.chat.id, response, reply_markup=markup)

    except Exception as e:
        logger.error(f"Ошибка при загрузке ответа FAQ: {e}")
        bot.send_message(message.chat.id, "Ошибка при загрузке ответа")
        display_faq_menu(message)


def display_all_programs(message: Message) -> None:
    """Показывает все программы, сгруппированные по типам"""
    try:
        # Группировка программ по menu_id
        personal_programs = Programs.select().where(Programs.menu == 4)  # Персональные
        group_programs = Programs.select().where(Programs.menu == 5)  # Групповые
        top_programs = Programs.select().where(Programs.menu == 20)  # ТОП-Мастер
        massage_programs = Programs.select().where(Programs.menu == 3)  # Массаж

        response = "Все программы студии\n\n"

        # Персональные занятия
        if personal_programs.count() > 0:
            response += "Персональные занятия:\n"
            for program in personal_programs:
                response += f"• {program.program_title}\n"
            response += "\n"

        # Групповые занятия
        if group_programs.count() > 0:
            response += "Групповые занятия:\n"
            for program in group_programs:
                duration = program.program_duration if program.program_duration else ""
                price = program.program_price if program.program_price else ""
                response += f"- {program.program_title}"
                if duration:
                    response += f" - {duration}"
                if price:
                    response += f" - {price}"
                response += "\n"
            response += "\n"

        # ТОП-Мастер
        if top_programs.count() > 0:
            response += "Занятия с ТОП-Мастером:\n"
            for program in top_programs:
                response += f"- {program.program_title}\n"
            response += "\n"

        # Массаж
        if massage_programs.count() > 0:
            response += "Массаж:\n"
            for program in massage_programs:
                response += f"- {program.program_title}\n"
                if program.program_description:
                    # Берет только первую строку описания
                    desc_lines = program.program_description.split('\n')
                    if desc_lines:
                        response += f"  {desc_lines[0]}\n"
            response += "\n"

        # Если ничего не найдено
        if response == "Все программы студии\n\n":
            response += "На данный момент программы отсутствуют."

        button_titles = [CALL_BACK]
        markup = create_keyboard(button_titles, add_back_button=True, back_button_text=MAIN_MENU)

        # Отправляет сообщение пользователю
        bot.send_message(
            message.chat.id,
            response,
            reply_markup=markup
        )

    except Exception as e:
        logger.error(f"Ошибка при загрузке всех программ: {e}")
        bot.send_message(message.chat.id, "Ошибка при загрузке списка программ")
