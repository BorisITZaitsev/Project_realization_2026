"""
АИС «Налоговая инспекция» — модуль печатных форм (HTML)
"""
import os
import webbrowser
import tempfile
from datetime import datetime
import models

STYLE = """
<style>
  body { font-family: Arial, sans-serif; font-size: 12px; margin: 20px; color: #222; }
  h2, h3 { text-align: center; margin: 4px 0; }
  p.sub  { text-align: center; color: #555; margin: 2px 0 10px; }
  table  { width: 100%; border-collapse: collapse; margin-top: 10px; }
  th, td { border: 1px solid #aaa; padding: 5px 8px; }
  th     { background: #dde9f7; text-align: center; font-weight: bold; }
  td.r   { text-align: right; }
  td.c   { text-align: center; }
  .badge { display:inline-block; background:#c0392b; color:#fff;
           border-radius:4px; padding:1px 6px; font-size:11px; }
  @media print { button { display: none; } }
</style>
<button onclick="window.print()" style="margin-bottom:12px;padding:5px 16px;cursor:pointer">🖨 Печать</button>
"""


def _open(html: str):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w', encoding='utf-8')
    tmp.write(html)
    tmp.close()
    webbrowser.open('file://' + tmp.name)


# ── Ведомость задолженников ──────────────────────────────────────────────────

def print_debt_report():
    rows_data = models.get_debt_report()
    rows = ''
    for i, r in enumerate(rows_data, 1):
        rows += (f'<tr><td class="c">{i}</td>'
                 f'<td>{r["ПолноеНаименование"]}</td>'
                 f'<td class="c">{r["ИНН"]}</td>'
                 f'<td class="c">{r["КПП"] or "—"}</td>'
                 f'<td>{r["ЮридическийАдрес"]}</td>'
                 f'<td>{r["ГенеральныйДиректор"] or "—"}</td>'
                 f'<td>{r["Телефон"] or "—"}</td>'
                 f'<td>{r["ОКВЭДы"] or "—"}</td></tr>')

    today = datetime.today().strftime('%d.%m.%Y')
    html = f'''<html><head><meta charset="utf-8">
    <title>Задолженность по отчётности</title>{STYLE}</head><body>
    <h2>ВЕДОМОСТЬ</h2>
    <h3>«Перечень организаций с задолженностью по сдаче отчётности»</h3>
    <p class="sub">Дата формирования: {today} &nbsp;|&nbsp; Всего организаций: {len(rows_data)}</p>
    <table>
      <tr><th>№</th><th>Наименование</th><th>ИНН</th><th>КПП</th>
          <th>Адрес</th><th>Рук-ль</th><th>Телефон</th><th>ОКВЭД</th></tr>
      {rows if rows else '<tr><td colspan="8" style="text-align:center;color:#888">Задолженностей не найдено</td></tr>'}
    </table>
    </body></html>'''
    _open(html)


# ── Список ЮрЛиц по ОКВЭД ───────────────────────────────────────────────────

def print_entities_by_okved(okved_id, okved_code, okved_name):
    rows_data = models.get_entities_by_okved(okved_id)
    rows = ''
    for i, r in enumerate(rows_data, 1):
        main = '<span class="badge">осн.</span>' if r['Основной'] else ''
        rows += (f'<tr><td class="c">{i}</td>'
                 f'<td>{r["ПолноеНаименование"]} {main}</td>'
                 f'<td class="c">{r["ИНН"]}</td>'
                 f'<td>{r["ЮридическийАдрес"]}</td>'
                 f'<td>{r["Телефон"] or "—"}</td></tr>')

    today = datetime.today().strftime('%d.%m.%Y')
    html = f'''<html><head><meta charset="utf-8">
    <title>ЮрЛица по ОКВЭД {okved_code}</title>{STYLE}</head><body>
    <h2>Список юридических лиц по виду деятельности</h2>
    <h3>ОКВЭД {okved_code} — {okved_name}</h3>
    <p class="sub">Дата: {today} &nbsp;|&nbsp; Организаций: {len(rows_data)}</p>
    <table>
      <tr><th>№</th><th>Наименование</th><th>ИНН</th><th>Адрес</th><th>Телефон</th></tr>
      {rows if rows else '<tr><td colspan="5" style="text-align:center;color:#888">Нет организаций</td></tr>'}
    </table>
    </body></html>'''
    _open(html)


# ── Карточка юридического лица ───────────────────────────────────────────────

def print_entity_card(entity_id):
    e = models.get_entity(entity_id)
    if not e:
        return
    okved_list = models.get_entity_okved(entity_id)
    okved_str = '; '.join(
        f'{r["Код"]} ({r["Наименование"]}){"*" if r["Основной"] else ""}' for r in okved_list
    ) or '—'

    def field(label, val):
        return f'<tr><td style="width:200px;font-weight:bold;background:#f5f7fa">{label}</td><td>{val or "—"}</td></tr>'

    debt_badge = '<span class="badge">ЗАДОЛЖЕННОСТЬ</span>' if e['ЕстьЗадолженность'] else ''
    today = datetime.today().strftime('%d.%m.%Y')
    html = f'''<html><head><meta charset="utf-8">
    <title>Карточка: {e["ПолноеНаименование"]}</title>{STYLE}</head><body>
    <h2>КАРТОЧКА ЮРИДИЧЕСКОГО ЛИЦА {debt_badge}</h2>
    <p class="sub">Сформировано: {today}</p>
    <table>
      {field("Полное наименование", e["ПолноеНаименование"])}
      {field("ИНН", e["ИНН"])}
      {field("КПП", e["КПП"])}
      {field("ОКПО", e["ОКПО"])}
      {field("ОКАДО", e["ОКАДО"])}
      {field("Дата регистрации", e["ДатаРегистрации"])}
      {field("Юридический адрес", e["ЮридическийАдрес"])}
      {field("Почтовый адрес", e["ПочтовыйАдрес"])}
      {field("Генеральный директор", e["ГенеральныйДиректор"])}
      {field("Телефон", e["Телефон"])}
      {field("Email", e["Email"])}
      {field("Сайт", e["Сайт"])}
      {field("БИК", e["БИК"])}
      {field("Расчётный счёт", e["РасчетныйСчет"])}
      {field("Корпоративный счёт", e["КорпоративныйСчет"])}
      {field("Виды деятельности (ОКВЭД)", okved_str)}
    </table>
    <p style="font-size:10px;color:#888;margin-top:10px">* — основной вид деятельности</p>
    </body></html>'''
    _open(html)


# ── Статистика по ОКВЭД ──────────────────────────────────────────────────────

def print_okved_stats():
    data = models.get_okved_stats()
    rows = ''
    for i, r in enumerate(data, 1):
        rows += (f'<tr><td class="c">{i}</td>'
                 f'<td class="c">{r["Код"]}</td>'
                 f'<td>{r["Наименование"]}</td>'
                 f'<td class="c">{r["Количество"]}</td></tr>')
    today = datetime.today().strftime('%d.%m.%Y')
    html = f'''<html><head><meta charset="utf-8">
    <title>Статистика ОКВЭД</title>{STYLE}</head><body>
    <h2>РАСПРЕДЕЛЕНИЕ ЮРИДИЧЕСКИХ ЛИЦ ПО ВИДАМ ДЕЯТЕЛЬНОСТИ</h2>
    <p class="sub">Дата: {today}</p>
    <table>
      <tr><th>№</th><th>Код ОКВЭД</th><th>Наименование</th><th>Кол-во ЮрЛиц</th></tr>
      {rows}
    </table>
    </body></html>'''
    _open(html)
