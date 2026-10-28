# -*- coding: utf-8 -*-
"""Weapon skill categories (magical WS, ranged WS).

res weapon_skills has no "is magical" field, so magical weapon skills (hybrids included) are listed here by English name.
Ranged weapon skills are those of the res skills Archery (25) and Marksmanship (26). tests/test_ws.py checks that the names match res.
"""

# Magical weapon skills (where Magic Attack / Magic Damage gear applies; hybrid weapon skills included)
MAGIC_WS = [
    # Dagger
    "Gust Slash", "Cyclone", "Energy Steal", "Energy Drain", "Aeolian Edge",
    # Sword
    "Burning Blade", "Red Lotus Blade", "Shining Blade", "Seraph Blade", "Sanguine Blade",
    # Great Sword
    "Frostbite", "Freezebite", "Herculean Slash",
    # Axe
    "Cloudsplitter", "Primal Rend",
    # Scythe
    "Shadow of Death", "Dark Harvest", "Infernal Scythe",
    # Polearm
    "Thunder Thrust", "Raiden Thrust",
    # Katana
    "Blade: Ei", "Blade: Yu", "Blade: Teki", "Blade: To", "Blade: Chi",
    # Great Katana
    "Tachi: Goten", "Tachi: Kagero", "Tachi: Jinpu", "Tachi: Koki",
    # Club
    "Shining Strike", "Seraph Strike", "Flash Nova",
    # Staff
    "Earth Crusher", "Rock Crusher", "Starburst", "Sunburst", "Cataclysm", "Vidohunir", "Garland of Bliss", "Omniscience",
    # Archery / Marksmanship (ranged, but magical, so they go here)
    "Flaming Arrow", "Hot Shot", "Trueflight", "Wildfire", "Leaden Salute",
]

# Ranged weapon skills (res Archery / Marksmanship; MAGIC_WS takes precedence for magical ones)
RANGED_WS = [
    "Flaming Arrow", "Piercing Arrow", "Dulling Arrow", "Sidewinder", "Blast Arrow", "Arching Arrow", "Empyreal Arrow",
    "Namas Arrow", "Refulgent Arrow", "Jishnu's Radiance", "Apex Arrow", "Sarv",
    "Hot Shot", "Split Shot", "Sniper Shot", "Slug Shot", "Blast Shot", "Heavy Shot", "Detonator", "Coronach",
    "Trueflight", "Leaden Salute", "Numbing Shot", "Wildfire", "Last Stand", "Terminus",
]

# Critical weapon skills (where Critical hit rate / Critical hit damage gear applies).
# Source: init_weapon_skill in the author's user-globals.lua (the weapon skills split out into sets.precast.WS.Critical)
CRIT_WS = [
    "Backhand Blow", "Ascetic's Fury", "Stringing Pummel", "Victory Smite", "Evisceration", "Vorpal Blade",
    "Chant du Cygne", "Power Slash", "Rampage", "Keen Edge", "Raging Rush", "Vorpal Scythe", "Vorpal Thrust",
    "Skewer", "Drakesbane", "Blade: Rin", "Blade: Jin", "Blade: Hi", "True Strike", "Hexa Strike",
]

# Jobs that get the ranged WS set (sets.precast.WS.Range) (jobs that mainly use ranged weapons)
RANGED_JOBS = ("RNG", "COR")
# Jobs that get the ranged WS and ranged attack sets (SAM can use bows, so it gets the sets but no ammo switching)
RANGED_SET_JOBS = ("RNG", "COR", "SAM")


def kind_of(en_name):
    """From a WS English name: "RangeMagic" (magical ranged) / "Magic" / "Range" / "Critical" / None (regular physical melee)."""
    if en_name in MAGIC_WS:
        return "RangeMagic" if en_name in RANGED_WS else "Magic"
    if en_name in RANGED_WS:
        return "Range"
    if en_name in CRIT_WS:
        return "Critical"
    return None


# Job-exclusive weapon skills (Mythic and Ergon). Not shown in other jobs' dropdowns even if the weapon type matches.
# Source: the Japanese FF11 wiki (wiki.ffo.jp/html/15881.html for Mythic weapon skills, 31448.html for Ergon).
# Relic and Empyrean weapon skills are usable by any job that can equip the weapon, so they aren't listed here.
JOB_ONLY_WS = {
    "Ascetic's Fury": ('MNK',),  # Mythic
    'Stringing Pummel': ('PUP',),  # Mythic
    'Mandalic Stab': ('THF',),  # Mythic
    'Mordant Rime': ('BRD',),  # Mythic
    'Pyrrhic Kleos': ('DNC',),  # Mythic
    'Death Blossom': ('RDM',),  # Mythic
    'Atonement': ('PLD',),  # Mythic
    'Expiacion': ('BLU',),  # Mythic
    'Primal Rend': ('BST',),  # Mythic
    "King's Justice": ('WAR',),  # Mythic
    'Insurgency': ('DRK',),  # Mythic
    'Drakesbane': ('DRG',),  # Mythic
    'Blade: Kamu': ('NIN',),  # Mythic
    'Tachi: Rana': ('SAM',),  # Mythic
    'Mystic Boon': ('WHM',),  # Mythic
    'Vidohunir': ('BLM',),  # Mythic
    'Garland of Bliss': ('SMN',),  # Mythic
    'Omniscience': ('SCH',),  # Mythic
    'Trueflight': ('RNG',),  # Mythic
    'Leaden Salute': ('COR',),  # Mythic
    'Dimidiation': ('RUN',),  # Ergon
    'Exudation': ('GEO',),  # Ergon
}


def usable_by_job(en_name, job):
    """For a job-exclusive WS, True only for that job. Any other WS is True (filtering by weapon type happens in choices)."""
    jobs = JOB_ONLY_WS.get(en_name)
    return jobs is None or job in jobs
