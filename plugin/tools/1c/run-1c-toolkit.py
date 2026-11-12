"""Поднять MCP-сервер 1c-toolkit на ТЕСТОВОЙ базе проекта (команда /ones-core:toolkit).

    python run-1c-toolkit.py --plugin-data <папка данных плагина> [--db <id базы>] [--port <порт>] [--client thick|thin] [--project <папка проекта>] [--timeout 180] [--dry-run]

Перенос tools/1c/run-1c-toolkit.ps1 мастера на Python с путями плагина (ADR-0002). Механизм — поставщика
(ROCTUP/1c-mcp-toolkit, с v1.7.1): обработка открывается из командной строки 1С и по параметру
/C "startup;mode=embedded;port=<порт>;auth=windows" сама поднимает встроенный HTTP/MCP-сервер.
Запуск 1С — через скрипт скилла db-run (use-skills-not-manual-edits): он держит экранирование и проверку «процесс не упал».
Откуда что берётся:
  порт      — --port, иначе переменная ONEC_TOOLKIT_PORT (её пишет /ones-core:setup), по умолчанию 6003; сервер 1c-toolkit
              плагина слушает только ONEC_TOOLKIT_PORT — тулкит на другом порту виден через свой сервер в .mcp.json проекта;
  база      — --db (id из .v8-project.json), иначе default; только из реестра проекта, а в нём — лишь тестовые базы
              (secrets-and-production-database);
  вход      — /WA + auth=windows: без пароля в командной строке и в файлах; у базы с полем user без пароля
              (демо-база эталона) — /N<user> + auth=password;
  платформа — v8path записи базы, иначе v8path реестра, иначе ONEC_PLATFORM_BIN;
  клиент    — --client, иначе поле client записи базы, по умолчанию thick (1cv8.exe); thin — 1cv8c.exe из той же папки
              платформы: нет такого файла — отказ, без подмены толстым клиентом;
  обработка — <папка данных>/bin/mcp-toolkit/MCP_Toolkit.epf (ставит установщик программ);
  состояние — <папка данных>/state/1c-toolkit-bases.json: порт -> проект и база; по нему барьер ПДн (guard-personal-data)
              берёт отметку pd базы. Пишется перед стартом 1С, снимается, если 1С не стартовала.
ENTERPRISE — живой сеанс, а не пакетный запуск: готовность ждём по порту, ничего не останавливаем (остановка процессов 1С —
только по пути своей базы и отдельно). Идемпотентен: порт уже слушает — выход 0 без второго сеанса.
Выход: 0 — сервер поднят или уже был; 1 — не поднялся (причина — в logs/1c-toolkit.log проекта); 2 — неверные входные данные.
"""
import argparse
import datetime
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))


def db_run_script():
    """Скрипт скилла db-run: в плагине — <плагин>/skills, в мастере ядра — .claude/skills."""
    for base in (os.path.join(ROOT, 'skills'), os.path.join(os.path.dirname(ROOT), '.claude', 'skills')):
        p = os.path.join(base, 'db-run', 'scripts', 'db-run.py')
        if os.path.isfile(p):
            return p
    return None


def thin_client(v8):
    """Путь к тонкому клиенту рядом с платформой: v8 — папка bin или путь к 1cv8.exe; файла нет — None."""
    if not v8:
        return None
    folder = v8 if os.path.isdir(v8) else os.path.dirname(v8)
    exe = os.path.join(folder, '1cv8c.exe' if os.name == 'nt' else '1cv8c')
    return exe if os.path.isfile(exe) else None


def listening(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(('127.0.0.1', port)) == 0


def write_base_state(plugin_data, port, project, db_id, pid=None):
    """Записать, на какой базе поднят тулкит на порту (db_id=None — снять запись); pid — процесс 1С: барьер ПДн верит
    записи, только пока этот процесс жив (аудит 30.10.2026: запись переживала сеанс 1С)."""
    path = os.path.join(os.path.abspath(plugin_data), 'state', '1c-toolkit-bases.json')
    try:
        with open(path, encoding='utf-8') as f:
            ports = json.load(f).get('ports')
    except (OSError, ValueError, AttributeError):
        ports = None
    ports = ports if isinstance(ports, dict) else {}
    if db_id is None:
        ports.pop(str(port), None)
    else:
        ports[str(port)] = {'project': os.path.abspath(project), 'db': db_id,
                            'since': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        if pid:
            ports[str(port)]['pid'] = pid
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + '.tmp', 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'ports': ports}, f, ensure_ascii=False, indent=2)
    os.replace(path + '.tmp', path)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser(description='Поднять сервер 1c-toolkit на тестовой базе')
    ap.add_argument('--plugin-data', required=True, help='папка данных плагина (${CLAUDE_PLUGIN_DATA})')
    ap.add_argument('--db', help='id базы из .v8-project.json (по умолчанию — default)')
    ap.add_argument('--port', type=int, help='порт тулкита (по умолчанию — ONEC_TOOLKIT_PORT)')
    ap.add_argument('--client', choices=('thick', 'thin'), help='клиент 1С: thick — 1cv8.exe, thin — 1cv8c.exe (по умолчанию — поле client базы, иначе thick)')
    ap.add_argument('--project', default=os.getcwd())
    ap.add_argument('--timeout', type=int, default=180)
    ap.add_argument('--dry-run', action='store_true', help='только показать, что будет запущено')
    a = ap.parse_args()
    proj = os.path.abspath(a.project)
    log_dir = os.path.join(proj, 'logs')

    def log(msg):
        line = '%s  %s' % (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), msg)
        print(line)
        if not a.dry_run:
            os.makedirs(log_dir, exist_ok=True)
            with open(os.path.join(log_dir, '1c-toolkit.log'), 'a', encoding='utf-8') as f:
                f.write(line + '\n')

    try:
        port = a.port or int(os.environ.get('ONEC_TOOLKIT_PORT') or 6003)
    except ValueError:
        log('ONEC_TOOLKIT_PORT — не число: %r' % os.environ.get('ONEC_TOOLKIT_PORT'))
        return 2
    reg_path = os.path.join(proj, '.v8-project.json')
    if not os.path.isfile(reg_path):
        log('нет реестра баз %s — зарегистрируйте тестовую базу скиллом db-list' % reg_path)
        return 2
    try:
        with open(reg_path, encoding='utf-8-sig') as f:
            reg = json.load(f)
    except ValueError as e:
        log('реестр баз %s не разбирается как JSON: %s' % (reg_path, e))
        return 2
    dbs = reg.get('databases') or []
    dbs = [dbs] if isinstance(dbs, dict) else dbs  # одна база может быть записана объектом, как принимают хуки
    if not isinstance(dbs, list):
        log('в .v8-project.json поле databases должно быть массивом баз')
        return 2
    dbs = [d for d in dbs if isinstance(d, dict)]
    want = a.db or reg.get('default')
    db = next((d for d in dbs if d.get('id') == want), None)
    if not db:
        ids = ', '.join(str(d.get('id')) for d in dbs)
        log('в .v8-project.json нет базы %r (%s); зарегистрированы: %s' % (want, '--db' if a.db else 'default', ids or 'ни одной'))
        return 2
    # Порт — после проверки входа: иначе запущенный тулкит выдавал «поднят» (код 0) и на базе не из реестра (18.10.2026)
    if listening(port):
        log('порт %d уже слушает — 1c-toolkit поднят (на какой базе — скрипт не проверяет), второй сеанс 1С не открываю' % port)
        return 0
    epf = os.path.join(os.path.abspath(a.plugin_data), 'bin', 'mcp-toolkit', 'MCP_Toolkit.epf')
    script = db_run_script()
    for need, what in ((epf, 'обработки MCP_Toolkit.epf (поставит установщик программ)'), (script, 'скрипта скилла db-run')):
        if not need or not os.path.isfile(need):
            log('нет %s: %s' % (what, need))
            return 2

    # Вход: /WA + auth=windows. База с именованным пользователем без пароля (демо-база эталона, учебная) /WA не пускает —
    # 1С сразу выходит с кодом 1; ей вход /N<имя> + auth=password. Пароль-значение в командную строку не кладём:
    # пользователь с паролем остаётся на /WA (secrets-and-production-database).
    user = str(db.get('user') or '')
    by_name = bool(user) and not str(db.get('password') or '')
    args = [sys.executable, script, '-Execute', epf, '-CParam',
            'startup;mode=embedded;port=%d;auth=%s' % (port, 'password' if by_name else 'windows')]
    args += ['-UserName', user] if by_name else ['-AdditionalV8Arguments', '/WA']
    login = 'пользователь базы /N' if by_name else '/WA'
    v8 = db.get('v8path') or reg.get('v8path') or os.environ.get('ONEC_PLATFORM_BIN')
    client = a.client or str(db.get('client') or 'thick').lower()
    if client not in ('thick', 'thin'):
        log('у базы %r поле client — %r, а нужно thick или thin' % (db.get('id'), db.get('client')))
        return 2
    if client == 'thin':
        thin = thin_client(v8)
        if not thin:
            log('тонкий клиент: нет 1cv8c рядом с платформой %r — задайте v8path в .v8-project.json или ONEC_PLATFORM_BIN' % (v8 or ''))
            return 2
        v8 = thin
        login += ', тонкий клиент'
    if v8:
        args += ['-V8Path', v8]
    if db.get('type') == 'server':
        args += ['-InfoBaseServer', str(db.get('server', '')), '-InfoBaseRef', str(db.get('ref', ''))]
    else:
        args += ['-InfoBasePath', str(db.get('path', ''))]
    if a.dry_run:
        print('Будет запущено (база %r, порт %d):' % (db.get('id'), port))
        print('  ' + ' '.join('"%s"' % x if ' ' in x or ';' in x else x for x in args))
        return 0

    try:
        write_base_state(a.plugin_data, port, proj, db.get('id'))
    except OSError as e:
        log('не записал, на какой базе поднят тулкит (%s) — барьер ПДн откажет вызовам с данными базы' % e)
    log('запуск 1С на базе %r через скилл db-run, порт %d, вход %s' % (db.get('id'), port, login))
    r = subprocess.run(args, cwd=proj, capture_output=True, text=True, encoding='utf-8', errors='replace')
    for line in (r.stdout + r.stderr).splitlines():
        if line.strip():
            log('  db-run: ' + line.strip())
    if r.returncode != 0:
        log('db-run вернул %d — 1С не стартовала (причина — в строках db-run выше)' % r.returncode)
        try:
            write_base_state(a.plugin_data, port, proj, None)
        except OSError as e:
            log('не снял запись о базе порта %d (%s) — уберите её из state/1c-toolkit-bases.json папки данных' % (port, e))
        return 1
    pm = re.search(r'^PID:\s*(\d+)', r.stdout, re.M)   # db-run печатает номер процесса 1С
    if pm:
        try:
            write_base_state(a.plugin_data, port, proj, db.get('id'), int(pm.group(1)))
        except OSError as e:
            log('не записал процесс 1С для порта %d (%s) — барьер ПДн будет отказывать' % (port, e))
    else:
        log('db-run не сообщил номер процесса 1С — барьер ПДн будет отказывать данным базы')
    deadline = time.time() + a.timeout
    while time.time() < deadline and not listening(port):
        time.sleep(2)
    if not listening(port):
        log('за %d с порт %d не поднялся. Вероятно, 1С ждёт ручного действия: вход /WA не настроен для этого '
            'пользователя или обработка запросила подтверждение безопасного режима' % (a.timeout, port))
        return 1
    try:
        with urllib.request.urlopen('http://127.0.0.1:%d/health' % port, timeout=5) as resp:
            status = json.loads(resp.read().decode('utf-8', 'replace')).get('status')
        log('1c-toolkit поднят: порт %d слушает, /health status=%s' % (port, status))
    except (OSError, ValueError) as e:
        log('1c-toolkit поднят: порт %d слушает; /health не ответил (%s) — MCP-эндпоинт /mcp' % (port, e))
    return 0


if __name__ == '__main__':
    sys.exit(main())
