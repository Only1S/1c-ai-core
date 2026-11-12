"""Влияние обновления на расширения: скилл cfe-update-impact на паре «текущая конфигурация → результат слияния».

Использование:
  python extensions-impact.py --repo <репозиторий слияния> --ext <выгрузка расширения> [--ext …]
                              [--new-rev <ревизия>] [--old-xml <каталог>] [--new-xml <каталог>] [--work <каталог>]

Старая версия — ветка custom: конфигурация, под которую расширения написаны сейчас (с нашими доработками, а не голый
старый релиз). Новая — результат слияния (индекс после git add) или --new-rev. Обе выгружаются без checkout в
<work>/<метка>/old и new; готовые выгрузки можно передать --old-xml / --new-xml (например xml из прогона import-check).
Сверх cfe-update-impact: заимствованный объект или форма (ObjectBelonging=Adopted) без ExtendedConfigurationObject —
ПРОБЛЕМА: после загрузки такая форма молча перестаёт применяться (vendor-release-update, «Расширения»).
Отчёт: <work>/<метка>/extensions-report.md и .json, по каждому расширению — вывод и JSON cfe-update-impact.
Коды: 0 — проблем нет, 1 — есть ПРОБЛЕМА, 2 — неверные аргументы.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from release_xml import dump_info, export_tree, git  # noqa: E402

IMPACT = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'cfe-update-impact', 'scripts', 'cfe-update-impact.py')


def adopted_without_link(ext):
    """Заимствованные объекты, формы и макеты расширения без ExtendedConfigurationObject: [путь]."""
    out = []
    for d, _, fs in os.walk(ext):
        rel = os.path.relpath(d, ext).replace('\\', '/')
        depth = 0 if rel == '.' else rel.count('/') + 1
        if not (depth == 1 or (depth == 3 and os.path.basename(d) in ('Forms', 'Templates'))):
            continue
        for f in fs:
            if not f.lower().endswith('.xml'):
                continue
            t = open(os.path.join(d, f), encoding='utf-8-sig', errors='replace').read(20000)
            props = t.split('</Properties>', 1)[0]
            if '<ObjectBelonging>Adopted</ObjectBelonging>' in props and not re.search(
                    r'<ExtendedConfigurationObject>\s*[0-9a-fA-F-]{36}\s*</ExtendedConfigurationObject>', props):
                out.append((rel + '/' + f).lstrip('./'))
    return sorted(out)


def main():
    ap = argparse.ArgumentParser(description='Влияние обновления на расширения (cfe-update-impact на результате слияния)')
    ap.add_argument('--repo', required=True)
    ap.add_argument('--ext', action='append', required=True, help='выгрузка расширения (можно несколько)')
    ap.add_argument('--new-rev', help='ревизия новой версии вместо индекса')
    ap.add_argument('--old-xml', help='готовая выгрузка текущей конфигурации вместо ветки custom')
    ap.add_argument('--new-xml', help='готовая выгрузка результата слияния вместо индекса')
    ap.add_argument('--work', help='каталог прогонов (по умолчанию <repo>-extensions)')
    a = ap.parse_args()
    repo = os.path.abspath(a.repo)
    exts = [os.path.abspath(e) for e in a.ext]
    bad = [e for e in exts if not os.path.isfile(os.path.join(e, 'Configuration.xml'))]
    if not os.path.isdir(os.path.join(repo, '.git')) or bad or not os.path.isfile(IMPACT):
        print('нужны репозиторий слияния, выгрузки расширений с Configuration.xml и скилл cfe-update-impact (%s); не так: %s' % (
            IMPACT, ', '.join(bad) or (repo if not os.path.isdir(os.path.join(repo, '.git')) else IMPACT)))
        return 2
    run_dir = stem = os.path.join(os.path.abspath(a.work or repo.rstrip(os.sep) + '-extensions'), time.strftime('%Y%m%d-%H%M%S'))
    n_run = 1
    while os.path.exists(run_dir):
        n_run += 1
        run_dir = '%s-%d' % (stem, n_run)
    os.makedirs(run_dir)
    try:
        if not a.new_rev and not a.new_xml:
            unmerged = [l for l in git(repo, 'ls-files', '-u', '-z').split('\0') if '\t' in l]
            if unmerged:
                print('слияние не разрешено (%d путей) — новая версия ещё не готова: resolve-merge.py и ручное разрешение' % len(unmerged))
                return 2
        old = os.path.abspath(a.old_xml) if a.old_xml else os.path.join(run_dir, 'old')
        new = os.path.abspath(a.new_xml) if a.new_xml else os.path.join(run_dir, 'new')
        if not a.old_xml:
            export_tree(repo, 'custom', old)
        if not a.new_xml:
            export_tree(repo, a.new_rev, new)
    except RuntimeError as e:
        print(e)
        return 2
    results, total = [], 0
    for ext in exts:
        name = dump_info(ext).get('name') or os.path.basename(ext)
        js = os.path.join(run_dir, 'ext-%s.json' % name)
        r = subprocess.run([sys.executable, '-B', IMPACT, '-ExtensionPath', ext, '-OldConfigPath', old, '-NewConfigPath', new, '-Json', js],
                           capture_output=True, env=dict(os.environ, PYTHONIOENCODING='utf-8'))
        out = (r.stdout + r.stderr).decode('utf-8', 'replace')
        open(os.path.join(run_dir, 'ext-%s.txt' % name), 'w', encoding='utf-8', newline='\n').write(out)
        data = json.load(open(js, encoding='utf-8')) if os.path.isfile(js) else {}
        problems = [f for f in data.get('findings', []) if f.get('level') == 'ПРОБЛЕМА']
        unlinked = adopted_without_link(ext)
        n = len(problems) + len(unlinked)
        total += n if r.returncode in (0, 1) else 1
        results.append({'extension': name, 'path': ext, 'impact_code': r.returncode, 'problems': len(problems),
                        'summary': data.get('summary', {}), 'adopted_without_link': unlinked,
                        'first_problems': [{'where': f.get('where'), 'message': f.get('message')} for f in problems[:20]],
                        'error': out[-1500:] if r.returncode not in (0, 1) else None})
    json.dump({'repo': repo, 'old': old, 'new': new, 'problems': total, 'extensions': results},
              open(os.path.join(run_dir, 'extensions-report.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    md = ['# Влияние обновления на расширения', '',
          'Старая версия — ветка `custom` (текущая конфигурация), новая — %s. Проблем: **%d**.' % (
              'ревизия ' + a.new_rev if a.new_rev else 'результат слияния', total), '',
          '| Расширение | ПРОБЛЕМА (cfe-update-impact) | Заимствовано без ExtendedConfigurationObject |', '|---|---|---|']
    for x in results:
        md.append('| %s | %s | %d |' % (x['extension'], x['problems'] if x['error'] is None else 'ошибка запуска, код %s' % x['impact_code'],
                                        len(x['adopted_without_link'])))
    for x in results:
        if x['first_problems'] or x['adopted_without_link'] or x['error']:
            md += ['', '## %s' % x['extension'], '']
            md += ['- %s — %s' % (p['where'], p['message']) for p in x['first_problems']]
            md += ['- `%s` — заимствование без ExtendedConfigurationObject: после загрузки молча перестанет применяться; '
                   'заимствовать заново (cfe-borrow) от объекта новой версии' % p for p in x['adopted_without_link']]
            if x['error']:
                md += ['- cfe-update-impact не отработал: `%s`' % x['error'].strip().splitlines()[-1]]
    md += ['', 'Полный вывод по каждому расширению — `ext-<имя>.txt` рядом. Дальше — «Дальше по отчёту» скилла cfe-update-impact, '
           'затем /cfe-validate и проверка применимости на тестовой базе (/db-cfe-admin check).']
    open(os.path.join(run_dir, 'extensions-report.md'), 'w', encoding='utf-8', newline='\n').write('\n'.join(md) + '\n')
    print('расширений %d, проблем %d; отчёт: %s' % (len(results), total, os.path.join(run_dir, 'extensions-report.md')))
    return 1 if total else 0


if __name__ == '__main__':
    sys.exit(main())
