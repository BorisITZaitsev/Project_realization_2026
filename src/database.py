"""
АИС «Налоговая инспекция» — модуль базы данных (SQLite)
"""
import sqlite3
import os
import shutil
import hashlib
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'tax.db')


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_connection()
    c = conn.cursor()

    # Справочник ОКВЭД
    c.execute('''CREATE TABLE IF NOT EXISTS ОКВЭД (
        КодОКВЭД   INTEGER PRIMARY KEY AUTOINCREMENT,
        Код        TEXT NOT NULL UNIQUE,
        Наименование TEXT NOT NULL,
        Архивный   INTEGER NOT NULL DEFAULT 0
    )''')

    # Юридические лица
    c.execute('''CREATE TABLE IF NOT EXISTS ЮрЛица (
        КодЮрЛица              INTEGER PRIMARY KEY AUTOINCREMENT,
        ПолноеНаименование     TEXT NOT NULL,
        ЮридическийАдрес       TEXT NOT NULL,
        ПочтовыйАдрес          TEXT,
        ДатаРегистрации        TEXT NOT NULL,
        ИНН                    TEXT NOT NULL UNIQUE,
        КПП                    TEXT,
        БИК                    TEXT,
        РасчетныйСчет          TEXT,
        КорпоративныйСчет      TEXT,
        ОКПО                   TEXT,
        ОКАДО                  TEXT,
        ГенеральныйДиректор    TEXT,
        Email                  TEXT,
        Телефон                TEXT,
        Сайт                   TEXT,
        ЕстьЗадолженность      INTEGER NOT NULL DEFAULT 0,
        Архивный               INTEGER NOT NULL DEFAULT 0
    )''')

    # Связь ЮрЛица — ОКВЭД (M:N)
    c.execute('''CREATE TABLE IF NOT EXISTS ЮрЛицо_ОКВЭД (
        КодСвязи   INTEGER PRIMARY KEY AUTOINCREMENT,
        КодЮрЛица  INTEGER NOT NULL,
        КодОКВЭД   INTEGER NOT NULL,
        Основной   INTEGER NOT NULL DEFAULT 0,
        UNIQUE(КодЮрЛица, КодОКВЭД),
        FOREIGN KEY (КодЮрЛица) REFERENCES ЮрЛица(КодЮрЛица),
        FOREIGN KEY (КодОКВЭД)  REFERENCES ОКВЭД(КодОКВЭД)
    )''')

    # Пользователи
    c.execute('''CREATE TABLE IF NOT EXISTS Пользователи (
        КодПользователя INTEGER PRIMARY KEY AUTOINCREMENT,
        Логин           TEXT NOT NULL UNIQUE,
        ПарольХэш       TEXT NOT NULL,
        Роль            TEXT NOT NULL DEFAULT 'оператор',
        Активен         INTEGER NOT NULL DEFAULT 1
    )''')

    conn.commit()

    # Создать admin по умолчанию если нет
    row = c.execute("SELECT COUNT(*) FROM Пользователи").fetchone()[0]
    if row == 0:
        c.execute("INSERT INTO Пользователи(Логин,ПарольХэш,Роль) VALUES (?,?,?)",
                  ('admin', hash_password('admin'), 'администратор'))
        c.execute("INSERT INTO Пользователи(Логин,ПарольХэш,Роль) VALUES (?,?,?)",
                  ('operator', hash_password('operator'), 'оператор'))
        conn.commit()

    # Несколько базовых ОКВЭД
    sample_okved = [
        ('47.11', 'Торговля розничная преимущественно пищевыми продуктами'),
        ('62.01', 'Разработка компьютерного программного обеспечения'),
        ('41.20', 'Строительство жилых и нежилых зданий'),
        ('56.10', 'Деятельность ресторанов и услуги по доставке питания'),
        ('49.41', 'Перевозка грузов специализированными автотранспортными средствами'),
        ('68.20', 'Аренда и управление собственным или арендованным недвижимым имуществом'),
        ('85.11', 'Образование дошкольное'),
        ('86.10', 'Деятельность больничных организаций'),
        ('64.19', 'Денежное посредничество прочее'),
        ('46.90', 'Торговля оптовая неспециализированная'),
    ]
    for code, name in sample_okved:
        c.execute("INSERT OR IGNORE INTO ОКВЭД(Код,Наименование) VALUES (?,?)", (code, name))

    conn.commit()
    conn.close()


def backup_db():
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = os.path.join(os.path.dirname(DB_PATH), '..', 'backup')
    os.makedirs(backup_dir, exist_ok=True)
    dest = os.path.join(backup_dir, f'tax_backup_{ts}.db')
    shutil.copy2(DB_PATH, dest)
    return dest
