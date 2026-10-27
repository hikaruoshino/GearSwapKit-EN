-- 出力した Lua の「強化が効いている間に魔法を唱えるときの装備」(学者の章など) の動きを、GearSwap を模擬して確認する。
-- 実行: lua5.1.exe tests/cast_lua_test.lua <出力した Lua のパス> <precast のバフ番号> <midcast のバフ番号>
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
if env.after_gear_sets then env.after_gear_sets() end   -- GearSwap と同じ順 (get_sets の中で init_gear_sets のあと)

local magic = {action_type = "Magic"}
local ability = {action_type = "Ability"}

-- 強化が無いとき: 何も着ない
env.job_post_precast(magic, {}, nil, {})
env.job_post_midcast(magic, {}, nil, {})
check(#equipped == 0, "強化が無いときは着ない")

-- 詠唱開始と詠唱中の両方で着る強化 (電光石火の章など: 詠唱時間と再詠唱時間の両方に効く) だけが効いている
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

-- 詠唱中用の強化 (令狸執鼠の章など) が効いている
env.buffactive[mid_id] = 1
env.job_post_midcast(magic, {}, nil, {})
check(#equipped == 1, "詠唱中に、章の装備を着る")
equipped = {}
env.job_post_precast(magic, {}, nil, {})
check(#equipped == 0, "詠唱中用の装備は、詠唱を始めるときには着ない")

if fails == 0 then io.write("OK 魔法を唱えるときの装備 (Lua): 失敗 0 件\n") else io.write("FAILED " .. fails .. "\n"); os.exit(1) end
