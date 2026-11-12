# -*- coding: utf-8 -*-
"""Аудит бюджета комментариев в модулях 1С (правило docs/code/comment-budget.md).

Проверяет три вещи в каждом переданном .bsl:
  1) описание метода занимает РОВНО одну строку;
  2) между описанием и секциями нет абзацев прозы;
  3) внутри тел методов нет комментариев, отдельной строкой и в конце строки с кодом, кроме директив
     анализаторов, меток строк для перевода и маркеров-заглушек; «//» внутри строкового литерала
     комментарием не считается.

Запуск:  python tools/1c/bsl-comment-audit.py <файл.bsl> [<файл.bsl> ...]
Код возврата 1, если найдено хоть одно нарушение — годится для гейта перед сдачей правки.

Исправление: python tools/1c/bsl-comment-audit.py --fix --out <папка> <файл.bsl> ...
  - удаляет комментарии в телах методов (директивы @skip-check / BSLLS: остаются);
  - удаляет абзацы прозы между описанием и секциями шапки;
  - многострочное описание сокращает до первого предложения и печатает его для проверки.
Исправленные копии пишутся в <папка> с сохранением относительного пути; исходник не меняется.
Без --out исправление пишется на место — для проектов EDT так не делать: модуль загружается
в модель через write_module_source (правило docs/tools/edt-mcp-pitfalls.md).
"""
import io, os, re, sys

sys.stdout.reconfigure(encoding='utf-8')

METHOD = re.compile(r'^\s*(?:(?:Асинх|Async)\s+)?(Процедура|Функция|Procedure|Function)\s+(\w+)', re.I)
END = re.compile(r'^\s*(КонецПроцедуры|КонецФункции|EndProcedure|EndFunction)', re.I)
SECTION = re.compile(r'^\s*//\s*(Параметры|Возвращаемое значение|Parameters|Returns)\s*:', re.I)
# BSLLS:<Правило>-off/-on — штатное подавление bsl-analyzer, служебная директива, а не пояснение.
# Совпадение — по синтаксису директивы, а не по упоминанию: строка прозы со ссылкой вида
# «(v8std BSLLS:TryNumber)» директивой не является (обрывки фраз оставались при чистке 01.10.2026).
# ACC:/АПК: — подавление проверки АПК; @NON-NLS-n, @query-part-n, @Access-right-n, @NStr-n — метки строк для перевода
# (две настоящие конфигурации, 30.10.2026: больше 3400 из 11 509 комментариев в конце строк с кодом).
DIRECTIVE = re.compile(r'^\s*//\s*(@skip-check\b|@skip-warning\b|@strict-types\b|BSLLS:\w+-(?:off|on)\b|'
                       r'@non-nls\b|@query-part\b|@access-right\b|@nstr\b|(?:ACC|CAC|APK|АПК):\d+|Логика наполняется)', re.I)


def line_comment(line, in_string=False):
    """Комментарий строки кода: (его текст или '', открыт ли строковый литерал в конце строки). Многострочный литерал продолжается
    строкой с «|», между такими строками синтаксис допускает пустую строку и комментарий; иная строка — литерал уже закончился."""
    stripped = line.strip()
    if stripped.startswith('//'):
        return stripped, in_string
    if not stripped:
        return '', in_string
    in_string = in_string and stripped.startswith('|')
    for position, char in enumerate(line):
        if char == '"':
            in_string = not in_string
        elif not in_string and line.startswith('//', position):
            return line[position:].strip(), False
    return '', in_string


def audit(path):
    lines = io.open(path, encoding='utf-8-sig').read().split('\n')
    problems = []

    inside = False
    in_string = False
    for index, line in enumerate(lines):
        if END.match(line):
            inside = False
            continue

        if inside:
            comment, in_string = line_comment(line, in_string)
            if comment and not is_directive(comment):
                problems.append((index + 1, 'комментарий в теле метода', comment[:70]))
            continue

        match = METHOD.match(line)
        if not match:
            continue
        inside = True
        in_string = False

        header = []
        cursor = index - 1
        while cursor >= 0:
            current = lines[cursor].strip()
            if current.startswith('&') or current == '':
                cursor -= 1
                continue
            if current.startswith('//'):
                header.insert(0, current)
                cursor -= 1
                continue
            break

        if not header:
            continue

        description = []
        prose = []
        state = 'description'
        for item in header:
            if is_directive(item):
                continue
            if SECTION.match(item):
                state = 'sections'
                continue
            if state == 'sections':
                continue
            if item == '//':
                state = 'after-description'
                continue
            if state == 'description':
                description.append(item)
            else:
                prose.append(item)

        if len(description) > 1:
            problems.append((index + 1, 'описание из %d строк' % len(description), match.group(2)))
        if prose:
            problems.append((index + 1, 'абзац прозы в шапке (%d строк)' % len(prose), match.group(2)))

    return problems


def is_directive(text):
    return bool(DIRECTIVE.match(text))


ABBREVIATIONS = ('см', 'напр', 'т.е', 'т.п', 'т.д', 'т.к', 'e.g', 'i.e', 'etc', 'стр', 'п')
LINE_LIMIT = 120


def first_sentence(parts, indent):
    text = ' '.join(p.strip().lstrip('/').strip() for p in parts).strip()
    sentence = text
    for match in re.finditer(r'[.!?](\s|$)', text):
        candidate = text[:match.start() + 1]
        word = re.split(r'[\s(]', candidate[:-1])[-1].lower()
        if word in ABBREVIATIONS or candidate.count('(') > candidate.count(')'):
            continue
        sentence = candidate
        break
    return sentence if len(indent) + 3 + len(sentence) <= LINE_LIMIT else None


def header_range(lines, method_index):
    cursor = method_index - 1
    start = method_index
    while cursor >= 0:
        current = lines[cursor].strip()
        if current.startswith('&') or current == '':
            cursor -= 1
            continue
        if current.startswith('//'):
            start = cursor
            cursor -= 1
            continue
        break
    return start


def fix_header(lines, start, end, report, name):
    block = lines[start:end]
    comment_rows = [i for i, l in enumerate(block) if l.strip().startswith('//')]
    if not comment_rows:
        return block

    state = 'description'
    description, prose = [], []
    for i in comment_rows:
        item = block[i].strip()
        if is_directive(item):
            continue
        if SECTION.match(item):
            state = 'sections'
            continue
        if state == 'sections':
            continue
        if item == '//':
            if state == 'description' and description:
                state = 'after-description'
            continue
        if state == 'description':
            description.append(i)
        else:
            prose.append(i)

    drop = set(prose)
    replacement = {}
    if len(description) > 1:
        indent = block[description[0]][:len(block[description[0]]) - len(block[description[0]].lstrip())]
        sentence = first_sentence([block[i] for i in description], indent)
        if sentence is None:
            report.append(('ВРУЧНУЮ: первое предложение длиннее 120 символов', name))
        else:
            replacement[description[0]] = indent + '// ' + sentence
            drop.update(description[1:])
            report.append(('описание сокращено', '%s: %s' % (name, sentence)))
    if prose:
        report.append(('удалена проза в шапке (%d строк)' % len(prose), name))

    result = []
    for i, line in enumerate(block):
        if i in drop:
            continue
        result.append(replacement.get(i, line))

    collapsed = []
    for line in result:
        if line.strip() == '//' and collapsed and collapsed[-1].strip() == '//':
            continue
        collapsed.append(line)
    return collapsed


def code_fingerprint(text):
    code, in_string = [], False
    for line in text.replace('\r\n', '\n').split('\n'):
        comment, in_string = line_comment(line, in_string)
        stripped = line.strip()
        stripped = stripped[:len(stripped) - len(comment)].rstrip()
        if stripped:
            code.append(stripped)
    return code


def fix(path):
    text = io.open(path, encoding='utf-8-sig', newline='').read()
    newline = '\r\n' if '\r\n' in text else '\n'
    lines = text.split(newline)
    report = []
    output = []
    inside = False
    in_string = False
    removed_in_body = False
    pending_header_from = None

    index = 0
    while index < len(lines):
        line = lines[index]
        if inside:
            if END.match(line):
                inside = False
                output.append(line)
                index += 1
                continue
            comment, in_string = line_comment(line, in_string)
            stripped = line.strip()
            if stripped.startswith('//') and not is_directive(stripped):
                report.append(('удалён комментарий в теле', stripped[:70]))
                removed_in_body = True
                index += 1
                continue
            if stripped == '' and removed_in_body and output and output[-1].strip() == '':
                index += 1
                continue
            removed_in_body = False
            if comment and stripped != comment and not is_directive(comment):
                report.append(('удалён комментарий в теле', comment[:70]))
                line = line.rstrip()[:-len(comment)].rstrip()
            output.append(line)
            index += 1
            continue

        match = METHOD.match(line)
        if match:
            start = header_range(lines, index)
            header_lines = len(lines[start:index])
            if header_lines:
                del output[len(output) - header_lines:]
                output.extend(fix_header(lines, start, index, report, match.group(2)))
            output.append(line)
            inside = True
            in_string = False
            removed_in_body = False
            index += 1
            continue

        output.append(line)
        index += 1

    return newline.join(output), report


def main(argv):
    fix_mode = '--fix' in argv
    out_dir = None
    if '--out' in argv:
        out_dir = argv[argv.index('--out') + 1]
    paths = [a for i, a in enumerate(argv)
             if not a.startswith('--') and not (i > 0 and argv[i - 1] == '--out')]

    total = 0
    for path in paths:
        if not os.path.isfile(path):
            print('НЕТ ФАЙЛА', path)
            continue
        if fix_mode:
            fixed, report = fix(path)
            original = io.open(path, encoding='utf-8-sig', newline='').read()
            if code_fingerprint(original) != code_fingerprint(fixed):
                print('ОТКАЗ: изменился код, а не только комментарии —', path)
                total += 1
                continue
            has_bom = io.open(path, 'rb').read(3) == b'\xef\xbb\xbf'
            if out_dir:
                # абсолютный путь и путь с .. раскладываются ВНУТРИ --out: os.path.join отбросил бы out_dir
                rel = os.path.normpath(path)
                if os.path.isabs(rel) or rel == '..' or rel.startswith('..' + os.sep):
                    rel = os.path.splitdrive(os.path.abspath(path))[1].lstrip('\\/')
                target = os.path.join(out_dir, rel)
                if os.path.normcase(os.path.abspath(target)) == os.path.normcase(os.path.abspath(path)):
                    print('ОТКАЗ: --out указывает на сам исходник —', path)
                    total += 1
                    continue
            else:
                target = path
            os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
            with io.open(target, 'w', encoding='utf-8-sig' if has_bom else 'utf-8', newline='') as stream:
                stream.write(fixed)
            print(path, '->', target, '| исправлений:', len(report))
            for kind, detail in report:
                if kind != 'удалён комментарий в теле':
                    print('    %-48s %s' % (kind, detail))
            problems = audit(target)
        else:
            problems = audit(path)
        if problems:
            print(path)
            for line_number, kind, detail in problems:
                print('    строка %-6d %-32s %s' % (line_number, kind, detail))
        total += len(problems)

    print('ИТОГО нарушений бюджета комментариев:', total)
    return 1 if total else 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1:]))
