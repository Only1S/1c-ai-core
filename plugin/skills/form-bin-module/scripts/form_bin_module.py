#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""form-bin-module — модули ОБЫЧНЫХ форм 1С из Form.bin выгрузки Конфигуратора. ТОЛЬКО ЧТЕНИЕ.

В выгрузке DumpConfigToFiles (и epf-dump) у обычной формы нет отдельного .bsl: модуль лежит
внутри бинарного контейнера <...>/Ext/Form.bin (внутренние файлы `form` и `module`). Скрипт
складывает тексты модулей в ПАРАЛЛЕЛЬНОЕ дерево вне выгрузки — там их видят Grep, code-index,
BSL LS и ревью. Раскладка вывода: <out>/<...>/Ext/Module.bsl — НЕ раскладка управляемой формы
(Ext/Form/Module.bsl): по ней анализатор считает модуль управляемой формой и сыплет ложными
CompilationDirectiveLost/UnavailableInEnvironment (у обычной формы толстый клиент, директив нет).
Исходная выгрузка открывается только на чтение; обратной записи в Form.bin нет и не будет
(формат контейнера формы не документирован — риск порчи).

Режимы:
    extract <src> --out <dir> [--json <отчёт.json>]   извлечь (пишется только изменившееся)
    report  <src> [--out <dir>] [--json <отчёт.json>] посчитать; с --out — сверить зеркало

Код возврата: 0 — без ошибок разбора; 1 — есть формы, модуль которых не извлёкся; 2 — ошибка аргументов.

По мотивам Caponid/1c-form-tools (extract_form_modules.py), лицензия MIT. Идея (Form.bin →
внутренний файл `module` через библиотеку v8unpack) — оттуда; отличия этого порта:
контейнер читается в памяти, без временных каталогов; вывод — только в отдельный каталог,
не рядом с Form.bin; переводы строк нормализуются в CRLF без дублирования CR (в оригинале
CRLF превращался в CRCRLF — issue #1 репозитория); сверка зеркала и сироты; обратной упаковки нет.
Проверено на v8unpack 1.2.6 (использует её внутренний API: detect_format, Container.files).

Лицензия исходного кода, на мотивах которого написан порт:

    MIT License

    Copyright (c) 2025 Caponid

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.
"""

import argparse
import io
import json
import os
import sys

try:
    from v8unpack.container_reader import detect_format
except ImportError:
    sys.stderr.write("ОШИБКА: нужна Python-библиотека v8unpack (pip install v8unpack)\n")
    sys.exit(2)

SIG32 = b'\xFF\xFF\xFF\x7F'   # контейнер 1С
SIG64 = b'\xFF' * 8           # 64-битный вариант контейнера (так его различает v8unpack)
BOM = b'\xEF\xBB\xBF'
MAX_ERRORS_SHOWN = 20


def _prefixed(p):
    """Абсолютный путь с префиксом \\\\?\\ (UNC — \\\\?\\UNC\\), чтобы Windows не резала пути длиннее 260."""
    if p.startswith('\\\\?\\'):
        return p
    return '\\\\?\\UNC\\' + p[2:] if p.startswith('\\\\') else '\\\\?\\' + p


def _long(path):
    """Длинный путь Windows (>260) — через префикс \\\\?\\ (глубокие кириллические деревья выгрузки)."""
    p = os.path.abspath(path)
    if os.name == 'nt' and len(p) >= 240:
        return _prefixed(p)
    return p


def _walk(root, errs):
    """os.walk с префиксом длинного пути и учётом ошибок обхода.

    Без префикса и onerror os.walk молча пропускает каталоги длиннее 260 символов —
    формы выпадают, а отчёт показывает «ошибок разбора: 0». Отдаёт пути без префикса.
    """
    base = os.path.abspath(root)
    wroot = _prefixed(base) if os.name == 'nt' else base

    def onerror(e):
        errs.append({'form_bin': str(getattr(e, 'filename', '?')),
                     'error': f'обход каталога: {type(e).__name__}: {e}'})

    for dirpath, dirnames, filenames in os.walk(wroot, onerror=onerror):
        dirnames.sort()
        yield base + dirpath[len(wroot):], dirnames, filenames


def _module_bytes(data):
    """Внутренний файл `module` контейнера (поиск и во вложенных контейнерах) или None."""
    bio = io.BytesIO(data)
    container = detect_format(bio, 0)
    container.read(bio, 0)
    nested = []
    for name, entry in container.files.items():
        chunk = b''.join(entry.data)
        if len(chunk) != entry.size:
            raise ValueError(f"усечённые данные '{name}': {len(chunk)} из {entry.size} байт")
        if name == 'module':
            return chunk
        if chunk[:4] == SIG32 or chunk[:8] == SIG64:
            nested.append(chunk)
    for chunk in nested:
        found = _module_bytes(chunk)
        if found is not None:
            return found
    return None


def read_form_module(bin_path):
    """(статус, байты модуля в UTF-8 BOM + CRLF | None, текст ошибки | None).

    Статусы: ok — модуль есть; empty — модуль пустой; absent — файла `module` нет; error.
    """
    with open(_long(bin_path), 'rb') as f:
        data = f.read()
    if not (data.startswith(SIG32) or data.startswith(SIG64)):
        return 'error', None, f'не контейнер 1С: сигнатура {data[:8].hex(" ")}'
    try:
        raw = _module_bytes(data)
    except Exception as e:  # формат недокументирован: любой сбой разбора — ошибка формы, не всего прогона
        return 'error', None, f'ошибка разбора контейнера: {type(e).__name__}: {e}'
    if raw is None:
        return 'absent', None, None
    try:
        text = raw[len(BOM):].decode('utf-8') if raw.startswith(BOM) else raw.decode('utf-8')
    except UnicodeDecodeError as e:
        return 'error', None, f'модуль не в UTF-8 (зашифрован или иной формат?): {e}'
    if not text.strip():
        return 'empty', None, None
    # CRLF → LF → CRLF: одиночные CR не трогаем, CRCRLF не возникает
    return 'ok', BOM + text.replace('\r\n', '\n').replace('\n', '\r\n').encode('utf-8'), None


def iter_form_bins(src, errs):
    for dirpath, _, filenames in _walk(src, errs):
        for fn in sorted(filenames):
            if fn.lower() == 'form.bin':
                yield os.path.join(dirpath, fn)


def mirror_path(out, src, bin_path):
    """<src>/<...>/Ext/Form.bin → <out>/<...>/Ext/Module.bsl."""
    return os.path.join(out, os.path.relpath(os.path.dirname(bin_path), src), 'Module.bsl')


def _read_or_none(path):
    try:
        with open(_long(path), 'rb') as f:
            return f.read()
    except FileNotFoundError:
        return None


def run(src, out, write):
    st = {'forms': 0, 'modules': 0, 'empty': 0, 'absent': 0, 'errors': [],
          'written': 0, 'unchanged': 0, 'actual': 0, 'stale': 0, 'missing': 0, 'orphans': []}
    expected = set()
    for bin_path in iter_form_bins(src, st['errors']):
        st['forms'] += 1
        rel = os.path.relpath(bin_path, src)
        status, payload, err = read_form_module(bin_path)
        if status == 'error':
            st['errors'].append({'form_bin': rel, 'error': err})
            if out is not None:
                # модуль есть, но не прочитан — его прежнее зеркало не сирота
                expected.add(os.path.normcase(os.path.abspath(mirror_path(out, src, bin_path))))
            continue
        if status in ('empty', 'absent'):
            st[status] += 1
            continue
        st['modules'] += 1
        if out is None:
            continue
        dest = mirror_path(out, src, bin_path)
        expected.add(os.path.normcase(os.path.abspath(dest)))
        current = _read_or_none(dest)
        if write:
            if current == payload:
                st['unchanged'] += 1
            else:
                os.makedirs(_long(os.path.dirname(dest)), exist_ok=True)
                with open(_long(dest), 'wb') as f:
                    f.write(payload)
                st['written'] += 1
        else:
            st['missing' if current is None else ('actual' if current == payload else 'stale')] += 1
    # Сироты: Module.bsl в зеркале без живого модуля в выгрузке (форму удалили или модуль опустел).
    # Не удаляются — только перечисляются.
    if out is not None and os.path.isdir(out):
        for dirpath, _, filenames in _walk(out, st['errors']):
            if os.path.basename(dirpath).lower() != 'ext':
                continue
            for fn in filenames:
                p = os.path.join(dirpath, fn)
                if fn.lower() == 'module.bsl' and os.path.normcase(os.path.abspath(p)) not in expected:
                    st['orphans'].append(os.path.relpath(p, out))
    return st


def _inside(child, parent):
    child, parent = os.path.normcase(os.path.abspath(child)), os.path.normcase(os.path.abspath(parent))
    return child == parent or child.startswith(parent.rstrip(os.sep) + os.sep)


def main():
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding='utf-8')
    p = argparse.ArgumentParser(description='Модули обычных форм 1С из Form.bin (только чтение, v8unpack)')
    p.add_argument('mode', choices=['extract', 'report'])
    p.add_argument('src', help='Каталог выгрузки Конфигуратора (или epf-dump), где искать Form.bin')
    p.add_argument('--out', help='Каталог зеркала модулей (ВНЕ выгрузки); для extract обязателен')
    p.add_argument('--json', help='Записать полный отчёт в JSON-файл')
    a = p.parse_args()

    if not os.path.isdir(a.src):
        p.error(f'каталог выгрузки не найден: {a.src}')
    if a.mode == 'extract' and not a.out:
        p.error('для extract нужен --out <каталог зеркала>')
    if a.out and (_inside(a.out, a.src) or _inside(a.src, a.out)):
        p.error('--out не должен совпадать с выгрузкой, лежать внутри неё или содержать её '
                '(влияние лишних .bsl в выгрузке на загрузку в базу не проверено)')

    try:
        from importlib.metadata import version
        v8u = version('v8unpack')
    except Exception:
        v8u = '?'
    st = run(a.src, a.out, write=(a.mode == 'extract'))

    print(f'Режим: {a.mode}; выгрузка: {a.src}' + (f'; зеркало: {a.out}' if a.out else '') + f'; v8unpack {v8u}')
    print(f"Обычных форм (Form.bin): {st['forms']}")
    print(f"  с модулем: {st['modules']}; пустой модуль: {st['empty']}; без модуля: {st['absent']}; "
          f"ошибок разбора: {len(st['errors'])}")
    if a.out:
        if a.mode == 'extract':
            print(f"Зеркало: записано {st['written']}, без изменений {st['unchanged']}")
        else:
            print(f"Зеркало: актуально {st['actual']}, устарело {st['stale']}, отсутствует {st['missing']}")
        print(f"Сироты в зеркале (модуля в выгрузке больше нет; не удалены): {len(st['orphans'])}")
        for o in st['orphans'][:MAX_ERRORS_SHOWN]:
            print(f'  сирота: {o}')
    for e in st['errors'][:MAX_ERRORS_SHOWN]:
        print(f"  ОШИБКА {e['form_bin']}: {e['error']}")
    if len(st['errors']) > MAX_ERRORS_SHOWN:
        print(f"  … ещё ошибок: {len(st['errors']) - MAX_ERRORS_SHOWN} (полный список — --json)")

    if a.json:
        report = dict(st, mode=a.mode, src=os.path.abspath(a.src),
                      out=os.path.abspath(a.out) if a.out else None, v8unpack=v8u)
        with open(a.json, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=1)
    return 1 if st['errors'] else 0


if __name__ == '__main__':
    sys.exit(main())
