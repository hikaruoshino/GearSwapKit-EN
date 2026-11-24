"""Run generated Bard Lua under Lua 5.1 for each song in both languages."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE)]

import _env
import export_parser
import i18n
from project import Project


INSTRUMENT_JA = {
    "Gjallarhorn": "ギャッラルホルン", "Daurdabla": "ダウルダヴラ",
    "Terpander": "テルパンダー", "Marsyas": "マルシュアス", "Loughnashade": "ラックナシェード",
}


def song_project(dummy_songs):
    project = Project("BRD")
    # A song and Japanese alias added through the custom spell picker in an older release.
    project.add_pair(2, "Advancing March", "無敵の進撃マーチ")
    gear = {
        "sets.precast.FC['歌唱']": 'body="Song FC"',
        "sets.midcast.SongEffect": 'feet="Duration", body="Common", range="Gjallarhorn"',
        "sets.midcast.March": 'hands="March Hands", body="March"',
        "sets.midcast.Daurdabla": 'body="Dummy", range="Daurdabla"',
        "sets.midcast['Honor March']": 'body="Honor", range="Marsyas"',
        "sets.midcast['Aria of Passion']": 'body="Aria", range="Loughnashade"',
        "sets.midcast['Advancing March']": 'body="Custom"',
        "sets.midcast.Lullaby": 'body="Accuracy"',
    }
    for path, slots in gear.items():
        if i18n.lang() == "ja":
            for en, ja in INSTRUMENT_JA.items():
                slots = slots.replace(en, ja)
        project.assign(path, export_parser.parse_equipped_set("sets.exported={" + slots + "}"))
    saved = json.loads(project.to_json())
    saved["jobs"]["BRD"]["dummy_songs"] = dummy_songs
    return Project.from_json(json.dumps(saved))


# Follow Mote-Include's song name, spell map, skill and type lookup and casting hooks.
# Observe equipped slots while the generated code classifies songs and combines gear.
HARNESS = """
local lang, casts = dofile(arg[2])
local worn = {range="Idle", hands="Idle", feet="Idle", body="Idle"}
local function noop() end
function S(values)
    local s = {contains=function(self, k) return self[k] == true end}
    for _, k in ipairs(values) do s[k] = true end
    return s
end
function set_combine(...)
    local result = {}
    for _, items in ipairs({...}) do
        for k, v in pairs(items) do result[k] = v end
    end
    return result
end
local zone_callbacks = {}
windower = {raw_register_event=function(event, callback)
    if event == "zone change" then table.insert(zone_callbacks, callback) end
end}
local messages = {}
function add_to_chat(color, message)
    assert(type(message) == "string" and message:match("%S") and not message:find("[\\r\\n]"),
           "通知は空でない 1 行")
    table.insert(messages, message)
end
windower.add_to_chat = add_to_chat
windower.to_shift_jis = function(message) return message end
function cancel_spell() _global.cancel_spell = true end
local pending
local casting
function midaction() return casting ~= nil, casting end
empty = {name="empty"}
function equip(items) pending = set_combine(pending, items) end
function M(options) return {current=options[1], value=options[1]} end
set_language, send_command = noop, noop
function include(name)
    assert(name == "Mote-Include.lua")
    job_setup()
    user_setup()
    init_gear_sets()
end
sets = {precast={FC={}, JA={}, WS={}}, midcast={Pet={}}, idle={}, engaged={}, buff={}}
state = {CastingMode={current="Normal"}, IdleMode={options=noop}}
buffactive, classes = {}, {}
player = {status="Idle", equipment=worn}
dofile(arg[1])
get_sets()

local function phase(action, spell, family, handled, registered, timestamp)
    -- GearSwap は ts に対応する登録を _global に写す。正常終了の spell 引数は別表になり得る。
    _global = {spell=registered or spell, timestamp=timestamp, current_event=action, cancel_spell=false}
    local pre = spell.action_type == "Ability" and sets.precast.JA or sets.precast.FC
    local base = ({precast=pre, midcast=sets.midcast, aftercast=sets.idle})[action]
    pending = {}
    local map = family ~= "-" and family or nil
    if job_get_spell_map then map = job_get_spell_map(spell, map) or map end
    -- user_<action> が先に処理済みにした場合も post は呼ばれる。
    local args = {handled=handled or false, cancel=false}
    local hook = _G["job_" .. action]
    if hook and not args.handled then hook(spell, action, map, args) end
    if args.cancel then cancel_spell() end
    if not args.cancel and not args.handled then
        local chosen = action == "aftercast" and base or base[classes.CustomClass] or base[spell.name] or base[map]
            or base[spell.skill] or base[spell.type] or base
        equip(chosen)
    end
    hook = _G["job_post_" .. action]
    if hook and not args.cancel then hook(spell, action, map, args) end
    if pending.range == empty then pending.range = "empty" end
    worn = set_combine(worn, pending)
    player.equipment = worn
    print(action, worn.body, worn.range, worn.hands, worn.feet,
          worn.main or "-", worn.sub or "-", worn.ammo or "-")
end
local function make_spell(en, ja, target)
    local spell = {english=en, name=lang=="ja" and ja or en, type="BardSong",
        skill=lang=="ja" and "歌唱" or "Singing", action_type="Magic",
        target={type=target, distance=1}}
    if target == "Enemy" then
        spell.target = nil
        spell.targets = {Enemy=true}
    end
    return spell
end
local function cast_song(en, ja, family, target, ending, handled)
    local spell = make_spell(en, ja, target)
    phase("precast", spell, family, handled)
    casting = spell
    phase("midcast", spell, family)

    if ending then
        spell.interrupted = ending == "interrupt"
        if spell.interrupted then spell.action_type = "Interruption" end
        casting = nil
        phase("aftercast", spell, family)
    end
end
for _, cast in ipairs(casts) do cast_song(unpack(cast)) end
"""

# Simulate precast_send_check, send_action and the action result notification.
# Match a same-name result to the latest registration, as find_by_spell does.
FLOW = """
local registry, now, next_id = {}, 1000, 0
gearswap = {command_registry=registry}
os.time = function() return math.floor(now) end
os.clock = function() return now end
local function expire()
    for id, entry in pairs(registry) do
        if now - entry.started >= entry.spell.cast_time * 1.1 + 2 then registry[id] = nil end
    end
end
function midaction()
    for id, entry in pairs(registry) do
        if entry.midaction then return true, entry.spell, id end
    end
    return false
end
local function start(spell, family)
    next_id = next_id + 1
    local id = next_id
    registry[id] = {spell=spell, family=family, started=now}
    phase("precast", spell, family, false, spell, id)
    if _global.cancel_spell then
        registry[id] = nil
    else
        registry[id].midaction = true
        phase("midcast", spell, family, false, spell, id)
    end
    return id
end
local function finish(result)
    local found
    for id, entry in pairs(registry) do
        if entry.spell.name == result.name and entry.spell.prefix == result.prefix then
            if not found or id > found then found = id end
        end
    end
    if not found then return nil end
    local entry = registry[found]
    entry.midaction = false
    phase("aftercast", result, entry.family, false, entry.spell, found)
    registry[found] = nil
    return found
end
local function song(en, ja)
    local sp = make_spell(en, ja, "SELF")
    sp.cast_time, sp.prefix = 8, "/song"
    return sp
end
local function honor() return song("Honor March", "栄典の戴冠マーチ") end
local function dummy() return song("Army's Paeon", "戦士達のピーアン") end
local function pianissimo()
    return {english="Pianissimo", name="Pianissimo", type="JobAbility", action_type="Ability",
            cast_time=0, prefix="/jobability", target={type="SELF"}}
end
local function gear(body, instrument)
    assert(worn.body == body and worn.range == instrument,
           "胴/遠隔: " .. tostring(worn.body) .. "/" .. tostring(worn.range)
           .. " (期待: " .. body .. "/" .. instrument .. ")")
end
"""

# Check instruments and armor independently during precast and midcast.
# None skips that slot for the current phase.
CASES = [
    ("Mage's Ballad", "魔道士のバラード", "Ballad", "SELF", None,
     ("Common", "Gjallarhorn", None, "Duration")),
    ("Victory March", "栄光の凱旋マーチ", "March", "SELF", None,
     ("March", "Gjallarhorn", "March Hands", "Duration")),
    ("Honor March", "栄典の戴冠マーチ", "March", "SELF", "Marsyas",
     ("Honor", "Marsyas", "March Hands", "Duration")),
    ("Aria of Passion", "冷静と情熱のアリア", "-", "SELF", "Loughnashade",
     ("Aria", "Loughnashade", None, "Duration")),
    ("Advancing March", "無敵の進撃マーチ", "March", "SELF", None,
     ("Custom", "Gjallarhorn", "March Hands", "Duration")),
    ("Army's Paeon", "戦士達のピーアン", "Paeon", "SELF", None,
     ("Dummy", "Daurdabla", "Idle", "Idle")),
    ("Army's Paeon II", "戦士達のピーアンII", "Paeon", "SELF", None,
     ("Common", "Gjallarhorn", None, "Duration")),
    ("Foe Lullaby", "魔物のララバイ", "Lullaby", "MONSTER", None,
     ("Accuracy", "Idle", None, "Idle")),
    ("Magic Finale", "魔法のフィナーレ", "-", "MONSTER", None,
     ("Song FC", "Idle", None, "Idle")),
]


def old_song_project(en, ja, slots, include_weapons=False):
    """A 1.3.1 save with individual song gear in custom and no shared gear or dummy songs."""
    path = f"sets.midcast['{en}']"
    data = {
        "custom": [[path, en, f"sets.midcast['{ja}']"]],
        "assignments": {"sets.precast.FC['歌唱']": {"body": '"Song FC"'}, path: slots},
    }
    return Project.from_json(json.dumps({
        "version": 2, "job": "BRD", "include_weapons": include_weapons, "jobs": {"BRD": data},
    }))


@unittest.skipUnless(Path(_env.LUA51).is_file(), "Set GSK_LUA51 to the Lua 5.1 executable.")
class BardSongs(unittest.TestCase):
    def setUp(self):
        self.addCleanup(i18n.set_lang, i18n.lang())
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)
        self.harness = self.folder / "test.lua"

    def run_casts(self, project, casts, scenario=""):
        self.harness.write_text(HARNESS + scenario, encoding="utf-8")
        job = self.folder / "BRD.lua"
        job.write_text(project.to_lua(), encoding="utf-8")
        case = self.folder / "case.lua"
        rows = ["{" + ", ".join(json.dumps(v, ensure_ascii=False) for v in cast) + "}" for cast in casts]
        case.write_text("return " + json.dumps(i18n.lang()) + ", {" + ", ".join(rows) + "}", encoding="utf-8")
        result = subprocess.run([_env.LUA51, self.harness, job, case], capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", "replace"))
        return [line.split("\t") for line in result.stdout.decode("utf-8").splitlines()]

    def check_song(self, project, row):
        en, ja, family, target, instrument, mid = row
        lines = self.run_casts(project, [(en, ja, family, target)])
        self.assertEqual(len(lines), 2)
        for line, phase, expected in zip(lines, ("precast", "midcast"),
                                         (("Song FC", instrument, None, None), mid)):
            event, *actual = line[:5]
            self.assertEqual(event, phase)
            self.assertEqual(len(actual), 4)
            for slot, got, want in zip(("body", "range", "hands", "feet"), actual, expected):
                if slot == "range" and i18n.lang() == "ja":
                    want = INSTRUMENT_JA.get(want, want)
                if want is not None:
                    self.assertEqual(got, want, f"{phase} {slot}")

    def test_generated_songs(self):
        for lang in ("ja", "en"):
            i18n.set_lang(lang)
            project = song_project(["Army's Paeon", "Honor March", "Aria of Passion", "Foe Lullaby"])
            for row in CASES:
                with self.subTest(lang=lang, song=row[0]):
                    self.check_song(project, row)

    def test_english_rev1_honor_march_without_spell_map(self):
        # The English rev1 map omits Honor March, so Mote supplies a nil spellMap.
        i18n.set_lang("en")
        self.check_song(song_project([]), (
            "Honor March", "栄典の戴冠マーチ", "-", "SELF", "Marsyas",
            ("Honor", "Marsyas", "March Hands", "Duration"),
        ))

    def test_dummy_instrument_and_excluded_weapons(self):
        for lang in ("ja", "en"):
            i18n.set_lang(lang)
            for specified in (False, True):
                with self.subTest(lang=lang, specified=specified):
                    project = song_project(["Army's Paeon"])
                    project.include_weapons = False
                    slots = 'body="Dummy", main="Sword", sub="Shield", ammo="Stone"'
                    instrument = "Terpander" if specified else "Daurdabla"
                    if lang == "ja":
                        instrument = INSTRUMENT_JA[instrument]
                    if specified:
                        slots += f', range="{instrument}"'
                    project.assign("sets.midcast.Daurdabla", export_parser.parse_equipped_set(
                        "sets.exported={" + slots + "}"))
                    _, mid = self.run_casts(project, [("Army's Paeon", "戦士達のピーアン", "Paeon", "SELF")])
                    self.assertEqual(mid, ["midcast", "Dummy", instrument, "Idle", "Idle", "-", "-", "Stone"])

    def test_instrument_between_songs(self):
        honor = ("Honor March", "栄典の戴冠マーチ", "March", "SELF")
        ballad = ("Mage's Ballad", "魔道士のバラード", "Ballad", "SELF")
        dummy = ("Army's Paeon", "戦士達のピーアン", "Paeon", "SELF")
        lullaby = ("Foe Lullaby", "魔物のララバイ", "Lullaby", "Enemy")
        for lang in ("ja", "en"):
            i18n.set_lang(lang)
            for first, second in ((honor, ballad), (dummy, lullaby)):
                for cycle in (False, True):
                    for ending in ("normal", "interrupt"):
                        with self.subTest(lang=lang, first=first[0], cycle=cycle, ending=ending):
                            if first == honor:
                                project = old_song_project(*honor[:2], {"body": '"Honor"'})
                                instrument, body, next_body = "Marsyas", "Honor", "Song FC"
                            else:
                                project = song_project([dummy[0], lullaby[0]])
                                instrument, body, next_body = "Daurdabla", "Dummy", "Accuracy"
                            if lang == "ja":
                                instrument = INSTRUMENT_JA[instrument]
                            if cycle:
                                item = export_parser.parse_equipped_set('sets.exported={range="Selected"}')
                                project.add_weapon("range", item["range"])
                            restored = "Selected" if cycle else "Idle"
                            events = self.run_casts(project, [(*first, ending), (*second, "normal")])
                            self.assertEqual([e[0] for e in events], ["precast", "midcast", "aftercast"] * 2)
                            self.assertEqual([e[2] for e in events], [
                                instrument if first == honor else "Idle", instrument, restored,
                                restored, restored, restored,
                            ])
                            self.assertEqual((events[1][1], events[4][1]), (body, next_body))

    def test_handled_precast_leaves_range_to_user(self):
        i18n.set_lang("en")
        project = song_project(["Army's Paeon"])
        # Distinguish an instrument equipped by normal Mote song selection from one equipped by a generated hook.
        project.assign("sets.midcast['Honor March']", export_parser.parse_equipped_set(
            'sets.exported={body="Honor"}'))
        for en, ja, family in [
            ("Honor March", "栄典の戴冠マーチ", "March"),
            ("Army's Paeon", "戦士達のピーアン", "Paeon"),
        ]:
            with self.subTest(song=en):
                events = self.run_casts(project, [], f"""
                    local spell = make_spell("{en}", "{ja}", "SELF")
                    phase("precast", spell, "{family}", true)
                    casting = spell
                    phase("midcast", spell, "{family}")
                    worn.range = "Manual Horn"
                    casting = nil
                    phase("aftercast", spell, "{family}")
                """)
                self.assertEqual(events[0][1], "Idle")  # Mote の通常 FC も省略された。
                self.assertEqual([e[2] for e in events], ["Idle", "Idle", "Manual Horn"])

    def check_flow(self, scenario):
        i18n.set_lang("en")
        project = song_project(["Army's Paeon"])
        project.assign("sets.idle", export_parser.parse_equipped_set('sets.exported={body="Idle Coat"}'))
        return self.run_casts(project, [], FLOW + scenario)

    def test_range_cycle_restores_selection_when_previous_range_unknown(self):
        for lang in ("ja", "en"):
            with self.subTest(lang=lang):
                i18n.set_lang(lang)
                project = song_project([])
                project.assign("sets.idle", export_parser.parse_equipped_set('sets.exported={body="Idle Coat"}'))
                for name in ("First Horn", "Selected Horn"):
                    item = export_parser.parse_equipped_set(f'sets.exported={{range="{name}"}}')
                    project.add_weapon("range", item["range"])
                events = self.run_casts(project, [], FLOW + """
                    state.RangeWeapons.value, state.RangeWeapons.current = "Selected Horn", "Selected Horn"
                    player.equipment.range = nil
                    local id = start(honor(), "March")
                    assert(finish(honor()) == id)
                    gear("Idle Coat", "Selected Horn")
                """)
                instrument = INSTRUMENT_JA["Marsyas"] if lang == "ja" else "Marsyas"
                self.assertEqual([e[2] for e in events], [instrument, instrument, "Selected Horn"])

    def test_repeated_cancellations_notify_once_per_song(self):
        for lang in ("ja", "en"):
            with self.subTest(lang=lang):
                i18n.set_lang(lang)
                self.run_casts(song_project([]), [], FLOW + """
                    for cast_number = 1, 2 do
                        local original = start(honor(), "March")
                        assert(#messages == cast_number - 1, "通常の詠唱開始で通知が増えた")
                        for retry = 1, 3 do
                            assert(not registry[start(honor(), "March")], "再入力が取り消されなかった")
                            assert(#messages == cast_number, "取消通知の累計: " .. #messages)
                        end
                        now = now + 4
                        assert(not registry[start(honor(), "March")])
                        assert(#messages == cast_number)
                        now = now + honor().cast_time - 4
                        assert(finish(honor()) == original)
                        assert(#messages == cast_number, "終了時に通知が増えた")
                    end
                """)

    def test_notice_interval_across_interrupted_casts(self):
        expected = {
            "ja": "歌の詠唱中のため、再入力を取り消しました。",
            "en": "Already singing. The additional song request was canceled.",
        }
        for lang, message in expected.items():
            with self.subTest(lang=lang):
                i18n.set_lang(lang)
                self.run_casts(song_project([]), [], FLOW + f"""
                    local function reject_then_interrupt(count)
                        local id = start(honor(), "March")
                        local retry = start(dummy(), "Paeon")
                        assert(registry[id] and not registry[retry], "通知の有無にかかわらず再入力を拒否する")
                        assert(#messages == count, "時刻 " .. now .. " の通知累計: " .. #messages)
                        assert(messages[count] == {json.dumps(message, ensure_ascii=False)}, "取消通知の文言")
                        local result = honor()
                        result.interrupted, result.action_type = true, "Interruption"
                        assert(finish(result) == id, "先行する栄典の中断")
                        assert(#messages == count, "中断で通知が増えた")
                    end
                    local first = now + 0.5
                    now = first
                    reject_then_interrupt(1)
                    now = first + 0.01
                    reject_then_interrupt(1)
                    now = first + 2.99
                    reject_then_interrupt(1)
                    now = first + 3
                    reject_then_interrupt(2)
                    now = now + 3.01
                    reject_then_interrupt(3)
                """)

    def test_missing_range_mode_restores_previous_and_clears_cast(self):
        i18n.set_lang("en")
        project = song_project(["Army's Paeon"])
        item = export_parser.parse_equipped_set('sets.exported={range="Cycle Horn"}')
        project.add_weapon("range", item["range"])
        project.assign("sets.idle", export_parser.parse_equipped_set('sets.exported={body="Idle Coat"}'))
        self.run_casts(project, [], FLOW + """
            local original = start(honor(), "March")
            gear("Honor", "Marsyas")
            state.RangeWeapons = nil
            assert(finish(honor()) == original)
            gear("Idle Coat", "Idle")

            -- 直前の専用楽器と同じ楽器を手動で装備。古い復帰先が残っていれば Idle に戻ってしまう。
            worn.range = "Marsyas"
            local next_song = start(dummy(), "Paeon")
            gear("Dummy", "Daurdabla")
            assert(finish(dummy()) == next_song)
            gear("Idle Coat", "Marsyas")
        """)

    def test_non_song_inputs_are_not_cancelled(self):
        for other in ("pianissimo()", "cure()"):
            with self.subTest(action=other):
                events = self.check_flow(f"""
                    local function cure()
                        return {{english="Cure", name="Cure", type="WhiteMagic", action_type="Magic",
                                cast_time=2, prefix="/magic", target={{type="SELF"}}}}
                    end
                    local original = start(honor(), "March")
                    local id = start({other}, "-")
                    assert(registry[id] and registry[id].midaction, "歌以外の入力が midcast に届かなかった")
                    assert(finish({other}) == id)
                    assert(#messages == 0, "歌以外の入力で取消通知が出た")
                    assert(finish(honor()) == original)
                    gear("Idle Coat", "Idle")
                """)
                self.assertEqual([e[0] for e in events],
                                 ["precast", "midcast", "precast", "midcast", "aftercast", "aftercast"])

    def test_repeated_songs_keep_first_midcast_and_release_to_idle(self):
        for first, family, body, instrument in [("honor", "March", "Honor", "Marsyas"),
                                                ("dummy", "Paeon", "Dummy", "Daurdabla")]:
            for presses in (2, 3):
                with self.subTest(first=first, presses=presses):
                    events = self.check_flow(f"""
                        local original = start({first}(), "{family}")
                        gear("{body}", "{instrument}")
                        for n = 2, {presses} do
                            local retry = start(honor(), "March")
                            assert(registry[retry] == nil, "取り消した連打の登録が残った")
                            gear("{body}", "{instrument}")
                        end
                        assert(finish({first}()) == original, "最初の詠唱の完了通知を照合できない")
                        gear("Idle Coat", "Idle")
                        assert(finish(honor()) == nil, "完了済みの通知が再配信された")
                        gear("Idle Coat", "Idle")
                    """)
                    self.assertEqual([e[0] for e in events], ["precast", "midcast"]
                                     + ["precast"] * (presses - 1) + ["aftercast"])

    def test_song_after_pianissimo(self):
        for pending in (False, True):
            with self.subTest(ability_pending=pending):
                before = "" if pending else 'assert(finish(pianissimo()) == ability)'
                after = 'assert(finish(pianissimo()) == ability)' if pending else ""
                self.check_flow(f"""
                    local ability = start(pianissimo(), "-")
                    {before}
                    local sp = dummy()
                    sp.cast_time, sp.targets, sp.target.type = 4, {{Self=true, Party=true}}, "PLAYER"
                    local original = start(sp, "Paeon")
                    gear("Dummy", "Daurdabla")
                    local retry = start(honor(), "March")
                    assert(not registry[retry], "味方に下歌を詠唱中、栄典の登録が残った")
                    gear("Dummy", "Daurdabla")
                    {after}
                    gear("Dummy", "Daurdabla")
                    assert(finish(dummy()) == original)
                    gear("Idle Coat", "Idle")
                """)

    def test_song_after_zone_or_expiry(self):
        for reset in ("zone", "expiry"):
            for manual in (False, True):
                with self.subTest(reset=reset, manual=manual):
                    reset_registry = """
                        registry = {}
                        gearswap.command_registry = registry
                        for _, callback in ipairs(zone_callbacks) do callback(10, 9) end
                    """ if reset == "zone" else "now = now + 60; expire()"
                    switch = 'worn.range = "Manual Horn"' if manual else ""
                    restored = "Manual Horn" if manual else "Idle"
                    self.check_flow(f"""
                        local lost = start(dummy(), "Paeon")
                        gear("Dummy", "Daurdabla")
                        {reset_registry}
                        assert(not registry[lost])
                        {switch}
                        local current = start(honor(), "March")
                        gear("Honor", "Marsyas")
                        assert(finish(dummy()) == nil, "消去済みの登録へ遅延通知が届いた")
                        gear("Honor", "Marsyas")
                        assert(finish(honor()) == current)
                        gear("Idle Coat", "{restored}")
                    """)

    def test_dummy_then_buff_uses_new_manual_range(self):
        i18n.set_lang("en")
        project = song_project(["Army's Paeon"])
        project.assign("sets.midcast.Paeon", export_parser.parse_equipped_set(
            'sets.exported={hands="Paeon Hands", feet="Paeon Feet"}'))
        events = self.run_casts(project, [], """
            cast_song("Army's Paeon", "戦士達のピーアン", "Paeon", "SELF", "normal")
            worn.range = "Manual Horn"
            cast_song("Mage's Ballad", "魔道士のバラード", "Ballad", "SELF", "normal")
            cast_song("Army's Paeon II", "戦士達のピーアンII", "Paeon", "SELF", "normal")
        """)
        self.assertEqual(events[1][1:5], ["Dummy", "Daurdabla", "Idle", "Idle"])
        self.assertEqual([e[2] for e in events[:6]],
                         ["Idle", "Daurdabla", "Idle", "Manual Horn", "Gjallarhorn", "Manual Horn"])
        self.assertEqual(events[4][1], "Common")
        self.assertEqual(events[7][3:5], ["Paeon Hands", "Paeon Feet"])

    def test_empty_and_unknown_range(self):
        i18n.set_lang("en")
        for initial, restored in [('"empty"', "empty"), ("nil", "Marsyas")]:
            with self.subTest(initial=initial):
                events = self.run_casts(song_project([]), [], f"""
                    player.equipment.range = {initial}
                    cast_song("Honor March", "栄典の戴冠マーチ", "March", "SELF", "normal")
                    print(pending.range or "-")
                """)
                self.assertEqual([e[2] for e in events[:3]], ["Marsyas", "Marsyas", restored])
                self.assertEqual(events[3], ["-" if initial == "nil" else "empty"])

    def test_old_honor_only(self):
        for lang in ("ja", "en"):
            i18n.set_lang(lang)
            project = old_song_project("Honor March", "栄典の戴冠マーチ", {"body": '"Honor"'})
            for row in [
                ("Honor March", "栄典の戴冠マーチ", "March", "SELF", "Marsyas",
                 ("Honor", "Marsyas", None, None)),
                ("Mage's Ballad", "魔道士のバラード", "Ballad", "SELF", "Idle",
                 ("Song FC", "Idle", None, None)),
            ]:
                with self.subTest(lang=lang, song=row[0]):
                    self.check_song(project, row)

    def test_explicit_individual_instrument(self):
        en, ja = "Advancing March", "無敵の進撃マーチ"
        for lang in ("ja", "en"):
            i18n.set_lang(lang)
            for common in (False, True):
                with self.subTest(lang=lang, common=common):
                    project = old_song_project(en, ja, {"body": '"Custom"', "range": '"Individual Horn"'},
                                               include_weapons=True)
                    if common:
                        project.assign("sets.midcast.SongEffect", export_parser.parse_equipped_set(
                            'sets.exported={range="Common Horn", feet="Duration"}'))
                    self.check_song(project, (en, ja, "March", "SELF", "Idle",
                                              ("Custom", "Individual Horn", None, "Duration" if common else "Idle")))


if __name__ == "__main__":
    if not Path(_env.LUA51).is_file():
        print("SKIP: Lua 5.1 が見つからないため BRD の生成 Lua 試験は未実行です（GSK_LUA51）。", file=sys.stderr)
    unittest.main()
