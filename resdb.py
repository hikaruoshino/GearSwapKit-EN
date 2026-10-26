# -*- coding: utf-8 -*-
"""Windower の res フォルダー (spells.lua など) から、技・魔法の日本語名と英語名の対応を引く。

標準の GearSwap (Mote-Include) は、技の名前でセットを探すときに英語名 (spell.english) を使う。
日本語の名前を入れてもらい、英語名に直して書くために使う。res は読むだけで、書き換えない。
"""
import os
import re

# 種類ごとに引く表 (sets.precast.WS など、セットの置き場ごとに、技の出どころが違う)
TABLES = {
    "ws": ["weapon_skills"],
    "ja": ["job_abilities"],
    "magic": ["spells"],
    "pet": ["job_abilities", "monster_abilities", "spells"],
}

_ENTRY = re.compile(r'\[(\d+)\]\s*=\s*\{(.*)\}\s*,?\s*$')
_EN = re.compile(r'\ben\s*=\s*"((?:[^"\\]|\\.)*)"')
_JA = re.compile(r'\bja\s*=\s*"((?:[^"\\]|\\.)*)"')


def guess_res_dir(data_dir):
    """GearSwap の data フォルダー (…/Windower4/addons/gearswap/data) から、res フォルダーを探す。"""
    if not data_dir:
        return None
    d = os.path.abspath(data_dir)
    for up in range(1, 6):
        d = os.path.dirname(d)
        cand = os.path.join(d, "res")
        if os.path.isfile(os.path.join(cand, "spells.lua")):
            return cand
    return None


def _unescape(s):
    return s.replace('\\"', '"').replace("\\\\", "\\")


class ResDB:
    def __init__(self, res_dir):
        self.res_dir = res_dir
        self._cache = {}     # 表の名前 -> [(en, ja), ...]

    def available(self):
        return bool(self.res_dir) and os.path.isfile(os.path.join(self.res_dir, "spells.lua"))

    def _load(self, table):
        if table in self._cache:
            return self._cache[table]
        rows = []
        path = os.path.join(self.res_dir or "", table + ".lua")
        try:
            with open(path, "rb") as f:
                text = f.read().decode("utf-8", errors="replace")
        except OSError:
            self._cache[table] = rows
            return rows
        for line in text.splitlines():
            m = _ENTRY.search(line)
            if not m:
                continue
            body = m.group(2)
            en = _EN.search(body)
            ja = _JA.search(body)
            if en and ja:
                rows.append((_unescape(en.group(1)), _unescape(ja.group(1))))
        self._cache[table] = rows
        return rows

    def names(self, kind, name):
        """入力した名前 (日本語・英語どちらでも) から、[(英語名, 日本語名)] を返す (重複なし・見つかった順)。"""
        key = (name or "").strip()
        if not key:
            return []
        low = key.lower()
        found = []
        for table in TABLES.get(kind, []):
            for en, ja in self._load(table):
                if ja == key or en.lower() == low:
                    pair = (en, ja)
                    if pair not in found:
                        found.append(pair)
        return found


# --- 装備できるジョブ (res/items.lua の jobs・ジョブの印の足し合わせ) ---
_JOBS_MASK = re.compile(r'\bjobs=(\d+)')
_JOB_ROW = re.compile(r'\bid=(\d+).*?\bens="([A-Z]+)"')


def _read_text(path):
    try:
        with open(path, "rb") as f:
            return f.read().decode("utf-8", errors="replace")
    except OSError:
        return ""


def _job_ids(self):
    """ジョブの略称 (SMN など) -> ジョブ番号 (res/jobs.lua)。"""
    if getattr(self, "_job_ids_cache", None) is None:
        ids = {}
        for line in _read_text(os.path.join(self.res_dir or "", "jobs.lua")).splitlines():
            m = _JOB_ROW.search(line)
            if m:
                ids[m.group(2)] = int(m.group(1))
        self._job_ids_cache = ids
    return self._job_ids_cache


def _item_masks(self):
    """装備の名前 (日本語・英語の小文字) -> 使えるジョブの印の足し合わせ。同じ名前の別の版は、足し合わせる。"""
    if getattr(self, "_item_masks_cache", None) is None:
        masks = {}
        for line in _read_text(os.path.join(self.res_dir or "", "items.lua")).splitlines():
            jm = _JOBS_MASK.search(line)
            if not jm:
                continue
            en = _EN.search(line)
            ja = _JA.search(line)
            mask = int(jm.group(1))
            for nm in ((ja.group(1) if ja else None), (en.group(1).lower() if en else None)):
                if nm:
                    masks[nm] = masks.get(nm, 0) | mask
        self._item_masks_cache = masks
    return self._item_masks_cache


def usable_by(self, item_name, job):
    """その装備を、そのジョブ (SMN など) が使えるか。使える True・使えない False・res に無い名前は None。"""
    if not self.available():
        return None
    key = (item_name or "").strip()
    mask = _item_masks(self).get(key)
    if mask is None:
        mask = _item_masks(self).get(key.lower())
    if mask is None:
        return None
    jid = _job_ids(self).get(job)
    if jid is None:
        return None
    return bool((mask >> jid) & 1)


ResDB.usable_by = usable_by

_SLOTS = re.compile(r'\bslots=(\d+)')


def item_slots(self, item_name):
    """その装備を着られる部位の印 (res の slots。メイン = 1・サブ = 2 …。同じ名前の別の版は足し合わせる)。res に無い名前は None。"""
    if not self.available():
        return None
    if getattr(self, "_item_slots_cache", None) is None:
        cache = {}
        for line in _read_text(os.path.join(self.res_dir or "", "items.lua")).splitlines():
            sm = _SLOTS.search(line)
            if not sm:
                continue
            en, ja = _EN.search(line), _JA.search(line)
            for nm in ((ja.group(1) if ja else None), (en.group(1).lower() if en else None)):
                if nm:
                    cache[nm] = cache.get(nm, 0) | int(sm.group(1))
        self._item_slots_cache = cache
    key = (item_name or "").strip()
    found = self._item_slots_cache.get(key)
    return found if found is not None else self._item_slots_cache.get(key.lower())


ResDB.item_slots = item_slots


ResDB._job_ids_map = _job_ids


def _item_names(self):
    """装備の名前 (日本語) -> 英語名。同じ日本語名が複数あるときは、最初のもの。"""
    if getattr(self, "_item_names_cache", None) is None:
        names = {}
        for line in _read_text(os.path.join(self.res_dir or "", "items.lua")).splitlines():
            en = _EN.search(line)
            ja = _JA.search(line)
            if en and ja:
                names.setdefault(_unescape(ja.group(1)), _unescape(en.group(1)))
        self._item_names_cache = names
    return self._item_names_cache


def item_en(self, ja_name):
    """装備の日本語名から英語名を引く。見つからなければ None。"""
    if not self.available():
        return None
    return _item_names(self).get((ja_name or "").strip())


ResDB.item_en = item_en


# --- アビリティの種類 (res/job_abilities.lua の type) ---
_TYPE = re.compile(r'\btype="([A-Za-z0-9]+)"')


def ability_type(self, en_name):
    """アビリティの英語名から、res の type (JobAbility・CorsairRoll・Waltz など) を返す。無ければ None。"""
    if not self.available():
        return None
    if getattr(self, "_ability_types_cache", None) is None:
        types = {}
        for line in _read_text(os.path.join(self.res_dir or "", "job_abilities.lua")).splitlines():
            en = _EN.search(line)
            t = _TYPE.search(line)
            if en and t:
                types.setdefault(_unescape(en.group(1)), t.group(1))
        self._ability_types_cache = types
    return self._ability_types_cache.get(en_name)


ResDB.ability_type = ability_type
