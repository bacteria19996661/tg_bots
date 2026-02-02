from . import handlers
from . import main_menu_handler
from . import order_handlers
from . import schedule_handlers
from . import navigation_programs
from . import navigation_info

# Экспорт функций
from .main_menu_handler import (
    show_main_menu,
    create_user_menu
)

from .handlers import (
    start,
    handle_submenu_selection,
    helper,
    back_to_faq_menu,
    handle_all_text
)

from .order_handlers import (
    order_init,
    forward_order_to_admin,
    forward_order_to_user,
    handle_order,
    get_phone_contact,
    get_phone_text,
    get_name,
    get_service_type,
    get_comment_and_save
)

from .schedule_handlers import (
    handle_schedule_week_selection,
    handle_schedule_date_selection,
    handle_schedule_activity_selection_wrapper,
    is_schedule_file_fresh,
    get_schedule_handler,
    load_grouped_schedule_data,
    get_week_dates,
    format_schedule_response,
    show_schedule_week_selection,
    show_schedule_dates,
    show_schedule_for_date,
    handle_schedule_activity_selection
)

from .navigation_programs import (
    handle_menu_selection,
    find_program_or_menu,
    handle_no_programs_found,
    show_general_programs_menu,
    show_program_details,
    show_programs_by_type,
    show_group_programs_format,
    show_group_programs_by_duration,
    show_programs_by_menu_id,
    handle_menu_navigation_programs,
    show_spare_menu,
    handle_back_navigation,
)

from .navigation_info import (
    show_information_menu,
    display_info_content,
    display_info_menu_item,
    display_info_tab,
    display_pricing,
    parse_coordinates,
    display_location,
    display_faq_menu,
    display_faq_answer,
    display_all_programs,
)

__all__ = ['main_menu_handler', 'handlers', 'order_handlers', 'schedule_handlers', 'navigation_programs',
           'navigation_info']


def register_handlers(_bot):
    from . import handlers
    from . import order_handlers
    from . import schedule_handlers
    from . import navigation_programs
    from . import navigation_info

    # Регистрируем кастомные фильтры
    # _bot.add_custom_filter(custom_filters.StateFilter(_bot))

    # Регистрация происходит через декораторы при импорте модулей - можно вернуть None
    return [main_menu_handler, handlers, order_handlers, schedule_handlers,
            navigation_programs, navigation_info]
