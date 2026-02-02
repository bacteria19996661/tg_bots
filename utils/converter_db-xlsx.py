import sqlite3
import pandas as pd
import os
from datetime import datetime

import signal
import sys


# Таймаут 1 минута
def timeout_handler(signum, frame):
    print("Превышено время выполнения скрипта")
    sys.exit(1)


signal.signal(signal.SIGABRT, timeout_handler)


def quick_sqlite_to_excel(db_path, excel_path):
    """
    Экспорт таблиц из SQLite в Excel
    """
    try:
        if os.path.exists(excel_path):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{excel_path}.backup_{timestamp}"
            os.rename(excel_path, backup_path)
            print(f"Создана резервная копия: {backup_path}")

        # Подключение к DB
        conn = sqlite3.connect(db_path)

        # Получает список таблиц
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [table[0] for table in cursor.fetchall()]

        # Экспортирует таблицы
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            for table in tables:
                df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
                df.to_excel(writer, sheet_name=table, index=False)
                print(f"Экспортирована таблица: {table} ({len(df)} записей)")

        conn.close()
        print(f"Экспорт завершен: {excel_path}")

    except Exception as e:
        print(f"Ошибка экспорта: {e}")


if __name__ == "__main__":
    # База данных находится на директорию выше (в корне проекта)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)  # Поднимаемся на уровень выше
    db_file = os.path.join(parent_dir, "database.db")
    excel_file = os.path.join(current_dir, "database.xlsx")

    print(f"Ищем базу данных: {db_file}")
    print(f"Сохраняем Excel в: {excel_file}")

    quick_sqlite_to_excel(db_file, excel_file)
