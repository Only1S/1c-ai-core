"""Суммы SHA-256 файлов плагина ones-core (волна 3 п.3.9) — список выпуска и его сверка.

    python plugin-sums.py write  <папка плагина | архив.zip> <SHA256SUMS.txt> [--prefix plugin/] [--asset <файл> ...]
    python plugin-sums.py verify <папка плагина> <SHA256SUMS.txt>

write — выпуск (release-core) пишет список сумм всех файлов собранного плагина (пути от папки плагина, через «/»),
        плюс строки ассетов выпуска (--asset, например obfuscator.zip); файл прикладывается к странице Release.
        Источник — папка или zip из `git archive` коммита выпуска (--prefix — папка плагина внутри архива): архив несёт
        файлы с переводами строк по .gitattributes — ровно те байты, что получит проект при установке.
verify — в проекте: сверить установленный плагин (папка ${CLAUDE_PLUGIN_ROOT}) со списком, скачанным со страницы
        Release его версии. Строки ассетов (без «/» и без файла в папке) пропускаются. Лишние файлы (кэш Python и т. п.)
        не ошибка, их число видно в итоге. Формат строк — как у sha256sum: «<сумма>  <путь>»; пустые строки допустимы.
Коды выхода: 0 — всё совпало (или список записан); 1 — файл изменён или пропал (назван); 2 — ошибка запуска, в том числе
негодный список: строка не по формату или ни одного сверенного файла (неудачное скачивание не считается подтверждением).
Только стандартная библиотека Python.
"""
import hashlib
import os
import re
import sys
import zipfile

SKIP_DIRS = {'.git', '__pycache__'}
SUM_LINE = re.compile(r'([0-9a-fA-F]{64})\s+\*?(.+)')


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def collect(root):
    """[(путь от root через «/», сумма)] по всем файлам, по алфавиту; .git и кэш Python не входят."""
    out = []
    for base, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for f in sorted(files):
            if f.endswith('.pyc'):
                continue
            full = os.path.join(base, f)
            out.append((os.path.relpath(full, root).replace(os.sep, '/'), sha256_of(full)))
    return sorted(out)


def collect_zip(path, prefix=''):
    """То же по архиву: файлы под prefix, пути — от prefix."""
    out = []
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            name = info.filename
            if name.endswith('/') or not name.startswith(prefix):
                continue
            rel = name[len(prefix):]
            if any(p in SKIP_DIRS for p in rel.split('/')[:-1]) or rel.endswith('.pyc'):
                continue
            out.append((rel, hashlib.sha256(z.read(info)).hexdigest()))
    return sorted(out)


def write(root, out_file, assets=(), prefix=''):
    rows = collect_zip(root, prefix) if os.path.isfile(root) else collect(root)
    lines = ['%s  %s' % (digest, rel) for rel, digest in rows]
    lines += ['%s  %s' % (sha256_of(a), os.path.basename(a)) for a in assets]
    with open(out_file, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    return len(rows), len(assets)


def parse(sums_file):
    """({путь: сумма}, [негодные строки]) из файла формата sha256sum; пустые строки не в счёт."""
    want, bad = {}, []
    with open(sums_file, encoding='utf-8-sig') as f:
        for ln in f:
            ln = ln.strip()
            mm = SUM_LINE.fullmatch(ln)
            if mm:
                want[mm.group(2).strip()] = mm.group(1).lower()
            elif ln:
                bad.append(ln)
    return want, bad


def verify(root, want):
    """(сверено, [(путь, причина)], файлов вне списка): ассеты выпуска без «/», которых нет в папке, не сверяются."""
    problems, checked = [], 0
    for rel, digest in sorted(want.items()):
        full = os.path.join(root, *rel.split('/'))
        if '/' not in rel and not os.path.isfile(full) and rel.endswith('.zip'):
            continue    # ассет выпуска (obfuscator.zip): в папку плагина не ставится
        checked += 1
        if not os.path.isfile(full):
            problems.append((rel, 'нет файла'))
        elif sha256_of(full) != digest:
            problems.append((rel, 'сумма не совпала'))
    return checked, problems, sum(1 for rel, _ in collect(root) if rel not in want)


def main(argv):
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError):
            pass
    if len(argv) < 3 or argv[0] not in ('write', 'verify'):
        print(__doc__.strip().splitlines()[2].strip())
        print(__doc__.strip().splitlines()[3].strip())
        return 2
    mode, root, sums_file = argv[0], argv[1], argv[2]
    is_zip = mode == 'write' and os.path.isfile(root) and zipfile.is_zipfile(root)
    if not os.path.isdir(root) and not is_zip:
        print('нет папки плагина: %s' % root)
        return 2
    if mode == 'write':
        assets = [argv[i + 1] for i, x in enumerate(argv) if x == '--asset' and i + 1 < len(argv)]
        prefix = next((argv[i + 1] for i, x in enumerate(argv) if x == '--prefix' and i + 1 < len(argv)), '')
        missing = [x for x in assets if not os.path.isfile(x)]
        if missing:
            print('нет файла ассета: %s' % ', '.join(missing))
            return 2
        n, k = write(root, sums_file, assets, prefix)
        if not n:
            print('в %s нет файлов%s — список сумм пуст' % (root, ' под ' + prefix if prefix else ''))
            return 2
        print('суммы записаны: %s — файлов плагина %d, ассетов %d' % (sums_file, n, k))
        return 0
    if not os.path.isfile(sums_file):
        print('нет списка сумм: %s' % sums_file)
        return 2
    try:
        want, bad = parse(sums_file)
    except (OSError, UnicodeDecodeError) as e:
        print('список сумм не читается: %s — %s (скачайте SHA256SUMS.txt заново со страницы Release)' % (sums_file, e))
        return 2
    if bad:
        print('список сумм испорчен: %s — строк не по формату %d, первая: %s (скачайте SHA256SUMS.txt заново со страницы Release)'
              % (sums_file, len(bad), bad[0][:80]))
        return 2
    checked, problems, extra = verify(root, want)
    if not checked:
        print('в списке %s нет ни одного файла плагина — сверять нечего (скачайте SHA256SUMS.txt заново со страницы Release)' % sums_file)
        return 2
    for rel, why in problems:
        print('[FAIL] %s — %s' % (rel, why))
    print('Итог: сверено %d, расхождений %d, вне списка %d' % (checked, len(problems), extra))
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
