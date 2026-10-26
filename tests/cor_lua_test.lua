-- 出力した Lua の「遠隔攻撃・ロール・クイックドロー」を、GearSwap を模擬して確認する。
-- 実行: lua5.1.exe tests/cor_lua_test.lua <出力した Lua のパス>   (test_cor.py が作る COR の Lua)
local path = arg[1]
local fails = 0
local function check(cond, msg) if not cond then fails = fails + 1; io.write("NG: " .. msg .. "\n") end end

local worn = {}
local function name_of(item) return type(item) == "table" and item.name or item end
local function opts() return {options = function(self, ...) self.list = {...}; self.value = ... end} end
local env = {
    include = function() end, set_language = function() end, send_command = function() end,
    equip = function(t) for k, v in pairs(t) do worn[k] = v end end,
    empty = "empty",
    M = function(t) return {description = t.description, value = t[1], list = {t[1], t[2]}} end,
    state = {IdleMode = opts(), OffenseMode = opts(), HybridMode = opts(), RangedMode = opts()},
    sets = {precast = {JA = {}, WS = {}, RA = {}}, midcast = {RA = {}}, buff = {}, idle = {}, engaged = {}},
    set_combine = function(a, b) local r = {} for k, v in pairs(a) do r[k] = v end for k, v in pairs(b) do r[k] = v end return r end,
    player = {equipment = {}},
    pairs = pairs, ipairs = ipairs, string = string, table = table, tostring = tostring, type = type,
}
setmetatable(env, {__index = _G})
local chunk = assert(loadfile(path))
setfenv(chunk, env)
chunk()
env.user_setup()
env.init_gear_sets()
local S = env.sets

check(S.midcast.RA == S.RA_STP and S.RA_STP.head == "STP帽", "sets.midcast.RA は遠隔攻撃 (STP)")
check(S.midcast.RA.Acc == S.RA_ACC and S.RA_ACC.head == "飛命帽", "sets.midcast.RA.Acc は遠隔攻撃 (飛命)")
check(env.state.RangedMode.list and env.state.RangedMode.list[2] == "Acc", "RangedMode に Acc がある")
check(S.precast.RA.head == "スナップ帽", "スナップショットのセット")
check(S.precast.CorsairRoll.head == "ロール帽" and S.precast.CorsairRoll.legs == "ロール脚",
      "sets.precast.CorsairRoll は、ロール (共通) にアビリティ強化の装備を重ねたもの")
local allies = S.precast.CorsairRoll["Allies' Roll"]
check(allies and allies.head == "ＣＳトリコルヌ+3" and allies.body == "ロール胴" and allies.legs == "ロール脚",
      "ロールごとの装備は、ロール (共通) に重ねる")
check(S.precast.CorsairShot == S.RA_QDSTP, "クイックドローの既定は STP")
check(S.precast.CorsairShot["Light Shot"] == S.RA_QDACC and S.precast.CorsairShot["Dark Shot"] == S.RA_QDACC, "ライト・ダークは魔命")
check(S.QuickDraw and S.QuickDraw[env.state.QuickDrawMode.value] == S.RA_QDSTP, "QuickDrawMode の既定は STP")

local function pre(spell)
    worn = {}
    env.job_post_precast(spell, {}, nil, {})
    return worn
end
local w = pre({type = "CorsairShot", english = "Fire Shot", action_type = "Ability"})
check(w.head == "QDSTP帽" and name_of(w.ammo) == "アニミキーブレット", "ファイアショット: STP の装備と QD の弾")
env.state.QuickDrawMode.value = env.state.QuickDrawMode.list[2]
w = pre({type = "CorsairShot", english = "Fire Shot", action_type = "Ability"})
check(w.head == "QD威力帽", "QuickDrawMode を切り替えると威力の装備")
w = pre({type = "CorsairShot", english = "Light Shot", action_type = "Ability"})
check(w.head == nil and name_of(w.ammo) == "アニミキーブレット", "ライトショットは QuickDrawMode の装備を着ない (魔命のセットのまま)")

if fails == 0 then io.write("OK 遠隔攻撃・ロール・クイックドロー (Lua): 失敗 0 件\n") else io.write("FAILED " .. fails .. "\n"); os.exit(1) end
