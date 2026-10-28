# -*- coding: utf-8 -*-
"""Builds pick lists for "Add per skill" from Windower's res, so actions can be chosen without typing names.

Spells are limited to jobs that learn them, pet moves follow SMN / BST, weapon skills are grouped by weapon type,
and abilities by ability type. res is only read.
"""
import os
import re

import ws_types as _WS
from i18n import is_en

_ID = re.compile(r'\bid=(\d+)')
_EN = re.compile(r'\ben="((?:[^"\\]|\\.)*)"')
_JA = re.compile(r'\bja="((?:[^"\\]|\\.)*)"')
_TYPE = re.compile(r'\btype="([A-Za-z]+)"')
_SKILL = re.compile(r'\bskill=(\d+)')
_LEVELS = re.compile(r'\blevels=\{([^}]*)\}')
_LEVEL = re.compile(r'\[(\d+)\]=(\d+)')

# Japanese names for ability types (res type)
JA_TYPE_NAMES = {
    "JobAbility": "ジョブアビリティ", "Scholar": "学者の章・ストラタジェム", "Waltz": "ワルツ", "Samba": "サンバ",
    "Step": "ステップ", "Jig": "ジグ", "Rune": "ルーン", "Effusion": "ランの付与", "Ward": "ウォード",
    "CorsairRoll": "ファントムロール", "CorsairShot": "クイックドロー",
}
PET_TYPE_NAMES = {
    "BloodPactRage": "契約の履行:幻術 (攻撃)", "BloodPactWard": "契約の履行:験術 (強化・弱体)",
    "Monster": "ほんきだせ・しじをさせろ の技", "PetCommand": "ペットへの指示",
}
# Group names in English (as the English client calls them)
JA_TYPE_NAMES_EN = {
    "JobAbility": "Job Abilities", "Scholar": "Stratagems", "Waltz": "Waltzes", "Samba": "Sambas",
    "Step": "Steps", "Jig": "Jigs", "Rune": "Runes", "Effusion": "Effusions", "Ward": "Wards",
    "CorsairRoll": "Phantom Rolls", "CorsairShot": "Quick Draw",
}
PET_TYPE_NAMES_EN = {
    "BloodPactRage": "Blood Pact: Rage", "BloodPactWard": "Blood Pact: Ward",
    "Monster": "Sic / Ready moves", "PetCommand": "Pet commands",
}
OTHER_EN = "Other"
RECEIVED_GROUP = ("被強化の装備", "Received buffs")


def _lang_name(ja_map, en_map, key):
    return en_map.get(key, ja_map.get(key)) if is_en() else ja_map.get(key)


# Weapon types each job can use (numbers from res/skills.lua: 1 Hand-to-Hand, 2 Dagger, 3 Sword, 4 Great Sword, 5 Axe, 6 Great Axe, 7 Scythe, 8 Polearm,
# 9 Katana, 10 Great Katana, 11 Club, 12 Staff, 25 Archery, 26 Marksmanship). Used to narrow the WS list by job.
# res has no per-job WS data, so this only filters by weapon type (job-specific limits on relic, mythic and similar WS aren't checked).
JOB_WEAPON_SKILLS = {
    "WAR": [1, 2, 3, 4, 5, 6, 7, 8, 11, 12, 25, 26],
    "MNK": [1, 11, 12],
    "WHM": [11, 12],
    "BLM": [2, 7, 11, 12],
    "RDM": [2, 3, 11, 25],
    "THF": [1, 2, 3, 11, 25, 26],
    "PLD": [2, 3, 4, 8, 11, 12],
    "DRK": [2, 3, 4, 5, 6, 7, 11, 26],
    "BST": [2, 3, 5, 7, 11],
    "BRD": [2, 3, 11, 12],
    "RNG": [2, 3, 5, 11, 25, 26],
    "SAM": [2, 3, 8, 10, 11, 25],
    "NIN": [1, 2, 3, 9, 10, 11, 25, 26],
    "DRG": [2, 3, 8, 11, 12],
    "SMN": [2, 11, 12],
    "BLU": [3, 11],
    "COR": [2, 3, 26],
    "PUP": [1, 2, 11],
    "DNC": [1, 2, 3],
    "SCH": [2, 11, 12],
    "GEO": [2, 11, 12],
    "RUN": [3, 4, 5, 6, 11],
}

# Pet moves filtered by job (every other job gets all of them)
PET_TYPES_BY_JOB = {"SMN": ["BloodPactRage", "BloodPactWard"], "BST": ["Monster", "PetCommand"]}


def _unescape(s):
    return s.replace('\\"', '"').replace("\\\\", "\\")


def _rows(res_dir, table):
    """Pull {id, en, ja, type, skill, levels} out of each line of res/<table>.lua."""
    path = os.path.join(res_dir or "", table + ".lua")
    try:
        with open(path, "rb") as f:
            text = f.read().decode("utf-8", errors="replace")
    except OSError:
        return []
    out = []
    for line in text.splitlines():
        if "=" not in line or "[" not in line:
            continue
        en, ja = _EN.search(line), _JA.search(line)
        if not (en and ja):
            continue
        row = dict(en=_unescape(en.group(1)), ja=_unescape(ja.group(1)))
        for key, rx in (("id", _ID), ("skill", _SKILL)):
            m = rx.search(line)
            row[key] = int(m.group(1)) if m else None
        m = _TYPE.search(line)
        row["type"] = m.group(1) if m else None
        lv = _LEVELS.search(line)
        row["levels"] = {int(a): int(b) for a, b in _LEVEL.findall(lv.group(1))} if lv else {}
        out.append(row)
    return out


def _skill_names(res_dir):
    col = "en" if is_en() else "ja"
    names = {r["id"]: r[col] for r in _rows(res_dir, "skills") if r["id"] is not None}
    # Spells with learn levels but no skill (Trusts, teleports, etc.) are grouped under "Other"
    return {k: (_other() if v in ("(N/A)", "N/A", "") else v) for k, v in names.items()}


def _other():
    return OTHER_EN if is_en() else "その他"


def groups_of(items):
    """Group names in the list (display order, no duplicates)."""
    seen = []
    for it in items:
        if it["group"] not in seen:
            seen.append(it["group"])
    return seen


def choices(resdb, kind, job):
    """kind: "ws" / "ja" / "magic" / "pet". Returns [{en, ja, group}] (ordered by group, then name).
    Returns an empty list when resdb isn't available."""
    if kind != "received" and (resdb is None or not resdb.available()):
        return []
    res_dir = resdb.res_dir if resdb is not None else None
    skills = _skill_names(res_dir) if res_dir else {}
    items = []
    if kind == "ws":
        allowed = JOB_WEAPON_SKILLS.get(job)
        for r in _rows(res_dir, "weapon_skills"):
            if allowed is not None and r["skill"] not in allowed:
                continue
            if job and not _WS.usable_by_job(r["en"], job):     # job-specific WS (e.g. Leaden Salute is COR only)
                continue
            items.append(dict(en=r["en"], ja=r["ja"], group=skills.get(r["skill"], _other()), order=r["skill"] or 0))
    elif kind == "magic":
        job_id = resdb._job_ids_map().get(job)
        for r in _rows(res_dir, "spells"):
            if job_id is not None and job_id in r["levels"]:
                items.append(dict(en=r["en"], ja=r["ja"], group=skills.get(r["skill"], _other()),
                                  order=(r["skill"] or 0) * 1000 + r["levels"][job_id]))
    elif kind == "ja":
        for r in _rows(res_dir, "job_abilities"):
            if r["type"] in JA_TYPE_NAMES:
                items.append(dict(en=r["en"], ja=r["ja"], group=_lang_name(JA_TYPE_NAMES, JA_TYPE_NAMES_EN, r["type"]), order=r["id"] or 0))
    elif kind == "received":
        import set_catalog as _C
        for i, (name, ja, _ids, _aoe) in enumerate(_C.RECEIVED):
            items.append(dict(en=name, ja=ja, group=RECEIVED_GROUP[1] if is_en() else RECEIVED_GROUP[0], order=i))
    elif kind == "pet":
        wanted = PET_TYPES_BY_JOB.get(job, list(PET_TYPE_NAMES))
        for r in _rows(res_dir, "job_abilities"):
            if r["type"] in wanted:
                items.append(dict(en=r["en"], ja=r["ja"], group=_lang_name(PET_TYPE_NAMES, PET_TYPE_NAMES_EN, r["type"]), order=wanted.index(r["type"]) * 100000 + (r["id"] or 0)))
    # Group order: by smallest order value, not order of appearance
    items.sort(key=lambda it: (it["order"], it["ja"]))
    seen, out = set(), []
    for it in items:
        key = (it["en"], it["group"])
        if key in seen:
            continue
        seen.add(key)
        out.append(dict(en=it["en"], ja=it["ja"], group=it["group"]))
    return out
