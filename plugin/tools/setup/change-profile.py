"""change-profile.py — профиль правки 1С по ТРЁМ осям, с фиксацией того, что подняло глубину.

Зачем. full-checker-set-before-done п.8 требует считать глубину проверок по классу правки; скрипт
печатает профиль из фактического содержимого правки, и доки ссылаются на него, а не на оценку по памяти.
Приём трёх осей и фиксации `driver` — Romandredan/1c-quality-gate (MIT, (c) 2026 romandredan,
README «Расчёт глубины» + tools/profile.mjs); таблицы меток и минимумов составлены заново под наш стек,
код наш.

Ось 1 — ОБЪЁМ: C0 косметика · C1 точечная · C2 модульная · C3 структурная.
Ось 2 — АРХЕТИПЫ: набор меток по маркерам в тексте и путях; у каждой свой минимум для контуров `code`
        и `arch`. Асимметрия сознательная: транзакция тянет разбор КОДА и не поднимает архитектуру,
        новый общий модуль наоборот поднимает АРХИТЕКТУРУ и не трогает код.
Ось 3 — СЛОЖНОСТЬ: закрывает «строк мало, но код тяжёлый» (вложенность, длина метода, число
        параметров, рекурсия).
Итог: глубина контура = max(по объёму, максимум минимумов сработавших архетипов, по сложности),
и отдельно печатается `driver` — что именно подняло глубину.

Запуск:
    python tools/setup/change-profile.py                       # изменённые .bsl из git (рабочее дерево + индекс)
    python tools/setup/change-profile.py --files A.bsl B.bsl   # ВЕСЬ переданный файл считается правкой
    python tools/setup/change-profile.py --json                # плюс машиночитаемый профиль одной строкой
    python tools/setup/change-profile.py --strict              # код выхода 1, если был [FAIL]

Читает: `git status --porcelain -z --untracked-files=all` и `git diff HEAD -M -- <файл>` в корне мастера
(новые файлы — целиком, переименованные — только правка), либо файлы из --files. Ничего не пишет.
Коды выхода: 0 — профиль посчитан (или правок .bsl нет); 1 — был [FAIL] и задан --strict.
"""
import argparse
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib'))
from gate import Gate, core_root, read_text  # noqa: E402

# Таблица архетипов: метка, минимум code, минимум arch, маркеры текста, маркер пути, только новый файл.
# Минимумы: 0 = не поднимает, 1..2 = уровень контура. Маркеры — по добавленному тексту и пути.
ARCHETYPES = [
    ('запрос',             2, 0, r'Новый Запрос|Запрос\.Текст|ВЫБРАТЬ\s|ПОМЕСТИТЬ\s', None, False),
    ('транзакция',         2, 0, r'НачатьТранзакцию|ЗафиксироватьТранзакцию|ОтменитьТранзакцию|БлокировкаДанных', None, False),
    ('движения регистра',  2, 1, r'НаборЗаписей|Движения\.|РегистрыНакопления\.|РегистрыСведений\.', None, False),
    ('обработчик объекта', 2, 1, r'ОбработкаПроведения|ПередЗаписью|ПриЗаписи|ОбработкаЗаполнения|ОбработкаПроверкиЗаполнения', None, False),
    ('интеграция и HTTP',  2, 2, r'HTTPСоединение|HTTPЗапрос|WSПрокси|WSСсылки|ОтправитьSMS|Новый HTTP', None, False),
    ('права и RLS',        1, 2, r'ОграничениеДоступа|RLS|Роли\.|ПравоДоступа', r'[\\/]Roles[\\/]', False),
    ('CFE-перехват',       2, 2, r'&Вместо|&После|&Перед|&ИзменениеИКонтроль', None, False),
    ('фон и регламент',    2, 1, r'РегламентноеЗадание|ФоновоеЗадание|ДлительныеОперации|ВыполнитьВФоне', None, False),
    ('клиент-сервер',      1, 1, r'&НаКлиенте|&НаСервере|&НаСервереБезКонтекста|&НаКлиентеНаСервере', None, False),
    ('модуль формы',       1, 1, r'ПриОткрытии|ПриСозданииНаСервере|ОбработкаВыбора', r'[\\/]Forms[\\/]', False),
    ('асинхронный клиент', 2, 1, r'ОписаниеОповещения|НачатьПомещениеФайла|Асинх |Ждать ', None, False),
    ('новый общий модуль', 1, 2, None, r'[\\/]CommonModules[\\/]', True),
]

IM = re.I | re.M
COMMENT_OR_BLANK = re.compile(r'^\s*(//.*)?$')


def cosmetic(added, removed):
    """Объём C0 (косметика): каждая добавленная и каждая снятая строка — комментарий или пустая.
    Закомментированный и удалённый код — не косметика. Тем же классификатором гейт конца хода (stop-guard) решает, что правка
    модуля не требует стандартов и validate_module (full-checker-set-before-done п.8, второй классификатор не заводится)."""
    return all(COMMENT_OR_BLANK.match(x) for x in list(added) + list(removed))


def split_lines(text):
    """Строки как у .NET ReadLine: разрыв — \\r\\n, \\r или \\n; завершающий разрыв пустой строки не даёт."""
    lines = re.split(r'\r\n|\r|\n', text)
    if lines and lines[-1] == '':
        lines.pop()
    return lines


def read_lines(path):
    # Режим чтения текста уже сводит \r\n и \r к \n.
    return split_lines(read_text(path))


def git_text(root, *args):
    """git в корне мастера: (код, stdout). Вывод — UTF-8, битые байты заменяются по одному,
    без отката всего вывода на другую кодировку (так читает PowerShell при UTF-8-консоли)."""
    try:
        # quotepath=off: кириллический путь .bsl приходит как есть, а не восьмеричными экранами (иначе файла «нет»)
        r = subprocess.run(['git', '-c', 'core.quotepath=off', '-C', root] + list(args), capture_output=True, timeout=600)
    except (OSError, subprocess.TimeoutExpired):
        return 1, ''
    return r.returncode, r.stdout.decode('utf-8', 'replace')


def collect_git(g, root, strict, removed=None):
    """Правка по git: новые и неотслеживаемые .bsl целиком, изменённые — добавленные строки диффа к HEAD (снятые — в removed)."""
    items = []
    rc, out = git_text(root, 'status', '--porcelain', '-z', '--untracked-files=all')
    if rc != 0:
        g.bad('git недоступен — профиль по правке посчитать нечем')
        g.summary()
        g.exit(strict)
    entries = iter(out.split('\0'))
    for line in entries:
        if not line.strip():
            continue
        flag = line[0:2]
        rel = line[3:]
        # у переименования и копии в -z за новым путём идёт старый (замер 30.10.2026: «старый -> новый» шёл одним путём,
        # дифф был пуст, и правка получала класс «низкий»)
        old = next(entries, '') if re.search(r'[RC]', flag) else ''
        if not re.search(r'\.bsl$', rel, re.I):
            continue
        full = os.path.join(root, rel)
        is_new = re.search(r'\?|A', flag, re.I) is not None
        added = []
        if is_new:
            if os.path.exists(full):
                try:
                    added = read_lines(full)
                except OSError as e:
                    print(e, file=sys.stderr)
        else:
            # оба пути и -M: иначе переименованный файл считался бы целиком новым
            _, d = git_text(root, 'diff', 'HEAD', '-M', '--', *([old, rel] if old else [rel]))
            added = [x[1:] for x in split_lines(d) if x.startswith('+') and not x.startswith('+++')]
            if removed is not None:
                removed += [x[1:] for x in split_lines(d) if x.startswith('-') and not x.startswith('---')]
        items.append((rel, added, is_new))
    return items


def collect_files(g, files):
    """Правка по списку файлов: каждый файл целиком."""
    items = []
    for f in files:
        if not os.path.exists(f):
            g.bad('файл не найден: ' + f)
            continue
        try:
            items.append((f, read_lines(f), False))
        except OSError as e:
            print(e, file=sys.stderr)
    return items


def main():
    g = Gate()  # до argparse: Gate переключает консоль на UTF-8, иначе справка в канале — кракозябры
    ap = argparse.ArgumentParser(description='Профиль правки 1С по трём осям (объём, архетипы, сложность).')
    ap.add_argument('--files', nargs='+', action='extend', default=[], help='файлы целиком как правка (вместо git)')
    ap.add_argument('--json', action='store_true', help='напечатать машиночитаемый профиль')
    ap.add_argument('--strict', action='store_true', help='код выхода 1 при [FAIL]')
    args = ap.parse_args()

    # в проекте скрипт приходит плагином (кэш плагина — не репозиторий правки): берём git проекта (аудит 30.10.2026)
    root = os.environ.get('CLAUDE_PROJECT_DIR') or ''
    if not root or not os.path.exists(os.path.join(root, '.git')):
        cwd_git = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True)
        root = cwd_git.stdout.strip() if cwd_git.returncode == 0 and cwd_git.stdout.strip() else core_root(__file__)

    # --- сбор правки ---
    removed = []
    if args.files:
        mode = 'files'
        items = collect_files(g, args.files)
    else:
        mode = 'git'
        items = collect_git(g, root, args.strict, removed)

    if not items:
        g.info('правок .bsl не найдено: профиль не считается (это не ошибка — сравнивать нечего)')
        g.summary()
        g.exit(False)

    all_added = [x for _, added, _ in items for x in added]
    added_count = len(all_added)
    file_count = len(items)
    text = '\n'.join(all_added)

    # --- ось 1: объём ---
    new_export = re.search(r'^\s*(Процедура|Функция)\b.*\bЭкспорт\b', text, IM) is not None
    new_module = any(is_new and re.search(r'[\\/]CommonModules[\\/]', p, re.I) for p, _, is_new in items)
    methods_touched = sum(1 for _ in re.finditer(r'^\s*(Процедура|Функция)\s+[A-Za-zА-Яа-яЁё_]', text, IM))
    only_comments = cosmetic(all_added, removed)   # добавлены и сняты только комментарии и пустые строки

    volume = 'C1'
    if only_comments:
        volume = 'C0'
    if methods_touched > 1 or new_export or added_count > 40 or file_count > 1:
        volume = 'C2'
    if new_module or file_count >= 4:
        volume = 'C3'

    # --- ось 2: архетипы ---
    labels = []
    min_code = 0
    min_arch = 0
    arch_driver = ''
    for label, a_code, a_arch, a_text, a_path, new_only in ARCHETYPES:
        hit = bool(a_text) and re.search('(?i)' + a_text, text) is not None
        if a_path and any(re.search(a_path, p, re.I) and (not new_only or is_new) for p, _, is_new in items):
            hit = True
        if not hit:
            continue
        labels.append(label)
        if a_code > min_code:
            min_code = a_code
            arch_driver = label
        if a_arch > min_arch:
            min_arch = a_arch
            if not arch_driver:
                arch_driver = label

    # --- ось 3: сложность ---
    cx = []
    max_nest = 0
    for x in all_added:
        m = re.match(r'\t+', x)
        if m and len(m.group()) > max_nest:
            max_nest = len(m.group())
    if max_nest >= 4:
        cx.append('вложенность %d' % max_nest)
    for sig in re.finditer(r'^\s*(?:Процедура|Функция)\s+[A-Za-zА-Яа-яЁё_0-9]+\s*\(([^)]*)\)', text, IM):
        ps = [p for p in sig.group(1).split(',') if p.strip()]
        if len(ps) >= 7:
            cx.append('параметров %d' % len(ps))
    if added_count > 120 and methods_touched <= 1:
        cx.append('метод свыше 120 строк')
    for nm in re.finditer(r'^\s*(?:Процедура|Функция)\s+([A-Za-zА-Яа-яЁё_0-9]+)', text, IM):
        name = nm.group(1)
        # рекурсия — вызов СВОЕГО имени в СВОЁМ теле (до КонецПроцедуры/КонецФункции или следующего метода),
        # с левой границей идентификатора: вызов другого метода и «ПередЗаполнить(» за «Заполнить(» не считаются
        rest = text[nm.end():]
        end = re.search(r'^\s*(?:Конец(?:Процедуры|Функции)\b|(?:Процедура|Функция)\s)', rest, IM)
        body = rest[:end.start()] if end else rest
        if re.search(r'(?<![A-Za-zА-Яа-яЁё_0-9.])' + re.escape(name) + r'\s*\(', body, re.I):
            cx.append('рекурсия ' + name)
    cx = list(dict.fromkeys(cx))   # без повторов, порядок первого появления, с учётом регистра

    # --- сложение осей ---
    base_code = {'C0': 0, 'C1': 1, 'C2': 2, 'C3': 2}[volume]
    base_arch = {'C0': 0, 'C1': 0, 'C2': 1, 'C3': 3}[volume]
    cx_code = 2 if cx else 0

    code = max(base_code, min_code, cx_code)
    arch = max(base_arch, min_arch)

    driver = 'объём:' + volume
    if min_code > base_code or min_arch > base_arch:
        driver = 'архетип:' + arch_driver
    if cx_code > max(base_code, min_code):
        driver = 'сложность:' + cx[0]

    klass = 'средний'
    if code <= 0 and arch <= 0:
        klass = 'низкий'
    if code >= 2 or arch >= 2:
        klass = 'высокий'

    # --- вывод ---
    if mode == 'files':
        g.warn('режим -Files: ВЕСЬ файл считается правкой, класс объёма завышен — для реальной правки запускать без -Files (профиль по git)')
    g.info('файлов: %d · добавленных строк: %d · затронуто методов: %d' % (file_count, added_count, methods_touched))
    g.info('ось 1 объём: ' + volume)
    g.info('ось 2 архетипы: ' + (', '.join(labels) if labels else 'нет'))
    g.info('ось 3 сложность: ' + (', '.join(cx) if cx else 'нет'))
    g.ok('глубина: code=L%d · arch=ур.%d · класс правки %s · driver=%s' % (code, arch, klass, driver))
    if code >= 2 or arch >= 2:
        g.info('по full-checker-set-before-done п.8 класс «высокий» требует ПОЛНОГО сета проверок и функционального прогона — без исключений')
    if args.json:
        payload = {
            'mode': mode, 'files': file_count, 'addedLines': added_count, 'methods': methods_touched,
            'volume': volume, 'archetypes': labels, 'complexity': cx,
            'code': code, 'arch': arch, 'class': klass, 'driver': driver,
        }
        print(json.dumps(payload, ensure_ascii=False, separators=(',', ':')), flush=True)
    g.summary()
    g.exit(args.strict)


if __name__ == '__main__':
    main()
