"""Разбор тела файла .feature для валидатора Vanessa (наш модуль рядом с вендорным validate.py, реестр vendor-patches).

Вендорный обход знал три заголовка и семь ключевых слов, сравнивал начало строки без границы слова и не следил за
блоками \"\"\": шаги «Структуры сценария», шаги на «Допустим», «Если», строка без ключевого слова и файл без сценариев
проходили с кодом 0, а строка кода «Итог = 1;» в блоке считалась шагом. Здесь — один проход по файлу, от него зависят и
проверка шагов, и проверка кавычек.
"""
import re

BACKGROUND_HEADERS = ('Контекст:', 'Предыстория:')
SCENARIO_HEADERS = ('Сценарий:', 'Пример:', 'Структура сценария:', 'Шаблон сценария:')
FEATURE_HEADERS = ('Функционал:', 'Функция:', 'Функциональность:', 'Свойство:', 'Фича:', 'Правило:')
EXAMPLES_HEADER = 'Примеры:'
# все ключевые слова шага русского Gherkin плюс «Если» Turbo Gherkin; граница слова обязательна: «Итог», «Номер», «Иначе»
KEYWORD = re.compile(r'(?:Дано|Допустим|Пусть|Когда|Если|Тогда|То|Затем|И|Также|К тому же|Но|А|Иначе)(?=[\s:]|$)', re.I)
ELSE_ONLY = re.compile(r'Иначе:?$', re.I)
ELSE_IF = re.compile(r'ИначеЕсли\s+(.*)$', re.I)
FENCES = ('"""', '```')


def walk(lines):
    """Проход по строкам файла: {'steps': [(строка, текст шага)], 'problems': [(строка, текст, что не так, подсказка)],
    'scenarios': число сценариев}. Текст шага — первая строка и строки таблицы; блок \"\"\" не разбирается."""
    steps, problems, scenarios = [], [], 0
    header = None            # (строка, текст) открытого сценария или контекста, в котором пока нет шагов
    in_body = in_examples = seen_step = False
    fence = fence_line = None
    current = None

    def flush():
        nonlocal current
        if current:
            steps.append((current[0], '\n'.join(current[1])))
            current = None

    def close_body():
        nonlocal header
        flush()
        if header:
            problems.append((header[0], header[1], 'В сценарии нет ни одного шага',
                             'Добавьте шаги из библиотеки: строка без ключевого слова считается описанием, а не шагом'))
        header = None

    for no, raw in enumerate(lines, 1):
        s = raw.strip()
        if fence:
            if s == fence:
                fence = None
            continue
        if s.startswith(FENCES):
            if in_body and not in_examples:
                fence, fence_line = s[:3], no
            continue
        if not s or s.startswith(('#', '@')):
            continue
        if s.startswith(FEATURE_HEADERS):
            close_body()
            in_body = in_examples = False
            continue
        if s.startswith(BACKGROUND_HEADERS + SCENARIO_HEADERS):
            close_body()
            scenarios += 1 if s.startswith(SCENARIO_HEADERS) else 0
            header, in_body, in_examples, seen_step = (no, s), True, False, False
            continue
        if s.startswith(EXAMPLES_HEADER):
            flush()
            in_examples = True
            continue
        if not in_body or in_examples:
            continue
        if s.startswith('|'):
            if current:
                current[1].append(s)
            continue
        if s.startswith('*') or ELSE_ONLY.match(s):   # группа шагов и «Иначе» Turbo Gherkin — служебные строки, не шаги
            flush()
            continue
        else_if = ELSE_IF.match(s)
        text = 'Если ' + else_if.group(1) if else_if else s
        if KEYWORD.match(text):
            flush()
            header, seen_step = None, True
            current = (no, [text])
        elif seen_step:                               # до первого шага это описание сценария, после — потерянный шаг
            flush()
            problems.append((no, s, 'Строка без ключевого слова шага',
                             'Начните строку с ключевого слова (Дано, Когда, Тогда, И, Но, Если), шаг берите из библиотеки'))
    close_body()
    if fence:
        problems.append((fence_line, fence, 'Многострочный блок не закрыт', 'Закройте блок строкой %s' % fence))
    return {'steps': steps, 'problems': problems, 'scenarios': scenarios}


def has_single_quoted(line):
    """Есть ли параметр целиком в одинарных кавычках. Апостроф внутри значения в двойных кавычках — часть значения; значение
    с двойными кавычками внутри можно записать только в одинарных («ООО "Вектор"»), поэтому это тоже не ошибка."""
    i, n = 0, len(line)
    while i < n:
        ch = line[i]
        if ch in '"\'':
            j = line.find(ch, i + 1)
            if j < 0:
                return False
            if ch == "'" and '"' not in line[i + 1:j]:
                return True
            i = j
        i += 1
    return False
