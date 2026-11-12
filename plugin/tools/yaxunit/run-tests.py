r"""Прогон юнит-тестов YAXUnit на ТЕСТОВОЙ базе проекта и вердикт по отчёту (команда /ones-core:tests).

    python run-tests.py [--project <папка>] [--base <id>] [--extensions <имя> ...] [--timeout 120] [--no-skips] [--dry-run]

Рецепт — docs/tools/task-recipes.md §12 (проверен живым прогоном 11.07.2026), здесь он собран в один шаг:
  база      — только из .v8-project.json проекта (незарегистрированная считается рабочей, secrets-and-production-database)
              и только с отметкой pd: none или masked (personal-data-masked-from-1c): тест — код на данных базы, текст падения
              идёт к модели; проверка в настоящем запуске, --dry-run базу не открывает;
  платформа — v8path базы или реестра, иначе ONEC_PLATFORM_BIN; клиент — 1cv8c.exe;
  конфиг    — logs/yaxunit/<метка>/run-config.json: filter.extensions, reportPath (jUnit), closeAfterTests, exitCode, logging;
  запуск    — ENTERPRISE /C"RunUnitTests=<конфиг>" БЕЗ ожидания процесса (§12 п.4: при ловушке установки клиент висит вечно):
              ждём файл exitCode с дедлайном, по таймауту останавливаем только СВОЙ процесс (designer-batch-runs п.4);
  вход      — пользователь и пароль базы только из окружения ONEC_DB_USER_<id> / ONEC_DB_PWD_<id>, иначе вход ОС.
Вердикт — по отчёту этого прогона, а не по коду процесса: «pass» только при тестах > 0 и без падений.
Пропущенный тест (<skipped/> в отчёте) — не проход (волна 2 п.2.11): в вердикте «пропущено N» отдельно от прошедших;
все пропущены — «не выполнен»; с --no-skips (тесты обязательны: тест на баг, приёмка) любой пропуск — не зелёный.
Выход: 0 — тесты зелёные; 1 — красные, не выполнены, обязательный тест пропущен или клиент завис; 2 — неверные входные данные.
"""
import argparse
import datetime
import importlib.util
import json
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET


def junit_cases(path):
    """(тестов, упавших, [(имя, сообщение)]) из jUnit-отчёта; (0, 0, []) — отчёта нет или он не разбирается."""
    if not os.path.isfile(path):
        return 0, 0, []
    try:
        root = ET.parse(path).getroot()
    except Exception:
        return 0, 0, []
    tests, failed = 0, []
    for case in root.iter('testcase'):
        tests += 1
        bad = case.find('failure')
        bad = bad if bad is not None else case.find('error')
        if bad is not None:
            msg = (bad.get('message') or bad.text or '').strip().splitlines()
            failed.append(('%s.%s' % (case.get('classname') or '', case.get('name') or '?'), msg[0][:200] if msg else ''))
    if tests == 0:   # отчёт без testcase — счётчики набора
        for s in ([root] if root.tag.endswith('testsuite') else root.iter('testsuite')):
            tests += int(s.get('tests', 0) or 0)
    return tests, len(failed), failed


def junit_skipped(path):
    """Число пропущенных тестов jUnit-отчёта: testcase с <skipped/>, а без testcase — атрибут skipped набора; 0 — нет отчёта."""
    try:
        root = ET.parse(path).getroot()
    except Exception:
        return 0
    cases = list(root.iter('testcase'))
    if cases:
        return sum(1 for c in cases if c.find('skipped') is not None)
    return sum(int(s.get('skipped', 0) or 0) for s in ([root] if root.tag.endswith('testsuite') else root.iter('testsuite')))


def pd_refusal(base_id, db, reg_path):
    """Причина не запускать прогон на этой базе или None: решение барьера ПДн (personal-data-masked-from-1c), сбой — отказ."""
    try:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'hooks', 'guard-personal-data.py')
        spec = importlib.util.spec_from_file_location('guard_personal_data', path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.run_refusal(base_id, db, reg_path, 'прогон YAXUnit')
    except Exception as e:
        return 'personal-data-masked-from-1c: проверка отметки pd не удалась (%s) — сбой = отказ (п.5 правила)' % e


def connection(db):
    """Ключ подключения 1cv8c: файловая база — /F<путь>, серверная — /S<сервер>\\<база>."""
    if (db.get('type') or '').lower() == 'server' and db.get('server') and db.get('ref'):
        return '/S%s\\%s' % (db['server'], db['ref'])
    if db.get('path'):
        return '/F%s' % db['path']
    return None


def main():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding='utf-8')
        except Exception:
            pass
    ap = argparse.ArgumentParser(description='Прогон YAXUnit на тестовой базе проекта и вердикт по отчёту.')
    ap.add_argument('--project', default='.', help='папка проекта с .v8-project.json')
    ap.add_argument('--base', help='id базы (по умолчанию default реестра)')
    ap.add_argument('--extensions', nargs='*', default=[], help='тестовые расширения; пусто — все тесты базы')
    ap.add_argument('--timeout', type=int, default=120, help='дедлайн ожидания отчёта, с (по умолчанию 120)')
    ap.add_argument('--no-skips', action='store_true', help='тесты обязательны: любой пропущенный тест — не зелёный (код 1)')
    ap.add_argument('--dry-run', action='store_true', help='собрать конфиг и команду, не запускать')
    a = ap.parse_args()

    proj = os.path.abspath(a.project)
    reg_path = os.path.join(proj, '.v8-project.json')
    try:
        with open(reg_path, encoding='utf-8-sig') as f:
            reg = json.load(f)
    except (OSError, ValueError) as e:
        print('реестр баз %s не прочитан (%s) — без него базу не выбрать' % (reg_path, e), file=sys.stderr)
        return 2
    dbs = reg.get('databases') or []
    dbs = [dbs] if isinstance(dbs, dict) else [d for d in dbs if isinstance(d, dict)]
    want = a.base or reg.get('default')
    db = next((d for d in dbs if d.get('id') == want), None)
    if not db:
        print('база %r не зарегистрирована в .v8-project.json — тесты гоняются только на тестовой базе' % want, file=sys.stderr)
        return 2
    conn = connection(db)
    if not conn:
        print('у базы %r нет path (файловая) или server+ref (серверная)' % want, file=sys.stderr)
        return 2
    why = pd_refusal(want, db, reg_path)
    if why and not a.dry_run:
        print(why, file=sys.stderr)
        return 2
    v8 = db.get('v8path') or reg.get('v8path') or os.environ.get('ONEC_PLATFORM_BIN') or ''
    exe = os.path.join(v8, '1cv8c.exe') if v8 else ''
    if not a.dry_run and not os.path.isfile(exe):
        print('нет клиента 1cv8c.exe в %r — задайте v8path в .v8-project.json или ONEC_PLATFORM_BIN' % v8, file=sys.stderr)
        return 2

    work = os.path.join(proj, 'logs', 'yaxunit', datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
    os.makedirs(work, exist_ok=True)
    report, code_file, log_file = (os.path.join(work, n) for n in ('report.xml', 'exitcode.txt', 'yaxunit.log'))
    cfg = {'reportFormat': 'jUnit', 'reportPath': report, 'closeAfterTests': True, 'exitCode': code_file,
           'logging': {'file': log_file, 'enable': True, 'level': 'debug'}}
    if a.extensions:
        cfg['filter'] = {'extensions': a.extensions}
    cfg_path = os.path.join(work, 'run-config.json')
    with open(cfg_path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

    cmd = [exe or '1cv8c.exe', 'ENTERPRISE', conn, '/DisableStartupDialogs', '/DisableSplash', '/C', 'RunUnitTests=' + cfg_path]
    user = os.environ.get('ONEC_DB_USER_%s' % want)
    pwd = os.environ.get('ONEC_DB_PWD_%s' % want)
    if user:
        cmd.append('/N' + user)
        if pwd:
            cmd.append('/P' + pwd)
    else:
        cmd.append('/WA+')
    shown = [('/P***' if c.startswith('/P') and pwd and c == '/P' + pwd else c) for c in cmd]
    print('YAXUnit: база %r, конфиг %s' % (want, cfg_path))
    print('команда: ' + ' '.join('"%s"' % c if ' ' in c else c for c in shown))
    if a.dry_run:
        print('(dry-run: не запускаю)')
        return 0

    started = time.time()
    proc = subprocess.Popen(cmd)
    deadline = started + a.timeout
    while time.time() < deadline and not os.path.isfile(code_file) and proc.poll() is None:
        time.sleep(2)
    hung = not os.path.isfile(code_file) and proc.poll() is None
    if hung:
        proc.kill()   # только свой процесс (по нему же), чужие сеансы 1С не трогаем
    else:
        time.sleep(2)   # отчёт дописывается вслед за файлом кода
    fresh = os.path.isfile(report) and os.path.getmtime(report) >= started - 1
    tests, fails, failed = junit_cases(report) if fresh else (0, 0, [])
    skipped = junit_skipped(report) if fresh else 0
    code = open(code_file, encoding='utf-8-sig').read().strip() if os.path.isfile(code_file) else ''
    verdict, rc = judge(hung, tests, fails, skipped, a.no_skips, a.timeout, log_file, proc.returncode, code)
    print('вердикт: ' + verdict)
    for name, msg in failed[:10]:
        print('  ✗ %s — %s' % (name, msg))
    if len(failed) > 10:
        print('  … и ещё %d' % (len(failed) - 10))
    print('отчёт: %s' % report)
    return rc


def judge(hung, tests, fails, skipped, no_skips, timeout, log_file, proc_rc, code):
    """(вердикт, код выхода) по отчёту прогона; пропуск — не проход: в тексте отдельно, все пропущены или --no-skips — код 1."""
    passed = max(tests - fails - skipped, 0)
    if hung:
        return ('не выполнен: клиент не закрылся за %d с. Частые причины (§12 п.4): в модуле приложения хоста нет '
                'ПриНачалеРаботыСистемы() или одного из обработчиков ошибок (нужны оба имени: ОбработкаОтображенияОшибки '
                'и ErrorDisplayProcessing); расширение YAXUnit не применено (ibcmd config apply --extension); режим '
                'совместимости расширений хоста выше движка. Лог движка: %s' % (timeout, log_file)), 1
    if fails:
        return 'КРАСНЫЕ: тестов %d, упало %d, пропущено %d' % (tests, fails, skipped), 1
    if tests == 0 and not os.path.isfile(log_file):
        # движок даже не начал лог: клиент закрылся сразу (живая проба 30.10.2026 — базы на сервере нет)
        return ('не выполнен: клиент 1С закрылся без отчёта и лога движка (код процесса %s) — база недоступна '
                '(«Информационная база не обнаружена»), не прошёл вход или расширение YAXUnit не подключено; '
                'проверьте базу скиллом db-cfe-admin list' % proc_rc), 1
    if tests == 0:
        return ('не выполнен: отчёта этого прогона нет или в нём 0 тестов (код движка %r): модуль тестов не должен быть '
                '«Вызов сервера» или «Глобальный» — иначе движок его не видит (скилл yaxunit) — лог: %s' % (code, log_file)), 1
    if passed == 0:
        return 'не выполнен: все %d тестов пропущены — пропуск не проход' % tests, 1
    if skipped and no_skips:
        return ('НЕ зелёные: прошло %d, пропущено %d из %d — тесты обязательны (--no-skips), пропуск не проход'
                % (passed, skipped, tests)), 1
    if skipped:
        return 'зелёные с пропусками: прошло %d, падений 0, пропущено %d — пропущенные не проверены' % (passed, skipped), 0
    return 'зелёные: тестов %d, падений 0, пропущено 0' % tests, 0


if __name__ == '__main__':
    sys.exit(main())
