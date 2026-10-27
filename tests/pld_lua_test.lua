-- 出力した Lua の「ナイトの仕組み」を、GearSwap を模擬して確認する。
-- 実行: lua5.1.exe tests/pld_lua_test.lua <出力した Lua のパス> <3 段階 = 1 / 0>
local path, three = arg[1], arg[2] == "1"
local fails = 0
local function check(cond, msg) if not cond then fails = fails + 1; io.write("NG: " .. msg .. "\n") end end

local worn, sent, busy = {}, {}, true
local env = {
    include = function() end, set_language = function() end,
    send_command = function(c) sent[#sent + 1] = c end,
    equip = function(t) for k, v in pairs(t) do if type(k) == "string" then worn[k] = v end end end,
    midaction = function() return busy end,
    add_to_chat = function() end,
    M = function(a, b)
        if type(a) == "table" then return {description = a.description, value = a[1], current = a[1]} end
        return {value = a, description = b}
    end,
    state = {IdleMode = {options = function() end}},
    sets = {precast = {JA = {}, WS = {}}, midcast = {}, buff = {}, idle = {}, engaged = {}},
    set_combine = function(a, b) local r = {} for k, v in pairs(a) do r[k] = v end for k, v in pairs(b) do r[k] = v end return r end,
    player = {sub_job = "WAR"},
    buffactive = {},
    pairs = pairs, ipairs = ipairs, string = string, table = table, tostring = tostring, tonumber = tonumber, type = type,
}
env.get_midcast_set = function(spell, spellMap)
    return env.sets.midcast[spell.english] or (spellMap and env.sets.midcast[spellMap]) or env.sets.midcast
end
setmetatable(env, {__index = _G})
local chunk = assert(loadfile(path))
setfenv(chunk, env)
chunk()
env.user_setup()
env.init_gear_sets()
if env.after_gear_sets then env.after_gear_sets() end   -- GearSwap と同じ順 (get_sets の中で init_gear_sets のあと)
local sets = env.sets

-- 敵対心: セットの無いアビリティは敵対心の装備・センチネルは敵対心 (最大) に重ねる
check(sets.precast.JA.head == "ＳＶシャレル+1", "セットの無いアビリティは、敵対心の装備 (sets.precast.JA に入っている)")
check(sets.precast.JA["Sentinel"] and sets.precast.JA["Sentinel"].body == "最大の胴" and sets.precast.JA["Sentinel"].feet == "ＣＢレギンス+3",
      "センチネルは、敵対心 (最大) に重ねる")
check(sets.precast.JA["Shield Bash"] and sets.precast.JA["Shield Bash"].body == "敵対心の胴", "シールドバッシュは、敵対心に重ねる")
check(sets.midcast.Flash and sets.midcast.Flash.body == "敵対心の胴" and sets.midcast.Flash.neck == "ムーンライトネックレス", "フラッシュは、敵対心に重ねる")
check(sets.midcast.head == nil, "詠唱中断の装備を sets.midcast に入れない (アビリティの midcast で着ないように)")
if not three then
    worn, sent = {}, {}
    env.job_post_midcast({english = "Protect V", action_type = "Magic", cast_time = 2.5}, {}, nil, {})
    check(worn.head == "ＣＶアーメット+3", "セットの無い魔法は、詠唱中ずっと詠唱中断の装備")
    worn = {}
    env.job_post_midcast({english = "Cure IV", action_type = "Magic", cast_time = 2.5}, {}, "Cure", {})
    check(worn.head == nil, "セットのある魔法 (ケアル) は、そのセットのまま (3 段階を使わないとき)")
end
worn = {}
env.job_post_midcast({english = "Majesty", action_type = "Ability", type = "JobAbility"}, {}, nil, {})
check(worn.head == nil, "アビリティの midcast では、詠唱中断の装備を着ない")

-- 手動の対魔法・状態異常耐性
check(env.state.Magical and env.state.Magical.value == false and env.state.StatusResist, "対魔法・状態異常耐性の切り替えがある (初めはオフ)")
local idle = env.customize_idle_set({head = "待機の頭", neck = "待機の首"})
check(idle.head == "待機の頭", "オフのときは、待機の装備のまま")
env.state.Magical.value = true
idle = env.customize_idle_set({head = "待機の頭", neck = "待機の首"})
check(idle.head == "対魔法の頭" and idle.neck == "待機の首", "対魔法をオンにすると、待機の装備に重ねる")
env.state.StatusResist.value = true
local melee = env.customize_melee_set({head = "戦闘の頭"})
check(melee.head == "耐性の頭", "両方オンなら、状態異常耐性が上")

-- 3 段階の着替え
if three then
    worn, sent, busy = {}, {}, true
    local cure = {english = "Cure IV", action_type = "Magic", cast_time = 2.5}
    env.job_post_midcast(cure, {}, "Cure", {})
    check(worn.head == "ＣＶアーメット+3", "詠唱中は、詠唱中断の装備")
    check(sent[#sent] and sent[#sent]:find("gs c land", 1, true), "着弾の直前に替える命令を送る")
    -- 2.5 秒 × (1 - 0.40) - 0.30 = 1.20 秒
    check(sent[#sent]:find("wait 1.20", 1, true), "待ち時間は、ファストキャスト 40% で 1.20 秒 (" .. tostring(sent[#sent]) .. ")")
    worn = {}
    env.job_self_command({"land"}, {})
    check(worn.head == "ＳＶシャレル+1" and worn.legs == "ケアルの脚", "着弾の直前に、ケアルの装備に替える")
    -- 詠唱が終わったあと (中断など) に命令が届いても、着替えない
    env.job_post_midcast(cure, {}, "Cure", {})
    env.job_post_aftercast(cure, {}, "Cure", {})
    busy, worn = false, {}
    env.job_self_command({"land"}, {})
    check(worn.head == nil, "詠唱が終わったあとは、着弾の装備に替えない")
    -- サポ赤なら、特性を足す
    env.player.sub_job, busy, sent = "RDM", true, {}
    env.job_post_midcast(cure, {}, "Cure", {})
    check(sent[#sent]:find("wait 0.82", 1, true), "サポ赤は 15% 足す: 2.5 × 0.45 - 0.30 = 0.82 秒 (" .. tostring(sent[#sent]) .. ")")
else
    check(env.job_post_midcast == nil or true, "")
    check(not env.job_self_command or (function() local w = {}; worn = {}; env.job_self_command({"land"}, {}); return worn.head == nil end)(),
          "3 段階を使わないときは、land の命令が無い")
end

if fails == 0 then io.write("OK ナイトの仕組み (Lua): 失敗 0 件\n") else io.write("FAILED " .. fails .. "\n"); os.exit(1) end
