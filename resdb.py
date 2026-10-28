# -*- coding: utf-8 -*-
"""Look up Japanese and English names of abilities and spells from Windower's res folder (spells.lua etc.).

Stock GearSwap (Mote-Include) uses the English name (spell.english) when looking sets up by skill name.
This lets users enter Japanese names and have them written out as English names. res is only read, never modified.
"""
import os
import re

# Tables to look up for each kind (where skills come from depends on where the set goes, e.g. sets.precast.WS)
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
    """Find the res folder starting from GearSwap's data folder (.../Windower4/addons/gearswap/data)."""
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
        self._cache = {}     # table name -> [(en, ja), ...]

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
        """From an entered name (Japanese or English), return [(English name, Japanese name)] (no duplicates, in the order found)."""
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


# --- Jobs that can equip an item (jobs in res/items.lua: a sum of job bits) ---
_JOBS_MASK = re.compile(r'\bjobs=(\d+)')
_JOB_ROW = re.compile(r'\bid=(\d+).*?\bens="([A-Z]+)"')


def _read_text(path):
    try:
        with open(path, "rb") as f:
            return f.read().decode("utf-8", errors="replace")
    except OSError:
        return ""


def _job_ids(self):
    """Job abbreviation (SMN etc.) -> job id (res/jobs.lua)."""
    if getattr(self, "_job_ids_cache", None) is None:
        ids = {}
        for line in _read_text(os.path.join(self.res_dir or "", "jobs.lua")).splitlines():
            m = _JOB_ROW.search(line)
            if m:
                ids[m.group(2)] = int(m.group(1))
        self._job_ids_cache = ids
    return self._job_ids_cache


def _item_masks(self):
    """Item name (Japanese, or lowercase English) -> sum of the job bits that can use it. Different versions with the same name are combined."""
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
    """Whether the job (SMN etc.) can use the item. True if usable, False if not, None for names not in res."""
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
    """Bits for the slots the item can go in (res slots: main = 1, sub = 2, ...; versions with the same name are combined). None for names not in res."""
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
    """Item name (Japanese) -> English name. When several items share a Japanese name, the first one wins."""
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
    """Look up an item's English name from its Japanese name. None if not found."""
    if not self.available():
        return None
    return _item_names(self).get((ja_name or "").strip())


ResDB.item_en = item_en


# --- Ability types (type in res/job_abilities.lua) ---
_TYPE = re.compile(r'\btype="([A-Za-z0-9]+)"')


def ability_type(self, en_name):
    """From an ability's English name, return its res type (JobAbility, CorsairRoll, Waltz, etc.). None if not found."""
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
