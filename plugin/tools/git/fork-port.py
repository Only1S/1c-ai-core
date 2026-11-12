"""Взять срез работы из ДРУГОГО форка конфигурации в ТЕКУЩИЙ клон напрямую, минуя долгий путь через ствол.

Безопасно: git fetch + checkout указанных путей из origin/<ветка> — они сразу попадают в индекс
(застейджены), БЕЗ авто-коммита и push. Обязательная сверка после — по правилу partial-branch-port-worktree
(ссылки перенесённых объектов, Configuration.mdo, чекеры). Работает в любом репозитории конфигурации:
в текущей папке или по явному пути --repo; к корню мастера ядра не привязан.

Запуск:
    python fork-port.py --from <форк> --paths <конфиг>/src/CommonModules/<Модуль> [<путь> ...] [--repo <клон>] [--preview]

    --from     ветка-источник в origin (имя форка или ствол) — обязательно
    --paths    пути к объектам или каталогам, можно несколько — обязательно
    --repo     целевой клон (по умолчанию текущая папка «.»)
    --preview  только показать, что придёт (git diff --stat), ничего не менять

Примеры:
    python fork-port.py --repo D:/GIT/<конфиг>-<форк> --from <форк> --paths <конфиг>/src/CommonModules/<Модуль> --preview
    python fork-port.py --from <форк> --paths <конфиг>/src/CommonModules/<ПодсистемаМодуль>

Читает: репозиторий --repo (git fetch из origin). Пишет: рабочее дерево и индекс --repo по путям --paths
(кроме --preview). Ни коммита, ни push.

Коды выхода: 0 — перенесено или показан --preview; 1 — не git-репозиторий, в origin нет ветки,
в целевых путях незакоммиченное, checkout не удался; 2 — ошибка параметров командной строки.
Прогресс и ошибки git идут в stderr как есть и не считаются фатальными: решения — по кодам возврата git.
"""
import argparse
import subprocess
import sys


def utf8_console():
    """Вывод в UTF-8 независимо от кодовой страницы консоли (cp866 портит кириллицу)."""
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError):
            pass


def say(m=''):
    print(m, flush=True)


def git(repo, *args, quiet=False):
    """git -C repo …: stdout забираем текстом, stderr — в консоль как есть (quiet — гасим оба). Возвращает (код, stdout)."""
    try:
        r = subprocess.run(['git', '-C', repo] + list(args), stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL if quiet else None)
    except OSError:
        return 1, ''
    return r.returncode, r.stdout.decode('utf-8', 'replace')


def echo(text):
    """Вывод git построчно, как его печатает конвейер PowerShell."""
    for line in text.splitlines():
        say(line)


def main():
    utf8_console()
    p = argparse.ArgumentParser(description='Взять срез работы из другого форка в текущий клон (fetch + checkout путей, без коммита).')
    p.add_argument('--from', dest='source', required=True, help='ветка-источник в origin (имя форка или ствол)')
    p.add_argument('--paths', nargs='+', required=True, help='пути к объектам/каталогам, можно несколько')
    p.add_argument('--repo', default='.', help='целевой клон (по умолчанию текущая папка)')
    p.add_argument('--preview', action='store_true', help='только показать, что придёт; ничего не менять')
    a = p.parse_args()
    # обязательные параметры не принимают пустую строку — как Mandatory в PowerShell
    if not a.source:
        p.error('--from: пустая строка')
    if any(not x for x in a.paths):
        p.error('--paths: пустая строка')
    repo, src, paths = a.repo, a.source, a.paths

    if git(repo, 'rev-parse', '--git-dir', quiet=True)[0] != 0:
        say('Не git-репозиторий: %s' % repo)
        return 1
    cur = ' '.join(git(repo, 'branch', '--show-current')[1].splitlines())
    say()
    say('Цель:     %s (ветка %s)' % (repo, cur))
    say('Источник: origin/%s' % src)
    say('Пути:     %s' % ', '.join(paths))
    say()

    fcode, fout = git(repo, 'fetch', '--quiet', 'origin', src)
    echo(fout)
    if fcode != 0:
        # без свежего fetch origin/<ветка> — прошлый снимок: перенос взял бы устаревший срез молча (аудит 30.10.2026)
        say("fetch origin %s не удался (код %d) — origin/%s может быть устаревшим; переносить не буду. Проверь сеть и доступ" % (src, fcode, src))
        return 1
    if git(repo, 'rev-parse', '--verify', '--quiet', 'origin/' + src, quiet=True)[0] != 0:
        say("В origin нет ветки '%s'" % src)
        return 1

    if a.preview:
        say('Что придёт (diff origin/%s по путям):' % src)
        # от текущего состояния к источнику: «что придёт», а не обратная разница (замер 29.10.2026, волна 2 п.2.9)
        echo(git(repo, 'diff', '--stat', 'HEAD', 'origin/' + src, '--', *paths)[1])
        say()
        say('Preview — ничего не менял. Убери --preview, чтобы применить.')
        return 0

    dirty = git(repo, 'status', '--porcelain', '--', *paths)[1]
    if dirty.strip():
        say('В целевых путях есть незакоммиченное — сначала закоммить/откати:')
        echo(dirty)
        return 1

    # restore, а не checkout: файл, удалённый в источнике, удаляется и здесь — как его показал --preview (аудит 30.10.2026)
    code, out = git(repo, 'restore', '--source=origin/' + src, '--staged', '--worktree', '--', *paths)
    echo(out)
    if code != 0:
        say('restore из origin/%s не удался' % src)
        return 1
    say('Взято из origin/%s и застейджено. НЕ закоммичено, НЕ запушено.' % src)
    say()
    say('ОБЯЗАТЕЛЬНО дальше (partial-branch-port-worktree):')
    say('  1) граница среза шире, чем кажется — проверь ссылки перенесённых объектов (grep), дотяни зависимости')
    say('  2) сверка Configuration.mdo <-> файлы (объявлен-но-нет-файла / файл-но-не-объявлен)')
    say('  3) revalidate + get_project_errors в EDT, bsl-analyzer (числа совпасть с веткой-источником)')
    say('  4) только потом commit (журнал форка); для метаданных .mdo — штатное объединение, не текст')
    say()
    echo(git(repo, 'status', '--short', '--', *paths)[1])
    return 0


if __name__ == '__main__':
    sys.exit(main())
