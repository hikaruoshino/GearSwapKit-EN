# -*- coding: utf-8 -*-
"""Check the GearSwap data folder for files that would override the kit's output.

After loading the job Lua, Mote-Include automatically loads the files below, which override functions with the same names
(init_include in Mote-Include.lua, load_sidecar in Mote-Utility.lua):
  - user-globals.lua / <character>-globals.lua
  - <JOB>_gear.lua / <character>_<JOB>_gear.lua  (directly in data, data/<folder>/, data/common/, data/gear/)
If any of these defines init_gear_sets, the sets the kit built won't be used.
"""
import os

from i18n import L


def find_conflicts(data_dir, job):
    """Return [(file path, reason)]. Empty if there is no data_dir."""
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
