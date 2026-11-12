r"""protect.py — защитить XML-выгрузку проекта закрытым движком обфускации (Т-8 волны 3, доставка в проекты, ADR-0009).

Проектный аналог мастерского build-protected.py, но зовёт УСТАНОВЛЕННЫЙ машинный бинарник (без JDK и исходников):
копия выгрузки -> обфускатор на месте в копии по флагам -> отчёт «что защищено и чем». Исходники из --src не меняются.
Бинарник ставит install-tools из релиз-ассета приватного канала; здесь он только запускается.

Запуск (через команду /ones-core:protect):
    python "${CLAUDE_PLUGIN_ROOT}/tools/obfuscator/protect.py" --src <папка выгрузки> --out <папка сборки>
        [--context auto|all|none] [--strings] [--flow] [--keep <файл>] [--report <отчёт.json>] [--engine <путь к .exe>]

Движок: --engine, иначе ${CLAUDE_PLUGIN_DATA}/bin/obfuscator/onescore-obfuscator.exe (рядом — tree-sitter.dll, tree-sitter-bsl.dll).
Коды выхода: 0 — все модули записаны; 1 — есть отклонённые; 2 — нет движка/папок или движок не запустился.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding='utf-8')
    except Exception:
        pass


def engine_path(explicit):
    if explicit:
        return explicit
    data = os.environ.get('CLAUDE_PLUGIN_DATA')
    name = 'onescore-obfuscator.exe' if os.name == 'nt' else 'onescore-obfuscator'
    return os.path.join(data, 'bin', 'obfuscator', name) if data else ''


def main():
    ap = argparse.ArgumentParser(description='Защитить выгрузку закрытым движком обфускации (установленный бинарник).')
    ap.add_argument('--src', required=True, help='папка XML-выгрузки (не изменяется)')
    ap.add_argument('--out', required=True, help='папка сборки (не должна существовать или пуста)')
    ap.add_argument('--context', default='auto', choices=['auto', 'all', 'none'])
    ap.add_argument('--strings', action='store_true')
    ap.add_argument('--flow', action='store_true')
    ap.add_argument('--keep', help='файл неприкосновенных имён')
    ap.add_argument('--report', help='куда записать отчёт JSON')
    ap.add_argument('--engine', help='путь к onescore-obfuscator.exe (иначе из папки данных плагина)')
    args = ap.parse_args()

    exe = engine_path(args.engine)
    if not exe or not os.path.isfile(exe):
        # в окружении команд инструмента Bash CLAUDE_PLUGIN_DATA нет: путь приходит текстом команды, ключом --engine
        print('нет движка обфускации: %s\nпоставить: python "${CLAUDE_PLUGIN_ROOT}/tools/setup/install-tools.py" '
              '--dest "${CLAUDE_PLUGIN_DATA}/bin" --only obfuscator' % (exe or '<путь не задан: передайте --engine '
                                                                        '"${CLAUDE_PLUGIN_DATA}/bin/obfuscator/onescore-obfuscator.exe">'),
              file=sys.stderr)
        return 2
    if not os.path.isdir(args.src):
        print('нет папки выгрузки: %s' % args.src, file=sys.stderr)
        return 2
    if os.path.exists(args.out) and os.listdir(args.out):
        print('папка сборки не пуста: %s (укажите несуществующую или пустую)' % args.out, file=sys.stderr)
        return 2

    shutil.copytree(args.src, args.out, dirs_exist_ok=True)   # копия — исходники не трогаем
    cmd = [exe, '--in', args.out, '--out', args.out, '--context', args.context]
    if args.strings:
        cmd.append('--strings')
    if args.flow:
        cmd.append('--flow')
    if args.keep:
        cmd += ['--keep', args.keep]
    r = subprocess.run(cmd, capture_output=True)
    rows = []
    for line in r.stdout.decode('utf-8', 'replace').splitlines():
        line = line.strip()
        if line.startswith('{'):
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass
    if not rows and r.returncode not in (0, 1):
        print('движок не запустился (код %s): %s' % (r.returncode, r.stderr.decode('utf-8', 'replace')[:300]), file=sys.stderr)
        return 2
    # движок упал или прервался на середине — поставка не собрана, даже если часть модулей он отчитал (аудит 30.10.2026)
    expected = sum(1 for _d, _s, fs in os.walk(args.out) for f in fs if f.lower().endswith('.bsl'))
    if r.returncode not in (0, 1) or len(rows) < expected:
        print('движок прервался (код %s, отчитано модулей %d из %d): поставка НЕ собрана, папка %s — промежуточная, '
              'в поставку её не отдавать. %s' % (r.returncode, len(rows), expected, args.out,
                                                 r.stderr.decode('utf-8', 'replace')[:300]), file=sys.stderr)
        return 2

    techniques = [n for n, on in (('переименование', True), ('строки', args.strings), ('ветвления', args.flow),
                                  ('по метаданным', bool(args.keep))) if on]
    modules = [{'path': x.get('path'), 'ok': x.get('ok'), 'renamed': x.get('renamed'),
                'hidden': x.get('hidden'), 'wrapped': x.get('wrapped'), 'reason': x.get('reason')} for x in rows]
    rejected = [m for m in modules if not m['ok']]
    if args.report:
        with open(args.report, 'w', encoding='utf-8', newline='\n') as f:
            json.dump({'src': args.src, 'out': args.out, 'techniques': techniques,
                       'modules_total': len(modules), 'modules_rejected': len(rejected), 'modules': modules},
                      f, ensure_ascii=False, indent=2)

    print('# %s: %s' % ('Защищённая поставка собрана в' if not rejected else
                        'Поставка НЕ готова — часть модулей осталась открытым текстом, папка', args.out))
    print('# Приёмы: %s' % (', '.join(techniques) or '—'))
    print('# Модулей обработано: %d, отклонено: %d' % (len(modules), len(rejected)))
    for m in modules:
        print('#   %s %s  переименовано=%s скрыто_строк=%s обёрнуто=%s%s'
              % ('OK ' if m['ok'] else 'ОТКЛОНЁН', m['path'], m['renamed'], m['hidden'], m['wrapped'],
                 '' if m['ok'] else '  причина: ' + str(m['reason'])))
    print('# --- живые шаги (платформа и база, приёмка по слову владельца) ---')
    print('# сборка: epf-build/erf-build по папке %s; для конфигурации/расширения — загрузка в ТЕСТОВУЮ базу' % args.out)
    print('# проверка: YAXUnit до и после (поведение должно совпасть), веб-клиент, замер скорости')
    if rejected:
        # отклонённый модуль движок не тронул: в папке он лежит открытым текстом из копии исходников
        print('# ВНИМАНИЕ: %d модулей отклонены и лежат в %s ОТКРЫТЫМ текстом — такую папку в поставку не отдавать: '
              'исправьте причины и соберите заново' % (len(rejected), args.out), file=sys.stderr)
    return 1 if rejected else 0


if __name__ == '__main__':
    sys.exit(main())
