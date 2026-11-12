"""Общий фоновый индексатор кода (code-index) — один на машину, в папке данных плагина (ADR-0006).

    python code-index-daemon.py --plugin-data <папка данных> add --src <выгрузка> [--project <папка проекта>] [--index-dir <папка>] [--dry-run]
    python code-index-daemon.py --plugin-data <папка данных> remove --src <выгрузка> [--dry-run]
    python code-index-daemon.py --plugin-data <папка данных> autostart on|off [--startup-dir <папка>] [--dry-run]
    python code-index-daemon.py --plugin-data <папка данных> start | stop | restart | status | reload

Устройство — по документации code-index-mcp: сервер `serve` только читает индекс и без запущенного индексатора отвечает
`daemon_offline`; индексатор и сервер находят друг друга через файл daemon.json в папке CODE_INDEX_HOME. Здесь это
<папка данных>/code-index: в ней daemon.toml со списком выгрузок; серверу плагина её передаёт .mcp.json (env).
Индекс выгрузки лежит в <выгрузка>/.code-index/index.db. По правилу platform/code-index-outside-sources это ссылка (junction)
на <проект>/.code-index (или на --index-dir, если выгрузок у проекта несколько: <проект>/.code-index/<алиас>) — add создаёт
её, если её нет, и только потом добавляет выгрузку в daemon.toml: индексатор, увидевший выгрузку без ссылки, сразу заводит
индекс внутри исходников. remove убирает выгрузку из списка и перезапускает индексатор: reload не отпускает файл индекса
убранной выгрузки. stop ждёт выхода процесса — команда индексатора `daemon stop` возвращается раньше.
Писатель индекса — один: если ссылка .code-index ведёт в папку tools/code-index прежней схемы «копия ядра», за выгрузкой следит
индексатор той копии — add её не добавляет, пока тот не остановлен.
autostart on — файл в папке «Автозагрузка» пользователя (без прав администратора, как у установщика самого индексатора);
ставится только по согласию владельца в /ones-core:setup. Коды выхода: 0 — сделано; 1 — сбой; 2 — неверные входные данные;
3 — выгрузку ведёт другой индексатор.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time


def is_junction(p):
    """Ссылка-соединение (junction): os.path.isjunction есть только с Python 3.12, README обещает 3.8+ (аудит 30.10.2026)."""
    f = getattr(os.path, 'isjunction', None)
    if f is not None:
        return f(p)
    try:
        st = os.lstat(p)
    except OSError:
        return False
    return bool(getattr(st, 'st_file_attributes', 0) & 0x400) and not os.path.islink(p)   # FILE_ATTRIBUTE_REPARSE_POINT

STARTUP_NAME = 'ones-core code-index.vbs'
TOML_HEAD = ('# Общий фоновый индексатор кода ones-core: список выгрузок. Пишет /ones-core:setup (code-index-daemon.py add).\n'
             '[daemon]\nhttp_port = 0\nmax_concurrent_initial = 1\n')


def home_of(data):
    return os.path.join(os.path.abspath(data), 'code-index')


def bin_of(data):
    return os.path.join(os.path.abspath(data), 'bin', 'code-index', 'bsl-indexer.exe')


def read_paths(toml_path):
    if not os.path.isfile(toml_path):
        return []
    with open(toml_path, encoding='utf-8') as f:
        text = f.read()
    out = []
    for m in re.finditer(r'^\s*path\s*=\s*(?:\'([^\']*)\'|"((?:[^"\\]|\\.)*)")', text, re.M):
        out.append(m.group(1) if m.group(1) is not None else m.group(2).replace('\\\\', '\\'))
    return out


def write_paths(toml_path, paths):
    parts = [TOML_HEAD]
    for p in paths:
        q = "'%s'" % p if "'" not in p else '"%s"' % p.replace('\\', '\\\\')
        parts.append('\n[[paths]]\npath = %s\n' % q)
    os.makedirs(os.path.dirname(toml_path), exist_ok=True)
    with open(toml_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(''.join(parts))


def same(a, b):
    return os.path.normcase(os.path.normpath(a)) == os.path.normcase(os.path.normpath(b))


def run_bin(data, *args, timeout=30):
    env = dict(os.environ, CODE_INDEX_HOME=home_of(data))
    try:
        r = subprocess.run([bin_of(data)] + list(args), capture_output=True, env=env, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, str(e)
    return r.returncode, (r.stdout + r.stderr).decode('utf-8', 'replace')


def running(data):
    rc, out = run_bin(data, 'daemon', 'status', '--json')
    if rc != 0:
        return False
    try:
        return bool(json.loads(out[out.index('{'):]).get('status') in ('ok', 'running', 'ready'))
    except ValueError:
        return 'ok' in out.lower()


def daemon_procs():
    """Запущенные процессы `daemon run` индексатора: [(pid, программа)].
    Вывод — в UTF-8 явно: иначе PowerShell отдаёт его в кодировке консоли, и путь профиля с кириллицей не совпадёт со своим."""
    ps = ("[Console]::OutputEncoding = [Text.Encoding]::UTF8; Get-CimInstance Win32_Process -Filter \"Name='bsl-indexer.exe' OR Name='code-index.exe'\" | "
          "Where-Object { $_.CommandLine -match 'daemon\\s+run' } | ForEach-Object { '{0}|{1}' -f $_.ProcessId, $_.ExecutablePath }")
    try:
        r = subprocess.run(['powershell', '-NoProfile', '-Command', ps], capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return []
    out = []
    for line in r.stdout.decode('utf-8', 'replace').splitlines():
        pid, _, exe = line.strip().partition('|')
        if pid.isdigit() and exe:
            out.append((int(pid), exe))
    return out


def own_pids(data):
    return [pid for pid, exe in daemon_procs() if same(exe, bin_of(data))]


def other_daemons(data):
    """Запущенные индексаторы, кроме нашего: [(программа, список выгрузок из его daemon.toml)].
    CODE_INDEX_HOME прежних копий ядра — папка самой программы (их daemon-run.cmd), поэтому daemon.toml ищется рядом с ней."""
    return [(exe, read_paths(os.path.join(os.path.dirname(exe), 'daemon.toml')))
            for _, exe in daemon_procs() if not same(exe, bin_of(data))]


def link_target(link):
    try:
        t = os.readlink(link)
    except OSError:
        return None
    return t[4:] if t.startswith('\\\\?\\') else t


def cmd_add(a):
    src = os.path.abspath(a.src)
    proj = os.path.abspath(a.project)
    if not os.path.isdir(src):
        print('Нет папки выгрузки: %s' % src)
        return 2
    for exe, watched in other_daemons(a.plugin_data):
        if any(same(p, src) for p in watched):
            print('Выгрузку %s уже ведёт другой запущенный индексатор (%s). Писатель индекса должен быть один: сначала '
                  'остановите тот индексатор и снимите его автозапуск (план перевода проекта), затем повторите.' % (src, exe))
            return 3
    link = os.path.join(src, '.code-index')
    want = os.path.abspath(a.index_dir) if a.index_dir else os.path.join(proj, '.code-index')
    actions = []
    if is_junction(link):
        t = link_target(link)
        if t and same(t, want):
            pass
        elif t and re.search(r'[\\/]tools[\\/]code-index[\\/]', t, re.I):
            print('Выгрузку ведёт индексатор прежней схемы «копия ядра»: ссылка %s ведёт в %s. Сначала остановите тот '
                  'индексатор и перенесите индекс в %s (план перевода проекта), затем повторите.' % (link, t, want))
            return 3
        else:
            actions.append('ссылка %s уже ведёт в %s — оставляю' % (link, t))
    elif os.path.isdir(link):
        actions.append('в выгрузке своя папка индекса %s (не ссылка) — оставляю как есть' % link)
    else:
        actions.append('папка индекса %s и ссылка на неё из выгрузки %s' % (want, link))
        if not a.dry_run:
            os.makedirs(want, exist_ok=True)
            r = subprocess.run(['cmd', '/c', 'mklink', '/J', link, want], capture_output=True)
            if r.returncode != 0 or not is_junction(link):
                print('Не удалось создать ссылку %s: %s' % (link, r.stdout.decode('cp866', 'replace').strip()))
                return 1
    toml = os.path.join(home_of(a.plugin_data), 'daemon.toml')
    paths = read_paths(toml)
    if not any(same(p, src) for p in paths):
        actions.append('выгрузка в списке индексатора %s' % toml)
        if not a.dry_run:
            write_paths(toml, paths + [src])
            if running(a.plugin_data):
                rc, out = run_bin(a.plugin_data, 'daemon', 'reload')
                actions.append('индексатор перечитал список' if rc == 0 else 'индексатор не перечитал список: %s' % out.strip()[:200])
    print(('Что будет сделано' if a.dry_run else 'Сделано') + (':' if actions else ': ничего — выгрузка уже подключена'))
    for x in actions:
        print('  - ' + x)
    return 0


def startup_dir(a):
    if a.startup_dir:
        return a.startup_dir
    return os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')


def cmd_autostart(a):
    path = os.path.join(startup_dir(a), STARTUP_NAME)
    if a.state == 'off':
        if os.path.isfile(path):
            if not a.dry_run:
                os.remove(path)
            print('Автозапуск индексатора снят: %s' % path)
        else:
            print('Автозапуска индексатора нет — снимать нечего')
        return 0
    home, exe = home_of(a.plugin_data), bin_of(a.plugin_data)
    if not os.path.isfile(exe):
        print('Нет программы индексатора %s — сначала установщик программ' % exe)
        return 2
    vbs = ("' ones-core: общий фоновый индексатор кода. Ставит /ones-core:setup, снять — code-index-daemon.py autostart off\r\n"
           'Set sh = CreateObject("WScript.Shell")\r\n'
           'sh.Environment("Process")("CODE_INDEX_HOME") = "%s"\r\n'
           'sh.Run """%s"" daemon run", 0, False\r\n') % (home, exe)
    print('Автозапуск индексатора при входе в Windows: %s' % path)
    if not a.dry_run:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-16') as f:  # WSH читает UTF-16 с BOM: в пути профиля бывает кириллица
            f.write(vbs)
    return 0


def cmd_start(a):
    if running(a.plugin_data):
        print('Индексатор уже работает')
        return 0
    home, exe = home_of(a.plugin_data), bin_of(a.plugin_data)
    if not os.path.isfile(os.path.join(home, 'daemon.toml')):
        print('Нет списка выгрузок %s — сначала add' % os.path.join(home, 'daemon.toml'))
        return 2
    log = open(os.path.join(home, 'daemon.log'), 'ab')
    flags = 0x00000008 | 0x00000200 | 0x08000000  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
    subprocess.Popen([exe, 'daemon', 'run'], env=dict(os.environ, CODE_INDEX_HOME=home), stdout=log, stderr=log,
                     stdin=subprocess.DEVNULL, creationflags=flags, close_fds=True)
    for _ in range(15):
        time.sleep(1)
        if running(a.plugin_data):
            print('Индексатор запущен (журнал — %s)' % os.path.join(home, 'daemon.log'))
            return 0
    print('Индексатор не ответил за 15 с — см. %s' % os.path.join(home, 'daemon.log'))
    return 1


def cmd_stop(a, wait=30):
    pids = own_pids(a.plugin_data)
    if not pids and not running(a.plugin_data):
        print('Индексатор не работает')
        return 0
    run_bin(a.plugin_data, 'daemon', 'stop')
    for _ in range(wait):
        if not own_pids(a.plugin_data):
            print('Индексатор остановлен')
            return 0
        time.sleep(1)
    print('Индексатор не вышел за %d с (процесс %s) — файлы индекса ещё заняты' % (wait, ', '.join(map(str, own_pids(a.plugin_data)))))
    return 1


def cmd_restart(a):
    rc = cmd_stop(a)
    return rc if rc else cmd_start(a)


def cmd_remove(a):
    src = os.path.abspath(a.src)
    toml = os.path.join(home_of(a.plugin_data), 'daemon.toml')
    paths = read_paths(toml)
    left = [p for p in paths if not same(p, src)]
    if len(left) == len(paths):
        print('Выгрузки %s в списке индексатора нет — убирать нечего' % src)
        return 0
    was = running(a.plugin_data) or bool(own_pids(a.plugin_data))
    print(('Что будет сделано' if a.dry_run else 'Сделано') + ':')
    print('  - выгрузка убрана из списка индексатора %s' % toml)
    if was:
        print('  - индексатор перезапущен: reload не отпускает файл индекса убранной выгрузки')
    print('  - ссылка %s и сам индекс остались — убрать их или нет, решает владелец' % os.path.join(src, '.code-index'))
    if a.dry_run:
        return 0
    write_paths(toml, left)
    return cmd_restart(a) if was else 0


def cmd_status(a):
    rc, out = run_bin(a.plugin_data, 'daemon', 'status')
    print(out.strip() or ('индексатор не отвечает (код %d)' % rc))
    print('список выгрузок:', read_paths(os.path.join(home_of(a.plugin_data), 'daemon.toml')) or 'пуст')
    return 0 if rc == 0 else 1


def cmd_reload(a):
    rc, out = run_bin(a.plugin_data, 'daemon', 'reload')
    print(out.strip() or ('код %d' % rc))
    return 0 if rc == 0 else 1


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser(description='Общий фоновый индексатор кода ones-core')
    ap.add_argument('--plugin-data', required=True, help='папка данных плагина (${CLAUDE_PLUGIN_DATA})')
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('add')
    p.add_argument('--src', required=True)
    p.add_argument('--project', default=os.getcwd())
    p.add_argument('--index-dir', help='папка индекса, на которую ведёт ссылка (по умолчанию <проект>/.code-index)')
    p.add_argument('--dry-run', action='store_true')
    p = sub.add_parser('remove')
    p.add_argument('--src', required=True)
    p.add_argument('--dry-run', action='store_true')
    p = sub.add_parser('autostart')
    p.add_argument('state', choices=['on', 'off'])
    p.add_argument('--startup-dir')
    p.add_argument('--dry-run', action='store_true')
    for name in ('start', 'stop', 'restart', 'status', 'reload'):
        sub.add_parser(name)
    a = ap.parse_args()
    return {'add': cmd_add, 'remove': cmd_remove, 'autostart': cmd_autostart, 'start': cmd_start, 'stop': cmd_stop,
            'restart': cmd_restart, 'status': cmd_status, 'reload': cmd_reload}[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main())
