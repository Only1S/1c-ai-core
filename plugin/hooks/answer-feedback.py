"""UserPromptSubmit: подсказка в следующем ходе — что проверки конца хода отметили в прошлых ответах этой сессии.

Читает logs/answer-check.jsonl (строки этой сессии, дописанные после прошлого показа), печатает короткий перечень
«правило — что найдено — как исправить» и запоминает, докуда показано (logs/answer-feedback.json). Так наблюдение
stop-guard, которое видит только владелец (systemMessage), доходит до модели (решение владельца 17.10.2026, выпуск 4.8.0).
Строки с пометкой shown (подсказку модель уже получила в момент правки) не повторяются. Молчит, когда нечего сказать;
ошибка — молча.
"""
import json
import os
import sys

FIX = {
    'questions-as-options': ('process/questions-as-options', 'вопрос владельцу — окном вариантов, рекомендуемый вариант первым'),
    'work-through-tools': ('tools/work-through-tools', 'называть только те инструменты, что вызывались в этом ходе'),
    'two-axis-code-review': ('code/two-axis-code-review', 'итог ревью — два вердикта: «Стандарты:» и «Спека:»'),
    'tool-calls-not-chat-text': ('process/tool-calls-not-chat-text', 'выполняемое — настоящим вызовом инструмента, не текстом в ответе'),
    'design-before-code': ('design/design-before-code', 'до создания объектов — проработка по пунктам и согласование окном вариантов'),
    'five-role-design-review': ('design/five-role-design-review', 'до реализации — консилиум пяти ролей и единый план'),
    'bug-diagnosis-loop': ('code/bug-diagnosis-loop', 'баг — сперва автоматическое репро и красный тест; метки [DEBUG-…] вычистить'),
    'journal-placement': ('process/journal-placement', 'правки конфигурации — в docs/worklog.md и docs/changelog.md её репозитория'),
    'config-git-forks-and-merges': ('platform/config-git-forks-and-merges', 'перенос между ветками — merge или cherry-pick, не копированием'),
    'ask-before-changing': ('process/ask-before-changing', 'общие модули, роли, корень — после «да» владельца; на вопрос — сперва ответ'),
    'token-economy-and-local-tools': ('process/token-economy-and-local-tools', 'читать точечно, прочитанное не перечитывать'),
    'probe-tool-capabilities': ('tools/probe-tool-capabilities', 'флаг программы — подтвердить --help или прогоном, потом советовать'),
    'naming-and-module-design': ('code/naming-and-module-design', 'постфикс общего модуля — по его флагам (std469); переименовать до коммита'),
    'requirements-by-interview': ('design/requirements-by-interview', 'факт добывается инструментом, владельцу — только решения'),
    'stop-gate-warn': ('tools/full-checker-set-before-done', 'после правки 1С — полный набор проверок в том же ходе'),
    'stop-gate-skipped': ('tools/full-checker-set-before-done', 'гейт пропустил ход без проверок — сделай недостающие проверки сейчас'),
}
TAIL = 512 * 1024   # новая сессия читает журнал не с начала: строки сессии появляются только после её старта


def main():
    root = os.environ.get('CLAUDE_PROJECT_DIR')
    if not root:
        return
    data = json.loads(sys.stdin.buffer.read().decode('utf-8', 'replace').lstrip('﻿') or '{}') or {}
    sid = str(data.get('session_id') or '')
    log = os.path.join(root, 'logs', 'answer-check.jsonl')
    if not sid or not os.path.isfile(log):
        return
    state_path = os.path.join(root, 'logs', 'answer-feedback.json')
    try:
        with open(state_path, encoding='utf-8-sig') as f:
            state = json.load(f)
        state = state if isinstance(state, dict) else {}
    except (OSError, ValueError):
        state = {}
    with open(log, 'rb') as f:
        size = f.seek(0, 2)
        pos = state.get(sid)
        pos = pos if isinstance(pos, int) and 0 <= pos <= size else max(0, size - TAIL)
        f.seek(pos)
        chunk = f.read()
    # последняя строка могла быть дописана не до конца — её дочитает следующий ход
    cut = chunk.rfind(b'\n') + 1
    found = {}
    for line in chunk[:cut].decode('utf-8', 'replace').splitlines():
        try:
            o = json.loads(line)
        except ValueError:
            continue
        if not isinstance(o, dict) or o.get('sid') != sid or o.get('shown') or o.get('kind') not in FIX:
            continue
        rec = found.setdefault(o['kind'], [0, ''])
        rec[0] += 1
        rec[1] = str(o.get('sample') or '')
    state[sid] = pos + cut
    if len(state) > 50:   # старые сессии не копятся: остаются 50 последних по месту в журнале
        state = dict(sorted(state.items(), key=lambda kv: kv[1] if isinstance(kv[1], int) else 0)[-50:])
    try:
        with open(state_path, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(state, f, ensure_ascii=False, indent=1)
    except OSError:
        pass
    if not found:
        return
    lines = ['⚠ answer-feedback: проверки конца хода отметили в прошлых ответах этой сессии нарушения правил ядра. Если это ещё '
             'актуально — исправь в этом ходе; если срабатывание ложное — скажи об этом владельцу одной строкой.']
    for k, (kind, (count, sample)) in enumerate(found.items(), 1):
        doc, fix = FIX[kind]
        lines.append('%d) %s (docs/%s.md)%s — %s. Найдено: %s' % (k, kind, doc, ' ×%d' % count if count > 1 else '', fix, sample[:220]))
    sys.stdout.buffer.write(('\n'.join(lines[:9]) + '\n').encode('utf-8'))
    sys.stdout.flush()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
