-- Simulates GearSwap to check the generated Lua's "gear for casting while a buff is active" (Scholar stratagems, etc.).
-- Run: lua5.1.exe tests/cast_lua_test.lua <path to generated Lua> <precast buff ID> <midcast buff ID>
local path, pre_id, mid_id = arg[1], tonumber(arg[2]), tonumber(arg[3])
local fails = 0
local function check(cond, msg) if not cond then fails = fails + 1; io.write("NG: " .. msg .. "\n") end end

local equipped = {}
local env = {
    include = function() end, set_language = function() end, send_command = function() end,
    M = function(t) return {description = t.description, value = t[1], current = t[1]} end,
    state = {IdleMode = {options = function() end}},
    sets = {precast = {JA = {}}, buff = {}, idle = {}},
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
if env.after_gear_sets then env.after_gear_sets() end   -- Same order as GearSwap (after init_gear_sets inside get_sets)

local magic = {action_type = "Magic"}
local ability = {action_type = "Ability"}

-- No buff: nothing is equipped
env.job_post_precast(magic, {}, nil, {})
env.job_post_midcast(magic, {}, nil, {})
check(#equipped == 0, "強化が無いときは着ない")

-- Only a buff worn at both precast and midcast is active (e.g. Celerity: affects both casting time and recast)
env.buffactive[pre_id] = 1
env.job_post_precast(magic, {}, nil, {})
check(#equipped == 1 and equipped[1].feet ~= nil, "詠唱を始めるときに、足の装備を着る")
equipped = {}
env.job_post_midcast(magic, {}, nil, {})
check(#equipped == 1 and equipped[1].feet ~= nil, "詠唱中にも、足の装備を着る")
equipped = {}
env.job_post_precast(ability, {}, nil, {})
check(#equipped == 0, "魔法でなければ (アビリティ) 着ない")
env.buffactive[pre_id] = nil

-- A midcast buff is active (e.g. Perpetuance)
env.buffactive[mid_id] = 1
env.job_post_midcast(magic, {}, nil, {})
check(#equipped == 1, "詠唱中に、章の装備を着る")
equipped = {}
env.job_post_precast(magic, {}, nil, {})
check(#equipped == 0, "詠唱中用の装備は、詠唱を始めるときには着ない")

if fails == 0 then io.write("OK 魔法を唱えるときの装備 (Lua): 失敗 0 件\n") else io.write("FAILED " .. fails .. "\n"); os.exit(1) end
