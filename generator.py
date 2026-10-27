# -*- coding: utf-8 -*-
"""選んだセットから、GearSwap (Mote-Include) のジョブ用 Lua を作る。

出力は GearSwap 標準の関数 (get_sets / user_setup / init_gear_sets) だけで組む。
他の作者のコードは使わない。装備の中身 (名前・オーグメント) は export の表記をそのまま使う。
"""
import datetime
import json
import os

import export_parser as EP
import ws_types as WS
from i18n import L, is_en, SKILL_EN

WEAPON_SLOTS = ('main', 'sub', 'range', 'ammo')

HEADER_JA = """-- {title}
-- GearSwapKit で作成した {job} 用の GearSwap ファイル ({date})。
-- 使い方: このファイルを GearSwap の data フォルダー (data/{job}.lua) に置き、//lua r gearswap か、ジョブを変えて読み込みます。
-- 装備の名前は日本語です (set_language('japanese'))。装備を変えたいときは、一番下の init_gear_sets の中の名前を書き換えます。
-- 武器 ({weapon_slots}) は、{weapons}
"""
HEADER = HEADER_JA      # 互換のため (日本語の見出し)


# ファイルの分け方の説明と、装備のセットの前後の印 (ジョブ_gear.lua に写すとき、印のあいだをそのまま写せばよいように)
def SYSTEM_SECTION_NOTE(job):
    return [
        "",
        L("-- このファイルは 2 つに分かれています。", "-- This file has two parts."),
        L("--   1. システム (このすぐ下から): 着替えの仕組みです。普段は書き換えません。",
          "--   1. System (right below): the gear-swap logic. You normally do not edit it."),
        L("--   2. 装備のセット (ファイルの一番下の init_gear_sets): 装備の名前を書き換えるのは、ここです。",
          "--   2. Gear sets (init_gear_sets at the very bottom): this is where you change item names."),
        L("-- 装備のセットを別のファイルに分けるときは、data/キャラ名/%s_gear.lua を作成して、一番下の「装備のセット ここから」から" % job,
          "-- To keep the gear sets in a separate file, create data/<character name>/%s_gear.lua and paste everything" % job),
        L("--   「ここまで」の印までを丸ごとコピペします。GearSwap は、そちらの装備のセットを使います。",
          "--   from \"GEAR SETS BEGIN\" down to \"GEAR SETS END\" at the bottom. GearSwap then uses the sets in that file."),
        "",
        L("-- ======== システム ここから (着替えの仕組み。普段は書き換えません) ========",
          "-- ======== SYSTEM BEGIN (gear-swap logic; normally no need to edit) ========"),
    ]


def GEAR_SECTION_BEGIN(job):
    return [L("-- ======== システム ここまで ========", "-- ======== SYSTEM END ========"),
            "",
            L("-- ======== 装備のセット ここから ========", "-- ======== GEAR SETS BEGIN ========"),
            L("-- /キャラ名/%s_gear.lua を作成して、ここから下 (「装備のセット ここまで」の印まで) を丸々コピペすれば、そのまま使用できます。" % job,
              "-- Create /<character name>/%s_gear.lua and paste everything from here down (to GEAR SETS END) as is; it works without changes." % job)]


def GEAR_SECTION_END():
    return [L("-- ======== 装備のセット ここまで ========", "-- ======== GEAR SETS END ========")]


HEADER_EN = """-- {title}
-- GearSwap file for {job}, made with GearSwapKit ({date}).
-- Usage: put this file in your GearSwap data folder (data/{job}.lua), then //lua r gearswap or change jobs to load it.
-- To change gear, edit the item names inside init_gear_sets at the bottom.
-- Weapons ({weapon_slots}): {weapons}
"""


def _en_skill_keys(text):
    """英語クライアント用: セットのキーの日本語のスキル名 (['回復魔法']) を英語 (['Healing Magic']) にする。"""
    for ja, en in SKILL_EN.items():
        text = text.replace("['%s']" % ja, "['%s']" % en)
    return text


def make_key(base, name):
    """sets.precast.WS + レデンサリュート → sets.precast.WS['レデンサリュート']"""
    safe = name.replace('\\', '\\\\').replace("'", "\\'")
    return "%s['%s']" % (base, safe)


# Mote-Include が init で作る入れ物 (Mote-Include.lua 112〜124 行。自分で作らなくてよい)。sets.merit はキットが作る
MOTE_TABLES = {"sets", "sets.precast", "sets.precast.FC", "sets.precast.JA", "sets.precast.WS", "sets.precast.RA",
               "sets.midcast", "sets.midcast.RA", "sets.midcast.Pet", "sets.idle", "sets.resting", "sets.engaged",
               "sets.defense", "sets.buff", "sets.merit"}


def _parent(path):
    """sets.precast.CorsairRoll['X'] → sets.precast.CorsairRoll・sets.precast.JA.Maneuver → sets.precast.JA"""
    if path.endswith("]") and "[" in path:
        return path[:path.rindex("[")]
    if "." in path:
        return path[:path.rindex(".")]
    return None


def _depth(path):
    return path.count('.') + path.count('[')


# 矢弾を、武器ではなく普通の装備としてセットに入れるジョブ (ストンチタスラム+1 など、着替えに意味があるもの)。
# 遠隔のジョブ (狩人・コルセア) は、矢弾の使い分けの仕組みで替えるので除く
def ammo_as_gear(job):
    return job not in WS.RANGED_JOBS


def set_lines(path, items, include_weapons, base=None, cycle_slots=(), keep_slots=()):
    """1 つのセットを Lua の行にする。items は {スロット: Item}。
    base があれば、そのセットに重ねる (set_combine)。Mote-Include は個別の技のセット (sets.precast.CorsairRoll['…'] など) を
    見つけるとそれだけを着て、まとめのセット (ロール全般の頭・手など) を引き継がないため。"""
    lines = []
    for slot in EP.SLOTS:
        it = items.get(slot)
        if it is None:
            continue
        if slot in WEAPON_SLOTS and slot not in keep_slots and (not include_weapons or slot in cycle_slots):
            continue
        lines.append("        %s=%s," % (slot, it.raw))
    if not lines:
        return []
    if base:
        return ["    %s = set_combine(%s, {" % (path, base)] + lines + ["    })", ""]
    return ["    %s = {" % path] + lines + ["    }", ""]


WEAPON_STATES = [("main", "MainWeapons", "メイン"), ("sub", "SubWeapons", "サブ"), ("range", "RangeWeapons", "遠隔")]
WEAPON_LABEL_EN = {"main": "Main", "sub": "Sub", "range": "Ranged"}


def _lua_str(text):
    """Lua の文字列 ("…") にする。"""
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def weapon_names(items):
    """武器の表示名 (切り替えの選択肢の名前)。同じ名前が複数あるときは「 (2)」「 (3)」を付ける。"""
    names, seen = [], {}
    for it in items:
        base = it.name or L("武器", "Weapon")
        seen[base] = seen.get(base, 0) + 1
        names.append(base if seen[base] == 1 else "%s (%d)" % (base, seen[base]))
    return names


def weapon_blocks(weapons):
    """武器の切り替えの Lua。戻り値: (ファイルの先頭に置く行, user_setup の中に置く行)。武器が無ければ空。"""
    active = [(slot, field, label) for slot, field, label in WEAPON_STATES if weapons and weapons.get(slot)]
    if not active:
        return [], [], []
    top = [L("-- 武器の切り替え: ゲームで //gs c cycle MainWeapons (サブは SubWeapons・遠隔は RangeWeapons) を押すたびに、次の武器に持ち替えます。",
             "-- Weapon cycle: //gs c cycle MainWeapons (SubWeapons / RangeWeapons) switches to the next weapon."),
           L("-- //gs c weapons で、今選んでいる武器を装備します。武器は、装備のセット (待機・戦闘中など) には入れません。",
             "-- //gs c weapons equips the selected weapons. Weapons are left out of the idle / engaged sets."),
           "local weapon_items = {"]
    setup = []
    for slot, field, label in active:
        items = weapons[slot]
        names = weapon_names(items)
        top.append("    %s = {" % slot)
        for n, it in zip(names, items):
            top.append("        [%s] = %s," % (_lua_str(n), it.raw))
        top.append("    },")
        setup.append(L("    -- %s の武器の選択肢 (//gs c cycle %s)" % (label, field),
                       "    -- %s weapon choices (//gs c cycle %s)" % (WEAPON_LABEL_EN[slot], field)))
        setup.append("    state.%s = M{['description']='%s', %s}" % (field, field, ", ".join(_lua_str(n) for n in names)))
    top += [
        "}",
        "local weapon_states = {" + ", ".join("%s = '%s'" % (field, slot) for slot, field, _l in active) + "}",
        "",
        "local function equip_weapon(slot, name)",
        "    local item = weapon_items[slot] and weapon_items[slot][name]",
        "    if item then equip({[slot] = item}) end",
        "end",
        "",
        "function job_state_change(stateField, newValue, oldValue)",
        "    local slot = weapon_states[stateField]",
        "    if slot then equip_weapon(slot, newValue) end",
        L("    -- ナイトの対魔法・状態異常耐性 (武器も着替える) をオフにしたら、選んでいる武器に戻す",
          "    -- PLD: when Magical / StatusResist (which swap weapons too) is turned off, go back to the selected weapons"),
        L("    -- からくり士: マニューバの武器を持ったままにする (KeepManeuverWeapon) をオフにしたら、選んでいる武器に戻す",
          "    -- PUP: when KeepManeuverWeapon is turned off, go back to the selected weapons"),
        "    if stateField == 'KeepManeuverWeapon' and not newValue then send_command('wait 0.5; gs c weapons') end",
        "    if (stateField == 'Magical' or stateField == 'StatusResist') and not newValue",
        "        and not (state.Magical and state.Magical.value) and not (state.StatusResist and state.StatusResist.value) then",
        "        send_command('wait 0.5; gs c weapons')",
        "    end",
        "end",
        "",
    ]
    setup.append(L("    -- 読み込んだあと、少し待ってから、選んでいる武器を装備します",
                   "    -- Equip the selected weapons shortly after loading"))
    setup.append("    send_command('wait 3; gs c weapons')")
    cmds = [L("    -- //gs c weapons: 今選んでいる武器を装備します", "    -- //gs c weapons: equip the selected weapons"),
            "    if cmdParams[1] == 'weapons' then",
            "        for field, slot in pairs(weapon_states) do",
            "            if state[field] then equip_weapon(slot, state[field].current) end",
            "        end",
            "        eventArgs.handled = true",
            "        return",
            "    end"]
    return top, setup, cmds


MERIT_BASE = "sets.merit"


# メリット特性の装備を「ペットがいる間だけ」重ねるジョブ (オートマトン・飛竜の性能を上げる特性)。ほかのジョブは On の間いつでも重ねる
MERIT_NEEDS_PET = ("PUP", "DRG")


# 二刀流のセット: (パス, サポジョブの英語略称, 日本語略称)。作者の user-globals.lua の customize_melee_set と同じ
DUAL_SETS = [("sets.engaged.dual11", "NIN", "忍"), ("sets.engaged.dual21", "DNC", "踊")]


def overlay_blocks(buffs, emitted, job=None, toggles=(), dual=(), status=(), low_hp=False, sleep=False, weapon_cycle=False):
    """待機・戦闘中の装備に重ねる仕組みの Lua。
    - 効果中ずっと着る装備 (sets.buff): buffs = [(セットのパス, バフ番号, 英語名, 日本語名)]。その強化が付いている間だけ重ねる。
    - メリットポイントで覚える特性の装備 (sets.merit.*): //gs c cycle MeritGear を On にしたときだけ、ペットがいる間に重ねる
      (振っていない人は、ほかの装備で対応しているので、既定は Off)。
    戻り値: (ファイルの先頭に置く行, user_setup の中に置く行, init_gear_sets の最後に置く行)。重ねるものが無ければ空。
    Mote-Include は sets.buff などを自動では使わないので、customize_idle_set / customize_melee_set で重ねる。"""
    # buffs の 1 行: (パス, バフ番号, 英語名, 日本語名[, 着る時 = idle / precast / midcast / both[, 行動 = Magic / WeaponSkill / Ranged Attack]])
    rows = []
    for b in (buffs or []):
        if b[0] in emitted:
            b = tuple(b)
            rows.append(b[:4] + ((b[4] if len(b) > 4 else "idle"), (b[5] if len(b) > 5 else "Magic")))
    active = [b[:4] for b in rows if b[4] == "idle"]
    # "both" は、行動を始めるときと行動中の両方 (詠唱時間と再詠唱時間の両方に効くもの・学者の電光石火の章など)
    casts = {ph: [b[:4] + (b[5],) for b in rows if b[4] in (ph, "both")] for ph in ("precast", "midcast")}
    merits = [p for p in sorted(emitted) if p.startswith(MERIT_BASE + ".")]
    toggles = list(toggles or [])
    # toggles の 1 行: (state の名前, 説明, セットのパス[, "melee" = 戦闘中だけ重ねる])
    dual = [d for d in DUAL_SETS if d[0] in emitted] if dual else []
    status = list(status or [])
    if not active and not merits and not any(casts.values()) and not toggles and not dual and not status and not low_hp and not sleep:
        return [], [], []
    top = [L("-- 待機と戦闘中の装備に、条件つきで重ねる装備", "-- Conditional gear layered over the idle / engaged sets")]
    if active:
        top += [L("-- 効果中ずっと着る装備 (sets.buff): その強化が付いている間だけ、重ねます。",
                  "-- Buff gear (sets.buff): layered on while the buff is active."),
                L("local buff_gear = {}   -- {バフ番号, 英語名, 日本語名, セット}",
                  "local buff_gear = {}   -- {buff id, name, name, set}")]
    if any(casts.values()):
        top += [L("-- 強化が効いている間に、魔法・ウェポンスキル・遠隔攻撃をするときの装備 (学者の章・青魔道士のブルーチェーンなど):",
                  "-- Gear for spells / weapon skills / ranged attacks while a buff is active (SCH stratagems, BLU Chain Affinity, etc.):"),
                L("-- 行動を始めるとき (precast) と行動中 (midcast) に着ます。",
                  "-- worn in precast and midcast."),
                L("local cast_gear = {precast = {}, midcast = {}}   -- {バフ番号, セット, 行動の種類}",
                  "local cast_gear = {precast = {}, midcast = {}}   -- {buff id, set, action type}"),
                "local function cast_matches(kind, spell)",
                "    if kind == 'WeaponSkill' then return spell.type == 'WeaponSkill' end",
                "    if kind == 'Ranged Attack' then return spell.action_type == 'Ranged Attack' end",
                "    return spell.action_type == 'Magic'",
                "end",
                "local function equip_cast_gear(phase, spell)",
                "    for _, b in ipairs(cast_gear[phase]) do",
                "        if buffactive[b[1]] and cast_matches(b[3], spell) then equip(b[2]) end",
                "    end",
                "end",
                ""]
    if not active and not merits and not toggles and not dual and not status and not low_hp and not sleep:
        return top, [], _cast_reg(casts)
    if low_hp:
        top += [L("local LOW_HP = 30   -- HP がこの % 以下なら sets.LowHp を重ねる", "local LOW_HP = 30   -- layer sets.LowHp at or below this HP %")]
    if sleep:
        top += [L("-- 睡眠: スリップの装備 (sets.Sleep) で起きる。寝る前の武器を覚えておき、起きたら戻す",
                  "-- Sleep: wake up with slip gear (sets.Sleep). Remember the weapons and put them back on waking"),
                "local slept_weapons = nil"]
    if merits:
        needs_pet = job in MERIT_NEEDS_PET
        top += [L("-- メリットポイントで覚える特性の装備 (sets.merit): //gs c cycle MeritGear で On にしたときだけ、%s重ねます。"
                  % ("ペットがいる間に" if needs_pet else ""),
                  "-- Merit trait gear (sets.merit): layered on only when //gs c cycle MeritGear is On%s."
                  % (" and your pet is out" if needs_pet else "")),
                "local merit_gear = {}"]
    top += ["local function apply_overlay(base, melee)"]
    if active:
        top += ["    for _, b in ipairs(buff_gear) do",
                "        if buffactive[b[1]] then base = set_combine(base, b[4]) end",
                "    end"]
    if merits:
        top += ["    if state.MeritGear and state.MeritGear.value == 'On'%s then" % (" and pet and pet.isvalid" if needs_pet else ""),
                "        for _, s in ipairs(merit_gear) do base = set_combine(base, s) end",
                "    end"]
    for tg in toggles:
        field, desc, path = tg[:3]
        cond = " and melee" if len(tg) > 3 and tg[3] == "melee" else ""
        if field is None:     # いつも重ねる装備 (学者の陣頭指揮の足など)
            top += ["    base = set_combine(base, %s)" % path + ("" if is_en() else "   -- %s" % desc)]
        else:
            top += ["    if state.%s and state.%s.value%s then base = set_combine(base, %s) end" % (field, field, cond, path)]
    for en, ja, path, where in status:
        cond = "buffactive[%s]" % _lua_str(en) + ("" if is_en() else " or buffactive[%s]" % _lua_str(ja))
        only = " and not melee" if where == "idle" else ""
        top += ["    if (%s)%s then base = set_combine(base, %s) end" % (cond, only, path)]
    if low_hp:
        top += ["    if player and player.hpp and player.hpp <= LOW_HP then base = set_combine(base, sets.LowHp) end"]
    if sleep:
        top += ["    if (buffactive['Sleep']%s) then base = set_combine(base, sets.Sleep) end" % ("" if is_en() else " or buffactive['睡眠']")]
    if dual:
        top += [L("    -- 二刀流: サポジョブに合わせて、戦闘中の装備に重ねる (サポ忍 = sets.engaged.dual11・サポ踊 = sets.engaged.dual21)",
                  "    -- Dual wield: layered over engaged gear by subjob (/NIN = sets.engaged.dual11, /DNC = sets.engaged.dual21)")]
        for path, sub_en, sub_ja in dual:
            subs = "player.sub_job == '%s'" % sub_en + ("" if is_en() else " or player.sub_job == '%s'" % sub_ja)
            top += ["    if melee and (%s) then base = set_combine(base, %s) end" % (subs, path)]
    top += ["    return base",
            "end",
            "",
            "function customize_idle_set(idleSet)",
            "    return apply_overlay(idleSet)",
            "end",
            "",
            "function customize_melee_set(meleeSet)",
            "    return apply_overlay(meleeSet, true)",
            "end",
            ""]
    watch = [(en, ja) for en, ja, _p, _w in status]
    if active or watch or sleep:
        top += [L("-- 強化・状態が付いたとき・切れたときに、装備を着替え直します", "-- Re-equip when a buff or status is gained or lost"),
                "function job_buff_change(buff, gain, eventArgs)",
                "    local name = tostring(buff):lower()"]
        if sleep:
            top += ["    if name == 'sleep'%s then" % ("" if is_en() else " or name == '睡眠'"),
                    "        if gain then",
                    "            slept_weapons = {main = player.equipment.main, sub = player.equipment.sub, range = player.equipment.range}",
                    "            equip(sets.Sleep)",
                    "        else",
                    "            if slept_weapons then equip(slept_weapons) end",
                    "            slept_weapons = nil",
                    "            handle_equipping_gear(player.status)"]
            if weapon_cycle:
                top += ["            send_command('wait 0.5; gs c weapons')"]
            top += ["        end",
                    "        return",
                    "    end"]
        for en, ja in watch:
            top += ["    if name == %s%s then handle_equipping_gear(player.status) return end"
                    % (_lua_str(en.lower()), "" if is_en() else " or name == %s" % _lua_str(ja))]
        if active:
            top += ["    for _, b in ipairs(buff_gear) do",
                    "        if name == b[2]:lower() or name == b[3]:lower() then",
                    "            handle_equipping_gear(player.status)",
                    "            return",
                    "        end",
                    "    end"]
        top += ["end", ""]
    setup = []
    for tg in toggles:
        field, desc, path = tg[:3]
        if field is None:
            continue
        setup += [L("    -- %s の装備 (%s) を重ねるか: //gs c toggle %s" % (desc, path, field),
                    "    -- Layer %s gear (%s) on or off: //gs c toggle %s" % (TOGGLE_EN.get(field, field), path, field)),
                  "    state.%s = M(false, '%s')" % (field, field)]
    if merits:
        setup += [L("    -- メリットポイントで覚える特性 (最適化・微調整など) の装備を使うか (//gs c cycle MeritGear)。振っていなければ Off のまま",
                    "    -- Use merit trait gear (Optimization, Fine-Tuning, etc.): //gs c cycle MeritGear. Leave Off if you have no merits there"),
                 "    state.MeritGear = M{['description']='MeritGear', 'Off', 'On'}"]
    reg = []
    if active or merits or toggles or dual or status or low_hp or sleep:
        # 念のため: Mote-Include は sets.idle / sets.engaged を空で作るが、無いと customize_idle_set などが呼ばれないので、
        # 無ければ空のセットを用意する (標準の Mote-Include では何も変わらない)
        reg.append(L("    -- 待機・戦闘中の装備のセットが無いときのための用意 (普段は何もしません)",
                     "    -- Fallback in case idle / engaged sets are missing (normally does nothing)"))
        reg.append("    sets.idle = sets.idle or {}")
        reg.append("    sets.engaged = sets.engaged or {}")
    if active:
        reg.append(L("    -- 効果中ずっと着る装備の登録", "    -- Register buff gear"))
        for path, bid, en, ja in active:
            # 英語クライアントでは日本語名は使わないので、英語名を 2 つ並べる
            reg.append("    buff_gear[#buff_gear + 1] = {%d, %s, %s, %s}" % (bid, _lua_str(en), _lua_str(en if is_en() else ja), path))
    if merits:
        reg.append(L("    -- メリットポイントで覚える特性の装備の登録", "    -- Register merit trait gear"))
        for path in merits:
            reg.append("    merit_gear[#merit_gear + 1] = %s" % path)
    reg += _cast_reg(casts)
    reg.append("")
    return top, setup, reg


def _cast_reg(casts):
    """魔法を唱えるときの装備の登録の行。"""
    reg = []
    for ph in ("precast", "midcast"):
        if casts.get(ph):
            reg.append(L("    -- 効果中に行動するときの装備の登録 (%s)" % ph, "    -- Register buff action gear (%s)" % ph))
            for path, bid, en, ja, kind in casts[ph]:
                reg.append("    cast_gear.%s[#cast_gear.%s + 1] = {%d, %s, %s}" % (ph, ph, bid, path, _lua_str(kind)))
    return reg


import set_catalog as _SC


def received_blocks(emitted, manual=(), weapons=False):
    """被強化の装備 (sets.midcast.IncreasedPhalanx / IncreasedProtect / IncreasedShell) の Lua。
    戻り値: (ファイルの先頭の行, init_gear_sets の最後の行, job_post_midcast の中の行,
            job_self_command の中の行, job_post_aftercast の中の行)。セットが無ければ空。
    ほかの人が自分に唱え始めたら (action パケットの詠唱開始) 着て、着弾・中断 (または 8 秒) で gs c update を送って戻す。
    weapons: 受ける強化のセットに武器 (main / sub / range) が入っている (ナイトの剣・盾など)。着る前の武器を覚えて、戻すときに着直す
    (待機・戦闘中のセットには武器を入れていないので、gs c update だけでは武器が戻らないため)。"""
    # manual (自動で着替えない) のものは、セットだけを出して、反応の仕組みには登録しない
    use = [(name, ids, aoe) for name, _ja, ids, aoe in _SC.RECEIVED
           if "sets.midcast.%s" % name in emitted and name not in manual]
    if not use:
        return [], [], [], [], []
    top = [
        L("-- 受ける強化の装備 (被ファランクス・被プロテス・被シェル): ほかの人が自分に唱え始めたら着て、届いたら元に戻します。",
          "-- Received-buff gear (Phalanx / Protect / Shell received): worn when someone starts casting on you, removed when it lands."),
        L("-- 範囲の魔法 (プロテア・シェルラ・女神降臨の章のあとのファランクス) は、パーティーの人が唱えたときに着ます。",
          "-- AoE spells (Protectra, Shellra, Phalanx after Accession) trigger it when a party member casts them."),
        L("local received_sets = {}    -- [魔法の番号] = セットの名前 (sets.midcast.の後ろ)",
          "local received_sets = {}    -- [spell id] = set name (after sets.midcast.)"),
        L("local received_aoe = {}     -- [魔法の番号] = true (範囲の魔法)",
          "local received_aoe = {}     -- [spell id] = true (AoE spell)"),
        L("local CAST_BEGIN, CAST_INTERRUPT = 24931, 28787   -- 詠唱 (category 8) の開始・中断",
          "local CAST_BEGIN, CAST_INTERRUPT = 24931, 28787   -- casting (category 8) start / interrupt"),
        L("local RECEIVED_HOLD = 8     -- 着弾も中断も届かなかったときに戻すまでの秒数",
          "local RECEIVED_HOLD = 8     -- seconds before reverting if neither landing nor interrupt is seen"),
        L("local ACCESSION, ACCESSION_SEC = 218, 60   -- 学者の女神降臨の章 (次の魔法が範囲になる)",
          "local ACCESSION, ACCESSION_SEC = 218, 60   -- SCH Accession (next spell becomes AoE)"),
        "local accession_until, received_casters, received_on = {}, {}, nil",
        "",
        "local function received_update()",
        L("    if midaction() then return end   -- 自分の行動中は触らない (行動の後の着替えに任せる)",
          "    if midaction() then return end   -- don't touch gear during your own action (aftercast handles it)"),
        "    local now, name = os.clock(), nil",
        "    for id, v in pairs(received_casters) do",
        "        if now > v.until_time then received_casters[id] = nil else name = v.set end",
        "    end",
        "    if name then",
        ("        send_command('gs c received_save; gs equip sets.midcast.' .. name)" if weapons else
         "        send_command('gs equip sets.midcast.' .. name)"),
        "        received_on = name",
        "    elseif received_on then",
        "        received_on = nil",
        ("        send_command('gs c received_restore')" if weapons else "        send_command('gs c update')"),
        "    end",
        "end",
        "",
        L("-- raw 版: GearSwap の register_event は呼ぶたびに装備の再計算 (refresh_globals) をする。action は全員分が届くので、使わない",
          "-- raw version: GearSwap's register_event recomputes gear (refresh_globals) on every call; action fires for everyone, so don't use it"),
        "windower.raw_register_event('action', function(act)",
        "    local cat = act and act.category",
        L("    if cat ~= 8 and cat ~= 6 and cat ~= 4 then return end   -- 近接・遠隔など、見ない行動は先に捨てる",
          "    if cat ~= 8 and cat ~= 6 and cat ~= 4 then return end   -- drop actions we don't use (melee, ranged...) first"),
        "    local player = windower.ffxi.get_player()",
        "    if not player or act.actor_id == player.id then return end",
        "    if act.category == 8 then",
        "        if act.param == CAST_INTERRUPT then",
        "            if received_casters[act.actor_id] then received_casters[act.actor_id] = nil; received_update() end",
        "            return",
        "        end",
        "        if act.param ~= CAST_BEGIN then return end",
        "        local target = act.targets and act.targets[1]",
        "        local action = target and target.actions and target.actions[1]",
        "        local name = action and received_sets[action.param]",
        "        if not name then return end",
        "        local actor = windower.ffxi.get_mob_by_id(act.actor_id)",
        "        local own_aoe = actor and actor.in_party and target.id == act.actor_id",
        "        local aoe = own_aoe and (received_aoe[action.param]",
        "            or (accession_until[act.actor_id] and os.clock() <= accession_until[act.actor_id]))",
        "        if target.id ~= player.id and not aoe then return end",
        "        received_casters[act.actor_id] = {set = name, until_time = os.clock() + RECEIVED_HOLD}",
        "        received_update()",
        "        coroutine.schedule(received_update, RECEIVED_HOLD + 0.1)",
        "    elseif act.category == 6 then",
        "        if act.param == ACCESSION then accession_until[act.actor_id] = os.clock() + ACCESSION_SEC end",
        "    elseif act.category == 4 then",
        "        accession_until[act.actor_id] = nil",
        "        if received_casters[act.actor_id] then received_casters[act.actor_id] = nil; received_update() end",
        "    end",
        "end)",
        "",
    ]
    reg = [L("    -- 受ける強化の装備の登録 (魔法の番号は Windower の res)",
             "    -- Register received-buff gear (spell ids from Windower res)")]
    for name, ids, aoe in use:
        for i in ids + aoe:
            reg.append("    received_sets[%d] = '%s'" % (i, name))
        for i in aoe:
            reg.append("    received_aoe[%d] = true" % i)
    reg.append("")
    mid = [L("    -- 自分で自分に唱えるときは、詠唱中に受ける強化の装備を着る",
             "    -- When casting on yourself, wear the received-buff gear in midcast"),
           "    if spell and received_sets[spell.id] and spell.target and spell.target.type == 'SELF' then"]
    save = "received_weapons = received_weapons or {main = player.equipment.main, sub = player.equipment.sub, range = player.equipment.range}"
    if weapons:
        mid += ["        " + save]
    mid += ["        equip(sets.midcast[received_sets[spell.id]])",
            "    end"]
    cmds, after = [], []
    if weapons:
        # received_weapons は job_self_command (このファイルの上のほう) からも使うので、local にしない
        cmds = [L("    -- //gs c received_save / received_restore: 受ける強化の装備で持ち替える前の武器を覚える・着直す",
                  "    -- //gs c received_save / received_restore: remember / re-equip the weapons from before the received-buff gear"),
                "    if cmdParams[1] == 'received_save' then",
                "        " + save,
                "        eventArgs.handled = true",
                "        return",
                "    end",
                "    if cmdParams[1] == 'received_restore' then",
                "        if received_weapons then equip(received_weapons) end",
                "        received_weapons = nil",
                "        handle_equipping_gear(player.status)",
                "        eventArgs.handled = true",
                "        return",
                "    end"]
        after = [L("    -- 自分で自分に唱えた受ける強化のあとは、持ち替える前の武器に戻す",
                   "    -- After casting a received-buff spell on yourself, go back to the weapons from before"),
                 "    if received_weapons and not received_on then",
                 "        equip(received_weapons)",
                 "        received_weapons = nil",
                 "    end"]
    return top, reg, mid, cmds, after


def lockstyle_blocks(lockstyle):
    """ロックスタイル番号 (lockstyleset) の Lua。戻り値: (user_setup の中の行, init_gear_sets の最初の行, job_self_command の中の行)。"""
    if not lockstyle:
        return [], [], []
    setup = [L("    -- 読み込んだあと (武器を装備したあと)、少し待ってから、ロックスタイルをかけます",
               "    -- Apply lockstyle shortly after loading (after weapons are equipped)"),
             "    send_command('wait 5; gs c lockstyleset')"]
    init = [L("    -- ロックスタイル番号 (ゲームの装備セットの番号。//gs c lockstyleset で、もう一度かけます)",
              "    -- Lockstyle set number (in-game equipment set; //gs c lockstyleset re-applies it)"),
            "    lockstyleset = %d" % int(lockstyle),
            ""]
    cmds = [L("    -- //gs c lockstyleset: ロックスタイルをかけます", "    -- //gs c lockstyleset: apply lockstyle"),
            "    if cmdParams[1] == 'lockstyleset' then",
            "        if lockstyleset then send_command('input /lockstyleset ' .. lockstyleset) end",
            "        eventArgs.handled = true",
            "        return",
            "    end"]
    return setup, init, cmds


# 矢弾の使い分け (狩人・コルセア)。役目: 物理 (遠隔攻撃・物理の WS)・魔攻 (魔法属性の遠隔 WS)・クイックドロー (コルセア)
AMMO_ROLES = [("physical", "物理"), ("magical", "魔攻"), ("quickdraw", "クイックドロー")]
# 魔法属性の遠隔 WS (魔攻の弾を使う)
RANGED_MAGIC_WS = [n for n in WS.MAGIC_WS if n in WS.RANGED_WS]


def _RANGED_SKILL():
    """弓術・射撃の WS かの判定 (英語クライアントは英語名だけ)。"""
    if is_en():
        return "spell.skill == 'Archery' or spell.skill == 'Marksmanship'"
    return "spell.skill == 'Archery' or spell.skill == 'Marksmanship' or spell.skill == '弓術' or spell.skill == '射撃'"


def ammo_blocks(ammo, ws_ammo):
    """矢弾の使い分けの Lua。ammo: {役目: Item}・ws_ammo: {WS の英語名: Item} (特殊弾)。
    戻り値: (先頭, job_post_precast の中, job_post_aftercast の中, user_setup の中, job_self_command の中)。何も無ければ全部空。
    特殊弾とクイックドローの弾は、使ったあとに外して、遠隔攻撃で撃ってしまわないようにする (誤射防止)。"""
    ammo = {k: v for k, v in (ammo or {}).items() if v}
    ws_ammo = {k: v for k, v in (ws_ammo or {}).items() if v}
    if not (ammo or ws_ammo):
        return [], [], [], [], []
    normal = {it.name for it in ammo.values() if it.name} - ({ammo["quickdraw"].name} if "quickdraw" in ammo else set())
    special = sorted({it.name for it in ws_ammo.values() if it.name and it.name not in normal}
                     | ({ammo["quickdraw"].name} if "quickdraw" in ammo else set()))
    top = (["-- 矢弾の使い分け: 遠隔攻撃と物理の WS は物理の弾、魔法属性の遠隔 WS は魔攻の弾、クイックドローは専用の弾、",
            "-- 技ごとに選んだ WS はその弾 (特殊弾) を使います。特殊弾とクイックドローの弾は、使い終わったら物理の弾に戻します",
            "-- (物理の弾が無ければ外します)。遠隔攻撃で特殊弾を撃ってしまわないためです。//gs c ammo で物理の弾を装備します。"]
           if not is_en() else
           ["-- Ammo handling: ranged attacks and physical WS use the physical ammo, magical ranged WS use the magical ammo,",
            "-- Quick Draw uses its own ammo, and any WS with its own ammo (special ammo) uses that.",
            "-- Special and Quick Draw ammo is swapped back to physical ammo afterwards (or removed if none is set),",
            "-- so you never fire it with a normal ranged attack. //gs c ammo equips the physical ammo."]) + ["local ammo = {"]
    for role, _label in AMMO_ROLES:
        if role in ammo:
            top.append("    %s = %s," % (role, ammo[role].raw))
    top += ["}", "local ws_ammo = {"]
    for en in sorted(ws_ammo):
        top.append("    [%s] = %s," % (_lua_str(en), ws_ammo[en].raw))
    top += ["}", "local special_ammo = {"]
    for n in special:
        top.append("    [%s] = true," % _lua_str(n))
    top += ["}", "local ranged_magic_ws = {"]
    for i in range(0, len(RANGED_MAGIC_WS), 4):
        top.append("    " + " ".join("[%s] = true," % _lua_str(n) for n in RANGED_MAGIC_WS[i:i + 4]))
    top += ["}",
            "",
            L("-- この行動で使う矢弾 (nil なら替えない)", "-- Ammo for this action (nil = no change)"),
            "local function ammo_for(spell)",
            "    if spell.type == 'WeaponSkill' then",
            "        if ws_ammo[spell.english] then return ws_ammo[spell.english] end",
            "        if ranged_magic_ws[spell.english] then return ammo.magical or ammo.physical end",
            "        if %s then" % _RANGED_SKILL(),
            "            return ammo.physical",
            "        end",
            "    elseif spell.action_type == 'Ranged Attack' then",
            "        return ammo.physical",
            "    elseif spell.type == 'CorsairShot' then",
            "        return ammo.quickdraw",
            "    end",
            "end",
            "",
            "local function restore_ammo()",
            "    if special_ammo[player.equipment.ammo] then",
            "        equip({ammo = ammo.physical or empty})",
            "    end",
            "end",
            ""]
    pre = ["    local a = ammo_for(spell)",
           "    if a then",
           "        equip({ammo = a})",
           "    else",
           L("        restore_ammo()     -- ほかの行動の前に、特殊弾・クイックドローの弾を外す (誤射防止)",
             "        restore_ammo()     -- take off special / Quick Draw ammo before other actions"),
           "    end"]
    after = ["    restore_ammo()"]
    setup = [L("    -- 読み込んだあと、少し待ってから、物理の弾を装備します",
               "    -- Equip the physical ammo shortly after loading"),
             "    send_command('wait 3; gs c ammo')"] if "physical" in ammo else []
    cmds = [L("    -- //gs c ammo: 物理の弾を装備します", "    -- //gs c ammo: equip the physical ammo"),
            "    if cmdParams[1] == 'ammo' then",
            "        if ammo.physical then equip({ammo = ammo.physical}) end",
            "        eventArgs.handled = true",
            "        return",
            "    end"]
    return top, pre, after, setup, cmds


# ペットの技の分け方 (召喚士の契約の履行・獣使いの技)。分類は pet_moves.json (FF11 用語辞典で確かめたもの)
# ジョブ -> [(分類, セットの名前 = sets.midcast.Pet の後ろ)]
PET_MAPS = {
    "SMN": [("physical", "AvatarPhysicalPacts"), ("magical", "AvatarMagicalPacts"),
            ("buff", "AvatarBuffWard"), ("debuff", "AvatarDeBuffWard")],
    "BST": [("physical", "PhysicalDamage"), ("magical", "MagicDamage"), ("debuff", "MagicDamage")],
}
PET_TYPES = {"SMN": ("BloodPactRage", "BloodPactWard"), "BST": ("Monster",)}


def _pet_moves():
    import json
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pet_moves.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def pet_map_rows(job, emitted):
    """{技の英語名: セットの名前} (そのセットが出るものだけ)。"""
    rows = {}
    want = {kind: name for kind, name in PET_MAPS.get(job, [])
            if "sets.midcast.Pet.%s" % name in emitted
            # 強化の履行は、セットが無くても召喚魔法スキルの装備 (sets.SmnSkill) を使う
            or (name == "AvatarBuffWard" and "sets.SmnSkill" in emitted)}
    if not want:
        return rows
    for r in _pet_moves().get(job, []):
        name = want.get(r.get("kind"))
        if name and r.get("en"):
            rows[r["en"]] = name
    return rows


BLU_SETS = ("BluePhysical", "BlueMagical", "BlueBuff", "BlueHealing")


def blu_map_rows(job, emitted):
    """青魔法の分類 {英語名: 'BluePhysical' など}。そのセットを出すときだけ (blu_spells.json = 作者の Mote-Mappings.lua の分類)。"""
    if job != "BLU":
        return enfeeble_map_rows(job, emitted)
    have = {c for c in BLU_SETS if "sets.midcast.%s" % c in emitted}
    if not have and "sets.midcast.BlueMagicAcc" not in emitted:
        return {}
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blu_spells.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)["spells"]
    if "sets.midcast.BlueMagicAcc" in emitted:
        have.add("BlueMagicAcc")
        data = dict(data, **{n: "BlueMagicAcc" for n in BLU_ACC_SPELLS})
    return {en: c for en, c in data.items() if c in have}


# 弱体の青魔法 (魔命が大事なもの)。sets.midcast.BlueMagicAcc があるときだけ、これらをそちらに分ける
BLU_ACC_SPELLS = ["Sheep Song", "Soporific", "Dream Flower", "Yawn", "Blank Gaze", "Geist Wall", "Sound Blast", "Chaotic Eye",
                  "Frightful Roar", "Jettatura", "Feather Tickle", "Reaving Wind", "Mortal Ray", "Absolute Terror", "Cruel Joke",
                  "Infrasonics", "Filamented Hold", "Lowing", "Auroral Drape", "Venom Shell", "Stinking Gas", "Awful Eye",
                  "Actinic Burst", "Cold Wave", "Light of Penance", "Blistering Roar"]
# 弱体魔法の INT 系・MND 系 (作者の RDM.lua の分け方を広げたもの)
ENFEEBLE_INT = ["Sleep", "Sleep II", "Sleepga", "Sleepga II", "Break", "Breakga", "Bind", "Blind", "Blind II",
                "Gravity", "Gravity II", "Poison", "Poison II", "Poisonga", "Dispel"]
ENFEEBLE_MND = ["Silence", "Paralyze", "Paralyze II", "Slow", "Slow II", "Addle", "Addle II", "Distract", "Distract II",
                "Distract III", "Frazzle", "Frazzle II", "Frazzle III"]


def enfeeble_map_rows(job, emitted):
    """弱体魔法の INT 系・MND 系 {英語名: 'EnfeeblingEffectInt' など}。そのセットを出すときだけ。"""
    out = {}
    if "sets.midcast.EnfeeblingEffectInt" in emitted:
        out.update({n: "EnfeeblingEffectInt" for n in ENFEEBLE_INT})
    if "sets.midcast.EnfeeblingEffectMnd" in emitted:
        out.update({n: "EnfeeblingEffectMnd" for n in ENFEEBLE_MND})
    return out


def ws_blocks(emitted, job=None):
    """WS の分け方 (job_get_spell_map) の Lua。sets.precast.WS.Magic / .Range が出るときだけ。
    標準の Mote-Include は spellMap の名前でもセットを探すので、魔法属性の WS は 'Magic'・遠隔の WS は 'Range' と分ける。"""
    has_magic = "sets.precast.WS.Magic" in emitted
    has_range = "sets.precast.WS.Range" in emitted
    has_rmagic = "sets.precast.WS.RangeMagic" in emitted
    has_crit = "sets.precast.WS.Critical" in emitted
    pet_rows = pet_map_rows(job, emitted) if job else {}
    blu_rows = blu_map_rows(job, emitted)
    if not (has_magic or has_range or has_rmagic or has_crit or pet_rows or blu_rows):
        return []
    top = []
    if blu_rows:
        top += [L("-- 青魔法の分け方: sets.midcast.BluePhysical (物理)・BlueMagical (魔法)・BlueBuff (強化)・BlueHealing (回復)",
                  "-- Blue magic mapping: sets.midcast.BluePhysical / BlueMagical / BlueBuff / BlueHealing"),
                L("-- (魔法ごとのセット sets.midcast['魔法の名前'] があれば、そちらが先に使われます)",
                  "-- (A per-spell set, sets.midcast['Spell Name'], takes priority if you have one)"),
                "local blu_spell_map = {"]
        for en in sorted(blu_rows):
            top.append("    [%s] = '%s'," % (_lua_str(en), blu_rows[en]))
        top += ["}"]
    if pet_rows:
        names = sorted(set(pet_rows.values()))
        top += [L("-- ペットの技の分け方: %s" % "・".join("sets.midcast.Pet.%s" % n for n in names),
                  "-- Pet move mapping: %s" % ", ".join("sets.midcast.Pet.%s" % n for n in names)),
                L("-- (分類は FF11 用語辞典で確かめたもの。技ごとのセット sets.midcast.Pet['技の名前'] があれば、そちらが先に使われます)",
                  "-- (A per-move set, sets.midcast.Pet['Move Name'], takes priority if you have one)"),
                "local pet_move_map = {"]
        for en in sorted(pet_rows):
            top.append("    [%s] = '%s'," % (_lua_str(en), pet_rows[en]))
        top += ["}",
                "local pet_move_types = {%s}" % ", ".join("['%s'] = true" % t for t in PET_TYPES[job])]
    if not (has_magic or has_range or has_rmagic or has_crit):
        top += ["function job_get_spell_map(spell, default_spell_map)"]
        if pet_rows:
            top.append("    if pet_move_types[spell.type] and pet_move_map[spell.english] then return pet_move_map[spell.english] end")
        if blu_rows:
            top.append("    if blu_spell_map[spell.english] then return blu_spell_map[spell.english] end")
        top += ["end", ""]
        return top
    top += [L("-- ウェポンスキルの分け方: 魔法属性の WS (属性物理を含む) は sets.precast.WS.Magic、"
              "弓術・射撃の WS は sets.precast.WS.Range を使います",
              "-- Weapon skill mapping: magical WS (including hybrid) use sets.precast.WS.Magic, "
              "archery / marksmanship WS use sets.precast.WS.Range"),
            L("-- (技ごとのセット sets.precast.WS['技の名前'] があれば、そちらが先に使われます)",
              "-- (A per-WS set, sets.precast.WS['WS Name'], takes priority if you have one)")]
    if has_crit:
        top[1:1] = [L("-- クリティカルの WS (エヴィサレーション・ボーパルブレードなど) は sets.precast.WS.Critical を使います",
                      "-- Critical-hit WS (Evisceration, Vorpal Blade, etc.) use sets.precast.WS.Critical")]
    if has_rmagic:
        top[1:1] = [L("-- 魔法属性の遠隔 WS (レデンサリュートなど) は sets.precast.WS.RangeMagic を使います",
                      "-- Magical ranged WS (Leaden Salute, etc.) use sets.precast.WS.RangeMagic")]
    if has_magic or has_rmagic:
        top.append("local magic_ws = {")
        for i in range(0, len(WS.MAGIC_WS), 4):
            top.append("    " + " ".join("[%s] = true," % _lua_str(n) for n in WS.MAGIC_WS[i:i + 4]))
        top.append("}")
    if has_crit:
        top.append("local crit_ws = {")
        for i in range(0, len(WS.CRIT_WS), 4):
            top.append("    " + " ".join("[%s] = true," % _lua_str(n) for n in WS.CRIT_WS[i:i + 4]))
        top.append("}")
    top += ["function job_get_spell_map(spell, default_spell_map)"]
    if pet_rows:
        top.append("    if pet_move_types[spell.type] and pet_move_map[spell.english] then return pet_move_map[spell.english] end")
    if blu_rows:
        top.append("    if blu_spell_map[spell.english] then return blu_spell_map[spell.english] end")
    top += ["    if spell.type ~= 'WeaponSkill' then return end"]
    ranged = "(%s)" % _RANGED_SKILL()
    if has_rmagic:
        top.append("    if magic_ws[spell.english] and %s then return 'RangeMagic' end" % ranged)
    if has_magic:
        top.append("    if magic_ws[spell.english] then return 'Magic' end")
    if has_range:
        top.append("    if %s then return 'Range' end" % _RANGED_SKILL())
    if has_crit:
        top.append("    if crit_ws[spell.english] then return 'Critical' end")
    top += ["end", ""]
    return top


# --- ナイト (PLD) ---
# 敵対心 (最大) を土台にするアビリティ (詠唱の無い、敵対心を稼ぐアビリティ)
PLD_ENMITY_MAX_JA = ("Sentinel", "Rampart", "Majesty", "Vallation", "Valiance", "Palisade")
# 敵対心を土台にする魔法 (技ごとに足したとき)
PLD_ENMITY_SPELLS = ("Flash", "Foil", "Reprisal", "Crusade", "Banish", "Banishga", "Banish II", "Holy", "Enlight",
                     "Jettatura", "Geist Wall", "Sheep Song", "Blank Gaze", "Soporific", "Stinking Gas", "Poisonga")
# 手動で重ねる装備: (state の名前, 説明, セットのパス)。後ろのものが上に重なる
PLD_TOGGLES = [("Magical", "対魔法", "sets.idle.Magical"), ("StatusResist", "状態異常耐性", "sets.StatusResist")]
TOGGLE_EN = {"Magical": "magic defense", "StatusResist": "status resistance", "TreasureHunter": "Treasure Hunter"}
# トレジャーハンター: //gs c toggle TreasureHunter で、戦闘中の装備に重ねる (全ジョブ)
TH_TOGGLE = ("TreasureHunter", "トレジャーハンター", "sets.TreasureHunter", "melee")
# ノックバック防止: //gs c toggle KnockBack で、戦闘中の装備に重ねる (ナイト・魔導剣士)
KB_TOGGLE = ("KnockBack", "ノックバック防止", "sets.KnockBack", "melee")
TOGGLE_EN["KnockBack"] = "knockback guard"
# 死の宣告・神獣の加護: (英語名, 日本語名, セット, idle = 待機だけ / both)
STATUS_OVERLAYS = [("Doom", "死の宣告", "sets.midcast.IncreasedCursna", "both"),
                   ("Avatar's Favor", "神獣の加護", "sets.idle.Avatar.Favor", "idle")]
# メインとサブも着替えるセット (対魔法の武器・盾)。オフにしたら、武器の切り替えで選んでいる武器に戻す
PLD_WEAPON_SETS = ("sets.idle.Magical", "sets.StatusResist")
PHALANX_SET = "sets.midcast['Phalanx']"     # 魔法のファランクス (剣・盾のファランクス+ も持ち替える)
PLD_LAND_ADJUST = 0.30     # 着弾の何秒前に着弾の装備へ替えるか (作者の PLD.lua の実測: 0.30 秒で 10/10)
PLD_SUB_RDM_FC = 15        # サポ赤のファストキャストの特性 (%)


def pld_base(path, emitted):
    """ナイトの技ごとのセットを重ねる元。アビリティ → 敵対心 (最大)・敵対心の魔法 → 敵対心。"""
    for prefix, names, chain in (("sets.precast.JA['", None, ("sets.Enmity",)),
                                 ("sets.midcast['", PLD_ENMITY_SPELLS, ("sets.Enmity",))):
        if path.startswith(prefix) and path.endswith("']"):
            en = path[len(prefix):-2].replace("\\'", "'")
            if names is not None and en not in names:
                return None
            if names is None and en in PLD_ENMITY_MAX_JA:
                chain = ("sets.EnmityMax", "sets.Enmity")
            for c in chain:
                if c in emitted:
                    return c
            return None
    if path == "sets.midcast.Flash" and "sets.Enmity" in emitted:
        return "sets.Enmity"
    return None


def pld_blocks(emitted, three_stage=False, fast_cast=0):
    """ナイトの仕組みの Lua。戻り値: dict(top, post_midcast, aftercast, cmds, setup, init_tail, toggles)。
    - 敵対心: セットの無いアビリティは sets.precast.JA (Mote が最後に見る場所) に、敵対心の装備を入れておく
    - 詠唱中断: セットの無い魔法は sets.midcast (同じく最後に見る場所) に、詠唱中断の装備を入れておく
    - 3 段階の着替え (three_stage): 詠唱中は詠唱中断の装備、着弾の直前に、その魔法の装備 (ケアルなど) へ替える"""
    out = dict(top=[], post_midcast=[], aftercast=[], cmds=[], setup=[], init_tail=[], toggles=[])
    init = []
    if "sets.Enmity" in emitted:
        init += [L("    -- セットを作っていないアビリティは、敵対心の装備で使います",
                   "    -- Job abilities without their own set use the enmity set"),
                 L("    for slot, item in pairs(sets.Enmity or {}) do   -- ジョブ_gear.lua で消しても止まらないように",
                   "    for slot, item in pairs(sets.Enmity or {}) do   -- keeps working if removed in JOB_gear.lua"),
                 "        if type(slot) == 'string' and sets.precast.JA[slot] == nil then sets.precast.JA[slot] = item end",
                 "    end"]
    if "sets.midcast.interruption" in emitted:
        # sets.midcast (Mote が最後に見る場所) に入れると、アビリティの midcast でも着てしまうので、魔法のときだけ着る
        out["post_midcast"] = [
            L("    -- セットを作っていない魔法は、詠唱中ずっと詠唱中断の装備です (アビリティ・WS では着ない)",
              "    -- Spells without their own set use the spell interruption set in midcast (not for JAs / WS)"),
            "    if spell.action_type == 'Magic' and get_midcast_set(spell, spellMap) == sets.midcast then",
            "        equip(sets.midcast.interruption)",
            "    end"]
    if init:
        out["init_tail"] = init + [""]
    out["toggles"] = [t for t in PLD_TOGGLES if t[2] in emitted]
    if three_stage and "sets.midcast.interruption" in emitted:
        fc = max(0, min(80, int(fast_cast or 0)))
        out["top"] = [
            L("-- 3 段階の着替え: 詠唱の開始 = ファストキャスト → 詠唱中 = 詠唱中断 → 着弾の直前 = その魔法の装備 (ケアルなど)",
              "-- 3-stage swap: precast = fast cast -> midcast = spell interruption -> just before landing = the spell's own set (Cure, etc.)"),
            L("-- 着弾の時刻は、ファストキャストから計算します。装備のファストキャストが変わったら fast_cast を直してください。",
              "-- Landing time is estimated from fast cast. Update fast_cast if your gear's fast cast changes."),
            L("local fast_cast = %d        -- 装備のファストキャスト (%%)。サポ赤のときは、特性の %d%% を足します" % (fc, PLD_SUB_RDM_FC),
              "local fast_cast = %d        -- fast cast from gear (%%); +%d%% is added automatically with /RDM" % (fc, PLD_SUB_RDM_FC)),
            L("local land_adjust = %.2f     -- 着弾の何秒前に替えるか (短いと間に合いません。//gs c landadjust 0.4 で変更)" % PLD_LAND_ADJUST,
              "local land_adjust = %.2f     -- seconds before landing to swap (too short and it misses; change with //gs c landadjust 0.4)" % PLD_LAND_ADJUST),
            "local land_set = nil",
            ""]
        out["post_midcast"] = [     # 3 段階は、セットの有無にかかわらず詠唱中断を着るので、上の行と入れ替える
            L("    -- 3 段階の着替え: いまの装備 (その魔法の装備) を覚えて、詠唱中断の装備に替え、着弾の直前に戻す",
              "    -- 3-stage swap: remember the spell's set, switch to interruption gear, swap back just before landing"),
            "    if spell.action_type == 'Magic' then",
            "        land_set = get_midcast_set(spell, spellMap)",
            "        equip(sets.midcast.interruption)",
            ("        local fc = fast_cast + ((player.sub_job == 'RDM'%s) and %d or 0)"
             % ("" if is_en() else " or player.sub_job == '赤'", PLD_SUB_RDM_FC)),
            "        if fc > 80 then fc = 80 end",
            "        local wait = (spell.cast_time or 2.5) * (1 - fc / 100) - land_adjust",
            "        if wait < 0.05 then wait = 0.05 end",
            "        send_command('wait ' .. string.format('%.2f', wait) .. '; gs c land')",
            "    end"]
        out["aftercast"] = ["    land_set = nil"]
        out["cmds"] = [
            L("    -- //gs c land: 着弾の直前に、その魔法の装備に替えます (3 段階の着替えの最後。まだ詠唱中のときだけ)",
              "    -- //gs c land: swap to the spell's set just before it lands (last stage; only while still casting)"),
            "    if cmdParams[1] == 'land' then",
            "        if land_set and midaction() then equip(land_set) end",
            "        land_set = nil",
            "        eventArgs.handled = true",
            "        return",
            "    end",
            L("    -- //gs c landadjust 秒: 着弾の何秒前に替えるか",
              "    -- //gs c landadjust <sec>: how many seconds before landing to swap"),
            "    if cmdParams[1] == 'landadjust' then",
            "        local n = tonumber(cmdParams[2])",
            L("        if n then land_adjust = n; add_to_chat(122, '着弾の ' .. n .. ' 秒前に替えます') end",
              "        if n then land_adjust = n; add_to_chat(122, 'Landing swap set to ' .. n .. 's before landing') end"),
            "        eventArgs.handled = true",
            "        return",
            "    end"]
    return out


# --- からくり士 (PUP) ---
PUP_WS_SET = "sets.midcast.Pet.WeaponSkill"
PUP_ENMITY_SET = "sets.midcast.Pet.Enmity"


def maneuver_blocks(emitted):
    """からくり士のマニューバのメイン (乾坤圏など) を、マニューバのあと選んでいる武器に戻す Lua。
    //gs c toggle KeepManeuverWeapon でオンにすると戻さない (TP を消したくないとき)。
    戻り値: dict(top, post_precast, aftercast, setup)。マニューバのセットが無ければ空。"""
    out = dict(top=[], post_precast=[], aftercast=[], setup=[])
    if "sets.precast.JA.Maneuver" not in emitted:
        return out
    out["top"] = [L("-- マニューバのメイン (乾坤圏など) は、マニューバのあと、持ち替える前の武器に戻します (戻すと TP は消えます)。",
                    "-- The Maneuver main weapon (Kenkonken, etc.) is swapped back after the Maneuver (this resets TP)."),
                  L("-- //gs c toggle KeepManeuverWeapon でオンにすると、戻さずに持ったままにします。",
                    "-- Turn on //gs c toggle KeepManeuverWeapon to keep holding it."),
                  "local maneuver_prev_main = nil",
                  L("-- 戻す先: 武器の切り替えで選んでいる武器 (あれば)。無ければ、持ち替える前の武器",
                    "-- Swap back to the weapon selected in the weapon cycle, or else the one held before"),
                  L("-- (オートマトンの WS のためにシュコアトルなどを持っていたときに、それへ戻さないため)",
                    "-- (so we don't go back to e.g. Xiucoatl held only for an automaton WS)"),
                  "local function maneuver_main(fallback)",
                  "    if weapon_items and weapon_items.main and state.MainWeapons and weapon_items.main[state.MainWeapons.current] then",
                  "        return weapon_items.main[state.MainWeapons.current]",
                  "    end",
                  "    return fallback",
                  "end",
                  "local function is_maneuver(spell)",
                  "    return spell.english and spell.english:find('Maneuver', 1, true) ~= nil",
                  "end",
                  ""]
    out["post_precast"] = [L("    -- マニューバでメインを持ち替えるときは、元の武器を覚えておく",
                             "    -- Remember the current main weapon before a Maneuver swaps it"),
                           "    if is_maneuver(spell) and sets.precast.JA.Maneuver.main and player.equipment.main ~= nil",
                           "            and not (state.KeepManeuverWeapon and state.KeepManeuverWeapon.value) then",
                           L("        -- オートマトンの WS のために持ち替えている最中なら、その前の武器を覚える",
                             "        -- If mid-swap for an automaton WS, remember the weapon from before that"),
                           "        maneuver_prev_main = maneuver_prev_main or pet_ws_prev_main or player.equipment.main",
                           "    end"]
    out["aftercast"] = [L("    -- マニューバのあと、元の武器に戻す (KeepManeuverWeapon がオンなら戻さない)",
                          "    -- After a Maneuver, swap the main weapon back (unless KeepManeuverWeapon is on)"),
                        "    if is_maneuver(spell) and maneuver_prev_main then",
                        "        if not (state.KeepManeuverWeapon and state.KeepManeuverWeapon.value)",
                        "                and maneuver_prev_main ~= '' and maneuver_prev_main ~= 'empty' then",
                        "            equip({main = maneuver_main(maneuver_prev_main)})",
                        "        end",
                        "        maneuver_prev_main = nil",
                        "    end"]
    out["setup"] = [L("    -- マニューバのメイン (乾坤圏など) を持ったままにするか (//gs c toggle KeepManeuverWeapon。オンなら TP が消えない)",
                      "    -- Keep the Maneuver main weapon (Kenkonken, etc.) after Maneuvers: //gs c toggle KeepManeuverWeapon (on = keep TP)"),
                    "    state.KeepManeuverWeapon = M(false, 'KeepManeuverWeapon')"]
    return out


def pup_blocks(emitted, auto=False):
    """からくり士のオートマトンの技の装備の Lua。戻り値: dict(top, setup, cmds)。
    - 反応する着替え: オートマトンの技が出たとき (job_pet_midcast)、WS (連携属性のある技) はペットの WS の装備、
      ストロボ・フラッシュバルブはペットの敵対心の装備を着る
    - 自動の事前着替え (auto): 1 秒ごとに、オートマトンの TP が 930 以上なら WS の装備、ストロボ (火のマニューバ中)・
      フラッシュバルブ (光のマニューバ中) の再使用まで残り 2 秒なら敵対心の装備を、先に着ておく (技が出てからでは間に合わないため)"""
    has_ws, has_en = PUP_WS_SET in emitted, PUP_ENMITY_SET in emitted
    out = dict(top=[], setup=[], cmds=[])
    if not (has_ws or has_en):
        return out
    top = [L("-- オートマトンの技の装備: 技が出たとき、WS (連携属性のある技) は sets.midcast.Pet.WeaponSkill、",
             "-- Automaton gear: when it uses a move, WS (moves with a skillchain property) use sets.midcast.Pet.WeaponSkill"),
           L("-- ストロボ・フラッシュバルブ (敵対心) は sets.midcast.Pet.Enmity を着ます",
             "-- and Strobe / Flashbulb (enmity) use sets.midcast.Pet.Enmity."),
           L("-- WS のセットのメイン (シュコアトルなど) は持ち替えます。ただし乾坤圏を持っているときは替えません。",
             "-- The WS set's main weapon (Xiucoatl, etc.) is swapped in, except while holding Kenkonken."),
           L("-- セットにメインが無ければ、今の武器のまま。WS が終わったら、持ち替える前の武器に戻します。",
             "-- With no main in the set the weapon stays as is; after the WS, the previous weapon is restored."),
           L("local PET_WS_KEEP_MAIN = {['乾坤圏'] = true, ['Kenkonken'] = true}",
             "local PET_WS_KEEP_MAIN = {['Kenkonken'] = true}"),
           "local pet_ws_prev_main = nil",
           "local function pet_ws_set()",
           "    local set = sets.midcast.Pet.WeaponSkill",
           "    if not set or not set.main then return set end",
           "    if PET_WS_KEEP_MAIN[player.equipment.main] then",
           "        local copy = {}",
           "        for slot, item in pairs(set) do if slot ~= 'main' then copy[slot] = item end end",
           "        return copy",
           "    end",
           "    if not pet_ws_prev_main then pet_ws_prev_main = player.equipment.main end",
           "    return set",
           "end",
           L("-- 戻す先: 武器の切り替えで選んでいる武器 (あれば)。無ければ、持ち替える前の武器",
             "-- Swap back to the weapon selected in the weapon cycle, or else the one held before"),
           L("-- (マニューバと WS が重なったときに、一時的に持っていた武器へ戻さないため)",
             "-- (so overlapping Maneuver / WS swaps don't leave you on a temporary weapon)"),
           "local function chosen_main(fallback)",
           "    if weapon_items and weapon_items.main and state.MainWeapons and weapon_items.main[state.MainWeapons.current] then",
           "        return weapon_items.main[state.MainWeapons.current]",
           "    end",
           "    return fallback",
           "end",
           "local function restore_main()",
           "    if pet_ws_prev_main and pet_ws_prev_main ~= '' and pet_ws_prev_main ~= 'empty' then",
           "        equip({main = chosen_main(pet_ws_prev_main)})",
           "    end",
           "    pet_ws_prev_main = nil",
           "end",
           "",
           "local function pup_set_for(spell)",
           "    if spell.english == 'Provoke' or spell.english == 'Flashbulb' then return %s end"
           % ("sets.midcast.Pet.Enmity" if has_en else "nil"),
           "    if spell.skillchain_a and spell.skillchain_a ~= '' then return %s end"
           % ("pet_ws_set()" if has_ws else "nil"),
           "end",
           "",
           "function job_pet_midcast(spell, action, spellMap, eventArgs)",
           "    local set = pup_set_for(spell)",
           "    if set then",
           "        equip(set)",
           "        eventArgs.handled = true",
           "    end",
           "end",
           "",
           "function job_pet_aftercast(spell, action, spellMap, eventArgs)",
           "    if pet_gear_reset then pet_gear_reset() end",
           "    restore_main()",
           "end",
           ""]
    top[top.index("local pet_ws_prev_main = nil")] = "local pet_ws_prev_main, pet_gear_reset = nil, nil"
    if auto:
        top += [
            L("-- 自動の事前着替え: 技が出てからでは着替えが間に合わないので、出そうなときに先に着ておきます",
              "-- Pre-equip: swapping after the move fires is too late, so put the gear on when a move is about to happen"),
            L("-- (//gs c toggle PetAutoGear で、オン・オフ)", "-- (toggle with //gs c toggle PetAutoGear)"),
            L("local PET_WS_TP = 930                 -- この TP 以上で、WS の装備を先に着る (オートマトンは 1000 ですぐ撃つので先回り)",
              "local PET_WS_TP = 930                 -- pre-equip WS gear at this TP (the automaton fires right at 1000)"),
            L("local STROBE_RECAST, FLASHBULB_RECAST = 30, 45   -- ストロボ・フラッシュバルブの再使用 (秒)",
              "local STROBE_RECAST, FLASHBULB_RECAST = 30, 45   -- Strobe / Flashbulb recast (sec)"),
            L("local PRE_EQUIP_SEC, PRE_EQUIP_TIMEOUT = 2, 10   -- 再使用の残りがこの秒数で先に着る・着てから出ないまま諦めるまでの秒数",
              "local PRE_EQUIP_SEC, PRE_EQUIP_TIMEOUT = 2, 10   -- pre-equip with this much recast left / give up after this long"),
            L("local ABIL_PROVOKE, ABIL_FLASHBULB = 1945, 1947  -- オートマトンの技の番号 (res/monster_abilities.lua)",
              "local ABIL_PROVOKE, ABIL_FLASHBULB = 1945, 1947  -- automaton move ids (res/monster_abilities.lua)"),
            "local BUFF_FIRE_MANEUVER, BUFF_LIGHT_MANEUVER = 300, 306",
            "local strobe_time, flashbulb_time = 0, 0",
            "local pet_gear, pet_gear_since = nil, 0",
            L("pet_gear_reset = function() pet_gear = nil end   -- 技が終わったとき (job_pet_aftercast) に呼ぶ",
              "pet_gear_reset = function() pet_gear = nil end   -- called when the move finishes (job_pet_aftercast)"),
            "",
            "local function has_attachment(...)",
            "    if not pet.isvalid or not pet.attachments then return false end",
            "    for _, name in ipairs({...}) do",
            "        if pet.attachments[name] then return true end",
            "    end",
            "    return false",
            "end",
            "",
            "local function recast_left(fired, recast, now)",
            "    if fired == 0 then return 0 end",
            "    return math.max(0, recast - (now - fired))",
            "end",
            "",
            "local function pet_auto_gear()",
            "    local now = os.time()",
            "    if not state.PetAutoGear.value then return end",
            "    if not pet.isvalid then",
            "        strobe_time, flashbulb_time = 0, 0",
            "        if pet_gear then pet_gear = nil; handle_equipping_gear(player.status); restore_main() end",
            "        return",
            "    end",
            L("    if midaction() or pet_midaction() then return end   -- 行動中は、行動の装備を崩さない",
              "    if midaction() or pet_midaction() then return end   -- don't break action gear"),
            L("    -- 先に着たのに出ないときは、出たものとみなして諦める",
              "    -- If the move never came, treat it as used and give up"),
            "    if pet_gear == 'strobe' and now - pet_gear_since >= PRE_EQUIP_TIMEOUT then strobe_time = now end",
            "    if pet_gear == 'flashbulb' and now - pet_gear_since >= PRE_EQUIP_TIMEOUT then flashbulb_time = now end",
            "    local want, set = nil, nil",
            "    if pet.status == 'Engaged' then",
        ]
        cond = []
        if has_en:
            cond += [
                L("        if has_attachment('ストロボ', 'ストロボII', 'Strobe', 'Strobe II') and buffactive[BUFF_FIRE_MANEUVER]",
                  "        if has_attachment('Strobe', 'Strobe II') and buffactive[BUFF_FIRE_MANEUVER]"),
                "                and recast_left(strobe_time, STROBE_RECAST, now) <= PRE_EQUIP_SEC then",
                "            want, set = 'strobe', sets.midcast.Pet.Enmity",
                L("        elseif has_attachment('フラッシュバルブ', 'Flashbulb') and buffactive[BUFF_LIGHT_MANEUVER]",
                  "        elseif has_attachment('Flashbulb') and buffactive[BUFF_LIGHT_MANEUVER]"),
                "                and recast_left(flashbulb_time, FLASHBULB_RECAST, now) <= PRE_EQUIP_SEC then",
                "            want, set = 'flashbulb', sets.midcast.Pet.Enmity",
            ]
        if has_ws:
            cond += ["        %sif (pet.tp or 0) >= PET_WS_TP then" % ("else" if has_en else ""),
                     "            want, set = 'ws', pet_ws_set()"]
        top += cond + ["        end",
                       "    end",
                       "    if not want and not pet_gear then return end",
                       L("    -- 出そうなあいだは毎回着直す (本体の行動のあと、Mote が戦闘中の装備に戻すため。変わった部位だけ送られる)",
                         "    -- Re-equip every tick while pending (Mote reverts to engaged gear after your actions; only changed slots are sent)"),
                       "    if want ~= pet_gear then pet_gear_since = now end",
                       "    pet_gear = want",
                       "    if set then equip(set) else handle_equipping_gear(player.status); restore_main() end",
                       "end",
                       "",
                       L("-- 1 秒に 1 回だけ見る (毎フレームは重いので)", "-- Check once per second (every frame is too heavy)"),
                       "local pet_last_tick = 0",
                       "windower.raw_register_event('prerender', function()",
                       "    local now = os.time()",
                       "    if now == pet_last_tick then return end",
                       "    pet_last_tick = now",
                       "    send_command('gs c pet_tick')",
                       "end)",
                       "",
                       L("-- オートマトンのストロボ・フラッシュバルブが出た時刻を覚える (再使用の計算に使う)",
                         "-- Track when the automaton used Strobe / Flashbulb (for the recast timers)"),
                       "windower.raw_register_event('action', function(act)",
                       "    if act.category ~= 11 or (act.param ~= ABIL_PROVOKE and act.param ~= ABIL_FLASHBULB) then return end",
                       "    local my_pet = windower.ffxi.get_mob_by_target('pet')",
                       "    if not my_pet or act.actor_id ~= my_pet.id then return end",
                       "    if act.param == ABIL_PROVOKE then strobe_time = os.time() else flashbulb_time = os.time() end",
                       "end)",
                       ""]
        out["setup"] = [L("    -- オートマトンの技の装備を、先に着ておくか (//gs c toggle PetAutoGear)",
                          "    -- Pre-equip automaton move gear (//gs c toggle PetAutoGear)"),
                        "    state.PetAutoGear = M(true, 'PetAutoGear')"]
        out["cmds"] = [L("    -- //gs c pet_tick: 1 秒ごとの事前着替え (自動で送られます)",
                         "    -- //gs c pet_tick: per-second pre-equip check (sent automatically)"),
                       "    if cmdParams[1] == 'pet_tick' then",
                       "        pet_auto_gear()",
                       "        eventArgs.handled = true",
                       "        return",
                       "    end"]
    out["top"] = top
    return out


# --- 属性帯 (八輪の帯) とオルペウスサッシュの自動選択 (精霊魔法) ---
# 効果量: 天候 ±10% (強天候 ±25%)・曜日 ±10% (FF11用語辞典 html/2218)。オルペウスサッシュは対象との距離で +15〜+1%
# (1.93 ヤルム以内で +15、13 以上で +1、あいだは直線。作者が使ってきた値・BG-Wiki)。効果の大きいほうを着る。
IMMANENCE_SET = "sets.buff['Immanence']"


def waist_blocks(emitted, enabled):
    """戻り値: dict(top, post_midcast)。enabled でなければ空。震天動地の章が効いている間は腰を替えず、
    震天動地の章の装備 (sets.buff['Immanence']) を最後に着直す (最優先)。"""
    out = dict(top=[], post_midcast=[])
    has_imm = IMMANENCE_SET in emitted
    imm = ([L("    -- 震天動地の章の装備を最優先 (ほかの装備の上から、最後に着る)",
              "    -- Immanence gear has top priority (equipped last, over everything else)"),
            L("    if (buffactive['震天動地の章'] or buffactive['Immanence']) and spell.action_type == 'Magic' then",
              "    if buffactive['Immanence'] and spell.action_type == 'Magic' then"),
            "        equip(%s)" % IMMANENCE_SET,
            "    end"] if has_imm else [])
    if not enabled:
        out["post_midcast"] = imm
        return out
    head_ja = [
        "-- 属性帯 (八輪の帯) とオルペウスサッシュ: 精霊魔法のダメージが大きくなるほうの腰を、詠唱中に着ます",
        "-- 天候 (学者の陣を含む) ±10% (強天候 ±25%)・曜日 ±10%。オルペウスサッシュは対象に近いほど +15%〜+1%",
        "local OBI, ORPHEUS = {waist = '八輪の帯'}, {waist = 'オルペウスサッシュ'}",
        "local WEAKER = {['火'] = '水', ['水'] = '雷', ['雷'] = '土', ['土'] = '風', ['風'] = '氷', ['氷'] = '火', ['光'] = '闇', ['闇'] = '光'}",
        "local EN_JA = {Fire = '火', Water = '水', Lightning = '雷', Thunder = '雷', Earth = '土', Wind = '風', Ice = '氷', Light = '光', Dark = '闇'}",
        "local function ja_element(e) return EN_JA[e] or e end",
        "",
        "-- 帯を着たときの効果 (%)。属性の無いものは nil"]
    # 英語クライアント: 名前・属性は英語だけ (res/items.lua・res/elements.lua の en)。関数名 ja_element は下の行と共通にするため残す
    head_en = [
        "-- Hachirin-no-Obi vs. Orpheus's Sash: in midcast, wear whichever waist gives more elemental magic damage.",
        "-- Weather (incl. SCH storms) +/-10% (double weather +/-25%), day +/-10%. Orpheus's Sash: +15% up close down to +1%.",
        "local OBI, ORPHEUS = {waist = 'Hachirin-no-Obi'}, {waist = \"Orpheus's Sash\"}",
        "local WEAKER = {Fire = 'Water', Water = 'Lightning', Lightning = 'Earth', Earth = 'Wind', Wind = 'Ice', Ice = 'Fire', Light = 'Dark', Dark = 'Light'}",
        "local EN_JA = {Thunder = 'Lightning'}   -- normalize element names",
        "local function ja_element(e) return EN_JA[e] or e end",
        "",
        "-- Obi bonus (%), or nil for non-elemental spells"]
    out["top"] = (head_en if is_en() else head_ja) + [
        "local function obi_bonus(element)",
        "    local e = ja_element(element)",
        "    if not WEAKER[e] then return nil end",
        "    local b = 0",
        "    local we = ja_element(world.weather_element)",
        "    local power = ({[1] = 10, [2] = 25})[tonumber(world.weather_intensity) or 0] or 0",
        "    if we == e then b = b + power elseif we == WEAKER[e] then b = b - power end",
        "    local de = ja_element(world.day_element)",
        "    if de == e then b = b + 10 elseif de == WEAKER[e] then b = b - 10 end",
        "    return b",
        "end",
        "",
        L("-- オルペウスサッシュの効果 (%)。距離が分からなければ nil",
          "-- Orpheus's Sash bonus (%), or nil if distance is unknown"),
        "local function orpheus_bonus(distance)",
        "    distance = tonumber(distance)",
        "    if not distance then return nil end",
        "    if distance <= 1.93 then return 15 end",
        "    if distance >= 13 then return 1 end",
        "    return 15 - 14 * (distance - 1.93) / (13 - 1.93)",
        "end",
        "",
        L("-- 効果の大きいほうの腰。同じなら、対象が動いても変わらない帯。どちらも効果が無ければ nil (セットの腰のまま)",
          "-- Pick the better waist; ties go to the Obi (unaffected by distance). nil = keep the set's waist"),
        "local function elemental_waist(spell)",
        "    local ob = obi_bonus(spell.element)",
        "    if not ob then return nil end",
        "    local orp = orpheus_bonus(spell.target and spell.target.distance)",
        "    if ob > 0 and (not orp or ob >= orp) then return OBI end",
        "    return orp and ORPHEUS or nil",
        "end",
        ""]
    post = [L("    -- 腰の自動選択 (震天動地の章が効いている間は替えない)",
              "    -- Auto waist (skipped while Immanence is up)"),
            L("    if spell.action_type == 'Magic' and not buffactive['震天動地の章'] and not buffactive['Immanence'] then",
              "    if spell.action_type == 'Magic' and not buffactive['Immanence'] then"),
            L("        local nuke = (spell.skill == '精霊魔法' or spell.skill == 'Elemental Magic') and spellMap ~= 'ElementalEnfeeble'",
              "        local nuke = spell.skill == 'Elemental Magic' and spellMap ~= 'ElementalEnfeeble'"),
            "            and spell.english ~= 'Impact'",
            "        if nuke or spell.english == 'Meteor' then",
            "            local w = elemental_waist(spell)",
            "            if w then equip(w) end",
            "        elseif spellMap == 'Cure' or spellMap == 'Curaga' then",
            "            local ob = obi_bonus(spell.element)",
            L("            if ob and ob > 0 then equip(OBI) end   -- 回復魔法: 天候・曜日でプラスのときだけ",
              "            if ob and ob > 0 then equip(OBI) end   -- cures: only when weather / day is favorable"),
            "        end",
            "    end"]
    out["post_midcast"] = post + imm
    return out


# --- 狩人・コルセアの遠隔攻撃、コルセアのロールとクイックドロー ---
# 名前は作者の COR_gear.lua と同じ (sets.RA_STP など)。出したら、Mote-Include が探す名前に結ぶ
COR_QD_SETS = [("sets.RA_QDSTP", "ソーティ", "StoreTP"), ("sets.RA_QDDPS", "通常", "Damage")]
COR_QD_ACC_SHOTS = [("Light Shot", "ライトショット"), ("Dark Shot", "ダークショット")]


def ranged_links(emitted):
    """{出したセット: [結ぶ先のパス]}。結ぶ先は、出した直後に `先 = セット` の行で作る (ロールごとのセットなどを、その上に重ねるため)。"""
    links = {"sets.RA_STP": ["sets.midcast.RA"], "sets.RA_ACC": ["sets.midcast.RA.Acc"],
             "sets.CorsairRoll": ["sets.precast.CorsairRoll"]}
    qd = [p for p, _ja, _en in COR_QD_SETS if p in emitted]
    if qd:
        links[qd[0]] = ["sets.precast.CorsairShot"]      # 既定のクイックドローは STP (無ければ威力)
    return {k: v for k, v in links.items() if k in emitted}


def cor_blocks(emitted):
    """遠隔攻撃のモードと、コルセアのクイックドローの切り替えの Lua。戻り値: dict(setup, post_precast, init_tail)。"""
    out = dict(setup=[], post_precast=[], init_tail=[])
    qd = [(p, L(ja, en)) for p, ja, en in COR_QD_SETS if p in emitted]
    if len(qd) == 2:
        names = ", ".join("'%s'" % n for _p, n in qd)
        out["setup"] += [L("    -- //gs c cycle QuickDrawMode で、クイックドローの装備を切り替えます (%s)" % names.replace("'", ""),
                           "    -- //gs c cycle QuickDrawMode switches Quick Draw gear (%s)" % names.replace("'", "")),
                         "    state.QuickDrawMode = M{['description']='QuickDrawMode', %s}" % names]
        out["init_tail"] += [L("    -- //gs c cycle QuickDrawMode で切り替えるクイックドローの装備 (job_post_precast で着る)",
                               "    -- Quick Draw sets for //gs c cycle QuickDrawMode (worn in job_post_precast)"),
                             "    sets.QuickDraw = {"]
        out["init_tail"] += ["        ['%s'] = %s," % (n, p) for p, n in qd] + ["    }"]
        out["post_precast"] = [
            L("    -- クイックドロー: QuickDrawMode の装備を着る (ライトショット・ダークショットは魔命の装備のまま)",
              "    -- Quick Draw: wear the QuickDrawMode set (Light Shot / Dark Shot keep their accuracy set)"),
            "    if spell.type == 'CorsairShot' and spell.english ~= 'Light Shot' and spell.english ~= 'Dark Shot'",
            "        and sets.QuickDraw and sets.QuickDraw[state.QuickDrawMode.value] then",
            "        equip(sets.QuickDraw[state.QuickDrawMode.value])",
            "    end"]
    if "sets.RA_QDACC" in emitted:
        out["init_tail"] += [L("    -- ライトショット・ダークショットは、魔命の装備で撃つ",
                               "    -- Light Shot and Dark Shot use the magic accuracy set"),
                             "    sets.precast.CorsairShot = sets.precast.CorsairShot or {}"]
        for en, ja in COR_QD_ACC_SHOTS:
            out["init_tail"].append("    %s = sets.RA_QDACC" % make_key("sets.precast.CorsairShot", en))
            if not is_en():     # 日本語名で探す改造版の Mote-Include 用
                out["init_tail"].append("    %s = sets.RA_QDACC" % make_key("sets.precast.CorsairShot", ja))
    if out["init_tail"]:
        out["init_tail"].append("")
    return out


def ws_base(path, emitted):
    """技ごとの WS (sets.precast.WS['英語名']) を重ねる元のセット。魔法属性 → WS.Magic・遠隔 → WS.Range・ほか → WS (共通)。"""
    prefix = "sets.precast.WS['"
    if not (path.startswith(prefix) and path.endswith("']")):
        return None
    en = path[len(prefix):-2].replace("\\'", "'")
    kind = WS.kind_of(en)
    # 遠隔魔攻のセットが無ければ魔攻のセット、それも無ければ共通の WS に重ねる
    chain = {"RangeMagic": ["RangeMagic", "Magic"]}.get(kind, [kind] if kind else [])
    for cand in ["sets.precast.WS.%s" % k for k in chain] + ["sets.precast.WS"]:
        if cand and cand in emitted:
            return cand
    return None


def build_lua(job, assignments, include_weapons=False, title=None, aliases=None, weapons=None, buffs=None, lockstyle=None,
              received_manual=(), ammo=None, ws_ammo=None, pld_three_stage=False, pld_fast_cast=0, pup_auto=False,
              auto_waist=False):
    """assignments: {path: {slot: Item}}。空のセットは出さない。
    aliases: {別名のパス: 元のパス}。元のセットが出力されるときだけ、`別名 = 元` の行を足す
    (標準の Mote-Include は技の名前を英語で探し、日本語名に改造したものは日本語で探す。両方で動くようにする)。
    weapons: {main/sub/range: [Item, ...]}。あれば、//gs c cycle MainWeapons などで持ち替える仕組みを足す。
    buffs: [(sets.buff のセットのパス, バフ番号, 英語名, 日本語名)]。あれば、効果中ずっと着る装備を重ねる仕組みを足す。"""
    used = {p: s for p, s in assignments.items() if s}
    # バ系の魔法は強化魔法の装備に重ねるので、その後に出す
    order = sorted(used, key=lambda p: (_depth(p) + (1 if p == "sets.midcast.BarElement" else 0), p.endswith("]"),
                                        list(assignments).index(p)))
    out = []
    if is_en():
        weapons_note = ("included in the sets." if include_weapons else
                        "left out of the sets (swapping weapons resets TP). Add main= etc. to a set if you need it.")
        out.append(HEADER_EN.format(title=title or ("GearSwap for %s" % job), job=job,
                                    date=datetime.date.today().isoformat(), weapons=weapons_note,
                                    weapon_slots="main / sub / range" if ammo_as_gear(job) else "main / sub / range / ammo"
                                    ).rstrip('\n'))
    else:
        weapons_note = ("セットに含めています。" if include_weapons else
                        "セットに含めていません (武器を替えるとTPが消えるため)。必要なら、装備の行に main= などを足してください。")
        out.append(HEADER_JA.format(title=title or ("%s 用 GearSwap" % job), job=job,
                                    date=datetime.date.today().isoformat(), weapons=weapons_note,
                                    weapon_slots="メイン・サブ・遠隔" if ammo_as_gear(job) else "メイン・サブ・遠隔・矢弾").rstrip('\n'))
    out.append("")
    weapon_top, weapon_setup, weapon_cmds = weapon_blocks(weapons)
    if weapon_top:
        out.extend(weapon_top)
    lock_setup, lock_init, lock_cmds = lockstyle_blocks(lockstyle)
    ammo_top, ammo_pre, ammo_after, ammo_setup, ammo_cmds = ammo_blocks(ammo, ws_ammo)
    out.extend(ammo_top)       # job_self_command より前に (local の ammo を使うため)
    # 武器の切り替えがあるスロットは、セットに入れない (Mote は cycle の後に装備を作り直すので、セットの武器で上書きされる)
    cycle_slots = {slot for slot, items in (weapons or {}).items() if items}
    if ammo_top:
        cycle_slots.add("ammo")     # 矢弾は使い分けの仕組みで替えるので、セットには入れない
    keep_slots = ("ammo",) if ammo_as_gear(job) and "ammo" not in cycle_slots else ()

    def keep_for(path):
        # ナイトの対魔法・状態異常耐性は、メインとサブ (マリグナスソード・イージスなど) も着替える
        if job == "PLD" and path in PLD_WEAPON_SETS:
            return tuple(keep_slots) + ("main", "sub")
        # からくり士のオートマトンの WS は、メイン (シュコアトルなど) も持ち替える (乾坤圏のときは Lua の側で替えない)
        if job == "PUP" and path == PUP_WS_SET:
            return tuple(keep_slots) + ("main",)
        # からくり士のマニューバは、メイン (乾坤圏など、マニューバを強化する武器) も持ち替える
        if job == "PUP" and path == "sets.precast.JA.Maneuver":
            return tuple(keep_slots) + ("main",)
        # 受ける強化の装備と魔法のファランクスは、武器も持ち替える (ナイトの剣・盾のファランクス+ など。TP を減らしたくなければ、export か Lua から外す)
        if path.startswith("sets.midcast.Increased") or path == PHALANX_SET:
            return tuple(keep_slots) + ("main", "sub", "range")
        # 睡眠から起きる装備は、プライムウェポン (武器) も持ち替える
        if path == "sets.Sleep":
            return tuple(keep_slots) + ("main", "sub", "range")
        return keep_slots
    emitted_paths = {p for p in used if set_lines(p, used[p], include_weapons, cycle_slots=cycle_slots, keep_slots=keep_for(p))}
    pld = pld_blocks(emitted_paths, pld_three_stage, pld_fast_cast) if job == "PLD" else pld_blocks(set())
    out.extend(pld["top"])     # job_self_command より前に (local の land_set を使うため)
    pup = pup_blocks(emitted_paths, pup_auto) if job == "PUP" else pup_blocks(set())
    out.extend(pup["top"])     # job_self_command より前に (local の pet_auto_gear を使うため)
    man = maneuver_blocks(emitted_paths) if job == "PUP" else maneuver_blocks(set())
    out.extend(man["top"])
    waist = waist_blocks(emitted_paths, auto_waist)
    out.extend(waist["top"])
    cor = cor_blocks(emitted_paths)
    links = ranged_links(emitted_paths)
    # 受ける強化: job_self_command に武器を覚える・着直すコマンドを入れるので、先に作る
    recv_weapons = any(p.startswith("sets.midcast.Increased") and set(used[p]) & {"main", "sub", "range"}
                       for p in emitted_paths)
    recv_top, recv_reg, recv_mid, recv_cmds, recv_after = received_blocks(emitted_paths, received_manual, recv_weapons)
    cmds = weapon_cmds + lock_cmds + ammo_cmds + pld["cmds"] + pup["cmds"] + recv_cmds
    if cmds:
        out.append("function job_self_command(cmdParams, eventArgs)")
        out.extend(cmds)
        out.append("end")
        out.append("")
    # 学者: 陣頭指揮の足は、陣の魔法の詠唱の開始と詠唱中に履く (マクロの部位着替えと同じ。ファストキャストの装備の上から)
    # 魔法のファランクス: 剣・盾を持ち替えるときは、唱える前の武器を覚えて、唱えたあとに戻す
    # (待機・戦闘中のセットには武器を入れていないので、行動の後の着替えだけでは武器が戻らないため)
    phalanx_weapons = PHALANX_SET in emitted_paths and bool(set(used[PHALANX_SET]) & {"main", "sub", "range"})
    phalanx_mid = ([L("    -- 魔法のファランクスで剣・盾を持ち替えるので、持ち替える前の武器を覚える",
                      "    -- Phalanx swaps sword / shield, so remember the weapons from before"),
                    "    if spell.english == 'Phalanx' then",
                    "        phalanx_weapons = phalanx_weapons or {main = player.equipment.main, sub = player.equipment.sub, range = player.equipment.range}",
                    "    end"] if phalanx_weapons else [])
    phalanx_after = ([L("    -- 魔法のファランクスを唱えたあとは、持ち替える前の武器に戻す",
                        "    -- After Phalanx, go back to the weapons from before"),
                      "    if phalanx_weapons and spell.english == 'Phalanx' then",
                      "        equip(phalanx_weapons)",
                      "        phalanx_weapons = nil",
                      "    end"] if phalanx_weapons else [])
    storm = "sets.Stormsurge" in emitted_paths
    storm_lines = ([L("    -- 陣の魔法では、ファストキャストなどの装備の上から、陣頭指揮の足を履く",
                      "    -- Storm spells: wear the Stormsurge feet over fast cast gear"),
                    "    if spellMap == 'Storm' then equip(sets.Stormsurge) end"] if storm else [])
    toggles = pld["toggles"] + [tg for tg in (TH_TOGGLE, KB_TOGGLE) if tg[2] in emitted_paths]
    status = [s for s in STATUS_OVERLAYS if s[2] in emitted_paths]
    buff_top, buff_setup, buff_reg = overlay_blocks(buffs, emitted_paths, job, toggles, dual=True, status=status,
                                                    low_hp="sets.LowHp" in emitted_paths, sleep="sets.Sleep" in emitted_paths,
                                                    weapon_cycle=bool(weapon_setup))
    if buff_top:
        out.extend(buff_top)
    out.extend(ws_blocks(emitted_paths, job))
    out.extend(recv_top)
    has_cast = "local function equip_cast_gear(phase, spell)" in "\n".join(buff_top)
    # クイックドローの装備は、矢弾 (ammo_pre) より先に着る (弾は使い分けの仕組みで替える)
    post_pre = ((["    equip_cast_gear('precast', spell)"] if has_cast else []) + cor["post_precast"] + ammo_pre + man["post_precast"]
                + storm_lines)
    holy = ([L("    -- 聖水を使うときは、被カーズナ (聖水の効果アップ) の装備を着る",
                "    -- Holy Water: wear the Cursna-received gear (Holy Water +)"),
              "    if spell.action_type == 'Item' and (spell.english == 'Holy Water'%s) then" % ("" if is_en() else " or spell.name == '聖水'"),
              "        equip(sets.midcast.IncreasedCursna)",
              "    end"] if "sets.midcast.IncreasedCursna" in emitted_paths else [])
    other = ([L("    -- ほかの人への強化魔法: ほかの人への装備を着て、魔法ごとの装備 (リフレシュなど) があれば、その上から着る",
                "    -- Enhancing on others: wear the Other set, with any spell-specific set over it"),
              "    if spell.skill == '%s' and spell.target and spell.target.type ~= 'SELF' then" % ("Enhancing Magic" if is_en() else "強化魔法"),
              "        local own = get_midcast_set(spell, spellMap)",
              "        if own and own ~= sets.midcast['%s'] then" % ("Enhancing Magic" if is_en() else "強化魔法"),
              "            equip(set_combine(sets.midcast['%s'].Other, own))" % ("Enhancing Magic" if is_en() else "強化魔法"),
              "        else",
              "            equip(sets.midcast['%s'].Other)" % ("Enhancing Magic" if is_en() else "強化魔法"),
              "        end",
              "    end"] if "sets.midcast['強化魔法'].Other" in emitted_paths else [])
    entrust = ([L("    -- エントラスト中に、ほかの人へインデ魔法をかけるときは、エントラストの装備",
                   "    -- Indi spell on someone else under Entrust: wear the Entrust set"),
                 "    if (buffactive['Entrust']%s) and spell.english:sub(1, 5) == 'Indi-' and spell.target.type ~= 'SELF' then"
                 % ("" if is_en() else " or buffactive['エントラスト']"),
                 "        equip(sets.midcast.Entrust)",
                 "    end"] if job == "GEO" and "sets.midcast.Entrust" in emitted_paths else [])
    post_mid = ((["    equip_cast_gear('midcast', spell)"] if has_cast else []) + phalanx_mid + recv_mid + pld["post_midcast"] + storm_lines
                + waist["post_midcast"] + entrust + other)
    post_pre = post_pre + holy
    if post_pre:
        out += ["function job_post_precast(spell, action, spellMap, eventArgs)"] + post_pre + ["end", ""]
    if post_mid:
        out += ["function job_post_midcast(spell, action, spellMap, eventArgs)"] + post_mid + ["end", ""]
    after = ammo_after + pld["aftercast"] + man["aftercast"] + recv_after + phalanx_after
    if after:
        out += ["function job_post_aftercast(spell, action, spellMap, eventArgs)"] + after + ["end", ""]
    # 装備のセットを作ったあとに行う登録 (after_gear_sets) は、中身が決まってから、ここに差し込む
    after_at = len(out)
    out.append("function get_sets()")
    out.append("    mote_include_version = 2")
    out.append(L("    include('Mote-Include.lua')   -- この中で ジョブ_gear.lua (あれば) を読み、init_gear_sets を呼びます",
                 "    include('Mote-Include.lua')   -- loads JOB_gear.lua (if any) and calls init_gear_sets"))
    if not is_en():     # 英語クライアントは既定 (英語) のまま
        out.append("    set_language('japanese')")
    call_at = len(out)
    out.append("end")
    out.append("")
    out.append("function job_setup()")
    out.append("end")
    out.append("")
    out.append("function user_setup()")
    # モードの切り替え: セットがあるモードだけを選択肢にする
    for field, base, modes in (("IdleMode", "sets.idle", ("DT", "Refresh", "Tate")),
                               ("OffenseMode", "sets.engaged", ("Acc", "SubtleBlow", "Parry", "Enn", "Tate", "PetSTP")),
                               ("HybridMode", "sets.engaged", ("DT",)),
                               ("CastingMode", "sets.midcast['精霊魔法']", ("MB", "Acc")),
                               ("RangedMode", "sets.midcast.RA", ("Acc", "Critical"))):
        linked = {tg for ts in links.values() for tg in ts}
        have = [m for m in modes if "%s.%s" % (base, m) in used or "%s.%s" % (base, m) in linked]
        if have:
            opts = ["Normal"] + have
            what = {"IdleMode": ("待機", "idle"), "CastingMode": ("精霊魔法 (MB = マジックバースト)", "elemental nuke (MB = magic burst)")}.get(
                field, ("戦闘中", "engaged"))
            out.append(L("    -- //gs c cycle %s で、%sの装備を切り替えます (%s)" % (field, what[0], " / ".join(opts)),
                         "    -- //gs c cycle %s switches %s gear (%s)" % (field, what[1], " / ".join(opts))))
            out.append("    state.%s:options(%s)" % (field, ", ".join("'%s'" % o for o in opts)))
    out.extend(weapon_setup)
    out.extend(buff_setup)
    out.extend(lock_setup)
    out.extend(ammo_setup)
    out.extend(cor["setup"])
    out.extend(pup["setup"])
    out.extend(man["setup"])
    out.append("end")
    out.append("")
    out.extend(GEAR_SECTION_BEGIN(job))
    out.append("function init_gear_sets()")
    out.extend(lock_init)
    if any(p.startswith(MERIT_BASE + ".") for p in emitted_paths):
        out.append("    %s = {}" % MERIT_BASE)
        out.append("")
    # 入れ物の用意: 種類のセットの中の技 (sets.precast.CorsairRoll['…'] など) は、種類のセットが無いと書けないので、
    # 無ければ空のセットを作る (Mote-Include が作る sets.precast.JA・sets.buff などは除く)
    parents = []
    for p in sorted(emitted_paths, key=_depth):
        par = _parent(p)
        if par and par not in MOTE_TABLES and par not in emitted_paths and par not in parents:
            parents.append(par)
    for par in parents:
        out.append("    %s = %s or {}" % (par, par))
    if parents:
        out.append("")
    emitted = set()
    for p in order:
        par = _parent(p)
        base = par if (p.endswith("]") and par in emitted and par not in MOTE_TABLES) else None
        base = base or ws_base(p, emitted)
        if not base and p == "sets.midcast.BarElement" and "sets.midcast['強化魔法']" in emitted:
            base = "sets.midcast['強化魔法']"
        # ケアルの詠唱の開始は、ファストキャストに重ねる (ケアル詠唱時間短縮の部位だけ替えればよいように)
        if not base and p == "sets.precast.FC.Cure" and "sets.precast.FC" in emitted:
            base = "sets.precast.FC"
        # マジックバースト・魔命重視は、精霊魔法の装備に重ねる。遠隔攻撃 (クリティカル) は遠隔攻撃に重ねる
        if not base and p in ("sets.midcast['精霊魔法'].MB", "sets.midcast['精霊魔法'].Acc") and "sets.midcast['精霊魔法']" in emitted:
            base = "sets.midcast['精霊魔法']"
        if not base and p == "sets.midcast.RA.Critical" and "sets.midcast.RA" in emitted:
            base = "sets.midcast.RA"
        # ほかの人への強化は、強化魔法の装備に重ねる
        if not base and p == "sets.midcast['強化魔法'].Other" and "sets.midcast['強化魔法']" in emitted:
            base = "sets.midcast['強化魔法']"
        if job == "PLD":
            base = base or pld_base(p, emitted)
        # 結ぶ先と同じ名前のセット (アビリティ強化の装備の sets.precast.CorsairRoll など) は、結んだ元に重ねる
        src = next((s for s, ts in links.items() if p in ts), None)
        if not base and src in emitted:
            base = src
        lines = set_lines(p, used[p], include_weapons, base, cycle_slots, keep_for(p))
        if lines:
            emitted.add(p)
            # Mote-Include が探す名前に結ぶ (sets.midcast.RA = sets.RA_STP など)。ロールごとのセットは、結んだ先に重ねる
            for target in links.get(p, []):
                lines = lines[:-1] + ["    %s = %s" % (target, p), ""]
                emitted.add(target)
        out.extend(lines)
    # 英語クライアント用の出力には、日本語名の別名を出さない
    alias_lines = [] if is_en() else ["    %s = %s" % (a, target) for a, target in (aliases or {}).items() if target in emitted]
    # 召喚士: 作っていないセットを、ほかのセットで代わりにする (作者の SMN_gear.lua と同じ組み方)
    if job == "SMN":
        for target, source, why, why_en in (
                ("sets.precast.BloodPactRage", "sets.precast.BloodPactWard", "幻術の履行も、履行の短縮の装備で使う",
                 "Blood Pact: Rage uses the BP delay gear too"),
                ("sets.midcast.Pet.AvatarBuffWard", "sets.SmnSkill", "強化の履行は、召喚魔法スキルの装備で実行する",
                 "buff wards use summoning skill gear"),
                ("sets.idle.Pet", "sets.idle.Avatar", "召喚獣がいるときの待機 (Mote は sets.idle.Pet を見る)",
                 "idle with an avatar out (Mote looks for sets.idle.Pet)")):
            if source in emitted and target not in emitted:
                alias_lines.append("    %s = %s   -- %s" % (target, source, L(why, why_en)))
    # 風水士: 羅盤がいるときの待機 (Mote は、ペットがいると sets.idle.Pet を見る)
    if job == "GEO" and "sets.idle.Luopan" in emitted and "sets.idle.Pet" not in emitted:
        alias_lines.append("    sets.idle.Pet = sets.idle.Luopan   -- %s" % L("羅盤がいるときの待機", "idle with a luopan out"))
    # アスピル: 日本語名で探す改造版の Mote はドレインと同じ系統 (Drain)、標準の Mote は Aspir で探す
    if "sets.midcast.Drain" in emitted and "sets.midcast.Aspir" not in emitted:
        alias_lines.append("    sets.midcast.Aspir = sets.midcast.Drain   -- %s" % L("アスピルも、ドレインの装備で唱える",
                                                                                "Aspir uses the Drain gear"))
    if out[-1] == "":
        out.pop()
    out.append("end")
    out.extend(GEAR_SECTION_END())
    out.append("")
    # 装備のセットを作ったあとに行う登録。init_gear_sets には入れない
    # (init_gear_sets を ジョブ_gear.lua に写したとき、このファイルの local (buff_gear など) が見えずに止まるため)
    post = []
    if alias_lines:
        post.append(L("    -- 日本語名の別名 (標準の Mote-Include は英語名で、日本語名で探す改造版は日本語名で、セットを探します)",
                      "    -- Fallback sets"))
        post.extend(alias_lines)
        post.append("")
    post += buff_reg + recv_reg + pld["init_tail"] + cor["init_tail"]
    while post and post[-1] == "":
        post.pop()
    if post:
        out.insert(call_at, "    after_gear_sets()")
        out[after_at:after_at] = [
            L("-- 装備のセットを作ったあとに行う登録です (get_sets から呼びます)。ジョブ_gear.lua には写さないでください。",
              "-- Registration done after the gear sets are built (called from get_sets). Do not copy this into JOB_gear.lua."),
            "function after_gear_sets()"] + post + ["end", ""]
    out[1:1] = SYSTEM_SECTION_NOTE(job)
    text = "\n".join(out)
    # 英語クライアント: キーのスキル名を英語に (中で比べている sets.midcast['強化魔法'] などを壊さないよう、最後に置き換える)
    return _en_skill_keys(text) if is_en() else text
