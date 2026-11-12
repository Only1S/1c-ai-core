"""Слияние нового релиза в ветку custom и отчёт о конфликтах по классам — без автоматического разрешения.

Использование:
  python merge-release.py --repo <репозиторий слияния> [--new <ветка нового релиза>] [--report <каталог отчёта>]

Ветка custom выкладывается в рабочий каталог репозитория, затем git merge --no-commit -X no-renames (детектор переименований
склеивает похожие XML разных объектов). Слияние остаётся незавершённым: разрешение — следующий шаг скилла. Отчёт:
merge-report.json (каждый путь с классом, видом артефакта и признаками) и merge-report.md (сводка). Коды: 0 — слияние
выполнено (конфликты в отчёте), 1 — ошибка git, 2 — неверные аргументы.

Классы:
  оба изменили              — файл менялся и у нас, и у поставщика
  поставщик удалил          — у поставщика файла нет, у нас он изменён (признак «шум»: наше отличие от старого релиза — шум выгрузки)
  у нас удалено             — мы удалили, поставщик изменил
  двойник                   — объект с одним именем добавлен с обеих сторон, uuid разные (данные заказчика под угрозой)
  добавлено с обеих сторон  — то же, uuid совпадает или это не объект верхнего уровня
  сирота                    — наш файл внутри объекта, которого после слияния нет (поставщик удалил объект целиком;
                              признак «шум» у модуля: модуль пустой)
  слито автоматически       — файл менялся с обеих сторон, git склеил без конфликта (не конфликт, но просмотреть: смысл мог разойтись)
"""
import argparse
import collections
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from release_xml import artifact_kind, git, index_blobs, is_empty_module, is_noise, object_of, object_uuid  # noqa: E402


def stage_blob(repo, stage, path):
    try:
        return git(repo, 'show', ':%d:%s' % (stage, path), raw=True)
    except RuntimeError:
        return None


def rev_blob(repo, rev, path):
    try:
        return git(repo, 'show', '%s:%s' % (rev, path), raw=True)
    except RuntimeError:
        return None


def main():
    ap = argparse.ArgumentParser(description='Слияние нового релиза в custom и отчёт о конфликтах')
    ap.add_argument('--repo', required=True)
    ap.add_argument('--new', help='ветка нового релиза (по умолчанию — единственная vendor-*, не предок custom)')
    ap.add_argument('--report', help='каталог отчёта (по умолчанию — рядом с репозиторием)')
    a = ap.parse_args()
    repo = os.path.abspath(a.repo)
    if not os.path.isdir(os.path.join(repo, '.git')):
        print('не репозиторий слияния: %s (сначала make-branches.py)' % repo)
        return 2
    branches = [b.strip() for b in git(repo, 'for-each-ref', '--format=%(refname:short)', 'refs/heads/vendor-*').splitlines() if b.strip()]
    base = git(repo, 'merge-base', 'custom', branches[0] if branches else 'custom').strip() if branches else ''
    new = a.new or next((b for b in branches if git(repo, 'rev-parse', b).strip() != base), None)
    old = next((b for b in branches if git(repo, 'rev-parse', b).strip() == base), None)
    if not new or not old:
        print('не найдены ветки старого и нового релиза (vendor-*): %s' % ', '.join(branches))
        return 2
    if os.path.isfile(os.path.join(repo, '.git', 'MERGE_HEAD')):
        print('слияние уже идёт в %s — разрешите его или git merge --abort' % repo)
        return 2
    report = os.path.abspath(a.report or repo.rstrip(os.sep) + '-report')
    os.makedirs(report, exist_ok=True)
    try:
        git(repo, 'checkout', '-q', '-f', 'custom')
        git(repo, 'merge', '--no-commit', '--no-ff', '-X', 'no-renames', new, check=False)
    except RuntimeError as e:
        print(e)
        return 1
    stages = collections.defaultdict(set)
    for line in git(repo, 'ls-files', '-u', '-z').split('\0'):
        if not line.strip():
            continue
        meta, path = line.split('\t', 1)
        stages[path].add(int(meta.split()[2]))
    rows = []
    for path, st in sorted(stages.items()):
        row = {'path': path, 'kind': artifact_kind(path)}
        if st == {1, 2, 3}:
            row['class'] = 'оба изменили'
        elif st == {1, 2}:
            row['class'] = 'поставщик удалил'
            row['noise'] = is_noise(stage_blob(repo, 1, path), stage_blob(repo, 2, path))
        elif st == {1, 3}:
            row['class'] = 'у нас удалено'
        elif st == {2, 3}:
            u_ours, u_theirs = object_uuid(stage_blob(repo, 2, path)), object_uuid(stage_blob(repo, 3, path))
            row['class'] = 'двойник' if (row['kind'] == 'объект' and u_ours and u_theirs and u_ours != u_theirs) else 'добавлено с обеих сторон'
            row['uuid'] = {'ours': u_ours, 'theirs': u_theirs}
        else:
            row['class'] = 'прочее'
        rows.append(row)
    # слито автоматически: файл менялся с обеих сторон, git склеил без конфликта — смысловой конфликт возможен, нужен просмотр;
    # blob — хеш склейки: по нему resolve-merge отличает нетронутый файл от ручного решения
    ours_changed = set(git(repo, 'diff', '--name-only', '-z', '--diff-filter=M', old, 'custom').split('\0')) - {''}
    theirs_changed = set(git(repo, 'diff', '--name-only', '-z', '--diff-filter=M', old, new).split('\0')) - {''}
    blobs = index_blobs(repo)
    for path in sorted((ours_changed & theirs_changed) - set(stages)):
        rows.append({'path': path, 'kind': artifact_kind(path), 'class': 'слито автоматически', 'blob': blobs.get(path)})
    # сироты: наш файл внутри объекта, чьего XML после слияния нет ни в индексе, ни среди конфликтов
    index = set(p for p in git(repo, 'ls-files', '-z').split('\0') if p)
    ours_only = set(git(repo, 'diff', '--name-only', '-z', '--diff-filter=A', old, 'custom').split('\0')) - {''}
    for path in sorted(ours_only):
        obj = object_of(path)
        if not obj or path.endswith('.xml') and path.count('/') == 1:
            continue
        if obj + '.xml' not in index and path in index and obj + '.xml' not in stages:
            row = {'path': path, 'kind': artifact_kind(path), 'class': 'сирота', 'object': obj}
            if path.endswith('.bsl'):
                row['noise'] = is_empty_module(rev_blob(repo, 'custom', path))
            rows.append(row)
    by_class = collections.Counter(r['class'] for r in rows)
    by_kind = collections.defaultdict(collections.Counter)
    for r in rows:
        by_kind[r['class']][r['kind']] += 1
    json.dump({'old': old, 'new': new, 'rows': rows}, open(os.path.join(report, 'merge-report.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    md = ['# Слияние %s → custom (общий предок %s)' % (new, old), '',
          'Конфликтов и находок: **%d**. Слияние не завершено — разрешение следующим шагом.' % len(rows), '',
          '| Класс | Всего | По видам артефактов |', '|---|---|---|']
    for c, n in by_class.most_common():
        md.append('| %s | %d | %s |' % (c, n, ', '.join('%s %d' % kv for kv in by_kind[c].most_common())))
    if by_class.get('поставщик удалил'):
        md += ['', 'Из «поставщик удалил» наше отличие от старого релиза — только шум выгрузки: %d из %d.' % (
            sum(1 for r in rows if r.get('noise') and r['class'] == 'поставщик удалил'), by_class['поставщик удалил'])]
    if any(r.get('noise') for r in rows if r['class'] == 'сирота'):
        md += ['', 'Из сирот пустые модули (шум выгрузки, удаляются вместе с объектом): %d.' % sum(
            1 for r in rows if r.get('noise') and r['class'] == 'сирота')]
    md += ['', 'Дальше: `resolve-merge.py` — структурное слияние XML и шум выгрузки, затем `check-merge.py`.']
    for c in ('двойник', 'сирота', 'слито автоматически'):
        items = [r for r in rows if r['class'] == c]
        if items:
            md += ['', '## %s (%d)' % (c.capitalize(), len(items)), ''] + ['- `%s`' % r['path'] for r in items[:200]]
    open(os.path.join(report, 'merge-report.md'), 'w', encoding='utf-8', newline='\n').write('\n'.join(md) + '\n')
    print('слияние %s → custom: находок %d (%s)' % (new, len(rows), ', '.join('%s %d' % kv for kv in by_class.most_common())))
    print('отчёт: %s' % os.path.join(report, 'merge-report.md'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
