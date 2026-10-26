-- 出力した Lua の「オートマトンの技の装備」を、GearSwap を模擬して確認する。
-- 実行: lua5.1.exe tests/pup_lua_test.lua <出力した Lua のパス> <自動 = 1 / 0>
local path, auto = arg[1], arg[2] == "1"
local fails = 0
local function check(cond, msg) if not cond then fails = fails + 1; io.write("NG: " .. msg .. "\n") end end

local worn, restored, handlers, T = {}, 0, {}, 1000
local env = {
    include = function() end, set_language = function() end, send_command = function() end,
    equip = function(t) for k, v in pairs(t) do if type(k) == "string" then worn[k] = v end end end,
    midaction = function() return false end, pet_midaction = function() return false end,
    handle_equipping_gear = function() restored = restored + 1; worn = {} end,
    M = function(a, b)
        if type(a) == "table" then return {description = a.description, value = a[1], current = a[1]} end
        return {value = a, description = b}
    end,
    state = {IdleMode = {options = function() end}},
    sets = {precast = {JA = {}, WS = {}}, midcast = {Pet = {}}, buff = {}, idle = {}, engaged = {}},
    set_combine = function(a, b) local r = {} for k, v in pairs(a) do r[k] = v end for k, v in pairs(b) do r[k] = v end return r end,
    player = {status = "Engaged", equipment = {main = "ヴェリタス"}},
    pet = {isvalid = true, status = "Engaged", tp = 0, attachments = {["ストロボII"] = true}},
    buffactive = {},
    os = {time = function() return T end, clock = os.clock},
    math = math,
    windower = {raw_register_event = function(ev, fn) handlers[ev] = fn end,
                ffxi = {get_mob_by_target = function() return {id = 99} end}},
    pairs = pairs, ipairs = ipairs, string = string, table = table, tostring = tostring, tonumber = tonumber, type = type,
}
setmetatable(env, {__index = _G})
local chunk = assert(loadfile(path))
setfenv(chunk, env)
chunk()
env.user_setup()
env.init_gear_sets()

-- 反応する着替え: 技が出たとき
local ev = {handled = false}
env.job_pet_midcast({english = "Bone Crusher", skillchain_a = "Fragmentation"}, {}, nil, ev)
check(worn.head == "WSの頭" and ev.handled, "オートマトンの WS で、WS の装備を着る")
worn, ev = {}, {handled = false}
env.job_pet_midcast({english = "Provoke"}, {}, nil, ev)
check(worn.head == "敵対心の頭" and ev.handled, "ストロボ (Provoke) で、敵対心の装備を着る")
worn, ev = {}, {handled = false}
env.job_pet_midcast({english = "Flashbulb"}, {}, nil, ev)
check(worn.head == "敵対心の頭", "フラッシュバルブで、敵対心の装備を着る")
worn, ev = {}, {handled = false}
env.job_pet_midcast({english = "Cure", skillchain_a = ""}, {}, nil, ev)
check(worn.head == nil and not ev.handled, "それ以外の技 (魔法など) は、Mote の普段の処理に任せる")

-- メインの持ち替え: シュコアトルに持ち替え、終わったら元の武器に戻す。乾坤圏なら替えない
env.player.equipment = {main = "ヴェリタス"}
worn = {}
env.job_pet_midcast({english = "Bone Crusher", skillchain_a = "Fragmentation"}, {}, nil, {handled = false})
check(worn.main == "シュコアトル", "WS で、メインをシュコアトルに持ち替える")
env.player.equipment.main = "シュコアトル"
worn = {}
env.job_pet_aftercast({english = "Bone Crusher"}, {}, nil, {})
check(worn.main == "ヴェリタス", "WS が終わったら、元の武器 (ヴェリタス) に戻す")
env.player.equipment.main = "乾坤圏"
worn = {}
env.job_pet_midcast({english = "Bone Crusher", skillchain_a = "Fragmentation"}, {}, nil, {handled = false})
check(worn.main == nil and worn.head == "WSの頭", "乾坤圏のときは、メインを替えない (ほかの部位は着る)")
worn = {}
env.job_pet_aftercast({english = "Bone Crusher"}, {}, nil, {})
check(worn.main == nil, "乾坤圏のときは、終わっても武器を替えない")
env.player.equipment.main = "ヴェリタス"

local function tick()
    worn = {}
    env.job_self_command({"pet_tick"}, {})
end

if auto then
    check(env.state.PetAutoGear and env.state.PetAutoGear.value == true, "自動の事前着替えの切り替えがある (オン)")
    check(handlers.prerender and handlers.action, "1 秒ごとの処理と、技の検出を登録する")
    -- 火のマニューバ中・ストロボII 付き・まだ一度も出ていない → 敵対心の装備を先に着る
    env.buffactive[300] = true
    tick()
    check(worn.head == "敵対心の頭", "火のマニューバ中は、ストロボの前に敵対心の装備を先に着る")
    -- ストロボが出た → 再使用 30 秒のあいだは着ない。TP 930 以上なら WS の装備
    handlers.action({category = 11, param = 1945, actor_id = 99})
    env.pet.tp = 950
    T = T + 1
    tick()
    check(worn.head == "WSの頭", "ストロボのあとは、TP 930 以上で WS の装備を先に着る")
    -- 本体が行動して Mote が戦闘中の装備に戻しても、次の 1 秒で着直す
    T = T + 1
    tick()
    check(worn.head == "WSの頭", "出そうなあいだは、毎回着直す")
    -- TP が下がった (技が出た) → 普段の装備に戻す
    env.pet.tp = 0
    restored = 0
    T = T + 1
    tick()
    check(restored == 1, "出そうでなくなったら、普段の装備に戻す")
    -- 再使用の 2 秒前 (ストロボから 28 秒) → また敵対心の装備
    T = T + 26
    tick()
    check(worn.head == "敵対心の頭", "ストロボの再使用の 2 秒前に、敵対心の装備を先に着る")
    -- トグルでオフにすると、何もしない
    env.state.PetAutoGear.value = false
    T = T + 1
    tick()
    check(worn.head == nil, "//gs c toggle PetAutoGear でオフにすると、先に着ない")
else
    check(env.state.PetAutoGear == nil and handlers.prerender == nil, "チェックが無ければ、事前着替えの仕組みを出さない")
end

if fails == 0 then io.write("OK オートマトンの技の装備 (Lua): 失敗 0 件\n") else io.write("FAILED " .. fails .. "\n"); os.exit(1) end
