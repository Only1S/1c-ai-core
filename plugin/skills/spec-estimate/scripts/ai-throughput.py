"""Фактическая скорость ИИ по журналам сессий Claude Code: активные часы, код в час, расход недельного лимита.

Использование:
  python ai-throughput.py [--projects-dir <папка>] [--only <подстрока имени папки>]
                          [--week-start <ГГГГ-ММ-ДДTЧЧ:ММ:СС+00:00> --week-used <проценты>]

Папка журналов по умолчанию — projects в CLAUDE_CONFIG_DIR или ~/.claude. Читает только журналы, наружу
ничего не отправляет и не печатает их содержимое: на выходе одни числа.

Активное время — сумма промежутков между записями журнала не длиннее 5 минут: модель думает или ждёт
инструмент; более длинная пауза считается уходом человека. Строки — всё, что записано в .bsl инструментами
Write и Edit, вместе с переписываниями, поэтому это верхняя граница, а не размер готового кода. Правки через
MCP-серверы в строки не входят.

С --week-start и --week-used: начало текущей недели тарифа и процент её расхода показывают, сколько активных
часов даёт тариф за неделю при нынешнем способе работы.

Коды выхода: 0 — посчитано; 2 — нет папки журналов или неверная дата.
"""
import argparse
import datetime as dt
import glob
import json
import os
import sys

GAP = 300


def stamp(value):
    return dt.datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()


def code_lines(block):
    """Строки .bsl в одном вызове инструмента."""
    name = block.get('name')
    data = block.get('input') or {}
    if not str(data.get('file_path') or '').lower().endswith('.bsl'):
        return 0
    if name == 'Write':
        return str(data.get('content') or '').count('\n') + 1
    if name == 'Edit':
        return str(data.get('new_string') or '').count('\n') + 1
    return 0


def scan(path, week_start, into):
    previous = None
    seen = set()
    with open(path, encoding='utf-8', errors='replace') as lines:
        for line in lines:
            try:
                record = json.loads(line)
            except ValueError:
                continue
            when = record.get('timestamp')
            if not when or record.get('type') not in ('assistant', 'user'):
                continue
            current = stamp(when)
            if previous is not None and 0 <= current - previous <= GAP:
                into['active'] += current - previous
                if week_start is not None and current >= week_start:
                    into['week_active'] += current - previous
            previous = current
            if record['type'] != 'assistant':
                continue
            message = record.get('message') or {}
            key = message.get('id')
            if key and key not in seen:
                seen.add(key)
                into['output'] += (message.get('usage') or {}).get('output_tokens') or 0
            content = message.get('content')
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get('type') == 'tool_use':
                        into['calls'] += 1
                        into['lines'] += code_lines(block)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    base = os.environ.get('CLAUDE_CONFIG_DIR') or os.path.join(os.path.expanduser('~'), '.claude')
    ap = argparse.ArgumentParser(description='Скорость ИИ по журналам сессий')
    ap.add_argument('--projects-dir', default=os.path.join(base, 'projects'), help='папка журналов Claude Code')
    ap.add_argument('--only', default='', help='только папки, в имени которых есть эта подстрока')
    ap.add_argument('--week-start', help='начало текущей недели тарифа, ISO с часовым поясом')
    ap.add_argument('--week-used', type=float, help='процент недельного лимита, истраченный с начала недели')
    a = ap.parse_args()
    if not os.path.isdir(a.projects_dir):
        print('Нет папки журналов: %s' % a.projects_dir)
        return 2
    try:
        week_start = stamp(a.week_start) if a.week_start else None
    except ValueError:
        print('Неверная дата --week-start: %s' % a.week_start)
        return 2
    if (week_start is None) != (a.week_used is None):
        print('Неделя тарифа считается по двум ключам вместе: --week-start и --week-used')
        return 2
    if a.week_used is not None and a.week_used <= 0:
        print('--week-used должен быть больше нуля: при нуле расход недели в часы не пересчитать')
        return 2
    print('| Проект | Активных часов | Вызовов | Строк BSL | Строк в час | Выход, млн токенов |')
    print('|---|---:|---:|---:|---:|---:|')
    total = dict(active=0.0, week_active=0.0, output=0, calls=0, lines=0)
    small = dict(active=0.0, week_active=0.0, output=0, calls=0, lines=0)
    small_count = 0

    def line(title, row):
        hours = row['active'] / 3600
        print('| %s | %.1f | %d | %d | %.0f | %.1f |' % (title, hours, row['calls'], row['lines'], row['lines'] / hours if hours else 0, row['output'] / 1e6))

    for name in sorted(os.listdir(a.projects_dir)):
        folder = os.path.join(a.projects_dir, name)
        if a.only not in name or not os.path.isdir(folder):
            continue
        row = dict(active=0.0, week_active=0.0, output=0, calls=0, lines=0)
        for path in glob.glob(os.path.join(folder, '*.jsonl')) + glob.glob(os.path.join(folder, '*', 'subagents', '*.jsonl')):
            try:
                scan(path, week_start, row)
            except OSError:
                continue
        for key in total:
            total[key] += row[key]
        if row['active'] < 3600:
            small_count += 1
            for key in small:
                small[key] += row[key]
            continue
        line(name, row)
    if small_count:
        line('остальные, меньше часа каждый (%d)' % small_count, small)
    hours = total['active'] / 3600
    if hours:
        print('\nИтого: %.0f активных часов, %.0f вызовов в час, %.0f строк BSL в час, %.0f тыс. выходных токенов в час'
              % (hours, total['calls'] / hours, total['lines'] / hours, total['output'] / 1e3 / hours))
    if week_start is not None:
        week = total['week_active'] / 3600
        print('С начала недели тарифа: %.1f активных часов при %g%% лимита, вся неделя — около %.0f часов из 168'
              % (week, a.week_used, week / a.week_used * 100))
    return 0


if __name__ == '__main__':
    sys.exit(main())
