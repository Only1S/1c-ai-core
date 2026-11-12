"""gate-evidence.py — след прогона проверок и СНЯТИЕ взведённого гейта качества.

Зачем. full-checker-set-before-done п.9 требует отчёт из трёх категорий (проверено · пропущено ·
НЕ проверено), но носителем был текст ответа: после сессии от него не оставалось ничего, и
«прогнал ли я полный сет по этой правке» нельзя было ни проверить, ни опровергнуть. Скрипт даёт
следу файловый носитель и одновременно снимает взвод, который поставил контур 1 (правка .bsl).
Приём следа с машиночитаемыми строками — Romandredan/1c-quality-gate (MIT, (c) 2026 romandredan,
их `quality evidence`); формат и код наши, категории — наши собственные из п.9.

Взвод ставит plugin/hooks/validate-bsl.py (PostToolUse на .bsl), читает stop-guard в конце хода.

Запуск:
    python tools/checks/gate-evidence.py --checked "bsl-analyzer: чисто" --not-verified "компиляция: нет тестовой базы"
    python tools/checks/gate-evidence.py --list

Параметры (каждый списочный принимает несколько значений и может повторяться):
    --checked <строки>       что ПРОВЕРЕНО: инструмент и результат («bsl-analyzer: чисто»)
    --skipped <строки>       что ПРОПУЩЕНО и почему («XML не затронут»)
    --not-verified <строки>  что НЕ проверено и почему («нет тестовой базы») — категория обязательна,
                             и пустой она быть не может, если что-то применимо и не выполнено
    --files <пути>           какие файлы закрываются следом; по умолчанию — все взведённые
    --session-id <ид>        сессия (по умолчанию из CLAUDE_SESSION_ID; без неё — все сессии сразу)
    --root <папка>           корень, где лежит logs/ (по умолчанию — папка проекта CLAUDE_PROJECT_DIR, без неё — корень ядра;
                             в плагине скрипт лежит в tools/checks/ и пишет в logs/ проекта; --root нужен регрессу contour-tests §18)
    --list                   только показать взведённое, ничего не писать
    --strict                 код выхода 1, если есть FAIL
Без --checked и без --not-verified скрипт ОТКАЗЫВАЕТСЯ писать след: след без содержания — подлог.

Читает:  <корень>/logs/gate-state.json (взведённые правки по сессиям), <корень>/logs/gate-evidence.md.
Пишет:   <корень>/logs/gate-evidence.md (дописывает прогон), <корень>/logs/gate-state.json (снятый взвод).
         Каталог logs/ в .gitignore; файлы — UTF-8 без BOM, переводы строк LF.
Коды выхода: 0 — без --strict всегда и со --strict без FAIL; 1 — со --strict и есть FAIL
(след без содержания, сбой записи). --list всегда завершается кодом 0.
"""
import argparse
import datetime
import json
import ntpath
import os
import sys

ROOT_DEFAULT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.dont_write_bytecode = True  # не оставлять tools/lib/__pycache__ после прогона
sys.path.insert(0, os.path.join(ROOT_DEFAULT, 'tools', 'lib'))
from gate import Gate, read_text  # noqa: E402
import textio  # noqa: E402


def truthy(v):
    """Истинность значения так, как её видит PowerShell (Where-Object { $_ }) у значений из JSON."""
    if isinstance(v, dict):
        return True
    if isinstance(v, list):
        return truthy(v[0]) if len(v) == 1 else bool(v)
    return bool(v)


def as_text(v):
    """Строковое представление значения при склейке списка (-join)."""
    if v is None or isinstance(v, dict):
        # объект из JSON в PS — PSCustomObject, его ToString() при -join даёт пустую строку
        return ''
    if isinstance(v, bool):
        return 'True' if v else 'False'
    if isinstance(v, list):
        return ' '.join(as_text(x) for x in v)
    return str(v)


def is_rooted(p):
    """Аналог [IO.Path]::IsPathRooted: начинается с разделителя или с буквы диска."""
    return p[:1] in ('\\', '/') or bool(ntpath.splitdrive(p)[0])


def rel_path(p, root):
    """Путь в следе — ТОЛЬКО относительно корня. Абсолютный означал бы, что в logs/gate-evidence.md
    попадает каталог профиля пользователя (гейт утечек health-check срабатывает на этом законно).
    Вне корня каталоги не пишем — для снятия взвода хватает имени."""
    if not p or not is_rooted(p):
        return p
    if p[:len(root)].lower() == root.lower():
        return p[len(root):].lstrip('\\/')
    return ntpath.basename(p.rstrip('\\/'))


def find_key(state, key):
    """Ключ сессии без учёта регистра (в старой версии состояние — хеш-таблица PowerShell)."""
    low = key.lower()
    for k in state:
        if k.lower() == low:
            return k
    return None


def unique_flat(state):
    """Все взведённые файлы всех сессий, без пустых и без повторов (порядок первого появления)."""
    out = []
    for vals in state.values():
        for a in vals:
            if truthy(a) and a not in out:
                out.append(a)
    return out


def no_ci_dupes(pairs):
    # ConvertFrom-Json (PS 5.1) отвергает ключи, совпадающие лишь без учёта регистра («a» и «A»), —
    # состояние тогда не разобрано; точный повтор («a» и «a») принимает, побеждает последний — как dict(pairs)
    seen = {}
    for k, _ in pairs:
        low = k.lower()
        if low in seen and seen[low] != k:
            raise ValueError('повтор ключа ' + k)
        seen.setdefault(low, k)
    return dict(pairs)


def load_state(gs_path):
    loaded = json.loads(read_text(gs_path), object_pairs_hook=no_ci_dupes)
    if not isinstance(loaded, dict):
        raise ValueError('состояние — не объект')
    return {k: (v if isinstance(v, list) else [v]) for k, v in loaded.items()}


def main():
    g = Gate()  # до argparse: Gate переключает консоль на UTF-8, иначе справка в канале — кракозябры
    ap = argparse.ArgumentParser(description='След прогона проверок и снятие взведённого гейта качества.')
    ap.add_argument('--checked', nargs='+', action='extend', default=None, help='что проверено: инструмент и результат')
    ap.add_argument('--skipped', nargs='+', action='extend', default=None, help='что пропущено и почему')
    ap.add_argument('--not-verified', nargs='+', action='extend', default=None, help='что НЕ проверено и почему')
    ap.add_argument('--files', nargs='+', action='extend', default=None, help='какие файлы закрываются следом')
    ap.add_argument('--session-id', default='', help='сессия (по умолчанию CLAUDE_SESSION_ID, иначе все сессии)')
    ap.add_argument('--root', default='', help='корень с папкой logs (по умолчанию — папка проекта, иначе корень ядра)')
    ap.add_argument('--list', action='store_true', help='только показать взведённое')
    ap.add_argument('--strict', action='store_true', help='код выхода 1 при FAIL')
    args = ap.parse_args()

    root = args.root or os.environ.get('CLAUDE_PROJECT_DIR') or ROOT_DEFAULT

    checked = [s for s in (args.checked or []) if s]
    skipped = [s for s in (args.skipped or []) if s]
    not_verified = [s for s in (args.not_verified or []) if s]
    files = [rel_path(p, root) for p in (args.files or []) if p]

    session_id = args.session_id or os.environ.get('CLAUDE_SESSION_ID', '')
    # Claude Code номер сессии командам не передаёт (ревизия Р-31): без --session-id работаем по всем сессиям
    # сразу — отметка снимается по файлу, в какой бы сессии её ни поставили.
    all_sessions = not session_id
    scope = 'во всех сессиях' if all_sessions else 'в сессии %s' % session_id
    if not session_id:
        session_id = 'все сессии'

    logs = os.path.join(root, 'logs')
    gs_path = os.path.join(logs, 'gate-state.json')
    ev_path = os.path.join(logs, 'gate-evidence.md')

    state = {}
    if os.path.exists(gs_path):
        try:
            state = load_state(gs_path)
        except (OSError, ValueError, RecursionError):
            state = {}
            g.warn('состояние гейта не разобрано — считаю, что взведённого нет')
    if all_sessions:
        armed = unique_flat(state)
    else:
        key = find_key(state, session_id)
        armed = [a for a in (state[key] if key is not None else []) if truthy(a)]

    if args.list:
        if armed:
            g.info('взведено %s: %s' % (scope, ', '.join(as_text(a) for a in armed)))
        else:
            g.ok('взведённого %s нет' % scope)
        g.summary()
        g.exit(False)

    if not checked and not not_verified:
        g.bad('след не записан: нужен хотя бы --checked или --not-verified. След без содержания — подлог (full-checker-set-before-done п.3)')
        g.summary()
        g.exit(args.strict)

    target = files if files else list(armed)
    if not target:
        g.warn('%s нет взведённых правок .bsl — след пишется, но снимать нечего' % scope)

    # --- запись следа ---------------------------------------------------------
    stamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    lines = ['', '## Прогон %s · сессия %s' % (stamp, session_id), '',
             '[gate scope: files=%d, list=%s]' % (len(target), '|'.join(as_text(t) for t in target))]
    lines += ['[gate checked: %s]' % c for c in checked]
    lines += ['[gate skipped: %s]' % s for s in skipped]
    lines += ['[gate not_verified: %s]' % n for n in not_verified]
    if not not_verified:
        lines.append('[gate not_verified: нет — заявлено, что применимых непроверенных нет]')

    prev = ''
    if os.path.exists(ev_path):
        try:
            prev = read_text(ev_path)
        except OSError:
            prev = ''
    if not prev:
        prev = ('# След прогонов проверок (гейт качества)\n\n'
                'Файл дописывается скриптом tools\\checks\\gate-evidence.py; каталог logs\\ в .gitignore.')
    try:
        os.makedirs(logs, exist_ok=True)
        textio.write(ev_path, prev.rstrip() + '\n' + '\n'.join(lines) + '\n', bom=False)
    except OSError as e:
        # старая версия здесь печатала исключение и всё равно рапортовала «след записан»
        g.bad('след не записан: logs\\gate-evidence.md — %s' % e)
        g.summary()
        g.exit(args.strict)
    g.ok('след записан: logs\\gate-evidence.md (проверено: %d, пропущено: %d, НЕ проверено: %d)'
         % (len(checked), len(skipped), len(not_verified)))

    # --- снятие взвода --------------------------------------------------------
    if target and armed:
        if all_sessions:
            keys = list(state.keys())
        else:
            key = find_key(state, session_id)
            keys = [key] if key is not None else []
        closed = {as_text(t).lower() for t in target}
        for k in keys:
            left = [a for a in state[k] if truthy(a) and as_text(a).lower() not in closed]
            if left:
                state[k] = left
            else:
                del state[k]
        if all_sessions:
            rest = unique_flat(state)
        else:
            key = find_key(state, session_id)
            rest = [a for a in (state[key] if key is not None else []) if truthy(a)]
        try:
            textio.write(gs_path, json.dumps(state, ensure_ascii=False, indent=2), bom=False)
        except OSError as e:
            g.bad('взвод не снят: logs\\gate-state.json не записан — %s' % e)
            g.summary()
            g.exit(args.strict)
        if rest:
            g.warn('гейт снят частично, осталось взведённым: ' + ', '.join(as_text(a) for a in rest))
        else:
            g.ok('гейт снят полностью: взведённых правок в сессии не осталось')
    g.summary()
    g.exit(args.strict)


if __name__ == '__main__':
    main()
