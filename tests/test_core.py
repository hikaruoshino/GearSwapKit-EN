# -*- coding: utf-8 -*-
"""GearSwapKit の確認。実行 (GearSwapKit/ で): python -I tests/test_core.py"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import _env as ENV
import export_parser as EP
import generator as G
import set_catalog as C

fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)
        sys.stdout.buffer.write(("NG: %s\n" % msg).encode("utf-8"))


EQUIPPED = '''sets.exported={
    main="ブルトガング",
    sub={ name="ドゥバン", augments={'HP+5','"Dbl.Atk."+2',}},
    ammo="サピエンスオーブ",
    head={ name="ＢＣホーン+1", bag="wardrobe"},
    neck="シビルスカーフ",
    left_ear="アスプロピアス",
    right_ear="オノワイヤリング+1",
    body="唱門師浄衣改",
    hands="ニャメガントレ",
    left_ring="シュネデックリング",
    right_ring="メランリング",
    back={ name="カンペストレケープ", augments={'Pet: "Regen"+10','DEX+3',}},
    waist="プラチナモグベルト",
    legs="アシドゥイズボン+1",
    feet="バヤミサボ+1",
}
'''
INVENTORY = '''sets.exported = {
    sub="デジョンカジェル",
    sub="デジョンカジェル",
    item="味噌ラーメン",
    head={ name="ＰＤボード+4", augments={'Enh. "Altruism" and "Focalization"',}},
    head="ＡＣボード+2",
}'''

eq = EP.parse_equipped_set(EQUIPPED)
check(len(eq) == 15, "装備中のセット (遠隔なし) は 15 スロット (実際 %d)" % len(eq))
check(eq['sub'].name == "ドゥバン" and "augments" in eq['sub'].raw, "オーグメント付きの名前を読む")
check(eq['back'].raw.count("'") >= 4, "オーグメントの引用符を保つ")
check(eq['head'].name == "ＢＣホーン+1", "bag 付きの表でも名前を読む")
check(not EP.looks_like_inventory(EQUIPPED), "装備中のセットは所持品の一覧と見なさない")
check(EP.looks_like_inventory(INVENTORY), "所持品の一覧を見分ける")
inv = EP.parse_inventory(INVENTORY)
check(len(inv['sub']) == 1, "同じ装備の重複は 1 つにまとめる")
check(len(inv['head']) == 2, "別の装備は残す")
check('item' not in inv, "item= (アイテム) は除く")

lua = G.build_lua("SMN", {"sets.idle": eq, "sets.idle.DT": eq, "sets.midcast.Pet": {}}, include_weapons=False)
check("        main=" not in lua and '        ammo="サピエンスオーブ",' in lua, "武器は既定で入れない (矢弾は、遠隔のジョブ以外は普通の装備として入れる)")
check("head={ name=\"ＢＣホーン+1\"" in lua or 'head={ name="ＢＣホーン+1"' in lua, "表のまま出力する")
check("sets.midcast.Pet" not in lua, "空のセットは出さない")
check(lua.index("sets.idle = {") < lua.index("sets.idle.DT = {"), "親のセットが先")
check("state.IdleMode:options('Normal', 'DT')" in lua, "DT のセットがあれば IdleMode を足す")
check("set_language('japanese')" in lua, "日本語の指定が入る")
lua2 = G.build_lua("SMN", {"sets.idle": eq}, include_weapons=True)
check('main="ブルトガング"' in lua2, "武器を含める指定で main を出す")
check(G.make_key("sets.precast.WS", "it's") == "sets.precast.WS['it\\'s']", "名前の ' を逃がす")

sm = C.sets_for_job("SMN")
check(any(s["path"] == "sets.precast.BloodPactWard" for s in sm), "SMN の一覧に履行の短縮がある")
check(all(s.get("help") for s in sm), "全てのセットにヘルプ文がある")
check(len({s["path"] for s in C.sets_for_job("BST")}) == len(C.sets_for_job("BST")), "セットの重複がない")

# 本物の export (所持品の一覧) を読めるか
real = ENV.EXPORT_ALL
if os.path.exists(real):
    text = EP.read_file(real)
    inv = EP.parse_inventory(text)
    total = sum(len(v) for v in inv.values())
    check(EP.looks_like_inventory(text), "本物の所持品の一覧を見分ける")
    check(total > 300, "本物の所持品の一覧から 300 以上の装備を読む (実際 %d)" % total)
    mains = EP.weapon_candidates(inv, "main")
    subs = EP.weapon_candidates(inv, "sub")
    ranges = EP.weapon_candidates(inv, "range")
    check(len(mains) > 5 and all(c.slot == "main" for c in mains), "メインの武器の候補を取れる (実際 %d)" % len(mains))
    check(len(subs) >= len(inv.get("sub", [])), "サブの候補には、サブの行も含まれる (実際 %d)" % len(subs))
    check(len(set(c.raw for c in mains)) == len(mains), "候補に重複がない")
    check(EP.weapon_candidates(inv, "head") == [], "武器以外のスロットは、候補なし")

# //gs export all は片手武器を sub= で書き出すので、メインの候補にも入れる (res があれば、盾・グリップは除く)
real_all = ENV.EXPORT_ALL
RES = ENV.RES
if os.path.exists(real_all) and os.path.isdir(RES):
    import resdb as RDB
    rdb = RDB.ResDB(RES)
    inv_all = EP.parse_inventory(EP.read_file(real_all))
    mains = [c.name for c in EP.weapon_candidates(inv_all, "main", rdb)]
    check("ブルトガング" in mains and "マリグナスソード" in mains, "sub= で書き出された片手武器も、メインの候補に出る")
    check("イージス" not in mains and "ドゥバン" not in mains, "盾は、メインの候補に出さない")
    check(rdb.item_slots("イージス") == 2, "res の部位 (イージス = サブ)")

# モードの切り替え: セットのあるモードだけを選択肢にする (戦闘中のカット = HybridMode DT は全ジョブ)
check(any(s["path"] == "sets.engaged.DT" for s in C.sets_for_job("WAR")), "戦闘中 (被ダメージ軽減) は全ジョブにある")
from project import Project as _P
pp = _P("PUP")
for p in ("sets.idle", "sets.idle.Tate", "sets.engaged", "sets.engaged.Tate", "sets.engaged.PetSTP", "sets.engaged.DT"):
    pp.assign(p, EP.parse_equipped_set('sets.exported={ head="頭" }'))
lp = pp.to_lua()
check("state.IdleMode:options('Normal', 'Tate')" in lp, "マトン盾の待機があれば、IdleMode に Tate")
check("state.OffenseMode:options('Normal', 'Tate', 'PetSTP')" in lp, "マトン盾・マトンSTP の戦闘中があれば、OffenseMode に両方")
check(any(s["path"] == "sets.engaged.PetSTP" for s in C.sets_for_job("PUP")), "からくり士に、戦闘中 (マトンSTP) がある")
check("state.HybridMode:options('Normal', 'DT')" in lp, "戦闘中のカットがあれば、HybridMode に DT")
pw_ = _P("WAR")
pw_.assign("sets.engaged", EP.parse_equipped_set('sets.exported={ head="頭" }'))
check("HybridMode" not in pw_.to_lua(), "カットのセットが無ければ、HybridMode は出さない")

# コメントアウトした装備は読まない (手で直した export)。文字列の中の -- は残す
COMMENTED = '''sets.exported={
    head="ＢＣホーン+1",
--    head="ＧＬホーン+1",
    body="ＣＮダブレット+3",   -- 胴はこれ
    --[[
    legs="エンタイサーパンツ",
    ]]
    neck={ name="召喚士の首輪+2", augments={'Path: A','x--y',}},
}'''
ce = EP.parse_equipped_set(COMMENTED)
check(ce["head"].name == "ＢＣホーン+1" and "legs" not in ce and ce["body"].name == "ＣＮダブレット+3",
      "コメントアウトした行・複数行のコメントの装備は読まない")
check("x--y" in ce["neck"].raw, "文字列の中の -- は消さない")
check(not EP.looks_like_inventory(COMMENTED), "コメントアウトした頭があっても、所持品の一覧と間違えない")

sys.stdout.buffer.write((("OK GearSwapKit: 失敗 0 件" if not fails else "FAILED %d" % len(fails)) + "\n").encode("utf-8"))
sys.exit(1 if fails else 0)
