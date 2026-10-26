# -*- coding: utf-8 -*-
"""矢弾の使い分け (狩人・コルセア) の確認。
実行 (GearSwapKit/ で): python -I tests/test_ammo.py"""
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


def item(name):
    return EP.Item("ammo", name, '"%s"' % name)


# 一覧: 矢弾は狩人とコルセアだけ・クイックドローはコルセアだけ
for job in C.ALL_JOBS:
    paths = [e["path"] for e in C.sets_for_job(job)]
    check(("ammo:physical" in paths) == (job in ("RNG", "COR")), "%s の矢弾の項目は、狩人とコルセアだけ" % job)
    check(("ammo:quickdraw" in paths) == (job == "COR"), "%s のクイックドローの弾は、コルセアだけ" % job)

# 所持品の一覧から矢弾の候補を取れる
inv = EP.parse_inventory('sets.exported={ ammo="クロノブレット", ammo="ライヴブレット", ammo="クロノブレット", head="ＬＡトリコルヌ+3" }')
check([c.name for c in EP.weapon_candidates(inv, "ammo")] == ["クロノブレット", "ライヴブレット"], "矢弾の候補 (重複なし)")

pr = Project("COR")
H = EP.parse_equipped_set
pr.assign("sets.precast.WS", H('sets.exported={ ammo="クロノブレット", head="ＮＹヘルム+1" }'))
pr.set_ammo("physical", item("クロノブレット"))
pr.set_ammo("physical", item("クロノブレット"))
pr.set_ammo("magical", item("ライヴブレット"))
pr.set_ammo("quickdraw", item("アニミキーブレット"))
pr.set_ws_ammo("Savage Blade", item("ホクスボクブレット"))
pr.set_ws_ammo("Aeolian Edge", item("ホクスボクブレット"))
check(pr.is_assigned("ammo:physical") and pr.is_assigned("ammo:special"), "割り当て済みと表示される")
check(pr.has_work("COR"), "矢弾だけでも作業ありになる")
lua = pr.to_lua()
check('        ammo="クロノブレット",' not in lua, "セットには矢弾を入れない (使い分けで替える)")
check('["ホクスボクブレット"] = true,' in lua and '["アニミキーブレット"] = true,' in lua, "特殊弾とクイックドローの弾は誤射防止の対象")
check('["クロノブレット"] = true,' not in lua and '["ライヴブレット"] = true,' not in lua, "普通の弾は誤射防止の対象にしない")
check("function job_post_aftercast" in lua and "gs c ammo" in lua, "使ったあとに戻す・読み込み後に装備する")

# 保存して読み直しても残る
pr2 = Project.from_json(pr.to_json())
pr2.set_job("COR")
check(pr2.ammo.get("magical") and pr2.ammo["magical"].name == "ライヴブレット", "保存した矢弾を読み直せる")
check(pr2.ws_ammo.get("Savage Blade") and pr2.ws_ammo["Savage Blade"].name == "ホクスボクブレット", "保存した特殊弾を読み直せる")
pr2.clear("ammo:special")
check(not pr2.ws_ammo and pr2.ammo, "特殊弾を外しても、ほかの矢弾は残る")

# 矢弾を選ばなければ、今までどおり
p3 = Project("COR")
p3.assign("sets.precast.WS", H('sets.exported={ head="ＮＹヘルム+1" }'))
check("job_post_aftercast" not in p3.to_lua(), "矢弾を選ばなければ、仕組みを出さない")

if os.path.exists(LUAC):
    d = tempfile.mkdtemp()
    path = os.path.join(d, "COR.lua")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(lua)
    r = subprocess.run([LUAC, "-p", path], capture_output=True)
    check(r.returncode == 0, "luac を通る " + r.stderr.decode("utf-8", "replace"))
    if os.path.exists(LUA51):
        r = subprocess.run([LUA51, os.path.join(HERE, "ammo_lua_test.lua"), path], capture_output=True)
        sys.stdout.buffer.write(r.stdout + r.stderr)
        check(r.returncode == 0, "模擬 GearSwap で、矢弾の使い分けが正しい")

if fails:
    sys.stdout.buffer.write(("FAILED %d 件\n" % len(fails)).encode("utf-8"))
    sys.exit(1)
sys.stdout.buffer.write("OK 矢弾の使い分け: 失敗 0 件\n".encode("utf-8"))
