"""PreToolUse: отказ на тождественный повтор вызова, который упал 3 раза подряд с теми же данными (часть 13-го контура).

Решение владельца 05.11.2026, по мотивам agent-usage-guard (MIT, пересказ; docs/sources/claude-code-mods-review.md).
Сбои считает failure-streak.py на PostToolUseFailure и пишет в logs/failure-streak.json проекта подпись последнего
сбойного вызова и сколько раз подряд упал именно он. Здесь — быстрая сверка подписи с этим файлом; совпало и счёт
не меньше 3 — перепроверка по хвосту журнала сессии: серию не прервал ни успешный ответ, ни запрос владельца.
Подтвердилось — отказ: «прочитай ошибку и измени вызов или подход». Отказ барьера PreToolUse события
PostToolUseFailure не даёт, поэтому серию из одних отказов барьеров этот хук не видит. Любой собственный сбой — пропуск.
"""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def streak_module():
    spec = importlib.util.spec_from_file_location('failure_streak', os.path.join(HERE, 'failure-streak.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def deny(reason):
    out = {'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'deny',
                                  'permissionDecisionReason': reason}}
    sys.stdout.buffer.write(json.dumps(out, ensure_ascii=False).encode('utf-8'))


def main():
    data = json.loads(sys.stdin.buffer.read().decode('utf-8'))
    sid = str(data.get('session_id') or '')
    if not sid:
        return
    fs = streak_module()
    entry = fs.load_state(fs.state_path(data)).get(sid) or {}
    if int(entry.get('count') or 0) < fs.SAME_LIMIT:
        return
    sig = fs.signature(data.get('tool_name'), data.get('tool_input'))
    if sig != entry.get('sig'):
        return
    records = fs.tail_records(data.get('transcript_path'))
    run = fs.streak(records)
    same = fs.same_tail(run, records, sig)
    if same < fs.SAME_LIMIT:
        return
    last = run[-1][1] if run else ''
    times = 'раза' if 2 <= same % 10 <= 4 and not 12 <= same % 100 <= 14 else 'раз'
    deny('stop-on-failures: этот же вызов %s упал %d %s подряд с теми же данными (последняя ошибка: «%s») — повтор отклонён. '
         'Прочитай текст ошибки и измени вызов или подход. Причина вне твоих рук (сервер не поднят, нет доступа, нужен вход) — '
         'скажи владельцу, что нужно сделать, окном вариантов.' % (data.get('tool_name'), same, times, last))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
