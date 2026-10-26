# -*- coding: utf-8 -*-
"""学者のアビリティ強化の装備 (陣頭指揮の足 = いつも履いたまま・震天動地の章 = ＡＣブレーサー) の確認。
実行 (GearSwapKit/ で): python -I tests/test_sch.py"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import _env as ENV
import ability_gear as AG
import export_parser as EP
from project import Project

LUAC = ENV.LUAC
LUA51 = ENV.LUA51
fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)
        sys.stdout.buffer.write(("NG: %s\n" % msg).encode("utf-8"))


sch = {e["ability_en"]: e for e in AG.entries_for_job("SCH")}
check(sch["Stormsurge"]["timing"] == "spell" and sch["Stormsurge"]["set_path"] == "sets.Stormsurge", "陣頭指揮は、陣の魔法を唱えるときに履く")
check([i["ja"] for i in sch["Immanence"]["items"]][0].startswith("ＡＣブレーサー"), "震天動地の章は、ＡＣブレーサー系")
check("spell" in AG.TIMING_NAMES, "「決まった魔法を唱えるとき」の説明がある")

pr = Project("SCH")
pr.assign("sets.idle", EP.parse_equipped_set('sets.exported={ feet="待機の足", head="待機の頭" }'))
pr.assign("sets.precast.FC", EP.parse_equipped_set('sets.exported={ feet="ＦＣの足" }'))
path = pr.add_ability_gear(sch["Stormsurge"], EP.Item("feet", "ＰＤローファー+4", '"ＰＤローファー+4"'))
pr.add_ability_gear(sch["Immanence"], EP.Item("hands", "ＡＣブレーサー+3", '"ＡＣブレーサー+3"'))
lua = pr.to_lua()
check(path == "sets.Stormsurge" and "sets.Stormsurge = {" in lua, "陣頭指揮の足のセットを出す")
check("sets.Stormsurge)" not in lua.split("function customize_idle_set")[0][-400:] and "base = set_combine(base, sets.Stormsurge)" not in lua, "待機・戦闘中には重ねない")
check("if spellMap == 'Storm' then equip(sets.Stormsurge) end" in lua, "陣の魔法では、詠唱の開始・詠唱中も履き直す")
check('hands="ＡＣブレーサー+3"' in lua, "震天動地の章のセットに、ＡＣブレーサーが入る")

if os.path.exists(LUAC):
    d = tempfile.mkdtemp()
    p = os.path.join(d, "SCH.lua")
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(lua)
    r = subprocess.run([LUAC, "-p", p], capture_output=True)
    check(r.returncode == 0, "luac を通る " + r.stderr.decode("utf-8", "replace"))
    if os.path.exists(LUA51):
        test = '''
local worn = {}
local env = setmetatable({include=function() end, set_language=function() end, send_command=function() end,
    equip=function(t) for k,v in pairs(t) do worn[k]=v end end,
    M=function(a,b) if type(a)=="table" then return {value=a[1]} end return {value=a} end,
    state={IdleMode={options=function() end}}, buffactive={},
    sets={precast={JA={},WS={}}, midcast={Pet={}}, idle={}, engaged={}, buff={}},
    set_combine=function(a,b) local r={} for k,v in pairs(a) do r[k]=v end for k,v in pairs(b) do r[k]=v end return r end},
    {__index=_G})
local f = assert(loadfile(arg[1])); setfenv(f, env); f(); env.user_setup(); env.init_gear_sets()
local idle = env.customize_idle_set and env.customize_idle_set(env.sets.idle) or env.sets.idle
assert(idle == nil or idle.feet ~= "ＰＤローファー+4", "待機には陣頭指揮の足を重ねない")
env.job_post_precast({english="Firestorm", action_type="Magic"}, {}, "Storm", {})
assert(worn.feet == "ＰＤローファー+4", "陣の魔法の詠唱の開始で、足を履き直す")
worn = {}
env.job_post_precast({english="Fire", action_type="Magic"}, {}, "Fire", {})
assert(worn.feet == nil, "ほかの魔法では、履き直さない")
print("OK")
'''
        t = os.path.join(d, "t.lua")
        with open(t, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(test)
        r = subprocess.run([LUA51, t, p], capture_output=True)
        check(r.returncode == 0 and b"OK" in r.stdout, "模擬 GearSwap で、陣頭指揮の足を履いたままにする " + r.stderr.decode("utf-8", "replace"))

# バ系の魔法: 強化魔法を使うジョブの一覧にあり、強化魔法の装備に重ねる
import set_catalog as C
for job in ("WHM", "RDM", "SCH", "PLD", "RUN"):
    check("sets.midcast.BarElement" in [e["path"] for e in C.sets_for_job(job)], "%s に、バ系の魔法がある" % job)
check("sets.midcast.BarElement" not in [e["path"] for e in C.sets_for_job("WAR")], "戦士には、バ系の魔法は出さない")
pb = Project("SCH")
pb.assign("sets.midcast['強化魔法']", EP.parse_equipped_set('sets.exported={ legs="強化の脚", head="強化の頭" }'))
pb.assign("sets.midcast.BarElement", EP.parse_equipped_set('sets.exported={ legs="シェダルサラウィル" }'))
check("sets.midcast.BarElement = set_combine(sets.midcast['強化魔法'], {" in pb.to_lua(), "バ系の魔法は、強化魔法の装備に重ねる")

# 属性帯・オルペウスサッシュの自動選択と、震天動地の章の最優先
pw = Project("SCH")
pw.assign("sets.midcast['精霊魔法']", EP.parse_equipped_set('sets.exported={ waist="セットの腰", head="精霊の頭" }'))
pw.add_ability_gear(sch["Immanence"], EP.Item("hands", "ＡＣブレーサー+3", '"ＡＣブレーサー+3"'))
check(Project("SCH").auto_waist is False, "腰の自動選択は、初めはチェックなし")
lua_off = pw.to_lua()
check("elemental_waist" not in lua_off and "equip(sets.buff['Immanence'])" in lua_off, "チェックなし: 腰は替えないが、震天動地の章の最優先は入る")
pw.set_auto_waist(True)
lw = pw.to_lua()
check("elemental_waist" in lw, "チェックあり: 腰を自動で選ぶ")
p2 = Project.from_json(pw.to_json())
p2.set_job("SCH")
check(p2.auto_waist, "チェックを保存して読み直せる")
if os.path.exists(LUA51):
    d2 = tempfile.mkdtemp()
    pp = os.path.join(d2, "SCH.lua")
    with open(pp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(lw)
    test2 = '''
local worn = {}
local env = setmetatable({include=function() end, set_language=function() end, send_command=function() end,
    equip=function(t) for k,v in pairs(t) do worn[k]=v end end,
    M=function(a,b) if type(a)=="table" then return {value=a[1]} end return {value=a} end,
    state={IdleMode={options=function() end}}, buffactive={},
    world={weather_element="なし", weather_intensity=0, day_element="氷"},
    sets={precast={JA={},WS={}}, midcast={Pet={}}, idle={}, engaged={}, buff={}},
    set_combine=function(a,b) local r={} for k,v in pairs(a) do r[k]=v end for k,v in pairs(b) do r[k]=v end return r end},
    {__index=_G})
local f = assert(loadfile(arg[1])); setfenv(f, env); f(); env.user_setup(); env.init_gear_sets()
local function cast(element, dist, name)
    worn = {}
    env.job_post_midcast({english=name or "Fire V", skill="精霊魔法", element=element, action_type="Magic",
                          target={distance=dist}}, {}, nil, {})
    return worn.waist
end
-- 熱波の陣II (強天候 +25%) の火: 帯 (25) > サッシュ (遠いので 1)
env.world.weather_element, env.world.weather_intensity = "火", 2
assert(cast("火", 20) == "八輪の帯", "強天候の火は八輪の帯")
-- 天候なし・曜日も無関係: 近ければオルペウスサッシュ
env.world.weather_element, env.world.weather_intensity, env.world.day_element = "なし", 0, "光"
assert(cast("火", 1.5) == "オルペウスサッシュ", "天候なしで近ければオルペウスサッシュ")
-- 曜日 +10 と距離 3 (約 13.6): サッシュ
env.world.day_element = "火"
assert(cast("火", 3) == "オルペウスサッシュ", "曜日 +10 より距離 3 のサッシュが大きい")
-- 曜日 +10 と距離 8 (約 7.3): 帯
assert(cast("火", 8) == "八輪の帯", "距離 8 なら曜日 +10 の帯")
-- 弱点の天候 (水) で遠い: 帯は着ず、サッシュ (+1)
env.world.weather_element, env.world.weather_intensity, env.world.day_element = "水", 1, "光"
assert(cast("火", 20) == "オルペウスサッシュ", "弱点の天候では帯を着ない")
-- インパクトは替えない
assert(cast("闇", 1, "Impact") == nil, "インパクトでは腰を替えない")
-- 震天動地の章: 腰を替えず、震天動地の章の装備 (手) を最後に着る
env.buffactive["震天動地の章"] = true
env.world.weather_element, env.world.weather_intensity = "火", 2
local w = cast("火", 1)
assert(w == nil and worn.hands == "ＡＣブレーサー+3", "震天動地の章の間は腰を替えず、手を最優先")
print("OK")
'''
    t2 = os.path.join(d2, "t.lua")
    with open(t2, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(test2)
    r = subprocess.run([LUA51, t2, pp], capture_output=True)
    check(r.returncode == 0 and b"OK" in r.stdout, "模擬 GearSwap で、腰の自動選択と震天動地の章の最優先 " + r.stderr.decode("utf-8", "replace"))

if fails:
    sys.stdout.buffer.write(("FAILED %d 件\n" % len(fails)).encode("utf-8"))
    sys.exit(1)
sys.stdout.buffer.write("OK 学者の装備: 失敗 0 件\n".encode("utf-8"))
