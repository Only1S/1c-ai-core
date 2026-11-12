"""Карта форков конфигурации одним взглядом: где каждая ветка-форк относительно ствола.

По каждой ветке хаба, кроме ствола: на сколько коммитов отстаёт от ствола, есть ли свои коммиты
(или форк уже влит в ствол), последний коммит (хэш и давность) и его тема. Таблица — как у прежней
версии (Format-Table -AutoSize -Wrap): ширина колонок по содержимому, длинная тема переносится
по ширине консоли, ветки — в порядке сортировки Windows без учёта регистра.
Config-agnostic: хаб берётся из --hub, иначе из переменной окружения ONEC_GIT_HUB, иначе origin
клона в текущей папке; если дан каталог клона — берётся его origin.

Запуск:
    python fork-status.py --hub D:/GIT/<конфиг>.git
    python fork-status.py                          (из клона: хаб = его origin)

    --hub    путь к bare-хабу (или каталог клона с origin=хаб)
    --trunk  ствол-интегратор (по умолчанию main)
    --fetch  принимается для совместимости и ничего не делает (в прежней версии тоже не был реализован)

Читает: хаб (git for-each-ref, rev-list, merge-base, log), origin клона. Ничего не пишет.
Коды выхода: 0 — карта показана; 1 — хаб не задан, не найден или в нём нет ветки ствола;
2 — ошибка параметров командной строки.
"""
import argparse
import functools
import os
import re
import shutil
import subprocess
import sys

COLUMNS = ('Форк', 'Отстаёт', 'Уникальное', 'Посл.коммит', 'Тема')
NEWLINE = re.compile(r'\r\n|\r|\n')
# NORM_IGNORECASE | NORM_LINGUISTIC_CASING — так .NET сравнивает строки с CompareOptions.IgnoreCase
IGNORE_CASE = 0x00000001 | 0x08000000


def utf8_console():
    """Вывод в UTF-8 независимо от кодовой страницы консоли (cp866 портит кириллицу)."""
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError):
            pass


def say(m=''):
    print(m, flush=True)


def git(*args):
    """git … из текущей папки: (код, строки stdout). stderr гасится, как 2>$null у прежней версии."""
    try:
        r = subprocess.run(['git'] + list(args), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    except OSError:
        return 1, []
    lines = NEWLINE.split(r.stdout.decode('utf-8', 'replace'))
    if lines and lines[-1] == '':
        lines.pop()
    return r.returncode, lines


def text(lines):
    """Вывод команды одной строкой — так PowerShell подставляет массив строк в текст."""
    return ' '.join(lines)


def _windows_compare():
    """Лингвистическое сравнение строк Windows без учёта регистра (CompareStringEx); None — не Windows."""
    if os.name != 'nt':
        return None
    try:
        import ctypes
        f = ctypes.WinDLL('kernel32').CompareStringEx
    except (OSError, AttributeError):
        return None
    f.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_wchar_p, ctypes.c_int, ctypes.c_wchar_p,
                  ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    f.restype = ctypes.c_int

    def cmp(a, b, locale=None):
        # locale None — культура пользователя (Sort-Object), '' — инвариантная (оператор -ne)
        r = f(locale, IGNORE_CASE, a, -1, b, -1, None, None, None)
        return ((a > b) - (a < b)) if r == 0 else r - 2
    return cmp


COMPARE = _windows_compare()


def sort_names(names):
    if COMPARE:
        return sorted(names, key=functools.cmp_to_key(COMPARE))
    return sorted(names, key=lambda s: (s.casefold(), s))


def same_name(a, b):
    if COMPARE:
        return COMPARE(a, b, '') == 0
    return a.casefold() == b.casefold()


def console_buffer_width():
    """Ширина буфера консоли Windows ($Host.UI.RawUI.BufferSize.Width) — и при перенаправленном выводе; 0 — не узнать."""
    try:
        import ctypes
        from ctypes import wintypes

        class Info(ctypes.Structure):
            _fields_ = [('dwSize', wintypes._COORD), ('dwCursorPosition', wintypes._COORD),
                        ('wAttributes', wintypes.WORD), ('srWindow', wintypes.SMALL_RECT),
                        ('dwMaximumWindowSize', wintypes._COORD)]
        k32 = ctypes.WinDLL('kernel32')
        k32.CreateFileW.restype = wintypes.HANDLE
        k32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                                    wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        k32.GetConsoleScreenBufferInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Info)]
        k32.CloseHandle.argtypes = [wintypes.HANDLE]
        # GENERIC_READ|GENERIC_WRITE, FILE_SHARE_READ|FILE_SHARE_WRITE, OPEN_EXISTING
        h = k32.CreateFileW('CONOUT$', 0xC0000000, 3, None, 3, 0, None)
        if not h or h == ctypes.c_void_p(-1).value:
            return 0
        try:
            info = Info()
            return info.dwSize.X if k32.GetConsoleScreenBufferInfo(h, ctypes.byref(info)) else 0
        finally:
            k32.CloseHandle(h)
    except (OSError, AttributeError, ValueError):
        return 0


def line_width():
    """Ширина строки таблицы, как у вывода PowerShell в консоль: ширина буфера минус 1."""
    w = console_buffer_width() if os.name == 'nt' else 0
    if w <= 0:
        w = shutil.get_terminal_size((120, 24)).columns
    return w - 1


def fit_widths(widths, total):
    """Подогнать ширины под строку, как Format-Table: правую колонку ужать, а если в ней не останется
    и одной клетки — скрыть (0) и ужимать следующую слева."""
    w = list(widths)
    while True:
        vis = [i for i, x in enumerate(w) if x > 0]
        if not vis:
            return w
        excess = sum(w[i] for i in vis) + len(vis) - 1 - total
        if excess <= 0:
            return w
        last = vis[-1]
        if w[last] - excess >= 1:
            w[last] -= excess
            return w
        w[last] = 0


def chunks(s, width):
    """Перенос значения по ширине колонки — посимвольно, как Format-Table -Wrap в русской культуре."""
    if len(s) <= width:
        return [s]
    return [s[i:i + width] for i in range(0, len(s), width)]


def render(rows, total):
    """Строки таблицы: заголовок, черта под заголовком, строки данных (хвостовые пробелы срезаны)."""
    widths = [max([len(COLUMNS[i])] + [len(r[i]) for r in rows]) for i in range(len(COLUMNS))]
    w = fit_widths(widths, total)
    vis = [i for i, x in enumerate(w) if x > 0]
    if total < 5 or not vis:
        return []
    out = []

    def emit(cells):
        parts = [chunks(cells[i], w[i]) for i in vis]
        for j in range(max(len(p) for p in parts)):
            out.append(' '.join((p[j] if j < len(p) else '').ljust(w[i]) for p, i in zip(parts, vis)).rstrip())
    emit(COLUMNS)
    emit(['-' * min(len(c), w[i]) for i, c in enumerate(COLUMNS)])
    for r in rows:
        emit(r)
    return out


def resolve_hub(hub):
    if hub:
        return hub
    if os.environ.get('ONEC_GIT_HUB'):
        return os.environ['ONEC_GIT_HUB']
    code, out = git('remote', 'get-url', 'origin')
    if code == 0 and text(out):
        return text(out)
    return None


def main():
    utf8_console()
    p = argparse.ArgumentParser(description='Карта форков: где каждая ветка хаба относительно ствола.')
    p.add_argument('--hub', help='путь к bare-хабу (или каталог клона с origin=хаб)')
    p.add_argument('--trunk', default='main', help='ствол-интегратор (по умолчанию main)')
    p.add_argument('--fetch', action='store_true', help='для совместимости; ничего не делает')
    a = p.parse_args()
    trunk = a.trunk

    hub = resolve_hub(a.hub)
    if not hub:
        say('Хаб не задан. Укажи --hub <путь к *.git>, задай переменную окружения ONEC_GIT_HUB, '
            'либо запусти из клона (origin=хаб).')
        return 1
    # нормализуем: если дали каталог клона — возьмём его origin
    if os.path.exists(os.path.join(hub, '.git')):
        code, out = git('-C', hub, 'remote', 'get-url', 'origin')
        if code == 0:
            hub = text(out)
    if not os.path.exists(hub):
        say('Хаб не найден: %s' % hub)
        return 1

    gd = '--git-dir=' + hub
    code, out = git(gd, 'rev-parse', '--short', trunk)
    trunk_tip = text(out)
    if code != 0 or not trunk_tip:
        say("В хабе нет ветки '%s': %s" % (trunk, hub))
        return 1

    say()
    say('Хаб:   %s' % hub)
    say('Ствол: %s = %s  (%s)' % (trunk, trunk_tip, text(git(gd, 'log', '-1', '--format=%s', trunk)[1])))
    say()

    names = sort_names([b for b in git(gd, 'for-each-ref', '--format=%(refname:short)', 'refs/heads')[1]
                        if not same_name(b, trunk)])
    rows = []
    for b in names:
        lr = re.split(r'\s+', text(git(gd, 'rev-list', '--left-right', '--count', '%s...%s' % (trunk, b))[1]))
        behind, own = lr[0], (lr[1] if len(lr) > 1 else '')
        in_trunk = git(gd, 'merge-base', '--is-ancestor', b, trunk)[0] == 0
        if in_trunk:
            rel = 'влит в ствол'
        elif own.isdigit() and int(own) > 0:
            rel = '%s своих' % own
        else:
            rel = '-'
        rows.append((b, behind, rel, text(git(gd, 'log', '-1', '--format=%h %cr', b)[1]),
                     text(git(gd, 'log', '-1', '--format=%s', b)[1])))
    if rows:
        say()
        for line in render(rows, line_width()):
            say(line)
        say()
        say()

    port = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fork-port.py')
    if ' ' in port:
        port = '"%s"' % port
    say('Подробнее по форку X:  git --git-dir=%s log %s..X   /   git --git-dir=%s diff %s X' % (hub, trunk, hub, trunk))
    say('Взять срез из форка:    python %s --from X --paths <путь> (из целевого клона)' % port)
    return 0


if __name__ == '__main__':
    sys.exit(main())
