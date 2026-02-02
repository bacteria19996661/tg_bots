import os
from dotenv import load_dotenv, find_dotenv

from pathlib import Path

# Корневая директория проекта (2 уровня вверх от /config_data/config.py)
ROOT_DIR = Path(__file__).parent.parent

DB_PATH = ROOT_DIR / 'database.db'
SCHEDULE_FILE_PATH = ROOT_DIR / 'yogita_schedule.json'
NEWS_MEDIA_DIR = ROOT_DIR / 'news_media'

# Настройки логирования
ENABLE_LOGGING = True  # Отключить -> False / Включить -> True
LOG_PATH = ROOT_DIR / 'logs' / 'bot.log'
MAX_LOG_SIZE = 5 * 1024 * 1024  # 5 MB
BACKUP_COUNT = 2  # Количество резервных копий логов

TARGET_URL = "https://yogita.ru"

if not find_dotenv():
    exit("Переменные окружения не загружены, так как отсутствует файл .env")
else:
    load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')

API_LINK = os.getenv('API_LINK')
CLIENT_ID = os.getenv('CLIENT_ID')
CLUB_ID = os.getenv('CLUB_ID')
FRANCHISE_ID = os.getenv('FRANCHISE_ID')
FRANCHISE_CODE = CLIENT_ID    # Код франшизы code

DEFAULT_TOKEN = os.getenv('DEFAULT_TOKEN')
DEFAULT_E_TAG = os.getenv('DEFAULT_E_TAG')

if BOT_TOKEN is None:
    exit('BOT_TOKEN не найден')

# Список Администраторов
ADMIN_CHAT_IDS = list(
    map(int, os.getenv('ADMIN_CHAT_IDS', '').split(','))
)

DATE_FORMAT = "%d.%m.%Y %H:%M:%S"

# Соответствие пунктов меню из базы данных
MENU_STRUCTURE = {
    'about': 1,  # О компании
    'events': 2,  # Мероприятия
    'services': 3,  # Услуги
    'personal': 4,  # Персональные занятия
    'group': 5,  # Групповые занятия
    'schedule': 6,  # Расписание
    'pricing': 7,  # Стоимость
    'mentors': 8,  # Наставники
    'retreats': 9,  # Ретриты
    'reviews': 10,  # Отзывы
    'faq': 11,  # FAQ
    'contacts': 12,  # Контакты
    'location': 13,  # Схема проезда
    'general': 14,  # Общие программы (Пилатес / Йога / Терапия)
    'pregnancy': 15,  # Для беременных / после родов
    'weight': 16,  # Коррекция веса
    'kids': 17,  # Для детей
    'rehabilitation': 18,  # Реабилитация после травм
    'all_company': 19,  # Контакты и расписание
    'top': 20,  # Занятия с ТОП-Мастером
    'standard': 21,  # Обычные (60 минут)
    'extended': 22,  # Длительные (90-120 минут)
    'all_programs': 23  # Все программы
}

# Основные пункты меню для главного экрана
MAIN_MENU_ITEMS = [14, 15, 16, 17, 18, 19]

HELP = 'Помощь'
CANCEL = 'Отмена'
BACK = 'Назад'
SKIP = 'Пропустить'
BACK_FAQ = 'Назад к вопросам'
SEND_CONTACT = 'Отправить контакт'
CALL_BACK = 'Записаться на занятие'
CALL_TO = 'Записаться на'
MAIN_MENU = 'Главное Меню'
ADMIN_PANEL = 'Панель администратора'

NO_PROGRAM_MESSAGE = 'Услуга или программа не выбрана'

DEFAULT_COMMANDS = (
    ("start", "Запустить бота"),
    ("menu", MAIN_MENU),
    ("order", CALL_BACK),
    ("cancel", CANCEL),
    ("help", HELP),
    ("admin_panel", ADMIN_PANEL)
)

CANCEL_COMMANDS = ['Отмена', 'отмена', 'ОТМЕНА', 'cancel', 'Cancel', 'CANCEL', '/cancel']

NEWS_ADD = 'Добавить новость'
NEWS_ADD_MEDIA = 'Добавить медиа'
NEWS_TEXT_ONLY = 'Только текст'
NEWS_SEND = 'Разослать новость'
NEWS_LIST = 'Список новостей'
NEWS_STATS = 'Статистика рассылок'
USER_STATS = 'Статистика пользователей'
NEWS_STOP = 'Прервать рассылку'
NEWS_DELETE = "Удалить последнюю новость"
NEWS_CANCEL = "Отменить создание новости"
USER_MENU = 'Пользовательское меню'

NEWS_STATUS_ADD = 'Черновик'
NEWS_STATUS_COMMIT = 'Добавлена'
NEWS_STATUS_SEND = 'Отправлена'

NEWS_SEND_MESSAGE = 'Рассылка завершена!'
NEWS_STOP_MESSAGE = "Прерывание рассылки! Рассылка будет остановлена после завершения отправки текущему пользователю."

ADMIN_ACTIONS = {
    'admin_panel': ('admin_panel', ADMIN_PANEL, 'Панель администратора'),
    'add_news': ('add_news', NEWS_ADD, 'Добавить новость'),
    'send_news': ('send_news', NEWS_SEND, 'Разослать новость'),
    'list_news': ('list_news', NEWS_LIST, 'Список новостей'),
    'del_news': ('del_news', NEWS_DELETE, 'Удалить последнюю новость'),
    'news_stats': ('news_stats', NEWS_STATS, 'Статистика рассылок'),
    'user_stats': ('user_stats', USER_STATS, 'Статистика пользователей'),
    'news_stop': ('stop', NEWS_STOP, 'Прервать рассылку'),
    'user_menu': ('user_menu', USER_MENU, 'Пользовательское меню'),
}

# Генерация списка кнопок Админ-панели
ADMIN_BUTTONS = [item[1] for item in ADMIN_ACTIONS.values()
                 if item[0] not in ['admin_panel']]

ADMIN_COMMANDS = tuple((item[0], item[2]) for item in ADMIN_ACTIONS.values())

NEWS_STOP_COMMANDS = ['stop', 'стоп', '/stop', 'Stop', 'Стоп', 'STOP', 'СТОП']

DEFAULT_COORDINATES = (55.831903, 37.330881)

ADRESS = 'Адрес'
COORDINATES = 'Координаты'
ADRESS_DESCRIPTION = ("От м. «Мякинино» 10 мин. на автобусе.\n"
                     "От м. «Тушинская» 15 мин. на маршрутке.\n"
                     "Есть парковка.")
