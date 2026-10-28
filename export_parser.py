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

SLOT_JA = {
    'main': 'メイン', 'sub': 'サブ', 'range': '遠隔', 'ammo': '矢弾', 'head': '頭', 'neck': '首',
    'left_ear': '左耳', 'right_ear': '右耳', 'body': '胴', 'hands': '手', 'left_ring': '左指',
    'right_ring': '右指', 'back': '背', 'waist': '腰', 'legs': '脚', 'feet': '足',
}

_KEY = re.compile(r'([A-Za-z_][A-Za-z_0-9]*)\s*=\s*')


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
                out.append(text[i:])
                break
            out.append(text[i:j])
            i = j
            continue
        if c == '-' and text.startswith('--', i):
            m = re.match(r'--\[(=*)\[', text[i:])
            if m:
                close = ']' + m.group(1) + ']'
                end = text.find(close, i + m.end())
                i = n if end < 0 else end + len(close)
            else:
                end = text.find('\n', i)
                i = n if end < 0 else end      # keep the newline
            continue
        out.append(c)
        i += 1
    return ''.join(out)


def parse_entries(text):
    """Return every "slot=gear" in the file in order of appearance ([Item, ...]). item= lines (non-gear items) are skipped.
    Gear inside comments (--) isn't read."""
    text = strip_comments(text)
    items = []
    i = 0
    while True:
        m = _KEY.search(text, i)
        if not m:
            break
        key = m.group(1)
        j = m.end()
        if j >= len(text):
            break
        if key not in SLOTS:
            # Not a slot (e.g. the outer sets.exported = {): keep reading inside it
            i = j
            continue
        if text[j] in ('"', "'"):
            value, nxt = _read_string(text, j)
            raw = '"%s"' % value.replace('\\', '\\\\').replace('"', '\\"')
            name = value
        elif text[j] == '{':
            raw, nxt = _read_table(text, j)
            name = _table_name(raw)
        else:
            i = j
            continue
        items.append(Item(key, name, raw))
        i = nxt   # name= and augments= inside the table were already handled when the table was read
    return items


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
