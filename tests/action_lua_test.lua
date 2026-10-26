-- 出力した Lua の「強化が効いている間に WS・遠隔攻撃をするときの装備」の動きを、GearSwap を模擬して確認する。
-- 実行: lua5.1.exe tests/action_lua_test.lua <出力した Lua のパス> <バフ番号> <WeaponSkill / Ranged Attack>
local path, bid, kind = arg[1], tonumber(arg[2]), arg[3]
local fails = 0
local function check(cond, msg) if not cond then fails = fails + 1; io.write("NG: " .. msg .. "\n") end end

local equipped = {}
local env = {
    include = function() end, set_language = function() end, send_command = function() end,
    M = function(t) return {description = t.description, value = t[1], current = t[1]} end,
    state = {IdleMode = {options = function() end}},
    sets = {precast = {JA = {}}, buff = {}, idle = {}, engaged = {}},
    player = {status = "Idle"},
    buffactive = {},
    equip = function(t) equipped[#equipped + 1] = t end,
    handle_equipping_gear = function() end,
    set_combine = function(a, b) local r = {} for k, v in pairs(a) do r[k] = v end for k, v in pairs(b) do r[k] = v end return r end,
    pairs = pairs, ipairs = ipairs, string = string, table = table, tostring = tostring,
}
setmetatable(env, {__index = _G})
local chunk = assert(loadfile(path))
setfenv(chunk, env)
chunk()
env.user_setup()
env.init_gear_sets()

local ws = {action_type = "Ability", type = "WeaponSkill"}
local ra = {action_type = "Ranged Attack", type = "Misc"}
local magic = {action_type = "Magic", type = "WhiteMagic"}
local ja = {action_type = "Ability", type = "JobAbility"}
local target = (kind == "WeaponSkill") and ws or ra
local phase = (kind == "WeaponSkill") and "job_post_precast" or "job_post_midcast"

env[phase](target, {}, nil, {})
check(#equipped == 0, "強化が無いときは着ない")

env.buffactive[bid] = 1
env[phase](target, {}, nil, {})
check(#equipped == 1, kind .. " のときに着る")
equipped = {}
for _, other in ipairs({magic, ja, (kind == "WeaponSkill") and ra or ws}) do
    env[phase](other, {}, nil, {})
end
check(#equipped == 0, "ほかの行動 (魔法・アビリティ・別の攻撃) では着ない")

if fails == 0 then io.write("OK " .. kind .. " のときの装備 (Lua): 失敗 0 件\n") else io.write("FAILED " .. fails .. "\n"); os.exit(1) end
