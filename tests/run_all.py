# -*- coding: utf-8 -*-
"""tests/ のテストを全部実行する。実行 (GearSwapKit/ で): python -I tests/run_all.py
画面のテスト (test_gui.py) は tkinter が要る。外部のファイル (res・Lua 5.1 など) の場所は tests/_env.py を参照。
無いものは、そのテストの中で確認を飛ばす。"""
import glob
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
failed = []
for path in sorted(glob.glob(os.path.join(HERE, "test_*.py"))):
    r = subprocess.run([sys.executable, "-I", path], cwd=ROOT, capture_output=True)
    out = (r.stdout + r.stderr).decode("utf-8", "replace").strip().splitlines()
    last = out[-1] if out else "(出力なし)"
    sys.stdout.buffer.write(("%s %s: %s\n" % ("OK  " if r.returncode == 0 else "NG  ", os.path.basename(path), last)).encode("utf-8"))
    if r.returncode != 0:
        failed.append(os.path.basename(path))
        for line in out[-15:]:
            sys.stdout.buffer.write(("      %s\n" % line).encode("utf-8"))
sys.stdout.buffer.write(("\n全 %d 本 / 失敗 %d 本 %s\n" % (len(glob.glob(os.path.join(HERE, "test_*.py"))), len(failed), " ".join(failed))).encode("utf-8"))
sys.exit(1 if failed else 0)
