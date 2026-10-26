-- 出力した Lua の「マニューバのメインを元の武器に戻す」を、GearSwap を模擬して確認する。
-- 実行: lua5.1.exe tests/maneuver_lua_test.lua <出力した Lua のパス>
local path = arg[1]
local fails = 0
local function check(cond, msg) if not cond then fails = fails + 1; io.write("NG: " .. msg .. "\n") end end

local worn = {}
local env = {
    include = function() end, set_language = function() end, send_command = function() end,
    equip = function(t) for k, v in pairs(t) do if type(k) == "string" then worn[k] = v end end end,
    M = function(a, b)
        if type(a) == "table" then return {description = a.description, value = a[1], current = a[1]} end
        return {value = a, description = b}
    end,
    state = {IdleMode = {options = function() end}},
    sets = {precast = {JA = {}, WS = {}}, midcast = {Pet = {}}, buff = {}, idle = {}, engaged = {}},
    set_combine = function(a, b) local r = {} for k, v in pairs(a) do r[k] = v end for k, v in pairs(b) do r[k] = v end return r end,
    player = {equipment = {main = "オータス"}},
    pairs = pairs, ipairs = ipairs, string = string, table = table, tostring = tostring, type = type,
}
setmetatable(env, {__index = _G})
local chunk = assert(loadfile(path))
setfenv(chunk, env)
chunk()
env.user_setup()
env.init_gear_sets()

check(env.sets.precast.JA.Maneuver.main == "乾坤圏", "マニューバのセットに乾坤圏が入っている")
local fire = {english = "Fire Maneuver", type = "JobAbility"}
env.job_post_precast(fire, {}, nil, {})
env.player.equipment.main = "乾坤圏"
worn = {}
env.job_post_aftercast(fire, {}, nil, {})
check(worn.main == "オータス", "マニューバのあと、元の武器 (オータス) に戻す")

-- KeepManeuverWeapon がオンなら、戻さない
check(env.state.KeepManeuverWeapon and env.state.KeepManeuverWeapon.value == false, "KeepManeuverWeapon がある (初めはオフ)")
env.state.KeepManeuverWeapon.value = true
env.player.equipment.main = "オータス"
env.job_post_precast(fire, {}, nil, {})
env.player.equipment.main = "乾坤圏"
worn = {}
env.job_post_aftercast(fire, {}, nil, {})
check(worn.main == nil, "KeepManeuverWeapon がオンなら、乾坤圏のまま")

-- オートマトンの WS のためにシュコアトルを持っている最中にマニューバ → WS が終わる → マニューバが終わる: オータスに戻る
env.state.KeepManeuverWeapon.value = false
env.player.equipment.main = "オータス"
env.job_pet_midcast({english = "Bone Crusher", skillchain_a = "Fragmentation"}, {}, nil, {handled = false})
env.player.equipment.main = "シュコアトル"
env.job_post_precast(fire, {}, nil, {})            -- マニューバの開始 (シュコアトルを持っている)
env.player.equipment.main = "乾坤圏"
worn = {}
env.job_pet_aftercast({english = "Bone Crusher"}, {}, nil, {})   -- WS が終わる
check(worn.main == "オータス", "WS が終わったら、選んでいる武器 (オータス) に戻す")
worn = {}
env.job_post_aftercast(fire, {}, nil, {})         -- マニューバが終わる
check(worn.main == "オータス", "マニューバのあとも、シュコアトルではなく選んでいる武器 (オータス) に戻す")

-- マニューバ以外のアビリティでは何もしない
env.state.KeepManeuverWeapon.value = false
worn = {}
env.job_post_precast({english = "Repair", type = "JobAbility"}, {}, nil, {})
env.job_post_aftercast({english = "Repair", type = "JobAbility"}, {}, nil, {})
check(worn.main == nil, "マニューバ以外では、武器を替えない")

if fails == 0 then io.write("OK マニューバの武器 (Lua): 失敗 0 件\n") else io.write("FAILED " .. fails .. "\n"); os.exit(1) end
