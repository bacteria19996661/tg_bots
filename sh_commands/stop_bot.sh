#!/bin/bash
# Остановка всех процессов бота

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/bot_control.log"
BOT_LOG="$LOG_DIR/bot.log"

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
    echo "$1"
}

log_message "ОСТАНОВКА БОТА"

# Остановка всех процессов бота
BOT_PROCESSES=$(ps aux | grep -E "python.*(main\.py|bot)" | grep -v grep | awk '{print $2}')

if [ -z "$BOT_PROCESSES" ]; then
    log_message "Процессы бота не найдены"
    exit 0
fi

log_message "Найдены процессы: $BOT_PROCESSES"

# Остановка процессов
for pid in $BOT_PROCESSES; do
    log_message "Останавливаем процесс $pid"
    kill -TERM "$pid" 2>/dev/null

    # Ожидание завершения
    sleep 2

    # Принудительное завершение
    if ps -p "$pid" > /dev/null 2>&1; then
        log_message "Принудительное завершение процесса $pid"
        kill -KILL "$pid" 2>/dev/null
    fi
done

# Удаление lock файлов
LOCK_FILES=(
    "/tmp/yogita_bot.lock"
    "/tmp/yogita_bot.pid"
    "$SCRIPT_DIR/bot.lock"
)

for lock_file in "${LOCK_FILES[@]}"; do
    if [ -f "$lock_file" ]; then
        rm -f "$lock_file"
        log_message "Удален lock файл: $lock_file"
    fi
done

log_message "Все процессы бота остановлены"
