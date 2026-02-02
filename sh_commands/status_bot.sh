#!/bin/bash
# Проверка статуса бота

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/bot_control.log"
BOT_LOG="$LOG_DIR/bot.log"
BOT_SCRIPT="main.py"

check_status() {
    if ps aux | grep -v grep | grep -q "$BOT_SCRIPT"; then
        echo "Бот запущен"
        ps aux | grep -v grep | grep "$BOT_SCRIPT"
        return 0
    else
        echo "Бот не запущен"
        return 1
    fi
}

echo "СТАТУС БОТА"
echo "Время: $(date '+%Y-%m-%d %H:%M:%S')"
check_status
