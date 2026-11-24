# -*- coding: utf-8 -*-
"""Checks the Impact-only sets (precast and midcast) added in 1.3.1.
Impact needs Twilight Cloak (a body piece that also locks the head slot), so casting it must pick the Impact sets
rather than the normal Fast Cast set, take the hat off (head=empty), and skip buff gear.
Run from GearSwapKit/: python -I tests/test_impact.py"""
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import _env as ENV
import export_parser as EP
import i18n
import set_catalog as C
from project import Project

LUAC = ENV.LUAC
LUA51 = ENV.LUA51
JP = re.compile(r"[぀-ヿ㐀-鿿＀-￯]")
fails = []
skipped = []
MAGIC_KIND = 2      # The "Magic" kind of per-move sets (third entry of set_catalog.CUSTOM_KINDS)

FC_PATH, MID_PATH = "sets.precast.FC['Impact']", "sets.midcast['Impact']"
FC_ALIAS, MID_ALIAS = "sets.precast.FC['インパクト']", "sets.midcast['インパクト']"
CELERITY = "sets.buff['Celerity']"      # Gear for casting while the buff is up (head and feet)


def check(cond, msg):
    if not cond:
        fails.append(msg)
        sys.stdout.buffer.write(("NG: %s\n" % msg).encode("utf-8"))


def parse(body):
    return EP.parse_equipped_set("sets.exported={ %s }" % body)


def impact_jobs_from_res():
    """Job abbreviations (from jobs.lua) in the levels of res/spells.lua id=503 (Impact). None without res."""
    spells, jobs = os.path.join(ENV.RES, "spells.lua"), os.path.join(ENV.RES, "jobs.lua")
    if not (ENV.RES and os.path.exists(spells) and os.path.exists(jobs)):
        return None
    with open(spells, encoding="utf-8") as fh:
        line = next((x for x in fh if x.lstrip().startswith("[503] = {id=503,")), "")
    m = re.search(r"levels=\{([^}]*)\}", line)
    ids = [int(x) for x in re.findall(r"\[(\d+)\]=", m.group(1))] if m else []
    with open(jobs, encoding="utf-8") as fh:
        ens = {int(a): b for a, b in re.findall(r"\[(\d+)\] = \{id=\d+,.*?ens=\"([A-Z]+)\"", fh.read())}
    return {ens[i] for i in ids if i in ens}


def warns(pr):
    """Impact warnings shown by "Create Lua". None if the version under test has no such check."""
    f = getattr(pr, "impact_warnings", None)
    return f() if f else None


def make(job, cloak, head=None, fc=True, body_fc=None, cast_gear=True, imm=False):
    """A Project with both Impact sets, plus normal FC, Elemental Magic and buff gear to compare against."""
    pr = Project(job)
    if fc:
        pr.assign("sets.precast.FC", parse('head="ＦＣの頭", body="ＦＣの胴", feet="ＦＣの足"'))
        pr.assign("sets.midcast['精霊魔法']", parse('head="精霊の頭", body="精霊の胴", waist="セットの腰"'))
    extra = (', head="%s"' % head) if head else ""
    pr.assign(FC_PATH, parse('body="%s", feet="ＦＣの足"%s' % (body_fc or cloak, extra)))
    pr.assign(MID_PATH, parse('body="%s", waist="専用の腰"%s' % (cloak, extra)))
    if cast_gear:
        pr.custom.append((CELERITY, "効果中に魔法をするときの装備: 電光石火の章 (Celerity)", None))
        pr._cur().buffs[CELERITY] = (999, "Celerity", "電光石火の章", "both", "Magic")
        pr.assign(CELERITY, parse('head="章の頭", feet="章の足"'))
    if imm:
        pr.custom.append(("sets.buff['Immanence']", "効果中に魔法をするときの装備: 震天動地の章 (Immanence)", None))
        pr._cur().buffs["sets.buff['Immanence']"] = (470, "Immanence", "震天動地の章", "midcast", "Magic")
        pr.assign("sets.buff['Immanence']", parse('hands="ＡＣブレーサー+3", body="震天の胴"'))
    pr.set_auto_waist(True)
    return pr


# (a) Both entries appear only for the jobs in the res levels
i18n.set_lang("ja")
res_jobs = impact_jobs_from_res()
if res_jobs is None:
    skipped.append("res (インパクトのジョブの照合)")
else:
    check(set(C.IMPACT_JOBS) == res_jobs, "IMPACT_JOBS が res の levels と同じ (%s / %s)" % (sorted(C.IMPACT_JOBS), sorted(res_jobs)))
for job in C.ALL_JOBS:
    rows = {e["path"]: e for e in C.sets_for_job(job)}
    has = (FC_PATH in rows, MID_PATH in rows)
    if job in C.IMPACT_JOBS:
        check(has == (True, True), "%s に、インパクトの 2 項目がある" % job)
        check(rows.get(FC_PATH, {}).get("alias") == FC_ALIAS and rows.get(MID_PATH, {}).get("alias") == MID_ALIAS,
              "%s: 日本語名の別名がある" % job)
    else:
        check(has == (False, False), "%s には、インパクトの項目を出さない" % job)
blm = {e["path"]: e for e in C.sets_for_job("BLM")}
for p in (FC_PATH, MID_PATH):
    h = blm.get(p, {}).get("help", "")
    check("トワイライトプリス" in h and "頭" in h, "%s の説明に、トワイライトプリスと頭の注意がある" % p)
check("ファストキャストの装備を入れます" in blm.get(FC_PATH, {}).get("help", ""), "FC の説明は「ファストキャストの装備を入れます」")
check(blm.get(MID_PATH, {}).get("title") == "インパクト (詠唱中・着弾)", "詠唱中の題名")

# Adding Impact as a "Magic" per-move set is refused as a duplicate: the list already has that set
pr = Project("BLM")
check(pr.add_custom(MAGIC_KIND, "Impact") == ("dup", None), "技ごとの追加で Impact を足すと重複になる")
check(pr.add_pair(MAGIC_KIND, "Impact", "インパクト") == "dup", "一覧から選んでも重複になる")
check(pr.add_custom(MAGIC_KIND, "Fire") == ("ok", "sets.midcast['Fire']"), "ほかの魔法は今までどおり足せる")
# An Impact per-move set saved by an older version (same key) merges with the list entry
po = Project("BLM")
po.custom.append((MID_PATH, "魔法: インパクト (Impact)", MID_ALIAS))
po.assign(MID_PATH, parse('body="トワイライトプリス"'))
check([r["path"] for r in po.entries()].count(MID_PATH) == 1, "前の版で足したインパクトは、一覧に 1 行だけ")
lo = po.to_lua()
check(lo.count("    %s = {" % MID_PATH) == 1 and lo.count("    %s = %s" % (MID_ALIAS, MID_PATH)) == 1,
      "前の版で足したインパクトも、セットと別名を 1 回だけ出す")

# (b) Japanese output: the sets, their aliases, and head=empty
lua_ja = make("BLM", "トワイライトプリス").to_lua()
check("    %s = {" % FC_PATH in lua_ja and "    %s = {" % MID_PATH in lua_ja, "2 つのセットを出す")
check("    %s = %s" % (FC_ALIAS, FC_PATH) in lua_ja and "    %s = %s" % (MID_ALIAS, MID_PATH) in lua_ja, "日本語名の別名の行を出す")
check(lua_ja.count("head=empty,") == 2, "頭を割り当てていない 2 つのセットにだけ head=empty を出す")
lua_head = make("BLM", "トワイライトプリス", head="別の頭").to_lua()
check("head=empty," not in lua_head and lua_head.count('head="別の頭",') == 2, "頭を割り当てたときは、その頭のまま")

# "Create Lua" warnings: a head piece is assigned, or the body isn't a cloak that can cast Impact
check(warns(make("BLM", "トワイライトプリス")) == [], "正しく作れば警告しない")
check(warns(make("BLM", "クレパスクラプリス")) == [], "クレパスクラプリス (res 23799・インパクト使用可能) も警告しない")
w_head = warns(make("BLM", "トワイライトプリス", head="別の頭"))
check(w_head is not None and len(w_head) == 2 and all("頭" in w for w in w_head), "頭を割り当てたら、2 つのセットとも警告する (%s)" % w_head)
w_body = warns(make("BLM", "トワイライトプリス", body_fc="ＦＣの胴"))
check(w_body is not None and len(w_body) == 1 and "トワイライトプリス" in w_body[0], "FC の胴がプリスでなければ警告する (%s)" % w_body)
check(warns(Project("WAR")) == [], "インパクトの無いジョブは警告しない")

# (c) English mode: no alias lines; titles, help and warnings in English
i18n.set_lang("en")
lua_en = make("BLM", "Twilight Cloak").to_lua()
check("    %s = {" % FC_PATH in lua_en and lua_en.count("head=empty,") == 2, "英語版も 2 つのセットと head=empty を出す")
check(FC_ALIAS not in lua_en and MID_ALIAS not in lua_en, "英語版には日本語名の別名を出さない")
w_en = warns(make("BLM", "Twilight Cloak", head="Other Hat"))
check(w_en is not None and len(w_en) == 2 and not any(JP.search(w) for w in w_en), "英語版の警告は英語 (%s)" % w_en)
check(warns(make("BLM", "twilight cloak")) == [], "英語名は大文字小文字を区別しない (GearSwap と同じ)")
for job in sorted(C.IMPACT_JOBS):
    en_rows = [r for r in Project(job).entries() if r["path"] in (FC_PATH, MID_PATH)]
    check(len(en_rows) == 2, "%s: 英語版にもインパクトの 2 項目がある" % job)
    for r in en_rows:
        check(r["title"] and r["help"] and not JP.search(r["title"] + r["help"]), "%s %s: 英語に日本語が無い" % (job, r["path"]))
        check("Twilight Cloak" in r["help"] and "head" in r["help"].lower(), "%s %s: 英語の説明にプリスと頭" % (job, r["path"]))
en_mid = {r["path"]: r for r in Project("BLM").entries()}.get(MID_PATH, {})
check(en_mid.get("title") == "Impact (midcast / until it lands)", "英語の題名を日本語とそろえる (%s)" % en_mid.get("title"))
i18n.set_lang("ja")

# Version
with open(os.path.join(ROOT, "app.py"), encoding="utf-8") as fh:
    version = re.search(r'^VERSION = "(\d+)\.(\d+)\.(\d+)"$', fh.read(), re.MULTILINE)
    check(version is not None and tuple(map(int, version.groups())) >= (1, 3, 1),
          "インパクト対応の 1.3.1 以降")

# (d) Mock GearSwap: Mote-Include's set lookup (name -> spellMap -> skill) plus job_post_precast / job_post_midcast
LUA_TEST = r'''
local worn = {}
local env = setmetatable({include=function() end, set_language=function() end, send_command=function() end,
    empty="empty",
    equip=function(t) for k,v in pairs(t) do worn[k]=v end end,
    M=function(a,b) local o = {value=(type(a)=="table") and a[1] or a, current=(type(a)=="table") and a[1] or a}
        o.options=function() end return o end,
    state={IdleMode={options=function() end}, CastingMode={current="Normal", value="Normal", options=function() end}},
    buffactive={},
    world={weather_element="なし", weather_intensity=0, day_element="なし"},
    sets={precast={FC={},JA={},WS={}}, midcast={Pet={}}, idle={}, engaged={}, buff={}},
    set_combine=function(a,b) local r={} for k,v in pairs(a) do r[k]=v end for k,v in pairs(b) do r[k]=v end return r end},
    {__index=_G})
local f = assert(loadfile(arg[1])); setfenv(f, env); f()
env.user_setup(); env.init_gear_sets()
if env.after_gear_sets then env.after_gear_sets() end
local sets = env.sets
local name, skill, other, cloak, dark, fire_el, imm = ARGS[1], ARGS[2], ARGS[3], ARGS[4], ARGS[5], ARGS[6], ARGS[7]
local function named(set, spell)
    if set[spell.name] then return set[spell.name] end
    return set
end
local function select(set, spell)
    local s = named(set, spell)
    if s == set and spell.skill and set[spell.skill] then s = named(set[spell.skill], spell) end
    return s
end
-- 待機の頭と胴を着た状態から、詠唱の開始 → 詠唱中
local function cast(spell)
    worn = {head="待機の頭", body="待機の胴", feet="待機の足"}
    env.equip(select(sets.precast.FC, spell))
    if env.job_post_precast then env.job_post_precast(spell, {}, nil, {}) end
    local pre = {} for k, v in pairs(worn) do pre[k] = v end
    env.equip(select(sets.midcast, spell))
    if env.job_post_midcast then env.job_post_midcast(spell, {}, nil, {}) end
    return pre, worn
end
local impact = {name=name, english="Impact", skill=skill, element=dark, action_type="Magic", target={distance=1}}
local fire = {name=other, english="Fire", skill=skill, element=fire_el, action_type="Magic", target={distance=1}}
-- 電光石火の章 (999) が効いている。腰の自動選択が効く天候・曜日にする
env.buffactive[999] = true
env.world.weather_element, env.world.weather_intensity, env.world.day_element = dark, 2, dark
if imm == "1" then env.buffactive["震天動地の章"], env.buffactive["Immanence"] = true, true end
local pre, mid = cast(impact)
assert(pre.body == cloak, "インパクトの詠唱の開始で、胴がプリス: " .. tostring(pre.body))
assert(pre.head == "empty", "インパクトの詠唱の開始で、頭を外す: " .. tostring(pre.head))
assert(pre.feet == "ＦＣの足", "インパクトの詠唱の開始に、強化中の装備を重ねない: " .. tostring(pre.feet))
assert(mid.body == cloak, "インパクトの詠唱中も、胴がプリス: " .. tostring(mid.body))
assert(mid.head == "empty", "インパクトの詠唱中も、頭を外す: " .. tostring(mid.head))
assert(mid.feet == "ＦＣの足", "インパクトの詠唱中に、強化中の装備を重ねない: " .. tostring(mid.feet))
assert(mid.waist == "専用の腰", "インパクトでは腰を自動で替えない: " .. tostring(mid.waist))
assert(mid.hands == nil, "インパクトに、震天動地の章の装備を重ねない: " .. tostring(mid.hands))
pre, mid = cast(fire)
assert(pre.body == "ＦＣの胴", "ほかの魔法は、通常の FC")
assert(pre.head == "章の頭" and pre.feet == "章の足", "ほかの魔法の詠唱の開始には、強化中の装備を重ねる")
assert(mid.feet == "章の足", "ほかの魔法の詠唱中にも、強化中の装備を重ねる")
if imm == "1" then
    assert(mid.hands == "ＡＣブレーサー+3", "ほかの魔法には、震天動地の章の装備を重ねる")
else
    assert(mid.body == "精霊の胴", "ほかの精霊魔法は、精霊魔法の装備")
end
print("OK")
'''


def write_tmp(text, name):
    d = tempfile.mkdtemp()
    p = os.path.join(d, name)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return p


def luac_ok(lua, label):
    p = write_tmp(lua, "JOB.lua")
    r = subprocess.run([LUAC, "-p", p], capture_output=True)
    check(r.returncode == 0, label + ": luac を通る " + r.stderr.decode("utf-8", "replace"))
    return p


def run_lua(lua, args, label):
    p = luac_ok(lua, label)
    # The Windows command line garbles UTF-8 Japanese, so the arguments go inside the script instead
    t = write_tmp("local ARGS = {%s}\n" % ", ".join('"%s"' % a for a in args) + LUA_TEST, "t.lua")
    r = subprocess.run([LUA51, t, p], capture_output=True)
    check(r.returncode == 0 and b"OK" in r.stdout,
          label + ": 模擬 GearSwap で、インパクト用のセットを選ぶ " + r.stderr.decode("utf-8", "replace"))


if not os.path.exists(LUAC):
    skipped.append("luac (構文の確認)")
else:
    only = make("GEO", "トワイライトプリス", fc=False, cast_gear=False).to_lua()
    check("    %s = {" % FC_PATH in only and "    sets.precast.FC = {" not in only, "FC を割り当てずインパクトだけでも出す")
    luac_ok(only, "FC を割り当てずインパクトだけ")
if not (os.path.exists(LUA51) and os.path.exists(LUAC)):
    skipped.append("lua5.1 (模擬 GearSwap)")
else:
    ja = ["インパクト", "精霊魔法", "ファイア", "トワイライトプリス", "闇", "火"]
    for job in ("BLM", "RDM", "GEO", "DRK"):
        run_lua(make(job, "トワイライトプリス").to_lua(), ja + ["0"], "%s 日本語版" % job)
    run_lua(make("SCH", "トワイライトプリス", imm=True).to_lua(), ja + ["1"], "SCH 日本語版 (震天動地の章)")
    i18n.set_lang("en")
    en = ["Impact", "Elemental Magic", "Fire", "Twilight Cloak", "Dark", "Fire"]
    run_lua(make("BLM", "Twilight Cloak").to_lua(), en + ["0"], "BLM 英語版")
    run_lua(make("SCH", "Twilight Cloak", imm=True).to_lua(), en + ["1"], "SCH 英語版 (震天動地の章)")
    i18n.set_lang("ja")

skip_note = (" (飛ばした: %s)" % "・".join(skipped)) if skipped else ""
if fails:
    sys.stdout.buffer.write(("FAILED %d 件%s\n" % (len(fails), skip_note)).encode("utf-8"))
    sys.exit(1)
sys.stdout.buffer.write(("OK インパクトの専用セット: 失敗 0 件%s\n" % skip_note).encode("utf-8"))
