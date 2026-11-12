"""PostToolUse: автопроверка модуля 1С (.bsl) сразу после правки.

Перенос validate-bsl.ps1 на Python (ADR-0002) один к одному; сверяется проверками contour-tests (раздел 1).
  1. Анализатор bsl-analyzer: ошибка или предупреждение (error, warning — с 05.11.2026; note — нет) в СТРОКАХ ПРАВКИ блокирует
     (с 17.10.2026; прежние замечания модуля вне правки — подсказка модели без блокировки «свой код исправь в этой же задаче»,
     то же для смешения алфавитов; запись через EDT целиком — как раньше, весь файл) (код 2 + текст в stderr —
     модель видит причину и исправляет). Семейства, которые на одиночном файле дают ложные срабатывания
     (метаданные не резолвятся), не блокируют — их список ниже, расширять только с замером.
  2. Языковой профиль: смешение кириллицы и латиницы в одном имени блокирует; латинские сокращения из имён
     самой платформы (ЧтениеXML, HTTPСоединение) нарушением не считаются.
  0. Правка .bsl отмечается в logs/gate-state.json проекта: в конце хода напомнят записать прогон проверок
     (режим наблюдения — ничего не блокирует). Служебные зоны и временная папка вне проекта не взводят — тот же
     отбор, что у гейта конца хода (с 4.6.1: песочница помощника в %TEMP% держала напоминание всю сессию).
     Правка модуля вне исходников проекта (все ONEC_PROJECT_SRC*, configSrc и src расширений реестра баз) — подсказка модели
     (с 4.7.0, edit-project-sources-directly).
  3. Бюджет комментариев (с 17.10.2026, comment-budget): нарушения аудита tools/1c/bsl-comment-audit.py — только
     в строках, записанных этой правкой (куски structuredPatch, иначе место new_string; новый файл — целиком), —
     блокирующий фидбек. Маркеры вставок в типовые (// <--, // -->, //++, //--) нарушением не считаются;
     запись модуля через EDT целиком (write_module_source) не проверяется — своё от поставщика там не отличить.
  4. Часовой анализатора (с 10.11.2026, по мотивам 1c-quality-gate): анализатор не нашёл в модуле ничего — тем же вызовом
     прогоняется образец с заведомой ошибкой; молчит и на нём — DEGRADED «вердикт недостоверен» владельцу и модели вместо
     зелёного. Успех помнится в logs/analyzer-sentinel.json на сессию, лаунчер и версию движка.
  5. Гигиена файла (с 10.11.2026, по мотивам 1c-quality-gate) — блокирует: в строках правки управляющие символы и невидимые
     знаки (нулевой ширины, смены направления), тире «–», «—», «−» в коде вне строк и комментариев; строка правки с другим
     переводом строки, чем у файла; снятый BOM у модуля, у которого он был в HEAD. Замер 10.11.2026: 4991 модуль двух рабочих
     конфигураций целиком — 12 находок, все U+200B в комментариях машинного перевода; тире и смешанных переводов — ноль.
Где анализатор: в плагине — ${CLAUDE_PLUGIN_DATA}/bin/bsl-analyzer/bsl-analyzer.exe (ставит install-tools.py);
без плагина (в мастере ядра) — та же стандартная папка данных плагина в профиле пользователя, затем прежний tools/bsl-analyzer.exe.
Не видит: .bsl, записанный через Bash или скрипты скиллов, — его видит гейт конца хода через shell-arm.py (с 10.11.2026).
Любая внутренняя ошибка — пропуск с пометкой DEGRADED (молчаливый пропуск неотличим от «замечаний нет»).
"""
import datetime
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

FALSE_FAMILIES = r'^(QueryToMissingMetadata|UnresolvedMethodCall|MissingCommonModule|UnresolvedField|InvalidCharacterInFile)$'
PLATFORM_ABBR = {'HTTP', 'HTTPS', 'XML', 'XDTO', 'JSON', 'XSD', 'XSLT', 'COM', 'WS', 'WSDL', 'SOAP', 'FTP', 'FTPS', 'HTML', 'XHTML',
                 'URI', 'URL', 'UUID', 'GUID', 'OLE', 'ZIP', 'SMTP', 'POP3', 'IMAP', 'TCP', 'UDP', 'SSL', 'TLS', 'OPENSSL',
                 'CSV', 'DBF', 'BOM', 'ODATA', 'SQL', 'DOM', 'SAX', 'CDATA', 'DTD', 'ASCII', 'UTF8', 'ANSI', 'BASE64', 'MD5',
                 'SHA1', 'SHA256', 'PDF', 'EDT',
                 # обход контекста платформы bsl-context 8.3.27 и 8.5.1, 30.10.2026: типы, глобальные имена, члены типов
                 'ACTIVEDOCUMENT', 'ACTIVEX', 'BLUETOOTH', 'BMP', 'BYTEORDERMARK', 'CDATADOM', 'DOMXPATH', 'FASTINFOSET', 'HEX', 'IP',
                 'LINUX', 'MAC', 'MACOS', 'MIME', 'MMS', 'NDEF', 'NFC', 'NSS', 'OEM', 'OPENID', 'OPENIDCONNECT', 'QR', 'S3', 'SMS',
                 'SSLIMAP', 'SSLPOP3', 'SSLSMTP', 'WEB', 'WEBSOCKET', 'WIFI', 'WINDOWS', 'XBASE', 'XPATH', 'XPATHXS', 'XS', 'XSL'}
# Имена платформы, чей латинский кусок — обычное слово или короткая метка: целым именем, иначе пройдёт ИмяSource.
# Буква «c» в двух именах ОформлениеВо…клицательныйЗнак — латинская, так они записаны в самой платформе.
PLATFORM_NAMES = {x.upper() for x in (
    'AppletТеги', 'AreaТеги', 'EmbedТеги', 'FrameТеги', 'IframeТеги', 'JavaScriptТеги', 'LinkТеги', 'NoembedТеги', 'ObjectТеги', 'SourceТеги',
    'StyleТеги', 'ImportАтрибуты', 'W3IncludeАтрибуты', 'ПоведениеКлавишиEnter', 'ПриНажатииEnter', 'ТипПоведенияКлавишиEnter',
    'ИгнорироватьЗначенияNULL', 'PushУведомления', 'ПсевдоцилиндрическаяПроекцияПутнинаP2', 'ПсевдоцилиндрическаяПроекцияПутнинаP5',
    'ОформлениеВоcклицательныйЗнак', 'ОформлениеЗнакВоcклицательныйЗнак', 'КаноническийXML1_1', 'КаноническийXML1_1СКомментариями')}
CYR = 'Ѐ-ӿ'
HERE = os.path.dirname(os.path.abspath(__file__))
INSERT_MARKER = r'^\s*//\s*(<--|-->|\+\+|--)'


def err(text):
    sys.stderr.buffer.write((text + '\n').encode('utf-8'))
    sys.stderr.flush()


SYSTEM, CONTEXT = [], []   # сообщения копятся и выводятся одним JSON в конце: два объекта подряд Claude Code не разберёт


def degraded(text):
    """Пропуск без проверки — видимо (systemMessage при коде 0), а не только в отладочный журнал."""
    SYSTEM.append(text)


def emit(code):
    """При коде 2 до модели доходит только stderr — туда же и накопленное; при коде 0 — один JSON."""
    if code == 2:
        for text in SYSTEM + CONTEXT:
            err(text)
        return
    out = {}
    if SYSTEM:
        out['systemMessage'] = ' | '.join(SYSTEM)
    if CONTEXT:
        out['hookSpecificOutput'] = {'hookEventName': 'PostToolUse', 'additionalContext': ' | '.join(CONTEXT)}
    if out:
        sys.stdout.buffer.write(json.dumps(out, ensure_ascii=False).encode('utf-8'))
        sys.stdout.flush()


def plugin_data():
    """Папка данных плагина: из переменной плагина, иначе стандартная в профиле пользователя (мастер ядра работает без плагина)."""
    return os.environ.get('CLAUDE_PLUGIN_DATA') or os.path.join(os.path.expanduser('~'), '.claude', 'plugins', 'data', 'ones-core-ones-core')


def analyzer_path(root):
    p = os.path.join(plugin_data(), 'bin', 'bsl-analyzer', 'bsl-analyzer.exe')
    if os.path.isfile(p):
        return p
    return os.path.join(root or '', 'tools', 'bsl-analyzer.exe')


def source_roots(root):
    """Исходники проекта: все ONEC_PROJECT_SRC*, configSrc и src расширений реестра баз. Корень проекта сюда не входит."""
    roots = [v.strip().strip('"') for k, v in sorted(os.environ.items()) if k.upper().startswith('ONEC_PROJECT_SRC') and v.strip()]
    try:
        with open(os.path.join(root or '', '.v8-project.json'), encoding='utf-8-sig') as f:
            dbs = (json.load(f) or {}).get('databases') or []
        for db in [dbs] if isinstance(dbs, dict) else dbs:
            for p in [db.get('configSrc')] + [e.get('src') for e in db.get('extensions') or [] if isinstance(e, dict)]:
                if isinstance(p, str) and p:
                    roots.append(p if os.path.isabs(p) else os.path.join(root, p))
    except (OSError, ValueError, AttributeError, TypeError):
        pass
    return roots


def resolve_module_path(j, root):
    """edt-mcp write_module_source даёт modulePath относительно src проекта: ищем свежую запись (до 120 с)."""
    mp = (j.get('tool_input') or {}).get('modulePath')
    if not mp:
        return None
    best, best_time = None, None
    seen = set()
    for r in source_roots(root):
        if r in seen:
            continue
        seen.add(r)
        cand = os.path.join(r, mp.replace('/', os.sep))
        if os.path.isfile(cand):
            tm = os.path.getmtime(cand)
            if best_time is None or tm > best_time:
                best, best_time = cand, tm
    if best and (datetime.datetime.now().timestamp() - best_time) < 120:
        return best
    return None


def not_working_config(f, root, j):
    """Отбор гейта конца хода (stop-guard): служебная зона или временная папка вне проекта — не рабочая конфигурация."""
    n = f.replace('\\', '/').strip().strip('"').lower()
    r = root.replace('\\', '/').lower().rstrip('/')
    inside = bool(r) and n.startswith(r + '/')
    tmp = {tempfile.gettempdir(), os.path.realpath(tempfile.gettempdir())}
    in_tmp = any(n.startswith(t.replace('\\', '/').lower().rstrip('/') + '/') for t in tmp) or '/appdata/local/temp/' in n
    if in_tmp and not inside:
        return True
    try:
        spec = importlib.util.spec_from_file_location('guard_skills', os.path.join(HERE, 'guard-skills.py'))
        gs = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gs)
        return bool(gs.exempt(n, j))
    except Exception:
        return False


def outside_src(f, root, j):
    """edit-project-sources-directly (с 4.7.0): модуль правится вне исходников проекта (source_roots) — подсказка, не отказ.
    Без ONEC_PROJECT_SRC проверка молчит, как и раньше."""
    src = (os.environ.get('ONEC_PROJECT_SRC') or '').strip().strip('"').rstrip('\\/')
    if not src or not_working_config(f, root, j):
        return
    n = f.replace('\\', '/').lower()
    if any(n.startswith(s.replace('\\', '/').lower().rstrip('/') + '/') for s in source_roots(root)):
        return
    CONTEXT.append('правка %s — вне исходников проекта (ONEC_PROJECT_SRC=%s): по правилу edit-project-sources-directly код и '
                   'метаданные правятся прямо в исходниках проекта. Намеренно (вторая выгрузка, внешняя обработка, копия для '
                   'сравнения) — скажи об этом в ответе; нет — перенеси правку в исходники' % (f, src))


def arm_gate(j, root, f):
    """Отметить правку в logs/gate-state.json (режим наблюдения; любая ошибка — молча)."""
    try:
        if not root or not_working_config(f, root, j):
            return
        sid = str(j.get('session_id') or '') or 'nosession'
        # CC_GATE_STATE_DIR — для самопроверки: тестовые правки не взводят гейт в настоящем logs/ (ревизия Р-31)
        gs_dir = os.environ.get('CC_GATE_STATE_DIR') or os.path.join(root, 'logs')
        os.makedirs(gs_dir, exist_ok=True)
        gs_path = os.path.join(gs_dir, 'gate-state.json')
        state = {}
        if os.path.isfile(gs_path):
            try:
                with open(gs_path, encoding='utf-8-sig') as fh:
                    loaded = json.load(fh)
                state = {k: (v if isinstance(v, list) else [v]) for k, v in loaded.items()}
            except (OSError, ValueError, AttributeError):
                state = {}
        armed = list(state.get(sid, []))
        if f.lower().startswith(root.lower()):
            rel = f[len(root):].lstrip('\\/')
        elif os.path.isabs(f):
            rel = f.replace('\\', '/')   # вне проекта — полный путь: по одному имени файла не понять, что взвело
        else:
            rel = f
        if rel not in armed:
            armed.append(rel)
        state[sid] = [a for a in armed if a]
        with open(gs_path, 'w', encoding='utf-8', newline='\n') as fh:
            json.dump(state, fh, ensure_ascii=False, indent=2)
    except Exception:
        pass


def run_analyzer(exe, f):
    """Ошибки и предупреждения (error, warning; note — нет) в правленном файле без семейств ложных срабатываний; None — отчёта нет.
    Предупреждения — с 05.11.2026, решение владельца: «ошибки и предупреждения нужно обязательно исправлять, нельзя пропускать»."""
    d = os.path.dirname(f)
    tmp = os.path.join(tempfile.gettempdir(), 'bslhook_%d' % os.getpid())
    shutil.rmtree(tmp, ignore_errors=True)
    try:
        # --changed-files — путь ОТНОСИТЕЛЬНО -s: с абсолютным анализатор молча находит 0 замечаний
        subprocess.run([exe, 'analyze', '--incremental', '-s', d, '--changed-files', os.path.basename(f),
                        '-r', 'sarif', '-o', tmp, '-q'], capture_output=True, timeout=55)
        rep = os.path.join(tmp, 'bsl-analyzer.sarif')
        if not os.path.isfile(rep):
            return None
        try:
            with open(rep, encoding='utf-8-sig') as fh:
                s = json.load(fh)
        except (OSError, ValueError):
            return None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    leaf = re.escape(os.path.basename(f))
    results = ((s.get('runs') or [{}])[0].get('results')) or []
    errs = []
    for r in results:
        try:
            uri = r['locations'][0]['physicalLocation']['artifactLocation']['uri']
        except (KeyError, IndexError, TypeError):
            uri = ''
        if r.get('level') in ('error', 'warning') and not re.search(FALSE_FAMILIES, str(r.get('ruleId') or ''), re.I) and re.search(leaf, uri, re.I):
            errs.append(r)
    return errs


# Часовой анализатора (с 10.11.2026, по мотивам 1c-quality-gate): «замечаний нет» верно, только если анализатор находит заведомую
# ошибку. Образец гоняется тем же вызовом run_analyzer во временной папке (настройки проекта на него не влияют); успех помнится
# на сессию, лаунчер и версию движка, провал не помнится — следующая правка проверит снова.
SENTINEL_TEXT = 'Процедура ЧасовойАнализатора() Экспорт\n\tЕсли Тогда\nКонецПроцедуры\n'
SENTINEL_TTL = 6 * 3600


def engine_version():
    """Версия движка, которую тянет лаунчер (кэш %USERPROFILE%/.bsl-analyzer/bin/.app-version); пусто — не известна."""
    try:
        with open(os.path.join(os.path.expanduser('~'), '.bsl-analyzer', 'bin', '.app-version'), encoding='utf-8') as fh:
            return fh.read().strip()[:40]
    except OSError:
        return ''


def analyzer_alive(exe, state_dir, sid):
    """True — анализатор нашёл ошибку образца (или нашёл её раньше в этой сессии), False — молчит."""
    try:
        st = os.stat(exe)
        key = '%s|%d|%d|%s' % (sid, st.st_size, int(st.st_mtime), engine_version())
    except OSError:
        key = ''
    path = os.path.join(state_dir, 'analyzer-sentinel.json')
    try:
        with open(path, encoding='utf-8-sig') as fh:
            saved = json.load(fh)
        if key and saved.get('key') == key and saved.get('ok') and time.time() - float(saved.get('ts') or 0) < SENTINEL_TTL:
            return True
    except (OSError, ValueError, AttributeError, TypeError):
        pass
    d = tempfile.mkdtemp(prefix='bslsentinel_')
    try:
        sample = os.path.join(d, 'Module.bsl')
        with open(sample, 'wb') as fh:
            fh.write(b'\xef\xbb\xbf' + SENTINEL_TEXT.encode('utf-8'))
        ok = bool(run_analyzer(exe, sample))
    finally:
        shutil.rmtree(d, ignore_errors=True)
    if ok and key:
        try:
            os.makedirs(state_dir, exist_ok=True)
            with open(path, 'w', encoding='utf-8', newline='\n') as fh:
                json.dump({'key': key, 'ok': True, 'ts': time.time()}, fh, ensure_ascii=False)
        except OSError:
            pass
    return ok


def error_line(e):
    try:
        return int(e['locations'][0]['physicalLocation']['region']['startLine'])
    except (KeyError, IndexError, TypeError, ValueError):
        return 0


class _Nothing(frozenset):
    """Правка ничего не записала: кусок правки есть, строк «+» в нём нет (только удаление)."""


NOTHING = _Nothing()


def written_lines(j, f):
    """Номера строк, записанных правкой: None — файл новый (весь свой), NOTHING — правка только удаляла,
    пустое множество — определить нельзя."""
    resp = j.get('tool_response')
    if isinstance(resp, dict):
        if resp.get('type') == 'create':
            return None
        patch = resp.get('structuredPatch')
        if isinstance(patch, list) and patch:
            added = set()
            for hunk in patch:
                n = int((hunk or {}).get('newStart') or 1)
                for line in (hunk or {}).get('lines') or []:
                    if line.startswith('+'):
                        added.add(n)
                        n += 1
                    elif not line.startswith(('-', '\\')):
                        n += 1
            return added or NOTHING   # Issue Only1S/1c-ai-core#4: без «+» правка ничего не записала, а не «определить нельзя»
    new = str((j.get('tool_input') or {}).get('new_string') or '')
    if new.strip():
        with open(f, encoding='utf-8-sig') as fh:
            text = fh.read()
        at = text.find(new)
        if at >= 0:
            first = text.count('\n', 0, at) + 1
            return set(range(first, first + new.count('\n') + 1))
    return set()


def replaced_text(j):
    """Текст, который правка заменила: снятые строки кусков правки и old_string."""
    resp = j.get('tool_response') if isinstance(j.get('tool_response'), dict) else {}
    gone = [ln[1:] for hunk in resp.get('structuredPatch') or [] for ln in (hunk or {}).get('lines') or [] if ln.startswith('-')]
    return '\n'.join(gone + [str((j.get('tool_input') or {}).get('old_string') or '')])


def comment_budget(j, f):
    """Нарушения бюджета комментариев в строках, записанных правкой; описание метода — своё, если правка задела шапку."""
    mine = written_lines(j, f)
    if mine is not None and not mine:
        return []
    tool_path = os.path.join(HERE, '..', 'tools', '1c', 'bsl-comment-audit.py')
    if not os.path.isfile(tool_path):
        degraded('validate-bsl: DEGRADED — нет tools/1c/bsl-comment-audit.py, бюджет комментариев НЕ проверен')
        return []
    spec = importlib.util.spec_from_file_location('bsl_comment_audit', tool_path)
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    with open(f, encoding='utf-8-sig') as fh:
        lines = fh.read().split('\n')
    found = []
    before = replaced_text(j)
    for number, kind, detail in tool.audit(f):
        if kind == 'комментарий в теле метода':
            # detail — сам комментарий: маркер бывает и в конце строки с кодом, а комментарий, стоявший в конце строки до правки,
            # записала не эта правка: иначе правка кода в чужой строке получала бы отказ за чужое пояснение
            if re.match(INSERT_MARKER, detail) or (detail in before and not lines[number - 1].lstrip().startswith('//')):
                continue
            span = {number}
        else:
            span = set(range(tool.header_range(lines, number - 1) + 1, number))
        if mine is None or span & mine:
            found.append('строка %d: %s (%s)' % (number, kind, detail))
    return found


SUPPRESS = re.compile(r'//\s*(@skip-check\b[^\r\n]*|@skip-warning\b[^\r\n]*|BSLLS(?::\w+)?-off\b|(?:ACC|CAC|APK|АПК):\s*\d+[^\r\n]*)', re.I)


def new_suppressions(j, f):
    """Директивы подавления диагностики, записанные этой правкой: [(строка, директива)]; перенос прежней не считается."""
    mine = written_lines(j, f)
    if mine is not None and not mine:
        return []
    with open(f, encoding='utf-8-sig') as fh:
        lines = fh.read().split('\n')
    before = replaced_text(j)
    found = []
    for number, line in enumerate(lines, 1):
        if mine is not None and number not in mine:
            continue
        mt = SUPPRESS.search(line)
        if mt and mt.group(1).strip() not in before:
            found.append((number, mt.group(1).strip()))
    return found


# Гигиена файла (с 10.11.2026, по мотивам 1c-quality-gate): управляющие символы и невидимые знаки направления, тире вместо
# минуса в коде вне строк и комментариев — в строках правки; строка правки с другим переводом строки, чем у файла; снятый BOM.
CONTROL = re.compile('[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\u200b-\u200f\u202a-\u202e\u2066-\u2069\ufeff]')
DASHES = re.compile('[\u2013\u2014\u2212]')


def blank_strings_and_comments(src):
    """Строковые литералы (с продолжением «|») и комментарии — пробелами; переводы строк внутри сохраняются."""
    return re.sub(r'"(?:[^"]|"")*"|//[^\r\n]*', lambda x: re.sub(r'[^\r\n]', ' ', x.group(0)), src)


def head_had_bom(f):
    """У версии файла в HEAD его git-репозитория был BOM; None — файла в HEAD нет или git недоступен."""
    try:
        r = subprocess.run(['git', '--no-optional-locks', '-C', os.path.dirname(f), 'cat-file', 'blob',
                            'HEAD:./' + os.path.basename(f)], capture_output=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.startswith(b'\xef\xbb\xbf') if r.returncode == 0 else None


def hygiene(f, mine):
    """Нарушения гигиены: [(строка, что)]; mine — строки правки (None — файл новый, весь свой)."""
    with open(f, 'rb') as fh:
        raw = fh.read()
    had_bom = raw.startswith(b'\xef\xbb\xbf')
    text = raw.decode('utf-8-sig', 'replace')
    lines = text.split('\n')
    found = []

    def mine_line(n):
        return mine is not NOTHING and (mine is None or not mine or n in mine)
    for n, line in enumerate(lines, 1):
        if not mine_line(n):
            continue
        mt = CONTROL.search(line.rstrip('\r'))
        if mt:
            found.append((n, 'управляющий или невидимый символ U+%04X' % ord(mt.group(0))))
    code = blank_strings_and_comments(text).split('\n')
    for n, line in enumerate(code, 1):
        if mine_line(n) and DASHES.search(line):
            found.append((n, 'тире «%s» в коде вместо минуса «-»' % DASHES.search(line).group(0)))
    ends = ['crlf' if ln.endswith('\r') else 'lf' for ln in lines[:-1]]
    if 'crlf' in ends and 'lf' in ends:
        major = 'crlf' if ends.count('crlf') >= ends.count('lf') else 'lf'
        odd = [k + 1 for k, e in enumerate(ends) if e != major and mine_line(k + 1)]
        if odd:
            other, usual = ('CRLF', 'LF') if major == 'lf' else ('LF', 'CRLF')
            found.append((odd[0], 'перевод строки %s в файле на %s (строк: %d) — смешанные переводы строк' % (other, usual, len(odd))))
    if not had_bom and mine is not NOTHING and head_had_bom(f):
        found.append((1, 'у модуля в HEAD был BOM, сейчас его нет — верни BOM (UTF-8 с BOM, как в выгрузке)'))
    return found


def mixed_identifiers(f):
    with open(f, 'rb') as fh:
        src = fh.read().decode('utf-8-sig', 'replace')
    # строки и комментарии — одним проходом; переводы строк внутри сохраняются, чтобы номер строки находки был верным
    src = re.sub(r'"(?:[^"]|"")*"|//[^\r\n]*', lambda x: '\n' * x.group(0).count('\n') or ' ', src)
    found = []
    for mt in re.finditer(r'\b[0-9A-Za-z_' + CYR + r']*(?:[A-Za-z][' + CYR + r']|[' + CYR + r'][A-Za-z])[0-9A-Za-z_' + CYR + r']*', src):
        if mt.group(0).upper() in PLATFORM_NAMES:
            continue
        for seg in re.findall(r'[A-Za-z][A-Za-z0-9]*', mt.group(0)):
            if seg.upper() not in PLATFORM_ABBR:
                found.append((src.count('\n', 0, mt.start()) + 1, mt.group(0)))
                break
    return found


def main():
    raw = sys.stdin.buffer.read().decode('utf-8', 'replace').lstrip('\ufeff')
    try:
        j = json.loads(raw)
    except ValueError:
        degraded('validate-bsl: DEGRADED — вход не разобран как JSON, правка пропущена без проверки')
        return 0
    root = os.environ.get('CLAUDE_PROJECT_DIR', '')
    f = (j.get('tool_input') or {}).get('file_path') or (j.get('tool_response') or {}).get('filePath')
    if not f:
        f = resolve_module_path(j, root)
    if not f or not re.search(r'\.bsl$', f, re.I) or not os.path.isfile(f):
        return 0

    arm_gate(j, root, f)
    outside_src(f, root, j)
    # Блокируют только находки в строках, записанных правкой (с 17.10.2026): прежние ошибки старого модуля — подсказка.
    # Новый файл — весь свой; если строки правки определить нельзя (запись через EDT целиком) — как раньше, весь файл;
    # правка только удаляла строки — своих строк нет, прежние находки — подсказка.
    mine = written_lines(j, f)

    def ours(line):
        return mine is not NOTHING and (mine is None or not mine or line in mine)

    # Подавление вместо исправления (решение владельца 05.11.2026, по мотивам config-protection ECC — docs/sources/ecc-review.md):
    # не блокирует — подавление бывает законным, но решает его владелец; BSLLS:…-off к тому же ломает bsl-analyzer на кириллице
    sup = new_suppressions(j, f)
    if sup:
        CONTEXT.append('подавление диагностики в строках этой правки %s: %s — исправь код, а не прячь замечание. Подавить '
                       'можно только после «да» владельца (спроси окном вариантов, назови диагностику и почему она ложная); '
                       'BSLLS:…-off к тому же обрывает bsl-analyzer на кириллице — ложный зелёный (bug-diagnosis-loop Ф5)'
                       % (os.path.basename(f), '; '.join('строка %d: %s' % (n, d) for n, d in sup[:3])))

    dirty = hygiene(f, mine)
    if dirty:
        err('гигиена файла: %d нарушений в %s — %s. Исправь до продолжения: тире в коде — на минус «-», управляющие и '
            'невидимые символы убрать, переводы строк — как у файла, BOM — вернуть (по мотивам 1c-quality-gate).'
            % (len(dirty), f, '; '.join('строка %d: %s' % x for x in dirty[:5]) + (' и ещё %d' % (len(dirty) - 5) if len(dirty) > 5 else '')))
        return 2

    exe = analyzer_path(root)
    if os.path.isfile(exe):
        errs = run_analyzer(exe, f)
        if errs is None:
            degraded('validate-bsl: DEGRADED — bsl-analyzer не дал отчёта по %s, синтаксис НЕ проверен (сбой или таймаут анализатора)' % f)
        elif not errs:
            state_dir = os.environ.get('CC_GATE_STATE_DIR') or (os.path.join(root, 'logs') if root else tempfile.gettempdir())
            if not analyzer_alive(exe, state_dir, str(j.get('session_id') or '') or 'nosession'):
                text = ('validate-bsl: DEGRADED — часовой: bsl-analyzer не нашёл заведомую ошибку в образце, анализатор не работает; '
                        'его «замечаний нет» по %s недостоверно' % os.path.basename(f))
                degraded(text)
                CONTEXT.append(text + ' — не считай модуль проверенным анализатором: проверь validate_module и скажи владельцу, '
                                      'что bsl-analyzer молчит (версия: bsl-analyzer --version)')
        new = [e for e in errs or [] if ours(error_line(e))]
        old = [e for e in errs or [] if e not in new]
        if old:
            CONTEXT.append('bsl-analyzer: в %s %d прежних ошибок и предупреждений вне строк этой правки (%s) — не блокирует, но '
                           'пропускать нельзя: свой код исправь отдельным шагом этой же задачи; объект поставщика на поддержке — '
                           'назови владельцу списком (full-checker-set-before-done)'
                           % (os.path.basename(f), len(old), ', '.join(dict.fromkeys(str(e.get('ruleId')) for e in old))))
        if new:
            rules = ', '.join(dict.fromkeys('%s (%s)' % (e.get('ruleId'), e.get('level')) for e in new))
            err('bsl-analyzer: %d error(s)/warning(s) in written lines of %s - rules: %s - fix the code before continuing, '
                'warnings too (work-through-tools p.5)' % (len(new), f, rules))
            return 2
    else:
        err('validate-bsl: bsl-analyzer.exe not found - contour 1 (bsl-analyzer) is DEAD, fail-open. '
            'Install it: python tools/setup/install-tools.py --dest <plugin data folder> (see docs/tools/installed-tools-and-servers.md).')

    mix = mixed_identifiers(f)
    mix_new = [name for line, name in mix if ours(line)]
    if len(mix_new) < len(mix):
        CONTEXT.append('в %s %d прежних имён со смешением алфавитов вне строк этой правки — не блокирует' % (os.path.basename(f), len(mix) - len(mix_new)))
    if mix_new:
        err('mixed-language identifiers (%d) in written lines of %s - language-profile violation, use ONE language per project profile. Samples: %s'
            % (len(mix_new), f, ', '.join(mix_new[:3])))
        return 2

    found = comment_budget(j, f)
    if found:
        err('comment-budget: %d нарушений бюджета комментариев в записанных строках %s — %s. Описание метода — одна строка, '
            'без абзацев прозы в шапке и без пояснений в теле; «почему так» — в журнал работы (docs-project/changelog.md), '
            'не в код (docs/code/comment-budget.md). Директивы анализаторов и маркеры вставок в типовые не считаются.'
            % (len(found), f, '; '.join(found[:5]) + (' и ещё %d' % (len(found) - 5) if len(found) > 5 else '')))
        return 2
    return 0


if __name__ == '__main__':
    try:
        code = main()
    except Exception as e:
        degraded('validate-bsl: DEGRADED — внутренняя ошибка, правка пропущена без проверки: %s' % e)
        code = 0
    emit(code)
    sys.exit(code)
