r"""run-scenario.py — прогон сценария Vanessa Automation на тестовой базе проекта (Т-6 волны 3, #8 проверка в клиенте).

Берёт прошедший валидатор `.feature` (скилл `vanessa`) и гоняет его в КЛИЕНТЕ 1С на тестовой базе проекта через
vanessa-runner (`vrunner test vanessa`), отдаёт вердикт pass/fail. Config-agnostic: база читается из `.v8-project.json`
проекта, OneScript/vanessa-runner ищется окружением/поиском, пароль базы — ТОЛЬКО из окружения (в конфиг и в вывод
не попадает). Боевую базу не трогаем — только зарегистрированная тестовая ([[secrets-and-production-database]]).

Запуск:
    python run-scenario.py <feature> [--project <dir>] [--base <id>] [--report <path>] [--dry-run] [--v8version X] [--timeout N]
        <feature>      путь к .feature (сперва прогнать валидатор скилла vanessa)
        --project      папка проекта с .v8-project.json (по умолчанию текущая)
        --base         id базы из .v8-project.json (по умолчанию — default проекта)
        --report       путь к junit-отчёту (по умолчанию рядом с feature)
        --v8version    версия платформы 1С (по умолчанию из ONEC_V8VERSION, иначе из v8path реестра)
        --timeout      сколько секунд ждать отчёт (по умолчанию 900); истекло — клиент прогона закрывается, вердикт «не выполнен»
        --dry-run      только собрать команду vrunner (без запуска), пароль замаскирован

OneScript: домашняя папка — $ONEC_ONESCRIPT_HOME, иначе поиск (D:/tools/onescript*, PATH). Учётка базы id<ID>:
$ONEC_DB_USER_<ID> / $ONEC_DB_PWD_<ID> — её получает менеджер тестирования (vrunner); клиенту тестирования пароль не передаётся
(Vanessa пишет строку запуска с /P во временный .bat): он войдёт только через ОС или пользователем без пароля, харнесс
предупреждает. Нет учётки — вход ОС: менеджеру /WA+ ставит vrunner, клиенту тестирования «Этот клиент» — харнесс в файле
настроек Vanessa (issue #7). Код выхода: 0 — сценарий прошёл;
1 — сценарий упал, не выполнен или выполнен не весь; 2 — нет feature, нет toolchain или база не найдена/не тестовая/без
отметки pd: none или masked (personal-data-masked-from-1c: проверка в настоящем запуске, --dry-run базу не открывает).
Пропуск — не проход (волна 2 п.2.11): сценарий проверки обязателен, поэтому пропущенный сценарий или шаг (<skipped/>,
атрибут skipped набора — так Vanessa-ADD отмечает нереализованные и непройденные шаги) даёт «не выполнен полностью».
"""
import argparse
import glob
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

POLL = 3    # как часто смотреть отчёт, с
GRACE = 5   # сколько дать движку дописать файлы после отчёта, с
# без ВыполнитьСценарии Vanessa Automation только открывается и ждёт кнопку (журнал базы, проба 30.10.2026);
# ВыполнитьСценарии и ЗавершитьРаботуСистемы Vanessa переводит из строки в Булево, прочие ключи присваивает как есть — JSON true
VA_SETTINGS = {'ВыполнитьСценарии': 'Истина', 'ЗавершитьРаботуСистемы': 'Истина',
               'ЗакрытьTestClientПослеЗапускаСценариев': True}


def va_settings(user):
    """Настройки движка Vanessa. Без учётки в окружении клиенту тестирования «Этот клиент» — вход ОС (/WA+): сама Vanessa
    ставит ему /N"<пользователь>" без /WA+, и клиент ждёт на окне входа (issue #7). Строку с тем же Имя Vanessa находит и
    заменяет только ДопПараметры; путь к базе и порт берёт из своего сеанса."""
    s = dict(VA_SETTINGS)
    if not user:
        s['КлиентТестирования'] = {'ДанныеКлиентовТестирования': [{'Имя': 'Этот клиент', 'ДопПараметры': '/WA+'}]}
    return s


def pd_refusal(base_id, base, reg_path):
    """Причина не запускать сценарий на этой базе или None: решение барьера ПДн (personal-data-masked-from-1c), сбой — отказ."""
    try:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'hooks', 'guard-personal-data.py')
        spec = importlib.util.spec_from_file_location('guard_personal_data', path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.run_refusal(base_id, base, reg_path, 'сценарий Vanessa')
    except Exception as e:
        return 'personal-data-masked-from-1c: проверка отметки pd не удалась (%s) — сбой = отказ (п.5 правила)' % e


def validate_feature(feature):
    """Прогнать валидатор скилла vanessa: (код, вывод) или (None, ''), если скилла рядом нет.
    В плагине скилл — <плагин>/skills/vanessa, в мастере ядра — .claude/skills/vanessa."""
    here = os.path.dirname(os.path.abspath(__file__))
    for skill in (os.path.join(here, '..', '..', 'skills', 'vanessa'),
                  os.path.join(here, '..', '..', '..', '.claude', 'skills', 'vanessa')):
        val = os.path.join(skill, 'scripts', 'validate.py')
        lib = os.path.join(skill, 'ai-knowledge', 'steps-library.json')
        if os.path.isfile(val) and os.path.isfile(lib):
            r = subprocess.run([sys.executable, val, os.path.abspath(feature), '--library', lib, '--compact'],
                               cwd=os.path.dirname(val), capture_output=True,
                               env=dict(os.environ, PYTHONIOENCODING='utf-8'))
            return r.returncode, (r.stdout + r.stderr).decode('utf-8', 'replace')
    return None, ''


def fresh_reports(report, since):
    """junit-файлы отчёта этого прогона: сам файл или *.xml в каталоге (рекурсивно), изменённые не раньше старта."""
    if os.path.isfile(report):
        paths = [report]
    else:
        paths = glob.glob(os.path.join(report, '**', '*.xml'), recursive=True)
    return [p for p in paths if os.path.getmtime(p) >= since - 1]


def report_ready(report, since):
    """Отчёт этого прогона дописан: свежий junit-файл есть и разбирается как XML."""
    paths = fresh_reports(report, since)
    try:
        for p in paths:
            ET.parse(p)
    except (ET.ParseError, OSError):
        return False
    return bool(paths)


def junit_counts(path):
    """(число тестов, число падений+ошибок) из junit-отчёта; (0,0) если отчёта нет/не разобрать."""
    if not os.path.isfile(path):
        return 0, 0
    try:
        root = ET.parse(path).getroot()
    except Exception:
        return 0, 0
    suites = [root] if root.tag.endswith('testsuite') else root.iter('testsuite')
    tests = fails = 0
    for s in suites:
        tests += int(s.get('tests', 0) or 0)
        fails += int(s.get('failures', 0) or 0) + int(s.get('errors', 0) or 0)
    return tests, fails


def junit_skipped(path):
    """Число пропущенных в junit-отчёте: testcase с <skipped/>, а без testcase — атрибут skipped набора; 0 — нет отчёта."""
    try:
        root = ET.parse(path).getroot()
    except Exception:
        return 0
    cases = list(root.iter('testcase'))
    if cases:
        return sum(1 for c in cases if c.find('skipped') is not None)
    return sum(int(s.get('skipped', 0) or 0) for s in ([root] if root.tag.endswith('testsuite') else root.iter('testsuite')))


def judge(vrunner_rc, tests, fails, skipped):
    """(вердикт, код выхода): «pass» — только непустой отчёт этого прогона без падений и без пропусков."""
    if vrunner_rc != 0 or fails > 0:
        return 'fail (тестов %d, падений %d, пропущено %d)' % (tests, fails, skipped), 1
    if tests == 0:
        return 'не выполнен (сценарий не запущен: клиент не прошёл аутентификацию базы или не стартовал)', 1
    if skipped:
        return ('не выполнен полностью: пропущено %d из %d — сценарий проверки обязателен, пропуск не проход '
                '(шаг не реализован в библиотеке или не дошёл до выполнения)' % (skipped, tests)), 1
    return 'pass (тестов %d, падений 0, пропущено 0)' % tests, 0


def plugin_data():
    """Папка данных плагина: в окружении команд инструмента Bash переменной нет — стандартная папка профиля, как в хуках."""
    return os.environ.get('CLAUDE_PLUGIN_DATA') or os.path.join(os.path.expanduser('~'), '.claude', 'plugins', 'data', 'ones-core-ones-core')


def find_onescript():
    """Домашняя папка OneScript с vanessa-runner: env, затем типовые места, затем PATH. Возвращает (oscript, main.os) или (None,None)."""
    homes = []
    env_home = os.environ.get('ONEC_ONESCRIPT_HOME')
    if env_home:
        homes.append(env_home)
    # поставленный установщиком плагина (install-tools --only onescript vanessa-runner vanessa-add vanessa-automation)
    homes.append(os.path.join(plugin_data(), 'bin', 'onescript'))
    homes += sorted(glob.glob('D:/tools/onescript*'), reverse=True)
    homes += sorted(glob.glob('C:/Program Files/OneScript*'))
    for h in homes:
        osc = os.path.join(h, 'bin', 'oscript.exe')
        mn = os.path.join(h, 'lib', 'vanessa-runner', 'src', 'main.os')
        if os.path.isfile(osc) and os.path.isfile(mn):
            return osc, mn
    # запасной путь: oscript в PATH (vrunner рядом)
    osc = shutil.which('oscript')
    if osc:
        h = os.path.dirname(os.path.dirname(osc))
        mn = os.path.join(h, 'lib', 'vanessa-runner', 'src', 'main.os')
        if os.path.isfile(mn):
            return osc, mn
    return None, None


def find_engine():
    """Движок сценариев Vanessa Automation (.epf): $ONEC_VANESSA_EPF, иначе поставленный установщиком плагина; нет — пусто
    (vrunner возьмёт bddRunner из vanessa-add 6.9.5, который не разбирает режим совместимости «Не использовать» и
    английские конфигурации — проба 30.10.2026)."""
    env_epf = os.environ.get('ONEC_VANESSA_EPF')
    if env_epf and os.path.isfile(env_epf):
        return env_epf
    p = os.path.join(plugin_data(), 'bin', 'vanessa-automation', 'vanessa-automation-single.epf')
    return p if os.path.isfile(p) else ''


def v8version_of(cfg, base):
    """Версия платформы X.Y.Z.B из v8path записи базы, иначе корневого v8path реестра; нет — пустая строка."""
    for p in (base.get('v8path'), cfg.get('v8path')):
        m = re.search(r'(\d+\.\d+\.\d+\.\d+)', str(p or ''))
        if m:
            return m.group(1)
    return ''


def ibconnection(base):
    """Строка подключения vrunner из записи базы .v8-project.json: сервер → /S server/ref, файл → /F path."""
    t = (base.get('type') or '').lower()
    if t == 'server' and base.get('server') and base.get('ref'):
        return '/S%s\\%s' % (base['server'], base['ref'])
    if base.get('path'):
        return '/F%s' % base['path']
    return None


def own_clients(rows, ibc):
    """PID клиентов этого прогона из строк (pid, командная строка): та же база и запуск под тестирование (/TESTMANAGER,
    /TESTCLIENT). Обычный сеанс человека в этой базе и соседние базы сюда не попадают."""
    base = re.compile(re.escape(ibc.lower()) + r'(?=[\s/]|$)')
    pids = []
    for pid, line in rows:
        flat = line.replace('"', '').lower()
        if base.search(flat) and re.search(r'/test(manager|client)\b', flat):
            pids.append(pid)
    return pids


def list_clients():
    """(pid, командная строка) процессов 1cv8*; вне Windows — пусто, клиент там закрывает только сам vrunner."""
    if os.name != 'nt':
        return []
    ps = ("[Console]::OutputEncoding=[Text.Encoding]::UTF8;Get-CimInstance Win32_Process -Filter \"Name like '1cv8%'\" | "
          "ForEach-Object { '{0}|{1}' -f $_.ProcessId, $_.CommandLine }")
    out = subprocess.run(['powershell.exe', '-NoProfile', '-Command', ps], capture_output=True, timeout=60).stdout
    return [line.split('|', 1) for line in out.decode('utf-8', 'replace').splitlines() if '|' in line]


def close_own_clients(ibc):
    """Закрыть клиенты этого прогона, вернуть их число; чужие сеансы не трогаем ([[designer-batch-runs]])."""
    pids = own_clients(list_clients(), ibc)
    for pid in pids:
        subprocess.run(['taskkill', '/PID', pid, '/F'], capture_output=True)
    return len(pids)


def run_vrunner(cmd, cwd, report, started, ibc, limit):
    """Запустить vrunner и дождаться конца сценария: (код vrunner, 'report' | 'timeout' | '').
    Обычно клиент закрывает сам движок. Не закрыл, а отчёт готов, или истёк срок — закрывает харнесс: только клиент этого прогона."""
    p = subprocess.Popen(cmd, cwd=cwd)
    why = ''
    while p.poll() is None and not why:
        time.sleep(POLL)
        if report_ready(report, started):
            why = 'report'
            time.sleep(GRACE)   # движок дописывает остальные файлы отчёта
        elif time.time() - started > limit:
            why = 'timeout'
    if why:
        print('клиентов этого прогона закрыто: %d' % close_own_clients(ibc))
        try:
            p.wait(30)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait()
    return p.returncode, why


def main():
    ap = argparse.ArgumentParser(description='Прогон сценария Vanessa Automation на тестовой базе проекта (Т-6 волны 3).')
    ap.add_argument('feature', help='путь к .feature (после валидатора скилла vanessa)')
    ap.add_argument('--project', default='.', help='папка проекта с .v8-project.json')
    ap.add_argument('--base', help='id базы (по умолчанию default проекта)')
    ap.add_argument('--report', help='путь к junit-отчёту')
    ap.add_argument('--format', default='jUnit', help='формат отчёта vrunner (по умолчанию jUnit)')
    ap.add_argument('--v8version', default=os.environ.get('ONEC_V8VERSION'), help='версия платформы 1С')
    ap.add_argument('--timeout', type=int, default=900, help='сколько секунд ждать отчёт')
    ap.add_argument('--dry-run', action='store_true', help='только собрать команду, не запускать')
    args = ap.parse_args()
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding='utf-8')
        except Exception:
            pass

    if not os.path.isfile(args.feature):
        print('нет файла сценария: %s (сперва сгенерируйте и проверьте скиллом vanessa)' % args.feature, file=sys.stderr)
        return 2
    # «красный валидатор — в клиент не гоним» — проверкой, а не текстом скилла (аудит 30.10.2026)
    vrc, vout = validate_feature(args.feature)
    if vrc is None:
        print('не найден валидатор скилла vanessa (scripts/validate.py) — без проверки шагов сценарий не гоним', file=sys.stderr)
        return 2
    if vrc != 0:
        print('валидатор скилла vanessa красный — сценарий в клиент не гоним; исправьте шаги:\n' + vout[-1500:], file=sys.stderr)
        return 1
    proj = os.path.abspath(args.project)
    vpj = os.path.join(proj, '.v8-project.json')
    if not os.path.isfile(vpj):
        print('нет .v8-project.json в проекте: %s' % proj, file=sys.stderr)
        return 2
    cfg = json.load(open(vpj, encoding='utf-8'))
    base_id = args.base or cfg.get('default')
    bases = {b.get('id'): b for b in cfg.get('databases', [])}
    base = bases.get(base_id)
    if not base:
        print('база %r не зарегистрирована в .v8-project.json (боевую не трогаем — только тестовая)' % base_id, file=sys.stderr)
        return 2
    ibc = ibconnection(base)
    if not ibc:
        print('не собрать строку подключения для базы %r (нет server/ref или path)' % base_id, file=sys.stderr)
        return 2
    why = pd_refusal(base_id, base, vpj)
    if why and not args.dry_run:
        print(why, file=sys.stderr)
        return 2

    osc, mainos = find_onescript()
    if not osc:
        if not args.dry_run:
            print('не найден OneScript с vanessa-runner: поставьте установщиком плагина — python "${CLAUDE_PLUGIN_ROOT}/tools/'
                  'setup/install-tools.py" --only onescript vanessa-runner vanessa-add vanessa-automation — или задайте ONEC_ONESCRIPT_HOME',
                  file=sys.stderr)
            return 2
        osc, mainos = 'oscript', '<main.os>'

    # --report-path у `test vanessa` — КАТАЛОГ: Vanessa-ADD выгружает в него все форматы (vanessa-runner 3.x,
    # ПодкомандаTestVanessa.ДополнитьНастройкиОтчетами → ОбеспечитьКаталог); junit-файлы ищем внутри (аудит 30.10.2026)
    report = os.path.abspath(args.report or os.path.splitext(os.path.abspath(args.feature))[0] + '.report')
    cmd = [osc, mainos, 'test', 'vanessa', '--feature-path', os.path.abspath(args.feature),
           '--ibconnection', ibc, '--report-format', args.format, '--report-path', report]
    # без версии vanessa-runner берёт новейшую платформу на машине (проба 30.10.2026: 8.5.1 на базе 8.3.27 — клиент повис
    # на вопросе о платформе); версия — из v8path реестра (у базы, иначе общий), как у скиллов db-*
    v8ver = args.v8version or v8version_of(cfg, base)
    if not v8ver:
        print('не задана версия платформы: нет v8path в .v8-project.json и нет --v8version (иначе vanessa-runner возьмёт '
              'новейшую установленную платформу)', file=sys.stderr)
        return 2
    cmd += ['--v8version', v8ver]
    # учётка базы — только из окружения; нет — интегрированная аутентификация
    user = os.environ.get('ONEC_DB_USER_%s' % base_id)
    pwd = os.environ.get('ONEC_DB_PWD_%s' % base_id)
    engine = find_engine()
    if engine:
        # vrunner сливает этот файл с настройками отчётов и отдаёт движку ключом VBParams
        settings = report + '.vaparams.json'
        if not args.dry_run:
            with open(settings, 'w', encoding='utf-8') as f:
                json.dump(va_settings(user), f, ensure_ascii=False)
        cmd += ['--bddrunner-path', engine, '--vanessasettings', settings]
    if user:
        cmd += ['--db-user', user]
        # решение владельца 20.11.2026: пароль клиенту тестирования не передаём — Vanessa пишет строку запуска с /P во временный .bat
        print('предупреждение: учётка базы уходит только менеджеру тестирования; клиенту тестирования пароль не передаётся — '
              'клиент тестирования войдёт только через ОС или пользователем без пароля', file=sys.stderr)
    if pwd:
        cmd += ['--db-pwd', pwd]

    shown = list(cmd)
    if pwd:
        shown[cmd.index('--db-pwd') + 1] = '***'   # по месту ключа: пароль, совпавший с другим аргументом, не печатается
    print('vrunner: ' + ' '.join('"%s"' % c if ' ' in c else c for c in shown))
    if args.dry_run:
        print('(dry-run: не запускаю)')
        return 0

    started = time.time()
    rc, why = run_vrunner(cmd, proj, report, started, ibc, args.timeout)
    if why == 'timeout':
        print('вердикт сценария: не выполнен (за %d с нет отчёта: клиент завис или ждёт ответа в окне); отчёт: %s'
              % (args.timeout, report))
        return 1
    if why == 'report':
        rc = 0   # клиент закрыт харнессом: код vrunner о нём уже ничего не говорит, вердикт — по отчёту
    # vrunner может вернуть 0, даже если сценарий не выполнился (клиент не прошёл аутентификацию) — поэтому
    # «pass» ставим только по непустому junit-отчёту без падений; нет отчёта при rc0 → «не выполнен», не «pass».
    # Засчитываются только отчёты ЭТОГО прогона: старый зелёный отчёт прошлого запуска — не вердикт.
    tests, fails, skipped = 0, 0, 0
    for path in fresh_reports(report, started):
        t, f = junit_counts(path)
        tests, fails, skipped = tests + t, fails + f, skipped + junit_skipped(path)
    verdict, code = judge(rc, tests, fails, skipped)
    print('вердикт сценария: %s (код vrunner %s); отчёт: %s' % (verdict, rc, report))
    return code


if __name__ == '__main__':
    sys.exit(main())
