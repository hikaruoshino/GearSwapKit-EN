# -*- coding: utf-8 -*-
"""アビリティを強化する装備 (レリック装束・エンピリアン装束の一部の部位) の対応表と、所持品との照らし合わせ。

対応表 (ability_gear.json) は、FF11用語辞典 (wiki.ffo.jp) の各装束のページから作った。
強化すると装備の名前が変わる (グリフホーン → ＧＬホーン+1 → …) ので、世代ごとの名前を全部持つ。
所持品の一覧 (//gs export all) にある名前と照らし合わせて、持っているものだけを候補にする。
"""
import json
import os
import sys

# EXE (Nuitka の 1 ファイル版) では、ability_gear.json を EXE の中に入れ (--include-data-files)、展開先 (__file__ の隣) から読む
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

# 英語 (今の言語は timing_name などで選ぶ)
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
    """TIMING_NAMES の今の言語の文。知らない key はそのまま返す。"""
    return _pick(TIMING_NAMES, TIMING_NAMES_EN, key)


def cast_phase_name(key):
    return _pick(CAST_PHASE_NAMES, CAST_PHASE_NAMES_EN, key)


def cast_on_name(key):
    return _pick(CAST_ON_NAMES, CAST_ON_NAMES_EN, key)


def load(path=None):
    """対応表を読む。戻り値: {ジョブ: [エントリ]}。読めなければ空。"""
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
    """装備の名前の照合用の鍵: 日本語名と、res で引ける英語名 (小文字)。"""
    keys = {name}
    if resdb is not None and resdb.available():
        en = resdb.item_en(name)
        if en:
            keys.add(en.lower())
    return keys


def owned(entry, inventory, resdb=None):
    """エントリの装備のうち、所持品にあるもの。inventory は export_parser.parse_inventory の結果 ({スロット: [Item]})。
    戻り値: [(世代の番号, 対応表の装備, Item)] (世代の低い順)。同じ名前でオーグメントの違うものは、別々に返す。"""
    have = inventory.get(entry["slot"], [])
    out = []
    for gen, spec in enumerate(entry["items"]):
        keys = _keys(spec["ja"], resdb)
        for it in have:
            if it.name in keys or it.name.lower() in keys:
                out.append((gen, spec, it))
    return out


def best_owned(entry, inventory, resdb=None):
    """持っている中で、いちばん世代の高いもの (1 つ)。無ければ None。"""
    found = owned(entry, inventory, resdb)
    return found[-1] if found else None


def pick_key(entry):
    """画面で「1 つに絞る」単位: アビリティ・部位・使い方 (同じアビリティ・部位でも、使う瞬間用と効果中用は別のセット)。"""
    return (entry["ability_en"], entry["slot"], entry["timing"])


def describe(entry):
    """画面に出す 1 行の説明。"""
    from i18n import is_en
    if is_en():
        # effect (根拠の文) は日本語しか無いので、英語のときはアビリティ名・部位・使い方だけ
        return "%s (%s) [%s]" % (entry["ability_en"], entry.get("slot", ""), timing_name(entry["timing"]))
    return "%s: %s [%s]" % (entry["ability_ja"], entry["effect"], TIMING_NAMES.get(entry["timing"], entry["timing"]))
