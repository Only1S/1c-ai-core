"""PreToolUse: файл 1С правится скиллом, а не руками; плюс самозащита настроек и конфигов проверок.

Перенос guard-skills.ps1 на Python (ADR-0002) один к одному; сверяется проверками contour-tests (раздел 9).
Что делает:
  - ручная правка (Write/Edit) файла 1С — форма (управляемая, с 30.10.2026 и обычная: form.frm, Ext/Form.bin), объект
    метаданных, права роли, СКД, макет, командный интерфейс, пакет XDTO — отклоняется с подсказкой, каким скиллом это делается
    (для EDT — через edt-mcp);
  - самозащита настроек: правка .claude/settings(.local).json, которая включает disableAllHooks, убирает
    подключение защиты или сокращает permissions.deny, — отклоняется;
  - самозащита конфигов проверок: понижение уровня проверки в .v8-project.json (в том числе stopGate) и сокращение списка чужих
    имён tools/checks/health-check.names.txt — отклоняются;
  - только владелец (замер 30.10.2026): файлы хуков git и .git/config, настройки ssh-mcp (ворота подтверждения), новый или
    перенаправленный сервер в .mcp.json проекта, одобрение серверов в настройках (enabledMcpjsonServers, enableAllProjectMcpServers);
  - барьер источника (с 17.10.2026): вызов внешнего скилла не из белого списка (allowed-skill-sources; с 30.10.2026 скилл без
    приставки — только встроенный из BUILTIN_SKILLS или лежащий в проекте или плагине) и обращение
    к MCP-серверу 1С, не объявленному в .mcp.json проекта или плагина ones-core (use-own-mcp-servers-only), — отклоняются;
    с волны 1 — и любой другой сервер, в том числе подключение claude.ai (mcp__<uuid>__*), вне .mcp.json, плагина ones-core,
    серверов приложения APP_SERVERS и списка разрешённых ONEC_MCP_ALLOW; расширить этот список (и ONEC_PLUGINS_ALLOW)
    правкой настроек нельзя — только владельцу;
  - окно вариантов (с 4.8.0): вопрос без варианта «(Рекомендуется)» первым — отклоняется (questions-as-options п.2,
    requirements-by-interview п.4); вопрос владельцу о факте конфигурации — подсказка модели, без отказа.
Судится результат правки (файл после замены), а не её текст: обычное обслуживание проходит.

Служебные зоны (.claude/, docs/, docs-project/, tools/, scratchpad/, node_modules/, .git/) не проверяются:
там примеры и документация, а не живая конфигурация. Правка файла 1С через Bash здесь не видна — осознанная граница; запись в файлы
доверия барьеров (настройки, реестр, .mcp.json, хуки git) через оболочку отклоняет guard-destructive.
Отказ: код 0 + JSON permissionDecision=deny. Внутренняя ошибка — пропуск с пометкой DEGRADED в stderr.
"""
import json
import os
import re
import sys
import time


def deny(reason):
    payload = {'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'permissionDecision': 'deny',
        'permissionDecisionReason': reason,
    }}
    sys.stdout.buffer.write(json.dumps(payload, ensure_ascii=False).encode('utf-8'))
    sys.stdout.flush()
    sys.exit(0)


BAD_JSON = object()


def parse_obj(text):
    """Объект JSON из текста файла: пустой текст — {}, не JSON или не объект — BAD_JSON."""
    if not (text or '').strip():
        return {}
    try:
        o = json.loads(text.lstrip('﻿'))
    except ValueError:
        return BAD_JSON
    return o if isinstance(o, dict) else BAD_JSON


def deny_set(o):
    d = (o.get('permissions') or {}).get('deny') if isinstance(o.get('permissions'), dict) else None
    return {str(x) for x in d} if isinstance(d, list) else set()


def plugin_off(o_cur, o_new):
    """Ключи ones-core@*, которые правка выключает: значение не true или ключ пропал при прежнем true."""
    p_cur = o_cur.get('enabledPlugins') if isinstance(o_cur.get('enabledPlugins'), dict) else {}
    p_new = o_new.get('enabledPlugins') if isinstance(o_new.get('enabledPlugins'), dict) else {}
    off = [k for k, v in p_new.items() if k.lower().startswith('ones-core@') and v is not True]
    gone = [k for k, v in p_cur.items() if k.lower().startswith('ones-core@') and v is True and k not in p_new]
    return off + gone


def default_mode(o):
    perms = o.get('permissions')
    return str(perms.get('defaultMode') or '') if isinstance(perms, dict) else ''


PD_RANK = {'none': 0, 'masked': 1}   # остальное (raw, нет отметки, неизвестное) — 2: данные к модели не идут
CONN_KEYS = ('type', 'path', 'server', 'ref', 'dbServer', 'dbName', 'connection', 'url')


def registry_dbs_of(o):
    dbs = o.get('databases') or []
    dbs = [dbs] if isinstance(dbs, dict) else dbs
    return {str(d.get('id')): d for d in dbs if isinstance(d, dict)} if isinstance(dbs, list) else {}


def pd_rank(db):
    pd = db.get('pd') if db else None
    return PD_RANK.get(pd.strip().lower(), 2) if isinstance(pd, str) else 2


def edit_result(data, path):
    """(текст до правки, текст после) — после = None, если результат восстановить нельзя."""
    cur = ''
    if os.path.isfile(path):
        with open(path, 'rb') as f:
            cur = f.read().decode('utf-8-sig', 'replace')
    ti = data.get('tool_input') or {}
    after = None
    tool = data.get('tool_name')
    if tool == 'Write':
        after = str(ti.get('content') or '')
    elif tool == 'Edit':
        old, new = str(ti.get('old_string') or ''), str(ti.get('new_string') or '')
        if old and old in cur:
            after = cur.replace(old, new) if ti.get('replace_all') else cur.replace(old, new, 1)
    return cur, after


def checker_levels(text):
    """Уровни проверок из .v8-project.json: ключ -> уровень; None, если JSON не разбирается."""
    try:
        o = json.loads(text.lstrip('\ufeff'))
    except ValueError:
        return None
    if not isinstance(o, dict):
        return None
    levels = {}
    top = str(o.get('skillSuggester') or '').lower() or 'on'   # отсутствующий = 'on' (умолчание вендора)
    levels['skillSuggester'] = top
    levels['stopGate'] = str(o.get('stopGate') or '').lower() or 'block'   # гейт конца хода; отсутствующий = 'block'
    dbs = o.get('databases') or []
    if isinstance(dbs, dict):
        dbs = [dbs]
    for db in dbs:
        if not isinstance(db, dict):
            continue
        db_id = str(db.get('id') or '')
        if not db_id:
            continue
        e = str(db.get('editingAllowedCheck') or '')
        if e:
            levels["база '%s': editingAllowedCheck" % db_id] = e.lower()
        s = str(db.get('skillSuggester') or '')
        levels["база '%s': skillSuggester" % db_id] = s.lower() if s else top
    return levels


def count_names(text):
    return sum(1 for line in re.split(r'\r?\n', text) if line.strip() and not line.strip().startswith('#'))


EDT = ('в EDT-проекте — через edt-mcp (модель, не диск: docs/tools/edt-mcp-pitfalls.md, инвариант no-bypass); '
       'скиллы этого семейства работают только с XML-выгрузкой Конфигуратора')
META_TYPES = ('catalogs|documents|documentjournals|documentnumerators|enums|reports|dataprocessors|informationregisters|'
              'accumulationregisters|accountingregisters|calculationregisters|chartsofcharacteristictypes|chartsofaccounts|'
              'chartsofcalculationtypes|businessprocesses|tasks|exchangeplans|commonmodules|roles|subsystems|constants|'
              'sequences|filtercriteria|settingsstorages|commonforms|commontemplates|commoncommands|commandgroups|definedtypes|'
              'eventsubscriptions|scheduledjobs|webservices|httpservices|wsreferences|xdtopackages|sessionparameters|'
              'functionaloptions|functionaloptionsparameters|externaldatasources|styles|languages|commonattributes|commonpictures')
# Виды объектов выгрузки, которые meta-compile не создаёт (проба 30.10.2026: Unsupported type либо вид неизвестен скриптам meta-*)
META_TYPES_NO_COMPILE = 'styleitems|integrationservices|bots|palettecolors|websocketclients|interfaces'

# Карта «файл 1С -> чем его положено править»; порядок важен (первое совпадение).
RULES = [
    (lambda f, p: f == 'configuration.mdo', 'корневая конфигурация EDT — ' + EDT),
    (lambda f, p: f == 'configuration.xml', 'корневая конфигурация (XML-выгрузка) — скиллы cf-edit / cf-info, затем cf-validate'),
    (lambda f, p: f == 'form.form', 'управляемая форма EDT — ' + EDT + ' (метаданные, скриншот формы); правка .form на диске допустима только байтобезопасно и как крайняя мера, см. docs/tools/edt-mcp-pitfalls.md'),
    (lambda f, p: f == 'form.xml', 'управляемая форма (XML-выгрузка) — скиллы form-edit / form-compile / form-info, затем form-validate'),
    # обычные формы (30.10.2026): form.frm — текст формы обычного приложения, Form.bin — её бинарный контейнер в выгрузке
    (lambda f, p: f == 'form.frm', 'обычная форма (form.frm) — скилл form-ordinary: decode в JSON, правка операциями edit, encode '
     'и validate, затем загрузка в тестовую базу и снимок (forms-skills-and-visual-check); руками счётчики и ссылки формы ломаются'),
    (lambda f, p: f == 'form.bin' and re.search(r'/ext/form\.bin$', p) is not None,
     'обычная форма (Form.bin выгрузки Конфигуратора) — бинарный контейнер, руками не правится: форма — скилл form-ordinary '
     '(правка операциями edit), модуль формы прочитать — скилл form-bin-module (только чтение)'),
    (lambda f, p: f == 'rights.rights', 'права роли EDT — ' + EDT),
    (lambda f, p: f == 'rights.xml', 'права роли (XML-выгрузка) — скиллы role-edit (точечно в существующей роли) / role-compile (новая роль) / role-info, затем role-validate'),
    (lambda f, p: f.startswith('commandinterface.') and not f.endswith('.xml'), 'командный интерфейс EDT — ' + EDT),
    (lambda f, p: f == 'commandinterface.xml', 'командный интерфейс (XML-выгрузка) — скилл interface-edit, затем interface-validate (subsystem-edit меняет только свойства подсистемы, не состав интерфейса)'),
    (lambda f, p: f.endswith('.dcs'), 'схема компоновки данных EDT — ' + EDT),
    (lambda f, p: f == 'datacompositionschema.xml', 'схема компоновки данных (XML-выгрузка) — скиллы skd-edit / skd-compile / skd-info, затем skd-validate'),
    (lambda f, p: f.endswith('.mxl'), 'макет табличного документа EDT — ' + EDT + '; ручная правка портит файл'),
    (lambda f, p: f == 'template.xml' and re.search(r'/ext/template\.xml$', p) is not None,
     'макет (XML-выгрузка): схема компоновки — skd-edit / skd-compile / skd-info + skd-validate, табличный документ — mxl-compile / mxl-decompile / mxl-info + mxl-validate (тип макета — TemplateType в XML макета-владельца)'),
    (lambda f, p: f == 'package.bin' and re.search(r'/ext/package\.bin$', p) is not None,
     'пакет XDTO (XML-выгрузка) — скиллы xdto-edit / xdto-compile / xdto-info, затем xdto-validate'),
    (lambda f, p: f.endswith('.xdto'), 'пакет XDTO EDT — ' + EDT),
    (lambda f, p: f.endswith('.mdo'), 'объект метаданных — в EDT-проекте через edt-mcp (модель, не диск: docs/tools/edt-mcp-pitfalls.md, инвариант no-bypass), в XML-выгрузке — скиллы meta-edit / meta-compile, затем meta-validate. Дубли идентификаторов — отчёт uuid-validate, точечная правка uuid= в .mdo — только названным исключением (use-skills-not-manual-edits п.6)'),
    (lambda f, p: re.search(r'/subsystems/[^/]+\.xml$', p) is not None,
     'подсистема (XML-выгрузка) — скиллы subsystem-edit / subsystem-compile / subsystem-info, затем subsystem-validate'),
    (lambda f, p: re.search(r'/(' + META_TYPES + r')/[^/]+\.xml$', p) is not None,
     'объект метаданных в XML-выгрузке Конфигуратора — скиллы meta-edit / meta-compile / meta-info, затем meta-validate (для ролей role-*, для СКД skd-*, для XDTO xdto-*)'),
    (lambda f, p: re.search(r'/(' + META_TYPES_NO_COMPILE + r')/[^/]+\.xml$', p) is not None,
     'объект метаданных в XML-выгрузке Конфигуратора: сначала meta-info и meta-edit, если они знают этот вид; meta-compile такие '
     'объекты не создаёт, поэтому ручная правка здесь — названным исключением (п.6), затем meta-validate'),
]
CONTOURS = ['guard-destructive', 'guard-skills', 'support-guard', 'validate-bsl', 'stop-guard', 'enrich-code-facts', 'subagent-gate',
            'scan-inbound', 'health-check', 'prompt-gate', 'postcompact-note', 'answer-feedback', 'lint-project-docs',
            'failure-streak', 'repeat-guard', 'shell-arm']
RANK = {'on': 2, 'error': 2, 'block': 2, 'warn': 1, 'off': 0}
EXEMPT = {'.claude', 'docs', 'docs-project', 'tools', 'node_modules', '.git'}


def exempt(norm, data):
    """Служебная зона — по ПЕРВОЙ папке пути от корня проекта (подстрока «/tools/» в выгрузке — не зона: Catalogs/Tools)."""
    wt = re.search(r'/\.claude/worktrees/[^/]+/(.*)$', norm)
    if wt:
        rel = wt.group(1)
    else:
        root = (os.environ.get('CLAUDE_PROJECT_DIR') or str(data.get('cwd') or '')).replace('\\', '/').lower().rstrip('/')
        if not root:  # корень неизвестен (запуск не из Claude Code): прежнее правило — зона в любом месте пути
            return any('/%s/' % z in norm for z in EXEMPT) or '/scratchpad/' in norm
        if not norm.startswith(root + '/'):
            # вне проекта: только служебные места Claude Code и плагина
            home = os.path.expanduser('~').replace('\\', '/').lower().rstrip('/')
            plug = (os.environ.get('CLAUDE_PLUGIN_ROOT') or '').replace('\\', '/').lower().rstrip('/')
            return norm.startswith(home + '/.claude/') or bool(plug and norm.startswith(plug + '/')) or \
                '/scratchpad/' in norm or '/node_modules/' in norm
        rel = norm[len(root) + 1:]
    return rel.split('/', 1)[0] in EXEMPT or '/node_modules/' in '/' + rel


# \u0411\u0435\u043b\u044b\u0439 \u0441\u043f\u0438\u0441\u043e\u043a \u0432\u043d\u0435\u0448\u043d\u0438\u0445 \u0441\u043a\u0438\u043b\u043b\u043e\u0432 \u2014 \u0442\u043e\u0442 \u0436\u0435, \u0447\u0442\u043e \u0432 \u0442\u0430\u0431\u043b\u0438\u0446\u0435 docs/tools/allowed-skill-sources.md \u043f.2 (\u0441\u0432\u0435\u0440\u044f\u0435\u0442 contour-tests \u00a79g).
SKILL_WHITELIST = {'anthropic-skills:docx', 'anthropic-skills:xlsx', 'anthropic-skills:pptx', 'anthropic-skills:pdf',
                   'engineering:architecture', 'anthropic-skills:built-in-browser', 'anthropic-skills:chrome-browser'}
# \u0412\u0441\u0442\u0440\u043e\u0435\u043d\u043d\u044b\u0435 \u0441\u043a\u0438\u043b\u043b\u044b \u0441\u0430\u043c\u043e\u0439 \u0441\u0440\u0435\u0434\u044b Claude Code \u0438 \u043f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u044f (\u0431\u0435\u0437 \u043f\u0440\u0438\u0441\u0442\u0430\u0432\u043a\u0438 \u043f\u043b\u0430\u0433\u0438\u043d\u0430) \u2014 \u0440\u0430\u0437\u0440\u0435\u0448\u0435\u043d\u044b \u044f\u0432\u043d\u043e (\u0440\u0435\u0448\u0435\u043d\u0438\u0435 \u0432\u043b\u0430\u0434\u0435\u043b\u044c\u0446\u0430 30.10.2026,
# allowed-skill-sources \u043f.2\u0430); \u0441\u043e\u0441\u0442\u0430\u0432 \u0441\u0432\u0435\u0440\u0435\u043d \u0441\u043e \u0441\u043f\u0438\u0441\u043a\u043e\u043c \u0441\u043a\u0438\u043b\u043b\u043e\u0432 \u0441\u0435\u0441\u0441\u0438\u0438 30.10.2026. \u0420\u0435\u0432\u044c\u044e \u043a\u043e\u0434\u0430 1\u0421 \u2014 \u043f\u043e-\u043f\u0440\u0435\u0436\u043d\u0435\u043c\u0443 two-axis-code-review,
# \u0443\u043f\u0440\u043e\u0449\u0435\u043d\u0438\u0435 \u2014 simplify-codebase: \u0432\u0441\u0442\u0440\u043e\u0435\u043d\u043d\u044b\u0435 code-review/simplify \u0438\u0445 \u043d\u0435 \u0437\u0430\u043c\u0435\u043d\u044f\u044e\u0442.
BUILTIN_SKILLS = {'code-review', 'security-review', 'simplify', 'init', 'loop', 'schedule', 'claude-api', 'update-config',
                  'keybindings-help', 'fewer-permission-prompts', 'run', 'plugin-authoring', 'workflow-authoring', 'dataviz',
                  'artifact-design', 'artifact-diagramming', 'artifact-capabilities'}
UUID = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'


def local_skill(name, cwd=''):
    """\u0421\u043a\u0438\u043b\u043b \u0438\u043b\u0438 \u043a\u043e\u043c\u0430\u043d\u0434\u0430 \u0431\u0435\u0437 \u043f\u0440\u0438\u0441\u0442\u0430\u0432\u043a\u0438 \u043b\u0435\u0436\u0438\u0442 \u0432 \u043f\u0440\u043e\u0435\u043a\u0442\u0435 \u0438\u043b\u0438 \u043f\u043b\u0430\u0433\u0438\u043d\u0435: .claude/skills/<\u0438\u043c\u044f>/, .claude/commands/<\u0438\u043c\u044f>.md,
    .claude/workflows/<\u0438\u043c\u044f>.js \u043a\u043e\u0440\u043d\u044f \u043f\u0440\u043e\u0435\u043a\u0442\u0430 (\u0438 \u043a\u0430\u0442\u0430\u043b\u043e\u0433\u0430 \u0437\u0430\u043f\u0443\u0441\u043a\u0430), skills/ \u0438 commands/ \u043f\u043b\u0430\u0433\u0438\u043d\u0430. \u041a\u043e\u0440\u0435\u043d\u044c \u043d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u0435\u043d \u2014 None."""
    roots = [r for r in (os.environ.get('CLAUDE_PROJECT_DIR'), cwd) if r]
    plug = os.environ.get('CLAUDE_PLUGIN_ROOT') or ''
    if not roots and not plug:
        return None
    if not re.fullmatch(r'[\w.-]+', name):
        return False
    places = [os.path.join(r, '.claude', sub) for r in roots for sub in ('skills', 'commands', 'workflows')]
    places += [os.path.join(plug, sub) for sub in ('skills', 'commands')] if plug else []
    return any(os.path.isdir(os.path.join(p, name)) or os.path.isfile(os.path.join(p, name + '.md')) or
               os.path.isfile(os.path.join(p, name + '.js')) for p in places)


def check_skill(ti, cwd=''):
    """\u041b\u043e\u043a\u0430\u043b\u044c\u043d\u044b\u0439 \u0441\u043a\u0438\u043b\u043b \u2014 \u0431\u0435\u0437 \u043f\u0440\u0438\u0441\u0442\u0430\u0432\u043a\u0438 (\u0432 \u043f\u0440\u043e\u0435\u043a\u0442\u0435 \u0438\u043b\u0438 \u043f\u043b\u0430\u0433\u0438\u043d\u0435), \u0441 \u043f\u0440\u0438\u0441\u0442\u0430\u0432\u043a\u043e\u0439 ones-core \u0438\u043b\u0438 \u043a\u0430\u0442\u0430\u043b\u043e\u0436\u043d\u043e\u0439 (apps/web:deploy);
    \u0432\u0441\u0442\u0440\u043e\u0435\u043d\u043d\u044b\u0439 \u0441\u043a\u0438\u043b\u043b Claude Code \u2014 \u0438\u0437 BUILTIN_SKILLS; \u0432\u043d\u0435\u0448\u043d\u0438\u0439 \u2014 \u0442\u043e\u043b\u044c\u043a\u043e \u0438\u0437 \u0431\u0435\u043b\u043e\u0433\u043e \u0441\u043f\u0438\u0441\u043a\u0430."""
    name = str(ti.get('skill') or ti.get('command') or '').strip().lstrip('/')
    if not name:
        return
    if ':' not in name:
        if name.lower() in BUILTIN_SKILLS or local_skill(name, cwd) is not False:
            return
        deny("allowed-skill-sources: \u0441\u043a\u0438\u043b\u043b '%s' \u0431\u0435\u0437 \u043f\u0440\u0438\u0441\u0442\u0430\u0432\u043a\u0438 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d \u043d\u0438 \u0441\u0440\u0435\u0434\u0438 \u0441\u043a\u0438\u043b\u043b\u043e\u0432 \u0438 \u043a\u043e\u043c\u0430\u043d\u0434 \u043f\u0440\u043e\u0435\u043a\u0442\u0430 \u0438 \u043f\u043b\u0430\u0433\u0438\u043d\u0430 ones-core "
             "(.claude/skills, .claude/commands, .claude/workflows), \u043d\u0438 \u0441\u0440\u0435\u0434\u0438 \u0432\u0441\u0442\u0440\u043e\u0435\u043d\u043d\u044b\u0445 \u0441\u043a\u0438\u043b\u043b\u043e\u0432 Claude Code (\u043f.2\u0430) \u2014 \u0438\u0441\u0442\u043e\u0447\u043d\u0438\u043a "
             "\u043d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u0435\u043d. \u041e\u0441\u043d\u043e\u0432\u043d\u043e\u0439 \u043f\u0443\u0442\u044c \u2014 \u0441\u043a\u0438\u043b\u043b\u044b \u044f\u0434\u0440\u0430 (ones-core:* \u0432 \u043f\u0440\u043e\u0435\u043a\u0442\u0435). \u041d\u0443\u0436\u0435\u043d \u0440\u0430\u0437\u043e\u0432\u043e \u2014 \u0432\u043b\u0430\u0434\u0435\u043b\u0435\u0446 \u0432\u044b\u0437\u044b\u0432\u0430\u0435\u0442 \u0435\u0433\u043e \u0441\u0430\u043c \u043a\u043e\u043c\u0430\u043d\u0434\u043e\u0439 "
             "/%s (\u043f.4); \u0432\u0441\u0442\u0440\u043e\u0435\u043d\u043d\u044b\u0439 \u0441\u043a\u0438\u043b\u043b, \u043a\u043e\u0442\u043e\u0440\u043e\u0433\u043e \u043d\u0435\u0442 \u0432 \u0441\u043f\u0438\u0441\u043a\u0435, \u0432\u043d\u043e\u0441\u0438\u0442\u0441\u044f \u043f\u0440\u0430\u0432\u043a\u043e\u0439 \u043f\u0440\u0430\u0432\u0438\u043b\u0430 \u0438 guard-skills (\u043f.5)." % (name, name))
    prefix = name.split(':', 1)[0]
    if prefix == 'ones-core' or '/' in prefix or name.lower() in SKILL_WHITELIST:
        return
    deny("allowed-skill-sources: \u0432\u043d\u0435\u0448\u043d\u0438\u0439 \u0441\u043a\u0438\u043b\u043b '%s' \u043d\u0435 \u0432 \u0431\u0435\u043b\u043e\u043c \u0441\u043f\u0438\u0441\u043a\u0435 (\u043f.2). \u041e\u0441\u043d\u043e\u0432\u043d\u043e\u0439 \u043f\u0443\u0442\u044c \u2014 \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u044b\u0435 \u0441\u043a\u0438\u043b\u043b\u044b \u044f\u0434\u0440\u0430 "
         "(ones-core:* \u0432 \u043f\u0440\u043e\u0435\u043a\u0442\u0435, .claude/skills \u0432 \u043c\u0430\u0441\u0442\u0435\u0440\u0435). \u041d\u0443\u0436\u0435\u043d \u0440\u0430\u0437\u043e\u0432\u043e \u2014 \u0432\u043b\u0430\u0434\u0435\u043b\u0435\u0446 \u0432\u044b\u0437\u044b\u0432\u0430\u0435\u0442 \u0435\u0433\u043e \u0441\u0430\u043c \u043a\u043e\u043c\u0430\u043d\u0434\u043e\u0439 /%s (\u043f.4); "
         "\u043d\u0430 \u043f\u043e\u0441\u0442\u043e\u044f\u043d\u043a\u0443 \u2014 \u043f\u0440\u0430\u0432\u043a\u0430 \u0431\u0435\u043b\u043e\u0433\u043e \u0441\u043f\u0438\u0441\u043a\u0430 \u0432 docs/tools/allowed-skill-sources.md (\u043f.5) \u0438 \u0432 guard-skills." % (name, name))


def mcp_names(path):
    try:
        with open(path, encoding='utf-8-sig') as f:
            return {k.lower() for k in (json.load(f).get('mcpServers') or {})}
    except (OSError, ValueError, AttributeError):
        return set()


# \u0421\u0435\u0440\u0432\u0435\u0440\u044b \u0441\u0430\u043c\u043e\u0433\u043e \u043f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u044f, \u043a\u043e\u0442\u043e\u0440\u044b\u0435 \u043f\u0440\u0430\u0432\u0438\u043b\u0430 \u044f\u0434\u0440\u0430 \u0443\u0436\u0435 \u0440\u0435\u0433\u0443\u043b\u0438\u0440\u0443\u044e\u0442: \u0441\u0435\u0441\u0441\u0438\u0438 (\u0438\u0445 \u0437\u0430\u043f\u0443\u0441\u043a \u0441\u0442\u0435\u0440\u0435\u0436\u0451\u0442 subagent-gate) \u0438 \u0434\u0432\u0430 \u0431\u0440\u0430\u0443\u0437\u0435\u0440\u0430
# (\u0441\u0430\u043d\u043a\u0446\u0438\u043e\u043d\u0438\u0440\u043e\u0432\u0430\u043d\u043d\u044b\u0435 \u0441\u043a\u0438\u043b\u043b\u044b built-in-browser \u0438 chrome-browser; \u0443\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u0435 \u044d\u043a\u0440\u0430\u043d\u043e\u043c \u0441\u043d\u044f\u0442\u043e permissions.deny).
APP_SERVERS = {'claude_browser', 'claude-in-chrome', 'visualize', 'mcp-registry', 'scheduled-tasks'}
# терминал приложения — только чтение: запуск команды в нём шёл бы мимо барьера Bash (guard-destructive)
APP_READ_ONLY = {'terminal': ('read_terminal', 'list_terminal_tabs')}
APP_PREFIX = 'ccd_'   # серверы приложения Claude: сессии, панели, окно, настройки (запуск сессий стережёт subagent-gate)
ALLOW_VARS = ('ONEC_MCP_ALLOW', 'ONEC_PLUGINS_ALLOW')


def split_allow(v):
    return {x.strip().lower() for x in re.split(r'[,;\s]+', str(v or '')) if x.strip()}


def settings_env(text):
    """env \u0438\u0437 \u0442\u0435\u043a\u0441\u0442\u0430 \u043d\u0430\u0441\u0442\u0440\u043e\u0435\u043a Claude Code; \u043d\u0435 \u0440\u0430\u0437\u0431\u0438\u0440\u0430\u0435\u0442\u0441\u044f \u2014 {}."""
    try:
        o = json.loads((text or '').lstrip('\ufeff'))
    except ValueError:
        return {}
    e = o.get('env') if isinstance(o, dict) else None
    return e if isinstance(e, dict) else {}


def mcp_allowed(project):
    """\u0421\u043f\u0438\u0441\u043e\u043a \u0440\u0430\u0437\u0440\u0435\u0448\u0451\u043d\u043d\u044b\u0445 \u0441\u0435\u0440\u0432\u0435\u0440\u043e\u0432: \u043f\u0435\u0440\u0435\u043c\u0435\u043d\u043d\u0430\u044f ONEC_MCP_ALLOW \u0438 \u043e\u043d\u0430 \u0436\u0435 \u0432 env .claude/settings(.local).json \u043f\u0440\u043e\u0435\u043a\u0442\u0430."""
    out = split_allow(os.environ.get('ONEC_MCP_ALLOW'))
    for f in ('settings.json', 'settings.local.json'):
        try:
            with open(os.path.join(project, '.claude', f), encoding='utf-8-sig') as fh:
                out |= split_allow(settings_env(fh.read()).get('ONEC_MCP_ALLOW'))
        except OSError:
            pass
    return out


def allow_grown(cur, after):
    """\u0427\u0442\u043e \u043f\u0440\u0430\u0432\u043a\u0430 \u043d\u0430\u0441\u0442\u0440\u043e\u0435\u043a \u0434\u043e\u0431\u0430\u0432\u043b\u044f\u0435\u0442 \u0432 \u0441\u043f\u0438\u0441\u043a\u0438 \u0440\u0430\u0437\u0440\u0435\u0448\u0451\u043d\u043d\u044b\u0445 (ONEC_MCP_ALLOW, ONEC_PLUGINS_ALLOW)."""
    e_cur, e_new = settings_env(cur), settings_env(after)
    grown = [(k, sorted(split_allow(e_new.get(k)) - split_allow(e_cur.get(k)))) for k in ALLOW_VARS]
    return ['%s: %s' % (k, ', '.join(v)) for k, v in grown if v]


def check_mcp(tool):
    """\u0418\u0441\u0442\u043e\u0447\u043d\u0438\u043a MCP: \u0441\u0435\u0440\u0432\u0435\u0440 \u0438\u0437 .mcp.json \u043f\u0440\u043e\u0435\u043a\u0442\u0430 \u0438\u043b\u0438 \u043f\u043b\u0430\u0433\u0438\u043d\u0430 ones-core, \u0441\u0435\u0440\u0432\u0435\u0440 \u043f\u043b\u0430\u0433\u0438\u043d\u0430 ones-core \u0438\u043b\u0438 \u043f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u044f (APP_SERVERS),
    \u043b\u0438\u0431\u043e \u0438\u0437 \u0441\u043f\u0438\u0441\u043a\u0430 \u0440\u0430\u0437\u0440\u0435\u0448\u0451\u043d\u043d\u044b\u0445 ONEC_MCP_ALLOW; \u0438\u043d\u0430\u0447\u0435 \u2014 \u043e\u0442\u043a\u0430\u0437. \u041c\u043e\u0441\u0442 1\u0421 \u2014 \u0442\u043e\u043b\u044c\u043a\u043e \u0438\u0437 .mcp.json, \u0441\u043f\u0438\u0441\u043e\u043a \u0435\u0433\u043e \u043d\u0435 \u043e\u0442\u043a\u0440\u044b\u0432\u0430\u0435\u0442."""
    mm = re.match(r'^mcp__(.+?)__', tool)
    if not mm:
        return
    seg = mm.group(1).lower()
    if seg == 'ones-core':
        return   # инструмент, который регистрирует мод самого плагина ones-core ($.tool.register), — свой
    server, plugin = seg, ''
    if seg.startswith('plugin_'):
        plugin, _, server = seg[len('plugin_'):].partition('_')
        if plugin == 'ones-core':
            return
    claude_ai = re.fullmatch(UUID, seg) is not None   # \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u044f claude.ai: \u0438\u043c\u044f \u2014 \u0438\u0434\u0435\u043d\u0442\u0438\u0444\u0438\u043a\u0430\u0442\u043e\u0440, \u00ab1c\u00bb \u0432\u043d\u0443\u0442\u0440\u0438 \u043d\u0435\u0433\u043e \u2014 \u043d\u0435 1\u0421
    onec = not claude_ai and ('code-index' in server or
                              any(re.match(r'^(edt|1c|onec|bsl|v8|nkdk|yaxunit)', t) for t in re.split(r'[-_.]+', server)))
    project = os.environ.get('CLAUDE_PROJECT_DIR') or ''
    if not project:
        return
    # Серверы плагина ones-core приходят с приставкой plugin_ones-core_ (пропущены выше); одноимённый им сервер без
    # приставки объявлен вне проекта — чужой (аудит 30.10.2026: «1c-toolkit» из настроек пользователя шёл как свой).
    declared = set() if plugin else mcp_names(os.path.join(project, '.mcp.json'))
    if server in declared:
        return
    if onec:
        where = "\u043f\u043b\u0430\u0433\u0438\u043d\u0430 '%s'" % plugin if plugin else '\u0438\u0437 \u043d\u0430\u0441\u0442\u0440\u043e\u0435\u043a \u0432\u043d\u0435 \u043f\u0440\u043e\u0435\u043a\u0442\u0430'
        deny("use-own-mcp-servers-only: \u0441\u0435\u0440\u0432\u0435\u0440 1\u0421 '%s' (%s) \u043d\u0435 \u043e\u0431\u044a\u044f\u0432\u043b\u0435\u043d \u043d\u0438 \u0432 .mcp.json \u043f\u0440\u043e\u0435\u043a\u0442\u0430, \u043d\u0438 \u0432 .mcp.json \u043f\u043b\u0430\u0433\u0438\u043d\u0430 ones-core \u2014 "
             "\u0447\u0443\u0436\u043e\u0439 \u043c\u043e\u0441\u0442 \u043c\u043e\u0436\u0435\u0442 \u0432\u0435\u0441\u0442\u0438 \u0432 \u0434\u0440\u0443\u0433\u0443\u044e, \u0432 \u0442\u043e\u043c \u0447\u0438\u0441\u043b\u0435 \u0431\u043e\u0435\u0432\u0443\u044e, \u0431\u0430\u0437\u0443. \u041d\u0443\u0436\u043d\u043e\u0433\u043e \u043c\u043e\u0441\u0442\u0430 \u043d\u0435\u0442 \u2014 \u0441\u043e\u043e\u0431\u0449\u0438 \u0432\u043b\u0430\u0434\u0435\u043b\u044c\u0446\u0443 \u0438 \u043f\u043e\u043f\u0440\u043e\u0441\u0438 \u043f\u043e\u0434\u043d\u044f\u0442\u044c "
             "\u0441\u0432\u043e\u0439 (\u043f.3), \u043d\u0435 \u043f\u043e\u0434\u043c\u0435\u043d\u044f\u0439 \u0447\u0443\u0436\u0438\u043c." % (server, where))
    read_only = tool[len('mcp__%s__' % seg):].lower() in APP_READ_ONLY.get(seg, ())
    if seg in APP_SERVERS or seg.startswith(APP_PREFIX) or read_only or seg in mcp_allowed(project):
        return
    what = ("\u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u0435 claude.ai '%s'" % seg if claude_ai else
            "\u0441\u0435\u0440\u0432\u0435\u0440 '%s' \u043f\u043b\u0430\u0433\u0438\u043d\u0430 '%s'" % (server, plugin) if plugin else "\u0441\u0435\u0440\u0432\u0435\u0440 '%s'" % seg)
    deny("use-own-mcp-servers-only: %s (\u0438\u043d\u0441\u0442\u0440\u0443\u043c\u0435\u043d\u0442 %s) \u2014 \u043d\u0435\u0442 \u043d\u0438 \u0432 .mcp.json \u043f\u0440\u043e\u0435\u043a\u0442\u0430 \u0438\u043b\u0438 \u043f\u043b\u0430\u0433\u0438\u043d\u0430 ones-core, \u043d\u0438 \u0432 \u0441\u043f\u0438\u0441\u043a\u0435 "
         "\u0440\u0430\u0437\u0440\u0435\u0448\u0451\u043d\u043d\u044b\u0445: \u043f\u0440\u043e\u0435\u043a\u0442 \u0440\u0430\u0431\u043e\u0442\u0430\u0435\u0442 \u0442\u043e\u043b\u044c\u043a\u043e \u0441\u043e \u0441\u0432\u043e\u0438\u043c\u0438 \u0441\u0435\u0440\u0432\u0435\u0440\u0430\u043c\u0438, \u043f\u043e\u0441\u0442\u043e\u0440\u043e\u043d\u043d\u0435\u0435 \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u0435 \u0443\u043d\u043e\u0441\u0438\u0442 \u0434\u0430\u043d\u043d\u044b\u0435 \u043f\u0440\u043e\u0435\u043a\u0442\u0430 \u043d\u0430\u0440\u0443\u0436\u0443 \u0438 "
         "\u043f\u0440\u0438\u043d\u043e\u0441\u0438\u0442 \u0447\u0443\u0436\u0438\u0435 \u0438\u043d\u0441\u0442\u0440\u0443\u043a\u0446\u0438\u0438. \u041e\u0431\u043e\u0439\u0434\u0438\u0441\u044c \u0441\u0432\u043e\u0438\u043c\u0438 \u0441\u0435\u0440\u0432\u0435\u0440\u0430\u043c\u0438; \u0435\u0441\u043b\u0438 \u044d\u0442\u043e\u0442 \u043d\u0443\u0436\u0435\u043d \u2014 \u0441\u043a\u0430\u0436\u0438 \u0432\u043b\u0430\u0434\u0435\u043b\u044c\u0446\u0443, \u0437\u0430\u0447\u0435\u043c: \u0440\u0430\u0437\u0440\u0435\u0448\u0430\u0435\u0442 \u043e\u043d \u0441\u0430\u043c, "
         "\u0434\u043e\u0431\u0430\u0432\u0438\u0432 '%s' \u0432 ONEC_MCP_ALLOW (env \u0432 .claude/settings.json \u043f\u0440\u043e\u0435\u043a\u0442\u0430, \u0437\u0430\u043f\u0438\u0441\u0438 \u0447\u0435\u0440\u0435\u0437 \u0437\u0430\u043f\u044f\u0442\u0443\u044e)." % (what, tool, seg))


def mcp_servers(text):
    o = parse_obj(text)
    s = o.get('mcpServers') if o is not BAD_JSON else None
    return s if isinstance(s, dict) else {}


def mcp_grown(cur, after):
    """Что правка .mcp.json добавляет или перенаправляет: новый сервер или другая запись существующего (адрес, команда, аргументы)."""
    s_cur, s_new = mcp_servers(cur), mcp_servers(after)
    return sorted(k for k, v in s_new.items() if k not in s_cur or v != s_cur[k])


def mcp_approval_grown(o_cur, o_new):
    """Одобрение серверов .mcp.json в настройках: сервер, который ждал вопроса владельцу, заработал бы без него."""
    def names(o):
        v = o.get('enabledMcpjsonServers')
        return {str(x) for x in v} if isinstance(v, list) else set()
    out = sorted(names(o_new) - names(o_cur))
    if o_new.get('enableAllProjectMcpServers') and not o_cur.get('enableAllProjectMcpServers'):
        out.append('enableAllProjectMcpServers')
    return out


BROWSER = r'^mcp__(?:[\w-]+__)?(Claude_Browser|claude-in-chrome)__(browser_batch|computer)$'
SCREEN_ACTIONS = ('key', 'type', 'left_click_drag', 'screenshot', 'zoom', 'hold_key', 'left_mouse_down', 'left_mouse_up')


def check_browser(tool, ti):
    """no-screen-control п.4 (волна 2 п.2.19): координаты, эмуляция клавиатуры и скриншот — слой экрана, запрещены и внутри
    пакета browser_batch; клик и наведение по ref от самой страницы — её протокол, разрешены. Запрет в permissions.deny
    стоит только на сам computer и в проект приходит лишь повторным setup, а хук — с обновлением плагина."""
    mm = re.match(BROWSER, tool)
    if not mm:
        return
    items = [{'name': 'computer', 'input': ti or {}}] if mm.group(2) == 'computer' else \
        [a for a in (ti or {}).get('actions') or [] if isinstance(a, dict)]
    for a in items:
        if not str(a.get('name') or '').endswith('computer'):
            continue
        inp = a.get('input') if isinstance(a.get('input'), dict) else {}
        act = str(inp.get('action') or '')
        if 'coordinate' in inp or 'start_coordinate' in inp or act in SCREEN_ACTIONS or (act and not inp.get('ref') and act != 'wait'):
            deny('no-screen-control п.4: %s — действие «%s» %s — это слой экрана (координаты, клавиатура, снимок), даже '
                 'внутри вкладки браузера. Адресуйся элементом страницы: find/read_page дают ref, дальше клик по ref, '
                 'form_input для полей, get_page_text/read_page вместо скриншота.' % (tool, act or '?',
                                                                                     'по координатам' if 'coordinate' in inp else 'без ref'))


RECOMMENDED = r'\(\s*(\u0440\u0435\u043a\u043e\u043c\u0435\u043d\u0434\u0443\u0435\u0442\u0441\u044f|\u0440\u0435\u043a\u043e\u043c\u0435\u043d\u0434\u0443\u044e|\u0440\u0435\u043a\u043e\u043c\u0435\u043d\u0434\u043e\u0432\u0430\u043d\u043e|recommended)\s*\)'
FACT_QUESTION = (r'\b(\u0435\u0441\u0442\u044c \u043b\u0438|\u0441\u0443\u0449\u0435\u0441\u0442\u0432\u0443\u0435\u0442 \u043b\u0438|\u0438\u043c\u0435\u0435\u0442\u0441\u044f \u043b\u0438)\s+(\u0432\s+(\u043a\u043e\u043d\u0444\u0438\u0433\u0443\u0440\u0430\u0446\u0438\u0438|\u0431\u0430\u0437\u0435|\u043c\u043e\u0434\u0443\u043b\u0435|\u043a\u043e\u0434\u0435|\u043f\u0440\u043e\u0435\u043a\u0442\u0435)|\u0440\u0435\u043a\u0432\u0438\u0437\u0438\u0442|\u043c\u043e\u0434\u0443\u043b|\u043e\u0431\u044a\u0435\u043a\u0442|\u0441\u043f\u0440\u0430\u0432\u043e\u0447\u043d\u0438\u043a|'
                 r'\u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442|\u0440\u0435\u0433\u0438\u0441\u0442\u0440|\u043c\u0435\u0442\u043e\u0434|\u043f\u0440\u043e\u0446\u0435\u0434\u0443\u0440|\u0444\u0443\u043d\u043a\u0446\u0438|\u0444\u043e\u0440\u043c)'
                 r'|\b(\u043a\u0430\u043a\u043e\u0439|\u043a\u0430\u043a\u043e\u0433\u043e|\u043a\u0430\u043a\u0438\u043c)\s+\u0442\u0438\u043f\w*\s+(\u0443\s+)?(\u0440\u0435\u043a\u0432\u0438\u0437\u0438\u0442|\u043f\u043e\u043b[\u0435\u044f]|\u043a\u043e\u043b\u043e\u043d\u043a|\u043f\u0430\u0440\u0430\u043c\u0435\u0442\u0440|\u0438\u0437\u043c\u0435\u0440\u0435\u043d\u0438|\u0440\u0435\u0441\u0443\u0440\u0441)'
                 r'|\b(\u0433\u0434\u0435|\u0432 \u043a\u0430\u043a\u043e\u043c \u043c\u043e\u0434\u0443\u043b\u0435)\s+(\u043b\u0435\u0436\u0438\u0442|\u043d\u0430\u0445\u043e\u0434\u0438\u0442\u0441\u044f|\u043e\u043f\u0438\u0441\u0430\u043d\w*|\u043e\u043f\u0440\u0435\u0434\u0435\u043b\w*|\u0440\u0435\u0430\u043b\u0438\u0437\u043e\u0432\u0430\u043d\w*|\u043e\u0431\u044a\u044f\u0432\u043b\u0435\u043d\w*)'
                 r'|\b\u043a\u0430\u043a \u043d\u0430\u0437\u044b\u0432\u0430\u0435\u0442\u0441\u044f\s+(\u0440\u0435\u043a\u0432\u0438\u0437\u0438\u0442|\u043c\u043e\u0434\u0443\u043b\u044c|\u043e\u0431\u044a\u0435\u043a\u0442|\u043c\u0435\u0442\u043e\u0434|\u0440\u0435\u0433\u0438\u0441\u0442\u0440|\u0441\u043f\u0440\u0430\u0432\u043e\u0447\u043d\u0438\u043a|\u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442|\u043f\u0440\u043e\u0446\u0435\u0434\u0443\u0440|\u0444\u0443\u043d\u043a\u0446\u0438)')


def check_ask(data):
    """questions-as-options \u043f.2 \u0438 requirements-by-interview \u043f.4 \u2014 \u0443 \u043a\u0430\u0436\u0434\u043e\u0433\u043e \u0432\u043e\u043f\u0440\u043e\u0441\u0430 \u0440\u0435\u043a\u043e\u043c\u0435\u043d\u0434\u0443\u0435\u043c\u044b\u0439 \u0432\u0430\u0440\u0438\u0430\u043d\u0442, \u0438 \u043e\u043d \u043f\u0435\u0440\u0432\u044b\u0439
    (\u043e\u0442\u043a\u0430\u0437); \u0432\u043e\u043f\u0440\u043e\u0441 \u0432\u043b\u0430\u0434\u0435\u043b\u044c\u0446\u0443 \u043e \u0444\u0430\u043a\u0442\u0435 \u043a\u043e\u043d\u0444\u0438\u0433\u0443\u0440\u0430\u0446\u0438\u0438 (\u043f.2) \u2014 \u043f\u043e\u0434\u0441\u043a\u0430\u0437\u043a\u0430 \u043c\u043e\u0434\u0435\u043b\u0438 \u0438 \u0441\u0442\u0440\u043e\u043a\u0430 \u0432 logs/answer-check.jsonl."""
    bad, facts = [], []
    for q in (data.get('tool_input') or {}).get('questions') or []:
        if not isinstance(q, dict):
            continue
        opts = [o for o in q.get('options') or [] if isinstance(o, dict)]
        marked = [k for k, o in enumerate(opts) if re.search(RECOMMENDED, str(o.get('label') or ''), re.I)]
        head = str(q.get('header') or q.get('question') or '')[:50]
        if not marked:
            bad.append('\u00ab%s\u00bb \u2014 \u043d\u0438 \u043e\u0434\u0438\u043d \u0432\u0430\u0440\u0438\u0430\u043d\u0442 \u043d\u0435 \u043f\u043e\u043c\u0435\u0447\u0435\u043d \u00ab(\u0420\u0435\u043a\u043e\u043c\u0435\u043d\u0434\u0443\u0435\u0442\u0441\u044f)\u00bb' % head)
        elif not q.get('multiSelect') and marked[0] != 0:
            bad.append('\u00ab%s\u00bb \u2014 \u0440\u0435\u043a\u043e\u043c\u0435\u043d\u0434\u0443\u0435\u043c\u044b\u0439 \u0432\u0430\u0440\u0438\u0430\u043d\u0442 \u043d\u0435 \u043f\u0435\u0440\u0432\u044b\u0439' % head)
        if re.search(FACT_QUESTION, str(q.get('question') or ''), re.I):
            facts.append(str(q.get('question'))[:160])
    if bad:
        deny('questions-as-options \u043f.2 \u0438 requirements-by-interview \u043f.4: \u0443 \u043a\u0430\u0436\u0434\u043e\u0433\u043e \u0432\u043e\u043f\u0440\u043e\u0441\u0430 \u0440\u0435\u043a\u043e\u043c\u0435\u043d\u0434\u0443\u0435\u043c\u044b\u0439 \u0432\u0430\u0440\u0438\u0430\u043d\u0442 \u0438\u0434\u0451\u0442 \u043f\u0435\u0440\u0432\u044b\u043c, \u0441 \u043f\u043e\u043c\u0435\u0442\u043a\u043e\u0439 '
             '\u00ab(\u0420\u0435\u043a\u043e\u043c\u0435\u043d\u0434\u0443\u0435\u0442\u0441\u044f)\u00bb \u0432 \u043d\u0430\u0437\u0432\u0430\u043d\u0438\u0438 \u0438 \u043e\u0431\u043e\u0441\u043d\u043e\u0432\u0430\u043d\u0438\u0435\u043c \u0432 \u043f\u043e\u044f\u0441\u043d\u0435\u043d\u0438\u0438. ' + '; '.join(bad) + '. \u0417\u0430\u0434\u0430\u0439 \u043e\u043a\u043d\u043e \u0437\u0430\u043d\u043e\u0432\u043e \u0441 \u043f\u043e\u043c\u0435\u0442\u043a\u043e\u0439; \u0435\u0441\u043b\u0438 '
             '\u0432\u044b\u0431\u043e\u0440 \u0447\u0435\u0441\u0442\u043d\u043e \u0440\u0430\u0432\u043d\u043e\u0446\u0435\u043d\u043d\u044b\u0439 \u2014 \u043f\u043e\u043c\u0435\u0442\u044c \u0432\u0430\u0440\u0438\u0430\u043d\u0442 \u043f\u043e \u0443\u043c\u043e\u043b\u0447\u0430\u043d\u0438\u044e \u0438 \u0441\u043a\u0430\u0436\u0438 \u0432 \u043f\u043e\u044f\u0441\u043d\u0435\u043d\u0438\u0438, \u043f\u043e\u0447\u0435\u043c\u0443 \u043e\u043d.')
    if facts:
        root = os.environ.get('CLAUDE_PROJECT_DIR')
        if root:
            try:
                os.makedirs(os.path.join(root, 'logs'), exist_ok=True)
                with open(os.path.join(root, 'logs', 'answer-check.jsonl'), 'a', encoding='utf-8', newline='\n') as f:
                    f.write(json.dumps({'ts': int(time.time()), 'sid': str(data.get('session_id') or 'nosession'), 'shown': True,
                                        'kind': 'requirements-by-interview', 'sample': facts[0]}, ensure_ascii=False) + '\n')
            except OSError:
                pass
        sys.stdout.buffer.write(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'additionalContext': (
            'requirements-by-interview \u043f.2: \u0432\u043e\u043f\u0440\u043e\u0441 \u043f\u043e\u0445\u043e\u0436 \u043d\u0430 \u0432\u043e\u043f\u0440\u043e\u0441 \u043e \u0424\u0410\u041a\u0422\u0415 \u043a\u043e\u043d\u0444\u0438\u0433\u0443\u0440\u0430\u0446\u0438\u0438 (\u00ab%s\u00bb). \u0424\u0430\u043a\u0442 \u0434\u043e\u0431\u044b\u0432\u0430\u0435\u0442\u0441\u044f \u0438\u043d\u0441\u0442\u0440\u0443\u043c\u0435\u043d\u0442\u043e\u043c '
            '(meta-info, code-index, edt-mcp, 1c-toolkit), \u0432\u043b\u0430\u0434\u0435\u043b\u044c\u0446\u0443 \u0437\u0430\u0434\u0430\u044e\u0442\u0441\u044f \u0442\u043e\u043b\u044c\u043a\u043e \u0440\u0435\u0448\u0435\u043d\u0438\u044f. \u0415\u0441\u043b\u0438 \u043e\u0442\u0432\u0435\u0442 \u043c\u043e\u0436\u043d\u043e \u043f\u043e\u043b\u0443\u0447\u0438\u0442\u044c '
            '\u0438\u043d\u0441\u0442\u0440\u0443\u043c\u0435\u043d\u0442\u043e\u043c \u2014 \u043f\u043e\u043b\u0443\u0447\u0438 \u0435\u0433\u043e \u0441\u0430\u043c.' % facts[0])}}, ensure_ascii=False).encode('utf-8'))
        sys.stdout.flush()


def main():
    raw = sys.stdin.buffer.read().decode('utf-8', 'replace').lstrip('\ufeff')
    if not raw.strip():
        return
    data = json.loads(raw)
    tool = str(data.get('tool_name') or '')
    if tool == 'Skill':
        check_skill(data.get('tool_input') or {}, str(data.get('cwd') or ''))
        return
    if tool == 'AskUserQuestion':
        check_ask(data)
        return
    if tool.startswith('mcp__'):
        check_mcp(tool)
        check_browser(tool, data.get('tool_input'))
        return
    path = str((data.get('tool_input') or {}).get('file_path') or '')
    if not path.strip():
        return
    norm = path.replace('\\', '/').lower()

    # Журнал сессии и запись согласий — свидетельства «да» владельца для барьера помощников (аудит 30.10.2026)
    if re.search(r'/\.claude/projects/.+\.jsonl$', norm) or re.search(r'(^|/)logs/consent\.json$', norm):
        deny('subagents-on-explicit-consent: журнал сессии и logs/consent.json — свидетельства согласия владельца; агент их не '
             'правит. Нужен запуск помощников — спроси владельца окном вариантов.')

    # Хуки git и их настройка: подмена файла — обход проверок перед коммитом, как --no-verify (замер 30.10.2026)
    if re.search(r'(^|/)\.git/(hooks/|config$)', norm):
        deny('work-journals-and-commits п.8: файлы хуков git и .git/config правит только владелец — подменённый хук снимает красный '
             'health-check, сканер секретов и запрет строки Co-Authored-By. Хук мешает — чини то, на что он жалуется.')
    if re.search(r'/ssh-mcp/config\.toml$', norm):
        deny('ssh-mcp: файл настроек задаёт ворота подтверждения команд на сервере (approvalPolicy, role) — правит только владелец.')

    # Новый сервер — только владелец (use-own-mcp-servers-only): имя из .mcp.json проекта барьер источника считает своим.
    # plugin/.mcp.json — исходник плагина в мастере: он приходит в проекты выпуском, а не правкой на месте.
    if re.search(r'(^|/)\.mcp\.json$', norm) and not re.search(r'/plugin/\.mcp\.json$', norm):
        cur, after = edit_result(data, path)
        grown = mcp_grown(cur, after) if after is not None else []
        if grown:
            deny('use-own-mcp-servers-only: правка .mcp.json добавляет или перенаправляет сервер (%s) — имя отсюда барьер источника считает '
                 'своим, а чужой адрес ведёт в другую, в том числе боевую, базу. Список серверов меняет только владелец: скажи ему, какой '
                 'сервер и зачем.' % ', '.join(grown))
        return

    # Файлы, которым верят барьеры (замер 30.10.2026). Хук в кэше запускается заново на каждый вызов — правка действует сразу;
    # плагин внутри проекта — разработка (--plugin-dir), там его защищают контуры мастера ниже.
    root = (os.environ.get('CLAUDE_PROJECT_DIR') or '').replace('\\', '/').lower().rstrip('/')
    plug = (os.environ.get('CLAUDE_PLUGIN_ROOT') or '').replace('\\', '/').lower().rstrip('/')
    if re.search(r'/\.claude/plugins/(cache|marketplaces)/', norm) or \
            (plug and norm.startswith(plug + '/') and not (root and norm.startswith(root + '/'))):
        deny('самозащита контуров: файлы установленного плагина (кэш и клон канала) агент не правит — в них хуки, и правка сняла бы '
             'защиту сразу, в обход проверки. Плагин меняется только обновлением: claude plugin update. Если защита мешает — '
             'скажи владельцу, что и зачем.')
    # Настройки анализатора: правка существующего файла, чтобы проверка прошла, вместо исправления кода (решение владельца
    # 05.11.2026, по мотивам config-protection ECC — docs/sources/ecc-review.md). Новый файл — можно.
    if re.search(r'(^|/)\.bsl-language-server\.json$', norm) and os.path.isfile(path):
        deny('bug-diagnosis-loop Ф5: настройки BSL Language Server (.bsl-language-server.json) агент не правит — отключённая '
             'диагностика прячет замечание, а не исправляет код. Исправь код. Диагностика ложная — скажи владельцу, какая и '
             'почему; файл правит он.')
    if re.search(r'/state/1c-toolkit-bases\.json$', norm):
        deny('personal-data-masked-from-1c: файл состояния тулкита говорит барьеру ПДн, на какой базе поднят тулкит. Его пишет только '
             '/ones-core:toolkit; агент его не правит. Нужна другая база — подними тулкит на ней этой командой.')
    if re.search(r'/plugin/hooks/contours\.sha256$', norm):
        deny('самозащита контуров: реестр сумм хуков не правится руками — его пересобирает tools/indexes/gen-contour-registry.py.')
    if re.search(r'/plugin/hooks/hooks\.json$', norm):
        cur, after = edit_result(data, path)
        lost = [c for c in CONTOURS if c in cur and c not in after] if after is not None else []
        if lost:
            deny('самозащита контуров: после правки из hooks.json пропадает проводка контура: %s. Перенос блока делай одной правкой, '
                 'снятие контура — только решением владельца.' % ', '.join(lost))
        return

    # Самозащита настроек: судится результат правки.
    if re.search(r'/\.claude/settings(\.local)?\.json$', norm):
        cur, after = edit_result(data, path)
        if after is not None:
            o_new = parse_obj(after)
            if o_new is BAD_JSON:
                deny('самозащита контуров: после правки файл настроек не разбирается как объект JSON — Claude Code его не '
                     'прочтёт, а запреты и проводку контуров уже не сверить. Сделай правку так, чтобы результат был валидным JSON.')
            o_cur = parse_obj(cur)
            o_cur = {} if o_cur is BAD_JSON else o_cur
            if o_new.get('disableAllHooks') not in (None, False, 0, '', 'false') or \
                    re.search(r'"disableAllHooks"\s*:\s*true', after, re.I):
                deny('самозащита контуров: правка включает disableAllHooks — это снимает ВСЕ контуры принуждения. '
                     'Если это осознанное решение владельца — пусть он внесёт его сам.')
            off = plugin_off(o_cur, o_new)
            if off:
                deny('самозащита контуров: правка выключает плагин (%s) — вместе с ним снимаются все его барьеры и проверки. '
                     'Выключить плагин может только владелец, своей правкой настроек.' % ', '.join(off))
            # по числу подключений: guard-destructive стоит и на Bash, и на Read — снятие одного не скрыто другим
            lost = [c for c in CONTOURS if after.count(c) < cur.count(c)]
            if lost:
                deny('самозащита контуров: после правки из настроек пропадает проводка контура: ' + ', '.join(lost) +
                     '. Перенос блока делай одной правкой (новое место + удаление старого), снятие контура — только решением владельца.')
            removed = sorted(deny_set(o_cur) - deny_set(o_new))
            if removed:
                deny('самозащита контуров: из permissions.deny пропадают записи (%s) — первичный барьер ослабляется, даже если '
                     'взамен добавлены другие. Только решением владельца.' % ', '.join(removed[:5]))
            if default_mode(o_new) == 'bypassPermissions' and default_mode(o_cur) != 'bypassPermissions':
                deny('самозащита контуров: правка ставит режим bypassPermissions по умолчанию — вызовы пойдут без вопросов '
                     'владельцу. Режим выбирает только владелец.')
            grown = allow_grown(cur, after)
            if grown:
                deny('самозащита барьера источника: правка расширяет список разрешённых (%s) — посторонний сервер или плагин '
                     'разрешает только владелец, своей правкой настроек. Скажи ему, что и зачем нужно.' % '; '.join(grown))
            approved = mcp_approval_grown(o_cur, o_new)
            if approved:
                deny('use-own-mcp-servers-only: правка настроек одобряет серверы .mcp.json без вопроса владельцу (%s). Одобряет он сам, в окне '
                     'при запуске.' % ', '.join(approved))
        return

    # Самозащита конфигов проверок — до служебных зон: names.txt лежит в /tools/checks/ (до 16.10.2026 — в /tools/).
    if re.search(r'/\.v8-project\.json$', norm) or re.search(r'/tools/(checks/)?health-check\.names\.txt$', norm):
        cur, after = edit_result(data, path)
        if after is not None:
            if re.search(r'/\.v8-project\.json$', norm):
                # Реестр — точка доверия барьеров боевой базы и ПДн (аудит 30.10.2026): битый файл они читают вслепую,
                # отметку pd ставит только владелец, новое подключение базы подтверждает он же в окне разрешения.
                r_new, r_cur = parse_obj(after), parse_obj(cur)
                if r_new is BAD_JSON:
                    deny('самозащита реестра баз: после правки .v8-project.json не разбирается как объект JSON — барьеры '
                         'боевой базы и ПДн по нему уже не сверить. Сделай правку так, чтобы результат был валидным JSON.')
                dbs_cur = registry_dbs_of({} if r_cur is BAD_JSON else r_cur)
                dbs_new = registry_dbs_of(r_new)
                looser = [i for i, d in dbs_new.items() if pd_rank(d) < pd_rank(dbs_cur.get(i))]
                if looser:
                    deny('personal-data-masked-from-1c: правка ослабляет отметку pd у базы (%s) — после неё данные базы '
                         'пойдут к модели. Отметку ставит только владелец: скажи ему, какую базу и почему.' % ', '.join(looser))
                moved = [i for i, d in dbs_new.items()
                         if any(str(d.get(k) or '') != str((dbs_cur.get(i) or {}).get(k) or '') for k in CONN_KEYS)]
                l_cur, l_new = checker_levels(cur), checker_levels(after)
                if l_cur is not None and l_new is not None:
                    down = []
                    new_ci = {k.lower(): v for k, v in l_new.items()}   # в PowerShell ключи таблицы без учёта регистра
                    for k, v in l_cur.items():
                        if k.lower() not in new_ci:
                            continue
                        rc, rn = RANK.get(v), RANK.get(new_ci[k.lower()])
                        if rc is None or rn is None:
                            continue
                        if rn < rc:
                            down.append('%s: %s -> %s' % (k, v, new_ci[k.lower()]))
                    if down:
                        deny('самозащита конфигов чекеров: правка ПОНИЖАЕТ уровень проверки — ' + '; '.join(down) +
                             '. Если проверка мешает, починить надо то, на что она жалуется, а не её саму. Снятие проверки — только решением владельца.')
                if moved:
                    # отказ, а не вопрос: в режимах auto и bypassPermissions вопрос может пройти молча (контракт волны G)
                    deny('secrets-and-production-database: правка добавляет базу или меняет её подключение (%s). Запись в реестре '
                         'делает базу «тестовой» для барьеров, поэтому её вносит только владелец — своей правкой '
                         '.v8-project.json (блок databases). Скажи ему, какую базу и зачем.' % ', '.join(moved))
            else:
                n_cur, n_new = count_names(cur), count_names(after)
                if n_new < n_cur:
                    deny('самозащита конфигов чекеров: список имён для скана утечек сокращается (%d -> %d). Гейт утечки чужих имён '
                         '(health-check §7) ослабляется молча — убрать имя может только владелец, когда экземпляр действительно выведен.' % (n_cur, n_new))
        return

    if exempt(norm, data):
        return
    file = norm.split('/')[-1]
    for match, msg in RULES:
        if match(file, norm):
            deny('use-skills-not-manual-edits: артефакт 1С правится скиллом, а не руками. Файл: %s. Маршрут: %s. '
                 'Если скилл проверенно не покрывает случай — назови исключение вслух (use-skills-not-manual-edits п.6) и согласуй ручную правку с пользователем.' % (path, msg))


if __name__ == '__main__':
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stdout.buffer.write(json.dumps({'systemMessage': 'guard-skills: DEGRADED — внутренняя ошибка, правка пропущена без '
                                            'проверки: %s' % e}, ensure_ascii=False).encode('utf-8'))
        sys.stdout.flush()
    sys.exit(0)
