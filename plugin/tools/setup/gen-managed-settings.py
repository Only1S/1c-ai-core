r"""gen-managed-settings.py — собрать managed-settings.json организации из канонического списка запретов (Т-1 волны 3, #3).

Управляемые настройки Claude Code — высший уровень: пользователь, проект и локальные настройки их не перебивают
(code.claude.com/docs/en/settings, раздел «Settings precedence»). Этот генератор берёт ЕДИНЫЙ источник запретов
`project-deny.json` (его же ставит connect-project в проект) и добавляет замок каталога плагинов — чтобы запреты ядра
не снимались в проекте и нельзя было подгрузить чужие плагины/моды. Дубля списка запретов нет: один источник.

Запуск:
    python plugin/tools/setup/gen-managed-settings.py [--out <файл>]
        без --out — печать в stdout.

Куда класть результат (система, не агент — ставит владелец):
    Windows:      C:\Program Files\ClaudeCode\managed-settings.json
    macOS:        /Library/Application Support/ClaudeCode/managed-settings.json
    Linux и WSL:  /etc/claude-code/managed-settings.json
Проверка после установки: в Claude Code `/status` → строка «Setting sources» содержит «Enterprise managed settings».

Схема ключей сверена с code.claude.com (settings, managed-settings, plugins/org — 29.10.2026):
    permissions.deny             — запреты, неперебиваемые (управляемый уровень)
    strictKnownMarketplaces      — белый список источников каталогов плагинов ({source:github, repo} и {source:skills-dir})
    disableSideloadFlags         — запрет --plugin-dir/--plugin-url/--agents/--mcp-config (кроме sdk) и CLAUDE_CODE_PLUGIN_DIRS
    disableCommandPluginSources  — запрет плагинов с source=command
`allowManagedPermissionRulesOnly` НЕ ставим: он отбросил бы allow-правила проекта на читающие инструменты серверов ядра.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MARKETPLACE = 'Only1S/1c-ai-core'   # канал ядра (claude plugin install ones-core --marketplace Only1S/1c-ai-core)
OFFICIAL = 'anthropics/claude-plugins-official'


def build():
    deny = json.load(open(os.path.join(HERE, 'project-deny.json'), encoding='utf-8')).get('deny', [])
    return {
        '$schema': 'https://json.schemastore.org/claude-code-settings.json',
        'permissions': {'deny': deny},
        'strictKnownMarketplaces': [
            {'source': 'github', 'repo': OFFICIAL},
            {'source': 'github', 'repo': MARKETPLACE},
            {'source': 'skills-dir'},   # иначе skills-directory плагины перестают грузиться
        ],
        'disableSideloadFlags': True,
        'disableCommandPluginSources': True,
    }


def main():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding='utf-8')
        except Exception:
            pass
    ap = argparse.ArgumentParser(description='Собрать managed-settings.json организации из project-deny.json.')
    ap.add_argument('--out', help='файл результата (без него — stdout)')
    args = ap.parse_args()
    text = json.dumps(build(), ensure_ascii=False, indent=2) + '\n'
    if args.out:
        with open(args.out, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
        print('собрано: %s (положить в системный путь ClaudeCode, см. шапку скрипта)' % args.out)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == '__main__':
    sys.exit(main())
