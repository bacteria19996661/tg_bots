import os
from dotenv import load_dotenv, find_dotenv


# Настройки базы данных
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database.db')

# Настройки логирования
LOG_PATH = os.path.join(os.path.dirname(__file__), '..', 'bot.log')
MAX_LOG_SIZE = 5 * 1024 * 1024  # 5 MB
BACKUP_COUNT = 3  # Количество резервных копий логов

TARGET_URL = "https://yogita.ru"

if not find_dotenv():
    exit("Переменные окружения не загружены, так как отсутствует файл .env")
else:
    load_dotenv()


BOT_TOKEN = os.getenv('BOT_TOKEN')
if BOT_TOKEN is None:
    exit('BOT_TOKEN не найден')


ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')  # ID админа для уведомлений

DATE_FORMAT = "%d.%m.%Y %H:%M:%S"


# Соответствие пунктов меню из базы данных
MENU_STRUCTURE = {
    'about': 1,           # О компании
    'events': 2,          # Мероприятия
    'services': 3,        # Услуги
    'personal': 4,        # Персональные занятия
    'group': 5,           # Групповые занятия
    'schedule': 6,        # Расписание
    'pricing': 7,         # Стоимость
    'mentors': 8,         # Наставники
    'retreats': 9,        # Ретриты
    'reviews': 10,        # Отзывы
    'faq': 11,            # FAQ
    'contacts': 12,       # Контакты
    'location': 13,       # Схема проезда
    'general': 14,        # Общие программы (Пилатес / Йога / Терапия)
    'pregnancy': 15,      # Для беременных / после родов
    'weight': 16,         # Коррекция веса
    'kids': 17,           # Для детей
    'rehabilitation': 18, # Реабилитация после травм
    'all_company': 19,    # Контакты и расписание
    'top': 20,            # Занятия с ТОП-Мастером
    'standard': 21,       # Обычные (60 минут)
    'extended': 22,       # Длительные (90-120 минут)
    'all_programs': 23    # Все программы
}

# Основные пункты меню для главного экрана
MAIN_MENU_ITEMS = [14, 15, 16, 17, 18, 19]

# поддерживаемые команды
DEFAULT_COMMANDS = (
    ("start", "Запустить бота"),
    ("menu", "Открыть меню"),
    ("order", "Записаться на занятие"),
    ("help", "Помощь"),
)
