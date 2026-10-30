# -*- coding: utf-8 -*-
"""The kit's work state (which export is assigned to which set). Independent of the UI, so it can be tested.

Assignments, per-skill additions and weapon cycles are stored **separately for each job** (nothing registered on SMN shows up on COR).
"""
import datetime
import json
import os
import shutil
import tempfile
import time

import choices as CH
import export_parser as EP
from i18n import L, is_en
import generator as G
import resdb as R
import set_catalog as C

# Kinds of per-skill additions (same order as C.CUSTOM_KINDS) and the res table each one looks up
KIND_KEYS = ["ws", "ja", "magic", "pet", "received"]
RECEIVED_KIND = 4                 # received-buff gear (sets.midcast.IncreasedPhalanx etc.; attached with . rather than [ ])
JA_KIND = 1                       # Position of "Job ability" in KIND_KEYS / C.CUSTOM_KINDS
BUFF_BASE = "sets.buff"
BUFF_HELP = ("アビリティの強化が付いている間、着たままにする装備です。強化が付くと待機と戦闘中の装備に重ねて着て、"
             "切れると元に戻ります (アビリティ強化の装備から追加したものです)。")
MERIT_HELP = ("メリットポイントで覚える特性 (最適化・微調整など) を強化する装備です。メリットポイントを振っていないと効果が無いので、"
              "初めは使いません。振ってあるときだけ、ゲームで //gs c cycle MeritGear を押して On にすると、"
              "待機と戦闘中の装備に重ねて着ます (からくり士・竜騎士は、ペットを出している間だけ)。")
BUFF_HELP_EN = ("Gear kept on while the ability's effect is active. It's layered over your idle and engaged sets when the "
                "buff starts and removed when it wears off (added from the ability gear list).")
MERIT_HELP_EN = ("Gear that enhances a merit trait (Optimization, Fine-Tuning, etc.). It does nothing unless you've put merits "
                 "into that trait, so it starts off. If you have, use //gs c cycle MeritGear in game to turn it On and it's "
                 "layered over your idle and engaged sets (for PUP and DRG, only while your pet is out).")
# English display names for grouped sets that aren't in the list (set_path in ability_gear.json)
SPECIAL_SET_TITLES_EN = {"sets.Stormsurge": "Stormsurge feet (when casting storm spells)"}


def atomic_write(path, text, newline=None):
    """Write to a temporary file in the same folder, then swap it in. A crash mid-write never leaves the current file empty."""
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".gsk_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline=newline) as f:
            f.write(text)
        for i in range(5):
            try:
                os.replace(tmp, path)
                break
            except PermissionError:
                if i == 4:
                    raise
                time.sleep(0.1)  # antivirus or sync software can hold the target file for a moment
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def _key_name(path):
    """Name from sets.x['Name'] (empty string if there is none)."""
    if path.endswith("']") and "['" in path:
        return path[path.index("['") + 2:-2].replace("\\'", "'").replace("\\\\", "\\")
    return ""


_SET_ABILITY_EN = None


def _ability_en_for_set(path):
    """English name of the ability whose set_path in ability_gear.json is this path (None if there is none)."""
    global _SET_ABILITY_EN
    if _SET_ABILITY_EN is None:
        import ability_gear as AG
        _SET_ABILITY_EN = {}
        for lst in AG.load().values():
            for e in lst:
                if e.get("set_path"):
                    _SET_ABILITY_EN.setdefault(e["set_path"], e.get("ability_en"))
    return _SET_ABILITY_EN.get(path)


def _split_camel(s):
    """FineTuning → Fine Tuning"""
    return "".join((" " + ch if ch.isupper() and i else ch) for i, ch in enumerate(s))


class JobData:
    """Work state for a single job."""

    def __init__(self):
        self.assignments = {}      # path -> {slot: Item}
        self.custom = []           # [(path, display name, path of the Japanese-name alias or None)]  per-skill additions
        self.weapons = {}          # slot (main/sub/range) -> [Item, ...]  weapon cycle
        self.buffs = {}            # sets.buff path -> (buff id, English name, Japanese name)  gear kept on while the buff is active
        self.lockstyle = None      # lockstyle number (the in-game equipment set number). None means lockstyle isn't used
        self.received_manual = set()   # received-buff gear that isn't swapped in automatically (e.g. {"IncreasedPhalanx"})
        self.ammo = {}             # ammo role (physical/magical/quickdraw) -> Item  (RNG, COR)
        self.ws_ammo = {}          # WS English name -> Item  special ammo (used only for that WS)
        self.three_stage = False   # PLD: use the three-stage swap (Fast Cast -> spell interruption -> landing gear)
        self.fast_cast = 0         # PLD: gear Fast Cast (%) used for the three-stage swap timing
        self.pup_auto = False      # PUP: equip automaton weapon skill gear ahead of time (automatic pre-swap)
        self.auto_waist = False    # elemental magic: automatically pick the elemental obi (Hachirin-no-Obi) or Orpheus's Sash


class Project:
    def __init__(self, job="SMN"):
        self.job = job
        self.include_weapons = False
        self.resdb = None          # res used to look up English names from Japanese ones (works without it)
        self._jobs = {}            # job abbreviation -> JobData

    # --- Jobs ---
    def _cur(self):
        return self._jobs.setdefault(self.job, JobData())

    @property
    def assignments(self):
        return self._cur().assignments

    @property
    def custom(self):
        return self._cur().custom

    @custom.setter
    def custom(self, value):
        self._cur().custom = value

    @property
    def weapons(self):
        return self._cur().weapons

    @property
    def lockstyle(self):
        return self._cur().lockstyle

    def set_lockstyle(self, value):
        """Set the lockstyle number: an integer from 1 to 200 (a string is fine). Empty or out of range means none (None). Returns the number set, or None."""
        try:
            n = int(str(value).strip())
        except (TypeError, ValueError):
            n = None
        if n is not None and not (1 <= n <= 200):
            n = None
        self._cur().lockstyle = n
        return n

    def set_received_auto(self, name, auto):
        """Whether received-buff gear (name = IncreasedPhalanx etc.) is swapped in automatically in response to spells."""
        if auto:
            self._cur().received_manual.discard(name)
        else:
            self._cur().received_manual.add(name)

    def received_auto(self, name):
        return name not in self._cur().received_manual

    def set_job(self, job):
        """Switch jobs. Assignments are kept per job, so other jobs' contents don't show up (switching back restores them)."""
        self.job = job

    def has_work(self, job):
        """Whether the job has any assignments, additions or weapons."""
        d = self._jobs.get(job)
        return bool(d and (any(d.assignments.values()) or d.custom or any(d.weapons.values()) or d.lockstyle
                           or d.ammo or d.ws_ammo))

    def set_resdb(self, resdb):
        self.resdb = resdb

    # --- Set list ---
    def entries(self):
        """List of sets to show in the UI [{path, title, help, verified, custom}]"""
        rows = []
        for e in C.sets_for_job(self.job):
            rows.append(dict(path=e["path"], title=C.title(e), help=C.help_text(e),
                             verified=e.get("verified", False), custom=False, alias=e.get("alias"),
                             weapon_slot=e.get("weapon_slot"), ammo_role=e.get("ammo_role")))
        for path, label, _alias in self.custom:
            title = label if not is_en() else self._custom_title_en(path)
            rows.append(dict(path=path, title=title, help=self._custom_help(path),
                             verified=False, custom=True))
        return rows

    def _custom_title_en(self, path):
        """Build the English display name of a per-skill addition from its path (the saved display name is Japanese)."""
        name = _key_name(path)
        if path.startswith(BUFF_BASE + "["):
            b = self._cur().buffs.get(path)
            phase = b[3] if b and len(b) > 3 else "idle"
            if phase == "idle":
                return "While active: %s" % name
            act = {"WeaponSkill": "weapon skills", "Ranged Attack": "ranged attacks"}.get(b[4] if len(b) > 4 else "Magic", "spells")
            return "While active, for %s: %s" % (act, name)
        if path.startswith("sets.midcast.Increased"):
            return "%s: %s" % (C.CUSTOM_KINDS_EN[RECEIVED_KIND][0], C.received_label(path[len("sets.midcast."):]))
        if path.startswith(G.MERIT_BASE + "."):
            return "Merit gear: %s" % (_ability_en_for_set(path) or _split_camel(path[len(G.MERIT_BASE) + 1:]))
        if path in SPECIAL_SET_TITLES_EN:
            return SPECIAL_SET_TITLES_EN[path]
        for i, (base, _n, _t) in enumerate(C.CUSTOM_KINDS):
            if path.startswith(base + "["):
                return "%s: %s" % (C.CUSTOM_KINDS_EN[i][0], name)
        if path.startswith("sets.precast.") and name:
            return "%s: %s" % (C.CUSTOM_KINDS_EN[JA_KIND][0], name)
        if path.startswith("sets.precast."):
            t = path[len("sets.precast."):]
            return "%s (all)" % CH.JA_TYPE_NAMES_EN.get(t, _split_camel(t))
        return name or path

    def _custom_help(self, path):
        if path.startswith(BUFF_BASE + "["):
            return L(BUFF_HELP, BUFF_HELP_EN)
        if path.startswith("sets.midcast.Increased"):
            return C.received_help()
        if path.startswith(G.MERIT_BASE + "."):
            return L(MERIT_HELP, MERIT_HELP_EN)
        for i, (base, name, text) in enumerate(C.CUSTOM_KINDS):
            if path.startswith(base + "["):
                return C.kind_help(i)
        if path.startswith("sets.precast.") and path.endswith("]"):
            # A skill inside a type set (sets.precast.CorsairRoll['...'] etc.) gets the ability help text
            return C.kind_help(JA_KIND)
        return L("技ごとの追加のセットです。", "A set added per skill.")

    # --- Assignments ---
    def assign(self, path, items):
        """items: {slot: Item}. Empty removes the assignment."""
        if path.startswith(("weapons:", "ammo:")):
            return     # weapons are added with add_weapon, ammo with set_ammo / set_ws_ammo
        if items:
            self.assignments[path] = dict(items)
        else:
            self.assignments.pop(path, None)

    def clear(self, path):
        if path.startswith("weapons:"):
            self.weapons.pop(path.split(":", 1)[1], None)
            return
        if path.startswith("ammo:"):
            role = path.split(":", 1)[1]
            if role == "special":
                self._cur().ws_ammo.clear()
            else:
                self._cur().ammo.pop(role, None)
            return
        self.assignments.pop(path, None)

    def is_assigned(self, path):
        if path.startswith("weapons:"):
            return bool(self.weapons.get(path.split(":", 1)[1]))
        if path.startswith("ammo:"):
            role = path.split(":", 1)[1]
            return bool(self._cur().ws_ammo if role == "special" else self._cur().ammo.get(role))
        return bool(self.assignments.get(path))

    def _base_for(self, kind_index, en):
        """Where the set goes. For abilities whose res type isn't JobAbility (COR rolls, DNC waltzes, etc.), Mote-Include
        looks inside sets.precast.<type> (and ignores sets.precast.JA once that type set exists), so the set goes there."""
        base = C.CUSTOM_KINDS[kind_index][0]
        if kind_index == JA_KIND and self.resdb is not None and self.resdb.available():
            t = self.resdb.ability_type(en)
            # PetCommand (BST Sic, Ready, etc.) stays under JA, since the list already has sets.precast.JA['Sic'] and the like
            # (as long as sets.precast.PetCommand isn't created, Mote looks at JA)
            if t and t not in ("JobAbility", "WeaponSkill", "PetCommand"):
                base = "sets.precast.%s" % t
        return base

    def resolve(self, kind_index, name):
        """Turn an entered name (Japanese or English) into (status, English name, Japanese name). Status: "ok" / "empty" / "notfound". Adds nothing."""
        name = (name or "").strip()
        if not name:
            return "empty", None, None
        ascii_only = all(ord(ch) < 128 for ch in name)
        if kind_index == RECEIVED_KIND:
            for en, ja, _ids, _aoe in C.RECEIVED:
                if name in (en, ja) or ja.startswith(name):
                    return "ok", en, ja
            return "notfound", None, None
        if self.resdb is not None and self.resdb.available():
            found = self.resdb.names(KIND_KEYS[kind_index], name)
            if found:
                return "ok", found[0][0], found[0][1]
        if not ascii_only:
            return "notfound", None, None
        return "ok", name, None

    def path_for(self, kind_index, en):
        """Path of a per-skill addition set (including ones placed in a type set)."""
        if kind_index == RECEIVED_KIND:
            return "sets.midcast.%s" % en
        return G.make_key(self._base_for(kind_index, en), en)

    def add_custom(self, kind_index, name):
        """Add a per-skill set. Returns (status, path). Status: "ok" / "empty" / "dup" / "notfound".
        For a Japanese name, the English name is looked up in res and both the English-named set and a Japanese-name alias
        are created (stock Mote-Include looks sets up by English name). A Japanese name not found in res is "notfound". English names are used as is."""
        name = (name or "").strip()
        if not name:
            return "empty", None
        base, label, _ = C.CUSTOM_KINDS[kind_index]
        en, ja = name, None
        ascii_only = all(ord(ch) < 128 for ch in name)
        if self.resdb is not None and self.resdb.available():
            found = self.resdb.names(KIND_KEYS[kind_index], name)
            if found:
                en, ja = found[0]
            elif not ascii_only:
                return "notfound", None
        elif not ascii_only:
            return "notfound", None
        base = self._base_for(kind_index, en)
        path = G.make_key(base, en)
        if any(p == path for p, _l, _a in self.custom):
            return "dup", None
        alias = G.make_key(base, ja) if ja and ja != en else None
        shown = "%s (%s)" % (ja, en) if alias else en
        self.custom.append((path, "%s: %s" % (label, shown), alias))
        return "ok", path

    def add_pair(self, kind_index, en, ja):
        """Add a skill picked from the list (when both the English and Japanese names are already known). Returns "ok" / "dup"."""
        _b, label, _ = C.CUSTOM_KINDS[kind_index]
        if kind_index == RECEIVED_KIND:
            path = self.path_for(kind_index, en)
            if any(p == path for p, _l, _a in self.custom):
                return "dup"
            self.custom.append((path, "%s: %s" % (label, ja or en), None))
            return "ok"
        base = self._base_for(kind_index, en)
        path = G.make_key(base, en)
        if any(p == path for p, _l, _a in self.custom):
            return "dup"
        alias = G.make_key(base, ja) if ja and ja != en else None
        shown = "%s (%s)" % (ja, en) if alias else en
        self.custom.append((path, "%s: %s" % (label, shown), alias))
        return "ok"

    def remove_custom(self, path):
        self.custom = [c for c in self.custom if c[0] != path]
        self.assignments.pop(path, None)
        self._cur().buffs.pop(path, None)
        if path.startswith("sets.midcast.Increased"):
            self._cur().received_manual.discard(path[len("sets.midcast."):])

    # --- Ability gear ---
    def add_ability_gear(self, entry, item):
        """Assign one ability gear entry (from ability_gear.json) to that slot of the ability's set.
        Gear worn only at the moment of use (use) goes in sets.precast.JA['English name'] (plus a Japanese-name alias); gear kept
        on while the effect is active (while_active) goes in sets.buff['English name']. An existing item in the same slot is replaced. Returns the set path."""
        en, ja = entry["ability_en"], entry["ability_ja"]
        if entry.get("set_path"):
            # One set shared by several skills (e.g. all eight maneuvers = sets.precast.JA.Maneuver). Goes into the entry already in the list
            path = entry["set_path"]
            known = {e["path"] for e in C.sets_for_job(self.job)}
            if path not in known and not any(p == path for p, _l, _a in self.custom):
                # Sets not in the list (sets.merit.* etc.) are shown as per-skill additions (so they can be unassigned and removed)
                self.custom.append((path, entry.get("set_label") or ("メリット特性の装備: %s" % ja), None))
        elif entry.get("timing") in ("while_active", "cast") and entry.get("buff"):
            buff = entry["buff"]
            # "idle" while the effect is active (layered over idle/engaged); "precast" / "midcast" when casting a spell (SCH Arts, etc.)
            phase = entry.get("cast_phase", "midcast") if entry["timing"] == "cast" else "idle"
            path = G.make_key(BUFF_BASE, buff["en"])
            if not any(p == path for p, _l, _a in self.custom):
                shown = "%s (%s)" % (ja, en) if ja != en else en
                act = {"WeaponSkill": "ウェポンスキル", "Ranged Attack": "遠隔攻撃"}.get(entry.get("cast_on"), "魔法")
                label = "効果中の装備" if phase == "idle" else "効果中に%sをするときの装備" % act
                self.custom.append((path, "%s: %s" % (label, shown), None))
            kind = entry.get("cast_on", "Magic")     # action the gear is worn for while active: Magic / WeaponSkill / Ranged Attack
            self._cur().buffs[path] = (int(buff["id"]), buff["en"], buff["ja"], phase, kind)
        else:
            self.add_pair(JA_KIND, en, ja)       # does nothing if it's already there
            path = G.make_key(self._base_for(JA_KIND, en), en)
        slots = self.assignments.setdefault(path, {})
        slots[item.slot] = item
        return path

    # --- Weapon cycle ---
    def add_weapon(self, slot, item):
        """Add a weapon. If the same item (same name and augments) is already there, it isn't added and False is returned."""
        lst = self.weapons.setdefault(slot, [])
        if any(it.raw == item.raw for it in lst):
            return False
        lst.append(item)
        return True

    # --- Ammo (RNG, COR) ---
    @property
    def ammo(self):
        return self._cur().ammo

    @property
    def ws_ammo(self):
        return self._cur().ws_ammo

    def set_ammo(self, role, item):
        """Set the single ammo for a role (physical/magical/quickdraw), replacing any previous one."""
        self._cur().ammo[role] = EP.Item("ammo", item.name, item.raw)

    def set_ws_ammo(self, ws_en, item):
        """Special ammo: set the ammo used only for that WS. item=None removes it."""
        if item is None:
            self._cur().ws_ammo.pop(ws_en, None)
        else:
            self._cur().ws_ammo[ws_en] = EP.Item("ammo", item.name, item.raw)

    # --- Automatic elemental obi / Orpheus's Sash selection ---
    @property
    def auto_waist(self):
        return self._cur().auto_waist

    def set_auto_waist(self, on):
        self._cur().auto_waist = bool(on)

    # --- PUP automatic pre-swap ---
    @property
    def pup_auto(self):
        return self._cur().pup_auto

    def set_pup_auto(self, on):
        self._cur().pup_auto = bool(on)

    # --- PLD three-stage swap ---
    @property
    def three_stage(self):
        return self._cur().three_stage

    def set_three_stage(self, on):
        self._cur().three_stage = bool(on)

    @property
    def fast_cast(self):
        return self._cur().fast_cast

    def set_fast_cast(self, value):
        """Gear Fast Cast (%): an integer from 0 to 100 (a string is fine). 0 if it can't be parsed. Returns the value set."""
        try:
            n = int(str(value).strip())
        except (TypeError, ValueError):
            n = 0
        self._cur().fast_cast = max(0, min(100, n))     # values above the 80% cap are kept (used to warn about waste; the output clamps to 80)
        return self._cur().fast_cast

    # --- Output ---
    def _relocate_custom(self):
        """Move sets.precast.JA['...'] entries from older work files (saved before type sets were used) to where they belong.
        e.g. sets.precast.JA['Tactician\\'s Roll'] -> sets.precast.CorsairRoll['Tactician\\'s Roll']. Assignments and aliases move too."""
        if self.resdb is None or not self.resdb.available():
            return
        ja_base = C.CUSTOM_KINDS[JA_KIND][0]
        prefix = ja_base + "['"
        moved = []
        for path, label, alias in self.custom:
            if path.startswith(prefix) and path.endswith("']"):
                en = path[len(prefix):-2].replace("\\'", "'").replace("\\\\", "\\")
                base = self._base_for(JA_KIND, en)
                if base != ja_base:
                    new_path = G.make_key(base, en)
                    new_alias = None
                    if alias and alias.startswith(prefix):
                        new_alias = base + alias[len(ja_base):]
                    if path in self.assignments:
                        self.assignments[new_path] = self.assignments.pop(path)
                    moved.append((path, (new_path, label, new_alias)))
                    continue
            moved.append((path, (path, label, alias)))
        self.custom = [c for _old, c in moved]

    def to_lua(self):
        """Output only the current job's contents."""
        self._relocate_custom()
        order = [e["path"] for e in self.entries()]
        ordered = {}
        for p in order:
            if p in self.assignments:
                ordered[p] = self.assignments[p]
        # Sets no longer in the list (items removed in a kit update that were assigned earlier) aren't output, but stay in the work file
        self.orphans = [p for p in self.assignments if p not in ordered and self.assignments[p]]
        aliases = {alias: path for path, _l, alias in self.custom if alias}
        for e in self.entries():
            if e.get("alias"):
                aliases[e["alias"]] = e["path"]
        buffs = [(p, b[0], b[1], b[2], b[3] if len(b) > 3 else "idle", b[4] if len(b) > 4 else "Magic")
                 for p, b in self._cur().buffs.items()]
        return G.build_lua(self.job, ordered, include_weapons=self.include_weapons, aliases=aliases, weapons=self.weapons,
                           buffs=buffs, lockstyle=self._cur().lockstyle,
                           received_manual=self._cur().received_manual,
                           ammo=self._cur().ammo, ws_ammo=self._cur().ws_ammo,
                           pld_three_stage=self._cur().three_stage, pld_fast_cast=self._cur().fast_cast,
                           pup_auto=self._cur().pup_auto, auto_waist=self._cur().auto_waist)

    def write_lua(self, data_dir):
        """Write data_dir/<job>.lua, backing up any existing file in the same folder first. Returns (path, backup or None).
        The whole Lua is built before anything is written, so a failure while building never empties the current file."""
        text = self.to_lua()
        path = os.path.join(data_dir, "%s.lua" % self.job)
        backup = None
        if os.path.exists(path):
            stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup = os.path.join(data_dir, "%s.lua.%s.bak" % (self.job, stamp))
            shutil.copy2(path, backup)
        atomic_write(path, text, newline="\n")
        return path, backup

    # --- Save / load (for resuming work; all jobs) ---
    @staticmethod
    def _job_to_dict(d):
        return dict(custom=d.custom, buffs={p: list(b) for p, b in d.buffs.items()},
                    assignments={p: {s: it.raw for s, it in items.items()} for p, items in d.assignments.items()},
                    weapons={slot: [it.raw for it in lst] for slot, lst in d.weapons.items() if lst},
                    lockstyle=d.lockstyle, received_manual=sorted(d.received_manual),
                    ammo={r: it.raw for r, it in d.ammo.items()}, ws_ammo={w: it.raw for w, it in d.ws_ammo.items()},
                    three_stage=d.three_stage, fast_cast=d.fast_cast, pup_auto=d.pup_auto,
                    auto_waist=d.auto_waist)

    def to_json(self):
        jobs = {job: self._job_to_dict(d) for job, d in self._jobs.items()
                if any(d.assignments.values()) or d.custom or any(d.weapons.values()) or d.lockstyle
                or d.ammo or d.ws_ammo}
        data = dict(version=2, job=self.job, include_weapons=self.include_weapons, jobs=jobs)
        return json.dumps(data, ensure_ascii=False, indent=1)

    def _load_job(self, job, jd):
        """Load one job's dict as that job's contents."""
        keep = self.job
        self.job = job
        try:
            self.custom = [tuple(x) if len(x) >= 3 else (x[0], x[1], None) for x in jd.get("custom", [])]
            if jd.get("lockstyle"):
                self.set_lockstyle(jd.get("lockstyle"))
            for name in jd.get("received_manual", []):
                self.set_received_auto(name, False)
            for p, b in jd.get("buffs", {}).items():
                self._cur().buffs[p] = (int(b[0]), b[1], b[2], b[3] if len(b) > 3 else "idle", b[4] if len(b) > 4 else "Magic")
            for p, items in jd.get("assignments", {}).items():
                slot_items = {}
                for slot, raw in items.items():
                    found = EP.parse_entries("%s=%s" % (slot, raw))
                    if found:
                        slot_items[slot] = found[0]
                if slot_items:
                    self.assignments[p] = slot_items
            for slot, raws in jd.get("weapons", {}).items():
                for raw in raws:
                    found = EP.parse_entries("%s=%s" % (slot, raw))
                    if found:
                        self.add_weapon(slot, found[0])
            self._cur().three_stage = bool(jd.get("three_stage", False))
            self._cur().pup_auto = bool(jd.get("pup_auto", False))
            self._cur().auto_waist = bool(jd.get("auto_waist", False))
            self.set_fast_cast(jd.get("fast_cast", 0))
            for role, raw in jd.get("ammo", {}).items():
                found = EP.parse_entries("ammo=%s" % raw)
                if found:
                    self.set_ammo(role, found[0])
            for ws, raw in jd.get("ws_ammo", {}).items():
                found = EP.parse_entries("ammo=%s" % raw)
                if found:
                    self.set_ws_ammo(ws, found[0])
        finally:
            self.job = keep

    @classmethod
    def from_json(cls, text):
        data = json.loads(text)
        pr = cls(data.get("job", "SMN"))
        pr.include_weapons = bool(data.get("include_weapons", False))
        if "jobs" in data:
            for job, jd in data["jobs"].items():
                pr._load_job(job, jd)
        else:
            # Old format (a single job only): read it as that job's contents
            pr._load_job(pr.job, data)
        return pr
