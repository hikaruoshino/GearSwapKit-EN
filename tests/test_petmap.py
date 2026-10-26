# -*- coding: utf-8 -*-
"""召喚士の契約の履行・獣使いの技の分け方 (物理・魔法) の確認。
実行 (GearSwapKit/ で): python -I tests/test_petmap.py"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import _env as ENV
import export_parser as EP
import generator as G
from project import Project

LUA51 = ENV.LUA51
fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)
        sys.stdout.buffer.write(("NG: %s\n" % msg).encode("utf-8"))


data = G._pet_moves()
check(len(data.get("SMN", [])) > 100 and len(data.get("BST", [])) > 100, "分類表 (pet_moves.json) を読める")
kinds = {(j, r["en"]): r["kind"] for j in ("SMN", "BST") for r in data.get(j, [])}
check(kinds.get(("SMN", "Predator Claws")) == "physical", "プレデタークローは物理")
check(kinds.get(("SMN", "Meteor Strike")) == "magical", "メテオストライクは魔法")
check(kinds.get(("SMN", "Hastega")) == "buff" and kinds.get(("SMN", "Sleepga")) == "debuff", "ヘイスガは強化・スリプガは弱体")

H = EP.parse_equipped_set


def lua_for(job, sets):
    pr = Project(job)
    for p in sets:
        pr.assign(p, H('sets.exported={ head="%s" }' % p))
    return pr.to_lua()


smn = lua_for("SMN", ("sets.midcast.Pet.AvatarPhysicalPacts", "sets.midcast.Pet.AvatarMagicalPacts", "sets.SmnSkill",
                      "sets.midcast.Pet.AvatarDeBuffWard", "sets.precast.BloodPactWard", "sets.idle.Avatar"))
q = smn.replace('"', "'")
check("['Predator Claws'] = 'AvatarPhysicalPacts'" in q and "['Meteor Strike'] = 'AvatarMagicalPacts'" in q,
      "召喚士: 物理・魔法の履行の分け方を出す")
check("['Hastega'] = 'AvatarBuffWard'" in q and "['Sleepga'] = 'AvatarDeBuffWard'" in q, "召喚士: 強化・弱体の履行を分ける")
check("sets.midcast.Pet.AvatarBuffWard = sets.SmnSkill" in smn, "強化の履行のセットが無ければ、召喚魔法スキルの装備を使う")
check("sets.precast.BloodPactRage = sets.precast.BloodPactWard" in smn, "幻術の履行も、履行の短縮の装備で使う")
check("sets.idle.Pet = sets.idle.Avatar" in smn, "召喚獣がいるときの待機は sets.idle.Avatar (Mote が見る sets.idle.Pet に入れる)")
only_phys = lua_for("SMN", ("sets.midcast.Pet.AvatarPhysicalPacts",))
check("AvatarMagicalPacts" not in only_phys, "セットの無い分類は、分け方に入れない")
import set_catalog as C
smn_paths = [e["path"] for e in C.sets_for_job("SMN")]
check("sets.midcast['召喚魔法']" not in smn_paths and "sets.midcast.Pet.BloodPactRage" not in smn_paths,
      "召喚魔法 (呼ぶとき)・召喚獣の技 (幻術) は一覧に出さない")
bst = lua_for("BST", ("sets.midcast.Pet.PhysicalDamage", "sets.midcast.Pet.MagicDamage"))
check("'Foot Kick'] = 'PhysicalDamage'" in bst.replace('"', "'"), "獣使い: フットキックは物理")
check("MagicDamage" in bst, "獣使い: 魔法・弱体の技は魔命のセット")
check("pet_move_map" not in lua_for("WAR", ("sets.engaged",)), "ほかのジョブには出さない")

# 模擬 GearSwap: job_get_spell_map がペットの技だけを分ける (同じ名前の魔法 = 自分のファイアII などは分けない)
if os.path.exists(LUA51):
    test = '''
local env = setmetatable({include=function() end, set_language=function() end, send_command=function() end,
    M=function(t) return {} end, state={IdleMode={options=function() end}},
    sets={precast={JA={},WS={}}, midcast={Pet={}}, idle={}, engaged={}, buff={}},
    set_combine=function(a,b) local r={} for k,v in pairs(a) do r[k]=v end for k,v in pairs(b) do r[k]=v end return r end},
    {__index=_G})
local f = assert(loadfile(arg[1])); setfenv(f, env); f(); env.user_setup(); env.init_gear_sets()
local m = env.job_get_spell_map
assert(m({type="BloodPactRage", english="Predator Claws"}) == "AvatarPhysicalPacts", "物理")
assert(m({type="BloodPactRage", english="Fire II"}) == "AvatarMagicalPacts", "履行のファイアII")
assert(m({type="BlackMagic", english="Fire II"}) == nil, "自分のファイアII は分けない")
assert(m({type="BloodPactWard", english="Hastega"}) == "AvatarBuffWard", "強化の履行")
assert(m({type="BloodPactWard", english="Sleepga"}) == "AvatarDeBuffWard", "弱体の履行")
print("OK")
'''
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "SMN.lua"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(smn)
    with open(os.path.join(d, "t.lua"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(test)
    r = subprocess.run([LUA51, os.path.join(d, "t.lua"), os.path.join(d, "SMN.lua")], capture_output=True)
    check(r.returncode == 0 and b"OK" in r.stdout, "模擬 GearSwap で、ペットの技だけを分ける " + (r.stderr or b"").decode("utf-8", "replace"))

if fails:
    sys.stdout.buffer.write(("FAILED %d 件\n" % len(fails)).encode("utf-8"))
    sys.exit(1)
sys.stdout.buffer.write("OK ペットの技の分け方: 失敗 0 件\n".encode("utf-8"))
