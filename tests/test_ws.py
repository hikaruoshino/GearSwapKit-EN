# -*- coding: utf-8 -*-
"""WS の魔攻 (sets.precast.WS.Magic)・遠隔 (sets.precast.WS.Range)・技ごとの WS の重ね方の確認。
実行 (GearSwapKit/ で): python -I tests/test_ws.py"""
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import _env as ENV
import export_parser as EP
import set_catalog as C
import ws_types as WS
from project import Project

RES = ENV.RES
LUAC = ENV.LUAC
LUA51 = ENV.LUA51
fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)
        sys.stdout.buffer.write(("NG: %s\n" % msg).encode("utf-8"))


# --- 名前を res と突き合わせる ---
if os.path.isfile(os.path.join(RES, "weapon_skills.lua")):
    with open(os.path.join(RES, "weapon_skills.lua"), "rb") as f:
        txt = f.read().decode("utf-8", errors="replace")
    all_ws = set(re.findall(r'\ben="([^"]*)"', txt))
    for n in WS.MAGIC_WS:
        check(n in all_ws, "魔法属性の WS の名前が res にある: %s" % n)
    ranged = set()
    for line in txt.splitlines():
        m = re.search(r'\ben="([^"]*)".*\bskill=(\d+)', line)
        if m and m.group(2) in ("25", "26"):
            ranged.add(m.group(1))
    check(ranged == set(WS.RANGED_WS), "遠隔の WS の一覧が、res の弓術・射撃と一致 (差: %s)" % sorted(ranged ^ set(WS.RANGED_WS)))
check(len(WS.MAGIC_WS) == len(set(WS.MAGIC_WS)), "魔法属性の WS に重複が無い")

# ジョブ専用の WS (ミシック・エルゴン): 名前が res にあり、ほかのジョブのドロップダウンには出ない
if os.path.isfile(os.path.join(RES, "weapon_skills.lua")):
    for n in WS.JOB_ONLY_WS:
        check(n in all_ws, "ジョブ専用の WS の名前が res にある: %s" % n)
    import choices as CH
    import resdb as RDB
    rdb = RDB.ResDB(RES)
    rng = [i["en"] for i in CH.choices(rdb, "ws", "RNG")]
    cor = [i["en"] for i in CH.choices(rdb, "ws", "COR")]
    check("Leaden Salute" not in rng and "Trueflight" in rng, "RNG: レデンサリュートは出ず、トゥルーフライトは出る")
    check("Leaden Salute" in cor and "Trueflight" not in cor, "COR: レデンサリュートは出て、トゥルーフライトは出ない")
    check("Last Stand" in rng and "Last Stand" in cor, "ふつうの射撃の WS (ラストスタンド) は両方に出る")
    check("Savage Blade" in cor and "Death Blossom" not in [i["en"] for i in CH.choices(rdb, "ws", "BLU")],
          "BLU には赤魔道士専用のデスブロッサムが出ない")
check(WS.kind_of("Leaden Salute") == "RangeMagic" and WS.kind_of("Aeolian Edge") == "Magic" and WS.kind_of("Jishnu's Radiance") == "Range" and WS.kind_of("Savage Blade") is None,
      "分け方: レデンサリュート = 魔攻・ジシュヌの光輝 = 遠隔・サベッジブレード = ふつう")

# --- 一覧: 魔攻の WS は全ジョブ・遠隔の WS は狩人とコルセアだけ ---
for job in C.ALL_JOBS:
    paths = [e["path"] for e in C.sets_for_job(job)]
    check("sets.precast.WS.Magic" in paths, "%s に魔攻の WS がある" % job)
    check(("sets.precast.WS.Range" in paths) == (job in ("RNG", "COR")), "%s の遠隔の WS は、狩人とコルセアだけ" % job)
    check(("sets.precast.WS.RangeMagic" in paths) == (job in ("RNG", "COR")), "%s の遠隔魔攻の WS は、狩人とコルセアだけ" % job)
    if "sets.precast.WS.Magic" in paths:
        check(paths.index("sets.precast.WS.Magic") == paths.index("sets.precast.WS") + 1, "%s: 魔攻の WS は、共通の WS のすぐ後" % job)

# --- 出力 ---
H = EP.parse_equipped_set
pr = Project("COR")
pr.assign("sets.precast.WS", H('sets.exported={ head="ＮＹヘルム+1", body="ＮＹメイル+1" }'))
pr.assign("sets.precast.WS.Magic", H('sets.exported={ head="ピクシードヘアピン+1", neck="コモドアチャーム+2" }'))
pr.assign("sets.precast.WS.Range", H('sets.exported={ head="ＬＡトリコルヌ+3" }'))
for en, ja in (("Leaden Salute", "レデンサリュート"), ("Last Stand", "ラストスタンド"), ("Savage Blade", "サベッジブレード")):
    pr.add_pair(0, en, ja)
pr.assign("sets.precast.WS['Leaden Salute']", H('sets.exported={ ring1="アルコンリング" , left_ring="アルコンリング" }'))
pr.assign("sets.precast.WS['Last Stand']", H('sets.exported={ waist="フォシャベルト" }'))
pr.assign("sets.precast.WS['Savage Blade']", H('sets.exported={ waist="セールフィベルト+1" }'))
lua = pr.to_lua()
check("sets.precast.WS['Leaden Salute'] = set_combine(sets.precast.WS.Magic, {" in lua, "レデンサリュートは魔攻の WS に重ねる")
check("sets.precast.WS['Last Stand'] = set_combine(sets.precast.WS.Range, {" in lua, "ラストスタンドは遠隔の WS に重ねる")
check("sets.precast.WS['Savage Blade'] = set_combine(sets.precast.WS, {" in lua, "サベッジブレードは共通の WS に重ねる")
check(lua.index("sets.precast.WS.Magic = {") < lua.index("sets.precast.WS['Leaden Salute']"), "魔攻の WS が先に出る (重ねる元が先に要る)")
check("sets.precast.WS['レデンサリュート'] = sets.precast.WS['Leaden Salute']" in lua, "日本語名の別名も出る")
check("function job_get_spell_map(spell, default_spell_map)" in lua and "[\"Leaden Salute\"] = true," in lua, "WS の分け方の関数が出る")
check("return 'Range'" in lua, "遠隔のセットがあれば、遠隔の分け方も出る")
p2 = Project("WAR")
p2.assign("sets.precast.WS", H('sets.exported={ head="ＮＹヘルム+1" }'))
check("job_get_spell_map" not in p2.to_lua(), "魔攻・遠隔のセットが無ければ、分け方の関数は出さない")
p3 = Project("WAR")
p3.assign("sets.precast.WS.Magic", H('sets.exported={ head="ピクシードヘアピン+1" }'))
check("return 'Range'" not in p3.to_lua() and "return 'Magic'" in p3.to_lua(), "遠隔のセットが無ければ、遠隔の分け方は出さない")

# 遠隔魔攻のセットがあれば、遠隔の魔法属性 WS はそちら・近接の魔法属性 WS は魔攻のまま
p4 = Project("COR")
p4.assign("sets.precast.WS", H('sets.exported={ head="ＮＹヘルム+1" }'))
p4.assign("sets.precast.WS.Magic", H('sets.exported={ head="ニャメヘルム" }'))
p4.assign("sets.precast.WS.RangeMagic", H('sets.exported={ head="妖蟲の髪飾り+1" }'))
for en, ja in (("Leaden Salute", "レデンサリュート"), ("Aeolian Edge", "イオリアンエッジ")):
    p4.add_pair(0, en, ja)
p4.assign("sets.precast.WS['Leaden Salute']", H('sets.exported={ right_ring="アルコンリング" }'))
p4.assign("sets.precast.WS['Aeolian Edge']", H('sets.exported={ right_ring="メトリリング+1" }'))
lua4 = p4.to_lua()
check("sets.precast.WS['Leaden Salute'] = set_combine(sets.precast.WS.RangeMagic, {" in lua4, "レデンサリュートは遠隔魔攻に重ねる")
check("sets.precast.WS['Aeolian Edge'] = set_combine(sets.precast.WS.Magic, {" in lua4, "イオリアンエッジは魔攻に重ねる")
check("return 'RangeMagic'" in lua4, "遠隔魔攻の分け方が出る")
check("return 'RangeMagic'" not in lua, "遠隔魔攻のセットが無ければ、遠隔魔攻の分け方は出さない")

if os.path.exists(LUAC):
    d4 = tempfile.mkdtemp()
    path4 = os.path.join(d4, "COR.lua")
    with open(path4, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(lua4)
    if os.path.exists(LUA51):
        r = subprocess.run([LUA51, os.path.join(HERE, "ws_rmagic_lua_test.lua"), path4], capture_output=True)
        sys.stdout.buffer.write(r.stdout + r.stderr)
        check(r.returncode == 0, "模擬 GearSwap で、遠隔魔攻の分け方が正しい")

if os.path.exists(LUAC):
    d = tempfile.mkdtemp()
    path = os.path.join(d, "COR.lua")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(lua)
    r = subprocess.run([LUAC, "-p", path], capture_output=True)
    check(r.returncode == 0, "luac を通る " + r.stderr.decode("utf-8", "replace"))
    if os.path.exists(LUA51):
        r = subprocess.run([LUA51, os.path.join(HERE, "ws_lua_test.lua"), path], capture_output=True)
        sys.stdout.buffer.write(r.stdout + r.stderr)
        check(r.returncode == 0, "模擬 GearSwap で、WS の分け方が正しい")

if fails:
    sys.stdout.buffer.write(("FAILED %d 件\n" % len(fails)).encode("utf-8"))
    sys.exit(1)
sys.stdout.buffer.write("OK WS の魔攻・遠隔: 失敗 0 件\n".encode("utf-8"))
