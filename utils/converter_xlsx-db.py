import pandas as pd
import sqlite3
import os

import signal
import sys


def get_protected_tables():
    """Список защищенных таблиц"""
    return ['sqlite_sequence', 'user', 'date', 'orders', 'news', 'newsstats']


def excel_to_sqlite(excel_file_path, db_file_path):
    """
    Конвертация Excel в SQLite с сохранением защищенных таблиц
    """
    try:
        excel_file = pd.ExcelFile(excel_file_path)

        conn = sqlite3.connect(db_file_path)
        print(f"Подключение к базе данных: {db_file_path}")

        protected_tables = get_protected_tables()

        # Список существующих таблиц в БД
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [table[0].lower() for table in cursor.fetchall()]

        print(f"Все таблицы: {existing_tables}"
              f"\nЗащищенные таблицы: {protected_tables}")

        for sheet_name in excel_file.sheet_names:
            table_name = sheet_name.lower()

            if sheet_name.lower() == 'sqlite_sequence':    # Пропускаем системные таблицы
                continue

            if table_name in protected_tables:    # Пропускаем защищенные таблицы
                continue

            df = pd.read_excel(excel_file, sheet_name=sheet_name)

            df = df.where(pd.notnull(df), None)    # Заменяет NaN на None для корректной работы с SQLite

            # Сохраняет в SQLite с заменой существующей таблицы
            df.to_sql(table_name, conn, if_exists='replace', index=False)

        conn.close()    # Закрывает соединение
        print("Конвертация Excel в SQLite завершена")

    except Exception as e:
        print(f"Ошибка при конвертации: {e}")


def verify_database(db_file_path):
    """
    Проверяет содержимое базы данных после миграции
    """
    conn = sqlite3.connect(db_file_path)
    cursor = conn.cursor()

    try:
        # Получает список таблиц, кроме системных
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            AND name != 'sqlite_sequence'
        """)
        tables = cursor.fetchall()

        print("\nПроверка базы данных:")

        protected_tables = get_protected_tables()

        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]

            status = "ЗАЩИЩЕНА" if table_name in protected_tables else "обновлена"
            print(f"Таблица {table_name}, записей {count} - {status}")

            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            # print(f"Колонки: {[col[1] for col in columns]}")

    except Exception as e:
        print(f"Ошибка при проверке: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    excel_file = os.path.join(current_dir, "database.xlsx")

    # База в корне проекта (на уровень выше utils)
    parent_dir = os.path.dirname(current_dir)  # Поднимаемся на уровень выше
    db_file = os.path.join(parent_dir, "database.db")

    print(f"Рабочая директория: {current_dir}"
          f"\nExcel файл: {excel_file}"
          f"\nSQLite база: {db_file}\n")

    if not os.path.exists(excel_file):
        print(f"Ошибка: Файл {excel_file} не найден")
        exit(1)

    if not os.path.exists(db_file):
        print(f"Ошибка: База данных {db_file} не найдена")
        exit(1)

    excel_to_sqlite(excel_file, db_file)
    verify_database(db_file)
