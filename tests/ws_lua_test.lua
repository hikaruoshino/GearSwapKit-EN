-- 出力した Lua の「WS の分け方 (job_get_spell_map)」を、GearSwap を模擬して確認する。
-- 実行: lua5.1.exe tests/ws_lua_test.lua <出力した Lua のパス>   (魔攻と遠隔の両方のセットがある Lua)
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

local map = env.job_get_spell_map
check(map({type = "WeaponSkill", english = "Leaden Salute", skill = "射撃"}) == "Magic", "レデンサリュート (射撃・魔法属性) は Magic")
check(map({type = "WeaponSkill", english = "Sanguine Blade", skill = "片手剣"}) == "Magic", "サンギンブレードは Magic")
check(map({type = "WeaponSkill", english = "Last Stand", skill = "射撃"}) == "Range", "ラストスタンド (日本語のスキル名) は Range")
check(map({type = "WeaponSkill", english = "Jishnu's Radiance", skill = "Archery"}) == "Range", "ジシュヌの光輝 (英語のスキル名) は Range")
check(map({type = "WeaponSkill", english = "Savage Blade", skill = "片手剣"}) == nil, "サベッジブレードは分けない (共通の WS)")
check(map({type = "BlackMagic", english = "Fire", skill = "精霊魔法"}) == nil, "WS でなければ分けない")

-- 技ごとのセットが、元のセットを引き継いでいる
local ls = env.sets.precast.WS["Leaden Salute"]
check(ls and ls.neck == env.sets.precast.WS.Magic.neck, "レデンサリュートのセットは、魔攻の WS の装備を引き継ぐ")

if fails == 0 then io.write("OK WS の分け方 (Lua): 失敗 0 件\n") else io.write("FAILED " .. fails .. "\n"); os.exit(1) end
