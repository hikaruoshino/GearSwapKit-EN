# -*- coding: utf-8 -*-
"""英語 (英語クライアント向け) の出力の確認。
主なジョブに英語の装備名を割り当てて出力し、日本語が残らない・luac を通る・スキルのキーが英語・
日本語名の別名と set_language('japanese') が出ない、を確かめる。
実行 (GearSwapKit/ で): python -I tests/test_i18n_lua.py"""
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
import i18n
import set_catalog as C
from project import Project

LUAC = ENV.LUAC
LUA51 = ENV.LUA51
JA_CHARS = re.compile(r"[　-ヿ一-鿿＀-￯]")
fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)
        sys.stdout.buffer.write(("NG: %s\n" % msg).encode("utf-8"))


H = EP.parse_equipped_set
JOBS = ("SMN", "PLD", "PUP", "COR", "SCH", "BST", "RNG", "WHM")


# 学者の腰の自動選択を、英語クライアントの値 (天候・曜日・スキル名) で動かす模擬
WAIST_TEST = r"""
local path = arg[1]
local fails = 0
local function check(c, m) if not c then fails = fails + 1; io.write("NG: " .. m .. "\n") end end
local worn = {}
local env = {
    include = function() end, set_language = function() end, send_command = function() end,
    equip = function(s) for k, v in pairs(s) do worn[k] = v end end,
    M = function(t, d) if type(t) == 'table' then return {description = t.description, value = t[1], current = t[1]} end return {value = t} end,
    state = {IdleMode = {options = function() end}, OffenseMode = {options = function() end}, HybridMode = {options = function() end}, CastingMode = {options = function() end}, RangedMode = {options = function() end}},
    sets = {precast = {JA = {}, WS = {}, FC = {}}, midcast = {Pet = {}}, buff = {}, idle = {}, engaged = {}, defense = {}},
    set_combine = function(a, b) local r = {} for k, v in pairs(a or {}) do r[k] = v end for k, v in pairs(b or {}) do r[k] = v end return r end,
    windower = {register_event = function() end, raw_register_event = function() end, ffxi = {}},
    buffactive = {}, world = {}, player = {equipment = {}}, midaction = function() return false end,
}
setmetatable(env, {__index = _G})
local chunk = assert(loadfile(path))
setfenv(chunk, env)
chunk()
env.user_setup()
env.init_gear_sets()
if env.after_gear_sets then env.after_gear_sets() end   -- GearSwap と同じ順 (get_sets の中で init_gear_sets のあと)
local function cast(el, dist, skill, map)
    worn = {}
    env.job_post_midcast({action_type = 'Magic', element = el, skill = skill or 'Elemental Magic', english = 'Fire V',
                          target = {distance = dist}}, {}, map or 'Fire', {})
    return worn.waist
end
env.world = {weather_element = 'Fire', weather_intensity = 2, day_element = 'Fire'}
check(cast('Fire', 10) == 'Hachirin-no-Obi', "Fire weather x2 + Firesday -> Obi")
env.world = {weather_element = 'Water', weather_intensity = 1, day_element = 'Ice'}
check(cast('Fire', 1) == "Orpheus's Sash", "Water weather vs Fire -> Orpheus")
env.world = {weather_element = 'Thunder', weather_intensity = 1, day_element = 'Lightning'}
check(cast('Lightning', 10) == 'Hachirin-no-Obi', "Thunder weather normalizes to Lightning")
env.world = {weather_element = 'None', weather_intensity = 0, day_element = 'Fire'}
check(cast('Fire', 10, 'Healing Magic', 'Cure') == 'Hachirin-no-Obi', "Cure on Firesday -> Obi")
env.buffactive = {Immanence = true}
check(cast('Fire', 1) == nil, "no waist swap under Immanence")
if fails > 0 then os.exit(1) end
print("OK waist (en)")
"""


def ammo_item(name):
    return EP.Item("ammo", name, '"%s"' % name)


def build(job):
    pr = Project(job)
    for e in C.sets_for_job(job):
        path = e["path"]
        if not path.startswith("sets"):
            continue
        pr.assign(path, H('sets.exported={ main="Kenkonken", head="Nyame Helm", body="Nyame Mail", waist="Orpheus\'s Sash" }'))
    pr.add_weapon("main", EP.Item("main", "Naegling", '"Naegling"'))
    pr.add_weapon("main", EP.Item("main", "Naegling", '"Naegling"'))
    pr.set_lockstyle(5)
    if job == "SCH":
        pr.set_auto_waist(True)
    if job == "PLD":
        pr.set_three_stage(True)
        pr.set_fast_cast(40)
    if job == "PUP":
        pr.set_pup_auto(True)
    if job in ("COR", "RNG"):
        pr.set_ammo("physical", ammo_item("Chrono Bullet"))
        pr.set_ammo("magical", ammo_item("Living Bullet"))
        if job == "COR":
            pr.set_ammo("quickdraw", ammo_item("Animikii Bullet"))
        pr.set_ws_ammo("Savage Blade", ammo_item("Hauksbok Bullet"))
    return pr


i18n.set_lang("en")
try:
    outs = {}
    for job in JOBS:
        try:
            lua = build(job).to_lua()
        except Exception as ex:     # 割り当ての途中で失敗したら、それも報告する
            check(False, "%s: 出力できない (%r)" % (job, ex))
            continue
        outs[job] = lua
        bad = [ln for ln in lua.splitlines() if JA_CHARS.search(ln)]
        check(not bad, "%s: 日本語が残っている: %s" % (job, " / ".join(bad[:5])))
        check("set_language('japanese')" not in lua, "%s: set_language('japanese') を出さない" % job)
        check("-- GearSwap file for %s" % job in lua, "%s: 見出しが英語" % job)
    # スキルのキーが英語
    whm = outs.get("WHM", "")
    check("sets.midcast['Healing Magic']" in whm or "sets.midcast['Enhancing Magic']" in whm,
          "WHM: スキルのキーが英語 (sets.midcast['Healing Magic'] など)")
    # 日本語名の別名を出さない (獣使いの「ほんきだせ」など)
    check("Fallback sets" not in outs.get("BST", "") or "JA['" not in outs.get("BST", "").split("Fallback sets")[1].split("end")[0],
          "BST: 日本語名の別名を出さない")
    # 判定の値が英語
    sch = outs.get("SCH", "")
    check("'Hachirin-no-Obi'" in sch and "\"Orpheus's Sash\"" in sch, "SCH: 腰の名前が英語")
    check("buffactive['Immanence']" in sch, "SCH: 震天動地の章は英語名で見る")
    check("spell.skill == 'Elemental Magic'" in sch, "SCH: 精霊魔法は英語名で見る")
    check("['Kenkonken'] = true" in outs.get("PUP", ""), "PUP: 乾坤圏は英語名で見る")
    check("has_attachment('Strobe', 'Strobe II')" in outs.get("PUP", ""), "PUP: ストロボは英語名で見る")
    check("player.sub_job == 'RDM')" in outs.get("PLD", ""), "PLD: サポ赤は RDM で見る")

    if LUAC and os.path.exists(LUAC):
        d = tempfile.mkdtemp()
        for job, lua in outs.items():
            path = os.path.join(d, "%s.lua" % job)
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(lua)
            r = subprocess.run([LUAC, "-p", path], capture_output=True)
            check(r.returncode == 0, "%s: luac を通る %s" % (job, r.stderr.decode("utf-8", "replace")))
        # 模擬 GearSwap: 矢弾の使い分け (英語の出力でも動く)
        if LUA51 and os.path.exists(LUA51):
            # ammo_lua_test.lua は弾の名前を日本語で持つので、弾の名前はそれに合わせ (データなので出力の確認には使わない)、
            # スキル名だけを英語クライアントの値に置き換えた写しで動かす
            pc = Project("COR")
            pc.assign("sets.precast.WS", H('sets.exported={ ammo="クロノブレット", head="Nyame Helm" }'))
            pc.set_ammo("physical", ammo_item("クロノブレット"))
            pc.set_ammo("magical", ammo_item("ライヴブレット"))
            pc.set_ammo("quickdraw", ammo_item("アニミキーブレット"))
            pc.set_ws_ammo("Savage Blade", ammo_item("ホクスボクブレット"))
            pc.set_ws_ammo("Aeolian Edge", ammo_item("ホクスボクブレット"))
            path = os.path.join(d, "COR_ammo.lua")
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(pc.to_lua())
            with open(os.path.join(HERE, "ammo_lua_test.lua"), encoding="utf-8") as fh:
                src = fh.read().replace('"射撃"', '"Marksmanship"').replace('"片手剣"', '"Sword"')
            t_ammo = os.path.join(d, "ammo_en_t.lua")
            with open(t_ammo, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(src)
            r = subprocess.run([LUA51, t_ammo, path], capture_output=True)
            sys.stdout.buffer.write(r.stdout + r.stderr)
            check(r.returncode == 0, "模擬 GearSwap で、英語の出力の矢弾の使い分けが正しい")
            # 模擬 GearSwap: 学者の腰の自動選択 (英語の天候・曜日・装備名)
            t = os.path.join(d, "waist_t.lua")
            with open(t, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(WAIST_TEST)
            r = subprocess.run([LUA51, t, os.path.join(d, "SCH.lua")], capture_output=True)
            sys.stdout.buffer.write(r.stdout + r.stderr)
            check(r.returncode == 0, "模擬 GearSwap で、英語の出力の腰の自動選択が正しい")
finally:
    i18n.set_lang("ja")
check(i18n.lang() == "ja", "日本語に戻す")
check("set_language('japanese')" in Project("WHM").to_lua(), "日本語に戻したら set_language('japanese') を出す")

if fails:
    sys.stdout.buffer.write(("FAILED %d 件\n" % len(fails)).encode("utf-8"))
    sys.exit(1)
sys.stdout.buffer.write("OK 英語の出力: 失敗 0 件\n".encode("utf-8"))
