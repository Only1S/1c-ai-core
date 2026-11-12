"""Подключить проект к ядру ones-core (плагин Claude Code): git, настройки, переменные, заготовки журналов.

    python connect-project.py --src <папка выгрузки конфигурации> --platform-bin <папка bin платформы 1С> [параметры]

Что делает (только дописывает недостающее, ничего не удаляет; с --dry-run — только показывает):
  1. git: если папка проекта ещё не репозиторий — git init (история проекта обязательна).
  2. .claude/settings.json проекта: каталог плагинов и включение плагина ones-core; запреты опасных команд
     (permissions.deny) — плагин сам их задать не может, поэтому они живут в настройках проекта; разрешения на
     инструменты серверов плагина, которые только читают (permissions.allow: v8std, bsl-platform, bsl-context, code-index,
     bsl-ls — решение владельца 17.10.2026), чтобы сессия не спрашивала о каждом, и чтение статей скиллов из кэша плагина
     (Read(~/.claude/plugins/cache/ones-core/**), решение владельца 29.10.2026; запись туда не разрешается). Инструменты
     1c-toolkit (запросы и код в базе) — по-прежнему с вопросом.
  3. .claude/settings.local.json (вне git): переменные проекта — где выгрузка, где платформа, порты серверов.
  4. .mcp.json проекта: необязательный сервер edt-mcp при --edt-port; 1c-forms идёт в плагине.
  5. .gitignore: секреты, локальные настройки, логи, индексы.
  6. docs-project/: заготовки журналов и оглавления, если их нет.
  7. git pre-commit: проверка секретов перед коммитом (tools/git/secret-scan.py). Сканер копируется в папку данных
     плагина (--plugin-data): путь к ней не меняется при обновлении плагина, а путь к самому плагину — меняется.
     Чужой pre-commit не трогается — скрипт сообщает, какую строку в него добавить.
  7б. git commit-msg: страж правил коммита — строка Co-Authored-By не проходит (копия tools/git/commit-msg плагина,
     work-journals-and-commits п.8). Ставится и без --plugin-data; чужой commit-msg не трогается.
  8. Индекс кода (ADR-0006): папка <проект>/.code-index, ссылка на неё из выгрузки, выгрузка в списке общего фонового
     индексатора (code-index-daemon.py add, тоже по --plugin-data). Автозапуск и запуск индексатора — отдельным шагом
     /ones-core:setup, по согласию владельца.
Параметры: --project (по умолчанию текущая папка), --toolkit-port (по умолчанию 6003), --edt-port,
--plugin-data (папка данных плагина, ${CLAUDE_PLUGIN_DATA}), --marketplace (по умолчанию github: Only1S/1c-ai-core),
--dry-run.

    python connect-project.py --project <папка проекта> --deny-only [--dry-run]

Только запреты (с волны 1): в permissions.deny .claude/settings.json проекта дописать недостающие из project-deny.json и
убрать снятые (retired); остальные настройки и шаги не трогаются, --src и --platform-bin не нужны. Каждая запись
печатается до записи файла; с --dry-run — только печать. Команду подсказывает session-start, когда запреты отстают.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ID = 'ones-core@ones-core'
# серверы плагина, которые только читают: правило на весь сервер — mcp__plugin_<плагин>_<сервер> (проверено пробой)
READONLY_SERVERS = ('v8std', 'bsl-platform', 'bsl-context', 'code-index', 'bsl-ls')
# бюджет списка скиллов: при 1% (по умолчанию) описания редких скиллов плагина срезаются; skillOverrides скиллы плагина не берёт
SKILL_BUDGET = 0.02
DEFAULT_REPO = 'Only1S/1c-ai-core'


def plugin_cache_read_rule():
    """Правило чтения статей скиллов из кэша плагинов Claude Code: весь кэш ones-core (папка версии меняется с выпуском).
    Путь в домашнем каталоге — формой ~/, иначе абсолютной //c/… (на Windows путь приводится к виду POSIX)."""
    cfg = os.environ.get('CLAUDE_CONFIG_DIR') or os.path.join(os.path.expanduser('~'), '.claude')
    cache = os.path.abspath(os.path.join(cfg, 'plugins', 'cache', PLUGIN_ID.split('@')[1]))
    home = os.path.abspath(os.path.expanduser('~'))
    if os.path.normcase(cache).startswith(os.path.normcase(home) + os.sep):
        return 'Read(~/%s/**)' % os.path.relpath(cache, home).replace('\\', '/')
    drive, rest = os.path.splitdrive(cache)
    return 'Read(//%s%s/**)' % (drive.rstrip(':').lower() + '/' if drive else '', rest.replace('\\', '/').lstrip('/'))
GITIGNORE = ['.env', '.env.*', '!.env.example', '.claude/settings.local.json', '.claude/task-steps.json', 'logs/', '*.log',
             '.code-index/', '.form-bin-mirror/', '.archify/', '__pycache__/', '*.pyc']
JOURNALS = {
    'INDEX.md': '# Знания и журналы проекта\n\nОглавление `docs-project/`: журналы и знания этого проекта. Правила ядра — в плагине ones-core '
                '(путь называет сообщение в начале сессии).\n\n## Журналы\n- [worklog](worklog.md) — журнал работы\n'
                '- [changelog](changelog.md) — правки по строке\n- [observations](observations.md) — наблюдения, которые ещё не стали правилом\n',
    'worklog.md': '# Журнал работы\n\nЧто прочитано, что сделано, текущее состояние — по вехам.\n',
    'changelog.md': '# Хронология правок\n\n| Время | Файл | Что изменено | Зачем | Проверка |\n|---|---|---|---|---|\n',
    'observations.md': '# Наблюдения\n\n| Дата | Что замечено | Где всплыло | Что предлагается |\n|---|---|---|---|\n',
}


HOOK_MARK = '# ones-core: проверка секретов перед коммитом'
COMMIT_MSG_MARK = '# ones-core: страж правил коммита'


def git_hooks_dir(proj):
    """Папка хуков git проекта (учитывает рабочие копии и core.hooksPath); без git — .git/hooks."""
    if os.path.isdir(os.path.join(proj, '.git')) or os.path.isfile(os.path.join(proj, '.git')):
        # путь — в UTF-8, как его отдаёт git: в кодировке системы кириллица в пути рабочей копии портилась
        r = subprocess.run(['git', '-C', proj, 'rev-parse', '--git-path', 'hooks'], capture_output=True, encoding='utf-8',
                           errors='replace')
        if r.returncode == 0 and r.stdout.strip():
            return os.path.join(proj, r.stdout.strip())
    return os.path.join(proj, '.git', 'hooks')


def pre_commit_text(scan, python):
    """Текст git pre-commit: сканер из папки данных плагина; нет сканера — коммит не запирается."""
    scan = scan.replace(chr(92), '/')
    python = python.replace(chr(92), '/')
    return ('#!/bin/sh\n'
            + HOOK_MARK + ' (ставит /ones-core:setup; обойти осознанно — git commit --no-verify)\n'
            + 'SCAN="%s"\n' % scan
            + 'PY="%s"\n' % python
            + '[ -x "$PY" ] || PY=python\n'
            + 'if [ ! -f "$SCAN" ]; then\n'
            + '  echo "ones-core: сканер секретов не найден ($SCAN) - коммит без проверки; повторите /ones-core:setup"\n'
            + '  exit 0\n'
            + 'fi\n'
            + '"$PY" "$SCAN" || exit 1\n')


def load(path):
    if not os.path.isfile(path):
        return {}
    with open(path, encoding='utf-8-sig') as f:
        return json.load(f)


def save(path, data, actions, label, dry):
    actions.append(label)
    if dry:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')


def merge_deny(s):
    """Запреты шаблона в настройках s: дописать недостающие, убрать снятые; вернуть (дописанные, снятые)."""
    tpl = load(os.path.join(HERE, 'project-deny.json'))
    deny = s.setdefault('permissions', {}).setdefault('deny', [])
    added = [d for d in tpl.get('deny', []) if d not in deny]
    deny.extend(added)
    retired = [d for d in tpl.get('retired', []) if d in deny]
    deny[:] = [d for d in deny if d not in retired]
    return added, retired


def deny_only(proj, dry):
    """--deny-only: permissions.deny и бюджет списка скиллов в .claude/settings.json проекта; каждая запись печатается до записи файла.
    Бюджет здесь же, потому что обновление проектов идёт этим путём: без него описания части скиллов плагина не доходят до модели."""
    sp = os.path.join(proj, '.claude', 'settings.json')
    s = load(sp)
    added, retired = merge_deny(s)
    budget = 'skillListingBudgetFraction' not in s
    if budget:
        s['skillListingBudgetFraction'] = SKILL_BUDGET
    changed = added or retired or budget
    print(('Что будет сделано' if dry else 'Сделано') + (':' if changed else ': ничего — запреты проекта совпадают с шаблоном ядра'))
    for d in added:
        print('  + запрет %s' % d)
    for d in retired:
        print('  - снятый запрет %s (убран из шаблона ядра)' % d)
    if budget:
        print('  + бюджет списка скиллов skillListingBudgetFraction = %s' % SKILL_BUDGET)
    if changed and not dry:
        save(sp, s, [], '', False)
    return 0


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser(description='Подключить проект к ядру ones-core')
    ap.add_argument('--project', default=os.getcwd())
    ap.add_argument('--src', help='папка выгрузки конфигурации (src); обязательна, кроме --deny-only')
    ap.add_argument('--platform-bin', help='папка bin платформы 1С, например C:/Program Files/1cv8/8.3.27.2214/bin; обязательна, кроме --deny-only')
    ap.add_argument('--toolkit-port', type=int, default=6003)
    ap.add_argument('--edt-port', type=int)
    ap.add_argument('--plugin-data', help='папка данных плагина (${CLAUDE_PLUGIN_DATA}) — туда кладётся сканер секретов для pre-commit')
    ap.add_argument('--marketplace', default=DEFAULT_REPO, help='репозиторий GitHub owner/name или локальная папка каталога')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--deny-only', action='store_true', help='только запреты и бюджет списка скиллов: дописать недостающие из шаблона и убрать снятые')
    a = ap.parse_args()
    proj = os.path.abspath(a.project)
    dry = a.dry_run
    actions = []
    if a.deny_only:
        return deny_only(proj, dry)
    if not a.src or not a.platform_bin:
        ap.error('нужны --src и --platform-bin (или --deny-only — только запреты)')

    if not os.path.isdir(os.path.join(a.src)):
        print('Нет папки выгрузки: %s' % a.src)
        return 2
    if not os.path.isfile(os.path.join(a.platform_bin, '1cv8.exe')):
        print('В папке платформы нет 1cv8.exe: %s' % a.platform_bin)
        return 2

    # 1. git
    if not os.path.isdir(os.path.join(proj, '.git')):
        actions.append('git init')
        if not dry:
            subprocess.run(['git', '-C', proj, 'init', '-q'], check=True)

    # 2. настройки проекта
    sp = os.path.join(proj, '.claude', 'settings.json')
    s = load(sp)
    before = json.dumps(s, sort_keys=True)
    src = {'source': 'directory', 'path': a.marketplace} if os.path.isdir(a.marketplace) else {'source': 'github', 'repo': a.marketplace}
    s.setdefault('extraKnownMarketplaces', {}).setdefault('ones-core', {'source': src})
    s.setdefault('enabledPlugins', {}).setdefault(PLUGIN_ID, True)
    s.setdefault('skillListingBudgetFraction', SKILL_BUDGET)
    _, retired = merge_deny(s)
    deny = s['permissions']['deny']
    if retired:
        actions.append('сняты устаревшие запреты: %s' % ', '.join(retired))
    allow = s['permissions'].setdefault('allow', [])
    plugin = PLUGIN_ID.split('@')[0]
    for rule in ['mcp__plugin_%s_%s' % (plugin, srv) for srv in READONLY_SERVERS] + [plugin_cache_read_rule()]:
        if rule not in allow:
            allow.append(rule)
    if json.dumps(s, sort_keys=True) != before:
        save(sp, s, actions, '.claude/settings.json: плагин, %d запретов, разрешения на %d читающих серверов плагина и чтение '
             'статей скиллов из кэша плагина, бюджет списка скиллов %s' % (len(deny), len(READONLY_SERVERS),
                                                               s['skillListingBudgetFraction']), dry)

    # 3. переменные проекта (вне git)
    lp = os.path.join(proj, '.claude', 'settings.local.json')
    loc = load(lp)
    before = json.dumps(loc, sort_keys=True)
    env = loc.setdefault('env', {})
    env['ONEC_PROJECT_SRC'] = os.path.abspath(a.src)
    env['ONEC_PLATFORM_BIN'] = os.path.abspath(a.platform_bin)
    env['ONEC_TOOLKIT_PORT'] = str(a.toolkit_port)
    if a.edt_port:
        env['EDT_MCP_PORT'] = str(a.edt_port)
    if json.dumps(loc, sort_keys=True) != before:
        save(lp, loc, actions, '.claude/settings.local.json: переменные проекта', dry)

    # 4. необязательные серверы
    mp = os.path.join(proj, '.mcp.json')
    mcp = load(mp)
    before = json.dumps(mcp, sort_keys=True)
    servers = mcp.setdefault('mcpServers', {})
    # повторный setup с новым портом обновляет url (аудит 30.10.2026: setdefault оставлял старый порт, а переменная менялась)
    for name, port in (('edt-mcp', a.edt_port),):
        if port:
            url = 'http://localhost:%d/mcp' % port
            cur = servers.get(name)
            if not isinstance(cur, dict):
                servers[name] = {'type': 'http', 'url': url}
            elif cur.get('url') != url:
                cur['url'] = url
    if servers and json.dumps(mcp, sort_keys=True) != before:
        save(mp, mcp, actions, '.mcp.json: необязательные серверы (%s)' % ', '.join(servers), dry)
    if '1c-forms' in servers:
        print('  ! в .mcp.json проекта остался свой сервер 1c-forms: теперь он идёт в плагине, запись и копию сервера в проекте можно удалить')

    # 5. .gitignore
    gp = os.path.join(proj, '.gitignore')
    have = open(gp, encoding='utf-8').read().split('\n') if os.path.isfile(gp) else []
    add = [g for g in GITIGNORE if g not in have]
    if add:
        actions.append('.gitignore: +%d строк' % len(add))
        if not dry:
            with open(gp, 'a', encoding='utf-8', newline='\n') as f:
                if have and have[-1] != '':
                    f.write('\n')
                f.write('# ядро ones-core: секреты, локальные настройки, логи, индексы\n' + '\n'.join(add) + '\n')
    # файл, уже закоммиченный до строки в .gitignore, git продолжает вести — сказать, само не убирать (ask-before-changing)
    r = subprocess.run(['git', '-C', proj, 'ls-files', '--error-unmatch', '.claude/settings.local.json'], capture_output=True)
    if r.returncode == 0:
        actions.append('ВНИМАНИЕ: .claude/settings.local.json уже под git — .gitignore его не уберёт, а секрет из env попал бы '
                       'в историю. Снять с учёта (файл останется на диске): git rm --cached .claude/settings.local.json и коммит')

    # 6. журналы проекта
    for name, text in JOURNALS.items():
        p = os.path.join(proj, 'docs-project', name)
        if not os.path.exists(p):
            actions.append('docs-project/%s' % name)
            if not dry:
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with open(p, 'w', encoding='utf-8', newline='\n') as f:
                    f.write(text)

    # 7. проверка секретов перед коммитом
    if a.plugin_data:
        scan_src = os.path.join(os.path.dirname(HERE), 'git', 'secret-scan.py')
        scan_dst = os.path.join(os.path.abspath(a.plugin_data), 'bin', 'secret-scan.py')
        if not os.path.isfile(scan_dst) or open(scan_src, 'rb').read() != open(scan_dst, 'rb').read():
            actions.append('сканер секретов -> %s' % scan_dst)
            if not dry:
                os.makedirs(os.path.dirname(scan_dst), exist_ok=True)
                shutil.copyfile(scan_src, scan_dst)
        hooks_dir = git_hooks_dir(proj)
        hook = os.path.join(hooks_dir, 'pre-commit')
        want = pre_commit_text(scan_dst, sys.executable)
        have_hook = open(hook, encoding='utf-8', errors='replace').read() if os.path.isfile(hook) else None
        if have_hook is not None and HOOK_MARK not in have_hook:
            actions.append('git pre-commit: в проекте уже есть свой хук — не трогаю; проверку секретов добавить в него строкой: '
                           '"%s" "%s" || exit 1' % (sys.executable.replace(chr(92), '/'), scan_dst.replace(chr(92), '/')))
        elif have_hook != want:
            actions.append('git pre-commit: проверка секретов перед коммитом')
            if not dry:
                os.makedirs(hooks_dir, exist_ok=True)
                with open(hook, 'w', encoding='utf-8', newline='\n') as f:
                    f.write(want)

    # 7б. страж правил коммита: строка Co-Authored-By не проходит (work-journals-and-commits п.8)
    cm_src = os.path.join(os.path.dirname(HERE), 'git', 'commit-msg')
    cm_hook = os.path.join(git_hooks_dir(proj), 'commit-msg')
    cm_want = open(cm_src, encoding='utf-8').read()
    cm_have = open(cm_hook, encoding='utf-8', errors='replace').read() if os.path.isfile(cm_hook) else None
    if cm_have is not None and COMMIT_MSG_MARK not in cm_have:
        actions.append('git commit-msg: в проекте уже есть свой хук — не трогаю; строку Co-Authored-By он должен отклонять, '
                       'образец — %s' % cm_src.replace(chr(92), '/'))
    elif cm_have != cm_want:
        actions.append('git commit-msg: строка Co-Authored-By в сообщении коммита не проходит')
        if not dry:
            os.makedirs(os.path.dirname(cm_hook), exist_ok=True)
            with open(cm_hook, 'w', encoding='utf-8', newline='\n') as f:
                f.write(cm_want)
            os.chmod(cm_hook, 0o755)

    # 8. индекс кода: папка индекса проекта, ссылка из выгрузки, выгрузка в списке общего индексатора (ADR-0006)
    if a.plugin_data:
        r = subprocess.run([sys.executable, os.path.join(HERE, 'code-index-daemon.py'), '--plugin-data', a.plugin_data, 'add',
                            '--src', os.path.abspath(a.src), '--project', proj] + (['--dry-run'] if dry else []), capture_output=True)
        out = r.stdout.decode('utf-8', 'replace')
        if r.returncode == 0:
            actions += ['индекс кода: ' + l.strip()[2:] for l in out.splitlines() if l.startswith('  - ')]
        else:
            actions.append('индекс кода не подключён (код %d): %s' % (r.returncode, out.strip()[:300]))

    print(('Что будет сделано' if dry else 'Сделано') + (':' if actions else ': ничего — проект уже подключён'))
    for x in actions:
        print('  - ' + x)
    if not dry and actions:
        print('Дальше: перезапустить Claude Code в папке проекта — плагин подхватится; программы инструментов ставит '
              'install-tools.py (команду покажет сообщение в начале сессии).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
