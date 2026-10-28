# -*- coding: utf-8 -*-
"""Switch the UI and output language (Japanese / English).

Usage: write L("Japanese text", "English text") wherever text appears; it returns the one for the current language.
app.py reads the language from the settings file and applies it with set_lang() (chosen on first launch, changed via the "Language" menu at the top).
In English mode, the generated Lua also targets the English client (generator.py checks lang()).
"""

LANGS = ("ja", "en")
_lang = "ja"


def set_lang(code):
    global _lang
    _lang = code if code in LANGS else "ja"


def lang():
    return _lang


def is_en():
    return _lang == "en"


def L(ja, en):
    """Text in the current language."""
    return en if _lang == "en" else ja


# Magic skill names (used as set keys, sets.midcast['...']). The Japanese client looks them up in Japanese, the English client in English
SKILL_EN = {
    "回復魔法": "Healing Magic", "強化魔法": "Enhancing Magic", "弱体魔法": "Enfeebling Magic",
    "精霊魔法": "Elemental Magic", "暗黒魔法": "Dark Magic", "神聖魔法": "Divine Magic",
    "召喚魔法": "Summoning Magic", "忍術": "Ninjutsu", "歌唱": "Singing", "青魔法": "Blue Magic",
    "風水魔法": "Geomancy",
}


def skill_name(ja):
    """Convert a skill name to the name the client uses in the current language."""
    return SKILL_EN.get(ja, ja) if _lang == "en" else ja
