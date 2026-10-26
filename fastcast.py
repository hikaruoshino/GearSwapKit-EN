# -*- coding: utf-8 -*-
"""装備のファストキャスト (%) を、Windower の res から足し合わせる (ナイトの 3 段階の着替えの計算に使う)。

- 装備の性能: res/item_descriptions.lua の英語の説明の "Fast Cast"+N%  (名前 → 番号は res/items.lua)
- オーグメント: export の augments の '"Fast Cast"+N'
同じ名前の装備が複数の版 (Lv75 と Lv99 など) あるときは、大きいほうを使う。res は読むだけ。
"""
import os
import re

from i18n import L

_ITEM = re.compile(r'^\s*\[(\d+)\]\s*=\s*\{id=\d+,en="((?:[^"\\]|\\.)*)",ja="((?:[^"\\]|\\.)*)"')
_DESC = re.compile(r'^\s*\[(\d+)\]\s*=\s*\{id=\d+,en="((?:[^"\\]|\\.)*)"')
_FC_DESC = re.compile(r'(?:\\")?Fast Cast(?:\\")?\s*\+(\d+)%')
# 数値の無い書き方 (オルンミラトルクの Increases "Fast Cast" effect など)。値が分からないので、画面で知らせる
_FC_VAGUE = re.compile(r'(?:Increases|Enhances) (?:\\")?Fast Cast(?:\\")? effect')
_FC_AUG = re.compile(r'"Fast Cast"\s*\+(\d+)')

# 説明に数値の無い装備の値 (Increases "Fast Cast" effect など)。
# オルンミラトルク = +5%: 作者のナイトの FC セット (sets.precast.FC.value = 69) の合計と、ほかの装備の値 64% の差で確認 (2026-10-26)
KNOWN_VAGUE = {"オルンミラトルク": 5, "orunmila's torque": 5}

_cache = {}


def _read(path):
    try:
        with open(path, "rb") as f:
            return f.read().decode("utf-8", errors="replace")
    except OSError:
        return ""


def _tables(res_dir):
    """(名前 → [番号], 番号 → 説明のファストキャスト)。res_dir ごとに 1 回だけ読む。"""
    if res_dir in _cache:
        return _cache[res_dir]
    ids = {}
    for line in _read(os.path.join(res_dir, "items.lua")).splitlines():
        m = _ITEM.match(line)
        if m:
            for nm in (m.group(3), m.group(2).lower()):
                ids.setdefault(nm, []).append(int(m.group(1)))
    fc = {}
    for line in _read(os.path.join(res_dir, "item_descriptions.lua")).splitlines():
        m = _DESC.match(line)
        if m:
            f = _FC_DESC.search(m.group(2))
            if f:
                fc[int(m.group(1))] = int(f.group(1))
            elif _FC_VAGUE.search(m.group(2)):
                fc[int(m.group(1))] = None
    _cache[res_dir] = (ids, fc)
    return _cache[res_dir]


def item_fast_cast(res_dir, item):
    """装備 1 つ (export_parser.Item) のファストキャスト。戻り値: (性能 + オーグメントの %, 説明に数値の無いファストキャストがあるか)。"""
    total = sum(int(x) for x in _FC_AUG.findall(item.raw or ""))
    vague = False
    if res_dir:
        ids, fc = _tables(res_dir)
        name = (item.name or "").strip()
        found = ids.get(name) or ids.get(name.lower()) or []
        vals = [fc[i] for i in found if i in fc]
        nums = [v for v in vals if v is not None]
        known = KNOWN_VAGUE.get(name, KNOWN_VAGUE.get(name.lower()))
        if nums:
            total += max(nums)
        elif known is not None:
            total += known
        elif vals:
            vague = True
    return total, vague


FC_CAP = 80          # ファストキャストの上限 (装備と特性を合わせて)
MAIN_RDM_FC = 38     # 赤魔道士 (メイン) の特性 + ジョブポイント (作者の PLD.lua と同じ値)
SUB_RDM_FC = 15      # サポ赤の特性 (マスターレベル 30 以上は 20)


def advice(total, job):
    """ファストキャストの合計 (装備) から、上限を超えて無駄になっていないかの知らせ。問題が無ければ空。"""
    if total <= 0:
        return ""
    if job == "RDM":
        whole = total + MAIN_RDM_FC
        if whole > FC_CAP:
            return L("赤魔道士の特性 %d%% を足すと %d%% で、上限 %d%% を %d%% 超えています。超えた分は無駄なので、"
                     "その部位をほかの性能の装備に替えられます。" % (MAIN_RDM_FC, whole, FC_CAP, whole - FC_CAP),
                     "With Red Mage's own %d%% Fast Cast trait you're at %d%%, %d%% over the %d%% cap. "
                     "That extra is wasted, so those slots could go to other stats." % (MAIN_RDM_FC, whole, whole - FC_CAP, FC_CAP))
        return ""
    if total > FC_CAP:
        return L("装備だけで上限 %d%% を %d%% 超えています。超えた分は無駄なので、その部位をほかの性能の装備に替えられます。"
                 % (FC_CAP, total - FC_CAP),
                 "Your gear alone is %d%% over the %d%% cap. That extra is wasted, so those slots could go to other stats."
                 % (total - FC_CAP, FC_CAP))
    if total + SUB_RDM_FC > FC_CAP:
        return L("サポ赤にすると、特性 %d%% (マスターレベル 30 以上は 20%%) が足されて %d%% 以上になり、上限 %d%% を超えます。"
                 "サポ赤で使うなら、%d%% 分はほかの性能の装備に替えられます。"
                 % (SUB_RDM_FC, total + SUB_RDM_FC, FC_CAP, total + SUB_RDM_FC - FC_CAP),
                 "With /RDM, the subjob trait adds %d%% (20%% at Master Level 30+), putting you at %d%% or more, over the %d%% cap. "
                 "If you play /RDM, you can spare %d%% of Fast Cast for other stats."
                 % (SUB_RDM_FC, total + SUB_RDM_FC, FC_CAP, total + SUB_RDM_FC - FC_CAP))
    return ""


def set_fast_cast(res_dir, items):
    """セット ({部位: Item}) のファストキャストの合計 (%)。
    戻り値: (合計, [(部位, 名前, 値)] 値が 0 より大きいもの, [名前] 数値の分からないファストキャストの装備)。"""
    rows, unknown = [], []
    for slot, it in (items or {}).items():
        v, vague = item_fast_cast(res_dir, it)
        if v:
            rows.append((slot, it.name, v))
        if vague:
            unknown.append(it.name)
    return sum(v for _s, _n, v in rows), rows, unknown
