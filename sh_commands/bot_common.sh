#!/bin/bash
# Общие настройки и функции для скриптов управления ботом

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/bot_control.log"
BOT_LOG="$LOG_DIR/bot.log"

LOCK_FILE="/tmp/yogita_bot.lock"
PID_FILE="/tmp/yogita_bot.pid"
VENV_PATH=".venv"

# Создание папки для логов
mkdir -p "$LOG_DIR"

# Функция логирования
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
    echo "$1"
}

# Проверка запущенных процессов бота
check_bot_processes() {
    pgrep -f "python.*(main\.py|bot\.py)" > /dev/null 2>&1
}

# Проверка существования основного файла бота
get_main_file() {
    if [ -f "$SCRIPT_DIR/main.py" ]; then
        echo "main.py"
    else
        echo ""
    fi
}

# Активация виртуального окружения
activate_venv() {
    if [ -d "$VENV_PATH" ]; then
        # Проверяем структуру .venv
        if [ -f "$VENV_PATH/bin/activate" ]; then
            VENV_ACTIVATE="$VENV_PATH/bin/activate"
            log_message "Структура .venv: Linux (bin/activate)"
        elif [ -f "$VENV_PATH/Scripts/activate" ]; then
            VENV_ACTIVATE="$VENV_PATH/Scripts/activate"
            log_message "Структура .venv: Windows (Scripts/activate)"
        else
            log_message "ERROR: Не найден скрипт активации в $VENV_PATH"
            return 1
        fi

        source "$VENV_ACTIVATE" 2>/dev/null
        if [ -n "$VIRTUAL_ENV" ]; then
            log_message "Активирован .venv: $VIRTUAL_ENV"
            return 0
        else
            log_message "WARNING: Не удалось активировать .venv"
            return 1
        fi
    fi
    return 1
}

# Определение команды python
get_python_cmd() {
    if [ -n "$VIRTUAL_ENV" ]; then
        echo "python"
    elif command -v python3 >/dev/null 2>&1; then
        echo "python3"
    else
        echo "python"
    fi
}

# Определение команды pip
get_pip_cmd() {
    if [ -n "$VIRTUAL_ENV" ]; then
        echo "pip"
    elif command -v pip3 >/dev/null 2>&1; then
        echo "pip3"
    else
        echo "pip"
    fi
}