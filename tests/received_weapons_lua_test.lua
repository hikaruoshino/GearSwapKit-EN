-- 武器 (剣・盾) の入った被ファランクスの動きを、GearSwap と Windower を模擬して確認する。
-- 着る前の武器を覚えて、届いたら (または自分で唱えたあとに) その武器に戻すこと。
-- 実行: lua5.1.exe tests/received_weapons_lua_test.lua <出力した Lua のパス>   (武器入りの被ファランクスを登録した Lua)
local path = arg[1]
local fails = 0
local function check(cond, msg) if not cond then fails = fails + 1; io.write("NG: " .. msg .. "\n") end end

local ME, PALLY = 100, 200
local sent, equipped, handler, updates = {}, {}, nil, 0
local env = {
    include = function() end, set_language = function() end,
    send_command = function(c) sent[#sent + 1] = c end,
    equip = function(t) equipped[#equipped + 1] = t end,
    midaction = function() return false end,
    handle_equipping_gear = function() updates = updates + 1 end,
    M = function(t) return {description = t.description, value = t[1], current = t[1]} end,
    state = {IdleMode = {options = function() end}},
    sets = {precast = {JA = {}}, midcast = {}, buff = {}, idle = {}, engaged = {}},
    player = {status = 'Idle', equipment = {main = '元の剣', sub = '元の盾', range = 'empty'}},
    windower = {
        raw_register_event = function(name, fn) if name == "action" then handler = fn end end,
        ffxi = {
            get_player = function() return {id = ME} end,
            get_mob_by_id = function(id) return {id = id, in_party = (id == PALLY)} end,
        },
    },
    coroutine = {schedule = function() end},
    os = {clock = function() return 0 end},
    pairs = pairs, ipairs = ipairs, string = string, table = table, tostring = tostring,
}
setmetatable(env, {__index = _G})
local chunk = assert(loadfile(path))
setfenv(chunk, env)
chunk()
env.user_setup()
env.init_gear_sets()
if env.after_gear_sets then env.after_gear_sets() end
local set = env.sets.midcast.IncreasedPhalanx
check(set and set.main == 'サクパタソード' and set.sub == 'プリュウェン', "被ファランクスのセットに剣と盾が入る")

local function last() return sent[#sent] end
local function cmd(name) local ev = {}; env.job_self_command({name}, ev); return ev.handled end

-- ほかの人 (コルモルなど) が自分にファランクス → 武器を覚えてから着る → 届いたら武器を着直す
handler({actor_id = PALLY, category = 8, param = 24931, targets = {{id = ME, actions = {{param = 107}}}}})
check(last() == "gs c received_save; gs equip sets.midcast.IncreasedPhalanx", "唱え始めで、武器を覚えてから着る (実際 " .. tostring(last()) .. ")")
check(cmd('received_save'), "received_save を受け付ける")
check(env.received_weapons and env.received_weapons.main == '元の剣' and env.received_weapons.sub == '元の盾', "着る前の武器を覚える")
env.player.equipment.main, env.player.equipment.sub = 'サクパタソード', 'プリュウェン'
check(cmd('received_save') and env.received_weapons.main == '元の剣', "2 回目の received_save では、覚えた武器を上書きしない")
handler({actor_id = PALLY, category = 4, param = 107, targets = {}})
check(last() == "gs c received_restore", "届いたら、武器を着直すコマンドを送る (実際 " .. tostring(last()) .. ")")
local before = updates
check(cmd('received_restore'), "received_restore を受け付ける")
local w = equipped[#equipped]
check(w and w.main == '元の剣' and w.sub == '元の盾', "覚えていた武器を着直す")
check(updates == before + 1, "待機・戦闘中の装備にも着替え直す")
check(env.received_weapons == nil, "着直したら、覚えた武器を消す")

-- 自分で自分にファランクス → 詠唱中に着る → 唱えたあとに武器を戻す
env.player.equipment.main, env.player.equipment.sub = '元の剣', '元の盾'
equipped = {}
env.job_post_midcast({id = 106, target = {type = 'SELF'}, action_type = 'Magic'}, {}, nil, {})
check(equipped[#equipped] == set, "自分に唱えるとき、詠唱中に被ファランクスを着る")
check(env.received_weapons and env.received_weapons.main == '元の剣', "自分に唱えるときも、着る前の武器を覚える")
env.job_post_aftercast({id = 106, target = {type = 'SELF'}}, {}, nil, {})
w = equipped[#equipped]
check(w and w.main == '元の剣' and w.sub == '元の盾' and env.received_weapons == nil, "唱えたあと、着る前の武器に戻す")

io.write(string.format("%s 武器入りの被ファランクス (Lua): 失敗 %d 件\n", fails == 0 and "OK" or "NG", fails))
os.exit(fails == 0 and 0 or 1)
