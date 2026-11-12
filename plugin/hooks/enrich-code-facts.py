"""PreToolUse на Grep: подмешать факты из индекса кода (code-index), ничего не запрещая.

Перенос enrich-code-facts.ps1 на Python (ADR-0002); сверяется проверками contour-tests (раздел 12).
Когда поиск идёт по «чистому» имени (не регулярному выражению), хук спрашивает индекс и отдаёт найденные
процедуры и функции через additionalContext — это точнее сырого поиска по тексту. Grep выполняется в любом случае.
Ограничители цены (запуск индексатора ~0,3 с): только чистое имя; только если индекс существует; одна и та же
подсказка — один раз за сессию; таймаут 5 с. Любая ошибка, пустой результат, нет индекса — молчание.
Где индексатор: в плагине — ${CLAUDE_PLUGIN_DATA}/bin/code-index/bsl-indexer.exe; без плагина (в мастере ядра) —
та же стандартная папка данных плагина в профиле пользователя, затем прежний tools/code-index/bsl-indexer.exe.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import time


def temp_dir():
    """Папка временных файлов, как tempfile.gettempdir(), но без импорта tempfile: он тянет shutil и random — около 50 мс
    на каждом вызове частого хука (замер 11.11.2026). Порядок переменных — как у tempfile; нет ни одной — сам tempfile."""
    for k in ('TMPDIR', 'TEMP', 'TMP'):
        d = os.environ.get(k)
        if d and os.path.isdir(d) and os.access(d, os.W_OK):
            return os.path.abspath(d)
    import tempfile
    return tempfile.gettempdir()


def plugin_data():
    """Папка данных плагина: из переменной плагина, иначе стандартная в профиле пользователя (мастер ядра работает без плагина)."""
    return os.environ.get('CLAUDE_PLUGIN_DATA') or os.path.join(os.path.expanduser('~'), '.claude', 'plugins', 'data', 'ones-core-ones-core')


def indexer_path(root):
    p = os.path.join(plugin_data(), 'bin', 'code-index', 'bsl-indexer.exe')
    if os.path.isfile(p):
        return p
    return os.path.join(root, 'tools', 'code-index', 'bsl-indexer.exe')


def main():
    raw = sys.stdin.buffer.read().decode('utf-8', 'replace').lstrip('\ufeff')
    if not raw.strip():
        return
    data = json.loads(raw)
    pattern = str((data.get('tool_input') or {}).get('pattern') or '')
    if not pattern.strip() or not re.match(r'^[^\W\d][\w]{3,63}$', pattern):
        return
    root = os.environ.get('CLAUDE_PROJECT_DIR') or str(data.get('cwd') or '')
    if not root.strip():
        return
    # Где индекс: корень проекта, затем исходники из манифеста (ONEC_PROJECT_SRC, затем ONEC_PROJECT_SRC_<имя> по имени).
    cands = [root]
    if os.environ.get('ONEC_PROJECT_SRC'):
        cands.append(os.environ['ONEC_PROJECT_SRC'])
    cands += [v for k, v in sorted(os.environ.items()) if k.upper().startswith('ONEC_PROJECT_SRC_')]
    src = next((c for c in cands if c and os.path.isfile(os.path.join(c, '.code-index', 'index.db'))), None)
    if not src:
        return
    exe = indexer_path(root)
    if not os.path.isfile(exe):
        return
    sid = str(data.get('session_id') or '') or 'nosid'
    key = hashlib.sha1(('%s|%s' % (sid, pattern)).encode('utf-8')).hexdigest().upper()[:16]
    mark = os.path.join(temp_dir(), 'cc-enrich-%s.mark' % key)
    if os.path.exists(mark):
        return
    try:
        res = subprocess.run([exe, 'query', pattern, '--path', src, '--json'], capture_output=True, timeout=5)
    except subprocess.TimeoutExpired:
        return
    open(mark, 'w').close()
    # метки старше суток — убрать (ревизия Р-32: копились во TEMP без конца)
    tmp, now = temp_dir(), time.time()
    for name in os.listdir(tmp):
        if name.startswith('cc-enrich-'):
            p = os.path.join(tmp, name)
            try:
                if now - os.path.getmtime(p) > 86400:
                    os.remove(p)
            except OSError:
                pass
    out = res.stdout.decode('utf-8-sig', 'replace').strip()
    if not out:
        return
    fns = (json.loads(out).get('functions')) or []
    if not fns:
        return
    lines = []
    for f in fns[:5]:
        sig = f.get('args') or ''
        lines.append('  %s%s  строки %s-%s' % (f.get('name'), sig, f.get('line_start'), f.get('line_end')))
    if len(fns) > 5:
        lines.append('  ... ещё %d' % (len(fns) - 5))
    text = '\n'.join([
        "[code-index] Символ '%s' есть в индексе — вот факты (сырой Grep их не даёт):" % pattern,
        '\n'.join(lines),
        'Дальше точнее: get_callers / get_call_tree (кто вызывает), get_file_summary (карта файла), grep_body (поиск в телах). '
        'Индекс отражает состояние на момент индексации.'])
    payload = {'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'additionalContext': text}}
    sys.stdout.buffer.write(json.dumps(payload, ensure_ascii=False).encode('utf-8'))
    sys.stdout.flush()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
