# -*- coding: utf-8 -*-
"""Locations of external files the tests use (Windower's res, Lua 5.1, the inventory export, etc.).

Read from environment variables, or from tests/local_paths.json (not published; each user fills in the paths on their own PC).
Anything found in neither is set to an empty string. When a path is empty or doesn't exist, the tests skip the checks that need it.

Example local_paths.json:
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


RES = _path("res", "GSK_RES")                       # Windower's res folder
LUAC = _path("luac", "GSK_LUAC")                    # Lua 5.1 luac (syntax check)
LUA51 = _path("lua51", "GSK_LUA51")                 # Lua 5.1 (runs the mock GearSwap)
GS_DATA = _path("gearswap_data", "GSK_GS_DATA")     # GearSwap data folder (starting point when looking for res)
EXPORT_ALL = _path("export_all", "GSK_EXPORT_ALL")  # inventory list from //gs export all
TEST_DATA = _path("test_data", "GSK_TEST_DATA")     # data folder used by the GUI tests
