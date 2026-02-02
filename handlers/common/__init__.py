from . import admin_only
from . import utils
from . import keyboards
from . import validators

# Экспорт функций
from .admin_only import (
    is_admin,
    admin_required)

from .utils import (
    get_or_create_user,
    proceed_to_next_state
)

from .keyboards import (
    create_keyboard,
    create_programs_keyboard
)

from .validators import (
    validate_phone,
    validate_order_input
)

__all__ = ['admin_only', 'utils', 'keyboards', 'validators']


def register_handlers(_bot):
    from . import admin_only
    from . import utils
    from . import keyboards
    from . import validators

    # Регистрация происходит через декораторы при импорте модулей - можно вернуть None
    return [admin_only, utils, keyboards, validators]
