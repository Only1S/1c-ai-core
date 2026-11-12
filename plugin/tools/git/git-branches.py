r"""Обзор веток монорепо конфигурации: где стоит каждая ветка хаба и каждый клон-форк.

Отвечает на вопрос «как идут ветки»: ветки хаба, их положение относительно main, таблица
«клон -> ветка -> впереди/позади» и граф. Config-agnostic: хаб — origin опорного клона, клоны —
соседние папки с тем же origin; пути не захардкожены. Едет в плагин, поэтому tools/lib не подключает.
Перевод tools/git/git-branches.ps1 (поведение и тексты 1:1).

Запуск:
    python git-branches.py                       — из корня любого клона: соседи ищутся автоматически
    python git-branches.py --repo D:\GIT\<конфиг>-<форк>
    python git-branches.py --no-fetch            — без обращения к хабу (быстро, данные могут устареть)
    python git-branches.py --depth 30            — глубина графа (по умолчанию 20)
    python git-branches.py --gui                 — открыть графический просмотрщик gitk (мышью, с историей)

Опорный репозиторий: --repo, иначе текущая папка (если это корень клона), иначе корень рабочего
дерева над ONEC_PROJECT_SRC (переменная манифеста проекта).
Читает: опорный клон и соседние папки (родитель опорного и родитель клона из ONEC_PROJECT_SRC).
Пишет: только ссылки origin/* опорного клона (git fetch origin --prune, если нет --no-fetch); --gui запускает gitk.
Коды выхода: 0 — обзор выведен; 1 — git-репозиторий не найден, у него нет remote origin или gitk не запустился;
2 — ошибка параметров командной строки. Прогресс и ошибки git идут в stderr как есть.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

FILE_ATTRIBUTE_HIDDEN = 0x2
FILE_ATTRIBUTE_DIRECTORY = 0x10
EOL = re.compile(r'\r\n|\r|\n')
DRIVE_ROOT = re.compile(r'^[A-Za-z]:\\?$')
UNC_SHARE = re.compile(r'^\\\\[^\\]+\\[^\\]+$')


def git_out(d, args):
    """Строки вывода git; None — git не запустился или вернул ненулевой код.
    stderr не перехватывается: прогресс и ошибки git идут прямо в консоль, как в прежней версии."""
    try:
        r = subprocess.run(['git', '-C', d] + list(args), stdout=subprocess.PIPE)
    except OSError:
        return None
    if r.returncode != 0:
        return None
    lines = EOL.split(r.stdout.decode('utf-8', 'replace'))
    if lines and lines[-1] == '':
        lines.pop()
    return lines


def one(lines):
    """Значение вывода как скаляр: нет строк — None, одна — она сама, несколько — через пробел."""
    if not lines:
        return None
    return lines[0] if len(lines) == 1 else ' '.join(lines)


def truthy(lines):
    """Истинность вывода по правилам PowerShell: одна строка — по её непустоте, несколько — истина."""
    if not lines:
        return False
    return bool(lines[0]) if len(lines) == 1 else True


def s(v):
    return '' if v is None else v


def u16len(t):
    # ширина и обрезка — в единицах UTF-16, как у строк .NET
    return len(t.encode('utf-16-le', 'surrogatepass')) // 2


def u16cut(t, n):
    return t.encode('utf-16-le', 'surrogatepass')[:2 * n].decode('utf-16-le', 'replace')


def pad(t, w):
    t = s(t)
    return t + ' ' * max(0, w - u16len(t))


def split_parent(p):
    """Родитель пути по правилам Split-Path -Parent: слеши -> «\\», у корня диска и UNC-ресурса родителя нет ('')."""
    t = p.replace('/', '\\')
    while len(t) > 1 and t.endswith('\\') and not DRIVE_ROOT.match(t):
        t = t[:-1]
    if DRIVE_ROOT.match(t) or UNC_SHARE.match(t):
        return ''
    i = t.rfind('\\')
    if i < 0:
        return ''
    parent = t[:i]
    if re.match(r'^[A-Za-z]:$', parent):
        return parent + '\\'
    return parent or '\\'


def is_git_repo(d):
    if not os.path.exists(os.path.join(d, '.git')):
        return False
    # хоть одна строка вывода (как «$null -ne» у прежней версии)
    return bool(git_out(d, ['rev-parse', '--git-dir']))


def work_tree_root(probe):
    """Подняться от пути (src внутри проекта) до корня рабочего дерева; '' — не нашлось."""
    while probe and not is_git_repo(probe):
        probe = split_parent(probe)
    return probe


def unique(items):
    # порядок первого вхождения, с учётом регистра (как Select-Object -Unique)
    out = []
    for x in items:
        if x not in out:
            out.append(x)
    return out


def list_dirs(root):
    """Подпапки в порядке файловой системы; скрытые пропускаются (Get-ChildItem без -Force)."""
    try:
        with os.scandir(root) as it:
            entries = list(it)
    except OSError:
        return []
    res = []
    for e in entries:
        try:
            st = e.stat(follow_symlinks=False)
        except OSError:
            continue
        attrs = getattr(st, 'st_file_attributes', None)
        if attrs is None:
            if not e.is_dir() or e.name.startswith('.'):
                continue
        elif not attrs & FILE_ATTRIBUTE_DIRECTORY or attrs & FILE_ATTRIBUTE_HIDDEN:
            continue
        res.append(os.path.abspath(os.path.join(root, e.name)))
    return res


def strip_origin(ref):
    return re.sub(r'^origin/', '', ref, flags=re.I)


def is_origin_head(ref):
    return ref.lower() in ('origin/head', 'origin')


def start_gitk(exe, cwd):
    if hasattr(os, 'startfile'):
        os.startfile(exe, 'open', '--all', cwd)
    else:
        subprocess.Popen([exe, '--all'], cwd=cwd, start_new_session=True)


def main():
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description='Обзор веток монорепо конфигурации: хаб, ветки, клоны, граф.')
    ap.add_argument('--repo', help='опорный клон (по умолчанию — текущая папка или ONEC_PROJECT_SRC)')
    ap.add_argument('--no-fetch', action='store_true', help='не обращаться к хабу (быстро, данные могут устареть)')
    ap.add_argument('--gui', action='store_true', help='открыть графический просмотрщик gitk')
    ap.add_argument('--depth', type=int, default=20, help='глубина графа (по умолчанию 20)')
    a = ap.parse_args()
    env_src = os.environ.get('ONEC_PROJECT_SRC')

    # 1. Опорный репозиторий: параметр -> текущая папка -> манифест (ONEC_PROJECT_SRC)
    repo = a.repo
    if not repo:
        cand = os.getcwd()
        if is_git_repo(cand):
            repo = cand
        elif env_src:
            repo = work_tree_root(env_src)
    if not repo or not is_git_repo(repo):
        print('Не найден git-репозиторий. Укажите: git-branches.py --repo <путь к клону>')
        return 1

    # 2. Хаб — из origin опорного клона
    hub = git_out(repo, ['remote', 'get-url', 'origin'])
    if not truthy(hub):
        print("У репозитория %s нет remote 'origin' — обзор веток хаба невозможен." % repo)
        return 1
    hub = one(hub).strip()

    print('')
    print('=== Хаб: ' + hub)
    if not a.no_fetch:
        print('    (fetch...)')
        git_out(repo, ['fetch', 'origin', '--prune', '--quiet'])

    # 3. Клоны: соседи опорного + клон из манифеста; отбор по совпадению origin (без учёта регистра).
    # Родитель берётся от полного пути: у «--repo .» прежняя версия получала пустой путь и падала.
    roots = [split_parent(os.path.abspath(repo))]
    if env_src:
        probe = work_tree_root(env_src)
        if probe:
            roots.append(split_parent(os.path.abspath(probe)))
    clones = []
    for root in unique(roots):
        # у корня диска родителя нет — соседей не ищем
        if not root or not os.path.exists(root):
            continue
        for d in list_dirs(root):
            if not is_git_repo(d):
                continue
            origin = one(git_out(d, ['remote', 'get-url', 'origin']))
            if origin and origin.strip().lower() == hub.lower():
                clones.append(d)
    clones = unique(clones)

    # 4. Ветки хаба
    print('')
    print('=== Ветки в хабе:')
    refs = git_out(repo, ['for-each-ref', '--sort=-committerdate',
                          '--format=%(refname:short)|%(objectname:short)|%(committerdate:short)|%(contents:subject)',
                          'refs/remotes/origin']) or []
    for line in refs:
        p = line.split('|', 3)
        if is_origin_head(p[0]):
            continue
        subj = p[3] if len(p) >= 4 else ''
        if u16len(subj) > 48:
            subj = u16cut(subj, 48) + '...'
        print('  %s %s %s  %s' % (pad(strip_origin(p[0]), 10), pad(p[1] if len(p) > 1 else '', 9),
                                  p[2] if len(p) > 2 else '', subj))

    # 5. Кто относительно main
    main_ref = 'origin/main'
    if not truthy(git_out(repo, ['rev-parse', '--verify', main_ref])):
        main_ref = None
    if main_ref:
        print('')
        print('=== Ветки относительно main:')
        for line in refs:
            ref = line.split('|', 1)[0]
            if is_origin_head(ref) or ref.lower() == main_ref:
                continue
            ahead = one(git_out(repo, ['rev-list', '--count', '%s..%s' % (main_ref, ref)]))
            behind = one(git_out(repo, ['rev-list', '--count', '%s..%s' % (ref, main_ref)]))
            if ahead == '0' and behind == '0':
                state = 'совпадает с main'
            elif behind == '0':
                state = 'впереди main на %s' % s(ahead)
            elif ahead == '0':
                state = 'позади main на %s — нужно подтянуть main' % s(behind)
            else:
                state = 'разошлась: своих %s, не хватает %s' % (s(ahead), s(behind))
            print('  %s %s' % (pad(strip_origin(ref), 10), state))

    # 6. Клоны
    print('')
    print('=== Клоны (рабочие деревья):')
    for clone in clones:
        branch = one(git_out(clone, ['rev-parse', '--abbrev-ref', 'HEAD']))
        head = one(git_out(clone, ['log', '-1', '--format=%h']))
        dirty = git_out(clone, ['status', '--porcelain', '--untracked-files=no'])
        dirty_mark = 'есть НЕЗАФИКСИРОВАННЫЕ правки' if truthy(dirty) else 'чисто'
        upstream = one(git_out(clone, ['rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{upstream}']))
        sync = 'upstream не задан'
        if upstream:
            ahead = one(git_out(clone, ['rev-list', '--count', '%s..HEAD' % upstream]))
            behind = one(git_out(clone, ['rev-list', '--count', 'HEAD..%s' % upstream]))
            if ahead == '0' and behind == '0':
                sync = 'синхронен с хабом'
            elif behind == '0':
                sync = 'НЕ ЗАПУШЕНО: %s' % s(ahead)
            elif ahead == '0':
                sync = 'отстаёт от хаба на %s' % s(behind)
            else:
                sync = 'разошёлся: свои %s, не забрано %s' % (s(ahead), s(behind))
        print('  %s %s %s %s; %s' % (pad(os.path.basename(clone), 24), pad(branch, 8), pad(head, 9), sync, dirty_mark))

    # 7. Граф
    print('')
    print('=== Граф (главные точки: где стоят ветки):')
    graph = git_out(repo, ['log', '--graph', '--oneline', '--decorate', '--simplify-by-decoration',
                           '--all', '-%d' % a.depth]) or []
    for line in graph:
        print('  ' + (u16cut(line, 100) if u16len(line) > 100 else line))
    print('')
    print('Подсказка: линейная история = ветка вливалась fast-forward (отдельной линии не будет).')

    # 8. Графический просмотрщик по запросу
    if a.gui:
        gitk = shutil.which('gitk')
        if not gitk:
            # gitk идёт в составе Git for Windows, но не всегда попадает в PATH
            git_exe = shutil.which('git')
            if git_exe:
                guess = os.path.join(os.path.dirname(os.path.dirname(git_exe)), 'mingw64', 'bin', 'gitk')
                if os.path.exists(guess):
                    gitk = guess
        if gitk:
            print('Открываю gitk --all (граф всех веток)...')
            try:
                start_gitk(gitk, repo)
            except OSError as e:
                print('gitk не запустился: %s' % e)
                return 1
        else:
            print('gitk не найден. Он входит в Git for Windows; иначе смотрите граф в EDT: Team -> Show in History.')
    else:
        print('Графически: git-branches.py --gui  (откроет gitk)  |  в EDT: Team -> Show in History')
    print('')
    return 0


if __name__ == '__main__':
    sys.exit(main())
