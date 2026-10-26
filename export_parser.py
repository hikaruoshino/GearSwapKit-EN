# -*- coding: utf-8 -*-
"""GearSwap の export (//gs export) の Lua を読む。

2 種類の形式を読める:
  1. 装備中のセット   : sets.exported = { main="…", head={ name="…", augments={…} }, … }  (スロットごとに 1 つ)
  2. 所持品の一覧     : 同じスロット名の行が重複して並ぶ ("item=" の行も混ざる)

Lua を実行せず、文字列と { } の対応だけを見て読む (他人から受け取ったファイルでも安全)。
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
    """装備 1 つ。raw は Lua にそのまま書ける表記 ("名前" か { name=…, augments=… })。"""

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
    """text[i] が引用符のとき、(文字列の中身, 次の位置) を返す。"""
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
    """text[i] == '{' のとき、対応する '}' までの文字列 (両端を含む) と次の位置を返す。"""
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
    """Lua のコメント (-- から行末まで・--[[ … ]] / --[==[ … ]==] の複数行) を取り除く。文字列の中の -- は残す。
    export のファイルを手で直して、装備の行をコメントアウトしていても、その装備を読まないようにするため。"""
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
                i = n if end < 0 else end      # 改行は残す
            continue
        out.append(c)
        i += 1
    return ''.join(out)


def parse_entries(text):
    """ファイル内の「スロット=装備」を、出てきた順に全部返す ([Item, …])。item= の行 (アイテム) は除く。
    コメント (--) の中の装備は読まない。"""
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
            # スロット以外 (sets.exported = { の外側など) は、中身を読み続ける
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
        i = nxt   # 表の中の name= や augments= は、この表の読み取りで済んでいる
    return items


def parse_equipped_set(text):
    """装備中のセットを {スロット: Item} で返す。同じスロットが複数あれば、最初のものを使う。"""
    result = {}
    for it in parse_entries(text):
        result.setdefault(it.slot, it)
    return result


def parse_inventory(text):
    """所持品の一覧を {スロット: [Item, …]} で返す (重複は除く)。"""
    result = {}
    for it in parse_entries(text):
        lst = result.setdefault(it.slot, [])
        if it not in lst:
            lst.append(it)
    return result


def looks_like_inventory(text):
    """同じスロットが 2 回以上出る、または item= の行があれば、所持品の一覧とみなす。"""
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
    """所持品の一覧 (parse_inventory の結果) から、そのスロットに使える武器の候補を返す。
    メイン = main の行・サブ = sub の行 + main の行 (片手武器を二刀流で持つため)・遠隔 = range の行・矢弾 = ammo の行。"""
    # //gs export all は、片手武器 (ブルトガングなど) を sub= として書き出すので、メインの候補には sub の行も入れる。
    # res があれば、メインに装備できないもの (盾・グリップ) は除く
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
