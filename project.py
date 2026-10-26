# -*- coding: utf-8 -*-
"""キットの作業内容 (どのセットに、どの export を割り当てたか)。画面から独立していて、テストできる。

割り当て・技ごとの追加・武器の切り替えは、**ジョブごとに別々**に持つ (SMN で登録したものが COR に出ることはない)。
"""
import datetime
import json
import os
import shutil

import choices as CH
import export_parser as EP
from i18n import L, is_en
import generator as G
import resdb as R
import set_catalog as C

# 「技ごとの追加」の種類 (C.CUSTOM_KINDS と同じ順) と、引く res の表
KIND_KEYS = ["ws", "ja", "magic", "pet", "received"]
RECEIVED_KIND = 4                 # 被強化の装備 (sets.midcast.IncreasedPhalanx など。[ ] ではなく . で付く)
JA_KIND = 1                       # KIND_KEYS / C.CUSTOM_KINDS の中の「ジョブアビリティ」の位置
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
# 一覧に無い、まとめのセット (ability_gear.json の set_path) の英語の表示名
SPECIAL_SET_TITLES_EN = {"sets.Stormsurge": "Stormsurge feet (when casting storm spells)"}


def _key_name(path):
    """sets.x['Name'] の Name (無ければ空)。"""
    if path.endswith("']") and "['" in path:
        return path[path.index("['") + 2:-2].replace("\\'", "'").replace("\\\\", "\\")
    return ""


_SET_ABILITY_EN = None


def _ability_en_for_set(path):
    """ability_gear.json で set_path がこの path のアビリティの英語名 (無ければ None)。"""
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
    """1 つのジョブの作業内容。"""

    def __init__(self):
        self.assignments = {}      # path -> {slot: Item}
        self.custom = []           # [(path, 表示名, 日本語名の別名のパス または None)]  技ごとの追加
        self.weapons = {}          # スロット (main/sub/range) -> [Item, ...]  武器の切り替え
        self.buffs = {}            # sets.buff のパス -> (バフ番号, 英語名, 日本語名)  効果中ずっと着る装備
        self.lockstyle = None      # ロックスタイル番号 (ゲームの装備セットの番号)。None なら使わない
        self.received_manual = set()   # 被強化の装備のうち、自動で着替えないもの (例: {"IncreasedPhalanx"})
        self.ammo = {}             # 矢弾の役目 (physical/magical/quickdraw) -> Item  (狩人・コルセア)
        self.ws_ammo = {}          # WS の英語名 -> Item  特殊弾 (その WS だけで使う弾)
        self.three_stage = False   # ナイト: 3 段階の着替え (ファストキャスト → 詠唱中断 → 着弾の装備) を使うか
        self.fast_cast = 0         # ナイト: 3 段階の着替えの計算に使う、装備のファストキャスト (%)
        self.pup_auto = False      # からくり士: オートマトンの技の装備を先に着る (自動の事前着替え) を入れるか
        self.auto_waist = False    # 精霊魔法で、属性帯 (八輪の帯) とオルペウスサッシュを自動で選ぶか


class Project:
    def __init__(self, job="SMN"):
        self.job = job
        self.include_weapons = False
        self.resdb = None          # 日本語名 → 英語名を引くための res (無くても動く)
        self._jobs = {}            # ジョブの略称 -> JobData

    # --- ジョブ ---
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
        """ロックスタイル番号を決める。1〜200 の整数 (文字でもよい)。空・範囲外は使わない (None)。戻り値: 決まった番号か None。"""
        try:
            n = int(str(value).strip())
        except (TypeError, ValueError):
            n = None
        if n is not None and not (1 <= n <= 200):
            n = None
        self._cur().lockstyle = n
        return n

    def set_received_auto(self, name, auto):
        """被強化の装備 (name = IncreasedPhalanx など) を、魔法に反応して自動で着替えるか。"""
        if auto:
            self._cur().received_manual.discard(name)
        else:
            self._cur().received_manual.add(name)

    def received_auto(self, name):
        return name not in self._cur().received_manual

    def set_job(self, job):
        """ジョブを変える。割り当ては、ジョブごとに別々に持つので、ほかのジョブの内容は出ない (戻すと、元に戻る)。"""
        self.job = job

    def has_work(self, job):
        """そのジョブに、何か割り当て・追加・武器があるか。"""
        d = self._jobs.get(job)
        return bool(d and (any(d.assignments.values()) or d.custom or any(d.weapons.values()) or d.lockstyle
                           or d.ammo or d.ws_ammo))

    def set_resdb(self, resdb):
        self.resdb = resdb

    # --- 一覧 ---
    def entries(self):
        """画面に出すセットの一覧 [{path, title, help, verified, custom}]"""
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
        """技ごとの追加の英語の表示名を、path から作る (保存してある表示名は日本語のため)。"""
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
            # 種類のセットの中の技 (sets.precast.CorsairRoll['…'] など) は、アビリティの説明
            return C.kind_help(JA_KIND)
        return L("技ごとの追加のセットです。", "A set added per skill.")

    # --- 割り当て ---
    def assign(self, path, items):
        """items: {slot: Item}。空なら割り当てを外す。"""
        if path.startswith(("weapons:", "ammo:")):
            return     # 武器の切り替えは add_weapon・矢弾は set_ammo / set_ws_ammo で足す
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
        """セットの置き場。アビリティのうち、res の種類が JobAbility 以外 (コルセアのロール・踊り子のワルツなど) は、
        Mote-Include が sets.precast.<種類> の中で探す (種類のセットがあると sets.precast.JA を見ない) ので、そこに置く。"""
        base = C.CUSTOM_KINDS[kind_index][0]
        if kind_index == JA_KIND and self.resdb is not None and self.resdb.available():
            t = self.resdb.ability_type(en)
            # PetCommand (獣使いのほんきだせ・しじをさせろ など) は、一覧に元から sets.precast.JA['Sic'] などがあるので JA のまま
            # (sets.precast.PetCommand を作らなければ、Mote は JA を見る)
            if t and t not in ("JobAbility", "WeaponSkill", "PetCommand"):
                base = "sets.precast.%s" % t
        return base

    def resolve(self, kind_index, name):
        """入れた名前 (日本語・英語) を、(状態, 英語名, 日本語名) にする。状態: "ok" / "empty" / "notfound"。追加はしない。"""
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
        """技ごとの追加のセットのパス (種類のセットに置くものも含む)。"""
        if kind_index == RECEIVED_KIND:
            return "sets.midcast.%s" % en
        return G.make_key(self._base_for(kind_index, en), en)

    def add_custom(self, kind_index, name):
        """技ごとの追加。戻り値: (状態, path)。状態: "ok" / "empty" / "dup" / "notfound"。
        日本語名を入れたときは、res から英語名を引き、英語名のセットと、日本語名の別名の両方を作る
        (標準の Mote-Include は英語名で探す)。res で見つからない日本語名は "notfound"。英語名は、そのまま使う。"""
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
        """一覧から選んだ技を足す (英語名と日本語名が、すでに分かっているとき)。戻り値: "ok" / "dup"。"""
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

    # --- アビリティ強化の装備 ---
    def add_ability_gear(self, entry, item):
        """アビリティ強化の装備 (ability_gear.json のエントリ) の 1 つを、そのアビリティのセットの、その部位に割り当てる。
        使う瞬間だけ着るもの (use) は sets.precast.JA['英語名'] (+ 日本語名の別名)・効果中ずっと着るもの (while_active) は
        sets.buff['英語名']。すでに同じ部位があれば、置き換える。戻り値: セットのパス。"""
        en, ja = entry["ability_en"], entry["ability_ja"]
        if entry.get("set_path"):
            # 複数の技を 1 つのセットでまとめて扱うもの (例: マニューバ 8 種 = sets.precast.JA.Maneuver)。一覧に元からある場面へ入れる
            path = entry["set_path"]
            known = {e["path"] for e in C.sets_for_job(self.job)}
            if path not in known and not any(p == path for p, _l, _a in self.custom):
                # 一覧に無いセット (sets.merit.* など) は、技ごとの追加として一覧に出す (割り当てを外す・削除ができるように)
                self.custom.append((path, entry.get("set_label") or ("メリット特性の装備: %s" % ja), None))
        elif entry.get("timing") in ("while_active", "cast") and entry.get("buff"):
            buff = entry["buff"]
            # 効果中ずっと (待機・戦闘中に重ねる) は "idle"・魔法を唱えるとき (学者の章など) は "precast" / "midcast"
            phase = entry.get("cast_phase", "midcast") if entry["timing"] == "cast" else "idle"
            path = G.make_key(BUFF_BASE, buff["en"])
            if not any(p == path for p, _l, _a in self.custom):
                shown = "%s (%s)" % (ja, en) if ja != en else en
                act = {"WeaponSkill": "ウェポンスキル", "Ranged Attack": "遠隔攻撃"}.get(entry.get("cast_on"), "魔法")
                label = "効果中の装備" if phase == "idle" else "効果中に%sをするときの装備" % act
                self.custom.append((path, "%s: %s" % (label, shown), None))
            kind = entry.get("cast_on", "Magic")     # 効果中に着る行動: Magic / WeaponSkill / Ranged Attack
            self._cur().buffs[path] = (int(buff["id"]), buff["en"], buff["ja"], phase, kind)
        else:
            self.add_pair(JA_KIND, en, ja)       # すでにあれば、何もしない
            path = G.make_key(self._base_for(JA_KIND, en), en)
        slots = self.assignments.setdefault(path, {})
        slots[item.slot] = item
        return path

    # --- 武器の切り替え ---
    def add_weapon(self, slot, item):
        """武器を足す。同じ装備 (名前もオーグメントも同じ) がすでにあれば、足さずに False。"""
        lst = self.weapons.setdefault(slot, [])
        if any(it.raw == item.raw for it in lst):
            return False
        lst.append(item)
        return True

    # --- 矢弾 (狩人・コルセア) ---
    @property
    def ammo(self):
        return self._cur().ammo

    @property
    def ws_ammo(self):
        return self._cur().ws_ammo

    def set_ammo(self, role, item):
        """矢弾の役目 (physical/magical/quickdraw) に、1 つ決める (置き換え)。"""
        self._cur().ammo[role] = EP.Item("ammo", item.name, item.raw)

    def set_ws_ammo(self, ws_en, item):
        """特殊弾: その WS だけで使う弾を決める。item が None なら外す。"""
        if item is None:
            self._cur().ws_ammo.pop(ws_en, None)
        else:
            self._cur().ws_ammo[ws_en] = EP.Item("ammo", item.name, item.raw)

    # --- 属性帯・オルペウスサッシュの自動選択 ---
    @property
    def auto_waist(self):
        return self._cur().auto_waist

    def set_auto_waist(self, on):
        self._cur().auto_waist = bool(on)

    # --- からくり士の自動の事前着替え ---
    @property
    def pup_auto(self):
        return self._cur().pup_auto

    def set_pup_auto(self, on):
        self._cur().pup_auto = bool(on)

    # --- ナイトの 3 段階の着替え ---
    @property
    def three_stage(self):
        return self._cur().three_stage

    def set_three_stage(self, on):
        self._cur().three_stage = bool(on)

    @property
    def fast_cast(self):
        return self._cur().fast_cast

    def set_fast_cast(self, value):
        """装備のファストキャスト (%)。0〜100 の整数 (文字でもよい)。読めなければ 0。戻り値: 決まった値。"""
        try:
            n = int(str(value).strip())
        except (TypeError, ValueError):
            n = 0
        self._cur().fast_cast = max(0, min(100, n))     # 上限 (80%) 超えも残す (無駄の知らせに使う。出力では 80 で切る)
        return self._cur().fast_cast

    # --- 出力 ---
    def _relocate_custom(self):
        """古い作業 (種類のセットに置く前に保存したもの) の sets.precast.JA['…'] を、正しい置き場所へ移す。
        例: sets.precast.JA['Tactician\\'s Roll'] → sets.precast.CorsairRoll['Tactician\\'s Roll']。割り当てと別名も移す。"""
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
        """今のジョブの内容だけを出力する。"""
        self._relocate_custom()
        order = [e["path"] for e in self.entries()]
        ordered = {}
        for p in order:
            if p in self.assignments:
                ordered[p] = self.assignments[p]
        # 一覧に無いセット (キットの更新で外した項目に、前に割り当てたもの) は出力しない。作業のファイルには残す
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
        """data_dir/<ジョブ>.lua に書く。既にあれば、同じ場所にバックアップを取ってから。(path, backup または None) を返す。"""
        path = os.path.join(data_dir, "%s.lua" % self.job)
        backup = None
        if os.path.exists(path):
            stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup = os.path.join(data_dir, "%s.lua.%s.bak" % (self.job, stamp))
            shutil.copy2(path, backup)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(self.to_lua())
        return path, backup

    # --- 保存 / 読み込み (作業のやり直し用・全ジョブぶん) ---
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
        """1 ジョブぶんの辞書を、そのジョブの内容として読み込む。"""
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
            # 古い形式 (1 つのジョブだけ): そのジョブの内容として読む
            pr._load_job(pr.job, data)
        return pr
