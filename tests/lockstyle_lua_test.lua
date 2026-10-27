-- 出力した Lua の「ロックスタイル」の動きを、GearSwap を模擬して確認する。
-- 実行: lua5.1.exe tests/lockstyle_lua_test.lua <出力した Lua のパス>   (ロックスタイル番号 94・武器の切り替えありの Lua)
local path = arg[1]
local fails = 0
local function check(cond, msg) if not cond then fails = fails + 1; io.write("NG: " .. msg .. "\n") end end

local sent = {}
local env = {
    include = function() end, set_language = function() end,
    send_command = function(c) sent[#sent + 1] = c end,
    equip = function() end,
    M = function(t) return {description = t.description, value = t[1], current = t[1]} end,
    state = {IdleMode = {options = function() end}},
    sets = {precast = {JA = {}}, buff = {}, idle = {}, engaged = {}},
    pairs = pairs, ipairs = ipairs, string = string, table = table, tostring = tostring,
}
setmetatable(env, {__index = _G})
local chunk = assert(loadfile(path))
setfenv(chunk, env)
chunk()
env.user_setup()
env.init_gear_sets()
if env.after_gear_sets then env.after_gear_sets() end   -- GearSwap と同じ順 (get_sets の中で init_gear_sets のあと)

local found = false
for _, c in ipairs(sent) do if c == "wait 5; gs c lockstyleset" then found = true end end
check(found, "読み込み後に、少し待ってロックスタイルをかける命令を送る")
check(env.lockstyleset == 94, "lockstyleset が 94")

sent = {}
local ea = {handled = false}
env.job_self_command({"lockstyleset"}, ea)
check(ea.handled and sent[1] == "input /lockstyleset 94", "//gs c lockstyleset で /lockstyleset 94 を送る")

local ea2 = {handled = false}
env.job_self_command({"weapons"}, ea2)
check(ea2.handled, "//gs c weapons も、同じ関数で処理する")

local ea3 = {handled = false}
env.job_self_command({"unknown"}, ea3)
check(not ea3.handled, "ほかのコマンドは、そのまま通す")

if fails == 0 then io.write("OK ロックスタイル (Lua): 失敗 0 件\n") else io.write("FAILED " .. fails .. "\n"); os.exit(1) end
