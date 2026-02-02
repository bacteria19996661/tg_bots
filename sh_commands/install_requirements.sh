#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/bot_control.log"
BOT_LOG="$LOG_DIR/bot.log"

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
    echo "$1"
}

log_message "УСТАНОВКА ЗАВИСИМОСТЕЙ"

# Виртуальное окружение
if [ -d ".venv" ]; then
    source ".venv/bin/activate" 2>/dev/null
    if [ -n "$VIRTUAL_ENV" ]; then
        log_message "Активирован .venv"
        PIP_CMD="pip"
    else
        log_message "Используем системный pip с --user"
        PIP_CMD="pip install --user"
    fi
else
    log_message "Используем системный pip с --user"
    PIP_CMD="pip install --user"
fi

# Установка зависимостей
if [ -f "requirements.txt" ]; then
    log_message "Установка зависимостей из requirements.txt"
    $PIP_CMD install -r requirements.txt 2>&1 | tee -a "$LOG_FILE"
    
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        log_message "Зависимости успешно установлены"
    else
        log_message "Ошибка при установке зависимостей"
        exit 1
    fi
else
    log_message "Файл requirements.txt не найден"
    exit 1
fi

log_message "Установка завершена"
