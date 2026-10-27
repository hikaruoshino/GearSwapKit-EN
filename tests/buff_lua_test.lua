-- 出力した Lua の「効果中ずっと着る装備 (sets.buff)」の動きを、GearSwap を模擬して確認する。
-- 実行: lua5.1.exe tests/buff_lua_test.lua <出力した Lua のパス>
local path = arg[1]
local fails = 0
local function check(cond, msg) if not cond then fails = fails + 1; io.write("NG: " .. msg .. "\n") end end

local handled = 0
local env = {
    include = function() end, set_language = function() end, send_command = function() end,
    M = function(t) return {description = t.description, current = t[1]} end,
    state = {IdleMode = {options = function() end}},
    sets = {precast = {JA = {}}, buff = {}},   -- Mote-Include が作る入れ物 (sets.idle は Mote は作らない)
    player = {status = "Idle"},
    buffactive = {},
    handle_equipping_gear = function() handled = handled + 1 end,
    set_combine = function(a, b)   -- GearSwap の set_combine の代わり: 後のセットで上書きして混ぜる
        local r = {}
        for k, v in pairs(a) do r[k] = v end
        for k, v in pairs(b) do r[k] = v end
        return r
    end,
    pairs = pairs, ipairs = ipairs, string = string, table = table, tostring = tostring,
}
setmetatable(env, {__index = _G})
local chunk = assert(loadfile(path))
setfenv(chunk, env)
chunk()
env.init_gear_sets()
if env.after_gear_sets then env.after_gear_sets() end   -- GearSwap と同じ順 (get_sets の中で init_gear_sets のあと)
check(type(env.sets.idle) == "table" and type(env.sets.engaged) == "table", "待機・戦闘中のセットが無くても、空のセットができる (Mote が customize_idle_set を呼べる)")

local base = {head = "ふつうの頭", body = "ふつうの胴"}

-- 強化が付いていないとき: そのまま
local s = env.customize_idle_set(base)
check(s.head == "ふつうの頭", "強化が無いときは、待機の装備のまま")

-- 強化 (神獣の加護 = 番号 431) が付いたとき: 待機・戦闘中の装備の頭だけが替わる
env.buffactive[431] = 1
s = env.customize_idle_set(base)
check(s.head ~= "ふつうの頭" and s.body == "ふつうの胴", "強化が付いている間は、待機の頭が強化の装備になる (ほかはそのまま)")
s = env.customize_melee_set(base)
check(s.head ~= "ふつうの頭" and s.body == "ふつうの胴", "戦闘中の装備にも重なる")

-- 強化が付いた・切れたときの着替え直し (名前は英語・日本語のどちらでも、大文字小文字は問わない)
handled = 0
env.job_buff_change("Avatar's Favor", true, {})
env.job_buff_change("神獣の加護", false, {})
env.job_buff_change("avatar's favor", true, {})
check(handled == 3, "英語名・日本語名・小文字のどれでも、着替え直す (実際 " .. handled .. " 回)")
handled = 0
env.job_buff_change("ヘイスト", true, {})
check(handled == 0, "関係ない強化では、着替え直さない")

if fails == 0 then io.write("OK 効果中の装備 (Lua): 失敗 0 件\n") else io.write("FAILED " .. fails .. "\n"); os.exit(1) end
