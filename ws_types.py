# -*- coding: utf-8 -*-
"""ウェポンスキルの分け方 (魔法属性の WS・遠隔の WS)。

res の weapon_skills には「魔法属性か」の項目が無いので、魔法属性の WS (属性物理を含む) は、ここに英語名で持つ。
遠隔の WS は、res のスキル (弓術 25・射撃 26) のもの。名前が res と合うかは tests/test_ws.py で確かめる。
"""

# 魔法属性の WS (魔攻・魔法ダメージの装備が効くもの。属性物理の WS を含む)
MAGIC_WS = [
    # 短剣
    "Gust Slash", "Cyclone", "Energy Steal", "Energy Drain", "Aeolian Edge",
    # 片手剣
    "Burning Blade", "Red Lotus Blade", "Shining Blade", "Seraph Blade", "Sanguine Blade",
    # 両手剣
    "Frostbite", "Freezebite", "Herculean Slash",
    # 片手斧
    "Cloudsplitter", "Primal Rend",
    # 両手鎌
    "Shadow of Death", "Dark Harvest", "Infernal Scythe",
    # 両手槍
    "Thunder Thrust", "Raiden Thrust",
    # 片手刀
    "Blade: Ei", "Blade: Yu", "Blade: Teki", "Blade: To", "Blade: Chi",
    # 両手刀
    "Tachi: Goten", "Tachi: Kagero", "Tachi: Jinpu", "Tachi: Koki",
    # 片手棍
    "Shining Strike", "Seraph Strike", "Flash Nova",
    # 両手棍
    "Earth Crusher", "Rock Crusher", "Starburst", "Sunburst", "Cataclysm", "Vidohunir", "Garland of Bliss", "Omniscience",
    # 弓術・射撃 (遠隔だが魔法属性なので、こちら)
    "Flaming Arrow", "Hot Shot", "Trueflight", "Wildfire", "Leaden Salute",
]

# 遠隔の WS (res の弓術・射撃。魔法属性のものは MAGIC_WS が優先)
RANGED_WS = [
    "Flaming Arrow", "Piercing Arrow", "Dulling Arrow", "Sidewinder", "Blast Arrow", "Arching Arrow", "Empyreal Arrow",
    "Namas Arrow", "Refulgent Arrow", "Jishnu's Radiance", "Apex Arrow", "Sarv",
    "Hot Shot", "Split Shot", "Sniper Shot", "Slug Shot", "Blast Shot", "Heavy Shot", "Detonator", "Coronach",
    "Trueflight", "Leaden Salute", "Numbing Shot", "Wildfire", "Last Stand", "Terminus",
]

# クリティカルの WS (クリティカル率・クリティカルダメージの装備が効くもの)。
# 出どころ: 作者の user-globals.lua の init_weapon_skill (sets.precast.WS.Critical に分けている WS)
CRIT_WS = [
    "Backhand Blow", "Ascetic's Fury", "Stringing Pummel", "Victory Smite", "Evisceration", "Vorpal Blade",
    "Chant du Cygne", "Power Slash", "Rampage", "Keen Edge", "Raging Rush", "Vorpal Scythe", "Vorpal Thrust",
    "Skewer", "Drakesbane", "Blade: Rin", "Blade: Jin", "Blade: Hi", "True Strike", "Hexa Strike",
]

# 遠隔の WS のセット (sets.precast.WS.Range) を出すジョブ (遠隔武器が主のジョブ)
RANGED_JOBS = ("RNG", "COR")
# 遠隔の WS・遠隔攻撃のセットを出すジョブ (侍は弓を持てるので、矢弾の使い分けは無しでセットだけ)
RANGED_SET_JOBS = ("RNG", "COR", "SAM")


def kind_of(en_name):
    """WS の英語名から "RangeMagic" (魔法属性の遠隔) / "Magic" / "Range" / "Critical" / None (ふつうの近接物理)。"""
    if en_name in MAGIC_WS:
        return "RangeMagic" if en_name in RANGED_WS else "Magic"
    if en_name in RANGED_WS:
        return "Range"
    if en_name in CRIT_WS:
        return "Critical"
    return None


# ジョブ専用の WS (ミシック WS・エルゴン WS)。武器の種類が合っても、ほかのジョブのドロップダウンには出さない。
# 出どころ: FF11用語辞典 (wiki.ffo.jp/html/15881.html ミシックウェポンスキル・31448.html エルゴン)。
# レリック・エンピリアン WS は、その武器を持てるジョブなら使えるので、ここには入れない。
JOB_ONLY_WS = {
    "Ascetic's Fury": ('MNK',),  # ミシック
    'Stringing Pummel': ('PUP',),  # ミシック
    'Mandalic Stab': ('THF',),  # ミシック
    'Mordant Rime': ('BRD',),  # ミシック
    'Pyrrhic Kleos': ('DNC',),  # ミシック
    'Death Blossom': ('RDM',),  # ミシック
    'Atonement': ('PLD',),  # ミシック
    'Expiacion': ('BLU',),  # ミシック
    'Primal Rend': ('BST',),  # ミシック
    "King's Justice": ('WAR',),  # ミシック
    'Insurgency': ('DRK',),  # ミシック
    'Drakesbane': ('DRG',),  # ミシック
    'Blade: Kamu': ('NIN',),  # ミシック
    'Tachi: Rana': ('SAM',),  # ミシック
    'Mystic Boon': ('WHM',),  # ミシック
    'Vidohunir': ('BLM',),  # ミシック
    'Garland of Bliss': ('SMN',),  # ミシック
    'Omniscience': ('SCH',),  # ミシック
    'Trueflight': ('RNG',),  # ミシック
    'Leaden Salute': ('COR',),  # ミシック
    'Dimidiation': ('RUN',),  # エルゴン
    'Exudation': ('GEO',),  # エルゴン
}


def usable_by_job(en_name, job):
    """ジョブ専用の WS なら、そのジョブだけ True。それ以外の WS は True (武器の種類での絞り込みは choices で行う)。"""
    jobs = JOB_ONLY_WS.get(en_name)
    return jobs is None or job in jobs
