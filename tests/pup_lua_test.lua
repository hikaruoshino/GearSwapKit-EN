-- Simulates GearSwap to check the generated Lua's "automaton ability gear".
-- Run: lua5.1.exe tests/pup_lua_test.lua <path to generated Lua> <auto = 1 / 0>
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
if env.after_gear_sets then env.after_gear_sets() end   -- Same order as GearSwap (after init_gear_sets inside get_sets)

-- Reactive swaps: when an ability goes off
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

-- Main weapon swap: switch to Xiucoatl, then back to the original weapon when done. Not with Kenkonken
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
    -- Fire maneuver up, Strobe II attached, not used yet -> put on enmity gear in advance
    env.buffactive[300] = true
    tick()
    check(worn.head == "敵対心の頭", "火のマニューバ中は、ストロボの前に敵対心の装備を先に着る")
    -- Strobe used -> don't wear it during the 30 s recast. At TP 930+ use WS gear
    handlers.action({category = 11, param = 1945, actor_id = 99})
    env.pet.tp = 950
    T = T + 1
    tick()
    check(worn.head == "WSの頭", "ストロボのあとは、TP 930 以上で WS の装備を先に着る")
    -- Even if the player acts and Mote puts engaged gear back on, re-equip on the next 1 s tick
    T = T + 1
    tick()
    check(worn.head == "WSの頭", "出そうなあいだは、毎回着直す")
    -- TP dropped (ability used) -> back to normal gear
    env.pet.tp = 0
    restored = 0
    T = T + 1
    tick()
    check(restored == 1, "出そうでなくなったら、普段の装備に戻す")
    -- 2 s before the recast is up (28 s after Strobe) -> enmity gear again
    T = T + 26
    tick()
    check(worn.head == "敵対心の頭", "ストロボの再使用の 2 秒前に、敵対心の装備を先に着る")
    -- Toggled off: do nothing
    env.state.PetAutoGear.value = false
    T = T + 1
    tick()
    check(worn.head == nil, "//gs c toggle PetAutoGear でオフにすると、先に着ない")
else
    check(env.state.PetAutoGear == nil and handlers.prerender == nil, "チェックが無ければ、事前着替えの仕組みを出さない")
end

if fails == 0 then io.write("OK オートマトンの技の装備 (Lua): 失敗 0 件\n") else io.write("FAILED " .. fails .. "\n"); os.exit(1) end
