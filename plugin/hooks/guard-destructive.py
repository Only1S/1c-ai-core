"""PreToolUse: защита до выполнения — останавливает разрушительные и опасные команды.

Перенос guard-destructive.ps1 на Python (ADR-0002) один к одному; поведение сверяется теми же
проверками contour-tests (раздел 6). Что ловится:
  - разрушительные команды: rm с рекурсией и принуждением и rm с рекурсией вне временной папки, Remove-Item -Recurse (псевдонимы
    ri/del/erase/rd/rmdir, сокращения ключа), rmdir /s и del /s (и слитно /q/s), robocopy /MIR и /PURGE, [IO.Directory]::Delete и
    .Delete($true), конвейер целиком (gci -Recurse | Remove-Item, find | xargs rm), git reset --hard / clean -f / checkout . и -f /
    switch -f и --discard-changes / restore каталога (., папка/; --staged и один файл проходят) / push --force, +refspec, --mirror,
    --delete, :ветка / stash clear и drop / branch -D и -d -f / filter-branch / reflog expire / gc --prune=now / update-ref -d /
    commit --no-verify и склейка -nm / --no-gpg-sign / core.hooksPath в git -c, git config и GIT_CONFIG_*;
  - правка реестра Windows (reg add/delete/import/…, regedit /s, *-ItemProperty и *-Item по HKLM:/HKCU:/Registry::);
  - чтение и копирование секретов (.env и .env.* кроме образцов, ключи, учётные данные из домашнего каталога, .pgpass)
    читающей утилитой (READERS — по всему тексту) и любой другой программой (по словам-путям, в том числе маска .en? и путь в
    переменной этой же команды), кроме безобидных SECRET_SAFE (ls, test, stat, wc, echo…), конвейером (ls .env | xargs cat),
    инструментами Read и Grep — по всей машине (запрет Read(**/…) действует только в папке проекта), печать токена gh и окружения
    (env, printenv, Get-ChildItem Env:, echo $…TOKEN); у grep/rg/sed/awk/findstr/Select-String первый позиционный аргумент —
    шаблон или программа, а не файл;
  - запись из оболочки в файлы доверия барьеров (OWNER_FILES): журнал сессии, logs/consent.json, .v8-project.json, настройки
    Claude Code, .mcp.json, настройки ssh-mcp, хуки git, .git/config, с 20.11.2026 .bsl-language-server.json — перенаправлением,
    tee, cp/mv/rm, sed -i, Set-Content, кодом
    (write_text, open(…,'w'), writeFileSync, [IO.File]::Write*: цель записи — литерал или переменная с литералом, имя в тексте,
    который код пишет в другой файл, не запись); чтение и копия ИЗ них проходят; claude mcp add; reload-config с action=reload;
    слой экрана из оболочки (SendKeys, CopyFromScreen, mouse_event, pyautogui, nircmd);
  - запись в базу 1С, не зарегистрированную в .v8-project.json (CLI 1cv8/1cv8c/ibcmd: /F, /S, /IBName, File=, Srvr=, Ref=,
    --db-path, --db-server, --db-name; скрипты скиллов db-*, web-publish, epf-dump, erf-dump: -InfoBasePath, -InfoBaseServer,
    -InfoBaseRef; массив -ArgumentList и переменные этой же команды подставляются, аргументы в неизвестной переменной, /@ и
    ibcmd --config — отказ, ibcmd --remote и -r сверяются как сервер): сервер и имя базы сверяются ПАРОЙ с одной записью
    databases[] (server + ref), незнакомый сервер — отказ,
    псевдонимы — не имя базы; путь базы нормализуется ("D:\\\\…" в кавычках Bash, /d/… Git Bash, слэши, регистр); база
    судится только у сегмента, который может запустить платформу — у печатающих программ (grep, echo, git …) нет;
  - изменяющий SQL (INSERT/UPDATE/DELETE/MERGE/ALTER/CREATE/GRANT…, обрыв сеансов и обслуживание: pg_terminate_backend,
    VACUUM, REINDEX, CLUSTER, CALL, DO, EXEC, KILL; файл или поток запросов, pg_restore) через psql/sqlcmd/
    mysql и т. п. к серверу, которого нет среди серверов реестра (server или dbServer записи; или без адреса); DROP/TRUNCATE —
    к любому;
  - команда в кавычках вложенной оболочки (bash/sh -c, cmd /c, pwsh -Command, eval в позиции команды, Invoke-Expression) и код
    интерпретатора (python -c, node -e): рекурсивное удаление (shutil.rmtree, fs.rmSync с recursive) и команды, которые код
    запускает; eval аргументом другой программы (`claude plugin eval …`) — не вычисление строки;
  - запуск скрипта скилла без -V8Path, если выше каталога запуска нет .v8-project.json с v8path (выбралась бы
    новейшая платформа и могла сконвертировать базу);
  - прямой запуск скриптов необратимых скиллов (meta-remove, support-edit, remove-form, remove-template, db-load-dt);
  - адреса со схемой file:/data:/javascript: и эндпоинты метаданных облака (до запроса);
  - запись в файлы, которым верят барьеры: реестр .v8-project.json, файл состояния тулкита, установленный плагин; обращение к
    серверу 1c-toolkit мимо MCP (порт тулкита, /mcp; с 20.11.2026 и в теле heredoc, поданном интерпретатору) и чтение таблиц
    данных клиентом СУБД (замер 30.10.2026), кроме базы
    реестра с pd: none, названной в команде сервером и именем;
  - дисциплина команд (с 17.10.2026): пакетный запуск 1cv8 не через Start-Process -Wait (в том числе кодом python -c/node -e,
    [Diagnostics.Process]::Start, созданием Win32_Process), остановка и ожидание процессов 1С по имени (Stop-Process/taskkill
    /IM и /FI, wmic и CIM Terminate, через переменную с отбором по имени; designer-batch-runs), фон через `&` вместо
    run_in_background, проверки ядра (и recall-check, build-plugin --validate) и обновление плагина и канала без
    run_in_background (run-checks-quietly-in-background), сообщение коммита через heredoc или here-string
    (tool-calls-not-chat-text п.3). Команда режется без разрезов внутри кавычек: `;` и `|` в тексте сообщения коммита, echo или
    шаблоне grep — данные; текст вложенной оболочки и Start-Process оболочки судится как команды (30.10.2026).
Команда удаления (rd, del, Remove-Item, rm) — отдельным словом или программой в позиции команды, а не частью пути (C:\\dir\\rd).
Префикс команды `env …` и присваивания `ИМЯ=значение` перед программой барьер срезает, а не принимает за другую программу.
Тело heredoc (`cat > f <<'EOF' … EOF`) и here-string PowerShell (`@' … '@`) — данные, а не команды (волна 2, 30.10.2026):
барьер судит команду без них, оставляя от раскрываемого тела (<<EOF без кавычек, @") подстановки $( ) и `…`. Тело,
которое читает исполнитель, судится как команды: оболочка (bash <<EOF, sh -s, cat <<EOF | bash, sudo -s, '@ | iex, eval
строки с телом), интерпретатор (python - <<EOF — ещё и как код), ssh (как команды на сервере), клиент СУБД (как SQL),
файл с телом, который та же команда запускает (bash run.sh, ./run.sh); тело без строки-конца — тоже команды.
Инструменты ssh-mcp (с 20.10.2026): удалённая команда (параметр command) проверяется теми же правилами, что и Bash;
локальный файл (localPath) не может быть секретом или учётными данными (вывоз на сервер), скачивание пишет только
во временную папку — иначе запись шла бы мимо барьеров Edit/Write, — и не скачивает секрет (remotePath). Удалённая команда
в кавычках (`ssh хост '…'`, `tmux send-keys '…'`, помощник `vm-shell`) разбирается как отдельные команды. На сервере
(ssh, vm-shell, ssh-mcp) ещё запрещены kill/killall/pkill, pg_ctl stop/kill, truncate и chmod/chown -R.

Честные границы: скрипт в файле и закодированная команда (-EncodedCommand) не разбираются — что делает `python x.py`, по тексту
команды не видно, виден только секрет в её аргументах; путь, собранный кодом или из другой команды (Join-Path, переменная прошлой
команды, относительный путь после cd), не сверяется, кроме имени consent.json; код, читающий окружение (os.environ), не
разбирается; запуск приложений из оболочки (start, Start-Process) слоем экрана не считается; рекурсивный поиск по каталогу
(grep -r) может задеть .env — барьер его не ловит; изменяющий SQL узнаётся по ключевым словам запроса, а содержимое файла
запросов не читается — файл или поток к чужому серверу считается изменяющим; вопрос «ask» не используется — канал
подтверждения не гарантирован, поэтому только отказ. Ключ --all-reasons (мод ask-guard, ADR-0011) не выносит решения: печатает
JSON-список всех отказов команды, потому что окно мода разрешает команду целиком.

Отказ: код 0 + JSON permissionDecision=deny (работает и в режиме без подтверждений).
Любая внутренняя ошибка — пропуск (сломанная защита не должна блокировать работу) с видимой пометкой DEGRADED
(systemMessage); первичный барьер — permissions.deny проекта.

Важно при сверке с PowerShell-версией: оператор -match там НЕ учитывает регистр (здесь — re.I), а -cmatch
учитывает (git branch -D); -contains тоже без учёта регистра.
"""
import fnmatch
import io
import json
import os
import re
import sys

I = re.IGNORECASE


REASONS = None   # режим --all-reasons (мод ask-guard, ADR-0011): отказы копятся, разбор идёт до конца команды


def emit_deny(reason):
    if REASONS is not None:
        REASONS.append(reason)
        return
    payload = {'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'permissionDecision': 'deny',
        'permissionDecisionReason': reason,
    }}
    sys.stdout.buffer.write(json.dumps(payload, ensure_ascii=False).encode('utf-8'))
    sys.stdout.flush()
    sys.exit(0)


def temp_dir():
    """Папка временных файлов, как tempfile.gettempdir(), но без импорта tempfile: он тянет shutil и random — около 50 мс
    на каждом вызове частого хука (замер 11.11.2026). Порядок переменных — как у tempfile; нет ни одной — сам tempfile."""
    for k in ('TMPDIR', 'TEMP', 'TMP'):
        d = os.environ.get(k)
        if d and os.path.isdir(d) and os.access(d, os.W_OK):
            return os.path.abspath(d)
    import tempfile
    return tempfile.gettempdir()


def m(pattern, text, flags=I):
    return re.search(pattern, text, flags) is not None


# `env -i A=1 python …`, `PYTHONIOENCODING=utf-8 python …`: программа — после префикса
ENV_PREFIX = re.compile(r'^(?:env(?:\s+-\S+)*\s+)?(?:[A-Za-z_]\w*=(?:"[^"]*"|\'[^\']*\'|\S*)\s+)*')


def strip_env_prefix(s):
    return ENV_PREFIX.sub('', s, count=1)


def split_outside_quotes(cmd, pipes=True):
    """Части команды по переводу строки, &&, ||, ;, | — кроме разделителей внутри кавычек (строки подключения 1С);
    pipes=False — звенья конвейера `|` остаются в одной части (оператор целиком: отбор процессов и их остановка)."""
    seps = '\n;|' if pipes else '\n;'
    parts, cur, q, i = [], [], '', 0
    while i < len(cmd):
        ch = cmd[i]
        if q:
            cur.append(ch)
            if ch == q:
                q = ''
        elif ch in '"\'':
            q = ch
            cur.append(ch)
        elif cmd.startswith('&&', i) or cmd.startswith('||', i):
            parts.append(''.join(cur))
            cur = []
            i += 1
        elif ch in seps:
            parts.append(''.join(cur))
            cur = []
        else:
            cur.append(ch)
        i += 1
    parts.append(''.join(cur))
    return [p for p in parts if p.strip()]


def tokens_of(text):
    """Слова команды без кавычек вокруг: литерал с пробелами — одно слово."""
    return [t[1:-1] if len(t) > 1 and t[0] == t[-1] and t[0] in '"\'' else t
            for t in re.findall(r'"[^"]*"|\'[^\']*\'|\S+', text)]


def abbrev(full, n):
    """Длинный ключ и его сокращения от n знаков: git принимает однозначный префикс (`--har` = `--hard`, аудит 30.10.2026).
    Конец ключа — не буква и не дефис: `--force-with-lease` и `--follow-tags` под `--force` не попадают."""
    return r'(?:' + '|'.join(re.escape(full[:k]) for k in range(len(full), n - 1, -1)) + r')(?![\w-])'


# Имя команды удаления PowerShell/cmd отдельным словом (не часть пути `C:\dir\rd` и не `rd.txt`); Remove-Item бывает с модулем
DEL_WORD = r'(?:^|[\s;&|({}])(?:Microsoft\.PowerShell\.Management\\)?(?:%s)(?=$|[\s;&|)}])'
# rm — отдельным словом где угодно (`xargs rm`, `sudo -u x rm`) или путём к программе в позиции команды (`/bin/rm -rf`);
# путь, который кончается на \rm, в аргументах другой программы (`Get-ChildItem C:\x\rm -Recurse -Force`) — не удаление
RM_CMD = (DEL_WORD % 'rm') + r'|(?:^|[;&|({}`]|\$\()\s*(?:(?:sudo|doas|xargs|exec|command|builtin|nohup|time|nice|env)' \
    r'(?:\s+-\S+)*\s+)*\S*[\\/]rm(?=$|[\s;&|)}])'


# rm в позиции команды, а не слово в аргументах (`grep -r rm docs/`): рекурсия без принуждения судится только здесь
RM_AT_CMD = (r'(?:^|[;&|({`]|\$\()\s*(?:(?:(?:sudo|doas)(?:\s+-u\s+\S+)?|xargs|exec|command|builtin|nohup|time|nice|env)(?:\s+-\S+)*\s+)*'
             r'(?:\S*[\\/])?rm(?=$|[\s;&|)}])')
# ключи rm слитно: только его буквы, иначе -Force и -ErrorAction PowerShell считались рекурсией (буква r)
RM_SHORT = r'(?:^|\s)-[dfiIPrRvx]*%s[dfiIPrRvx]*(?=\s|$)'
TEMP_PATH = r'^(?:/tmp|/var/tmp|\$\{?(?:TMP|TEMP|TMPDIR)\}?|\$env:(?:TMP|TEMP)|%(?:TMP|TEMP)%)[\\/].'
GIT_OPTS = r'\bgit(?:\s+-\S+(?:\s+[^\s-]\S*)??)*?\s+'   # git с общими ключами до подкоманды: `git -c a=b commit`
# склейка коротких ключей коммита: до -n — только ключи без значения (-uno и -mn — значения ключей -u и -m, а не -n)
COMMIT_NO_HOOKS = GIT_OPTS + r'commit\b.*(?:' + abbrev('--no-verify', 9) + r'|(?:^|\s)-[aeiopqsvz]*n[A-Za-z]*(?=\s|$))'
BRANCH_FORCE_DELETE = (r'\bbranch\b(?=.*\s(?:-[a-zA-Z]*d[a-zA-Z]*(?:\s|$)|' + abbrev('--delete', 4) + r'))'
                       r'(?=.*\s(?:-[a-zA-Z]*f[a-zA-Z]*(?:\s|$)|' + abbrev('--force', 6) + r'))')


def in_temp(p):
    """Путь во временной папке: по имени ($TMP, /tmp, %TEMP%, scratchpad сессии) или по настоящему пути; `..` выводит из неё."""
    p = p.strip().rstrip('\\/')
    if not p or re.search(r'(?:^|[\\/])\.\.(?:[\\/]|$)', p):
        return False
    if m(TEMP_PATH, p) or m(r'[\\/]scratchpad[\\/]', p):
        return True
    native = re.sub(r'^/([a-zA-Z])(?=/)', r'\1:', p)
    return os.path.isabs(native) and under_temp(native)


def rm_leaves_temp(text):
    """Рекурсивный rm бьёт мимо временной папки: цель не видна (`xargs rm -r`) или хотя бы одна цель вне неё."""
    toks = tokens_of(text)
    i = next((k for k, t in enumerate(toks) if re.split(r'[\\/]', t)[-1].lower() == 'rm'), None)
    args = [t for t in toks[i + 1:] if not t.startswith('-')] if i is not None else []
    return not args or not all(in_temp(a) for a in args)


def restore_discards(s):
    """git restore отбрасывает правки целого каталога: путь `.`, `*`, `:/` или с концевым слэшем. Один файл — обычная работа
    (`.github/x.yml` — не `.`), --staged без --worktree дерева не трогает."""
    mm = re.search(r'\brestore\b(.*)$', s, I)
    if not mm:
        return False
    toks, paths, staged, worktree, i = mm.group(1).split(), [], False, False, 0
    while i < len(toks):
        t = toks[i]
        if t == '--':
            paths += toks[i + 1:]
            break
        if t.startswith('--'):
            staged = staged or (len(t) > 3 and '--staged'.startswith(t))
            worktree = worktree or (len(t) > 3 and '--worktree'.startswith(t))
            i += 2 if t in ('--source', '--pathspec-from-file') else 1
        elif t.startswith('-') and len(t) > 1:
            if t[1] != 's':
                staged, worktree = staged or 'S' in t, worktree or 'W' in t
            i += 2 if t == '-s' else 1
        else:
            paths.append(t)
            i += 1
    if staged and not worktree:
        return False
    return any(p in ('.', './', '*', ':/', ':/*') or p.endswith(('/', '\\')) for p in paths)


def hooks_path_changed(s, raw):
    """core.hooksPath уводит git мимо хуков .git/hooks: разовым -c, настройкой, переменными GIT_CONFIG_*. Чтение настройки — можно."""
    if m(r'\bgit(?:\s+-\S+(?:\s+[^\s-]\S*)??)*?\s+(?:-c\s*|--config-env[= ]\s*)core\.hookspath', s):
        return True
    if m(r'\bGIT_CONFIG_(?:KEY_\d+|PARAMETERS)\b', s) and m(r'core\.hookspath', raw or s):
        return True
    mm = re.search(GIT_OPTS + r'config\b(.*)$', s, I)
    toks = mm.group(1).split() if mm else []
    keys = [i for i, t in enumerate(toks) if t.lower() == 'core.hookspath']
    if not keys or any(t in ('--get', '--get-all', '--get-regexp', '-l', '--list', 'get', 'list') for t in toks):
        return False
    return any(t in ('--unset', '--unset-all', '--replace-all', '--add', 'set', 'unset') for t in toks) or \
        any(not t.startswith('-') for t in toks[keys[0] + 1:])


# Программа удаления под другим именем: `r=rm; $r -rf x`, `alias x='rm -rf'; x y`
DEL_ALIAS = r'(?:^|[\s;&|(])(?:alias\s+)?([A-Za-z_]\w*)=["\']?((?:\S*[\\/])?(?:rm|rmdir|Remove-Item)(?:\s+-[^\s"\']+)*)["\']?(?=$|[\s;&|)])'


def expand_del_alias(cmd):
    """Подставляет значение вместо имени в позиции команды, дальше команду судят обычные правила удаления."""
    for name, value in re.findall(DEL_ALIAS, cmd):
        cmd = re.sub(r'\$\{?%s\}?(?=$|[\s;&|)])' % name, lambda _: value, cmd)
        cmd = re.sub(r'(^|[;&|(]\s*)%s(?=\s)' % name, lambda x: x.group(1) + value, cmd, flags=re.M)
    return cmd


def destructive(s, on_server=False, raw=None):
    """Причина отказа для разрушительной команды или None; on_server — команда исполнится на сервере (ssh, vm-shell, ssh-mcp);
    raw — та же команда с литералами: цели rm в кавычках и значения переменных."""
    if m(RM_CMD, s):
        rec = m(RM_SHORT % '[rR]', s) or m(r'--recursive\b|(?:^|\s)-rec(?:u(?:r(?:se?)?)?)?(?=\s|:|$)', s)
        frc = m(RM_SHORT % 'f', s) or m(r'--force\b|(?:^|\s)-fo(?:r(?:ce?)?)?(?=\s|$)', s)
        if rec and frc:
            return 'rm с рекурсией и принуждением — безвозвратное удаление'
        if rec and m(RM_AT_CMD, strip_env_prefix(s)) and rm_leaves_temp(raw or s):
            return 'rm с рекурсией вне временной папки — безвозвратное удаление каталога, в том числе файлов только для чтения'
    # команда удаления — отдельным словом, а не частью пути: `Get-ChildItem C:\dir\rd -Recurse` ничего не удаляет
    if m(DEL_WORD % r'Remove-Item|ri|del|erase|rd|rmdir', s) and m(r'(^|\s)-r(e(c(u(r(s(e)?)?)?)?)?)?(\s|:|$)', s):
        return 'Remove-Item -Recurse (псевдонимы ri/del/erase/rd/rmdir, сокращения ключа) — рекурсивное удаление'
    if m(DEL_WORD % 'rm', s) and m(r'-Recurse', s) and m(r'-Force', s):
        return 'Remove-Item -Recurse -Force — безвозвратное рекурсивное удаление'
    if m((DEL_WORD % 'rd|rmdir') + r'.*\s/{1,2}(?:q/{1,2})?s\b', s):
        return 'rmdir /s — рекурсивное удаление'
    if m((DEL_WORD % 'del') + r'.*\s/{1,2}(?:[qf]/{1,2})*s\b', s):
        return 'del /s — рекурсивное удаление'
    if m(r'\[(?:System\.)?IO\.Directory\]::Delete\s*\([^)]*\$true|\.Delete\s*\(\s*\$true\s*\)', s) or \
            (m(r'\bFileSystem\]::DeleteDirectory\b', s) and not m(r'SendToRecycleBin', raw or s)):
        return 'рекурсивное удаление в коде интерпретатора ([IO.Directory]::Delete, .Delete($true)) — безвозвратно, мимо корзины'
    if m(r'(?:^|[\s;&|(])robocopy(?:\.exe)?(?=\s).*\s/{1,2}(?:MIR|PURGE)\b', s):
        return 'robocopy /MIR или /PURGE — удаляет в приёмнике всё, чего нет в источнике'
    if m(r'\bfind\b.*\s-(delete\b|exec(dir)?\s+(\S*[\\/])?(rm|unlink|shred)\b)', s):
        return 'find … -delete / -exec rm — массовое удаление файлов'
    if hooks_path_changed(s, raw):
        return ('core.hooksPath — обход проверок перед коммитом: красный health-check, сканер секретов и запрет строки '
                'Co-Authored-By не сработают (work-journals-and-commits п.8)')
    if m(r'\bgit\b', s):
        if m(r'\breset\b.*' + abbrev('--hard', 4), s):
            return 'git reset --hard — потеря незакоммиченной работы'
        if m(r'\bclean\b.*(-[A-Za-z]*f|' + abbrev('--force', 3) + ')', s):
            return 'git clean -f/--force — удаление неотслеживаемых файлов (без -f git не удаляет: -n/--dry-run/-nd проходят)'
        if m(r'\bcheckout\b\s+(\.|--(\s|$))', s):
            return 'git checkout . / -- — отброс правок рабочего дерева'
        if m(r'\bcheckout\b.*((^|\s)-[A-Za-z]*f\b|' + abbrev('--force', 5) + r'|\s--\s+\.(\s|$))', s):
            return 'git checkout -f/--force или <ref> -- . — отброс правок рабочего дерева'
        if m(r'\bswitch\b.*((^|\s)-[A-Za-z]*f\b|' + abbrev('--force', 5) + '|' + abbrev('--discard-changes', 4) + ')', s):
            return 'git switch -f/--discard-changes — отброс правок рабочего дерева'
        if m(r'\bstash\s+(clear|drop)\b', s):
            return 'git stash clear/drop — уничтожение сохранённых правок'
        if restore_discards(s):
            return 'git restore . — отброс правок рабочего дерева'
        if m(r'\bpush\b.*(' + abbrev('--force', 5) + r'|(^|\s)-[A-Za-z]*f[A-Za-z]*(\s|$)|(^|\s)\+\S|' + abbrev('--mirror', 4) + ')', s):
            return 'force-push (--force, -f, +refspec, --mirror) — перезапись удалённой истории'
        if m(r'\bpush\b.*(?:' + abbrev('--delete', 4) + r'|(?:^|\s)-[A-Za-z]*d[A-Za-z]*(?:\s|$)|(?:^|\s):\S)', s):
            return 'git push --delete или :ветка — удаление ветки на удалённом репозитории'
        if m(r'\bbranch\b.*(^|\s)-D\b', s, 0) or m(BRANCH_FORCE_DELETE, s, 0):
            return 'git branch -D — форс-удаление ветки без проверки слияния (-cmatch: -d безопасен, git откажет на несмерженной)'
        if m(r'filter-branch', s):
            return 'git filter-branch — переписывание истории'
        if m(r'\breflog\b.*expire', s):
            return 'git reflog expire — уничтожение сети безопасности'
        if m(r'\bgc\b.*--prune=now', s):
            return 'git gc --prune=now — уничтожение висячих объектов'
        if m(r'update-ref\s+-d', s):
            return 'git update-ref -d — удаление ссылки'
        if m(COMMIT_NO_HOOKS, s):
            return 'git commit --no-verify — обход pre-commit health-check (work-journals-and-commits п.8)'
        if m(r'\bcommit\b.*' + abbrev('--no-gpg-sign', 6), s):
            return 'git commit --no-gpg-sign — обход подписи'
    # Серверные команды (чекап 29.10.2026): только разрушительное и необратимое; чтение и restart проходят
    lead = r'^\s*(sudo\s+(-\S+\s+)*)?'
    if m(r'\bsystemctl\s+(--?\S+\s+)*(stop|disable|mask|kill|isolate|poweroff|reboot|halt|suspend|hibernate)\b', s):
        return 'systemctl stop/disable/mask/kill — остановка или отключение службы на сервере'
    if m(r'\bservice\s+\S+\s+stop\b', s):
        return 'service … stop — остановка службы на сервере'
    if m(lead + r'(shutdown|poweroff|reboot|halt)\b', s):
        return 'выключение или перезагрузка машины'
    if m(r'\b(mkfs(\.\w+)?|wipefs|fdisk|sfdisk|parted)\b', s) or m(r'\bdd\b.*\bof=/dev/', s):
        return 'разметка, форматирование или запись поверх устройства (mkfs/wipefs/fdisk/parted/dd of=/dev)'
    if m(r'\b(lvremove|vgremove|pvremove|lvreduce)\b', s):
        return 'удаление или уменьшение тома LVM — данные на томе пропадут'
    if m(r'\brac\b.*\b(infobase|session|cluster|server|process|connection)\b.*\b(drop|terminate|remove|disconnect)\b', s):
        return 'rac … drop/terminate/remove — удаление базы из кластера или обрыв сеансов пользователей'
    if m(r'\b(dropdb|dropuser)\b', s):
        return 'dropdb/dropuser — удаление базы или роли PostgreSQL'
    if m(r'\bapt(-get)?\s+(\S+\s+)*(purge|remove|autoremove)\b', s) or m(r'\bdpkg\s+(-r|-P|--remove|--purge)\b', s):
        return 'удаление пакетов на сервере (apt purge/remove/autoremove, dpkg -r/-P)'
    if m(r'\bufw\s+(--force\s+)?(disable|reset)\b', s) or m(r'\biptables\s+(-F|--flush)\b', s):
        return 'сброс или отключение сетевого экрана (ufw disable/reset, iptables -F)'
    if m(r'\bcrontab\s+-r\b', s):
        return 'crontab -r — удаление всех заданий расписания'
    return server_only(s) if on_server else None


def server_only(s):
    """Только на сервере: остановка процессов и СУБД, затирание файла, рекурсивная смена прав (локально — обычная работа)."""
    if m(r'\b(killall|pkill)\b', s) or m(r'(^|[\s;&|(])kill\s+(?!-(0|l)(\s|$))\S', s):
        return 'kill/killall/pkill на сервере — остановку процессов 1С и СУБД выполняет владелец сам'
    if m(r'\bpg_ctl(cluster)?\b.*\b(stop|kill)\b', s):
        return 'pg_ctl stop/kill — остановку СУБД на сервере выполняет владелец сам'
    if m(r'(^|[\s;&|(])truncate\s+-', s):
        return 'truncate — затирание файла на сервере'
    if m(r'\b(chmod|chown|chgrp)\s+(\S+\s+)*?(-[A-Za-z]*R\b|--recursive\b)', s, 0):
        return 'chmod/chown -R — рекурсивная смена прав или владельца на сервере'
    return None


def sql_drop(raw):
    """DROP/TRUNCATE в запросе к СУБД — по тексту ДО вырезания кавычек: запрос почти всегда стоит в кавычках."""
    if m(r'\b(psql|sqlcmd|osql|mysql|clickhouse-client|pg_dump|pgbench)\b', raw) and \
            m(r'\b(DROP\s+(DATABASE|TABLE|SCHEMA|ROLE|USER|OWNED|EXTENSION)|TRUNCATE\s+(TABLE\s+)?\w)', raw):
        return 'DROP/TRUNCATE в запросе к СУБД — безвозвратное удаление данных'
    return None


# Читает или копирует содержимое файла (затем копию можно прочесть в обход Read(**/.env)); утилиты поиска — PATTERN_TOOLS
READERS = (r'(^|[\s;&|({])(cat|type|less|more|head|tail|tac|rev|bat|nl|base64|xxd|od|hexdump|strings|iconv|sort|uniq|cut|'
           r'certutil|Get-Content|gc|gci|Copy-Item|cpi|cp|copy|xcopy|robocopy|scp|'
           # аудит 30.10.2026: список читателей был мал — diff, paste, tr, jq, source и архиваторы читали .env мимо барьера
           r'diff|cmp|comm|paste|tr|jq|yq|source|envsubst|xargs|openssl|gpg|tar|zip|7z|rsync|split|fold|fmt|column|'
           r'Import-Csv|ConvertFrom-\w+|Get-Item|gi|Select-Xml|Compress-Archive|Send-MailMessage|'
           r'curl|wget|Invoke-WebRequest|iwr|Invoke-RestMethod|irm)\b|(^|[;&|({]\s*)\.\s+\S|'
           r'\[(System\.)?IO\.File\]::(Read|Copy|Open)|'
           # интерпретатор программой, а не расширением `.py`; код или модуль: -c, -e, -p, -m и склейки -ne, -pe, -Command, --print
           r'(?<![.\w-])(python3?|py|node|ruby|perl|php|pwsh|powershell)(\.exe)?\b.*\s(?:-[a-z]{0,2}[cemp]|-Command|--print|--eval)\b')
SECRET_FILE = (r'(\.env\b(?!\.(?:example|sample|template)\b)|\.pem\b|\.key\b|\bid_rsa\b|\bid_ed25519\b|[\\/]secrets[\\/]|'
               r'\.pgpass\b|\bpgpass\.conf\b|[\w.-]+_(ed25519|rsa|ecdsa|dsa)\b(?!\.pub\b)|'
               r'(?:^|[\s"\'\\/])\.claude[\\/]settings\.local\.json\b)')   # env проекта — штатное место секретов
# Файлы доверия барьеров (путь со слэшами /, нижний регистр): по ним решается, кто согласился, какая база тестовая, какие серверы
# свои и живы ли хуки. Write/Edit судит guard-skills по результату правки; из оболочки результата не видно, поэтому запись — отказ.
# Журнал сессии и запись согласий — свидетельства согласия владельца (аудит 30.10.2026).
OWNER_FILES = (
    (r'(?:^|/)\.claude/projects/.*\.jsonl$|(?:^|/)consent\.json$',
     'запись в журнал сессии или logs/consent.json — это свидетельства «да» владельца для барьера помощников, агент их не правит '
     '(subagents-on-explicit-consent)'),
    (r'(?:^|/)\.v8-project\.json$',
     'запись в реестр баз .v8-project.json из оболочки — реестр решает, какая база тестовая и чьи данные можно читать: базу и '
     'отметку pd вносит владелец, обычная правка — через Edit, там судится результат (secrets-and-production-database)'),
    (r'(?:^|/)\.claude/settings(?:\.local)?\.json$',
     'запись в настройки Claude Code из оболочки — так снимаются запреты, хуки и подключение плагина; обычная правка — через Edit, '
     'там судится результат'),
    (r'(?:^|(?<!plugin)/)\.mcp\.json$', 'запись в .mcp.json из оболочки — список серверов проекта расширяет только владелец '
     '(use-own-mcp-servers-only)'),   # plugin/.mcp.json — исходник плагина в мастере, не список проекта
    (r'(?:^|/)ssh-mcp/config\.toml$', 'запись в настройки ssh-mcp — ими снимаются ворота подтверждения команд на сервере, правит только владелец'),
    (r'(?:^|/)\.git/(?:hooks(?:/|$)|config$)|(?:^|/)tools/git/hooks(?:/|$)',
     'запись в файлы хуков git или .git/config — обход проверок перед коммитом (work-journals-and-commits п.8)'),
    (r'(?:^|/)1c-toolkit-bases\.json$', 'запись в файл состояния тулкита — он говорит барьеру ПДн, на какой базе поднят тулкит; '
     'его пишет только /ones-core:toolkit (personal-data-masked-from-1c)'),
    (r'(?:^|/)\.claude/plugins/(?:cache|marketplaces)/|(?:^|/)\$\{?claude_plugin_root\}?(?:/|$)',
     'запись в установленный плагин — в нём хуки, правка сняла бы защиту сразу; плагин меняется только обновлением: claude plugin update'),
    # с 20.11.2026: из оболочки не создаётся, не правится и не удаляется; новый файл — только через Write, его судит guard-skills
    (r'(?:^|/)\.bsl-language-server\.json$',
     'bug-diagnosis-loop Ф5: настройки BSL Language Server из оболочки не создаются, не правятся и не удаляются — отключённая '
     'диагностика прячет замечание, а не исправляет код; ложную диагностику объявляет владелец'),
)
# Запись кодом интерпретатора и .NET: первым делом — куда. Упоминание файла в тексте, который код пишет в другой файл, не запись
# (журнал работы с `.v8-project.json` в тексте — обычная правка). Аргумент: литерал или переменная с литералом в этом же коде.
CODE_ARG = r'(?:[rRbBuUfF]{0,2}"[^"\n]*"|[rRbBuUfF]{0,2}\'[^\'\n]*\'|[^\s,()"\']+)'
CODE_WRITES = tuple(x.replace('ARG', CODE_ARG) for x in (
    r'\bopen\s*\(\s*(ARG)\s*,[^)\n]*?["\'][rbt]*[wax+][rbt+]*["\']',
    r'\bPath\s*\(\s*(ARG)\s*\)\s*\.\s*(?:write_text|write_bytes|unlink|rename|replace)\b',
    r'\bPath\s*\(\s*(ARG)\s*\)\s*\.\s*open\s*\(\s*["\'][rbt]*[wax+]',
    r'(\b[A-Za-z_]\w*)\s*\.\s*(?:write_text|write_bytes|unlink|rename)\s*\(',
    r'\b(?:write|append)File(?:Sync)?\s*\(\s*(ARG)',
    r'\bfs\.(?:rm|unlink|rename|truncate)\w*\s*\(\s*(ARG)',
    r'\bfs\.copyFile\w*\s*\(\s*ARG\s*,\s*(ARG)',
    r'\[(?:System\.)?IO\.File\]::(?:Write|Append|Delete|Replace|Create|OpenWrite)\w*\s*\(\s*(ARG)',
    r'\[(?:System\.)?IO\.File\]::Copy\s*\(\s*ARG\s*,\s*(ARG)',
    r'\[(?:System\.)?IO\.File\]::Move\s*\(\s*(ARG)\s*,\s*(ARG)',
    r'\bos\.(?:remove|unlink|truncate)\s*\(\s*(ARG)',
    r'\bos\.(?:rename|replace)\s*\(\s*(ARG)\s*,\s*(ARG)',
    r'\bshutil\.copy\w*\s*\(\s*ARG\s*,\s*(ARG)',
    r'\bshutil\.move\s*\(\s*(ARG)\s*,\s*(ARG)',
    r'\bfile_put_contents\s*\(\s*(ARG)',
    r'\bFile\.write\s*\(\s*(ARG)'))
# Программы, у которых меняются все файлы-аргументы, и программы, у которых — последний (приёмник)
WRITE_ALL = {'rm', 'rmdir', 'unlink', 'shred', 'truncate', 'del', 'erase', 'rd', 'remove-item', 'ri', 'chmod', 'chown', 'chattr',
             'attrib', 'icacls', 'mv', 'move', 'move-item', 'mi', 'rename-item', 'rni', 'ren', 'rename', 'tee', 'set-content', 'sc',
             'add-content', 'ac', 'out-file', 'clear-content', 'clc', 'new-item', 'ni'}
WRITE_LAST = {'cp', 'copy', 'copy-item', 'cpi', 'xcopy', 'rsync', 'ln', 'install'}
SCRIPT_RUNNERS = {'python', 'python3', 'py', 'node', 'ruby', 'perl', 'php', 'bash', 'sh', 'pwsh', 'powershell'}
LEAD_WORDS = r'^(?:(?:if|then|elif|else|do|while|until|time|nohup|sudo|exec|command|builtin|!|\{|\()\s+)+'
ASSIGN_HEAD = r'^\$[\w:]+\s*\+?=\s*|^[A-Za-z_]\w*=\$\('   # `$ok = …`, `x=$(…`
# Файл на вход перенаправлением: `tr a a < .env`, `$(<.env)`, `while read l; do …; done < .env` (<<< и <( — не файл)
REDIRECT_IN = r'(?<![<\w])<(?![<(&])\s*["\']?([^\s"\'<>|;&)]+)'
# Утилиты, у которых первый позиционный аргумент — шаблон или программа, а не файл: секрет судится по файлам-аргументам.
# Ключи: с значением, задающие шаблон, задающие файл; короткие — буквами, длинные — словами.
PATTERN_TOOLS = {
    'grep': ('efmABCdD', 'ef', 'f', ('--regexp', '--file', '--max-count', '--after-context', '--before-context', '--context',
                                     '--include', '--exclude', '--exclude-dir', '--label', '--devices', '--directories'),
             ('--regexp', '--file'), ('--file',)),
    'rg': ('efgtTmABCMjEr', 'ef', 'f', ('--regexp', '--file', '--glob', '--iglob', '--type', '--type-not', '--max-count',
                                        '--after-context', '--before-context', '--context', '--max-columns', '--threads',
                                        '--encoding', '--replace', '--max-depth', '--sort', '--sortr'),
           ('--regexp', '--file'), ('--file',)),
    'sed': ('efl', 'ef', 'f', ('--expression', '--file', '--line-length'), ('--expression', '--file'), ('--file',)),
    'awk': ('Fvf', 'f', 'f', ('--field-separator', '--assign', '--file'), ('--file',), ('--file',)),
}
for _alias, _base in (('egrep', 'grep'), ('fgrep', 'grep'), ('gawk', 'awk'), ('mawk', 'awk'), ('nawk', 'awk')):
    PATTERN_TOOLS[_alias] = PATTERN_TOOLS[_base]


def pattern_tool_files(norm):
    """Файлы-аргументы утилиты поиска и правки текста (grep, rg, sed, awk, findstr, Select-String) без шаблона и программы;
    None — такой утилиты в сегменте нет. `grep -rn "\\.env" docs/` читает docs/, а не .env."""
    toks = [t[1:-1] if len(t) > 1 and t[0] == t[-1] and t[0] in '"\'' else t
            for t in re.findall(r'"[^"]*"|\'[^\']*\'|\S+', strip_env_prefix(norm))]
    for i, t in enumerate(toks):
        name = re.split(r'[\\/]', t)[-1].lower()
        name = name[:-4] if name.endswith('.exe') else name
        if name in PATTERN_TOOLS or name in ('findstr', 'select-string', 'sls'):
            break
    else:
        return None
    rest, files, positional, given = toks[i + 1:], [], [], False
    j = 0
    while j < len(rest):
        t, tl = rest[j], rest[j].lower()
        if name in ('select-string', 'sls') and t.startswith('-'):
            key = tl.rstrip(':')
            if key in ('-path', '-literalpath', '-lp', '-pspath') and j + 1 < len(rest):
                files.append(rest[j + 1])
            given = given or key == '-pattern'
            j += 2 if key in ('-path', '-literalpath', '-lp', '-pspath', '-pattern', '-encoding', '-context', '-include',
                              '-exclude', '-culture', '-inputobject') else 1
            continue
        if name == 'findstr' and t.startswith('/'):
            given = given or tl.startswith(('/c:', '/g:'))
            if tl.startswith(('/g:', '/f:')):
                files.append(t[3:])
            j += 1
            continue
        if name in PATTERN_TOOLS and t == '--':
            positional += rest[j + 1:]
            break
        if name in PATTERN_TOOLS and t.startswith('--'):
            vshort, pshort, fshort, vlong, plong, flong = PATTERN_TOOLS[name]
            key, eq, val = t.partition('=')
            if key in vlong and not eq:
                val = rest[j + 1] if j + 1 < len(rest) else ''
                j += 1
            given = given or key in plong
            if key in flong:
                files.append(val)
            j += 1
            continue
        if name in PATTERN_TOOLS and len(t) > 1 and t.startswith('-') and not re.fullmatch(r'-\d+', t):
            vshort, pshort, fshort = PATTERN_TOOLS[name][:3]
            for k, ch in enumerate(t[1:], 1):
                if ch in vshort:
                    val = t[k + 1:]
                    if not val:
                        val = rest[j + 1] if j + 1 < len(rest) else ''
                        j += 1
                    given = given or ch in pshort
                    if ch in fshort:
                        files.append(val)
                    break
            j += 1
            continue
        positional.append(t)
        j += 1
    return files + (positional if given else positional[1:])


def redirect_targets(text):
    """Файлы после > и >> вне кавычек; `2>&1` — не файл."""
    out, q, i, n = [], '', 0, len(text)
    while i < n:
        c = text[i]
        if q:
            q = '' if c == q else q
        elif c in '"\'':
            q = c
        elif c == '>':
            j = i + 2 if text.startswith('>>', i) else i + 1
            if not text.startswith('&', j):
                mm = re.match(r'\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s;&|<>]+))', text[j:])
                if mm:
                    out.append(next(g for g in mm.groups() if g is not None))
            i = j - 1
        i += 1
    return out


def program_args(norm):
    """Программа сегмента (имя без пути, .exe и открывающей скобки, нижний регистр) и её слова — без префиксов окружения,
    присваивания результата (`$ok = Test-Path x`, `x=$(ls y)`), ключевых слов оболочки и запуска (&, call, start, cmd /c).
    Выражение PowerShell (`$x -replace …`, `[regex]::Replace(…)`, `"текст" + …`, присваивание литерала) — не запуск: программы нет."""
    s = norm.strip()
    head = re.match(ASSIGN_HEAD, s)
    if head:
        s = s[head.end():]
        if s[:1] in ('"', "'", '@', '$', '(', '['):
            return '', []
    s = re.sub(LEAD_WORDS, '', strip_env_prefix(s), flags=I)
    toks = tokens_of(re.sub(LAUNCH_LEAD, '', s, count=1, flags=I))
    if not toks:
        return '', []
    first = toks[0].lstrip('(')
    if first[:1] == '$' or (first[:1] == '[' and first not in ('[', '[[')) or (re.search(r'\s', first) and not re.search(r'[\\/]', first)):
        return '', []
    name = re.split(r'[\\/]', first)[-1].lower()
    return (name[:-4] if name.endswith('.exe') else name), toks[1:]


# Имя файла-секрета целиком (по SECRET_FILE ловится и часть слова — там, где программа точно читает файл). Образцы — не секрет.
SECRET_BASE = re.compile(r'[\w.-]*\.env(?:\.[\w.-]+)?|[\w.-]*\.(?:pem|key)|id_rsa|id_ed25519|\.pgpass|pgpass\.conf|'
                         r'[\w.-]+_(?:ed25519|rsa|ecdsa|dsa)|settings\.local\.json', I)
SECRET_SAMPLE = re.compile(r'\.env\.(?:example|sample|template|md)$', I)
# Что может попасть под маску: `.en?`, `.e*`, `*.key`, `id_*`
MASK_NAMES = ('.env', '.env.local', 'prod.env', '.pgpass', 'id_rsa', 'id_ed25519', 'server.key', 'server.pem', 'agent_ed25519', 'agent_rsa')
# Программы, которым имя секрета в аргументах не открывает содержимое: показывают файл, а не его текст, или пишут само имя.
SECRET_SAFE = {'ls', 'dir', 'vdir', 'stat', 'wc', 'du', 'file', 'test', '[', '[[', 'test-path', 'resolve-path', 'split-path', 'join-path',
               'get-childitem', 'touch', 'chmod', 'chown', 'icacls', 'attrib', 'echo', 'printf', 'write-host', 'write-output', 'mkdir',
               'rm', 'unlink', 'rmdir', 'rd', 'del', 'erase', 'remove-item', 'ri', 'cd', 'pushd', 'set-location', 'sl', 'which', 'where',
               'find', 'fd', 'ssh', 'sftp', 'ssh-keygen', 'ssh-add', 'export', 'set', 'local', 'declare', 'for', 'foreach',
               'foreach-object', 'where-object', 'select-object', 'sort-object', 'group-object', 'measure-object', 'format-table',
               'format-list', 'out-string', 'out-null', '%', '?'}
# git показывает содержимое и у diff/show/grep/blame; эти подкоманды — только имена и состояние (log — без -p)
SECRET_SAFE_GIT = {'add', 'rm', 'status', 'check-ignore', 'ls-files', 'commit', 'stage', 'restore', 'reset', 'log'}


def secret_token(t):
    """Слово команды — путь к секрету: имя файла целиком или маска, под которую он попадает, папка ключей и домашние учётные
    данные. Текст с пробелом (`"про .env файл"`), адрес и свойство объекта ($cfg.key) — не путь."""
    t = t.strip().rstrip(')}];,')
    if '://' in t:
        return False
    whole = t
    t = re.sub(r'^(?:--?[\w-]+[=:]|if=|@)', '', t)
    if m(HOME_CREDS, t) or m(r'(?:^|[\\/])\.claude[\\/]settings\.local\.json$', t):
        return True
    base = re.split(r'[\\/:]', t)[-1]
    if not base or re.search(r'\s', base) or (re.search(r'\s', t) and not re.match(r'[A-Za-z]:|[\\/~.$%]', t)):
        return False   # текст с пробелом — не путь, путь с пробелом начинается как путь
    if '*' in base or '?' in base:
        # маска — слово без пробела с явным началом или концом имени секрета; `*`, `.*`, `\\s*` — всё подряд или регулярное выражение
        if re.search(r'\s', whole) or not re.fullmatch(r'[\w.*?-]+', base) or not base.strip('*?.') or \
                not (base.startswith(('.', 'id_')) or re.search(r'(?:\.(?:key|pem|env)|_(?:rsa|ed25519|ecdsa|dsa))$', base, I)):
            return False
        return any(fnmatch.fnmatchcase(x, base.lower()) for x in MASK_NAMES)
    if base.lower() == 'settings.local.json':
        return False   # только в .claude: выше
    return bool(SECRET_BASE.fullmatch(base)) and not SECRET_SAMPLE.search(base)


def secret_path(p):
    """Путь в инструменте Read или Grep — секрет: имя, папка ключей, домашние учётные данные, папка secrets."""
    return secret_token(p) or m(r'[\\/]secrets[\\/]', p)


def secret_args(norm):
    """Слова, которые программа сегмента может прочитать как файл; пусто — программа из безобидных (шапка: «любой читающей»)."""
    prog, args = program_args(norm)
    if prog in SECRET_SAFE and not (prog == 'find' and m(r'\s-(?:exec|execdir|ok|okdir)\b', norm)):
        return []
    if prog == 'git':
        sub = next((a for a in args if not a.startswith('-')), '')
        if sub in SECRET_SAFE_GIT and not (sub == 'log' and m(r'(?:^|\s)(?:-p|-u|--patch)\b', norm)):
            return []
    drop = redirect_targets(norm)
    return [a for a in args if a not in drop]


def secret_name(name):
    """Имя переменной окружения похоже на секрет; PWD и OLDPWD — каталог, а не пароль."""
    return m(r'TOKEN|PASSW(?:OR)?D|SECRET|API_?KEY|PRIVATE_?KEY|CREDENTIAL|_PWD(?:_|$)', name)


def env_read(stripped, norm):
    """Печать окружения целиком или переменной с секретом (блок env настроек проекта доходит до процессов оболочки).
    Передать секрет программе можно: `curl -H "…$TOKEN"` его не печатает."""
    s = stripped.strip()
    if re.fullmatch(r'env|printenv|set|export(?:\s+-p)?|(?:declare|typeset)\s+-[px]', s):
        return True
    mm = re.match(r'printenv\s+(\S+)', s)
    if mm and secret_name(mm.group(1)):
        return True
    mm = re.match(r'(?:Get-ChildItem|gci|ls|dir|Get-Item|gi|Get-Content|gc|cat|type)\b[^|]*?(?:\s|["\'])Env:\\?([\w*?]*)', norm, I)
    if mm and (not re.fullmatch(r'\w+', mm.group(1)) or secret_name(mm.group(1))):
        return True
    if m(r'\[(?:System\.)?Environment\]::GetEnvironmentVariables\b', s):
        return True
    mm = re.search(r'GetEnvironmentVariable\s*\(\s*["\'](\w+)', norm, I)
    if mm and secret_name(mm.group(1)):
        return True
    mm = re.fullmatch(r'["\']?\$env:(\w+)["\']?', norm.strip(), I)
    if mm and secret_name(mm.group(1)):
        return True
    if program_args(norm)[0] in ('echo', 'printf', 'write-host', 'write-output', 'write-information', 'print'):
        text = re.sub(r"'[^']*'", ' ', norm)
        return any(secret_name(a or b) for a, b in re.findall(r'\$(?:env:)?\{?([A-Za-z_]\w*)\}?|%([A-Za-z_]\w*)%', text))
    return False


def secret_read(stripped, norm):
    """Причина отказа для чтения или копирования секрета или None: stripped — сегмент без литералов, norm — с ними.
    Утилиты из READERS судятся по всему тексту, любая другая программа — в secret_word_read. Первый аргумент grep и sed — шаблон,
    а не файл."""
    texts = [' '.join(re.findall(REDIRECT_IN, norm))]
    files = pattern_tool_files(norm)
    if files is not None:
        texts.append(' '.join(files))
    if m(READERS, stripped):
        texts.append(norm)
    for text in texts:
        if m(SECRET_FILE, text):
            return 'чтение или копирование секрета (.env/*.key/*.pem/.pgpass/secrets) — секрет попадёт в контекст/журнал'
        if m(HOME_CREDS, text):
            return ('чтение учётных данных из домашнего каталога (ssh-ключи, токены gh/git/npm/облаков, .credentials.json) — '
                    'секрет попадёт в контекст')
    return None


def secret_word_read(norm):
    """Слова команды и печать окружения — только то, что исполнит сама оболочка: строки кода, поданного интерпретатору, — данные
    (`Rows.Key` в тексте запроса — не файл)."""
    files = pattern_tool_files(re.sub(ASSIGN_HEAD, '', norm.strip()))
    if any(secret_token(t) for t in (files if files is not None else secret_args(norm))):
        return 'чтение или копирование секрета (.env/*.key/*.pem/.pgpass/ключи, в том числе по маске) — секрет попадёт в контекст/журнал'
    if env_read(strip_literals(unquote_atoms(norm)), norm):
        return ('печать переменных окружения с секретами (env, printenv, Get-ChildItem Env:, echo $…TOKEN) — значения попадут в контекст '
                'и журнал; имена покажет compgen -e, обычную переменную — printenv ИМЯ')
    return None


def owner_reason(path):
    p = path.replace('\\', '/').lower().rstrip('/')
    return next((why for rx, why in OWNER_FILES if re.search(rx, p)), None)


def owner_mask_reason(mask):
    """Маска пути, под которую попадает файл доверия: `logs/cons*.json`. Начало имени должно быть явным: `*.json` — всё подряд."""
    head, _, base = mask.replace('\\', '/').lower().rpartition('/')
    if not re.search(r'[*?\[]', base) or not re.match(r'[\w.-]{2,}', base):
        return None
    for name in ('consent.json', '.v8-project.json', 'settings.json', 'settings.local.json', '.mcp.json', 'config.toml',
                 '.bsl-language-server.json'):
        if fnmatch.fnmatchcase(name, base) and owner_reason((head + '/' if head else '') + name):
            return owner_reason((head + '/' if head else '') + name)
    return None


def code_value(arg, code):
    """Значение аргумента вызова: литерал или литерал, присвоенный этой переменной в том же коде (`p = '…'`, `p = Path('…')`)."""
    arg = arg.strip()
    mm = re.match(r'[rRbBuUfF]{0,2}(["\'])(.*)\1$', arg, re.S)
    if mm:
        return mm.group(2)
    mm = re.search(r'(?:^|[^\w.])\$?' + re.escape(arg.lstrip('$')) + r'\s*=\s*(?:(?:pathlib\.)?Path\s*\(\s*)?[rRbBuUfF]{0,2}(?:"([^"\n]*)"|\'([^\'\n]*)\')', code)
    return (mm.group(1) or mm.group(2)) if mm else arg


def owner_code_reason(code):
    """Код (python -c, node -e, [IO.File]::…, тело heredoc) пишет в файл доверия: цель записи — литерал или переменная с литералом."""
    for rx in CODE_WRITES:
        for mm in re.finditer(rx, code):
            for arg in mm.groups():
                why = owner_reason(code_value(arg, code))
                if why:
                    return why
    return None


def write_targets(norm, prog, args):
    """Файлы, которые меняет сегмент: цели перенаправления, файлы-аргументы программ удаления, переноса и записи, приёмник
    копирования, файлы sed -i и dd of=. Источник копирования — чтение: `cp реестр копия` проходит."""
    out = redirect_targets(norm)
    words = [a for a in args if not a.startswith('-')]
    if prog in WRITE_ALL:
        out += words
    elif prog in WRITE_LAST:
        out += words[-1:] + [args[i + 1] for i, a in enumerate(args[:-1]) if a.lower() in ('-destination', '-dest')]
    elif prog == 'dd':
        out += [a[3:] for a in args if a.lower().startswith('of=')]
    elif prog in ('sed', 'perl') and m(r'(?:^|\s)(?:-[A-Za-z]*i\b|--in-place)', norm, 0):
        out += (pattern_tool_files(norm) or words) if prog == 'sed' else words
    return out


def owner_file_write(norm):
    """Причина отказа: команда меняет файл доверия барьеров (OWNER_FILES) или None; чтение и копия из него проходят."""
    prog, args = program_args(norm)
    for t in write_targets(norm, prog, args):
        why = owner_reason(t) or owner_mask_reason(t)
        if why and not in_temp(t):   # копия в песочнице временной папки барьеры не обманет
            return why
    if prog in TEXT_PROGRAMS:
        return None
    if m(r'\bclaude(?:\.exe)?\s+mcp\s+(?:add|add-json|add-from-claude-desktop|remove)\b', norm):
        return 'claude mcp add — список серверов проекта меняет только владелец (use-own-mcp-servers-only)'
    if prog in SCRIPT_RUNNERS and any(re.search(r'(?:^|/)consent\.json$', a.replace('\\', '/').lower()) for a in args):
        return OWNER_FILES[0][1]
    return owner_code_reason(norm)


# Слой экрана из оболочки (no-screen-control): координаты, клавиатура, снимок. Имя — вызов только у программы, не печатающей текст.
SCREEN_OS = (r'\b(?:pyautogui|pynput|SendKeys|SendInput|mouse_event|keybd_event|SetCursorPos|CopyFromScreen|nircmd|nircmdc|xdotool|'
             r'AutoHotkey)\b')


def screen_layer(norm):
    return m(SCREEN_OS, norm) and program_of(norm) not in TEXT_PROGRAMS


# Звенья конвейера: отбор файлов и их удаление или чтение стоят в разных звеньях, порознь они безобидны
PIPE_LIST_RECURSE = r'(?:^|[\s(])(?:Get-ChildItem|gci|ls|dir)\b.*(?:^|\s)-r(?:e(?:c(?:u(?:r(?:se?)?)?)?)?)?(?=\s|$)'
PIPE_DELETE = (DEL_WORD % r'Remove-Item|ri|del|erase|rm') + r'|\.Delete\s*\('
PIPE_READ = r'\bxargs\b(?!.*\b(?:ls|stat|wc|file|rm|echo|printf)\b)|\b(?:Get-Content|gc|Copy-Item|cpi)\b'


def pipe_verdict(statement):
    """Причина отказа для конвейера, опасного только целиком, или None."""
    stages = [re.sub(r'\s+', ' ', x).strip() for x in split_outside_quotes(statement)]
    bare = [strip_literals(unquote_atoms(x)) for x in stages]
    for i in range(1, len(stages)):
        if m(PIPE_DELETE, bare[i]) and any(m(PIPE_LIST_RECURSE, b) for b in bare[:i]):
            return 'Remove-Item -Recurse через конвейер (Get-ChildItem -Recurse | Remove-Item) — рекурсивное удаление'
        if m(r'\bxargs\b.*\b(?:rm|unlink|shred)\b', bare[i]) and any(m(r'(?:^|\s)find\s', b) for b in bare[:i]):
            return 'find … -delete через конвейер (find | xargs rm) — массовое удаление файлов'
        if m(PIPE_READ, bare[i]) and any(secret_token(t) for x in stages[:i] for t in program_args(x)[1]):
            return 'чтение или копирование секрета через конвейер (ls .env | xargs cat) — секрет попадёт в контекст/журнал'
    return None
# .ssh — и папка целиком (архив, копия), и часть пути, собранного из кусков: joinpath('.ssh', '<ключ>') (волна 2 п.2.19)
HOME_CREDS = (r'[\\/]\.ssh(?:[\\/]|(?=[\s\'"`;|)]|$))|[\'"]\.ssh[\'"]|GitHub CLI[\\/]hosts\.yml|[\\/]\.config[\\/]gh[\\/]|\.credentials\.json|\.git-credentials|\.npmrc\b|'
              r'\.pypirc\b|[\\/]\.aws[\\/]|[\\/]\.azure[\\/]|[\\/]\.kube[\\/]|[\\/]\.gnupg[\\/]|'
              r'ones-core[\\/]ssh[\\/](?!(?:[^\s\'"\\/]*\.pub|known_hosts|config)(?:[\s\'"]|$))')


# Удалённая команда в кавычках: ssh/ssh.exe, tmux send-keys, помощник vm-shell — текст внутри кавычек исполнится на сервере
REMOTE_CARRIER = r'(^|[\s/\\])ssh(\.exe)?\s|\btmux\s+send-keys\b|\bvm-shell(\.py)?\b'


def remote_quoted(norm):
    """Причина отказа для удалённой команды внутри кавычек или None (кавычки вне удалённой команды не трогаются)."""
    if not m(REMOTE_CARRIER, norm):
        return None
    for lit in (a or b for a, b in re.findall(r'"([^"]*)"|\'([^\']*)\'', norm)):
        for part in re.split(r'\r?\n|&&|\|\||;|\|', lit):
            p = re.sub(r'\s+', ' ', part).strip()
            if not p:
                continue
            st = strip_literals(unquote_atoms(p))
            why = destructive(st, on_server=True, raw=p) or sql_drop(p)
            if not why and (secret_read(st, p) or secret_word_read(p)):
                why = 'чтение или копирование секрета на сервере (.env/*.key/*.pem/.pgpass/~/.ssh/токены)'
            if why:
                return why
    return None


def literals(s):
    """Содержимое литералов в кавычках верхнего уровня (вложенные кавычки остаются внутри своего литерала)."""
    return [a or b for a, b in re.findall(r'"([^"]*)"|\'([^\']*)\'', s)]


# Обращение к серверу тулкита мимо MCP (замер 30.10.2026): барьер ПДн стоит на инструментах, а не на порту. Штатные /health и /api — не /mcp.
TOOLKIT_URL = r'(?:127\.0\.0\.1|localhost|\[::1\]):(\d+)/mcp\b'
NET_CLIENT = r'\b(curl|wget|Invoke-WebRequest|iwr|Invoke-RestMethod|irm)\b'


def toolkit_bypass(cmd, project_dir, fed=()):
    """Порт тулкита, к которому команда идёт сетевым клиентом, кодом (-c/-e) или телом heredoc, поданным интерпретатору
    (python - <<E, node <<E; с 20.11.2026), или None. Скрипт в файле не читается, адрес, собранный из частей, не виден."""
    found = set(re.findall(TOOLKIT_URL, cmd, I))
    bare = [strip_literals(unquote_atoms(re.sub(r'\s+', ' ', x).strip())) for x in split_outside_quotes(cmd)]
    if not found or not (any(m(NET_CLIENT, x) or m(CODE_CARRIER, x) for x in bare) or
                         any(k == 'code' and re.search(TOOLKIT_URL, b, I) for k, _, b, _ in fed)):
        return None
    ports = {os.environ.get('ONEC_TOOLKIT_PORT') or '6003'}
    try:
        with open(os.path.join(project_dir, '.mcp.json'), encoding='utf-8-sig') as f:
            servers = json.load(f).get('mcpServers') or {}
        ports |= {x for k, v in servers.items() if 'toolkit' in k.lower() for x in re.findall(r':(\d+)/', str(v.get('url') or ''))}
    except (OSError, ValueError, AttributeError):
        pass
    return next(iter(sorted(found & ports)), None)


def sql_read(p):
    """Таблица данных, которую читает запрос клиента СУБД, или None: системные каталоги и голый счётчик — диагностика (ПДн п.6)."""
    text = re.sub(r'\bSELECT\s+count\s*\(\s*\*\s*\)\s+FROM\s+\S+', ' ', p, flags=I)
    tables = re.findall(r'\b(?:FROM|JOIN)\s+(?:ONLY\s+)?"?([\w.$]+)', text, I) if m(r'\bSELECT\b', text) else []
    tables += re.findall(r'(?:-c\s*["\']?|;\s*)TABLE\s+"?([\w.$]+)', text, I) + re.findall(r'\bCOPY\s+"?([\w.$]+)[^;]*?\bTO\b', text, I)
    return next((t for t in tables if not m(r'^(pg_|information_schema|sys\b|master\.|msdb\.|mysql\.|performance_schema)', t)), None)


# eval — встроенная команда оболочки: судится только в позиции команды (начало сегмента, после ; & | ( { ! $( `, ключевого
# слова и префикса sudo/exec/command); слово eval аргументом другой программы (`claude plugin eval …`) — не вычисление строки
EVAL_AT_CMD = (r'(?:^|[\n;&|({!`]|\$\(|\b(?:then|do|else|elif|if|while|until)\s)\s*(?:[A-Za-z_]\w*=\S*\s+)*'
               r'(?:(?:sudo|exec(?:\s+-a\s+\S+)?|command|builtin|nohup|time|nice)(?:\s+-\S+)*\s+)*eval(?:\s|$)')
# Текст в кавычках исполнится как команда: вложенная оболочка или вычисление строки
SHELL_CARRIER = (r'(?:^|[\s/\\(])(?:bash|sh|zsh|dash|ksh)(?:\.exe)?\s+(?:-\S+\s+)*-[A-Za-z]*c\b|\bcmd(?:\.exe)?\s+/[ck]\b|'
                 r'\b(?:pwsh|powershell)(?:\.exe)?\b.*\s-(?:c|Command)\b|' + EVAL_AT_CMD + r'|\b(?:Invoke-Expression|iex)\b')
# Оболочка, которая читает команды со входа: звено после `|` (`… | bash`, `… | iex`) и here-string (`bash <<< '…'`)
SHELL_SINK = (r'^(?:\S*[\\/])?(?:bash|sh|zsh|dash|ksh|pwsh|powershell|cmd|iex|Invoke-Expression)(?:\.exe)?'
              r'(?:\s+(?:-\S+|/[ck]))*\s*$')
HERE_STRING = r'(?:^|[\s/\\(])(?:bash|sh|zsh|dash|ksh|pwsh|powershell)(?:\.exe)?\b[^<]*<<<'
# Код интерпретатора в кавычках: удаляет сам или запускает команды
CODE_CARRIER = r'(?:^|[\s/\\(&])(?:python3?|py|node|ruby|perl|php)(?:\.exe)?\s+(?:\S+\s+)*?-[A-Za-z]*[ce]\b'
CODE_REMOVE = (r'\brmtree\s*\(|\bos\.removedirs\b|\b(?:rmSync|rmdirSync|rm|rmdir)\s*\([^)]*recursive|\bFileUtils\.rm_r|'
               r'\bremove_tree\b|\bRemove-Item\b.*-Recurse')
CODE_RUNS = (r'\bos\.(?:system|popen|exec\w*|spawn\w*)\b|\bsubprocess\b|\bPopen\b|\bexec(?:File)?Sync\b|\bspawnSync\b|'
             r'\bchild_process\b|\bsystem\s*\(|`[^`]+`')


def inner_commands(text, depth=0, remote=False):
    """Команды, которые исполнятся ВНУТРИ другой: текст в кавычках вложенной оболочки (bash -c, cmd /c, pwsh -Command, eval,
    Invoke-Expression) и удалённой команды (ssh, tmux send-keys, vm-shell), команды из кода интерпретатора (os.system,
    subprocess, execSync). Элементы: ('cmd', команда, без литералов, на сервере) и ('code', код, '', на сервере) — код,
    который удаляет сам (shutil.rmtree, fs.rmSync с recursive). Глубина — до трёх вложений."""
    out = []
    if depth > 3:
        return out
    prev = ''
    for part in split_outside_quotes(text):
        p = re.sub(r'\s+', ' ', part).strip()
        st = strip_literals(unquote_atoms(p))
        if depth:
            out.append(('cmd', p, st, remote))
        rem = remote or m(REMOTE_CARRIER, st)
        if m(SHELL_CARRIER, st) or m(REMOTE_CARRIER, st) or m(HERE_STRING, st):
            for lit in literals(p):
                out += inner_commands(lit, depth + 1, rem)
        # текст предыдущего звена уходит в оболочку: `echo 'rm -rf x' | bash` (аудит 30.10.2026)
        if prev and re.match(SHELL_SINK, st, I):
            for lit in literals(prev):
                out += inner_commands(lit, depth + 1, rem)
        # подстановка команды исполняется и внутри двойных кавычек: `echo "$(git reset --hard)"`; одинарные — текст
        for mm in re.finditer(r'\$\(([^()]*)\)|`([^`]*)`', re.sub(r"'[^']*'", ' ', p)):
            out += inner_commands(mm.group(1) or mm.group(2) or '', depth + 1, rem)
        prev = p
        if m(CODE_CARRIER, st):
            for code in literals(p):
                if m(CODE_REMOVE, code):
                    out.append(('code', code, '', rem))
                if m(CODE_RUNS, code):
                    args = literals(code)
                    for lit in args + [' '.join(args)]:
                        out += inner_commands(lit, depth + 1, rem)
    return out


# Изменяющий SQL: клиент СУБД — программой (не в кавычках), запрос — в аргументах, файле или потоке
SQL_CLIENT = r'(?:^|[\s/\\(])(psql|pg_restore|sqlcmd|osql|mysql|mariadb|clickhouse-client)(?:\.exe)?(?=\s|$)'
SQL_WRITE = (r'\b(INSERT\s+INTO|UPDATE\s+[\w."\[\]]+\s+SET|DELETE\s+(FROM\s+)?[\w."\[\]#@]+|MERGE\s+(INTO\s+)?[\w."\[\]]+|'
             r'ALTER\s+\w+|CREATE\s+(OR\s+REPLACE\s+)?\w+|GRANT\s+\w+|REVOKE\s+\w+|COPY\s+\S+\s+FROM)\b')
# Обрыв сеансов, обслуживание и вызов процедур: строк не меняют, но рвут работу пользователей или берут блокировку (замер 30.10.2026).
# Судятся без ключей клиента: `psql --cluster 16/main -c "SELECT 1"` — не обслуживание.
SQL_MAINT = (r'\b(?:pg_terminate_backend|pg_cancel_backend|VACUUM|REINDEX\s+\w+|CLUSTER(?:\s+\w+)?|KILL\s+\d+|'
             r'EXEC(?:UTE)?\s+(?!(?:master\.\.)?(?:xp_read|sp_help|sp_who|sp_spaceused|sp_databases|sp_tables|sp_columns))[\w.\[\]]+)\b|'
             r'\bCALL\s+[\w."]+\s*\(|\bDO\s+(?:LANGUAGE\s+\w+\s+)?\$')
SQL_OPT = r'(?:^|\s)(?:--(?!command\b)[\w-]+(?:[= ]\S+)?|-[hpUdSPt]\s*\S+)'


def sql_hosts(p, mssql):
    """Адреса серверов СУБД из команды клиента."""
    if mssql:
        rxs = ((r'(?:^|\s)-S\s*["\']?([^\s"\']+)', 0), (r'(?<![\w-])(?:Server|Data Source)\s*=\s*([^;"\']+)', I))
    else:
        rxs = ((r'(?:^|\s)-h\s*["\']?([^\s"\']+)', 0), (r'--host[= ]\s*["\']?([^\s"\']+)', I),
               (r'(?<![\w-])host\s*=\s*["\']?([^\s"\';]+)', I),
               (r'\b(?:postgres(?:ql)?|mysql|mariadb)://(?:[^@/\s"\']*@)?([^:/\s"\'?]+)', I))
    return [db_host(x) for rx, fl in rxs for x in re.findall(rx, p, fl)]


def sql_databases(p, mssql):
    """Имена баз из команды клиента СУБД."""
    rxs = [(r'(?:^|\s)-d\s*["\']?([^\s"\']+)', 0), (r'--dbname[= ]\s*["\']?([^\s"\']+)', I), (r'(?<![\w-])dbname\s*=\s*["\']?([^\s"\';]+)', I)]
    rxs += [(r'(?<![\w-])(?:Database|Initial Catalog)\s*=\s*([^;"\']+)', I)] if mssql else \
        [(r'\bpostgres(?:ql)?://[^/\s"\']*/([^?\s"\']+)', I)]
    return [x.strip().lower() for rx, fl in rxs for x in re.findall(rx, p, fl)]


# Запрос уходит из базы, названной в команде: переключение внутри, трёхчастное имя, чужая база через расширение
SQL_LEAVES_BASE = (r'\\c(?:onnect)?\b|\bUSE\s+[\w\["]|\bdblink|\bpostgres_fdw\b|\bOPEN(?:ROWSET|QUERY|DATASOURCE)\b|'
                   r'\b(?:FROM|JOIN)\s+[\w\[\]"]+\.[\w\[\]"]*\.[\w\[\]"]+')


def sql_clean_base(p, st, dbs):
    """Запрос psql или sqlcmd читает базу реестра с отметкой pd: none: в команде один сервер и одна база, и обе совпали с
    dbServer (или server) и dbName её записи (решение владельца 30.10.2026, personal-data-masked-from-1c п.6). Без dbName в
    записи — нет: на одном сервере СУБД лежат и чистые базы, и базы с настоящими данными."""
    client = re.search(SQL_CLIENT, st, I).group(1).lower()
    mssql = client in ('sqlcmd', 'osql')
    hosts, names = sql_hosts(p, mssql), sql_databases(p, mssql)
    if not (mssql or client == 'psql') or len(set(hosts)) != 1 or len(set(names)) != 1 or m(SQL_LEAVES_BASE, p):
        return False
    return any(str(db.get('pd') or '').strip().lower() == 'none' and str(db.get('dbName') or '').strip().lower() == names[0] and
               db_host(str(db.get('dbServer') or db.get('db_server') or db.get('server') or '')) == hosts[0] for db in dbs)


def sql_write(p, st, servers):
    """Причина отказа для изменяющего запроса к СУБД на сервере не из реестра (или без адреса сервера) или None."""
    mm = re.search(SQL_CLIENT, st, I)
    if not mm:
        return None
    client = mm.group(1).lower()
    mssql = client in ('sqlcmd', 'osql')
    stream = (client == 'pg_restore' or m(r'(?<!<)<(?![<(])', st) or m(r'\\ir?\s|\bsource\s', p) or
              m(r'(?:^|\s)(?:-i|--input-file)(?:\s|=|$)' if mssql else r'(?:^|\s)(?:-f|--file)(?:\s|=|$)', st, 0))
    if not (stream or m(SQL_WRITE, p) or m(SQL_MAINT, re.sub(SQL_OPT, ' ', p))):
        return None
    hosts = sql_hosts(p, mssql)
    if not hosts:
        return ('изменяющий запрос к СУБД (%s) без адреса сервера (-h/-S): сервер не сверить с .v8-project.json — '
                'незарегистрированный считается боевым' % client)
    alien = [h for h in hosts if h not in servers]
    if alien:
        return ("изменяющий запрос к СУБД (%s) на сервере '%s', которого нет в .v8-project.json — незарегистрированный сервер "
                "считается боевым (secrets-and-production-database)" % (client, ', '.join(alien)))
    return None


class RegistryBroken(Exception):
    """Реестр .v8-project.json есть, но не читается: барьер не может сверить базу — это отказ, а не пропуск."""


def registry_dbs(project_dir):
    """Записи databases[] из .v8-project.json проекта (пусто, если реестра нет); битый реестр — RegistryBroken."""
    proj_file = os.path.join(project_dir, '.v8-project.json')
    if not os.path.isfile(proj_file):
        return []
    try:
        with open(proj_file, encoding='utf-8-sig') as f:
            reg = json.load(f)
    except (OSError, ValueError) as e:
        raise RegistryBroken('%s: %s' % (proj_file, e))
    dbs = (reg.get('databases') if isinstance(reg, dict) else None) or []
    return [dbs] if isinstance(dbs, dict) else [x for x in dbs if isinstance(x, dict)] if isinstance(dbs, list) else []


def registry_or_deny(project_dir, cmd):
    try:
        return registry_dbs(project_dir)
    except RegistryBroken as e:
        emit_deny('Реестр баз не читается (%s): барьер не может сверить, тестовая ли база, — запись в базу 1С и изменяющий SQL '
                  'отклоняются, пока реестр не починен (secrets-and-production-database).\nКоманда: %s' % (e, cmd[:300]))


def registry_write(stripped, norm):
    if m(r'(^|[\s;&|(])reg(\.exe)?\s+(add|delete|import|restore|load|unload|copy)\b', stripped) or \
            m(r'\bregedit(\.exe)?\b.*\s/s\b', stripped):
        return True
    return m(r'\b(Set|New|Remove|Rename|Clear)-ItemProperty\b|\b(New|Remove|Move|Rename|Set)-Item\b|\b(sp|ri|ni|mi|rni)\b', stripped) and \
        m(r'\b(HKLM|HKCU|HKCR|HKU|HKCC):|Registry::', norm)


PS_VALUE_OPTS = {'-executionpolicy', '-ep', '-ex', '-windowstyle', '-w', '-configurationname', '-workingdirectory', '-wd',
                 '-outputformat', '-of', '-inputformat', '-if', '-version', '-v', '-settingsfile', '-psconsolefile'}
LAUNCHER = (r'^(?:\S*[\\/])?(?:cmd(?:\.exe)?\s+/{1,2}[ck]|nohup|npx(?:\.cmd)?(?:\s+-\S+)*|timeout\s+(?:-\S+\s+)*\d+[smhd]?)\s+(?P<rest>.+)$')


def uv_target(rest):
    """Что запускает `uv run <rest>`: скрипт или интерпретатор после ключей; своя программа остаётся как есть. Ключей со
    значением у uv run больше тридцати, поэтому слово сразу после ключа считается его значением, а не программой."""
    toks = re.findall(r'"[^"]*"|\'[^\']*\'|\S+', rest)
    for i, tok in enumerate(toks):
        bare = tok.strip('"\'')
        if bare.startswith('-'):
            continue
        if re.search(r'\.(?:py|ps1)$', bare, I):
            return 'python ' + ' '.join(toks[i:])
        if re.fullmatch(r'(?:\S*[\\/])?(?:python3?|py|pwsh|powershell)(?:\.exe)?', bare, I):
            return ' '.join(toks[i:])
        if i == 0 or not toks[i - 1].startswith('-'):
            break
    return rest


def strip_launcher(s):
    """Команда под запускалкой: `cmd /c x`, `uv run x`, `nohup x`, `timeout 600 x`, `npx x` — это запуск x (замер 30.10.2026:
    без кавычек такой запуск проходил мимо проверок и запрета ⛔-скриптов)."""
    for _ in range(3):
        s = s.strip()
        mm = re.match(LAUNCHER, s, I | re.S)
        uv = re.match(r'^(?:\S*[\\/])?uv(?:\.exe)?\s+run\s+(.+)$', s, I | re.S)
        if not mm and not uv:
            break
        s = mm.group('rest') if mm else uv_target(uv.group(1))
    return s


def runs_script(s, names):
    """Сегмент исполняет скрипт с таким именем (а не читает, не ищет и не компилирует его). Судится то, что интерпретатор
    ЗАПУСКАЕТ: первый позиционный аргумент, путь после -File, строка после -Command; `python -m <модуль>` и `python -c <код>`
    — не запуск файла, кроме кода, который сам запускает файл (runpy, exec, subprocess). Наблюдение 16.10.2026: прежняя
    проверка «интерпретатор в начале + имя где угодно» отклоняла `python -m py_compile …/support-edit.py`."""
    s = strip_launcher(strip_env_prefix(s))
    interp = r'^(?:&\s*)?["\']?(?:[^\s"\']*[\\/])?(?:powershell|pwsh|python3?|py)(?:\.exe)?["\']?(?:\s|$)'
    named = r'(?:^|[\\/\s"\'])(?:' + names + r')\.(?:ps1|py)\b'
    direct = r'^(?:&\s*|\.\s+)?["\']?(?:[^\s"\']*[\\/])?(?:' + names + r')\.ps1\b'
    if m(direct, s):
        return True
    if not m(interp, s):
        return False
    toks = [t.strip('"\'') for t in re.findall(r'"[^"]*"|\'[^\']*\'|\S+', re.sub(r'^&\s*', '', s))]
    script = re.compile(r'(?:^|[\\/])(?:' + names + r')\.(?:ps1|py)$', I)
    prog, rest = re.split(r'[\\/]', toks[0])[-1].lower(), toks[1:]
    i = 0
    if prog.startswith('py'):   # python, python3, py
        while i < len(rest):
            t = rest[i]
            if re.fullmatch(r'-[A-Za-z]+', t) and re.search(r'[cm]', t[1:]):
                code = ' '.join(rest[i + 1:])
                return bool(re.search(r'runpy|exec\s*\(|subprocess|os\.system|Popen', code) and m(named, code))
            if t in ('-X', '-W'):
                i += 2
                continue
            if t.startswith('-'):
                i += 1
                continue
            return bool(script.search(t))
        return False
    while i < len(rest):   # powershell, pwsh
        t, tl = rest[i], rest[i].lower()
        if tl in ('-file', '-f'):
            return i + 1 < len(rest) and bool(script.search(rest[i + 1]))
        if tl in ('-command', '-c', '-encodedcommand', '-ec', '-e'):
            return m(named, ' '.join(rest[i + 1:]))
        if tl in PS_VALUE_OPTS:
            i += 2
            continue
        if t.startswith('-'):
            i += 1
            continue
        return bool(script.search(t))
    return False


def unquote_atoms(s):
    """Литерал из одного слова — само слово: оболочка снимает кавычки, и `git reset "--hard"`, `"rm" -rf` — те же команды
    (аудит 30.10.2026). Литерал с пробелом (текст сообщения, шаблон поиска) остаётся литералом."""
    return re.sub(r'"([^"\s$`]+)"|\'([^\'\s]+)\'', lambda mm: mm.group(1) or mm.group(2), s)


def strip_literals(s):
    """Пустые кавычки — в ничто (в шелле они схлопываются), непустые литералы — в токен-заглушку."""
    s = s.replace('""', '').replace("''", '')
    s = re.sub(r'"[^"]*"', ' STRLIT ', s)
    return re.sub(r"'[^']*'", ' STRLIT ', s)


def drop_heredoc_bodies(cmd):
    """Команда без тел heredoc (<<СЛОВО … СЛОВО) и here-string PowerShell (@' … '@): для правил дисциплины команд тело — данные
    (запись файла с текстом про запуск проверки — не запуск). Разрушительные правила тела по-прежнему видят (M6)."""
    out, end = [], None
    for line in cmd.split('\n'):
        if end is not None:
            if line.strip() == end or (end in ("'@", '"@') and line.lstrip().startswith(end)):
                end = None
                out.append(line)
            continue
        out.append(line)
        hd = re.search(r'(?<!<)<<(?!<)[-~]?\s*["\']?([A-Za-z_]\w*)["\']?', line)  # <<< — однострочная here-string, не heredoc
        if hd:
            end = hd.group(1)
        elif re.search(r'@(["\'])\s*$', line):
            end = re.search(r'@(["\'])\s*$', line).group(1) + '@'
    return '\n'.join(out)


# Тело heredoc (cat > f <<'EOF' … EOF) и here-string PowerShell (@' … '@) — данные, пока его не читает исполнитель:
# оболочка, интерпретатор, ssh, клиент СУБД или вычисление строки. Тогда тело судится как команды (волна 2, ложный отказ
# на тексте журнала 30.10.2026). Имена исполнителей — по имени программы среди слов строки с оператором.
HD_OP = re.compile(r'<<(-|~)?[ \t]*(?:"([^"\n]+)"|\'([^\'\n]+)\'|(\\)?([A-Za-z_][\w.-]*))')
FEED_SHELL = {'bash', 'sh', 'zsh', 'dash', 'ksh', 'mksh', 'ash', 'fish', 'busybox', 'pwsh', 'powershell', 'cmd', 'wsl', 'su',
              'xargs', 'source', 'at', 'batch', 'crontab', 'iex', 'invoke-expression', 'invoke-command',
              'start-job', 'add-type'}
FEED_CODE = {'python', 'python2', 'python3', 'py', 'pypy', 'pypy3', 'node', 'nodejs', 'deno', 'bun', 'ruby', 'perl', 'php',
             'lua', 'luajit', 'rscript', 'osascript', 'tclsh', 'expect'}
FEED_REMOTE = {'ssh', 'plink', 'vm-shell', 'vm-shell.py'}
FEED_SQL = {'psql', 'mysql', 'mariadb', 'sqlcmd', 'osql', 'clickhouse-client', 'sqlite3', 'mongo', 'mongosh', 'redis-cli',
            'cqlsh', 'isql'}
# вычисление строки где угодно в команде: тело могло попасть в переменную (`X=$(cat <<'EOF' …)`, затем `eval "$X"`);
# eval — только в позиции команды (EVAL_AT_CMD), поэтому его нет и в FEED_SHELL
FEED_ANYWHERE = EVAL_AT_CMD + r'|(?:^|[\s;&|(])(?:iex|Invoke-Expression)\b|ScriptBlock\]::Create'
FEED_VAR_SHELL = (r'(?:^|[\s/\\(])(?:bash|sh|zsh|dash|ksh|pwsh|powershell|cmd)(?:\.exe)?\b[^\n]*\s(?:-c|/c|-Command|'
                  r'-EncodedCommand)\s+(?:["\'][^"\'\n]*)?\$')
SUBST = r'\$\(([^()]*)\)|`([^`]*)`'


def feed_kind(text):
    """Кто читает тело: 'remote' | 'shell' | 'code' | 'sql' | '' (данные) — по словам строки с оператором (без литералов)."""
    st = strip_literals(unquote_atoms(text))
    names = set()
    for tok in re.split(r'[\s|;&()<>{}]+', st):
        t = re.split(r'[\\/]', tok.strip('"\'`'))[-1].lower()
        names.add(t[:-4] if t.endswith('.exe') else t)
    if names & FEED_REMOTE:
        return 'remote'
    if names & FEED_SHELL or m(r'ScriptBlock\]::Create', st) or m(r'(?:^|[;&|(]\s*)\.\s+\S', st) or \
            m(r'\bsudo(?:\s+-\S+(?:\s+(?!-)\S+)?)*?\s+-(?:[A-Za-z]*[si]|-shell|-login)(?=\s|$)', st, 0):
        return 'shell'
    if names & FEED_CODE:
        return 'code'
    return 'sql' if names & FEED_SQL else ''


def heredoc_spans(cmd):
    """Тела heredoc оболочки: [(начало строки оператора, конец строки оператора, начало тела, конец тела, кавычки у слова)].
    Оператор ищется вне литералов и комментариев (кавычки и $( ) — через строки, как в bash); тело — со следующей строки
    до строки, равной слову (у <<- — без ведущих табуляций). Тело без строки-конца не данные: такого «heredoc» нет."""
    out, pending, stack, i, n = [], [], ['top'], 0, len(cmd)
    while i < n:
        c, top = cmd[i], stack[-1]
        if top == 'sq':
            if c == "'":
                stack.pop()
            i += 1
            continue
        if c == '\\':
            i += 2
            continue
        if top == 'dq':
            if c == '"':
                stack.pop()
            elif cmd.startswith('$(', i):
                stack.append('sub')
                i += 1
            elif c == '`':
                stack.append('bq')
            i += 1
            continue
        if c == '#' and (i == 0 or cmd[i - 1] in ' \t\n;&|('):
            j = cmd.find('\n', i)
            i = n if j < 0 else j
            continue
        if c == "'":
            stack.append('sq')
        elif c == '"':
            stack.append('dq')
        elif cmd.startswith('$(', i):
            stack.append('sub')
            i += 1
        elif c == '(' and top == 'sub':
            stack.append('sub')
        elif c == ')' and top == 'sub':
            stack.pop()
        elif c == '`':
            stack.pop() if top == 'bq' else stack.append('bq')
        elif cmd.startswith('<<', i) and not cmd.startswith('<<<', i) and (i == 0 or cmd[i - 1] != '<'):
            mm = HD_OP.match(cmd, i)
            if mm:
                word = mm.group(2) or mm.group(3) or mm.group(5)
                pending.append((word, bool(mm.group(2) or mm.group(3) or mm.group(4)), mm.group(1) == '-',
                                cmd.rfind('\n', 0, i) + 1))
                i = mm.end()
                continue
        elif c == '\n' and pending:
            pos, line_end = i + 1, i
            for word, quoted, dash, op_line in pending:
                k, end = pos, None
                while k < n:
                    e = cmd.find('\n', k)
                    e = n if e < 0 else e
                    ln = cmd[k:e].rstrip('\r')
                    if (ln.lstrip('\t') if dash else ln) == word:
                        end = (k, e)
                        break
                    k = e + 1
                if end is None:
                    return out   # тело без конца: дальше разбор не доверяем — судится как команды
                out.append((op_line, line_end, pos, end[0], quoted))
                pos = end[1] + 1
            pending = []
            i = pos
            continue
        i += 1
    return out


def here_string_spans(cmd):
    """Тела here-string PowerShell: [(начало строки с @' или @", конец этой строки, начало тела, начало строки-конца,
    раскрывается ли $( ))]; строка-конец начинается с '@ или "@."""
    out, lines, pos, cur = [], cmd.split('\n'), 0, None
    for ln in lines:
        if cur is not None:
            if ln.lstrip().startswith(cur[1] + '@'):
                out.append((cur[0], cur[2], cur[2] + 1, pos, cur[1] == '"'))
                cur = None
        elif re.search(r'@(["\'])\s*$', ln):
            cur = (pos, re.search(r'@(["\'])\s*$', ln).group(1), pos + len(ln))
        pos += len(ln) + 1
    return out


def heredoc_view(cmd, tool=''):
    """Команда для барьера: тела-данные heredoc и here-string вырезаны (строка-конец остаётся — по ней видно, где тело
    кончилось), у раскрываемых тел (<<EOF без кавычек, @") остаются подстановки $( ) и `…` — они исполнятся.
    Тело, которое читает исполнитель (bash <<EOF, sh -s, python - <<EOF, powershell -Command -, cat <<EOF | bash,
    ssh хост <<EOF, psql <<EOF, '@ | iex), остаётся командами. Второе значение — тела для исполнителя:
    [(вид, строка оператора, тело)] — код интерпретатора, удалённая команда и SQL судятся ещё и по своим правилам.
    У PowerShell нет heredoc (<<) — там ищутся только here-string."""
    spans = [] if tool == 'PowerShell' else [(a, b, c, d, q, 'hd') for a, b, c, d, q in heredoc_spans(cmd)]
    spans += [(a, b, c, d, q, 'hs') for a, b, c, d, q in here_string_spans(cmd)]
    if not spans:
        return cmd, []
    # что останется вне тел: по нему ищутся вычисление строки и запуск файла, в который тело записано
    outside, last = [], 0
    for a, b, c, d, q, form in sorted(spans, key=lambda s: s[2]):
        if c >= last:
            outside.append(cmd[last:c])
            last = d
    outside = ''.join(outside + [cmd[last:]])
    anywhere = m(FEED_ANYWHERE, strip_literals(outside)) or m(FEED_VAR_SHELL, outside)
    cut, fed = [], []
    for a, b, c, d, q, form in spans:
        opener = cmd[a:b]
        if form == 'hs':   # исполнитель может стоять и после '@ на строке-конца
            tail_end = cmd.find('\n', d)
            opener += ' ' + cmd[d:len(cmd) if tail_end < 0 else tail_end].lstrip()[2:]
        kind = feed_kind(opener) or ('shell' if anywhere else runs_target(opener, outside))
        body = cmd[c:d]
        if kind:
            fed.append((kind, opener, body, form))
            continue
        keep = [x or y for x, y in re.findall(SUBST, body)] if (form == 'hd' and not q) or (form == 'hs' and q) else []
        cut.append((c, d, ''.join('$(%s)\n' % x for x in keep)))
    view, last = [], 0
    for c, d, repl in sorted(cut):
        view += [cmd[last:c], repl]
        last = d
    return ''.join(view + [cmd[last:]]), fed


def runs_target(opener, outside):
    """Файл, в который пишется тело (> файл, tee файл, Set-Content файл), запускается в этой же команде: интерпретатором
    (python файл) — 'code', оболочкой (bash файл, ./файл, & .\\файл.ps1, powershell -File файл) — 'shell'; иначе ''."""
    targets = re.findall(r'(?:>>?|\btee(?:\s+-a)?|\b(?:Set-Content|Add-Content|Out-File|sc|ac)(?:\s+-(?:Path|FilePath|LiteralPath))?)'
                         r'\s*["\']?([^\s"\'|;&<>]+)', opener, I)
    for t in targets:
        base = re.split(r'[\\/]', t)[-1]
        if not base or base.lower() in ('-', 'null', '$null'):
            continue
        name = re.escape(base) + r'["\']?(?:\s|$)'
        code = re.search(r'(?:^|[\s;&|(])(?:sudo\s+)?(python3?|py|node|ruby|perl|php)(?:\.exe)?\s+(?:-\S+\s+)*["\']?(?:\S*[\\/])?'
                         + name, outside, I)
        if code:
            return 'code'
        if m(r'(?:^|[\s;&|(])(?:(?:sudo\s+)?(?:bash|sh|zsh|dash|ksh|source|\.|pwsh|powershell|cmd|crontab)(?:\.exe)?\s+(?:-\S+\s+)*|'
             r'&\s*|-File\s+)["\']?(?:\S*[\\/])?' + name, outside) or \
                m(r'(?:^|\n|[;&|]\s*)["\']?\.{0,2}[\\/](?:\S*[\\/])?' + name, outside):
            return 'shell'
    return ''


def fed_commands(fed):
    """Тела, поданные исполнителю, — элементами inner_commands: код интерпретатора (удаляет сам или запускает команды),
    строки удалённой команды (на сервере), SQL клиента СУБД целиком со строкой оператора. Тело here-string для разбора
    сегментов — литерал в кавычках, поэтому его строки, поданные оболочке, судятся здесь же как команды."""
    out = []
    for kind, opener, body, form in fed:
        if form == 'hs' and kind in ('shell', 'code'):
            for line in body.split('\n'):
                p = re.sub(r'\s+', ' ', line).strip()
                if p:
                    out.append(('cmd', p, strip_literals(unquote_atoms(p)), False))
        if kind == 'code':
            if m(CODE_REMOVE, body):
                out.append(('code', body.strip(), '', False))
            if m(CODE_RUNS, body):
                args = literals(body)
                for lit in args + [' '.join(args)]:
                    out += inner_commands(lit, 1)
        elif kind == 'remote':
            for line in body.split('\n'):
                p = re.sub(r'\s+', ' ', line).strip()
                if p:
                    out.append(('cmd', p, strip_literals(unquote_atoms(p)), True))
        elif kind == 'sql':
            p = re.sub(r'\s+', ' ', opener + ' ' + body).strip()
            out.append(('cmd', p, strip_literals(p), False))
    return out


# Платформа 1С: толстый клиент, тонкий клиент, сервер; режим пакетного запуска — по ключам командной строки.
ONEC_EXE = r'1cv8[cs]?(?:\.exe)?'
CREATE_MODE = r'(?:\b1cv8[cs]?(?:\.exe)?["\']?\s+|-ArgumentList\s+(?:@\(\s*)?["\']?)CREATEINFOBASE\b'
# Регистрацию базы агент сам себе не выдаёт (аудит 30.10.2026): запись в реестр вносит владелец (guard-skills — отказ агенту)
OWNER_REGISTERS = ('Если база тестовая — скажи владельцу: запись в реестр .v8-project.json вносит он сам; иначе команду '
                   'выполняет он сам.')
LAUNCH_LEAD = r'^(?:&\s*|\.\s+|call\s+|start\s+(?:"[^"]*"\s+)?|cmd(?:\.exe)?\s+/[ck]\s+(?:start\s+(?:"[^"]*"\s+)?)?)*'


# Запуск процесса кодом или API мимо Start-Process: Python, Node, .NET, WMI/CIM
LAUNCH_API = (r'\bsubprocess\b|\bPopen\b|\bos\.(?:system|popen|spawn\w*|startfile|exec\w*)\b|\bchild_process\b|'
              r'\b(?:exec|execFile|spawn)(?:Sync)?\s*\(|\[(?:System\.)?Diagnostics\.Process\]::Start\b|'
              r'\b(?:Invoke-CimMethod|Invoke-WmiMethod)\b.*\bCreate\b|\bWin32_Process\b.*\.Create\(')


def onec_vars(cmd):
    """Имена переменных PowerShell, которым в этой команде присвоен путь к платформе ($v8 = '...\\1cv8.exe')."""
    return {x.lower() for x in re.findall(r'\$(\w+)\s*=\s*[^\n;|]*?\b' + ONEC_EXE + r'\b', cmd, I)}


def onec_direct(seg, names):
    """Сегмент запускает платформу напрямую (не через Start-Process): первым словом или оператором вызова `&`."""
    s = strip_env_prefix(seg)
    if re.match(r'\$\{?\w+\}?\s*=\s*(?!&)', s):
        return False   # `$bin = "…\\1cv8.exe"` только запоминает путь (штатная форма правила); запуск — `$p = & $bin …`
    mm = re.match(LAUNCH_LEAD + r'(?:"([^"]+)"|\'([^\']+)\'|(\S+))', s, I)
    if mm:
        tok = next(g for g in mm.groups() if g)
        if m(r'(?:^|[\\/])' + ONEC_EXE + r'$', tok):
            return True
        vm = re.match(r'^\$\{?(\w+)\}?$', tok)
        if vm and vm.group(1).lower() in names:
            return True
    # вызов внутри вложенной оболочки: powershell -Command "& 'C:\...\1cv8.exe' DESIGNER ..."
    if m(r'&\s*(?:"[^"]*[\\/]' + ONEC_EXE + r'"|\'[^\']*[\\/]' + ONEC_EXE + r'\'|\S*[\\/]' + ONEC_EXE + r'\b)', s):
        return True
    return any(v.lower() in names for v in re.findall(r'&\s*\$\{?(\w+)\}?', s))


def onec_mode(text):
    """'batch' — пакетный режим конфигуратора; 'tests' — предприятие с пакетными ключами (YAXUnit); '' — интерактивный запуск."""
    if m(r'\b(DESIGNER|CREATEINFOBASE)\b', text):
        return 'batch'
    if m(r'\bENTERPRISE\b', text) and m(r'RunUnitTests|/Execute\b|/Out\b', text):
        return 'tests'
    return ''


KILL_VERB = (r'\b(Stop-Process|spps|Wait-Process|taskkill|pkill|killall|kill)\b|\.(Kill|Terminate)\(\)|'
             r'\bInvoke-CimMethod\b.*\bTerminate\b|\bwmic\b.*\bprocess\b.*\b(call\s+terminate|delete)\b')


def selects_onec(stage):
    """Звено конвейера отбирает процессы 1С по имени: Get-Process 1cv8, Where-Object по имени, Win32_Process с Name=1cv8."""
    lit = strip_literals(stage)
    return (m(r'\b(Get-Process|gps|ps)\b', lit) and m(r'\b(Get-Process|gps|ps)\s+(?:-Name\s+)?["\']?1cv8', stage)) or \
        m(r'\bWhere-Object\b.*\b(Name|ProcessName)\s+-(like|eq|match)\s+["\']?1cv8', stage) or \
        (m(r'\b(Get-CimInstance|gcim|Get-WmiObject|gwmi)\b', lit) and m(r'\bWin32_Process\b.*\bName\s*(=|\s+like\s+)\s*\\?["\']?1cv8', stage))


def onec_selection_vars(statements):
    """Переменные, которым присвоен отбор процессов 1С по имени ($p = Get-Process 1cv8): остановка через них — тоже по имени."""
    out = set()
    for st in statements:
        mm = re.match(r'\s*\$(\w+)\s*=', st)
        if mm and not m(r'CommandLine', st) and any(selects_onec(x) for x in split_outside_quotes(st)):
            out.add(mm.group(1).lower())
    return out


# Текст в кавычках, который исполнит другая программа: вложенная оболочка, удалённая команда, Start-Process оболочки
RUNS_QUOTED = r'\b(?:Start-Process|saps)\b.*\b(?:pwsh|powershell|cmd|bash|sh)(?:\.exe)?\b'


def statements_of(cmd, depth=0):
    """Операторы команды для правила остановки процессов: по ; && || и переводу строки вне кавычек (звенья `|` — вместе),
    плюс операторы текста, который исполнит вложенная оболочка или удалённая команда (`powershell -Command "a | b"`).
    `;` и `|` в тексте сообщения коммита, echo или шаблоне grep — данные, а не разделители (волна 2, 30.10.2026)."""
    out = []
    for st in split_outside_quotes(cmd, pipes=False):
        out.append(st)
        bare = strip_literals(unquote_atoms(st))
        if depth < 3 and (m(SHELL_CARRIER, bare) or m(REMOTE_CARRIER, bare) or m(RUNS_QUOTED, bare)):
            for lit in literals(st):
                out += statements_of(lit, depth + 1)
    return out


def kill_by_name(statement, sel_vars=()):
    """Остановка или ожидание процессов 1С по ИМЕНИ (под маску попадают чужие сеансы), без фильтра по командной строке:
    ключом имени, отбором в том же звене или раньше по конвейеру, переменной с таким отбором из прежней команды."""
    if m(r'CommandLine', statement):
        return False
    stages = split_outside_quotes(statement)
    by_name = (r'(-Name|-ProcessName|/IM)\s*[:=]?\s*["\']?1cv8|\b(pkill|killall)\b[^\n]*1cv8|/FI\s*["\']?\s*IMAGENAME\s+eq\s+1cv8|'
               r'\bwmic\b.*\bwhere\b.*\bname\s*(=|\s+like\s+)\s*\\?["\']?1cv8')
    for i, stage in enumerate(stages):
        if not m(KILL_VERB, strip_literals(stage)):
            continue
        if m(by_name, stage) or selects_onec(stage) or any(selects_onec(x) for x in stages[:i]):
            return True
        if any(re.search(r'\$' + re.escape(v) + r'\b', x, I) for x in stages[:i + 1] for v in sel_vars):
            return True
    return False


def norm_path(p, project_dir):
    """Путь базы для сверки с реестром: путь Git Bash /d/x — это D:\\x; удвоенный обратный слэш ("D:\\\\_work\\\\ib" в двойных
    кавычках Bash — это D:\\_work\\ib, а Windows понимает его и в PowerShell) — один; слэши — обратные, регистр — нижний."""
    p = p.strip()
    if os.name == 'nt':
        p = re.sub(r'^/([a-zA-Z])(?=/|$)', r'\1:', p)
    p = p.replace('/', '\\')
    unc = re.match(r'\\{2,}', p)
    p = ('\\\\' if unc else '') + re.sub(r'\\{2,}', r'\\', p[unc.end():] if unc else p)
    try:
        if not os.path.isabs(p):
            p = os.path.abspath(os.path.join(project_dir, p))
    except (OSError, ValueError):
        pass
    return p.rstrip('\\').lower()


# Имя платформы 1С в сегменте и программы, которые только печатают, ищут или показывают текст: имя платформы у них в
# аргументах — шаблон поиска или текст, а не запуск (`grep -o "1cv8.exe ENTERPRISE /F D:…" журнал`, ложный отказ 30.10.2026).
# sed и awk сюда не входят: они умеют исполнять команды (e, system()).
PLATFORM_WORD = r'\b(?:1cv8[cs]?|ibcmd)(?:\.exe)?\b'
TEXT_PROGRAMS = {'grep', 'egrep', 'fgrep', 'rg', 'findstr', 'select-string', 'sls', 'cat', 'type', 'tac', 'less', 'more', 'head',
                 'tail', 'echo', 'printf', 'write-host', 'write-output', 'get-content', 'gc', 'ls', 'dir', 'get-childitem', 'gci',
                 'test-path', 'wc', 'sort', 'uniq', 'cut', 'where', 'which', 'get-command', 'git', 'gh', 'jq'}


def program_of(seg):
    """Программа сегмента: первое слово после префиксов окружения и запуска (&, call, start, cmd /c) — без пути и .exe."""
    s = strip_env_prefix(seg.strip())
    mm = re.match(LAUNCH_LEAD + r'(?:"([^"]*)"|\'([^\']*)\'|(\S+))', s, I)
    tok = next((x for x in mm.groups() if x), '') if mm else ''
    name = re.split(r'[\\/]', tok)[-1].lower()
    return name[:-4] if name.endswith('.exe') else name


def launches_platform(seg):
    """Сегмент может запустить платформу (1cv8, 1cv8c, ibcmd): её имя есть, а программа сегмента — не из печатающих и ищущих
    текст; у них — только платформа в подстановке $( ) или `…` (она исполнится). Прочее, в том числе обёртки, судится."""
    if not m(PLATFORM_WORD, seg):
        return False
    return program_of(seg) not in TEXT_PROGRAMS or \
        m(r'\$\([^)]*%s|`[^`]*%s' % (PLATFORM_WORD, PLATFORM_WORD), re.sub(r"'[^']*'", ' ', seg))


def join_arrays(cmd):
    """Массив @( … ) на нескольких строках — одной строкой: перевод строки внутри него не разделяет команды."""
    return re.sub(r'@\((?:[^()]|\([^()]*\))*\)', lambda mm: re.sub(r'\s*\n\s*', ' ', mm.group(0)), cmd)


def shell_vars(cmd):
    """Переменные, которым эта же команда присвоила значение: `f=.env`, `$a='…'`, `$a=@('DESIGNER','/F',$ib)`, `$a+='…'`, `$env:X='…'`."""
    out = {}
    for st in statements_of(join_arrays(cmd)):
        mm = re.match(r'\s*(?:export\s+|local\s+|set\s+)?\$?(?:env:)?([^\W\d]\w*)\s*(\+?=)\s*(.*?)\s*$', st, re.S)
        if not mm:
            continue
        lits = literals(mm.group(3))
        val = ' '.join(lits) if lits else (mm.group(3).split() or [''])[0]
        key = mm.group(1).lower()
        out[key] = out.get(key, '') + ' ' + val if mm.group(2) == '+=' else val
    return out


def expand_vars(text, vars_):
    """Текст с подставленными значениями известных переменных; неизвестная остаётся как есть."""
    if not vars_:
        return text
    for _ in range(3):
        new = re.sub(r'\$(?:env:)?\{?([^\W\d]\w*)\}?', lambda mm: vars_.get(mm.group(1).lower(), mm.group(0)), text)
        if new == text:
            break
        text = new
    return text


def platform_view(seg, vars_):
    """Сегмент таким, каким его получит платформа: переменные подставлены, массив -ArgumentList 'a','b' склеен в строку —
    штатная форма правила designer-batch-runs п.2, а шаблоны /F и /S ищут ключ после пробела."""
    s = expand_vars(re.sub(r'(?<=\s)@([^\W\d]\w*)\b', r'$\1', seg), vars_).replace('`"', '"')
    mm = re.search(r'-(?:ArgumentList|Args)\b[\s:]*(.*)$', s, I)
    if mm:
        tail = re.split(r'\s-(?:Wait|PassThru|NoNewWindow|WindowStyle|WorkingDirectory|FilePath|RedirectStandard\w+|Verb|Credential|'
                        r'LoadUserProfile|UseNewEnvironment)\b', mm.group(1), maxsplit=1, flags=I)[0]
        lits = literals(tail)
        if lits:
            s += ' ' + ' '.join(lits)
    return s


def launches_by_args(view):
    """Программа в переменной ($env:V8BIN, $bin из другой команды): платформу выдаёт её режим в аргументах запуска."""
    return m(r'(?:^|[\s;&|(])(?:Start-Process|saps|&)\s', view) and m(r'(?:^|[\s"\'])(?:DESIGNER|ENTERPRISE|CREATEINFOBASE)(?=[\s"\']|$)', view)


def db_host(s):
    """Сервер 1С или СУБД для сверки с реестром: без кавычек, регистра, схемы tcp://, tcp: и ssh://, пользователя (ssh://u@srv),
    порта (srv:1541, srv,1433) и именованного экземпляра MS SQL (srv\\inst)."""
    s = str(s or '').strip().strip('"\'').lower()
    s = re.sub(r'^(?:tcp:(?://)?|ssh://)', '', s).split('@')[-1]
    return re.split(r'[:,\\]', s)[0]


def path_forms(p):
    """\u041d\u043e\u0440\u043c\u0430\u043b\u0438\u0437\u043e\u0432\u0430\u043d\u043d\u044b\u0439 \u043f\u0443\u0442\u044c \u0432 \u0434\u043b\u0438\u043d\u043d\u043e\u0439 \u0438 \u043a\u043e\u0440\u043e\u0442\u043a\u043e\u0439 (8.3) \u0444\u043e\u0440\u043c\u0435 Windows \u2014 %TEMP% \u0431\u044b\u0432\u0430\u0435\u0442 \u0437\u0430\u043f\u0438\u0441\u0430\u043d \u043b\u044e\u0431\u043e\u0439 \u0438\u0437 \u043d\u0438\u0445."""
    forms = {p}
    if os.name == 'nt':
        import ctypes
        for fn in (ctypes.windll.kernel32.GetLongPathNameW, ctypes.windll.kernel32.GetShortPathNameW):
            buf = ctypes.create_unicode_buffer(32768)
            if fn(p, buf, 32768):
                forms.add(buf.value)
    return {os.path.normcase(os.path.abspath(f)).rstrip('\\/') for f in forms if f}


def under_temp(local):
    parents = path_forms(os.path.dirname(os.path.abspath(local)))
    return any(c == t or c.startswith(t + os.sep) for t in path_forms(temp_dir()) for c in parents)


def ssh_mcp_local_file(tool, tool_input):
    """\u041f\u0440\u0438\u0447\u0438\u043d\u0430 \u043e\u0442\u043a\u0430\u0437\u0430 \u0434\u043b\u044f \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u043e\u0433\u043e \u0444\u0430\u0439\u043b\u0430 \u0438\u043d\u0441\u0442\u0440\u0443\u043c\u0435\u043d\u0442\u0430 ssh-mcp \u0438\u043b\u0438 None."""
    local = str(tool_input.get('localPath') or '')
    if not local.strip():
        return None
    if m(SECRET_FILE, local) or m(HOME_CREDS, local):
        return ('\u043b\u043e\u043a\u0430\u043b\u044c\u043d\u044b\u0439 \u0444\u0430\u0439\u043b \u2014 \u0441\u0435\u043a\u0440\u0435\u0442 \u0438\u043b\u0438 \u0443\u0447\u0451\u0442\u043d\u044b\u0435 \u0434\u0430\u043d\u043d\u044b\u0435 (.env/*.key/*.pem/~/.ssh/\u0442\u043e\u043a\u0435\u043d\u044b): \u0447\u0435\u0440\u0435\u0437 %s \u043e\u043d \u0443\u0439\u0434\u0451\u0442 \u043d\u0430 \u0441\u0435\u0440\u0432\u0435\u0440 '
                '\u0438\u043b\u0438 \u0431\u0443\u0434\u0435\u0442 \u043f\u0435\u0440\u0435\u0437\u0430\u043f\u0438\u0441\u0430\u043d' % tool)
    if tool.endswith('sftp-download-file') and not under_temp(local):
        return ('\u0441\u043a\u0430\u0447\u0438\u0432\u0430\u043d\u0438\u0435 \u043f\u0438\u0448\u0435\u0442 \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u044b\u0439 \u0444\u0430\u0439\u043b \u043c\u0438\u043c\u043e \u0431\u0430\u0440\u044c\u0435\u0440\u043e\u0432 Edit/Write; \u0440\u0430\u0437\u0440\u0435\u0448\u0435\u043d\u043e \u0442\u043e\u043b\u044c\u043a\u043e \u0432\u043e \u0432\u0440\u0435\u043c\u0435\u043d\u043d\u0443\u044e \u043f\u0430\u043f\u043a\u0443 (%s), '
                '\u0434\u0430\u043b\u044c\u0448\u0435 \u2014 \u0448\u0442\u0430\u0442\u043d\u044b\u043c\u0438 \u0438\u043d\u0441\u0442\u0440\u0443\u043c\u0435\u043d\u0442\u0430\u043c\u0438' % temp_dir())
    return None


def main():
    raw = sys.stdin.buffer.read().decode('utf-8', 'replace').lstrip('\ufeff')
    if not raw.strip():
        return
    data = json.loads(raw)
    tool_input = data.get('tool_input') or {}
    project_dir = os.environ.get('CLAUDE_PROJECT_DIR', '')

    # Политика адреса до запроса: только два опасных класса, остальное (в том числе localhost) пропускается.
    url = str(tool_input.get('url') or '')
    if url:
        u = url.strip().lower()
        if re.match(r'^(file|data|javascript|blob|vbscript):', u):
            scheme = re.sub(r'^([a-z]+):.*', r'\1:', u, flags=re.S)
            emit_deny("Схема адреса запрещена до запроса: '%s'. http(s) — единственный разрешённый транспорт для внешнего контента; "
                      "file:/data:/javascript: читают локальное или исполняют код под видом загрузки." % scheme)
        if re.search(r'://(169\.254\.169\.254|metadata\.google\.internal|100\.100\.100\.200|metadata\.azure\.com|metadata\.oraclecloud\.com|169\.254\.170\.2)([:/]|$)', u):
            emit_deny('Адрес — эндпоинт метаданных облачного провайдера: такой запрос отдаёт учётные данные инстанса, а не документацию. '
                      'Запрещён независимо от того, кто его предложил (secrets-and-production-database).')

    tool = str(data.get('tool_name') or '')
    # Запреты Read(**/…) в permissions.deny действуют только внутри папки проекта (замер 30.10.2026), здесь — по всей машине
    if tool in ('Read', 'Grep'):
        for p in (str(tool_input.get(k) or '') for k in ('file_path', 'path', 'glob')):
            if p and secret_path(p):
                emit_deny('Заблокировано до-исполнительным барьером (guard-destructive): чтение секрета инструментом %s (.env/*.key/*.pem/'
                          '.pgpass/ключи, папка ключей агента, домашние учётные данные) — секрет попадёт в контекст и журнал сессии '
                          '(secrets-and-production-database п.6).\nПуть: %s' % (tool, p))
        return
    if tool.startswith('mcp__') and 'ssh-mcp' in tool:
        if tool.endswith('signal-process'):
            emit_deny('Заблокировано до-исполнительным барьером (guard-destructive): сигнал процессу на сервере (ssh-mcp signal-process) — '
                      'остановку процессов 1С и СУБД выполняет владелец сам.')
        if tool.endswith('reload-config') and str(tool_input.get('action') or '').lower() == 'reload':
            emit_deny('Заблокировано до-исполнительным барьером (guard-destructive): перечитать настройки ssh-mcp (reload-config с '
                      'action=reload) — так вступает в силу снятие ворот подтверждения команд на сервере. Перечитывает их владелец сам; '
                      'status проходит.')
        why = ssh_mcp_local_file(tool, tool_input)
        if why:
            emit_deny('Заблокировано до-исполнительным барьером (guard-destructive): %s.\nФайл: %s' % (why, tool_input.get('localPath')))
        remote = str(tool_input.get('remotePath') or '')
        if 'sftp-download' in tool and (m(SECRET_FILE, remote) or m(HOME_CREDS, remote)):
            emit_deny('Заблокировано до-исполнительным барьером (guard-destructive): скачивание секрета с сервера (.env/*.key/*.pem/'
                      '.pgpass/~/.ssh) — секрет попадёт на эту машину и в контекст.\nФайл на сервере: %s' % remote)

    cmd = str(tool_input.get('command') or '')
    if not cmd.strip():
        return
    # Тело heredoc и here-string — данные, пока его не читает исполнитель: дальше барьер судит команду без таких тел
    cmd, fed = heredoc_view(cmd, tool)
    cmd = expand_del_alias(re.sub(r'\\\r?\n[ \t]*', ' ', cmd))   # перенос строки в оболочке — тот же сегмент

    # Сегменты режутся ДО нормализации пробелов: иначе многострочная команда станет одним сегментом. Разделители внутри
    # кавычек — не разделители: `git commit -m "a (rm -rf x); c"` резался по `;`, кавычка оставалась открытой и текст
    # сообщения судился как команда (волна 2 п.2.13, наблюдение 29.10.2026).
    raw_segments = [x for x in split_outside_quotes(cmd) if x.strip()]
    # Строки тела, которое читает не оболочка (код, SQL, удалённая команда): прежние правила видят их как команды (M6), а правила
    # по словам команды — нет: для них это данные, а имена в тексте кода — не аргументы программы (замер на журналах сессий).
    own_cmd = cmd
    for kind, _, body, _ in fed:
        if kind != 'shell' and body:
            own_cmd = own_cmd.replace(body, '', 1)
    vars_ = shell_vars(own_cmd)

    # команда исполнится на сервере: инструмент ssh-mcp целиком, в Bash — сегмент с ssh/tmux send-keys/vm-shell
    ssh_mcp = tool.startswith('mcp__') and 'ssh-mcp' in tool
    for seg in raw_segments:
        norm = re.sub(r'\s+', ' ', seg).strip()
        norm_git = re.sub(r'\bgit\s+-C\s+\S+\s+', 'git ', norm)   # с учётом регистра: `git -c ключ=значение` — другой ключ
        stripped = strip_literals(unquote_atoms(norm_git))
        why = destructive(stripped, on_server=ssh_mcp or m(REMOTE_CARRIER, stripped), raw=norm_git) or sql_drop(norm_git)
        if not why:
            why = secret_read(stripped, norm_git)
        if not why and registry_write(stripped, norm_git):
            why = 'правка реестра Windows (reg add/delete/import, regedit /s, *-ItemProperty по HKLM:/HKCU:) — меняет систему, в том числе автозапуск'
        if not why and m(r'\bgh\s+auth\s+(token\b|status\b.*--show-token)', stripped):
            why = 'печать токена GitHub CLI (gh auth token / --show-token) — токен попадёт в контекст и журнал'
        if not why:
            rq = remote_quoted(norm_git)
            if rq:
                why = 'удалённая команда в кавычках (ssh/tmux send-keys/vm-shell): ' + rq
        if why:
            emit_deny('Заблокировано до-исполнительным барьером (guard-destructive): %s.\nСегмент: %s\n'
                      'Если это осознанное решение — выполни вручную сам; агент деструктив не запускает.' % (why, norm))

    # То, что исполнит сама оболочка: слова команды, файлы доверия, слой экрана. Значения переменных этой же команды подставляются:
    # `f=.env; cat $f`, `F=logs; echo x > $F/consent.json`.
    for seg in split_outside_quotes(own_cmd):
        norm = re.sub(r'\s+', ' ', seg).strip()
        plain = re.sub(r'\bgit\s+-C\s+\S+\s+', 'git ', norm)
        lhs = re.match(r'\$[\w:]+\s*\+?=', plain)   # левая часть присваивания — имя, а не значение
        lhs = lhs.end() if lhs else 0
        expanded = plain[:lhs] + expand_vars(plain[lhs:], vars_)
        why = secret_read(strip_literals(unquote_atoms(plain)), expanded) or secret_word_read(expanded)
        if not why and not ssh_mcp:
            why = owner_file_write(expanded)
        if not why and screen_layer(norm):
            why = ('no-screen-control: управление экраном и вводом через ОС (SendKeys, CopyFromScreen, mouse_event, pyautogui, nircmd) — '
                   'слой экрана запрещён и из оболочки; состояние дают сами объекты: edt-mcp, read_page, снимок формы')
        if why:
            emit_deny('Заблокировано до-исполнительным барьером (guard-destructive): %s.\nСегмент: %s\n'
                      'Если это осознанное решение — выполни вручную сам; агент деструктив не запускает.' % (why, norm))

    segs_norm = [re.sub(r'\s+', ' ', x).strip() for x in raw_segments]

    port = toolkit_bypass(cmd, project_dir, fed)
    if port:
        emit_deny('Заблокировано до-исполнительным барьером (guard-destructive): обращение к серверу 1c-toolkit (порт %s) мимо MCP — '
                  'так данные базы идут к модели без барьера ПДн (personal-data-masked-from-1c п.6). Данные базы — инструментами '
                  'тулкита; штатные /health и /api/close_1c_session этого правила не касаются.' % port)

    # Команда внутри другой: вложенная оболочка, удалённая команда, код интерпретатора — те же правила, что снаружи.
    inner = inner_commands(cmd) + fed_commands(fed)
    for kind, p, st, remote in inner:
        why = 'рекурсивное удаление в коде интерпретатора (shutil.rmtree, fs.rmSync с recursive, …)' if kind == 'code' else \
            destructive(st, on_server=remote or ssh_mcp, raw=p) or sql_drop(p) or secret_read(st, p)
        if why:
            emit_deny('Заблокировано до-исполнительным барьером (guard-destructive): команда внутри другой (вложенная оболочка, '
                      'heredoc в исполнитель, удалённая команда или код интерпретатора) — %s.\nКоманда: %s\nЕсли это осознанное '
                      'решение — выполни вручную сам; агент деструктив не запускает.' % (why, p))

    # То же для того, что исполнит вложенная оболочка; код, поданный интерпретатору телом heredoc, — на запись в файл доверия
    for kind, p, st, remote in inner_commands(own_cmd) + fed_commands([f for f in fed if f[0] == 'shell']):
        why = secret_word_read(p) or (owner_file_write(p) if not remote and not ssh_mcp else None) if kind == 'cmd' else None
        if why:
            emit_deny('Заблокировано до-исполнительным барьером (guard-destructive): команда внутри другой (вложенная оболочка, '
                      'heredoc в исполнитель, удалённая команда или код интерпретатора) — %s.\nКоманда: %s\nЕсли это осознанное '
                      'решение — выполни вручную сам; агент деструктив не запускает.' % (why, p))
    for kind, _, body, _ in fed:
        why = owner_code_reason(body) if kind == 'code' and not ssh_mcp else None
        if why:
            emit_deny('Заблокировано до-исполнительным барьером (guard-destructive): %s.\nКоманда: %s' % (why, body.strip()[:300]))

    # Конвейер целиком: звенья по отдельности безобидны (`gci -Recurse | ri`, `ls .env | xargs cat`, `find | xargs rm`)
    for statement in statements_of(drop_heredoc_bodies(cmd)):
        why = pipe_verdict(statement)
        if why:
            emit_deny('Заблокировано до-исполнительным барьером (guard-destructive): %s.\nКоманда: %s\n'
                      'Если это осознанное решение — выполни вручную сам; агент деструктив не запускает.' % (why, re.sub(r'\s+', ' ', statement).strip()))

    # Изменяющий SQL — только к серверу СУБД из реестра; части режутся без разделителей внутри кавычек (`-c "SELECT 1; UPDATE …"`).
    sql_parts = [(p, strip_literals(p)) for p in (re.sub(r'\s+', ' ', x).strip() for x in split_outside_quotes(cmd))]
    sql_parts = [(p, st) for p, st in sql_parts + [(p, st) for kind, p, st, _ in inner if kind == 'cmd'] if re.search(SQL_CLIENT, st, I)]
    sql_dbs = registry_or_deny(project_dir, cmd) if sql_parts else []
    servers = {db_host(db[k]) for db in sql_dbs for k in ('server', 'dbServer', 'db_server') if db.get(k)}
    for p, st in sql_parts:
        why = sql_write(p, st, servers)
        if why:
            emit_deny('Заблокировано до-исполнительным барьером (guard-destructive): %s.\nКоманда: %s\nЧтение (SELECT) проходит; '
                      'изменение — только на тестовом сервере, зарегистрированном в .v8-project.json (server или dbServer), '
                      'иначе — вручную владельцем.' % (why, p))
        table = sql_read(p)
        if table and not sql_clean_base(p, st, sql_dbs):
            emit_deny('Заблокировано до-исполнительным барьером (guard-destructive): запрос клиента СУБД читает таблицу данных %s — это '
                      'данные базы мимо барьера ПДн (personal-data-masked-from-1c п.6).\nКоманда: %s\nПроходят системные каталоги '
                      '(pg_*, information_schema, sys.*), SELECT count(*) и таблицы базы с pd: none, если сервер и база в команде совпали с '
                      'dbServer и dbName её записи в .v8-project.json; остальное читает владелец сам.' % (table, p))

    # Остановка и ожидание процессов 1С — только своих, по командной строке своей базы (designer-batch-runs пп.3–4).
    # Раньше проверки базы: иначе `taskkill /F /IM 1cv8.exe` получил бы отказ с неверной причиной («база '/IM'»).
    # Операторы — без разрезов внутри кавычек: `git commit -m "Stop-Process -Name 1cv8; …"` — текст, а не остановка
    statements = statements_of(drop_heredoc_bodies(cmd))
    sel_vars = onec_selection_vars(statements)
    for statement in statements:
        if kill_by_name(statement, sel_vars):
            emit_deny('Остановка или ожидание процессов 1С по ИМЕНИ (designer-batch-runs пп.3–4): под маску попадают чужие сеансы — '
                      'Конфигуратор владельца, другие экземпляры.\nКоманда: %s\nНужно: отбирать по командной строке своей базы '
                      '(Get-CimInstance Win32_Process … | Where-Object { $_.CommandLine -like "*<путь своей базы>*" }) или по .Id из '
                      'Start-Process -PassThru. Чужой сеанс — сообщить владельцу, не трогать.' % re.sub(r'\s+', ' ', statement).strip())

    # Целевая база 1С: CLI (1cv8/ibcmd) и исполняемые скрипты db-* (кроме db-create и db-list) — по .v8-project.json.
    # web-publish открывает базу для веб-доступа — тоже только зарегистрированную (тестовую).
    # Части режутся без разделителей внутри кавычек: строка подключения «File=…;» и «Srvr=…;Ref=…» не должна распасться.
    # epf-dump и erf-dump (тот же скрипт epf-dump) открывают базу платформой — тоже только зарегистрированную (30.10.2026).
    db_scripts = r'db-(?!create\b|list\b)[a-z-]+|web-publish|epf-dump|erf-dump|epf-build|erf-build'
    # Каждый сегмент — в виде после подстановки переменных и склейки массива -ArgumentList (platform_view).
    cli_1c = [v for v, x in ((platform_view(y, vars_), y) for y in (re.sub(r'\s+', ' ', z).strip() for z in split_outside_quotes(join_arrays(own_cmd))))
              if launches_platform(v) or launches_by_args(v) or runs_script(x, db_scripts)]
    if cli_1c:
        known, known_paths, pairs = [], [], []
        for db in registry_or_deny(project_dir, cmd):
            for key in ('ref', 'server', 'path', 'name'):
                if db.get(key):
                    known.append(str(db[key]))
            for alias in (db.get('aliases') or []):
                if alias:
                    known.append(str(alias))
            if db.get('path'):
                known_paths.append(norm_path(str(db['path']), project_dir))
            if db.get('server'):
                # серверная база сверяется парой «сервер + база»: имя БД СУБД (ibcmd --db-name) — dbName или ref
                pairs.append((db_host(db['server']), str(db.get('ref') or '').lower(),
                              str(db.get('dbName') or db.get('db_name') or db.get('ref') or '').lower()))
        known_low = {k.lower() for k in known}
        srv_res = (r'(?:^|\s)/S\s*["\']?([^\s"\'\\/]+)[\\/]', r'(?<![-\w])Srvr\s*=\s*["\']?([^;"\'\s]+)',
                   r'-InfoBaseServer[= ]\s*["\']?([^\s"\']+)', r'--(?:db|database)-server[= ]\s*["\']?([^\s"\']+)')
        ref_res = (r'(?:-InfoBaseRef[= ]\s*|(?<![-\w])Ref=|(?:^|\s)/S\s*["\']?[^\s"\'\\/]+[\\/]|--(?:db|database)-name[= ]\s*)["\']?(\w[^\s"\';,\\]*)',
                   r'(?:^|\s)/IBName\s*(?:"([^"]+)"|\'([^\']+)\'|(\S+))')
        path_res = (r'-InfoBasePath[= ]\s*(?:"([^"]+)"|\'([^\']+)\'|(\S+))',
                    r'(?:^|\s)/F\s*(?:"([^"]+)"|\'([^\']+)\'|([^\s"\']+))',
                    r'(?<![-\w])File\s*=\s*(?:"([^"]+)"|\'([^\']+)\'|([^;"\']+))',
                    r'--(?:db|database)-path[= ]\s*(?:"([^"]+)"|\'([^\']+)\'|(\S+))')
        ibcmd_args = r'\bibcmd(?:\.exe)?["\']?\s(.*)$'   # ключи самой ibcmd, а не обёртки: `bash -c "ibcmd …"`
        for seg in cli_1c:
            # создание новой базы в существующую (боевую) не пишет — но только настоящий режим создания: слово первым
            # аргументом платформы или `ibcmd infobase create`; в имени журнала или в комментарии — не режим (аудит 30.10.2026)
            seg_nc = re.sub(r'(^|\s)#.*$', '', seg)
            if (m(CREATE_MODE, seg_nc) and not m(r'\b(DESIGNER|ENTERPRISE)\b', seg_nc)) or \
                    m(r'\bibcmd(?:\.exe)?["\']?\s+infobase\s+create\b', seg_nc):
                continue
            if m(r'(?:^|\s)/@', seg):
                emit_deny("Параметры запуска платформы из файла (/@): базу в файле барьер не видит, незарегистрированная считается "
                          "боевой (secrets-and-production-database).\nСегмент: %s\nНужно: база прямо в команде (/F, /S)." % seg)
            ib_args = re.search(ibcmd_args, seg, I)
            ib_args = ' ' + ib_args.group(1) if ib_args else ''
            if m(r'\s(?:--config[= ]|-c[= ]?\s*\S)', ib_args, 0):
                emit_deny("ibcmd с файлом конфигурации (--config, -c): базу в нём барьер не видит, незарегистрированная считается боевой "
                          "(secrets-and-production-database).\nСегмент: %s\nНужно: база прямо в команде (--db-path, --db-server и --db-name)." % seg)
            servers = [db_host(mm.group(1)) for rx in srv_res for mm in re.finditer(rx, seg, I)]
            # адрес шлюза автономного сервера: --remote=ssh://хост:порт, -r ssh://хост:порт
            servers += [db_host(x) for x in re.findall(r'\s(?:--remote|-r)(?:=|\s+)["\']?([^\s"\']+)', ib_args)]
            if servers:
                # указан сервер — он и база должны быть ОДНОЙ записью реестра; псевдоним вместо ref — другая база на кластере
                own = {p[0] for p in pairs}
                for srv in servers:
                    if srv not in own:
                        emit_deny("Сервер 1С '%s' не из .v8-project.json: совпадение имени базы с тестовой не делает чужой сервер "
                                  "тестовым — незарегистрированный сервер считается боевым (secrets-and-production-database), агент на "
                                  "него не пишет.\nСегмент: %s\n" % (srv, seg) + OWNER_REGISTERS)
                for rx in ref_res:
                    for mm in re.finditer(rx, seg, I):
                        ref = next(g for g in mm.groups() if g).lower()
                        if not any(p[0] in servers and ref in (p[1], p[2]) for p in pairs):
                            emit_deny("База 1С '%s' на сервере '%s' не зарегистрирована парой server + ref в .v8-project.json "
                                      "(псевдоним и имя другой записи не засчитываются). Незарегистрированная считается боевой "
                                      "(secrets-and-production-database): агент на неё не пишет.\nСегмент: %s\n"
                                      % (ref, ', '.join(servers), seg) + OWNER_REGISTERS)
                continue
            for rx in ref_res:
                for mm in re.finditer(rx, seg, I):
                    ref = next(g for g in mm.groups() if g)
                    if ref.lower() not in known_low:
                        emit_deny("Целевая база 1С '%s' НЕ зарегистрирована в .v8-project.json. Незарегистрированная считается боевой "
                                  "(secrets-and-production-database): агент на неё не пишет.\nСегмент: %s\n" % (ref, seg) + OWNER_REGISTERS)
            for rx in path_res:
                for pm in re.finditer(rx, seg, I):
                    ib_path = next(g for g in pm.groups() if g).strip()
                    if norm_path(ib_path, project_dir) in known_paths:
                        continue
                    emit_deny("Файловая база 1С '%s' НЕ зарегистрирована в .v8-project.json (databases[].path). Незарегистрированная "
                              "считается боевой (secrets-and-production-database): агент на неё не пишет.\nСегмент: %s\n"
                              % (ib_path, seg) + OWNER_REGISTERS)
            if m(r'-(?:ArgumentList|Args)\b[\s:]*(?:@\(\s*)?["\']?\$', seg) and \
                    not any(re.search(rx, seg, I) for rx in srv_res + ref_res + path_res):
                emit_deny("Аргументы запуска платформы в переменной, значение которой барьер не видит: база не распознана, незарегистрированная "
                          "считается боевой (secrets-and-production-database).\nСегмент: %s\nНужно: присвоить аргументы в этой же команде "
                          "или написать базу прямо в -ArgumentList." % seg)

    # Скрипт скилла с платформой без -V8Path вне проекта: выберется новейшая платформа и может сконвертировать базу.
    plat_scripts = r'db-(?!list\b)[a-z-]+|epf-build|epf-dump|erf-build|erf-dump|web-publish'
    run_dir = str(data.get('cwd') or '') or project_dir
    if run_dir.strip():
        for seg in segs_norm:
            cdm = re.match(r'^(?:cd|chdir|set-location|push-location|sl|pushd)\s+(?:/d\s+)?["\']?([^"\']+?)["\']?\s*$', seg, I)
            if cdm:
                to = re.sub(r'^/([a-z])/', r'\1:/', cdm.group(1), flags=I)
                try:
                    run_dir = to if os.path.isabs(to) else os.path.abspath(os.path.join(run_dir, to))
                except (OSError, ValueError):
                    pass
                continue
            if runs_script(seg, plat_scripts) and not m(r'(^|\s)-V8Path\b', seg):
                reg_file, d = None, run_dir
                while d:
                    if os.path.exists(os.path.join(d, '.v8-project.json')):
                        reg_file = os.path.join(d, '.v8-project.json')
                        break
                    up = os.path.dirname(d)
                    if not up or up == d:
                        break
                    d = up
                why = '' if reg_file else "от каталога запуска '%s' вверх нет .v8-project.json" % run_dir
                if reg_file:
                    try:
                        with open(reg_file, encoding='utf-8-sig') as f:
                            reg = json.load(f)
                        dbs = reg.get('databases') or []
                        dbs = [dbs] if isinstance(dbs, dict) else dbs
                        if not (reg.get('v8path') or (dbs and all(isinstance(x, dict) and x.get('v8path') for x in dbs))):
                            why = "в %s не задан v8path (ни общий, ни у каждой базы)" % reg_file
                    except (OSError, ValueError) as e:
                        why = 'реестр баз %s не читается (%s)' % (reg_file, e)
                if why:
                    emit_deny("Скрипт скилла запускается без -V8Path, а %s: платформа выберется сама — новейшая установленная, "
                              "а она может быть другой линейки (например, 8.5), и открытие базы платформой другой линейки может её "
                              "сконвертировать.\nСегмент: %s\nПередай -V8Path из v8path в .v8-project.json или запусти из корня проекта." % (why, seg))

    # Прямой запуск скриптов необратимых скиллов: только отказ (подтверждение в режиме без вопросов не гарантировано).
    locked = r'meta-remove|support-edit|remove-form|remove-template|db-load-dt'
    # сегменты — без разрезов внутри кавычек: `python -c "import runpy; runpy.run_path(…)"` иначе распадался надвое и проходил
    # внутри вложенной оболочки и через Start-Process — тот же запуск (аудит 30.10.2026)
    started = r'\b(?:Start-Process|saps)\b.*\b(?:python3?|py|pwsh|powershell)(?:\.exe)?\b.*(?:^|[\\/\s"\'])(?:%s)\.(?:ps1|py)\b' % locked
    for seg in [re.sub(r'\s+', ' ', x).strip() for x in split_outside_quotes(cmd)] + [p for kind, p, _, _ in inner if kind == 'cmd']:
        if runs_script(seg, locked) or m(started, seg) or \
                m(r'\b(?:Start-Process|saps)\b.*-FilePath\s+["\']?[^"\'\s]*(?:%s)\.ps1\b' % locked, seg):
            emit_deny('Запуск скрипта ⛔-скилла (удаление объекта/формы/макета, снятие с поддержки, загрузка DT) — необратимо, модель сама '
                      'его не выполняет (use-skills-not-manual-edits п.9).\nСегмент: %s\nЕсли это осознанное решение — выполни команду сам: '
                      'подтверждение через `ask` в bypassPermissions/auto не гарантировано, поэтому барьер отвечает отказом, а не вопросом.' % seg)

    # Дисциплина команд — по команде без тел heredoc и here-string (там данные, а не вызовы).
    # Сегменты — без разрезов внутри кавычек (`git commit -m "a; python tools/checks/health-check.py"` — текст, а не запуск),
    # плюс команды, которые здесь же исполнит вложенная оболочка или код интерпретатора (inner); удалённая команда (ssh,
    # vm-shell) — нет: дисциплина запуска платформы и проверок касается этой машины, `nohup … &` на сервере — обычная работа.
    cmd = drop_heredoc_bodies(cmd)
    segs_norm = [re.sub(r'\s+', ' ', x).strip() for x in split_outside_quotes(cmd)] + \
        [p for kind, p, _, remote in inner if kind == 'cmd' and p and not remote]

    # Пакетный запуск платформы (designer-batch-runs п.1): 1cv8 отсоединяется от консоли — код возврата пуст,
    # следующий шаг идёт вслепую. Режим берётся из сегмента, а если там его нет (аргументы в переменной) — из всей команды.
    names = onec_vars(cmd)
    for seg in segs_norm:
        mode = onec_mode(seg) or onec_mode(cmd)
        if not mode:
            continue
        if m(r'\b(Start-Process|saps)\b', seg) and (m(ONEC_EXE, seg) or any(('$' + v) in seg.lower() for v in names)):
            if not m(r'(^|\s)-Wait\b', seg) and not (mode == 'tests' and m(r'(^|\s)-PassThru\b', seg)):
                emit_deny('Пакетный запуск 1С через Start-Process без -Wait (designer-batch-runs п.1): процесс уйдёт в фон, код возврата '
                          'и журнал /Out прочитаются до конца операции.\nСегмент: %s\nНужно: Start-Process -FilePath $bin -ArgumentList $арг '
                          '-Wait -PassThru -NoNewWindow, код — из .ExitCode. Исключение — прогон YAXUnit: -PassThru и ожидание файла exitCode.' % seg)
        elif m(LAUNCH_API, seg) and (m(ONEC_EXE, seg) or any(('$' + v) in seg.lower() for v in names)):
            emit_deny('Пакетный запуск 1С кодом интерпретатора или API процессов (designer-batch-runs п.1): subprocess, '
                      'child_process, [Diagnostics.Process]::Start и создание Win32_Process не ждут конца операции и не отдают код '
                      'возврата так, как Start-Process -Wait.\nСегмент: %s\nНужно: Start-Process -FilePath $bin -ArgumentList $арг '
                      '-Wait -PassThru -NoNewWindow, код — из .ExitCode; или скилл db-*.' % seg)
        elif onec_direct(seg, names):
            emit_deny('Пакетный запуск 1С напрямую, не через Start-Process -Wait (designer-batch-runs п.1): 1cv8 отсоединяется от '
                      'консоли, $LASTEXITCODE остаётся пустым, следующий шаг идёт вслепую.\nСегмент: %s\nНужно: Start-Process -FilePath '
                      '$bin -ArgumentList $арг -Wait -PassThru -NoNewWindow (из Bash — через powershell -Command), код — из .ExitCode; '
                      'или скилл db-*.' % seg)

    # Фон — только штатный run_in_background, не `&` внутри команды (designer-batch-runs п.8): оболочка завершается раньше
    # платформы, 1cv8 остаётся сиротой, журнал обрывается. Касается платформы, скриптов скиллов с ней и проверок ядра.
    heavy = (r'db-[a-z-]+|epf-build|epf-dump|erf-build|erf-dump|web-publish|health-check|contour-tests|mcp-smoke|weekly-check|'
             r'pre-publish-audit|release-core|recall-check|build-plugin')
    for seg in segs_norm:
        lit = re.sub(r'\d*>&\d*|&>>?', ' ', strip_literals(seg))
        if m(r'[^\s=({,|;>&]\s*&(?![&>\d])', lit) and (m(r'\b(' + ONEC_EXE + r'|ibcmd(\.exe)?)\b', seg) or runs_script(re.sub(r'\s*&\s*$', '', seg), heavy)):
            emit_deny('Фон через `&` внутри команды (designer-batch-runs п.8): оболочка завершится раньше платформы или скрипта, процесс '
                      'останется сиротой, журнал оборвётся.\nСегмент: %s\nНужно: та же команда без `&` и с run_in_background: true.' % seg)

    # Сообщение коммита — коротким -m, без heredoc и here-string (tool-calls-not-chat-text п.3).
    # Открывающая строка heredoc остаётся в команде: смотрим её саму (`git commit -m "$(cat <<'EOF'`, `cat <<EOF | git commit -F -`).
    # Оператор — вне литерала: `git commit -m "про <<'EOF' в тексте"` — текст сообщения, а не heredoc (30.10.2026).
    if any(m(r'\bgit\s+commit\b', strip_literals(re.sub(r'\bgit\s+-C\s+\S+\s+', 'git ', x, flags=I))) and
           (m(r'(?<!<)<<(?!<)[-~]?\s*["\']?[A-Za-z_]\w*', strip_literals(x)) or m(r'@["\']\s*$', x)) for x in cmd.split('\n')):
        emit_deny('Сообщение коммита через heredoc или here-string (tool-calls-not-chat-text п.3): многострочное тело в вызове ломается '
                  'на кавычках и переводах строк.\nНужно: git commit -m "заголовок" -m "абзац" -m "абзац" — каждый абзац отдельным -m.')

    # Проверки и выпуск — в фоне, наружу только вердикт (run-checks-quietly-in-background п.1).
    if tool_input.get('run_in_background') not in (True, 'true', 'True', 1):
        # recall-check (замер полноты) и сборка плагина с проверкой (build-plugin --validate) — тоже долгие прогоны (30.10.2026)
        checks = r'health-check|contour-tests|mcp-smoke|weekly-check|pre-publish-audit|release-core|recall-check'
        for seg in segs_norm:
            if m(r'(^|\s)(--help|-h|-\?)(\s|$)', seg):
                continue
            if runs_script(seg, checks) or (runs_script(seg, 'build-plugin') and m(r'(^|\s)--validate\b', seg)) or \
                    m(r'^(?:\S*[\\/])?claude(?:\.exe)?\s+plugin\s+(update|install|marketplace\s+update)\b', strip_launcher(strip_env_prefix(seg))):
                emit_deny('Проверка или выпуск запускается не в фоне (run-checks-quietly-in-background п.1): простыня вывода уйдёт в '
                          'чат.\nСегмент: %s\nНужно: та же команда с run_in_background: true, затем прочитать только итог '
                          '(строки «Итог»/FAIL) и отчитаться строкой на чекер.' % seg)


# при сбое самого барьера (волна 2 п.2.11): во входе видна опасная команда — отказ, а не пропуск без проверки
FAIL_CLOSED = (r'\b(ibcmd|1cv8c?(\.exe)?|rac|ras|psql|pg_restore|pg_dump|dropdb|sqlcmd|ssh|scp|sftp)\b|ssh-mcp|'
               r'\brm\s+-\w*[rf]|Remove-Item\b.*-Recurse|\bgit\s+(push\b.*(--force|-f\b)|reset\s+--hard|clean\s+-\w*f)|'
               r'\b(DROP|TRUNCATE)\s+(TABLE|DATABASE)\b|\bformat\s+[a-z]:|' + r'\.env\b|[\\/]\.ssh\b|\bid_(rsa|ed25519)\b|\.pgpass\b')


def crash_verdict(raw_in, e):
    """Причина отказа при сбое самого барьера или None — пропуск с пометкой DEGRADED. Тело-данные heredoc и здесь не
    судится: слово ssh в тексте журнала, который пишется в файл, отказа не даёт; вход не разобрать — судится как есть."""
    seen = raw_in.decode('utf-8', 'replace')
    try:
        d_in = json.loads(seen)
        c_in = d_in['tool_input']['command']
        d_in['tool_input']['command'] = heredoc_view(c_in, str(d_in.get('tool_name') or ''))[0]
        seen = json.dumps(d_in, ensure_ascii=False)
    except Exception:
        pass
    if re.search(FAIL_CLOSED, seen, re.I):
        return ('guard-destructive: внутренняя ошибка барьера (%s), а во входе — опасная команда (база 1С, ssh, удаление, '
                'силовой git или путь к секрету): без проверки не пропускаю. Повтори вызов; не проходит — скажи владельцу.' % e)
    return None


if __name__ == '__main__':
    raw_in = sys.stdin.buffer.read()
    sys.stdin = io.TextIOWrapper(io.BytesIO(raw_in), encoding='utf-8')
    if '--all-reasons' in sys.argv[1:]:   # список всех отказов JSON; сбой — код 1, и мод оставляет отказ
        REASONS = []
        main()
        sys.stdout.buffer.write(json.dumps(REASONS, ensure_ascii=False).encode('utf-8'))
        sys.exit(0)
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # отказ защиты не должен блокировать работу, но и молчать не должен
        why = crash_verdict(raw_in, e)
        if why:
            emit_deny(why)
        sys.stdout.buffer.write(json.dumps({'systemMessage': 'guard-destructive: DEGRADED — внутренняя ошибка, вызов пропущен без '
                                            'проверки: %s' % e}, ensure_ascii=False).encode('utf-8'))
        sys.stdout.flush()
    sys.exit(0)
