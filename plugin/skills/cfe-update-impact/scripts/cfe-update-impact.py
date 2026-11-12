#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cfe-update-impact — влияние нового релиза типовой конфигурации на расширение (CFE).

Вход — три выгрузки Конфигуратора (DumpConfigToFiles): старая версия конфигурации,
новая версия и расширение. Выход — отчёт: какие перехватчики методов, обработчики
форм с callType и заимствованные объекты затронуты дельтой релиза.

Идея и перечень проверок — по мотивам xnd1124/CfeUpdater (у репозитория нет лицензии:
код, регулярные выражения и тестовые наборы оттуда не заимствованы, реализация своя).
Только стандартная библиотека Python 3. Ничего не пишет в выгрузки — только читает.

Коды выхода: 0 — проблем нет, 1 — есть хотя бы одна ПРОБЛЕМА, 2 — ошибка входных данных.
"""

import argparse
import difflib
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

PROBLEM = "ПРОБЛЕМА"
INFO = "ИНФО"
OK = "ОК"

SECTIONS = {
    "methods": "1. Перехватчики методов (&Перед / &После / &Вместо)",
    "control": "2. &ИзменениеИКонтроль — контролируемые методы",
    "forms": "3. Обработчики форм с callType (Before / After / Override)",
    "adopted": "4. Заимствованные объекты, формы и макеты",
}

# Аннотации перехвата: русское и английское написание (лексер bsl-parser, v8std).
INTERCEPT_ANN = {
    "перед": "Перед", "before": "Перед",
    "после": "После", "after": "После",
    "вместо": "Вместо", "around": "Вместо",
    "изменениеиконтроль": "ИзменениеИКонтроль", "changeandvalidate": "ИзменениеИКонтроль",
}

# Директивы компиляции.
CONTEXT_ANN = {
    "наклиенте": "НаКлиенте", "atclient": "НаКлиенте",
    "насервере": "НаСервере", "atserver": "НаСервере",
    "насерверебезконтекста": "НаСервереБезКонтекста", "atservernocontext": "НаСервереБезКонтекста",
    "наклиентенасерверебезконтекста": "НаКлиентеНаСервереБезКонтекста",
    "atclientatservernocontext": "НаКлиентеНаСервереБезКонтекста",
    "наклиентенасервере": "НаКлиентеНаСервере", "atclientatserver": "НаКлиентеНаСервере",
}

CALLTYPE_ANN = {"Before": "Перед", "After": "После", "Override": "Вместо"}

KW_PROC = {"процедура", "procedure"}
KW_FUNC = {"функция", "function"}
KW_END = {"конецпроцедуры", "конецфункции", "endprocedure", "endfunction"}
KW_EXPORT = {"экспорт", "export"}
KW_VAL = {"знач", "val"}
KW_VAR = {"перем", "var"}
KW_PROCEED = {"продолжитьвызов", "proceedwithcall"}

# Маркеры правок &ИзменениеИКонтроль; допускают отступ и хвостовой комментарий.
MARKER_RE = re.compile(
    r"^#\s*(вставка|insert|конецвставки|endinsert|удаление|delete|конецудаления|enddelete)(?!\w)",
    re.IGNORECASE)

# Секции Form.xml, где нет элементов формы (у реквизитов и элементов имена могут совпадать).
FORM_NON_ITEM_SECTIONS = {"Attributes", "Commands", "Parameters", "Events", "BaseForm",
                          "CommandInterface"}


# ---------------------------------------------------------------------------
# Лексер и разбор модулей BSL
# ---------------------------------------------------------------------------

def lex_bsl(text):
    """Токены модуля: список (строка, вид, значение).

    Вид: I — идентификатор/ключевое слово, S — кусок строкового литерала, D — литерал даты,
    N — число, P — знак. Комментарии и пробелы отбрасываются; «//» внутри строки — текст строки;
    многострочные литералы (продолжение через «|», комментарии между строками) учитываются.
    """
    toks = []
    in_str = False
    for ln, line in enumerate(text.split("\n"), 1):
        n = len(line)
        i = 0
        piece = None
        if in_str:
            s = line.lstrip()
            if s.startswith("|"):
                i = n - len(s) + 1
                piece = []
            elif s.startswith("//") or not s.strip():
                continue
            else:
                in_str = False  # незакрытая строка — дальше разбираем как код
        while i < n:
            if in_str:
                j = line.find('"', i)
                if j < 0:
                    piece.append(line[i:])
                    i = n
                    break
                if j + 1 < n and line[j + 1] == '"':
                    piece.append(line[i:j + 2])
                    i = j + 2
                    continue
                piece.append(line[i:j])
                toks.append((ln, "S", "".join(piece)))
                piece = None
                in_str = False
                i = j + 1
                continue
            ch = line[i]
            if ch.isspace() or ch == "﻿":
                i += 1
                continue
            if ch == "/" and line.startswith("//", i):
                break
            if ch == '"':
                in_str = True
                piece = []
                i += 1
                continue
            if ch == "'":
                j = line.find("'", i + 1)
                if j < 0:
                    j = n - 1
                toks.append((ln, "D", line[i:j + 1]))
                i = j + 1
                continue
            if ch.isalpha() or ch == "_":
                j = i + 1
                while j < n and (line[j].isalnum() or line[j] == "_"):
                    j += 1
                toks.append((ln, "I", line[i:j]))
                i = j
                continue
            if ch.isdigit():
                j = i + 1
                while j < n and (line[j].isdigit() or line[j] == "."):
                    j += 1
                toks.append((ln, "N", line[i:j]))
                i = j
                continue
            if line[i:i + 2] in ("<>", "<=", ">="):
                toks.append((ln, "P", line[i:i + 2]))
                i += 2
                continue
            toks.append((ln, "P", ch))
            i += 1
        if in_str and piece is not None:
            toks.append((ln, "S", "".join(piece)))
    return toks


def _param_info(seg):
    """Параметр сигнатуры из его токенов: (Знач, имя, значение по умолчанию или None)."""
    byval = bool(seg) and seg[0][1] == "I" and seg[0][2].casefold() in KW_VAL
    rest = seg[1:] if byval else seg
    name = rest[0][2] if rest else ""
    default = None
    for idx, t in enumerate(rest):
        if t[1] == "P" and t[2] == "=":
            default = " ".join(x[2] if x[1] != "S" else '"' + x[2] + '"' for x in rest[idx + 1:])
            break
    return {"byval": byval, "name": name, "default": default}


def parse_module(text):
    """Методы модуля: {имя_casefold: запись}. Границы — по токенам, не по регуляркам строк."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    toks = lex_bsl(text)
    methods = {}
    pending = []
    i, n = 0, len(toks)
    while i < n:
        ln, k, v = toks[i]
        if k == "P" and v == "&" and i + 1 < n and toks[i + 1][1] == "I":
            name = toks[i + 1][2]
            arg = None
            j = i + 2
            if (j + 2 < n and toks[j][1] == "P" and toks[j][2] == "("
                    and toks[j + 1][1] == "S" and toks[j + 2][2] == ")"):
                arg = toks[j + 1][2]
                j += 3
            pending.append((name, arg, ln))
            i = j
            continue
        if k == "I" and v.casefold() in KW_VAR:
            pending = []  # аннотации относились к переменной модуля
            i += 1
            continue
        if (k == "I" and v.casefold() in (KW_PROC | KW_FUNC) and i + 2 < n
                and toks[i + 1][1] == "I" and toks[i + 2][1] == "P" and toks[i + 2][2] == "("
                and not (i > 0 and toks[i - 1][2] == ".")):
            is_func = v.casefold() in KW_FUNC
            name = toks[i + 1][2]
            j = i + 3
            depth = 1
            seg = []
            segs = []
            while j < n:
                t = toks[j]
                if t[1] == "P" and t[2] == "(":
                    depth += 1
                elif t[1] == "P" and t[2] == ")":
                    depth -= 1
                    if depth == 0:
                        break
                if depth == 1 and t[1] == "P" and t[2] == ",":
                    segs.append(seg)
                    seg = []
                else:
                    seg.append(t)
                j += 1
            if seg or segs:
                segs.append(seg)
            header_end = toks[j][0] if j < n else ln
            j += 1
            export = False
            if j < n and toks[j][1] == "I" and toks[j][2].casefold() in KW_EXPORT:
                export = True
                header_end = toks[j][0]
                j += 1
            body_start = j
            while j < n and not (toks[j][1] == "I" and toks[j][2].casefold() in KW_END):
                j += 1
            end_line = toks[j][0] if j < n else len(lines)
            rec = {
                "name": name,
                "is_func": is_func,
                "annotations": pending,
                "decl_line": ln,
                "end_line": end_line,
                "params": [_param_info(s) for s in segs],
                "export": export,
                "body_tokens": toks[body_start:j],
                "body_lines": lines[header_end:max(header_end, end_line - 1)],
            }
            methods.setdefault(name.casefold(), rec)
            pending = []
            i = j + 1
            continue
        i += 1
    return methods


def code_key(tokens):
    """Ключ сравнения «по смыслу»: без пробелов и комментариев, регистр идентификаторов не важен."""
    return tuple((k, v.casefold() if k == "I" else v) for _, k, v in tokens)


def control_lines(lines):
    """Ключ построчного контроля: строки без отступов, пустые выброшены, комментарии сохранены."""
    return [s.strip() for s in lines if s.strip()]


def strip_markers(lines):
    """Тело &ИзменениеИКонтроль без правок: блоки #Вставка выброшены, маркеры #Удаление сняты."""
    out = []
    skip = False
    for s in lines:
        m = MARKER_RE.match(s.strip())
        if m:
            w = m.group(1).casefold()
            if w in ("вставка", "insert"):
                skip = True
            elif w in ("конецвставки", "endinsert"):
                skip = False
            continue
        if not skip:
            out.append(s)
    return out


def apply_markers(lines):
    """Результат правок &ИзменениеИКонтроль: блоки #Удаление выброшены, содержимое #Вставка оставлено."""
    out = []
    skip = False
    for s in lines:
        m = MARKER_RE.match(s.strip())
        if m:
            w = m.group(1).casefold()
            if w in ("удаление", "delete"):
                skip = True
            elif w in ("конецудаления", "enddelete"):
                skip = False
            continue
        if not skip:
            out.append(s)
    return out


def context_of(method):
    for name, _arg, _ln in method["annotations"]:
        c = CONTEXT_ANN.get(name.casefold())
        if c:
            return c
    return None


def signature_text(method):
    parts = []
    for p in method["params"]:
        s = ("Знач " if p["byval"] else "") + p["name"]
        if p["default"] is not None:
            s += " = " + p["default"]
        parts.append(s)
    return "(" + ", ".join(parts) + ")"


def signature_key(method):
    return tuple((p["byval"], p["name"].casefold(), p["default"]) for p in method["params"])


def calls_proceed(method):
    return any(k == "I" and v.casefold() in KW_PROCEED for _, k, v in method["body_tokens"])


def diff_stat(a_lines, b_lines):
    plus = minus = 0
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a_lines, b_lines, autojunk=False).get_opcodes():
        if tag in ("replace", "delete"):
            minus += i2 - i1
        if tag in ("replace", "insert"):
            plus += j2 - j1
    return plus, minus


def unified(a_lines, b_lines, limit):
    out = list(difflib.unified_diff(a_lines, b_lines, "старая", "новая", n=1, lineterm=""))
    if len(out) > limit:
        out = out[:limit] + ["… (обрезано: ещё %d строк)" % (len(out) - limit)]
    return out


# ---------------------------------------------------------------------------
# Чтение файлов и XML
# ---------------------------------------------------------------------------

def read_text(path):
    with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
        return fh.read()


def lname(el):
    tag = el.tag
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def child(el, name):
    for c in el:
        if lname(c) == name:
            return c
    return None


def parse_xml(path):
    try:
        return ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return None


def canon_file(path):
    """Нормализованное содержимое: XML — каноническая форма без пробельного текста, иначе байты."""
    try:
        if path.lower().endswith(".xml"):
            return ET.canonicalize(xml_data=read_text(path), strip_text=True)
    except ET.ParseError:
        pass
    with open(path, "rb") as fh:
        return fh.read()


def canon_el(el):
    if el is None:
        return None
    return ET.canonicalize(xml_data=ET.tostring(el, encoding="unicode"), strip_text=True)


def md_object(root):
    """Первый элемент-объект метаданных внутри <MetaDataObject>."""
    if root is None:
        return None
    for c in root:
        if isinstance(c.tag, str):
            return c
    return None


def md_props(obj):
    props = child(obj, "Properties") if obj is not None else None
    res = {}
    if props is not None:
        for p in props:
            if lname(p) in ("Name", "ObjectBelonging", "ExtendedConfigurationObject"):
                res[lname(p)] = (p.text or "").strip()
    return res


def child_objects(obj):
    """Потомки ChildObjects с именем: {(вид, имя_casefold): элемент}. Формы/макеты-ссылки (текст) — тоже."""
    res = {}
    co = child(obj, "ChildObjects") if obj is not None else None
    if co is None:
        return res
    for c in co:
        kind = lname(c)
        if not kind:
            continue
        name = md_props(c).get("Name") or (c.text or "").strip()
        if name:
            res[(kind, name.casefold())] = c
    return res


# ---------------------------------------------------------------------------
# Анализ
# ---------------------------------------------------------------------------

class Report:
    def __init__(self):
        self.items = []

    def add(self, section, level, where, message, details=None):
        self.items.append({"section": section, "level": level, "where": where,
                           "message": message, "details": details or []})

    def count(self, section=None, level=None):
        return sum(1 for x in self.items
                   if (section is None or x["section"] == section) and (level is None or x["level"] == level))


class Analyzer:
    def __init__(self, ext, old, new, want_diff, diff_limit):
        self.ext, self.old, self.new = ext, old, new
        self.want_diff = want_diff
        self.diff_limit = diff_limit
        self.rep = Report()
        self._mods = {}

    # --- утилиты ---

    def rel(self, path):
        return os.path.relpath(path, self.ext).replace("\\", "/")

    def module(self, root, rel_path):
        key = (root, rel_path)
        if key not in self._mods:
            p = os.path.join(root, rel_path)
            self._mods[key] = parse_module(read_text(p)) if os.path.isfile(p) else None
        return self._mods[key]

    def body_diff(self, m_old, m_new):
        a, b = control_lines(m_old["body_lines"]), control_lines(m_new["body_lines"])
        plus, minus = diff_stat(a, b)
        det = ["в оригинале +%d / −%d строк" % (plus, minus)]
        if self.want_diff:
            det += unified(a, b, self.diff_limit)
        return det

    def find_renamed(self, mods_new, m_old):
        key = code_key(m_old["body_tokens"])
        if len(key) < 3:
            return None
        for m in mods_new.values():
            if code_key(m["body_tokens"]) == key and m["name"].casefold() != m_old["name"].casefold():
                return m["name"]
        return None

    # --- разделы 1 и 2: перехватчики методов ---

    def check_interceptors(self):
        for dirpath, _dirs, files in os.walk(self.ext):
            for fn in files:
                if not fn.lower().endswith(".bsl"):
                    continue
                path = os.path.join(dirpath, fn)
                rel = self.rel(path)
                for m in parse_module(read_text(path)).values():
                    for ann, arg, ln in m["annotations"]:
                        kind = INTERCEPT_ANN.get(ann.casefold())
                        if kind and arg:
                            self.check_one(rel, m, kind, arg, ln)

    def check_one(self, rel, ext_m, kind, target, line):
        section = "control" if kind == "ИзменениеИКонтроль" else "methods"
        where = '%s:%d &%s("%s") → %s' % (rel, line, kind, target, ext_m["name"])
        mods_old = self.module(self.old, rel)
        mods_new = self.module(self.new, rel)
        m_old = mods_old.get(target.casefold()) if mods_old else None
        m_new = mods_new.get(target.casefold()) if mods_new else None

        if mods_new is None:
            if mods_old is None:
                self.rep.add(section, INFO, where, "модуля нет ни в старой, ни в новой версии — сверить, та ли старая выгрузка")
            else:
                self.rep.add(section, PROBLEM, where, "модуль исчез в новой версии (объект удалён, переименован или модуль пуст)")
            return
        if m_new is None:
            if m_old is None:
                self.rep.add(section, INFO, where, "метода нет ни в старой, ни в новой версии — вне дельты релиза")
                return
            ren = self.find_renamed(mods_new, m_old)
            msg = "метод-оригинал исчез в новой версии"
            if ren:
                msg += "; вероятно переименован в «%s» (тело совпадает)" % ren
            self.rep.add(section, PROBLEM, where, msg)
            return

        problems, infos = [], []
        # сигнатура: вид метода, число и состав параметров, директива компиляции
        if m_old is not None and m_old["is_func"] != m_new["is_func"]:
            problems.append("вид оригинала изменился: %s → %s" % (
                "Функция" if m_old["is_func"] else "Процедура", "Функция" if m_new["is_func"] else "Процедура"))
        if kind in ("Перед", "После") and m_new["is_func"]:
            # запрет платформы не подтверждён документацией — только информируем, не ПРОБЛЕМА
            infos.append("оригинал — функция: &%s не меняет её возвращаемое значение, "
                         "сверить, что перехват остался осмысленным" % kind)
        if len(ext_m["params"]) != len(m_new["params"]):
            problems.append("число параметров перехватчика (%d) ≠ оригиналу новой версии (%d): %s" % (
                len(ext_m["params"]), len(m_new["params"]), signature_text(m_new)))
        elif m_old is not None and signature_key(m_old) != signature_key(m_new):
            infos.append("сигнатура оригинала изменилась: %s → %s" % (signature_text(m_old), signature_text(m_new)))
        if m_old is not None and context_of(m_old) != context_of(m_new):
            problems.append("директива компиляции оригинала изменилась: %s → %s — сверить директиву перехватчика" % (
                context_of(m_old) or "нет", context_of(m_new) or "нет"))

        details = []
        if kind == "ИзменениеИКонтроль":
            ext_base = control_lines(strip_markers(ext_m["body_lines"]))
            new_ctrl = control_lines(m_new["body_lines"])
            old_ctrl = control_lines(m_old["body_lines"]) if m_old else None
            msg_ok = "контрольная часть совпадает с оригиналом новой версии"
            applied = code_key(lex_bsl("\n".join(apply_markers(ext_m["body_lines"]))))
            if ext_base == new_ctrl:
                pass
            elif applied == code_key(m_new["body_tokens"]):
                problems.append("правки расширения уже есть в оригинале новой версии (перенесены в основную) — "
                                "перехватчик можно удалить")
                if old_ctrl is not None and old_ctrl != new_ctrl:
                    details = self.body_diff(m_old, m_new)
            elif old_ctrl is None:
                problems.append("контрольная часть расходится с оригиналом новой версии; в старой версии метода не было")
            elif old_ctrl != new_ctrl:
                note = ""
                if code_key(m_old["body_tokens"]) == code_key(m_new["body_tokens"]):
                    note = " (по смыслу изменились только комментарии/форматирование, но контроль платформы построчный)"
                was = "; перехватчик был согласован со старой версией" if ext_base == old_ctrl else \
                    "; перехватчик расходился и со старой версией"
                problems.append("оригинал изменился в релизе — переналожить #Вставка/#Удаление на новый оригинал" + note + was)
                details = self.body_diff(m_old, m_new)
            else:
                problems.append("оригинал в релизе не менялся, но контрольная часть перехватчика с ним расходится "
                                "(дрейф был и до обновления)")
            if not problems:
                self.rep.add(section, INFO if infos else OK, where, "; ".join(infos) or msg_ok)
                return
        else:
            if m_old is None:
                infos.append("в старой версии метода не было — оригинал появился в релизе")
            elif code_key(m_old["body_tokens"]) != code_key(m_new["body_tokens"]):
                details = self.body_diff(m_old, m_new)
                if kind == "Вместо":
                    if calls_proceed(ext_m):
                        problems.append("тело оригинала изменилось; перехватчик вызывает его через ПродолжитьВызов — "
                                        "сверить свою логику вокруг вызова")
                    else:
                        problems.append("тело оригинала изменилось, а перехватчик заменяет его целиком — "
                                        "правки вендора в расширение не попадут")
                else:
                    infos.append("тело оригинала изменилось — перехватчик &%s продолжит работать, сверить логику" % kind)
            elif control_lines(m_old["body_lines"]) != control_lines(m_new["body_lines"]):
                infos.append("изменились только комментарии/форматирование оригинала")

        if problems:
            self.rep.add(section, PROBLEM, where, "; ".join(problems + infos), details)
        elif infos:
            self.rep.add(section, INFO, where, "; ".join(infos), details)
        else:
            self.rep.add(section, OK, where, "оригинал не изменился")

    # --- раздел 3: обработчики форм с callType ---

    @staticmethod
    def form_index(root):
        """Карта базовой формы: события формы, элементы (имя → {событие: обработчик}), команды."""
        form_events, items, commands = {}, {}, {}
        ev = child(root, "Events")
        if ev is not None:
            for e in ev:
                if lname(e) == "Event" and not e.get("callType"):
                    form_events[e.get("name", "")] = (e.text or "").strip()
        for sec in root:
            if lname(sec) in FORM_NON_ITEM_SECTIONS:
                continue
            for el in sec.iter():
                nm = el.get("name")
                if not nm or not isinstance(el.tag, str) or lname(el) == "Event":
                    continue
                evs = {}
                sub = child(el, "Events")
                if sub is not None:
                    for e in sub:
                        if lname(e) == "Event" and not e.get("callType"):
                            evs[e.get("name", "")] = (e.text or "").strip()
                items.setdefault(nm, evs)
        cmds = child(root, "Commands")
        if cmds is not None:
            for c in cmds:
                if lname(c) != "Command":
                    continue
                act = None
                for a in c:
                    if lname(a) == "Action" and not a.get("callType"):
                        act = (a.text or "").strip()
                commands[c.get("name", "")] = act
        return form_events, items, commands

    @staticmethod
    def ext_calltype_items(root):
        """События расширения с callType: (вид, владелец, событие, callType, обработчик расширения)."""
        res = []
        ev = child(root, "Events")
        if ev is not None:
            for e in ev:
                if lname(e) == "Event" and e.get("callType"):
                    res.append(("form", None, e.get("name", ""), e.get("callType"), (e.text or "").strip()))
        for sec in root:
            if lname(sec) in FORM_NON_ITEM_SECTIONS:
                continue
            for el in sec.iter():
                nm = el.get("name")
                sub = child(el, "Events") if nm and isinstance(el.tag, str) else None
                if sub is None:
                    continue
                for e in sub:
                    if lname(e) == "Event" and e.get("callType"):
                        res.append(("item", nm, e.get("name", ""), e.get("callType"), (e.text or "").strip()))
        cmds = child(root, "Commands")
        if cmds is not None:
            for c in cmds:
                if lname(c) != "Command":
                    continue
                for a in c:
                    if lname(a) == "Action" and a.get("callType"):
                        res.append(("command", c.get("name", ""), "Action", a.get("callType"), (a.text or "").strip()))
        return res

    def check_forms(self):
        for dirpath, _dirs, files in os.walk(self.ext):
            if "Form.xml" not in files or os.path.basename(dirpath) != "Ext":
                continue
            path = os.path.join(dirpath, "Form.xml")
            root = parse_xml(path)
            if root is None or child(root, "BaseForm") is None:
                continue  # собственная форма расширения
            items = self.ext_calltype_items(root)
            if not items:
                continue
            rel = self.rel(path)
            mod_rel = rel[:-len("Form.xml")] + "Form/Module.bsl"
            old_root = parse_xml(os.path.join(self.old, rel))
            new_root = parse_xml(os.path.join(self.new, rel))
            if new_root is None:
                lvl = PROBLEM if old_root is not None else INFO
                self.rep.add("forms", lvl, rel, "формы нет в новой версии — %d обработчик(ов) с callType повисли" % len(items)
                             if old_root is not None else "формы нет ни в старой, ни в новой версии")
                continue
            if old_root is None:
                self.rep.add("forms", INFO, rel, "формы нет в старой выгрузке — дельту обработчиков не посчитать")
                continue
            idx_old = self.form_index(old_root)
            idx_new = self.form_index(new_root)
            mods_old = self.module(self.old, mod_rel) or {}
            mods_new = self.module(self.new, mod_rel) or {}
            for kind, owner, event, ct, handler in items:
                self.check_form_item(rel, kind, owner, event, ct, handler, idx_old, idx_new, mods_old, mods_new)

    def check_form_item(self, rel, kind, owner, event, ct, handler, idx_old, idx_new, mods_old, mods_new):
        ann = CALLTYPE_ANN.get(ct, ct)
        label = {"form": "форма", "item": "элемент %s" % owner, "command": "команда %s" % owner}[kind]
        where = "%s: %s.%s [%s=&%s] → %s" % (rel, label, event, ct, ann, handler)
        heavy = PROBLEM if ct == "Override" else INFO

        def base(idx):
            fe, it, cm = idx
            if kind == "form":
                return True, fe.get(event) or None
            if kind == "item":
                if owner not in it:
                    return False, None
                return True, it[owner].get(event) or None
            if owner not in cm:
                return False, None
            return True, cm[owner] or None

        ex_old, h_old = base(idx_old)
        ex_new, h_new = base(idx_new)
        if not ex_new:
            if ex_old:
                self.rep.add("forms", PROBLEM, where, "%s исчез(ла) в новой версии формы" % label)
            else:
                self.rep.add("forms", INFO, where, "в базовой форме такого владельца нет (собственный элемент/команда расширения?)")
            return
        if h_new is None:
            if h_old:
                self.rep.add("forms", PROBLEM, where, "в новой версии у события больше нет базового обработчика (был «%s»)" % h_old)
            else:
                self.rep.add("forms", INFO, where, "базового обработчика нет ни в старой, ни в новой версии")
            return
        if h_old is None:
            self.rep.add("forms", heavy, where, "вендор добавил базовый обработчик «%s» — сверить порядок с обработчиком расширения" % h_new)
            return
        notes = []
        if h_old.casefold() != h_new.casefold():
            notes.append("базовый обработчик переименован: %s → %s" % (h_old, h_new))
        m_old, m_new = mods_old.get(h_old.casefold()), mods_new.get(h_new.casefold())
        if m_old is None or m_new is None:
            notes.append("метод базового обработчика не найден в модуле формы (%s)" % ("старой" if m_old is None else "новой"))
            self.rep.add("forms", INFO, where, "; ".join(notes))
            return
        if code_key(m_old["body_tokens"]) != code_key(m_new["body_tokens"]):
            notes.insert(0, "тело базового обработчика «%s» изменилось" % h_new)
            self.rep.add("forms", heavy, where, "; ".join(notes), self.body_diff(m_old, m_new))
        elif notes:
            self.rep.add("forms", INFO, where, "; ".join(notes))
        else:
            self.rep.add("forms", OK, where, "базовый обработчик не изменился")

    # --- раздел 4: заимствованные объекты ---

    def iter_adopted(self):
        """Заимствованные объекты расширения: (отн. путь XML, вид, имя, uuid оригинала, объект)."""
        for dirpath, _dirs, files in os.walk(self.ext):
            reld = os.path.relpath(dirpath, self.ext).replace("\\", "/")
            depth = 0 if reld == "." else reld.count("/") + 1
            base = os.path.basename(dirpath)
            if not (depth == 1 or (depth == 3 and base in ("Forms", "Templates"))):
                continue
            for fn in files:
                if not fn.lower().endswith(".xml"):
                    continue
                path = os.path.join(dirpath, fn)
                obj = md_object(parse_xml(path))
                if obj is None:
                    continue
                pr = md_props(obj)
                if pr.get("ObjectBelonging") != "Adopted":
                    continue
                yield self.rel(path), lname(obj), pr.get("Name", fn[:-4]), pr.get("ExtendedConfigurationObject", ""), obj

    @staticmethod
    def uuid_of(path):
        obj = md_object(parse_xml(path))
        return obj.get("uuid", "") if obj is not None else ""

    def find_by_uuid(self, rel, uid):
        """Переименование у вендора: ищем в том же каталоге новой версии объект с тем же uuid."""
        if not uid:
            return None
        d = os.path.join(self.new, os.path.dirname(rel))
        if not os.path.isdir(d):
            return None
        pat = re.compile(r'uuid="%s"' % re.escape(uid))
        for fn in os.listdir(d):
            if not fn.lower().endswith(".xml"):
                continue
            try:
                with open(os.path.join(d, fn), "r", encoding="utf-8-sig", errors="replace") as fh:
                    head = fh.read(4096)
            except OSError:
                continue
            if pat.search(head):
                return fn[:-4]
        return None

    def check_adopted(self):
        for rel, kind, name, ext_uuid, ext_obj in self.iter_adopted():
            where = "%s %s (%s)" % (kind, name, rel)
            p_old, p_new = os.path.join(self.old, rel), os.path.join(self.new, rel)
            if not os.path.isfile(p_new):
                if os.path.isfile(p_old):
                    ren = self.find_by_uuid(rel, ext_uuid)
                    self.rep.add("adopted", PROBLEM, where, "объект удалён в новой версии" +
                                 ("; найден под именем «%s» (тот же uuid) — переименован" % ren if ren else ""))
                else:
                    self.rep.add("adopted", INFO, where, "объекта нет ни в старой, ни в новой версии")
                continue
            u_old = self.uuid_of(p_old) if os.path.isfile(p_old) else ""
            u_new = self.uuid_of(p_new)
            if ext_uuid and u_new and ext_uuid != u_new:
                if u_old == ext_uuid:
                    self.rep.add("adopted", PROBLEM, where, "объект пересоздан в новой версии (uuid %s → %s) — "
                                 "заимствование ссылается на старый" % (u_old, u_new))
                else:
                    self.rep.add("adopted", INFO, where, "ExtendedConfigurationObject расширения не совпадает с uuid "
                                 "ни старой, ни новой версии — сверить, та ли старая выгрузка")
            if kind in ("Form", "CommonForm"):
                self.check_adopted_content(rel, where, "Form.xml", "форма")
            elif kind in ("Template", "CommonTemplate"):
                self.check_adopted_template(rel, where)
            if kind not in ("Form", "Template"):
                self.check_adopted_object(where, ext_obj, p_old, p_new)

    def check_adopted_content(self, rel, where, fname, what):
        sub = rel[:-4] + "/Ext/" + fname
        f_old, f_new = os.path.join(self.old, sub), os.path.join(self.new, sub)
        if not os.path.isfile(f_new):
            return
        if not os.path.isfile(f_old):
            self.rep.add("adopted", INFO, where, "%s: в старой выгрузке нет %s — сравнить не с чем" % (what, sub))
            return
        if canon_file(f_old) != canon_file(f_new):
            self.rep.add("adopted", INFO, where, "%s изменена у вендора — сверить отличия расширения (/form-info), "
                         "BaseForm расширения — снимок прежней формы" % what)
        else:
            self.rep.add("adopted", OK, where, "%s не изменилась" % what)

    def check_adopted_template(self, rel, where):
        sub = rel[:-4] + "/Ext"
        d_old, d_new, d_ext = (os.path.join(r, sub) for r in (self.old, self.new, self.ext))

        def files(d):
            # рекурсивно и только файлы: подкаталог в Ext не должен ронять сравнение
            if not os.path.isdir(d):
                return {}
            res = {}
            for dp, _, fns in os.walk(d):
                for f in fns:
                    p = os.path.join(dp, f)
                    res[os.path.relpath(p, d).replace(os.sep, "/")] = p
            return res

        fo, fn_, fe = files(d_old), files(d_new), files(d_ext)
        if not fn_:
            return
        changed = sorted(f for f in fn_ if f not in fo or canon_file(fo[f]) != canon_file(fn_[f]))
        if not changed:
            self.rep.add("adopted", OK, where, "макет у вендора не изменился")
            return
        if not fe:
            self.rep.add("adopted", INFO, where, "макет изменён у вендора (%s); своей копии содержимого в расширении нет"
                         % ", ".join(changed))
            return
        if all(f in fe and canon_file(fe[f]) == canon_file(fn_[f]) for f in changed):
            self.rep.add("adopted", OK, where, "макет изменён у вендора, копия в расширении уже совпадает с новой версией")
            return
        self.rep.add("adopted", PROBLEM, where, "макет изменён у вендора (%s), а расширение держит свою копию — "
                     "перенести правки вендора в копию расширения" % ", ".join(changed))

    def check_adopted_object(self, where, ext_obj, p_old, p_new):
        if not os.path.isfile(p_old):
            return
        o_old, o_new = md_object(parse_xml(p_old)), md_object(parse_xml(p_new))
        if o_old is None or o_new is None:
            return
        problems, infos = [], []
        self.compare_adopted_children(ext_obj, o_old, o_new, "", problems, infos)
        whole_changed = canon_el(o_old) != canon_el(o_new)
        if whole_changed and not infos and not problems:
            c_old, c_new = child_objects(o_old), child_objects(o_new)
            added = len(set(c_new) - set(c_old))
            removed = len(set(c_old) - set(c_new))
            changed = sum(1 for k in set(c_old) & set(c_new) if canon_el(c_old[k]) != canon_el(c_new[k]))
            props = canon_el(child(o_old, "Properties")) != canon_el(child(o_new, "Properties"))
            if props or added or removed or changed:
                infos.append("метаданные объекта изменены у вендора (свойства: %s; состав: +%d −%d ~%d); "
                             "заимствованные части не затронуты" % ("да" if props else "нет", added, removed, changed))
            elif o_old.get("uuid") != o_new.get("uuid"):
                return  # отличается только uuid — уже разобрано в check_adopted
            else:
                infos.append("изменились только служебные данные объекта (InternalInfo)")
        if problems:
            self.rep.add("adopted", PROBLEM, where, "; ".join(problems + infos))
        elif infos:
            self.rep.add("adopted", INFO, where, "; ".join(infos))
        elif not whole_changed:
            self.rep.add("adopted", OK, where, "метаданные объекта не изменились")

    def compare_adopted_children(self, ext_obj, o_old, o_new, prefix, problems, infos):
        c_ext, c_old, c_new = child_objects(ext_obj), child_objects(o_old), child_objects(o_new)
        for key, el in c_ext.items():
            if md_props(el).get("ObjectBelonging") != "Adopted":
                continue
            label = "%s%s.%s" % (prefix, key[0], md_props(el).get("Name", key[1]))
            if key not in c_new:
                if key in c_old:
                    problems.append("заимствованный %s удалён в новой версии" % label)
                continue
            if key in c_old and canon_el(c_old[key]) != canon_el(c_new[key]):
                infos.append("заимствованный %s изменён у вендора" % label)
            if key in c_old:
                self.compare_adopted_children(el, c_old[key], c_new[key], label + "/", problems, infos)


# ---------------------------------------------------------------------------
# Вход, вывод
# ---------------------------------------------------------------------------

def check_dump(path, role, is_ext):
    if not os.path.isdir(path):
        return "%s: каталог не найден: %s" % (role, path)
    cfg = os.path.join(path, "Configuration.xml")
    if not os.path.isfile(cfg):
        if os.path.isfile(os.path.join(path, "src", "Configuration", "Configuration.mdo")) or \
                os.path.isfile(os.path.join(path, "Configuration", "Configuration.mdo")):
            return "%s: это формат EDT — нужна выгрузка Конфигуратора (/db-dump-xml): %s" % (role, path)
        return "%s: нет Configuration.xml — нужна выгрузка Конфигуратора (DumpConfigToFiles): %s" % (role, path)
    text = read_text(cfg)
    has_ext_mark = "ConfigurationExtensionPurpose" in text or "<ObjectBelonging>Adopted" in text
    if is_ext and not has_ext_mark:
        return "%s: Configuration.xml не похож на расширение (нет ConfigurationExtensionPurpose): %s" % (role, path)
    if not is_ext and "ConfigurationExtensionPurpose" in text:
        return "%s: передано расширение вместо конфигурации: %s" % (role, path)
    return None


def print_report(an, show_ok):
    rep = an.rep
    print("cfe-update-impact — влияние релиза на расширение")
    print("  расширение: %s" % an.ext)
    print("  старая:     %s" % an.old)
    print("  новая:      %s" % an.new)
    for sec, title in SECTIONS.items():
        rows = [x for x in rep.items if x["section"] == sec]
        print()
        print("== %s ==" % title)
        if not rows:
            print("  (нет объектов проверки)")
            continue
        shown = 0
        for lvl in (PROBLEM, INFO, OK):
            for x in rows:
                if x["level"] != lvl or (lvl == OK and not show_ok):
                    continue
                shown += 1
                print("  [%s] %s" % (x["level"], x["where"]))
                print("      %s" % x["message"])
                for d in x["details"]:
                    print("        %s" % d)
        hidden = sum(1 for x in rows if x["level"] == OK)
        if not show_ok and hidden:
            print("  … без изменений: %d (показать: -ShowOk)" % hidden)
        elif not shown:
            print("  (нет)")
    print()
    print("== Сводка ==")
    for sec, title in SECTIONS.items():
        print("  %-62s ПРОБЛЕМА %3d · ИНФО %3d · ОК %3d" % (
            title, rep.count(sec, PROBLEM), rep.count(sec, INFO), rep.count(sec, OK)))
    total = rep.count(level=PROBLEM)
    print("  Итого проблем: %d" % total)
    if rep.count("control", PROBLEM):
        print("  Дальше: &ИзменениеИКонтроль — /cfe-patch-method -Check, затем -Actualize против НОВОЙ версии.")
    if total:
        print("  После правок: /cfe-validate, загрузка на тестовую базу и /db-cfe-admin check.")


def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(
        prog="cfe-update-impact",
        description="Влияние нового релиза конфигурации на расширение: три выгрузки Конфигуратора.")
    ap.add_argument("-ExtensionPath", required=True, help="выгрузка расширения")
    ap.add_argument("-OldConfigPath", required=True, help="выгрузка СТАРОЙ версии конфигурации")
    ap.add_argument("-NewConfigPath", required=True, help="выгрузка НОВОЙ версии конфигурации")
    ap.add_argument("-ShowOk", action="store_true", help="показывать и неизменённые пункты")
    ap.add_argument("-Diff", action="store_true", help="печатать дифф изменённых оригиналов")
    ap.add_argument("-DiffLimit", type=int, default=60, help="строк диффа на метод (по умолчанию 60)")
    ap.add_argument("-Json", help="дополнительно записать отчёт в JSON-файл")
    args = ap.parse_args()

    ext, old, new = (os.path.abspath(p) for p in (args.ExtensionPath, args.OldConfigPath, args.NewConfigPath))
    errors = [e for e in (check_dump(ext, "Расширение", True), check_dump(old, "Старая версия", False),
                          check_dump(new, "Новая версия", False)) if e]
    if errors:
        for e in errors:
            print("ОШИБКА: " + e, file=sys.stderr)
        return 2
    if os.path.normcase(old) == os.path.normcase(new):
        print("ВНИМАНИЕ: старая и новая выгрузки — один каталог, дельты релиза не будет.", file=sys.stderr)

    an = Analyzer(ext, old, new, args.Diff, max(5, args.DiffLimit))
    an.check_interceptors()
    an.check_forms()
    an.check_adopted()
    print_report(an, args.ShowOk)

    if args.Json:
        data = {"extension": ext, "old": old, "new": new,
                "summary": {sec: {lvl: an.rep.count(sec, lvl) for lvl in (PROBLEM, INFO, OK)} for sec in SECTIONS},
                "findings": an.rep.items}
        with open(args.Json, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=1)
    return 1 if an.rep.count(level=PROBLEM) else 0


if __name__ == "__main__":
    sys.exit(main())
