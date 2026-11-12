"""project-check.py — проверка проекта 1С средствами плагина ones-core: только чтение, без платформы 1С и без сети.

Зовёт мод «кнопка проверок» (plugin/hooks/project-check.tsx, команда /check) в фоне; годится и для запуска руками:
    python <плагин>/tools/checks/project-check.py [--project <папка>] [--report <файл>] [--json] [--strict]

Что проверяет:
  1. Изменённые модули .bsl (git: рабочее дерево и индекс против HEAD, новые файлы — целиком; служебные зоны guard-skills
     мимо) — те же проверки, что хук validate-bsl.py после правки, по изменённым строкам: ошибки bsl-analyzer, смешение
     алфавитов в именах, бюджет комментариев. Замечания анализатора вне изменённых строк — справкой, на вердикт не влияют.
     Модулей больше MAX_BSL или кончилось время DEADLINE_S — остальные пропускаются с пометкой.
  2. Изменённые проектные доки docs-project/**/*.md — линтер lint-project-docs.py (матрица, ADR, карточки, ссылки).
  3. Подготовленное к коммиту (git add) — проверка секретов secret-scan.py; значение секрета в отчёт не попадает.
  4. Запреты опасных команд в .claude/settings.json проекта против шаблона ядра (project-deny.json).
  5. Программы инструментов ядра в папке данных плагина (bsl-analyzer, code-index и др.).
Уровни: FAIL — ошибка (модуль, секрет, нечитаемые настройки), WARN — замечание, OK, SKIP — не применимо или нечем.
Последняя строка текста — «Итог: …»; с --json за ней ещё строка JSON {"verdict","fail","warn","ok","skip","headline"} для мода.
Пишет: только файл --report (тот же текст, UTF-8, LF). Хуки не взводит: гейт качества и журнал подсказок не трогаются.
Коды выхода: 0 — без --strict всегда; со --strict 1, если есть FAIL.
"""
import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(os.path.dirname(HERE))
MAX_BSL = 20
MAX_DOCS = 30
DEADLINE_S = 480
EXEMPT_FALLBACK = {'.claude', 'docs', 'docs-project', 'tools', 'node_modules', '.git'}
LEVELS = ('FAIL', 'WARN', 'OK', 'SKIP')


def load(name, *parts):
    """Модуль плагина по пути (hooks/validate-bsl.py и др.); нет файла или не грузится — None."""
    path = os.path.join(PLUGIN, *parts)
    if not os.path.isfile(path):
        return None
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def git(root, *args):
    try:
        r = subprocess.run(['git', '--no-optional-locks', '-C', root, '-c', 'core.quotePath=false', *args], capture_output=True)
    except OSError:
        return 127, ''
    return r.returncode, r.stdout.decode('utf-8', 'replace')


def changed_files(root):
    """Изменённые и новые файлы рабочего дерева и индекса: [(путь от корня, новый ли)]; не git — None. Удалённые — мимо."""
    rc, out = git(root, 'status', '--porcelain=v1', '-z', '--untracked-files=all')
    if rc != 0:
        return None
    items, res, i = out.split('\0'), [], 0
    while i < len(items):
        entry = items[i]
        i += 1
        if len(entry) < 4:
            continue
        st, path = entry[:2], entry[3:]
        if 'R' in st or 'C' in st:
            i += 1   # в -z за новым именем идёт прежнее
        if 'D' in st:
            continue
        res.append((path.replace('\\', '/'), st == '??'))
    return res


def added_lines(root, rel, untracked):
    """Номера строк, добавленных против HEAD; новый файл (или нет HEAD) — None, то есть весь файл."""
    if untracked:
        return None
    rc, out = git(root, 'diff', '-U0', '--no-color', '--no-ext-diff', 'HEAD', '--', rel)
    if rc != 0:
        return None
    lines = set()
    for mm in re.finditer(r'^@@ -\S+ \+(\d+)(?:,(\d+))? @@', out, re.M):
        start, n = int(mm.group(1)), int(mm.group(2) if mm.group(2) is not None else 1)
        lines.update(range(start, start + n))
    return lines


def removed_lines(root, rel):
    """Строки, снятые против HEAD, с приставкой «-»: комментарий, стоявший в строке до правки, — не новая запись."""
    rc, out = git(root, 'diff', '-U0', '--no-color', '--no-ext-diff', 'HEAD', '--', rel)
    return [x for x in out.split('\n') if x.startswith('-') and not x.startswith('---')] if rc == 0 else []


def hook_input(lines, removed=()):
    """Вход validate-bsl.py, как после правки: строки изменений — кусками structuredPatch, новый файл — create."""
    if lines is None:
        return {'tool_response': {'type': 'create'}}
    return {'tool_response': {'structuredPatch': [{'newStart': n, 'lines': ['+']} for n in sorted(lines)] +
                              [{'newStart': 1, 'lines': list(removed)}]}}


class Report:
    def __init__(self):
        self.rows = []

    def add(self, level, check, text):
        self.rows.append((level, check, text))

    def count(self, level):
        return sum(1 for r in self.rows if r[0] == level)

    def verdict(self):
        return 'fail' if self.count('FAIL') else 'warn' if self.count('WARN') else 'ok'

    def headline(self):
        fails = [r for r in self.rows if r[0] == 'FAIL']
        warns = [r for r in self.rows if r[0] == 'WARN']
        if not fails and not warns:
            return 'проверок %d, пропущено %d' % (self.count('OK'), self.count('SKIP'))
        first = (fails or warns)[0]
        return 'ошибок %d, замечаний %d; первое — %s: %s' % (len(fails), len(warns), first[1], first[2][:120])


def check_bsl(root, files, rep, vb, exempt):
    bsl = [(p, u) for p, u in files if p.lower().endswith('.bsl') and p.split('/', 1)[0].lower() not in exempt]
    if not bsl:
        rep.add('SKIP', 'модули .bsl', 'изменённых модулей нет')
        return
    if vb is None:
        rep.add('FAIL', 'модули .bsl', 'нет hooks/validate-bsl.py плагина — модули не проверены')
        return
    exe = vb.analyzer_path(root)
    have = os.path.isfile(exe)
    if not have:
        rep.add('WARN', 'модули .bsl', 'bsl-analyzer не установлен — синтаксис не проверен (/ones-core:setup ставит программы)')
    deadline = time.time() + DEADLINE_S
    clean, old_total = 0, 0
    for k, (rel, untracked) in enumerate(bsl):
        if k >= MAX_BSL or time.time() > deadline:
            rep.add('SKIP', 'модули .bsl', 'не проверены %d из %d модулей: лимит %d модулей или %d с' % (len(bsl) - k, len(bsl), MAX_BSL, DEADLINE_S))
            break
        f = os.path.join(root, rel)
        mine = added_lines(root, rel, untracked)
        if mine is not None and not mine:
            continue   # только удалённые строки — нечего судить
        ours = (lambda n: True) if mine is None else (lambda n: n in mine)
        found = []
        if have:
            errs = vb.run_analyzer(exe, f)
            if errs is None:
                rep.add('WARN', 'модули .bsl', '%s — bsl-analyzer не дал отчёта (сбой или таймаут)' % rel)
            else:
                new = [e for e in errs if ours(vb.error_line(e))]
                old_total += len(errs) - len(new)
                if new:
                    found.append('bsl-analyzer: %d ошибок (%s)' % (len(new), ', '.join(dict.fromkeys(str(e.get('ruleId')) for e in new))))
        mix = [name for line, name in vb.mixed_identifiers(f) if ours(line)]
        if mix:
            found.append('смешение алфавитов в именах (%d): %s' % (len(mix), ', '.join(mix[:3])))
        budget = vb.comment_budget(hook_input(mine, removed_lines(root, rel)), f)
        if budget:
            found.append('бюджет комментариев (%d): %s' % (len(budget), '; '.join(budget[:3])))
        if found:
            rep.add('FAIL', 'модули .bsl', '%s — %s' % (rel, ' · '.join(found)))
        else:
            clean += 1
    if clean:
        rep.add('OK', 'модули .bsl', 'чисто в изменённых строках: %d из %d' % (clean, len(bsl)) +
                ('; прежних ошибок анализатора вне изменений — %d (справкой)' % old_total if old_total else ''))
    for note in getattr(vb, 'SYSTEM', []) or []:
        rep.add('WARN', 'модули .bsl', note)


def check_docs(root, files, rep):
    docs = [p for p, _ in files if p.lower().startswith('docs-project/') and p.lower().endswith('.md')]
    if not docs:
        rep.add('SKIP', 'проектные доки', 'изменённых доков docs-project/ нет')
        return
    lp = load('ones_lint_project_docs', 'hooks', 'lint-project-docs.py')
    if lp is None:
        rep.add('WARN', 'проектные доки', 'нет hooks/lint-project-docs.py плагина — доки не проверены')
        return
    bad = 0
    for rel in docs[:MAX_DOCS]:
        path = os.path.join(root, rel)
        try:
            with open(path, encoding='utf-8-sig', errors='replace') as fh:
                body = fh.read().replace('\r\n', '\n')
            issues, _ = lp.lint(path, body, {}, root)
        except Exception as e:
            rep.add('WARN', 'проектные доки', '%s — линтер не отработал: %s' % (rel, e))
            continue
        if issues:
            bad += 1
            rep.add('WARN', 'проектные доки', '%s — %s' % (rel, '; '.join(issues[:3])))
    if not bad:
        rep.add('OK', 'проектные доки', 'замечаний нет: %d док(ов)' % min(len(docs), MAX_DOCS))


def check_secrets(root, rep):
    rc, staged = git(root, 'diff', '--cached', '--name-only')
    if rc != 0 or not staged.strip():
        rep.add('SKIP', 'секреты', 'к коммиту ничего не подготовлено (git add)')
        return
    scan = os.path.join(PLUGIN, 'tools', 'git', 'secret-scan.py')
    if not os.path.isfile(scan):
        rep.add('WARN', 'секреты', 'нет tools/git/secret-scan.py плагина — подготовленное не проверено')
        return
    try:
        r = subprocess.run([sys.executable, '-I', scan], cwd=root, capture_output=True, timeout=120,
                           env=dict(os.environ, PYTHONIOENCODING='utf-8'))
        out = (r.stdout + r.stderr).decode('utf-8', 'replace')
    except (OSError, subprocess.TimeoutExpired) as e:
        rep.add('WARN', 'секреты', 'проверка секретов не отработала: %s' % e)
        return
    if r.returncode == 1:
        lines = [x.strip() for x in out.splitlines() if x.strip()][:6]
        rep.add('FAIL', 'секреты', 'в подготовленном к коммиту найден секрет — %s' % ' | '.join(lines))
    else:
        rep.add('OK', 'секреты', 'в подготовленном к коммиту секретов нет')


def check_deny(root, rep):
    sp = os.path.join(root, '.claude', 'settings.json')
    if not os.path.isfile(sp):
        rep.add('WARN', 'запреты проекта', 'нет .claude/settings.json — проект не подключён: /ones-core:setup')
        return
    cp = load('ones_connect_project', 'tools', 'setup', 'connect-project.py')
    if cp is None:
        rep.add('WARN', 'запреты проекта', 'нет tools/setup/connect-project.py плагина — запреты не сверены')
        return
    try:
        added, retired = cp.merge_deny(cp.load(sp))
    except (OSError, ValueError, AttributeError) as e:
        rep.add('FAIL', 'запреты проекта', '.claude/settings.json не разбирается: %s' % e)
        return
    if added or retired:
        rep.add('WARN', 'запреты проекта', 'отстают от шаблона ядра: недостаёт %d, снятых %d — /ones-core:setup допишет' % (len(added), len(retired)))
    else:
        rep.add('OK', 'запреты проекта', 'совпадают с шаблоном ядра')


def check_tools(rep, vb):
    it = load('ones_install_tools', 'tools', 'setup', 'install-tools.py')
    if it is None:
        rep.add('WARN', 'программы ядра', 'нет tools/setup/install-tools.py плагина — не сверены')
        return
    data = vb.plugin_data() if vb is not None else (os.environ.get('CLAUDE_PLUGIN_DATA') or
                                                    os.path.join(os.path.expanduser('~'), '.claude', 'plugins', 'data', 'ones-core-ones-core'))
    dest = os.path.join(data, 'bin')
    try:
        with open(it.MANIFEST, encoding='utf-8') as fh:
            tools = [t for t in json.load(fh)['tools'] if not t.get('optional')]
        state = it.load_state(dest) if os.path.isdir(dest) else {}
        missing = [t['name'] for t in tools if not (os.path.isdir(dest) and it.is_installed(t, dest, state))]
    except (OSError, ValueError, KeyError) as e:
        rep.add('WARN', 'программы ядра', 'состояние не прочитано: %s' % e)
        return
    if missing:
        rep.add('WARN', 'программы ядра', 'не установлены: %s — /ones-core:setup поставит' % ', '.join(missing))
    else:
        rep.add('OK', 'программы ядра', 'на месте: %d' % len(tools))


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser(description='Проверка проекта 1С средствами плагина ones-core (только чтение)')
    ap.add_argument('--project', default=os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd())
    ap.add_argument('--report', help='куда записать текст отчёта')
    ap.add_argument('--json', action='store_true', help='последней строкой — JSON с вердиктом')
    ap.add_argument('--strict', action='store_true', help='код выхода 1, если есть FAIL')
    a = ap.parse_args()
    root = os.path.abspath(a.project)
    rep = Report()
    vb = load('ones_validate_bsl', 'hooks', 'validate-bsl.py')
    gs = load('ones_guard_skills', 'hooks', 'guard-skills.py')
    exempt = {z.lower() for z in (getattr(gs, 'EXEMPT', None) or EXEMPT_FALLBACK)}
    files = changed_files(root)
    if files is None:
        for check in ('модули .bsl', 'проектные доки', 'секреты'):
            rep.add('SKIP', check, 'папка не репозиторий git — изменений не видно')
    else:
        check_bsl(root, files, rep, vb, exempt)
        check_docs(root, files, rep)
        check_secrets(root, rep)
    check_deny(root, rep)
    check_tools(rep, vb)

    lines = ['== Проверка проекта: %s ==' % root]
    order = {lv: i for i, lv in enumerate(LEVELS)}
    lines += ['[%s] %s: %s' % (' OK ' if lv == 'OK' else lv, check, text) for lv, check, text in sorted(rep.rows, key=lambda r: order[r[0]])]
    lines.append('Итог: ошибок %d, замечаний %d, чисто %d, пропущено %d' % tuple(rep.count(lv) for lv in LEVELS))
    text = '\n'.join(lines) + '\n'
    if a.report:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(a.report)), exist_ok=True)
            with open(a.report, 'w', encoding='utf-8', newline='\n') as fh:
                fh.write(text)
        except OSError as e:
            text += 'отчёт не записан (%s): %s\n' % (a.report, e)
    sys.stdout.write(text)
    if a.json:
        sys.stdout.write(json.dumps({'verdict': rep.verdict(), 'fail': rep.count('FAIL'), 'warn': rep.count('WARN'),
                                     'ok': rep.count('OK'), 'skip': rep.count('SKIP'), 'headline': rep.headline()},
                                    ensure_ascii=False) + '\n')
    return 1 if a.strict and rep.count('FAIL') else 0


if __name__ == '__main__':
    sys.exit(main())
