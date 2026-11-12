"""Установка программ инструментов ядра (ADR-0003): скачать из официальных релизов, сверить
контрольную сумму, разложить в постоянную папку плагина. Только стандартная библиотека Python.

    python install-tools.py                 # установить недостающее в ${CLAUDE_PLUGIN_DATA}/bin
    python install-tools.py --check         # только показать, что установлено (ничего не скачивает)
    python install-tools.py --from D:/dist  # взять файлы релизов из папки, а не из интернета
    python install-tools.py --dest D:/x/bin --only code-index bsl-analyzer
    python install-tools.py --check-manifest  # только проверить записи манифеста (версия, сумма, адрес)

Повторный запуск ничего не перекачивает. Несовпадение суммы — отказ: файл не устанавливается.
Подмена атомарная (волна 3 п.3.9): файлы раскладываются во временную папку рядом, сверяются с суммами, и папка
программы заменяется целиком переименованием; прежняя версия возвращается при сбое. Занятая программа (запущен сервер) —
отказ без изменений, а не смесь старых и новых файлов.
Код возврата: 0 — всё на месте; 1 — что-то не установлено (причина напечатана).
"""
import argparse
import contextlib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
import uuid
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(HERE, 'tools-manifest.json')
STATE = 'installed.json'
SHA256_RE = re.compile(r'[0-9a-f]{64}')
OPM_HUB = 'http://hub.oscript.io/download/'


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def load_state(dest):
    p = os.path.join(dest, STATE)
    if os.path.isfile(p):
        with open(p, encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_state(dest, state):
    """Запись состояния через временный файл: оборванная запись не оставляет битый installed.json."""
    p = os.path.join(dest, STATE)
    tmp = p + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write('\n')
    os.replace(tmp, p)


def check_manifest(tools):
    """[(имя, причина)] — записи, которым нельзя доверить установку: нет версии, суммы SHA-256 или адрес не ведёт
    на файл этой версии. Закрытый ассет канала (gh-release) без своей суммы обязан проверяться вложенным sha256.txt."""
    problems, seen = [], set()
    for t in tools:
        name = t.get('name') or '?'
        if name in seen:
            problems.append((name, 'имя повторяется'))
        seen.add(name)
        for key in ('version', 'asset', 'kind', 'purpose'):
            if not t.get(key):
                problems.append((name, 'нет поля %s' % key))
        if t.get('kind') == 'zip' and not t.get('extract'):
            problems.append((name, 'у архива нет списка extract'))
        if t.get('kind') == 'opm' and not t.get('host'):
            problems.append((name, 'у пакета opm нет host — программы OneScript, в которую он ставится'))
        if t.get('fetch') == 'gh-release':
            if t.get('verify') != 'inner-sha256':
                problems.append((name, 'ассет канала без проверки вложенным sha256.txt (verify: inner-sha256)'))
            continue
        if not SHA256_RE.fullmatch(t.get('sha256') or ''):
            problems.append((name, 'sha256 — не 64 строчных шестнадцатеричных знака'))
        url = t.get('url') or ''
        # каталог пакетов OneScript отвечает только по http: пакет opm с закреплённой суммой — исключение
        if not (url.startswith('https://') or (t.get('kind') == 'opm' and url.startswith(OPM_HUB))):
            problems.append((name, 'адрес загрузки не https'))
        if t.get('version') and t['version'] not in url:
            problems.append((name, 'версии %s нет в адресе загрузки' % t['version']))
        if t.get('asset') and not url.endswith('/' + t['asset']):
            problems.append((name, 'адрес не ведёт на файл %s' % t['asset']))
    return problems


def verify_files(folder, files):
    """Каждый файл папки совпадает с записанной суммой; иначе — отказ с именем файла."""
    for name, digest in files.items():
        p = os.path.join(folder, name)
        if not os.path.isfile(p) or sha256_of(p) != digest:
            raise RuntimeError('файл %s не совпал с суммой %s… — установка отменена' % (name, digest[:12]))


def swap_in(staged, final):
    """Заменить папку программы целиком: staged → final переименованием на том же томе. Прежняя версия отходит в сторону
    и возвращается при сбое — в final всегда либо старая версия целиком, либо новая целиком."""
    old = None
    if os.path.isdir(final):
        old = '%s.old-%s' % (final, uuid.uuid4().hex[:8])
        try:
            os.replace(final, old)
        except OSError as e:
            raise RuntimeError('папка %s занята (запущен сервер или открыта сессия?) — прежняя версия не тронута: %s'
                               % (final, e))
    try:
        os.replace(staged, final)
    except OSError:
        if old:
            os.replace(old, final)
        raise
    if old:
        shutil.rmtree(old, ignore_errors=True)


@contextlib.contextmanager
def work_dir(dest):
    """Рабочая папка установки с обычными правами. tempfile в Windows закрывает папку для всех, кроме владельца, эти права
    уходят с программой при переносе, а от имени администратора владелец — группа: обычный процесс программу не откроет."""
    tmp = os.path.join(dest, '.install-' + uuid.uuid4().hex[:8])
    os.makedirs(tmp)
    try:
        yield tmp
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def folder_denied(dest, tool):
    """Папка программы есть, но этот процесс не может её открыть."""
    try:
        os.listdir(os.path.join(dest, tool['name']))
    except PermissionError:
        return True
    except OSError:
        pass
    return False


def drop_leftovers(dest, name):
    """Убрать прежние папки .old-* этой программы, если их не удалось снести сразу (файл был занят)."""
    try:
        entries = os.listdir(dest)
    except OSError:
        return
    for e in entries:
        if e.startswith(name + '.old-') and os.path.isdir(os.path.join(dest, e)):
            shutil.rmtree(os.path.join(dest, e), ignore_errors=True)


def is_installed(tool, dest, state):
    """Установлена ровно эта версия, и каждый файл совпадает с записанной суммой."""
    rec = state.get(tool['name'])
    if not rec:
        return False
    if tool['kind'] == 'opm':   # пакет живёт в lib программы-хозяина: на месте ровно эта версия и папка пакета
        return (rec.get('version') == tool['version'] and rec.get('asset_sha256') == tool['sha256']
                and os.path.isdir(os.path.join(dest, tool['host'], 'lib', tool.get('package', tool['name']))))
    # обфускатор (gh-release) следует за последним релизом канала — фиксированной версии/суммы в манифесте нет;
    # «установлен» = файлы на месте и совпадают с записанными суммами (обновление — явным перезапуском install-tools)
    if tool.get('fetch') != 'gh-release':
        if rec.get('version') != tool['version'] or rec.get('asset_sha256') != tool['sha256']:
            return False
    for name, digest in rec.get('files', {}).items():
        p = os.path.join(dest, tool['name'], name)
        if not os.path.isfile(p) or sha256_of(p) != digest:
            return False
    return bool(rec.get('files'))


def fetch(tool, source_dir, tmp_dir):
    """Файл релиза во временной папке: из --from или скачанный."""
    target = os.path.join(tmp_dir, tool['asset'])
    if source_dir:
        src = os.path.join(source_dir, tool['asset'])
        if not os.path.isfile(src):
            raise RuntimeError('в папке %s нет файла %s' % (source_dir, tool['asset']))
        shutil.copyfile(src, target)
        return target
    if tool.get('fetch') == 'gh-release':
        # приватный ассет канала: качаем из ПОСЛЕДНЕГО релиза под авторизацией gh проекта (той же, что ставила плагин)
        gh = shutil.which('gh')
        if not gh:
            raise RuntimeError('нужен GitHub CLI (gh) для закрытого ассета %s: установите gh и выполните gh auth login '
                               '(или возьмите файл из папки: --from)' % tool['asset'])
        r = subprocess.run([gh, 'release', 'download', '--repo', tool['repo'], '--pattern', tool['asset'],
                            '--dir', tmp_dir], capture_output=True)
        if r.returncode != 0 or not os.path.isfile(target):
            raise RuntimeError('не удалось скачать %s из релиза %s через gh: %s'
                               % (tool['asset'], tool['repo'], r.stderr.decode('utf-8', 'replace')[:200]))
        return target
    req = urllib.request.Request(tool['url'], headers={'User-Agent': 'ones-core-install-tools'})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp, open(target, 'wb') as out:
            shutil.copyfileobj(resp, out, 1 << 20)
    except OSError as e:
        raise RuntimeError('не удалось скачать %s: %s (нет интернета? можно взять файл из папки: --from)' % (tool['url'], e))
    return target


def unpack(tool, asset_path, out_dir):
    """Разложить файлы программы в out_dir; вернуть {имя: сумма}."""
    os.makedirs(out_dir, exist_ok=True)
    files = {}
    if tool['kind'] == 'tree':   # программа целиком (OneScript): все файлы архива с путями, каждый — с суммой
        root = os.path.realpath(out_dir)
        with zipfile.ZipFile(asset_path) as z:
            for n in z.namelist():
                if n.endswith('/'):
                    continue
                rel = n[len(tool['strip']):] if tool.get('strip') and n.startswith(tool['strip']) else n
                target = os.path.realpath(os.path.join(out_dir, rel))
                if not target.startswith(root + os.sep):
                    raise RuntimeError('в архиве %s путь за пределами папки: %s — установка отменена' % (tool['asset'], n))
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with z.open(n) as src, open(target, 'wb') as dst:
                    shutil.copyfileobj(src, dst, 1 << 20)
                files[rel.replace('\\', '/')] = sha256_of(target)
        return files
    if tool['kind'] == 'zip':
        with zipfile.ZipFile(asset_path) as z:
            members = {os.path.basename(n): n for n in z.namelist() if not n.endswith('/')}
            for want in tool['extract']:
                if want not in members:
                    raise RuntimeError('в архиве %s нет файла %s (есть: %s)' % (tool['asset'], want, ', '.join(sorted(members)) or 'пусто'))
                target = os.path.join(out_dir, want)
                with z.open(members[want]) as src, open(target, 'wb') as dst:
                    shutil.copyfileobj(src, dst, 1 << 20)
                files[want] = sha256_of(target)
    else:
        name = tool.get('save_as', tool['asset'])
        target = os.path.join(out_dir, name)
        shutil.copyfile(asset_path, target)
        files[name] = sha256_of(target)
    return files


def unpack_verified(tool, asset_path, out_dir):
    """Распаковать extract[] из zip и сверить каждый файл с суммой из ВЛОЖЕННОГО sha256.txt (целостность ассета).
    Подлинность даёт приватный канал + авторизация gh; здесь проверяем, что файлы не бились. Вернуть {имя: сумма}."""
    os.makedirs(out_dir, exist_ok=True)
    with zipfile.ZipFile(asset_path) as z:
        members = {os.path.basename(n): n for n in z.namelist() if not n.endswith('/')}
        if 'sha256.txt' not in members:
            raise RuntimeError('в ассете %s нет sha256.txt — целостность не проверить' % tool['asset'])
        want_sums = {}
        for ln in z.read(members['sha256.txt']).decode('utf-8', 'replace').splitlines():
            parts = ln.split()
            if len(parts) >= 2:
                want_sums[os.path.basename(parts[1].replace('\\', '/'))] = parts[0].lower()
        files = {}
        for want in tool['extract']:
            if want not in members:
                raise RuntimeError('в ассете %s нет файла %s (есть: %s)' % (tool['asset'], want, ', '.join(sorted(members)) or 'пусто'))
            target = os.path.join(out_dir, want)
            with z.open(members[want]) as src, open(target, 'wb') as dst:
                shutil.copyfileobj(src, dst, 1 << 20)
            got = sha256_of(target)
            exp = want_sums.get(want)
            if exp is None:
                raise RuntimeError('в sha256.txt ассета %s нет записи для %s' % (tool['asset'], want))
            if got != exp:
                raise RuntimeError('контрольная сумма %s не совпала (ожидалась %s…, получена %s…)' % (want, exp[:12], got[:12]))
            files[want] = got
    return files


def python_env(tool, staging):
    """Окружение Python программы в её папке: только готовые сборки из списка с суммами (--require-hashes), код установки
    пакетов не исполняется. Вернуть {имя: сумма} файла окружения, по которому видно, что оно на месте."""
    venv = os.path.join(staging, '.venv')
    py = os.path.join(venv, 'Scripts', 'python.exe') if os.name == 'nt' else os.path.join(venv, 'bin', 'python')
    steps = ([sys.executable, '-m', 'venv', venv],
             [py, '-m', 'pip', 'install', '--disable-pip-version-check', '--require-hashes', '--no-deps', '--only-binary', ':all:',
              '-r', os.path.join(HERE, tool['requirements'])])
    for cmd in steps:
        r = subprocess.run(cmd, capture_output=True, timeout=900)
        if r.returncode != 0:
            tail = (r.stdout + r.stderr).decode('utf-8', 'replace').strip().splitlines()[-2:]
            raise RuntimeError('окружение Python не собрано (код %d): %s' % (r.returncode, ' | '.join(tail)))
    return {'.venv/pyvenv.cfg': sha256_of(os.path.join(venv, 'pyvenv.cfg'))}


def opm_command(tool, dest, package_path):
    """Команда установки пакета .ospx менеджером opm программы-хозяина (OneScript); opm.bat не берём — он зовёт oscript
    без пути. Зависимости пакета opm берёт из каталога OneScript по версиям из его метаданных — без сумм (предел цепочки)."""
    home = os.path.join(dest, tool['host'])
    oscript = os.path.join(home, 'bin', 'oscript.exe' if os.name == 'nt' else 'oscript')
    opm = os.path.join(home, 'lib', 'opm', 'src', 'cmd', 'opm.os')
    if not (os.path.isfile(oscript) and os.path.isfile(opm)):
        raise RuntimeError('нет программы %s с opm в %s — поставьте её первой: --only %s %s'
                           % (tool['host'], home, tool['host'], tool['name']))
    return [oscript, opm, 'install', '-f', package_path]


def install_opm(tool, dest, asset):
    """Поставить пакет .ospx (сумма уже сверена) в lib программы-хозяина; вернуть {имя пакета: сумма .ospx}."""
    r = subprocess.run(opm_command(tool, dest, asset), capture_output=True, timeout=900)
    pkg_dir = os.path.join(dest, tool['host'], 'lib', tool.get('package', tool['name']))
    if r.returncode != 0 or not os.path.isdir(pkg_dir):
        tail = (r.stdout + r.stderr).decode('utf-8', 'replace').strip().splitlines()[-3:]
        raise RuntimeError('opm не поставил пакет %s (код %d): %s' % (tool['name'], r.returncode, ' | '.join(tail)))
    return {tool['asset']: tool['sha256']}


def main():
    # вывод — всегда UTF-8: при запуске с -I переменная PYTHONIOENCODING игнорируется, и русский текст рассыпался
    sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser(description='Установка программ инструментов ядра')
    ap.add_argument('--dest', help='куда ставить (по умолчанию ${CLAUDE_PLUGIN_DATA}/bin)')
    ap.add_argument('--from', dest='source', help='папка с файлами релизов вместо скачивания')
    ap.add_argument('--only', nargs='+', help='только эти программы (имена из манифеста)')
    ap.add_argument('--check', action='store_true', help='только показать состояние, ничего не ставить')
    ap.add_argument('--check-manifest', action='store_true', help='только проверить записи манифеста: версия, сумма, адрес')
    a = ap.parse_args()

    with open(MANIFEST, encoding='utf-8') as f:
        tools = json.load(f)['tools']
    problems = check_manifest(tools)
    if a.check_manifest:
        for name, why in problems:
            print('[FAIL] манифест: %s — %s' % (name, why))
        print('Итог: записей %d, с ошибками %d' % (len(tools), len({n for n, _ in problems})))
        return 1 if problems else 0
    bad_records = {n: why for n, why in reversed(problems)}

    dest = a.dest or (os.path.join(os.environ['CLAUDE_PLUGIN_DATA'], 'bin') if os.environ.get('CLAUDE_PLUGIN_DATA') else None)
    if not dest:
        print('Не задана папка установки: передай --dest или запусти из плагина (там есть CLAUDE_PLUGIN_DATA).')
        return 1
    if a.only:
        unknown = set(a.only) - {t['name'] for t in tools}
        if unknown:
            print('Нет в манифесте: %s' % ', '.join(sorted(unknown)))
            return 1
        tools = [t for t in tools if t['name'] in a.only]
    else:
        tools = [t for t in tools if not t.get('optional')]   # опциональные (обфускатор) — только по явному --only

    os.makedirs(dest, exist_ok=True)
    state = load_state(dest)
    failed = 0
    for t in tools:
        label = '%s %s' % (t.get('name'), t.get('version'))
        if t.get('name') in bad_records:
            print('[FAIL] %-34s запись манифеста не годится: %s — не ставлю' % (label, bad_records[t.get('name')]))
            failed += 1
            continue
        if folder_denied(dest, t):
            print('[FAIL] %-34s нет доступа к папке: верните права от имени администратора: icacls "%s" /reset /T'
                  % (label, os.path.join(dest, t['name'])))
            failed += 1
            continue
        if is_installed(t, dest, state):
            print('[ OK ] %-34s уже установлена' % label)
            continue
        if a.check:
            print('[НЕТ ] %-34s не установлена — %s' % (label, t['purpose']))
            failed += 1
            continue
        try:
            drop_leftovers(dest, t['name'])
            with work_dir(dest) as tmp:
                asset = fetch(t, a.source, tmp)
                staging = os.path.join(tmp, 'unpacked')
                if t['kind'] == 'opm':
                    got = sha256_of(asset)
                    if got != t['sha256']:
                        raise RuntimeError('контрольная сумма не совпала: ожидалась %s…, получена %s… — пакет не установлен' % (t['sha256'][:12], got[:12]))
                    files = install_opm(t, dest, asset)
                    state[t['name']] = {'version': t['version'], 'asset': t['asset'], 'asset_sha256': got, 'files': files}
                    save_state(dest, state)
                    print('[ OK ] %-34s установлен в %s' % (label, t['host']))
                    continue
                if t.get('verify') == 'inner-sha256':
                    files = unpack_verified(t, asset, staging)   # целостность — по вложенному sha256.txt
                    ver_key = files.get(t['extract'][0], '')
                else:
                    got = sha256_of(asset)
                    if got != t['sha256']:
                        raise RuntimeError('контрольная сумма не совпала: ожидалась %s…, получена %s… — файл не установлен' % (t['sha256'][:12], got[:12]))
                    files = unpack(t, asset, staging)
                    ver_key = t['sha256']
                    if t['kind'] not in ('zip', 'tree') and set(files.values()) != {t['sha256']}:
                        raise RuntimeError('копия файла не совпала с проверенным ассетом — установка отменена')
                    if t.get('requirements'):
                        files.update(python_env(t, staging))
                verify_files(staging, files)                   # сверка разложенного ДО подмены
                final = os.path.join(dest, t['name'])
                swap_in(staging, final)                        # папка целиком: старая версия или новая, не смесь
            verify_files(final, files)
            # изменяемая часть программы (lib/ OneScript: opm обновляет её пакеты) сверена при установке, дальше — нет
            files = {n: s for n, s in files.items() if not any(n.startswith(m) for m in t.get('mutable', []))}
            state[t['name']] = {'version': t.get('version', 'channel'), 'asset': t['asset'], 'asset_sha256': ver_key, 'files': files}
            save_state(dest, state)
            print('[ OK ] %-34s установлена (%s)' % (label, '%d файлов' % len(files) if t['kind'] == 'tree' else ', '.join(files)))
        except (RuntimeError, OSError, zipfile.BadZipFile) as e:
            print('[FAIL] %-34s %s' % (label, e))
            failed += 1
    print('Итог: %d из %d на месте%s' % (len(tools) - failed, len(tools), '' if not failed else ' — см. строки FAIL/НЕТ выше'))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
