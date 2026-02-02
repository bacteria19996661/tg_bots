# =======  АВТОМАТИЧЕСКАЯ РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ ==========

# from .common import *
# from .public import *
# from .admin import *

# Инициализация всех обработчиков
# __all__ = ['common', 'public', 'admin']


# =======  РУЧНАЯ РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ ==========

from . import common
from . import public
from . import admin

from loader import bot as _bot

# Экспорт bot для использования во всех модулях
bot = _bot


# Функция для регистрации всех обработчиков
def register_handlers(_bot):
    """
    Регистрирует все обработчики
    """
    public.register_handlers(bot)
    admin.register_handlers(bot)
    common.register_handlers(bot)
