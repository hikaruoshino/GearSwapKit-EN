# -*- coding: utf-8 -*-
"""Read the Lua written by GearSwap's export (//gs export).

Two formats are supported:
  1. Equipped set   : sets.exported = { main="...", head={ name="...", augments={...} }, ... }  (one per slot)
  2. Inventory list : lines with the same slot name repeat (with "item=" lines mixed in)

The Lua isn't executed; only strings and matching { } are looked at (so files received from others are safe).
"""
import re

SLOTS = ['main', 'sub', 'range', 'ammo', 'head', 'neck', 'left_ear', 'right_ear', 'body',
         'hands', 'left_ring', 'right_ring', 'back', 'waist', 'legs', 'feet']

# Slot aliases GearSwap accepts (slot_map in GearSwap/statics.lua). //gs export itself only writes the full names,
# but hand-edited or shared sets can use them
SLOT_ALIASES = {
    'ranged': 'range',
    'ear1': 'left_ear', 'ear2': 'right_ear', 'lear': 'left_ear', 'rear': 'right_ear',
    'learring': 'left_ear', 'rearring': 'right_ear',
    'ring1': 'left_ring', 'ring2': 'right_ring', 'lring': 'left_ring', 'rring': 'right_ring',
}

SLOT_JA = {
    'main': 'メイン', 'sub': 'サブ', 'range': '遠隔', 'ammo': '矢弾', 'head': '頭', 'neck': '首',
    'left_ear': '左耳', 'right_ear': '右耳', 'body': '胴', 'hands': '手', 'left_ring': '左指',
    'right_ring': '右指', 'back': '背', 'waist': '腰', 'legs': '脚', 'feet': '足',
}

_KEY = re.compile(r'([A-Za-z_][A-Za-z_0-9]*)\s*=\s*')
# Inside a { ... } table, a slot= after a newline means the closing brace was forgotten and the next line's gear got swallowed
_SLOT_NAMES = '|'.join(sorted(SLOTS + list(SLOT_ALIASES), key=len, reverse=True))
_SLOT_IN_TABLE = re.compile(r'\n\s*(?:%s)\s*=' % _SLOT_NAMES)
_ITEM_TABLE = re.compile(r'\{\s*name\s*=')      # one item's table { name="...", augments={...} }
_NO_EQUALS = re.compile(r'(?:^|[{,])[ \t]*(%s)[ \t]*["\'{]' % _SLOT_NAMES, re.M)


class Item:
    """One piece of gear. raw is the notation that can be written into Lua as is ("name" or { name=..., augments=... })."""

    def __init__(self, slot, name, raw):
        self.slot = slot
        self.name = name
        self.raw = raw

    def __repr__(self):
        return 'Item(%s, %s)' % (self.slot, self.name)

    def __eq__(self, other):
        return isinstance(other, Item) and self.slot == other.slot and self.raw == other.raw

    def __hash__(self):
        return hash((self.slot, self.raw))


def _read_string(text, i):
    """When text[i] is a quote, return (string contents, next position)."""
    quote = text[i]
    j = i + 1
    out = []
    while j < len(text):
        c = text[j]
        if c == '\\' and j + 1 < len(text):
            out.append(text[j + 1])
            j += 2
            continue
        if c == quote:
            return ''.join(out), j + 1
        if c == '\n':
            break                       # a Lua "..." string can't span lines (missing closing quote)
        out.append(c)
        j += 1
    raise ValueError('文字列が閉じていません')


def _read_table(text, i):
    """When text[i] == '{', return the text up to the matching '}' (both braces included) and the next position."""
    depth = 0
    j = i
    while j < len(text):
        c = text[j]
        if c in ('"', "'"):
            _, j = _read_string(text, j)
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return text[i:j + 1], j + 1
        j += 1
    raise ValueError('{ } が閉じていません')


def _table_name(raw):
    m = re.search(r'name\s*=\s*', raw)
    if not m:
        return ''
    k = m.end()
    if k < len(raw) and raw[k] in ('"', "'"):
        name, _ = _read_string(raw, k)
        return name
    return ''


def strip_comments(text):
    """Strip Lua comments (-- to end of line, and multi-line --[[ ... ]] / --[==[ ... ]==]). A -- inside a string is kept.
    This way, gear lines commented out by hand-editing an export file aren't read."""
    out = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in ('"', "'"):
            try:
                _value, j = _read_string(text, i)
            except ValueError:
                j = text.find('\n', i)          # unclosed quote: keep the rest of the line as is and carry on
                j = n if j < 0 else j
            out.append(text[i:j])
            i = j
            continue
        if c == '-' and text.startswith('--', i):
            m = re.match(r'--\[(=*)\[', text[i:])
            if m:
                close = ']' + m.group(1) + ']'
                end = text.find(close, i + m.end())
                stop = n if end < 0 else end + len(close)
                out.append('\n' * text.count('\n', i, stop))   # keep the newlines so line numbers don't shift
                i = stop
            else:
                end = text.find('\n', i)
                i = n if end < 0 else end      # keep the newline
            continue
        out.append(c)
        i += 1
    return ''.join(out)


def _scan(text):
    """Return (gear read [Item, ...], spots that couldn't be read [positions in the comment-stripped text, ...], the comment-stripped text).
    Spots that couldn't be read = a slot name whose value isn't "..." / { ... } (ear1== etc.), an unclosed quote or { },
    or a non-slot name with what looks like an item name (lefft_ear="..." etc.)."""
    text = strip_comments(text)
    items, unread = [], []
    i = 0
    while True:
        m = _KEY.search(text, i)
        if not m:
            break
        key = SLOT_ALIASES.get(m.group(1), m.group(1))
        j = m.end()
        if j >= len(text):
            if key in SLOTS:
                unread.append(m.start())
            break
        if key not in SLOTS:
            # Not a slot (e.g. the outer sets.exported = {): keep reading inside it.
            # But if it carries a gear-shaped value ("..." or { name=... }), it's a misspelled slot name (lefft_ear etc.)
            if key not in ('item', 'name') and (text[j] in ('"', "'") or _ITEM_TABLE.match(text, j)):
                unread.append(m.start())
                if text[j] == '{':
                    try:
                        _raw, i = _read_table(text, j)
                        continue
                    except ValueError:
                        pass
            i = j
            continue
        try:
            if text[j] in ('"', "'"):
                value, nxt = _read_string(text, j)
                raw = '"%s"' % value.replace('\\', '\\\\').replace('"', '\\"')
                name = value
            elif text[j] == '{':
                raw, nxt = _read_table(text, j)
                if _SLOT_IN_TABLE.search(raw):
                    raise ValueError('{ } が閉じていません')   # missing closing brace: it swallowed the next line's slot
                name = _table_name(raw)
            elif re.match(r'empty\b', text[j:j + 6]):
                i = j + 5            # sub=empty (GearSwap's "wear nothing") isn't treated as gear
                continue
            else:
                unread.append(m.start())     # a variable (gear.X etc.) or a typo (ear1== etc.)
                i = j
                continue
            if '=' in name and text[j] != '{':
                # Item names never contain = (checked against res): a missing closing quote read on into the next item on the same line (compact format).
                # Skip this item and re-read from just after its opening quote (the next item then reads correctly with its own quotes)
                unread.append(m.start())
                i = j + 1
                continue
        except ValueError:
            unread.append(m.start())     # unclosed quote or { }: skip this line and carry on from the next one
            nl = text.find('\n', j)
            if nl < 0:
                break
            i = nl
            continue
        if not (name or "").strip():
            i = nxt          # an empty item such as head="" is not treated as gear
            continue
        items.append(Item(key, name, raw))
        i = nxt   # name= and augments= inside the table were already handled when the table was read
    # A missing = (neck"..." / neck "..."): a slot name and a value at the start of a line or right after { or ,
    for m in _NO_EQUALS.finditer(text):
        unread.append(m.start(1))
    unread.sort()
    return items, unread, text


def parse_entries(text):
    """Return every "slot=gear" in the file in order of appearance ([Item, ...]). item= lines (non-gear items) are skipped.
    Gear inside comments (--) isn't read."""
    return _scan(text)[0]


def unread_lines(text):
    """Return the lines that look like gear but couldn't be read, as [(line number, line text), ...] (to flag typos made when editing by hand)."""
    _items, unread, stripped = _scan(text)
    out = []
    for pos in unread:
        no = stripped.count('\n', 0, pos) + 1
        if not out or out[-1][0] != no:
            # The line text runs from the unread slot name to the end of the line (so even a one-line file shows which item it is)
            end = stripped.find('\n', pos)
            out.append((no, stripped[pos:end if end >= 0 else len(stripped)].strip()))
    return out


def parse_equipped_set(text):
    """Return the equipped set as {slot: Item}. If a slot appears more than once, the first one is used."""
    result = {}
    for it in parse_entries(text):
        result.setdefault(it.slot, it)
    return result


def parse_inventory(text):
    """Return the inventory list as {slot: [Item, ...]} (duplicates removed)."""
    result = {}
    for it in parse_entries(text):
        lst = result.setdefault(it.slot, [])
        if it not in lst:
            lst.append(it)
    return result


def looks_like_inventory(text):
    """Treat the text as an inventory list if any slot appears twice or more, or if there are item= lines."""
    seen = set()
    for it in parse_entries(text):
        if it.slot in seen:
            return True
        seen.add(it.slot)
    return bool(re.search(r'^\s*item\s*=', strip_comments(text), re.M))


def read_file(path):
    with open(path, 'rb') as f:
        data = f.read()
    for enc in ('utf-8-sig', 'cp932'):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            pass
    return data.decode('utf-8', errors='replace')


def weapon_candidates(inventory, slot, resdb=None):
    """From an inventory list (the result of parse_inventory), return the weapon candidates usable in that slot.
    main = main lines; sub = sub lines + main lines (for dual-wielding one-handed weapons); range = range lines; ammo = ammo lines."""
    # //gs export all writes one-handed weapons (Burtgang etc.) as sub=, so sub lines are included in the main candidates too.
    # With res available, items that can't go in main (shields, grips) are excluded
    keys = {"main": ["main", "sub"], "sub": ["sub", "main"], "range": ["range"], "ammo": ["ammo"]}.get(slot, [])
    out = []
    for key in keys:
        for it in inventory.get(key, []):
            if slot == "main" and key == "sub" and resdb is not None:
                mask = resdb.item_slots(it.name)
                if mask is not None and not (mask & 1):
                    continue
            cand = Item(slot, it.name, it.raw)
            if cand not in out:
                out.append(cand)
    return out
