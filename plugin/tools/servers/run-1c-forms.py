"""Запуск MCP-сервера 1c-forms (проверка, схема и сборка управляемых форм 1С).

Сервер ставит установщик в ${CLAUDE_PLUGIN_DATA}/bin/1c-formsserver — одна копия на машину, с окружением Python в её папке.
Порт не нужен: сервер запускает сам Claude Code и говорит с ним через stdin/stdout. Встроенный режим EDT выключен: он написан
под другой API edt-mcp (forms-from-edt-metadata).
"""
import os
import subprocess
import sys

CODE = "from mcp_forms.server import mcp; mcp.run(transport='stdio', show_banner=False)"


def main():
    data = os.environ.get('CLAUDE_PLUGIN_DATA') or ''
    home = os.path.join(data, 'bin', '1c-formsserver')
    py = os.path.join(home, '.venv', 'Scripts', 'python.exe') if os.name == 'nt' else os.path.join(home, '.venv', 'bin', 'python')
    if not os.path.isfile(py):
        sys.stderr.write('1c-forms не установлен: нет %s. Установить программы: python tools/setup/install-tools.py --only 1c-formsserver\n' % py)
        return 1
    env = dict(os.environ, PYTHONPATH=os.path.join(home, 'src'), PYTHONIOENCODING='utf-8', EDT_ENABLED='false',
               DATA_PATH=os.path.join(home, 'data'), EDT_REFERENCE_PATH=os.path.join(home, 'edt_reference'),
               DATABASES_PATH=os.path.join(data, '1c-forms', 'databases'))
    return subprocess.call([py, '-c', CODE], env=env, cwd=home)


if __name__ == '__main__':
    sys.exit(main())
