"""Импорт результата слияния в одноразовую файловую базу и синтаксический контроль модулей (/CheckModules).

Использование:
  python import-check.py --repo <репозиторий слияния> [--rev <ревизия>] [--work <каталог>] [--ibcmd <путь>] [--v8 <1cv8.exe>]
                         [--modes ThinClient,Server] [--check-config] [--baseline <import-report.json>]
                         [--keep-db] [--skip-checks] [--dry-run]

Шаги — отдельными запусками, стоп на первом провале (designer-batch-runs):
  1. выгрузка индекса (результат слияния после git add) или ревизии --rev в <запуск>/xml — без checkout в репозитории;
  2. ibcmd infobase create — пустая файловая база в <запуск>/ib (свои --data и --db-path, рабочие базы не трогаются);
  3. ibcmd config import — полная загрузка XML (здесь ломается импорт на первом сломанном файле);
  4. 1cv8 DESIGNER /CheckModules <режимы> с /Out и /DumpResult — синтаксический контроль модулей;
  5. по --check-config — 1cv8 DESIGNER /CheckConfig -ConfigLogIntegrity -IncorrectReferences.
Вердикт шага конфигуратора — по коду возврата (0 — успех, 1 — ошибка, 101 — найдены ошибки), по числу в /DumpResult и по
журналу /Out этого запуска (нет журнала — шаг не пройден). --baseline — отчёт такого же прогона по новому релизу
(--rev vendor-<версия>): совпавшие строки журнала помечаются «унаследовано от поставщика».
Перед импортом (без --rev) нужны: ни одного неразрешённого пути и свежий check-report.json без ошибок (хеш индекса совпадает);
--skip-checks — только с объяснением владельцу. --dry-run — проверить предусловия и напечатать команды, ничего не запуская.
Временная база удаляется после прогона (--keep-db — оставить). Отчёт: <запуск>/import-report.md и .json.
Коды: 0 — импорт и проверки прошли, 1 — шаг не прошёл, 2 — неверные аргументы или предусловие не выполнено.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from release_xml import export_tree, find_ibcmd, git  # noqa: E402

MODES = ('ThinClient', 'WebClient', 'MobileClient', 'MobileAppClient', 'MobileClientStandalone', 'Server', 'MobileAppServer',
         'ExternalConnection', 'ThickClientOrdinaryApplication')   # ключи /CheckModules — 1c-platform-kb, its-docs adm-pr07 p2
DESIGNER_CODES = {0: 'успех', 1: 'ошибка', 101: 'найдены ошибки'}
MODULE_LINE = re.compile(r'\{[^}]+\}')   # строка с местом в модуле; формат журнала живым запуском не подтверждён


def run_tool(cmd, shell_line=None):
    """Запуск ibcmd (списком) или 1cv8 (готовой строкой: кавычки внутри значений 1С разбирает сама). Ждёт процесс."""
    # stdin закрыт: ibcmd на Windows при запросе учётных данных читает консоль и иначе может зависнуть (примечание db-load-xml)
    r = subprocess.run(shell_line if shell_line is not None else cmd, capture_output=True, stdin=subprocess.DEVNULL)
    out = r.stdout + r.stderr
    try:
        text = out.decode('utf-8')
    except UnicodeDecodeError:
        text = out.decode('cp866', 'replace')
    return r.returncode, text.strip()


def q(p):
    return '"%s"' % p


def read_log(path):
    if not os.path.isfile(path):
        return None
    return [ln.strip() for ln in open(path, encoding='utf-8-sig', errors='replace').read().splitlines() if ln.strip()]


def designer_verdict(code, res_path, log_path, started):
    """Вердикт шага конфигуратора по сигналам: код, /DumpResult, журнал /Out этого запуска."""
    lines = read_log(log_path) if os.path.isfile(log_path) and os.path.getmtime(log_path) >= started - 1 else None
    res = open(res_path, encoding='utf-8-sig', errors='replace').read().strip() if os.path.isfile(res_path) else None
    why = []
    if code != 0:
        why.append('код %s (%s)' % (code, DESIGNER_CODES.get(code, 'неизвестный')))
    if res not in (None, '', '0'):
        why.append('в /DumpResult — %s' % res)
    if lines is None:
        why.append('журнала /Out этого запуска нет — шаг не подтверждён')
    return (not why), why, lines or [], res


def main():
    ap = argparse.ArgumentParser(description='Импорт результата слияния в одноразовую базу и /CheckModules')
    ap.add_argument('--repo', required=True)
    ap.add_argument('--rev', help='импортировать ревизию (например vendor-<версия> — базовая линия), а не индекс')
    ap.add_argument('--work', help='каталог прогонов (по умолчанию <repo>-import)')
    ap.add_argument('--report', help='каталог отчётов слияния (по умолчанию <repo>-report)')
    ap.add_argument('--ibcmd', help='путь к ibcmd.exe или каталогу bin платформы')
    ap.add_argument('--v8', help='путь к 1cv8.exe (по умолчанию — рядом с ibcmd)')
    ap.add_argument('--modes', default='ThinClient,Server', help='режимы /CheckModules через запятую (по умолчанию ThinClient,Server)')
    ap.add_argument('--check-config', action='store_true', help='ещё /CheckConfig -ConfigLogIntegrity -IncorrectReferences')
    ap.add_argument('--baseline', help='import-report.json прогона по новому релизу — совпавшие строки журнала не считаются новыми')
    ap.add_argument('--keep-db', action='store_true', help='не удалять временную базу')
    ap.add_argument('--skip-checks', action='store_true', help='не требовать свежий check-report.json без ошибок')
    ap.add_argument('--dry-run', action='store_true', help='предусловия и команды, без запуска')
    a = ap.parse_args()
    repo = os.path.abspath(a.repo)
    if not os.path.isdir(os.path.join(repo, '.git')):
        print('не репозиторий слияния: %s' % repo)
        return 2
    modes = [m.strip() for m in a.modes.split(',') if m.strip()]
    bad = [m for m in modes if m not in MODES]
    if not modes or bad:
        print('режимы /CheckModules: нужен хотя бы один из %s; неизвестные: %s' % (', '.join(MODES), ', '.join(bad) or '—'))
        return 2
    # предусловия
    problems = []
    try:
        if a.rev:
            git(repo, 'rev-parse', '--verify', a.rev + '^{commit}')
        else:
            unmerged = sorted(set(l.split('\t', 1)[1] for l in git(repo, 'ls-files', '-u', '-z').split('\0') if '\t' in l))
            if unmerged:
                problems.append('не разрешено путей: %d (первый: %s) — сначала resolve-merge.py и ручное разрешение' % (
                    len(unmerged), unmerged[0]))
            elif not a.skip_checks:
                cr = os.path.join(os.path.abspath(a.report or repo.rstrip(os.sep) + '-report'), 'check-report.json')
                rep = json.load(open(cr, encoding='utf-8')) if os.path.isfile(cr) else None
                tree = git(repo, 'write-tree').strip()
                if rep is None:
                    problems.append('нет %s — сначала check-merge.py' % cr)
                elif rep.get('tree') != tree:
                    problems.append('check-report.json устарел: индекс изменился после проверки — повторить check-merge.py')
                elif rep.get('errors'):
                    problems.append('в check-report.json ошибок: %d — сначала исправить' % rep['errors'])
    except RuntimeError as e:
        problems.append(str(e))
    ibcmd = find_ibcmd(a.ibcmd)
    v8 = a.v8 or (os.path.join(os.path.dirname(ibcmd), '1cv8.exe') if ibcmd else None)
    if not a.dry_run:
        if not ibcmd:
            problems.append('ibcmd.exe не найден: --ibcmd, ONEC_PLATFORM_BIN или v8path в .v8-project.json')
        if not v8 or not os.path.isfile(v8):
            problems.append('1cv8.exe не найден: %s (--v8)' % v8)
    baseline = None
    if a.baseline:
        if not os.path.isfile(a.baseline):
            problems.append('нет базовой линии %s' % a.baseline)
        else:
            baseline = json.load(open(a.baseline, encoding='utf-8'))
    for p in problems:
        print('ПРЕДУСЛОВИЕ: ' + p)
    if problems:
        return 2
    label = (a.rev or 'index').replace('/', '-')
    work = os.path.abspath(a.work or repo.rstrip(os.sep) + '-import')
    run_dir = stem = os.path.join(work, time.strftime('%Y%m%d-%H%M%S') + '-' + label)
    n_run = 1
    while os.path.exists(run_dir):   # свой каталог на каждый запуск: журнал прошлого прогона не прочитается как свой
        n_run += 1
        run_dir = '%s-%d' % (stem, n_run)
    xml_dir, ib, logs = os.path.join(run_dir, 'xml'), os.path.join(run_dir, 'ib'), os.path.join(run_dir, 'logs')
    data, db = os.path.join(ib, 'data'), os.path.join(ib, 'db')
    ib_args = ['--data=' + data, '--db-path=' + db]
    ibc = ibcmd or '<ibcmd.exe>'
    v8x = v8 or '<1cv8.exe>'

    def designer(batch, name):
        log, res = os.path.join(logs, name + '.log'), os.path.join(logs, name + '.res')
        line = '%s DESIGNER /F %s /DisableStartupDialogs /DisableStartupMessages %s /Out %s /DumpResult %s' % (
            q(v8x), q(db), batch, q(log), q(res))
        return line, log, res
    cm_line, cm_log, cm_res = designer('/CheckModules ' + ' '.join('-' + m for m in modes), 'check-modules')
    cc_line, cc_log, cc_res = designer('/CheckConfig -ConfigLogIntegrity -IncorrectReferences', 'check-config')
    plan = [('выгрузка %s в каталог' % ('ревизии ' + a.rev if a.rev else 'индекса'), 'git checkout-index → ' + xml_dir),
            ('пустая файловая база', subprocess.list2cmdline([ibc, 'infobase', 'create'] + ib_args + ['--create-database'])),
            ('импорт XML', subprocess.list2cmdline([ibc, 'config', 'import'] + ib_args + [xml_dir])),
            ('синтаксический контроль модулей', cm_line)]
    if a.check_config:
        plan.append(('проверка конфигурации', cc_line))
    print('прогон: %s%s' % (run_dir, ' (пробный: ничего не запускается)' if a.dry_run else ''))
    for i, (what, cmd) in enumerate(plan, 1):
        print('  %d. %s: %s' % (i, what, cmd))
    if a.dry_run:
        return 0
    os.makedirs(logs, exist_ok=True)
    steps, ok = [], True
    t0 = time.time()
    try:
        n = export_tree(repo, a.rev, xml_dir)
        steps.append({'step': plan[0][0], 'ok': n > 0 and os.path.isfile(os.path.join(xml_dir, 'Configuration.xml')),
                      'detail': 'файлов %d' % n})
    except RuntimeError as e:
        steps.append({'step': plan[0][0], 'ok': False, 'detail': str(e)[-800:]})
    ok = steps[-1]['ok']
    if ok:
        code, out = run_tool([ibcmd, 'infobase', 'create'] + ib_args + ['--create-database'])
        ok = code == 0 and os.path.isdir(db) and any(f.lower().endswith('.1cd') for f in os.listdir(db))
        steps.append({'step': plan[1][0], 'ok': ok, 'code': code, 'detail': out[-1500:]})
    if ok:
        t = time.time()
        code, out = run_tool([ibcmd, 'config', 'import'] + ib_args + [xml_dir])
        ok = code == 0
        steps.append({'step': plan[2][0], 'ok': ok, 'code': code, 'seconds': int(time.time() - t),
                      'messages': [ln for ln in out.splitlines() if ln.strip()][-200:]})
    checks = [(plan[3][0], cm_line, cm_log, cm_res)] + ([(plan[4][0], cc_line, cc_log, cc_res)] if a.check_config else [])
    for what, line, log, res in checks:
        if not ok:
            break
        t = time.time()
        code, out = run_tool(None, shell_line=line)
        passed, why, lines, resv = designer_verdict(code, res, log, t)
        base_lines = set()
        for s in (baseline or {}).get('steps', []):
            if s.get('step') == what:
                base_lines = set(s.get('messages', []))
        new_lines = [ln for ln in lines if ln not in base_lines]
        if baseline is not None and code == 101 and not new_lines and lines:
            passed, why = True, ['код 101, но все %d строк журнала — как у поставщика (базовая линия)' % len(lines)]
        steps.append({'step': what, 'ok': passed, 'code': code, 'result': resv, 'why': why, 'seconds': int(time.time() - t),
                      'messages': lines[:2000], 'new_messages': new_lines[:500],
                      'module_lines': sum(1 for ln in new_lines if MODULE_LINE.search(ln))})
        ok = passed
    if not a.keep_db:
        shutil.rmtree(ib, ignore_errors=True)
    report = {'repo': repo, 'rev': a.rev, 'run_dir': run_dir, 'ok': ok, 'seconds': int(time.time() - t0), 'modes': modes,
              'baseline': a.baseline, 'kept_db': db if a.keep_db else None, 'steps': steps}
    json.dump(report, open(os.path.join(run_dir, 'import-report.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    md = ['# Импорт и проверка модулей: %s' % ('ревизия ' + a.rev if a.rev else 'результат слияния'), '',
          'Итог: **%s**, %d с. Каталог прогона: `%s`.' % ('прошло' if ok else 'не прошло', report['seconds'], run_dir), '',
          '| Шаг | Итог | Подробности |', '|---|---|---|']
    for s in steps:
        md.append('| %s | %s | %s |' % (s['step'], 'да' if s['ok'] else '**нет**',
                                        '; '.join(s.get('why') or []) or s.get('detail', '') or 'код %s' % s.get('code', '—')))
    for s in steps:
        msgs = s.get('new_messages', s.get('messages'))
        if msgs and not s['ok']:
            md += ['', '## %s — сообщения%s' % (s['step'], ' (новые относительно базовой линии)' if baseline else ''), '']
            md += ['- %s' % m for m in msgs[:200]]
    open(os.path.join(run_dir, 'import-report.md'), 'w', encoding='utf-8', newline='\n').write('\n'.join(md) + '\n')
    for s in steps:
        print('  %s %s' % ('ok ' if s['ok'] else 'НЕТ', s['step']) + ('' if s['ok'] else ': ' + '; '.join(s.get('why') or [str(s.get('code', ''))])))
    print('итог: %s; отчёт: %s' % ('прошло' if ok else 'не прошло', os.path.join(run_dir, 'import-report.md')))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
