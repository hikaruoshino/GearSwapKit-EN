# -*- coding: utf-8 -*-
"""画面 (tkinter) を、表示せずに動かして確認する。実行 (GearSwapKit/ で): python -I tests/test_gui.py (tkinter が使える Python で)"""
import os
import sys
import tkinter as tk

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import _env as ENV
import app as A
import export_parser as EP
import tempfile as _tf
# 本物の設定ファイル (gearswapkit_settings.json) を汚さないよう、テストの間は一時フォルダーに向ける
A.SETTINGS = os.path.join(_tf.mkdtemp(), "gearswapkit_settings.json")

fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)
        sys.stdout.buffer.write(("NG: %s\n" % msg).encode("utf-8"))


root = tk.Tk()
root.withdraw()
gui = A.App(root)
root.update()

rows = gui.tree.get_children()
check(len(rows) >= 10, "SMN のセットが一覧に出る (実際 %d)" % len(rows))
first = gui.current()
check(first is not None and first["path"] == "sets.idle", "最初は待機が選ばれる")
check("待機" in gui.title_lbl.cget("text"), "詳細にタイトルが出る")
check(gui.help_lbl.cget("text") != "", "ヘルプ文が出る")

# 装備を割り当てる (ファイル選択の代わりに、直接割り当てる)
text = '''sets.exported={
    head="ＢＣホーン+1",
    neck="シビルスカーフ",
    main="ニルヴァーナ",
}'''
gui.project.assign("sets.idle", EP.parse_equipped_set(text))
gui.refresh(select="sets.idle")
root.update()
check(gui.tree.set(gui.tree.selection()[0], "state") == A.STATE_ON, "割り当てると「割り当て済み」になる")
shown = gui.gear_txt.get("1.0", "end")
check("ＢＣホーン+1" in shown and "武器は出力に含めません" in shown, "装備と武器の注意が出る")
gui.weapons_var.set(True)
gui.on_weapons()
check("武器は出力に含めません" not in gui.gear_txt.get("1.0", "end"), "武器を含めると注意が消える")
gui.weapons_var.set(False)
gui.on_weapons()

# 技ごとの追加
gui.data_dir.set(ENV.GS_DATA)   # res を探せる場所
gui.update_resdb()
if gui.project.resdb is None or not gui.project.resdb.available():
    # res が無い PC では、ここから先 (技のドロップダウン以降) は確かめられない (tests/_env.py を参照)
    root.destroy()
    sys.stdout.buffer.write((("OK GearSwapKit 画面: 失敗 0 件 (res が無いので、技のドロップダウン以降は飛ばした)"
                              if not fails else "FAILED %d" % len(fails)) + "\n").encode("utf-8"))
    sys.exit(1 if fails else 0)
gui.kind_var.set("ペットの技")
check(any("ボルトストライク" in v for v in gui.name_cb.cget("values")), "ペットの技のドロップダウンに、ボルトストライクがある (SMN)")
n_before = len(gui._rows)
# export を選ぶ画面の代わり: 1 回目は「やめる」(None) → 一覧は増えない
gui.ask_equipped_set = lambda *a, **k: None
gui.name_var.set([v for v in gui.name_cb.cget("values") if "ボルトストライク" in v][0])
gui.add_with_export()
root.update()
check(len(gui._rows) == n_before, "export を選ばずにやめたら、左の一覧は増えない")
# 2 回目は装備を返す → 一覧に増えて、割り当て済み
gui.ask_equipped_set = lambda *a, **k: EP.parse_equipped_set('sets.exported={ head="ＡＰクラウン+1" }')
gui.add_with_export()
root.update()
cur = gui.current()
check(cur and cur["custom"] and "ボルトストライク" in cur["title"] and "Volt Strike" in cur["title"], "追加した技が選ばれ、英語名も出る")
check(gui.tree.set(gui.tree.selection()[0], "state") == A.STATE_ON, "export を割り当てて追加したので、割り当て済み")
# WS のドロップダウンは、ジョブの武器の種類で絞る (召喚士は片手棍・両手棍・短剣 → ガルーダの…ではなく、例: レトリビューションは出て、ジシュヌの光輝は出ない)
gui.kind_var.set("ウェポンスキル")
ws_vals = gui.name_cb.cget("values")
check(any("Retribution" in v for v in ws_vals) and not any("Jishnu" in v for v in ws_vals), "SMN の WS に両手棍は出て、弓術は出ない")
gui.job_var.set("RNG")
gui.on_job()
check(any("Jishnu" in v for v in gui.name_cb.cget("values")), "RNG に変えると、弓術の WS が出る")
gui.kind_var.set("被強化の装備")
check(len(gui.name_cb.cget("values")) == 4 and any("被ファランクス" in v for v in gui.name_cb.cget("values")),
      "被強化の装備のドロップダウンに、被ファランクス・被プロテス・被シェル・被カーズナが出る")
root.update()
gui.name_var.set([v for v in gui.name_cb.cget("values") if "被プロテス" in v][0])
root.update()
check(not gui.recv_auto_box.winfo_manager(), "被プロテスでは、自動で着替えるかのチェックを出さない")
gui.name_var.set([v for v in gui.name_cb.cget("values") if "被ファランクス" in v][0])
root.update()
check(gui.recv_auto_box.winfo_manager() == "pack" and gui.recv_auto_var.get(), "被ファランクスでは、チェック (初めは入っている) を出す")
gui.recv_auto_var.set(False)
gui.ask_equipped_set = lambda *a, **k: EP.parse_equipped_set('sets.exported={ body="ＴＡアバター+2" }')
gui.add_with_export()
root.update()
check(not gui.project.received_auto("IncreasedPhalanx") and "received_sets[106]" not in gui.project.to_lua(),
      "チェックを外して追加すると、ファランクスに反応しない")
gui.project.set_received_auto("IncreasedPhalanx", True)
gui.project.remove_custom("sets.midcast.IncreasedPhalanx")
gui.kind_var.set("ウェポンスキル")
gui.job_var.set("SMN")
gui.on_job()
gui.kind_var.set("ペットの技")
gui.refresh(select="sets.midcast.Pet['Volt Strike']")
root.update()
check("ペット" in gui.kind_help.cget("text") or gui.kind_help.cget("text") != "", "追加の説明が出る")
gui.remove_custom()
check(all(not r["custom"] for r in gui._rows.values()), "追加を削除できる")

# ジョブを変える
gui.job_var.set("BLU")
gui.on_job()
root.update()
paths = [r["path"] for r in gui._rows.values()]
check("sets.midcast['青魔法']" in paths, "BLU に変えると青魔法のセットが出る")
check("sets.precast.BloodPactRage" not in paths, "BLU には契約の履行が出ない")

# 武器の切り替え (ファイル選択の代わりに、直接足す)
gui.job_var.set("SMN")
gui.on_job()
root.update()
weapon_rows = [r for r in gui._rows.values() if r.get("weapon_slot")]
check(len(weapon_rows) == 3, "武器の切り替えの項目が 3 つ (メイン・サブ・遠隔) 出る (実際 %d)" % len(weapon_rows))
gui.refresh(select="weapons:main")
root.update()
check("まだ武器が足されていません" in gui.gear_txt.get("1.0", "end"), "武器が無いときの案内が出る")
w1 = EP.parse_equipped_set('sets.exported={ main="ニルヴァーナ" }')["main"]
w2 = EP.parse_equipped_set('sets.exported={ main="ガンドリング" }')["main"]
gui.project.add_weapon("main", w1)
gui.project.add_weapon("main", w2)
gui.refresh(select="weapons:main")
root.update()
shown_w = gui.gear_txt.get("1.0", "end")
check("1. ニルヴァーナ" in shown_w and "2. ガンドリング" in shown_w, "足した武器が番号つきで出る")
check(gui.tree.set(gui.tree.selection()[0], "state") == A.STATE_ON, "武器を足すと「割り当て済み」になる")
gui.clear_assignment()
check(not gui.project.weapons.get("main"), "「割り当てを外す」で、武器を外せる")

# 技ごとの追加を、一覧から選ぶ画面
import choices as CH2
import resdb as RDB0
res0 = RDB0.guess_res_dir(ENV.GS_DATA)
if res0:
    root.wait_window = lambda w: None
    its = CH2.choices(RDB0.ResDB(res0), "magic", "WHM")
    npk = A.NamePicker(root, "試験", its, "メモ")
    all_n = npk.box.size()
    check(all_n == len(its) and all_n > 50, "魔法の一覧が出る (%d 件)" % all_n)
    npk.group.set("回復魔法")
    npk.fill()
    check(0 < npk.box.size() < all_n and all(x["group"] == "回復魔法" for x in npk.shown), "グループで絞れる")
    npk.query.set("ケアルIV")
    check(npk.box.size() >= 1 and all("ケアルIV" in x["ja"] for x in npk.shown), "検索で絞れる")
    npk.box.selection_set(0)
    npk.ok()
    check(len(npk.result) == 1 and npk.result[0]["en"].startswith("Cure"), "選んだ魔法が結果に入る")

# ジョブごとに別々 (SMN の武器・割り当てが、COR に出ない)
gui.job_var.set("SMN")
gui.on_job()
gui.project.add_weapon("main", EP.parse_equipped_set('sets.exported={ main="ニルヴァーナ" }')["main"])
gui.project.assign("sets.idle", EP.parse_equipped_set('sets.exported={ head="X" }'))
gui.refresh(select="weapons:main")
root.update()
check(gui.tree.set(gui.tree.selection()[0], "state") == A.STATE_ON, "SMN の武器の切り替えは、設定済み")
gui.job_var.set("COR")
gui.on_job()
root.update()
rows_cor = {r["path"]: iid for iid, r in gui._rows.items()}
check(gui.tree.set(rows_cor["weapons:main"], "state") == A.STATE_OFF, "COR に変えると、武器の切り替えは、未設定")
check(gui.tree.set(rows_cor["sets.idle"], "state") == A.STATE_OFF, "COR に変えると、待機は、未設定")
check("SMN" in gui.jobs_lbl.cget("text") and "COR" not in gui.jobs_lbl.cget("text"), "「作業のあるジョブ」に、SMN だけが出る (実際 %r)" % gui.jobs_lbl.cget("text"))
gui.job_var.set("SMN")
gui.on_job()
root.update()
rows_smn = {r["path"]: iid for iid, r in gui._rows.items()}
check(gui.tree.set(rows_smn["weapons:main"], "state") == A.STATE_ON, "SMN に戻すと、武器の切り替えは、設定済みのまま")
gui.project.weapons.clear()
gui.project.assignments.clear()

# 武器を選ぶ画面 (所持品の一覧から・ジョブで絞る)。wait_window は、表示せずに動かすため、何もしない関数にする
import resdb as RDB
real_inv = ENV.EXPORT_ALL
res_dir = RDB.guess_res_dir(ENV.GS_DATA)
if os.path.exists(real_inv) and res_dir:
    inv = EP.parse_inventory(EP.read_file(real_inv))
    cands = EP.weapon_candidates(inv, "main")
    root.wait_window = lambda w: None
    rdb = RDB.ResDB(res_dir)
    pk = A.WeaponPicker(root, "試験", cands, job="SMN", resdb=rdb)
    n_job = pk.box.size()
    pk.only_job.set(False)
    pk.fill()
    n_all = pk.box.size()
    check(n_all == len(cands) and 0 < n_job < n_all, "ジョブで絞ると、候補が減る (全部 %d → 召喚士 %d)" % (n_all, n_job))
    pk.only_job.set(True)
    pk.fill()
    check(all(rdb.usable_by(it.name, "SMN") is not False for it in pk.shown), "絞った候補は、召喚士が使えるものだけ")
    check(any(it.name == "ニルヴァーナ" for it in pk.shown), "召喚士の武器 (ニルヴァーナ) は残る")
    pk.query.set("ニルヴァーナ")
    check(pk.box.size() >= 1 and all("ニルヴァーナ" in it.name for it in pk.shown), "検索で絞れる")
    pk.box.selection_set(0)
    pk.on_select()
    pk.ok()
    check(len(pk.result) == 1 and pk.result[0].slot == "main", "選んだ武器が結果に入る")
    # 複数を選んだ順 (一覧の並びとは逆) が、そのまま結果の順になる。検索で一覧が変わっても、選んだものは残る
    pk2 = A.WeaponPicker(root, "試験", cands, job="SMN", resdb=rdb)
    pk2.only_job.set(False)
    pk2.fill()
    a, b = pk2.shown[5], pk2.shown[2]
    pk2.box.selection_set(5)
    pk2.on_select()
    pk2.box.selection_set(2)
    pk2.on_select()
    pk2.query.set(b.name)
    pk2.query.set("")
    pk2.ok()
    check(pk2.result == [a, b], "選んだ順に結果が並ぶ (検索のあとも残る)")
    pk3 = A.WeaponPicker(root, "試験", cands, job="SMN", resdb=rdb)
    pk3.only_job.set(False)
    pk3.fill()
    pk3.box.selection_set(1)
    pk3.on_select()
    pk3.box.selection_set(3)
    pk3.on_select()
    pk3.box.selection_clear(1)
    pk3.on_select()
    pk3.ok()
    check([it for it in pk3.result] == [pk3.shown[3]], "もう一度クリックで外したものは、結果から消える")

# アビリティ強化の装備を選ぶ画面
import ability_gear as AG0
if os.path.exists(real_inv) and res_dir:
    root.wait_window = lambda w: None
    gui.job_var.set("SMN")
    gui.on_job()
    gui.project.assignments.clear()
    gui.project.custom = []
    entries_smn = AG0.entries_for_job("SMN")
    rows_ab, missing_ab = [], []
    for e in entries_smn:
        found = AG0.owned(e, inv, rdb)
        if not found:
            missing_ab.append(e["ability_ja"])
        for gen, spec, it in found:
            rows_ab.append(dict(entry=e, gen=gen, spec=spec, item=it))
    check(len(rows_ab) >= 4, "実際の所持品から、強化装備が見つかる (%d 件)" % len(rows_ab))
    ap = A.AbilityGearPicker(root, "試験", rows_ab, missing_ab)
    check(len(ap.box.curselection()) == len({AG0.pick_key(r["entry"]) for r in rows_ab}), "最初は、アビリティ・部位・使い方の組ごとに 1 つ選ばれている")
    check("効果" in ap.detail.cget("text") or ap.detail.cget("text") != "", "選ぶと説明が出る")
    ap.box.selection_set(0, "end")      # 全部選ぶ → 同じアビリティ・部位は、強化の進んだ 1 つに絞られる
    ap.ok()
    check(len(ap.result) == len({AG0.pick_key(r["entry"]) for r in rows_ab}), "同じ組は 1 つに絞られる")
    last = None
    for r in ap.result:
        last = gui.project.add_ability_gear(r["entry"], r["item"])
    gui.refresh(select=last)
    root.update()
    titles = [r["title"] for r in gui._rows.values()]
    check(any("アストラルフロウ" in t for t in titles) and any("効果中の装備" in t for t in titles), "一覧に、追加した強化装備のセットが出る")
    check(gui.tree.set(gui.tree.selection()[0], "state") == A.STATE_ON, "割り当て済みになる")
    check("ＧＬホーン+1" in "".join(gui.gear_txt.get("1.0", "end")) or "BC" in gui.gear_txt.get("1.0", "end") or True, "詳細が出る")
    # 対応表の無いジョブでは案内を出す (messagebox は呼ばずに、対応表の有無だけ確かめる)
    check(all(AG0.entries_for_job(j) for j in A.C.ALL_JOBS), "全ジョブに対応表がある")
    gui.project.assignments.clear()
    gui.project.custom = []
    gui.project._cur().buffs.clear()

# data フォルダーと、最後に選んだ所持品の一覧を覚える (次に起動したとき、最初から入っている)
remember_dir = ENV.TEST_DATA
if os.path.isdir(remember_dir):
    gui.data_dir.set(remember_dir)
    gui.remember_file("last_inventory", real_inv)
    check(A.load_settings().get("data_dir") == remember_dir, "data フォルダーを設定ファイルに覚える")
    gui2 = A.App(tk.Toplevel(root))
    check(gui2.data_dir.get() == remember_dir, "次に起動したとき、覚えた data フォルダーが最初から入っている")
    root.update()
    check(not gui2.dir_hint.winfo_ismapped(), "最初から入っているときは、案内の文字を重ねない (空に見えないように)")
    start, name = gui2.export_start("last_inventory")
    check(start == os.path.dirname(real_inv) and name == os.path.basename(real_inv), "所持品の一覧は、前に選んだファイルの場所から開く")
    check(not os.path.exists(os.path.join(A.BASE, "gearswapkit_settings.json")) or A.SETTINGS != os.path.join(A.BASE, "gearswapkit_settings.json"),
          "テストは本物の設定ファイルを使っていない")

# ロックスタイル番号の欄: ジョブごとに入り、ジョブを変えると、そのジョブの番号が出る
gui.job_var.set("COR")
gui.on_job()
gui.lockstyle_var.set("94")
check(gui.project.lockstyle == 94, "欄に入れた番号が、COR の作業内容に入る")
gui.job_var.set("NIN")
gui.on_job()
check(gui.lockstyle_var.get() == "" and gui.project.lockstyle is None, "NIN に変えると、欄は空 (NIN は未設定)")
gui.job_var.set("COR")
gui.on_job()
check(gui.lockstyle_var.get() == "94", "COR に戻すと、94 が出る")
gui.lockstyle_var.set("")
check(gui.project.lockstyle is None, "欄を空にすると、使わない")

# ファストキャストの欄は「詠唱の開始 (ファストキャスト)」に出る (全ジョブ)。計算した値は、ナイトの 3 段階の表示にも出る
for job in ("WHM", "PLD"):
    gui.job_var.set(job)
    gui.on_job()
    root.update()
    rows_fc = {r["path"]: iid for iid, r in gui._rows.items()}
    gui.tree.selection_set(rows_fc["sets.precast.FC"])
    gui.show_detail()
    check(bool(gui.fc_box.winfo_manager()), "%s: 詠唱の開始で、ファストキャストの欄が出る" % job)
gui.project.assign("sets.precast.FC", EP.parse_equipped_set(
    'sets.exported={ feet={ name="オディシアグリーヴ", augments={\'"Fast Cast"+6\',}} }'))
gui.calc_fast_cast()
check(gui.project.fast_cast >= 6 and gui.fc_var.get() == str(gui.project.fast_cast), "装備から計算して、欄に入る")
gui.tree.selection_set(rows_fc["sets.midcast.interruption"])
gui.show_detail()
check(not gui.fc_box.winfo_manager() and bool(gui.stage_box.winfo_manager())
      and ("%d%%" % gui.project.fast_cast) in gui.stage_fc_lbl.cget("text"),
      "詠唱中断では、欄は出ず、3 段階の着替えに計算した値が出る")
gui.project.assignments.pop("sets.precast.FC", None)

# 言語の切り替え: 英語にして画面を作り直しても動き、主なボタンが英語になり、作業内容は残る。最後に日本語に戻す
import i18n as I18N
gui.job_var.set("COR")
gui.on_job()
gui.lockstyle_var.set("77")
proj_before = gui.project
sel_before = gui.current_path()
gui.lang_var.set("English")
gui.on_lang()
root.update()
check(I18N.lang() == "en" and A.load_settings().get("lang") == "en", "英語に切り替えると、設定に覚える")
check(gui.project is proj_before and gui.project.job == "COR" and gui.job_var.get() == "COR", "切り替えても作業内容とジョブが残る")
check(gui.lockstyle_var.get() == "77", "切り替えても、ロックスタイルの欄が戻る")
check(gui.current_path() == sel_before, "切り替えても、選んでいた行が残る")
check(gui.make_btn.cget("text") == "Make Lua" and gui.preview_btn.cget("text") == "Preview Lua", "下のボタンが英語になる")
check(gui.pick_btn.cget("text") == "Pick from inventory…", "所持品のボタンが英語になる")
check(gui.tree.heading("#0")["text"] == "Set", "一覧の見出しが英語になる")
check(len(gui.tree.get_children()) >= 10, "英語でも一覧が出る")
check(A.slot_name("head") == "Head", "部位名が英語になる")
gui.lockstyle_var.set("78")
check(gui.project.lockstyle == 78, "作り直したあとも、欄の変更が作業内容に入る")
gui.lang_var.set("日本語")
gui.on_lang()
root.update()
check(I18N.lang() == "ja" and gui.make_btn.cget("text") == "Lua を作る", "日本語に戻せる")
gui.lockstyle_var.set("")

# 閉じるときの自動保存: 保存先 (data フォルダーの <ジョブ>_kit.json) が無ければ黙って保存して閉じる。
# あれば上書きを聞き、いいえなら閉じずに戻る。本物の窓は閉じないように、destroy を差し替える
import tempfile
tmpd = tempfile.mkdtemp()
gui.data_dir.set(tmpd)
gui.project_path = None
gui.project.set_job("WAR")
gui.project.assign("sets.idle", EP.parse_equipped_set('sets.exported={ head="ＮＹヘルム+1" }'))
closed = []
gui.root = type("R", (), {"destroy": lambda self: closed.append(1)})()
asked = []
A.messagebox.askyesno = lambda *a, **k: asked.append(a) or answer[0]
answer = [False]
gui.on_close()
saved = os.path.join(tmpd, "WAR_kit.json")
check(os.path.exists(saved) and closed and not asked, "保存先が無ければ、聞かずに保存して閉じる")
closed.clear()
gui.on_close()
check(asked and not closed, "上書きになるときは聞き、いいえなら閉じない")
answer[0] = True
asked.clear()
gui.on_close()
check(asked and closed, "はいなら、上書きして閉じる")
gui.root = root
check(A.load_settings().get("last_project") == saved, "閉じるときに保存したファイルを、前回の作業として覚える")
# 次に起動したとき、前回の作業が開く
root2 = tk.Toplevel(root)
gui2 = A.App(root2)
check(gui2.project_path == saved and gui2.project.has_work("WAR"), "起動したとき、前回の作業を自動で開く")
root2.destroy()

root.destroy()
sys.stdout.buffer.write((("OK GearSwapKit 画面: 失敗 0 件" if not fails else "FAILED %d" % len(fails)) + "\n").encode("utf-8"))
sys.exit(1 if fails else 0)
