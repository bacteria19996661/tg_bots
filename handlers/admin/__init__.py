from . import handlers
from . import news_handlers

# Экспорт функций
from .handlers import (
    handle_admin_panel,
    show_admin_panel
)

from .news_handlers import (
    handle_add_news,
    handle_cancel,
    handle_news_title,
    handle_news_content,
    handle_news_media_choice,
    handle_news_media,
    save_media_file,
    save_news,
    handle_delete_last_news,
    handle_send_news,
    handle_stop_news,
    send_news_to_user,
    send_news_log,
    send_news_report,
    handle_list_news,
    handle_news_stats,
    handle_user_stats
)

__all__ = ['handlers', 'news_handlers']


def register_handlers(_bot):
    from . import handlers

    # Регистрация происходит через декораторы при импорте модулей
    return ['handlers', 'news_handlers']
