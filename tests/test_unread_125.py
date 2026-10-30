# -*- coding: utf-8 -*-
"""Tests for 1.2.5: typos made when editing an export by hand (ear1== etc.) are reported by line number instead of being skipped silently.
Gear that can be read is still read as before. A file without typos reports nothing.
Run (from GearSwapKit/): python -I tests/test_unread_125.py [export files to check ...]"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import export_parser as EP

fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)
        sys.stdout.buffer.write(("NG: %s\n" % msg).encode("utf-8"))


# 1. The typo the user tried (a doubled =, and no comma after head="")
typo = ('sets.exported = {\n'
        '    main="Nirvana",\n'
        '    head=""\n'
        '    body="Con. Doublet +3",\n'
        '    ear1=="Lugalbanda Earring",\n'
        '    rear=={ name="Beckoner\'s Earring +1", augments={\'Pet: Accuracy+11\',}},\n'
        '    lring="Varar Ring +1",\n'
        '}\n')
got = EP.parse_equipped_set(typo)
check(sorted(got) == ["body", "left_ring", "main"], "読める行は読む (%s)" % sorted(got))
lines = EP.unread_lines(typo)
check([n for n, _ in lines] == [5, 6], "= が 2 つの行を 5・6 行目として知らせる (%s)" % lines)
check(lines and lines[0][1].startswith("ear1=="), "行の中身を添える (%s)" % lines[:1])

# 2. Nothing is reported for a correct file, aliases, empty items or comments
ok = ('-- comment ear1=="x"\n'
      '--[[ a multi-line\n'
      'comment ]]\n'
      'sets.exported={ main="Naegling", head="", ear1="Odnowa Earring +1",\n'
      '  ring2={ name="Gelatinous Ring +1", augments={"Path: A"} } }\n')
check(EP.unread_lines(ok) == [], "正しいファイルでは何も知らせない (%s)" % EP.unread_lines(ok))
check(len(EP.parse_equipped_set(ok)) == 3, "正しいファイルの装備は 3 つ読む")

# 3. Line numbers don't shift after a multi-line comment
after_block = '--[[\na\nb\n]]\nsets.exported = {\n    neck="Loricate Torque +1",\n    waist=="Flume Belt +1",\n}\n'
check([n for n, _ in EP.unread_lines(after_block)] == [7], "複数行のコメントのあとでも 7 行目と数える (%s)" % EP.unread_lines(after_block))

# 4. A misspelled slot name (lefft_ear) and an unclosed quote
check([n for n, _ in EP.unread_lines('sets.x = {\n  lefft_ear="Etiolation Earring",\n  neck="Sanctity Necklace",\n}')] == [2],
      "スロットでない名前に装備の名前がある行を知らせる")
unclosed = 'sets.x = {\n  neck="Sanctity Necklace",\n  waist="Flume Belt +1,\n  feet="Nyame Sollerets",\n}'
gu = EP.parse_equipped_set(unclosed)
check(gu.get("neck") is not None and gu.get("feet") is not None and gu["feet"].name == "Nyame Sollerets"
      and "waist" not in gu, "閉じていない引用符の行だけを飛ばし、前後の装備は読む (例外で止まらない) (%s)" % gu)
check([n for n, _ in EP.unread_lines(unclosed)] == [3], "閉じていない引用符の行を知らせる (%s)" % EP.unread_lines(unclosed))

# 5. Nothing is reported for an inventory list (item= lines)
inv = 'main="Naegling"\nmain="Kaja Rod"\nitem="Remedy"\nsub={ name="Ammurapi Shield" }\n'
check(EP.unread_lines(inv) == [], "所持品の一覧の item= の行は知らせない")

# 6. sub=empty (GearSwap's "wear nothing") isn't reported; a variable (gear.X) is
emp = 'sets.x = {\n  sub=empty,\n  head=gear.Slip,\n  neck="Sanctity Necklace",\n}'
check([n for n, _ in EP.unread_lines(emp)] == [3], "sub=empty は知らせず、head=gear.Slip は知らせる (%s)" % EP.unread_lines(emp))
check(sorted(EP.parse_equipped_set(emp)) == ["neck"], "sub=empty は装備として読まない")

# 7. A misspelled slot name whose value is a table with augments
tt = 'sets.x = {\n  lefft_ear={ name="Etiolation Earring", augments={\'HP+50\',}},\n  neck="Sanctity Necklace",\n}'
check([n for n, _ in EP.unread_lines(tt)] == [2], "lefft_ear={ name=… } を知らせる (%s)" % EP.unread_lines(tt))
check(sorted(EP.parse_equipped_set(tt)) == ["neck"], "打ち間違いの行のあとも読む")

# 8. A missing } doesn't swallow the next line's gear
br = "sets.exported = {\n    head={ name=\"Nyame Helm\", augments={'Path: B',},\n    body=\"Nyame Mail\",\n}\n"
gb = EP.parse_equipped_set(br)
check("head" not in gb and gb.get("body") is not None and gb["body"].name == "Nyame Mail",
      "} の閉じ忘れの head は読まず、次の body は読む (%s)" % gb)
check([n for n, _ in EP.unread_lines(br)] == [2], "} の閉じ忘れを 2 行目として知らせる (%s)" % EP.unread_lines(br))

# 9. Several slots on one line (//gs export compact) with an unclosed quote: no wrong name, and the next items are still read
cp = 'sets.exported={\n    head="Nyame Helm, neck="Loricate Torque +1", left_ear="Etiolation Earring",\n}'
gc = EP.parse_equipped_set(cp)
check("head" not in gc and gc.get("neck") and gc["neck"].name == "Loricate Torque +1" and gc.get("left_ear"),
      "compact の閉じ忘れ: head は読まず、neck・left_ear は読む (%s)" % gc)
check([n for n, _ in EP.unread_lines(cp)] == [2], "compact の閉じ忘れを 2 行目として知らせる (%s)" % EP.unread_lines(cp))

# 10. A file written on one line (minify): the line text starts at the slot that couldn't be read
mn = 'sets.exported={main="Naegling",neck=="Loricate Torque +1",waist="Flume Belt +1",}'
um = EP.unread_lines(mn)
check(len(um) == 1 and um[0][1].startswith("neck=="), "1 行のファイルでも、どの装備か分かる (%s)" % um)
check(sorted(EP.parse_equipped_set(mn)) == ["main", "waist"], "1 行のファイルで、後ろの装備も読む")

# 11. A missing =
ne = 'sets.x = {\n  neck"Loricate Torque +1",\n  waist "Flume Belt +1",\n  feet="Nyame Sollerets",\n}'
check([n for n, _ in EP.unread_lines(ne)] == [2, 3], "= の書き忘れを知らせる (%s)" % EP.unread_lines(ne))

# 12. A file saved by Notepad (BOM + CRLF), read through read_file
import tempfile
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, "crlf.lua")
    with open(p, "wb") as f:
        f.write(b"\xef\xbb\xbf" + typo.replace("\n", "\r\n").encode("utf-8"))
    uc = EP.unread_lines(EP.read_file(p))
    check([n for n, _ in uc] == [5, 6] and not any("\r" in s for _, s in uc), "BOM + CRLF でも行番号がずれず、\\r が残らない (%s)" % uc)

# 13. Real exports report nothing (no false warnings). Without arguments, the local exports are read
paths = sys.argv[1:]
if not paths:
    import glob
    paths = glob.glob(os.path.join(HERE, "..", "..", "GearSwap", "data", "export", "Pesan*.lua"))
for p in paths:
    u = EP.unread_lines(EP.read_file(p))
    check(u == [], "%s: 何も知らせない (%s)" % (os.path.basename(p), u[:3]))

if fails:
    sys.stdout.buffer.write(("FAILED %d 件\n" % len(fails)).encode("utf-8"))
    sys.exit(1)
sys.stdout.buffer.write(("OK 読めなかった行の知らせ: 失敗 0 件 (本物の export %d 個)\n" % len(paths)).encode("utf-8"))
