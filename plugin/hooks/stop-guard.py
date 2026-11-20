"""Stop и SubagentStop: блокирующий гейт для правок 1С и напоминания в конце хода (systemMessage).

Перенос stop-guard.ps1 на Python (ADR-0002). Напоминает о трёх вещах, если они есть:
  1. незакоммиченные модули .bsl в репозитории проекта и в репозиториях исходников из манифеста —
     прогнан ли полный набор проверок, записана ли веха;
  2. правки .bsl, отмеченные в logs/gate-state.json, по которым не записан прогон проверок (режим наблюдения:
     в блокирующем режиме завершение хода было бы отклонено);
  3. защитный скрипт изменился в этой сессии и разошёлся с реестром контрольных сумм contours.sha256;
  4. наблюдение за финальным ответом (с 17.10.2026, режим наблюдения — пишет в logs/answer-check.jsonl и предупреждает,
     ход не продлевает): вопрос владельцу свободным текстом (questions-as-options), ход с вызовами инструментов без
     на SubagentStop — итог помощника-ревьюера без двух вердиктов
     «Стандарты» и «Спека» (two-axis-code-review); с 4.8.0 — ещё десять детекторов по журналу хода (turn_rule_notes):
     текст вызова в ответе, объект 1С без проработки и консилиума, баг без репро и метки [DEBUG-…], журнал не в том
     репозитории, копирование между рабочими деревьями, общие объекты без поручения, сплошное чтение, флаг
     без проверки, постфикс общего модуля против флагов std469, ревью без двух вердиктов. Найденное следующий ход
     показывает модели (answer-feedback.py);
  5. БЛОКИРУЮЩИЙ гейт конца хода (с 17.10.2026, решение владельца): ход или задание помощника с правкой кода или
     метаданных 1С не завершается, пока в нём же нет проверки по стандартам (v8std / скилл 1c-standards), validate_module
     bsl-context по пути каждого изменённого модуля после правки (модуль вне корня выгрузки сервера — текстом, source=),
     парного валидатора после скилла-генератора и перечня инструментов в ответе ({"decision": "block"}). Два отказа подряд
     в одном ходе — пропуск с видимой пометкой и записью в logs/answer-check.jsonl; переключатель stopGate в .v8-project.json
     (block по умолчанию, warn, off).
Молчит, когда напоминать не о чем. Ошибка гейта — пропуск с пометкой DEGRADED; с 30.10.2026 и сбой детектора хода или
наблюдения за ответом называется: строка kind='DEGRADED' с именем детектора в logs/answer-check.jsonl и пометка в systemMessage;
так же называется ход, начала которого нет в самом большом окне журнала: детекторы тогда судят по хвосту.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
I = re.IGNORECASE
ASKS_OWNER = (r'\b(вы|вам|вас|ваш\w*|хотите|нужно ли|сделать ли|делать ли|продолж\w*|подтверд\w*|соглас\w*|выбер\w*|выбрать|'
              r'стоит ли|можно ли|запуст\w*|начать|начинать|или|should i|do you|want me|shall i)\b')
WINDOWS = (16, 64, 256)   # окна чтения хвоста журнала сессии, МБ: растут, пока не найдётся начало хода


def prose_tail(text, n=3):
    """Последние n абзацев прозы: без блоков кода, таблиц, цитат, раскрывашек."""
    text = re.sub(r'```.*?```', ' ', text, flags=re.S)
    paras = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    return [p for p in paras if not p.lstrip().startswith(('|', '>', '<'))][-n:]


def question_in_text(text):
    """Вопрос владельцу свободным текстом в конце ответа (вместо окна вариантов)."""
    for p in prose_tail(text):
        for s in re.split(r'(?<=[.!?…])\s+', p):
            s = s.strip()
            if s.endswith('?') and len(s) > 15 and re.search(ASKS_OWNER, s, I):
                return s[:160]
    return None


def block_text(content):
    if isinstance(content, str):
        return content
    return ' '.join(str(b.get('text') or '') for b in content if isinstance(b, dict)) if isinstance(content, list) else ''


def genuine_prompt(o, blocks, content):
    """Запись, с которой начинается ход: не ответ инструмента и не служебная вставка Claude Code. Отказ Stop-хука
    («Stop hook feedback») пишется как user с isMeta, системные напоминания — как user с текстом <system-reminder>:
    приняв их за границу, гейт после отказа «забывал» правку (живая проба в проекте, 17.10.2026)."""
    if o.get('isMeta') or any(b.get('type') == 'tool_result' for b in blocks):
        return False
    # Запрос в приложении часто приходит ОДНОЙ записью «<system-reminder>…</system-reminder> + текст запроса»: вставка —
    # только запись, где кроме таких блоков ничего нет (живая проба 4.6.1: фильтр по началу текста выбрасывал и сам запрос).
    rest = re.sub(r'<system-reminder>.*?</system-reminder>', '', block_text(content), flags=re.S).strip()
    return bool(rest) and not rest.startswith('Stop hook feedback')


def turn_calls(path):
    """Вызовы инструментов хода (с последнего запроса владельца) по журналу сессии: ([(имя, вход, ответ)], метка хода),
    ответ — (ошибка?, текст) или None, если его в журнале ещё нет; None целиком — журнал не прочитан."""
    if not path or not os.path.isfile(path):
        return None
    # Окно растёт, пока не найдётся начало хода (аудит 30.10.2026: на ходе длиннее 16 МБ журнала гейт молча выключался).
    # Не нашлось и в 256 МБ — весь хвост считается ходом: гейт судит по неполному ходу, а не пропускает его.
    for window in WINDOWS[:-1]:
        found = turn_calls_window(path, window * 1024 * 1024)
        if found is not None:
            return found
    return turn_calls_window(path, WINDOWS[-1] * 1024 * 1024, whole_tail=True)


def turn_calls_window(path, window, whole_tail=False):
    with open(path, 'rb') as f:
        size = f.seek(0, 2)
        start = max(0, size - window)
        f.seek(start)
        lines = f.read().decode('utf-8', 'replace').split('\n')
    if start:
        lines = lines[1:]   # первая строка хвоста обрезана посередине
    calls, results = [], {}
    for line in reversed(lines):
        try:
            o = json.loads(line)
        except ValueError:
            continue
        content = (o.get('message') or {}).get('content')
        blocks = [b for b in content if isinstance(b, dict)] if isinstance(content, list) else []
        if o.get('type') == 'assistant':
            calls.extend((str(b.get('name') or ''), b.get('input') or {}, str(b.get('id') or ''))
                         for b in reversed(blocks) if b.get('type') == 'tool_use')
        elif o.get('type') == 'user':
            for b in blocks:
                if b.get('type') == 'tool_result':
                    results[str(b.get('tool_use_id') or '')] = (bool(b.get('is_error')), block_text(b.get('content')))
            if genuine_prompt(o, blocks, content):
                return ([(n, i, results.get(cid)) for n, i, cid in reversed(calls)], str(o.get('uuid') or o.get('timestamp') or ''),
                        iso_epoch(o.get('timestamp')))
    if start == 0 or whole_tail:   # начала хода нет — ход идёт с начала прочитанного (не «пропустить»)
        return [(n, i, results.get(cid)) for n, i, cid in reversed(calls)], 'transcript-start' if start == 0 else 'transcript-tail', 0.0
    return None


def iso_epoch(ts):
    """Метка журнала сессии (ISO, UTC) в секундах эпохи; 0 — метки нет или она не разобрана."""
    try:
        import datetime
        return datetime.datetime.fromisoformat(str(ts).replace('Z', '+00:00')).timestamp()
    except (TypeError, ValueError):
        return 0.0


def check_ran(res):
    """Ответ validate_module — состоявшаяся проверка (JSON с полем valid), а не отказ сервера ({"ok": false, …})."""
    return bool(res) and not res[0] and '"valid"' in res[1]


def same_module(c, m):
    """Один и тот же модуль: пути совпали или один — хвост другого (путь от корня выгрузки)."""
    return c == m or c.endswith('/' + m) or m.endswith('/' + c)


# ---------- Блокирующий гейт конца хода для правок 1С (с 17.10.2026, решение владельца) ----------
# Ход с правкой кода или метаданных 1С не завершается, пока в этом же ходе нет: проверки по стандартам (v8std или
# скилл 1c-standards), validate_module bsl-context по пути каждого изменённого модуля после его последней правки,
# парного валидатора после скилла-генератора и перечня инструментов в ответе. Два отказа подряд — пропуск с пометкой.
GENERATORS = {
    'meta-compile': 'meta-validate', 'meta-edit': 'meta-validate',
    'form-add': 'form-validate', 'form-compile': 'form-validate', 'form-edit': 'form-validate',
    'role-compile': 'role-validate', 'role-edit': 'role-validate',
    'skd-compile': 'skd-validate', 'skd-edit': 'skd-validate', 'mxl-compile': 'mxl-validate',
    'subsystem-compile': 'subsystem-validate', 'subsystem-edit': 'subsystem-validate', 'interface-edit': 'interface-validate',
    'cf-init': 'cf-validate', 'cf-edit': 'cf-validate',
    'cfe-init': 'cfe-validate', 'cfe-borrow': 'cfe-validate', 'cfe-patch-method': 'cfe-validate',
    'epf-init': 'epf-validate', 'epf-bsp-init': 'epf-validate', 'epf-bsp-add-command': 'epf-validate', 'erf-init': 'erf-validate',
    'xdto-compile': 'xdto-validate', 'xdto-edit': 'xdto-validate', 'template-add': 'mxl-validate|skd-validate',
}
MAX_REFUSALS = 2
OUT_OF_ROOT = r'за\s+корень\s+выгрузки'   # отказ validate_module на файл вне корня выгрузки (живой ответ сервера, 30.10.2026)


def guard_skills():
    """Правила «что такое файл 1С» и «служебная зона» — из guard-skills, чтобы не держать их второй копией."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('guard_skills', os.path.join(HERE, 'guard-skills.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def norm(p):
    return str(p or '').replace('\\', '/').strip().strip('"').lower()


def in_temp(n):
    import tempfile
    tmp = {norm(tempfile.gettempdir()), norm(os.path.realpath(tempfile.gettempdir()))}
    return any(t and n.startswith(t.rstrip('/') + '/') for t in tmp) or '/appdata/local/temp/' in n


RUNNER = re.compile(
    r'^(?:\w+=(?:"[^"]*"|\'[^\']*\'|\S*)\s+)*(?:timeout\s+\d+\s+)?(?:&\s*)?'            # VAR=… перед командой, timeout, & PowerShell
    r'(?:["\']?(?:[^"\'\s]*[\\/])?(?:python3?|py|pwsh|powershell)(?:\.exe)?["\']?'      # интерпретатор, можно полным путём
    r'(?P<flags>(?:\s+-{1,2}[\w-]+(?:\s+(?!["\']?[^\s"\']*\.(?:py|ps1)\b)[^\s-]\S*)?)*)\s+)?'
    r'(?:"(?P<p1>[^"]+\.(?:py|ps1))"|\'(?P<p2>[^\']+\.(?:py|ps1))\'|(?P<p3>[^"\'\s]+\.(?:py|ps1)))', I)


def runs_skill_script(cmd, names):
    """Скрипты скиллов, которые команда ЗАПУСКАЕТ: сегмент начинается с интерпретатора (или & и пути) и пути скрипта.
    Имя скрипта в grep, cat или внутри python -c "…" — не запуск (волна 2 п.2.7, ложный отказ гейта 30.10.2026)."""
    if re.search(r'(^|\s)(--help|-h)(\s|$)', cmd):
        return []
    out = []
    for seg in re.split(r'&&|\|\||[;|\n]', cmd):
        mm = RUNNER.match(seg.strip())
        if not mm or re.search(r'(^|\s)-c\b', mm.group('flags') or ''):
            continue
        leaf = re.search(r'(?:^|[\\/])(%s)\.(?:py|ps1)$' % names, mm.group('p1') or mm.group('p2') or mm.group('p3'), I)
        if leaf:
            out.append(leaf.group(1).lower())
    return out


def gate_mode(root):
    try:
        with open(os.path.join(root, '.v8-project.json'), encoding='utf-8-sig') as f:
            mode = str((json.load(f) or {}).get('stopGate') or '').lower()
    except (OSError, ValueError, AttributeError):
        mode = ''
    return mode if mode in ('block', 'warn', 'off') else 'block'


SHELL_MAX_EACH = 5   # до стольких модулей от команды — проверка каждого; больше — пакетная проверка
BATCH_CHECK = re.compile(r'bsl-analyzer(?:\.exe)?["\']?\s+analyze\b|epf-build\.(?:py|ps1)|/CheckConfig\b|/CheckModules\b', I)
_SHELL_ARM = []


def shell_arm():
    """Модуль shell-arm.py: ключ команды и путь состояния определены там один раз, гейт берёт их оттуда."""
    if not _SHELL_ARM:
        import importlib.util
        spec = importlib.util.spec_from_file_location('shell_arm_for_gate', os.path.join(HERE, 'shell-arm.py'))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _SHELL_ARM.append(mod)
    return _SHELL_ARM[0]


def cmd_key(cmd):
    """Ключ команды оболочки (shell-arm.cmd_key): им записанные командой файлы 1С связываются с вызовом в журнале хода."""
    return shell_arm().cmd_key(cmd)


def shell_armed(root, sid, since=0.0):
    """Файлы 1С, записанные командами оболочки этой сессии (shell-arm.py): {ключ команды: [пути]}.

    since — начало хода (секунды эпохи): запись прошлого хода той же командой не взводит текущий.
    None — файл состояния есть, но не прочитан и после повтора (битый или занят): это не «взвода нет»."""
    for attempt in (0, 1):
        try:
            with open(os.path.join(root, shell_arm().SHELL_STATE), encoding='utf-8-sig') as f:
                st = json.load(f)
            rows = (st.get(sid) or {}).get('armed') or [] if isinstance(st, dict) else []
            break
        except FileNotFoundError:
            return {}
        except (OSError, ValueError, AttributeError):
            if attempt:
                return None
            time.sleep(0.2)
    out = {}
    for r in rows:
        if isinstance(r, dict) and r.get('cmd') and isinstance(r.get('files'), list):
            if since and float(r.get('ts') or 0) < since:
                continue
            out.setdefault(r['cmd'], [])
            out[r['cmd']] += [str(x) for x in r['files'] if x not in out[r['cmd']]]
    return out


_CHANGE_PROFILE = []
_CP_ERR = []   # почему классификатор не загружен: main выводит пометку DEGRADED


def contour_sha(path):
    """Отпечаток файла как в реестре contours.sha256: BOM снят, CRLF -> LF (как в gen-contour-registry)."""
    with open(path, 'rb') as f:
        txt = f.read().decode('utf-8-sig', 'replace').replace('\r\n', '\n')
    return hashlib.sha256(txt.encode('utf-8')).hexdigest()


def read_registry():
    """Реестр отпечатков контуров рядом с этим файлом: {имя: sha256}; реестра нет — {}."""
    reg = {}
    p = os.path.join(HERE, 'contours.sha256')
    if os.path.isfile(p):
        with open(p, encoding='utf-8-sig') as f:
            for line in f.read().splitlines():
                t = line.strip('\ufeff')
                if not t or t.startswith('#'):
                    continue
                parts = t.split('|')
                if len(parts) >= 2:
                    reg[parts[0]] = parts[1]
    return reg


def change_profile():
    """Классификатор класса правки change-profile.py (в плагине — hooks/../tools/setup, в мастере — plugin/../tools/setup).
    Грузится, только если отпечаток совпал с записью реестра contours.sha256; None — нет файла, отпечаток разошёлся или
    загрузка упала (причина в _CP_ERR, C0 выключен — гейт строже)."""
    if not _CHANGE_PROFILE:
        mod = None
        found = [p for p in (os.path.join(HERE, '..', 'tools', 'setup', 'change-profile.py'),
                             os.path.join(HERE, '..', '..', 'tools', 'setup', 'change-profile.py')) if os.path.isfile(p)]
        if not found:
            _CP_ERR.append('файл не найден')
        else:
            saved = list(sys.path)   # change-profile.py ставит tools/lib в sys.path[0]: после загрузки вернуть как было
            try:
                want = read_registry().get('change-profile.py')
                if not want:
                    _CP_ERR.append('нет записи в реестре contours.sha256')
                elif contour_sha(found[0]) != want:
                    _CP_ERR.append('отпечаток разошёлся с реестром contours.sha256')
                else:
                    import importlib.util
                    spec = importlib.util.spec_from_file_location('change_profile_for_gate', found[0])
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
            except Exception as e:
                mod = None
                _CP_ERR.append('ошибка загрузки: %s' % str(e)[:160])
            finally:
                sys.path[:] = saved
        _CHANGE_PROFILE.append(mod)
    return _CHANGE_PROFILE[0]


_C0 = {}            # (путь, начало хода) -> C0 ли модуль: второй проход гейта и повтор для записи командой git не зовут
_C0_NOREPO = set()  # папки, где git отказал (не репозиторий): C0 там невозможен, git повторно не запускается
_C0_DEADLINE = []   # общий срок git-вызовов C0 за ход: таймаут всего Stop-хука 15 с
C0_BUDGET_S = 4.0


def c0_module(path, since=0.0, root=''):
    """Класс глубины C0 (с 10.11.2026, по мотивам 1c-quality-gate): модуль отличается от HEAD только комментариями и пустыми
    строками — по change-profile.cosmetic, второго классификатора нет. Не C0: модуля нет в HEAD, он закоммичен после начала
    хода since (секунды эпохи), нет git или классификатора, модуль сверх SHELL_MAX_EACH за ход, общий срок git-вызовов истёк."""
    if not path or not os.path.isfile(path):
        return False
    key = (path, since)
    if key in _C0:
        return _C0[key]
    d, name = os.path.dirname(path), os.path.basename(path)
    nd = norm(d)
    if any(nd == x or nd.startswith(x + '/') for x in _C0_NOREPO) or len(_C0) >= SHELL_MAX_EACH:
        return False
    cp = change_profile()
    if cp is None or not hasattr(cp, 'cosmetic'):
        return False
    if not _C0_DEADLINE:
        _C0_DEADLINE.append(time.time() + C0_BUDGET_S)
    if time.time() >= _C0_DEADLINE[0]:
        return False

    def git(*args):
        left = _C0_DEADLINE[0] - time.time()
        if left <= 0:   # срок общий на ход: вызов после него не запускается (итог — не C0, строже)
            raise subprocess.TimeoutExpired(args, 0)
        return subprocess.run(['git', '--no-optional-locks', '-C', d] + list(args), capture_output=True, timeout=max(0.2, left))
    _C0[key] = False
    try:
        r = git('rev-parse', '--verify', '-q', 'HEAD:./' + name)   # 1 — модуля нет в HEAD, 128 — не репозиторий
        if r.returncode != 0:
            if r.returncode == 128:   # не репозиторий: и папка модуля, и корень проекта над ней (модули лежат по разным Ext)
                _C0_NOREPO.add(nd)
                if root and nd.startswith(norm(root).rstrip('/') + '/'):
                    _C0_NOREPO.add(norm(root).rstrip('/'))
            return False
        if since > 0:   # закоммиченное в этом ходе сравнивалось бы с собой: дифф пуст, а правка кода была
            r = git('log', '-1', '--format=%ct', 'HEAD', '--', './' + name)
            if r.returncode != 0 or int(r.stdout.decode('ascii', 'replace').strip() or 0) >= int(since):
                return False
        # -a --no-textconv --no-ext-diff: атрибуты -diff, binary, textconv и diff.external не прячут строки правки
        r = git('-c', 'core.quotepath=off', 'diff', 'HEAD', '-U0', '--no-color', '-a', '--no-textconv', '--no-ext-diff',
                '--', './' + name)
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    if r.returncode != 0:
        return False
    lines = r.stdout.decode('utf-8', 'replace').splitlines()
    _C0[key] = cp.cosmetic([x[1:] for x in lines if x.startswith('+') and not x.startswith('+++')],
                           [x[1:] for x in lines if x.startswith('-') and not x.startswith('---')])
    return _C0[key]


def gate_missing(calls, gs, root='', armed=None, since=0.0, blind=False):
    """Чего не хватает ходу с правкой 1С; None — правок 1С в ходе не было.

    armed — файлы 1С, записанные командами оболочки (shell-arm.py, по мотивам 1c-quality-gate): {cmd_key: [пути]};
    since — начало хода (секунды эпохи): модуль, закоммиченный после него, не C0;
    blind — состояние shell-arm не прочитано: что записали команды оболочки, не видно, после последней нужна пакетная проверка."""
    armed = armed or {}
    last_shell = None   # индекс последней команды оболочки, кроме самой пакетной проверки
    modules, meta, gens, ran = {}, [], [], []
    bulk = []      # (индекс, число) — команды, записавшие больше SHELL_MAX_EACH модулей: им нужна пакетная проверка
    standards = False
    checked = []   # (индекс, путь) состоявшихся проверок validate_module
    texts = []     # (индекс, module_path) состоявшихся проверок текстом, source=
    beyond = []    # пути, которые сервер отклонил как лежащие вне корня выгрузки
    refused = 0    # вызовы validate_module с отказом сервера (нет источника имён, не указан repo и т. п.)
    trees = {}     # относительный путь записи через EDT -> имя её проекта
    orig = {}      # нормализованный путь модуля -> путь как записан (для git нужен регистр букв)
    gen_names = '|'.join(re.escape(k) for k in GENERATORS)
    val_names = '|'.join(sorted({x for v in GENERATORS.values() for x in v.split('|')}))
    for i, (name, inp, res) in enumerate(calls):
        inp = inp if isinstance(inp, dict) else {}
        if name in ('Edit', 'Write', 'MultiEdit', 'NotebookEdit'):
            n = norm(inp.get('file_path'))
            inside = bool(root) and n.startswith(norm(root).rstrip('/') + '/')
            if not n or gs.exempt(n, {}) or (in_temp(n) and not inside):   # временная папка вне проекта — не рабочая конфигурация
                continue
            leaf = n.split('/')[-1]
            if n.endswith('.bsl'):
                modules[n] = i
                orig[n] = str(inp.get('file_path'))
            elif any(match(leaf, n) for match, _ in gs.RULES):
                meta.append(n)
        elif re.match(r'^mcp__.*edt.*__write_module_source$', name, I):
            n = norm(inp.get('modulePath') or inp.get('path') or inp.get('file_path'))
            if n:
                modules[n] = i
                if inp.get('projectName') and not re.match(r'^([a-z]:)?/', n):
                    trees[n] = norm(inp.get('projectName'))
        elif re.match(r'^mcp__.*bsl-context.*__validate_module$', name, I):
            if inp.get('path') and check_ran(res):
                checked.append((i, norm(inp.get('path'))))
            elif inp.get('path'):
                refused += 1
                if res and re.search(OUT_OF_ROOT, res[1], I):
                    beyond.append(norm(inp.get('path')))
            elif inp.get('source') and check_ran(res):
                texts.append((i, norm(inp.get('module_path'))))
        # стандарты — поиск и чтение стандарта или разбор кода и диагностик с ответом (волна 2 п.2.7), а не любой вызов v8std:
        # отказ сервера проверкой не считается
        elif (re.match(r'^mcp__.*v8std.*__v8std_(search|get_page|get_related|explain_diagnostics|explain_snippet)$', name, I) and not (res and res[0])) or \
                (name == 'Skill' and re.search(r'(^|:)1c-standards$', str(inp.get('skill') or ''), I)):
            standards = True
        elif name in ('Bash', 'PowerShell'):
            cmd = str(inp.get('command') or '')
            if not sandbox_run(cmd, gen_names, root):   # генератор в песочнице вне проекта — не правка конфигурации
                gens += [(i, g) for g in runs_skill_script(cmd, gen_names)]
            ran += [(i, v) for v in runs_skill_script(cmd, val_names)]
            if BATCH_CHECK.search(cmd):
                ran.append((i, '*batch*'))
            else:
                last_shell = i
            for p in armed.get(cmd_key(cmd), []):
                orig.setdefault(norm(p), str(p))
            wrote = [norm(p) for p in armed.get(cmd_key(cmd), [])]
            bsl = [p for p in wrote if p.endswith('.bsl')]
            # больше SHELL_MAX_EACH модулей — сразу пакетная проверка, C0 не считается (бюджет вызовов git за ход)
            shell_mods = bsl if len(bsl) > SHELL_MAX_EACH else [p for p in bsl if not c0_module(orig.get(p), since, root)]
            meta += [p for p in wrote if not p.endswith('.bsl')]
            if len(shell_mods) > SHELL_MAX_EACH:
                bulk.append((i, len(shell_mods)))
            else:
                for p in shell_mods:
                    modules[p] = i
    # класс C0: модуль, где в сравнении с HEAD менялись только комментарии и пустые строки, — хватает проверок хука validate-bsl
    # (анализатор, гигиена); стандарты и validate_module не требуются (full-checker-set-before-done п.8а)
    for m in [m for m in modules if m in orig and c0_module(orig[m], since, root)]:
        del modules[m]
    blind_need = blind and last_shell is not None and not any(vi > last_shell and v == '*batch*' for vi, v in ran)
    if not modules and not meta and not gens and not bulk and not blind_need:
        return None
    missing = []
    if not standards:
        missing.append('проверки по стандартам — скилл 1c-standards (локально, по карте code-situation-standards-map) или '
                       'v8std: разбор процедуры v8std_explain_snippet, поиск v8std_search по теме правки')
    # Сервер читает файлы только под своим корнем (ONEC_PROJECT_SRC, run-bsl-context.py). Модуль вне корня проверяется текстом;
    # путь с тем же хвостом проверил бы двойника из основного дерева, поэтому у такого модуля засчитан только точный путь.
    src = norm(os.environ.get('ONEC_PROJECT_SRC'))
    outside = [m for m in modules if any(same_module(c, m) for c in beyond) or
               (bool(src) and re.match(r'^([a-z]:)?/', m) is not None and not under(m, src))]

    def in_tree(c, m):
        """Проверка относится к дереву записи: модуль с тем же хвостом бывает и в основной конфигурации, и в расширении, поэтому
        у записи через EDT мимо корня сервера в пути проверки нужна папка проекта."""
        tree = trees.get(m)
        return not tree or '/%s/' % tree in '/%s/' % src or '/%s/' % tree in '/%s/' % c

    def path_checked(m, at):
        return any(ci > at and in_tree(c, m) and (c == m if m in outside else same_module(c, m)) for ci, c in checked)

    def short(paths):
        return ', '.join(u.split('/')[-3:][0] + '/…/' + u.split('/')[-1] if u.count('/') > 2 else u for u in paths[:4])
    unchecked = [m for m, at in modules.items() if m not in outside and not path_checked(m, at) and
                 not (m in trees and any(ci > at and c and same_module(c, m) and in_tree(c, m) for ci, c in texts))]
    left = [m for m in outside if not path_checked(m, modules[m]) and
            not any(ci > modules[m] and c and same_module(c, m) and in_tree(c, m) for ci, c in texts)]
    if len(left) == 1 and any(ci > modules[left[0]] and not c for ci, c in texts):   # текст без module_path не привязан к модулю
        left = []
    if unchecked:
        missing.append('проверки модуля по API платформы после правки — validate_module (bsl-context) с path= и repo= (в проекте '
                       'с плагином — repo="default"), засчитывается только ответ с полем valid, для: %s%s'
                       % (short(unchecked), ('; сервер отказал %d раз — проверь symbol_sources_status' % refused) if refused else ''))
        if any(m in trees for m in unchecked):
            missing[-1] += ('; запись через EDT: укажи полный путь с папкой проекта (%s) или проверь текстом, source= и module_path= '
                            'с этой папкой: модуль с тем же хвостом бывает и в расширении' % ', '.join(sorted({trees[m] for m in unchecked if m in trees})))
    if left:
        missing.append('проверки модуля вне корня выгрузки bsl-context — validate_module с source= (текст модуля), module_path= '
                       '(путь от папки исходников) и repo=, засчитывается ответ с полем valid; path= сервер для него отклоняет, для: %s'
                       % short(left))
    for gi, g in gens:
        need = GENERATORS[g].split('|')
        if not any(vi > gi and v in need for vi, v in ran):
            missing.append('парного валидатора после %s — запусти %s' % (g, ' или '.join(need)))
    for bi, n in bulk:
        if not any(vi > bi and v == '*batch*' for vi, v in ran):
            missing.append('пакетной проверки %d модулей, записанных командой оболочки, — bsl-analyzer analyze по их папке или сборка '
                           'с проверкой платформой (epf-build, /CheckConfig, /CheckModules) после этой команды' % n)
    if blind_need:
        missing.append('пакетной проверки после команд оболочки: состояние shell-arm не читается (logs/shell-arm.json битый или занят), '
                       'записанные ими файлы 1С гейту не видны — bsl-analyzer analyze по папке исходников или сборка с проверкой '
                       'платформой (epf-build, /CheckConfig, /CheckModules) после последней команды')
    summary = 'модулей %d, объектов метаданных %d, генераторов %d' % (len(modules) + sum(n for _, n in bulk), len(meta), len(gens))
    return list(dict.fromkeys(missing)), summary


def gate_state(root, key, turn, refused=None):
    """Счётчик отказов подряд для этого хода (logs/stop-gate.json); новый ход — счёт с нуля."""
    p = os.path.join(root, 'logs', 'stop-gate.json')
    try:
        with open(p, encoding='utf-8-sig') as f:
            st = json.load(f)
        st = st if isinstance(st, dict) else {}
    except (OSError, ValueError):
        st = {}
    rec = st.get(key) if isinstance(st.get(key), dict) else {}
    count = int(rec.get('refused') or 0) if rec.get('turn') == turn else 0
    if refused is not None:
        st[key] = {'turn': turn, 'refused': refused}
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, 'w', encoding='utf-8', newline='\n') as f:
                json.dump(st, f, ensure_ascii=False, indent=1)
        except OSError:
            pass
    return count


def stop_gate(root, sid, data):
    """Решение гейта: (решение, текст) — ('block'|'warn'|'skipped', …) или None, если гейт молчит."""
    mode = gate_mode(root)
    if mode == 'off':
        return None
    sub = data.get('hook_event_name') == 'SubagentStop'
    path = str(data.get('agent_transcript_path') or '') if sub else str(data.get('transcript_path') or '')
    got = turn_calls(path)
    if got is None:
        return None
    gs = guard_skills()
    text = str(data.get('last_assistant_message') or '')
    lost = []   # состояние shell-arm не прочитано в ходе с командой оболочки: записи командой не видны гейту

    def armed_now(got):
        armed = shell_armed(root, sid, got[2])
        if armed is None and any(c[0] in ('Bash', 'PowerShell') for c in got[0]):
            if not lost:
                log_answer(root, sid, 'DEGRADED', 'stop-guard: состояние shell-arm не прочитано')
            lost.append(1)
        return armed or {}
    armed = armed_now(got)
    res = gate_missing(got[0], gs, root, armed, got[2], blind=bool(lost))
    if res and res[0]:
        time.sleep(1.0)   # журнал сессии пишется с задержкой: перед отказом — перечитать один раз
        got = turn_calls(path) or got
        armed = armed_now(got)
        res = gate_missing(got[0], gs, root, armed, got[2], blind=bool(lost))
    key = '%s:%s' % (sid, data.get('agent_id') or 'main')
    if not res or not res[0]:
        if res is not None:
            gate_state(root, key, got[1], refused=0)
        if lost:
            return 'degraded', 'гейт конца хода: DEGRADED — записи командой оболочки не проверены: состояние shell-arm не читается'
        return None
    missing, summary = res
    listed = '; '.join('%d) %s' % (k + 1, x) for k, x in enumerate(missing))
    if mode == 'warn':
        log_answer(root, sid, 'stop-gate-warn', listed[:300])
        return 'warn', 'гейт конца хода (режим warn): в ходе правки 1С (%s), не хватает: %s' % (summary, listed)
    count = gate_state(root, key, got[1])
    if data.get('stop_hook_active') and count == 0:
        count = 1
    if count >= MAX_REFUSALS:
        gate_state(root, key, got[1], refused=0)
        log_answer(root, sid, 'stop-gate-skipped', listed[:300])
        return 'skipped', ('гейт конца хода ПРОПУЩЕН после %d отказов подряд — ход завершён без проверок: %s (%s). '
                           'Это не «проверено»: недостающее надо сделать следующим ходом.' % (MAX_REFUSALS, listed, summary))
    gate_state(root, key, got[1], refused=count + 1)
    return 'block', ('stop-gate (блокирующий гейт конца хода, docs/tools/full-checker-set-before-done.md): в этом %s менялись код '
                     'или метаданные 1С (%s), а в нём же не было: %s. Доделай недостающее и заверши ответ заново. Отказ %d из %d — '
                     'после %d-го гейт пропустит ход с видимой пометкой.'
                     % ('задании помощника' if sub else 'ходе', summary, listed, count + 1, MAX_REFUSALS, MAX_REFUSALS))


def log_answer(root, sid, kind, sample):
    try:
        os.makedirs(os.path.join(root, 'logs'), exist_ok=True)
        with open(os.path.join(root, 'logs', 'answer-check.jsonl'), 'a', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps({'ts': int(time.time()), 'sid': sid, 'kind': kind, 'sample': sample}, ensure_ascii=False) + '\n')
    except OSError:
        pass


def answer_notes(root, sid, data):
    """Режим наблюдения: срабатывание — в журнал и в предупреждение; в блокирующем режиме ход был бы продлён."""
    notes = []
    text = str(data.get('last_assistant_message') or '')
    if data.get('hook_event_name') == 'SubagentStop':
        if re.search(r'review', str(data.get('agent_type') or ''), I) and text.strip() and not (
                re.search(r'Стандарты\W{0,3}:', text) and re.search(r'Спека\W{0,3}:', text)):
            log_answer(root, sid, 'two-axis-code-review', text[:160])
            notes.append('итог помощника-ревьюера без двух вердиктов «Стандарты:» и «Спека:» (two-axis-code-review)')
        return notes
    if not text.strip():
        return notes
    q = question_in_text(text)
    if q:
        log_answer(root, sid, 'questions-as-options', q)
        notes.append('вопрос владельцу свободным текстом, а не окном вариантов (questions-as-options): «%s»' % q)
    view = session_view(str(data.get('transcript_path') or ''))
    if view and view.get('partial'):
        what = ('stop-guard: начала хода нет в последних %d МБ журнала — детекторы судят по хвосту, запрос владельца им не виден'
                % WINDOWS[-1])
        log_answer(root, sid, 'DEGRADED', what)
        notes.append('DEGRADED — ' + what)
    for rule, what in (turn_rule_notes(root, view, text) if view else []):
        log_answer(root, sid, rule, what[:300])
        notes.append('%s (%s)' % (what, rule))
    return notes


# ---------- Наблюдение за ходом по правилам ядра (с 4.8.0, решение владельца 17.10.2026) ----------
# Нарушение, видимое по журналу хода синтаксически, пишется в logs/answer-check.jsonl; в начале следующего хода
# answer-feedback.py показывает его модели («исправь»). Ход не продлевается: ложное срабатывание стоит одной подсказки.
ROLES = {'architect-1c', 'analyst-1c', 'ui-designer-1c', 'programmer-1c', 'tester-1c'}
ROLE_WORDS = ('архитектор', 'аналитик', 'дизайнер', 'программист', 'тестировщик')
CREATORS = ('meta-compile', 'form-add', 'form-compile', 'role-compile', 'skd-compile', 'mxl-compile', 'subsystem-compile', 'cf-init',
            'cfe-init', 'cfe-borrow', 'epf-init', 'epf-bsp-init', 'erf-init', 'xdto-compile', 'template-add')
EDITS = ('Edit', 'Write', 'MultiEdit', 'NotebookEdit')
EDT_WRITE = r'^mcp__.*edt.*__write_module_source$'
BUG = (r'(\bошибк[аиуе]\b|\bбаг\w*|не\s+работа(?:ет|ют)|\bпада(?:ет|ют)\b|\bупал[аио]?\b|\bисключени[ея]\b|\bслома\w*|\bглюч\w*|'
       r'\bbugs?\b|\berrors?\b|\bexceptions?\b|\bcrash\w*)')
# прогон тестов 1С — запуск, а не упоминание: харнессы ядра plugin/tools/yaxunit/run-tests.py и plugin/tools/vanessa/run-scenario.py,
# vrunner, клиент 1С с RunUnitTests, команда /ones-core:tests, инструменты прогона (замер 30.10.2026)
HARNESS = r'run[-_]?tests?|run-scenario'
TEST_CMD = r'(?:&\s*)?["\']?(?:[^"\'\s]*[\\/])?(?:vrunner|oscript)(?:\.\w+)?["\']?\s|(?:.*\b1cv8c?(?:\.exe)?\b|\s*start-process\b).*\brununittests\b'
TEST_TOOL = r'^mcp__.*(yaxunit|execute_code|run_?tests?)'
VERDICT = r'вердикт(?:\s+сценария)?:'
REQUEST = (r'\b(сделай|делай|сделайте|исправь|исправьте|поправь|добавь|добавьте|измени|поменяй|внеси|внедри|реализуй|удали|переименуй|'
           r'перенеси|почини|напиши|создай|доработай|обнови|начинай|начни|продолжай|продолжи|подними|выпускай|выпусти|запусти|прогони|'
           r'оформи|приведи|убери|замени|верни|откати|настрой|подключи|поставь|закоммить|давай|да|ок|нужно|надо|необходимо|хочу|прошу|'
           r'можешь|можете|fix|add|change|implement|update|create|remove|rename|continue|go ahead|yes|please)\b')
SHARED = r'(^|/)(commonmodules|roles)/|(^|/)configuration\.(xml|mdo)$'


def statements(prompt):
    """Запрос владельца без вопросов: предложение со знаком «?» — не поручение и не вставленный текст ошибки."""
    said = [s for s in re.split(r'(?<=[.!?…])\s+|\n+', prompt or '') if s.strip()]
    return ' '.join(s for s in said if not re.sub(r'[\s)\]»"\'`*_]+$', '', s).endswith('?'))


def request_in(prompt):
    """Поручение в запросе владельца: слово-поручение вне вопросов. «Нужно ли подключать Vanessa?» поручения не даёт,
    «Надо подключить Vanessa.» — даёт (30.10.2026)."""
    return re.search(REQUEST, statements(prompt), I) is not None


COPY =r'(^|[\s;&|(])(cp|copy|xcopy|robocopy|copy-item|cpi|rsync)\s|shutil\.copy'
SHELL = {'git', 'cd', 'ls', 'dir', 'cat', 'type', 'echo', 'grep', 'rg', 'find', 'head', 'tail', 'sed', 'awk', 'cp', 'mv', 'rm', 'mkdir',
         'sort', 'uniq', 'wc', 'xargs', 'tee', 'printf', 'test', 'set', 'export', 'curl', 'wget'}
RUNNERS = {'python', 'python3', 'py', 'node', 'pwsh', 'powershell', 'uv', 'npx', 'cmd', 'bash', 'sh'}
CM_FILE = re.compile(r'/commonmodules/([^/]+)/\1\.mdo$|/commonmodules/[^/]+\.xml$')
BIG_READ = 100 * 1024   # символов в ответе Read: больше — файл прочитан сплошняком
AUTOMATED = r'\s*(<task-notification>|<side-sessions-event>|<ci-monitor-event>|This session is being continued|Continue from where)'


def session_view(path):
    """Журнал сессии по порядку: вызовы [(имя, вход, ответ)], тексты модели [(номер следующего вызова, текст)], номер первого
    вызова текущего хода и текст его запроса без системных вставок; None — журнал не прочитан. Окна — как у turn_calls: не нашлось
    начала хода и в самом большом — весь хвост считается ходом с признаком partial, запроса владельца при этом нет."""
    if not path or not os.path.isfile(path):
        return None
    for window in WINDOWS[:-1]:
        view = session_view_window(path, window * 1024 * 1024)
        if view is not None:
            return view
    return session_view_window(path, WINDOWS[-1] * 1024 * 1024, whole_tail=True)


def session_view_window(path, window, whole_tail=False):
    with open(path, 'rb') as f:
        size = f.seek(0, 2)
        start = max(0, size - window)
        f.seek(start)
        lines = f.read().decode('utf-8', 'replace').split('\n')
    if start:
        lines = lines[1:]
    calls, ids, texts = [], {}, []
    turn, prompt = (0 if start == 0 else None), ''
    for line in lines:
        try:
            o = json.loads(line)
        except ValueError:
            continue
        if not isinstance(o, dict):
            continue
        content = o['message'].get('content') if isinstance(o.get('message'), dict) else None
        blocks = [b for b in content if isinstance(b, dict)] if isinstance(content, list) else []
        if o.get('type') == 'assistant':
            for b in blocks:
                if b.get('type') == 'tool_use':
                    ids[str(b.get('id') or '')] = len(calls)
                    calls.append([str(b.get('name') or ''), b.get('input') if isinstance(b.get('input'), dict) else {}, None])
                elif b.get('type') == 'text' and b.get('text'):
                    texts.append((len(calls), str(b.get('text'))))
        elif o.get('type') == 'user':
            for b in blocks:
                k = ids.get(str(b.get('tool_use_id') or '')) if b.get('type') == 'tool_result' else None
                if k is not None:
                    calls[k][2] = (bool(b.get('is_error')), block_text(b.get('content')))
            if genuine_prompt(o, blocks, content):
                turn = len(calls)
                prompt = re.sub(r'<system-reminder>.*?</system-reminder>', '', block_text(content), flags=re.S).strip()
                if re.match(AUTOMATED, prompt):   # ход начат событием, а не владельцем: слов владельца в нём нет
                    prompt = ''
    if turn is None and not whole_tail:
        return None
    return {'calls': [tuple(c) for c in calls], 'texts': texts, 'turn': turn or 0, 'prompt': prompt, 'partial': turn is None}


def fs_path(p):
    """Путь из вызова — в путь файловой системы: /d/x (Git Bash) → d:/x."""
    p = str(p or '').strip().strip('"\'')
    m = re.match(r'^/([a-zA-Z])/(.*)$', p)
    return '%s:/%s' % (m.group(1), m.group(2)) if m else p


def under(n, top):
    return n.startswith(norm(top).rstrip('/') + '/')


def work_file(n, root):
    """Файл рабочей конфигурации, а не одноразовая копия во временной папке вне проекта."""
    return bool(n) and not (in_temp(n) and not under(n, root))


def mentions_temp(cmd):
    import tempfile
    n = norm(cmd)
    return '/appdata/local/temp/' in n or any(t and t in n for t in {norm(tempfile.gettempdir()), norm(os.path.realpath(tempfile.gettempdir()))})


TARGET_ARGS = (r'-(OutputDir|ConfigPath|ConfigDir|ObjectPath|RolePath|SubsystemPath|FormPath|TemplatePath|CIPath|ExtensionPath|'
               r'SrcDir|SourceDir)\s+("([^"]+)"|\'([^\']+)\'|([^\s;&|]+))')
EDT_CREATE = r'^mcp__.*edt.*__(create_metadata|create_\w+|add_metadata\w*)$'
EDITORS = ('meta-edit', 'role-edit', 'cf-edit', 'subsystem-edit', 'interface-edit', 'form-edit', 'skd-edit', 'xdto-edit')


def bash_path(p):
    """Путь из команды в общем виде: «/d/x» оболочки Git Bash — это «d:/x»."""
    return re.sub(r'^/([a-z])/', r'\1:/', norm(p))


def work_tops(root):
    """Где лежит конфигурация проекта: корень, ONEC_PROJECT_SRC* и configSrc/src реестра баз (бывают вне корня)."""
    tops = [norm(root)] if root else []
    tops += [norm(v) for k, v in os.environ.items() if k.upper().startswith('ONEC_PROJECT_SRC') and v]
    try:
        if not root:
            raise OSError
        with open(os.path.join(root, '.v8-project.json'), encoding='utf-8-sig') as f:
            reg = json.load(f) or {}
        for db in reg.get('databases') or []:
            for p in [db.get('configSrc')] + [e.get('src') for e in db.get('extensions') or [] if isinstance(e, dict)]:
                if isinstance(p, str) and p:
                    tops.append(norm(p if os.path.isabs(p) else os.path.join(root, p)))
    except (OSError, ValueError, AttributeError, TypeError):
        pass
    return [t for t in tops if t]


def sandbox_run(cmd, names, root):
    """Запуск скилла-генератора или редактора в песочнице — цель во временной папке или вне проекта (D:/_work, пилоты, замер),
    а не в конфигурации проекта. Цель в проекте или его исходниках — работа, даже если проект во временной папке."""
    rest = re.sub(r'\S*(?:%s)\.(?:py|ps1)\S*' % names, ' ', cmd, flags=I)   # скрипт кандидата плагина бывает во временной папке
    def absolute(paths):
        return [bash_path(t) for t in paths if re.match(r'^([a-zA-Z]:[\\/]|/)', t)]
    tops = work_tops(root)

    def inside(paths):
        return any(any(a == t or under(a, t) for t in tops) for a in paths)
    # судится цель: явная абсолютная — сама по себе; относительная — от каталога, куда перешла команда (cd); без cd — от
    # проекта. Входной JSON во временной папке («-JsonPath %TEMP%\o.json -OutputDir src») — не песочница
    tgt = absolute([m[2] or m[3] or m[4] for m in re.findall(TARGET_ARGS, rest, I)])
    if tgt:
        return not inside(tgt)
    cds = [m[1] or m[2] or m[3] for m in re.findall(r'(?:^|[;&|(]\s*)cd\s+("([^"]+)"|\'([^\']+)\'|([^\s;&|]+))', rest)]
    if not cds:
        return False
    if absolute(cds):
        return not inside(absolute(cds))
    return mentions_temp(rest)   # cd в переменную («cd $S»): судит только признак временной папки в самой команде


def is_1c(n, gs):
    return n.endswith('.bsl') or any(match(n.split('/')[-1], n) for match, _ in gs.RULES)


def config_tops(root):
    """Корни git-репозиториев исходников конфигурации из ONEC_PROJECT_SRC*, кроме репозитория самого проекта."""
    own = norm(git('-C', root, 'rev-parse', '--show-toplevel').strip())
    tops = []
    for k, v in os.environ.items():
        if k.upper().startswith('ONEC_PROJECT_SRC') and v and os.path.exists(v):
            t = git('-C', v, 'rev-parse', '--show-toplevel').strip()
            if t and norm(t) != own and t not in tops:
                tops.append(t)
    return tops


def edited(calls, root=''):
    """Правленые файлы: [(путь как в вызове, нормализованный)] — Edit/Write, запись модуля через EDT и цели скриптов-редакторов
    (meta-edit, role-edit и др. через Bash; в песочнице вне проекта — не правка)."""
    out = []
    names = '|'.join(re.escape(e) for e in EDITORS)
    for name, inp, _ in calls:
        if name in EDITS or re.match(EDT_WRITE, name, I):
            p = str(inp.get('file_path') or inp.get('modulePath') or inp.get('path') or '')
            if p:
                out.append((p, norm(p)))
        elif name in ('Bash', 'PowerShell'):
            cmd = str((inp or {}).get('command') or '')
            if runs_skill_script(cmd, names) and not sandbox_run(cmd, names, root):
                rest = re.sub(r'\S*(?:%s)\.(?:py|ps1)\S*' % names, ' ', cmd, flags=I)
                out += [(p, bash_path(p)) for p in (mm[2] or mm[3] or mm[4] for mm in re.findall(TARGET_ARGS, rest, I))]
    return out


def chat_call(text):
    """tool-calls-not-chat-text п.1: разметка вызова инструмента в тексте ответа (вне блоков кода)."""
    bare = re.sub(r'`[^`\n]*`', ' ', re.sub(r'```.*?```', ' ', text, flags=re.S))
    m = re.search(r'<(?:antml:)?(?:invoke|function_calls|parameter)\b[^>\n]{0,80}>', bare)
    return [('tool-calls-not-chat-text', 'в ответе текст вызова инструмента вместо самого вызова: «%s»' % m.group(0)[:80])] if m else []


def created_object(view, gs, root=''):
    """Первый вызов хода, создающий объект 1С: скилл-генератор с целью в проекте (не в песочнице), создание через EDT или новый
    файл метаданных."""
    names = '|'.join(re.escape(c) for c in CREATORS)
    for k in range(view['turn'], len(view['calls'])):
        name, inp, res = view['calls'][k]
        if name in ('Bash', 'PowerShell'):
            cmd = str(inp.get('command') or '')
            g = runs_skill_script(cmd, names)
            # сам скрипт может лежать во временной папке (кандидат плагина на пробе) — судится цель, а не путь скрипта
            if g and not sandbox_run(cmd, names, root):
                return k, g[0]
        elif re.match(EDT_CREATE, name, I) and not (res and res[0]):   # в проекте EDT объект создаётся только так
            return k, str(inp.get('name') or inp.get('objectName') or inp.get('fqn') or name.split('__')[-1])
        elif name == 'Write' and res and not res[0] and re.search(r'created', res[1], I):
            n = norm(inp.get('file_path'))
            if n and not n.endswith('.bsl') and not gs.exempt(n, {}) and not in_temp(n) and is_1c(n, gs):
                return k, n.split('/')[-1]
    return None


def design_notes(view, gs, root=''):
    """design-before-code и five-role-design-review: объект 1С создан, а в сессии до него не было проработки и консилиума."""
    got = created_object(view, gs, root)
    if not got:
        return []
    k, what = got
    before = view['calls'][:k]
    prior = ' '.join(t for at, t in view['texts'] if at <= k).lower()
    out = []
    if not any(n in ('AskUserQuestion', 'ExitPlanMode') for n, _, _ in before) and \
            not re.search(r'проработк|консилиум|план реализации|\b[тt]-\d', prior):
        out.append(('design-before-code', 'объект 1С создан (%s) без проработки в сессии: до него не было ни проработки по пунктам, '
                    'ни согласования окном вариантов' % what))
    roles = {str(i.get('subagent_type') or '') for n, i, _ in before if n in ('Agent', 'Task')} & ROLES
    flow = any(n == 'Workflow' and re.search(r'consilium|консилиум', json.dumps(i, ensure_ascii=False), I) for n, i, _ in before)
    if not (roles or flow or 'консилиум' in prior or sum(w in prior for w in ROLE_WORDS) >= 3):
        out.append(('five-role-design-review', 'объект 1С создан (%s) без консилиума пяти ролей: ни помощников-ролей, ни сценария '
                    'консилиума, ни разбора по ролям в ответах сессии' % what))
    return out


def test_run(name, inp, res):
    """Вызов — состоявшийся прогон теста, а не чтение, поиск или загрузка скилла yaxunit. Красный тест — тоже прогон, это и есть
    репро: у харнесса ядра судится вердикт, а не код выхода; «не выполнен» и падение без вердикта прогоном не считаются."""
    failed, said = bool(res and res[0]), res[1] if res else ''
    if name in ('Bash', 'PowerShell'):
        cmd = str(inp.get('command') or '')
        if runs_skill_script(cmd, HARNESS):
            return not re.search(VERDICT + r'\s*не выполнен', said, I) and (not failed or re.search(VERDICT, said, I) is not None)
        return not re.search(r'(^|\s)(--help|-h)(\s|$)', cmd) and any(re.match(TEST_CMD, s.strip(), I) for s in re.split(r'&&|\|\||[;|\n]', cmd))
    if name == 'Skill':
        return not failed and re.search(r'(^|:)tests$', str(inp.get('skill') or ''), I) is not None
    return not failed and re.match(TEST_TOOL, name, I) is not None


def bug_notes(view, root):
    """bug-diagnosis-loop: задача об ошибке без автоматического репро в сессии; метки зондов [DEBUG-…] в правленом модуле."""
    mods = [p for p, n in edited(view['calls'][view['turn']:], root) if n.endswith('.bsl') and work_file(n, root)]
    if not mods:
        return []
    out = []
    if re.search(BUG, view['prompt'], I) and not any(test_run(*call) for call in view['calls']):
        out.append(('bug-diagnosis-loop', 'задача об ошибке, а модуль .bsl правится без автоматического репро и теста в сессии '
                    '(YAXUnit, execute_code на тестовой базе, харнесс)'))
    for p in dict.fromkeys(mods):
        f = fs_path(p) if os.path.isabs(fs_path(p)) else os.path.join(root, fs_path(p))
        try:
            with open(f, encoding='utf-8-sig', errors='replace') as h:
                if '[DEBUG-' in h.read():
                    out.append(('bug-diagnosis-loop', 'в %s остались метки зондов [DEBUG-…] — их вычищают до конца хода' % os.path.basename(f)))
        except OSError:
            pass
    return out


def journal_notes(view, gs, tops):
    """journal-placement: правки конфигурации в её git-репозитории записаны в журнал проекта, а не в журнал её репозитория."""
    eds = [n for _, n in edited(view['calls'][view['turn']:], os.environ.get('CLAUDE_PROJECT_DIR') or '')]
    out = []
    for t in tops():
        cfg = [n for n in eds if under(n, t) and is_1c(n, gs)]
        own = [n for n in eds if re.search(r'/docs-project/(worklog|changelog)\.md$', n) and not under(n, t)]
        if cfg and own and not [n for n in eds if under(n, t) and re.search(r'/docs/(worklog|changelog)\.md$', n)]:
            out.append(('journal-placement', 'правки конфигурации (%d файлов, репозиторий %s) записаны в журнал проекта %s, а не в '
                        'docs/worklog.md и docs/changelog.md её репозитория' % (len(cfg), t.replace('\\', '/').rstrip('/').split('/')[-1],
                                                                              own[0].split('/')[-1])))
    return out


def copy_notes(view, root, tops):
    """config-git-forks-and-merges: копирование файлов между рабочими деревьями одного репозитория вместо merge/cherry-pick."""
    cmds = [str(i.get('command') or '') for n, i, _ in view['calls'][view['turn']:]
            if n in ('Bash', 'PowerShell') and re.search(COPY, str(i.get('command') or ''), I)]
    if not cmds:
        return []
    for t in dict.fromkeys(list(tops()) + [root]):
        wts = sorted({norm(ln[9:]) for ln in git('-C', t, 'worktree', 'list', '--porcelain').splitlines() if ln.startswith('worktree ')},
                     key=len, reverse=True)
        if len(wts) < 2:
            continue
        for cmd in cmds:
            hit = set()
            for tok in re.findall(r'[a-z]:/[^\s"\'|;&<>]+|/[a-z]/[^\s"\'|;&<>]+', norm(cmd)):
                tok = norm(fs_path(tok))
                w = next((w for w in wts if tok == w or tok.startswith(w + '/')), None)
                if w:
                    hit.add(w)
            if len(hit) >= 2:
                return [('config-git-forks-and-merges', 'файлы скопированы между рабочими деревьями одного репозитория (%s) — перенос '
                         'между ветками делается merge или cherry-pick' % ', '.join(sorted(h.split('/')[-1] for h in hit)))]
    return []


def ask_notes(view, gs, root):
    """ask-before-changing: общие модули, роли или корень конфигурации правились без поручения и без окна вариантов в ходе."""
    now = view['calls'][view['turn']:]
    shared = [n for _, n in edited(now, root) if work_file(n, root) and not gs.exempt(n, {}) and re.search(SHARED, n)]
    prompt = view['prompt']
    # вставленный текст ошибки — тоже поручение «исправь» (повтор 482 ходов настоящих журналов, 17.10.2026), вопрос об ошибке — нет
    if not shared or not prompt or any(n in ('AskUserQuestion', 'ExitPlanMode') for n, _, _ in now) or \
            request_in(prompt) or re.search(BUG, statements(prompt), I):
        return []
    return [('ask-before-changing', '%s, а в ходе без согласования правились общие объекты (%s)' % (
        'запрос владельца — вопрос, а не поручение' if prompt.rstrip().endswith('?') else 'в запросе владельца нет поручения',
        ', '.join(dict.fromkeys('/'.join(n.split('/')[-2:]) for n in shared[:3]))))]


def token_notes(view):
    """token-economy-and-local-tools п.2: файл прочитан сплошняком. Повторное чтение не судится (решение владельца 18.10.2026):
    неизменённый файл второй раз Claude Code не отдаёт сам («Wasted call»), а файл, изменённый скриптом, перечитать законно."""
    out = []
    for n, i, r in view['calls'][view['turn']:]:
        if n == 'Read' and r and not r[0] and len(r[1]) > BIG_READ:
            out.append(('token-economy-and-local-tools', 'файл %s прочитан сплошняком (%d КБ текста) — читать точечно: offset/limit, '
                        'Grep, code-index' % (norm(i.get('file_path')).split('/')[-1], len(r[1]) // 1024)))
    return out[:3]


def probe_notes(view, text):
    """probe-tool-capabilities: флаг программы в ответе, которого сессия не видела ни в прогоне, ни в выводе --help, ни в файлах."""
    snippets = re.findall(r'`([^`\n]+)`', re.sub(r'```.*?```', ' ', text, flags=re.S))
    for body in re.findall(r'```(?:bash|sh|shell|powershell|pwsh|cmd|console)\s*\n(.*?)```', text, flags=re.S | I):
        snippets += [ln for ln in body.split('\n') if ln.strip()]
    claims = []
    for s in snippets:
        toks = [t.strip('"\'') for t in s.split()]
        if not toks:
            continue
        prog = re.split(r'[\\/]', toks[0])[-1].lower()
        if prog in RUNNERS and len(toks) > 1:
            prog = re.split(r'[\\/]', toks[1])[-1].lower()
        if not re.match(r'^[a-z0-9][\w.-]*$', prog) or prog in SHELL:
            continue
        claims += [(prog, fl) for fl in re.findall(r'(?<!\S)(--[a-z][a-z0-9-]+)', s) if (prog, fl) not in claims]
    if not claims:
        return []
    seen = [(norm(json.dumps(i, ensure_ascii=False)), r[1] if r and not r[0] else '') for _, i, r in view['calls']]
    bad = ['%s %s' % (p, f) for p, f in claims if not any((p in inp and f in inp and res) or f in res for inp, res in seen)]
    return [('probe-tool-capabilities', 'в ответе флаги, не подтверждённые в сессии ни прогоном, ни --help, ни исходником: %s'
             % ', '.join(bad[:4]))] if bad else []


def module_flags(body):
    def on(tag):
        return bool(re.search(r'<%s>\s*true\s*</%s>' % (tag, tag), body, I))
    reuse = re.search(r'<returnValuesReuse>\s*(\w+)\s*<', body, I)
    return {'global': on('global'), 'client': on('clientManagedApplication'), 'server': on('server'), 'servercall': on('serverCall'),
            'privileged': on('privileged'), 'cached': bool(reuse) and reuse.group(1).lower() != 'dontuse'}


def module_name_issues(name, f):
    """Постфикс имени общего модуля против его флагов — std469 пп. 2.1–2.4, 3.2.1–3.2.3 (сверено по v8std 17.10.2026; п.3.1
    об общих словах — рекомендация, её нарушает и БСП: СтроковыеФункции, — не проверяется)."""
    def ends(s, *sfx):
        return next((x for x in sfx if s.endswith(x)), '')
    out, base = [], name
    base = base[:len(base) - len(ends(base, 'Переопределяемый', 'Overridable', 'Локализация', 'Localization'))]
    if f['global']:
        g = ends(base, 'Глобальный', 'Global')
        if not g:
            out.append('глобальный модуль — постфикс «Глобальный» (п.3.2.1, АПК:83)')
        elif ends(base[:-len(g)], 'Клиент', 'Client'):
            out.append('у глобального модуля постфикс «Клиент» не ставится (п.3.2.1, АПК:363)')
        return out
    c = ends(base, 'ПовтИсп', 'Cached')
    if f['cached'] and not c:
        out.append('повторное использование значений — постфикс «ПовтИсп» / «КлиентПовтИсп» (п.3.2.3, АПК:85)')
    base = base[:len(base) - len(c)] if f['cached'] else base
    p = ends(base, 'ПолныеПрава', 'FullAccess')
    if f['privileged'] and not p:
        out.append('привилегированный модуль — постфикс «ПолныеПрава» (п.3.2.2, АПК:84)')
    base = base[:len(base) - len(p)] if f['privileged'] else base
    if f['servercall']:
        if not ends(base, 'ВызовСервера', 'ServerCall'):
            out.append('модуль с вызовом сервера — постфикс «ВызовСервера» (п.2.2, АПК:90)')
    elif f['client'] and f['server']:
        if not ends(base, 'КлиентСервер', 'ClientServer'):
            out.append('клиент-серверный модуль — постфикс «КлиентСервер» (п.2.4, АПК:1245)')
    elif f['client']:
        if not ends(base, 'Клиент', 'Client'):
            out.append('клиентский модуль — постфикс «Клиент» (п.2.3, АПК:80)')
    elif f['server'] and ends(base, 'Клиент', 'Client', 'КлиентСервер', 'ClientServer', 'ВызовСервера', 'ServerCall'):
        out.append('серверный модуль без вызова сервера — постфикс противоречит флагам (п.2.1)')
    return out


def naming_notes(view, root, tops):
    """naming-and-module-design: новый общий модуль, чей постфикс расходится с его флагами по std469."""
    now = view['calls'][view['turn']:]
    files = [fs_path(i.get('file_path')) for n, i, _ in now if n == 'Write' and CM_FILE.search(norm(i.get('file_path')))]
    if any((n in ('Bash', 'PowerShell') and runs_skill_script(str(i.get('command') or ''), 'meta-compile|meta-edit'))
           or re.match(r'^mcp__.*edt.*__\w*(create|add|new)\w*$', n, I) for n, i, _ in now):
        for t in dict.fromkeys(list(tops()) + [root]):
            for ln in git('-c', 'core.quotepath=false', '-C', t, 'status', '--porcelain', '--untracked-files=all').splitlines():
                rel = ln[3:].strip().strip('"')
                if ln[:2].strip() in ('??', 'A', 'AM') and CM_FILE.search('/' + norm(rel)):
                    files.append(os.path.join(t, rel))
    out = []
    for f in dict.fromkeys(files):
        try:
            with open(f, encoding='utf-8-sig', errors='replace') as h:
                body = h.read()
        except OSError:
            continue
        m = re.search(r'<name>\s*([^<\s]+)\s*</name>', body, I)
        issues = module_name_issues(m.group(1), module_flags(body)) if m else []
        if issues:
            out.append(('naming-and-module-design', 'общий модуль %s: %s (std469)' % (m.group(1), '; '.join(issues))))
    return out


def review_notes(view, text):
    """two-axis-code-review в основном ходе: просили ревью кода 1С, а в ответах хода нет двух вердиктов."""
    prompt = view['prompt']
    if not re.search(r'(ревью|review|проверь\s+(?:этот\s+|мой\s+)?(?:модуль|код))', prompt, I):
        return []
    reads = [i for p, i, _ in view['calls'][view['turn']:] if p == 'Read' and norm(i.get('file_path')).endswith('.bsl')]
    if not (reads or re.search(r'модул|\bкод|\.bsl|процедур|функци|\bbsl\b', prompt, I)):
        return []
    body = '\n'.join(t for at, t in view['texts'] if at >= view['turn']) + '\n' + text
    if re.search(r'Стандарты\W{0,3}:', body) and re.search(r'Спека\W{0,3}:', body):
        return []
    return [('two-axis-code-review', 'просили ревью кода, а в ответах хода нет двух вердиктов «Стандарты:» и «Спека:»')]


def turn_rule_notes(root, view, text):
    """Нарушения правил ядра, видимые по журналу хода: [(правило, что найдено)]; сбой одного детектора не гасит остальные."""
    gs = guard_skills()
    cache = []

    def tops():
        if not cache:
            cache.append(config_tops(root))
        return cache[0]
    found = []
    for name, fn in (('chat_call', lambda: chat_call(text)), ('design_notes', lambda: design_notes(view, gs, root)),
                     ('bug_notes', lambda: bug_notes(view, root)), ('journal_notes', lambda: journal_notes(view, gs, tops)),
                     ('copy_notes', lambda: copy_notes(view, root, tops)), ('ask_notes', lambda: ask_notes(view, gs, root)),
                     ('token_notes', lambda: token_notes(view)), ('probe_notes', lambda: probe_notes(view, text)),
                     ('naming_notes', lambda: naming_notes(view, root, tops)), ('review_notes', lambda: review_notes(view, text))):
        try:
            found += fn()
        except Exception as e:   # контракт деградации: сломанный детектор называется, а не молчит (неотличимо от «нарушений нет»)
            found.append(('DEGRADED', 'stop-guard: детектор %s не отработал — внутренняя ошибка: %s' % (name, str(e)[:160])))
    return found


def git(*args):
    r = subprocess.run(['git'] + list(args), capture_output=True)
    return r.stdout.decode('utf-8', 'replace') if r.returncode == 0 else ''


def main():
    root = os.environ.get('CLAUDE_PROJECT_DIR')
    if not root:
        return
    try:
        data = json.loads(sys.stdin.buffer.read().decode('utf-8', 'replace').lstrip('﻿') or '{}') or {}
        data = data if isinstance(data, dict) else {}
    except (ValueError, AttributeError, OSError):
        data = {}
    sid = str(data.get('session_id') or '')
    try:
        observed = answer_notes(root, sid or 'nosession', data)
    except Exception as e:   # наблюдение за ответом упало целиком — пометка DEGRADED, а не тишина
        log_answer(root, sid or 'nosession', 'DEGRADED', 'stop-guard: наблюдение за ответом: %s' % str(e)[:200])
        observed = ['DEGRADED — наблюдение за ответом не отработало (внутренняя ошибка: %s)' % str(e)[:160]]
    try:
        gate = stop_gate(root, sid or 'nosession', data)
    except Exception as e:   # сломанный гейт не должен запирать ход, но и молчать не должен
        gate = ('degraded', 'гейт конца хода: DEGRADED — внутренняя ошибка, проверка правок 1С пропущена: %s' % e)
    # классификатор C0 не загружен (подмена, сбой) — гейт строже, но это называется, а не молчит
    cp_note = ('DEGRADED — C0 выключен: change-profile.py не загружен (%s)' % _CP_ERR[0]) if _CP_ERR else ''
    if cp_note:
        log_answer(root, sid or 'nosession', 'DEGRADED', 'stop-guard: ' + cp_note)
    if gate and gate[0] == 'block':
        sys.stdout.buffer.write(json.dumps({'decision': 'block', 'reason': gate[1]}, ensure_ascii=False).encode('utf-8'))
        sys.stdout.flush()
        return
    if data.get('hook_event_name') == 'SubagentStop':
        # конец работы помощника: гейт и наблюдение за его итогом — прочие напоминания относятся к ходу целиком
        parts = ([gate[1]] if gate else []) + ([cp_note] if cp_note else [])
        parts += (['наблюдение за ответом (в блокирующем режиме помощник продолжил бы): ' + ' | '.join(observed)] if observed else [])
        if parts:
            sys.stdout.buffer.write(json.dumps({'systemMessage': 'stop-guard: ' + ' | '.join(parts)}, ensure_ascii=False).encode('utf-8'))
            sys.stdout.flush()
        return
    repos = [root]
    for k, v in os.environ.items():
        if k.upper().startswith('ONEC_PROJECT_SRC') and v and os.path.exists(v):
            top = git('-C', v, 'rev-parse', '--show-toplevel').strip()
            if top:
                repos.append(top.replace('/', '\\'))
    seen, uniq = set(), []
    for r in repos:
        key = r.rstrip('\\').lower()
        if key not in seen:
            seen.add(key)
            uniq.append(r.rstrip('\\'))
    bsl = []
    for r in uniq:
        # quotepath=false: кириллический путь без восьмеричных экранов; "?: путь с пробелом git берёт в кавычки
        out = git('-c', 'core.quotepath=false', '-C', r, 'status', '--porcelain', '--untracked-files=all')
        bsl += [line for line in out.splitlines() if re.search(r'\.bsl"?(\s|$)', line, re.I)]
    notes = []

    try:
        gs_path = os.path.join(root, 'logs', 'gate-state.json')
        if os.path.isfile(gs_path):
            with open(gs_path, encoding='utf-8-sig') as f:
                st = json.load(f)
            armed = []
            # только своя сессия: чужие и «nosession» (прогоны без session_id, например самотест) не висят вечно
            for k, v in st.items():
                if (sid and k != sid) or k == 'nosession':
                    continue
                for a in (v if isinstance(v, list) else [v]):
                    if a and a not in armed:
                        armed.append(a)
            if armed:
                show = armed if len(armed) <= 3 else armed[:3] + ['… и ещё %d' % (len(armed) - 3)]
                plug = os.environ.get('CLAUDE_PLUGIN_ROOT')
                # в проекте скрипт лежит в кэше плагина: без --root след писался бы туда, а взвод в logs/ проекта не снимался
                ev = ('python "%s" --root "%s"' % (os.path.join(plug, 'tools', 'checks', 'gate-evidence.py'), root)) if plug \
                    else 'tools\\checks\\gate-evidence.py'
                notes.append('гейт качества ВЗВЕДЁН по %d правкам .bsl (%s): в блокирующем режиме завершение хода было бы ОТКЛОНЕНО. '
                             'Сейчас режим наблюдения — запиши след прогона `%s --checked ... --not-verified ...`, '
                             'он же снимет взвод' % (len(armed), ', '.join(show), ev))
    except (OSError, ValueError, AttributeError):
        pass

    if bsl:
        notes.append('в рабочем дереве %d незакоммиченных .bsl. Прогнан ли полный сет чекеров (full-checker-set-before-done)? '
                     'Закрытая веха записана в worklog (work-journals-and-commits)?' % len(bsl))

    # Сверка защитных скриптов с реестром сумм (по тексту с LF — иначе core.autocrlf дал бы ложную тревогу).
    hooks_dir = HERE  # реестр и тела хуков — рядом с этим файлом (плагин и мастер ядра, ADR-0004)
    reg_path = os.path.join(hooks_dir, 'contours.sha256')
    if os.path.isfile(reg_path) and os.path.isdir(hooks_dir):
        reg = read_registry()
        drift = []
        for name in sorted(os.listdir(hooks_dir)):
            p = os.path.join(hooks_dir, name)
            if name == 'contours.sha256' or not os.path.isfile(p) or name.startswith('__'):
                continue
            h = contour_sha(p)
            if name not in reg:
                drift.append('%s (нет в реестре)' % name)
            elif reg[name] != h:
                drift.append(name)
        if drift:
            notes.append('тело контура разошлось с реестром отпечатков В ЭТОЙ СЕССИИ: %s. Если правка хука осознанная — '
                         'перегенерируй tools\\indexes\\gen-contour-registry.py в той же правке; если нет — барьер мог быть ослаблен.' % ', '.join(drift))

    if gate:
        notes.append(gate[1])
    if cp_note:
        notes.append(cp_note)
    if observed:
        notes.append('наблюдение за ответом (журнал logs/answer-check.jsonl; в блокирующем режиме ход был бы продлён): ' + '; '.join(observed))
    if not notes:
        return
    msg = 'stop-guard (7-й контур, совещательный): ' + ' | '.join(notes)
    sys.stdout.buffer.write(json.dumps({'systemMessage': msg}, ensure_ascii=False).encode('utf-8'))
    sys.stdout.flush()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:   # сбой вне гейта и детекторов (git, сверка отпечатков) — видимая пометка, ход не запирается
        sys.stdout.buffer.write(json.dumps({'systemMessage': 'stop-guard: DEGRADED — внутренняя ошибка, напоминания конца хода не '
                                            'выданы: %s' % e}, ensure_ascii=False).encode('utf-8'))
        sys.stdout.flush()
    sys.exit(0)
