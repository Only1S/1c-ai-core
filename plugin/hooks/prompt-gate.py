"""UserPromptSubmit: правила ядра (tools-gate.md) в контекст — целиком один раз на сессию и после сжатия, дальше одна строка.

Текст правил — около 8 тысяч знаков; вставленный в каждый запрос и каждое уведомление, он занимал четверть контекста длинной
сессии (замер 31.10.2026: 46 вставок). Уведомлениям о фоновых задачах и событиях приложения не отвечаем ничем: это не запрос
владельца. Сжатие видно по журналу сессии: строк compact_boundary стало больше — текст правил пропал из контекста, вставляем снова.
Сбой — полный текст: лучше лишние знаки, чем модель без правил. Исключение — первый запрос новой сессии: журнала ещё нет,
сжатий не было, сессия запоминается с нулём (иначе правила целиком приходили два хода подряд, живая проба 04.11.2026).
Запись «что уже показано» — logs/prompt-gate.json проекта.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEXT = os.path.join(HERE, 'tools-gate.md')
STATE = os.path.join('logs', 'prompt-gate.json')
SESSIONS_MAX = 32
SHORT = '⚙ Правила ядра из начала сессии действуют: факты — вызовом инструмента, скиллы обязательны, до кода — проработка и согласование.'
BLOCKS = re.compile(r'<(system-reminder|task-notification|side-sessions-event|ci-monitor-event)>[\s\S]*?</\1>')
NOTICES = ('<task-notification>', '<side-sessions-event>', '<ci-monitor-event>')


def say(text):
    sys.stdout.buffer.write((text.strip() + '\n').encode('utf-8'))


def full_text():
    with open(TEXT, encoding='utf-8-sig') as f:
        return f.read()


def automated(prompt):
    """Запрос целиком из служебных блоков и среди них есть уведомление: владелец ничего не написал."""
    return any(n in prompt for n in NOTICES) and not BLOCKS.sub('', prompt).strip()


def compactions(path):
    """Сколько раз сессия сжималась: записи журнала с subtype compact_boundary (формат сверен с журналом приложения
    04.11.2026), а не любое упоминание слова в тексте; журнала нет или не читается — None, тогда правила целиком."""
    try:
        count = 0
        with open(path, 'rb') as f:
            for line in f:
                if b'compact_boundary' not in line:
                    continue
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                if isinstance(record, dict) and record.get('subtype') == 'compact_boundary':
                    count += 1
        return count
    except (OSError, TypeError, ValueError):
        return None


def load(path):
    try:
        with open(path, encoding='utf-8') as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def save(path, seen, sid, count):
    seen.pop(sid, None)
    seen[sid] = count
    keep = dict(list(seen.items())[-SESSIONS_MAX:])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # запись во временный файл и подмена: параллельные сессии проекта не оставляют битый JSON
    tmp = '%s.%d.tmp' % (path, os.getpid())
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(keep, f)
    os.replace(tmp, path)


def main():
    try:
        data = json.loads(sys.stdin.buffer.read().decode('utf-8'))
        if automated(str(data.get('prompt') or '')):
            return
        sid = str(data.get('session_id') or '')
        root = os.environ.get('CLAUDE_PROJECT_DIR') or str(data.get('cwd') or '') or os.getcwd()
        path = os.path.join(root, STATE)
        seen = load(path)
        count = compactions(data.get('transcript_path'))
        if count is None:
            if not sid or sid in seen:
                say(full_text())
                return
            # первый запрос новой сессии: журнал приложение ещё не записало (живая проба 04.11.2026), сжатий не было
            count = 0
        known = sid != '' and seen.get(sid) == count
        save(path, seen, sid, count)
        say(SHORT if known else full_text())
    except Exception as e:   # контракт деградации: хук не падает, правила доходят
        sys.stderr.write('prompt-gate: %s\n' % e)
        say(full_text())


if __name__ == '__main__':
    main()
