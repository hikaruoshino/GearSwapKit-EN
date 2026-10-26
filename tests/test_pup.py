# -*- coding: utf-8 -*-
"""からくり士のオートマトンの技の装備 (WS・敵対心・自動の事前着替え) の確認。
実行 (GearSwapKit/ で): python -I tests/test_pup.py"""
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


for job in C.ALL_JOBS:
    paths = [e["path"] for e in C.sets_for_job(job)]
    check(("sets.midcast.Pet.WeaponSkill" in paths) == (job == "PUP"), "%s: オートマトンの WS はからくり士だけ" % job)
    check(("sets.midcast.Pet.Enmity" in paths) == (job == "PUP"), "%s: オートマトンの敵対心はからくり士だけ" % job)

H = EP.parse_equipped_set


def make(auto):
    pr = Project("PUP")
    pr.assign("sets.engaged", H('sets.exported={ head="戦闘の頭" }'))
    pr.assign("sets.midcast.Pet.WeaponSkill", H('sets.exported={ main="シュコアトル", head="WSの頭" }'))
    pr.assign("sets.midcast.Pet.Enmity", H('sets.exported={ head="敵対心の頭" }'))
    pr.set_pup_auto(auto)
    return pr


check(Project("PUP").pup_auto is False, "自動の事前着替えは、初めはチェックなし")
lua0, lua1 = make(False).to_lua(), make(True).to_lua()
check("function job_pet_midcast" in lua0 and "pet_tick" not in lua0, "チェックなし: 技が出たときの着替えだけ")
check("pet_tick" in lua1 and "PetAutoGear" in lua1, "チェックあり: 自動の事前着替えも出す")
p2 = Project.from_json(make(True).to_json())
p2.set_job("PUP")
check(p2.pup_auto, "チェックを保存して読み直せる")
check('main="シュコアトル",' in lua0, "オートマトンの WS のセットには、メインを入れる")
pn = make(False)
pn.assign("sets.midcast.Pet.Enmity", H('sets.exported={ main="ヴェリタス", head="敵対心の頭" }'))
check('main="ヴェリタス"' not in pn.to_lua(), "敵対心のセットには、メインを入れない")
pm = make(False)
pm.add_weapon("main", EP.Item("main", "オータス", '"オータス"'))
pm.assign("sets.precast.JA.Maneuver", H('sets.exported={ main="乾坤圏", head="ＰＩタージ+3" }'))
check('main="乾坤圏",' in pm.to_lua(), "マニューバのセットには、メイン (乾坤圏) を入れる (武器の切り替えがあっても)")
check("stateField == 'KeepManeuverWeapon' and not newValue then send_command('wait 0.5; gs c weapons')" in pm.to_lua(),
      "KeepManeuverWeapon をオフにしたら、選んでいる武器に戻す")
if os.path.exists(LUA51):
    dm = tempfile.mkdtemp()
    pm_path = os.path.join(dm, "PUP.lua")
    with open(pm_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(pm.to_lua())
    r = subprocess.run([LUA51, os.path.join(HERE, "maneuver_lua_test.lua"), pm_path], capture_output=True)
    sys.stdout.buffer.write(r.stdout + r.stderr)
    check(r.returncode == 0, "模擬 GearSwap で、マニューバのあと元の武器に戻す")
pw = Project("WAR")
pw.assign("sets.idle", H('sets.exported={ head="ＮＹヘルム+1" }'))
check("job_pet_midcast" not in pw.to_lua(), "からくり士以外には出さない")

if os.path.exists(LUAC):
    for auto, lua in ((False, lua0), (True, lua1)):
        d = tempfile.mkdtemp()
        path = os.path.join(d, "PUP.lua")
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(lua)
        r = subprocess.run([LUAC, "-p", path], capture_output=True)
        check(r.returncode == 0, "luac を通る " + r.stderr.decode("utf-8", "replace"))
        if os.path.exists(LUA51):
            r = subprocess.run([LUA51, os.path.join(HERE, "pup_lua_test.lua"), path, "1" if auto else "0"], capture_output=True)
            sys.stdout.buffer.write(r.stdout + r.stderr)
            check(r.returncode == 0, "模擬 GearSwap で、オートマトンの技の装備が正しい (自動 = %s)" % auto)

if fails:
    sys.stdout.buffer.write(("FAILED %d 件\n" % len(fails)).encode("utf-8"))
    sys.exit(1)
sys.stdout.buffer.write("OK オートマトンの技の装備: 失敗 0 件\n".encode("utf-8"))
