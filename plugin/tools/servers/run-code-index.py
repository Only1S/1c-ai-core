"""Запуск MCP-сервера code-index (поиск по коду выгрузки 1С) через стандартные потоки.

Сервер ставит установщик в ${CLAUDE_PLUGIN_DATA}/bin/code-index; индекс ведёт общий фоновый индексатор (ADR-0006),
сервер его только читает. Выгрузка — переменная проекта ONEC_PROJECT_SRC. Без неё сервер не запускается и говорит
почему: раньше «${ONEC_PROJECT_SRC}» из .mcp.json доходил до программы буквально, и она молча отвечала пустым индексом,
заводя в корне проекта папку с таким именем.
"""
import os
import subprocess
import sys


def say(text):
    sys.stderr.buffer.write((text + chr(10)).encode('utf-8'))
    sys.stderr.flush()


def main():
    data = os.environ.get('CLAUDE_PLUGIN_DATA') or ''
    exe = os.path.join(data, 'bin', 'code-index', 'bsl-indexer.exe')
    if not os.path.isfile(exe):
        say('code-index не установлен: нет %s. Установить программы: python tools/setup/install-tools.py (из папки плагина)' % exe)
        return 1
    src = (os.environ.get('ONEC_PROJECT_SRC') or '').strip()
    if not src or '${' in src:
        say('Не задана ONEC_PROJECT_SRC — путь к выгрузке конфигурации в настройках проекта '
            '(.claude/settings.local.json, блок env); задаёт /ones-core:setup')
        return 1
    if not os.path.isdir(src):
        say('Папки выгрузки нет: %s (ONEC_PROJECT_SRC в .claude/settings.local.json)' % src)
        return 1
    env = dict(os.environ)
    env.setdefault('CODE_INDEX_HOME', os.path.join(data, 'code-index'))
    return subprocess.call([exe, 'serve', '--path', src] + sys.argv[1:], env=env)


if __name__ == '__main__':
    sys.exit(main())
