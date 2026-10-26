# -*- coding: utf-8 -*-
"""ナイトの仕組み (敵対心・詠唱中断・3 段階の着替え・対魔法 / 状態異常耐性の手動切り替え) の確認。
実行 (GearSwapKit/ で): python -I tests/test_pld.py"""
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


# 一覧: ナイトだけ
for job in C.ALL_JOBS:
    paths = [e["path"] for e in C.sets_for_job(job)]
    check(("sets.midcast.interruption" in paths) == (job == "PLD"), "%s: 詠唱中断はナイトだけ" % job)
pld_paths = [e["path"] for e in C.sets_for_job("PLD")]
for p in ("sets.Enmity", "sets.EnmityMax", "sets.midcast.Cure", "sets.midcast.Flash", "sets.idle.Magical", "sets.StatusResist"):
    check(p in pld_paths, "ナイトの一覧に %s がある" % p)

H = EP.parse_equipped_set


def make(three):
    pr = Project("PLD")
    pr.assign("sets.Enmity", H('sets.exported={ head="ＳＶシャレル+1", body="敵対心の胴" }'))
    pr.assign("sets.EnmityMax", H('sets.exported={ body="最大の胴" }'))
    pr.assign("sets.midcast.interruption", H('sets.exported={ head="ＣＶアーメット+3", legs="ＣＶクウィス+3" }'))
    pr.assign("sets.midcast.Cure", H('sets.exported={ head="ＳＶシャレル+1", legs="ケアルの脚" }'))
    pr.assign("sets.midcast.Flash", H('sets.exported={ neck="ムーンライトネックレス" }'))
    pr.assign("sets.idle.Magical", H('sets.exported={ head="対魔法の頭" }'))
    pr.assign("sets.StatusResist", H('sets.exported={ head="耐性の頭" }'))
    for en, ja in (("Sentinel", "センチネル"), ("Shield Bash", "シールドバッシュ")):
        pr.add_pair(1, en, ja)
    pr.assign("sets.precast.JA['Sentinel']", H('sets.exported={ feet="ＣＢレギンス+3" }'))
    pr.assign("sets.precast.JA['Shield Bash']", H('sets.exported={ hands="ＣＢガントレ+3" }'))
    pr.set_three_stage(three)
    pr.set_fast_cast("40")
    return pr


p0 = make(False)
lua0 = p0.to_lua()
check("sets.precast.JA['Sentinel'] = set_combine(sets.EnmityMax, {" in lua0, "センチネルは敵対心 (最大) に重ねる")
check("sets.precast.JA['Shield Bash'] = set_combine(sets.Enmity, {" in lua0, "シールドバッシュは敵対心に重ねる")
check("sets.midcast.Flash = set_combine(sets.Enmity, {" in lua0, "フラッシュは敵対心に重ねる")
check("gs c land" not in lua0, "3 段階を使わなければ、着弾の命令は出さない (初めはチェックなし)")
check(Project("PLD").three_stage is False, "3 段階の着替えは、初めはチェックなし")
p1 = make(True)
lua1 = p1.to_lua()
check("gs c land" in lua1 and "local fast_cast = 40" in lua1, "3 段階を選ぶと、着弾の命令とファストキャストが出る")

# 遠隔のジョブ (狩人・コルセア) 以外は、矢弾をセットに入れる (ストンチタスラム+1 など)
pa = make(False)
pa.assign("sets.midcast.interruption", H('sets.exported={ ammo="ストンチタスラム+1", head="ＣＶアーメット+3" }'))
check('        ammo="ストンチタスラム+1",' in pa.to_lua(), "ナイトでは、矢弾をセットに入れる")
pm = Project("MNK")
pm.assign("sets.idle", H('sets.exported={ ammo="ストンチタスラム+1", head="ＣＶアーメット+3" }'))
check('ammo="ストンチタスラム+1"' in pm.to_lua(), "遠隔のジョブ以外 (モンクなど) も、矢弾をセットに入れる")
for rj in ("RNG", "COR"):
    pr_ = Project(rj)
    pr_.assign("sets.idle", H('sets.exported={ ammo="クロノブレット", head="ＣＶアーメット+3" }'))
    check('ammo="クロノブレット"' not in pr_.to_lua(), "%s (遠隔のジョブ) は、矢弾をセットに入れない" % rj)

# 対魔法・状態異常耐性は、メインとサブも入れる (武器の切り替えがあっても)。ほかのセットには入れない
pw2 = make(False)
pw2.add_weapon("main", EP.Item("main", "ブルトガング", '"ブルトガング"'))
pw2.assign("sets.idle.Magical", H('sets.exported={ main="マリグナスソード", sub="イージス", head="対魔法の頭" }'))
pw2.assign("sets.idle", H('sets.exported={ main="ブルトガング", sub="ドゥバン", head="待機の頭" }'))
lw = pw2.to_lua()
check('main="マリグナスソード",' in lw and 'sub="イージス",' in lw, "対魔法のセットには、メインとサブを入れる")
check('sub="ドゥバン",' not in lw, "待機のセットには、武器を入れない (今までどおり)")
check("gs c weapons')" in lw and "stateField == 'Magical'" in lw, "対魔法をオフにしたら、選んでいる武器に戻す")

# ファストキャストの計算 (res の説明 + オーグメント)。作者のナイトの FC セットで 69%
import fastcast as FCALC
RES = ENV.RES
if os.path.isdir(RES):
    fc_set = H('''sets.exported={
        ammo="サピエンスオーブ",
        head={ name="カマインマスク+1", augments={'Accuracy+20','Mag. Acc.+12','"Fast Cast"+4',}},
        neck="オルンミラトルク",
        left_ear="アスプロピアス",
        body="ＲＶサーコート+4",
        hands={ name="レイライングローブ", augments={'Accuracy+12','Mag. Acc.+14','"Mag.Atk.Bns."+15','"Fast Cast"+2',}},
        left_ring="月明の指輪",
        right_ring="キシャールリング",
        back={ name="ルディアノスマント", augments={'HP+60','Eva.+20 /Mag. Eva.+20','HP+20','"Fast Cast"+10','Phys. dmg. taken-10%',}},
        waist="プラチナモグベルト",
        legs="トラストブレー",
        feet={ name="オディシアグリーヴ", augments={'Attack+30','"Fast Cast"+6','Accuracy+10',}},
    }''')
    total, rows, unknown = FCALC.set_fast_cast(RES, fc_set)
    check(total == 69 and not unknown, "ナイトの FC セットは 69%% (実際 %d・不明 %s)" % (total, unknown))
check(FCALC.set_fast_cast(None, H('sets.exported={ feet={ name="オディシアグリーヴ", augments={\'"Fast Cast"+6\',}} }'))[0] == 6,
      "res が無くても、オーグメントの値は数える")

# 上限を超えたときの知らせ
check(FCALC.advice(69, "PLD").startswith("サポ赤にすると") and "84%" in FCALC.advice(69, "PLD"), "69% はサポ赤で上限を超えると知らせる")
check(FCALC.advice(50, "PLD") == "", "50% (サポ赤でも 65%) は知らせない")
check("10%" in FCALC.advice(90, "WHM") and FCALC.advice(90, "WHM").startswith("装備だけで"), "装備だけで 90% は、10% 超え")
check("超えています" in FCALC.advice(50, "RDM") and "8%" in FCALC.advice(50, "RDM"), "赤魔道士は特性 38% を足して 88% → 8% 超え")
check(FCALC.advice(0, "BLM") == "", "0% は知らせない")
import i18n
i18n.set_lang("en")
import re as _re
for _t, _j in ((69, "PLD"), (90, "WHM"), (50, "RDM")):
    _m = FCALC.advice(_t, _j)
    check(_m and not _re.search("[ぁ-んァ-ン一-龥]", _m), "英語のとき、知らせに日本語が残らない (%s %d%%): %s" % (_j, _t, _m))
i18n.set_lang("ja")

# 保存と読み直し
p2 = Project.from_json(p1.to_json())
p2.set_job("PLD")
check(p2.three_stage and p2.fast_cast == 40, "3 段階とファストキャストを保存して読み直せる")
check(Project("PLD").set_fast_cast("abc") == 0 and Project("PLD").set_fast_cast(120) == 100, "ファストキャストの値の丸め")

# ナイト以外では出さない
pw = Project("WAR")
pw.assign("sets.precast.WS", H('sets.exported={ head="ＮＹヘルム+1" }'))
check("interruption" not in pw.to_lua() and "Magical" not in pw.to_lua(), "ナイト以外には、ナイトの仕組みを出さない")

if os.path.exists(LUAC):
    for three, lua in ((False, lua0), (True, lua1)):
        d = tempfile.mkdtemp()
        path = os.path.join(d, "PLD.lua")
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(lua)
        r = subprocess.run([LUAC, "-p", path], capture_output=True)
        check(r.returncode == 0, "luac を通る " + r.stderr.decode("utf-8", "replace"))
        if os.path.exists(LUA51):
            r = subprocess.run([LUA51, os.path.join(HERE, "pld_lua_test.lua"), path, "1" if three else "0"], capture_output=True)
            sys.stdout.buffer.write(r.stdout + r.stderr)
            check(r.returncode == 0, "模擬 GearSwap で、ナイトの仕組みが正しい (3 段階 = %s)" % three)

if fails:
    sys.stdout.buffer.write(("FAILED %d 件\n" % len(fails)).encode("utf-8"))
    sys.exit(1)
sys.stdout.buffer.write("OK ナイトの仕組み: 失敗 0 件\n".encode("utf-8"))
