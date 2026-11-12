"""Карта проекта 1С со связями (волна 3 п.3.7) — строится локально, код никуда не уходит.

    python project-map.py --src <XML-выгрузка конфигурации> [--out <страница.html>]
                          [--code-index <index.db или папка> | --no-code-index] [--lang ru]
                          [--focus <Тип.Имя> [--archify-json <кандидат.json>] [--no-render]]

Что на карте: дерево подсистем → объекты их состава → общие модули; у каждого объекта — кто его вызывает и кого вызывает он
(ребро «объект → объект» со счётом вызовов и образцами «процедура → метод»). Вид ребра: «вызов» — метод общего модуля или
процедура модуля менеджера; «обращение» — метод платформы у менеджера объекта (Справочники.Товары.НайтиПоКоду).
Источник вызовов:
  - индекс code-index (таблицы files и calls, только чтение), если он есть и построен по ЭТОЙ выгрузке (сверка путей файлов);
    по умолчанию ищется в <выгрузка>/.code-index и <родитель>/.code-index (в т.ч. по алиасам), явно — --code-index;
  - иначе — разбор модулей .bsl выгрузки: вызовы вида Модуль.Метод( и Менеджер.Имя.Метод( без комментариев и строк.
    Вызовы через переменные, Выполнить() и ОбщегоНазначения.ОбщийМодуль("Имя") не видны ни тому, ни другому.
Выход — одна HTML-страница без внешних адресов (данные внутри): поиск, дерево подсистем, карточка объекта с кликабельными
связями и схемой соседства; открывается в браузере из файла. Наружу её не публиковать — в ней имена и вызовы кода.
--focus — дополнительно кандидат схемы archify (вид class: вызывающие → объект → вызываемые) и, если есть node и скилл
archify, его страница (`archify render class`); вылизать её — скиллом archify (finalize).
Формат EDT (.mdo) пока не поддержан — нужна XML-выгрузка (скилл db-dump-xml). Код выхода: 0 — карта построена, 2 — нет выгрузки.
"""
import argparse
import datetime
import glob
import html
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import urllib.parse

# папка выгрузки → тип объекта (как в Configuration.xml), подпись типа во множественном числе
TYPES = [
    ('Subsystems', 'Subsystem', 'Подсистемы'), ('CommonModules', 'CommonModule', 'Общие модули'),
    ('SessionParameters', 'SessionParameter', 'Параметры сеанса'), ('Roles', 'Role', 'Роли'),
    ('CommonAttributes', 'CommonAttribute', 'Общие реквизиты'), ('ExchangePlans', 'ExchangePlan', 'Планы обмена'),
    ('FilterCriteria', 'FilterCriterion', 'Критерии отбора'), ('EventSubscriptions', 'EventSubscription', 'Подписки на события'),
    ('ScheduledJobs', 'ScheduledJob', 'Регламентные задания'), ('FunctionalOptions', 'FunctionalOption', 'Функциональные опции'),
    ('FunctionalOptionsParameters', 'FunctionalOptionsParameter', 'Параметры функциональных опций'),
    ('DefinedTypes', 'DefinedType', 'Определяемые типы'), ('SettingsStorages', 'SettingsStorage', 'Хранилища настроек'),
    ('CommonForms', 'CommonForm', 'Общие формы'), ('CommonCommands', 'CommonCommand', 'Общие команды'),
    ('CommandGroups', 'CommandGroup', 'Группы команд'), ('CommonTemplates', 'CommonTemplate', 'Общие макеты'),
    ('CommonPictures', 'CommonPicture', 'Общие картинки'), ('XDTOPackages', 'XDTOPackage', 'XDTO-пакеты'),
    ('WebServices', 'WebService', 'Веб-сервисы'), ('HTTPServices', 'HTTPService', 'HTTP-сервисы'),
    ('WSReferences', 'WSReference', 'WS-ссылки'), ('IntegrationServices', 'IntegrationService', 'Сервисы интеграции'),
    ('StyleItems', 'StyleItem', 'Элементы стиля'), ('Styles', 'Style', 'Стили'), ('Languages', 'Language', 'Языки'),
    ('Constants', 'Constant', 'Константы'), ('Catalogs', 'Catalog', 'Справочники'), ('Documents', 'Document', 'Документы'),
    ('DocumentNumerators', 'DocumentNumerator', 'Нумераторы'), ('Sequences', 'Sequence', 'Последовательности'),
    ('DocumentJournals', 'DocumentJournal', 'Журналы документов'), ('Enums', 'Enum', 'Перечисления'),
    ('Reports', 'Report', 'Отчёты'), ('DataProcessors', 'DataProcessor', 'Обработки'),
    ('ChartsOfCharacteristicTypes', 'ChartOfCharacteristicTypes', 'Планы видов характеристик'),
    ('ChartsOfAccounts', 'ChartOfAccounts', 'Планы счетов'), ('ChartsOfCalculationTypes', 'ChartOfCalculationTypes', 'Планы видов расчёта'),
    ('InformationRegisters', 'InformationRegister', 'Регистры сведений'), ('AccumulationRegisters', 'AccumulationRegister', 'Регистры накопления'),
    ('AccountingRegisters', 'AccountingRegister', 'Регистры бухгалтерии'), ('CalculationRegisters', 'CalculationRegister', 'Регистры расчёта'),
    ('BusinessProcesses', 'BusinessProcess', 'Бизнес-процессы'), ('Tasks', 'Task', 'Задачи'),
    ('ExternalDataSources', 'ExternalDataSource', 'Внешние источники данных'), ('Bots', 'Bot', 'Боты'),
]
DIR2TYPE = {d: t for d, t, _ in TYPES}
TYPE2DIR = {t: d for d, t, _ in TYPES}
TYPE_LABEL = {t: lbl for _, t, lbl in TYPES}
TYPE_LABEL['Configuration'] = 'Конфигурация'
# имя менеджера в коде (оба языка встроенного языка) → тип объекта
MANAGERS = {
    'справочники': 'Catalog', 'catalogs': 'Catalog', 'документы': 'Document', 'documents': 'Document',
    'обработки': 'DataProcessor', 'dataprocessors': 'DataProcessor', 'отчеты': 'Report', 'отчёты': 'Report', 'reports': 'Report',
    'регистрысведений': 'InformationRegister', 'informationregisters': 'InformationRegister',
    'регистрынакопления': 'AccumulationRegister', 'accumulationregisters': 'AccumulationRegister',
    'регистрыбухгалтерии': 'AccountingRegister', 'accountingregisters': 'AccountingRegister',
    'регистрырасчета': 'CalculationRegister', 'calculationregisters': 'CalculationRegister',
    'планысчетов': 'ChartOfAccounts', 'chartsofaccounts': 'ChartOfAccounts',
    'планывидовхарактеристик': 'ChartOfCharacteristicTypes', 'chartsofcharacteristictypes': 'ChartOfCharacteristicTypes',
    'планывидоврасчета': 'ChartOfCalculationTypes', 'chartsofcalculationtypes': 'ChartOfCalculationTypes',
    'планыобмена': 'ExchangePlan', 'exchangeplans': 'ExchangePlan', 'бизнеспроцессы': 'BusinessProcess', 'businessprocesses': 'BusinessProcess',
    'задачи': 'Task', 'tasks': 'Task', 'перечисления': 'Enum', 'enums': 'Enum', 'константы': 'Constant', 'constants': 'Constant',
    'журналыдокументов': 'DocumentJournal', 'documentjournals': 'DocumentJournal',
    'последовательности': 'Sequence', 'sequences': 'Sequence', 'хранилищанастроек': 'SettingsStorage', 'settingsstorages': 'SettingsStorage',
}
CM_FLAGS = [('Global', 'Глобальный'), ('Server', 'Сервер'), ('ClientManagedApplication', 'Клиент'),
            ('ClientOrdinaryApplication', 'Клиент (обычное приложение)'), ('ExternalConnection', 'Внешнее соединение'),
            ('ServerCall', 'ВызовСервера'), ('Privileged', 'Привилегированный')]
REUSE = {'DuringRequest': 'на время вызова', 'DuringSession': 'на время сеанса'}
PROC = re.compile(r'^\s*(?:&\S+\s+)?(?:Асинх\s+|Async\s+)?(?:Процедура|Функция|Procedure|Function)\s+(\w+)\s*\(', re.I)
PROC_END = re.compile(r'^\s*(?:КонецПроцедуры|КонецФункции|EndProcedure|EndFunction)\b', re.I)
CALL2 = re.compile(r'(?<![\w.])(\w+)\s*\.\s*(\w+)\s*\(')
MGR = re.compile(r'(?<![\w.])(\w+)\s*\.\s*(\w+)(?:\s*\.\s*(\w+)\s*(\()?)?')
STR_OR_COMMENT = re.compile(r'"[^"]*(?:""[^"]*)*"|//[^\n]*')
SAMPLES = 3


def read_head(path, limit=262144):
    with open(path, 'rb') as f:
        return f.read(limit).decode('utf-8-sig', 'replace')


def pick_lang(block, lang):
    """Текст многоязычной строки 1С (<v8:item><v8:lang>…</v8:lang><v8:content>…</v8:content>) на языке профиля."""
    items = re.findall(r'<v8:lang>([^<]*)</v8:lang>\s*<v8:content>([^<]*)</v8:content>', block or '')
    d = {k: html.unescape(v) for k, v in items}
    for k in (lang, 'ru', 'en'):
        if d.get(k):
            return d[k]
    return html.unescape(items[0][1]) if items else ''


def props_of(path, lang):
    """Имя, синоним и блок свойств объекта из его XML (начало файла)."""
    try:
        t = read_head(path)
    except OSError:
        return '', ''
    m = re.search(r'(?s)<Properties>(.*?)(?:</Properties>|$)', t)
    p = m.group(1) if m else ''
    sm = re.search(r'(?s)<Synonym>(.*?)</Synonym>', p)
    return pick_lang(sm.group(1) if sm else '', lang), p


def cm_flags(props):
    on = [ru for tag, ru in CM_FLAGS if re.search(r'<%s>true</%s>' % (tag, tag), props)]
    rv = re.search(r'<ReturnValuesReuse>(\w+)</ReturnValuesReuse>', props)
    if rv and rv.group(1) in REUSE:
        on.append('ПовторноеИспользование: ' + REUSE[rv.group(1)])
    return ', '.join(on)


def read_subsystems(src, lang, add_obj):
    """Дерево подсистем рекурсивно: [{n, s, p, c, path}] — c хранит полные имена объектов состава (индексы — позже)."""
    out = []

    def walk(folder, parent, prefix):
        if not os.path.isdir(folder):
            return
        for f in sorted(x for x in os.listdir(folder) if x.lower().endswith('.xml')):
            name = f[:-4]
            path = os.path.join(folder, f)
            try:
                with open(path, encoding='utf-8-sig', errors='replace') as fh:
                    t = fh.read()
            except OSError:
                continue
            props = (re.search(r'(?s)<Properties>(.*?)</Properties>', t) or re.search(r'(?s)(.*)', t)).group(1)
            sm = re.search(r'(?s)<Synonym>(.*?)</Synonym>', props)
            cm = re.search(r'(?s)<Content>(.*?)</Content>', props)
            refs = re.findall(r'<xr:Item[^>]*>\s*([A-Za-z]+\.[^<\s]+)\s*</xr:Item>', cm.group(1)) if cm else []
            idx = len(out)
            out.append({'n': name, 's': pick_lang(sm.group(1) if sm else '', lang), 'p': parent,
                        'path': prefix + name, 'c': [r for r in refs if add_obj(r)]})
            walk(os.path.join(folder, name, 'Subsystems'), idx, prefix + name + '/')
    walk(os.path.join(src, 'Subsystems'), -1, '')
    return out


def owner_of(rel):
    """Путь модуля относительно корня выгрузки (XML или индекса EDT) → (объект, вид модуля); None — не модуль объекта."""
    parts = rel.replace('\\', '/').split('/')
    if parts[0] in ('Ext', 'Configuration') and len(parts) >= 2:
        return 'Configuration', parts[-1][:-4]
    t = DIR2TYPE.get(parts[0])
    if not t or len(parts) < 3:
        return None
    if 'Forms' in parts[2:]:
        i = parts.index('Forms', 2)
        return '%s.%s' % (t, parts[1]), 'форма ' + (parts[i + 1] if i + 1 < len(parts) else '?')
    if 'Commands' in parts[2:]:
        i = parts.index('Commands', 2)
        return '%s.%s' % (t, parts[1]), 'команда ' + (parts[i + 1] if i + 1 < len(parts) else '?')
    return '%s.%s' % (t, parts[1]), parts[-1][:-4]


def strip_code(text):
    """Комментарии убираются, строки становятся пустыми "" (многострочная строка оставляет свои переводы строк —
    номера строк не сдвигаются). Самая левая находка решает: «//» внутри строки — часть строки, кавычка в комментарии — комментарий."""
    return STR_OR_COMMENT.sub(lambda mm: '' if mm.group(0)[0] == '/' else '"' + '\n' * mm.group(0).count('\n') + '"', text)


def parse_module(text):
    """Модуль → (определённые процедуры {нижний регистр}, вызовы [(процедура, текст вызова, строка)])."""
    defs, calls, cur = set(), [], '<модуль>'
    for ln, line in enumerate(strip_code(text).split('\n'), 1):
        pm = PROC.match(line)
        if pm:
            cur = pm.group(1)
            defs.add(cur.lower())
        elif PROC_END.match(line):
            cur = '<модуль>'
            continue
        if '.' not in line:
            continue
        for mm in MGR.finditer(line):
            a, b, c, paren = mm.group(1), mm.group(2), mm.group(3), mm.group(4)
            if a.lower() in MANAGERS:
                calls.append((cur, '%s.%s.%s' % (a, b, c) if c and paren else '%s.%s' % (a, b), ln, bool(c and paren)))
        for mm in CALL2.finditer(line):
            if mm.group(1).lower() not in MANAGERS:
                calls.append((cur, '%s.%s' % (mm.group(1), mm.group(2)), ln, True))
    return defs, calls


class Model:
    def __init__(self):
        self.objects, self.index = [], {}
        self.cms = {}          # нижний регистр имени общего модуля → полное имя
        self.by_type = {}      # (тип, нижний регистр имени) → полное имя
        self.defs = {}         # полное имя объекта → процедуры модуля менеджера (нижний регистр)
        self.edges = {}        # (от, к, вид) → [счёт, образцы]
        self.modules = {}      # полное имя → число модулей

    def add(self, full, syn='', flags=''):
        if full in self.index:
            o = self.objects[self.index[full]]
            o['s'] = o['s'] or syn
            o['f'] = o['f'] or flags
            return self.index[full]
        t, _, name = full.partition('.')
        self.index[full] = len(self.objects)
        self.objects.append({'n': full, 't': t, 's': syn, 'f': flags, 'm': 0})
        self.by_type[(t, name.lower())] = full
        if t == 'CommonModule':
            self.cms[name.lower()] = full
        return self.index[full]

    def resolve(self, owner, proc, callee, is_call):
        """Текст вызова → ребро. «Модуль.Метод» — общий модуль; «Менеджер.Имя[.Метод]» — объект (вызов или обращение)."""
        parts = callee.split('.')
        if len(parts) < 2:
            return
        head = parts[0].lower()
        if head in self.cms and len(parts) == 2 and is_call:
            to, kind, method = self.cms[head], 'call', parts[1]
        elif head in MANAGERS:
            to = self.by_type.get((MANAGERS[head], parts[1].lower()))
            if not to:
                return
            method = parts[2] if len(parts) > 2 else ''
            kind = 'call' if method and is_call and method.lower() in self.defs.get(to, ()) else 'use'
        else:
            return
        if to == owner:
            return
        self.add(owner)
        e = self.edges.setdefault((owner, to, kind), [0, []])
        e[0] += 1
        smp = '%s → %s' % (proc, method or parts[1])
        if len(e[1]) < SAMPLES and smp not in e[1]:
            e[1].append(smp)


def read_config(src, lang):
    m = Model()
    cfg = os.path.join(src, 'Configuration.xml')
    t = read_head(cfg, 1 << 24)
    nm = re.search(r'(?s)<Configuration[^>]*>.*?<Properties>.*?<Name>([^<]*)</Name>', t)
    syn, _ = props_of(cfg, lang)
    co = re.search(r'(?s)<ChildObjects>(.*)</ChildObjects>', t)
    kids = re.findall(r'<(\w+)>([^<]+)</\1>', co.group(1)) if co else []
    for typ, name in kids:
        if typ == 'Subsystem':
            continue
        d = TYPE2DIR.get(typ)
        s, props = props_of(os.path.join(src, d, name + '.xml'), lang) if d else ('', '')
        m.add('%s.%s' % (typ, name), s, cm_flags(props) if typ == 'CommonModule' else '')

    def add_ref(ref):
        if ref.split('.', 1)[0] == 'Subsystem':
            return False
        m.add(ref)
        return True
    subs = read_subsystems(src, lang, add_ref)
    for s in subs:
        s['c'] = sorted({m.index[r] for r in s['c']})
    return m, subs, (nm.group(1) if nm else os.path.basename(src)), syn


def bsl_files(src):
    for d, dirs, files in os.walk(src):
        dirs[:] = [x for x in dirs if not x.startswith('.')]
        for f in files:
            if f.lower().endswith('.bsl'):
                p = os.path.join(d, f)
                yield os.path.relpath(p, src).replace('\\', '/'), p


def links_from_modules(m, src):
    parsed = []
    for rel, p in bsl_files(src):
        own = owner_of(rel)
        if not own:
            continue
        try:
            with open(p, encoding='utf-8-sig', errors='replace') as f:
                defs, calls = parse_module(f.read())
        except OSError:
            continue
        m.add(own[0])
        m.modules[own[0]] = m.modules.get(own[0], 0) + 1
        if own[1] == 'ManagerModule':
            m.defs.setdefault(own[0], set()).update(defs)
        parsed.append((own[0], calls))
    for owner, calls in parsed:
        for proc, callee, _ln, is_call in calls:
            m.resolve(owner, proc, callee, is_call)


def ci_open(db):
    uri = 'file:///' + urllib.parse.quote(os.path.abspath(db).replace('\\', '/'), safe='/:') + '?mode=ro'
    return sqlite3.connect(uri, uri=True)


def ci_candidates(src, explicit):
    if explicit:
        if os.path.isdir(explicit):
            return [p for p in [os.path.join(explicit, 'index.db')] + sorted(glob.glob(os.path.join(explicit, '*', 'index.db'))) if os.path.isfile(p)]
        return [explicit]
    out = []
    for base in (src, os.path.dirname(os.path.abspath(src))):
        out += [os.path.join(base, '.code-index', 'index.db')] + sorted(glob.glob(os.path.join(base, '.code-index', '*', 'index.db')))
    return [p for p in out if os.path.isfile(p)]


def ci_match(db, src):
    """Индекс построен по этой выгрузке? → (подходит, пояснение). Сверка — доля путей .bsl индекса, существующих в выгрузке."""
    try:
        con = ci_open(db)
        cols = {t: {r[1] for r in con.execute('PRAGMA table_info(%s)' % t)} for t in ('files', 'calls')}
        if not ({'id', 'path'} <= cols['files'] and {'file_id', 'caller', 'callee'} <= cols['calls']):
            con.close()
            return False, 'схема индекса не та (нет files.path или calls.callee)'
        paths = [r[0] for r in con.execute("SELECT path FROM files WHERE path LIKE '%.bsl' LIMIT 300")]
        con.close()
    except sqlite3.Error as e:
        return False, 'индекс не читается: %s' % e
    if not paths:
        return False, 'в индексе нет модулей .bsl'
    hit = sum(1 for p in paths if os.path.isfile(os.path.join(src, *p.split('/'))))
    if hit < 0.9 * len(paths):
        return False, 'индекс не от этой выгрузки (совпало путей %d из %d)' % (hit, len(paths))
    return True, ''


def links_from_index(m, db):
    con = ci_open(db)
    files = {fid: path for fid, path in con.execute("SELECT id, path FROM files WHERE path LIKE '%.bsl'")}
    owners = {}
    for fid, path in files.items():
        own = owner_of(path)
        if own:
            owners[fid] = own
            m.add(own[0])
            m.modules[own[0]] = m.modules.get(own[0], 0) + 1
    has_fn = {r[1] for r in con.execute('PRAGMA table_info(functions)')} >= {'file_id', 'name'}
    if has_fn:
        for fid, name in con.execute('SELECT file_id, name FROM functions'):
            own = owners.get(fid)
            if own and own[1] == 'ManagerModule':
                m.defs.setdefault(own[0], set()).add(name.lower())
    for fid, caller, callee in con.execute('SELECT file_id, caller, callee FROM calls'):
        own = owners.get(fid)
        if own and callee and '.' in callee:
            m.resolve(own[0], caller or '<модуль>', callee, True)
    con.close()


def build(src, lang, code_index=None, use_index=True):
    m, subs, cfg_name, cfg_syn = read_config(src, lang)
    source, note = 'modules', ''
    if use_index:
        for db in ci_candidates(src, code_index):
            ok, why = ci_match(db, src)
            if ok:
                links_from_index(m, db)
                source = 'code-index'
                note = 'индекс code-index: %s (обновлён %s)' % (db, datetime.datetime.fromtimestamp(os.path.getmtime(db)).strftime('%Y-%m-%d %H:%M'))
                break
            note = '%s: %s — связи разобраны по модулям выгрузки' % (db, why)
    if source == 'modules':
        links_from_modules(m, src)
        note = (note + '. ' if note else '') + ('разбор модулей выгрузки: вызовы «Модуль.Метод(» и «Менеджер.Имя.Метод(» без комментариев '
                                               'и строк; вызовы через переменные и Выполнить() не видны')
    for full, n in m.modules.items():
        m.objects[m.index[full]]['m'] = n
    edges = [[m.index[a], m.index[b], c, k, s] for (a, b, k), (c, s) in sorted(m.edges.items())]
    data = {'meta': {'config': cfg_name, 'synonym': cfg_syn, 'source': source, 'note': note, 'src': os.path.abspath(src),
                     'generated': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
                     'counts': {'objects': len(m.objects), 'subsystems': len(subs), 'edges': len(edges),
                                'commonModules': len(m.cms), 'calls': sum(e[2] for e in edges if e[3] == 'call')}},
            'types': {t: TYPE_LABEL.get(t, t) for t in sorted({o['t'] for o in m.objects})},
            'order': [t for _, t, _ in TYPES] + ['Configuration'],
            'objects': m.objects, 'subsystems': subs, 'edges': edges}
    return data


def focus_candidate(data, full, title_limit=6):
    """Кандидат archify (class): вызывающие слева, объект в центре, вызываемые справа; методы — вызванные у объекта."""
    names = [o['n'] for o in data['objects']]
    if full not in names:
        return None
    me = names.index(full)
    calls = [e for e in data['edges'] if e[3] == 'call']
    inc = sorted((e for e in calls if e[1] == me), key=lambda e: -e[2])[:title_limit]
    out = sorted((e for e in calls if e[0] == me), key=lambda e: -e[2])[:title_limit]
    methods = []
    for e in inc:
        for s in e[4]:
            mth = s.split(' → ')[-1]
            if mth not in methods:
                methods.append(mth)
    o = data['objects'][me]
    sub = lambda x: (x['s'] or data['types'].get(x['t'], x['t']))[:60]
    types = [{'id': 'focus', 'label': full, 'kind': 'class', 'sublabel': sub(o), 'row': max(len(inc), len(out), 1) // 2, 'col': 1,
              'methods': [{'name': x, 'visibility': 'public'} for x in methods[:8]]}]
    rels = []
    for side, lst, col in (('in', inc, 0), ('out', out, 2)):
        for r, e in enumerate(lst):
            other = data['objects'][e[0] if side == 'in' else e[1]]
            tid = '%s%d' % (side, r)
            types.append({'id': tid, 'label': other['n'], 'kind': 'class', 'sublabel': sub(other), 'row': r, 'col': col})
            rels.append({'from': tid if side == 'in' else 'focus', 'to': 'focus' if side == 'in' else tid,
                         'kind': 'dependency', 'label': '%d выз.' % e[2]})
    return {'schema_version': 1, 'diagram_type': 'class',
            'meta': {'title': 'Связи: ' + full, 'subtitle': 'Слева — кто вызывает, справа — кого вызывает (до %d самых частых); '
                     'источник — %s' % (title_limit, 'индекс code-index' if data['meta']['source'] == 'code-index' else 'разбор модулей'),
                     'quality_profile': 'standard'},
            'layout': {'mode': 'grid'}, 'types': types, 'relationships': rels}


def archify_bin():
    here = os.path.dirname(os.path.abspath(__file__))
    plugin_root = os.path.dirname(os.path.dirname(here))
    for p in (os.path.join(plugin_root, 'skills', 'archify', 'bin', 'archify.mjs'),
              os.path.join(os.path.dirname(plugin_root), '.claude', 'skills', 'archify', 'bin', 'archify.mjs')):
        if os.path.isfile(p):
            return p
    return None


def page(data):
    # «<» — экранирование JSON: ни «</script>», ни «<!--» из синонима не закроют и не переключат блок данных
    js = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    title = html.escape('Карта проекта — ' + (data['meta']['synonym'] or data['meta']['config']))
    return PAGE.replace('__TITLE__', title).replace('__DATA__', js)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser(description='Карта проекта 1С со связями по XML-выгрузке (локально, только чтение выгрузки).')
    ap.add_argument('--src', required=True, help='корень XML-выгрузки конфигурации (там Configuration.xml)')
    ap.add_argument('--out', help='страница карты (по умолчанию .archify/project-map-<время>/project-map.html в текущей папке)')
    ap.add_argument('--code-index', help='индекс code-index: файл index.db или папка с ним (по умолчанию — поиск рядом с выгрузкой)')
    ap.add_argument('--no-code-index', action='store_true', help='не брать индекс, разобрать модули выгрузки')
    ap.add_argument('--lang', default='ru', help='язык синонимов (код языка конфигурации), по умолчанию ru')
    ap.add_argument('--focus', help='полное имя объекта (CommonModule.Имя, Document.Имя) — кандидат схемы archify его связей')
    ap.add_argument('--archify-json', help='куда положить кандидат archify (по умолчанию рядом со страницей карты)')
    ap.add_argument('--no-render', action='store_true', help='только кандидат archify, без запуска archify render')
    a = ap.parse_args()
    src = os.path.abspath(a.src)
    if not os.path.isfile(os.path.join(src, 'Configuration.xml')):
        edt = os.path.isfile(os.path.join(src, 'Configuration', 'Configuration.mdo'))
        print('нет Configuration.xml в %s%s' % (src, ' — это проект EDT; карта строится по XML-выгрузке (скилл db-dump-xml)' if edt else ''))
        return 2
    out = os.path.abspath(a.out or os.path.join(os.getcwd(), '.archify', 'project-map-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S'),
                                                'project-map.html'))
    data = build(src, a.lang, a.code_index, not a.no_code_index)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        f.write(page(data))
    c = data['meta']['counts']
    print('карта: %s' % out)
    print('объектов %d, подсистем %d, общих модулей %d, связей %d (вызовов %d); источник: %s'
          % (c['objects'], c['subsystems'], c['commonModules'], c['edges'], c['calls'], data['meta']['note']))
    if a.focus:
        cand = focus_candidate(data, a.focus)
        if cand is None:
            print('фокус: объекта %s на карте нет (полное имя: Тип.Имя, как CommonModule.ОбщегоНазначения)' % a.focus)
            return 0
        slug = re.sub(r'[^\w.-]+', '-', a.focus)
        cj = os.path.abspath(a.archify_json or os.path.join(os.path.dirname(out), slug + '.class.json'))
        os.makedirs(os.path.dirname(cj), exist_ok=True)
        with open(cj, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(cand, f, ensure_ascii=False, indent=2)
            f.write('\n')
        print('кандидат archify: %s' % cj)
        node, arch = shutil.which('node'), archify_bin()
        if a.no_render:
            return 0
        if not node or not arch:
            print('archify render не запущен: нет %s — кандидат можно отрисовать скиллом archify' % ('node' if not node else 'скилла archify'))
            return 0
        stem = os.path.splitext(cj)[0]
        fh = (stem[:-len('.class')] if stem.endswith('.class') else stem) + '.html'
        r = subprocess.run([node, arch, 'render', 'class', cj, fh, '--quality', 'standard'], capture_output=True)
        tail = (r.stdout + r.stderr).decode('utf-8', 'replace').strip().splitlines()[-3:]
        print(('схема связей: %s' % fh) if r.returncode == 0 else 'archify render: код %d — %s' % (r.returncode, ' | '.join(tail)))
    return 0


PAGE = r'''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root{--bg:#f7f7f5;--card:#ffffff;--fg:#1d1d1f;--muted:#6b6b70;--line:#dcdcd8;--accent:#2f6fde;--accent-soft:#e6eefc;--use:#9a8f80;--chip:#efefec;--hit:#fff4c2}
@media (prefers-color-scheme:dark){:root{--bg:#161618;--card:#1f1f22;--fg:#ececee;--muted:#9a9aa2;--line:#34343a;--accent:#7aa7ff;--accent-soft:#22324f;--use:#a89c8c;--chip:#2a2a2f;--hit:#4a4220}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
header{padding:12px 16px;border-bottom:1px solid var(--line);background:var(--card)}
header h1{font-size:17px;margin:0 0 2px}header .meta{color:var(--muted);font-size:12px}
.wrap{display:grid;grid-template-columns:320px 1fr;min-height:calc(100vh - 62px)}
aside{border-right:1px solid var(--line);padding:12px;overflow:auto;max-height:calc(100vh - 62px);position:sticky;top:0;background:var(--card)}
main{padding:16px;overflow:auto;min-width:0}
input[type=search]{width:100%;padding:7px 9px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--fg);font:inherit}
.results a,.tree a{display:block;padding:2px 4px;border-radius:4px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.results a:hover,.tree a:hover{background:var(--accent-soft);text-decoration:none}
.tree details{margin-left:10px}.tree summary{cursor:pointer;list-style:none;display:flex;gap:4px;align-items:baseline}
.tree summary::-webkit-details-marker{display:none}.tree summary::before{content:"▸";color:var(--muted);width:10px}
.tree details[open]>summary::before{content:"▾"}.tree .leaf{margin-left:24px}
.n{color:var(--muted);font-size:12px}
h2{font-size:18px;margin:0 0 4px}h3{font-size:14px;margin:18px 0 6px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.03em}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:14px;margin-bottom:12px}
.chips{display:flex;flex-wrap:wrap;gap:6px}.chip{background:var(--chip);border-radius:12px;padding:2px 9px;font-size:13px}
.flags{color:var(--muted);font-size:13px}
table{border-collapse:collapse;width:100%}td,th{text-align:left;padding:4px 6px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--muted);font-weight:600;font-size:12px}td.num{text-align:right;white-space:nowrap;width:1%}
.kind-use{color:var(--use)}.smp{color:var(--muted);font-size:12px}
.crumbs{color:var(--muted);font-size:13px;margin-bottom:6px}
svg.nb{width:100%;height:auto;background:var(--card);border:1px solid var(--line);border-radius:8px}
svg.nb text{font:12px system-ui,sans-serif;fill:var(--fg)}svg.nb rect{fill:var(--chip);stroke:var(--line)}
svg.nb .me rect{fill:var(--accent-soft);stroke:var(--accent)}svg.nb a:hover rect{stroke:var(--accent)}
svg.nb path{fill:none;stroke:var(--accent);opacity:.55}svg.nb path.use{stroke:var(--use);stroke-dasharray:4 3}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
label.opt{color:var(--muted);font-size:13px;user-select:none}
@media (max-width:820px){.wrap{grid-template-columns:1fr}aside{position:static;max-height:none;border-right:0;border-bottom:1px solid var(--line)}.grid2{grid-template-columns:1fr}}
</style>
</head>
<body>
<header><h1 id="ttl"></h1><div class="meta" id="meta"></div></header>
<div class="wrap">
<aside>
<input type="search" id="q" placeholder="Поиск объекта: имя или синоним" autocomplete="off">
<div class="results" id="res"></div>
<h3>Подсистемы</h3>
<div class="tree" id="tree"></div>
</aside>
<main id="main"></main>
</div>
<script type="application/json" id="map-data">__DATA__</script>
<script>
(function(){
'use strict';
const D = JSON.parse(document.getElementById('map-data').textContent);
const O = D.objects, S = D.subsystems, E = D.edges, T = D.types;
const idx = new Map(O.map((o, i) => [o.n, i]));
const outE = O.map(() => []), inE = O.map(() => []);
E.forEach((e, k) => { outE[e[0]].push(k); inE[e[1]].push(k); });
const subsOf = O.map(() => []); S.forEach((s, si) => s.c.forEach(oi => subsOf[oi].push(si)));
const kids = S.map(() => []); S.forEach((s, si) => { if (s.p >= 0) kids[s.p].push(si); });
const none = O.map((o, i) => i).filter(i => !subsOf[i].length);
const order = new Map(D.order.map((t, i) => [t, i]));
let showUse = false;

function el(tag, cls, text) { const x = document.createElement(tag); if (cls) x.className = cls; if (text != null) x.textContent = text; return x; }
function link(href, text, title) { const a = el('a', null, text); a.href = href; if (title) a.title = title; return a; }
function oLink(i) { const o = O[i]; return link('#o=' + encodeURIComponent(o.n), o.n, o.s || ''); }
function sLink(si) { const s = S[si]; return link('#s=' + si, s.s || s.n, s.path); }
function sPath(si) { const p = []; for (let x = si; x >= 0; x = S[x].p) p.unshift(x); return p; }
function tl(t) { return T[t] || t; }
function calls(list) { return list.reduce((a, k) => a + (E[k][3] === 'call' ? E[k][2] : 0), 0); }
function deep(si) { const r = new Set(S[si].c); kids[si].forEach(k => deep(k).forEach(x => r.add(x))); return r; }

document.getElementById('ttl').textContent = 'Карта проекта — ' + (D.meta.synonym || D.meta.config);
const c = D.meta.counts;
document.getElementById('meta').textContent = 'Объектов ' + c.objects + ' · подсистем ' + c.subsystems + ' · общих модулей ' + c.commonModules +
  ' · связей ' + c.edges + ' (вызовов ' + c.calls + ') · построена ' + D.meta.generated + ' · ' + D.meta.note;

function buildTree() {
  const root = document.getElementById('tree');
  function node(si, host) {
    const cnt = el('span', 'n', ' ' + S[si].c.length);
    if (!kids[si].length) { const d = el('div', 'leaf'); d.append(sLink(si), cnt); host.append(d); return; }
    const det = el('details'); const sum = el('summary'); sum.append(sLink(si), cnt); det.append(sum);
    kids[si].forEach(k => node(k, det)); host.append(det);
  }
  S.forEach((s, si) => { if (s.p < 0) node(si, root); });
  const d = el('div', 'leaf'); d.append(link('#s=none', 'Вне подсистем'), el('span', 'n', ' ' + none.length)); root.append(d);
}

function search() {
  const q = document.getElementById('q').value.trim().toLowerCase(), res = document.getElementById('res');
  res.replaceChildren();
  if (!q) return;
  let n = 0;
  for (let i = 0; i < O.length && n < 80; i++) {
    const o = O[i];
    if (o.n.toLowerCase().includes(q) || (o.s && o.s.toLowerCase().includes(q))) { res.append(oLink(i)); n++; }
  }
  if (!n) res.append(el('div', 'n', 'ничего не найдено'));
}

function objList(ids, host) {
  const groups = new Map();
  ids.forEach(i => { const t = O[i].t; if (!groups.has(t)) groups.set(t, []); groups.get(t).push(i); });
  [...groups.keys()].sort((a, b) => (order.get(a) ?? 99) - (order.get(b) ?? 99)).forEach(t => {
    host.append(el('h3', null, tl(t) + ' · ' + groups.get(t).length));
    const ch = el('div', 'chips');
    groups.get(t).sort((a, b) => O[a].n.localeCompare(O[b].n)).forEach(i => { const s = el('span', 'chip'); s.append(oLink(i)); ch.append(s); });
    host.append(ch);
  });
}

function topTable(rows, host, head) {
  const tb = el('table'); const tr = el('tr'); head.forEach(h => tr.append(el('th', null, h))); tb.append(tr);
  rows.forEach(r => { const x = el('tr'); const a = el('td'); a.append(oLink(r[0])); x.append(a, el('td', 'flags', O[r[0]].s || ''), el('td', 'num', String(r[1]))); tb.append(x); });
  host.append(tb);
}

function home(m) {
  const cd = el('div', 'card'); cd.append(el('h2', null, D.meta.synonym || D.meta.config), el('div', 'flags', D.meta.src)); m.append(cd);
  const g = el('div', 'grid2');
  const a = el('div', 'card'); a.append(el('h3', null, 'Подсистемы верхнего уровня'));
  const tb = el('table'); S.forEach((s, si) => { if (s.p >= 0) return; const tr = el('tr'); const td = el('td'); td.append(sLink(si));
    tr.append(td, el('td', 'num', String(deep(si).size))); tb.append(tr); });
  a.append(tb);
  const b = el('div', 'card'); b.append(el('h3', null, 'Самые вызываемые общие модули'));
  const top = O.map((o, i) => [i, calls(inE[i])]).filter(r => O[r[0]].t === 'CommonModule' && r[1] > 0).sort((x, y) => y[1] - x[1]).slice(0, 25);
  topTable(top, b, ['Модуль', 'Синоним', 'Вызовов']);
  g.append(a, b); m.append(g);
}

function subsystem(m, key) {
  const cd = el('div', 'card');
  if (key === 'none') {
    cd.append(el('h2', null, 'Объекты вне подсистем'), el('div', 'flags', 'Не входят в состав ни одной подсистемы: ' + none.length));
    objList(none, cd); m.append(cd); return;
  }
  const si = +key, s = S[si]; if (!s) { home(m); return; }
  const cr = el('div', 'crumbs'); cr.append(link('#', 'Карта')); sPath(si).forEach(x => { cr.append(' / '); cr.append(sLink(x)); });
  cd.append(cr, el('h2', null, s.s || s.n), el('div', 'flags', 'Subsystem.' + s.path.split('/').join('.Subsystem.')));
  if (kids[si].length) { cd.append(el('h3', null, 'Дочерние подсистемы')); const ch = el('div', 'chips'); kids[si].forEach(k => { const x = el('span', 'chip'); x.append(sLink(k)); ch.append(x); }); cd.append(ch); }
  objList(s.c, cd); m.append(cd);
  const all = deep(si), agg = new Map();
  all.forEach(i => outE[i].forEach(k => { const e = E[k]; if (e[3] === 'call' && O[e[1]].t === 'CommonModule') agg.set(e[1], (agg.get(e[1]) || 0) + e[2]); }));
  const cm = el('div', 'card'); cm.append(el('h3', null, 'Общие модули, которые вызывают объекты подсистемы (с дочерними)'));
  const rows = [...agg.entries()].sort((x, y) => y[1] - x[1]).slice(0, 40);
  if (rows.length) topTable(rows, cm, ['Модуль', 'Синоним', 'Вызовов']); else cm.append(el('div', 'n', 'вызовов общих модулей нет'));
  m.append(cm);
}

function edgeTable(list, side, host) {
  const rows = list.filter(k => showUse || E[k][3] === 'call').sort((a, b) => E[b][2] - E[a][2]);
  if (!rows.length) { host.append(el('div', 'n', 'нет')); return; }
  const tb = el('table');
  rows.forEach(k => { const e = E[k], other = side === 'out' ? e[1] : e[0]; const tr = el('tr'); const td = el('td'); td.append(oLink(other));
    if (e[3] === 'use') td.append(el('span', 'kind-use', ' · обращение'));
    td.append(el('div', 'smp', e[4].join('; '))); tr.append(td, el('td', 'num', String(e[2]))); tb.append(tr); });
  host.append(tb);
}

const NS = 'http://www.w3.org/2000/svg';
function sv(tag, attrs) { const x = document.createElementNS(NS, tag); for (const k in attrs) x.setAttribute(k, attrs[k]); return x; }
function short(t, n) { return t.length > n ? t.slice(0, n - 1) + '…' : t; }
function neighbourhood(i, host) {
  const pick = list => list.filter(k => showUse || E[k][3] === 'call').sort((a, b) => E[b][2] - E[a][2]).slice(0, 12);
  const L = pick(inE[i]), R = pick(outE[i]), rows = Math.max(L.length, R.length, 1);
  const W = 960, bw = 280, bh = 26, gap = 8, H = rows * (bh + gap) + 24, cx = (W - bw) / 2, cy = H / 2 - bh / 2;
  const svg = sv('svg', {viewBox: '0 0 ' + W + ' ' + H, class: 'nb', role: 'img'});
  svg.append(sv('title', {})); svg.firstChild.textContent = 'Соседи объекта: слева — кто вызывает, справа — кого вызывает';
  function box(j, x, y, me) {
    const a = sv('a', {href: '#o=' + encodeURIComponent(O[j].n)}); if (me) a.setAttribute('class', 'me');
    const t = sv('title', {}); t.textContent = O[j].n + (O[j].s ? ' — ' + O[j].s : ''); a.append(t);
    a.append(sv('rect', {x: x, y: y, width: bw, height: bh, rx: 5}));
    const tx = sv('text', {x: x + 8, y: y + 17}); tx.textContent = short(O[j].n, 38); a.append(tx); svg.append(a);
  }
  function side(list, left) {
    const off = (H - list.length * (bh + gap)) / 2;
    list.forEach((k, r) => { const e = E[k], j = left ? e[0] : e[1], x = left ? 12 : W - bw - 12, y = off + r * (bh + gap);
      const x1 = left ? x + bw : cx + bw, y1 = left ? y + bh / 2 : cy + bh / 2, x2 = left ? cx : x, y2 = left ? cy + bh / 2 : y + bh / 2, mx = (x1 + x2) / 2;
      const p = sv('path', {d: 'M' + x1 + ',' + y1 + ' C' + mx + ',' + y1 + ' ' + mx + ',' + y2 + ' ' + x2 + ',' + y2, 'stroke-width': Math.min(1 + Math.log2(e[2]), 6)});
      if (e[3] === 'use') p.setAttribute('class', 'use');
      const t = sv('title', {}); t.textContent = e[2] + ' · ' + e[4].join('; '); p.append(t); svg.append(p); box(j, x, y, false); });
  }
  side(L, true); side(R, false); box(i, cx, cy, true); host.append(svg);
}

function object(m, name) {
  const i = idx.get(name); if (i == null) { home(m); return; }
  const o = O[i], cd = el('div', 'card');
  const cr = el('div', 'crumbs'); cr.append(link('#', 'Карта'), ' / ' + tl(o.t)); cd.append(cr);
  cd.append(el('h2', null, o.n));
  if (o.s) cd.append(el('div', null, o.s));
  const info = []; if (o.f) info.push(o.f); if (o.m) info.push('модулей: ' + o.m);
  if (info.length) cd.append(el('div', 'flags', info.join(' · ')));
  cd.append(el('h3', null, 'Входит в подсистемы'));
  if (subsOf[i].length) { const ch = el('div', 'chips'); subsOf[i].forEach(si => { const x = el('span', 'chip'); sPath(si).forEach((p, n) => { if (n) x.append(' / '); x.append(sLink(p)); }); ch.append(x); }); cd.append(ch); }
  else cd.append(link('#s=none', 'вне подсистем'));
  const opt = el('label', 'opt'); const cb = el('input'); cb.type = 'checkbox'; cb.checked = showUse;
  cb.addEventListener('change', () => { showUse = cb.checked; route(); }); opt.append(cb, ' показывать обращения к менеджерам (методы платформы)');
  cd.append(el('h3', null, 'Соседи'), opt); neighbourhood(i, cd); m.append(cd);
  const g = el('div', 'grid2');
  const a = el('div', 'card'); a.append(el('h3', null, 'Вызывается из · ' + calls(inE[i]))); edgeTable(inE[i], 'in', a);
  const b = el('div', 'card'); b.append(el('h3', null, 'Вызывает · ' + calls(outE[i]))); edgeTable(outE[i], 'out', b);
  g.append(a, b); m.append(g);
}

function route() {
  const m = document.getElementById('main'); m.replaceChildren();
  const h = new URLSearchParams(location.hash.slice(1));
  if (h.has('o')) object(m, h.get('o')); else if (h.has('s')) subsystem(m, h.get('s')); else home(m);
  window.scrollTo(0, 0);
}
buildTree();
document.getElementById('q').addEventListener('input', search);
document.getElementById('q').addEventListener('keydown', ev => { if (ev.key === 'Enter') { const a = document.querySelector('#res a'); if (a) location.hash = a.getAttribute('href'); } });
window.addEventListener('hashchange', route);
route();
})();
</script>
</body>
</html>
'''

if __name__ == '__main__':
    sys.exit(main())
