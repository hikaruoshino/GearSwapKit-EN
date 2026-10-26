-- 1.1.0 で足した仕組み (クリティカルの WS・トレジャーハンター・二刀流・モード・青魔法・風水士) を、GearSwap を模擬して確認する。
-- 実行: lua5.1.exe tests/v110_lua_test.lua <出力した Lua のパス> <ジョブ> <サポジョブ>
local path, job, sub = arg[1], arg[2], arg[3]
local fails = 0
local function check(cond, msg) if not cond then fails = fails + 1; io.write("NG: " .. job .. ": " .. msg .. "\n") end end

local worn = {}
local function opts() return {options = function(self, ...) self.list = {...}; self.value = ... end} end
local env = {
    include = function() end, set_language = function() end, send_command = function() end,
    equip = function(t) for k, v in pairs(t) do worn[k] = v end end,
    empty = "empty", buffactive = {}, pet = {isvalid = false},
    M = function(a, b) if type(a) == "table" then return {description = a.description, value = a[1]} end return {value = a, description = b} end,
    state = {IdleMode = opts(), OffenseMode = opts(), HybridMode = opts(), RangedMode = opts(), CastingMode = opts(),
             WeaponskillMode = opts(), DefenseMode = opts()},
    sets = {precast = {JA = {}, WS = {}, RA = {}, FC = {}}, midcast = {RA = {}, Pet = {}}, buff = {}, idle = {}, engaged = {}, defense = {}},
    set_combine = function(a, b) local r = {} for k, v in pairs(a or {}) do r[k] = v end for k, v in pairs(b or {}) do r[k] = v end return r end,
    player = {equipment = {}, sub_job = sub, main_job = job, status = "Engaged"},
    get_midcast_set = function() return {} end, midaction = function() return false end,
    windower = {ffxi = {get_player = function() return {} end}},
    pairs = pairs, ipairs = ipairs, string = string, table = table, tostring = tostring, type = type, tonumber = tonumber, math = math,
}
setmetatable(env, {__index = _G})
local chunk = assert(loadfile(path))
setfenv(chunk, env)
chunk()
env.user_setup()
env.init_gear_sets()
local S = env.sets

local function has(list, v) for _, x in ipairs(list or {}) do if x == v then return true end end return false end

-- モード
check(has(env.state.OffenseMode.list, "Acc") and has(env.state.OffenseMode.list, "SubtleBlow"), "OffenseMode に Acc と SubtleBlow")
if S.idle.Refresh then check(has(env.state.IdleMode.list, "Refresh"), "IdleMode に Refresh") end

-- クリティカルの WS
if env.job_get_spell_map and S.precast.WS.Critical then
    check(env.job_get_spell_map({type = "WeaponSkill", english = "Evisceration", skill = "Dagger"}, nil) == "Critical", "エヴィサレーションはクリティカル")
    check(env.job_get_spell_map({type = "WeaponSkill", english = "Savage Blade", skill = "Sword"}, nil) == nil, "サベッジブレードはクリティカルではない")
end

-- トレジャーハンター (戦闘中だけ)
check(env.state.TreasureHunter ~= nil, "TreasureHunter の切り替えがある")
env.state.TreasureHunter.value = true
local melee = env.customize_melee_set({head = "base"})
check(melee.head == "TH帽", "TreasureHunter をオンにすると、戦闘中に重ねる")
local idle = env.customize_idle_set({head = "base"})
check(idle.head == "base", "TreasureHunter は待機には重ねない")
env.state.TreasureHunter.value = false

-- 二刀流
if S.engaged.dual11 then
    melee = env.customize_melee_set({waist = "base"})
    if sub == "NIN" or sub == "忍" then check(melee.waist == "dual11腰", "サポ忍で dual11 を重ねる")
    elseif sub == "DNC" or sub == "踊" then check(melee.waist == "dual21腰", "サポ踊で dual21 を重ねる")
    else check(melee.waist == "base", "サポ忍・サポ踊でなければ重ねない") end
    check(env.customize_idle_set({waist = "base"}).waist == "base", "二刀流は待機には重ねない")
end

-- 青魔法
if job == "BLU" then
    check(env.job_get_spell_map({type = "BlueMagic", english = "Sinker Drill"}, nil) == "BluePhysical", "シンカードリルは物理")
    check(env.job_get_spell_map({type = "BlueMagic", english = "Tenebral Crush"}, nil) == "BlueMagical", "テネブラルクラッシュは魔法")
end

-- 風水士
if job == "GEO" then
    check(S.idle.Pet == S.idle.Luopan, "羅盤がいるときの待機は sets.idle.Pet")
    env.buffactive["Entrust"] = true
    worn = {}
    env.job_post_midcast({english = "Indi-Fury", target = {type = "PLAYER"}, action_type = "Magic", skill = "Geomancy"}, {}, nil, {})
    check(worn.head == "エントラスト帽", "エントラスト中のインデで、エントラストの装備")
end

-- マジックバースト
if S.midcast["精霊魔法"] and S.midcast["精霊魔法"].MB then
    check(has(env.state.CastingMode.list, "MB"), "CastingMode に MB")
end
if S.midcast["Elemental Magic"] and S.midcast["Elemental Magic"].MB then
    check(has(env.state.CastingMode.list, "MB"), "CastingMode に MB (英語)")
end

if fails == 0 then io.write("OK " .. job .. "\n") else io.write("FAILED " .. fails .. "\n"); os.exit(1) end
