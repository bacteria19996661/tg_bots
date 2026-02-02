import json
import time
from datetime import datetime, timedelta
from typing import Dict
import re

from config_data.config import SCHEDULE_FILE_PATH

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec


URL = "https://yogita.ru/#schedule"


class YogitaScheduleParser:
    def __init__(self, headless=True):
        options = Options()
        if headless:
            options.add_argument("--headless=new")

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")

        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 30)

    def load_page(self):
        self.driver.get(URL)
        time.sleep(5)

        self.wait.until(ec.presence_of_element_located((By.TAG_NAME, "iframe")))
        iframe = self.driver.find_element(By.TAG_NAME, "iframe")
        self.driver.switch_to.frame(iframe)

        self.wait.until(
            ec.presence_of_element_located((By.CLASS_NAME, "mf-schedule-cell"))
        )

    def get_week_dates(self) -> list[str]:
        """
        Возвращает список ISO-дат:
        index 0 → ПН, 1 → ВТ, ...
        """
        ths = self.driver.find_elements(By.CSS_SELECTOR, "thead th")[1:]

        raw_dates = []
        for th in ths:
            try:
                raw = th.find_element(By.CSS_SELECTOR, "div.ng-binding").text.strip()
            except:
                raw = ""
            raw_dates.append(raw)

        # Если даты есть в TH
        for raw in raw_dates:
            m = re.search(r"(\d{2})/(\d{2})", raw)
            if m:
                day, month = map(int, m.groups())
                year = datetime.now().year
                monday = datetime(year, month, day)
                break
        else:
            monday = datetime.now()

        # Расчет недели
        week_dates = [
            (monday + timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(len(raw_dates))
        ]

        return week_dates

    def parse_week(self, week_number: int) -> list[dict]:
        week_dates = self.get_week_dates()
        activities = []

        rows = self.driver.find_elements(By.CSS_SELECTOR, "tbody tr")

        for row in rows:
            tds = row.find_elements(By.XPATH, "./td")

            if len(tds) < 2:
                continue

            # td[0] — время, игнор
            for day_index, td in enumerate(tds[1:]):
                if day_index >= len(week_dates):
                    continue

                date_iso = week_dates[day_index]

                cells = td.find_elements(By.CLASS_NAME, "mf-schedule-cell")

                for cell in cells:
                    title = cell.find_element(
                        By.CSS_SELECTOR,
                        ".mf-widget-cell-title .ng-binding"
                    ).text

                    times = cell.find_elements(
                        By.CSS_SELECTOR,
                        ".mf-widget-cell-time .ng-binding"
                    )

                    trainers = cell.find_elements(
                        By.CSS_SELECTOR,
                        ".mf-widget-cell-train .ng-binding"
                    )

                    activities.append({
                        "week": week_number,
                        "date": date_iso,
                        "title": title,
                        "start_time": times[0].text if len(times) >= 2 else "",
                        "end_time": times[1].text if len(times) >= 2 else "",
                        "trainers": [t.text for t in trainers],
                    })

        return activities

    def switch_to_next_week(self):
        btn = self.wait.until(
            ec.element_to_be_clickable(
                (By.CSS_SELECTOR, ".mf-widget-period a.fa-chevron-right")
            )
        )
        self.driver.execute_script("arguments[0].click();", btn)

        self.wait.until(
            ec.presence_of_element_located((By.CLASS_NAME, "mf-schedule-cell"))
        )
        time.sleep(1)

    def normalize_date(self, raw: str) -> str:
        """
        Форматирование даты из 'пн. 22/12' в '2025-12-22'
        """
        match = re.search(r'(\d{2})/(\d{2})', raw)
        if not match:
            return ""

        day, month = match.groups()
        year = datetime.now().year
        return f"{year}-{month}-{day}"

    def run(self, weeks=2) -> Dict:
        self.load_page()

        all_activities = []

        for week in range(1, weeks + 1):
            print(f"Парсинг недели {week}")
            week_data = self.parse_week(week)
            print(f"найдено: {len(week_data)}")
            all_activities.extend(week_data)

            if week < weeks:
                self.switch_to_next_week()

        self.driver.quit()

        return {
            "timestamp": datetime.now().isoformat(),
            "source": URL,
            "total": len(all_activities),
            "activities": all_activities,
        }


# def save_schedule_to_file(data: Dict):
#     """Сохраняет расписание в корень проекта"""
#     file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "yogita_schedule.json")
#
#     with open(file_path, "w", encoding="utf-8") as f:
#         json.dump(data, f, ensure_ascii=False, indent=2)
#
#     print(f"Файл сохранен: {file_path}")
#     return file_path

def save_schedule_to_file(data: Dict):
    """Сохраняет расписание в файл, используя путь из конфига"""
    with open(SCHEDULE_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Файл сохранен: {SCHEDULE_FILE_PATH}")
    return SCHEDULE_FILE_PATH


if __name__ == "__main__":
    parser = YogitaScheduleParser(headless=True)
    result = parser.run(weeks=2)

    save_schedule_to_file(result)

    print(f"ПАРСИНГ ЗАВЕРШЕН. Найдено занятий: {result['total']}")
