-- 出力した Lua の「遠隔魔攻 (sets.precast.WS.RangeMagic)」の分け方を、GearSwap を模擬して確認する。
-- 実行: lua5.1.exe tests/ws_rmagic_lua_test.lua <出力した Lua のパス>   (test_ws.py が作る、魔攻と遠隔魔攻のある COR の Lua)
local path = arg[1]
local fails = 0
local function check(cond, msg) if not cond then fails = fails + 1; io.write("NG: " .. msg .. "\n") end end

local env = {
    include = function() end, set_language = function() end, send_command = function() end, equip = function() end,
    M = function(t) return {description = t.description, value = t[1], current = t[1]} end,
    state = {IdleMode = {options = function() end}},
    sets = {precast = {JA = {}, WS = {}}, buff = {}, idle = {}, engaged = {}},
    set_combine = function(a, b) local r = {} for k, v in pairs(a) do r[k] = v end for k, v in pairs(b) do r[k] = v end return r end,
    pairs = pairs, ipairs = ipairs, string = string, table = table, tostring = tostring,
}
setmetatable(env, {__index = _G})
local chunk = assert(loadfile(path))
setfenv(chunk, env)
chunk()
env.user_setup()
env.init_gear_sets()
if env.after_gear_sets then env.after_gear_sets() end   -- GearSwap と同じ順 (get_sets の中で init_gear_sets のあと)

local map = env.job_get_spell_map
check(map({type = "WeaponSkill", english = "Leaden Salute", skill = "射撃"}) == "RangeMagic", "レデンサリュート (射撃・魔法属性) は RangeMagic")
check(map({type = "WeaponSkill", english = "Wildfire", skill = "Marksmanship"}) == "RangeMagic", "ワイルドファイア (英語のスキル名) は RangeMagic")
check(map({type = "WeaponSkill", english = "Aeolian Edge", skill = "短剣"}) == "Magic", "イオリアンエッジ (近接・魔法属性) は Magic")
check(map({type = "WeaponSkill", english = "Savage Blade", skill = "片手剣"}) == nil, "サベッジブレードは分けない")

local ls = env.sets.precast.WS["Leaden Salute"]
check(ls and ls.head == "妖蟲の髪飾り+1", "レデンサリュートのセットは、遠隔魔攻の装備を引き継ぐ")
local ae = env.sets.precast.WS["Aeolian Edge"]
check(ae and ae.head == "ニャメヘルム", "イオリアンエッジのセットは、魔攻の装備を引き継ぐ")

if fails == 0 then io.write("OK 遠隔魔攻の分け方 (Lua): 失敗 0 件\n") else io.write("FAILED " .. fails .. "\n"); os.exit(1) end
