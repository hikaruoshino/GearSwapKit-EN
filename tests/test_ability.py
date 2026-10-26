# -*- coding: utf-8 -*-
"""アビリティ強化の装備 (ability_gear.json・ability_gear.py・Project.add_ability_gear) の確認。
実行 (GearSwapKit/ で): python -I tests/test_ability.py"""
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
import export_parser as EP
import resdb as RDB
from project import Project

RES = ENV.RES
LUAC = ENV.LUAC
LUA51 = ENV.LUA51

fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)
        sys.stdout.buffer.write(("NG: %s\n" % msg).encode("utf-8"))


def out(text):
    sys.stdout.buffer.write((text + "\n").encode("utf-8"))


table = AG.load()
check(bool(table), "対応表が読める")
check("SMN" in table and len(table["SMN"]) == 4, "SMN に 4 つ (アストラルフロウ・神獣の加護・マナシード・エレメントサイフォン)")

# --- 対応表の中身の整合 ---
VALID_SLOTS = set(EP.SLOTS)
for job, entries in table.items():
    for e in entries:
        tag = "%s/%s" % (job, e["ability_en"])
        check(e["slot"] in VALID_SLOTS, tag + ": スロット名が正しい")
        check(e["timing"] in AG.TIMING_NAMES, tag + ": timing が正しい")
        check(bool(e["items"]), tag + ": 装備がある")
        names = [i["ja"] for i in e["items"]]
        check(len(names) == len(set(names)), tag + ": 装備名に重複がない")
        if e["timing"] == "while_active":
            check(bool(e.get("buff")) and e["buff"].get("id"), tag + ": 効果中ずっと着るものは、バフの情報がある")

# --- res との突き合わせ (res がある環境だけ) ---
if os.path.isfile(os.path.join(RES, "items.lua")):
    def read(name):
        with open(os.path.join(RES, name), "rb") as f:
            return f.read().decode("utf-8", errors="replace")
    items_txt = read("items.lua")
    ja_items = set(re.findall(r'\bja="([^"]*)"', items_txt))
    abil_txt = read("job_abilities.lua")
    abilities = set(re.findall(r'\ben="([^"]*)",ja="([^"]*)"', abil_txt))
    abilities |= set(re.findall(r'\ben="([^"]*)",ja="([^"]*)"', read("spells.lua")))   # 学者の虚誘掩殺の策など、魔法の強化
    buffs_txt = read("buffs.lua")
    buffs = {int(m[0]): (m[1], m[2]) for m in re.findall(r'\bid=(\d+),en="([^"]*)",ja="([^"]*)"', buffs_txt)}
    for job, entries in table.items():
        for e in entries:
            tag = "%s/%s" % (job, e["ability_en"])
            if not e.get("set_path"):      # set_path のもの (マニューバなど) は、まとめのセットなので名前の照合はしない
                check((e["ability_en"], e["ability_ja"]) in abilities, tag + ": アビリティ名が res の job_abilities と一致")
            for i in e["items"]:
                check(i["ja"] in ja_items, tag + ": 装備名 %s が res の items にある" % i["ja"])
            if e.get("buff"):
                b = e["buff"]
                check(buffs.get(int(b["id"])) == (b["en"], b["ja"]), tag + ": バフの番号と名前が res の buffs と一致")
else:
    out("(res が無いので、res との突き合わせは省略)")

# --- 所持品との照合 ---
INV = EP.parse_inventory('''sets.exported={
 head="ＧＬホーン+1", head={ name="ＢＣホーン+2", augments={'Path: A',}}, head="ベコナーホーン", head="アストラルホーン",
 hands="ＢＣブレーサー+1", hands="ＢＣブレーサー+3",
 feet="Glyphic Piggash +1", feet="ＢＣピガッシュ+1",
 body="ＢＣダブレット+3",
}''')
by = {e["ability_en"]: e for e in table["SMN"]}
f = AG.owned(by["Astral Flow"], INV)
check([i.name for _g, _s, i in f] == ["ＧＬホーン+1"], "アストラルフロウ: 持っている頭は ＧＬホーン+1 だけ")
f = AG.owned(by["Avatar's Favor"], INV)
check([i.name for _g, _s, i in f] == ["ベコナーホーン", "ＢＣホーン+2"], "神獣の加護: 世代の低い順 (ベコナーホーン → ＢＣホーン+2)")
check(AG.best_owned(by["Avatar's Favor"], INV)[2].name == "ＢＣホーン+2", "神獣の加護: 持っている中で一番高い世代は ＢＣホーン+2")
check(AG.best_owned(by["Mana Cede"], INV)[2].name == "ＢＣブレーサー+3", "マナシード: ＢＣブレーサー+3")
check(AG.owned(by["Elemental Siphon"], INV) and [i.name for _g, _s, i in AG.owned(by["Elemental Siphon"], INV)] == ["ＢＣピガッシュ+1"],
      "エレメントサイフォン: 日本語名だけ照合 (res 無し)")
if os.path.isfile(os.path.join(RES, "items.lua")):
    rdb = RDB.ResDB(RES)
    f = AG.owned(by["Elemental Siphon"], INV, rdb)
    check(sorted(i.name for _g, _s, i in f) == ["Glyphic Piggash +1", "ＢＣピガッシュ+1"] or
          sorted(i.name for _g, _s, i in f) == ["ＢＣピガッシュ+1"],
          "英語名の所持品の照合 (res がある場合)。スペルの違う名前は一致しない")
    inv_en = EP.parse_inventory('sets.exported={ head="Glyphic Horn +1", feet="Beckoner\'s Pigaches +1" }')
    f = AG.owned(by["Astral Flow"], inv_en, rdb)
    check([i.name for _g, _s, i in f] == ["Glyphic Horn +1"], "英語名の所持品 (Glyphic Horn +1) も、アストラルフロウの候補になる")

# --- Project に追加して Lua を作る ---
pr = Project("SMN")
p_af = pr.add_ability_gear(by["Astral Flow"], AG.best_owned(by["Astral Flow"], INV)[2])
check(p_af == "sets.precast.JA['Astral Flow']", "使う瞬間だけ着るものは sets.precast.JA['英語名'] (実際 %s)" % p_af)
p_fav = pr.add_ability_gear(by["Avatar's Favor"], AG.best_owned(by["Avatar's Favor"], INV)[2])
check(p_fav == "sets.buff['Avatar\\'s Favor']", "効果中ずっと着るものは sets.buff['英語名'] (実際 %s)" % p_fav)
pr.add_ability_gear(by["Mana Cede"], AG.best_owned(by["Mana Cede"], INV)[2])
pr.add_ability_gear(by["Elemental Siphon"], AG.best_owned(by["Elemental Siphon"], INV)[2])
check(pr.has_work("SMN"), "作業ありになる")
lua = pr.to_lua()
check("sets.precast.JA['Astral Flow'] = {" in lua and 'head="ＧＬホーン+1"' in lua, "アストラルフロウのセットが出る")
check("sets.precast.JA['アストラルフロウ'] = sets.precast.JA['Astral Flow']" in lua, "日本語名の別名が出る")
check("sets.precast.JA['Mana Cede'] = {" in lua and 'hands="ＢＣブレーサー+3"' in lua, "マナシードは hands (綴りが正しい)")
check("hads" not in lua, "hads の綴りの間違いが無い")
check("sets.buff['Avatar\\'s Favor'] = {" in lua, "神獣の加護は sets.buff に出る")
check("sets.precast.JA['Avatar\\'s Favor']" not in lua, "神獣の加護は precast には出ない")
check("function customize_idle_set(idleSet)" in lua and "function customize_melee_set(meleeSet)" in lua, "待機・戦闘中に重ねる処理が出る")
# 念のための用意: Mote は sets.idle / sets.engaged を空で作るが、無い環境でも customize_idle_set が呼ばれるよう、無ければ空のセットを用意する
check("sets.idle" not in "".join(k for k in pr.assignments) and "sets.idle = sets.idle or {}" in lua
      and "sets.engaged = sets.engaged or {}" in lua, "待機・戦闘中のセットが無くても、空のセットを用意する")
check("buff_gear[#buff_gear + 1] = {431, \"Avatar's Favor\", \"神獣の加護\", sets.buff['Avatar\\'s Favor']}" in lua, "バフの登録が出る")
# 同じ部位を置き換える
pr.add_ability_gear(by["Mana Cede"], AG.owned(by["Mana Cede"], INV)[0][2])
check(len(pr.assignments["sets.precast.JA['Mana Cede']"]) == 1 and
      pr.assignments["sets.precast.JA['Mana Cede']"]["hands"].name == "ＢＣブレーサー+1", "同じ部位は置き換える")
# 保存と読み込み
pr2 = Project.from_json(pr.to_json())
check(pr2.to_lua() == pr.to_lua(), "保存して読み込み直しても、同じ Lua になる")
# 削除
pr2.remove_custom(p_fav)
lua2 = pr2.to_lua()
check("buff_gear" not in lua2 and "sets.buff[" not in lua2, "効果中の追加を削除すると、重ねる処理も消える")
# 一覧に出る
rows = {r["path"]: r for r in pr.entries()}
check(p_fav in rows and "効果中" in rows[p_fav]["help"] or "着たまま" in rows[p_fav]["help"], "一覧に効果中の装備が出て、説明がある")
check(not Project("COR").has_work("COR"), "ほかのジョブには出ない")

# まとめのセット (set_path): PUP のマニューバの胴は sets.precast.JA.Maneuver に入る
man = [e for e in table["PUP"] if e.get("set_path") == "sets.precast.JA.Maneuver"][0]
pp = Project("PUP")
inv_pup = EP.parse_inventory('sets.exported={ body="ＫＧファルセト+2", body="ＣＣファルセット+1" }')
best = AG.best_owned(man, inv_pup)
check(best and best[2].name == "ＫＧファルセト+2", "マニューバの胴: 強化の進んだ ＫＧファルセト+2")
p_man = pp.add_ability_gear(man, best[2])
check(p_man == "sets.precast.JA.Maneuver", "マニューバは sets.precast.JA.Maneuver に入る (実際 %s)" % p_man)
check(not pp.custom, "一覧に元からある場面なので、技ごとの追加は増えない")
check("sets.precast.JA.Maneuver = {" in pp.to_lua() and 'body="ＫＧファルセト+2"' in pp.to_lua(), "Lua に出る")

# 魔法を唱えるとき (学者の章): 電光石火の章の足は詠唱を始めるとき・令狸執鼠の章の手は詠唱中
cel = [e for e in table["SCH"] if e["ability_en"] == "Celerity"][0]
per = [e for e in table["SCH"] if e["ability_en"] == "Perpetuance"][0]
sub = [e for e in table["SCH"] if e["ability_en"] == "Sublimation"][0]
check(cel["timing"] == "cast" and cel["cast_phase"] == "both", "電光石火の章は、詠唱を始めるときと詠唱中の両方")
check(per["timing"] == "cast" and per["cast_phase"] == "midcast", "令狸執鼠の章は、詠唱中")
check(sub["timing"] == "while_active" and sub["buff"]["id"] == 187 and any(i["ja"] == "ＰＤガウン+3" for i in sub["items"]), "机上演習は蓄積中ずっと (wiki: 装備中のみ有効)・ＰＤガウン+3 も候補")
check(any(i["ja"] == "ＰＤローファー+3" for i in cel["items"]), "電光石火の章の足に ＰＤローファー+3 も候補")
ps = Project("SCH")
inv_s = EP.parse_inventory('sets.exported={ feet="ＰＤローファー+3", hands="ＡＢブレーサー+2", body="ＰＤガウン+3" }')
ps.add_ability_gear(cel, AG.best_owned(cel, inv_s)[2])
ps.add_ability_gear(per, AG.best_owned(per, inv_s)[2])
p_sub = ps.add_ability_gear(sub, AG.best_owned(sub, inv_s)[2])
check(p_sub == "sets.buff['Sublimation: Activated']", "机上演習は sets.buff (実際 %s)" % p_sub)
lua_s = ps.to_lua()
check("function job_post_precast" in lua_s and "function job_post_midcast" in lua_s, "詠唱を始めるとき・詠唱中の処理が出る")
check("cast_gear.precast[#cast_gear.precast + 1] = {%d, sets.buff['Celerity'], \"Magic\"}" % cel["buff"]["id"] in lua_s, "電光石火の章は precast に登録")
check("cast_gear.midcast[#cast_gear.midcast + 1] = {%d, sets.buff['Perpetuance'], \"Magic\"}" % per["buff"]["id"] in lua_s, "令狸執鼠の章は midcast に登録")
check("cast_gear.midcast[#cast_gear.midcast + 1] = {%d, sets.buff['Celerity'], \"Magic\"}" % cel["buff"]["id"] in lua_s, "電光石火の章は midcast にも登録")
check("customize_idle_set" in lua_s and "{187," in lua_s, "机上演習は蓄積中に待機へ重ねる")
if os.path.exists(LUA51):
    d3 = tempfile.mkdtemp()
    pth3 = os.path.join(d3, "SCH.lua")
    with open(pth3, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(lua_s)
    r = subprocess.run([LUAC, "-p", pth3], capture_output=True)
    check(r.returncode == 0, "学者の Lua が luac を通る " + r.stderr.decode("utf-8", "replace"))
    r = subprocess.run([LUA51, os.path.join(HERE, "cast_lua_test.lua"), pth3, str(cel["buff"]["id"]), str(per["buff"]["id"])], capture_output=True)
    sys.stdout.buffer.write(r.stdout + r.stderr)
    check(r.returncode == 0, "模擬 GearSwap で、詠唱を始めるとき・詠唱中の装備が正しく替わる")

# 効果中に WS・遠隔攻撃をするとき (踊り子の C.フラリッシュ・狩人のダブルショット) と、青魔道士のブルーチェーン (魔法)
clf = [e for e in table["DNC"] if e["ability_en"] == "Climactic Flourish"][0]
dbs = [e for e in table["RNG"] if e["ability_en"] == "Double Shot"][0]
cha = [e for e in table["BLU"] if e["ability_en"] == "Chain Affinity"][0]
check(clf["timing"] == "cast" and clf["cast_on"] == "WeaponSkill" and clf["cast_phase"] == "precast", "C.フラリッシュは WS を始めるとき")
check(dbs["timing"] == "cast" and dbs["cast_on"] == "Ranged Attack" and dbs["cast_phase"] == "midcast", "ダブルショットは遠隔攻撃中")
check(cha["timing"] == "cast" and cha["cast_on"] == "Magic" and cha["cast_phase"] == "midcast", "ブルーチェーンは魔法の詠唱中 (着弾時)")
pd_ = Project("DNC")
pd_.add_ability_gear(clf, EP.parse_equipped_set('sets.exported={ head="ＭＣティアラ+3" }')["head"])
lua_d = pd_.to_lua()
check("cast_gear.precast[#cast_gear.precast + 1] = {%d, sets.buff['Climactic Flourish'], \"WeaponSkill\"}" % clf["buff"]["id"] in lua_d,
      "C.フラリッシュは WS の precast に登録")
pg = Project("RNG")
pg.add_ability_gear(dbs, EP.parse_equipped_set('sets.exported={ head="ＡＭガペット+2" }')["head"])
lua_g = pg.to_lua()
check("cast_gear.midcast[#cast_gear.midcast + 1] = {%d, sets.buff['Double Shot'], \"Ranged Attack\"}" % dbs["buff"]["id"] in lua_g,
      "ダブルショットは遠隔攻撃の midcast に登録")
if os.path.exists(LUA51):
    for name, text, bid, kind in (("DNC", lua_d, clf["buff"]["id"], "WeaponSkill"), ("RNG", lua_g, dbs["buff"]["id"], "Ranged Attack")):
        d5 = tempfile.mkdtemp()
        p5 = os.path.join(d5, name + ".lua")
        with open(p5, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        r = subprocess.run([LUAC, "-p", p5], capture_output=True)
        check(r.returncode == 0, name + " の Lua が luac を通る")
        r = subprocess.run([LUA51, os.path.join(HERE, "action_lua_test.lua"), p5, str(bid), kind], capture_output=True)
        sys.stdout.buffer.write(r.stdout + r.stderr)
        check(r.returncode == 0, "模擬 GearSwap で、%s のときだけ着る" % kind)

# メリット特性 (最適化・微調整): 専用のセット・MeritGear で On のときだけ重ねる
opt = [e for e in table["PUP"] if e["ability_en"] == "Optimization"][0]
fin = [e for e in table["PUP"] if e["ability_en"] == "Fine-Tuning"][0]
inv_m = EP.parse_inventory('sets.exported={ head="ＰＩタージ+3", hands="ＰＩダスタナ+1", hands="ピトルダスタナ" }')
pp.add_ability_gear(opt, AG.best_owned(opt, inv_m)[2])
pp.add_ability_gear(fin, AG.best_owned(fin, inv_m)[2])
lua_m = pp.to_lua()
check("sets.merit = {}" in lua_m and "sets.merit.Optimization = {" in lua_m and 'head="ＰＩタージ+3"' in lua_m, "最適化は sets.merit.Optimization")
check("sets.merit.FineTuning = {" in lua_m and 'hands="ＰＩダスタナ+1"' in lua_m, "微調整は sets.merit.FineTuning (強化の進んだ方)")
check("state.MeritGear = M{['description']='MeritGear', 'Off', 'On'}" in lua_m, "MeritGear の切り替え (既定は Off)")
check(lua_m.count("function customize_idle_set") == 1, "customize_idle_set は 1 つだけ")
check("state.MeritGear.value == 'On' and pet and pet.isvalid" in lua_m, "からくり士は、ペットがいる間だけ重ねる")
# ペットのいないジョブ (コルセアのウィニングストリーク) は、On の間いつでも重ねる (ペットを条件にしない)
win = [e for e in table["COR"] if e.get("set_path") == "sets.merit.WinningStreak"][0]
pc = Project("COR")
pc.add_ability_gear(win, EP.parse_equipped_set('sets.exported={ head="ＬＡトリコルヌ+3" }')["head"])
lua_c = pc.to_lua()
check("state.MeritGear.value == 'On' then" in lua_c and "pet.isvalid" not in lua_c, "ペットのいないジョブは、ペットを条件にしない")
# 種類が JobAbility 以外の技 (コルセアのロール・踊り子のフラリッシュなど) は、Mote が sets.precast.<種類> の中で探すので、そこに置く
if os.path.isfile(os.path.join(RES, "job_abilities.lua")):
    rdb2 = RDB.ResDB(RES)
    check(rdb2.ability_type("Blitzer's Roll") == "CorsairRoll" and rdb2.ability_type("Mana Cede") == "JobAbility", "res から技の種類を引ける")
    blz = [e for e in table["COR"] if e["ability_en"] == "Blitzer's Roll"][0]
    pr_c = Project("COR")
    pr_c.set_resdb(rdb2)
    p_blz = pr_c.add_ability_gear(blz, EP.parse_equipped_set('sets.exported={ head="ＣＳトリコルヌ+3" }')["head"])
    check(p_blz == "sets.precast.CorsairRoll['Blitzer\\'s Roll']", "ブリッツァロールは sets.precast.CorsairRoll の中 (実際 %s)" % p_blz)
    lua_b = pr_c.to_lua()
    check("sets.precast.CorsairRoll = sets.precast.CorsairRoll or {}" in lua_b, "種類のセットが無ければ、空のセットを先に用意する")
    check("sets.precast.CorsairRoll['ブリッツァロール'] = sets.precast.CorsairRoll['Blitzer\\'s Roll']" in lua_b, "日本語名の別名も同じ種類のセットの中")
    check("sets.precast.JA = sets.precast.JA or {}" not in lua_b, "Mote が作る入れ物は用意しない")
    # まとめのセット (ファントムロール全般) と一緒でも、両方が同じ種類のセットに入る
    roll = [e for e in table["COR"] if e.get("set_path") == "sets.precast.CorsairRoll"][0]
    pr_c.add_ability_gear(roll, EP.parse_equipped_set('sets.exported={ hands="ＣＳガントリー+3" }')["hands"])
    lua_b2 = pr_c.to_lua()
    combine = "sets.precast.CorsairRoll['Blitzer\\'s Roll'] = set_combine(sets.precast.CorsairRoll, {"
    check(combine in lua_b2 and lua_b2.index("sets.precast.CorsairRoll = {") < lua_b2.index(combine)
          and "sets.precast.CorsairRoll = sets.precast.CorsairRoll or {}" not in lua_b2,
          "まとめのセットが先に出て、個別の技はまとめのセットに重ねる (Mote は個別のセットだけを着るため・ゲーム内で発覚)")
    check("sets.precast.CorsairRoll['Blitzer\\'s Roll'] = {" in lua_b, "まとめのセットが無ければ、重ねずに普通に書く")
    # 古い作業 (修正前に保存したもの・sets.precast.JA['Tactician\'s Roll']) を開いても、Lua を作るときに正しい置き場所へ移す
    old = Project("COR")
    tac = [e for e in table["COR"] if e["ability_en"] == "Tactician's Roll"][0]
    old.add_ability_gear(tac, EP.parse_equipped_set('sets.exported={ body="ＣＳフラック+3" }')["body"])   # res 無し → JA に入る
    old.add_ability_gear(roll, EP.parse_equipped_set('sets.exported={ hands="ＣＳガントリー+3" }')["hands"])
    check("sets.precast.JA['Tactician\\'s Roll']" in old.assignments, "res 無しのときは JA に入る (古い作業の再現)")
    reopened = Project.from_json(old.to_json())
    reopened.set_job("COR")
    reopened.set_resdb(rdb2)
    lua_o = reopened.to_lua()
    check("sets.precast.CorsairRoll['Tactician\\'s Roll'] = set_combine(sets.precast.CorsairRoll, {" in lua_o
          and 'body="ＣＳフラック+3"' in lua_o, "古い作業でも、Lua を作るときに種類のセットの中へ移して重ねる")
    check("sets.precast.CorsairRoll['タクティックロール'] = sets.precast.CorsairRoll['Tactician\\'s Roll']" in lua_o
          and "sets.precast.JA['Tactician\\'s Roll']" not in lua_o, "日本語名の別名も移り、JA には残らない")
    if os.path.exists(LUAC):
        d4 = tempfile.mkdtemp()
        pth4 = os.path.join(d4, "COR.lua")
        with open(pth4, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(lua_b2)
        r = subprocess.run([LUAC, "-p", pth4], capture_output=True)
        check(r.returncode == 0, "コルセアの Lua が luac を通る " + r.stderr.decode("utf-8", "replace"))
rows_m = {r["path"]: r for r in pp.entries()}
check("sets.merit.Optimization" in rows_m and "メリット" in rows_m["sets.merit.Optimization"]["help"], "一覧に出て、説明がある")
if os.path.exists(LUA51):
    d2 = tempfile.mkdtemp()
    pth = os.path.join(d2, "PUP.lua")
    with open(pth, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(lua_m)
    r = subprocess.run([LUAC, "-p", pth], capture_output=True)
    check(r.returncode == 0, "メリット特性入りの Lua が luac を通る " + r.stderr.decode("utf-8", "replace"))
    r = subprocess.run([LUA51, os.path.join(HERE, "merit_lua_test.lua"), pth], capture_output=True)
    sys.stdout.buffer.write(r.stdout + r.stderr)
    check(r.returncode == 0, "模擬 GearSwap で、MeritGear の On/Off とペットの有無で重ね方が変わる")

# --- luac で構文確認と、模擬 GearSwap での動作確認 ---
if os.path.exists(LUAC):
    d = tempfile.mkdtemp()
    path = os.path.join(d, "SMN.lua")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(lua)
    r = subprocess.run([LUAC, "-p", path], capture_output=True)
    check(r.returncode == 0, "luac -p を通る " + r.stderr.decode("utf-8", "replace"))
    if os.path.exists(LUA51):
        r = subprocess.run([LUA51, os.path.join(HERE, "buff_lua_test.lua"), path], capture_output=True)
        sys.stdout.buffer.write(r.stdout + r.stderr)
        check(r.returncode == 0, "模擬 GearSwap で、効果中の装備が重なる")
else:
    out("(luac が無いので、構文確認は省略)")

if fails:
    out("FAILED %d 件" % len(fails))
    sys.exit(1)
out("OK アビリティ強化の装備: 失敗 0 件")
