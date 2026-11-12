"""Запуск MCP-сервера bsl-context (справка и проверка выражений по API платформы 1С) через стандартные потоки.

Сервер ставит установщик в ${CLAUDE_PLUGIN_DATA}/bin/bsl-context. Ему нужен каталог установки платформы
(C:/Program Files/1cv8/<версия>), а переменная проекта ONEC_PLATFORM_BIN указывает на его папку bin — берём родителя.
Порт не нужен: сервер запускает сам Claude Code и говорит с ним через stdin/stdout.

Источник имён конфигурации (с 17.10.2026): если у проекта задан ONEC_PROJECT_SRC и в нём есть индекс code-index
(<исходники>/.code-index/index.db), рядом с данными плагина пишется config.toml с [symbol_source] kind=code_index_db и
root=исходники — без root validate_module с path= отвечает отказом (живая проба в проекте). Алиас источника у сервера —
"default": validate_module и rebuild_symbol_index вызываются с repo="default". Индекса нет — только справка платформы.
"""
import hashlib
import os
import subprocess
import sys


def build_config(src, plat, data):
    """Путь к config.toml с источником имён на исходники проекта; None — источника нет (нет исходников или индекса)."""
    src = (src or '').rstrip('\\/')
    db = os.path.join(src, '.code-index', 'index.db') if src else ''
    if not db or not os.path.isfile(db) or "'" in src or "'" in plat:
        return None
    folder = os.path.join(data or os.path.dirname(os.path.abspath(__file__)), 'bsl-context')
    os.makedirs(folder, exist_ok=True)
    cfg = os.path.join(folder, 'config-%s.toml' % hashlib.sha1(src.lower().encode('utf-8')).hexdigest()[:10])
    text = ("# создаётся run-bsl-context.py при каждом запуске — правка вручную будет перезаписана\n"
            "platform_path = '%s'\n\n[symbol_source]\nkind = \"code_index_db\"\nroot = '%s'\ndb_path = '%s'\n" % (plat, src, db))
    with open(cfg, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)
    return cfg


def main():
    data = os.environ.get('CLAUDE_PLUGIN_DATA') or ''
    exe = os.path.join(data, 'bin', 'bsl-context', 'bsl-context-rs.exe')
    if not os.path.isfile(exe):
        sys.stderr.write('bsl-context не установлен: нет %s. Установить программы: python tools/setup/install-tools.py (из папки плагина)\n' % exe)
        return 1
    plat = (os.environ.get('ONEC_PLATFORM_BIN') or '').rstrip('\\/')
    if not plat:
        sys.stderr.write('Не задана ONEC_PLATFORM_BIN — путь к папке bin платформы 1С в настройках проекта (.claude/settings.local.json, блок env)\n')
        return 1
    if os.path.basename(plat).lower() == 'bin':
        plat = os.path.dirname(plat)
    cfg = None
    try:
        cfg = build_config(os.environ.get('ONEC_PROJECT_SRC'), plat, data)
    except OSError as e:   # источник имён — улучшение, а не условие запуска: без него остаётся справка платформы
        sys.stderr.write('bsl-context: источник имён не настроен (%s) — проверка только по справке платформы\n' % e)
    return subprocess.call([exe, '--transport', 'stdio', '--platform-path', plat] + (['--config', cfg] if cfg else []) + sys.argv[1:])


if __name__ == '__main__':
    sys.exit(main())
