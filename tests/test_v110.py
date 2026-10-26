# -*- coding: utf-8 -*-
"""1.1.0 で足したセットと仕組みを、全ジョブで確かめる (日本語・英語の両方)。
実行 (GearSwapKit/ で): python -I tests/test_v110.py"""
import os
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
GEAR = {"sets.TreasureHunter": 'head="TH帽"', "sets.engaged.dual11": 'waist="dual11腰"',
        "sets.engaged.dual21": 'waist="dual21腰"', "sets.midcast.Entrust": 'head="エントラスト帽"'}

# 一覧に出るジョブ
def paths(job):
    return [e["path"] for e in C.sets_for_job(job)]


for job in C.ALL_JOBS:
    p = paths(job)
    for need in ("sets.precast.WS.Critical", "sets.TreasureHunter", "sets.engaged.Acc", "sets.engaged.SubtleBlow"):
        check(need in p, "%s に %s がある" % (job, need))
    check(("sets.engaged.dual11" in p) == (job in C.DUAL_JOBS), "%s の二刀流" % job)
    check(("sets.idle.Refresh" in p) == (job in ("MNK", "WHM", "BLM", "RDM", "PLD", "BRD", "RNG", "SMN", "BLU", "PUP", "SCH", "GEO", "RUN")),
          "%s の待機 (リフレシュ)" % job)
    check(("sets.midcast['精霊魔法'].MB" in p) == (job in ("BLM", "RDM", "SCH", "GEO")), "%s の MB" % job)
    check(len(p) == len(set(p)), "%s の一覧に重複が無い" % job)

d = tempfile.mkdtemp()
for lang in ("ja", "en"):
    i18n.set_lang(lang)
    for job in C.ALL_JOBS:
        pr = Project(job)
        for e in C.sets_for_job(job):
            if e["path"].startswith(("weapons:", "ammo:")):
                continue
            pr.assign(e["path"], H('sets.exported={ %s }' % GEAR.get(e["path"], 'neck="x"')))
        lua = pr.to_lua()
        path = os.path.join(d, "%s_%s.lua" % (job, lang))
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(lua)
        if os.path.exists(LUAC):
            r = subprocess.run([LUAC, "-p", path], capture_output=True)
            check(r.returncode == 0, "luac を通る %s %s %s" % (job, lang, r.stderr.decode("utf-8", "replace")))
        if os.path.exists(LUA51):
            subs = ["WAR"] + (["NIN", "DNC"] if job in C.DUAL_JOBS else [])
            if lang == "ja":
                subs = ["戦"] + (["忍", "踊"] if job in C.DUAL_JOBS else [])
            for sub in subs:
                r = subprocess.run([LUA51, os.path.join(HERE, "v110_lua_test.lua"), path, job, sub], capture_output=True)
                if r.returncode != 0:
                    sys.stdout.buffer.write(r.stdout + r.stderr)
                check(r.returncode == 0, "模擬 GearSwap %s %s /%s" % (job, lang, sub))
i18n.set_lang("ja")

if fails:
    sys.stdout.buffer.write(("FAILED %d 件\n" % len(fails)).encode("utf-8"))
    sys.exit(1)
sys.stdout.buffer.write("OK 1.1.0 の追加: 失敗 0 件\n".encode("utf-8"))
