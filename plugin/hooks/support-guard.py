"""PreToolUse на Edit/Write/MultiEdit: не дать вручную править объект типовой конфигурации на поддержке поставщика.

Перенос вендорного хука cc-1c-skills/hooks/support-guard.mjs (MIT, Nikolay-Shirokov) на Python (ADR-0002),
с двумя нашими добавками, которые уже стоят в скриптах скиллов (реестр vendor-patch-registry):
  - раскладка EDT: файл правил Configuration/ParentConfigurations.bin рядом с Configuration.mdo,
    файл объекта <Каталог>/<Каталог>.mdo;
  - EDT 2026.1: правила поддержки в Configuration.distr вместо ParentConfigurations.bin.
Реакция — как у поставщика и у проверки внутри скиллов: editingAllowedCheck из .v8-project.json
(deny по умолчанию | warn | off; у базы с подходящим configSrc — своё значение). Любая ошибка — пропуск.
"""
import json
import os
import re
import sys

GUID_RE = re.compile(r'\buuid="([0-9a-fA-F-]{36})"')
EXT_ROOT_RE = re.compile(r'<MetaDataObject\b[^>]*>\s*<(?:\w+:)?(?:ExternalDataProcessor|ExternalReport)\b')


def read_text(path, limit=None):
    with open(path, 'rb') as f:
        data = f.read() if limit is None else f.read(limit)
    return data.decode('utf-8-sig', 'replace')


def is_external_root(xml_path):
    """Корень автономной внешней обработки или отчёта — такой объект никогда не на поддержке."""
    try:
        return os.path.isfile(xml_path) and bool(EXT_ROOT_RE.search(read_text(xml_path, 4000)[:1000]))
    except OSError:
        return False


def root_uuid(xml_path):
    try:
        if not os.path.isfile(xml_path):
            return None
        m = GUID_RE.search(read_text(xml_path))
        return m.group(1) if m else None
    except OSError:
        return None


def distr_text(distr_path):
    """EDT 2026.1: правила из Configuration.distr — в текст старого формата, чтобы разбирал тот же код."""
    try:
        raw = read_text(distr_path)
    except OSError:
        return None
    if 'DistributionSupport' not in raw:
        return None
    parts = []
    for m in re.finditer(r'<items\b([^>]*)/>', raw):
        attrs = m.group(1)
        uid = re.search(r'userId="([^"]+)"', attrs)
        if not uid:
            continue
        rule = '1' if 'userMode="ChangesAllowed"' in attrs else '0'
        parts.append('%s,0,%s,%s' % (rule, uid.group(1), uid.group(1)))
    if not parts:
        return None
    return '{6,0,1,' + ','.join(parts) + '}'


def decide_support(target):
    """{blocked, code, reason, cfg_dir}; при любой ошибке — не заблокировано."""
    res = {'blocked': False, 'code': None, 'reason': '', 'cfg_dir': None}
    try:
        if is_external_root(target):
            return res
        elem_uuid = root_uuid(target)
        cfg_dir = bin_path = None
        d = target if os.path.isdir(target) else os.path.dirname(target)
        for _ in range(12):
            if not d:
                break
            if is_external_root(d + '.xml'):
                return res
            if not elem_uuid:
                elem_uuid = root_uuid(d + '.xml')
            if not elem_uuid:
                elem_uuid = root_uuid(os.path.join(d, os.path.basename(d) + '.mdo'))  # раскладка EDT
            if not cfg_dir:
                cand = os.path.join(d, 'Ext', 'ParentConfigurations.bin')
                cand_edt = os.path.join(d, 'Configuration', 'ParentConfigurations.bin')
                if os.path.exists(cand) or os.path.exists(os.path.join(d, 'Configuration.xml')):
                    cfg_dir, bin_path = d, cand
                elif os.path.exists(cand_edt) or os.path.exists(os.path.join(d, 'Configuration', 'Configuration.mdo')):
                    cfg_dir, bin_path = d, cand_edt
            if elem_uuid and cfg_dir:
                break
            parent = os.path.dirname(d)
            if parent == d:
                break
            d = parent
        res['cfg_dir'] = cfg_dir
        if not elem_uuid and cfg_dir:
            elem_uuid = (root_uuid(os.path.join(cfg_dir, 'Configuration.xml'))
                         or root_uuid(os.path.join(cfg_dir, 'Configuration', 'Configuration.mdo')))
        text = None
        if bin_path and os.path.exists(bin_path):
            with open(bin_path, 'rb') as f:
                data = f.read()
            if len(data) <= 32:
                return res
            if data[:3] == b'\xef\xbb\xbf':
                data = data[3:]
            text = data.decode('utf-8', 'replace')
        elif bin_path:
            text = distr_text(os.path.join(os.path.dirname(bin_path), 'Configuration.distr'))
        if not text:
            return res
        h = re.match(r'\{6,(\d+),(\d+),', text)
        if not h:
            return res
        g, k = int(h.group(1)), int(h.group(2))
        if k == 0:
            return res
        best = None
        if elem_uuid:
            for m in re.finditer(r'([0-2]),0,' + re.escape(elem_uuid.lower()), text):
                f1 = int(m.group(1))
                if best is None or f1 < best:
                    best = f1
        if g == 1:
            res.update(blocked=True, code='capability-off',
                       reason='возможность изменения конфигурации выключена (вся конфигурация read-only)')
        elif best == 0:
            res.update(blocked=True, code='locked',
                       reason='объект на замке (поддержка поставщика) — прямое редактирование сломает обновления')
        return res
    except Exception:
        return {'blocked': False, 'code': None, 'reason': '', 'cfg_dir': None}


def find_v8project(start):
    d = start
    for _ in range(20):
        if not d:
            break
        pj = os.path.join(d, '.v8-project.json')
        if os.path.isfile(pj):
            return pj
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return None


def norm(p):
    return os.path.normcase(os.path.abspath(p)).rstrip('\\/')


def edit_mode(cfg_dir, cwd):
    """deny (по умолчанию) | warn | off — у базы с подходящим configSrc, иначе общий, иначе deny."""
    try:
        pj = find_v8project(cwd) or (find_v8project(cfg_dir) if cfg_dir else None)
        if not pj:
            return 'deny'
        proj = json.loads(read_text(pj))
        if cfg_dir:
            full = norm(cfg_dir)
            for db in proj.get('databases') or []:
                src = db.get('configSrc') if isinstance(db, dict) else None
                if src:
                    s = norm(src)
                    if (full == s or full.startswith(s + os.sep)) and db.get('editingAllowedCheck'):
                        return db['editingAllowedCheck']
        return proj.get('editingAllowedCheck') or 'deny'
    except Exception:
        return 'deny'


def diagnostic(code, target, cfg_dir):
    head = ('[support-guard] Редактирование отклонено: это объект типовой конфигурации на поддержке поставщика, '
            'прямое редактирование молча сломает будущие обновления.')
    cfe = ('Рекомендуемый путь: внести доработку в расширение (навыки cfe-borrow / cfe-patch-method) — '
           'состояние поддержки менять не нужно, обновления вендора сохраняются.')
    off_note = 'Снять проверку для этой базы: editingAllowedCheck = warn|off в .v8-project.json.'
    edt_note = ('Проект EDT 2026.1 (правила в Configuration.distr): режим поддержки переключается в EDT, '
                'скрипт support-edit этот формат не меняет.')
    root = cfg_dir or '<каталог дампа>'
    distr = bool(cfg_dir) and os.path.exists(os.path.join(cfg_dir, 'Configuration', 'Configuration.distr'))
    if code == 'capability-off':
        lines = [head,
                 'Состояние: у всей конфигурации выключена возможность изменения (режим read-only «из коробки») — '
                 'поэтому объект «%s» редактировать нельзя.' % target,
                 cfe,
                 'Либо снять защиту явно (навык support-edit, два шага; скрипт выполняет владелец):',
                 '  1. support-edit -Path "%s" -Capability on   — включить возможность изменения (объекты пока остаются на замке);' % root,
                 '  2. support-edit -Path "%s" -Set editable   — открыть этот объект для редактирования.' % target,
                 'Изменение применяется в базу полной загрузкой выгрузки и обходит механизм обновлений вендора.',
                 off_note]
    else:
        lines = [head,
                 'Состояние: объект «%s» на замке (возможность изменения конфигурации включена, но сам объект не редактируется).' % target,
                 cfe,
                 'Либо разрешить редактирование этого объекта (навык support-edit, выбрать одно; скрипт выполняет владелец):',
                 '  • support-edit -Path "%s" -Set editable      — редактировать и дальше получать обновления вендора '
                 '(при обновлении возможны конфликты слияния);' % target,
                 '  • support-edit -Path "%s" -Set off-support   — снять с поддержки: редактирование свободно, '
                 'обновления по объекту больше не приходят.' % target,
                 off_note]
    if distr:
        lines.append(edt_note)
    return '\n'.join(lines)


def candidate_paths(tool_input):
    out = []
    if isinstance(tool_input, dict):
        if isinstance(tool_input.get('file_path'), str):
            out.append(tool_input['file_path'])
        for e in tool_input.get('file_edits') or []:
            if isinstance(e, dict) and isinstance(e.get('file_path'), str):
                out.append(e['file_path'])
    return out


def main():
    raw = sys.stdin.buffer.read().decode('utf-8', 'replace').lstrip('﻿')
    data = json.loads(raw) if raw.strip() else {}
    cwd = data.get('cwd') if isinstance(data.get('cwd'), str) else os.getcwd()
    for p in candidate_paths(data.get('tool_input')):
        target = p if os.path.isabs(p) else os.path.abspath(os.path.join(cwd, p))
        r = decide_support(target)
        if not r['blocked']:
            continue
        mode = edit_mode(r['cfg_dir'], cwd)
        if mode == 'off':
            continue
        if mode == 'warn':
            sys.stderr.buffer.write(('[support-guard] ПРЕДУПРЕЖДЕНИЕ: %s. Цель: %s\n' % (r['reason'], target)).encode('utf-8'))
            return
        out = {'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'deny',
                                      'permissionDecisionReason': diagnostic(r['code'], target, r['cfg_dir'])}}
        sys.stdout.buffer.write(json.dumps(out, ensure_ascii=False).encode('utf-8'))
        return


if __name__ == '__main__':
    try:
        main()
    except Exception as e:   # сбой барьера не молчит: контракт деградации enforcement-hooks (волна 2 п.2.9)
        sys.stdout.buffer.write(json.dumps({'systemMessage': 'support-guard: DEGRADED — внутренняя ошибка, правка пропущена '
                                            'без проверки поддержки: %s' % e}, ensure_ascii=False).encode('utf-8'))
        sys.stdout.flush()
    sys.exit(0)
