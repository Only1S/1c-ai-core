#!/usr/bin/env python3
"""Взвод гейта конца хода по файлам 1С, записанным командой оболочки (по мотивам Romandredan/1c-quality-gate, MIT).

У команды Bash/PowerShell нет аргумента «файл»: модуль, записанный генератором, скриптом или `git apply`, гейт stop-guard не
видел (10.11.2026 конвертер записал 14 тыс. строк BSL — гейт заметил только модуль, правленный инструментом). Поэтому:

- PreToolUse: время старта команды и её ключ (stop-guard.cmd_key); фоновой команде — подсказка: её запись хук не увидит;
- PostToolUse / PostToolUseFailure: `git status` рабочих деревьев (stop-guard.work_tops) — файлы 1С (stop-guard.is_1c),
  изменённые или новые и записанные не раньше старта команды, — в logs/shell-arm.json по сессии. Игнорируемые git файлы
  в `status` не попадают; грязный до команды и ею не тронутый файл отсекается временем записи.

stop-guard требует для них те же проверки, что для правки инструментом (до 5 модулей — validate_module по каждому, больше —
пакетная проверка). Любой сбой хука — пропуск (код 0): гейт не должен мешать работе из-за своей поломки; но не молча —
systemMessage с пометкой DEGRADED (контракт деградации, с 20.11.2026), в том числе когда git status дерева не ответил.
"""
import importlib.util
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SHELL_STATE = os.path.join('logs', 'shell-arm.json')   # путь состояния от корня проекта; stop-guard берёт его отсюда
PENDING_TTL = 6 * 3600     # незавершённые записи старше — выбрасываются
ROWS_MAX = 400             # записей взвода на сессию
GIT = ['git', '--no-optional-locks', '-c', 'core.quotepath=off']   # без записи .git/index: не спорим за блокировку с git агента
# Сроки git: в сумме меньше таймаута хука в hooks.json (30 с), иначе Claude Code снимет хук раньше, чем он назовёт сбой
GIT_TOP_TIMEOUT = 5
GIT_STATUS_TIMEOUT = 15
REPLACE_TRIES = 20         # подмена файла состояния: до ~1 с, пока другой процесс держит его открытым
# Проверки ядра идут в фоне по правилу run-checks-quietly-in-background и исходники 1С проекта не пишут: подсказка им — шум.
QUIET_BACKGROUND = re.compile(r'(health-check|contour-tests|mcp-smoke|weekly-check|release-core|build-plugin|run-tests|'
                              r'run-scenario|plugin-eval|gen-doc-index|gen-contour-registry)\.py\b', re.I)
BACKGROUND_HINT = ('shell-arm: команда запущена в фоне — файлы 1С, которые она запишет, гейт конца хода не увидит. '
                   'Если она пишет исходники 1С, запусти её без фона или проверь записанное (validate_module по модулям, '
                   'bsl-analyzer analyze по папке).')


def cmd_key(cmd):
    """Ключ команды оболочки: им гейт конца хода (stop-guard) связывает записанные командой файлы 1С с вызовом в журнале хода.
    Определение одно — здесь: до команды хук не грузит stop-guard (замер 11.11.2026, ~35 мс на каждом вызове оболочки)."""
    import hashlib
    return hashlib.sha256(str(cmd or '').strip().encode('utf-8')).hexdigest()[:16]


def load_sg():
    spec = importlib.util.spec_from_file_location('stop_guard_for_shell_arm', os.path.join(HERE, 'stop-guard.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


TIMEOUT = object()   # git не ответил в срок — в отличие от None (ненулевой код: не репозиторий и т. п.)


def run_all(argvs, timeout=60):
    """Команды git параллельно (у тяжёлого проекта пять деревьев по ~0,2 с — последовательно было бы секунду на каждый вызов).
    Срок общий на все команды, а не на каждую: ожидания по деревьям не складываются."""
    procs = [subprocess.Popen(a, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) for a in argvs]
    end = time.monotonic() + timeout
    out = []
    for p in procs:
        try:
            data, _ = p.communicate(timeout=max(0.1, end - time.monotonic()))
            out.append(data if p.returncode == 0 else None)
        except subprocess.TimeoutExpired:
            p.kill()
            out.append(TIMEOUT)
    return out


def parse_porcelain(raw):
    """Изменённые и новые файлы дерева из `status --porcelain -z` (игнорируемые git не входят): относительные пути."""
    parts = raw.decode('utf-8', 'replace').split(chr(0))
    out, k = [], 0
    while k < len(parts):
        e = parts[k]
        k += 1
        if len(e) < 4:
            continue
        out.append(e[3:])
        if e[0] in 'RC':          # переименование: следующий элемент — старый путь
            k += 1
    return out


def tops_of(sg, root):
    """(деревья git рабочих папок, папки, где git не ответил в срок)."""
    dirs = []
    for t in sg.work_tops(root):
        p = t if os.path.isdir(t) else os.path.dirname(t)
        if os.path.isdir(p) and p not in dirs:
            dirs.append(p)
    seen, lost = [], []
    for p, r in zip(dirs, run_all([GIT + ['-C', p, 'rev-parse', '--show-toplevel'] for p in dirs], timeout=GIT_TOP_TIMEOUT)):
        if r is TIMEOUT:
            lost.append(p)
            continue
        top = r.decode('utf-8', 'replace').strip() if r else ''
        if top and top not in seen:
            seen.append(top)
    return seen, lost


def written_1c(sg, root, t0):
    """Файлы 1С рабочих деревьев, изменённые или новые и записанные не раньше t0: (абсолютные пути, деревья, где git status
    не ответил)."""
    gs = sg.guard_skills()
    tops, lost = tops_of(sg, root)
    raws = run_all([GIT + ['-C', t, 'status', '--porcelain', '-z', '--untracked-files=all'] for t in tops],
                   timeout=GIT_STATUS_TIMEOUT)
    files = []
    lost += [top for top, raw in zip(tops, raws) if raw is None or raw is TIMEOUT]
    for top, raw in zip(tops, raws):
        for rel in parse_porcelain(raw) if raw is not None and raw is not TIMEOUT else []:
            full = os.path.join(top, rel)
            if not sg.is_1c(sg.norm(full), gs):
                continue
            try:
                if os.path.isfile(full) and os.stat(full).st_mtime >= t0:
                    files.append(full.replace('\\', '/'))
            except OSError:
                continue
    return sorted(set(files)), lost


def load_state(path):
    try:
        with open(path, encoding='utf-8-sig') as f:
            st = json.load(f)
        return st if isinstance(st, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(path, st):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.%d.tmp' % os.getpid()
    with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(st, f, ensure_ascii=False, indent=0)
    replace_retry(tmp, path)


def replace_retry(tmp, path):
    """os.replace с повтором: на Windows файл, открытый другим процессом (stop-guard читает состояние на Stop), подменить
    нельзя, пока его не закроют (PermissionError). Не вышло за все попытки — tmp убирается, ошибка поднимается."""
    try:
        for k in range(REPLACE_TRIES):
            try:
                os.replace(tmp, path)
                return
            except PermissionError:
                if k + 1 == REPLACE_TRIES:
                    raise
                time.sleep(0.05)
    except OSError:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def update_state(path, change):
    """Чтение-правка-запись под замком: параллельные команды одного ответа не теряют записи друг друга."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lock, fd = path + '.lock', None
    for _ in range(100):                      # до ~5 с
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(lock) > 30:   # замок упавшего процесса
                    os.remove(lock)
                    continue
            except OSError:
                pass
            time.sleep(0.05)
    try:
        st = load_state(path)
        out = change(st)
        save_state(path, st)
        return out
    finally:
        if fd is not None:
            os.close(fd)
            try:
                os.remove(lock)
            except OSError:
                pass


def main():
    raw = sys.stdin.buffer.read().decode('utf-8', 'replace').lstrip('\ufeff')
    data = json.loads(raw) if raw.strip() else {}
    if not isinstance(data, dict) or data.get('tool_name') not in ('Bash', 'PowerShell'):
        return 0
    root = os.environ.get('CLAUDE_PROJECT_DIR') or str(data.get('cwd') or '')
    tid = str(data.get('tool_use_id') or '')
    sid = str(data.get('session_id') or '') or 'nosession'
    if not root or not tid:
        return 0
    event = str(data.get('hook_event_name') or '')
    inp = data.get('tool_input') or {}
    path = os.path.join(root, SHELL_STATE)
    if event == 'PreToolUse':
        now = time.time()
        entry = {'t0': now, 'cmd': cmd_key(str(inp.get('command') or '')), 'sid': sid}

        def remember(st):
            pend = {k: v for k, v in (st.get('_pending') or {}).items()
                    if isinstance(v, dict) and now - float(v.get('t0') or 0) < PENDING_TTL}
            pend[tid] = entry
            st['_pending'] = pend
        update_state(path, remember)
        if inp.get('run_in_background') and not QUIET_BACKGROUND.search(str(inp.get('command') or '')):
            sys.stdout.buffer.write(json.dumps({'hookSpecificOutput': {
                'hookEventName': 'PreToolUse', 'additionalContext': BACKGROUND_HINT}}, ensure_ascii=False).encode('utf-8'))
        return 0
    if event not in ('PostToolUse', 'PostToolUseFailure'):
        return 0
    pend = update_state(path, lambda st: (st.get('_pending') or {}).pop(tid, None))
    if not isinstance(pend, dict):
        return 0
    files, lost = written_1c(load_sg(), root, float(pend.get('t0') or 0))      # долгий git status — вне замка
    if files:
        def arm(st):
            rec = st.setdefault(sid, {})
            rows = rec.get('armed') if isinstance(rec.get('armed'), list) else []
            rows.append({'cmd': pend.get('cmd'), 'files': files, 'ts': time.time()})
            rec['armed'] = rows[-ROWS_MAX:]
        update_state(path, arm)
    if lost:
        raise RuntimeError('git status не ответил (ошибка или срок %d с): %s' % (GIT_STATUS_TIMEOUT, ', '.join(lost)))
    return 0


if __name__ == '__main__':
    try:
        code = main()
    except Exception as e:
        sys.stdout.buffer.write(json.dumps({'systemMessage': 'shell-arm: DEGRADED — внутренняя ошибка, запись файлов 1С командой '
                                            'не проверена: %s' % e}, ensure_ascii=False).encode('utf-8'))
        sys.stdout.flush()
        code = 0
    sys.exit(code)
