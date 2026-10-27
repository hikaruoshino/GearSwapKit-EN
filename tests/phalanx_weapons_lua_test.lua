-- 魔法のファランクス (剣・盾入り) の動きを、GearSwap を模擬して確認する。
-- 唱える前の武器を覚えて、唱えたあとにその武器に戻すこと。ほかの魔法では何もしないこと。
-- 実行: lua5.1.exe tests/phalanx_weapons_lua_test.lua <出力した Lua のパス>
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

-- ほかの魔法では、武器を覚えない
env.job_post_midcast({english = 'Cure IV', action_type = 'Magic', target = {type = 'SELF'}}, {}, nil, {})
check(env.phalanx_weapons == nil, "ほかの魔法では、武器を覚えない")

-- ファランクス: 唱える前の武器を覚える → 唱えたあとに戻す
env.job_post_midcast({english = 'Phalanx', action_type = 'Magic', target = {type = 'SELF'}}, {}, nil, {})
check(env.phalanx_weapons and env.phalanx_weapons.main == '元の剣' and env.phalanx_weapons.sub == '元の盾', "唱える前の剣と盾を覚える")
equipped = {}
env.job_post_aftercast({english = 'Phalanx', target = {type = 'SELF'}}, {}, nil, {})
local w = equipped[#equipped]
check(w and w.main == '元の剣' and w.sub == '元の盾', "唱えたあと、元の剣と盾に戻す")
check(env.phalanx_weapons == nil, "戻したら、覚えた武器を消す")

io.write(string.format("%s 魔法のファランクスの武器 (Lua): 失敗 %d 件\n", fails == 0 and "OK" or "NG", fails))
os.exit(fails == 0 and 0 or 1)
