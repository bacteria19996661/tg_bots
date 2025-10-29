import telebot
from telebot import custom_filters
from handlers.custom_handlers.c_handlers import *

from loader import bot

import time

from models import init_database, db
import signal
import sys

import logging
from logging.handlers import RotatingFileHandler
from config_data.config import LOG_PATH, MAX_LOG_SIZE, BACKUP_COUNT, DEFAULT_COMMANDS


def setup_logging():
    """Логирование"""

    # Включение/отключение логирования
    ENABLE_LOGGING = True    # Отключить -> False / Включить -> True

    if not ENABLE_LOGGING:
        # logging.getLogger().setLevel(logging.CRITICAL)  # Только критические ошибки в Главном модуле

        logging.getLogger('__main__').setLevel(logging.CRITICAL)
        logging.getLogger('models').setLevel(logging.CRITICAL)
        logging.getLogger('c_handlers').setLevel(logging.CRITICAL)
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
    config.py - объявление токенов, ключей и прочих констант;
    c_handlers.py - обработчики
    main.py - создание обработчиков и запуск бота.
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
