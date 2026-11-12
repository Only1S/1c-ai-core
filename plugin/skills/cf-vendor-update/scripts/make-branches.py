"""Три ветки репозитория слияния из XML-выгрузок: vendor-<старый>, vendor-<новый> и custom (обе — потомки старого релиза).

Использование:
  python make-branches.py --repo <каталог репозитория слияния> --old-xml <выгрузка старого релиза>
                          --new-xml <выгрузка нового релиза> --custom-xml <выгрузка текущей конфигурации> [--force]

Выгрузки коммитятся без checkout (временный индекс + commit-tree): каталоги-источники не меняются. ConfigDumpInfo.xml в
ветки не идёт — он свой у каждой выгрузки и дал бы ложный конфликт. Проверки до коммита: версия поставщика текущей
конфигурации = версии старого релиза, формат выгрузки у всех трёх один (--force — продолжить при расхождении).
Коды: 0 — ветки готовы, 1 — ошибка git, 2 — неверные аргументы или проверка не прошла.
"""
import argparse
import os
import sys
import tempfile

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from release_xml import dump_info, git  # noqa: E402

GITATTR = b'* -text\n'


def commit_dir(repo, src, parent, message):
    """Коммит дерева каталога src без checkout; .gitattributes кладётся в индекс отдельно (каталог не трогаем)."""
    idx = os.path.join(tempfile.mkdtemp(prefix='vu-idx-'), 'index')
    env = {'GIT_INDEX_FILE': idx}
    git(repo, '--work-tree=' + src, 'add', '-A', '--', '.', ':(exclude)ConfigDumpInfo.xml', env=env)
    p = os.path.join(os.path.dirname(idx), 'gitattributes')
    open(p, 'wb').write(GITATTR)
    blob = git(repo, 'hash-object', '-w', p).strip()
    git(repo, 'update-index', '--add', '--cacheinfo', '100644,%s,.gitattributes' % blob, env=env)
    tree = git(repo, 'write-tree', env=env).strip()
    args = ['commit-tree', tree, '-m', message] + (['-p', parent] if parent else [])
    return git(repo, *args).strip()


def main():
    ap = argparse.ArgumentParser(description='Ветки репозитория слияния из трёх XML-выгрузок')
    ap.add_argument('--repo', required=True)
    ap.add_argument('--old-xml', required=True)
    ap.add_argument('--new-xml', required=True)
    ap.add_argument('--custom-xml', required=True)
    ap.add_argument('--force', action='store_true', help='продолжить при расхождении версий или формата')
    a = ap.parse_args()
    dirs = {'old': os.path.abspath(a.old_xml), 'new': os.path.abspath(a.new_xml), 'custom': os.path.abspath(a.custom_xml)}
    info = {}
    for k, d in dirs.items():
        info[k] = dump_info(d)
        if not info[k]:
            print('нет Configuration.xml в выгрузке %s: %s' % (k, d))
            return 2
        print('%-6s %s %s, формат %s — %s' % (k, info[k]['name'], info[k]['version'], info[k]['format'], d))
    problems = []
    if info['custom']['version'] != info['old']['version']:
        problems.append('версия текущей конфигурации %s ≠ старому релизу %s: общий предок выбран неверно' % (
            info['custom']['version'], info['old']['version']))
    if len({i['format'] for i in info.values()}) > 1:
        problems.append('формат выгрузки разный (%s): отличия засорятся служебными — выгрузите одной платформой' % (
            ', '.join('%s=%s' % (k, i['format']) for k, i in info.items())))
    for p in problems:
        print('ПРОВЕРКА: ' + p)
    if problems and not a.force:
        return 2
    repo = os.path.abspath(a.repo)
    if not os.path.isdir(os.path.join(repo, '.git')):
        os.makedirs(repo, exist_ok=True)
        git(repo, 'init', '-q')
    for k, v in (('core.autocrlf', 'false'), ('core.longpaths', 'true'), ('core.quotepath', 'off')):
        git(repo, 'config', k, v)
    old_b, new_b = 'vendor-' + info['old']['version'], 'vendor-' + info['new']['version']
    try:
        c_old = commit_dir(repo, dirs['old'], None, 'старый релиз %s' % info['old']['version'])
        git(repo, 'update-ref', 'refs/heads/' + old_b, c_old)
        c_new = commit_dir(repo, dirs['new'], c_old, 'новый релиз %s' % info['new']['version'])
        git(repo, 'update-ref', 'refs/heads/' + new_b, c_new)
        c_cus = commit_dir(repo, dirs['custom'], c_old, 'текущая конфигурация (доработки на %s)' % info['old']['version'])
        git(repo, 'update-ref', 'refs/heads/custom', c_cus)
    except RuntimeError as e:
        print(e)
        return 1
    for b in (old_b, new_b, 'custom'):
        n = len(git(repo, 'ls-tree', '-r', '--name-only', b).splitlines())
        print('ветка %-22s файлов %d' % (b, n))
    print('общий предок custom и %s: %s' % (new_b, git(repo, 'merge-base', 'custom', new_b).strip()[:10]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
