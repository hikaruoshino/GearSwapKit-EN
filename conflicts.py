# -*- coding: utf-8 -*-
"""GearSwap の data フォルダーに、キットの出力を上書きするファイルがないかを調べる。

Mote-Include は、ジョブの Lua を読み込んだあとに、次のファイルを自動で読み込み、同じ名前の関数を上書きする
(Mote-Include.lua の init_include・Mote-Utility.lua の load_sidecar)。
  - user-globals.lua / <キャラ名>-globals.lua
  - <ジョブ>_gear.lua / <キャラ名>_<ジョブ>_gear.lua  (data 直下・data/<フォルダー>/・data/common/・data/gear/)
これらが init_gear_sets を定義していると、キットが作ったセットは使われない。
"""
import os

from i18n import L


def find_conflicts(data_dir, job):
    """[(ファイルのパス, 理由)] を返す。data_dir が無ければ空。"""
    found = []
    if not data_dir or not os.path.isdir(data_dir):
        return found
    job_l = job.lower()

    def scan_dir(folder, depth):
        try:
            names = os.listdir(folder)
        except OSError:
            return
        for name in names:
            full = os.path.join(folder, name)
            low = name.lower()
            if os.path.isdir(full):
                if depth < 1 and low not in ("export", "backup", "_hold"):
                    scan_dir(full, depth + 1)
                continue
            if not low.endswith(".lua"):
                continue
            stem = low[:-4]
            if stem == job_l + "_gear" or stem.endswith("_" + job_l + "_gear"):
                found.append((full, L("このジョブの付属ファイルです。init_gear_sets を定義していると、キットのセットが上書きされます",
                                      "Gear file for this job. If it defines init_gear_sets, it replaces the sets the kit made.")))
            elif depth == 0 and (stem == "user-globals" or stem.endswith("-globals")):
                found.append((full, L("全ジョブ共通のファイルです。user_setup などの関数を上書きすることがあります",
                                      "Shared by every job. It may replace functions such as user_setup.")))

    scan_dir(data_dir, 0)
    return found
