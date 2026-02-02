from config_data.config import API_LINK, CLIENT_ID, CLUB_ID, SCHEDULE_FILE_PATH

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urlparse, parse_qs

from datetime import datetime, timedelta
import time
import requests
import json
from pathlib import Path


def get_token():

    request_link_token = (
        f"{API_LINK}oauth/access_token"
        f"?response_type=token"
        f"&client_id={CLIENT_ID}"
        f"&client_type=2"
        f"&redirect_uri=https://google.com"
    )

    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    try:
        driver.get(request_link_token)

        try:
            WebDriverWait(driver, 15).until(
                lambda d: d.execute_script("return window.location.hash") != ""
            )
        except TimeoutException:
            pass

        time.sleep(2)

        fragment = driver.execute_script("return window.location.hash")
        params = parse_qs(fragment.lstrip("#"))

        token = params.get("access_token", [None])[0]
        base_host = params.get("base_host", [None])[0]

        if not token:
            print(f'Токен не получен.\nHASH: {fragment}')
            return None, None

        print(f'ACCESS_TOKEN: {token}\nBASE_HOST: {base_host}')

        return token, base_host

    finally:
        driver.quit()


def get_schedule(access_token, base_host):

    if not access_token or not base_host:
        print("Нет токена или base_host")
        return

    request_link_schedule = (
        f"https://{base_host}/api/v8/"
        f"club/{CLUB_ID}/schedule.json"
    )

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }

    response = requests.get(request_link_schedule, headers=headers, timeout=10)

    print("STATUS:", response.status_code)

    if response.status_code != 200:
        print(f'Ошибка: {response.status_code}\n{response.text}')
        return

    data = response.json()


def add_week_to_schedule(data: dict, week: int) -> dict:
    """
    Добавить week в каждый элемент schedule.
    """
    if "schedule" not in data or not isinstance(data["schedule"], list):
        raise ValueError("Ключ 'schedule' отсутствует или некорректен")

    for item in data["schedule"]:
        item["week"] = week

    return data


def parse_next_link(next_link: str) -> tuple[int, int]:
    """
    Извлечь year и week из next
    :return: возвращает параметры для запроса year, week
    """
    if not next_link:
        raise ValueError("Ключ 'next' отсутствует")

    parsed = urlparse(next_link)
    params = parse_qs(parsed.query)

    try:
        year = int(params["year"][0])
        week = int(params["week"][0])
    except (KeyError, IndexError, ValueError):
        raise ValueError(f"Не удалось извлечь year/week из next: {next_link}")

    return year, week


def get_schedule_by_week(access_token, base_host, year=None, week=None):
    """
    Запрос расписания с параметрами year/week.
    """

    url = f"https://{base_host}/api/v8/club/{CLUB_ID}/schedule.json"

    params = {}
    if year is not None:
        params["year"] = year
    if week is not None:
        params["week"] = week

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }

    response = requests.get(url, headers=headers, params=params, timeout=10)

    if response.status_code != 200:
        raise RuntimeError(
            f"Ошибка запроса расписания ({response.status_code}): {response.text}"
        )

    return response.json()


def collect_two_weeks_schedule(access_token, base_host, output_filename):
    """
    Объединение данных за две недели в один файл
    """

    # Первая неделя
    data_week_1 = get_schedule_by_week(access_token, base_host)
    data_week_1 = add_week_to_schedule(data_week_1, week=1)

    # Извлекаем next
    next_link = data_week_1.get("next")
    year, week_from_next = parse_next_link(next_link)

    # Вторая неделя
    data_week_2 = get_schedule_by_week(
        access_token,
        base_host,
        year=year,
        week=week_from_next
    )
    data_week_2 = add_week_to_schedule(data_week_2, week=2)

    # Объединение данных в один файл
    combined = {
        "meta": {
            "generatedAt": time.strftime("%Y-%m-%d %H:%M:%S"),
            "weeks": [1, 2]
        },
        "club": data_week_1.get("club"),
        "dateSince": data_week_1.get("dateSince"),
        "dateTo": data_week_2.get("dateTo"),
        "schedule": (
            data_week_1.get("schedule", [])
            + data_week_2.get("schedule", [])
        )
    }

    # Сохранение общего файла
    file_path = Path(__file__).parent / output_filename
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=4)

    print(f"Общий файл сохранён: {file_path}")
    return combined


def is_active(item: dict) -> bool:
    """
    Проверка «активности»
        Считается активным, если нет поля cancelled=True.
        Неактивным, если null / {} / [] → false. Если есть объект → рекурсивно приводим тем же методом
    """
    if item.get("cancelled") is True:
        return False
    return True


def parse_datetime(dt_str: str) -> datetime:
    return datetime.fromisoformat(dt_str)


def transform_schedule_item(item: dict) -> dict:
    """
    Преобразование одного занятия
    """
    dt = parse_datetime(item["datetime"])
    length = item.get("length", 0)

    start_time = dt.strftime("%H:%M")
    end_time = (dt + timedelta(minutes=length)).strftime("%H:%M")

    trainers = [
        t.get("title")
        for t in item.get("trainers", [])
        if t.get("title")
    ]

    transformed = {
        "week": item.get("week"),
        "date": dt.date().isoformat(),
        "title": item.get("activity", {}).get("title"),
        "length": length,
        "start_time": start_time,
        "end_time": end_time,
        "room": item.get("room", {}).get("title"),
        "trainers": trainers
    }

    # change
    change = item.get("change")
    if change:
        transformed["change"] = transform_schedule_item(change)
    else:
        transformed["change"] = False

    return transformed


def build_final_schedule_dict(combined_data: dict) -> dict:
    """
    Формирование json для дальнейшей обработки.
    """
    activities = []

    for item in combined_data.get("schedule", []):

        if not is_active(item):
            continue

        activities.append(transform_schedule_item(item))

    result = {
        "timestamp": datetime.now().isoformat(),
        "source": "api",
        "total": len(activities),
        "activities": activities
    }

    return result


def save_final_schedule(data: dict):
    """Сохраняет финальное расписание в файл, используя путь из конфига"""
    with open(SCHEDULE_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"Адаптированный json-файл сохранён: {SCHEDULE_FILE_PATH}")


if __name__ == "__main__":
    token, base_host = get_token()

    if not token or not base_host:
        raise RuntimeError("Не удалось получить токен или base_host")

    combined_data = collect_two_weeks_schedule(
        access_token=token,
        base_host=base_host,
        output_filename="schedule_api.json"  # Сохраняется промежуточный файл для контроля
    )

    final_data = build_final_schedule_dict(combined_data)
    save_final_schedule(final_data)  # Используется путь из конфига
