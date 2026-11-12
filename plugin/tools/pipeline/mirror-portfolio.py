r"""mirror-portfolio.py — зеркало портфеля доработок в GitHub Issues закрытого репозитория (п.3.6 волны 3).

Людям вне сессии видно, что в работе и на какой стадии. Наружу уходят только название, стадия и путь карточки:
тексты ТЗ, «Следующий шаг» и код не уходят. Источник — gen-portfolio.py --json.

Запуск:
    python mirror-portfolio.py --repo <владелец/имя> [--root <проект>] [--dry-run] [--gh <программа gh>]
        --repo     закрытый репозиторий зеркала; открытый — отказ
        --root     корень проекта (иначе CLAUDE_PROJECT_DIR, иначе текущая папка)
        --dry-run  только показать действия

Карточке — одно issue с меткой «доработка» и меткой стадии. Стадия сменилась — метки переставляются; стадия «готово»
и карточка без файла — issue закрывается, дубль карточки — тоже. Повторный запуск без перемен ничего не делает.
Код выхода: 0 — зеркало совпало с портфелем; 1 — команда gh упала; 2 — репозиторий открытый, недоступен или нет портфеля.
"""
import argparse
import json
import os
import re
import subprocess
import sys

BASE_LABEL = 'доработка'
STAGE_PREFIX = 'стадия: '
MARK = '<!-- ones-core-card: %s -->'
MARK_RE = re.compile(r'<!-- ones-core-card: (.+?) -->')
DONE = 'done'


def card_body(card):
    """Тело issue: только путь карточки и служебная метка, по которой issue находится при следующем запуске."""
    return 'Карточка: `%s`.\n\n%s' % (card['rel'], MARK % card['rel'])


def stage_label(card):
    return STAGE_PREFIX + (card.get('stage') or card.get('raw') or 'нет стадии')


def is_open(issue):
    return (issue.get('state') or '').upper() == 'OPEN'


def plan(cards, issues):
    """Действия зеркала: (что, номер issue или None, данные) по карточкам и уже заведённым issue."""
    by_rel, twins = {}, []
    for issue in sorted(issues, key=lambda x: x.get('number') or 0):
        m = MARK_RE.search(issue.get('body') or '')
        if not m:
            continue
        kept = by_rel.get(m.group(1))
        if kept is None or (is_open(issue) and not is_open(kept)):
            by_rel[m.group(1)] = issue
        elif is_open(issue):
            twins.append(issue)   # новое issue попадает в список с задержкой: второй запуск подряд заводит дубль
    actions = []
    seen = set()
    for card in cards:
        seen.add(card['rel'])
        done = card.get('key') == DONE
        label = stage_label(card)
        issue = by_rel.get(card['rel'])
        if issue is None:
            if not done:
                actions.append(('create', None, {'title': card['title'], 'body': card_body(card), 'label': label}))
            continue
        old = [x['name'] for x in issue.get('labels', []) if x['name'].startswith(STAGE_PREFIX)]
        if issue.get('title') != card['title'] or old != [label]:
            actions.append(('edit', issue['number'], {'title': card['title'], 'add': label, 'remove': [x for x in old if x != label]}))
        state = (issue.get('state') or '').upper()
        if done and state == 'OPEN':
            actions.append(('close', issue['number'], {}))
        elif not done and state == 'CLOSED':
            actions.append(('reopen', issue['number'], {}))
    for rel, issue in by_rel.items():
        if rel not in seen and is_open(issue):
            actions.append(('close', issue['number'], {}))
    actions.extend(('close', issue['number'], {}) for issue in twins)
    return actions


def argv_of(gh, repo, action):
    """Команды gh одного действия: метка стадии заводится заранее (--force не падает на существующей)."""
    what, number, data = action
    if what == 'create':
        return [[gh, 'label', 'create', data['label'], '-R', repo, '--force'],
                [gh, 'issue', 'create', '-R', repo, '--title', data['title'], '--body', data['body'],
                 '--label', BASE_LABEL, '--label', data['label']]]
    if what == 'edit':
        cmd = [gh, 'issue', 'edit', str(number), '-R', repo, '--title', data['title'], '--add-label', data['add']]
        for old in data['remove']:
            cmd += ['--remove-label', old]
        return [[gh, 'label', 'create', data['add'], '-R', repo, '--force'], cmd]
    return [[gh, 'issue', what, str(number), '-R', repo]]


def gh_json(cmd):
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        return None, r.stderr.decode('utf-8', 'replace').strip()
    return json.loads(r.stdout.decode('utf-8', 'replace') or 'null'), ''


def main():
    ap = argparse.ArgumentParser(description='Зеркало портфеля доработок в GitHub Issues закрытого репозитория.')
    ap.add_argument('--repo', required=True, help='закрытый репозиторий зеркала, владелец/имя')
    ap.add_argument('--root', default=os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd(), help='корень проекта')
    ap.add_argument('--dry-run', action='store_true', help='только показать действия')
    ap.add_argument('--gh', default='gh', help='программа gh')
    args = ap.parse_args()
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding='utf-8')
        except Exception:
            pass

    info, err = gh_json([args.gh, 'repo', 'view', args.repo, '--json', 'isPrivate'])
    if info is None:
        print('репозиторий недоступен: %s' % err, file=sys.stderr)
        return 2
    if not info.get('isPrivate'):
        print('репозиторий %s открытый: зеркало только в закрытый' % args.repo, file=sys.stderr)
        return 2
    gen = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gen-portfolio.py')
    r = subprocess.run([sys.executable, gen, '--json', '--root', args.root], capture_output=True)
    portfolio = json.loads(r.stdout.decode('utf-8', 'replace') or '{}')
    if not portfolio.get('docs'):
        print('в проекте нет docs-project: зеркалить нечего', file=sys.stderr)
        return 2
    issues, err = gh_json([args.gh, 'issue', 'list', '-R', args.repo, '--label', BASE_LABEL, '--state', 'all',
                           '--limit', '1000', '--json', 'number,title,state,labels,body'])
    if issues is None:
        print('список issue не получен: %s' % err, file=sys.stderr)
        return 2

    actions = plan(portfolio.get('cards', []), issues)
    if not actions:
        print('зеркало совпадает с портфелем')
        return 0
    for action in actions:
        print('%s %s %s' % (action[0], action[1] or '', action[2].get('title', '')))
    if args.dry_run:
        print('(пробный запуск: ничего не изменено)')
        return 0
    if subprocess.run([args.gh, 'label', 'create', BASE_LABEL, '-R', args.repo, '--force'], capture_output=True).returncode != 0:
        print('метка %s не создана' % BASE_LABEL, file=sys.stderr)
        return 1
    for action in actions:
        for cmd in argv_of(args.gh, args.repo, action):
            r = subprocess.run(cmd, capture_output=True)
            if r.returncode != 0:
                print('сбой: %s: %s' % (' '.join(cmd[1:4]), r.stderr.decode('utf-8', 'replace').strip()), file=sys.stderr)
                return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
