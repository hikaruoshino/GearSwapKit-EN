-- Simulates GearSwap to check the generated Lua's "gear worn for as long as a buff lasts (sets.buff)".
-- Run: lua5.1.exe tests/buff_lua_test.lua <path to generated Lua>
local path = arg[1]
local fails = 0
local function check(cond, msg) if not cond then fails = fails + 1; io.write("NG: " .. msg .. "\n") end end

local handled = 0
local env = {
    include = function() end, set_language = function() end, send_command = function() end,
    M = function(t) return {description = t.description, current = t[1]} end,
    state = {IdleMode = {options = function() end}},
    sets = {precast = {JA = {}}, buff = {}},   -- Containers Mote-Include creates (Mote doesn't create sets.idle)
    player = {status = "Idle"},
    buffactive = {},
    handle_equipping_gear = function() handled = handled + 1 end,
    set_combine = function(a, b)   -- Stand-in for GearSwap's set_combine: merge, with the later set overriding
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
env.init_gear_sets()
if env.after_gear_sets then env.after_gear_sets() end   -- Same order as GearSwap (after init_gear_sets inside get_sets)
check(type(env.sets.idle) == "table" and type(env.sets.engaged) == "table", "待機・戦闘中のセットが無くても、空のセットができる (Mote が customize_idle_set を呼べる)")

local base = {head = "ふつうの頭", body = "ふつうの胴"}

-- Without the buff: unchanged
local s = env.customize_idle_set(base)
check(s.head == "ふつうの頭", "強化が無いときは、待機の装備のまま")

-- With the buff (Avatar's Favor = ID 431): only the head of the idle/engaged gear changes
env.buffactive[431] = 1
s = env.customize_idle_set(base)
check(s.head ~= "ふつうの頭" and s.body == "ふつうの胴", "強化が付いている間は、待機の頭が強化の装備になる (ほかはそのまま)")
s = env.customize_melee_set(base)
check(s.head ~= "ふつうの頭" and s.body == "ふつうの胴", "戦闘中の装備にも重なる")

-- Re-equip when the buff wears on/off (name may be English or Japanese, case-insensitive)
handled = 0
env.job_buff_change("Avatar's Favor", true, {})
env.job_buff_change("神獣の加護", false, {})
env.job_buff_change("avatar's favor", true, {})
check(handled == 3, "英語名・日本語名・小文字のどれでも、着替え直す (実際 " .. handled .. " 回)")
handled = 0
env.job_buff_change("ヘイスト", true, {})
check(handled == 0, "関係ない強化では、着替え直さない")

if fails == 0 then io.write("OK 効果中の装備 (Lua): 失敗 0 件\n") else io.write("FAILED " .. fails .. "\n"); os.exit(1) end
