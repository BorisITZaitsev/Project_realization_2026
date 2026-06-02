"""
АИС «Налоговая инспекция» — модели данных (DAL)
"""
import re
from database import get_connection, hash_password


# ─────────────────── Аутентификация ───────────────────

def authenticate(login: str, password: str):
    """Возвращает словарь пользователя или None."""
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM Пользователи WHERE Логин=? AND ПарольХэш=? AND Активен=1",
            (login, hash_password(password))
        ).fetchone()


# ─────────────────── Пользователи ───────────────────

def get_users():
    with get_connection() as conn:
        return conn.execute(
            "SELECT КодПользователя,Логин,Роль,Активен FROM Пользователи ORDER BY Логин"
        ).fetchall()

def add_user(login, password, role):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO Пользователи(Логин,ПарольХэш,Роль) VALUES (?,?,?)",
            (login, hash_password(password), role)
        )

def update_user_password(user_id, new_password):
    with get_connection() as conn:
        conn.execute(
            "UPDATE Пользователи SET ПарольХэш=? WHERE КодПользователя=?",
            (hash_password(new_password), user_id)
        )

def toggle_user_active(user_id, active: bool):
    with get_connection() as conn:
        conn.execute(
            "UPDATE Пользователи SET Активен=? WHERE КодПользователя=?",
            (1 if active else 0, user_id)
        )

def change_role(user_id, role):
    with get_connection() as conn:
        conn.execute(
            "UPDATE Пользователи SET Роль=? WHERE КодПользователя=?",
            (role, user_id)
        )


# ─────────────────── ОКВЭД ───────────────────

def get_okved_list(include_archived=False):
    sql = "SELECT * FROM ОКВЭД"
    if not include_archived:
        sql += " WHERE Архивный=0"
    sql += " ORDER BY Код"
    with get_connection() as conn:
        return conn.execute(sql).fetchall()

def add_okved(code, name):
    code = code.strip()
    if not re.match(r'^\d{2}(\.\d{1,2})?(\.\d{1,2})?$', code):
        raise ValueError(f'Некорректный формат кода ОКВЭД: {code}')
    with get_connection() as conn:
        conn.execute("INSERT INTO ОКВЭД(Код,Наименование) VALUES (?,?)", (code, name))

def update_okved(okved_id, code, name):
    with get_connection() as conn:
        conn.execute("UPDATE ОКВЭД SET Код=?,Наименование=? WHERE КодОКВЭД=?",
                     (code, name, okved_id))

def archive_okved(okved_id):
    with get_connection() as conn:
        conn.execute("UPDATE ОКВЭД SET Архивный=1 WHERE КодОКВЭД=?", (okved_id,))


# ─────────────────── Валидация ───────────────────

def _validate_inn(inn: str):
    inn = inn.strip()
    if not inn.isdigit():
        raise ValueError('ИНН должен содержать только цифры')
    if len(inn) not in (10, 12):
        raise ValueError('ИНН должен содержать 10 или 12 цифр')
    return inn

def _validate_kpp(kpp: str):
    if not kpp:
        return kpp
    kpp = kpp.strip()
    if not kpp.isdigit() or len(kpp) != 9:
        raise ValueError('КПП должен содержать ровно 9 цифр')
    return kpp

def _validate_email(email: str):
    if not email:
        return email
    if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
        raise ValueError('Некорректный формат email')
    return email

def _validate_date(date_str: str):
    """Принимает ДД.ММ.ГГГГ, проверяет корректность и что не в будущем."""
    from datetime import datetime
    try:
        dt = datetime.strptime(date_str.strip(), '%d.%m.%Y')
    except ValueError:
        raise ValueError('Дата должна быть в формате ДД.ММ.ГГГГ')
    if dt > datetime.today():
        raise ValueError('Дата регистрации не может быть позже текущей даты')
    return date_str.strip()


# ─────────────────── Юридические лица ───────────────────

def get_entities(search='', search_by='all', include_archived=False):
    """
    search_by: 'all' | 'inn' | 'name' | 'address'
    """
    sql = '''SELECT л.КодЮрЛица, л.ПолноеНаименование, л.ИНН, л.КПП,
                    л.ЮридическийАдрес, л.ДатаРегистрации,
                    л.ГенеральныйДиректор, л.Телефон, л.Email,
                    л.ЕстьЗадолженность, л.Архивный
             FROM ЮрЛица л
             WHERE 1=1'''
    params = []
    if not include_archived:
        sql += ' AND л.Архивный=0'
    if search:
        if search_by == 'inn':
            sql += ' AND л.ИНН LIKE ?'
            params.append(f'%{search}%')
        elif search_by == 'name':
            sql += ' AND л.ПолноеНаименование LIKE ?'
            params.append(f'%{search}%')
        elif search_by == 'address':
            sql += ' AND л.ЮридическийАдрес LIKE ?'
            params.append(f'%{search}%')
        else:
            sql += ' AND (л.ИНН LIKE ? OR л.ПолноеНаименование LIKE ? OR л.ЮридическийАдрес LIKE ?)'
            params.extend([f'%{search}%'] * 3)
    sql += ' ORDER BY л.ПолноеНаименование'
    with get_connection() as conn:
        return conn.execute(sql, params).fetchall()

def get_entity(entity_id):
    with get_connection() as conn:
        return conn.execute("SELECT * FROM ЮрЛица WHERE КодЮрЛица=?", (entity_id,)).fetchone()

def add_entity(data: dict):
    data['ИНН'] = _validate_inn(data.get('ИНН', ''))
    if data.get('КПП'):
        data['КПП'] = _validate_kpp(data['КПП'])
    if data.get('Email'):
        data['Email'] = _validate_email(data['Email'])
    data['ДатаРегистрации'] = _validate_date(data.get('ДатаРегистрации', ''))

    with get_connection() as conn:
        conn.execute('''INSERT INTO ЮрЛица(
            ПолноеНаименование,ЮридическийАдрес,ПочтовыйАдрес,ДатаРегистрации,
            ИНН,КПП,БИК,РасчетныйСчет,КорпоративныйСчет,ОКПО,ОКАДО,
            ГенеральныйДиректор,Email,Телефон,Сайт,ЕстьЗадолженность)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
            data.get('ПолноеНаименование',''),
            data.get('ЮридическийАдрес',''),
            data.get('ПочтовыйАдрес',''),
            data['ДатаРегистрации'],
            data['ИНН'],
            data.get('КПП',''),
            data.get('БИК',''),
            data.get('РасчетныйСчет',''),
            data.get('КорпоративныйСчет',''),
            data.get('ОКПО',''),
            data.get('ОКАДО',''),
            data.get('ГенеральныйДиректор',''),
            data.get('Email',''),
            data.get('Телефон',''),
            data.get('Сайт',''),
            1 if data.get('ЕстьЗадолженность') else 0,
        ))
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

def update_entity(entity_id, data: dict):
    data['ИНН'] = _validate_inn(data.get('ИНН', ''))
    if data.get('КПП'):
        data['КПП'] = _validate_kpp(data['КПП'])
    if data.get('Email'):
        data['Email'] = _validate_email(data['Email'])
    data['ДатаРегистрации'] = _validate_date(data.get('ДатаРегистрации', ''))

    with get_connection() as conn:
        conn.execute('''UPDATE ЮрЛица SET
            ПолноеНаименование=?,ЮридическийАдрес=?,ПочтовыйАдрес=?,ДатаРегистрации=?,
            ИНН=?,КПП=?,БИК=?,РасчетныйСчет=?,КорпоративныйСчет=?,ОКПО=?,ОКАДО=?,
            ГенеральныйДиректор=?,Email=?,Телефон=?,Сайт=?,ЕстьЗадолженность=?
            WHERE КодЮрЛица=?''', (
            data.get('ПолноеНаименование',''),
            data.get('ЮридическийАдрес',''),
            data.get('ПочтовыйАдрес',''),
            data['ДатаРегистрации'],
            data['ИНН'],
            data.get('КПП',''),
            data.get('БИК',''),
            data.get('РасчетныйСчет',''),
            data.get('КорпоративныйСчет',''),
            data.get('ОКПО',''),
            data.get('ОКАДО',''),
            data.get('ГенеральныйДиректор',''),
            data.get('Email',''),
            data.get('Телефон',''),
            data.get('Сайт',''),
            1 if data.get('ЕстьЗадолженность') else 0,
            entity_id,
        ))

def archive_entity(entity_id):
    with get_connection() as conn:
        conn.execute("UPDATE ЮрЛица SET Архивный=1 WHERE КодЮрЛица=?", (entity_id,))


# ─────────────────── Связи ЮрЛицо–ОКВЭД ───────────────────

def get_entity_okved(entity_id):
    with get_connection() as conn:
        return conn.execute('''
            SELECT o.КодОКВЭД, o.Код, o.Наименование, lo.Основной
            FROM ЮрЛицо_ОКВЭД lo
            JOIN ОКВЭД o ON lo.КодОКВЭД=o.КодОКВЭД
            WHERE lo.КодЮрЛица=?
            ORDER BY lo.Основной DESC, o.Код
        ''', (entity_id,)).fetchall()

def add_entity_okved(entity_id, okved_id, is_main=False):
    with get_connection() as conn:
        if is_main:
            conn.execute("UPDATE ЮрЛицо_ОКВЭД SET Основной=0 WHERE КодЮрЛица=?", (entity_id,))
        conn.execute('''INSERT OR IGNORE INTO ЮрЛицо_ОКВЭД(КодЮрЛица,КодОКВЭД,Основной)
                        VALUES (?,?,?)''', (entity_id, okved_id, 1 if is_main else 0))

def remove_entity_okved(entity_id, okved_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM ЮрЛицо_ОКВЭД WHERE КодЮрЛица=? AND КодОКВЭД=?",
                     (entity_id, okved_id))

def get_entities_by_okved(okved_id):
    with get_connection() as conn:
        return conn.execute('''
            SELECT л.КодЮрЛица, л.ПолноеНаименование, л.ИНН,
                   л.ЮридическийАдрес, л.Телефон, lo.Основной
            FROM ЮрЛицо_ОКВЭД lo
            JOIN ЮрЛица л ON lo.КодЮрЛица=л.КодЮрЛица
            WHERE lo.КодОКВЭД=? AND л.Архивный=0
            ORDER BY л.ПолноеНаименование
        ''', (okved_id,)).fetchall()


# ─────────────────── Отчёты / аналитика ───────────────────

def get_debt_report():
    """Перечень организаций с задолженностью по сдаче отчётности."""
    with get_connection() as conn:
        return conn.execute('''
            SELECT л.КодЮрЛица, л.ПолноеНаименование, л.ИНН, л.КПП,
                   л.ЮридическийАдрес, л.Телефон, л.Email, л.ГенеральныйДиректор,
                   GROUP_CONCAT(o.Код, ', ') AS ОКВЭДы
            FROM ЮрЛица л
            LEFT JOIN ЮрЛицо_ОКВЭД lo ON л.КодЮрЛица=lo.КодЮрЛица
            LEFT JOIN ОКВЭД o ON lo.КодОКВЭД=o.КодОКВЭД
            WHERE л.ЕстьЗадолженность=1 AND л.Архивный=0
            GROUP BY л.КодЮрЛица
            ORDER BY л.ПолноеНаименование
        ''').fetchall()

def get_okved_stats():
    """Статистика по ОКВЭД: количество ЮрЛиц на каждый код."""
    with get_connection() as conn:
        return conn.execute('''
            SELECT o.Код, o.Наименование, COUNT(lo.КодЮрЛица) AS Количество
            FROM ОКВЭД o
            LEFT JOIN ЮрЛицо_ОКВЭД lo ON o.КодОКВЭД=lo.КодОКВЭД
            LEFT JOIN ЮрЛица л ON lo.КодЮрЛица=л.КодЮрЛица AND л.Архивный=0
            WHERE o.Архивный=0
            GROUP BY o.КодОКВЭД
            ORDER BY Количество DESC, o.Код
        ''').fetchall()

def get_total_stats():
    with get_connection() as conn:
        total   = conn.execute("SELECT COUNT(*) FROM ЮрЛица WHERE Архивный=0").fetchone()[0]
        debt    = conn.execute("SELECT COUNT(*) FROM ЮрЛица WHERE ЕстьЗадолженность=1 AND Архивный=0").fetchone()[0]
        okved_c = conn.execute("SELECT COUNT(*) FROM ОКВЭД WHERE Архивный=0").fetchone()[0]
        return total, debt, okved_c
