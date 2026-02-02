import telebot
from telebot import custom_filters

from loader import bot

from models import init_database, db
import signal
import sys
import time

import logging
from logging.handlers import RotatingFileHandler
from config_data.config import LOG_PATH, MAX_LOG_SIZE, BACKUP_COUNT, DEFAULT_COMMANDS, ENABLE_LOGGING, NEWS_MEDIA_DIR

# Автоматическая регистрация обработчиков
import handlers


def setup_logging():
    """Логирование"""

    if not ENABLE_LOGGING:
        # Уровень CRITICAL для корневого логгера
        logging.getLogger().setLevel(logging.CRITICAL)

        # Список логгеров
        main_loggers = [
            '__main__',
            'models',
            'handlers',
            'handlers.admin',
            'handlers.admin.handlers',
            'handlers.admin.news_handlers',
            'common',
            'common.admin_only',
            'common.keyboards',
            'common.utils',
            'common.validators',
            'public',
            'public.api_schedule_handlers',
            'public.handlers',
            'public.main_menu_handler',
            'public.navigation_info',
            'public.navigation_programs',
            'public.order_handlers',
            'public.schedule_handlers'
        ]

        # Уровень CRITICAL для конкретных логгеров
        for logger_name in main_loggers:
            logging.getLogger(logger_name).setLevel(logging.CRITICAL)
        return

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Обработчик с ротацией логов
    file_handler = RotatingFileHandler(
        LOG_PATH,
        maxBytes=MAX_LOG_SIZE,
        backupCount=BACKUP_COUNT,
        encoding='utf-8'
    )

    # Обработчик для консоли
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Настройка базового логгера
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    file_handler.setFormatter(formatter)

    logging.info("\n\n>>\n")


def shutdown():
    """Завершение работы бота"""
    try:
        # Закрываем соединение с базой данных
        if not db.is_closed():
            db.close()
        logging.info("Соединение с DB закрыто")

    except Exception as e:
        logging.error("Ошибка при закрытии DB:", {e})

    sys.exit(0)


def signal_handler(sig, frame):
    """Обработчик сигнала Ctrl+C"""
    logging.info("Запущена команда Ctrl+C остановки бота")
    shutdown()


def setup_database():
    """Настройка базы данных с повторными попытками"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            init_database()
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                logging.error(f"Ошибка инициализации DB: {e}")
                return False


if __name__ == '__main__':
    """
    Регистрация обработчиков и запуск бота
    """
    try:

        setup_logging()
        logging.info("Запуск бота")

        # Регистрация обработчиков сигналов
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Инициализация базы данных перед запуском бота
        if not setup_database():
            logging.error("Ошибка: не удалось инициализировать DB")
            exit(1)

        # Создать папку для медиафайлов новостей
        NEWS_MEDIA_DIR.mkdir(exist_ok=True)

        # Фильтр состояний
        bot.add_custom_filter(custom_filters.StateFilter(bot))

        bot.set_my_commands([
            telebot.types.BotCommand(command, description) for command, description in DEFAULT_COMMANDS
        ])

        print("Бот запущен \nДля остановки бота нажмите Ctrl+C")
        bot.polling(none_stop=True, interval=0, timeout=60)

    except Exception as e:
        logging.error(f"Ошибка запуска бота: {e}")

    finally:
        shutdown()
