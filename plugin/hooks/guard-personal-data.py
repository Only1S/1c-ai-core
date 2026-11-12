"""PreToolUse на инструментах 1c-toolkit: данные базы 1С — только с базы без настоящих ПДн (personal-data-masked-from-1c).

Первый срез правила (волна 1, Б.13). Фильтра-маски ПДн ещё нет, поэтому по п.5 правила данные базы с настоящими ПДн
не запрашиваются вовсе. Что делает:
  - инструмент тулкита, отдающий данные базы (execute_query, execute_code, get_object_by_link, get_link_of_object,
    find_references_to_object, get_event_log, get_access_rights, get_screenshot, submit_for_deanonymization), и любой
    незнакомый инструмент тулкита проходят, только если у базы, на которой поднят тулкит, в .v8-project.json стоит
    "pd": "none" (данных о людях нет) или "pd": "masked" (копия обезличена); нет отметки = raw (п.3 правила) — отказ;
  - без отметки проходят только инструменты без данных базы — NO_DATA (перечень сверен с ПолучитьСхемыИнструментов
    обработки MCP_Toolkit.epf 1.9.0);
  - какая база на каком порту — файл состояния <папка данных плагина>/state/1c-toolkit-bases.json, его пишет
    run-1c-toolkit.py (/ones-core:toolkit); порт сервера — из url в .mcp.json плагина или проекта.
Сбой = отказ, не пропуск (п.5): не разобран вход, сервера нет в .mcp.json, url не на этот компьютер, нет записи о базе
порта, базы нет в реестре — отказ с подсказкой, что сделать. Отметки pd хук не ставит: это решение владельца.
Файлу состояния верить нельзя (замер 30.10.2026: «порт → чистая база» переписывается), поэтому чистая база сверяется с живым
процессом: командная строка процесса 1С, который держит порт, называет именно эту базу; порт держит не 1С или процесс не
определить — та же сверка у процесса из записи. Сам файл закрыт от агента в guard-skills и guard-destructive.
Решение — функция check(имя инструмента); тем же решением мод «чистка входящих» (inbound-filter.py, волна 2 п.2.20)
скрывает ответ такого вызова, если он всё же пришёл (хук до вызова не сработал, отметку базы сняли во время вызова).
Функция run_refusal — то же решение для прогонов мимо тулкита: харнессы run-tests и run-scenario (их код и текст падений на
базе) не запускаются на базе не none/masked; web-test держит ту же проверку у себя (cli/pd-gate.mjs).
Отказ: код 0 + JSON permissionDecision=deny; не удалось вывести и его — код 2 (тоже отказ).
"""
import json
import os
import re
import socket
import struct
import sys
from urllib.parse import urlsplit

RULE = 'personal-data-masked-from-1c'
NO_DATA = {'get_metadata', 'get_bsl_syntax_help', 'restart_1c_session', 'close_1c_session'}
LOCAL = {'127.0.0.1', 'localhost', '::1'}
CLEAN = {'none', 'masked'}


def deny(reason):
    payload = {'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'permissionDecision': 'deny',
        'permissionDecisionReason': reason,
    }}
    sys.stdout.buffer.write(json.dumps(payload, ensure_ascii=False).encode('utf-8'))
    sys.stdout.flush()
    sys.exit(0)


def plugin_data():
    return os.environ.get('CLAUDE_PLUGIN_DATA') or os.path.join(os.path.expanduser('~'), '.claude', 'plugins', 'data', 'ones-core-ones-core')


def load(path):
    with open(path, encoding='utf-8-sig') as f:
        return json.load(f)


def expand(s):
    """${VAR:-умолчание} и ${VAR} в url — как их раскрывает Claude Code в .mcp.json."""
    return re.sub(r'\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}', lambda mm: os.environ.get(mm.group(1)) or mm.group(2) or '', s)


def server_port(server, plugin):
    """Порт сервера тулкита по url в .mcp.json (плагина ones-core или проекта); None — url нет или он не на этот компьютер."""
    if plugin:
        if plugin != 'ones-core':
            return None
        mcp = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.mcp.json')
    else:
        root = os.environ.get('CLAUDE_PROJECT_DIR') or ''
        if not root:
            return None
        mcp = os.path.join(root, '.mcp.json')
    servers = load(mcp).get('mcpServers') or {}
    conf = next((v for k, v in servers.items() if k.lower() == server), None)
    if not isinstance(conf, dict) or not conf.get('url'):
        return None
    u = urlsplit(expand(str(conf['url'])))
    if (u.hostname or '').lower() not in LOCAL:
        return None
    return u.port


def process_alive(pid):
    """Жив ли процесс: на Windows — OpenProcess и код завершения (os.kill там процесс УБИВАЕТ), иначе — сигнал 0."""
    if os.name == 'nt':
        import ctypes
        k32 = ctypes.windll.kernel32
        h = k32.OpenProcess(0x1000, False, pid)   # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        try:
            code = ctypes.c_ulong()
            return bool(k32.GetExitCodeProcess(h, ctypes.byref(code))) and code.value == 259   # STILL_ACTIVE
        finally:
            k32.CloseHandle(h)
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except OSError:
        return False


def process_cmdline(pid):
    """Командная строка живого процесса или None: на Windows — NtQueryInformationProcess (класс 60), иначе /proc."""
    if os.name != 'nt':
        try:
            with open('/proc/%d/cmdline' % pid, 'rb') as f:
                return f.read().replace(b'\0', b' ').decode('utf-8', 'replace')
        except OSError:
            return None
    import ctypes
    k32, nt = ctypes.windll.kernel32, ctypes.windll.ntdll
    h = k32.OpenProcess(0x1000, False, pid)   # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return None
    try:
        size = ctypes.c_ulong(0)
        nt.NtQueryInformationProcess(h, 60, None, 0, ctypes.byref(size))
        if not size.value:
            return None
        buf = ctypes.create_string_buffer(size.value)
        if nt.NtQueryInformationProcess(h, 60, buf, size, ctypes.byref(size)) != 0:
            return None
        length = struct.unpack_from('<H', buf.raw, 0)[0]   # UNICODE_STRING: длина в байтах, затем указатель на текст
        ptr = struct.unpack_from('<Q', buf.raw, 8)[0]
        return ctypes.wstring_at(ptr, length // 2) if length and ptr else None
    finally:
        k32.CloseHandle(h)


def port_owner(port):
    """Номер процесса, который слушает порт на этой машине, или None (не найден; не Windows — сверка идёт по процессу из записи)."""
    if os.name != 'nt':
        return None
    import ctypes
    iphlp = ctypes.windll.iphlpapi
    size = ctypes.c_ulong(0)
    iphlp.GetExtendedTcpTable(None, ctypes.byref(size), False, socket.AF_INET, 3, 0)   # TCP_TABLE_OWNER_PID_LISTENER
    buf = ctypes.create_string_buffer(size.value)
    if iphlp.GetExtendedTcpTable(buf, ctypes.byref(size), False, socket.AF_INET, 3, 0) != 0:
        return None
    for i in range(struct.unpack_from('<I', buf.raw, 0)[0]):
        row = struct.unpack_from('<6I', buf.raw, 4 + i * 24)   # состояние, адрес, порт, адрес, порт, процесс
        if socket.ntohs(row[2] & 0xFFFF) == port:
            return row[5]
    return None


def names_base(line, db):
    """Командная строка запущена на этой базе: файловая — её путь, серверная — сервер (с портом или без) и имя базы."""
    flat = re.sub(r'/{2,}', '/', line.replace('\\', '/').replace('"', ' ').replace("'", ' ')).lower()
    if str(db.get('type') or '').lower() == 'server':
        srv, ref = str(db.get('server') or '').lower(), str(db.get('ref') or '').lower()
        return bool(srv and ref) and re.search(re.escape(srv) + r'(?::\d+)?/' + re.escape(ref) + r'(?:\s|$)', flat) is not None
    path = re.sub(r'/{2,}', '/', str(db.get('path') or '').replace('\\', '/')).rstrip('/').lower()
    return bool(path) and re.search(re.escape(path) + r'/?(?:\s|$)', flat) is not None


def base_on_port(port, pid, db):
    """На порту работает именно эта база: процесс 1С на порту называет её; порт держит не 1С или его не определить — процесс из записи."""
    owner = port_owner(port)
    line = process_cmdline(owner) if owner else None
    if line is None or re.search(r'1cv8', line, re.I) is None:
        line = process_cmdline(pid)
    return line is not None and names_base(line, db)


def pd_mark(db):
    """Описание отметки pd базы для текста отказа; None — база чистая (none или masked)."""
    pd = db.get('pd')
    pd = pd.strip().lower() if isinstance(pd, str) else ''
    if pd in CLEAN:
        return None
    return 'нет отметки pd' if not pd else ('pd: raw' if pd == 'raw' else "отметка pd: '%s' не из none/masked/raw" % pd)


def run_refusal(db_id, db, reg, what):
    """Причина отказа прогону на базе реестра или None: то же решение, что у инструментов тулкита. what — что запускается."""
    mark = pd_mark(db)
    if mark is None:
        return None
    return ("%s: %s на базе '%s' не запускается: у неё %s — значит, в ней настоящие ПДн (п.3 правила), а прогон — это код на данных "
            "базы, и его вывод идёт к модели (п.4, п.6). Отметку ставит только владелец — это его решение о данных, сам её не ставь: "
            "в %s у этой базы \"pd\": \"none\", если данных о людях в базе нет, или \"pd\": \"masked\", если копия обезличена."
            % (RULE, what, db_id, mark, reg))


def check(tool):
    """Причина отказа для вызова инструмента или None — пропуск. Её же берёт мод «чистка входящих» (inbound-filter.py):
    ответ вызова, который барьер не пропустил бы, до модели не доходит."""
    mm = re.match(r'^mcp__(.+?)__(.+)$', tool)
    if not mm:
        return
    server, name = mm.group(1).lower(), mm.group(2).lower()
    plugin = ''
    if server.startswith('plugin_'):
        plugin, _, server = server[len('plugin_'):].partition('_')
    if 'toolkit' not in server or name in NO_DATA:
        return
    what = "%s: вызов %s отдаёт данные базы 1С" % (RULE, tool)
    try:
        port = server_port(server, plugin)
    except (OSError, ValueError, AttributeError):
        port = None
    if not port:
        return ("%s, а порт сервера '%s' не определить: его нет в .mcp.json %s, url не разбирается или ведёт не на этот "
             "компьютер. Сбой проверки = отказ (п.5 правила). Что сделать: тулкит подключается сервером 1c-toolkit плагина "
             "(порт ONEC_TOOLKIT_PORT) или своим сервером в .mcp.json проекта с url http://127.0.0.1:<порт>/mcp."
             % (what, server, 'плагина ones-core' if plugin else 'проекта'))
    state = os.path.join(plugin_data(), 'state', '1c-toolkit-bases.json')
    try:
        rec = (load(state).get('ports') or {}).get(str(port))
        project, db_id = str(rec['project']), str(rec['db'])
    except (OSError, ValueError, AttributeError, KeyError, TypeError):
        return ("%s, а на какой базе поднят тулкит на порту %d — неизвестно (нет записи в %s). Неизвестная база считается "
             "базой с настоящими ПДн — отказ (п.3 и п.5 правила). Что сделать: закрыть сеанс 1С с обработкой MCP_Toolkit "
             "(инструмент close_1c_session) и поднять тулкит заново командой /ones-core:toolkit [база] — скрипт запишет, "
             "на какой базе он работает." % (what, port, state))
    # запись могла пережить сеанс 1С: на порту теперь другая база (аудит 30.10.2026) — верим ей, только пока жив её процесс
    pid = rec.get('pid') if isinstance(rec, dict) else None
    if not isinstance(pid, int) or not process_alive(pid):
        return ("%s; запись о базе порта %d устарела: %s. На порту может работать уже другая база — отказ (п.5 правила). "
             "Что сделать: поднять тулкит заново командой /ones-core:toolkit [база] — скрипт запишет базу и процесс 1С."
             % (what, port, 'в ней нет номера процесса 1С (запись прежней версии)' if not isinstance(pid, int)
                else 'процесса 1С %d уже нет' % pid))
    reg = os.path.join(project, '.v8-project.json')
    try:
        dbs = load(reg).get('databases') or []
        dbs = [dbs] if isinstance(dbs, dict) else dbs
        db = next((d for d in dbs if isinstance(d, dict) and str(d.get('id')) == db_id), None)
    except (OSError, ValueError, AttributeError, TypeError):
        db = None
    if db is None:
        return ("%s; по записи тулкит на порту %d поднят на базе '%s', но в реестре %s её нет или он не читается — "
             "отказ (п.5 правила). Что сделать: поднять тулкит заново командой /ones-core:toolkit на базе из реестра."
             % (what, port, db_id, reg))
    mark = pd_mark(db)
    if mark is None:
        if base_on_port(port, pid, db):
            return None
        return ("%s; по записи на порту %d база '%s', но ни процесс 1С на этом порту, ни процесс из записи на ней не запущены: "
                "запись подделана или устарела, на порту может быть база с настоящими ПДн — отказ (п.5 правила). Что сделать: "
                "поднять тулкит заново командой /ones-core:toolkit [база]." % (what, port, db_id))
    return ("%s, а у базы '%s' (тулкит на порту %d) %s — значит, в ней настоящие ПДн (п.3 правила). Фильтра-маски ПДн ещё "
            "нет, поэтому данные такой базы не запрашиваются вовсе (п.5). Отметку ставит только владелец — это его решение о "
            "данных, сам её не ставь: в %s у этой базы \"pd\": \"none\", если данных о людях в базе нет, или \"pd\": "
            "\"masked\", если копия обезличена. Пока отметки нет — работай без данных базы: get_metadata, code-index, meta-info."
            % (what, db_id, port, mark, reg))


def main():
    data = json.loads(sys.stdin.buffer.read().decode('utf-8', 'replace').lstrip('﻿'))
    why = check(str(data.get('tool_name') or ''))
    if why:
        deny(why)


if __name__ == '__main__':
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        try:
            deny('%s: барьер ПДн не смог проверить вызов (%s) — сбой = отказ (п.5 правила). Что сделать: сообщи владельцу; '
                 'данные базы до починки барьера не запрашивай.' % (RULE, e))
        except OSError:
            sys.stderr.write('%s: барьер ПДн упал — отказ\n' % RULE)
            sys.exit(2)
    sys.exit(0)
