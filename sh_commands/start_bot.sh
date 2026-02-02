#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/bot_control.log"
BOT_LOG="$LOG_DIR/bot.log"

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
    echo "$1"
}

log_message "ЗАПУСК БОТА"

LOCK_FILE="/tmp/yogita_bot.lock"
PID_FILE="/tmp/yogita_bot.pid"

# Проверка существующего бота
if [ -f "$LOCK_FILE" ]; then
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE" 2>/dev/null)
        if [ -n "$PID" ] && ps -p "$PID" > /dev/null 2>&1; then
            log_message "Бот уже запущен с PID: $PID"
            exit 1
        else
            rm -f "$LOCK_FILE" "$PID_FILE"
        fi
    else
        rm -f "$LOCK_FILE"
    fi
fi

# Проверка процессов по имени
if pgrep -f "python.*(main\.py|bot\.py)" > /dev/null 2>&1; then
    log_message "Процессы бота уже запущены. Сначала остановите: ./stop_bot.sh"
    exit 1
fi

# Рабочая директория
cd "$SCRIPT_DIR" || {
    log_message "Ошибка перехода в директорию: $SCRIPT_DIR"
    exit 1
}

log_message "Директория: $(pwd)"

# Виртуальное окружение
if [ -d ".venv" ]; then
    source ".venv/bin/activate" 2>/dev/null
    if [ -n "$VIRTUAL_ENV" ]; then
        log_message "Активирован .venv"
    else
        log_message "ВНИМАНИЕ: Не удалось активировать .venv"
    fi
fi

# Основной файл
if [ -f "main.py" ]; then
    MAIN_FILE="main.py"
elif [ -f "bot.py" ]; then
    MAIN_FILE="bot.py"
else
    log_message "Ошибка: не найден main.py или bot.py"
    exit 1
fi

log_message "Файл бота: $MAIN_FILE"

# Запуск
touch "$LOCK_FILE"
log_message "Запуск: python3 $MAIN_FILE"
nohup python3 "$MAIN_FILE" > "$SCRIPT_DIR/bot.log" 2>&1 &

BOT_PID=$!
echo "$BOT_PID" > "$PID_FILE"
log_message "PID: $BOT_PID"

# Проверка
sleep 3
if ps -p "$BOT_PID" > /dev/null 2>&1; then
    log_message "Бот запущен"
    sleep 5
    if ps -p "$BOT_PID" > /dev/null 2>&1; then
        log_message "Бот работает стабильно"
    else
        log_message "Бот завершился после запуска"
        rm -f "$LOCK_FILE" "$PID_FILE"
        exit 1
    fi
else
    log_message "Ошибка запуска"
    rm -f "$LOCK_FILE" "$PID_FILE"
    exit 1
fi

log_message "Успешно завершено"
