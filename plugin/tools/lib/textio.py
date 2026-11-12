"""Чтение и запись текстовых файлов ядра без порчи кодировки.

Правила (те же, что в .gitattributes и .editorconfig):
- кодировка UTF-8; BOM сохраняется ровно таким, каким был (у .ps1 он обязателен — PowerShell 5.1
  без BOM читает кириллицу как ANSI);
- переводы строк определяет ТИП файла, а не его прошлое состояние: .cmd/.bat/.vbs — CRLF, всё остальное — LF.

Использование:
    from textio import read, write, replace
    replace('docs/x.md', 'старый текст', 'новый текст')   # падает, если вхождений не ровно count
"""
import os

CRLF = '\r\n'
LF = '\n'
BOM = b'\xef\xbb\xbf'
CRLF_TYPES = ('.cmd', '.bat', '.vbs')


def eol_for(path):
    """Перевод строки, положенный файлу по его типу."""
    return CRLF if path.lower().endswith(CRLF_TYPES) else LF


def read(path):
    """Вернуть (текст с LF, был ли BOM)."""
    raw = open(path, 'rb').read()
    bom = raw.startswith(BOM)
    text = (raw[3:] if bom else raw).decode('utf-8')
    return text.replace(CRLF, LF), bom


def write(path, text, bom=None):
    """Записать текст; bom=None — оставить как было у файла (новый .ps1 получает BOM)."""
    if bom is None:
        if os.path.exists(path):
            bom = open(path, 'rb').read(3) == BOM
        else:
            bom = path.lower().endswith('.ps1')
    body = text.replace(CRLF, LF)
    if eol_for(path) == CRLF:
        body = body.replace(LF, CRLF)
    with open(path, 'wb') as f:
        f.write((BOM if bom else b'') + body.encode('utf-8'))


def replace(path, old, new, count=1):
    """Заменить ровно count вхождений; иначе — ошибка (никаких тихих промахов)."""
    text, bom = read(path)
    old, new = old.replace(CRLF, LF), new.replace(CRLF, LF)
    found = text.count(old)
    if found != count:
        raise SystemExit('%s: ожидалось вхождений %d, найдено %d: %r' % (path, count, found, old[:80]))
    write(path, text.replace(old, new), bom)
    return found


def normalize(path):
    """Привести файл к положенному переводу строк, не трогая содержимое и BOM."""
    text, bom = read(path)
    write(path, text, bom)


def tracked_text_files(root='.'):
    """Отслеживаемые git текстовые файлы. Пропускаются двоичные и помеченные в .gitattributes
    как -text (исходники 1С — байт в байт). core.quotepath=off — иначе git отдаёт кириллические
    имена в экранированном виде, и такие файлы молча выпадали из обработки."""
    import subprocess
    out = subprocess.run(['git', '-C', root, '-c', 'core.quotepath=off', 'ls-files', '--eol'],
                         capture_output=True, text=True, encoding='utf-8').stdout
    files = []
    for line in out.splitlines():
        meta, _, path = line.partition('\t')
        cols = meta.split()
        if cols[0] == 'i/-text' or (len(cols) > 2 and '-text' in cols[2]):
            continue
        files.append(os.path.join(root, path))
    return files


if __name__ == '__main__':
    # python tools/lib/textio.py <файл>...  — привести файлы к положенному переводу строк
    # python tools/lib/textio.py --all     — все отслеживаемые текстовые файлы проекта (содержимое не меняется)
    import sys
    targets = tracked_text_files() if sys.argv[1:] == ['--all'] else sys.argv[1:]
    changed = 0
    for p in targets:
        if not os.path.isfile(p):
            continue
        before = open(p, 'rb').read()
        normalize(p)
        if open(p, 'rb').read() != before:
            changed += 1
            print('приведён:', p)
    print('файлов приведено: %d из %d' % (changed, len(targets)))
