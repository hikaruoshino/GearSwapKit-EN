-- 出力した Lua の「矢弾の使い分け」を、GearSwap を模擬して確認する。
-- 実行: lua5.1.exe tests/ammo_lua_test.lua <出力した Lua のパス>   (test_ammo.py が作る COR の Lua)
local path = arg[1]
local fails = 0
local function check(cond, msg) if not cond then fails = fails + 1; io.write("NG: " .. msg .. "\n") end end

local worn = {}
local function name_of(item) return type(item) == "table" and item.name or item end
local env = {
    include = function() end, set_language = function() end, send_command = function() end,
    equip = function(t) for k, v in pairs(t) do worn[k] = v end end,
    empty = "empty",
    M = function(t) return {description = t.description, value = t[1], current = t[1]} end,
    state = {IdleMode = {options = function() end}},
    sets = {precast = {JA = {}, WS = {}}, buff = {}, idle = {}, engaged = {}},
    set_combine = function(a, b) local r = {} for k, v in pairs(a) do r[k] = v end for k, v in pairs(b) do r[k] = v end return r end,
    player = {equipment = {}},
    pairs = pairs, ipairs = ipairs, string = string, table = table, tostring = tostring, type = type,
}
setmetatable(env, {__index = _G})
local chunk = assert(loadfile(path))
setfenv(chunk, env)
chunk()
env.user_setup()
env.init_gear_sets()
if env.after_gear_sets then env.after_gear_sets() end   -- GearSwap と同じ順 (get_sets の中で init_gear_sets のあと)

local function act(spell)
    worn = {}
    env.job_post_precast(spell, {}, nil, {})
    local pre = name_of(worn.ammo)
    env.player.equipment.ammo = pre or env.player.equipment.ammo
    worn = {}
    env.job_post_aftercast(spell, {}, nil, {})
    local after = name_of(worn.ammo)
    if after then env.player.equipment.ammo = after end
    return pre, after
end

env.player.equipment.ammo = "クロノブレット"
local pre, after = act({type = "WeaponSkill", english = "Leaden Salute", skill = "射撃"})
check(pre == "ライヴブレット" and after == nil, "レデンサリュートは魔攻の弾・普通の弾なので戻さない")
pre, after = act({type = "WeaponSkill", english = "Last Stand", skill = "射撃"})
check(pre == "クロノブレット", "ラストスタンドは物理の弾")
pre, after = act({type = "WeaponSkill", english = "Savage Blade", skill = "片手剣"})
check(pre == "ホクスボクブレット" and after == "クロノブレット", "サベッジブレードは特殊弾を着て、終わったら物理の弾に戻す")
pre, after = act({type = "WeaponSkill", english = "Requiescat", skill = "片手剣"})
check(pre == nil and after == nil, "選んでいない近接の WS では、矢弾を替えない")
pre, after = act({type = "CorsairShot", english = "Fire Shot", action_type = "Ability"})
check(pre == "アニミキーブレット" and after == "クロノブレット", "クイックドローは専用の弾・終わったら物理の弾に戻す")
pre, after = act({type = "Misc", english = "Ranged", action_type = "Ranged Attack"})
check(pre == "クロノブレット", "遠隔攻撃は物理の弾")

worn = {}
env.job_self_command({"ammo"}, {})
check(name_of(worn.ammo) == "クロノブレット", "//gs c ammo で物理の弾を装備する")
check(env.sets.precast.WS.ammo == nil, "セットには矢弾を入れない")

if fails == 0 then io.write("OK 矢弾の使い分け (Lua): 失敗 0 件\n") else io.write("FAILED " .. fails .. "\n"); os.exit(1) end
