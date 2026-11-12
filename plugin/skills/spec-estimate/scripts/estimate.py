"""Расчёт оценки ТЗ для ИИ, работающего без остановки: три точки по работам, итог и календарь.

Использование:
  python estimate.py --input <оценка.json>

Формат файла (часы — активные часы ИИ: модель думает или ждёт инструмент):
  {
    "title": "Название ТЗ",
    "variants": ["Как в ТЗ", "На типовой"],
    "factor": 1.0,            поправка из калибровки: медиана «факт / оценка», по умолчанию 1
    "weekly_hours": 60,       сколько активных часов в неделю даёт тариф; нет — календарь по тарифу не считается
    "rows": [
      {"group": "Отчёт", "work": "Раздел 1", "hours": [[8, 12, 20], [6, 10, 16]]}
    ]
  }
В "hours" — по тройке (лучший случай, вероятный, худший) на каждый вариант.

Итог по работе — (о + 4н + х) / 6. Коридор — сумма середин «о–н» и «н–х»: сумма крайних точек
завышает размах, потому что все работы сразу не бывают лучшими или худшими.

Коды выхода: 0 — посчитано; 2 — файл не читается или в нём ошибка.
"""
import argparse
import json
import sys


def expected(t):
    return (t[0] + 4 * t[1] + t[2]) / 6


def check(data):
    """Список ошибок формата; пустой — можно считать."""
    errors = []
    variants = data.get('variants') or []
    rows = data.get('rows') or []
    if not variants:
        errors.append('нет variants')
    if not rows:
        errors.append('нет rows')
    for i, r in enumerate(rows, 1):
        if not isinstance(r, dict):
            errors.append('строка %d: нужен объект с group, work и hours' % i)
            continue
        name = r.get('work') or 'строка %d' % i
        if not r.get('group'):
            errors.append('%s: нет group' % name)
        hours = r.get('hours') or []
        if len(hours) != len(variants):
            errors.append('%s: троек %d, вариантов %d' % (name, len(hours), len(variants)))
            continue
        for t in hours:
            if len(t) != 3 or not all(isinstance(x, (int, float)) and x >= 0 for x in t):
                errors.append('%s: нужна тройка неотрицательных чисел, есть %s' % (name, t))
            elif not t[0] <= t[1] <= t[2]:
                errors.append('%s: нарушен порядок о <= н <= х: %s' % (name, t))
    return errors


def totals(data):
    """По каждому варианту: часы по группам, итог, нижняя и верхняя граница коридора."""
    factor = data.get('factor') or 1
    out = []
    for i, name in enumerate(data['variants']):
        groups = {}
        low = high = 0
        for r in data['rows']:
            t = r['hours'][i]
            groups[r['group']] = groups.get(r['group'], 0) + expected(t) * factor
            low += (t[0] + t[1]) / 2 * factor
            high += (t[1] + t[2]) / 2 * factor
        out.append({'name': name, 'groups': groups, 'total': sum(groups.values()), 'low': low, 'high': high})
    return out


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser(description='Оценка ТЗ в активных часах ИИ')
    ap.add_argument('--input', required=True, help='файл оценки в JSON')
    a = ap.parse_args()
    try:
        with open(a.input, encoding='utf-8-sig') as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        print('Файл оценки не читается: %s' % e)
        return 2
    errors = check(data)
    if errors:
        print('Ошибки в файле оценки:')
        for e in errors:
            print('  ' + e)
        return 2
    result = totals(data)
    print('# %s' % (data.get('title') or 'Оценка'))
    print('\n| Часть | ' + ' | '.join(v['name'] for v in result) + ' |')
    print('|---|' + '---:|' * len(result))
    for g in result[0]['groups']:
        print('| %s | %s |' % (g, ' | '.join('%.0f' % v['groups'][g] for v in result)))
    print('| **Итого, активных часов** | %s |' % ' | '.join('**%.0f**' % v['total'] for v in result))
    print('| Коридор | %s |' % ' | '.join('%.0f–%.0f' % (v['low'], v['high']) for v in result))
    print('| Суток без единой паузы | %s |' % ' | '.join('%.1f' % (v['total'] / 24) for v in result))
    weekly = data.get('weekly_hours')
    if weekly:
        print('| Недель при лимите %g ч в неделю | %s |' % (weekly, ' | '.join('%.1f' % (v['total'] / weekly) for v in result)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
