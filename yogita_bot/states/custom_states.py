from telebot.handler_backends import State, StatesGroup


class States(StatesGroup):

    base = State()
    menu_selection = State()  # Состояние для выбора из меню
    order_phone = State()
    order_name = State()
    order_service = State()
    order_comment = State()
    # Состояния для отслеживания навигации
    program_selection = State()  # Для выбора конкретной программы
    submenu_selection = State()  # Для подменю
