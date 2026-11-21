"""SessionStart (плагин): сказать модели, где лежат правила ядра, и проверить, на месте ли программы инструментов.

В проекте правила и справочники ядра лежат не в папке проекта, а в папке плагина (${CLAUDE_PLUGIN_ROOT}/docs);
тексты ядра ссылаются на них путями вида docs/<тема>/<имя>.md — от папки плагина. Вывод SessionStart доходит до модели.
Программы (code-index, bsl-analyzer, YAXUnit и др.) ставит установщик в ${CLAUDE_PLUGIN_DATA}/bin; если их нет — подсказать команду.
Скрипты ядра тексты называют путями tools/<папка>/<скрипт> — от папки плагина; скриптов мастера ядра (health-check и др.)
в плагине нет, и модель должна это знать, а не искать их в проекте.
Сканер секретов для git pre-commit живёт копией в ${CLAUDE_PLUGIN_DATA}/bin (путь не меняется при обновлении плагина);
если /ones-core:setup его уже положил — копия обновляется здесь, когда плагин обновился.
Профиль проекта (с 4.7.0): индекс кода внутри исходников настоящей папкой, а не ссылкой (code-index-outside-sources),
и папка платформы из ONEC_PLATFORM_BIN без 1cv8.exe (platform-version-and-optional-edt) — предупреждение модели;
с 4.9.0 — временные папки сессий проекта больше порога (ONEC_TEMP_WARN_GB, по умолчанию 5 ГБ).
Волна 1 (замер 29.10.2026): запреты проекта против шаблона плагина (недостающие и снятые — команда connect-project --deny-only),
версия установленных программ против манифеста этой сборки, посторонние плагины и их модули (кроме ones-core и ONEC_PLUGINS_ALLOW).
Замер 30.10.2026: нет бюджета списка скиллов в настройках проекта — та же команда.
С 20.11.2026 (решение владельца): нет переменной встроенного списка задач Claude Code — дописывается в env настроек проекта.
В мастере ядра (без CLAUDE_PLUGIN_ROOT) молчит: там docs/ лежит в корне проекта. Любая ошибка — молча.
"""
import json
import os
import re
import shutil
import sys

OWN_PLUGIN = 'ones-core@ones-core'


def obj(path):
    """JSON-объект из файла; нет файла, не разбирается или не объект — {}."""
    try:
        with open(path, encoding='utf-8-sig') as f:
            o = json.load(f)
    except (OSError, ValueError):
        return {}
    return o if isinstance(o, dict) else {}


def safe(fn, *a):
    """Одна проверка упала — остальные сообщения всё равно доходят до модели."""
    try:
        return fn(*a)
    except Exception:
        return []


def allow_list(name, proj):
    """Список разрешённых: переменная окружения и env в .claude/settings(.local).json проекта; через запятую, без учёта регистра."""
    vals = [os.environ.get(name) or '']
    for f in ('settings.json', 'settings.local.json'):
        env = obj(os.path.join(proj, '.claude', f)).get('env') if proj else None
        if isinstance(env, dict):
            vals.append(str(env.get(name) or ''))
    return {x.strip().lower() for v in vals for x in re.split(r'[,;\s]+', v) if x.strip()}


def deny_check(root, proj):
    """Запреты проекта (.claude/settings.json) против шаблона плагина: недостающие и снятые (retired) — предупреждение с командой.
    Та же команда дописывает бюджет списка скиллов: без ключа о нём отдельное напоминание."""
    tpl = obj(os.path.join(root, 'tools', 'setup', 'project-deny.json'))
    if not proj or not tpl.get('deny'):
        return []
    settings = obj(os.path.join(proj, '.claude', 'settings.json'))
    perms = settings.get('permissions')
    have = perms.get('deny') if isinstance(perms, dict) else None
    have = have if isinstance(have, list) else []
    add = [d for d in tpl.get('deny') or [] if d not in have]
    drop = [d for d in tpl.get('retired') or [] if d in have]
    cmd = 'python "%s" --project "%s" --deny-only' % (os.path.join(root, 'tools', 'setup', 'connect-project.py'), proj)
    notes = []
    if add or drop:
        parts = (['не хватает %d: %s' % (len(add), ', '.join(add))] if add else []) + \
                (['остались снятые %d: %s' % (len(drop), ', '.join(drop))] if drop else [])
        notes.append('Запреты проекта (permissions.deny в .claude/settings.json) отстают от шаблона ядра — %s. Запреты держат опасные команды '
                     'и чтение секретов до исполнения, а плагин сам их не обновляет; снятые ядро убрало как ошибочные. Скажи владельцу и с его '
                     '«да» обнови: сперва %s --dry-run (покажет каждую запись), затем то же без --dry-run — недостающие дописываются, снятые '
                     'убираются, остальные настройки не трогаются.' % ('; '.join(parts), cmd))
    if 'skillListingBudgetFraction' not in settings and 'skillListingBudgetFraction' not in obj(os.path.join(proj, '.claude', 'settings.local.json')):
        notes.append('В .claude/settings.json проекта нет бюджета списка скиллов (skillListingBudgetFraction): описания части скиллов '
                     'плагина не доходят до модели, а плагин сам этот ключ не пишет. Скажи владельцу и с его «да» допиши: %s' % cmd)
    return notes


TODO_KEY = 'CLAUDE_CODE_ENABLE_TODO_TOOLS'


def todo_tools(proj):
    """Встроенный список задач Claude Code (решение владельца 20.11.2026): на Opus 5.x его инструменты есть только с переменной.
    Нет её ни в окружении, ни в env настроек проекта — дописать в env .claude/settings.json (подключённого проекта; битый файл
    не трогается); Claude Code подхватывает правку настроек на ходу. Свой выбор проекта или пользователя (любое значение) не трогается."""
    sp = os.path.join(proj, '.claude', 'settings.json') if proj else ''
    if not sp or os.environ.get(TODO_KEY) is not None or not os.path.isfile(sp):
        return []
    if any(isinstance(obj(os.path.join(proj, '.claude', f)).get('env'), dict) and TODO_KEY in obj(os.path.join(proj, '.claude', f))['env']
           for f in ('settings.json', 'settings.local.json')):
        return []
    with open(sp, encoding='utf-8-sig') as f:
        s = json.load(f)   # битый файл — исключение, safe() вернёт []: не переписывать то, что не разобрано
    if not isinstance(s, dict) or not isinstance(s.setdefault('env', {}), dict):
        return []
    s['env'][TODO_KEY] = '1'
    with open(sp, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(s, f, ensure_ascii=False, indent=2)
        f.write('\n')
    return ['Включён встроенный список задач Claude Code: в env .claude/settings.json проекта дописано %s=1 (решение владельца). '
            'Шаги многошаговой задачи веди инструментами TaskCreate и TaskUpdate.' % TODO_KEY]


def plugin_modules(path):
    """Модули плагина (код в процессе Claude Code) — список "modules" из его hooks/hooks.json."""
    mods = obj(os.path.join(path, 'hooks', 'hooks.json')).get('modules') if path else None
    return [str(x) for x in mods] if isinstance(mods, list) else []


def plugin_checks(proj):
    """Посторонние плагины этого проекта (кроме ones-core и ONEC_PLUGINS_ALLOW) и их модули — предупреждение.
    Источники: installed_plugins.json (уровень пользователя и этот проект) и enabledPlugins настроек; выключенный (false) — молча."""
    cfg = os.environ.get('CLAUDE_CONFIG_DIR') or os.path.join(os.path.expanduser('~'), '.claude')
    here = os.path.normcase(os.path.abspath(proj)) if proj else ''
    paths = {}
    inst = obj(os.path.join(cfg, 'plugins', 'installed_plugins.json')).get('plugins')
    for pid, recs in (inst.items() if isinstance(inst, dict) else []):
        for r in recs if isinstance(recs, list) else []:
            if not isinstance(r, dict):
                continue
            pp = str(r.get('projectPath') or '')
            if r.get('scope') == 'user' or (here and pp and os.path.normcase(os.path.abspath(pp)) == here):
                paths.setdefault(pid, str(r.get('installPath') or ''))
    enabled = {}
    files = [os.path.join(cfg, 'settings.json')]
    if proj:
        files += [os.path.join(proj, '.claude', 'settings.json'), os.path.join(proj, '.claude', 'settings.local.json')]
    for f in files:   # по старшинству: проект перекрывает пользователя, local — проект
        ep = obj(f).get('enabledPlugins')
        if isinstance(ep, dict):
            enabled.update(ep)
    allow = allow_list('ONEC_PLUGINS_ALLOW', proj) | {OWN_PLUGIN}
    found = []
    for pid in sorted(set(paths) | {k for k, v in enabled.items() if v}):
        if enabled.get(pid) is False or pid.lower() in allow:
            continue
        mods = plugin_modules(paths.get(pid) or '')
        found.append(pid + (' (модули: %s)' % ', '.join(mods) if mods else ''))
    if not found:
        return []
    return ['Посторонние плагины в этом проекте (не ones-core и не в списке разрешённых ONEC_PLUGINS_ALLOW): %s. Чужой плагин со своими '
            'хуками и модулями работает в той же сессии и может обойти правила ядра. Скажи владельцу: оставить — он сам добавляет id '
            'в ONEC_PLUGINS_ALLOW (env в .claude/settings.json проекта, через запятую); убрать — claude plugin disable <id>.'
            % '; '.join(found)]


def is_link(p):
    """Ссылка или junction Windows (их ставит code-index-daemon.py add)."""
    try:
        return os.path.islink(p) or bool(getattr(os.path, 'isjunction', lambda _: False)(p))
    except OSError:
        return False


def session_temp_warning(budget=3.0):
    """Временные папки сессий Claude Code этого проекта (%TEMP%/claude/<слаг проекта>) больше порога — предупреждение.
    Слаг — путь проекта, где всё, кроме латиницы и цифр, заменено дефисом (D:\\my_proj → D--my-proj). Подсчёт — не дольше
    budget секунд; порог — ONEC_TEMP_WARN_GB (по умолчанию 5). Наблюдение 17.10.2026: копии баз, выводы фоновых задач и
    профили браузера не чистятся сами — три старые сессии заняли 36 ГБ на C:."""
    import re
    import tempfile
    import time
    proj = os.environ.get('CLAUDE_PROJECT_DIR') or ''
    if not proj:
        return []
    base = os.path.join(tempfile.gettempdir(), 'claude', re.sub(r'[^A-Za-z0-9]', '-', proj.rstrip('\\/')))
    if not os.path.isdir(base):
        return []
    try:
        limit = float(os.environ.get('ONEC_TEMP_WARN_GB') or 5) * 1024 ** 3
    except ValueError:
        limit = 5 * 1024 ** 3
    t0, total, per, full = time.time(), 0, {}, True
    for sid in os.listdir(base):
        for root, _, files in os.walk(os.path.join(base, sid)):
            for f in files:
                try:
                    s = os.path.getsize(os.path.join(root, f))
                except OSError:
                    continue
                total += s
                per[sid] = per.get(sid, 0) + s
            if time.time() - t0 > budget:
                full = False
                break
        if not full:
            break
    if total < limit:
        return []
    top = ', '.join('%s %.1f ГБ' % (k[:8], v / 1024 ** 3) for k, v in sorted(per.items(), key=lambda kv: -kv[1])[:3])
    return ['Временные папки сессий Claude Code этого проекта занимают %s%.1f ГБ (%s; крупнейшие: %s): копии баз, выводы фоновых '
            'задач и профили браузера сами не чистятся. Скажи владельцу и предложи перенести их на другой диск или удалить '
            'старые сессии — окончательно сам не удаляй.' % ('не меньше ' if not full else '', total / 1024 ** 3, base, top)]


def profile_checks():
    """Предупреждения по профилю проекта; пустой список — всё на месте или переменные не заданы."""
    out = session_temp_warning()
    src = (os.environ.get('ONEC_PROJECT_SRC') or '').strip().strip('"').rstrip('\\/')
    ci = os.path.join(src, '.code-index') if src else ''
    if ci and os.path.isdir(ci) and not is_link(ci):
        out.append('Индекс кода лежит внутри исходников настоящей папкой (%s), а не ссылкой: по правилу '
                   'code-index-outside-sources индекс хранится в <проект>/.code-index, в исходниках — только ссылка (junction), '
                   'исключённая из git и EDT. /ones-core:setup такую папку оставляет как есть — скажи владельцу, перенос — с ним.' % ci)
    plat = (os.environ.get('ONEC_PLATFORM_BIN') or '').strip().strip('"')
    if plat and not os.path.isfile(os.path.join(plat, '1cv8.exe')):
        out.append('Платформа 1С из профиля проекта не найдена: в ONEC_PLATFORM_BIN (%s) нет 1cv8.exe — пакетные запуски '
                   'платформы не заработают. Версия платформы — свойство профиля проекта (platform-version-and-optional-edt): '
                   'путь правится в .claude/settings.local.json или повторным /ones-core:setup.' % plat)
    return out


def main():
    root = os.environ.get('CLAUDE_PLUGIN_ROOT')
    if not root:
        return
    docs = os.path.join(root, 'docs')
    lines = ['⚙ ones-core: правила и справочники ядра — %s (оглавление по темам — %s). '
             'Пути вида docs/<тема>/<имя>.md в текстах ядра считаются от папки плагина %s; '
             'журналы и знания проекта — в docs-project/ проекта. Скиллы ядра вызываются с приставкой ones-core:.'
             % (docs, os.path.join(docs, 'MEMORY.md'), root)]
    data = os.environ.get('CLAUDE_PLUGIN_DATA')
    lines.append('Скрипты в текстах ядра (tools/<папка>/<скрипт>): если он есть в %s — запускать оттуда; если нет '
                 '(health-check, gen-doc-index, contour-tests, release-core и др.) — это инструмент мастера ядра, '
                 'в проекте его нет и запускать не нужно. Программы инструментов (индекс кода, анализатор, YAXUnit и др.) — %s.'
                 % (os.path.join(root, 'tools'), os.path.join(data, 'bin', '<имя>') if data else 'папка данных плагина, bin/<имя>'))
    if data and os.path.isfile(os.path.join(data, 'code-index', 'daemon.toml')) and not os.path.isfile(os.path.join(data, 'code-index', 'daemon.json')):
        lines.append('Фоновый индексатор кода не запущен — сервер code-index не ответит на запросы. Запустить: python "%s" --plugin-data "%s" start'
                     % (os.path.join(root, 'tools', 'setup', 'code-index-daemon.py'), data))
    if data:
        src = os.path.join(root, 'tools', 'git', 'secret-scan.py')
        dst = os.path.join(data, 'bin', 'secret-scan.py')
        try:
            if os.path.isfile(src) and os.path.isfile(dst) and open(src, 'rb').read() != open(dst, 'rb').read():
                shutil.copyfile(src, dst)
        except OSError:
            pass
    manifest = os.path.join(root, 'tools', 'setup', 'tools-manifest.json')
    if data and os.path.isfile(manifest):
        try:
            with open(manifest, encoding='utf-8') as f:
                tools = json.load(f).get('tools') or []
            state_path = os.path.join(data, 'bin', 'installed.json')
            state = {}
            if os.path.isfile(state_path):
                with open(state_path, encoding='utf-8') as f:
                    state = json.load(f)
            missing = [t.get('name') for t in tools if t.get('name') not in state]
            if missing:
                lines.append('Программы инструментов не установлены: %s. Установить (скачает из официальных релизов и сверит суммы): '
                             'python "%s" --dest "%s"' % (', '.join(missing), os.path.join(root, 'tools', 'setup', 'install-tools.py'),
                                                          os.path.join(data, 'bin')))
            # версия и сборка — как сверяет install-tools.py: другая версия или сумма файла = не та программа
            stale = [t for t in tools if t.get('name') in state and not (isinstance(state[t['name']], dict)
                     and state[t['name']].get('version') == t.get('version') and state[t['name']].get('asset_sha256') == t.get('sha256'))]
            if stale:
                desc = ['%s (стоит %s, в манифесте %s%s)' % (t['name'], (state[t['name']] or {}).get('version') or '?', t.get('version'),
                        ', другая сборка файла' if (state[t['name']] or {}).get('version') == t.get('version') else '') for t in stale]
                lines.append('Программы инструментов не той версии, что в манифесте этой сборки плагина: %s. Папка программ общая для '
                             'всех проектов этой машины (%s) — скажи владельцу; переустановка сменит версию для всех: python "%s" '
                             '--dest "%s" --only %s' % ('; '.join(desc), os.path.join(data, 'bin'),
                                                        os.path.join(root, 'tools', 'setup', 'install-tools.py'),
                                                        os.path.join(data, 'bin'), ' '.join(t['name'] for t in stale)))
        except (OSError, ValueError, AttributeError, TypeError):
            pass
    proj = os.environ.get('CLAUDE_PROJECT_DIR') or ''
    lines += safe(deny_check, root, proj)
    lines += safe(todo_tools, proj)
    lines += safe(plugin_checks, proj)
    lines += profile_checks()
    sys.stdout.buffer.write(('\n'.join(lines) + '\n').encode('utf-8'))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
