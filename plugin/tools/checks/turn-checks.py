"""turn-checks.py — проверки хода только на чтение: что уже проверено в текущем ходе и чего гейт конца хода ещё потребует.

Его зовут инструмент ядра turn_checks (мод hooks/core-tools.tsx) и панель «Доработка» (hooks/work-pane.tsx). Ход читается и
судится кодом самого гейта конца хода — hooks/stop-guard.py (turn_calls, gate_missing, gate_mode, runs_skill_script,
check_ran, GENERATORS), своей копии правил здесь нет: ответ инструмента и вердикт гейта не расходятся.

Запуск:
    python -I -B turn-checks.py --root <проект> --session <ид сессии> [--agent <ид помощника>] [--answer-stdin]
      --answer-stdin   итоговый ответ хода — на stdin (панель после хода); принимается ради совместимости с панелью:
                       строки «Маршрут» и «След инструментов» сняты 31.10.2026, ответ ни с чем не сверяется
Читает: журнал хода <CLAUDE_CONFIG_DIR или ~/.claude>/projects/*/<сессия>.jsonl, ход помощника —
    .../<сессия>/subagents/**/agent-<ид>.jsonl; <проект>/logs/gate-state.json (взведённые правки .bsl), logs/gate-evidence.md
    (след прогона), logs/answer-check.jsonl (замечания проверок конца хода), .v8-project.json (режим гейта stopGate).
Пишет: ничего — ни журналов logs/, ни состояния гейта (его gate_state и log_answer не зовутся), ни кэша байткода.
Печатает JSON (ASCII) {turn, gate, evidence, observations}. Коды выхода: 0 — ответ напечатан (в том числе «ход не найден»);
2 — ошибка вызова (нет --root, ид сессии или помощника не из букв, цифр, «-», «_», «.»).
"""
import argparse
import importlib.util
import json
import os
import re
import sys

sys.dont_write_bytecode = True   # гейт грузится из файла: без этого рядом с хуками появился бы __pycache__
HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(HERE, '..', '..', 'hooks', 'stop-guard.py')
ID = r'[\w.-]{1,128}'
TAIL = 512 * 1024        # журнал замечаний читается с хвоста, как в answer-feedback
SAMPLE_MAX = 160
I = re.IGNORECASE
# запуски своих харнессов плагина — сведения о ходе; гейт конца хода их не требует
HARNESS = {'gate-evidence': 'след прогона gate-evidence', 'run-tests': 'тесты YAXUnit (run-tests)',
           'run-scenario': 'сценарий Vanessa (run-scenario)'}


def load_gate():
    spec = importlib.util.spec_from_file_location('stop_guard', HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def text(path):
    try:
        with open(path, encoding='utf-8-sig', errors='replace') as f:
            return f.read()
    except OSError:
        return None


def transcript(sid, agent):
    """Журнал хода: основной — <projects>/*/<сессия>.jsonl, помощника — <projects>/*/<сессия>/subagents/**/agent-<ид>.jsonl."""
    base = os.environ.get('CLAUDE_CONFIG_DIR') or os.path.join(os.path.expanduser('~'), '.claude')
    projects = os.path.join(base, 'projects')
    try:
        dirs = sorted(os.listdir(projects))
    except OSError:
        return None
    for d in dirs:
        if not agent:
            f = os.path.join(projects, d, sid + '.jsonl')
            if os.path.isfile(f):
                return f
            continue
        want = 'agent-%s.jsonl' % agent
        for top, _, files in os.walk(os.path.join(projects, d, sid, 'subagents')):
            if want in files:
                return os.path.join(top, want)
    return None


def checks_ran(sg, calls, gs, root):
    """Проверки, которые уже были в ходе. Стандарты — то, что засчитывает гейт: рядом с пробной правкой модуля вызов
    убирает одно из требований гейта (своей копии правила о v8std и 1c-standards здесь нет). Считается число требований,
    а не их тексты: вторая правка меняет текст требования validate_module, но требований не убавляет."""
    probe = ('Edit', {'file_path': os.path.join(root, 'CommonModules', 'ПробаХода', 'Ext', 'Module.bsl')}, None)
    alone = len((sg.gate_missing([probe], gs, root) or ([], ''))[0])
    names = '|'.join(sorted({x for v in sg.GENERATORS.values() for x in v.split('|')}))
    out = []
    for name, inp, res in calls:
        inp = inp if isinstance(inp, dict) else {}
        err = bool(res and res[0])
        if re.match(r'^mcp__.*bsl-context.*__validate_module$', name, I) and inp.get('path'):
            got = re.search(r'"valid"\s*:\s*(true|false)', res[1]) if sg.check_ran(res) else None
            leaf = str(inp.get('path')).replace('\\', '/').rstrip('/').split('/')
            out.append({'what': 'validate_module %s — %s' % ('/'.join(leaf[-3:]), ('valid' if got.group(1) == 'true' else 'есть ошибки')
                                                                   if got else 'сервер не проверил'),
                        'ok': (got.group(1) == 'true') if got else False})
            continue
        if len((sg.gate_missing([probe, (name, inp, res)], gs, root) or ([], ''))[0]) < alone:
            out.append({'what': 'стандарты — %s' % (name if name != 'Skill' else 'скилл ' + str(inp.get('skill'))), 'ok': not err})
            continue
        if name in ('Bash', 'PowerShell'):
            cmd = str(inp.get('command') or '')
            for v in sg.runs_skill_script(cmd, names):
                out.append({'what': 'парный валидатор %s' % v, 'ok': not err})
            for v in sg.runs_skill_script(cmd, 'gate-evidence|run-tests|run-scenario'):
                out.append({'what': HARNESS[v], 'ok': not err})
    return out


def turn(sg, root, sid, agent, answer):
    path = transcript(sid, agent)
    got = sg.turn_calls(path) if path else None
    if got is None:
        return {'found': False, 'calls': 0, 'edits': None, 'missing': [], 'ran': []}
    calls = got[0]
    gs = sg.guard_skills()
    res = sg.gate_missing(calls, gs, root)
    return {'found': True, 'calls': len(calls), 'edits': res[1] if res else None, 'missing': res[0] if res else [],
            'ran': checks_ran(sg, calls, gs, root)}


def armed(root, sid):
    """Взведённые правки .bsl этой сессии — тем же отбором, что у гейта конца хода (чужие и nosession не считаются)."""
    try:
        st = json.loads(text(os.path.join(root, 'logs', 'gate-state.json')) or '{}')
    except ValueError:
        return []
    out = []
    for k, v in (st.items() if isinstance(st, dict) else []):
        if k != sid or k == 'nosession':
            continue
        out += [a for a in (v if isinstance(v, list) else [v]) if isinstance(a, str) and a and a not in out]
    return out


def evidence(root, sid):
    """Последний прогон из logs/gate-evidence.md (его пишет gate-evidence.py): метка, сессия, три категории следа."""
    body = text(os.path.join(root, 'logs', 'gate-evidence.md')) or ''
    heads = list(re.finditer(r'^## Прогон (.+?) · сессия (.+?)[ \t]*$', body, re.M))
    if not heads:
        return None
    h = heads[-1]
    part = body[h.end():]
    pick = lambda kind: [x.strip() for x in re.findall(r'^\[gate %s: (.*)\]\s*$' % kind, part, re.M)]
    return {'stamp': h.group(1).strip(), 'session': h.group(2).strip(), 'own': h.group(2).strip() in (sid, 'все сессии'),
            'checked': pick('checked'), 'skipped': pick('skipped'), 'notVerified': pick('not_verified')}


def observations(root, sid):
    """Замечания проверок конца хода этой сессии (logs/answer-check.jsonl, пишет stop-guard): вид, сколько раз, последний пример."""
    path = os.path.join(root, 'logs', 'answer-check.jsonl')
    try:
        with open(path, 'rb') as f:
            size = f.seek(0, 2)
            f.seek(max(0, size - TAIL))
            chunk = f.read().decode('utf-8', 'replace')
    except OSError:
        return []
    found = {}
    for ln in chunk.splitlines():
        try:
            o = json.loads(ln)
        except ValueError:
            continue
        if not isinstance(o, dict) or str(o.get('sid') or '') != sid or not o.get('kind'):
            continue
        k = str(o['kind'])
        found[k] = {'kind': k, 'count': found.get(k, {}).get('count', 0) + 1, 'sample': str(o.get('sample') or '')[:SAMPLE_MAX]}
    return list(found.values())


def main():
    ap = argparse.ArgumentParser(description='Проверки хода только на чтение — тем же кодом, что гейт конца хода.')
    ap.add_argument('--root', required=True, help='корень проекта (там logs/ и .v8-project.json)')
    ap.add_argument('--session', required=True, help='ид сессии — имя журнала <ид>.jsonl')
    ap.add_argument('--agent', default='', help='ид помощника: судить его ход по его журналу')
    ap.add_argument('--answer-stdin', action='store_true', help='итоговый ответ хода — на stdin')
    args = ap.parse_args()
    if not re.fullmatch(ID, args.session) or (args.agent and not re.fullmatch(ID, args.agent)) or '..' in args.session + args.agent:
        print('ид сессии и помощника — буквы, цифры, «-», «_», «.»', file=sys.stderr)
        return 2
    answer = sys.stdin.buffer.read().decode('utf-8', 'replace') if args.answer_stdin else None
    root = os.path.abspath(args.root)
    sg = load_gate()
    print(json.dumps({'turn': turn(sg, root, args.session, args.agent, answer),
                      'gate': {'mode': sg.gate_mode(root), 'armed': armed(root, args.session)},
                      'evidence': evidence(root, args.session), 'observations': observations(root, args.session)}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
