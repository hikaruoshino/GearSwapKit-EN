# -*- coding: utf-8 -*-
"""被強化の装備 (被ファランクス・被プロテス・被シェル) の確認。実行 (GearSwapKit/ で): python -I tests/test_received.py"""
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import _env as ENV
import ability_gear as AG
import choices as CH
import export_parser as EP
import set_catalog as C
from project import Project, RECEIVED_KIND

RES = ENV.RES
LUAC = ENV.LUAC
LUA51 = ENV.LUA51
fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)
        sys.stdout.buffer.write(("NG: %s\n" % msg).encode("utf-8"))


# --- 魔法の番号を res と突き合わせる ---
if os.path.isfile(os.path.join(RES, "spells.lua")):
    with open(os.path.join(RES, "spells.lua"), "rb") as f:
        txt = f.read().decode("utf-8", errors="replace")
    names = {int(m[0]): m[1] for m in re.findall(r'\bid=(\d+),en="([^"]*)"', txt)}
    expect = {"IncreasedPhalanx": "Phalanx", "IncreasedProtect": "Protect", "IncreasedShell": "Shell", "IncreasedCursna": "Cursna"}
    for name, _ja, ids, aoe in C.RECEIVED:
        for i in ids:
            check(names.get(i, "").startswith(expect[name]) and "ra" not in names.get(i, ""), "%s の番号 %d は %s 系 (実際 %s)" % (name, i, expect[name], names.get(i)))
        for i in aoe:
            check(names.get(i, "").startswith(expect[name] + "ra"), "%s の範囲の番号 %d は %sra 系 (実際 %s)" % (name, i, expect[name], names.get(i)))

# --- 選択式: 最初から左の一覧には出さない・技ごとの追加の「被強化の装備」で選ぶ ---
for job in C.ALL_JOBS:
    check(not any(e["path"].startswith("sets.midcast.Increased") and e["path"] != "sets.midcast.IncreasedCursna" for e in C.sets_for_job(job)), "%s: 最初から左の一覧には出さない (被カーズナ・死の宣告だけは出す)" % job)
items = CH.choices(None, "received", "SAM")
check([i["en"] for i in items] == ["IncreasedPhalanx", "IncreasedProtect", "IncreasedShell", "IncreasedCursna"], "ドロップダウンに 4 つ出る (res が無くても)")
check(C.CUSTOM_KINDS[RECEIVED_KIND][1] == "被強化の装備", "技ごとの追加の種類に「被強化の装備」がある")

pr = Project("SAM")
st, en, ja = pr.resolve(RECEIVED_KIND, "被ファランクス")
check(st == "ok" and en == "IncreasedPhalanx", "日本語の名前から選べる")
path = pr.path_for(RECEIVED_KIND, en)
check(path == "sets.midcast.IncreasedPhalanx", "パスは sets.midcast.IncreasedPhalanx")
pr.add_pair(RECEIVED_KIND, en, ja)
pr.assign(path, EP.parse_equipped_set('sets.exported={ body="ＴＡアバター+2", hands="ＴＡグローブ+2" }'))
pr.add_pair(RECEIVED_KIND, "IncreasedProtect", "被プロテス")
pr.assign("sets.midcast.IncreasedProtect", EP.parse_equipped_set('sets.exported={ right_ring="シェルターリング" }'))
rows = {r["path"]: r for r in pr.entries()}
check(path in rows and "受ける" in rows[path]["help"], "追加すると一覧に出て、説明がある")
lua = pr.to_lua()
check("sets.midcast.IncreasedPhalanx = {" in lua and "received_sets[106] = 'IncreasedPhalanx'" in lua
      and "received_sets[125] = 'IncreasedProtect'" in lua and "received_aoe[125] = true" in lua, "セットと魔法の番号の登録が出る")
check("received_sets[48]" not in lua, "割り当てていない被シェルは登録しない")
check(lua.count("function job_post_midcast") == 1, "job_post_midcast は 1 つ")
check(Project.from_json(pr.to_json()).to_lua() == lua, "保存と読み込みで同じ")

# 被ファランクスの「自動で着替える」を外したとき: セットは出すが、ファランクスには反応しない (被プロテスはそのまま反応する)
pm = Project.from_json(pr.to_json())
pm.set_job("SAM")
check(pm.received_auto("IncreasedPhalanx"), "初めは自動で着替える")
pm.set_received_auto("IncreasedPhalanx", False)
lua_m = pm.to_lua()
check("sets.midcast.IncreasedPhalanx = {" in lua_m, "自動を外しても、被ファランクスのセットは出す")
check("received_sets[106]" not in lua_m and "received_sets[107]" not in lua_m, "自動を外すと、ファランクスには反応しない")
check("received_sets[43] = 'IncreasedProtect'" in lua_m, "被プロテスは、そのまま反応する")
pm2 = Project.from_json(pm.to_json())
check(not pm2.received_auto("IncreasedPhalanx") and pm2.to_lua() == lua_m, "保存と読み込みで、自動を外した状態も残る")
pm2.set_job("NIN")
check(pm2.received_auto("IncreasedPhalanx"), "ほかのジョブには影響しない")
p_only = Project("SAM")
p_only.add_pair(RECEIVED_KIND, "IncreasedPhalanx", "被ファランクス")
p_only.assign("sets.midcast.IncreasedPhalanx", EP.parse_equipped_set('sets.exported={ body="ＴＡアバター+2" }'))
p_only.set_received_auto("IncreasedPhalanx", False)
lua_o = p_only.to_lua()
check("windower.register_event" not in lua_o and "job_post_midcast" not in lua_o, "自動のものが無ければ、反応の仕組みは出さない")
p_only.remove_custom("sets.midcast.IncreasedPhalanx")
check(p_only.received_auto("IncreasedPhalanx"), "被ファランクスを消すと、「自動で着替えない」の設定も消える (足し直したら初めの状態)")

# 学者の章 (行動のときの装備) と一緒でも、job_post_midcast は 1 つにまとまる
p2 = Project("SCH")
per = [e for e in AG.load()["SCH"] if e["ability_en"] == "Perpetuance"][0]
p2.add_ability_gear(per, EP.parse_equipped_set('sets.exported={ hands="ＡＢブレーサー+2" }')["hands"])
p2.add_pair(RECEIVED_KIND, "IncreasedPhalanx", "被ファランクス")
p2.assign("sets.midcast.IncreasedPhalanx", EP.parse_equipped_set('sets.exported={ body="ＴＡアバター+2" }'))
lua2 = p2.to_lua()
check(lua2.count("function job_post_midcast") == 1 and "equip_cast_gear('midcast', spell)" in lua2
      and "received_sets[spell.id]" in lua2, "学者の章と被強化を、1 つの job_post_midcast にまとめる")

if os.path.exists(LUAC):
    for name, text in (("SAM", lua), ("SCH", lua2)):
        d = tempfile.mkdtemp()
        p = os.path.join(d, name + ".lua")
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        r = subprocess.run([LUAC, "-p", p], capture_output=True)
        check(r.returncode == 0, name + " の Lua が luac を通る " + r.stderr.decode("utf-8", "replace"))
        if name == "SAM" and os.path.exists(LUA51):
            r = subprocess.run([LUA51, os.path.join(HERE, "received_lua_test.lua"), p], capture_output=True)
            sys.stdout.buffer.write(r.stdout + r.stderr)
            check(r.returncode == 0, "模擬 GearSwap で、受けるときの着替えと戻りが正しい")

if fails:
    sys.stdout.buffer.write(("FAILED %d 件\n" % len(fails)).encode("utf-8"))
    sys.exit(1)
sys.stdout.buffer.write("OK 被強化の装備: 失敗 0 件\n".encode("utf-8"))
