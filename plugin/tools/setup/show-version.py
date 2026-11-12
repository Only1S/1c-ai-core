"""Версия плагина ones-core в проекте: какая работает в этой сессии, какая установлена для проекта и какая последняя в канале.

Использование (команда /ones-core:version):
  python show-version.py [--project <папка проекта>] [--offline]

Работающая версия — из манифеста папки плагина, из которой запущен скрипт; установленная — запись проекта в
~/.claude/plugins/installed_plugins.json; последняя в канале — теги core-v* на GitHub (git ls-remote), а без сети или с
--offline — версия в локальной копии каталога ~/.claude/plugins/marketplaces/ones-core. Код 0 — отчёт выдан, 2 — нет
манифеста плагина. Ничего не меняет.
"""
import argparse
import json
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
HOME_PLUGINS = os.path.join(os.path.expanduser('~'), '.claude', 'plugins')
PLUGIN_ID = 'ones-core@ones-core'


def vtuple(v):
    m = re.match(r'^\D*(\d+)\.(\d+)\.(\d+)', v or '')
    return tuple(int(x) for x in m.groups()) if m else None


def manifest_version(root):
    p = os.path.join(root, '.claude-plugin', 'plugin.json')
    try:
        return json.load(open(p, encoding='utf-8-sig')).get('version')
    except (OSError, ValueError):
        return None


def installed_version(path, project):
    try:
        rows = json.load(open(path, encoding='utf-8-sig')).get('plugins', {}).get(PLUGIN_ID, [])
    except (OSError, ValueError):
        return None
    want = os.path.normcase(os.path.abspath(project))
    for e in rows:
        if e.get('projectPath') and os.path.normcase(os.path.abspath(e['projectPath'])) == want:
            return e.get('version')
    return None


def channel_version(mkt, offline):
    """(версия, откуда): теги GitHub, иначе локальная копия каталога."""
    if not offline:
        url = None
        try:
            url = subprocess.run(['git', '-C', mkt, 'remote', 'get-url', 'origin'], capture_output=True, timeout=15).stdout.decode().strip()
        except (OSError, subprocess.SubprocessError):
            pass
        if url:
            try:
                r = subprocess.run(['git', 'ls-remote', '--tags', '--refs', url, 'core-v*'], capture_output=True, timeout=30)
                tags = [ln.rsplit('/', 1)[-1] for ln in r.stdout.decode('utf-8', 'replace').splitlines() if 'refs/tags/' in ln]
                best = max((t for t in tags if vtuple(t)), key=vtuple, default=None)
                if best:
                    return best.replace('core-v', ''), 'по GitHub'
            except (OSError, subprocess.SubprocessError):
                pass
    v = manifest_version(os.path.join(mkt, 'plugin'))
    if v:
        return v, 'по локальной копии каталога, GitHub не спрашивали'
    return None, None


def main():
    ap = argparse.ArgumentParser(description='Версия плагина ones-core: работает, установлена, последняя в канале')
    ap.add_argument('--project', default=os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd())
    ap.add_argument('--plugin-root', default=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    ap.add_argument('--installed-json', default=os.path.join(HOME_PLUGINS, 'installed_plugins.json'))
    ap.add_argument('--marketplace-dir', default=os.path.join(HOME_PLUGINS, 'marketplaces', 'ones-core'))
    ap.add_argument('--offline', action='store_true', help='не спрашивать GitHub, взять версию из локальной копии каталога')
    a = ap.parse_args()
    running = manifest_version(a.plugin_root)
    if not running:
        print('Не найден манифест плагина в %s — версию определить нельзя.' % a.plugin_root)
        return 2
    in_cache = os.path.normcase(os.path.abspath(a.plugin_root)).startswith(os.path.normcase(os.path.join(HOME_PLUGINS, 'cache')))
    installed = installed_version(a.installed_json, a.project)
    channel, source = channel_version(a.marketplace_dir, a.offline)
    print('ones-core в проекте %s' % os.path.basename(os.path.abspath(a.project)))
    print('  работает в этой сессии: %s%s' % (running, '' if in_cache or a.plugin_root != ap.get_default('plugin_root') else
                                              ' (папка-исходник, не установленный выпуск — номер в манифесте условный)'))
    print('  установлена в проекте:  %s' % (installed or 'не установлен в этом проекте'))
    print('  последняя в канале:     %s' % ('%s (%s)' % (channel, source) if channel else 'не удалось узнать'))
    rt, it, ct = vtuple(running), vtuple(installed), vtuple(channel)
    if not installed:
        print('Итог: плагин ones-core не установлен в этом проекте — подключение: claude plugin install ones-core '
              '--marketplace Only1S/1c-ai-core --scope project, затем /ones-core:setup.')
    elif it and rt and it > rt:
        print('Итог: установлена %s, а сессия работает на %s — перезапустите Claude Code, чтобы подхватить новую версию.' % (installed, running))
    elif ct and it and ct > it:
        print('Итог: доступна %s — обновите:' % channel)
        print('  claude plugin marketplace update ones-core')
        print('  claude plugin update ones-core@ones-core --scope project')
        print('  затем перезапустите Claude Code.')
    elif ct:
        print('Итог: версия актуальна.')
    else:
        print('Итог: последнюю версию в канале узнать не удалось — проверьте доступ к GitHub или обновите каталог: '
              'claude plugin marketplace update ones-core.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
