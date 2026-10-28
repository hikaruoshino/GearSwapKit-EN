# -*- coding: utf-8 -*-
"""Adds up gear Fast Cast (%) from Windower's res (used to time the PLD 3-stage swap).

- Gear stats: "Fast Cast"+N% in the English description in res/item_descriptions.lua  (name -> ID via res/items.lua)
- Augments: '"Fast Cast"+N' in the export's augments
When several versions share a name (e.g. Lv75 and Lv99), the larger value is used. res is only read.
"""
import os
import re

from i18n import L

_ITEM = re.compile(r'^\s*\[(\d+)\]\s*=\s*\{id=\d+,en="((?:[^"\\]|\\.)*)",ja="((?:[^"\\]|\\.)*)"')
_DESC = re.compile(r'^\s*\[(\d+)\]\s*=\s*\{id=\d+,en="((?:[^"\\]|\\.)*)"')
_FC_DESC = re.compile(r'(?:\\")?Fast Cast(?:\\")?\s*\+(\d+)%')
# Wording with no number (e.g. Orunmila's Torque: Increases "Fast Cast" effect). The value is unknown, so the UI flags it
_FC_VAGUE = re.compile(r'(?:Increases|Enhances) (?:\\")?Fast Cast(?:\\")? effect')
_FC_AUG = re.compile(r'"Fast Cast"\s*\+(\d+)')

# Values for gear whose description has no number (Increases "Fast Cast" effect, etc.).
# Orunmila's Torque = +5%: confirmed from the gap between the author's PLD FC set total (sets.precast.FC.value = 69) and the other gear's 64% (2026-10-26)
KNOWN_VAGUE = {"オルンミラトルク": 5, "orunmila's torque": 5}

_cache = {}


def _read(path):
    try:
        with open(path, "rb") as f:
            return f.read().decode("utf-8", errors="replace")
    except OSError:
        return ""


def _tables(res_dir):
    """(name -> [IDs], ID -> Fast Cast from the description). Read only once per res_dir."""
    if res_dir in _cache:
        return _cache[res_dir]
    ids = {}
    for line in _read(os.path.join(res_dir, "items.lua")).splitlines():
        m = _ITEM.match(line)
        if m:
            for nm in (m.group(3), m.group(2).lower()):
                ids.setdefault(nm, []).append(int(m.group(1)))
    fc = {}
    for line in _read(os.path.join(res_dir, "item_descriptions.lua")).splitlines():
        m = _DESC.match(line)
        if m:
            f = _FC_DESC.search(m.group(2))
            if f:
                fc[int(m.group(1))] = int(f.group(1))
            elif _FC_VAGUE.search(m.group(2)):
                fc[int(m.group(1))] = None
    _cache[res_dir] = (ids, fc)
    return _cache[res_dir]


def item_fast_cast(res_dir, item):
    """Fast Cast of one piece of gear (export_parser.Item). Returns (base stat + augment %, whether its description has Fast Cast with no number)."""
    total = sum(int(x) for x in _FC_AUG.findall(item.raw or ""))
    vague = False
    if res_dir:
        ids, fc = _tables(res_dir)
        name = (item.name or "").strip()
        found = ids.get(name) or ids.get(name.lower()) or []
        vals = [fc[i] for i in found if i in fc]
        nums = [v for v in vals if v is not None]
        known = KNOWN_VAGUE.get(name, KNOWN_VAGUE.get(name.lower()))
        if nums:
            total += max(nums)
        elif known is not None:
            total += known
        elif vals:
            vague = True
    return total, vague


FC_CAP = 80          # Fast Cast cap (gear and traits combined)
MAIN_RDM_FC = 38     # Red Mage (main) trait + Job Points (same value as the author's PLD.lua)
SUB_RDM_FC = 15      # /RDM trait (20 at Master Level 30+)


def advice(total, job):
    """Warn when the gear Fast Cast total goes over the cap and is wasted. Empty if there's no problem."""
    if total <= 0:
        return ""
    if job == "RDM":
        whole = total + MAIN_RDM_FC
        if whole > FC_CAP:
            return L("赤魔道士の特性 %d%% を足すと %d%% で、上限 %d%% を %d%% 超えています。超えた分は無駄なので、"
                     "その部位をほかの性能の装備に替えられます。" % (MAIN_RDM_FC, whole, FC_CAP, whole - FC_CAP),
                     "With Red Mage's own %d%% Fast Cast trait you're at %d%%, %d%% over the %d%% cap. "
                     "That extra is wasted, so those slots could go to other stats." % (MAIN_RDM_FC, whole, whole - FC_CAP, FC_CAP))
        return ""
    if total > FC_CAP:
        return L("装備だけで上限 %d%% を %d%% 超えています。超えた分は無駄なので、その部位をほかの性能の装備に替えられます。"
                 % (FC_CAP, total - FC_CAP),
                 "Your gear alone is %d%% over the %d%% cap. That extra is wasted, so those slots could go to other stats."
                 % (total - FC_CAP, FC_CAP))
    if total + SUB_RDM_FC > FC_CAP:
        return L("サポ赤にすると、特性 %d%% (マスターレベル 30 以上は 20%%) が足されて %d%% 以上になり、上限 %d%% を超えます。"
                 "サポ赤で使うなら、%d%% 分はほかの性能の装備に替えられます。"
                 % (SUB_RDM_FC, total + SUB_RDM_FC, FC_CAP, total + SUB_RDM_FC - FC_CAP),
                 "With /RDM, the subjob trait adds %d%% (20%% at Master Level 30+), putting you at %d%% or more, over the %d%% cap. "
                 "If you play /RDM, you can spare %d%% of Fast Cast for other stats."
                 % (SUB_RDM_FC, total + SUB_RDM_FC, FC_CAP, total + SUB_RDM_FC - FC_CAP))
    return ""


def set_fast_cast(res_dir, items):
    """Total Fast Cast (%) of a set ({slot: Item}).
    Returns (total, [(slot, name, value)] for values above 0, [names] of Fast Cast gear with unknown values)."""
    rows, unknown = [], []
    for slot, it in (items or {}).items():
        v, vague = item_fast_cast(res_dir, it)
        if v:
            rows.append((slot, it.name, v))
        if vague:
            unknown.append(it.name)
    return sum(v for _s, _n, v in rows), rows, unknown
