-- 出力した Lua の「メリット特性の装備 (sets.merit)」の動きを、GearSwap を模擬して確認する。
-- 実行: lua5.1.exe tests/merit_lua_test.lua <出力した Lua のパス>
local path = arg[1]
local fails = 0
local function check(cond, msg) if not cond then fails = fails + 1; io.write("NG: " .. msg .. "\n") end end

local env = {
    include = function() end, set_language = function() end, send_command = function() end,
    M = function(t, d)
        if type(t) ~= "table" then return {value = t, description = d} end     -- M(false, '名前') の切り替え
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

local base = {head = "ふつうの頭", hands = "ふつうの手", body = "ふつうの胴"}
check(env.state.MeritGear and env.state.MeritGear.value == "Off", "MeritGear の既定は Off")

-- Off: ペットがいても重ねない
env.pet.isvalid = true
local s = env.customize_idle_set(base)
check(s.head == "ふつうの頭" and s.hands == "ふつうの手", "Off のときは重ねない")

-- On + ペットあり: 頭と手が替わる・胴はそのまま
env.state.MeritGear.value = "On"
s = env.customize_idle_set(base)
check(s.head ~= "ふつうの頭" and s.hands ~= "ふつうの手" and s.body == "ふつうの胴", "On でペットがいれば、頭と手を重ねる")
s = env.customize_melee_set(base)
check(s.head ~= "ふつうの頭", "戦闘中の装備にも重ねる")

-- On でもペットがいなければ重ねない
env.pet.isvalid = false
s = env.customize_idle_set(base)
check(s.head == "ふつうの頭", "ペットがいなければ重ねない")

if fails == 0 then io.write("OK メリット特性の装備 (Lua): 失敗 0 件\n") else io.write("FAILED " .. fails .. "\n"); os.exit(1) end
