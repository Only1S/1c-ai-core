"""Проверка секретов перед коммитом (git pre-commit проекта; ставит /ones-core:setup).

    python secret-scan.py            — проверить то, что подготовлено к коммиту (git add)
    python secret-scan.py --self-test — проверить сами образцы на встроенных примерах

Блокирует коммит (код 1):
  - приватный ключ или токен с узнаваемым префиксом (GitHub, Slack, AWS, Google, Anthropic, npm, GitLab, OpenAI sk-proj-)
    в добавленных строках — в любом файле, и в доке тоже;
  - пароль или токен строкой в коде 1С (.bsl, .os): Пароль = "…", Соединение.Пароль = "…", Токен = "…", КлючAPI = "…"
    и английские имена профиля en (Password, Token, Secret, ApiKey);
  - пароль 1С в строке подключения (Pwd=… рядом с Srvr=/Ref=/File=/Usr=) — в любом файле, кроме доков (.md, .txt,
    .rst, .adoc); Pwd= без строки подключения (переменная pwd = …) — только предупреждение;
  - заголовок Authorization: Basic/Bearer с токеном в JSON (.mcp.json и другие *.json);
  - реквизит-секрет в JSON (ключ password/pwd/token/secret/api_key со значением, которое не плейсхолдер:
    <…>, ${VAR}, $env:VAR, %VAR%, ***, пусто, пример с «...») — разбирается структурно, по всему файлу;
  - файл .env или .env.* (кроме .env.example, .env.sample, .env.template) — секреты живут в окружении, не в git.
Плейсхолдеры (пусто, <…>, ${…}, $env:…, %…%, {…}, ****, «...», слово-заглушка вроде «пароль») коммит не останавливают.
Предупреждает, но не блокирует: эвристики (password=…, Authorization вне JSON, ключ /P у 1cv8, логин:пароль в адресе),
а в доках — и Pwd=, и пароль строкой 1С: там это обычно образцы.
В отчёт идут файл, строка и вид находки; значение — никогда. Не секрет, а отказ стоит — решает владелец, своим коммитом.
Те же образцы, что у проверки мастера ядра (правило secrets-and-production-database). Сбой самого git — пропуск
с предупреждением: проверка не должна запирать коммиты.
"""
import json
import re
import subprocess
import sys

HIGH = re.compile(
    r'-----BEGIN [A-Z0-9 ]*PRIVATE KEY|xox[baprs]-[0-9A-Za-z-]{10,}|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{22,}'
    r'|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{35}|sk-ant-[a-z]{3,5}[0-9]{2}-[A-Za-z0-9_-]{40,}'
    r'|npm_[A-Za-z0-9]{36}|glpat-[A-Za-z0-9_-]{20,}|sk-proj-[A-Za-z0-9_-]{20,}')
PH = r'(?:pass|password|pwd|secret|token|пароль|логин|host|user|usr|admin|changeme|example|xxx|value)'
HEUR = re.compile(
    r'sk-[A-Za-z0-9]{16}|(?:password|api[_-]?key|token|secret)\s*[:=]\s*["\'][A-Za-z0-9+/_-]{12,}["\']'
    # пароли 1С в командной строке: ключ /P… у 1cv8 и --db-pwd/--password у ibcmd (плейсхолдеры — мимо)
    r'|(?:1cv8|ibcmd)\S*\s.*(?:\s/P|--db-pwd[= ]|--password[= ])\s*"?(?![$%<"]|\*)[^\s"]{4,}'
    r'|-u\s+[^\s:"\']+:(?!' + PH + r'\b)[^\s:"\']{8,}|://[^/\s:@]+:(?!' + PH + r'\b)[^/\s:@]{8,}@', re.I)
# пароль 1С в строке подключения Pwd=… — только рядом с Srvr=/Ref=/File=/Usr= (иначе это переменная pwd = …);
# значение и в кавычках "…", ""…"" (строка 1С), &quot;…&quot; (default.vrd); плейсхолдеры <…>, ${…}, %…%, {…}, ****, «...»,
# слово-заглушка и подстановка выражения ("…Pwd=" + Пароль) — мимо
CONN = re.compile(r'\b(?:Srvr|Ref|File|Usr)\s*=', re.I)
PWD = re.compile(r'\bPwd\s*=\s*(?:&quot;|""|"|\')?(?![$%<"\'{\[;&]|\*|' + PH + r'\b)(?![^;"\'&\s]*(?:\.\.\.|…))[^;"\'&\s]{4,}', re.I)
AUTH = re.compile(r'Authorization["\']?\s*[:=]\s*["\']?(?:Basic|Bearer)\s+[A-Za-z0-9+/_-]{8,}', re.I)
# секрет строкой в коде 1С: имя = "значение" (и сравнение тоже); имя — с Пароль/Токен/Секрет/КлючAPI или английской парой
BSL_ASSIGN = re.compile(r'(?<!\w)(\w+)\s*=\s*"([^"]*)"')
# главное слово имени — секрет: в русском оно первое (Пароль, ПарольПользователя, НовыйПароль, ТокенДоступа, КлючAPI),
# в английском — последнее (Password, UserPassword, AccessToken, ClientSecret, ApiKey); PasswordRecoveryOption — не секрет
SECRET_NAME = re.compile(r'^(?:нов(?:ый|ая|ое)|стар(?:ый|ая|ое)|текущ(?:ий|ая|ее)|временн(?:ый|ая|ое))?'
                         r'(?:пароль|токен|секрет(?!ар)|ключ_?(?:api|апи))'
                         r'|(?:passw(?:or)?d|pwd|token|secret|api_?(?:key|ключ))_?\d*$', re.I)
# имя не секрета: английская приставка-слово в CamelCase или snake_case (ShowPassword, SaveToken, max_token — но
# UserPassword секрет), адрес или вид в конце (ТокенURL, PasswordFile)
NOT_SECRET_NAME = re.compile(
    r'^(?:[Tt]ype|[Nn]ame|[Hh]int|[Tt]itle|[Ll]abel|[Ff]ield|[Tt]ext|[Uu]se|[Rr]emember|[Ss]ave|[Cc]heck|[Cc]hange|[Ss]how'
    r'|[Mm]ax|[Mm]in|[Ll]en|[Ee]xpire|[Hh]ash|[Ii]s|[Hh]as)(?=[A-Z_])'
    r'|(?i:(?:url|uri|endpoint|type|name|file|path|header|field|hint|title|label)$)')
# значение-плейсхолдер: пусто, <…>, ${…}, $env:…, %…%, {…}, [...], ****, «...», слово-заглушка, имя поля snake_case
VAL_PH = re.compile(r'^\s*$|^[<$%{\[*]|\.\.\.|…|^' + PH + r'$|^[a-z]+(?:_[a-z]+)+$', re.I)
CODE_1C = ('.bsl', '.os')
DOCS = ('.md', '.markdown', '.txt', '.rst', '.adoc')
# ключ-секрет и в середине имени (ONEC_PASSWORD_PROD), но не адрес или вид (token_url, secret_type)
JSON_KEY = re.compile(r'(?i)(pass(word|wd)?|pwd|api[_-]?key|apikey|secret|token)$'
                      r'|(?:^|[_.-])(pass(word|wd)?|pwd|api[_-]?key|apikey|secret|token)[_.-](?!.*(?:url|uri|endpoint|type|name|file|path|header|env)$)')
JSON_PH = re.compile(r'^\s*$|^<[^>]*>$|^\$\{[^}]+\}$|^\$env:|^%[^%]+%$|^\*+$|\.\.\.')
ENV_FILE = re.compile(r'(^|/)\.env(\.[^/]*)?$')
ENV_OK = re.compile(r'\.(example|sample|template|md)$')
HUNK = re.compile(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@')


def git(*args):
    r = subprocess.run(['git', '-c', 'core.quotepath=off'] + list(args), capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode('utf-8', 'replace').strip() or 'git %s: код %d' % (args[0], r.returncode))
    return r.stdout.decode('utf-8', 'replace')


def is_env_file(path):
    return bool(ENV_FILE.search(path)) and not ENV_OK.search(path)


def json_secrets(node, found):
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, str):
                if JSON_KEY.search(str(k)) and not JSON_PH.search(v):
                    found.append(str(k))
            elif v is not None:
                json_secrets(v, found)
    elif isinstance(node, list):
        for x in node:
            json_secrets(x, found)


def bsl_secret(text):
    """Строка кода 1С присваивает (или сравнивает) имени-секрету строковое значение, не плейсхолдер."""
    for name, val in BSL_ASSIGN.findall(text):
        if (SECRET_NAME.search(name) and not NOT_SECRET_NAME.search(name) and len(val) >= 4
                and not re.search(r'\s', val) and not VAL_PH.search(val)):
            return True
    return False


def conn_pwd(text):
    """Пароль 1С в строке подключения: значение ключа Pwd рядом с ключами Srvr, Ref, File или Usr."""
    return bool(CONN.search(text) and PWD.search(text))


def scan_lines(path, added):
    """added: [(номер строки, текст)] → (блокирующие, предупреждения). Строгость зависит от вида файла (код 1С, дока, JSON)."""
    block, warn = [], []
    low = path.lower()
    code_1c, doc, js = low.endswith(CODE_1C), low.endswith(DOCS), low.endswith('.json')
    for n, text in added:
        if HIGH.search(text):
            block.append('%s:%d — приватный ключ или токен' % (path, n))
        elif code_1c and bsl_secret(text):
            block.append('%s:%d — пароль или токен строкой в коде 1С: читай его из безопасного хранилища или настроек базы, '
                         'в коде не держи' % (path, n))
        elif not doc and conn_pwd(text):
            block.append('%s:%d — пароль 1С в строке подключения (Pwd=): подставляй из окружения — Pwd=${ONEC_PWD} или '
                         '%%ONEC_PWD%%' % (path, n))
        elif js and AUTH.search(text):
            block.append('%s:%d — токен в заголовке Authorization: в файле оставь "Bearer ${TOKEN}", сам токен — в окружении'
                         % (path, n))
        elif HEUR.search(text) or PWD.search(text) or AUTH.search(text) or (doc and bsl_secret(text)):
            warn.append('%s:%d — возможный секрет (эвристика)' % (path, n))
    return block, warn


def scan_staged():
    files = [f for f in git('diff', '--cached', '--name-only', '--diff-filter=ACMR', '-z').split('\0') if f]
    block, warn = [], []
    for f in files:
        if is_env_file(f):
            block.append('%s — файл с переменными окружения: секреты держат вне git (.gitignore)' % f)
    # Пути — без кавычек и \-кодов (core.quotePath=false): иначе `+++ "b/Справочники/…"` выгрузки 1С не узнавался как
    # заголовок, и все добавленные строки такого файла не проверялись (аудит 30.10.2026). Приставки — явно: при личной настройке
    # diff.noprefix, diff.mnemonicPrefix или diff.dstPrefix путь шёл без b/, и проверка молча ничего не находила (замер 30.10.2026).
    diff = git('-c', 'core.quotePath=false', 'diff', '--cached', '--no-color', '--no-ext-diff', '--src-prefix=a/', '--dst-prefix=b/',
               '-U0', '--diff-filter=ACMR')
    path, line, added, header = None, 0, {}, False
    for raw in diff.split('\n'):
        if raw.startswith('diff --git '):
            header, path = True, None
            continue
        if header:
            # заголовок файла — только до первого @@: добавленная строка «++ …» в теле правки заголовком не считается
            if raw.startswith('+++ '):
                p = raw[4:].strip()
                p = p[1:-1] if len(p) > 1 and p[0] == p[-1] == '"' else p
                path = p[2:] if p.startswith('b/') else None
                continue
            m = HUNK.match(raw)
            if not m:
                continue
            header = False
        m = HUNK.match(raw)
        if m:
            line = int(m.group(1))
            continue
        if path and raw.startswith('+'):
            added.setdefault(path, []).append((line, raw[1:]))
            line += 1
    for p, lines in added.items():
        b, w = scan_lines(p, lines)
        block += b
        warn += w
    for f in files:
        if f.lower().endswith('.json') and not f.endswith('package-lock.json'):
            try:
                data = json.loads(git('show', ':' + f).lstrip('﻿'))
            except (RuntimeError, ValueError):
                continue
            keys = []
            json_secrets(data, keys)
            for k in keys:
                block.append('%s — реквизит-секрет в ключе «%s»: вынеси в .env или окружение, в файле оставь ${VAR}' % (f, k))
    return block, warn


def self_test():
    """Образцы собираются из частей: в самом файле не должно быть ни одного настоящего на вид секрета."""
    hits = [
        '-----BEGIN ' + 'RSA PRIVATE KEY-----', 'gh' + 'p_' + 'A1b2' * 9, 'github' + '_pat_' + 'x' * 30,
        'AK' + 'IA' + 'ABCDEFGHIJKLMNOP', 'xo' + 'xb-' + '1234567890-abc', 'sk-' + 'ant-api03-' + 'Z' * 45,
        'np' + 'm_' + 'A1b2C3d4' * 4 + 'Z9y8', 'gl' + 'pat-' + 'x1Y2z3W4' * 3, 'sk-' + 'proj-' + 'Ab12' * 12,
    ]
    misses = ['token = ${GITHUB_TOKEN}', 'ghp_short', 'описание: ключ доступа хранится в окружении', 'npm_short',
              '"Authorization": "Bearer ${TOKEN}"', 'Srvr=srv;Ref=base;Pwd=${ONEC_PWD};', '1cv8 DESIGNER /N Admin /P%ONEC_PWD%',
              'Srvr=srv;Ref=base;Pwd=<пароль>;', 'Srvr=srv;Pwd=****;', 'Srvr=srv;Pwd=пароль;', 'Srvr=srv;Pwd=;']
    heur = ['password = "' + 'Qw3rtyUiop12' + '"', 'Authorization: Bearer ' + 'abcdefgh12345', 'https://' + 'ivan:S3cretPass99' + '@host/x',
            '"Authorization": "' + 'Bearer ' + 'abcdefgh12345' + '"', 'Srvr=srv;Ref=base;Usr=a;' + 'Pwd=' + 'Qw3rty9;',
            '1cv8.exe DESIGNER /S srv' + chr(92) + 'b /N Admin ' + '/P' + 'Qw3rty9', 'ibcmd infobase dump --db-user=a ' + '--db-pwd=' + 'Qw3rty9']
    errors = []
    errors += ['не поймал: %s…' % s[:14] for s in hits if not HIGH.search(s)]
    errors += ['ложная тревога: %s' % s for s in misses if any(r.search(s) for r in (HIGH, HEUR, PWD, AUTH))]
    errors += ['эвристика не поймала: %s…' % s[:14] for s in heur if not any(r.search(s) for r in (HEUR, PWD, AUTH))]
    # строгость по виду файла: код 1С, JSON и прочее — отказ; дока — только предупреждение; плейсхолдеры — тишина
    v = 'Qw3' + 'rty9' + 'Zx'
    stop = [('m.bsl', 'Пароль = "' + v + '";'), ('m.bsl', 'Соединение.Пароль = "' + v + '";'), ('m.bsl', 'Токен = "' + v + '";'),
            ('m.bsl', 'КлючAPI = "' + v + '";'), ('m.os', 'Connection.Password = "' + v + '";'),
            ('m.bsl', 'Стр = "Srvr=srv;Ref=base;' + 'Pwd=' + v + ';";'), ('.mcp.json', '"Authorization": "Bear' + 'er ' + v + 'abc"'),
            ('notes.md', hits[-3])]
    quiet = [('m.bsl', 'Пароль = "";'), ('m.bsl', 'Пароль = "<пароль>";'), ('m.bsl', 'Соединение.Пароль = "${ONEC_PWD}";'),
             ('m.bsl', 'Токен = "****";'), ('m.bsl', 'ТипТокена = "Bearer";'), ('m.bsl', 'ПодсказкаПароля = "Введите пароль";'),
             ('m.bsl', 'Пароль = Константы.ПарольСервиса.Получить();'), ('m.bsl', 'Стр = "Srvr=srv;Pwd=" + Пароль + ";";'),
             ('m.bsl', 'Токен = "access_token";'),('.mcp.json', '"Authorization": "Bearer ${ONEC_TOKEN}"'),
             ('SKILL.md', 'Пароль = "<образец>"'), ('SKILL.md', 'Srvr=srv;Pwd=<пароль>;')]
    for p, s in stop:
        if not scan_lines(p, [(1, s)])[0]:
            errors.append('не остановил: %s… (%s)' % (s[:12], p))
    for p, s in quiet:
        if any(scan_lines(p, [(1, s)])):
            errors.append('ложная находка: %s (%s)' % (s, p))
    for p, s in (('SKILL.md', 'Соединение.Пароль = "' + v + '";'), ('SKILL.md', 'Srvr=srv;' + 'Pwd=' + v + ';')):
        b, w = scan_lines(p, [(1, s)])
        if b or not w:
            errors.append('образец в доке: ждали предупреждение без отказа: %s… (%s)' % (s[:12], p))
    keys = []
    json_secrets({'bases': [{'user': 'Админ', 'password': 'Real' + 'Pass1'}, {'password': '${DB_PASS}'}, {'token': '<токен>'}],
                  'env': {'ONEC_PASSWORD_PROD': 'Real' + 'Pass2', 'token_url': 'https://x/oauth', 'max_tokens': '100'}}, keys)
    if keys != ['password', 'ONEC_PASSWORD_PROD']:
        errors.append('JSON: ожидались ключи password и ONEC_PASSWORD_PROD, найдено %s' % keys)
    if not (is_env_file('.env') and is_env_file('conf/.env.local')) or any(is_env_file(x) for x in ('.env.example', '.env.sample', 'docs/.env.md')):
        errors.append('распознавание файлов .env')
    for e in errors:
        print('[FAIL] ' + e)
    print('самопроверка: %s' % ('FAIL=%d' % len(errors) if errors else 'всё верно'))
    return 1 if errors else 0


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    if '--self-test' in sys.argv:
        return self_test()
    try:
        block, warn = scan_staged()
    except (OSError, RuntimeError) as e:
        print('ones-core: проверка секретов пропущена — %s' % e)
        return 0
    for w in warn:
        print('[ВНИМАНИЕ] ' + w)
    if block:
        for b in block:
            print('[СЕКРЕТ] ' + b)
        print('Коммит остановлен проверкой секретов ones-core. Убери секрет из подготовленных файлов (git restore --staged <файл>); '
              'если это точно не секрет — скажи владельцу: обойти проверку может только он, своим коммитом.')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
