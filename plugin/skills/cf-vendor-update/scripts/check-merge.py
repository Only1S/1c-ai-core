"""Проверки результата слияния до импорта в базу: висячие ссылки, права ролей, объекты «Удалить…», формы, состав.

Использование:
  python check-merge.py --repo <репозиторий слияния> [--report <каталог отчёта>] [--all]

Проверяется рабочий каталог репозитория (результат слияния). Импорт и коммит берут индекс, поэтому расхождение с индексом —
ошибка. Ссылки и права ищутся в нашей дельте — файлах, которые отличаются от нового релиза (--all — во всех файлах). Проверки:
  неразрешённое        — пути с конфликтом в индексе, маркеры конфликта <<<<<<< ======= >>>>>>> в файлах;
  без git add          — файл на диске отличается от индекса, удалён с диска или не добавлен в индекс;
  XML                  — файл XML не разбирается;
  состав               — объект в Configuration.xml без файла, файл объекта не в составе, объект в составе дважды;
  сирота               — файлы внутри объекта, описания которого нет (поставщик удалил объект, наш файл остался);
  ссылка на удалённый  — XML (тип cfg:CatalogRef.Имя с любым префиксом пространства current-config, Catalog.Имя, тексты
                         запросов query и QueryText) и модули (Справочники.Имя, «Справочник.Имя» в тексте запроса,
                         ОбщийМодуль.Метод; регистр букв не важен) ссылаются на объект, который был в старом релизе или у
                         нас, а после слияния его нет; подсказка — новое имя по тому же uuid (поставщик переименовал);
  право роли           — право на объект, реквизит, табличную часть, команду, измерение, ресурс… которого нет;
  «Удалить…»           — наша дельта ссылается на объект, помеченный поставщиком к удалению (Удалить…/Delete…), а у
                         поставщика в этом файле такой ссылки нет; отдельно — список объектов, которые поставщик так
                         пометил (тот же uuid, новое имя);
  форма                — повтор id в форме (элементы, реквизиты, команды, колонки реквизита — свои пространства).
Отчёт: check-report.md и check-report.json рядом с merge-report. В JSON — tree: хеш индекса (git write-tree) на момент
проверки; import-check.py по нему видит, что проверка устарела. Коды: 0 — ошибок нет, 3 — есть ошибки (предупреждения кода
не меняют), 1 — ошибка git, 2 — неверные аргументы.
"""
import argparse
import bisect
import collections
import json
import os
import re
import subprocess
import sys
import xml.parsers.expat

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from release_xml import git, object_uuid  # noqa: E402
import xml_merge  # noqa: E402

# Менеджеры встроенного языка: тип метаданных → (множественное рус., единственное рус.); английские — имя каталога
# выгрузки и тег типа. Имена сверены по справке платформы (bsl-context, bsl-platform) 30.10.2026.
RU_NAMES = {'Catalog': ('Справочники', 'Справочник'), 'Document': ('Документы', 'Документ'),
            'Enum': ('Перечисления', 'Перечисление'), 'InformationRegister': ('РегистрыСведений', 'РегистрСведений'),
            'AccumulationRegister': ('РегистрыНакопления', 'РегистрНакопления'),
            'AccountingRegister': ('РегистрыБухгалтерии', 'РегистрБухгалтерии'),
            'CalculationRegister': ('РегистрыРасчета', 'РегистрРасчета'), 'ChartOfAccounts': ('ПланыСчетов', 'ПланСчетов'),
            'ChartOfCharacteristicTypes': ('ПланыВидовХарактеристик', 'ПланВидовХарактеристик'),
            'ChartOfCalculationTypes': ('ПланыВидовРасчета', 'ПланВидовРасчета'),
            'BusinessProcess': ('БизнесПроцессы', 'БизнесПроцесс'), 'Task': ('Задачи', 'Задача'),
            'ExchangePlan': ('ПланыОбмена', 'ПланОбмена'), 'DataProcessor': ('Обработки', 'Обработка'),
            'Report': ('Отчеты', 'Отчет'), 'Constant': ('Константы', 'Константа'),
            'DocumentJournal': ('ЖурналыДокументов', 'ЖурналДокументов'), 'FilterCriterion': ('КритерииОтбора', 'КритерийОтбора')}
SUFFIX_RU = 'Ссылка|Объект|Менеджер|Выборка|Список|НаборЗаписей|МенеджерЗаписи|КлючЗаписи|Запись|ТабличнаяЧасть|СтрокаТабличнойЧасти'
SUFFIX_EN = 'Ref|Object|Manager|Selection|List|RecordSet|RecordManager|RecordKey|Record|TabularSection|TabularSectionRow'
DELETE_PREFIX = re.compile(r'^(?:Удалить|Delete)(?![a-zа-яё])')
SKIP_PARTS = ('StandardAttribute', 'StandardTabularSection')
TEXT_EXT = ('.xml', '.bsl', '.txt', '.html', '.htm', '.json', '.xsd', '.wsdl')
MARKER = re.compile(r'^(?:<{7} |>{7} |={7}\r?$)', re.M)
WORD = re.compile(r'[^\W\d]\w*')
CFG_PREFIX = re.compile(r'xmlns:([\w.-]+)="http://v8\.1c\.ru/8\.1/data/enterprise/current-config"')
XML_PREFIX = re.compile(r'[\w.-]+$')
# запрос схемы компоновки и динамического списка; вложенных тегов внутри нет: текст запроса экранирован
QUERY_TEXT = re.compile(r'<(?:[\w.-]+:)?(query|QueryText)(?:\s[^>]*)?>(.*?)</(?:[\w.-]+:)?\1>', re.S)
QUERY_COMMENT = re.compile(r'//[^\r\n]*')


class DirTree:
    """Файлы каталога (рабочий каталог слияния или выгрузка)."""

    def __init__(self, root, paths=None):
        self.root = root
        if paths is None:
            paths = set()
            for d, _, fs in os.walk(root):
                if '.git' in d.split(os.sep):
                    continue
                for f in fs:
                    paths.add(os.path.relpath(os.path.join(d, f), root).replace('\\', '/'))
        self.paths = set(p for p in paths if os.path.isfile(os.path.join(root, *p.split('/'))))

    def read(self, path):
        if path not in self.paths:
            return None
        return open(os.path.join(self.root, *path.split('/')), 'rb').read()

    def head(self, path):
        if path not in self.paths:
            return None
        with open(os.path.join(self.root, *path.split('/')), 'rb') as f:
            return f.read(4000)


class RevTree:
    """Файлы ревизии git (старый релиз, наша ветка, новый релиз) — чтение через git cat-file --batch."""

    def __init__(self, repo, rev):
        self.repo, self.rev, self.proc = repo, rev, None
        self.paths = set(git(repo, 'ls-tree', '-r', '--name-only', '-z', rev).split('\0')) - {''}

    def read(self, path):
        if path not in self.paths:
            return None
        if self.proc is None:
            self.proc = subprocess.Popen(['git', '-C', self.repo, 'cat-file', '--batch'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        self.proc.stdin.write(('%s:%s\n' % (self.rev, path)).encode('utf-8'))
        self.proc.stdin.flush()
        head = self.proc.stdout.readline().split()
        if len(head) < 3 or head[1] != b'blob':
            return None
        data = self.proc.stdout.read(int(head[2]))
        self.proc.stdout.read(1)
        return data

    def head(self, path):
        data = self.read(path)
        return data[:4000] if data is not None else None

    def close(self):
        if self.proc:
            self.proc.stdin.close()
            self.proc.wait()


class Lines:
    """Номер строки по позиции в тексте — бинарным поиском по переводам строк (подсчёт на каждую находку квадратичен)."""

    def __init__(self, text):
        self.nl = [m.start() for m in re.finditer('\n', text)]

    def at(self, pos):
        return bisect.bisect_left(self.nl, pos) + 1


def xml_error(data):
    """Ошибка формы XML (expat) или None."""
    p = xml.parsers.expat.ParserCreate()
    try:
        p.Parse(data, True)
    except xml.parsers.expat.ExpatError as e:
        return str(e)
    return None


def top_objects(tree):
    """{(каталог, имя): путь XML} объектов верхнего уровня."""
    out = {}
    for p in tree.paths:
        m = re.match(r'^([^/]+)/([^/]+)\.xml$', p)
        if m:
            out[(m.group(1), m.group(2))] = p
    return out


def folder_types(*trees):
    """Каталог выгрузки → тег типа метаданных (Catalogs → Catalog) по первому файлу каталога — из данных, а не по таблице."""
    out = {}
    for tree in trees:
        firsts = {}
        for (folder, _), p in sorted(top_objects(tree).items()):
            firsts.setdefault(folder, p)
        for folder, p in firsts.items():
            if folder in out:
                continue
            data = tree.head(p) or b''
            m = re.search(rb'<MetaDataObject\b[^>]*>\s*<(\w+)[\s>]', data)
            if m:
                out[folder] = m.group(1).decode('ascii')
    return out


def bsl_parts(text):
    """По строкам модуля: (номер, код без комментариев, [строковые литералы]) — многострочные литералы через «|» учтены;
    пустая строка и строка-комментарий между строками «|» литерал не закрывают (на ERP 2.5.20 это 11,4% ссылок в строках)."""
    in_str = False
    for no, line in enumerate(text.splitlines(), 1):
        code, strs, cur, i = [], [], [], 0
        if in_str:
            st = line.lstrip()
            if st.startswith('|'):
                i = len(line) - len(st) + 1
            elif not st or st.startswith('//'):
                continue
            else:
                in_str = False
        n = len(line)
        while i < n:
            ch = line[i]
            if in_str:
                if ch == '"':
                    if i + 1 < n and line[i + 1] == '"':
                        cur.append('"')
                        i += 2
                        continue
                    in_str = False
                    strs.append(''.join(cur))
                    cur = []
                else:
                    cur.append(ch)
            elif ch == '"':
                in_str = True
            elif line.startswith('//', i):
                break
            else:
                code.append(ch)
            i += 1
        if in_str:
            strs.append(''.join(cur))
        yield no, ''.join(code), strs


class Checker:
    def __init__(self, merged, base, custom, new):
        self.merged, self.base, self.custom, self.new = merged, base, custom, new
        self.findings = []
        self.types = folder_types(merged, base, custom)
        self.folder_of = {t: f for f, t in self.types.items()}
        self.present = top_objects(merged)
        self.was = top_objects(custom)
        self.was.update(top_objects(base))
        self.deleted = collections.defaultdict(set)   # тег типа → имена, которые были и исчезли
        for (folder, name) in self.was:
            if (folder, name) not in self.present and folder in self.types:
                self.deleted[self.types[folder]].add(name)
        self.delete_marked = {(self.types[f], n) for (f, n) in self.present if f in self.types and DELETE_PREFIX.match(n)}
        # встроенный язык и язык запросов не различают регистр: имена сравниваются в нижнем регистре
        self.deleted_lc = {t: {n.lower(): n for n in names} for t, names in self.deleted.items()}
        self.marked_lc = {(t, n.lower()): n for t, n in self.delete_marked}
        self._uuid_index, self._objects = {}, {}
        en = sorted(self.types.values(), key=len, reverse=True)
        alt_en = '|'.join(en)
        # префикс пространства current-config бывает любым (d5p1: в схемах ERP) — он проверяется по объявлениям в файле
        self.re_cfg = re.compile(r':(%s)(?:%s)?\.([^\W\d][\w]*)' % (alt_en, SUFFIX_EN))
        self.re_mdref = re.compile(r'>(%s)\.([^\W\d][\w]*)(?:\.[^<]*)?<' % alt_en)
        plural = {}
        for t in self.types.values():
            plural[self.folder_of[t]] = t
            if t in RU_NAMES:
                plural[RU_NAMES[t][0]] = t
        singular = {t: t for t in self.types.values()}
        singular.update({RU_NAMES[t][1]: t for t in self.types.values() if t in RU_NAMES})
        self.plural = {k.lower(): v for k, v in plural.items()}
        self.singular = {k.lower(): v for k, v in singular.items()}
        # перед менеджером точка допустима: Метаданные.Справочники.Имя, Metadata.Catalogs.Name
        self.re_plural = re.compile(r'(?<!\w)(%s)\s*\.\s*([^\W\d][\w]*)' % '|'.join(sorted(plural, key=len, reverse=True)), re.I)
        self.re_singular = re.compile(r'(?<![\w.])(%s)(?:%s|%s)?\.([^\W\d][\w]*)' % (
            '|'.join(sorted(singular, key=len, reverse=True)), SUFFIX_RU, SUFFIX_EN), re.I)
        cm = sorted(self.deleted.get('CommonModule', ()), key=len, reverse=True)
        self.re_cm = re.compile(r'(?<![\w.])(%s)\s*\.\s*[^\W\d]' % '|'.join(map(re.escape, cm)), re.I) if cm else None

    def add(self, check, severity, path, message, line=None, hint=None):
        self.findings.append({k: v for k, v in (('check', check), ('severity', severity), ('path', path), ('line', line),
                                                 ('message', message), ('hint', hint)) if v is not None})

    # ---------- переименование по uuid ----------
    def renamed(self, typ, name):
        """Новое имя объекта по uuid старого (поставщик переименовал, например в Удалить…) или None."""
        folder = self.folder_of.get(typ)
        if not folder:
            return None
        p = '%s/%s.xml' % (folder, name)
        u = object_uuid(self.base.head(p) or self.custom.head(p) or b'')
        if not u:
            return None
        if folder not in self._uuid_index:
            idx = {}
            for (f, n), path in self.present.items():
                if f == folder:
                    uu = object_uuid(self.merged.head(path) or b'')
                    if uu:
                        idx[uu] = n
            self._uuid_index[folder] = idx
        return self._uuid_index[folder].get(u)

    def ref(self, check, path, line, typ, name, vendor_text):
        """Ссылка нашей дельты на объект: удалён — ошибка, помечен «Удалить…» и у поставщика её нет — предупреждение."""
        low = name.lower()
        gone = self.deleted_lc.get(typ, {}).get(low)
        if gone:
            new_name = self.renamed(typ, gone)
            self.add(check, 'ошибка', path, 'ссылка на удалённый объект %s.%s' % (typ, gone), line,
                     'поставщик переименовал в %s (тот же uuid) — ссылку переименовать' % new_name if new_name else
                     'объекта нет ни у поставщика, ни у нас после слияния — перенести доработку или убрать ссылку')
        elif (typ, low) in self.marked_lc and low not in vendor_text.lower():
            self.add('Удалить…', 'предупреждение', path, 'доработка ссылается на объект %s.%s, помеченный к удалению' % (
                typ, self.marked_lc[(typ, low)]), line, 'перевести доработку на замену, которую дал поставщик')

    # ---------- проверки файлов ----------
    def check_xml_refs(self, path, text, vendor_text, lines):
        prefixes = {'cfg'} | set(CFG_PREFIX.findall(text))
        for m in self.re_cfg.finditer(text):
            pre = XML_PREFIX.search(text, max(0, m.start() - 40), m.start())
            if pre and pre.group(0) in prefixes and self.known(m.group(1), m.group(2)):
                self.ref('ссылка на удалённый', path, lines.at(m.start()), m.group(1), m.group(2), vendor_text)
        for m in self.re_mdref.finditer(text):
            if self.known(m.group(1), m.group(2)):
                self.ref('ссылка на удалённый', path, lines.at(m.start()), m.group(1), m.group(2), vendor_text)
        for q in QUERY_TEXT.finditer(text):
            body = QUERY_COMMENT.sub(lambda c: ' ' * len(c.group(0)), q.group(2))   # позиции сохраняются: по ним считается строка
            for m in self.re_singular.finditer(body):
                self.ref('ссылка на удалённый', path, lines.at(q.start(2) + m.start()), self.singular[m.group(1).lower()], m.group(2), vendor_text)

    def known(self, typ, name):
        low = name.lower()
        return low in self.deleted_lc.get(typ, ()) or (typ, low) in self.marked_lc

    def check_bsl(self, path, text, vendor_text):
        for no, code, strs in bsl_parts(text):
            for m in self.re_plural.finditer(code):
                self.ref('ссылка на удалённый', path, no, self.plural[m.group(1).lower()], m.group(2), vendor_text)
            if self.re_cm:
                for m in self.re_cm.finditer(code):
                    self.ref('ссылка на удалённый', path, no, 'CommonModule', m.group(1), vendor_text)
            for s in strs:
                for m in self.re_singular.finditer(s):
                    self.ref('ссылка на удалённый', path, no, self.singular[m.group(1).lower()], m.group(2), vendor_text)

    def obj_root(self, typ, name):
        key = (typ, name)
        if key not in self._objects:
            folder = self.folder_of.get(typ)
            data = self.merged.read('%s/%s.xml' % (folder, name)) if folder else None
            try:
                self._objects[key] = xml_merge.parse(data.decode('utf-8')).children[0].children[0] if data else None
            except (xml_merge.XmlError, UnicodeDecodeError, IndexError):
                self._objects[key] = None
        return self._objects[key]

    def sub_root(self, typ, name, kind, sub):
        """Описание подчинённого объекта отдельным файлом: таблица внешнего источника — <Таблица> в ChildObjects лишь именем,
        поля в <Источник>/Tables/<имя>.xml. Файла нет — None: глубже проверять нечем, ложной ошибки быть не должно."""
        data = self.merged.read('%s/%s/%ss/%s.xml' % (self.folder_of[typ], name, kind, sub))
        try:
            return xml_merge.parse(data.decode('utf-8')).children[0].children[0] if data else None
        except (xml_merge.XmlError, UnicodeDecodeError, IndexError):
            return None

    def base_child_uuid(self, typ, name, parts):
        """uuid подчинённого объекта по пути parts [(вид, имя)] в старом релизе или нашей ветке."""
        folder = self.folder_of.get(typ)
        for tree in (self.base, self.custom):
            data = tree.read('%s/%s.xml' % (folder, name)) if folder else None
            try:
                cur = xml_merge.parse(data.decode('utf-8')).children[0].children[0] if data else None
            except (xml_merge.XmlError, UnicodeDecodeError, IndexError):
                cur = None
            for kind, nm in parts:
                co = cur.child('ChildObjects') if cur is not None else None
                cur = next((c for c in co.children if c.tag == kind and c.prop_name() == nm), None) if co is not None else None
            if cur is not None and cur.attrs.get('uuid'):
                return cur.attrs['uuid']
        return None

    def check_rights(self, path, text, lines):
        try:
            root = xml_merge.parse(text).children[0]
        except xml_merge.XmlError:
            return
        for obj in root.children:
            if xml_merge.local_name(obj.tag) != 'object':
                continue
            nm = obj.child('name')
            full = nm.text if nm is not None else ''
            parts = full.split('.')
            if len(parts) < 2 or parts[0] not in self.folder_of:
                continue
            typ, name = parts[0], parts[1]
            line = lines.at(obj.start)
            if (self.folder_of[typ], name) not in self.present:
                new_name = self.renamed(typ, name) if name in self.deleted.get(typ, ()) else None
                self.add('право роли', 'ошибка', path, 'право на несуществующий объект %s' % full, line,
                         'поставщик переименовал в %s (тот же uuid) — право переименовать' % new_name if new_name else
                         'объекта нет — убрать права на него или перенести на замену')
                continue
            if typ == 'Subsystem':
                sub = 'Subsystems/' + name
                for kind, nm2 in zip(parts[2::2], parts[3::2]):
                    sub += '/Subsystems/' + nm2
                    if kind != 'Subsystem' or sub + '.xml' not in self.merged.paths:
                        self.add('право роли', 'ошибка', path, 'право на несуществующую подсистему %s' % full, line)
                        break
                continue
            cur, walked = self.obj_root(typ, name), []
            for kind, nm2 in zip(parts[2::2], parts[3::2]):
                if kind in SKIP_PARTS or cur is None:
                    break
                co = cur.child('ChildObjects')
                nxt = next((c for c in co.children if c.tag == kind and (c.prop_name() == nm2 or not c.children and c.text == nm2)),
                           None) if co is not None else None
                walked.append((kind, nm2))
                if nxt is None:
                    hint = None
                    u = self.base_child_uuid(typ, name, walked)
                    if u and co is not None:
                        same = next((c for c in co.children if c.attrs.get('uuid') == u), None)
                        if same is not None:
                            hint = 'переименован в %s (тот же uuid) — право переименовать' % same.prop_name()
                    self.add('право роли', 'ошибка', path, 'право на несуществующий %s %s в %s.%s' % (kind, nm2, typ, name), line,
                             hint or 'убрать право или перенести на замену')
                    break
                cur = nxt if nxt.children else self.sub_root(typ, name, kind, nm2)

    def check_form(self, path, text, lines):
        try:
            root = xml_merge.parse(text).children[0]
        except xml_merge.XmlError:
            return
        spaces = collections.defaultdict(list)

        def walk(node, space, section):
            """Элементы формы — одно пространство id на всю форму; в разделах Attributes/Commands/Parameters пространство —
            непосредственный родитель: колонки реквизита и каждый набор AdditionalColumns table=… нумеруются заново
            (сверено на 3682 формах ERP 2.5.20)."""
            for c in node.children:
                ln = xml_merge.local_name(c.tag)
                if node is root and ln in ('Attributes', 'Commands', 'Parameters'):
                    walk(c, ln, True)
                    continue
                if 'id' in c.attrs:
                    spaces[space].append((c.attrs['id'], c.attrs.get('name', ''), lines.at(c.start)))
                walk(c, space + '/' + (c.attrs.get('name') or c.attrs.get('table') or ln) if section else space, section)
        walk(root, 'элементы', False)
        for sp, items in spaces.items():
            seen = {}
            for i, name, line in items:
                if i in seen:
                    self.add('форма', 'ошибка', path, 'повтор id=%s (%s): «%s» и «%s»' % (i, sp, seen[i], name), line,
                             'после слияния формы перенумеровать id одного из элементов (form-edit), затем form-validate')
                else:
                    seen[i] = name

    def check_composition(self):
        data = self.merged.read('Configuration.xml')
        if data is None:
            self.add('состав', 'ошибка', 'Configuration.xml', 'нет Configuration.xml')
            return
        try:
            cfg = xml_merge.parse(data.decode('utf-8')).children[0].children[0]
        except (xml_merge.XmlError, UnicodeDecodeError, IndexError) as e:
            self.add('состав', 'ошибка', 'Configuration.xml', 'Configuration.xml не разбирается: %s' % e)
            return
        co = cfg.child('ChildObjects')
        listed = collections.Counter((c.tag, c.text) for c in (co.children if co is not None else []))
        for (tag, name), n in listed.items():
            if n > 1:
                self.add('состав', 'ошибка', 'Configuration.xml', 'объект %s.%s в составе %d раза' % (tag, name, n))
            folder = self.folder_of.get(tag)
            if folder and (folder, name) not in self.present:
                self.add('состав', 'ошибка', 'Configuration.xml', 'в составе %s.%s, а файла %s/%s.xml нет' % (tag, name, folder, name))
        for (folder, name) in self.present:
            tag = self.types.get(folder)
            if tag and (tag, name) not in listed:
                self.add('состав', 'ошибка', '%s/%s.xml' % (folder, name), 'файл объекта есть, а в составе Configuration.xml его нет')
        # сирота: файлы внутри объекта, описания которого нет (поставщик удалил объект, наш модуль или форма остались)
        orphans = collections.defaultdict(list)
        for p in self.merged.paths:
            parts = p.split('/')
            if len(parts) >= 3 and parts[0] in self.types and (parts[0], parts[1]) not in self.present:
                orphans['%s/%s' % (parts[0], parts[1])].append(p)
        for obj, files in sorted(orphans.items()):
            self.add('сирота', 'ошибка', files[0], 'файлы объекта %s, а описания %s.xml нет: %d (импорт на них остановится)' % (
                obj, obj, len(files)), hint='удалить вместе с объектом или перенести доработку — решение владельца')

    def run(self, delta, unmerged, unstaged=()):
        for p in unmerged:
            self.add('неразрешённое', 'ошибка', p, 'конфликт слияния не разрешён (resolve-merge.py, затем вручную)')
        for p in unstaged:
            self.add('без git add', 'ошибка', p, 'файл на диске не совпадает с индексом: проверка видит диск, импорт и коммит — индекс',
                     hint='git add или git rm, затем повторить check-merge')
        self.check_composition()
        # модуль разбирается построчно, только если в нём есть имя удалённого или помеченного к удалению объекта
        cands = set(n.lower() for names in self.deleted.values() for n in names) | {n.lower() for _, n in self.delete_marked}
        for path in sorted(delta):
            data = self.merged.read(path)
            if data is None or not path.lower().endswith(TEXT_EXT):
                continue
            text = data.decode('utf-8', 'replace')
            lines = Lines(text)
            markers = False
            for m in MARKER.finditer(text):
                markers = True
                self.add('неразрешённое', 'ошибка', path, 'маркер конфликта в файле', lines.at(m.start()))
            vendor = (self.new.read(path) or b'').decode('utf-8', 'replace') if path in self.new.paths else ''
            if path.endswith('.xml') and (markers or path in unmerged):
                continue   # файл с конфликтом уже в отчёте; «не разбирается» было бы его дублем
            if path.endswith('.xml'):
                err = xml_error(data)
                if err:
                    self.add('XML', 'ошибка', path, 'XML не разбирается: %s' % err)
                    continue
                if path.endswith('/Ext/Rights.xml'):
                    self.check_rights(path, text, lines)
                    continue
                if path.endswith('/Ext/Form.xml'):
                    self.check_form(path, text, lines)
                self.check_xml_refs(path, text, vendor, lines)
            elif path.endswith('.bsl') and cands & set(WORD.findall(text.lower())):
                self.check_bsl(path, text, vendor)
        return self.findings

    def vendor_marked(self):
        """Объекты, которые поставщик пометил к удалению переименованием (тот же uuid): [(тип, старое, новое)]."""
        out = []
        for typ, names in self.deleted.items():
            for name in sorted(names):
                nn = self.renamed(typ, name)
                if nn and DELETE_PREFIX.match(nn):
                    out.append((typ, name, nn))
        return out


def main():
    ap = argparse.ArgumentParser(description='Проверки результата слияния до импорта в базу')
    ap.add_argument('--repo', required=True)
    ap.add_argument('--report', help='каталог отчёта (по умолчанию — рядом с репозиторием, там же merge-report.json)')
    ap.add_argument('--all', action='store_true', help='проверять ссылки и права во всех файлах, а не только в нашей дельте')
    a = ap.parse_args()
    repo = os.path.abspath(a.repo)
    report = os.path.abspath(a.report or repo.rstrip(os.sep) + '-report')
    mr = os.path.join(report, 'merge-report.json')
    if not os.path.isdir(os.path.join(repo, '.git')) or not os.path.isfile(mr):
        print('нет репозитория слияния или отчёта %s — сначала merge-release.py' % mr)
        return 2
    rep = json.load(open(mr, encoding='utf-8'))
    old, new = rep['old'], rep['new']
    try:
        unmerged = sorted(set(l.split('\t', 1)[1] for l in git(repo, 'ls-files', '-u', '-z').split('\0') if '\t' in l))
        merged = DirTree(repo, set(p for p in git(repo, 'ls-files', '-z').split('\0') if p) - {'.gitattributes'})
        base, custom, newt = RevTree(repo, old), RevTree(repo, 'custom'), RevTree(repo, new)
        delta = merged.paths if a.all else set(p for p in git(repo, 'diff', '--name-only', '-z', new).split('\0') if p)
        tree = None if unmerged else git(repo, 'write-tree').strip()
        unstaged = sorted(set(p for args in (('diff', '--name-only', '-z'), ('ls-files', '--others', '--exclude-standard', '-z'))
                              for p in git(repo, *args).split('\0') if p) - set(unmerged))
    except RuntimeError as e:
        print(e)
        return 1
    ch = Checker(merged, base, custom, newt)
    findings = ch.run(delta, unmerged, unstaged)
    marked = ch.vendor_marked()
    for t in (base, custom, newt):
        t.close()
    errors = [f for f in findings if f['severity'] == 'ошибка']
    by = collections.Counter((f['check'], f['severity']) for f in findings)
    json.dump({'old': old, 'new': new, 'tree': tree, 'delta': len(delta), 'errors': len(errors), 'findings': findings,
               'vendor_marked': [{'type': t, 'old': o, 'new': n} for t, o, n in marked]},
              open(os.path.join(report, 'check-report.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    md = ['# Проверка результата слияния %s → custom' % new, '',
          'Файлов в нашей дельте: %d. Ошибок: **%d**, предупреждений: %d.' % (len(delta), len(errors), len(findings) - len(errors)), '']
    if by:
        md += ['| Проверка | Важность | Находок |', '|---|---|---|'] + ['| %s | %s | %d |' % (c, s, n) for (c, s), n in by.most_common()]
    for sev in ('ошибка', 'предупреждение'):
        items = [f for f in findings if f['severity'] == sev]
        if items:
            md += ['', '## %s (%d)' % ({'ошибка': 'Ошибки', 'предупреждение': 'Предупреждения'}[sev], len(items)), '']
            for f in items[:300]:
                md.append('- `%s%s` — %s: %s%s' % (f['path'], ':%d' % f['line'] if f.get('line') else '', f['check'], f['message'],
                                                   ('. ' + f['hint']) if f.get('hint') else ''))
    if marked:
        md += ['', '## Поставщик пометил к удалению (%d)' % len(marked), ''] + ['- %s.%s → %s' % m for m in marked[:200]]
    open(os.path.join(report, 'check-report.md'), 'w', encoding='utf-8', newline='\n').write('\n'.join(md) + '\n')
    print('проверка слияния: ошибок %d, предупреждений %d (%s)' % (len(errors), len(findings) - len(errors),
                                                                  ', '.join('%s %d' % (c, n) for (c, _), n in by.most_common())))
    print('отчёт: %s' % os.path.join(report, 'check-report.md'))
    return 3 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
