# -*- coding: utf-8 -*-
"""Project (作業内容)・conflicts (付属ファイルの警告) の確認。実行 (GearSwapKit/ で): python -I tests/test_project.py"""
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import _env as ENV
import conflicts
import export_parser as EP
import resdb as RDB
from project import Project

REAL_DATA = ENV.GS_DATA

fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)
        sys.stdout.buffer.write(("NG: %s\n" % msg).encode("utf-8"))


SET = EP.parse_equipped_set('''sets.exported={
    head="ＢＣホーン+1",
    neck={ name="召喚士の首輪+2", augments={'Path: A',}},
    main="ニルヴァーナ",
}''')

pr = Project("SMN")
paths = [e["path"] for e in pr.entries()]
check("sets.idle" in paths and "sets.precast.BloodPactWard" in paths, "SMN の一覧に共通と専用のセットがある")
check(not pr.is_assigned("sets.idle"), "最初は未設定")
pr.assign("sets.idle", SET)
check(pr.is_assigned("sets.idle"), "割り当てると設定済みになる")
pr.clear("sets.idle")
check(not pr.is_assigned("sets.idle"), "外すと未設定に戻る")

# res が無いときは、日本語名を受け付けない (英語名は、そのまま使える)
check(pr.add_custom(3, "ボルトストライク") == ("notfound", None), "res が無いと、日本語名は断る")
st, pe = pr.add_custom(3, "Volt Strike")
check(st == "ok" and pe == "sets.midcast.Pet['Volt Strike']", "英語名は、そのまま使う (実際 %r %r)" % (st, pe))
pr.remove_custom(pe)
real_res = RDB.guess_res_dir(REAL_DATA)
HAS_RES = bool(real_res)
if HAS_RES:   # res が無い PC では、日本語名の確認を飛ばし、英語名で続ける
    check(real_res is not None, "data フォルダーから res を探せる")
    pr.set_resdb(RDB.ResDB(real_res))
    st, p1 = pr.add_custom(3, "ボルトストライク")
    check(st == "ok" and p1 == "sets.midcast.Pet['Volt Strike']", "日本語名から英語名のセットを作る (実際 %r %r)" % (st, p1))
    check(any(c[0] == p1 and c[2] == "sets.midcast.Pet['ボルトストライク']" for c in pr.custom), "日本語名の別名も持つ")
    check(pr.add_custom(3, "ボルトストライク") == ("dup", None), "同じ追加は断る (日本語名)")
    check(pr.add_custom(3, "volt strike") == ("dup", None), "英語名の大文字小文字が違っても、同じ追加")
    check(pr.add_custom(0, "   ") == ("empty", None), "空の名前は断る")
    check(pr.add_custom(3, "存在しない技名") == ("notfound", None), "res に無い日本語名は断る")
    st, pw = pr.add_custom(0, "レデンサリュート")
    check(st == "ok" and pw.startswith("sets.precast.WS['") and pw.isascii(), "ウェポンスキルの日本語名から英語名を引ける (実際 %r)" % pw)
    pr.remove_custom(pw)
else:
    st, p1 = pr.add_custom(3, "Volt Strike")
check(any(e["path"] == p1 and e["custom"] for e in pr.entries()), "追加した技が一覧に出る")
pr.assign("sets.idle", SET)
pr.assign(p1, SET)
lua = pr.to_lua()
check("sets.midcast.Pet['Volt Strike'] = {" in lua, "追加した技のセットを英語名で出力する")
check(not HAS_RES or "sets.midcast.Pet['ボルトストライク'] = sets.midcast.Pet['Volt Strike']" in lua, "日本語名の別名を出力する")
check("main=" not in lua.split("function init_gear_sets")[1], "武器は既定で出力しない")
pr.include_weapons = True
check('main="ニルヴァーナ"' in pr.to_lua(), "武器を含める指定で出力する")
pr.include_weapons = False

# 割り当ては、ジョブごとに別々 (SMN の内容が、ほかのジョブに出ない・戻すと元に戻る)
check(pr.is_assigned("sets.idle") and pr.has_work("SMN"), "SMN に割り当てがある")
pr.set_job("COR")
check(not pr.is_assigned("sets.idle"), "COR に変えると、待機は未設定")
check(not pr.has_work("COR") and pr.has_work("SMN"), "COR には作業が無く、SMN にはある")
check(not pr.is_assigned("weapons:main") and not pr.weapons and not pr.custom, "COR に、SMN の武器・技ごとの追加は出ない")
check("sets.idle" not in pr.to_lua().split("function init_gear_sets")[1], "COR の出力に、SMN の待機は入らない")
pr.add_weapon("main", EP.parse_equipped_set('sets.exported={ main="ガンドリング" }')["main"])
check(pr.is_assigned("weapons:main"), "COR に武器を足すと、COR だけ設定済みになる")
pr.set_job("SMN")
check(pr.is_assigned("sets.idle") and "ガンドリング" not in "".join(it.name for it in pr.weapons.get("main", [])), "SMN に戻すと、SMN の内容のまま (COR の武器は入らない)")
check(all(it.name != "ガンドリング" for it in pr.weapons.get("main", [])), "SMN の武器に COR の武器が混ざらない")
pr.set_job("COR")
pr.weapons.pop("main", None)
pr.set_job("SMN")

# 保存と読み込み
pr2 = Project.from_json(pr.to_json())
check(pr2.job == "SMN" and pr2.is_assigned(p1), "保存した作業を読み戻せる")
check(pr2.assignments["sets.idle"]["neck"].raw == SET["neck"].raw, "オーグメントの表記が保たれる")
check(pr2.to_lua() == pr.to_lua(), "読み戻しても同じ Lua になる")

# 出力 (バックアップ)
tmp = tempfile.mkdtemp()
try:
    path, backup = pr.write_lua(tmp)
    check(os.path.exists(path) and backup is None, "初めての出力はバックアップなし")
    path, backup = pr.write_lua(tmp)
    check(backup and os.path.exists(backup), "2 回目はバックアップを残す")
    check(open(path, encoding="utf-8").read() == pr.to_lua(), "出力の中身が一致する")

    # 付属ファイルの警告
    data = os.path.join(tmp, "data")
    os.makedirs(os.path.join(data, "MyChar"))
    os.makedirs(os.path.join(data, "common"))
    os.makedirs(os.path.join(data, "export"))
    for rel in ("user-globals.lua", "MyChar/SMN_gear.lua", "common/smn_gear.lua", "MyChar/BLU_gear.lua", "export/SMN_gear.lua", "MyChar_x.lua"):
        with open(os.path.join(data, rel), "w") as f:
            f.write("--")
    found = conflicts.find_conflicts(data, "SMN")
    names = sorted(os.path.relpath(p, data).replace("\\", "/").lower() for p, _ in found)
    check(names == ["common/smn_gear.lua", "mychar/smn_gear.lua", "user-globals.lua"], "SMN の付属ファイルと共通ファイルを見つける (実際 %r)" % names)
    check(conflicts.find_conflicts(data, "WAR") == [("%s" % os.path.join(data, "user-globals.lua"), found[[p for p, _ in found].index(os.path.join(data, "user-globals.lua"))][1])]
          or len(conflicts.find_conflicts(data, "WAR")) == 1, "別のジョブでは共通ファイルだけ")
    check(conflicts.find_conflicts(os.path.join(tmp, "nothing"), "SMN") == [], "フォルダーが無ければ空")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# 全ジョブ・全セットに装備を入れて出力した Lua が、構文として正しいこと (luac が使えるときだけ)
import subprocess
import set_catalog as CAT
WEAPON_MAIN_A_EARLY = EP.parse_equipped_set('sets.exported={ main="ニルヴァーナ" }')["main"]
WEAPON_SUB_EARLY = EP.parse_equipped_set('sets.exported={ sub="ドゥバン" }')["sub"]
LUAC = ENV.LUAC
if os.path.exists(LUAC):
    for job in CAT.ALL_JOBS:
        pj = Project(job)
        for e in pj.entries():
            if e.get("weapon_slot"):
                continue
            pj.assign(e["path"], SET)
        pj.add_weapon("main", WEAPON_MAIN_A_EARLY)
        pj.add_weapon("sub", WEAPON_SUB_EARLY)
        tmpd = tempfile.mkdtemp()
        try:
            out_path, _b = pj.write_lua(tmpd)
            r = subprocess.run([LUAC, "-p", out_path], capture_output=True)
            check(r.returncode == 0, "%s の出力が Lua の構文として正しい (%s)" % (job, r.stderr.decode("utf-8", "replace")[:80]))
        finally:
            shutil.rmtree(tmpd, ignore_errors=True)
    pb = Project("BST")
    pb.assign("sets.precast.JA['Sic']", SET)
    check("sets.precast.JA['ほんきだせ'] = sets.precast.JA['Sic']" in pb.to_lua(), "BST の ほんきだせ に日本語の別名がつく")
    pn = Project("NIN")
    pn.assign("sets.precast.FC.Utsusemi", SET)
    check("sets.precast.FC.Utsusemi = {" in pn.to_lua(), "NIN の空蝉の詠唱の開始のセットが出る")

# 技ごとの追加の一覧 (res から・選択式)
import choices as CH
if real_res:
    rdc = RDB.ResDB(real_res)
    whm = CH.choices(rdc, "magic", "WHM")
    smn = CH.choices(rdc, "magic", "SMN")
    check(any(x["ja"] == "ケアルIV" for x in whm) and not any(x["ja"] == "ケアルIV" for x in smn), "魔法は、そのジョブが覚えるものだけ (ケアルIV は白魔道士だけ)")
    check("召喚魔法" in CH.groups_of(smn), "召喚士の魔法に、召喚魔法のグループがある")
    check(any(x["en"] == "Volt Strike" for x in CH.choices(rdc, "pet", "SMN")), "召喚士のペットの技に、ボルトストライクがある")
    check(not any(x["en"] == "Foot Kick" for x in CH.choices(rdc, "pet", "SMN")), "召喚士のペットの技に、フットキックは無い")
    check(any(x["en"] == "Foot Kick" for x in CH.choices(rdc, "pet", "BST")), "獣使いのペットの技に、フットキックがある")
    check(any(x["ja"] == "レデンサリュート" for x in CH.choices(rdc, "ws", "COR")), "ウェポンスキルに、レデンサリュートがある")
    check(any(x["ja"] == "マナシード" for x in CH.choices(rdc, "ja", "SMN")), "アビリティに、マナシードがある")
    check(CH.choices(None, "ws", "COR") == [], "res が無いときは、空の一覧")
    pc = Project("SMN")
    check(pc.add_pair(3, "Volt Strike", "ボルトストライク") == "ok" and pc.add_pair(3, "Volt Strike", "ボルトストライク") == "dup", "一覧から選んだ技を足せる (重複は断る)")
    check(any(c[2] == "sets.midcast.Pet['ボルトストライク']" for c in pc.custom), "一覧から足した技にも、日本語の別名がつく")

# 装備できるジョブ (res の items・jobs)
if real_res:
    rd = RDB.ResDB(real_res)
    check(rd.usable_by("ニルヴァーナ", "SMN") is True, "ニルヴァーナは召喚士が使える")
    check(rd.usable_by("ニルヴァーナ", "WAR") is False, "ニルヴァーナは戦士が使えない")
    check(rd.usable_by("ニャメヘルム", "WAR") is True and rd.usable_by("ニャメヘルム", "SMN") is True, "ニャメヘルムは全ジョブが使える")
    check(rd.usable_by("Nirvana", "SMN") is True, "英語名でも引ける")
    check(rd.usable_by("存在しない名前", "SMN") is None, "res に無い名前は、判断できない (None)")
    check(rd.usable_by("ニルヴァーナ", "XXX") is None, "ジョブの略称が違うときも、判断できない (None)")

# 全ジョブぶんの保存と読み込み・古い形式 (1 ジョブ) の読み込み
pm = Project("SMN")
pm.assign("sets.idle", SET)
pm.set_job("COR")
pm.assign("sets.engaged", SET)
pm.set_job("SMN")
pm2m = Project.from_json(pm.to_json())
check(pm2m.is_assigned("sets.idle") and not pm2m.is_assigned("sets.engaged"), "保存から読み戻すと、SMN の内容 (COR のものは出ない)")
pm2m.set_job("COR")
check(pm2m.is_assigned("sets.engaged") and not pm2m.is_assigned("sets.idle"), "COR の内容も、別に読み戻る")
old_json = '{"job": "BLU", "include_weapons": false, "custom": [], "assignments": {"sets.idle": {"head": "\\"X\\""}}, "weapons": {}}'
po = Project.from_json(old_json)
check(po.job == "BLU" and po.is_assigned("sets.idle"), "古い形式の保存も、そのジョブの内容として読める")

# 武器の切り替え
WEAPON_MAIN_A = EP.parse_equipped_set('sets.exported={ main="ニルヴァーナ", head="X" }')["main"]
WEAPON_MAIN_B = EP.parse_equipped_set('sets.exported={ main="ガンドリング" }')["main"]
WEAPON_SUB = EP.parse_equipped_set('sets.exported={ sub={ name="ドゥバン", augments={\'HP+5\',} } }')["sub"]
pw = Project("SMN")
check(not pw.is_assigned("weapons:main"), "武器は、最初は未設定")
check(pw.add_weapon("main", WEAPON_MAIN_A) and pw.add_weapon("main", WEAPON_MAIN_B), "メインの武器を 2 本足せる")
check(pw.add_weapon("main", WEAPON_MAIN_A) is False, "同じ武器は足さない")
check(pw.add_weapon("sub", WEAPON_SUB), "サブの武器を足せる")
check(pw.is_assigned("weapons:main") and pw.is_assigned("weapons:sub") and not pw.is_assigned("weapons:range"), "足した分だけ、設定済みになる")
pw.assign("sets.idle", SET)
lua_w = pw.to_lua()
check("state.MainWeapons = M{['description']='MainWeapons', \"ニルヴァーナ\", \"ガンドリング\"}" in lua_w, "MainWeapons の選択肢が出る")
check("state.RangeWeapons" not in lua_w, "足していない遠隔は出さない")
check("function job_state_change" in lua_w and "function job_self_command" in lua_w, "切り替えの関数が出る")
pw2 = Project.from_json(pw.to_json())
check(pw2.to_lua() == lua_w, "保存と読み込みで、武器も同じになる")
tmpw = tempfile.mkdtemp()
try:
    outp, _b = pw.write_lua(tmpw)
    LUA51 = ENV.LUA51
    if os.path.exists(LUA51):
        r = subprocess.run([LUA51, os.path.join(os.path.dirname(HERE), "tests", "weapons_lua_test.lua"), outp], capture_output=True)
        out_txt = r.stdout.decode("utf-8", "replace")
        check(r.returncode == 0 and "OK" in out_txt, "武器の切り替えの Lua が、模擬の GearSwap で動く (%s)" % out_txt[:200])
    pw.clear("weapons:main")
    check(not pw.is_assigned("weapons:main"), "武器を外せる")
finally:
    shutil.rmtree(tmpw, ignore_errors=True)

# 武器の切り替えと「武器も含める」の両方: 切り替えのあるスロットはセットに入れない (Mote の cycle の後の着替えで上書きされるため)
pb = Project("SMN")
pb.include_weapons = True
pb.assign("sets.idle", EP.parse_equipped_set('sets.exported={ main="ガンドリング", sub="エンキアストラップ", head="ＢＣホーン+1" }'))
pb.add_weapon("main", WEAPON_MAIN_A)
lua_b = pb.to_lua()
idle_part = lua_b.split("sets.idle = {")[1].split("}")[0]
check("main=" not in idle_part and "sub=" in idle_part and "head=" in idle_part,
      "武器の切り替えのあるメインは待機のセットに入れず、切り替えの無いサブは入れる")

# ロックスタイル番号 (lockstyleset): ジョブごと・1〜200・保存して読み込める・武器のコマンドと 1 つの job_self_command にまとめる
pl = Project("COR")
check(pl.set_lockstyle("94") == 94 and pl.lockstyle == 94, "ロックスタイル番号を入れられる")
check(pl.has_work("COR"), "ロックスタイル番号だけでも、作業ありになる")
pl.set_job("NIN")
check(pl.lockstyle is None, "ほかのジョブには入らない")
check(pl.set_lockstyle("abc") is None and pl.set_lockstyle("0") is None and pl.set_lockstyle("201") is None, "数字でない・範囲外は使わない")
pl.set_job("COR")
pl.add_weapon("main", WEAPON_MAIN_A)
lua_l = pl.to_lua()
check("    lockstyleset = 94" in lua_l and "send_command('wait 5; gs c lockstyleset')" in lua_l, "lockstyleset と、読み込み後にかける命令が出る")
check(lua_l.count("function job_self_command") == 1 and "cmdParams[1] == 'weapons'" in lua_l
      and "cmdParams[1] == 'lockstyleset'" in lua_l, "武器とロックスタイルのコマンドを 1 つの関数にまとめる")
check(Project.from_json(pl.to_json()).to_lua() == lua_l, "保存と読み込みで、ロックスタイル番号も同じになる")
check("lockstyleset" not in Project("SMN").to_lua(), "番号を入れていなければ出さない")
tmpl = tempfile.mkdtemp()
try:
    outl, _b = pl.write_lua(tmpl)
    LUAC0 = ENV.LUAC
    if os.path.exists(LUAC0):
        r = subprocess.run([LUAC0, "-p", outl], capture_output=True)
        check(r.returncode == 0, "ロックスタイル入りの Lua が luac を通る " + r.stderr.decode("utf-8", "replace"))
    LUA51 = ENV.LUA51
    if os.path.exists(LUA51):
        r = subprocess.run([LUA51, os.path.join(HERE, "lockstyle_lua_test.lua"), outl], capture_output=True)
        sys.stdout.buffer.write(r.stdout + r.stderr)
        check(r.returncode == 0, "模擬 GearSwap で、//gs c lockstyleset が /lockstyleset 94 を送る")
finally:
    shutil.rmtree(tmpl, ignore_errors=True)

# 一覧から外した項目 (古い作業の割り当て) は出力しない。作業のファイルには残す
po = Project("SMN")
po.assignments["sets.midcast.Pet.BloodPactWard"] = EP.parse_equipped_set('sets.exported={ head="古い頭" }')
po.assign("sets.idle.Avatar", EP.parse_equipped_set('sets.exported={ head="ＢＣホーン+1" }'))
lo = po.to_lua()
check("古い頭" not in lo and "sets.idle.Pet = sets.idle.Avatar" in lo, "一覧に無い古いセットは出力しない")
check(po.orphans == ["sets.midcast.Pet.BloodPactWard"], "出力しなかった古いセットを覚えておく")
check("sets.midcast.Pet.BloodPactWard" in po.to_json(), "作業のファイルには残す")

sys.stdout.buffer.write((("OK GearSwapKit project: 失敗 0 件" if not fails else "FAILED %d" % len(fails)) + "\n").encode("utf-8"))
sys.exit(1 if fails else 0)
