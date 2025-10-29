from peewee import (
    AutoField,
    CharField,
    DateTimeField,
    ForeignKeyField,
    IntegerField,
    Model,
    SqliteDatabase,
    SQL,
    TextField
)
from datetime import datetime

from config_data.config import DATE_FORMAT, DB_PATH
import os
import logging


# Логгер для модуля
logger = logging.getLogger(__name__)


# Создаем директорию для DB, если нет
db_dir = os.path.dirname(DB_PATH)
if db_dir and not os.path.exists(db_dir):
    os.makedirs(db_dir)
    logger.info(f"Создана директория для DB: {db_dir}")

db = SqliteDatabase(DB_PATH)


class BaseModel(Model):
    class Meta:
        database = db


# Таблицы для ТГ-бота
class User(BaseModel):
    user_id = IntegerField(primary_key=True)
    username = CharField(null=True)
    first_name = CharField()
    last_name = CharField(null=True)


class Date(BaseModel):
    # date_id = AutoField(primary_key=True)    # Идентификаторы не создаются, если были удалены записи
    date_id = IntegerField(primary_key=True, constraints=[SQL('AUTOINCREMENT')])
    user = ForeignKeyField(User, backref="dates")
    title = CharField()
    description = CharField()
    due_date = DateTimeField(default=datetime.now().replace(microsecond=0))

    def __str__(self):
        return "{date_id}. {title} - {due_date}".format(
            date_id=self.date_id,
            title=self.title,
            due_date=self.due_date.strftime(DATE_FORMAT)
        )


# Таблица для заказа из ТГ-бота
class Orders(BaseModel):
    order_id = AutoField(primary_key=True)
    user = ForeignKeyField(User, backref="orders")
    phone = CharField(max_length=20)
    name = CharField(max_length=100)
    service_type = CharField(max_length=100, null=True)  # Услуга
    comment = TextField(null=True)  # Комментарий
    created_date = DateTimeField(default=datetime.now().replace(microsecond=0))

    def __str__(self):
        return f"Заявка #{self.order_id} от {self.name}"


# Таблицы для студии йоги
class Menu(BaseModel):
    menu_id = IntegerField(primary_key=True)
    menu_title = CharField(max_length=50)
    menu_description = TextField()


class Programs(BaseModel):
    program_id = IntegerField(primary_key=True)
    multiple_menu_ids = CharField(max_length=50, null=True)
    menu = ForeignKeyField(Menu, backref='programs', on_delete='CASCADE')
    program_title = CharField(max_length=200)
    program_description = TextField()
    program_duration = CharField(max_length=100)
    program_price = CharField(max_length=50)


class Price(BaseModel):
    price_id = IntegerField(primary_key=True)
    menu = ForeignKeyField(Menu, backref='prices', on_delete='CASCADE')
    price_title = CharField(max_length=100)
    price_description = TextField()


class PriceDetail(BaseModel):
    price_detail_id = IntegerField(primary_key=True)
    price = ForeignKeyField(Price, backref='details', on_delete='CASCADE')
    price_detail_title = CharField(max_length=100)
    price_detail_description = TextField()
    price_detail_duration = CharField(max_length=50)
    price_detail_price = CharField(max_length=50)


class Contacts(BaseModel):
    contacts_id = IntegerField(primary_key=True)
    menu = ForeignKeyField(Menu, backref='contacts', on_delete='CASCADE')
    contacts_title = CharField(max_length=20)
    contacts_description = CharField(max_length=200)


class Events(BaseModel):
    event_id = IntegerField(primary_key=True)
    menu = ForeignKeyField(Menu, backref='events', on_delete='CASCADE')
    event_title = CharField(max_length=200)
    event_description = TextField()
    event_duration = CharField(max_length=100)
    event_price = CharField(max_length=50)


class Mentors(BaseModel):
    mentor_id = IntegerField(primary_key=True)
    menu = ForeignKeyField(Menu, backref='mentors', on_delete='CASCADE')
    mentor_title = CharField(max_length=100)
    mentor_description = TextField()


class Retreats(BaseModel):
    retreat_id = IntegerField(primary_key=True)
    menu = ForeignKeyField(Menu, backref='retreats', on_delete='CASCADE')
    retreat_title = CharField(max_length=100)
    retreat_description = TextField()


class Reviews(BaseModel):
    review_id = IntegerField(primary_key=True)
    menu = ForeignKeyField(Menu, backref='reviews', on_delete='CASCADE')
    img_link = TextField()


class FAQ(BaseModel):
    faq_id = IntegerField(primary_key=True)
    menu = ForeignKeyField(Menu, backref='faqs', on_delete='CASCADE')
    question = TextField()
    answer = TextField()


def create_tables():
    """Создает таблицы в базе данных, если они не существуют"""
    try:
        with db:
            models = [
                User, Date, Orders, Menu, Price, PriceDetail, Contacts, Events,
                Mentors, Retreats, Reviews, Programs, FAQ
            ]
            db.create_tables(models, safe=True)
            logging.info("Таблицы базы данных проверены/созданы")
    except Exception as e:
        logger.error(f"Ошибка при создании таблиц DB: {e}")
        raise


def init_database():
    """Инициализация базы данных - только создание таблиц"""
    logging.info(f"Инициализация DB: {DB_PATH}")

    # Проверяем существует ли файл базы данных
    db_exists = os.path.exists(DB_PATH)

    if db_exists:
        logging.info(f"Подключение к существующей DB")
    else:
        logging.info("Создание новой DB")

    # Только создаем таблицы, не заполняем данными
    create_tables()


# При импорте модуля только создаем таблицы
if __name__ != "__main__":
    init_database()
