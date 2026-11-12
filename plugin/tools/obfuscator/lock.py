r"""lock.py — план «замка» модулей 1С для поставки (срез 5 движка обфускации, ADR-0008 п.7).

Замок — штатными средствами платформы, не правкой кода: поставка без исходного текста (`hidden`), пароль на модуль
(`encrypted`), запрет изменений на поддержке (правило поставщика). Пакетно это умеет только платформа 8.5.1 —
команды `/ModuleGetSourceCodeAccess` и `/ModuleSetSourceCodeAccess` (в 8.3.27 их нет, замок ставится вручную в
Конфигураторе). Синтаксис и ограничения сверены по базе знаний платформы (its-docs: otlichiya-8.5.1-ot-8.3.27 §,
dev-gl37-gl38 §38.2, adm-pr07 — `/CheckConfig -DistributiveModules`).

Рекомендованный порядок платформы: получить список замыкаемых модулей `/ModuleGetSourceCodeAccess <файл>`, оставить
нужные с нужным режимом, применить `/ModuleSetSourceCodeAccess <файл>`, затем `/UpdateDBCfg`. В список GET платформа
включает ТОЛЬКО модули, которые можно закрыть паролем или поставлять без исходного текста, — значит модуль, которого
в списке нет, закрыть нельзя (модуль управляемого приложения, модули форм и команд, модули с директивами
препроцессора, клиентские общие модули управляемого режима — dev-gl37-gl38 §38.2).

Запуск:
    python "${CLAUDE_PLUGIN_ROOT}/tools/obfuscator/lock.py" plan --platform 8.5.1 --access-list <файл GET> --policy <политика.json> --set-out <файл SET>
        проверить политику против списка GET, записать файл SET, напечатать команды пакетного замка
    python "${CLAUDE_PLUGIN_ROOT}/tools/obfuscator/lock.py" plan --platform 8.3.27 --policy <политика.json>
        напечатать инструкцию ручного замка в Конфигураторе (пакетных команд в 8.3.27 нет)
    python "${CLAUDE_PLUGIN_ROOT}/tools/obfuscator/lock.py" verify --policy <политика.json> --access-list <свежий файл GET>
        сверить режимы модулей с политикой: код 1, если модуль не закрыт или его нет в списке

Политика (JSON): {"hidden": ["<имя модуля>", ...], "encrypted": [...], "support_ban": true|false}.
Имя модуля — как в файле GET (поле до первого «:», с префиксом «<Расширение> » если из расширения).
Пароль для `encrypted` берётся из окружения ONEC_OBFUSCATOR_MODULE_PASSWORD (в файл/репозиторий не вписывается).
Файл SET содержит пароль в открытом виде — пишется в каталог вызывающего, не в git; после применения удалить.

Коды выхода: 0 — план построен; 1 — политика требует закрыть модуль, которого нет в списке GET (закрыть нельзя),
или нет пароля для encrypted; 2 — ошибка вызова.
"""
import argparse
import json
import os
import sys

for _s in (sys.stdout, sys.stderr):   # кириллица в выводе не должна падать на cp1251/cp866 консоли
    try:
        _s.reconfigure(encoding='utf-8')
    except Exception:
        pass

MODES = ('hidden', 'encrypted', 'open')


def parse_access_list(path):
    """Файл GET: строки «[Расширение ]ИмяМодуля:режим:». Возвращает {имя: режим}."""
    names = {}
    with open(path, encoding='utf-8-sig') as f:
        for raw in f:
            line = raw.rstrip('\n').rstrip('\r')
            if not line.strip():
                continue
            parts = line.split(':')
            if len(parts) < 2:
                continue
            names[parts[0]] = parts[1]
    return names


def load_policy(path):
    with open(path, encoding='utf-8-sig') as f:
        p = json.load(f)
    return [str(x) for x in p.get('hidden', [])], [str(x) for x in p.get('encrypted', [])], bool(p.get('support_ban', False))


def support_ban_note():
    return ('Запрет изменений на поддержке: в Конфигураторе — Поддержка -> Настройка поддержки -> для объектов задать '
            '«Изменения запрещены». Снять можно только сняв всю конфигурацию с поддержки (dev-gl37-gl38 §38.2).')


def plan_851(access_list, policy, set_out):
    available = parse_access_list(access_list)
    hidden, encrypted, support_ban = load_policy(policy)
    password = os.environ.get('ONEC_OBFUSCATOR_MODULE_PASSWORD')

    problems = []
    if encrypted and not password:
        problems.append('encrypted требует пароль, но ONEC_OBFUSCATOR_MODULE_PASSWORD не задан')
    for name in hidden + encrypted:
        if name not in available:
            problems.append('модуль «%s» нельзя закрыть: его нет в списке GET (модуль управляемого приложения, форма, '
                            'команда, модуль с препроцессором или клиентский общий модуль управляемого режима)' % name)

    lines = []
    for name in hidden:
        if name in available:
            lines.append('%s:hidden:' % name)
    for name in encrypted:
        if name in available and password:
            lines.append('%s:encrypted:%s' % (name, password))

    for pr in problems:
        print('ВНИМАНИЕ: %s' % pr, file=sys.stderr)
    if not lines and not support_ban:
        print('нечего закрывать: политика пуста или все модули отклонены', file=sys.stderr)

    # CRLF, как в файле GET: при LF платформа без ошибки закрывает только первый модуль (проба 31.10.2026)
    with open(set_out, 'w', encoding='utf-8', newline='\r\n') as f:
        f.write('\n'.join(lines) + ('\n' if lines else ''))

    print('# План замка 8.5.1 (файл SET записан: %s; в нём пароль — не в git, после применения удалить)' % set_out)
    print('# 1) применить режимы доступа к модулям основной конфигурации:')
    print('1cv8 DESIGNER /IBConnectionString "<строка подключения>" /ModuleSetSourceCodeAccess "%s" /Out set-log.txt' % set_out)
    print('# 2) обновить конфигурацию базы данных:')
    print('1cv8 DESIGNER /IBConnectionString "<строка подключения>" /UpdateDBCfg /Out upd-log.txt')
    print('# 3) проверить, что образы модулей без исходного текста формируются:')
    print('1cv8 DESIGNER /IBConnectionString "<строка подключения>" /CheckConfig -DistributiveModules /Out check-log.txt')
    print('# 4) снять список заново и сверить режимы с политикой: о пропущенной строке платформа не сообщает:')
    print('1cv8 DESIGNER /IBConnectionString "<строка подключения>" /ModuleGetSourceCodeAccess "<файл>" /Out get-log.txt')
    print('python "${CLAUDE_PLUGIN_ROOT}/tools/obfuscator/lock.py" verify --policy "%s" --access-list "<файл>"' % policy)
    print('# hidden необратим: исходный текст удаляется безвозвратно. Сверка пакетного режима: все команды — через')
    print('# Start-Process -Wait -PassThru, ожидание процессов 1cv8 только по пути своей базы (designer-batch-runs).')
    print('# Замок только поверх обфускации: в .cf и в XML-выгрузке остаётся часть исходного текста (проба 31.10.2026).')
    if support_ban:
        print('# ' + support_ban_note())
    return 1 if problems else 0


def plan_8327(policy):
    hidden, encrypted, support_ban = load_policy(policy)
    print('# Замок на платформе 8.3.27 — вручную в Конфигураторе (пакетных команд /ModuleSetSourceCodeAccess нет; они с 8.5.1).')
    if hidden:
        print('# Поставка без исходного текста (необратимо) для модулей:')
        for n in hidden:
            print('#   - %s' % n)
        print('#   Конфигуратор -> Конфигурация -> Поставка конфигурации -> Настройка поставки: для модуля задать поставку')
        print('#   без исходных текстов. Нельзя для модуля управляемого приложения, форм и команд, модулей с препроцессором,')
        print('#   клиентских общих модулей управляемого режима (dev-gl37-gl38 §38.2).')
        print('#   Проверка образов: 1cv8 DESIGNER ... /CheckConfig -DistributiveModules /Out check-log.txt')
    if encrypted:
        print('# Пароль на модуль для модулей:')
        for n in encrypted:
            print('#   - %s' % n)
        print('#   Конфигуратор -> открыть модуль -> Текст -> Установить пароль. В пакетном режиме 8.3.27 модули с паролем')
        print('#   пропускаются с диагностическим сообщением.')
    if support_ban:
        print('# ' + support_ban_note())
    return 0


def verify(access_list, policy):
    """Свежий файл GET против политики: код 1, если модуль не в ожидаемом режиме или его нет в списке."""
    modes = parse_access_list(access_list)
    hidden, encrypted, _ = load_policy(policy)
    wrong = ['%s: ждали %s, в списке %s' % (name, want, modes.get(name, 'нет'))
             for want, names in (('hidden', hidden), ('encrypted', encrypted)) for name in names if modes.get(name) != want]
    for line in wrong:
        print('НЕ ЗАКРЫТ: %s' % line, file=sys.stderr)
    if not wrong:
        print('режимы совпали с политикой: модулей %d' % (len(hidden) + len(encrypted)))
    return 1 if wrong else 0


def main():
    ap = argparse.ArgumentParser(description='План замка модулей 1С для поставки (срез 5, ADR-0008 п.7).')
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('plan', help='построить план замка')
    p.add_argument('--platform', required=True, choices=['8.5.1', '8.3.27'])
    p.add_argument('--policy', required=True)
    p.add_argument('--access-list', help='файл /ModuleGetSourceCodeAccess (нужен для 8.5.1)')
    p.add_argument('--set-out', help='куда записать файл SET (нужен для 8.5.1)')
    v = sub.add_parser('verify', help='сверить режимы модулей с политикой после замка')
    v.add_argument('--policy', required=True)
    v.add_argument('--access-list', required=True, help='свежий файл /ModuleGetSourceCodeAccess')
    args = ap.parse_args()
    if not os.path.isfile(args.policy):
        print('нет файла политики: %s' % args.policy, file=sys.stderr)
        return 2
    if args.cmd == 'verify':
        if not os.path.isfile(args.access_list):
            print('нет файла списка GET: %s' % args.access_list, file=sys.stderr)
            return 2
        return verify(args.access_list, args.policy)
    if args.platform == '8.5.1':
        if not args.access_list or not args.set_out:
            print('для 8.5.1 нужны --access-list (файл GET) и --set-out', file=sys.stderr)
            return 2
        if not os.path.isfile(args.access_list):
            print('нет файла списка GET: %s' % args.access_list, file=sys.stderr)
            return 2
        return plan_851(args.access_list, args.policy, args.set_out)
    return plan_8327(args.policy)


if __name__ == '__main__':
    sys.exit(main())
