-- Simulates GearSwap to check the generated Lua's "merit trait gear (sets.merit)".
-- Run: lua5.1.exe tests/merit_lua_test.lua <path to generated Lua>
local path = arg[1]
local fails = 0
local function check(cond, msg) if not cond then fails = fails + 1; io.write("NG: " .. msg .. "\n") end end

local env = {
    include = function() end, set_language = function() end, send_command = function() end,
    M = function(t, d)
        if type(t) ~= "table" then return {value = t, description = d} end     -- toggle created by M(false, 'name')
        return {description = t.description, value = t[1], current = t[1]}
    end,
    state = {IdleMode = {options = function() end}},
    sets = {precast = {JA = {}}, buff = {}, idle = {}},
    player = {status = "Idle"},
    pet = {isvalid = false},
    buffactive = {},
    handle_equipping_gear = function() end,
    set_combine = function(a, b)
        local r = {}
        for k, v in pairs(a) do r[k] = v end
        for k, v in pairs(b) do r[k] = v end
        return r
    end,
    pairs = pairs, ipairs = ipairs, string = string, table = table, tostring = tostring,
}
setmetatable(env, {__index = _G})
local chunk = assert(loadfile(path))
setfenv(chunk, env)
chunk()
env.user_setup()
env.init_gear_sets()
if env.after_gear_sets then env.after_gear_sets() end   -- Same order as GearSwap (after init_gear_sets inside get_sets)

local base = {head = "ふつうの頭", hands = "ふつうの手", body = "ふつうの胴"}
check(env.state.MeritGear and env.state.MeritGear.value == "Off", "MeritGear の既定は Off")

-- Off: don't layer it on, even with a pet out
env.pet.isvalid = true
local s = env.customize_idle_set(base)
check(s.head == "ふつうの頭" and s.hands == "ふつうの手", "Off のときは重ねない")

-- On + pet out: head and hands change, body stays the same
env.state.MeritGear.value = "On"
s = env.customize_idle_set(base)
check(s.head ~= "ふつうの頭" and s.hands ~= "ふつうの手" and s.body == "ふつうの胴", "On でペットがいれば、頭と手を重ねる")
s = env.customize_melee_set(base)
check(s.head ~= "ふつうの頭", "戦闘中の装備にも重ねる")

-- Even when On, don't layer it on without a pet
env.pet.isvalid = false
s = env.customize_idle_set(base)
check(s.head == "ふつうの頭", "ペットがいなければ重ねない")

if fails == 0 then io.write("OK メリット特性の装備 (Lua): 失敗 0 件\n") else io.write("FAILED " .. fails .. "\n"); os.exit(1) end
