# -*- coding: utf-8 -*-
"""場面の一覧と説明の日英切り替えの確認。実行 (GearSwapKit/ で): python -I tests/test_i18n_catalog.py"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import ability_gear as AG
import i18n
import set_catalog as C
from project import Project, RECEIVED_KIND, JA_KIND

JP = re.compile(r"[぀-ヿ㐀-鿿＀-￯]")
fails = []


def check(ok, msg):
    print(("OK  " if ok else "NG  ") + msg)
    if not ok:
        fails.append(msg)


def make(job):
    pr = Project(job)
    # 技ごとの追加 (res 無しでも足せる英語名・被強化・アビリティ強化の効果中・メリット)
    pr.add_custom(0, "Leaden Salute")
    pr.add_pair(JA_KIND, "Manawell", "マナウェル")
    pr.add_pair(RECEIVED_KIND, "IncreasedPhalanx", "被ファランクス (受けるファランクスの強化)")
    pr.custom.append(("sets.buff['Immanence']", "効果中に魔法をするときの装備: 震天動地の章 (Immanence)", None))
    pr._cur().buffs["sets.buff['Immanence']"] = (470, "Immanence", "震天動地の章", "midcast", "Magic")
    pr.custom.append(("sets.merit.FineTuning", "メリット特性の装備: 微調整", None))
    pr.custom.append(("sets.Stormsurge", "陣頭指揮の足 (陣の魔法を唱えるとき)", None))
    pr.custom.append(("sets.precast.CorsairRoll", "メリット特性の装備: ファントムロール", None))
    return pr


try:
    before = {}
    i18n.set_lang("ja")
    for job in C.ALL_JOBS:
        before[job] = [(r["path"], r["title"], r["help"]) for r in make(job).entries()]
    check(all(JP.search(t) for rows in before.values() for _p, t, _h in rows if not _p.startswith("sets.precast.WS['")),
          "日本語のとき、題名は日本語")

    i18n.set_lang("en")
    bad = []
    for job in C.ALL_JOBS:
        rows = make(job).entries()
        check([r["path"] for r in rows] == [p for p, _t, _h in before[job]], job + ": path は言語で変わらない")
        for r in rows:
            for k in ("title", "help"):
                if not r[k] or JP.search(r[k]):
                    bad.append("%s %s %s: %r" % (job, r["path"], k, r[k]))
    for b in bad[:20]:
        print("    " + b)
    check(not bad, "英語のとき、全ジョブの title / help に日本語が残らない")
    check(all(not JP.search(C.kind_label(i) + C.kind_help(i)) for i in range(len(C.CUSTOM_KINDS))), "技ごとの追加の種類も英語")
    check(not JP.search(AG.timing_name("use") + AG.cast_phase_name("both") + AG.cast_on_name("Magic")), "ability_gear の名前も英語")
    check(AG.timing_name("??") == "??", "知らない timing はそのまま")
    t = {r["path"]: r["title"] for r in make("SCH").entries()}
    check(t["sets.precast.WS['Leaden Salute']"] == "Weapon skill: Leaden Salute", "技ごとの追加の英語の表示名")
    check(t["sets.midcast['回復魔法']"] == "Midcast (Healing Magic)", "魔法スキルの場面の英語")

    i18n.set_lang("ja")
    for job in C.ALL_JOBS:
        now = [(r["path"], r["title"], r["help"]) for r in make(job).entries()]
        if now != before[job]:
            check(False, job + ": 日本語に戻すと元どおり")
            break
    else:
        check(True, "日本語に戻すと、全ジョブ元どおり")
finally:
    i18n.set_lang("ja")

print("\n失敗: %d" % len(fails) if fails else "\nすべて OK")
sys.exit(1 if fails else 0)
