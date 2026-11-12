"""PostToolUseFailure: стоп при повторных сбоях инструментов — 3 подряд подсказка сменить подход, 5 — остановиться и спросить владельца.

По мотивам circuit-breaker Citadel (MIT, пересказ; docs/sources/citadel-review.md). Сбои считаются по хвосту журнала
сессии, своего файла состояния нет: подряд идущие ответы инструментов с is_error после последнего успешного ответа
или последнего запроса владельца. Отказ барьера (PreToolUse, код 2) события PostToolUseFailure не порождает, но в
журнале записан ответом с ошибкой — поэтому входит в серию, когда следом идёт настоящий сбой (зонд 05.11.2026).
Прерывание владельцем (is_interrupt) не считается. Хук ничего не блокирует; его собственный сбой — тихий выход 0.
Вывод — байты UTF-8: печать кириллицы через print на Windows приходила модели битой (зонд 05.11.2026).
С 05.11.2026 (решение владельца, по мотивам agent-usage-guard, MIT): сколько последних сбоев — один и тот же вызов
(подпись: инструмент и вход без description/timeout/run_in_background), пишется в logs/failure-streak.json проекта;
по нему барьер repeat-guard.py отказывает в тождественном повторе после 3 одинаковых сбоев подряд.
"""
import hashlib
import json
import os
import sys
import time

HINT_AT = 3
STOP_AT = 5
SAME_LIMIT = 3
TAIL_BYTES = 512 * 1024
SHOW = 3
STATE = os.path.join('logs', 'failure-streak.json')
SESSIONS_MAX = 32
SKIP_KEYS = {'description', 'timeout', 'run_in_background'}


def signature(tool, ti):
    """Подпись вызова: инструмент и вход без служебных полей, которые модель меняет при том же действии."""
    if isinstance(ti, dict):
        ti = {k: v for k, v in ti.items() if k not in SKIP_KEYS}
    raw = json.dumps({'tool': str(tool or ''), 'input': ti}, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]


def calls(records):
    """tool_use_id → (инструмент, вход) по записям ответа модели в журнале."""
    out = {}
    for rec in records:
        if rec.get('type') != 'assistant':
            continue
        for b in ((rec.get('message') or {}).get('content') or []):
            if isinstance(b, dict) and b.get('type') == 'tool_use':
                out[str(b.get('id') or '')] = (str(b.get('name') or ''), b.get('input'))
    return out


def same_tail(run, records, sig, current=''):
    """Сколько последних сбоев серии — тот же вызов (по подписи); текущий сбой берётся по его собственной подписи."""
    known = calls(records)
    n = 0
    for tid, _ in reversed(run):
        if tid and tid == current:
            n += 1
            continue
        name, ti = known.get(tid, (None, None))
        if name is None or signature(name, ti) != sig:
            break
        n += 1
    return n


def state_path(data):
    root = os.environ.get('CLAUDE_PROJECT_DIR') or str(data.get('cwd') or '') or os.getcwd()
    return os.path.join(root, STATE)


def load_state(path):
    try:
        with open(path, encoding='utf-8') as f:
            obj = json.load(f)
        return obj if isinstance(obj, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(path, sid, entry):
    """Запись через временный файл и подмену: параллельные сессии проекта не оставляют битый JSON."""
    seen = load_state(path)
    seen.pop(sid, None)
    seen[sid] = entry
    keep = dict(list(seen.items())[-SESSIONS_MAX:])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = '%s.%d.tmp' % (path, os.getpid())
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(keep, f)
    os.replace(tmp, path)


def text_of(content):
    """Текст ответа инструмента одной строкой до 140 знаков."""
    if isinstance(content, list):
        content = ' '.join(str(b.get('text') or '') for b in content if isinstance(b, dict))
    text = ' '.join(str(content or '').split())
    return text if len(text) <= 140 else text[:137] + '...'


def tail_records(path):
    """Записи хвоста журнала сессии; первая строка обрезанного хвоста отбрасывается."""
    with open(path, 'rb') as f:
        f.seek(0, 2)
        size = f.tell()
        f.seek(max(0, size - TAIL_BYTES))
        data = f.read()
    lines = data.split(b'\n')
    if size > TAIL_BYTES:
        lines = lines[1:]
    out = []
    for line in lines:
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if isinstance(rec, dict):
            out.append(rec)
    return out


def streak(records):
    """Ошибки подряд в конце журнала: [(tool_use_id, текст)]. Успех или запрос владельца начинают серию заново."""
    run = []
    for rec in records:
        if rec.get('type') != 'user':
            continue
        content = (rec.get('message') or {}).get('content')
        if isinstance(content, str):
            run = []
            continue
        if not isinstance(content, list):
            continue
        results = [b for b in content if isinstance(b, dict) and b.get('type') == 'tool_result']
        if not results:
            if any(isinstance(b, dict) and b.get('type') == 'text' for b in content):
                run = []
            continue
        for b in results:
            if b.get('is_error'):
                run.append((str(b.get('tool_use_id') or ''), text_of(b.get('content'))))
            else:
                run = []
    return run


def plural(n):
    if n % 10 == 1 and n % 100 != 11:
        return '%d сбой' % n
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return '%d сбоя' % n
    return '%d сбоев' % n


def message(run):
    n = len(run)
    if n < HINT_AT:
        return ''
    last = '; '.join('«%s»' % t for _, t in run[-SHOW:])
    if n < STOP_AT:
        return ('⚙ stop-on-failures: %s инструментов подряд. Последние: %s. Не повторяй тот же вызов: прочитай текст ошибки, '
                'проверь допущение (путь, ключ, право, состояние), смени подход или инструмент. Отказ барьера не обходить — '
                'выполнить его указание.' % (plural(n), last))
    return ('⚙ stop-on-failures: %s инструментов подряд. Остановись: новых попыток не делай. Опиши владельцу, что пробовал '
            'и на чём падает (последние: %s), и спроси окном вариантов, как быть.' % (plural(n), last))


def main():
    try:
        data = json.loads(sys.stdin.buffer.read().decode('utf-8'))
        if data.get('is_interrupt'):
            return
        records = tail_records(data.get('transcript_path'))
        run = streak(records)
        current = str(data.get('tool_use_id') or '')
        if not current or current not in {tid for tid, _ in run}:
            run.append((current, text_of(data.get('error'))))
        sid = str(data.get('session_id') or '')
        if sid:
            sig = signature(data.get('tool_name'), data.get('tool_input'))
            try:
                save_state(state_path(data), sid, {'sig': sig, 'count': same_tail(run, records, sig, current),
                                                   'tool': str(data.get('tool_name') or ''), 'ts': int(time.time())})
            except OSError:
                pass
        text = message(run)
        if text:
            out = {'hookSpecificOutput': {'hookEventName': 'PostToolUseFailure', 'additionalContext': text}}
            sys.stdout.buffer.write((json.dumps(out, ensure_ascii=False) + '\n').encode('utf-8'))
    except Exception:
        return


if __name__ == '__main__':
    main()
    sys.exit(0)
