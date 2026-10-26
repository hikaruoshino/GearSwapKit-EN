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
    windower = {ffxi = {get_player = function() return {} end}, register_event = function() end},
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

-- 1.2.0: 睡眠 (スリップの装備に替えて、起きたら武器を戻す)

if S.Sleep then
    env.player.equipment = {main = "元の剣", sub = "元の盾", range = "empty"}
    env.handle_equipping_gear = function() end
    worn = {}
    env.job_buff_change("Sleep", true, {})
    check(worn.main == "プライムソード" and worn.head == "フレンジーサリット", "睡眠でスリップの装備 (武器も)")
    worn = {}
    env.job_buff_change("Sleep", false, {})
    check(worn.main == "元の剣" and worn.sub == "元の盾", "起きたら元の武器に戻す")
    env.buffactive["Sleep"] = true
    check(env.customize_idle_set({}).head == "フレンジーサリット", "睡眠中は待機にもスリップの装備を重ねる")
    env.buffactive["Sleep"] = nil
end
-- 死の宣告 (被カーズナの装備を重ねる)・聖水
if S.midcast.IncreasedCursna then
    env.buffactive["Doom"] = true
    check(env.customize_idle_set({}).neck == "カーズナ首" and env.customize_melee_set({}).neck == "カーズナ首", "死の宣告中は被カーズナを重ねる")
    env.buffactive["Doom"] = nil
    check(env.customize_idle_set({}).neck == nil, "死の宣告でなければ重ねない")
    worn = {}
    env.job_post_precast({action_type = "Item", english = "Holy Water", name = "聖水", type = "Item"}, {}, nil, {})
    check(worn.neck == "カーズナ首", "聖水を使うとき被カーズナを着る")
end
-- 神獣の加護 (待機だけ)
if S.idle.Avatar and S.idle.Avatar.Favor then
    env.buffactive["Avatar's Favor"] = true
    check(env.customize_idle_set({}).head == "加護帽", "神獣の加護中の待機")
    check(env.customize_melee_set({}).head == nil, "加護は戦闘中には重ねない")
    env.buffactive["Avatar's Favor"] = nil
end
-- HP が少ないとき・ノックバック
if S.LowHp then
    env.player.hpp = 20
    check(env.customize_idle_set({}).body == "LowHp胴", "HP 30% 以下で LowHp")
    env.player.hpp = 80
    check(env.customize_idle_set({}).body == nil, "HP が多ければ重ねない")
end
if S.KnockBack then
    env.state.KnockBack.value = true
    check(env.customize_melee_set({}).back == "リパルスマント", "KnockBack をオンで戦闘中に重ねる")
    env.state.KnockBack.value = false
end
-- 弱体の INT / MND
if S.midcast.EnfeeblingEffectInt then
    check(env.job_get_spell_map({english = "Sleep II", type = "WhiteMagic"}, nil) == "EnfeeblingEffectInt", "スリプルIIは INT 系")
    check(env.job_get_spell_map({english = "Silence", type = "WhiteMagic"}, nil) == "EnfeeblingEffectMnd", "サイレスは MND 系")
end
-- 青魔法の魔命
if S.midcast.BlueMagicAcc then
    check(env.job_get_spell_map({english = "Sheep Song", type = "BlueMagic"}, nil) == "BlueMagicAcc", "シープソングは魔命")
end
-- モードの選択肢
if S.midcast.RA and S.midcast.RA.Critical then check(has(env.state.RangedMode.list, "Critical"), "RangedMode に Critical") end
if S.engaged.Parry then check(has(env.state.OffenseMode.list, "Parry"), "OffenseMode に Parry") end
if S.engaged.Enn then check(has(env.state.OffenseMode.list, "Enn"), "OffenseMode に Enn") end

if fails == 0 then io.write("OK " .. job .. "\n") else io.write("FAILED " .. fails .. "\n"); os.exit(1) end
