# -*- coding: utf-8 -*-
"""Table of gear that enhances job abilities (certain relic and empyrean armor pieces), matched against your inventory.

The table (ability_gear.json) was built from each armor set's page on the Japanese FF11 wiki (wiki.ffo.jp).
Upgrading changes a piece's name (Glyphic Horn -> Glyphic Horn +1 -> ...), so the name of every stage is kept.
Names are matched against the inventory list (//gs export all), and only gear you own becomes a candidate.
"""
import json
import os
import sys

# In the EXE (Nuitka onefile build), ability_gear.json is bundled inside (--include-data-files) and read from the extraction folder (next to __file__)
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(HERE, "ability_gear.json")

TIMING_NAMES = {"use": "使う瞬間だけ着る", "while_active": "効果中ずっと着る",
                "merit": "メリット特性 (//gs c cycle MeritGear を On にしたときに着る。からくり士・竜騎士はペットがいる間)",
                "cast": "その強化が効いている間に、魔法・ウェポンスキル・遠隔攻撃をするときに着る",
                "spell": "決まった魔法 (陣の魔法など) を唱えるとき、詠唱の開始と詠唱中に着る"}
TIMING_SETS = {"use": "sets.precast.JA", "while_active": "sets.buff", "merit": "sets.merit", "cast": "sets.buff",
               "spell": "sets"}
CAST_PHASE_NAMES = {"precast": "始めるとき", "midcast": "行動中 (詠唱中・遠隔攻撃中)", "both": "始めるときと行動中の両方"}
CAST_ON_NAMES = {"Magic": "魔法", "WeaponSkill": "ウェポンスキル", "Ranged Attack": "遠隔攻撃"}

# English (the current language is picked in timing_name and friends)
TIMING_NAMES_EN = {"use": "worn only the moment you use it", "while_active": "kept on while the effect is active",
                   "merit": "merit trait (worn when //gs c cycle MeritGear is On; PUP/DRG only while the pet is out)",
                   "cast": "worn for spells, weapon skills or ranged attacks while the buff is active",
                   "spell": "worn in precast and midcast of specific spells (e.g. storms)"}
CAST_PHASE_NAMES_EN = {"precast": "on start", "midcast": "during the action (midcast / ranged attack)",
                       "both": "on start and during the action"}
CAST_ON_NAMES_EN = {"Magic": "spells", "WeaponSkill": "weapon skills", "Ranged Attack": "ranged attacks"}


def _pick(ja, en, key):
    from i18n import is_en
    d = en if is_en() else ja
    return d.get(key, ja.get(key, key))


def timing_name(key):
    """TIMING_NAMES text in the current language. Unknown keys are returned as-is."""
    return _pick(TIMING_NAMES, TIMING_NAMES_EN, key)


def cast_phase_name(key):
    return _pick(CAST_PHASE_NAMES, CAST_PHASE_NAMES_EN, key)


def cast_on_name(key):
    return _pick(CAST_ON_NAMES, CAST_ON_NAMES_EN, key)


def load(path=None):
    """Load the table. Returns {job: [entries]}, or empty if it can't be read."""
    try:
        with open(path or DATA_PATH, "rb") as f:
            data = json.loads(f.read().decode("utf-8"))
    except (OSError, ValueError):
        return {}
    return data.get("jobs", {})


def entries_for_job(job, table=None):
    table = table if table is not None else load()
    return list(table.get(job, []))


def _keys(name, resdb):
    """Keys for matching gear names: the Japanese name, plus the English name (lowercase) if res has it."""
    keys = {name}
    if resdb is not None and resdb.available():
        en = resdb.item_en(name)
        if en:
            keys.add(en.lower())
    return keys


def owned(entry, inventory, resdb=None):
    """Pieces from the entry that are in the inventory. inventory is the result of export_parser.parse_inventory ({slot: [Item]}).
    Returns [(stage number, table gear, Item)] (lowest stage first). Same-named pieces with different augments are returned separately."""
    have = inventory.get(entry["slot"], [])
    out = []
    for gen, spec in enumerate(entry["items"]):
        keys = _keys(spec["ja"], resdb)
        for it in have:
            if it.name in keys or it.name.lower() in keys:
                out.append((gen, spec, it))
    return out


def best_owned(entry, inventory, resdb=None):
    """The single highest-stage piece you own, or None."""
    found = owned(entry, inventory, resdb)
    return found[-1] if found else None


def pick_key(entry):
    """The unit the UI narrows down to one: ability, slot and usage (on-use and while-active get separate sets even for the same ability and slot)."""
    return (entry["ability_en"], entry["slot"], entry["timing"])


def describe(entry):
    """One-line description for the UI."""
    from i18n import is_en
    if is_en():
        # effect (the source text) only exists in Japanese, so in English show just the ability name, slot and usage
        return "%s (%s) [%s]" % (entry["ability_en"], entry.get("slot", ""), timing_name(entry["timing"]))
    return "%s: %s [%s]" % (entry["ability_ja"], entry["effect"], TIMING_NAMES.get(entry["timing"], entry["timing"]))
