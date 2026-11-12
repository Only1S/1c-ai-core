"""PostToolUse Write/Edit файла .md: механические части правил о проектных доках — подсказка модели (additionalContext).

Проверяет только распознаваемое синтаксически (writing-for-agents п.8), не блокирует (с 4.8.0, решение владельца 17.10.2026):
  - матрица готовности (readiness-matrix-and-process-diagram пп.2–3, 7, 9): колонки, статус из словаря, непустое
    «Чего не хватает» у не-готовой строки, блок mermaid с путём отказа;
  - статусы тикетов среза (vertical-task-slicing п.4) — только из словаря;
  - ADR (decision-records-and-glossary пп.3–4): имя NNNN-slug, разделы, правка «Решения» закоммиченного принятого ADR
    (Edit или перезапись целиком через Write — сверка с версией из git);
  - деловой документ для людей в .md, в том числе в docs-project/deliverables/ (office-formats-for-people; ТЗ в .md допустимо —
    решение владельца 17.10.2026);
  - description скилла (writing-for-agents п.2): есть, до 1024 символов, говорит, когда звать;
  - ссылки на файлы ядра и проекта, которых нет (docs-match-reality) — только в дописанном тексте; с 30.10.2026 ищутся и от
    корня репозитория правленого файла (в рабочей копии worktree новые файлы ветки есть только там);
  - имя нового файла в docs-project/ — латиница, строчные, слова через дефис (file-and-folder-names п.1, с 30.10.2026);
  - карточка доработки (customization-pipeline) — док в docs-project/ с полем «Стадия:» в шапке: ключ из словаря стадий,
    «Следующий шаг» до 60 символов, выход ТЕКУЩЕЙ стадии на месте (stage_exit_missing — её же зовёт gen-portfolio.py);
  - новый док в docs-project/ есть в её INDEX.md (project-knowledge-folder п.3) — в проекте health-check этого не стережёт.
Честность клеток (статус от инструмента, а не по памяти) хуком не проверяется — это остаётся дисциплиной.
Найденное пишется и в logs/answer-check.jsonl с пометкой shown. Внутренняя ошибка — пропуск с пометкой DEGRADED: строка
kind='DEGRADED' в logs/answer-check.jsonl и systemMessage (контракт деградации, с 30.10.2026).
"""
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
I = re.IGNORECASE
STATUSES = ('открыт', 'в работе', 'на проверке', 'готов')
MATRIX_COLS = ('требование', 'чем реализовано', 'шов приемки', 'тест', 'статус', 'чего не хватает')   # после clean(): «ё» → «е»
FAIL_PATH = r'отказ|ошибк|исключени|не удал|таймаут|повтор|откат|отмен|fail|error|reject|timeout|retry|\balt\b|\belse\b|\|\s*нет\s*\|'
HISTORY = r'/(worklog|changelog|observations|live-probes|rules-and-skills-health|weekly-report|releases)\.md$|/adr/'
ADR_SECTIONS = (('контекст', r'^#{2,3}\s*(контекст|context)\b'),
                ('рассмотренные варианты', r'^#{2,3}\s*(рассмотренные\s+(варианты|альтернативы)|альтернативы|варианты|options|alternatives)'),
                ('решение', r'^#{2,3}\s*(решение|decision)\b'),
                ('последствия', r'^#{2,3}\s*(последстви|consequences)'),
                ('статус', r'^\**\s*(статус|status)\b|^#{2,3}\s*(статус|status)\b'))
ADR_ACCEPTED = r'(статус|status)\s*:?\**\s*:?\s*\**\s*(принят|accepted)'
# ТЗ в .md допустимо (решение владельца 17.10.2026, для всех проектов): рабочее ТЗ — .md, .docx — когда уходит наружу
DELIVERABLE_NAME = (r'(^|[-_.])(smeta|estimate|proposal|presentation|otchet|report|reglament|specification|spetsifikatsiya|'
                    r'tekhproekt)$')
# жанры deliverable — как их называет правило office-formats-for-people: техпроект, отчёт, спецификация, смета, презентация,
# регламент (+ коммерческое предложение); ТЗ не судится
DELIVERABLE_H1 = r'^#\s*(техпроект|отч[её]т|спецификаци[яи]|смета|коммерческое предложение|презентация|регламент)'
# имя файла в docs-project/ — латиница, строчные, слова через дефис (file-and-folder-names п.1); имена по требованию инструмента
DOC_NAME = r'[a-z0-9]+(-[a-z0-9]+)*\.md'
TOOL_NAMES = ('index.md', 'readme.md', 'claude.md', 'memory.md', 'skill.md')
# docs/ и docs-project/ в обратных кавычках не судятся: в проекте это часто журнал репозитория конфигурации или чужой папки;
# ссылка бывает с номером или диапазоном строк — «файл:строка», как велит docs-match-reality п.1
AT_LINE = r'(?::\d+(?:[-–]\d+)?)?'
REF = (r'`((?:\.claude|tools|plugin)[/\\][\w./\\-]+\.[a-z0-9]+)' + AT_LINE + r'`|'
       r'\]\(((?!https?:|mailto:|#|/)[^)\s#]+\.[a-z0-9]+)' + AT_LINE + r'(?:#[^)]*)?\)')
BUILT = (('plugin/docs/', 'docs/'), ('plugin/skills/', '.claude/skills/'), ('plugin/commands/', '.claude/commands/'),
         ('plugin/agents/', '.claude/agents/'))   # в мастере эти части плагина лежат в своей раскладке (ADR-0004)
TICKET_FIELD = r'^\s*(?:[-*]\s*)?\**\s*(критерий при[её]мки|шов при[её]мки)\s*\**\s*[:—–]'
# конвейер доработки (customization-pipeline): ключи стадий по порядку; выход каждой — в stage_exit_missing
STAGES = ('request', 'analysis', 'slicing', 'build', 'acceptance', 'done')
NEXT_MAX = 60
REQ_ID = r'(?<![\w-])[ТT]-\d+'


def norm(p):
    return str(p or '').replace('\\', '/').lower()


def cells(line):
    s = line.strip()
    return [c.strip() for c in s[1:-1].split('|')] if s.startswith('|') and s.endswith('|') and len(s) > 1 else None


def tables(body):
    """Таблицы markdown: [(заголовок, [строки])]; ячейки — без обрамляющих | и пробелов."""
    out, cur = [], None
    for line in body.split('\n'):
        row = cells(line)
        if row is None:
            cur = None
        elif cur is None:
            cur = (row, [])
            out.append(cur)
        elif not all(re.fullmatch(r':?-{2,}:?', c) or not c for c in row):
            cur[1].append(row)
    return out


def clean(c):
    return re.sub(r'[*`_]', '', c or '').strip().lower().replace('ё', 'е')


def is_matrix(h):
    """Заголовок матрицы готовности (ячейки после clean): колонка «Требование» и первая колонка Т-n — или, как пишут
    в проектах, «Т» либо «№» вместе с «Чего не хватает» или «Чем реализовано» (иначе это просто нумерованный список требований)."""
    if not h or 'требование' not in h:
        return False
    if re.fullmatch(r'[тt]-?n', h[0]):
        return True
    return h[0] in ('т', 't', '№', 'n', '#') and ('чего не хватает' in h or 'чем реализовано' in h)


def is_ticket_table(h):
    """Заголовок таблицы тикетов срезов: «Статус» и критерий приёмки или шов, но не матрица готовности."""
    return 'статус' in h and not is_matrix(h) and any(re.match(r'(критерий приемки|шов)', c) for c in h)


def matrix_issues(body):
    """Матрица готовности: заголовок, который узнаёт is_matrix."""
    out, found = [], False
    for head, rows in tables(body):
        h = [clean(c) for c in head]
        if not is_matrix(h):
            continue
        found = True
        lost = [c for c in MATRIX_COLS if c not in h]
        if lost:
            out.append('в матрице готовности нет колонок: %s (readiness-matrix-and-process-diagram п.2)' % ', '.join(lost))
        st = h.index('статус') if 'статус' in h else None
        gap = h.index('чего не хватает') if 'чего не хватает' in h else None
        for row in rows:
            row += [''] * (len(h) - len(row))
            status = clean(row[st]) if st is not None else ''
            if status and status not in STATUSES:
                out.append('строка %s: статус «%s» вне словаря (открыт / в работе / на проверке / готов — vertical-task-slicing п.4)'
                           % (row[0], status))
            if gap is not None and status and status != 'готов' and clean(row[gap]) in ('', '—', '-', '–', 'нет', 'ничего'):
                out.append('строка %s: статус «%s», а «Чего не хватает» пусто — у не-готовой строки там недостающий артефакт или '
                           'решение (п.3)' % (row[0], status))
    if found:
        schemes = re.findall(r'```mermaid\s*\n(.*?)```', body, re.S)
        if not schemes:
            out.append('рядом с матрицей нет схемы процесса — блока ```mermaid (п.7)')
        elif not any(re.search(FAIL_PATH, s, I) for s in schemes):
            out.append('на схеме процесса нет пути отказа — ветки ошибки, что пишется в журнал и что видит пользователь (п.9)')
    return out


def ticket_issues(body):
    """Тикеты срезов: поле «Статус:» рядом с полями тикета и колонка «Статус» таблицы тикетов — только из словаря."""
    out = []
    if re.search(TICKET_FIELD, body, I | re.M):   # поля тикета
        for m in re.finditer(r'^\s*(?:[-*]\s*)?\**\s*статус\s*\**\s*[:—–]\s*\**\s*([^\n|*]+)', body, I | re.M):
            v = clean(m.group(1))
            if v and not v.startswith(STATUSES):
                out.append('статус тикета «%s» вне словаря (открыт / в работе / на проверке / готов — vertical-task-slicing п.4)' % v[:40])
    for head, rows in tables(body):
        h = [clean(c) for c in head]
        if is_ticket_table(h):
            k = h.index('статус')
            for row in rows:
                v = clean(row[k]) if k < len(row) else ''
                if v and not v.startswith(STATUSES):
                    out.append('статус «%s» в таблице срезов вне словаря (vertical-task-slicing п.4)' % v[:40])
    return out


def sections(body, rx):
    """Тексты разделов (## … ####), чей заголовок подходит под rx, — до заголовка того же или старшего уровня."""
    out, lines = [], body.split('\n')
    for i, ln in enumerate(lines):
        h = re.match(r'(#{2,4})[ \t]+(.*)', ln)
        if h and re.search(rx, h.group(2), I):
            seg = []
            for nxt in lines[i + 1:]:
                h2 = re.match(r'(#{1,6})[ \t]', nxt)
                if h2 and len(h2.group(1)) <= len(h.group(1)):
                    break
                seg.append(nxt)
            out.append('\n'.join(seg))
    return out


def card_field(body, name):
    """Значение поля шапки карточки («Стадия», «Следующий шаг») — до первого раздела ##; поля нет — None."""
    top = re.split(r'^##[ \t]', body, maxsplit=1, flags=re.M)[0]
    f = re.search(r'^[ \t]*(?:[-*][ \t]+)?\**[ \t]*%s[ \t]*\**[ \t]*:(.*)$' % name, top, I | re.M)
    return re.sub(r'^[\s*`]+|[\s*`]+$', '', f.group(1)) if f else None


def stage_key(value):
    k = re.match(r'[\w-]+', value or '')
    return k.group(0).lower() if k else ''


def tickets_ok(s):
    """Раздел тикетов срезов: критерий приёмки со ссылкой на Т-n и статус — полями тикета или таблицей тикетов."""
    if re.search(r'^\s*(?:[-*]\s*)?\**\s*критерий при[её]мки\s*\**\s*[:—–].*' + REQ_ID, s, I | re.M) and \
            re.search(r'^\s*(?:[-*]\s*)?\**\s*статус\s*\**\s*[:—–]\s*\**\s*\S', s, I | re.M):
        return True
    return any(is_ticket_table([clean(c) for c in hd]) and any(re.search(REQ_ID, ' '.join(r)) for r in rows) for hd, rows in tables(s))


def stage_exit_missing(body, stage, lint=False):
    """Чего не хватает выходу стадии stage (customization-pipeline, «Проверяемый выход»); пусто — выход готов.
    Выходы накапливаются: на slicing нужен и выход analysis. Выход request (вердикт пре-гейта) — дисциплина.
    Выход build — все строки матрицы «готов»: его проверяют переход (move, --exit-ok) и стадии acceptance и done; подсказка
    хука (lint=True) на самой стадии build о нём молчит — «готов» ставится только по зелёному набору проверок."""
    k = STAGES.index(stage)
    out = []
    if k >= 1 and not any(re.search(REQ_ID, s) for s in sections(body, r'требовани')):
        out.append('раздел «Требования» с пунктами Т-n')
    if k < 2:
        return out
    if not any(tickets_ok(s) for s in sections(body, r'срез|тикет')):
        out.append('тикеты срезов: цель, критерий приёмки со ссылкой на Т-n, шов, статус, блокеры')
    mx = [(h, [r for r in rows if re.search(REQ_ID, r[0])]) for h, rows in
          (([clean(c) for c in hd], rs) for hd, rs in tables(body)) if is_matrix(h)]
    if not any(rows for _, rows in mx):
        out.append('матрица готовности со строками Т-n')
    if not any(re.search(FAIL_PATH, s, I) for s in re.findall(r'```mermaid\s*\n(.*?)```', body, re.S)):
        out.append('схема процесса — блок mermaid с путём отказа')
    if k >= 4 or (k == 3 and not lint):
        wait = []
        for h, rows in mx:
            st = h.index('статус') if 'статус' in h else None
            for r in rows:
                v = clean(r[st]) if st is not None and st < len(r) else ''
                if v != 'готов':
                    wait.append('%s (%s)' % (re.sub(r'[*`_]', '', r[0]).strip(), v or 'без статуса'))
        if wait:
            out.append('в матрице не «готов»: ' + ', '.join(wait))
    return out


def card_path(path):
    """Путь, где лежат карточки доработок: docs-project/, кроме журналов, ADR, портфеля и оглавления — у хука и генератора
    портфеля одно правило."""
    n = norm(path)
    return '/docs-project/' in n and not re.search(HISTORY, n) and not re.search(r'/(pipeline|index)\.md$', n)


def rejected(body):
    """Карточка закрыта с отказом (/ones-core:plan close): в шапке «Итог: отказ — причина»."""
    return (card_field(body, 'Итог') or '').lower().startswith('отказ')


def card_issues(body, known=()):
    """Карточка доработки (поле «Стадия:» в шапке): ключ из словаря, «Следующий шаг» до 60 символов, выход текущей стадии.
    known — уже найденные замечания к файлу: о схеме, если о ней сказала матрица, второй раз не говорится."""
    raw = card_field(body, 'Стадия')
    if raw is None or rejected(body):
        return []
    out, key, nxt = [], stage_key(raw), card_field(body, 'Следующий шаг')
    if key not in STAGES:
        out.append('ключ стадии «%s» вне словаря (%s — customization-pipeline)' % (raw[:30], ', '.join(STAGES)))
    if not nxt and key != 'done':
        out.append('в шапке карточки нет «Следующий шаг:» — одна строка до %d символов (customization-pipeline)' % NEXT_MAX)
    elif nxt and len(nxt) > NEXT_MAX:
        out.append('«Следующий шаг» — %d символов, а нужно до %d: он приходит подсказкой в поле ввода (customization-pipeline)'
                   % (len(nxt), NEXT_MAX))
    lost = stage_exit_missing(body, key, lint=True) if key in STAGES else []
    if any('схем' in x for x in known):
        lost = [x for x in lost if not x.startswith('схема процесса')]
    if lost:
        out.append('карточка на стадии «%s»: выходу стадии не хватает — %s (customization-pipeline)' % (key, '; '.join(lost)))
    return out


def portfolio_stale(root):
    """Карточка записана мимо /ones-core:plan, а портфель docs-project/pipeline.md уже есть — сверка gen-portfolio --check."""
    if not root or not os.path.isfile(os.path.join(root, 'docs-project', 'pipeline.md')):
        return []
    gp = os.path.join(HERE, '..', 'tools', 'pipeline', 'gen-portfolio.py')
    if not os.path.isfile(gp):
        return []
    r = subprocess.run([sys.executable, '-I', '-B', gp, '--root', root, '--check'], capture_output=True, timeout=60)
    return ['портфель docs-project/pipeline.md отстал от карточек — пересобери: /ones-core:plan без аргументов '
            '(gen-portfolio.py)'] if r.returncode == 1 else []


def git_committed(path):
    r = subprocess.run(['git', '-C', os.path.dirname(path), 'log', '-1', '--format=%H', '--', os.path.basename(path)], capture_output=True)
    return r.returncode == 0 and bool(r.stdout.strip())


def committed_text(path):
    """Текст файла в HEAD его репозитория; None — файла там нет."""
    r = subprocess.run(['git', '-C', os.path.dirname(path), 'show', 'HEAD:./' + os.path.basename(path)], capture_output=True)
    return r.stdout.decode('utf-8', 'replace').replace('\r\n', '\n') if r.returncode == 0 else None


def decision_section(body):
    sec = re.search(r'^#{2,3}\s*(решение|decision)\b.*?(?=^#{2}\s|\Z)', body, I | re.M | re.S)
    return sec.group(0) if sec else ''


def adr_issues(path, body, data):
    leaf = os.path.basename(path).lower()
    if leaf in ('readme.md', 'index.md', 'template.md', '0000-template.md'):
        return []
    out = []
    if not re.fullmatch(r'\d{4}-[a-z0-9]+(?:-[a-z0-9]+)*\.md', leaf):
        out.append('имя ADR — NNNN-slug.md, сквозной номер и латиница через дефис (decision-records-and-glossary п.3)')
    lost = [name for name, rx in ADR_SECTIONS if not re.search(rx, body, I | re.M)]
    if lost and data.get('tool_name') == 'Write':   # полнота — при заведении ADR; старые записи правкой статуса не корим
        out.append('в ADR нет разделов: %s (п.3)' % ', '.join(lost))
    ti = data.get('tool_input') or {}
    changed = False
    if data.get('tool_name') == 'Edit' and re.search(ADR_ACCEPTED, body, I) and \
            not re.search(r'статус|status', str(ti.get('old_string') or ''), I):
        sec, new = decision_section(body), str(ti.get('new_string') or '')
        changed = bool(sec and new.strip() and new in sec and git_committed(path))
    elif data.get('tool_name') == 'Write':   # файл перезаписан целиком: сверка с принятым текстом из git, пробелы не важны
        old = committed_text(path)
        changed = bool(old and re.search(ADR_ACCEPTED, old, I) and decision_section(old)
                       and decision_section(old).split() != decision_section(body).split())
    if changed:
        out.append('правится «Решение» принятого ADR — смена решения оформляется новым ADR со ссылкой «отменяет NNNN», у старого '
                   'меняется только статус (п.4)')
    return out


def skill_issues(path, body):
    m = re.match(r'^---\n(.*?)\n---', body, re.S)
    if not m:
        return ['у SKILL.md нет frontmatter с name и description (writing-for-agents п.2)']
    fm = m.group(1)
    d = re.search(r'^description:[ \t]*(.*)$', fm, re.M)
    desc = d.group(1).strip() if d else ''
    if d and desc in ('>', '|', '>-', '|-', ''):   # многострочное значение — строки с отступом сразу под ключом
        folded = []
        for ln in fm[d.end():].lstrip('\n').split('\n'):
            if ln[:1] not in (' ', '\t') or not ln.strip():
                break
            folded.append(ln.strip())
        desc = ' '.join(folded)
    desc = desc.strip('"\'')
    out = []
    if not desc:
        out.append('у скилла нет description — указатель, по которому скилл вызывается (writing-for-agents п.2)')
    elif len(desc) > 1024:
        out.append('description скилла длиннее 1024 символов (%d) — Claude Code его обрежет' % len(desc))
    n = re.search(r'^name:[ \t]*["\']?([^"\'\n]+)', fm, re.M)
    folder = os.path.basename(os.path.dirname(path))
    if n and n.group(1).strip() != folder:
        out.append('name скилла «%s» не совпадает с папкой «%s»' % (n.group(1).strip(), folder))
    return out


def deliverable_issue(path, body, data):
    leaf, n = os.path.basename(path).lower(), '/' + norm(path)
    if data.get('tool_name') != 'Write' or leaf in ('readme.md', 'claude.md') or \
            (re.search(r'/docs(-project)?/', n) and '/docs-project/deliverables/' not in n):
        return []   # docs/ и docs-project/ — база знаний (office-formats-for-people, таблица); deliverables — не база знаний (п.5)
    h1 = re.search(r'^#\s.*$', body, re.M)
    if re.search(DELIVERABLE_NAME, leaf[:-3], I) or (h1 and re.search(DELIVERABLE_H1, h1.group(0), I)):
        return ['похоже на деловой документ для людей (техпроект, отчёт, спецификация, смета, КП, презентация, регламент) — его '
                'делают в родном формате (.docx / .xlsx / .pptx) скиллом, а не в .md (office-formats-for-people); рабочее ТЗ в .md '
                'допустимо']
    return []


def name_issue(path, roots, data):
    """Новый файл в docs-project/ с именем не по шаблону (file-and-folder-names п.1): латиница, строчные, слова через дефис.
    Только при заведении (Write); INDEX.md, README.md и прочие имена по требованию инструмента — исключение (п.5)."""
    n = norm(path)
    if data.get('tool_name') != 'Write' or '/.obsidian/' in n or \
            not any(r and n.startswith(norm(r).rstrip('/') + '/docs-project/') for r in roots):
        return []
    leaf = os.path.basename(path)
    if leaf.lower() in TOOL_NAMES or re.fullmatch(DOC_NAME, leaf):
        return []
    return ['имя %s не по шаблону: латиница, строчные буквы, слова через дефис, по-английски (docs/process/file-and-folder-names.md '
            'п.1) — переименуй до того, как на файл появятся ссылки' % leaf]


def repo_root(path):
    """Корень git-репозитория, в котором лежит файл (папка или файл .git — так у рабочей копии worktree); нет — ''."""
    d = os.path.dirname(os.path.abspath(path))
    while d:
        if os.path.exists(os.path.join(d, '.git')):
            return d
        up = os.path.dirname(d)
        if up == d:
            return ''
        d = up
    return ''


def index_issue(path, roots, data):
    """Новый док в docs-project/ не внесён в её INDEX.md (project-knowledge-folder п.3): в проекте полноту оглавления
    health-check не стережёт — он есть только в мастере. Только при заведении дока (Write) и когда INDEX.md уже есть.
    roots — корень проекта и корень репозитория правленого файла (рабочая копия worktree лежит не в корне проекта)."""
    n = norm(path)
    root = next((r for r in roots if r and n.startswith(norm(r).rstrip('/') + '/docs-project/')), '')
    if data.get('tool_name') != 'Write' or not root or n.endswith('/index.md') or '/.obsidian/' in n:
        return []
    try:
        with open(os.path.join(root, 'docs-project', 'INDEX.md'), encoding='utf-8-sig', errors='replace') as f:
            text = f.read().lower()
    except OSError:
        return []
    leaf = os.path.basename(path)
    return [] if leaf.lower() in text else [
        'док %s не внесён в оглавление docs-project/INDEX.md — добавь строку о нём (project-knowledge-folder п.3)' % leaf]


def ref_issues(path, text, roots):
    """Ссылки на файлы, которых нет. Сверка — от корня репозитория правленого файла (в рабочей копии worktree новые файлы
    ветки есть только там) и от корня проекта, плагина и исходников конфигурации."""
    plug = os.environ.get('CLAUDE_PLUGIN_ROOT') or os.path.dirname(HERE)
    srcs = [v for k, v in os.environ.items() if k.upper().startswith('ONEC_PROJECT_SRC') and v]
    tops = [r for r in dict.fromkeys(roots) if r]
    out = []
    from urllib.parse import unquote
    for a, b in re.findall(REF, text, I):
        p = unquote(a or b).replace('\\', '/')   # ссылки markdown бывают в URL-кодировке: %20, %D0%91…
        if '<' in p or '*' in p or '{' in p:
            continue
        bases = ([os.path.dirname(path)] if b else []) + [x for r in tops for x in (r, os.path.join(r, 'plugin'))] + [plug] + srcs
        alt = [p] + [to + p[len(frm):] for frm, to in BUILT if p.startswith(frm)]
        if not any(os.path.exists(os.path.normpath(os.path.join(base, q))) for base in bases for q in alt):
            out.append(p)
    return ['ссылки на файлы, которых нет: %s — док описывает фактическое состояние (docs-match-reality)' % ', '.join(
        list(dict.fromkeys(out))[:5])] if out else []


def lint(path, body, data, root):
    """Замечания к файлу после правки: ([текст], [правило])."""
    ti = data.get('tool_input') or {}
    n = norm(path)
    new = str(ti.get('content') or ti.get('new_string') or '') + ''.join(
        str(e.get('new_string') or '') for e in ti.get('edits') or [] if isinstance(e, dict))
    issues, kinds = [], []
    roots = [repo_root(path), root]   # репозиторий файла первым: в рабочей копии worktree корень проекта — основная копия

    def add(kind, found):
        if found:
            issues.extend(found)
            kinds.append(kind)
    if n.endswith('/skill.md'):
        add('writing-for-agents', skill_issues(path, body))
    elif re.search(r'/docs-project/adr/[^/]+\.md$', n):
        add('decision-records-and-glossary', adr_issues(path, body, data))
    elif '/docs/' not in '/' + n:   # docs/ — правила ядра (образцы матрицы и тикетов) или журнал репозитория конфигурации
        add('readiness-matrix-and-process-diagram', matrix_issues(body))
        if '/docs-project/' in n:
            add('vertical-task-slicing', [x for x in ticket_issues(body) if x not in issues])
            add('project-knowledge-folder', index_issue(path, roots, data))
            add('file-and-folder-names', name_issue(path, roots, data))
        if card_path(path):
            add('customization-pipeline', card_issues(body, issues))
            if card_field(body, 'Стадия') is not None:
                add('customization-pipeline', portfolio_stale(root))
        add('office-formats-for-people', deliverable_issue(path, body, data))
    if not re.search(HISTORY, n):
        add('docs-match-reality', ref_issues(path, new, roots))
    return issues, kinds


def main():
    root = os.environ.get('CLAUDE_PROJECT_DIR')
    data = json.loads(sys.stdin.buffer.read().decode('utf-8', 'replace').lstrip('﻿') or '{}') or {}
    path = str((data.get('tool_input') or {}).get('file_path') or '')
    if not root or not path.lower().endswith('.md') or not os.path.isfile(path):
        return
    with open(path, encoding='utf-8-sig', errors='replace') as f:
        body = f.read().replace('\r\n', '\n')
    issues, kinds = lint(path, body, data, root)
    if not issues:
        return
    try:
        os.makedirs(os.path.join(root, 'logs'), exist_ok=True)
        with open(os.path.join(root, 'logs', 'answer-check.jsonl'), 'a', encoding='utf-8', newline='\n') as f:
            for k in kinds:
                f.write(json.dumps({'ts': int(time.time()), 'sid': str(data.get('session_id') or 'nosession'), 'shown': True,
                                    'kind': k, 'sample': os.path.basename(path)}, ensure_ascii=False) + '\n')
    except OSError:
        pass
    msg = 'lint-project-docs: в %s — %s. Поправь в этой же правке, если замечание верное.' % (
        os.path.basename(path), '; '.join('%d) %s' % (k + 1, x) for k, x in enumerate(issues[:8])))
    sys.stdout.buffer.write(json.dumps({'hookSpecificOutput': {'hookEventName': 'PostToolUse', 'additionalContext': msg}},
                                       ensure_ascii=False).encode('utf-8'))
    sys.stdout.flush()


def degraded(e):
    """Контракт деградации проверки после факта: сбой называется — строкой kind='DEGRADED' в logs/answer-check.jsonl и
    пометкой в systemMessage, а не молчанием (неотличимым от «замечаний нет»)."""
    root = os.environ.get('CLAUDE_PROJECT_DIR')
    if root:
        try:
            os.makedirs(os.path.join(root, 'logs'), exist_ok=True)
            with open(os.path.join(root, 'logs', 'answer-check.jsonl'), 'a', encoding='utf-8', newline='\n') as f:
                f.write(json.dumps({'ts': int(time.time()), 'sid': 'nosession', 'kind': 'DEGRADED', 'hook': 'lint-project-docs',
                                    'sample': str(e)[:200]}, ensure_ascii=False) + '\n')
        except OSError:
            pass
    sys.stdout.buffer.write(json.dumps({'systemMessage': 'lint-project-docs: DEGRADED — внутренняя ошибка, проверка дока пропущена: %s'
                                        % e}, ensure_ascii=False).encode('utf-8'))
    sys.stdout.flush()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        degraded(e)
    sys.exit(0)
