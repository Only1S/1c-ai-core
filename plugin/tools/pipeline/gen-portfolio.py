"""gen-portfolio.py — портфель доработок docs-project/pipeline.md из карточек и перевод стадии карточки (/ones-core:plan).

Карточка — док docs-project/**/<слаг>.md с полем «Стадия:» в шапке (customization-pipeline). Чего не хватает выходу её
стадии, считает тот же код, что у хука lint-project-docs (stage_exit_missing), — портфель, подсказка хука и перевод
стадии не расходятся.

Запуск (корень проекта — --root, иначе CLAUDE_PROJECT_DIR, иначе текущая папка):
    python gen-portfolio.py                           — пересобрать docs-project/pipeline.md и напечатать его
    python gen-portfolio.py --check                   — ничего не пишет; код 1, если файл разошёлся с карточками
    python gen-portfolio.py --card <путь> --exit-ok   — код 0, если выход текущей стадии карточки готов; иначе 1 и перечень
    python gen-portfolio.py --json                    — только чтение: портфель JSON (ASCII) для панели «Доработка» и
                                                        инструмента work_status — карточки, стадия, чего не хватает, строки
                                                        матрицы по статусам, сверка портфеля с файлом; без docs-project — docs: false
    python gen-portfolio.py new <направление> <слаг> <название…>
                                                      — карточка из шаблона card-template.md (стадия request), строка в INDEX.md
    python gen-portfolio.py move <слаг> <стадия> [--reason "<причина>"]
                                                      — вперёд: на одну стадию и только при готовом выходе текущей; назад —
                                                        только с причиной; переход пишется в «История стадий» карточки
    python gen-portfolio.py close <слаг> --reason "<причина>"
                                                      — закрыть с отказом: стадия done, в шапке «Итог: отказ — причина»,
                                                        запись в «История стадий»; причина обязательна
Карточки — по тому же правилу, что у хука (card_path): docs-project/, кроме журналов, ADR, портфеля и оглавления.
Пишет: docs-project/pipeline.md (UTF-8 без BOM, LF), строки в docs-project/INDEX.md; new — карточку; move и close — поля
шапки и «История стадий» карточки. После new, move и close портфель пересобирается. --check и --json не пишут ничего.
Коды выхода: 0 — сделано, совпадает или выход готов; 1 — отказ (выход не готов, портфель разошёлся, возврат без причины,
слаг занят, стадия вне словаря); 2 — ошибка вызова (нет docs-project, неверное имя, нет шаблона).
"""
import argparse
import difflib
import importlib.util
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, 'card-template.md')
PORTFOLIO = 'pipeline.md'
MARK = 'собирается генератором, руками не править'
NAMES = {'request': 'заявка', 'analysis': 'разбор и ТЗ', 'slicing': 'план срезов', 'build': 'реализация',
         'acceptance': 'приёмка', 'done': 'слияние и закрытие'}
SLUG = r'[a-z0-9]+(?:-[a-z0-9]+)*'   # file-and-folder-names: латиница строчными через дефис
STAGE_LINE = r'^([ \t]*(?:[-*][ \t]+)?\**[ \t]*Стадия[ \t]*\**[ \t]*:)(.*)$'   # то же поле, что card_field хука
L = None   # хук lint-project-docs: card_field, stage_key, stage_exit_missing, STAGES


def load_lint():
    """Проверки карточки — из хука lint-project-docs (в плагине и в мастере он лежит в ../../hooks)."""
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('lint_project_docs', os.path.join(HERE, '..', '..', 'hooks', 'lint-project-docs.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read(path):
    with open(path, encoding='utf-8-sig', errors='replace') as f:
        return f.read().replace('\r\n', '\n')


def write(path, text):
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)


def cards(docs):
    """Карточки docs-project: [{rel, path, body, raw, key, title, next}], обход по алфавиту, скрытые папки — мимо."""
    out = []
    for d, dirs, files in os.walk(docs):
        dirs[:] = sorted(x for x in dirs if not x.startswith('.'))
        for f in sorted(files):
            rel = os.path.relpath(os.path.join(d, f), docs).replace('\\', '/')
            if not f.lower().endswith('.md') or not L.card_path(os.path.join(d, f)):
                continue
            body = read(os.path.join(d, f))
            raw = L.card_field(body, 'Стадия')
            if raw is None:
                continue
            h1 = re.search(r'^#[ \t]+(.+?)[ \t#]*$', body, re.M)
            out.append({'rel': rel, 'path': os.path.join(d, f), 'body': body, 'raw': raw, 'key': L.stage_key(raw),
                        'title': h1.group(1).strip() if h1 else f[:-3], 'next': L.card_field(body, 'Следующий шаг')})
    return out


def missing(c):
    """Чего не хватает выходу текущей стадии карточки — та же проверка, что в lint-project-docs; закрытой с отказом — ничего."""
    if L.rejected(c['body']):
        return []
    return L.stage_exit_missing(c['body'], c['key']) if c['key'] in L.STAGES else ['ключ стадии вне словаря']


def cell(s):
    return (s or '').replace('\n', ' ').replace('|', '\\|').strip() or '—'


def ordered(docs):
    """Карточки в порядке портфеля: по стадии конвейера, внутри стадии — по пути."""
    rank = {k: n for n, k in enumerate(L.STAGES)}
    return sorted(cards(docs), key=lambda c: (rank.get(c['key'], len(rank)), c['rel']))


def portfolio(docs):
    """Текст портфеля: строка на карточку, по стадии конвейера, внутри стадии — по пути."""
    cs = ordered(docs)
    lines = ['# Портфель доработок', '',
             '> Этот файл %s: его пишет `gen-portfolio.py` (команда `/ones-core:plan`) из карточек `docs-project/**/*.md` '
             'с полем «Стадия:»; ручную правку ловит `gen-portfolio.py --check`. Стадии и их выходы — справочник '
             '`customization-pipeline`.' % MARK, '']
    if not cs:
        lines.append('Доработок нет — карточку заводит `/ones-core:plan new <направление> <слаг> <название>`.')
    else:
        lines += ['| Доработка | Стадия | Следующий шаг | Чего не хватает |', '|---|---|---|---|']
        for c in cs:
            stage = '`%s` — %s' % (c['key'], 'закрыто с отказом' if L.rejected(c['body']) else NAMES[c['key']]) \
                if c['key'] in NAMES else '«%s» — вне словаря' % c['raw']
            link = '[%s](%s)' % (cell(c['title']).replace(']', '\\]'), c['rel'].replace(' ', '%20'))
            lines.append('| %s | %s | %s | %s |' % (link, cell(stage), cell(c['next']), cell('; '.join(missing(c)))))
    return '\n'.join(lines) + '\n'


def matrix_counts(body):
    """Строки Т-n матрицы готовности по статусам — тем же разбором таблиц, что у хука (tables, clean, is_matrix)."""
    out = {}
    for head, rows in L.tables(body):
        h = [L.clean(c) for c in head]
        if not L.is_matrix(h):
            continue
        st = h.index('статус') if 'статус' in h else None
        for r in rows:
            if re.search(L.REQ_ID, r[0]):
                v = (L.clean(r[st]) if st is not None and st < len(r) else '') or 'без статуса'
                out[v] = out.get(v, 0) + 1
    return out


def as_json(docs):
    """Портфель для панели «Доработка» и инструмента work_status — только чтение: порядок и «чего не хватает» те же, что
    в pipeline.md; portfolio — сверка файла портфеля с карточками (absent, in-sync, stale), как у --check."""
    cs = ordered(docs)
    path = os.path.join(docs, PORTFOLIO)
    state = 'absent' if not os.path.isfile(path) else ('in-sync' if read(path) == portfolio(docs) else 'stale')
    return {'docs': True, 'portfolio': state, 'cards': [
        {'rel': c['rel'], 'title': c['title'], 'key': c['key'], 'raw': c['raw'], 'stage': NAMES.get(c['key']), 'next': c['next'],
         'rejected': L.rejected(c['body']), 'missing': missing(c), 'matrix': matrix_counts(c['body']),
         'mtime': os.path.getmtime(c['path'])} for c in cs]}


def ensure_index(docs, rel, name, desc):
    """Строка о доке в docs-project/INDEX.md (project-knowledge-folder п.3) — в раздел «Доработки», если её ещё нет."""
    idx = os.path.join(docs, 'INDEX.md')
    text = read(idx) if os.path.isfile(idx) else '# Проектные доки\n'
    if '](%s)' % rel in text:
        return
    line = '- [%s](%s) — %s' % (name, rel, desc)
    sec = re.search(r'^##[ \t]+Доработки[ \t]*$', text, re.M)
    if not sec:
        text = text.rstrip('\n') + '\n\n## Доработки\n' + line + '\n'
    else:
        nxt = re.search(r'^#{1,2}[ \t]', text[sec.end():], re.M)
        end = sec.end() + nxt.start() if nxt else len(text)
        tail = text[end:]
        text = text[:end].rstrip('\n') + '\n' + line + '\n' + ('\n' + tail if tail else '')
    write(idx, text)


def build(docs):
    text = portfolio(docs)
    write(os.path.join(docs, PORTFOLIO), text)
    ensure_index(docs, PORTFOLIO, 'pipeline', 'портфель доработок: стадия, следующий шаг и чего не хватает каждой карточке (%s)' % MARK)
    return text


def check(docs):
    path = os.path.join(docs, PORTFOLIO)
    want = portfolio(docs)
    if not os.path.isfile(path):
        if not cards(docs):
            print('[ OK ] карточек доработок нет — сверять портфель не с чем')
            return 0
        print('[FAIL] портфеля docs-project/%s нет, а карточки есть — пересобери: python gen-portfolio.py' % PORTFOLIO)
        return 1
    have = read(path)
    if have == want:
        print('[ OK ] портфель docs-project/%s совпадает с карточками' % PORTFOLIO)
        return 0
    print('[FAIL] портфель docs-project/%s разошёлся с карточками (правлен руками или не пересобран) — пересобери: '
          'python gen-portfolio.py' % PORTFOLIO)
    diff = [ln for ln in difflib.unified_diff(have.split('\n'), want.split('\n'), 'в файле', 'из карточек', n=0, lineterm='')
            if ln[:1] in '+-' and not ln.startswith(('+++', '---'))]
    for ln in diff[:6]:
        print('       ' + ln[:200])
    return 1


def exit_ok(path):
    """Готов ли выход текущей стадии карточки: 0 — да; 1 — нет, с перечнем; 2 — это не карточка."""
    if not os.path.isfile(path):
        print('нет файла %s' % path, file=sys.stderr)
        return 2
    body = read(path)
    raw = L.card_field(body, 'Стадия')
    if raw is None:
        print('%s — не карточка доработки: в шапке нет поля «Стадия:»' % path, file=sys.stderr)
        return 2
    key = L.stage_key(raw)
    if L.rejected(body):
        print('карточка закрыта с отказом — выходы стадий не проверяются')
        return 0
    if key not in L.STAGES:
        print('ключ стадии «%s» вне словаря (%s) — выход не проверить' % (raw, ', '.join(L.STAGES)))
        return 1
    lost = L.stage_exit_missing(body, key)
    if lost:
        print('выход стадии «%s» не готов — не хватает:\n%s' % (key, '\n'.join('- ' + x for x in lost)))
        return 1
    print('выход стадии «%s» готов' % key)
    return 0


def new_card(docs, direction, slug, title):
    if not re.fullmatch(SLUG, direction) or not re.fullmatch(SLUG, slug):
        print('направление и слаг — латиница строчными через дефис (file-and-folder-names): «%s», «%s»' % (direction, slug), file=sys.stderr)
        return 2
    if direction == 'adr':
        print('adr — служебная папка решений (decision-records-and-glossary), карточка там не заводится: выбери направление', file=sys.stderr)
        return 2
    title = ' '.join(title.split())   # перевод строки в названии подставил бы в шапку своё поле «Стадия:»
    if not title:
        print('нет названия доработки', file=sys.stderr)
        return 2
    if not os.path.isfile(TEMPLATE):
        print('нет шаблона карточки %s' % TEMPLATE, file=sys.stderr)
        return 2
    taken = [os.path.relpath(os.path.join(d, f), docs).replace('\\', '/') for d, _, fs in os.walk(docs) for f in fs
             if f.lower() == slug + '.md']
    if taken:
        print('слаг «%s» уже занят: docs-project/%s — у карточки слаг свой' % (slug, taken[0]))
        return 1
    rel = '%s/%s.md' % (direction, slug)
    os.makedirs(os.path.join(docs, direction), exist_ok=True)
    write(os.path.join(docs, rel), read(TEMPLATE).replace('{{название}}', title).replace('{{слаг}}', slug))
    ensure_index(docs, rel, slug, 'карточка доработки «%s»' % title)
    build(docs)
    print('карточка заведена: docs-project/%s (стадия request); строка в INDEX.md, портфель пересобран' % rel)
    return 0


def set_stage(body, key):
    """Новый ключ в поле «Стадия:» шапки: меняется только первое слово-ключ (его читает stage_key), обрамление (**, `)
    и хвост после ключа остаются."""
    top_end = re.search(r'^##[ \t]', body, re.M)
    cut = top_end.start() if top_end else len(body)

    def repl(f):
        v = re.match(r'([\s*`]*)([\w-]+)(.*)$', f.group(2))
        return f.group(1) + (v.group(1) + key + v.group(3) if v else ' ' + key)
    return re.sub(STAGE_LINE, repl, body[:cut], count=1, flags=re.M | re.I) + body[cut:]


def set_result(body, text):
    """Поле «Итог:» в шапке карточки — строкой сразу под «Стадия:» тем же оформлением; уже есть — заменяется."""
    top_end = re.search(r'^##[ \t]', body, re.M)
    cut = top_end.start() if top_end else len(body)
    top = body[:cut]
    have = re.search(r'^([ \t]*(?:[-*][ \t]+)?\**[ \t]*Итог[ \t]*\**[ \t]*:)(.*)$', top, re.M | re.I)
    if have:
        close = re.match(r'\**', have.group(2)).group(0)   # «**Итог:** …»: выделение закрывается после двоеточия, оно в значении поля
        return top[:have.start(2)] + close + ' ' + text + top[have.end(2):] + body[cut:]
    st = re.search(STAGE_LINE, top, re.M | re.I)
    close = re.match(r'\**', st.group(2)).group(0)
    line = re.sub(r'Стадия', 'Итог', st.group(1), count=1, flags=re.I) + close + ' ' + text
    return top[:st.end()] + '\n' + line + top[st.end():] + body[cut:]


def add_history(body, line):
    """Строка перехода в раздел «История стадий» (раздела нет — заводится в конце карточки)."""
    sec = re.search(r'^##[ \t]+История стадий[ \t]*$', body, re.M)
    if not sec:
        return body.rstrip('\n') + '\n\n## История стадий\n\n' + line + '\n'
    nxt = re.search(r'^#{1,2}[ \t]', body[sec.end():], re.M)
    end = sec.end() + nxt.start() if nxt else len(body)
    part, tail = body[sec.end():end].rstrip('\n'), body[end:]
    gap = '\n' if part.split('\n')[-1].startswith('- ') else '\n\n'
    return body[:sec.end()] + part + gap + line + '\n' + ('\n' + tail if tail else '')


def find_card(docs, ref):
    """Карточка по слагу или <направление>/<слаг>; не нашлась или неоднозначна — None и пояснение."""
    ref = ref.replace('\\', '/')
    ref = ref[:-3] if ref.lower().endswith('.md') else ref
    found = [c for c in cards(docs) if c['rel'][:-3] == ref or c['rel'][:-3].endswith('/' + ref)]
    if len(found) != 1:
        names = ', '.join(c['rel'][:-3] for c in (found or cards(docs))) or 'карточек нет'
        print(('слаг «%s» неоднозначен — укажи <направление>/<слаг>: %s' if found else 'карточки «%s» нет; есть: %s') % (ref, names))
        return None
    return found[0]


def move(docs, ref, stage, reason):
    c = find_card(docs, ref)
    if c is None:
        return 1
    target = stage.strip().lower()
    if target not in L.STAGES:
        print('стадии «%s» нет в словаре: %s' % (stage, ', '.join(L.STAGES)))
        return 1
    cur = c['key']
    if cur not in L.STAGES:
        print('в карточке ключ стадии «%s» вне словаря — сперва верни в поле «Стадия:» ключ, с которого карточка не уходила' % c['raw'])
        return 1
    ci, ti = L.STAGES.index(cur), L.STAGES.index(target)
    if ti == ci:
        print('карточка уже на стадии «%s»' % cur)
        return 1
    if ti > ci:
        if ti != ci + 1:
            print('вперёд — по одной стадии: после «%s» идёт «%s», а не «%s»' % (cur, L.STAGES[ci + 1], target))
            return 1
        lost = L.stage_exit_missing(c['body'], cur)
        if lost:
            print('перевод «%s» → «%s» отклонён: выход стадии «%s» не готов — не хватает:\n%s'
                  % (cur, target, cur, '\n'.join('- ' + x for x in lost)))
            return 1
    elif not reason.strip():
        print('назад («%s» → «%s») — только с причиной: --reason "<почему>"; причина записывается в карточку' % (cur, target))
        return 1
    line = '- %s · %s → %s%s' % (time.strftime('%d.%m.%Y'), cur, target, (' · причина: ' + ' '.join(reason.split())) if reason.strip() else '')
    write(c['path'], add_history(set_stage(c['body'], target), line))
    build(docs)
    print('стадия docs-project/%s: %s → %s; портфель пересобран. Обнови «Следующий шаг:» в карточке и пересобери портфель'
          % (c['rel'], cur, target))
    return 0


def close(docs, ref, reason):
    """Закрыть с отказом (решение владельца 29.10.2026): стадия done, «Итог: отказ — причина», запись в «История стадий»."""
    c = find_card(docs, ref)
    if c is None:
        return 1
    why = ' '.join(reason.split())
    if not why:
        print('закрыть с отказом — только с причиной: --reason "<почему>"; причина записывается в карточку')
        return 1
    if c['key'] == 'done':
        print('карточка уже закрыта (стадия done)')
        return 1
    line = '- %s · %s → done · закрыто с отказом · причина: %s' % (time.strftime('%d.%m.%Y'), c['key'] or c['raw'], why)
    write(c['path'], add_history(set_result(set_stage(c['body'], 'done'), 'отказ — ' + why), line))
    build(docs)
    print('docs-project/%s закрыта с отказом: стадия done, «Итог: отказ — %s»; портфель пересобран' % (c['rel'], why))
    return 0


def main():
    global L
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description='Портфель доработок docs-project/pipeline.md и стадии карточек (customization-pipeline).')
    ap.add_argument('--root', help='корень проекта (по умолчанию CLAUDE_PROJECT_DIR или текущая папка)')
    ap.add_argument('--check', action='store_true', help='ничего не писать; код 1, если портфель разошёлся с карточками')
    ap.add_argument('--card', help='путь карточки — вместе с --exit-ok')
    ap.add_argument('--exit-ok', action='store_true', help='код 0, если выход текущей стадии карточки --card готов')
    ap.add_argument('--json', action='store_true', help='только чтение: портфель JSON для панели «Доработка» и инструмента work_status')
    sub = ap.add_subparsers(dest='cmd')
    pn = sub.add_parser('new', help='завести карточку из шаблона со стадией request')
    pn.add_argument('direction', metavar='направление')
    pn.add_argument('slug', metavar='слаг')
    pn.add_argument('title', metavar='название', nargs='+')
    pm = sub.add_parser('move', help='перевести карточку на другую стадию')
    pm.add_argument('ref', metavar='слаг')
    pm.add_argument('stage', metavar='стадия')
    pm.add_argument('--reason', default='', help='причина возврата назад (обязательна) — пишется в карточку')
    pc = sub.add_parser('close', help='закрыть карточку с отказом')
    pc.add_argument('ref', metavar='слаг')
    pc.add_argument('--reason', default='', help='причина отказа (обязательна) — пишется в карточку')
    for p in (pn, pm, pc):
        p.add_argument('--root', default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    args = ap.parse_args()
    if bool(args.card) != bool(args.exit_ok):
        ap.error('--card и --exit-ok задаются вместе')
    if args.json and (args.cmd or args.check or args.card):
        ap.error('--json — только чтение портфеля: без подкоманд, --check и --card')
    try:
        L = load_lint()
    except Exception as e:
        print('не загрузился хук lint-project-docs рядом с плагином: %s' % e, file=sys.stderr)
        return 2
    root = args.root or os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()
    if args.card:
        p = args.card if os.path.isabs(args.card) or os.path.isfile(args.card) else os.path.join(root, args.card)
        return exit_ok(p)
    docs = os.path.join(root, 'docs-project')
    if args.json:
        # ASCII: панель и инструмент читают вывод через трубу — кириллица не зависит от кодировки консоли
        print(json.dumps(as_json(docs) if os.path.isdir(docs) else {'docs': False, 'portfolio': 'absent', 'cards': []}))
        return 0
    if not os.path.isdir(docs):
        print('нет папки docs-project в %s — это не корень проекта (папку заводит /ones-core:setup)' % root, file=sys.stderr)
        return 2
    if args.cmd == 'new':
        return new_card(docs, args.direction, args.slug, ' '.join(args.title).strip())
    if args.cmd == 'move':
        return move(docs, args.ref, args.stage, args.reason)
    if args.cmd == 'close':
        return close(docs, args.ref, args.reason)
    if args.check:
        return check(docs)
    print(build(docs), end='')
    return 0


if __name__ == '__main__':
    sys.exit(main())
