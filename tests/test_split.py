# -*- coding: utf-8 -*-
"""出力した ジョブ.lua の「装備のセット」の部分を、ジョブ_gear.lua に丸ごと写しても動くかを確かめる (全ジョブ・日本語と英語)。
- 印 (装備のセット ここから / ここまで) が 1 組だけあり、その中は init_gear_sets の関数だけ
- 切り出した部分だけで luac を通る
- 切り出した部分が、システムの部分の local (buff_gear など) を使っていない (別のファイルからは見えないため)
- システムの部分 + 別のファイルとして読んだ装備のセット で、模擬 GearSwap の確認 (v110_lua_test.lua) が通る
実行 (GearSwapKit/ で): python -I tests/test_split.py"""
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
fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)
        sys.stdout.buffer.write(("NG: %s\n" % msg).encode("utf-8"))


H = EP.parse_equipped_set
# v110_lua_test.lua が名前で確かめる装備 (test_v110.py と同じ)
GEAR = {"sets.TreasureHunter": 'head="TH帽"', "sets.engaged.dual11": 'waist="dual11腰"',
        "sets.engaged.dual21": 'waist="dual21腰"', "sets.midcast.Entrust": 'head="エントラスト帽"',
        "sets.Sleep": 'main="プライムソード", head="フレンジーサリット"', "sets.midcast.IncreasedCursna": 'neck="カーズナ首"',
        "sets.idle.Avatar.Favor": 'head="加護帽"', "sets.LowHp": 'body="LowHp胴"', "sets.KnockBack": 'back="リパルスマント"',
        "sets.midcast['強化魔法'].Other": 'body="他人胴"', "sets.midcast.Refresh": 'head="リフレ帽"',
        "sets.midcast.EnfeeblingEffectInt": 'head="INT帽"', "sets.midcast.EnfeeblingEffectMnd": 'head="MND帽"',
        "sets.midcast.BlueMagicAcc": 'head="青魔命帽"'}
MARKS = {"ja": ("-- ======== 装備のセット ここから ========", "-- ======== 装備のセット ここまで ========"),
         "en": ("-- ======== GEAR SETS BEGIN ========", "-- ======== GEAR SETS END ========")}

d = tempfile.mkdtemp()
for lang in ("ja", "en"):
    i18n.set_lang(lang)
    begin, end = MARKS[lang]
    for job in C.ALL_JOBS:
        pr = Project(job)
        for e in C.sets_for_job(job):
            if e["path"].startswith(("weapons:", "ammo:")):
                continue
            pr.assign(e["path"], H('sets.exported={ %s }' % GEAR.get(e["path"], 'neck="x"')))
        lua = pr.to_lua()
        name = "%s %s" % (job, lang)
        check(lua.count(begin) == 1 and lua.count(end) == 1, "%s: 印が 1 組ある" % name)
        if lua.count(begin) != 1 or lua.count(end) != 1:
            continue
        a = lua.index(begin)
        b = lua.index(end) + len(end)
        gear = lua[a:b]
        system = lua[:a] + lua[b:]
        check(("_gear.lua" in gear.split("\n")[1]), "%s: 印のすぐ下に、ジョブ_gear.lua の作り方の一文がある" % name)
        code = [ln for ln in gear.split("\n") if ln.strip() and not ln.strip().startswith("--")]
        check(code[0] == "function init_gear_sets()" and code[-1] == "end", "%s: 装備のセットの中は init_gear_sets の関数だけ" % name)
        # システムの部分のファイルの頭の local を、装備のセットが使っていないか
        locals_ = set(re.findall(r"^local (?:function )?([A-Za-z_][A-Za-z0-9_]*)", system, re.M))
        for extra in re.findall(r"^local ([A-Za-z_][A-Za-z0-9_, ]*?)\s*=", system, re.M):
            locals_.update(n.strip() for n in extra.split(","))
        used = sorted(n for n in locals_ if re.search(r"\b%s\b" % re.escape(n), "\n".join(code)))
        check(not used, "%s: 装備のセットが、システムの local を使っていない (%s)" % (name, ", ".join(used)))
        gear_path = os.path.join(d, "%s_%s_gear.lua" % (job, lang))
        with open(gear_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(gear + "\n")
        if os.path.exists(LUAC):
            r = subprocess.run([LUAC, "-p", gear_path], capture_output=True)
            check(r.returncode == 0, "%s: 切り出した装備のセットだけで luac を通る %s" % (name, r.stderr.decode("utf-8", "replace")))
        # システムの部分 + 別のファイルの装備のセット (GearSwap がサイドカーを読むのと同じく、local は見えない)
        side = gear_path.replace("\\", "/")
        split_lua = system + ("\nlocal sidecar = assert(loadfile('%s'))\nsetfenv(sidecar, getfenv(1))\nsidecar()\n" % side)
        split_path = os.path.join(d, "%s_%s_split.lua" % (job, lang))
        with open(split_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(split_lua)
        if os.path.exists(LUA51):
            sub = "WAR" if lang == "en" else "戦"
            r = subprocess.run([LUA51, os.path.join(HERE, "v110_lua_test.lua"), split_path, job, sub], capture_output=True)
            if r.returncode != 0:
                sys.stdout.buffer.write(r.stdout + r.stderr)
            check(r.returncode == 0, "%s: ジョブ_gear.lua に分けても、模擬 GearSwap の確認が通る" % name)
i18n.set_lang("ja")

if fails:
    sys.stdout.buffer.write(("FAILED %d 件\n" % len(fails)).encode("utf-8"))
    sys.exit(1)
sys.stdout.buffer.write("OK ジョブ_gear.lua への分け方: 失敗 0 件\n".encode("utf-8"))
