-- Simulates GearSwap to check Phalanx (with sword and shield in the set).
-- It should remember the weapons held before casting and switch back to them afterward, and do nothing for other spells.
-- Run: lua5.1.exe tests/phalanx_weapons_lua_test.lua <path to generated Lua>
local path = arg[1]
local fails = 0
local function check(cond, msg) if not cond then fails = fails + 1; io.write("NG: " .. msg .. "\n") end end

local equipped = {}
local env = {
    include = function() end, set_language = function() end,
    send_command = function() end,
    equip = function(t) equipped[#equipped + 1] = t end,
    midaction = function() return false end,
    get_midcast_set = function() return {} end,
    handle_equipping_gear = function() end,
    M = function(t) return {description = t.description, value = t[1], current = t[1]} end,
    state = {IdleMode = {options = function() end}},
    sets = {precast = {JA = {}}, midcast = {}, buff = {}, idle = {}, engaged = {}},
    player = {status = 'Idle', equipment = {main = '元の剣', sub = '元の盾', range = 'empty'}},
    windower = {raw_register_event = function() end, register_event = function() end, ffxi = {get_player = function() return {id = 1} end}},
    coroutine = {schedule = function() end},
    pairs = pairs, ipairs = ipairs, string = string, table = table, tostring = tostring,
}
setmetatable(env, {__index = _G})
local chunk = assert(loadfile(path))
setfenv(chunk, env)
chunk()
env.user_setup()
env.init_gear_sets()
if env.after_gear_sets then env.after_gear_sets() end
local set = env.sets.midcast['Phalanx']
check(set and set.main == 'サクパタソード' and set.sub == 'プリュウェン', "魔法のファランクスのセットに剣と盾が入る")

-- Other spells don't remember the weapons
env.job_post_midcast({english = 'Cure IV', action_type = 'Magic', target = {type = 'SELF'}}, {}, nil, {})
check(env.phalanx_weapons == nil, "ほかの魔法では、武器を覚えない")

-- Phalanx: remember the weapons before casting -> restore them afterward
env.job_post_midcast({english = 'Phalanx', action_type = 'Magic', target = {type = 'SELF'}}, {}, nil, {})
check(env.phalanx_weapons and env.phalanx_weapons.main == '元の剣' and env.phalanx_weapons.sub == '元の盾', "唱える前の剣と盾を覚える")
equipped = {}
env.job_post_aftercast({english = 'Phalanx', target = {type = 'SELF'}}, {}, nil, {})
local w = equipped[#equipped]
check(w and w.main == '元の剣' and w.sub == '元の盾', "唱えたあと、元の剣と盾に戻す")
check(env.phalanx_weapons == nil, "戻したら、覚えた武器を消す")

-- Phalanx II (RDM, self or others): Mote casts it with the Phalanx set, so it also remembers and restores the weapons
env.player.equipment.main, env.player.equipment.sub = '元の剣', '元の盾'
env.job_post_midcast({english = 'Phalanx II', action_type = 'Magic', target = {type = 'PLAYER'}}, {}, nil, {})
check(env.phalanx_weapons and env.phalanx_weapons.main == '元の剣', "ファランクスII でも、唱える前の剣と盾を覚える")
equipped = {}
env.job_post_aftercast({english = 'Phalanx II', target = {type = 'PLAYER'}}, {}, nil, {})
w = equipped[#equipped]
check(w and w.main == '元の剣' and w.sub == '元の盾' and env.phalanx_weapons == nil, "ファランクスII を唱えたあとも、元の剣と盾に戻す")

io.write(string.format("%s 魔法のファランクスの武器 (Lua): 失敗 %d 件\n", fails == 0 and "OK" or "NG", fails))
os.exit(fails == 0 and 0 or 1)
