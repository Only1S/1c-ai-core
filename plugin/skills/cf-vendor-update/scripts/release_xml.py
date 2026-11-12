"""Общие функции скилла cf-vendor-update: сведения выгрузки, git репозитория слияния, классы конфликтов, правила шума."""
import json
import os
import re
import subprocess
import tempfile


def dump_info(xml_dir):
    """Имя, поставщик, версия конфигурации и версия формата выгрузки из Configuration.xml."""
    p = os.path.join(xml_dir, 'Configuration.xml')
    if not os.path.isfile(p):
        return {}
    t = open(p, encoding='utf-8-sig', errors='replace').read()
    props = t.split('<ChildObjects>')[0]

    def tag(name):
        m = re.search(r'<%s>([^<]*)</%s>' % (name, name), props)
        return m.group(1) if m else ''
    fm = re.search(r'<MetaDataObject\b[^>]*\bversion="([^"]+)"', t)
    return {'name': tag('Name'), 'vendor': tag('Vendor'), 'version': tag('Version'), 'format': fm.group(1) if fm else ''}


def git(repo, *args, env=None, check=True, raw=False):
    """git в репозитории слияния; кириллица в путях — без экранирования."""
    e = dict(os.environ, **(env or {}))
    r = subprocess.run(['git', '-C', repo, '-c', 'core.quotepath=off'] + list(args), capture_output=True, env=e)
    if check and r.returncode:
        raise RuntimeError('git %s: %s' % (' '.join(args[:3]), (r.stderr or r.stdout).decode('utf-8', 'replace').strip()[-800:]))
    return r.stdout if raw else r.stdout.decode('utf-8', 'replace')


def index_blobs(repo):
    """{путь: хеш} файлов индекса без конфликта — одним вызовом: у ERP «слито автоматически» могут быть тысячи файлов."""
    out = {}
    for row in git(repo, 'ls-files', '-s', '-z').split('\0'):
        if '\t' in row:
            meta, path = row.split('\t', 1)
            if meta.split()[2] == '0':
                out[path] = meta.split()[1]
    return out


def artifact_kind(path):
    """Вид артефакта выгрузки по пути — от него зависит способ разрешения конфликта."""
    p = path.replace('\\', '/')
    name = p.rsplit('/', 1)[-1]
    if name.endswith('.bsl'):
        return 'модуль'
    if name == 'Form.xml' or name == 'Form.bin':
        return 'форма'
    if name.startswith('Template.') or '/Templates/' in p:
        return 'макет'
    if name == 'Rights.xml':
        return 'права'
    if p == 'Configuration.xml':
        return 'корень конфигурации'
    if re.match(r'^[^/]+/[^/]+\.xml$', p):
        return 'объект'
    if name.endswith('.xml'):
        return 'xml'
    return 'прочее'


def object_of(path):
    """Объект верхнего уровня, которому принадлежит файл: 'Catalogs/Номенклатура' (без .xml) или None для корня."""
    parts = path.replace('\\', '/').split('/')
    if len(parts) < 2:
        return None
    return parts[0] + '/' + (parts[1][:-4] if len(parts) == 2 and parts[1].endswith('.xml') else parts[1])


def object_uuid(xml_bytes):
    """uuid объекта верхнего уровня (первый элемент внутри MetaDataObject)."""
    t = xml_bytes[:4000].decode('utf-8', 'replace') if xml_bytes else ''
    m = re.search(r'<MetaDataObject\b[^>]*>\s*<\w+\s+uuid="([0-9a-fA-F-]{36})"', t)
    return m.group(1).lower() if m else None


# Правила шума выгрузки: отличие ветки заказчика от старого релиза, которое не является доработкой. Каждое правило — с
# примером, на котором оно сработало (../references/noise.md); пробелы внутри строки шумом не считаются: правка литерала или
# синонима — доработка, а шум с автоматическим принятием удаления поставщика стоил бы её потери.
def _strip_lines(text):
    return '\n'.join(s for s in (ln.strip() for ln in text.splitlines()) if s)


NOISE_RULES = (
    ('BOM', lambda t: t.lstrip('﻿')),
    ('переводы строк, отступы, пробелы в конце строк и пустые строки', _strip_lines),
)


def normalize(text, rules=NOISE_RULES):
    for _, fn in rules:
        text = fn(text)
    return text


def is_noise(old_bytes, ours_bytes):
    """Отличие нашей стороны от старого релиза — только шум выгрузки (по NOISE_RULES)."""
    if old_bytes is None or ours_bytes is None:
        return False
    a = normalize(old_bytes.decode('utf-8', 'replace'))
    b = normalize(ours_bytes.decode('utf-8', 'replace'))
    return a == b


def is_empty_module(data):
    """Пустой модуль (только BOM и пробельные символы) — шум выгрузки: такой файл не несёт доработки."""
    return data is not None and not normalize(data.decode('utf-8', 'replace'))


def find_ibcmd(explicit):
    """ibcmd.exe: ключ --ibcmd, затем ONEC_PLATFORM_BIN, затем v8path из .v8-project.json вверх от текущего каталога."""
    cands = []
    if explicit:
        cands.append(explicit if explicit.lower().endswith('.exe') else os.path.join(explicit, 'ibcmd.exe'))
    if os.environ.get('ONEC_PLATFORM_BIN'):
        cands.append(os.path.join(os.environ['ONEC_PLATFORM_BIN'], 'ibcmd.exe'))
    d = os.getcwd()
    while True:
        p = os.path.join(d, '.v8-project.json')
        if os.path.isfile(p):
            try:
                v8 = json.load(open(p, encoding='utf-8-sig')).get('v8path') or ''
            except ValueError:
                v8 = ''
            if v8:
                cands.append(os.path.join(v8 if not v8.lower().endswith('.exe') else os.path.dirname(v8), 'ibcmd.exe'))
            break
        up = os.path.dirname(d)
        if up == d:
            break
        d = up
    for c in cands:
        if os.path.isfile(c):
            return c
    return None


def export_tree(repo, rev, out):
    """Файлы ревизии rev (None — индекс, то есть результат слияния после git add) в каталог out без checkout в репозитории:
    временный индекс + checkout-index. .gitattributes репозитория слияния в выгрузку не кладётся. Возвращает число файлов."""
    prefix = os.path.abspath(out).replace('\\', '/').rstrip('/') + '/'
    env = None
    if rev:
        idx = os.path.join(tempfile.mkdtemp(prefix='vu-exp-'), 'index')
        env = {'GIT_INDEX_FILE': idx}
        git(repo, 'read-tree', rev, env=env)
    os.makedirs(out, exist_ok=True)
    git(repo, 'checkout-index', '-a', '-f', '--prefix=' + prefix, env=env)
    ga = os.path.join(out, '.gitattributes')
    if os.path.isfile(ga):
        os.remove(ga)
    return sum(len(fs) for _, _, fs in os.walk(out))
