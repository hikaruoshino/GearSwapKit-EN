-- 出力した Lua の「武器の切り替え」の動きを、GearSwap を模擬して確認する。
-- 実行: lua5.1.exe tests/weapons_lua_test.lua <出力した Lua のパス>
local path = arg[1]
local fails = 0
local function check(cond, msg) if not cond then fails = fails + 1; io.write("NG: " .. msg .. "\n") end end

local equipped = {}
local sent = {}
local env = {
    equip = function(t) equipped[#equipped + 1] = t end,
    send_command = function(c) sent[#sent + 1] = c end,
    include = function() end, set_language = function() end,
    M = function(t)   -- Mote の M{} の代わり: 選択肢と、いまの選択
        local m = {description = t.description, current = t[1], options = {}}
        for i = 1, #t do m.options[i] = t[i] end
        return m
    end,
    state = {IdleMode = {options = function() end}},
    pairs = pairs, ipairs = ipairs, string = string, table = table,
}
setmetatable(env, {__index = _G})
local chunk = assert(loadfile(path))
setfenv(chunk, env)
chunk()

check(type(env.user_setup) == "function", "user_setup がある")
env.user_setup()
check(env.state.MainWeapons ~= nil and env.state.MainWeapons.current == "ニルヴァーナ", "MainWeapons の最初の選択")
check(#env.state.MainWeapons.options == 2, "MainWeapons に 2 本")
check(env.state.SubWeapons ~= nil, "SubWeapons がある")
check(env.state.RangeWeapons == nil, "遠隔は足していないので、RangeWeapons は作らない")
check(sent[#sent] == "wait 3; gs c weapons", "読み込んだあとに武器を装備する命令を送る")

-- cycle したときに Mote が呼ぶ job_state_change
env.job_state_change("MainWeapons", "ガンドリング", "ニルヴァーナ")
check(equipped[#equipped] and equipped[#equipped].main == "ガンドリング", "ガンドリングをメインに装備する")
equipped = {}
env.job_state_change("SubWeapons", "ドゥバン", "x")
check(equipped[#equipped] and type(equipped[#equipped].sub) == "table" and equipped[#equipped].sub.name == "ドゥバン", "オーグメント付きのサブを装備する")
equipped = {}
env.job_state_change("IdleMode", "DT", "Normal")
check(#equipped == 0, "武器の状態ではない変更では、何もしない")
env.job_state_change("MainWeapons", "存在しない", "x")
check(#equipped == 0, "名前が合わないときは、何もしない")

-- //gs c weapons
local ea = {handled = false}
env.job_self_command({"weapons"}, ea)
check(ea.handled == true, "weapons コマンドを処理する")
check(#equipped >= 2, "今の選択の武器を、メインとサブの両方、装備する (実際 " .. #equipped .. ")")
local ea2 = {handled = false}
env.job_self_command({"unknown"}, ea2)
check(ea2.handled == false, "ほかのコマンドは、そのまま通す")

if fails == 0 then io.write("OK 武器の切り替え (Lua): 失敗 0 件\n") else io.write("FAILED " .. fails .. "\n"); os.exit(1) end
