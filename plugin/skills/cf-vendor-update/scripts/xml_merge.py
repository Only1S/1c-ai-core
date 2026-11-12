"""Трёхстороннее структурное слияние XML выгрузки 1С — по элементам, а не по строкам; текст исходников сохраняется.

Основа результата — версия поставщика: неизменённые поддеревья переносятся её текстом как есть, наши правки — поддеревьями
нашей версии (переводы строк приводятся к стилю поставщика). Ключ элемента среди братьев:
  - атрибут uuid или name (реквизиты, табличные части, формы, xr:StandardAttribute, xr:GeneratedType);
  - тег, если у родителя он единственный во всех трёх версиях (свойства объекта: Name, Synonym, Type…);
  - иначе текст листа (<Catalog>Имя</Catalog> в составе конфигурации, <v8:Type>) или текст дочернего <name>/<v8:lang>
    (объект и право в Rights.xml, строка синонима на языке);
  - иначе порядковый номер среди одноимённых.
Обе стороны изменили одно место по-разному — конфликт: файл не собирается, возвращаются места конфликтов. После слияния
списка детей проверяется, что у объектов с uuid не появилось двух одинаковых имён (двойник реквизита).

Сливаются только файлы с корнем MetaDataObject (описания объектов и Configuration.xml) и Rights (права ролей) — по
содержимому, а не по имени файла. Формы, макеты, СКД, командный интерфейс, предопределённые — целиком с одной стороны:
поэлементное слияние позиционных форматов ломает импорт (vendor-release-update).
"""
import re

TOKEN = re.compile(r'<!--.*?-->|<!\[CDATA\[.*?\]\]>|<\?.*?\?>|<!DOCTYPE[^>]*>'
                   r'|<(/?)([^\s/>!?]+)((?:\s+[^\s=/>]+\s*=\s*(?:"[^"]*"|\'[^\']*\'))*)\s*(/?)>', re.S)
ATTR = re.compile(r'([^\s=/>]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\')')
MERGEABLE_ROOTS = ('MetaDataObject', 'Rights')
IDENTITY_ATTRS = ('uuid', 'name')
KEY_CHILDREN = ('name', 'lang')


class XmlError(ValueError):
    pass


class Node:
    __slots__ = ('tag', 'attrs', 'start', 'head_end', 'tail_start', 'end', 'children', 'text', 'raw_text', 'lead',
                 'mixed', 'src', '_canon')

    def __init__(self, tag, attrs, start, head_end, src):
        self.tag, self.attrs, self.start, self.head_end, self.src = tag, attrs, start, head_end, src
        self.tail_start = self.end = head_end
        self.children, self.text, self.raw_text, self.lead, self.mixed, self._canon = [], '', '', '', False, None

    def slice(self):
        return self.src[self.start:self.end]

    def child(self, local):
        return next((c for c in self.children if local_name(c.tag) == local), None)

    def prop_name(self):
        """Имя объекта метаданных: Properties/Name (или атрибут name)."""
        p = self.child('Properties')
        n = p.child('Name') if p is not None else None
        return n.text if n is not None else self.attrs.get('name', '')


def local_name(tag):
    return tag.rsplit(':', 1)[-1]


def parse(text):
    """Дерево документа с позициями в исходном тексте. Ошибка формы XML — XmlError с позицией."""
    doc = Node(None, {}, 0, 0, text)
    stack, pos = [doc], 0
    for m in TOKEN.finditer(text):
        s = text[pos:m.start()]
        top = stack[-1]
        if s.strip().strip('﻿'):
            if top is doc:
                raise XmlError('текст вне корневого элемента (позиция %d)' % pos)
            top.raw_text += s
            top.text += s.strip()
            if top.children:
                top.mixed = True
        pos = m.end()
        if m.group(2) is None:
            tok = m.group(0)
            if tok.startswith('<![CDATA['):
                top.raw_text += tok
                top.text += tok[9:-3]
            continue
        closing, tag, attrs, selfclose = m.group(1), m.group(2), m.group(3), m.group(4)
        if closing:
            node = stack.pop()
            if node is doc or node.tag != tag:
                raise XmlError('ожидался </%s>, встретился </%s> (позиция %d)' % (node.tag, tag, m.start()))
            node.tail_start, node.end = m.start(), m.end()
            continue
        node = Node(tag, {a.group(1): a.group(2) if a.group(2) is not None else a.group(3) for a in ATTR.finditer(attrs)},
                    m.start(), m.end(), text)
        prev_end = top.children[-1].end if top.children else top.head_end
        node.lead = text[prev_end:m.start()] if not text[prev_end:m.start()].strip() else ''
        if top.text and top is not doc:
            top.mixed = True
        top.children.append(node)
        if not selfclose:
            stack.append(node)
    if text[pos:].strip():
        raise XmlError('текст после корневого элемента (позиция %d)' % pos)
    if len(stack) != 1:
        raise XmlError('не закрыт элемент <%s>' % stack[-1].tag)
    if len(doc.children) != 1:
        raise XmlError('корневых элементов %d, нужен один' % len(doc.children))
    return doc


def canon(node):
    """Каноническая форма поддерева: пробелы между элементами и по краям текста не важны, порядок атрибутов тоже."""
    if node is None:
        return None
    if node._canon is None:
        node._canon = '<%s%s>%s%s</>' % (node.tag, ''.join(' %s=%s' % kv for kv in sorted(node.attrs.items())),
                                         node.text, ''.join(canon(c) for c in node.children))
    return node._canon


def root_tag(data):
    m = re.search(rb'<([A-Za-z][\w:.-]*)[\s>/]', re.sub(rb'<\?.*?\?>|<!--.*?-->', b'', data[:4096], flags=re.S))
    return m.group(1).decode('ascii', 'replace') if m else ''


def mergeable(data):
    """Файл сливается поэлементно, если его корень — описание объекта метаданных или права роли."""
    return data is not None and root_tag(data) in MERGEABLE_ROOTS


def _keys(children, repeated):
    """Ключ каждого ребёнка (см. шапку модуля); None — ключи неоднозначны (два ребёнка с одним ключом)."""
    out, seq = {}, {}
    for c in children:
        ident = next((a for a in IDENTITY_ATTRS if a in c.attrs), None)
        if ident:
            k = (c.tag, '@' + ident, c.attrs[ident])
        elif c.tag not in repeated:
            k = (c.tag,)
        elif not c.children:
            k = (c.tag, '=', c.text)
        else:
            sub = next((x for x in c.children if local_name(x.tag) in KEY_CHILDREN and not x.children), None)
            if sub is not None:
                k = (c.tag, local_name(sub.tag), sub.text)
            else:
                seq[c.tag] = seq.get(c.tag, 0) + 1
                k = (c.tag, '#', seq[c.tag])
        if k in out:
            return None
        out[k] = c
    return out


def _label(key, node):
    name = node.prop_name() if node is not None else ''
    if len(key) == 1:
        return local_name(key[0])
    return '%s[%s]' % (local_name(key[0]), name or key[2])


class Merger:
    def __init__(self, base, ours, theirs):
        self.b, self.o, self.t = parse(base), parse(ours), parse(theirs)
        self.nl = '\r\n' if '\r\n' in theirs else '\n'
        # переводы строк приводятся, только если стиль нашей версии другой: внутри значений бывает одиночный LF при CRLF
        # в разметке (пилот ERP 2.5.20), и сплошная замена изменила бы сами значения
        self.convert = ('\r\n' if '\r\n' in ours else '\n') != self.nl
        self.conflicts = []

    def conflict(self, path, why):
        self.conflicts.append({'path': '/'.join(path), 'why': why})
        return None

    def own(self, node):
        """Текст поддерева нашей версии — с переводами строк поставщика."""
        return self.own_text(node.slice())

    def run(self):
        rb, ro, rt = (d.children[0] for d in (self.b, self.o, self.t))
        if not (rb.tag == ro.tag == rt.tag):
            return self.conflict([rt.tag], 'корневые элементы разные: %s / %s / %s' % (rb.tag, ro.tag, rt.tag))
        body = self.merge(rb, ro, rt, [local_name(rt.tag)])
        if body is None:
            return None
        return self.t.src[:rt.start] + body + self.t.src[rt.end:]

    def merge_attrs(self, b, o, t, path):
        """Открывающий тег результата (без «/>»): атрибуты сливаются по ключам."""
        if o.attrs in (b.attrs, t.attrs):
            src, side = t, 't'
        elif t.attrs == b.attrs:
            src, side = o, 'o'
        else:
            merged = {}
            for k in list(t.attrs) + [k for k in o.attrs if k not in t.attrs]:
                vb, vo, vt = b.attrs.get(k), o.attrs.get(k), t.attrs.get(k)
                v = vt if vo == vb else vo if vt == vb or vo == vt else False
                if v is False:
                    return self.conflict(path, 'атрибут %s: у нас «%s», у поставщика «%s»' % (k, vo, vt))
                if v is not None:
                    merged[k] = v
            return '<%s%s>' % (t.tag, ''.join(' %s="%s"' % kv for kv in merged.items()))
        head = src.src[src.start:src.head_end]
        head = re.sub(r'\s*/>$', '>', head)
        return head if side == 't' else self.own_text(head)

    def own_text(self, s):
        if not self.convert:
            return s
        s = s.replace('\r\n', '\n')
        return s.replace('\n', self.nl) if self.nl != '\n' else s

    def merge(self, b, o, t, path):
        cb, co, ct = canon(b), canon(o), canon(t)
        if co == cb or co == ct:
            return t.slice()
        if ct == cb:
            return self.own(o)
        head = self.merge_attrs(b, o, t, path)
        if head is None:
            return None
        if b.mixed or o.mixed or t.mixed:
            return self.conflict(path, 'смешанное содержимое изменено с обеих сторон')
        # текст элемента — трёхсторонне, как значение
        if o.text == b.text:
            raw, side = t.raw_text, 't'
        elif t.text == b.text or o.text == t.text:
            raw, side = o.raw_text, 'o'
        else:
            return self.conflict(path, 'значение: у нас «%s», у поставщика «%s»' % (o.text[:80], t.text[:80]))
        if not (b.children or o.children or t.children):
            if not raw:
                return head[:-1] + '/>'
            return head + (raw if side == 't' else self.own_text(raw)) + '</%s>' % t.tag
        items = self.merge_children(b, o, t, path)
        if items is None:
            return None
        if not items and not raw.strip():
            return head[:-1] + '/>'
        out = [head]
        if raw.strip():
            out.append(raw if side == 't' else self.own_text(raw))
        for lead, s in items:
            out.append(lead + s)
        tail_src = t if t.children else o
        tail = tail_src.src[tail_src.children[-1].end:tail_src.tail_start] if tail_src.children else self.nl
        out.append((tail if tail_src is t else self.own_text(tail)) + '</%s>' % t.tag)
        return ''.join(out)

    def merge_children(self, b, o, t, path):
        repeated = set()
        for n in (b, o, t):
            seen = set()
            for c in n.children:
                (repeated.add if c.tag in seen else seen.add)(c.tag)
        kb, ko, kt = _keys(b.children, repeated), _keys(o.children, repeated), _keys(t.children, repeated)
        if kb is None or ko is None or kt is None:
            return self.conflict(path, 'дочерние элементы не различить по ключу — слить нельзя')
        result, failed = [], False   # [key, lead, text, имя результата, тег]
        for k, tn in kt.items():
            bn, on = kb.get(k), ko.get(k)
            here = path + [_label(k, tn)]
            if on is None:
                if bn is None:
                    result.append([k, tn.lead, tn.slice(), tn.prop_name(), tn.tag])
                elif canon(tn) != canon(bn):
                    failed = self.conflict(here, 'у нас удалено, поставщик изменил') or True
            elif bn is None:
                if canon(on) == canon(tn):
                    result.append([k, tn.lead, tn.slice(), tn.prop_name(), tn.tag])
                else:
                    failed = self.conflict(here, 'добавлено с обеих сторон по-разному') or True
            else:
                s = self.merge(bn, on, tn, here)
                if s is None:
                    failed = True
                else:
                    name = on.prop_name() if on.prop_name() != bn.prop_name() else tn.prop_name()
                    result.append([k, tn.lead, s, name, tn.tag])
        # наши добавления встают за ближайшим предшествующим (в нашем порядке) элементом результата; якорь None — в начало
        in_result, inserts, anchor = {r[0] for r in result}, {}, None
        for k, on in ko.items():
            if k in in_result:
                anchor = k
                continue
            if k in kt:
                continue
            bn = kb.get(k)
            if bn is not None:
                if canon(on) != canon(bn):
                    failed = self.conflict(path + [_label(k, on)], 'поставщик удалил, у нас изменено') or True
                continue
            inserts.setdefault(anchor, []).append([k, self.own_text(on.lead), self.own(on), on.prop_name(), on.tag])
        if failed:
            return None
        result = inserts.get(None, []) + [x for r in result for x in [r] + inserts.get(r[0], [])]
        names = {}
        for k, _, _, name, tag in result:
            if len(k) == 3 and k[1] == '@uuid' and name:
                if (tag, name) in names:
                    return self.conflict(path + ['%s[%s]' % (local_name(tag), name)],
                                         'двойник: одно имя, разные uuid (%s и %s)' % (names[(tag, name)], k[2]))
                names[(tag, name)] = k[2]
        return [(lead, s) for _, lead, s, _, _ in result]


def merge_bytes(base, ours, theirs):
    """Слить три версии файла. Результат — (байты или None, конфликты [{path, why}])."""
    try:
        texts = [x.decode('utf-8') for x in (base, ours, theirs)]
    except UnicodeDecodeError:
        return None, [{'path': '', 'why': 'файл не в UTF-8'}]
    try:
        m = Merger(*texts)
    except XmlError as e:
        return None, [{'path': '', 'why': 'XML не разбирается: %s' % e}]
    out = m.run()
    if out is None:
        return None, m.conflicts
    try:
        parse(out)
    except XmlError as e:   # страховка: собранный текст обязан разбираться
        return None, [{'path': '', 'why': 'результат слияния не разбирается: %s' % e}]
    return out.encode('utf-8'), []
