"""Разрешение незавершённого слияния (после merge-release.py): структурное слияние XML метаданных и шум выгрузки.

Использование:
  python resolve-merge.py --repo <репозиторий слияния> [--report <каталог отчёта>] [--dry-run]

Что решается само (каждое действие — в отчёте, файл кладётся в индекс git add / git rm):
  оба изменили, у нас только шум выгрузки        → версия поставщика
  оба изменили, у поставщика только шум            → наша версия
  оба изменили, XML описания объекта или прав      → структурное слияние по элементам (xml_merge.py); конфликт элементов
                                                     — файл не трогается, места конфликта в отчёте
  поставщик удалил, у нас только шум              → принять удаление
  добавлено с обеих сторон, отличие только шум     → версия поставщика
  слито автоматически, XML описания объекта/прав   → пересборка структурным слиянием; если построчная склейка git
                                                     разошлась со структурной — берётся структурная. Файл, изменённый
                                                     после слияния (в индексе не склейка git из merge-report или на диске
                                                     другой текст), не трогается: это ручное решение, в отчёте — разделом
Запуск можно повторять: ручные решения он не затирает.
Остальное (модули с правками с обеих сторон, формы, макеты, двойники, «у нас удалено», сироты) — решение владельца, в
отчёте с подсказкой. --dry-run — только отчёт, без записи. Отчёт: resolve-report.md и resolve-report.json рядом с
merge-report. Коды: 0 — выполнено (остаток в отчёте), 1 — ошибка git, 2 — неверные аргументы или нет слияния.
"""
import argparse
import collections
import json
import os
import sys
import tempfile

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from release_xml import artifact_kind, git, index_blobs, is_noise  # noqa: E402
import xml_merge  # noqa: E402

HINTS = {'модуль': 'основа — код поставщика, доработку перенести по смыслу; маркеры конфликтов не склеивать',
         'форма': 'форма целиком с одной стороны, затем перенести доработку скиллом form-edit; после — уникальность id (check-merge)',
         'макет': 'макет целиком с одной стороны (позиционный формат), правку перенести вручную',
         'права': 'права роли: конфликт элементов — решить по месту',
         'объект': 'конфликт элементов описания объекта — решить по месту',
         'корень конфигурации': 'конфликт элементов Configuration.xml — решить по месту',
         'xml': 'не описание объекта (командный интерфейс, предопределённые, схема) — целиком с одной стороны',
         'прочее': 'двоичный или служебный файл — целиком с одной стороны'}
LEFT = {'у нас удалено': 'мы удалили, поставщик изменил — решение владельца',
        'двойник': 'по умолчанию наш объект переименовать в Удалить… с сохранением uuid, взять объект поставщика — решение владельца',
        'добавлено с обеих сторон': 'сравнить по существу'}


def blob(repo, spec):
    try:
        return git(repo, 'show', spec, raw=True)
    except RuntimeError:
        return None


def pathspec_file(paths):
    p = os.path.join(tempfile.mkdtemp(prefix='vu-ps-'), 'paths')
    open(p, 'wb').write(b'\0'.join(x.encode('utf-8') for x in paths))
    return p


def main():
    ap = argparse.ArgumentParser(description='Разрешение слияния: структурное слияние XML и шум выгрузки')
    ap.add_argument('--repo', required=True)
    ap.add_argument('--report', help='каталог отчёта (по умолчанию — рядом с репозиторием, там же merge-report.json)')
    ap.add_argument('--dry-run', action='store_true', help='только отчёт, файлы и индекс не меняются')
    a = ap.parse_args()
    repo = os.path.abspath(a.repo)
    report = os.path.abspath(a.report or repo.rstrip(os.sep) + '-report')
    mr = os.path.join(report, 'merge-report.json')
    if not os.path.isfile(os.path.join(repo, '.git', 'MERGE_HEAD')):
        print('слияние не идёт в %s — сначала merge-release.py' % repo)
        return 2
    if not os.path.isfile(mr):
        print('нет отчёта слияния %s — сначала merge-release.py' % mr)
        return 2
    rep = json.load(open(mr, encoding='utf-8'))
    old, new = rep['old'], rep['new']
    stages = collections.defaultdict(set)
    try:
        for line in git(repo, 'ls-files', '-u', '-z').split('\0'):
            if line.strip():
                meta, path = line.split('\t', 1)
                stages[path].add(int(meta.split()[2]))
    except RuntimeError as e:
        print(e)
        return 1
    actions, to_rm, writes = [], [], {}

    def act(path, what, **kw):
        actions.append(dict(path=path, kind=artifact_kind(path), action=what, **kw))

    for path, st in sorted(stages.items()):
        kind = artifact_kind(path)
        b = blob(repo, ':1:' + path) if 1 in st else None
        o = blob(repo, ':2:' + path) if 2 in st else None
        t = blob(repo, ':3:' + path) if 3 in st else None
        if st == {1, 2, 3}:
            if is_noise(b, o):
                writes[path] = t
                act(path, 'взята версия поставщика: у нас только шум выгрузки', resolved=True)
            elif is_noise(b, t):
                writes[path] = o
                act(path, 'оставлена наша версия: у поставщика только шум выгрузки', resolved=True)
            elif xml_merge.mergeable(t) and xml_merge.mergeable(o) and xml_merge.mergeable(b):
                res, conf = xml_merge.merge_bytes(b, o, t)
                if res is not None:
                    writes[path] = res
                    act(path, 'слито структурно', resolved=True)
                else:
                    act(path, 'структурный конфликт', resolved=False, conflicts=conf[:50])
            else:
                act(path, 'оставлено: оба изменили', resolved=False, hint=HINTS.get(kind, ''))
        elif st == {1, 2}:
            if is_noise(b, o):
                to_rm.append(path)
                act(path, 'принято удаление поставщика: у нас только шум выгрузки', resolved=True)
            else:
                act(path, 'оставлено: поставщик удалил', resolved=False,
                    hint='решение владельца: куда переносится доработка (объект поставщик удалил или переименовал)')
        elif st == {1, 3}:
            act(path, 'оставлено: у нас удалено', resolved=False, hint=LEFT['у нас удалено'])
        elif st == {2, 3}:
            cls = next((r['class'] for r in rep['rows'] if r['path'] == path), 'добавлено с обеих сторон')
            if cls != 'двойник' and is_noise(o, t):
                writes[path] = t
                act(path, 'взята версия поставщика: добавлено с обеих сторон, отличие — только шум', resolved=True)
            else:
                act(path, 'оставлено: ' + cls, resolved=False, hint=LEFT.get(cls, ''))
        else:
            act(path, 'оставлено: прочее', resolved=False)
    # слито автоматически: построчная склейка XML описаний объектов перепроверяется структурной
    index = index_blobs(repo)
    for r in rep['rows']:
        path = r['path']
        if r['class'] != 'слито автоматически' or path in stages:
            continue
        b, o, t, cur = (blob(repo, '%s:%s' % (rev, path)) for rev in (old, 'HEAD', new, ''))
        if not (xml_merge.mergeable(t) and xml_merge.mergeable(o) and xml_merge.mergeable(b)) or cur is None:
            continue
        res, conf = xml_merge.merge_bytes(b, o, t)
        if res is None:
            act(path, 'проверить вручную: git склеил построчно, структурно — конфликт', resolved=False, conflicts=conf[:50])
            continue
        try:
            same = xml_merge.canon(xml_merge.parse(res.decode('utf-8'))) == xml_merge.canon(xml_merge.parse(cur.decode('utf-8')))
        except (xml_merge.XmlError, UnicodeDecodeError):
            same = False
        if same:
            continue
        p = os.path.join(repo, *path.split('/'))
        disk = open(p, 'rb').read() if os.path.isfile(p) else None
        if index.get(path) != r.get('blob') or disk != cur:     # после слияния файл менял человек: его решение не затираем
            act(path, 'оставлено: изменено вручную после слияния', resolved=True, manual=True)
            continue
        writes[path] = res
        act(path, 'построчная склейка git заменена структурной (разошлись)', resolved=True)
    if not a.dry_run:
        try:
            for path, data in writes.items():
                p = os.path.join(repo, *path.split('/'))
                os.makedirs(os.path.dirname(p), exist_ok=True)
                open(p, 'wb').write(data)
            if writes:
                git(repo, 'add', '--pathspec-from-file=' + pathspec_file(sorted(writes)), '--pathspec-file-nul')
            if to_rm:
                git(repo, 'rm', '-q', '--pathspec-from-file=' + pathspec_file(to_rm), '--pathspec-file-nul')
        except (RuntimeError, OSError) as e:
            print(e)
            return 1
    left = [x for x in actions if not x['resolved']]
    done = [x for x in actions if x['resolved']]
    by_action = collections.Counter(x['action'] for x in actions)
    json.dump({'old': old, 'new': new, 'dry_run': a.dry_run, 'actions': actions},
              open(os.path.join(report, 'resolve-report.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    md = ['# Разрешение слияния %s → custom%s' % (new, ' (пробный прогон, ничего не записано)' if a.dry_run else ''), '',
          'Решено автоматически: **%d**, осталось владельцу: **%d**.' % (len(done), len(left)), '',
          '| Действие | Файлов |', '|---|---|'] + ['| %s | %d |' % kv for kv in by_action.most_common()]
    manual = [x for x in actions if x.get('manual')]
    if manual:
        md += ['', '## Изменено вручную, оставлено как есть: структурная пересборка дала бы другой текст', '']
        md += ['- `%s`' % x['path'] for x in manual[:300]]
    if left:
        md += ['', '## Осталось решить', '']
        for x in left[:300]:
            md.append('- `%s` — %s%s' % (x['path'], x['action'], ('. ' + x['hint']) if x.get('hint') else ''))
            for c in x.get('conflicts', [])[:10]:
                md.append('  - `%s`: %s' % (c['path'] or '(файл)', c['why']))
    open(os.path.join(report, 'resolve-report.md'), 'w', encoding='utf-8', newline='\n').write('\n'.join(md) + '\n')
    print('%sрешено %d, осталось %d (%s)' % ('[пробно] ' if a.dry_run else '', len(done), len(left),
                                            ', '.join('%s %d' % kv for kv in by_action.most_common())))
    print('отчёт: %s' % os.path.join(report, 'resolve-report.md'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
