"""Общий вывод проверок и гейтов ядра на Python (замена прежнего tools/lib/common.ps1, ADR-0002).

Контракт вердикт-маркеров — единый для всех проверок:
    [ OK ]  — проверка пройдена (ровно так: пробел-OK-пробел)
    [WARN]  — не ошибка, но требует внимания (счётчик)
    [FAIL]  — ошибка гейта (счётчик; со --strict → код выхода 1)
    [SKIP]  — тест не прогнан (нет программы, платформы, стенда): отдельный счётчик, это НЕ проход; обязательный
              тест, который пропущен, — [FAIL] (волна 2 п.2.11: пропуск не считается зелёным там, где тест обязателен)
Прочие статусные маркеры отчётов ([DRY-RUN], [ОТКАТ] и т. п.) вердиктами не являются. Итог — строка
«== Итог: FAIL=n  WARN=m  пропущено k ==». Код выхода нормализован: 0 или 1, а не число ошибок (mod 256 не съест FAIL).

Использование:
    sys.path.insert(0, os.path.join(<корень>, 'tools', 'lib')); from gate import Gate, core_root, plugin_data, run
    g = Gate(); g.ok('…'); g.warn('…'); g.bad('…'); g.skip('…', required=False); g.info('…'); g.summary(); g.exit(strict)
"""
import os
import re
import subprocess
import sys

MARKER_RE = re.compile(r'\[(?: OK |WARN|FAIL)\]')


def utf8_console():
    """Вывод в UTF-8 независимо от кодовой страницы консоли (cp866 портит кириллицу)."""
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError):
            pass


class Gate:
    def __init__(self):
        utf8_console()
        self.fails = 0
        self.warns = 0
        self.skips = 0

    def ok(self, m):
        print('[ OK ] ' + m, flush=True)

    def skip(self, m, required=False):
        """Тест не прогнан: считается в «пропущено», а не в проходах; обязательный — ещё и ошибка гейта."""
        self.skips += 1
        if required:
            self.fails += 1
            print('[FAIL] пропущен обязательный тест — это не проход: ' + m, flush=True)
        else:
            print('[SKIP] ' + m, flush=True)

    def warn(self, m):
        self.warns += 1
        print('[WARN] ' + m, flush=True)

    def bad(self, m):
        self.fails += 1
        print('[FAIL] ' + m, flush=True)

    def info(self, m):
        print('       ' + m, flush=True)

    def summary(self, title='Итог'):
        print('\n== %s: FAIL=%d  WARN=%d  пропущено %d ==' % (title, self.fails, self.warns, self.skips), flush=True)

    def exit(self, strict):
        sys.exit(1 if (strict and self.fails > 0) else 0)


def core_root(script_file):
    """Корень мастера ядра для скрипта tools/<папка>/<имя>.py — родитель папки tools."""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(script_file))))


# Заведомо двоичные типы для чтения истории git. Всё остальное гейты читают с --text: файл в UTF-16 (его пишет оператор >
# в Windows PowerShell 5.1) git считает двоичным и без --text не показывает. Эти типы — без --text: в .exe и .jar законно
# лежат строки вроде BEGIN PRIVATE KEY, а текстовый файл с таким расширением git всё равно покажет.
BINARY_TYPES = ('exe', 'dll', 'so', 'jar', 'class', 'pyc', 'epf', 'erf', 'cf', 'cfe', 'cfu', 'dt', 'bin', 'bak', '1cd',
                'zip', '7z', 'gz', 'tar', 'rar', 'png', 'jpg', 'jpeg', 'gif', 'bmp', 'ico', 'webp', 'ttf', 'woff', 'woff2',
                'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'sqlite', 'db')


def history_pathspecs():
    """(пути для чтения с --text, заведомо двоичные пути): вместе — вся история, каждый файл ровно один раз.
    С путями git упрощает историю и теряет отброшенные слиянием ветки — звать вместе с --full-history."""
    only = [':(glob,icase)**/*.' + t for t in BINARY_TYPES]
    return ['.'] + [':(exclude,glob,icase)**/*.' + t for t in BINARY_TYPES], only


def plugin_data():
    """Папка данных плагина: переменная плагина, иначе стандартная папка в профиле пользователя."""
    return os.environ.get('CLAUDE_PLUGIN_DATA') or os.path.join(os.path.expanduser('~'), '.claude', 'plugins', 'data', 'ones-core-ones-core')


BOMS = ((b'\xff\xfe\x00\x00', 'utf-32-le'), (b'\x00\x00\xfe\xff', 'utf-32-be'), (b'\xef\xbb\xbf', 'utf-8'),
        (b'\xff\xfe', 'utf-16-le'), (b'\xfe\xff', 'utf-16-be'))


def read_text(path):
    """Текст файла: кодировка — по BOM (UTF-8, UTF-16, UTF-32, как .NET ReadAllText), без BOM — UTF-8.
    UTF-16 с BOM — то, что по умолчанию пишут '>' и Out-File в Windows PowerShell 5.1."""
    with open(path, 'rb') as f:
        raw = f.read()
    for bom, enc in BOMS:
        if raw.startswith(bom):
            return raw[len(bom):].decode(enc, errors='replace')
    return raw.decode('utf-8', errors='replace')


def run(cmd, cwd=None, timeout=600, env=None, input_bytes=None):
    """Запустить процесс, вернуть (код, stdout, stderr) текстом. Вывод — UTF-8, с откатом на cp866 (консольные программы Windows)."""
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, timeout=timeout, env=env, input=input_bytes)
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, '', str(e)

    def dec(b):
        try:
            return b.decode('utf-8')
        except UnicodeDecodeError:
            return b.decode('cp866', 'replace')
    return r.returncode, dec(r.stdout), dec(r.stderr)
