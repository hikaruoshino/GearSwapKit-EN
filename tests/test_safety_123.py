# -*- coding: utf-8 -*-
"""Tests for the 1.2.3 fixes: export slot aliases and empty items, the English Cure help for Paladin,
writing the Lua and the work file (a failure midway never empties the current file), and recording unreadable data JSON.
Run (from GearSwapKit/): python -I tests/test_safety_123.py"""
import glob
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import export_parser as EP
import generator as G
import project as P
import set_catalog as C

fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)
        sys.stdout.buffer.write(("NG: %s\n" % msg).encode("utf-8"))


# 1. Slot aliases (ear1 etc.) are read as the full slot names; empty items are skipped
text = ('sets.exported={ main="Naegling", head="", ear1="Odnowa Earring +1", rear="Tuisto Earring",\n'
        '  ring2={ name="Gelatinous Ring +1", augments={"Path: A"} }, lring="Moonlight Ring" }')
got = EP.parse_equipped_set(text)
check(got.get("left_ear") and got["left_ear"].name == "Odnowa Earring +1", "ear1 を left_ear として読む")
check(got.get("right_ear") and got["right_ear"].name == "Tuisto Earring", "rear を right_ear として読む")
check(got.get("right_ring") and got["right_ring"].name == "Gelatinous Ring +1", "ring2 (表の形) を right_ring として読む")
check(got.get("left_ring") and got["left_ring"].name == "Moonlight Ring", "lring を left_ring として読む")
check("head" not in got, 'head="" を装備として読まない')
check(got.get("main") and got["main"].name == "Naegling", "正規名のスロットは今までどおり読む")
got2 = EP.parse_equipped_set('sets.x={ ranged="Gastraphetes", learring="Etiolation Earring", rearring="Eabani Earring" }')
check(got2.get("range") and got2["range"].name == "Gastraphetes", "ranged を range として読む")
check(got2.get("left_ear") and got2.get("right_ear"), "learring・rearring を left_ear・right_ear として読む")

# 2. Paladin gets the Cure I-IV help, the healing jobs get the Cure I-VI help (English)
def cure_help_en(job):
    for e in C.sets_for_job(job):
        if e["path"] == "sets.midcast.Cure":
            return e.get("help_en") or ""
    return None

pld, whm = cure_help_en("PLD"), cure_help_en("WHM")
check(pld is not None and "I-IV" in pld, "PLD の英語のケアルの説明が I-IV のもの (%r)" % (pld or "")[:40])
check(whm is not None and "I-VI" in whm, "WHM の英語のケアルの説明が I-VI のもの (%r)" % (whm or "")[:40])

# 3. Writing: if building the Lua fails, the current file stays and no temporary file is left
with tempfile.TemporaryDirectory() as d:
    pj = P.Project("PLD")
    lua = os.path.join(d, "PLD.lua")
    with open(lua, "w", encoding="utf-8") as f:
        f.write("-- old file\n")

    def boom():
        raise ValueError("generation failed")
    real = pj.to_lua
    pj.to_lua = boom
    try:
        pj.write_lua(d)
        check(False, "to_lua が失敗したら write_lua も失敗を返す")
    except ValueError:
        pass
    with open(lua, encoding="utf-8") as f:
        check(f.read() == "-- old file\n", "Lua を作る途中で失敗しても、今の PLD.lua は空にならない")
    check(not glob.glob(os.path.join(d, ".gsk_*")), "失敗しても一時ファイルが残らない")
    pj.to_lua = real
    path, backup = pj.write_lua(d)
    with open(path, encoding="utf-8") as f:
        check("get_sets" in f.read(), "成功すれば新しい Lua に置き換わる")
    check(backup and os.path.exists(backup), "上書きの前のバックアップが残る")
    check(not glob.glob(os.path.join(d, ".gsk_*")), "成功しても一時ファイルが残らない")

    # atomic_write keeps the requested line ending
    p2 = os.path.join(d, "w.json")
    P.atomic_write(p2, "a\nb\n", newline="\n")
    with open(p2, "rb") as f:
        check(f.read() == b"a\nb\n", "atomic_write(newline='\\n') は LF で書く")

# 4. An unreadable data JSON returns {} and its name goes into MISSING_DATA
saved = G._DATA_CACHE.pop("pet_moves.json", "absent")
G._DATA_CACHE["pet_moves.json"] = None          # pretend it couldn't be read
G.MISSING_DATA.clear()
check(G._pet_moves() == {}, "pet_moves.json が読めないと {} を返す")
check("pet_moves.json" in G.MISSING_DATA, "読めなかった pet_moves.json を MISSING_DATA に残す")
del G._DATA_CACHE["pet_moves.json"]
if saved != "absent":
    G._DATA_CACHE["pet_moves.json"] = saved
G.MISSING_DATA.clear()
check(len(G._pet_moves().get("SMN", [])) > 100 and not G.MISSING_DATA, "読めるときは中身を返し、MISSING_DATA は空のまま")
check(isinstance(G._load_data("blu_spells.json", "spells"), dict) and not G.MISSING_DATA, "blu_spells.json の spells を読める")
with tempfile.TemporaryDirectory() as d:          # a JSON whose outermost value is [] counts as unreadable
    real_file = G.__file__
    with open(os.path.join(d, "bad.json"), "w", encoding="utf-8") as f:
        f.write("[1, 2]")
    G.__file__ = os.path.join(d, "generator.py")
    try:
        G.MISSING_DATA.clear()
        check(G._load_data("bad.json") == {} and "bad.json" in G.MISSING_DATA, "一番外側が辞書でない JSON は {} を返して記録する")
    finally:
        G.__file__ = real_file
        G._DATA_CACHE.pop("bad.json", None)
        G.MISSING_DATA.clear()

if fails:
    sys.stdout.buffer.write(("FAILED %d 件\n" % len(fails)).encode("utf-8"))
    sys.exit(1)
sys.stdout.buffer.write("OK 1.2.3 の修正 (別名スロット・ケアルの英語・安全な書き出し・データの警告): 失敗 0 件\n".encode("utf-8"))
