# -*- coding: utf-8 -*-
"""テストで使う外部のファイルの場所 (Windower の res・Lua 5.1・所持品の一覧など)。

環境変数か、tests/local_paths.json (公開しない・各自の PC の場所を書く) から読む。
どちらにも無いものは空文字にする。テストは、空や存在しない場所のときは、その確認を飛ばす。

local_paths.json の例:
{
 "res": "C:/Windower4/res",
 "luac": "C:/lua51/luac5.1.exe",
 "lua51": "C:/lua51/lua5.1.exe",
 "gearswap_data": "C:/Windower4/addons/GearSwap/data",
 "export_all": "C:/Windower4/addons/GearSwap/data/export/MyChar-all.lua",
 "test_data": "C:/Windower4/addons/gearswaptest/data"
}
"""
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
try:
    with open(os.path.join(_HERE, "local_paths.json"), encoding="utf-8") as _f:
        _LOCAL = json.load(_f)
except (OSError, ValueError):
    _LOCAL = {}


def _path(key, env):
    return os.environ.get(env) or _LOCAL.get(key) or ""


RES = _path("res", "GSK_RES")                       # Windower の res フォルダー
LUAC = _path("luac", "GSK_LUAC")                    # Lua 5.1 の luac (構文の確認)
LUA51 = _path("lua51", "GSK_LUA51")                 # Lua 5.1 (模擬 GearSwap の実行)
GS_DATA = _path("gearswap_data", "GSK_GS_DATA")     # GearSwap の data フォルダー (res を探す起点)
EXPORT_ALL = _path("export_all", "GSK_EXPORT_ALL")  # //gs export all の所持品の一覧
TEST_DATA = _path("test_data", "GSK_TEST_DATA")     # 画面のテストで使う data フォルダー
