# -*- coding: utf-8 -*-
"""Tests for ranged attacks (Ranger, Corsair) and Corsair rolls and Quick Draw.
Run (from GearSwapKit/): python -I tests/test_cor.py"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import _env as ENV
import export_parser as EP
import set_catalog as C
from project import Project

LUAC = ENV.LUAC
LUA51 = ENV.LUA51
fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)
        sys.stdout.buffer.write(("NG: %s\n" % msg).encode("utf-8"))


H = EP.parse_equipped_set

# List: ranged attack entries for RNG and COR; rolls and Quick Draw are COR only
for job in C.ALL_JOBS:
    paths = [e["path"] for e in C.sets_for_job(job)]
    ranged = job in ("RNG", "COR", "SAM")
    check(("sets.RA_STP" in paths) == ranged and ("sets.RA_ACC" in paths) == ranged and ("sets.precast.RA" in paths) == ranged,
          "%s の遠隔攻撃の項目は、狩人・コルセア・侍だけ" % job)
    check(("sets.CorsairRoll" in paths) == (job == "COR") and ("sets.RA_QDACC" in paths) == (job == "COR"),
          "%s のロール・クイックドローは、コルセアだけ" % job)

pr = Project("COR")
pr.assign("sets.precast.RA", H('sets.exported={ head="スナップ帽" }'))
pr.assign("sets.RA_STP", H('sets.exported={ head="STP帽" }'))
pr.assign("sets.RA_ACC", H('sets.exported={ head="飛命帽" }'))
pr.assign("sets.CorsairRoll", H('sets.exported={ head="ロール帽", body="ロール胴" }'))
pr.custom.append(("sets.precast.CorsairRoll", "ロール (アビリティ強化)", None))
pr.custom.append(("sets.precast.CorsairRoll['Allies\\' Roll']", "アライズロール", None))
pr.assign("sets.precast.CorsairRoll", H('sets.exported={ legs="ロール脚" }'))   # ability-enhancing gear (all rolls)
pr.assign("sets.precast.CorsairRoll['Allies\\' Roll']", H('sets.exported={ head="ＣＳトリコルヌ+3" }'))
pr.assign("sets.RA_QDSTP", H('sets.exported={ head="QDSTP帽" }'))
pr.assign("sets.RA_QDDPS", H('sets.exported={ head="QD威力帽" }'))
pr.assign("sets.RA_QDACC", H('sets.exported={ head="QD魔命帽" }'))
pr.set_ammo("physical", EP.Item("ammo", "クロノブレット", '"クロノブレット"'))
pr.set_ammo("quickdraw", EP.Item("ammo", "アニミキーブレット", '"アニミキーブレット"'))
lua = pr.to_lua()
check("    sets.midcast.RA = sets.RA_STP" in lua, "sets.midcast.RA に結ぶ")
check("state.QuickDrawMode = M{['description']='QuickDrawMode', 'ソーティ', '通常'}" in lua, "QuickDrawMode (ソーティ / 通常)")
check("sets.precast.CorsairShot['ライトショット'] = sets.RA_QDACC" in lua, "日本語名のライトショットも出す")
check(lua.index("sets.precast.CorsairRoll = sets.CorsairRoll") < lua.index("sets.precast.CorsairRoll['Allies\\' Roll'] = set_combine("),
      "ロールごとのセットより先に、ロール (共通) を結ぶ")

# With only a damage set, skip the mode and make it the default
p2 = Project("COR")
p2.assign("sets.RA_QDDPS", H('sets.exported={ head="QD威力帽" }'))
l2 = p2.to_lua()
check("sets.precast.CorsairShot = sets.RA_QDDPS" in l2 and "QuickDrawMode" not in l2, "クイックドローが 1 つならモードを出さない")

if os.path.exists(LUAC):
    d = tempfile.mkdtemp()
    for name, text in (("COR.lua", lua), ("COR2.lua", l2)):
        path = os.path.join(d, name)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        r = subprocess.run([LUAC, "-p", path], capture_output=True)
        check(r.returncode == 0, "luac を通る %s %s" % (name, r.stderr.decode("utf-8", "replace")))
    if os.path.exists(LUA51):
        r = subprocess.run([LUA51, os.path.join(HERE, "cor_lua_test.lua"), os.path.join(d, "COR.lua")], capture_output=True)
        sys.stdout.buffer.write(r.stdout + r.stderr)
        check(r.returncode == 0, "模擬 GearSwap で、遠隔攻撃・ロール・クイックドローが正しい")

if fails:
    sys.stdout.buffer.write(("FAILED %d 件\n" % len(fails)).encode("utf-8"))
    sys.exit(1)
sys.stdout.buffer.write("OK 遠隔攻撃・ロール・クイックドロー: 失敗 0 件\n".encode("utf-8"))
