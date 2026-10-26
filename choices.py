# -*- coding: utf-8 -*-
"""「技ごとの追加」で、名前を打たずに選べるようにするための一覧を、Windower の res から作る。

魔法は習得レベルのあるジョブだけ・ペットの技は召喚士 / 獣使いに合わせて・ウェポンスキルは武器の種類、
アビリティは種類で、グループ分けする。res は読むだけ。
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

# アビリティの種類の日本語名 (res の type)
JA_TYPE_NAMES = {
    "JobAbility": "ジョブアビリティ", "Scholar": "学者の章・ストラタジェム", "Waltz": "ワルツ", "Samba": "サンバ",
    "Step": "ステップ", "Jig": "ジグ", "Rune": "ルーン", "Effusion": "ランの付与", "Ward": "ウォード",
    "CorsairRoll": "ファントムロール", "CorsairShot": "クイックドロー",
}
PET_TYPE_NAMES = {
    "BloodPactRage": "契約の履行:幻術 (攻撃)", "BloodPactWard": "契約の履行:験術 (強化・弱体)",
    "Monster": "ほんきだせ・しじをさせろ の技", "PetCommand": "ペットへの指示",
}
# 英語のときのグループ名 (英語クライアントの呼び方)
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


# ジョブが使える武器の種類 (res/skills.lua の番号: 1 格闘・2 短剣・3 片手剣・4 両手剣・5 片手斧・6 両手斧・7 両手鎌・8 両手槍・
# 9 片手刀・10 両手刀・11 片手棍・12 両手棍・25 弓術・26 射撃)。WS の候補をジョブで絞るために使う。
# res にはジョブごとの WS の情報が無いので、武器の種類で絞るだけ (レリック・ミシックなどジョブ専用の WS の細かい制限は見ない)。
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

# ペットの技のジョブ別の絞り込み (それ以外のジョブは、すべて出す)
PET_TYPES_BY_JOB = {"SMN": ["BloodPactRage", "BloodPactWard"], "BST": ["Monster", "PetCommand"]}


def _unescape(s):
    return s.replace('\\"', '"').replace("\\\\", "\\")


def _rows(res_dir, table):
    """res/<table>.lua の各行から {id, en, ja, type, skill, levels} を取り出す。"""
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
    # 習得レベルのある魔法のうち、スキルが無いもの (フェイス・転送など) は、「その他」にまとめる
    return {k: (_other() if v in ("(N/A)", "N/A", "") else v) for k, v in names.items()}


def _other():
    return OTHER_EN if is_en() else "その他"


def groups_of(items):
    """一覧の「グループ」の名前 (表示順・重複なし)。"""
    seen = []
    for it in items:
        if it["group"] not in seen:
            seen.append(it["group"])
    return seen


def choices(resdb, kind, job):
    """kind: "ws" / "ja" / "magic" / "pet"。戻り値: [{en, ja, group}] (グループ → 名前の順)。
    resdb が使えないときは、空のリスト。"""
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
            if job and not _WS.usable_by_job(r["en"], job):     # ジョブ専用の WS (例: レデンサリュートはコルセアだけ)
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
    # グループの並び: 出てきた順ではなく、order の小さい順
    items.sort(key=lambda it: (it["order"], it["ja"]))
    seen, out = set(), []
    for it in items:
        key = (it["en"], it["group"])
        if key in seen:
            continue
        seen.add(key)
        out.append(dict(en=it["en"], ja=it["ja"], group=it["group"]))
    return out
