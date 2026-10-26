-- 出力した Lua の「被強化の装備」の動きを、GearSwap と Windower を模擬して確認する (action パケットを流す)。
-- 実行: lua5.1.exe tests/received_lua_test.lua <出力した Lua のパス>   (被ファランクス・被プロテスを登録した Lua)
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
        register_event = function(name, fn) if name == "action" then handler = fn end end,
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
check(handler ~= nil, "action のイベントを登録する")

local function cast_begin(actor, target, spell)
    handler({actor_id = actor, category = 8, param = 24931, targets = {{id = target, actions = {{param = spell}}}}})
end
local function land(actor) handler({actor_id = actor, category = 4, param = 0, targets = {}}) end
local function last() return sent[#sent] end

-- ほかの人が自分にファランクス → 着る → 着弾で戻す
cast_begin(PALLY, ME, 106)
check(last() == "gs equip sets.midcast.IncreasedPhalanx", "自分へのファランクスで、被ファランクスを着る")
land(PALLY)
check(last() == "gs c update", "着弾で、元の装備に戻す")

-- ほかの人へのファランクスには反応しない
sent = {}
cast_begin(PALLY, STRANGER, 106)
check(#sent == 0, "ほかの人へのファランクスでは着ない")

-- パーティーの人のプロテア (対象は唱えた本人) → 着る。パーティー外の人のプロテアは着ない
cast_begin(PALLY, PALLY, 125)
check(last() == "gs equip sets.midcast.IncreasedProtect", "パーティーの人のプロテアで、被プロテスを着る")
land(PALLY)
sent = {}
cast_begin(STRANGER, STRANGER, 125)
check(#sent == 0, "パーティー外の人のプロテアでは着ない")

-- 女神降臨の章のあとのファランクス (対象は唱えた本人・範囲) → 着る
handler({actor_id = PALLY, category = 6, param = 218, targets = {}})
cast_begin(PALLY, PALLY, 106)
check(last() == "gs equip sets.midcast.IncreasedPhalanx", "女神降臨の章のあとの範囲ファランクスで着る")
-- 中断で戻す
handler({actor_id = PALLY, category = 8, param = 28787, targets = {}})
check(last() == "gs c update", "詠唱の中断で戻す")

-- 登録していない被シェルは反応しない
sent = {}
cast_begin(PALLY, ME, 48)
check(#sent == 0, "登録していない被シェルでは着ない")

-- 自分の行動中は触らない
busy = true
sent = {}
cast_begin(PALLY, ME, 106)
check(#sent == 0, "自分の行動中は着替えない (行動の後に任せる)")
busy = false

-- 自分で自分に唱えるとき (詠唱中)
equipped = {}
env.job_post_midcast({id = 43, target = {type = "SELF"}}, {}, nil, {})
check(#equipped == 1, "自分で自分にプロテスを唱えるとき、詠唱中に被プロテスを着る")
equipped = {}
env.job_post_midcast({id = 43, target = {type = "PLAYER"}}, {}, nil, {})
check(#equipped == 0, "ほかの人に唱えるときは着ない")

if fails == 0 then io.write("OK 被強化の装備 (Lua): 失敗 0 件\n") else io.write("FAILED " .. fails .. "\n"); os.exit(1) end
