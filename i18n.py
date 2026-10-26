# -*- coding: utf-8 -*-
"""画面と出力の言語 (日本語 / 英語) の切り替え。

使い方: 文の場所で L("日本語の文", "English text") と書く。今の言語のほうを返す。
言語は app.py が設定ファイルから読み、set_lang() で決める (初回起動で選び、上の「Language / 言語」で変える)。
英語のときは、出力する Lua も英語クライアント向けにする (generator.py が lang() を見る)。
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
    """今の言語の文。"""
    return en if _lang == "en" else ja


# 魔法のスキルの名前 (セットのキー sets.midcast['…'] に使う)。日本語クライアントは日本語、英語クライアントは英語で探す
SKILL_EN = {
    "回復魔法": "Healing Magic", "強化魔法": "Enhancing Magic", "弱体魔法": "Enfeebling Magic",
    "精霊魔法": "Elemental Magic", "暗黒魔法": "Dark Magic", "神聖魔法": "Divine Magic",
    "召喚魔法": "Summoning Magic", "忍術": "Ninjutsu", "歌唱": "Singing", "青魔法": "Blue Magic",
    "風水魔法": "Geomancy",
}


def skill_name(ja):
    """スキルの名前を、今の言語のクライアントが使う名前にする。"""
    return SKILL_EN.get(ja, ja) if _lang == "en" else ja
