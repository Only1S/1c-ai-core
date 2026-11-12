"""Выгрузка релиза конфигурации (.cf/.dt) в XML через ibcmd: временная файловая база -> config export.

Использование:
  python dump-release.py --src <релиз.cf|.dt> --out <каталог XML> [--ibcmd <путь>] [--keep-db]

Каталог --out должен быть пустым или отсутствовать. Временная база — рядом с ним (<out>.db), после выгрузки удаляется
(--keep-db оставляет). Печатает имя, поставщика, версию конфигурации и версию формата выгрузки. Коды: 0 — выгружено,
1 — ошибка ibcmd, 2 — неверные аргументы.
"""
import argparse
import os
import shutil
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from release_xml import dump_info, find_ibcmd  # noqa: E402


def run(ibcmd, args):
    r = subprocess.run([ibcmd] + args, capture_output=True)
    return r.returncode, (r.stdout + r.stderr).decode('utf-8', 'replace').strip()


def main():
    ap = argparse.ArgumentParser(description='Выгрузка релиза .cf/.dt в XML через временную базу ibcmd')
    ap.add_argument('--src', required=True, help='полный файл релиза: .cf или .dt (файл обновления .cfu не подходит)')
    ap.add_argument('--out', required=True, help='каталог XML-выгрузки (пустой или отсутствует)')
    ap.add_argument('--ibcmd', help='путь к ibcmd.exe или каталогу bin платформы')
    ap.add_argument('--keep-db', action='store_true', help='не удалять временную базу (нужна для проверки модулей)')
    a = ap.parse_args()
    src, out = os.path.abspath(a.src), os.path.abspath(a.out)
    ext = os.path.splitext(src)[1].lower()
    if not os.path.isfile(src) or ext not in ('.cf', '.dt'):
        print('нужен полный файл релиза .cf или .dt: %s' % src)
        return 2
    if os.path.isdir(out) and os.listdir(out):
        print('каталог выгрузки не пуст: %s — укажите новый, чтобы выгрузки не смешались' % out)
        return 2
    ibcmd = find_ibcmd(a.ibcmd)
    if not ibcmd:
        print('ibcmd.exe не найден: укажите --ibcmd, ONEC_PLATFORM_BIN или v8path в .v8-project.json')
        return 2
    tmp = out.rstrip(os.sep) + '.db'
    if os.path.exists(tmp):
        print('временный каталог уже есть: %s — удалите его или выберите другой --out' % tmp)
        return 2
    data, db = os.path.join(tmp, 'data'), os.path.join(tmp, 'db')
    t0 = time.time()
    load = ['--load=' + src] if ext == '.cf' else ['--restore=' + src]
    code, msg = run(ibcmd, ['infobase', 'create', '--data=' + data, '--db-path=' + db, '--create-database'] + load)
    if code:
        print('ibcmd infobase create: код %d\n%s' % (code, msg[-1500:]))
        return 1
    t1 = time.time()
    os.makedirs(out, exist_ok=True)
    code, msg = run(ibcmd, ['config', 'export', '--data=' + data, '--db-path=' + db, out])
    if code:
        print('ibcmd config export: код %d\n%s' % (code, msg[-1500:]))
        return 1
    t2 = time.time()
    if not a.keep_db:
        shutil.rmtree(tmp, ignore_errors=True)
    files = sum(len(fs) for _, _, fs in os.walk(out))
    info = dump_info(out)
    print('выгружено: %s' % out)
    print('  конфигурация: %s, поставщик: %s, версия %s; формат выгрузки %s' % (
        info.get('name', '?'), info.get('vendor', '?'), info.get('version', '?'), info.get('format', '?')))
    print('  файлов: %d; загрузка в базу %d с, выгрузка %d с%s' % (
        files, t1 - t0, t2 - t1, '; база оставлена: ' + db if a.keep_db else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
