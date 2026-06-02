"""
АИС «Налоговая инспекция» — главное окно (tkinter)
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime
import sys, os

sys.path.insert(0, os.path.dirname(__file__))
import database
import models
import reports

database.init_db()

# ══════════════════ Стили ══════════════════

C = {
    'bg': '#F2F5F9',
    'header': '#1B3B6F',
    'accent': '#2563AB',
    'danger': '#B91C1C',
    'ok': '#15803D',
    'row_debt': '#FEE2E2',
    'row_arch': '#F3F4F6',
}

CURRENT_USER = {'login': None, 'role': None}


def configure_styles():
    s = ttk.Style()
    s.theme_use('clam')
    s.configure('Treeview', font=('Arial', 10), rowheight=24,
                background='white', fieldbackground='white')
    s.configure('Treeview.Heading', font=('Arial', 10, 'bold'),
                background=C['header'], foreground='white')
    s.map('Treeview', background=[('selected', C['accent'])],
          foreground=[('selected', 'white')])
    s.configure('TButton', font=('Arial', 9), padding=4)
    s.configure('TNotebook.Tab', font=('Arial', 10), padding=(10, 4))
    s.configure('TLabelframe.Label', font=('Arial', 10, 'bold'), foreground=C['header'])


def is_admin():
    return CURRENT_USER['role'] == 'администратор'


# ══════════════════ Вспомогательные функции ══════════════════

def lbl_entry(parent, text, row, default='', width=32, tooltip=''):
    ttk.Label(parent, text=text).grid(row=row, column=0, sticky='e', padx=6, pady=3)
    var = tk.StringVar(value=default)
    e = ttk.Entry(parent, textvariable=var, width=width)
    e.grid(row=row, column=1, sticky='ew', padx=6, pady=3)
    if tooltip:
        _add_tooltip(e, tooltip)
    return var


def _add_tooltip(widget, text):
    tip = None
    def enter(e):
        nonlocal tip
        x = widget.winfo_rootx() + 20
        y = widget.winfo_rooty() + 24
        tip = tk.Toplevel(widget)
        tip.wm_overrideredirect(True)
        tip.wm_geometry(f'+{x}+{y}')
        tk.Label(tip, text=text, background='#FFFBD6', relief='solid',
                 borderwidth=1, font=('Arial', 9), wraplength=260).pack()
    def leave(e):
        nonlocal tip
        if tip:
            tip.destroy()
            tip = None
    widget.bind('<Enter>', enter)
    widget.bind('<Leave>', leave)


def scrolled_tree(parent, cols, widths=None, height=14):
    frame = ttk.Frame(parent)
    tree = ttk.Treeview(frame, columns=cols, show='headings',
                        selectmode='browse', height=height)
    vsb = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
    hsb = ttk.Scrollbar(frame, orient='horizontal', command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    tree.grid(row=0, column=0, sticky='nsew')
    vsb.grid(row=0, column=1, sticky='ns')
    hsb.grid(row=1, column=0, sticky='ew')
    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)
    for i, c in enumerate(cols):
        tree.heading(c, text=c)
        w = (widths[i] if widths and i < len(widths) else 120)
        tree.column(c, width=w)
    tree.tag_configure('debt', background=C['row_debt'])
    tree.tag_configure('arch', background=C['row_arch'], foreground='#888')
    return frame, tree


# ══════════════════ Диалог входа ══════════════════

class LoginDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title('Вход в систему')
        self.grab_set()
        self.resizable(False, False)
        self.result = None
        self.protocol('WM_DELETE_WINDOW', self._cancel)

        f = ttk.Frame(self, padding=20)
        f.pack()

        ttk.Label(f, text='АИС «Налоговая инспекция»',
                  font=('Arial', 13, 'bold'), foreground=C['header']).grid(
            row=0, column=0, columnspan=2, pady=(0, 14))

        self.login_var = lbl_entry(f, 'Логин:', 1, tooltip='Введите логин пользователя')
        self.pass_var = lbl_entry(f, 'Пароль:', 2, tooltip='Введите пароль')
        ttk.Entry(f, textvariable=self.pass_var, show='*', width=32).grid(
            row=2, column=1, sticky='ew', padx=6, pady=3)
        # Перезаписываем обычный entry на скрытый
        for w in f.grid_slaves(row=2, column=1):
            w.destroy()
        e = ttk.Entry(f, textvariable=self.pass_var, show='*', width=32)
        e.grid(row=2, column=1, sticky='ew', padx=6, pady=3)
        e.bind('<Return>', lambda ev: self._login())

        bf = ttk.Frame(f)
        bf.grid(row=3, column=0, columnspan=2, pady=10)
        ttk.Button(bf, text='Войти', command=self._login).pack(side='left', padx=6)
        ttk.Button(bf, text='Отмена', command=self._cancel).pack(side='left')

    def _login(self):
        user = models.authenticate(self.login_var.get(), self.pass_var.get())
        if user:
            self.result = dict(user)
            self.destroy()
        else:
            messagebox.showerror('Ошибка', 'Неверный логин или пароль', parent=self)
            self.pass_var.set('')

    def _cancel(self):
        self.result = None
        self.destroy()


# ══════════════════ Форма ЮрЛица ══════════════════

class EntityDialog(tk.Toplevel):
    def __init__(self, parent, entity=None, readonly=False):
        super().__init__(parent)
        self.title('Просмотр юридического лица' if readonly
                   else ('Добавить ЮрЛицо' if entity is None else 'Редактировать ЮрЛицо'))
        self.grab_set()
        self.geometry('640x580')
        self.resizable(True, True)
        self.result = None

        nb = ttk.Notebook(self)
        nb.pack(fill='both', expand=True, padx=8, pady=6)

        # Вкладка 1: Основные данные
        f1 = ttk.Frame(nb, padding=8)
        nb.add(f1, text='  Основные реквизиты  ')
        f1.columnconfigure(1, weight=1)

        e = entity
        st = 'readonly' if readonly else 'normal'

        self.vars = {}
        fields = [
            ('ПолноеНаименование', 'Полное наименование:', 'До 64 символов'),
            ('ИНН',                'ИНН:', '10 или 12 цифр'),
            ('КПП',                'КПП:', '9 цифр'),
            ('ОКПО',               'ОКПО:', '8 цифр'),
            ('ОКАДО',              'ОКАДО:', 'До 16 цифр'),
            ('ДатаРегистрации',    'Дата регистрации:', 'ДД.ММ.ГГГГ'),
            ('ЮридическийАдрес',   'Юридический адрес:', 'До 128 символов'),
            ('ПочтовыйАдрес',      'Почтовый адрес:', 'До 128 символов'),
            ('ГенеральныйДиректор','Генеральный директор:', 'ФИО'),
            ('Телефон',            'Телефон:', '+7 (XXX) XXX-XX-XX'),
            ('Email',              'Email:', 'example@mail.ru'),
            ('Сайт',               'Сайт:', 'https://...'),
        ]
        for row_i, (key, label, tip) in enumerate(fields):
            ttk.Label(f1, text=label).grid(row=row_i, column=0, sticky='e', padx=6, pady=2)
            var = tk.StringVar(value=e[key] if e and e[key] else '')
            en = ttk.Entry(f1, textvariable=var, width=38, state=st)
            en.grid(row=row_i, column=1, sticky='ew', padx=6, pady=2)
            _add_tooltip(en, tip)
            self.vars[key] = var

        # Задолженность
        self.debt_var = tk.BooleanVar(value=bool(e['ЕстьЗадолженность']) if e else False)
        cb = ttk.Checkbutton(f1, text='Есть задолженность по отчётности',
                             variable=self.debt_var, state=st)
        cb.grid(row=len(fields), column=1, sticky='w', padx=6, pady=4)

        # Вкладка 2: Банковские реквизиты
        f2 = ttk.Frame(nb, padding=8)
        nb.add(f2, text='  Банк  ')
        f2.columnconfigure(1, weight=1)
        bank_fields = [
            ('БИК',                'БИК:', 'Банковский идентификационный код'),
            ('РасчетныйСчет',      'Расчётный счёт:', '20 цифр'),
            ('КорпоративныйСчет',  'Корпоративный счёт:', '20 цифр'),
        ]
        for row_i, (key, label, tip) in enumerate(bank_fields):
            ttk.Label(f2, text=label).grid(row=row_i, column=0, sticky='e', padx=6, pady=4)
            var = tk.StringVar(value=e[key] if e and e[key] else '')
            en = ttk.Entry(f2, textvariable=var, width=38, state=st)
            en.grid(row=row_i, column=1, sticky='ew', padx=6, pady=4)
            _add_tooltip(en, tip)
            self.vars[key] = var

        # Вкладка 3: ОКВЭД (только для существующих записей)
        if e and not readonly:
            self._entity_id = e['КодЮрЛица']
            f3 = ttk.Frame(nb, padding=8)
            nb.add(f3, text='  ОКВЭД  ')
            self._build_okved_tab(f3)
        elif e and readonly:
            self._entity_id = e['КодЮрЛица']
            f3 = ttk.Frame(nb, padding=8)
            nb.add(f3, text='  ОКВЭД  ')
            self._build_okved_tab(f3, readonly=True)

        if not readonly:
            bf = ttk.Frame(self)
            bf.pack(fill='x', padx=8, pady=6)
            ttk.Button(bf, text='💾 Сохранить', command=self._save).pack(side='right', padx=4)
            ttk.Button(bf, text='Отмена', command=self.destroy).pack(side='right')

    def _build_okved_tab(self, parent, readonly=False):
        frm, tree = scrolled_tree(parent,
                                   ('Код', 'Наименование', 'Основной'),
                                   (80, 380, 80), height=8)
        frm.pack(fill='both', expand=True)
        self._okved_tree = tree

        def load():
            tree.delete(*tree.get_children())
            for r in models.get_entity_okved(self._entity_id):
                tree.insert('', 'end', iid=r['КодОКВЭД'],
                            values=(r['Код'], r['Наименование'],
                                    'Да' if r['Основной'] else ''))

        load()
        if not readonly:
            bf = ttk.Frame(parent)
            bf.pack(fill='x', pady=4)
            ttk.Button(bf, text='+ Добавить ОКВЭД', command=lambda: self._add_okved(load)).pack(side='left', padx=3)
            ttk.Button(bf, text='✕ Удалить', command=lambda: self._del_okved(tree, load)).pack(side='left', padx=3)

    def _add_okved(self, reload_fn):
        okved_list = models.get_okved_list()
        names = [f'{r["Код"]} — {r["Наименование"]}' for r in okved_list]
        id_map = {f'{r["Код"]} — {r["Наименование"]}': r['КодОКВЭД'] for r in okved_list}

        dlg = tk.Toplevel(self)
        dlg.title('Добавить ОКВЭД')
        dlg.grab_set()
        dlg.resizable(False, False)
        f = ttk.Frame(dlg, padding=12)
        f.pack()
        ttk.Label(f, text='Вид деятельности:').grid(row=0, column=0, sticky='e', padx=6)
        var = tk.StringVar()
        cb = ttk.Combobox(f, textvariable=var, values=names, state='readonly', width=50)
        cb.grid(row=0, column=1, padx=6, pady=4)
        is_main = tk.BooleanVar()
        ttk.Checkbutton(f, text='Основной вид деятельности', variable=is_main).grid(
            row=1, column=1, sticky='w', padx=6)
        res = [None]

        def ok():
            if var.get():
                res[0] = (id_map[var.get()], is_main.get())
            dlg.destroy()

        bf = ttk.Frame(f)
        bf.grid(row=2, column=0, columnspan=2, pady=8)
        ttk.Button(bf, text='OK', command=ok).pack(side='left', padx=4)
        ttk.Button(bf, text='Отмена', command=dlg.destroy).pack(side='left')
        dlg.wait_window()
        if res[0]:
            try:
                models.add_entity_okved(self._entity_id, res[0][0], res[0][1])
                reload_fn()
            except Exception as ex:
                messagebox.showerror('Ошибка', str(ex), parent=self)

    def _del_okved(self, tree, reload_fn):
        sel = tree.selection()
        if sel and messagebox.askyesno('', 'Удалить связь с ОКВЭД?', parent=self):
            models.remove_entity_okved(self._entity_id, int(sel[0]))
            reload_fn()

    def _save(self):
        data = {k: v.get().strip() for k, v in self.vars.items()}
        data['ЕстьЗадолженность'] = self.debt_var.get()
        if not data.get('ПолноеНаименование'):
            messagebox.showerror('Ошибка', 'Введите полное наименование', parent=self)
            return
        self.result = data
        self.destroy()


# ══════════════════ Панель ЮрЛиц ══════════════════

class EntitiesPanel(ttk.Frame):
    def __init__(self, parent, status_cb):
        super().__init__(parent)
        self._status = status_cb
        self._build()

    def _build(self):
        # Панель поиска
        sf = ttk.LabelFrame(self, text='Поиск', padding=6)
        sf.pack(fill='x', padx=6, pady=4)
        ttk.Label(sf, text='Запрос:').pack(side='left')
        self._search_var = tk.StringVar()
        self._search_var.trace('w', lambda *a: self._load())
        ttk.Entry(sf, textvariable=self._search_var, width=28).pack(side='left', padx=4)
        ttk.Label(sf, text='Поле:').pack(side='left', padx=(10, 2))
        self._field_var = tk.StringVar(value='all')
        for text, val in [('Все', 'all'), ('ИНН', 'inn'), ('Название', 'name'), ('Адрес', 'address')]:
            ttk.Radiobutton(sf, text=text, variable=self._field_var, value=val,
                            command=self._load).pack(side='left', padx=2)
        self._arch_var = tk.BooleanVar()
        ttk.Checkbutton(sf, text='Показать архивных', variable=self._arch_var,
                        command=self._load).pack(side='left', padx=10)

        # Панель кнопок
        tb = ttk.Frame(self)
        tb.pack(fill='x', padx=6, pady=2)
        ttk.Button(tb, text='➕ Добавить', command=self._add).pack(side='left', padx=2)
        ttk.Button(tb, text='✏ Изменить', command=self._edit).pack(side='left', padx=2)
        ttk.Button(tb, text='👁 Просмотр', command=self._view).pack(side='left', padx=2)
        ttk.Button(tb, text='🗑 В архив', command=self._archive).pack(side='left', padx=2)
        ttk.Separator(tb, orient='vertical').pack(side='left', fill='y', padx=6)
        ttk.Button(tb, text='🖨 Карточка', command=self._print_card).pack(side='left', padx=2)
        ttk.Button(tb, text='📋 По ОКВЭД…', command=self._by_okved).pack(side='left', padx=2)

        # Таблица
        cols = ('КодЮрЛица', 'Наименование', 'ИНН', 'КПП', 'Адрес',
                'Директор', 'Телефон', 'Дата рег.', 'Задолж.')
        widths = (55, 280, 110, 90, 220, 160, 130, 95, 70)
        frm, self.tree = scrolled_tree(self, cols, widths, height=18)
        frm.pack(fill='both', expand=True, padx=6, pady=4)
        self.tree.bind('<Double-1>', lambda e: self._view())
        self._load()

    def _load(self):
        self.tree.delete(*self.tree.get_children())
        rows = models.get_entities(
            search=self._search_var.get(),
            search_by=self._field_var.get(),
            include_archived=self._arch_var.get()
        )
        for r in rows:
            tag = 'debt' if r['ЕстьЗадолженность'] else ('arch' if r['Архивный'] else '')
            self.tree.insert('', 'end', iid=r['КодЮрЛица'],
                             values=(r['КодЮрЛица'],
                                     r['ПолноеНаименование'],
                                     r['ИНН'], r['КПП'] or '',
                                     r['ЮридическийАдрес'],
                                     r['ГенеральныйДиректор'] or '',
                                     r['Телефон'] or '',
                                     r['ДатаРегистрации'],
                                     '⚠ Да' if r['ЕстьЗадолженность'] else ''),
                             tags=(tag,))
        total, debt, _ = models.get_total_stats()
        self._status(f'Всего ЮрЛиц: {total}  |  Задолженностей: {debt}')

    def _selected_id(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def _add(self):
        if not is_admin() and CURRENT_USER['role'] != 'оператор':
            messagebox.showwarning('Доступ', 'Нет прав')
            return
        dlg = EntityDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            try:
                models.add_entity(dlg.result)
                self._load()
            except Exception as e:
                messagebox.showerror('Ошибка', str(e))

    def _edit(self):
        eid = self._selected_id()
        if not eid:
            return
        e = models.get_entity(eid)
        dlg = EntityDialog(self, entity=e)
        self.wait_window(dlg)
        if dlg.result:
            try:
                models.update_entity(eid, dlg.result)
                self._load()
            except Exception as ex:
                messagebox.showerror('Ошибка', str(ex))

    def _view(self):
        eid = self._selected_id()
        if eid:
            EntityDialog(self, entity=models.get_entity(eid), readonly=True)

    def _archive(self):
        eid = self._selected_id()
        if eid and messagebox.askyesno('Архивировать', 'Перенести запись в архив?'):
            models.archive_entity(eid)
            self._load()

    def _print_card(self):
        eid = self._selected_id()
        if eid:
            reports.print_entity_card(eid)
        else:
            messagebox.showinfo('', 'Выберите организацию')

    def _by_okved(self):
        okved_list = models.get_okved_list()
        names = [f'{r["Код"]} — {r["Наименование"]}' for r in okved_list]
        id_map = {f'{r["Код"]} — {r["Наименование"]}': r for r in okved_list}
        dlg = tk.Toplevel(self)
        dlg.title('Список ЮрЛиц по ОКВЭД')
        dlg.grab_set()
        dlg.geometry('780x450')
        f = ttk.Frame(dlg, padding=8)
        f.pack(fill='x')
        ttk.Label(f, text='ОКВЭД:').pack(side='left')
        var = tk.StringVar()
        cb = ttk.Combobox(f, textvariable=var, values=names, state='readonly', width=55)
        cb.pack(side='left', padx=6)

        cols = ('Наименование', 'ИНН', 'Адрес', 'Телефон', 'Осн.')
        widths = (280, 110, 230, 120, 60)
        frm, tree = scrolled_tree(dlg, cols, widths, height=14)
        frm.pack(fill='both', expand=True, padx=8, pady=4)

        def search(*a):
            tree.delete(*tree.get_children())
            if not var.get():
                return
            okv = id_map[var.get()]
            for r in models.get_entities_by_okved(okv['КодОКВЭД']):
                tree.insert('', 'end', values=(
                    r['ПолноеНаименование'], r['ИНН'],
                    r['ЮридическийАдрес'], r['Телефон'] or '',
                    'Да' if r['Основной'] else ''
                ))

        cb.bind('<<ComboboxSelected>>', search)

        def print_rep():
            if not var.get():
                return
            okv = id_map[var.get()]
            reports.print_entities_by_okved(okv['КодОКВЭД'], okv['Код'], okv['Наименование'])

        ttk.Button(dlg, text='🖨 Печать списка', command=print_rep).pack(pady=4)


# ══════════════════ Панель ОКВЭД ══════════════════

class OkvedPanel(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._build()

    def _build(self):
        tb = ttk.Frame(self)
        tb.pack(fill='x', padx=6, pady=4)
        if is_admin():
            ttk.Button(tb, text='➕ Добавить', command=self._add).pack(side='left', padx=2)
            ttk.Button(tb, text='✏ Изменить', command=self._edit).pack(side='left', padx=2)
            ttk.Button(tb, text='🗑 Архивировать', command=self._archive).pack(side='left', padx=2)
        ttk.Button(tb, text='🖨 Статистика', command=reports.print_okved_stats).pack(side='right', padx=2)

        cols = ('КодОКВЭД', 'Код', 'Наименование', 'Кол-во ЮрЛиц')
        frm, self.tree = scrolled_tree(self, cols, (60, 80, 480, 100), height=20)
        frm.pack(fill='both', expand=True, padx=6)
        self._load()

    def _load(self):
        self.tree.delete(*self.tree.get_children())
        stats = {r['Код']: r['Количество'] for r in models.get_okved_stats()}
        for r in models.get_okved_list(include_archived=True):
            cnt = stats.get(r['Код'], 0)
            tag = 'arch' if r['Архивный'] else ''
            self.tree.insert('', 'end', iid=r['КодОКВЭД'],
                             values=(r['КодОКВЭД'], r['Код'], r['Наименование'], cnt),
                             tags=(tag,))

    def _selected_id(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def _add(self):
        dlg = tk.Toplevel(self)
        dlg.title('Добавить ОКВЭД')
        dlg.grab_set()
        dlg.resizable(False, False)
        f = ttk.Frame(dlg, padding=12)
        f.pack()
        f.columnconfigure(1, weight=1)
        code_var = lbl_entry(f, 'Код:', 0, tooltip='Формат: XX.XX.XX', width=16)
        name_var = lbl_entry(f, 'Наименование:', 1, width=46)
        res = [None]

        def ok():
            if not code_var.get() or not name_var.get():
                messagebox.showerror('', 'Заполните все поля', parent=dlg)
                return
            res[0] = (code_var.get(), name_var.get())
            dlg.destroy()

        bf = ttk.Frame(f)
        bf.grid(row=2, column=0, columnspan=2, pady=8)
        ttk.Button(bf, text='Сохранить', command=ok).pack(side='left', padx=4)
        ttk.Button(bf, text='Отмена', command=dlg.destroy).pack(side='left')
        dlg.wait_window()
        if res[0]:
            try:
                models.add_okved(*res[0])
                self._load()
            except Exception as e:
                messagebox.showerror('Ошибка', str(e))

    def _edit(self):
        oid = self._selected_id()
        if not oid:
            return
        row = next((r for r in models.get_okved_list(True) if r['КодОКВЭД'] == oid), None)
        if not row:
            return
        dlg = tk.Toplevel(self)
        dlg.title('Редактировать ОКВЭД')
        dlg.grab_set()
        dlg.resizable(False, False)
        f = ttk.Frame(dlg, padding=12)
        f.pack()
        f.columnconfigure(1, weight=1)
        code_var = lbl_entry(f, 'Код:', 0, row['Код'], width=16)
        name_var = lbl_entry(f, 'Наименование:', 1, row['Наименование'], width=46)
        res = [None]

        def ok():
            res[0] = (code_var.get(), name_var.get())
            dlg.destroy()

        bf = ttk.Frame(f)
        bf.grid(row=2, column=0, columnspan=2, pady=8)
        ttk.Button(bf, text='Сохранить', command=ok).pack(side='left', padx=4)
        ttk.Button(bf, text='Отмена', command=dlg.destroy).pack(side='left')
        dlg.wait_window()
        if res[0]:
            try:
                models.update_okved(oid, *res[0])
                self._load()
            except Exception as e:
                messagebox.showerror('Ошибка', str(e))

    def _archive(self):
        oid = self._selected_id()
        if oid and messagebox.askyesno('', 'Архивировать запись?'):
            models.archive_okved(oid)
            self._load()


# ══════════════════ Панель Отчётов ══════════════════

class ReportsPanel(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._build()

    def _build(self):
        frm = ttk.Frame(self, padding=20)
        frm.pack(fill='both', expand=True)

        ttk.Label(frm, text='Доступные отчёты',
                  font=('Arial', 14, 'bold'), foreground=C['header']).pack(pady=(10, 20))

        reports_info = [
            ('📄 Ведомость задолженников',
             'Перечень организаций с задолженностью по сдаче отчётности',
             reports.print_debt_report),
            ('📊 Статистика по ОКВЭД',
             'Распределение юридических лиц по видам экономической деятельности',
             reports.print_okved_stats),
        ]

        for title, desc, cmd in reports_info:
            rf = ttk.LabelFrame(frm, text=title, padding=10)
            rf.pack(fill='x', pady=6)
            ttk.Label(rf, text=desc, wraplength=500).pack(side='left', padx=6)
            ttk.Button(rf, text='Сформировать →', command=cmd).pack(side='right')

        # Статистика
        stats_frame = ttk.LabelFrame(frm, text='Сводная статистика', padding=10)
        stats_frame.pack(fill='x', pady=10)
        self._stats_label = ttk.Label(stats_frame, text='', font=('Arial', 11))
        self._stats_label.pack()
        ttk.Button(stats_frame, text='🔄 Обновить', command=self._refresh_stats).pack(pady=4)
        self._refresh_stats()

    def _refresh_stats(self):
        total, debt, okved_c = models.get_total_stats()
        self._stats_label.config(
            text=f'Юридических лиц на учёте: {total}   |   '
                 f'Задолженностей: {debt}   |   '
                 f'Кодов ОКВЭД: {okved_c}'
        )


# ══════════════════ Панель администратора ══════════════════

class AdminPanel(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._build()

    def _build(self):
        ttk.Label(self, text='Управление пользователями',
                  font=('Arial', 12, 'bold'), foreground=C['header']).pack(pady=8)

        tb = ttk.Frame(self)
        tb.pack(fill='x', padx=8, pady=4)
        ttk.Button(tb, text='➕ Добавить', command=self._add_user).pack(side='left', padx=3)
        ttk.Button(tb, text='🔑 Сменить пароль', command=self._change_pass).pack(side='left', padx=3)
        ttk.Button(tb, text='⇄ Изменить роль', command=self._change_role).pack(side='left', padx=3)
        ttk.Button(tb, text='⏸ Вкл/Откл', command=self._toggle_active).pack(side='left', padx=3)
        ttk.Separator(tb, orient='vertical').pack(side='left', fill='y', padx=8)
        ttk.Button(tb, text='💾 Рез. копия БД', command=self._backup).pack(side='left', padx=3)

        cols = ('КодПользователя', 'Логин', 'Роль', 'Активен')
        frm, self.tree = scrolled_tree(self, cols, (60, 200, 140, 80), height=12)
        frm.pack(fill='both', expand=True, padx=8, pady=4)
        self._load()

    def _load(self):
        self.tree.delete(*self.tree.get_children())
        for u in models.get_users():
            tag = '' if u['Активен'] else 'arch'
            self.tree.insert('', 'end', iid=u['КодПользователя'],
                             values=(u['КодПользователя'], u['Логин'],
                                     u['Роль'], 'Да' if u['Активен'] else 'Нет'),
                             tags=(tag,))

    def _selected_id(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def _add_user(self):
        dlg = tk.Toplevel(self)
        dlg.title('Новый пользователь')
        dlg.grab_set()
        dlg.resizable(False, False)
        f = ttk.Frame(dlg, padding=12)
        f.pack()
        f.columnconfigure(1, weight=1)
        login_var = lbl_entry(f, 'Логин:', 0)
        pass_var  = lbl_entry(f, 'Пароль:', 1)
        for w in f.grid_slaves(row=1, column=1):
            w.destroy()
        ep = ttk.Entry(f, textvariable=pass_var, show='*', width=32)
        ep.grid(row=1, column=1, sticky='ew', padx=6, pady=3)
        role_var, _ = tk.StringVar(value='оператор'), None
        ttk.Label(f, text='Роль:').grid(row=2, column=0, sticky='e', padx=6, pady=3)
        role_cb = ttk.Combobox(f, textvariable=role_var,
                               values=['оператор', 'администратор'], state='readonly', width=20)
        role_cb.grid(row=2, column=1, sticky='w', padx=6)
        res = [None]

        def ok():
            if not login_var.get() or not pass_var.get():
                messagebox.showerror('', 'Заполните логин и пароль', parent=dlg)
                return
            res[0] = (login_var.get(), pass_var.get(), role_var.get())
            dlg.destroy()

        bf = ttk.Frame(f)
        bf.grid(row=3, column=0, columnspan=2, pady=8)
        ttk.Button(bf, text='Создать', command=ok).pack(side='left', padx=4)
        ttk.Button(bf, text='Отмена', command=dlg.destroy).pack(side='left')
        dlg.wait_window()
        if res[0]:
            try:
                models.add_user(*res[0])
                self._load()
            except Exception as e:
                messagebox.showerror('Ошибка', str(e))

    def _change_pass(self):
        uid = self._selected_id()
        if not uid:
            return
        new_pass = simpledialog.askstring('Пароль', 'Новый пароль:', show='*', parent=self)
        if new_pass:
            models.update_user_password(uid, new_pass)
            messagebox.showinfo('', 'Пароль изменён')

    def _change_role(self):
        uid = self._selected_id()
        if not uid:
            return
        role = simpledialog.askstring('Роль', 'Введите роль (оператор / администратор):', parent=self)
        if role in ('оператор', 'администратор'):
            models.change_role(uid, role)
            self._load()

    def _toggle_active(self):
        uid = self._selected_id()
        if not uid:
            return
        row = next((u for u in models.get_users() if u['КодПользователя'] == uid), None)
        if row:
            models.toggle_user_active(uid, not row['Активен'])
            self._load()

    def _backup(self):
        try:
            path = database.backup_db()
            messagebox.showinfo('Резервная копия', f'Сохранено:\n{path}')
        except Exception as e:
            messagebox.showerror('Ошибка', str(e))


# ══════════════════ Главное окно ══════════════════

class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw()  # скрыть до входа
        configure_styles()
        self._show_login()

    def _show_login(self):
        dlg = LoginDialog(self)
        self.wait_window(dlg)
        if not dlg.result:
            self.destroy()
            return
        CURRENT_USER['login'] = dlg.result['Логин']
        CURRENT_USER['role']  = dlg.result['Роль']
        self._build_main()
        self.deiconify()

    def _build_main(self):
        self.title(f'АИС «Налоговая инспекция»  —  {CURRENT_USER["login"]} ({CURRENT_USER["role"]})')
        self.geometry('1200x700')
        self.minsize(950, 550)
        self.configure(bg=C['bg'])
        self.protocol('WM_DELETE_WINDOW', self._on_close)

        self._build_menu()
        self._build_notebook()
        self._build_statusbar()

    def _build_menu(self):
        mb = tk.Menu(self)
        self.config(menu=mb)

        m_file = tk.Menu(mb, tearoff=0)
        m_file.add_command(label='Выход', command=self._on_close)
        mb.add_cascade(label='Файл', menu=m_file)

        m_rep = tk.Menu(mb, tearoff=0)
        m_rep.add_command(label='Ведомость задолженников',
                          command=reports.print_debt_report)
        m_rep.add_command(label='Статистика по ОКВЭД',
                          command=reports.print_okved_stats)
        mb.add_cascade(label='Отчёты', menu=m_rep)

        if is_admin():
            m_adm = tk.Menu(mb, tearoff=0)
            m_adm.add_command(label='Резервное копирование', command=self._backup)
            m_adm.add_command(label='Управление пользователями',
                              command=lambda: self.nb.select(3))
            mb.add_cascade(label='Администрирование', menu=m_adm)

        m_help = tk.Menu(mb, tearoff=0)
        m_help.add_command(label='О программе', command=self._about)
        mb.add_cascade(label='Справка', menu=m_help)

    def _build_notebook(self):
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill='both', expand=True, padx=8, pady=4)

        self.entities_panel = EntitiesPanel(self.nb, self._set_status)
        self.okved_panel    = OkvedPanel(self.nb)
        self.reports_panel  = ReportsPanel(self.nb)

        self.nb.add(self.entities_panel, text='  Юридические лица  ')
        self.nb.add(self.okved_panel,    text='  Справочник ОКВЭД  ')
        self.nb.add(self.reports_panel,  text='  Отчёты  ')

        if is_admin():
            self.admin_panel = AdminPanel(self.nb)
            self.nb.add(self.admin_panel, text='  Администрирование  ')

    def _build_statusbar(self):
        self._status_var = tk.StringVar(value='Готово')
        ttk.Label(self, textvariable=self._status_var, relief='sunken',
                  anchor='w', padding=(8, 2)).pack(side='bottom', fill='x')

    def _set_status(self, text):
        self._status_var.set(text)

    def _backup(self):
        try:
            path = database.backup_db()
            messagebox.showinfo('Резервная копия', f'Сохранено:\n{path}')
        except Exception as e:
            messagebox.showerror('Ошибка', str(e))

    def _about(self):
        messagebox.showinfo('О программе',
                            'АИС «Налоговая инспекция»\nВерсия 1.0\n\n'
                            'Автоматизированная информационная система\n'
                            'учёта юридических лиц и видов их деятельности.\n\n'
                            'МГИМО, Одинцовский филиал, 2026\n\n'
                            f'Вход: {CURRENT_USER["login"]} ({CURRENT_USER["role"]})')

    def _on_close(self):
        if messagebox.askyesno('Выход', 'Выйти из программы?'):
            self.destroy()


if __name__ == '__main__':
    app = MainApp()
    app.mainloop()
