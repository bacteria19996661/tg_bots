#!/usr/bin/env python3
"""
Скрипт для установки зависимостей проекта на хостинге Beget
Устанавливает точные версии пакетов по одному
"""
import subprocess
import sys
import os
import platform


def install_packages_individually():
    """Установка зависимостей по одному с точными версиями"""
    print("Установка зависимостей по одному...")

    # Точные версии пакетов для совместимости
    packages = [
        "pyTelegramBotAPI==4.14.0",
        "python-dotenv==1.0.0",
        "peewee==3.17.0",
        "pymysql==1.0.2",
        "requests==2.31.0",
        "pyTelegramBotAPI==4.15.2",
        "PyMySQL==1.1.0"
    ]

    success_count = 0

    for package in packages:
        try:
            print(f"Установка {package}...")

            # Сначала пытаемся удалить существующую версию (если есть)
            try:
                subprocess.run([
                    sys.executable, "-m", "pip", "uninstall", "--user", "-y",
                    package.split('==')[0]
                ], capture_output=True, check=False)
            except:
                pass

            # Устанавливаем точную версию
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "--user", package
            ])

            print(f"{package} установлен")
            success_count += 1

        except subprocess.CalledProcessError as e:
            print(f"Не удалось установить {package}: {e}")

    return success_count == len(packages)


def install_requirements():
    """Установка зависимостей - сначала пробуем requirements.txt, потом по одному"""

    # Проверяем существование requirements.txt
    requirements_file = "requirements.txt"
    requirements_abs_path = "/home/b/bac/public_html/yogita_bot/requirements.txt"

    # Пробуем разные пути
    if os.path.exists(requirements_file):
        requirements_path = requirements_file
    elif os.path.exists(requirements_abs_path):
        requirements_path = requirements_abs_path
    else:
        print("Файл requirements.txt не найден, устанавливаем пакеты по одному")
        return install_packages_individually()

    print(f"Найден requirements.txt: {requirements_path}")

    try:
        # Обновляем pip (для пользователя)
        print("Обновление pip...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "--user", "--upgrade", "pip"
        ])

        # Устанавливаем зависимости из requirements.txt
        print("Установка из requirements.txt...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "--user", "-r", requirements_path
        ])

        print("Все зависимости установлены из requirements.txt")
        return True

    except subprocess.CalledProcessError as e:
        print(f"Ошибка при установке из requirements.txt: {e}")
        print("Пробуем установить пакеты по одному...")
        return install_packages_individually()


def install_playwright_browsers():
    """Установка браузеров для Playwright"""
    print("Пропускаем установку Playwright браузеров на shared хостинге")
    return True


def check_python_version():
    """Проверка версии Python"""
    print(f"Версия Python: {platform.python_version()}")

    version_tuple = sys.version_info
    if version_tuple < (3, 7):
        print("Требуется Python 3.7 или выше")
        return False
    else:
        print("Версия Python подходит")
        return True


def check_dependencies():
    """Проверка установленных зависимостей"""
    print("\nПроверка установленных зависимостей:")

    dependencies = {
        'telebot': 'pyTelegramBotAPI',
        'dotenv': 'python-dotenv',
        'peewee': 'peewee',
        'pymysql': 'pymysql',
        'requests': 'requests'
    }

    all_ok = True
    for import_name, package_name in dependencies.items():
        try:
            if import_name == 'telebot':
                import telebot
                version = getattr(telebot, '__version__', 'unknown')
            elif import_name == 'dotenv':
                from dotenv import load_dotenv
                version = 'loaded'
            elif import_name == 'peewee':
                import peewee
                version = peewee.__version__
            elif import_name == 'pymysql':
                import pymysql
                version = pymysql.__version__
            elif import_name == 'requests':
                import requests
                version = requests.__version__

            print(f"{package_name}: версия {version}")
        except ImportError as e:
            print(f"{package_name}: НЕ УСТАНОВЛЕН - {e}")
            all_ok = False

    return all_ok


def main():
    print("\nУстановка зависимостей для Telegram бота\n")

    # Проверка версии Python
    if not check_python_version():
        sys.exit(1)

    # Установка зависимостей
    if not install_requirements():
        print("Не удалось установить все зависимости")
        sys.exit(1)

    # Пропуск установки браузеров Playwright (не нужно на shared хостинге)
    install_playwright_browsers()

    # Проверка зависимостей
    if not check_dependencies():
        print("Не все зависимости установлены корректно")
        sys.exit(1)

    print("\nУстановка зависимостей завершена успешно!")
    print("Можно запустить бота: python main.py")


if __name__ == "__main__":
    main()