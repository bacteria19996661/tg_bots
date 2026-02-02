#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/bot_control.log"
BOT_LOG="$LOG_DIR/bot.log"

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
    echo "$1"
}

log_message "ПЕРЕЗАПУСК БОТА"

# Проверяем наличие скриптов
if [ ! -f "$SCRIPT_DIR/stop_bot.sh" ]; then
    log_message "ERROR: скрипт остановки stop_bot.sh не найден"
    exit 1
fi

if [ ! -f "$SCRIPT_DIR/start_bot.sh" ]; then
    log_message "ERROR: скрипт запуска start_bot.sh не найден"
    exit 1
fi

# Останавливаем бота
log_message "Остановка бота"
if bash "$SCRIPT_DIR/stop_bot.sh"; then
    log_message "Бот остановлен"
else
    log_message "WARNING: при остановке возникли проблемы"
fi

# Ожидание завершения
sleep 5

# Очистка lock-файлов
rm -f /tmp/yogita_bot.lock /tmp/yogita_bot.pid
sleep 2

# Запуск бота
log_message "Запуск бота"
if bash "$SCRIPT_DIR/start_bot.sh"; then
    log_message "Бот успешно перезапущен"
else
    log_message "ERROR: не удалось запустить бота"
    exit 1
fi

log_message "Перезапуск завершен"