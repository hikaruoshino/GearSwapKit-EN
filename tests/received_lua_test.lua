-- Simulates GearSwap and Windower to check the generated Lua's "received-buff gear" (feeds in action packets).
-- Run: lua5.1.exe tests/received_lua_test.lua <path to generated Lua>   (a Lua with received Phalanx and received Protect registered)
local path = arg[1]
local fails = 0
local function check(cond, msg) if not cond then fails = fails + 1; io.write("NG: " .. msg .. "\n") end end

local ME, PALLY, STRANGER = 100, 200, 300
local sent, equipped, handler, clock, busy = {}, {}, nil, 0, false
local env = {
    include = function() end, set_language = function() end,
    send_command = function(c) sent[#sent + 1] = c end,
    equip = function(t) equipped[#equipped + 1] = t end,
    midaction = function() return busy end,
    M = function(t) return {description = t.description, value = t[1], current = t[1]} end,
    state = {IdleMode = {options = function() end}},
    sets = {precast = {JA = {}}, midcast = {}, buff = {}, idle = {}, engaged = {}},
    windower = {
        raw_register_event = function(name, fn) if name == "action" then handler = fn end end,
        ffxi = {
            get_player = function() return {id = ME} end,
            get_mob_by_id = function(id) return {id = id, in_party = (id == PALLY)} end,
        },
    },
    coroutine = {schedule = function() end},
    os = {clock = function() return clock end},
    pairs = pairs, ipairs = ipairs, string = string, table = table, tostring = tostring,
}
setmetatable(env, {__index = _G})
local chunk = assert(loadfile(path))
setfenv(chunk, env)
chunk()
env.user_setup()
env.init_gear_sets()
if env.after_gear_sets then env.after_gear_sets() end   -- Same order as GearSwap (after init_gear_sets inside get_sets)
check(handler ~= nil, "action のイベントを登録する")

local function cast_begin(actor, target, spell)
    handler({actor_id = actor, category = 8, param = 24931, targets = {{id = target, actions = {{param = spell}}}}})
end
local function land(actor) handler({actor_id = actor, category = 4, param = 0, targets = {}}) end
local function last() return sent[#sent] end

-- Melee, ranged, etc. are dropped early without even calling get_player (actions arrive for everyone)
local calls = 0
local orig_gp = env.windower.ffxi.get_player
env.windower.ffxi.get_player = function() calls = calls + 1; return orig_gp() end
for _, cat in ipairs{1, 2, 3, 5, 7, 11, 12, 13} do
    handler({actor_id = STRANGER, category = cat, param = 0, targets = {}})
end
check(calls == 0 and #sent == 0, "見ないカテゴリは、get_player を呼ばずに捨てる")
handler({actor_id = STRANGER, category = 8, param = 0, targets = {}})
check(calls == 1, "見るカテゴリ (8) は、先へ進む")
env.windower.ffxi.get_player = orig_gp

-- Someone else casts Phalanx on me -> wear it -> restore on landing
cast_begin(PALLY, ME, 106)
check(last() == "gs equip sets.midcast.IncreasedPhalanx", "自分へのファランクスで、被ファランクスを着る")
land(PALLY)
check(last() == "gs c update", "着弾で、元の装備に戻す")

-- Ignore Phalanx cast on other people
sent = {}
cast_begin(PALLY, STRANGER, 106)
check(#sent == 0, "ほかの人へのファランクスでは着ない")

-- Protectra from a party member (target is the caster) -> wear it. Not for Protectra from outside the party
cast_begin(PALLY, PALLY, 125)
check(last() == "gs equip sets.midcast.IncreasedProtect", "パーティーの人のプロテアで、被プロテスを着る")
land(PALLY)
sent = {}
cast_begin(STRANGER, STRANGER, 125)
check(#sent == 0, "パーティー外の人のプロテアでは着ない")

-- Phalanx after Accession (target is the caster, AoE) -> wear it
handler({actor_id = PALLY, category = 6, param = 218, targets = {}})
cast_begin(PALLY, PALLY, 106)
check(last() == "gs equip sets.midcast.IncreasedPhalanx", "女神降臨の章のあとの範囲ファランクスで着る")
-- Restore on interrupt
handler({actor_id = PALLY, category = 8, param = 28787, targets = {}})
check(last() == "gs c update", "詠唱の中断で戻す")

-- Ignore received Shell when it isn't registered
sent = {}
cast_begin(PALLY, ME, 48)
check(#sent == 0, "登録していない被シェルでは着ない")

-- Hands off while I'm acting
busy = true
sent = {}
cast_begin(PALLY, ME, 106)
check(#sent == 0, "自分の行動中は着替えない (行動の後に任せる)")
busy = false

-- Casting on myself (midcast)
equipped = {}
env.job_post_midcast({id = 43, target = {type = "SELF"}}, {}, nil, {})
check(#equipped == 1, "自分で自分にプロテスを唱えるとき、詠唱中に被プロテスを着る")
equipped = {}
env.job_post_midcast({id = 43, target = {type = "PLAYER"}}, {}, nil, {})
check(#equipped == 0, "ほかの人に唱えるときは着ない")

if fails == 0 then io.write("OK 被強化の装備 (Lua): 失敗 0 件\n") else io.write("FAILED " .. fails .. "\n"); os.exit(1) end
