from telebot.types import Message, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from loader import bot

from models import User, News, NewsStats
from peewee import JOIN

from states.custom_states import States
from config_data.config import (CANCEL_COMMANDS, CANCEL, ADMIN_PANEL, NEWS_STATS, USER_STATS,
                                ADMIN_CHAT_IDS, NEWS_ADD, NEWS_TEXT_ONLY, NEWS_ADD_MEDIA,
                                NEWS_MEDIA_DIR, NEWS_SEND, NEWS_LIST, NEWS_DELETE, NEWS_STOP_COMMANDS,
                                NEWS_STOP_MESSAGE, NEWS_STATUS_ADD, NEWS_STATUS_COMMIT, NEWS_STATUS_SEND,
                                NEWS_SEND_MESSAGE, MAIN_MENU, ADMIN_BUTTONS)

from handlers.common.admin_only import admin_required, is_admin
from handlers.common.keyboards import create_keyboard
from handlers.admin.handlers import handle_admin_panel

from typing import Optional, Dict, List, Any

import time
from datetime import datetime

import re
import os
from pathlib import Path

import logging


logger = logging.getLogger(__name__)


# =======================================================================
# ======================== ОБРАБОТЧИКИ НОВОСТЕЙ =========================
# =======================================================================

@bot.message_handler(func=lambda message: message.text == NEWS_ADD)
@bot.message_handler(commands=['add_news'])
@admin_required
def handle_add_news(message: Message) -> None:
    """
    Начинает процесс добавления новости
    """
    try:
        # Очищаем флаги (для корректного сохранения новости)
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data.pop('news_saved', None)

    except Exception as e:
        logger.warning(f"Не удалось получить данные для пользователя {message.from_user.id}: {e}. "
                       f"Код продолжает выполняться.")

    markup = create_keyboard([CANCEL], add_back_button=True, row_width=2)

    bot.send_message(
        message.chat.id,
        "ДОБАВЛЕНИЕ НОВОСТИ\n\nВведите заголовок новости:",
        parse_mode='Markdown',
        reply_markup=markup
    )
    bot.set_state(message.from_user.id, States.news_title, message.chat.id)
    logger.info(f"Начало добавления новости администратором {message.from_user.id}")


@bot.message_handler(func=lambda message: message.text.lower() in CANCEL_COMMANDS, state='*')
def handle_cancel(message: Message):
    """
    Обрабатывает отмену из любого состояния
    """
    current_state = bot.get_state(message.from_user.id, message.chat.id)

    # Проверяем, находится ли пользователь в состоянии создания новости
    is_in_news_creation = False
    if current_state:
        if 'news' in current_state:
            is_in_news_creation = True

    if current_state and is_in_news_creation:
        # Получаем данные состояния перед удалением
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            news_title = data.get('news_title', 'Без названия')

        # Удаляем состояние и данные
        bot.delete_state(message.from_user.id, message.chat.id)

        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        if is_admin(message.from_user.id):
            markup.add(KeyboardButton(ADMIN_PANEL))
        else:
            markup.add(KeyboardButton(MAIN_MENU))

        bot.send_message(
            message.chat.id,
            f"Создание новости '{news_title[:50]}...' отменено!",
            reply_markup=markup
        )

        logger.info(f"Администратор {message.from_user.id} отменил создание новости.")
        return

    # Для всех прочих состояний
    elif current_state and 'order' in current_state:
        bot.send_message(
            message.chat.id,
            "Действие отменено!",
            reply_markup=ReplyKeyboardRemove()
        )
        bot.delete_state(message.from_user.id, message.chat.id)

    # Возвращаем в соответствующее меню
    elif is_admin(message.from_user.id):
        handle_admin_panel(message)
        logger.info(f"Администратор {message.from_user.id} отменил действие.")
    else:
        try:
            from handlers.public.main_menu_handler import show_main_menu
            show_main_menu(message)
            logger.info(f"Пользователь {message.from_user.id} отменил действие.")
        except Exception as e:
            logger.error(f"Ошибка при отмене добавления новости: {e}")


@bot.message_handler(state=States.news_title)
def handle_news_title(message: Message) -> None:
    """
    Обрабатывает заголовок новости
    """
    # Проверка на отмену
    if message.text.lower() in CANCEL_COMMANDS:
        handle_cancel(message)
        return

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['news_title'] = message.text

    logger.info(f"Получен заголовок новости: '{message.text[:50]}...'")

    markup = create_keyboard([CANCEL], add_back_button=False, row_width=2)

    bot.send_message(
        message.chat.id,
        "Введите текст новости:",
        parse_mode='Markdown',
        reply_markup=markup
    )
    bot.set_state(message.from_user.id, States.news_content, message.chat.id)


@bot.message_handler(state=States.news_content)
def handle_news_content(message: Message) -> None:
    """
    Обрабатывает текст новости
    """
    # Проверка на отмену
    if message.text.lower() in CANCEL_COMMANDS:
        handle_cancel(message)
        return

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['news_content'] = message.text

    logger.info(f"Получен текст новости, длина: {len(message.text)} символов.")

    button_titles = [NEWS_ADD_MEDIA, NEWS_TEXT_ONLY, CANCEL]
    markup = create_keyboard(button_titles, add_back_button=False, row_width=2)

    bot.send_message(
        message.chat.id,
        "Добавить фото или файл к новости?",
        reply_markup=markup
    )
    bot.set_state(message.from_user.id, States.news_media, message.chat.id)


@bot.message_handler(state=States.news_media, content_types=['text'])
@bot.message_handler(commands=[NEWS_ADD_MEDIA])
def handle_news_media_choice(message: Message) -> None:
    """
    Обрабатывает выбор медиа с защитой от дублирования
    """
    logger.info(f"handle_news_media_choice: состояние States.news_media активно")
    logger.info(f"Текст сообщения: {message.text}")

    # Проверка на отмену
    if message.text.lower() in CANCEL_COMMANDS:
        bot.delete_state(message.from_user.id, message.chat.id)
        bot.send_message(message.chat.id, "Добавление новости отменено.", reply_markup=ReplyKeyboardRemove())
        handle_admin_panel(message)
        return

    logger.info(f"handle_news_media_choice: состояние States.news_media активно")
    logger.info(f"Текст сообщения: {message.text}")

    # Проверка существования новости
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        if data.get('news_saved', False):
            logger.warning(f"Игнорируем повторный запрос от пользователя {message.from_user.id}")
            return

    if message.text == NEWS_TEXT_ONLY:
        logger.info("Создание новости без media")
        save_news(message, None, None, None)
        return

    elif message.text == NEWS_ADD_MEDIA:

        markup = create_keyboard([CANCEL], add_back_button=False, row_width=2)

        bot.send_message(message.chat.id, "Отправьте media для новости:", reply_markup=markup)
        logger.info("Ожидание media для новости")

    else:
        bot.send_message(message.chat.id, "Выберите один из предложенных вариантов или нажмите ОТМЕНА'")


@bot.message_handler(state=States.news_media, content_types=['photo', 'document', 'animation', 'video'])
def handle_news_media(message: Message) -> None:
    """
    Обрабатывает состояние добавления медиа для новости (фото, документы, GIF, видео)
    """
    # Проверка существования новости
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        if data.get('news_saved', False):
            logger.warning(f"Игнорируем повторное медиа от пользователя {message.from_user.id}")
            return

    try:
        file_info = None
        file_type = None
        original_name = None

        if message.photo:
            logger.info(f"Получено фото: {len(message.photo)} вариантов качества")
            photo = message.photo[-1]  # Самое качественное
            file_info = bot.get_file(photo.file_id)
            file_type = 'photo'
            original_name = f"photo_{int(time.time())}.jpg"

        elif message.animation:
            logger.info(f"Получена анимация: {message.animation.file_id}")
            file_info = bot.get_file(message.animation.file_id)
            file_type = 'gif'
            if hasattr(message, 'document') and message.document:
                original_name = message.document.file_name
            else:
                original_name = f"gif_{int(time.time())}.gif"

        elif message.video:
            logger.info(f"Получено видео")
            file_info = bot.get_file(message.video.file_id)
            file_type = 'video'
            if hasattr(message.video, 'file_name') and message.video.file_name:
                original_name = message.video.file_name
            else:
                original_name = f"video_{int(time.time())}.mp4"

        # Документ
        elif message.document:
            logger.info(f"Получен документ: {message.document.file_name} (MIME: {message.document.mime_type})")
            file_info = bot.get_file(message.document.file_id)
            file_type = 'document'
            original_name = message.document.file_name

        if not file_info:
            bot.send_message(message.chat.id, "Не удалось получить информацию о файле")
            return

        # Проверка размера файла
        if hasattr(file_info, 'file_size') and file_info.file_size:
            max_size = 20 * 1024 * 1024  # 20MB
            if file_info.file_size > max_size:
                bot.send_message(
                    message.chat.id,
                    f"Файл слишком большой ({file_info.file_size // (1024 * 1024)}MB). "
                    f"Максимальный размер: 20MB."
                )
                return

        # Создает директорию, если не существует
        # NEWS_MEDIA_DIR.mkdir(parents=True, exist_ok=True)

        # Сохранение файла
        filepath = save_media_file(file_info, f"news_{file_type}", original_name)
        logger.info(f"Медиа сохранено по пути: {filepath}")

        # Сохранение новости
        if file_type == 'photo':
            save_news(message, filepath, None, 'photo')
        elif file_type == 'gif':
            save_news(message, filepath, None, 'gif')
        elif file_type == 'video':
            save_news(message, None, filepath, 'video')
        else:
            save_news(message, None, filepath, 'document')

    except Exception as e:
        logger.error(f"Ошибка обработки медиа новости: {e}", exc_info=True)
        bot.send_message(message.chat.id, f"Ошибка при сохранении медиа: {e}")


def save_media_file(file_info, filename_prefix: str, original_name: str = None) -> str:
    """
    Сохраняет медиафайл и возвращает путь
    """
    try:
        downloaded_file = bot.download_file(file_info.file_path)

        if original_name:
            # Очистка названия файла
            safe_name = re.sub(r'[^\w\-_.]', '_', original_name)
            filename = f"{filename_prefix}_{int(time.time())}_{safe_name}"
        else:
            file_extension = Path(file_info.file_path).suffix
            if not file_extension:
                file_extension = '.jpg'  # Дефолтное расширение для фото
            filename = f"{filename_prefix}_{int(time.time())}{file_extension}"

        filepath = NEWS_MEDIA_DIR / filename

        with open(filepath, 'wb') as new_file:
            new_file.write(downloaded_file)

        logger.info(f"Файл сохранен: {filename}")
        return str(filepath)

    except Exception as e:
        logger.error(f"Ошибка сохранения медиафайла: {e}")
        raise


def save_news(message: Message, image_path: str = None, file_path: str = None, file_type: str = None) -> None:
    """
    Сохраняет новость в базу. Защищена от повторного вызова.
    """
    try:
        # Проверка существования новости
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            # Если новость уже была сохранена
            if data.get('news_saved', False):
                logger.warning(f"Попытка повторного сохранения новости для пользователя {message.from_user.id}")
                return

            # Флаг сохранения новости
            data['news_saved'] = True

            # Сохранение новости
            news = News.create(
                title=data['news_title'],
                content=data['news_content'],
                image_path=image_path,
                file_path=file_path,
                file_type=file_type,
                is_published=1,
                published_date=datetime.now().replace(microsecond=0)
            )

        logger.info(f"Создана новость #{news.news_id} '{data['news_title'][:30]}...'")

        # Удаление состояния после сохранения
        bot.delete_state(message.from_user.id, message.chat.id)

        markup = create_keyboard(ADMIN_BUTTONS, add_back_button=False, row_width=2)

        bot.send_message(
            message.chat.id,
            f"Новость 'ID {news.news_id} - {data['news_title']}' создана!",
            reply_markup=markup
        )

    except Exception as e:
        logger.error(f"Ошибка сохранения новости: {e}")
        bot.send_message(message.chat.id, f"Ошибка при сохранении новости: {e}")
        handle_admin_panel(message)


@bot.message_handler(func=lambda message: message.text == NEWS_DELETE)
@bot.message_handler(commands=['delete_last_news'])
@admin_required
def handle_delete_last_news(message: Message) -> None:
    """
    Удаляет последнюю неотправленную новость (со статусом 0 или 1)
    """
    try:
        # Поиск новости
        latest_news = News.select().where(
            (News.is_published == 0) | (News.is_published == 1)
        ).order_by(News.created_date.desc()).first()

        if not latest_news:
            bot.send_message(
                message.chat.id,
                "Нет неотправленных новостей для удаления.\n"
                "Все новости уже отправлены или нет созданных новостей."
            )
            logger.info("Попытка удаления неотправленной новости: не найдено")
            return

        # Удаление статистики
        stats_deleted = NewsStats.delete().where(NewsStats.news == latest_news).execute()

        if stats_deleted > 0:
            logger.info(f"Удалено {stats_deleted} записей статистики для новости #{latest_news.news_id}")

        # Удаление файлов
        files_deleted = []
        if latest_news.image_path and os.path.exists(str(latest_news.image_path)):
            try:
                os.remove(latest_news.image_path)
                files_deleted.append("фото")
                logger.info(f"Удален файл: {latest_news.image_path}")
            except Exception as e:
                logger.error(f"Ошибка удаления файла фото: {e}")

        if latest_news.file_path and os.path.exists(str(latest_news.file_path)):
            try:
                os.remove(latest_news.file_path)
                files_deleted.append("файл")
                logger.info(f"Удален файл: {latest_news.file_path}")
            except Exception as e:
                logger.error(f"Ошибка удаления файла документа: {e}")

        # Удаление новости
        news_id = latest_news.news_id
        news_title = latest_news.title
        latest_news.delete_instance()

        files_info = ""
        if files_deleted:
            files_info = f"\nУдалены: {', '.join(files_deleted)}"

        stats_info = f"\nУдалено записей статистики: {stats_deleted}" if stats_deleted > 0 else ""

        bot.send_message(
            message.chat.id,
            f"Новость ID {news_id} удалена!\n"
            f"Заголовок: {news_title}\n"
            f"Статус: {'черновик' if latest_news.is_published == 0 else 'ожидает отправки'}"
            f"{files_info}{stats_info}"
        )

        logger.info(f"Администратор {message.from_user.id} удалил новость ID {news_id}")

    except Exception as e:
        logger.error(f"Ошибка при удалении новости: {e}")
        bot.send_message(
            message.chat.id,
            f"Ошибка при удалении новости: {e}"
        )


@bot.message_handler(func=lambda message: message.text == NEWS_SEND)
@bot.message_handler(commands=['send_news'])
@admin_required
def handle_send_news(message: Message) -> None:
    """
    Отправляет последнюю новость всем пользователям
    """
    try:
        latest_news = News.select().where(News.is_published == 1).order_by(News.published_date.desc()).first()

        if not latest_news:
            bot.send_message(message.chat.id, "Нет опубликованных новостей для рассылки")
            logger.warning("Попытка рассылки без опубликованных новостей")
            return

        # Получение списка пользователей для рассылки
        users = User.select().where(User.user_id.not_in(ADMIN_CHAT_IDS))

        user_list = list(users)
        total_users = len(user_list)

        logger.info(
            f"Начало рассылки новости ID {latest_news.news_id} для {total_users} пользователей, кроме администраторов.")

        # Создает запись статистики
        start_time = datetime.now()
        news_stat = NewsStats.create(
            news=latest_news,
            total_users=total_users,
            start_time=start_time
        )

        bot.send_message(message.chat.id, f"Запуск рассылки новости для {total_users} пользователей...")

        sent_count = 0
        failed_count = 0
        results = []

        # Флаг для прерывания рассылки
        news_stop_requested = False

        for user in user_list:
            # Проверка флага отмены
            if news_stop_requested:
                logger.info(f"Рассылка прервана администратором {message.from_user.id}")
                bot.send_message(message.chat.id, NEWS_STOP_MESSAGE)
                break

            result = send_news_to_user(latest_news, user)
            results.append(result)

            if result['success']:
                sent_count += 1
            else:
                failed_count += 1

            time.sleep(0.1)

        try:
            latest_news.is_published = 2  # Отправлено
            latest_news.save()
            logger.info(f"Статус новости ID {latest_news.news_id} изменен на 'Отправлена'")
        except Exception as e:
            logger.error(f"Ошибка изменения статуса новости: {e}")

        # Завершение регистрации статистики
        end_time = datetime.now()
        duration_seconds = int((end_time - start_time).total_seconds())

        # Обновление статистики
        news_stat.sent_successfully = sent_count
        news_stat.failed_sent = failed_count
        news_stat.end_time = end_time
        news_stat.duration_seconds = duration_seconds
        news_stat.save()

        # Логирование результатов
        send_news_log(latest_news, total_users, sent_count, failed_count, results)

        # Отчет администратору
        send_news_report(message, sent_count, failed_count, results, duration_seconds)

        handle_admin_panel(message)

    except Exception as e:
        logger.error(f"Ошибка при рассылке новостей: {e}")
        bot.send_message(message.chat.id, f"Ошибка при рассылке: {e}")


# Прерывание рассылки
@bot.message_handler(func=lambda message: message.text.lower() in NEWS_STOP_COMMANDS)
@bot.message_handler(commands=['stop'])
def handle_stop_news(message: Message) -> None:
    """
    Обрабатывает запрос на прерывание рассылки
    """
    if not is_admin(message.from_user.id):
        return

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        if data.get('news_in_progress'):
            data['news_stop_requested'] = True
            bot.send_message(message.chat.id, NEWS_SEND_MESSAGE)
            logger.info(f"Запрос на прерывание рассылки от администратора {message.from_user.id}")
        else:
            bot.send_message(message.chat.id, "Активная рассылка не найдена.")


def send_news_to_user(news: News, user: User) -> dict:
    """
    Отправляет новость конкретному пользователю
    """
    result = {
        'user_id': user.user_id,
        'user_name': user.first_name,
        'success': False,
        'error': None
    }

    try:
        user_info = f"{user.first_name} (ID: {user.user_id})"
        logger.info(f"Отправка новости ID {news.news_id} пользователю: {user_info}")

        if news.file_type == 'photo' and news.image_path and os.path.exists(str(news.image_path)):
            with open(news.image_path, 'rb') as photo:
                bot.send_photo(
                    user.user_id,
                    photo,
                    caption=f"*{news.title}*\n\n{news.content}",
                    parse_mode='Markdown'
                )
            logger.info(f"Фото отправлено пользователю {user.user_id}")

        elif news.file_type == 'gif' and news.image_path and os.path.exists(str(news.image_path)):
            with open(news.image_path, 'rb') as gif:
                bot.send_animation(
                    user.user_id,
                    gif,
                    caption=f"*{news.title}*\n\n{news.content}",
                    parse_mode='Markdown'
                )
            logger.info(f"GIF отправлен пользователю {user.user_id}")

        elif news.file_type == 'video' and news.file_path and os.path.exists(str(news.file_path)):
            with open(news.file_path, 'rb') as video:
                bot.send_video(
                    user.user_id,
                    video,
                    caption=f"*{news.title}*\n\n{news.content}",
                    parse_mode='Markdown'
                )

        elif news.file_type == 'document' and news.file_path and os.path.exists(str(news.file_path)):
            with open(news.file_path, 'rb') as doc:
                bot.send_document(
                    user.user_id,
                    doc,
                    caption=f"*{news.title}*\n\n{news.content}",
                    parse_mode='Markdown'
                )
            logger.info(f"Файл отправлен пользователю {user.user_id}")

        else:
            news_text = f"*{news.title}*\n\n{news.content}"
            bot.send_message(
                user.user_id,
                f"*{news.title}*\n\n{news.content}",
                # news_text,
                parse_mode='Markdown'
            )
            logger.info(f"Текст отправлен пользователю {user.user_id}")

        result['success'] = True

    except Exception as e:
        error_msg = str(e)
        result['error'] = error_msg
        logger.error(f"Ошибка отправки пользователю {user.user_id}: {error_msg}")

    return result


def send_news_log(
        news: News,
        total_users: int,
        sent_count: int,
        failed_count: int,
        results: List) -> None:
    """
    Логирование результатов рассылки
    """
    logger.info("РЕЗУЛЬТАТЫ РАССЫЛКИ")
    logger.info(f"Новость: ID {news.news_id} - {news.title}")
    logger.info(f"Всего пользователей: {total_users}")
    logger.info(f"Успешно отправлено: {sent_count}")
    logger.info(f"Ошибок отправки: {failed_count}")

    successful_users = [r for r in results if r['success']]
    if successful_users:
        logger.info(f"Успешные отправки: {len(successful_users)}")

    failed_results = [r for r in results if not r['success']]
    if failed_results:
        logger.info(f"Ошибки отправки: {len(failed_results)}")
        for i, result in enumerate(failed_results[:5], 1):
            logger.info(f"Ошибка {i}: Пользователь {result['user_id']} - {result['error']}")


def send_news_report(
        message: Message,
        sent_count: int,
        failed_count: int,
        results: List[Dict[str, Any]],
        duration_seconds: Optional[int] = None) -> None:
    """
    Отправляет отчет администратору
    """
    report = f"{NEWS_SEND_MESSAGE}\n\nОтправлено: {sent_count}\nОшибок: {failed_count}"

    if duration_seconds:
        report += f"\nДлительность: {duration_seconds} сек."

    if failed_count > 0:
        failed_results = [r for r in results if not r['success']]
        report += f"\n\nНе удалось отправить {failed_count} пользователям"

        if failed_results:
            error_examples = []
            for result in failed_results[:3]:
                error_examples.append(f"• {result['user_name']} (ID: {result['user_id']}): {result['error'][:50]}...")

            report += "\n\nПримеры ошибок:\n" + "\n".join(error_examples)

    report += f"\n\nСтатус новости изменен на {NEWS_STATUS_SEND}"

    bot.send_message(message.chat.id, report)
    logger.info(f"Отчет отправлен администратору: {sent_count} успешно, {failed_count} ошибок")


@bot.message_handler(func=lambda message: message.text == NEWS_LIST)
@bot.message_handler(commands=['list_news'])
@admin_required
def handle_list_news(message: Message) -> None:
    """
    Показывает список последних новостей
    """
    try:
        news_items = News.select().order_by(News.created_date.desc()).limit(10)

        if not news_items:
            bot.send_message(message.chat.id, "Нет новостей")
            logger.info("Запрос списка новостей: пусто.")
            return

        response = "ПОСЛЕДНИЕ НОВОСТИ\n\n"
        for news in news_items:
            if news.is_published == 0:
                status = NEWS_STATUS_ADD
            elif news.is_published == 1:
                status = NEWS_STATUS_COMMIT
            elif news.is_published == 2:
                status = NEWS_STATUS_SEND
            else:
                status = f"Неизвестно ({news.is_published})"

            response += f"ID {news.news_id}\n"
            response += f"{news.title}\n"
            response += f"Приложение: {news.file_type}\n"
            response += f"Статус: {status}\n"
            response += f"Дата: {news.created_date.strftime('%d.%m.%Y %H:%M')}\n"
            response += "─" * 20 + "\n\n"

        bot.send_message(message.chat.id, response)
        logger.info(f"Отображен список из {len(news_items)} новостей")

    except Exception as e:
        logger.error(f"Ошибка получения списка новостей: {e}")
        bot.send_message(message.chat.id, f"Ошибка: {e}")


@bot.message_handler(func=lambda message: message.text == NEWS_STATS)
@bot.message_handler(commands=['news_stats'])
@admin_required
def handle_news_stats(message: Message) -> None:
    """
    Обрабатывает статистику рассылок
    """
    if not is_admin(message.from_user.id):
        return

    try:
        query = (NewsStats
                 .select(NewsStats, News)
                 .join(News, JOIN.LEFT_OUTER, on=(NewsStats.news == News.news_id))
                 .order_by(NewsStats.start_time.desc())
                 .limit(10))

        if not query:
            bot.send_message(message.chat.id, "Статистика рассылок отсутствует")
            return

        response = "СТАТИСТИКА РАССЫЛОК\n\n"

        for stat in query:
            # Проверка существования связанной новости
            if stat.news:
                news_title = stat.news.title[:30] + "..." if len(stat.news.title) > 30 else stat.news.title
                news_id = stat.news.news_id
            else:
                news_title = "Новость удалена"
                news_id = "?"

            success_rate = (stat.sent_successfully / stat.total_users * 100) if stat.total_users > 0 else 0

            response += f"ID новости: {news_id}\n"
            response += f"Заголовок новости: {news_title}\n"
            response += f"Дата: {stat.start_time.strftime('%d.%m.%Y %H:%M')}\n"
            response += f"Всего получателей: {stat.total_users}\n"
            response += f"Успешно: {stat.sent_successfully} ({success_rate:.1f}%)\n"
            response += f"Ошибок: {stat.failed_sent}\n"

            if stat.duration_seconds:
                response += f"Длительность: {stat.duration_seconds} сек.\n"

            response += "─" * 20 + "\n"

        bot.send_message(message.chat.id, response)
        logger.info(f"Отображена статистика рассылок для администратора {message.from_user.id}")

    except Exception as e:
        logger.error(f"Ошибка получения статистики рассылок: {e}")
        bot.send_message(message.chat.id, f"Ошибка при загрузке статистики: {e}")


@bot.message_handler(func=lambda message: message.text == USER_STATS)
@bot.message_handler(commands=['user_stats'])
@admin_required
def handle_user_stats(message: Message) -> None:
    """
    Обрабатывает кнопку статистики пользователей
    """
    try:
        users = User.select()
        total_users = users.count()

        recent_users = users.order_by(User.user_id.desc()).limit(5)

        response = f"СТАТИСТИКА ПОЛЬЗОВАТЕЛЕЙ\n\n"
        response += f"Всего пользователей: {total_users}\n"
        response += "Последние пользователи:\n"

        for user in recent_users:
            username = f" @{user.username}" if user.username else ""
            response += f"- {user.first_name} {username} (ID: {user.user_id})\n"

        bot.send_message(message.chat.id, response)
        logger.info(f"Статистика пользователей: всего - {total_users}")

    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        bot.send_message(message.chat.id, f"Ошибка: {e}")
