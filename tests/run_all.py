# -*- coding: utf-8 -*-
"""Runs every test in tests/. Run (from GearSwapKit/): python -I tests/run_all.py
The GUI test (test_gui.py) needs tkinter. See tests/_env.py for where external files (res, Lua 5.1, etc.) are found.
If something is missing, the test that needs it skips those checks."""
import glob
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
failed = []
skipped_cases = 0
for path in sorted(glob.glob(os.path.join(HERE, "test_*.py"))):
    r = subprocess.run([sys.executable, "-X", "utf8", "-I", path], cwd=ROOT, capture_output=True)
    out = (r.stdout + r.stderr).decode("utf-8", "replace").strip().splitlines()
    last = out[-1] if out else "(出力なし)"
    status = "NG" if r.returncode else "OK"
    skipped = re.fullmatch(r"OK \(skipped=(\d+)\)", last)
    if skipped:
        skipped_cases += int(skipped.group(1))
        status = "SKIP"
    sys.stdout.buffer.write(("%-4s %s: %s\n" % (status, os.path.basename(path), last)).encode("utf-8"))
    if r.returncode != 0:
        failed.append(os.path.basename(path))
        for line in out[-15:]:
            sys.stdout.buffer.write(("      %s\n" % line).encode("utf-8"))
sys.stdout.buffer.write(("\n全 %d 本 / 失敗 %d 本 %s\n" % (len(glob.glob(os.path.join(HERE, "test_*.py"))), len(failed), " ".join(failed))).encode("utf-8"))
if skipped_cases:
    sys.stdout.buffer.write(("Cases skipped by unittest: %d\n" % skipped_cases).encode("utf-8"))
sys.exit(1 if failed else 0)
