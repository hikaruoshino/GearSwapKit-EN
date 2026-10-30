# -*- coding: utf-8 -*-
"""GearSwapKit's main window (tkinter).

  1. Pick a job
  2. Pick a set (idle, engaged, precast, etc.) and hand it a file exported in game with "Assign export"
  3. "Make Lua" writes <job>.lua to GearSwap's data folder

UI text is written as L("Japanese", "English"), and the current language's text is shown (i18n.py). The language is stored
as "lang" in the settings file and chosen on first launch. Changing it with the top-row Language selector rebuilds the window on the spot.

Nothing is sent to the game and memory is never touched. The only files read are exports the user made themselves.
"""
import json
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import ability_gear as AG
import choices as CH
import conflicts
import export_parser as EP
import fastcast as FCALC
import generator as G
import i18n
import resdb as R
import set_catalog as C
from i18n import L
from project import Project, RECEIVED_KIND, atomic_write

APP_NAME = "GearSwapKit"
VERSION = "1.2.5"
BASE = os.path.dirname(os.path.abspath(sys.argv[0] if "__compiled__" in globals() else __file__))
_APPDATA = os.environ.get("APPDATA") or os.path.expanduser("~")
SETTINGS = os.path.join(_APPDATA, "GearSwapKit", "gearswapkit_settings.json")
OLD_SETTINGS = os.path.join(BASE, "gearswapkit_settings.json")     # Where older versions kept it (next to the EXE). Read only

# English for the notes on ability gear (the items' note in the table)
NOTE_EN = {
    "オーグメントしたものだけ": "Only works if the piece is augmented.",
    "オーグメント (忘れ去られた願い) をしたものだけ": "Only works if the piece is augmented (Forgotten Wish).",
    "時々効果アップ": "The boost only procs some of the time.",
    "オーグメントの性能として記載": "This property comes from the augment.",
}

STATE_ON = "✔ 割り当て済み"      # Japanese-mode text (state_on() / state_off() give the current language)
STATE_OFF = "未設定"

# Language choices (label, code). Labels are the same in either language
LANG_CHOICES = (("日本語", "ja"), ("English", "en"))

SLOT_EN = {
    'main': 'Main', 'sub': 'Sub', 'range': 'Range', 'ammo': 'Ammo', 'head': 'Head', 'neck': 'Neck',
    'left_ear': 'L.Ear', 'right_ear': 'R.Ear', 'body': 'Body', 'hands': 'Hands', 'left_ring': 'L.Ring',
    'right_ring': 'R.Ring', 'back': 'Back', 'waist': 'Waist', 'legs': 'Legs', 'feet': 'Feet',
}

ELEMENTAL_SETS = ("sets.midcast['精霊魔法']", "sets.midcast['Elemental Magic']")


def state_on():
    return L(STATE_ON, "✔ Assigned")


def state_off():
    return L(STATE_OFF, "Not set")


def slot_name(slot):
    """Display name of a slot (current language)."""
    return L(EP.SLOT_JA.get(slot, slot), SLOT_EN.get(slot, slot))


def kinds():
    """Kinds for "Add per skill" [(base, label, help)]. Uses set_catalog's current-language functions when it has them."""
    return [(C.CUSTOM_KINDS[i][0], C.kind_label(i), C.kind_help(i)) for i in range(len(C.CUSTOM_KINDS))]


def item_display(name, resdb):
    """Display name for gear. In English mode, the English name from res if found (otherwise unchanged)."""
    if not name:
        return L("(名前を読めません)", "(unreadable name)")
    if i18n.is_en() and resdb is not None and hasattr(resdb, "item_en"):
        try:
            en = resdb.item_en(name)
        except Exception:
            en = None
        if en:
            return en
    return name


def ability_display(entry):
    """Ability name from the ability gear table (English name in English mode)."""
    if i18n.is_en():
        return entry.get("ability_en") or entry.get("ability_ja", "")
    return entry.get("ability_ja") or entry.get("ability_en", "")


def load_settings():
    """Load saved settings (data folder, last chosen export file, language). Empty if unreadable."""
    for path in (SETTINGS, OLD_SETTINGS):
        try:
            with open(path, "rb") as f:
                data = json.loads(f.read().decode("utf-8"))
            if isinstance(data, dict):
                return data
        except (OSError, ValueError):
            continue
    return {}


def save_settings(data):
    """Write settings. If that fails (e.g. a read-only location), the kit keeps working."""
    try:
        os.makedirs(os.path.dirname(SETTINGS), exist_ok=True)
        atomic_write(SETTINGS, json.dumps(data, ensure_ascii=False, indent=1), newline="\n")
    except OSError:
        pass


def default_data_dir():
    """Look for Windower's GearSwap data folder in the usual install locations."""
    candidates = [
        os.path.join(os.path.expanduser("~"), "Documents", "Windower4", "addons", "gearswap", "data"),
        r"C:\Windower4\addons\gearswap\data",
        r"C:\Program Files (x86)\Windower4\addons\gearswap\data",
        r"C:\Program Files\Windower4\addons\gearswap\data",
    ]
    for c in candidates:
        if os.path.isdir(c):
            return c
    return ""


def ask_first_language(root):
    """On first launch (no language in settings), show a small window to pick a language. Returns "ja" / "en".
    Japanese if the window is closed."""
    chosen = ["ja"]
    win = tk.Toplevel(root)
    win.title("GearSwapKit — Language / 言語")
    win.resizable(False, False)
    frame = ttk.Frame(win, padding=16)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="言語を選んでください。\nChoose your language.", justify="center").pack(pady=(0, 10))
    row = ttk.Frame(frame)
    row.pack()

    def pick(code):
        chosen[0] = code
        win.destroy()

    for label, code in LANG_CHOICES:
        ttk.Button(row, text=label, width=12, command=lambda c=code: pick(c)).pack(side="left", padx=6)
    ttk.Label(frame, text="(あとで上の「Language / 言語」で変えられます / You can change this later.)",
              foreground="#666").pack(pady=(10, 0))
    win.protocol("WM_DELETE_WINDOW", win.destroy)
    win.grab_set()
    root.wait_window(win)
    return chosen[0]


class WeaponPicker:
    """Small window for picking several weapons from inventory candidates (with search). The chosen Items go in self.result."""

    def __init__(self, parent, title, items, job=None, resdb=None):
        self.items = items
        self.job = job
        self.resdb = resdb if (resdb is not None and resdb.available()) else None
        self.result = []
        self.win = tk.Toplevel(parent)
        self.win.title(title)
        self.win.geometry("520x520")
        self.win.transient(parent)
        top = ttk.Frame(self.win, padding=8)
        top.pack(fill="x")
        ttk.Label(top, text=L("検索", "Search")).pack(side="left")
        self.query = tk.StringVar()
        ent = ttk.Entry(top, textvariable=self.query)
        ent.pack(side="left", fill="x", expand=True, padx=6)
        self.query.trace_add("write", lambda *a: self.fill())
        self.only_job = tk.BooleanVar(value=self.resdb is not None and bool(job))
        if self.resdb is not None and job:
            ttk.Checkbutton(self.win, text=L("このジョブ (%s) で使える武器だけを出す", "Only show weapons usable by %s") % job,
                            variable=self.only_job, command=self.fill).pack(anchor="w", padx=8)
        elif job:
            ttk.Label(self.win, text=L("(Windower の res が見つからないので、ジョブでの絞り込みはできません)",
                                       "(Windower's res folder wasn't found, so the job filter is unavailable.)"),
                      foreground="#a33", padding=(8, 0)).pack(anchor="w")
        ttk.Label(self.win, text=L("使いたい武器を、切り替えたい順にクリックしてください (もう一度クリックで外れます)。\n"
                                   "選んだ順が、//gs c cycle で持ち替える順になります。",
                                   "Click weapons in the order you want to cycle them (click again to remove).\n"
                                   "This is the order //gs c cycle will swap through."),
                  padding=(8, 0), justify="left").pack(anchor="w")
        self.order_lbl = ttk.Label(self.win, text="", foreground="#336", padding=(8, 2), wraplength=490, justify="left")
        self.order_lbl.pack(anchor="w")
        frame = ttk.Frame(self.win, padding=8)
        frame.pack(fill="both", expand=True)
        self.order = []        # Items in click order
        self.box = tk.Listbox(frame, selectmode="multiple", exportselection=False)
        self.box.bind("<<ListboxSelect>>", lambda e: self.on_select())
        sb = ttk.Scrollbar(frame, orient="vertical", command=self.box.yview)
        self.box.config(yscrollcommand=sb.set)
        self.box.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        bottom = ttk.Frame(self.win, padding=8)
        bottom.pack(fill="x")
        ttk.Button(bottom, text=L("選んだ武器を足す", "Add selected"), command=self.ok).pack(side="right")
        ttk.Button(bottom, text=L("やめる", "Cancel"), command=self.win.destroy).pack(side="right", padx=6)
        self.shown = []
        self.fill()
        ent.focus_set()
        self.win.grab_set()
        parent.wait_window(self.win)

    def name_of(self, item):
        return item_display(item.name, self.resdb)

    def label(self, item):
        return self.name_of(item) + (L("  (オーグメント付き)", "  (augmented)") if "augments" in item.raw else "")

    def fill(self):
        q = self.query.get().strip().lower()
        self.box.delete(0, "end")
        self.shown = [it for it in self.items
                      if (q in (it.name or "").lower() or q in self.name_of(it).lower()) and self.usable(it)]
        for i, it in enumerate(self.shown):
            self.box.insert("end", self.label(it))
            if it in self.order:
                self.box.selection_set(i)     # keep selections selected even when the search changes the list
        self.show_order()

    def on_select(self):
        """Track click order (newly selected items go to the end, deselected ones are dropped)."""
        picked = {self.shown[i] for i in self.box.curselection()}
        shown = set(self.shown)
        self.order = [it for it in self.order if it in picked or it not in shown]
        for i in self.box.curselection():
            if self.shown[i] not in self.order:
                self.order.append(self.shown[i])
        self.show_order()

    def show_order(self):
        if self.order:
            text = L("選んだ順: ", "Order: ") + " → ".join("%d. %s" % (n + 1, self.name_of(it)) for n, it in enumerate(self.order))
        else:
            text = L("選んだ順: (まだありません)", "Order: (none yet)")
        self.order_lbl.config(text=text)

    def usable(self, item):
        """Job filter check. Gear not in res (None) can't be judged, so it's kept."""
        if not (self.only_job.get() and self.resdb is not None and self.job):
            return True
        return self.resdb.usable_by(item.name, self.job) is not False

    def ok(self):
        self.result = list(self.order)
        self.win.destroy()


class NamePicker:
    """Small window for picking several WS, spells or abilities from a list (with search and group filter).
    The chosen [{en, ja, group}] go in self.result."""

    def __init__(self, parent, title, items, note=""):
        self.items = items
        self.result = []
        self.all_label = L("すべて", "All")
        self.win = tk.Toplevel(parent)
        self.win.title(title)
        self.win.geometry("560x600")
        self.win.transient(parent)
        top = ttk.Frame(self.win, padding=8)
        top.pack(fill="x")
        ttk.Label(top, text=L("検索", "Search")).pack(side="left")
        self.query = tk.StringVar()
        ent = ttk.Entry(top, textvariable=self.query)
        ent.pack(side="left", fill="x", expand=True, padx=6)
        self.query.trace_add("write", lambda *a: self.fill())
        self.group = tk.StringVar(value=self.all_label)
        groups = [self.all_label] + CH.groups_of(items)
        cb = ttk.Combobox(top, textvariable=self.group, values=groups, state="readonly", width=24)
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda e: self.fill())
        if note:
            ttk.Label(self.win, text=note, foreground="#555", padding=(8, 0), wraplength=520).pack(anchor="w")
        ttk.Label(self.win, text=L("使いたいものを選んでください (Ctrl や Shift を押しながらクリックで、複数)。",
                                   "Select the ones you want (Ctrl/Shift+click to select several)."),
                  padding=(8, 2)).pack(anchor="w")
        frame = ttk.Frame(self.win, padding=8)
        frame.pack(fill="both", expand=True)
        self.box = tk.Listbox(frame, selectmode="extended", exportselection=False)
        sb = ttk.Scrollbar(frame, orient="vertical", command=self.box.yview)
        self.box.config(yscrollcommand=sb.set)
        self.box.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        bottom = ttk.Frame(self.win, padding=8)
        bottom.pack(fill="x")
        ttk.Button(bottom, text=L("選んだものを足す", "Add selected"), command=self.ok).pack(side="right")
        ttk.Button(bottom, text=L("やめる", "Cancel"), command=self.win.destroy).pack(side="right", padx=6)
        self.shown = []
        self.fill()
        ent.focus_set()
        self.win.grab_set()
        parent.wait_window(self.win)

    @staticmethod
    def label(item):
        if i18n.is_en():
            return item["en"]
        return "%s  (%s)" % (item["ja"], item["en"]) if item["ja"] != item["en"] else item["en"]

    def fill(self):
        q = self.query.get().strip().lower()
        g = self.group.get()
        self.box.delete(0, "end")
        self.shown = [it for it in self.items
                      if (g == self.all_label or it["group"] == g)
                      and (not q or q in it["ja"].lower() or q in it["en"].lower())]
        for it in self.shown:
            self.box.insert("end", self.label(it))

    def ok(self):
        self.result = [self.shown[i] for i in self.box.curselection()]
        self.win.destroy()


class AbilityGearPicker:
    """Small window for choosing ability gear from what you own.
    rows: [{entry, gen, spec, item}]. Initially, the most upgraded piece you own is selected for each ability.
    The chosen rows go in self.result (only the most upgraded one per ability and slot).
    In English mode, gear names are shown with their English names from res (when resdb exists and has them)."""

    def __init__(self, parent, title, rows, missing=(), resdb=None):
        self.rows = rows
        self.resdb = resdb
        self.result = []
        self.dropped = 0
        self.win = tk.Toplevel(parent)
        self.win.title(title)
        self.win.geometry("680x520")
        self.win.transient(parent)
        ttk.Label(self.win, wraplength=640, justify="left", padding=(8, 6),
                  text=L("持っている装備のうち、アビリティを強化するものです。強化すると名前が変わるものも、世代ごとに探しています。"
                         "いちばん強化の進んだものを、最初から選んであります。使う装備に印を付けてください "
                         "(同じアビリティ・同じ部位で複数選んだときは、強化の進んだ 1 つだけを使います)。",
                         "Gear you own that enhances job abilities. Every upgrade stage (e.g. +1, +2, +3) is checked, "
                         "and the most upgraded piece is preselected. Select the gear to use "
                         "(if you pick several for the same ability and slot, only the most upgraded one is used).")).pack(anchor="w")
        frame = ttk.Frame(self.win, padding=8)
        frame.pack(fill="both", expand=True)
        self.box = tk.Listbox(frame, selectmode="extended", exportselection=False)
        sb = ttk.Scrollbar(frame, orient="vertical", command=self.box.yview)
        self.box.config(yscrollcommand=sb.set)
        self.box.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        best = {}
        for i, r in enumerate(rows):
            self.box.insert("end", self.label(r))
            key = AG.pick_key(r["entry"])
            if key not in best or r["gen"] >= rows[best[key]]["gen"]:
                best[key] = i
        for i in best.values():
            self.box.selection_set(i)
        self.detail = ttk.Label(self.win, text="", wraplength=640, foreground="#555", padding=(8, 0))
        self.detail.pack(anchor="w")
        self.box.bind("<<ListboxSelect>>", lambda e: self.show_detail())
        if missing:
            ttk.Label(self.win, wraplength=640, foreground="#a33", padding=(8, 2),
                      text=L("持っていない (一覧に見つからなかった): ", "Not found in your inventory: ")
                      + L("、", ", ").join(missing)).pack(anchor="w")
        bottom = ttk.Frame(self.win, padding=8)
        bottom.pack(fill="x")
        ttk.Button(bottom, text=L("選んだ装備を足す", "Add selected"), command=self.ok).pack(side="right")
        ttk.Button(bottom, text=L("やめる", "Cancel"), command=self.win.destroy).pack(side="right", padx=6)
        self.show_detail()
        self.win.grab_set()
        parent.wait_window(self.win)

    def label(self, r):
        e, it = r["entry"], r["item"]
        aug = L("  (オーグメント付き)", "  (augmented)") if "augments" in it.raw else ""
        return "%s [%s]  %s%s" % (ability_display(e), slot_name(e["slot"]), item_display(it.name, self.resdb), aug)

    def show_detail(self):
        sel = self.box.curselection()
        if not sel:
            self.detail.config(text="")
            return
        r = self.rows[sel[-1]]
        e, note = r["entry"], r["spec"].get("note")
        when = AG.timing_name(e["timing"])
        if e.get("cast_phase"):
            when += " (%s%s%s)" % (AG.cast_on_name(e.get("cast_on", "Magic")), L("・", ", "),
                                   AG.cast_phase_name(e["cast_phase"]))
        # The table's effect, note and requirement text is Japanese only, so use English text in English mode
        effect = L(e["effect"], "Enhances %s" % e.get("ability_en", ""))
        if note and i18n.is_en():
            note = NOTE_EN.get(note, "See the Japanese note: " + note)
        requires = e.get("requires")
        if requires and i18n.is_en():
            requires = "Must be learned with merit points."
        self.detail.config(text="%s\n%s%s%s%s" % (effect, L("着るとき: ", "When worn: "), when,
                                                 ("\n" + L("注意: ", "Note: ") + note) if note else "",
                                                 ("\n" + L("使うには: ", "Requires: ") + requires) if requires else ""))

    def ok(self):
        chosen = [self.rows[i] for i in self.box.curselection()]
        best = {}
        for r in chosen:
            key = AG.pick_key(r["entry"])
            if key not in best or r["gen"] >= best[key]["gen"]:
                best[key] = r
        self.dropped = len(chosen) - len(best)
        self.result = list(best.values())
        self.win.destroy()


class App:
    def __init__(self, root):
        self.root = root
        root.geometry("1040x700")
        self.project = Project("SMN")
        self.settings = load_settings()
        remembered = self.settings.get("data_dir", "")
        self.data_dir = tk.StringVar(value=remembered if remembered and os.path.isdir(remembered) else default_data_dir())
        self.job_var = tk.StringVar(value=self.project.job)
        self.weapons_var = tk.BooleanVar(value=False)
        self.lockstyle_var = tk.StringVar(value="")
        self.project_path = None     # Work file last saved / opened (the target for auto-save on close)
        self._traces = []            # Traces _build puts on variables that survive a rebuild (data_dir etc.), removed on rebuild
        self._build()
        self.update_resdb()
        self.refresh()
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        # Open the previous work (last saved / opened / saved on close)
        last = self.settings.get("last_project")
        if last and os.path.isfile(last):
            self.load_project_file(last, quiet=True)

    def autosave_path(self):
        """Where to save on close: the work file last saved / opened, or <job>_kit.json in the data folder if none."""
        if self.project_path:
            return self.project_path
        d = self.data_dir.get().strip()
        return os.path.join(d, "%s_kit.json" % self.project.job) if d and os.path.isdir(d) else None

    def on_close(self):
        """Auto-save the work on close. If the file exists, ask before overwriting; on No, return without closing."""
        if not any(self.project.has_work(j) for j in C.ALL_JOBS):
            self.root.destroy()          # nothing has been worked on, so close without saving
            return
        path = self.autosave_path()
        if not path:
            path = filedialog.asksaveasfilename(title=L("閉じる前に作業を保存", "Save your work before closing"),
                                                defaultextension=".json",
                                                filetypes=[("JSON", "*.json")], initialfile="%s_kit.json" % self.project.job)
            if not path:
                return                   # no save location chosen, so return without closing
        elif os.path.exists(path):
            # Already saved (just saved, or opened and unchanged) with identical content: close without asking
            text = self.project.to_json()
            try:
                with open(path, encoding="utf-8") as f:
                    if f.read() == text:
                        self.remember_file("last_project", path)
                        self.root.destroy()
                        return
            except (OSError, UnicodeDecodeError):
                pass                     # if it can't be read, ask as usual
            if not messagebox.askyesno(APP_NAME, L("閉じる前に、作業を保存します。\n\n%s\n\nこのファイルはすでにあります。上書きして閉じますか?\n"
                                                   "(いいえを押すと、閉じずに画面に戻ります)",
                                                   "Your work will be saved before closing.\n\n%s\n\nThis file already exists. "
                                                   "Overwrite it and close?\n(No returns to the window without closing.)") % path):
                return
        try:
            atomic_write(path, self.project.to_json())
        except OSError as ex:
            messagebox.showerror(APP_NAME, L("保存できなかったので、閉じずに戻ります。\n%s",
                                             "Couldn't save, so the window stays open.\n%s") % ex)
            return
        self.remember_file("last_project", path)      # open this work on next launch
        self.root.destroy()

    # --- Language ---
    def on_lang(self):
        """Switch to the language picked in the top-row Language selector. Saves it to settings and rebuilds the window on the spot."""
        code = dict(LANG_CHOICES).get(self.lang_var.get(), "ja")
        if code == i18n.lang():
            return
        i18n.set_lang(code)
        self.settings["lang"] = code
        save_settings(self.settings)
        self.rebuild()

    def rebuild(self):
        """Rebuild the window in the current language. Work (self.project), data folder, job, selected row etc. are kept."""
        sel = self.current_path()
        try:
            kind_index = [k[1] for k in self._kinds_shown].index(self.kind_var.get())
        except (AttributeError, ValueError):
            kind_index = 0
        recv_auto = self.recv_auto_var.get() if hasattr(self, "recv_auto_var") else True
        for var, tid in self._traces:
            try:
                var.trace_remove("write", tid)
            except tk.TclError:
                pass
        self._traces = []
        for w in self.root.winfo_children():
            w.destroy()
        self._build()
        ks = self._kinds_shown
        if 0 <= kind_index < len(ks):
            self.kind_var.set(ks[kind_index][1])
        self.recv_auto_var.set(recv_auto)
        self.refresh_name_choices()
        self.show_lockstyle()
        self.update_recv_auto_box()
        self.refresh(select=sel)
        self.say(L("表示を日本語にしました。", "Switched the display to English."))

    def _trace(self, var, fn):
        """Add a trace to a variable that survives a rebuild (remembered so it can be removed on rebuild)."""
        self._traces.append((var, var.trace_add("write", lambda *a: fn())))

    # --- Building the window ---
    def _build(self):
        self.root.title(L("%s %s — GearSwap のひな形を作る", "%s %s — GearSwap template builder") % (APP_NAME, VERSION))
        top = ttk.Frame(self.root, padding=8)
        top.pack(fill="x")
        ttk.Label(top, text=L("ジョブ", "Job")).pack(side="left")
        cb = ttk.Combobox(top, textvariable=self.job_var, values=C.ALL_JOBS, width=6, state="readonly")
        cb.pack(side="left", padx=(4, 12))
        cb.bind("<<ComboboxSelected>>", lambda e: self.on_job())
        ttk.Label(top, text=L("ロックスタイル番号", "Lockstyle set")).pack(side="left")
        ttk.Entry(top, textvariable=self.lockstyle_var, width=5).pack(side="left", padx=(4, 12))
        self._trace(self.lockstyle_var, self.on_lockstyle)
        ttk.Checkbutton(top, text=L("武器 (メイン・サブ・遠隔・矢弾) もセットに含める",
                                    "Include weapons (main / sub / range / ammo) in sets"),
                        variable=self.weapons_var, command=self.on_weapons).pack(side="left")
        ttk.Button(top, text=L("作業を保存", "Save work"), command=self.save_project).pack(side="right")
        ttk.Button(top, text=L("作業を開く", "Open work"), command=self.open_project).pack(side="right", padx=4)
        # Language switcher (labels are the same in either language)
        self.lang_var = tk.StringVar(value=[n for n, c in LANG_CHOICES if c == i18n.lang()][0])
        lang_cb = ttk.Combobox(top, textvariable=self.lang_var, values=[n for n, _c in LANG_CHOICES],
                               width=8, state="readonly")
        lang_cb.pack(side="right", padx=(4, 12))
        lang_cb.bind("<<ComboboxSelected>>", lambda e: self.on_lang())
        self.lang_cb = lang_cb
        ttk.Label(top, text="Language / 言語").pack(side="right")

        # Jobs with work get their own row below the top bar and wrap to the window width
        # (in the top bar they got cut off as jobs were added, and pushed the Save/Open buttons out of the window)
        jobs_row = ttk.Frame(self.root, padding=(8, 0, 8, 4))
        jobs_row.pack(fill="x")
        self.jobs_lbl = ttk.Label(jobs_row, text="", foreground="#555", justify="left")
        self.jobs_lbl.pack(side="left", fill="x", expand=True)
        jobs_row.bind("<Configure>", lambda e: self.jobs_lbl.config(wraplength=max(200, e.width - 16)))

        folder = ttk.Frame(self.root, padding=(8, 0, 8, 6))
        folder.pack(fill="x")
        ttk.Label(folder, text=L("GearSwap の data フォルダー", "GearSwap data folder")).pack(side="left")
        entry_box = ttk.Frame(folder)
        entry_box.pack(side="left", fill="x", expand=True, padx=6)
        self.dir_entry = ttk.Entry(entry_box, textvariable=self.data_dir)
        self.dir_entry.pack(fill="x")
        # While the field is empty, overlay a faint hint (it disappears once you type)
        self.dir_hint = tk.Label(entry_box, text=L("例: C:\\Windower4\\addons\\gearswap\\data   (右の「選ぶ…」で探せます)",
                                                   "e.g. C:\\Windower4\\addons\\gearswap\\data   (or use Browse… on the right)"),
                                 foreground="#999", background="white", anchor="w")
        self.dir_hint.place(in_=self.dir_entry, x=4, y=2, relheight=0.9)
        self.dir_hint.bind("<Button-1>", lambda e: self.dir_entry.focus_set())
        self._trace(self.data_dir, self.update_dir_hint)
        self.update_dir_hint()     # don't show the hint when a remembered folder is already filled in (the overlap makes it look empty)
        self._trace(self.data_dir, self.remember_data_dir)
        ttk.Button(folder, text=L("選ぶ…", "Browse…"), command=self.choose_dir).pack(side="left")

        body = ttk.Panedwindow(self.root, orient="horizontal")
        body.pack(fill="both", expand=True, padx=8)

        left = ttk.Frame(body)
        body.add(left, weight=2)
        ttk.Label(left, text=L("どの場面の装備を作りますか", "Which set do you want to build?")).pack(anchor="w")
        self.tree = ttk.Treeview(left, columns=("state",), show="tree headings", selectmode="browse", height=18)
        self.tree.heading("#0", text=L("場面", "Set"))
        self.tree.heading("state", text=L("状態", "Status"))
        self.tree.column("#0", width=300)
        self.tree.column("state", width=110, anchor="center")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.show_detail())

        add = ttk.LabelFrame(left, text=L("技ごとの追加 (特定の技・魔法だけ、別の装備にしたいとき)",
                                          "Add per skill (separate gear for a specific WS, ability or spell)"), padding=6)
        add.pack(fill="x", pady=(6, 0))
        self.recv_auto_anchor = add
        self._kinds_shown = kinds()
        self.kind_var = tk.StringVar(value=self._kinds_shown[0][1])
        ttk.Combobox(add, textvariable=self.kind_var, values=[k[1] for k in self._kinds_shown], width=14,
                     state="readonly").pack(side="left")
        self.name_var = tk.StringVar()
        # Dropdown: actions usable by the current job (WS filtered by weapon type). You can also type a name to search
        self.name_cb = ttk.Combobox(add, textvariable=self.name_var, height=20)
        self.name_cb.pack(side="left", fill="x", expand=True, padx=6)
        self.name_cb.bind("<Return>", lambda e: self.add_with_export())
        self._name_map = {}
        ttk.Button(add, text=L("export を割り当てて追加…", "Assign export & add…"), command=self.add_with_export).pack(side="left")
        # Shown only when Phalanx received is picked: whether to swap automatically on Phalanx
        self.recv_auto_var = tk.BooleanVar(value=True)
        self.recv_auto_box = ttk.Checkbutton(left, text=L("ファランクスに反応して自動で着替える (自分に向けた詠唱の開始で着て、届いたら戻す)",
                                                          "Swap automatically for incoming Phalanx (equip when a cast on you "
                                                          "starts, swap back when it lands)"),
                                             variable=self.recv_auto_var)
        self.name_var.trace_add("write", lambda *a: self.update_recv_auto_box())
        ab = ttk.Frame(left)
        ab.pack(fill="x", pady=(4, 0))
        ttk.Button(ab, text=L("アビリティ強化の装備から追加…", "Add job ability gear…"),
                   command=self.pick_ability_gear).pack(side="left")
        ttk.Label(ab, text=L("(ＧＬホーン+1 など、持っている強化装備を自動で探します)",
                             "(finds ability-enhancing gear you own, e.g. Glyphic Horn +1)"),
                  foreground="#555").pack(side="left", padx=6)
        self.kind_help = ttk.Label(left, text="", wraplength=380, foreground="#555")
        self.kind_help.pack(anchor="w", pady=(2, 0))
        self.kind_var.trace_add("write", lambda *a: self.update_kind_help())
        self.kind_var.trace_add("write", lambda *a: self.refresh_name_choices())
        self.kind_var.trace_add("write", lambda *a: self.update_recv_auto_box())
        self.update_kind_help()

        right = ttk.Frame(body, padding=(10, 0, 0, 0))
        body.add(right, weight=3)
        self.title_lbl = ttk.Label(right, text="", font=("", 12, "bold"))
        self.title_lbl.pack(anchor="w")
        self.path_lbl = ttk.Label(right, text="", foreground="#666")
        self.path_lbl.pack(anchor="w")
        self.help_lbl = ttk.Label(right, text="", wraplength=520, justify="left")
        self.help_lbl.pack(anchor="w", pady=(6, 6))
        # Match the help text's wrap width to the window width
        right.bind("<Configure>", lambda e: self.help_lbl.config(wraplength=max(200, e.width - 24)))
        btns = ttk.Frame(right)
        btns.pack(anchor="w")
        self.assign_btn = ttk.Button(btns, text=L("export を割り当てる…", "Assign export…"), command=self.assign_export)
        self.assign_btn.pack(side="left")
        self.clear_btn = ttk.Button(btns, text=L("割り当てを外す", "Clear"), command=self.clear_assignment)
        self.clear_btn.pack(side="left", padx=6)
        self.pick_btn = ttk.Button(btns, text=L("所持品の一覧から選ぶ…", "Pick from inventory…"), command=self.pick_weapons)
        self.pick_btn.pack(side="left", padx=(6, 0))
        self.remove_btn = ttk.Button(btns, text=L("この追加を削除", "Remove this set"), command=self.remove_custom)
        self.remove_btn.pack(side="left")
        # Shown only for midcast (Elemental Magic): auto-pick of elemental obi / Orpheus's Sash
        self.waist_box = ttk.Frame(right)
        self.waist_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.waist_box, text=L("属性帯 (八輪の帯) とオルペウスサッシュを自動で選ぶ (天候・曜日・対象との距離で、効果の大きいほう)",
                                               "Auto-pick Hachirin-no-Obi or Orpheus's Sash (whichever is stronger "
                                               "for the weather, day and target distance)"),
                        variable=self.waist_var, command=self.on_auto_waist).pack(anchor="w")
        ttk.Label(self.waist_box, text=L("(震天動地の章が効いている間は腰を替えず、震天動地の章の装備を最優先で着ます)",
                                         "(While Immanence is active, the waist isn't swapped and your Immanence gear takes priority.)"),
                  foreground="#666").pack(anchor="w")
        # Shown only for PUP automaton WS / enmity sets: automatic pre-equip
        self.pup_box = ttk.Frame(right)
        self.pup_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.pup_box, text=L("自動で先に着る (オートマトンの TP 930 以上で WS の装備・ストロボ / フラッシュバルブの"
                                             "再使用の 2 秒前に敵対心の装備)",
                                             "Pre-equip automatically (WS gear when the automaton has 930+ TP; enmity gear "
                                             "2 seconds before Strobe / Flashbulb is ready)"),
                        variable=self.pup_var, command=self.on_pup_auto).pack(anchor="w")
        ttk.Label(self.pup_box, text=L("(ゲームでは //gs c toggle PetAutoGear で一時的に止められます)",
                                       "(In game, //gs c toggle PetAutoGear turns this off temporarily.)"),
                  foreground="#666").pack(anchor="w")
        # Shown only for PLD's spell interruption set: 3-stage swap (Fast Cast -> interruption -> landing gear)
        self.stage_box = ttk.Frame(right)
        self.stage_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.stage_box, text=L("3 段階で着替える (詠唱中は詠唱中断、着弾の直前にケアル・敵対心などの装備)",
                                               "3-stage swap (spell interruption gear while casting, then Cure / enmity gear "
                                               "just before the spell lands)"),
                        variable=self.stage_var, command=self.on_three_stage).pack(anchor="w")
        self.stage_fc_lbl = ttk.Label(self.stage_box, text="", foreground="#666")
        self.stage_fc_lbl.pack(anchor="w", pady=(2, 0))
        # Shown only for "precast (Fast Cast)" (all jobs): the set's Fast Cast total
        self.fc_box = ttk.Frame(right)
        fc_row = ttk.Frame(self.fc_box)
        fc_row.pack(anchor="w")
        ttk.Label(fc_row, text=L("このセットのファストキャスト (%)", "Fast Cast in this set (%)")).pack(side="left")
        self.fc_var = tk.StringVar(value="0")
        ttk.Entry(fc_row, textvariable=self.fc_var, width=5).pack(side="left", padx=4)
        self.fc_var.trace_add("write", lambda *a: self.on_fast_cast())
        ttk.Button(fc_row, text=L("装備から計算", "Calculate from gear"), command=self.calc_fast_cast).pack(side="left", padx=(0, 6))
        ttk.Label(fc_row, text=L("(export を割り当てると自動で計算します。ナイトの 3 段階の着替えに使います)",
                                 "(Calculated automatically when you assign an export. Used for PLD's 3-stage swap.)"),
                  foreground="#666").pack(side="left")
        # Warning when Fast Cast goes over the cap (80%) and is wasted
        self.fc_advice = ttk.Label(self.fc_box, text="", foreground="#a33", wraplength=520, justify="left")
        self.fc_advice.pack(anchor="w", pady=(2, 0))
        self.gear_txt = tk.Text(right, height=14, wrap="none", state="disabled", background="#fafafa")
        self.gear_txt.pack(fill="both", expand=True, pady=(8, 0))

        bottom = ttk.Frame(self.root, padding=8)
        bottom.pack(fill="x")
        self.preview_btn = ttk.Button(bottom, text=L("Lua を確認", "Preview Lua"), command=self.preview)
        self.preview_btn.pack(side="left")
        self.make_btn = ttk.Button(bottom, text=L("Lua を作る", "Make Lua"), command=self.make_lua)
        self.make_btn.pack(side="left", padx=6)
        self.status = ttk.Label(bottom, text=L("ゲームで装備を着て //gs export を実行し、できたファイルを割り当ててください。",
                                               "Equip your gear in game, run //gs export, then assign the file it creates."))
        self.status.pack(side="left", padx=10)

    # --- Display updates ---
    def jobs_text(self):
        worked = [j for j in C.ALL_JOBS if self.project.has_work(j)]
        return (L("作業のあるジョブ: ", "Jobs with work: ") + L("・", ", ").join(worked)) if worked else ""

    def refresh(self, select=None):
        self.jobs_lbl.config(text=self.jobs_text())
        sel = select or self.current_path()
        self.tree.delete(*self.tree.get_children())
        self._rows = {}
        for e in self.project.entries():
            iid = self.tree.insert("", "end", text=e["title"],
                                   values=(state_on() if self.project.is_assigned(e["path"]) else state_off(),))
            self._rows[iid] = e
            if e["path"] == sel:
                self.tree.selection_set(iid)
                self.tree.focus(iid)
        if not self.tree.selection() and self.tree.get_children():
            first = self.tree.get_children()[0]
            self.tree.selection_set(first)
            self.tree.focus(first)
        self.show_detail()

    def current(self):
        sel = self.tree.selection()
        return self._rows.get(sel[0]) if sel else None

    def current_path(self):
        try:
            e = self.current() if hasattr(self, "_rows") else None
        except tk.TclError:
            e = None
        return e["path"] if e else None

    def item_name(self, name):
        """Display name for gear (English name from res in English mode)."""
        return item_display(name, self.project.resdb)

    def set_gear_text(self, text):
        self.gear_txt.config(state="normal")
        self.gear_txt.delete("1.0", "end")
        self.gear_txt.insert("1.0", text)
        self.gear_txt.config(state="disabled")

    def show_detail(self):
        e = self.current()
        if not e:
            return
        self.title_lbl.config(text=e["title"])
        self.path_lbl.config(text=L("Lua での名前: %s", "Lua name: %s") % e["path"])
        note = "" if e["verified"] else L("\n(このセットの扱いは、ゲーム内での確認がまだです)",
                                          "\n(How this set behaves hasn't been verified in game yet.)")
        self.help_lbl.config(text=e["help"] + note)
        self.remove_btn.state(["!disabled"] if e["custom"] else ["disabled"])
        if e["path"] in ELEMENTAL_SETS:
            self._stage_loading = True
            try:
                self.waist_var.set(self.project.auto_waist)
            finally:
                self._stage_loading = False
            if not self.waist_box.winfo_manager():
                self.waist_box.pack(anchor="w", pady=(6, 0), before=self.gear_txt)
        else:
            self.waist_box.pack_forget()
        if self.project.job == "PUP" and e["path"] in (G.PUP_WS_SET, G.PUP_ENMITY_SET):
            self._stage_loading = True
            try:
                self.pup_var.set(self.project.pup_auto)
            finally:
                self._stage_loading = False
            if not self.pup_box.winfo_manager():
                self.pup_box.pack(anchor="w", pady=(6, 0), before=self.gear_txt)
        else:
            self.pup_box.pack_forget()
        if self.project.job == "PLD" and e["path"] == "sets.midcast.interruption":
            self._stage_loading = True
            try:
                self.stage_var.set(self.project.three_stage)
            finally:
                self._stage_loading = False
            self.stage_fc_lbl.config(text=L("着弾の時刻の計算に使うファストキャスト: %d%% (「詠唱の開始 (ファストキャスト)」で計算・変更。"
                                            "サポ赤の特性は自動で足します)",
                                            "Fast Cast used to time the landing swap: %d%% (calculate or edit it in the "
                                            "precast (Fast Cast) set; /RDM's trait is added automatically)")
                                     % self.project.fast_cast)
            if not self.stage_box.winfo_manager():
                self.stage_box.pack(anchor="w", pady=(6, 0), before=self.gear_txt)
        else:
            self.stage_box.pack_forget()
        if e["path"] == "sets.precast.FC":
            self._stage_loading = True
            try:
                self.fc_var.set(str(self.project.fast_cast))
            finally:
                self._stage_loading = False
            self.fc_advice.config(text=FCALC.advice(self.project.fast_cast, self.project.job))
            if not self.fc_box.winfo_manager():
                self.fc_box.pack(anchor="w", pady=(6, 0), before=self.gear_txt)
        else:
            self.fc_box.pack_forget()
        self.assign_btn.config(text=L("export から武器を足す…", "Add weapons from export…") if e.get("weapon_slot") else
                               L("export から矢弾を選ぶ…", "Pick ammo from export…") if e.get("ammo_role") else
                               L("export を割り当てる…", "Assign export…"))
        self.pick_btn.state(["!disabled"] if (e.get("weapon_slot") or e.get("ammo_role")) else ["disabled"])
        if e.get("ammo_role"):
            role = e["ammo_role"]
            if role == "special":
                rows = ["%s  ← %s" % (self.ws_label(ws), self.item_name(it.name)) for ws, it in sorted(self.project.ws_ammo.items())]
                text = "\n".join(rows) if rows else L("(まだ特殊弾が選ばれていません)", "(No special ammo chosen yet.)")
            else:
                it = self.project.ammo.get(role)
                text = self.item_name(it.name) if it else L("(まだ矢弾が選ばれていません)", "(No ammo chosen yet.)")
            self.set_gear_text(text)
            return
        if e.get("weapon_slot"):
            weapons = self.project.weapons.get(e["weapon_slot"], [])
            names = G.weapon_names(weapons)
            text = ("\n".join("%d. %s" % (i + 1, self.item_name(n)) for i, n in enumerate(names)) if names
                    else L("(まだ武器が足されていません)\n\n武器を 1 本ずつ装備して、//gs export で書き出し、「export から武器を足す…」で足してください。",
                           "(No weapons added yet.)\n\nEquip one weapon at a time, run //gs export, "
                           "then add it with \"Add weapons from export…\"."))
            self.set_gear_text(text)
            return
        items = self.project.assignments.get(e["path"], {})
        lines = []
        for slot in EP.SLOTS:
            it = items.get(slot)
            if it is None:
                continue
            skipped = (slot in ("main", "sub", "range", "ammo")) and not self.project.include_weapons
            if slot == "ammo" and G.ammo_as_gear(self.project.job):
                skipped = False
            if slot in ("main", "sub") and self.project.job == "PLD" and e["path"] in G.PLD_WEAPON_SETS:
                skipped = False     # PLD's magic / status resistance sets swap weapons too
            if slot == "main" and self.project.job == "PUP" and e["path"] in (G.PUP_WS_SET, "sets.precast.JA.Maneuver"):
                skipped = False     # PUP automaton WS sets also swap the main weapon (Xiucoatl etc.)
            if slot in ("main", "sub", "range") and (e["path"].startswith("sets.midcast.Increased") or e["path"] in ("sets.Sleep",) + G.PHALANX_SETS):
                skipped = False     # Received-buff sets (sword/shield Phalanx received+ etc.) and the wake-from-sleep set swap weapons too (same as keep_for in generator.py)
            lines.append("%s\t%s%s" % (slot_name(slot), self.item_name(it.name),
                                         L("   ← 武器は出力に含めません", "   ← weapons are left out of the Lua") if skipped else ""))
        text = "\n".join(lines) if lines else L("(まだ装備が割り当てられていません)", "(No gear assigned yet.)")
        self.set_gear_text(text)

    def update_resdb(self):
        """Find the res folder of the same Windower install from the data folder's location (used to map Japanese names to English)."""
        res = R.guess_res_dir(self.data_dir.get())
        old = self.project.resdb.res_dir if self.project.resdb is not None else None
        if self.project.resdb is None or old != res:
            self.project.set_resdb(R.ResDB(res) if res else None)
            self.refresh_name_choices()

    def update_dir_hint(self):
        if self.data_dir.get():
            self.dir_hint.place_forget()
        else:
            self.dir_hint.place(in_=self.dir_entry, x=4, y=2, relheight=0.9)

    def kind_index(self):
        return [k[1] for k in self._kinds_shown].index(self.kind_var.get())

    def refresh_name_choices(self):
        """Rebuild the dropdown contents for the current kind and job (needs res)."""
        if not hasattr(self, "name_cb"):
            return
        kind = self.kind_index()
        items = []
        if self.project.resdb is not None and self.project.resdb.available():
            items = CH.choices(self.project.resdb, ["ws", "ja", "magic", "pet", "received"][kind], self.project.job)
        elif kind == 4:
            items = CH.choices(None, "received", self.project.job)    # received-buff gear can be picked even without res
        self._name_map = {}
        labels = []
        for it in items:
            if i18n.is_en():
                label = C.received_label(it["en"]) if kind == 4 else it["en"]
            else:
                label = "%s  (%s)" % (it["ja"], it["en"]) if it["ja"] != it["en"] else it["en"]
            if label not in self._name_map:
                self._name_map[label] = (it["en"], it["ja"])
                labels.append(label)
        self.name_cb.config(values=labels)

    def _chosen_received(self):
        """What's picked under "Received buffs" (IncreasedPhalanx etc.). None for other kinds or when nothing is picked."""
        if self.kind_index() != 4:
            return None
        text = self.name_var.get().strip()
        if text in self._name_map:      # picked from the dropdown (label -> English name)
            return self._name_map[text][0]
        st, en, _ja = self.project.resolve(4, text)
        return en if st == "ok" else None

    def update_recv_auto_box(self):
        """Show the auto-swap checkbox only when Phalanx received is picked (filled with the current setting)."""
        if not hasattr(self, "recv_auto_box"):
            return
        if self._chosen_received() == "IncreasedPhalanx":
            self.recv_auto_var.set(self.project.received_auto("IncreasedPhalanx"))
            if not self.recv_auto_box.winfo_manager():
                self.recv_auto_box.pack(anchor="w", after=self.recv_auto_anchor)
        else:
            self.recv_auto_box.pack_forget()

    def update_kind_help(self):
        for base, label, text in self._kinds_shown:
            if label == self.kind_var.get():
                self.kind_help.config(text=text)
                return

    # --- Actions ---
    def on_lockstyle(self):
        """Store the lockstyle set number (1-200) in the current job's work. Blank means unused."""
        if getattr(self, "_lockstyle_loading", False):
            return
        text = self.lockstyle_var.get().strip()
        n = self.project.set_lockstyle(text)
        if text and n is None:
            self.say(L("ロックスタイル番号は 1〜200 の数字で入れてください (空なら使いません)。",
                       "Enter a lockstyle set number from 1 to 200 (leave blank to skip)."))
        elif n:
            self.say(L("%s は、読み込んだあとロックスタイル %d をかけます (//gs c lockstyleset でも)。",
                       "%s will apply lockstyle set %d after loading (or use //gs c lockstyleset).") % (self.project.job, n))
        self.jobs_lbl.config(text=self.jobs_text())

    def show_lockstyle(self):
        """Show the current job's lockstyle number in the field (on job change or when opening work)."""
        self._lockstyle_loading = True
        try:
            self.lockstyle_var.set(str(self.project.lockstyle) if self.project.lockstyle else "")
        finally:
            self._lockstyle_loading = False

    def on_job(self):
        self.project.set_job(self.job_var.get())
        self.show_lockstyle()
        self.refresh_name_choices()
        self.refresh()
        self.say(L("%s のセット一覧にしました。", "Showing sets for %s.") % self.project.job)

    def on_weapons(self):
        self.project.include_weapons = self.weapons_var.get()
        self.show_detail()

    def remember_data_dir(self):
        """Remember the data folder (so it's prefilled on next launch). Only folders that exist."""
        d = self.data_dir.get().strip()
        if d and os.path.isdir(d) and self.settings.get("data_dir") != d:
            self.settings["data_dir"] = d
            save_settings(self.settings)

    def export_start(self, key):
        """Starting location for the file dialog: folder of the last chosen file -> export in the data folder -> none."""
        last = self.settings.get(key, "")
        if last and os.path.isdir(os.path.dirname(last)):
            return os.path.dirname(last), os.path.basename(last)
        exp = os.path.join(self.data_dir.get() or "", "export")
        return (exp if os.path.isdir(exp) else None), ""

    def remember_file(self, key, path):
        if path and self.settings.get(key) != path:
            self.settings[key] = path
            save_settings(self.settings)

    def choose_dir(self):
        d = filedialog.askdirectory(title=L("GearSwap の data フォルダーを選んでください (…/Windower4/addons/gearswap/data)",
                                            "Choose your GearSwap data folder (…/Windower4/addons/gearswap/data)"))
        if d:
            self.data_dir.set(d)

    def ask_equipped_set(self, title=None):
        """Ask for a //gs export file of the equipped gear and return {slot: Item}. None if cancelled or unreadable."""
        if title is None:
            title = L("//gs export で書き出したファイルを選んでください", "Choose a file made with //gs export")
        start, _name = self.export_start("last_export")
        path = filedialog.askopenfilename(title=title, initialdir=start,
                                          filetypes=[("Lua", "*.lua"), (L("すべて", "All files"), "*.*")])
        if not path:
            return None
        try:
            text = EP.read_file(path)
        except OSError as ex:
            messagebox.showerror(APP_NAME, L("ファイルを読めませんでした。\n%s", "Couldn't read the file.\n%s") % ex)
            return None
        if EP.looks_like_inventory(text):
            messagebox.showwarning(APP_NAME, L("このファイルは、所持品の一覧のようです (同じ部位が何回も出てきます)。\n"
                                               "セットにしたい装備を着た状態で、//gs export を実行して、できたファイルを選んでください。",
                                               "This looks like a full inventory list (the same slot appears many times).\n"
                                               "Equip the gear for this set, run //gs export, and choose the file it creates."))
            return None
        items = EP.parse_equipped_set(text)
        unread = self.unread_note(text)
        if not items:
            messagebox.showwarning(APP_NAME, L("装備を読めませんでした。//gs export で書き出したファイルか、確認してください。",
                                               "No gear found in this file. Make sure it was made with //gs export.") + unread)
            return None
        if unread:
            # Don't silently skip typos made when editing by hand (ear1== etc.). Whatever could be read is still assigned
            messagebox.showwarning(APP_NAME, L("次の行は読めなかったので、割り当てません。\n"
                                               "書き間違い (= が 2 つ・引用符や { } の閉じ忘れなど) がないか確かめてください。"
                                               "装備の名前の代わりに変数 (gear.… など) を書いた行も読めません。",
                                               "These lines couldn't be read and won't be assigned.\n"
                                               "Check them for typos (a doubled =, a missing quote or brace). "
                                               "Lines that use a variable (gear.… etc.) instead of an item name can't be read either.") + unread)
        self.remember_file("last_export", path)    # open from the same folder next time
        return items

    @staticmethod
    def unread_note(text, limit=5):
        """Turn the unread lines into text to append to a warning ("" if there are none)."""
        lines = EP.unread_lines(text)
        if not lines:
            return ""
        out = ["", ""] + [L("%d 行目: %s", "Line %d: %s") % (no, s[:60]) for no, s in lines[:limit]]
        if len(lines) > limit:
            out.append(L("ほか %d 行", "and %d more") % (len(lines) - limit))
        return "\n".join(out)

    def add_with_export(self):
        """Add per skill: assign export gear to the action picked in the dropdown and add it.
        It only shows up in the left list once assigned (just picking it doesn't add it, to keep the list tidy)."""
        kind = self.kind_index()
        self.update_resdb()
        text = self.name_var.get().strip()
        if text in self._name_map:
            en, ja = self._name_map[text]
        else:
            status, en, ja = self.project.resolve(kind, text)
            if status == "empty":
                self.say(L("ドロップダウンから技を選んでください。", "Pick an action from the dropdown."))
                return
            if status == "notfound":
                if self.project.resdb is None or not self.project.resdb.available():
                    messagebox.showinfo(APP_NAME, L("技の一覧を出すには、Windower の res フォルダーが要ります。\n"
                                                    "上の「GearSwap の data フォルダー」を、…/Windower4/addons/gearswap/data のように選ぶと、"
                                                    "同じ Windower の res フォルダーを、自動で探します。",
                                                    "The action list needs Windower's res folder.\n"
                                                    "Set \"GearSwap data folder\" above to …/Windower4/addons/gearswap/data "
                                                    "and the res folder of that Windower install is found automatically."))
                else:
                    messagebox.showinfo(APP_NAME, L("その名前は、Windower の res に見つかりませんでした。\nドロップダウンから選んでください。",
                                                    "That name wasn't found in Windower's res.\nPlease pick from the dropdown."))
                return
        if i18n.is_en():
            shown = en
        else:
            shown = "%s (%s)" % (ja, en) if ja and ja != en else en
        items = self.ask_equipped_set(L("「%s」に使う装備を //gs export で書き出したファイルを選んでください",
                                        "Choose the //gs export file with your gear for \"%s\"") % shown)
        if items is None:
            return
        path = self.project.path_for(kind, en)
        if kind == RECEIVED_KIND and en == "IncreasedPhalanx":
            self.project.set_received_auto(en, self.recv_auto_var.get())
        self.project.add_pair(kind, en, ja)      # no-op if it already exists (the gear is replaced below)
        self.project.assign(path, items)
        self.name_var.set("")
        self.refresh(select=path)
        self.say(self.assigned_msg(shown, len(items)))

    def assigned_msg(self, name, n):
        return L("%s に、%d 個の装備を割り当てました。" % (name, n), "%s: %d item(s) assigned." % (name, n))

    def assign_export(self):
        e = self.current()
        if not e:
            return
        items = self.ask_equipped_set()
        if items is None:
            return
        if e.get("ammo_role"):
            item = items.get("ammo")
            if item is None:
                messagebox.showwarning(APP_NAME, L("このファイルには、矢弾がありません。\nその矢弾を装備した状態で、//gs export を実行したファイルを選んでください。",
                                                   "This file has no ammo.\nEquip the ammo, run //gs export, and choose that file."))
                return
            self.apply_ammo(e, [item])
            return
        if e.get("weapon_slot"):
            slot = e["weapon_slot"]
            item = items.get(slot)
            if item is None:
                messagebox.showwarning(APP_NAME, L("このファイルには、%s の武器がありません。\nその武器を装備した状態で、//gs export を実行したファイルを選んでください。",
                                                   "This file has no %s weapon.\nEquip the weapon, run //gs export, and choose that file.")
                                       % slot_name(slot))
                return
            if self.project.add_weapon(slot, item):
                self.say(L("%s に、%s を足しました。" % (e["title"], item.name),
                           "Added %s to %s." % (self.item_name(item.name), e["title"])))
            else:
                self.say(L("同じ武器が、すでに足されています。", "That weapon is already in the list."))
            self.refresh(select=e["path"])
            return
        self.project.assign(e["path"], items)
        self.refresh(select=e["path"])
        self.say(self.assigned_msg(e["title"], len(items)))
        if e["path"] == "sets.precast.FC":
            self.calc_fast_cast()       # recalculate the total when the Fast Cast set changes

    def ask_inventory(self):
        """Ask for an inventory file made with //gs export all and read it. Returns {slot: [Item]} or None."""
        start, name = self.export_start("last_inventory")
        path = filedialog.askopenfilename(title=L("//gs export all で書き出した所持品の一覧を選んでください",
                                                  "Choose the inventory file made with //gs export all"),
                                          initialdir=start, initialfile=name,
                                          filetypes=[("Lua", "*.lua"), (L("すべて", "All files"), "*.*")])
        if not path:
            return None
        try:
            text = EP.read_file(path)
        except OSError as ex:
            messagebox.showerror(APP_NAME, L("ファイルを読めませんでした。\n%s", "Couldn't read the file.\n%s") % ex)
            return None
        if EP.looks_like_inventory(text):
            self.remember_file("last_inventory", path)
        if not EP.looks_like_inventory(text):
            messagebox.showwarning(APP_NAME, L("このファイルは、所持品の一覧ではないようです。\n"
                                               "ゲームで //gs export all を実行して、できたファイルを選んでください。\n"
                                               "(着ている装備だけを書き出したファイルは、「export を割り当てる…」で使います。)",
                                               "This doesn't look like an inventory list.\n"
                                               "Run //gs export all in game and choose the file it creates.\n"
                                               "(A file with only your equipped gear goes in \"Assign export…\".)"))
            return None
        return EP.parse_inventory(text)

    def pick_ability_gear(self):
        """Find ability-enhancing gear (Glyphic Horn +1 etc.) in the inventory list, let the user choose, and add it."""
        job = self.project.job
        entries = AG.entries_for_job(job)
        if not entries:
            have = L("・", ", ").join(sorted(AG.load().keys()))
            messagebox.showinfo(APP_NAME, L("%s の、アビリティ強化の装備の対応表は、まだありません。\n"
                                            "今ある対応表: %s\n\n(「一覧から選ぶ…」で、アビリティを選んで、export を割り当てることはできます。)",
                                            "There's no job ability gear table for %s yet.\n"
                                            "Tables available: %s\n\n(You can still add a job ability under "
                                            "Add per skill and assign an export to it.)")
                                % (job, have or L("なし", "none")))
            return
        inv = self.ask_inventory()
        if inv is None:
            return
        self.update_resdb()
        rows, missing = [], []
        for e in entries:
            found = AG.owned(e, inv, self.project.resdb)
            if not found:
                missing.append("%s (%s)" % (ability_display(e), slot_name(e["slot"])))
            for gen, spec, it in found:
                rows.append(dict(entry=e, gen=gen, spec=spec, item=it))
        if not rows:
            messagebox.showinfo(APP_NAME, L("この一覧には、%s のアビリティを強化する装備が見つかりませんでした。\n(%s)",
                                            "No %s job ability gear was found in this inventory.\n(%s)")
                                % (job, L("、", ", ").join(missing)))
            return
        picker = AbilityGearPicker(self.root, L("アビリティ強化の装備を選ぶ (%s)", "Choose job ability gear (%s)") % job,
                                   rows, missing, resdb=self.project.resdb)
        last = None
        for r in picker.result:
            last = self.project.add_ability_gear(r["entry"], r["item"])
        if picker.result:
            self.refresh(select=last)
        msg = L("アビリティ強化の装備を %d 件、足しました。", "Added %d piece(s) of job ability gear.") % len(picker.result)
        if picker.dropped:
            msg += L(" (同じ部位で複数選ばれたものは、強化の進んだ 1 つにしました)",
                     " (Where several were picked for the same slot, only the most upgraded one was kept.)")
        self.say(msg)

    def pick_weapons(self):
        """Pick weapons from an inventory list made with //gs export all and add them."""
        e = self.current()
        if e and e.get("ammo_role"):
            inv = self.ask_inventory()
            if inv is None:
                return
            cands = EP.weapon_candidates(inv, "ammo")
            if not cands:
                messagebox.showinfo(APP_NAME, L("この一覧には、矢弾が見つかりませんでした。", "No ammo was found in this inventory."))
                return
            picker = WeaponPicker(self.root, L("%s を選ぶ (1 つ)", "Choose %s (one)") % e["title"], cands,
                                  resdb=self.project.resdb)
            if picker.result:
                self.apply_ammo(e, picker.result)
            return
        if not e or not e.get("weapon_slot"):
            return
        slot = e["weapon_slot"]
        inv = self.ask_inventory()
        if inv is None:
            return
        self.update_resdb()
        cands = EP.weapon_candidates(inv, slot, self.project.resdb)
        if not cands:
            messagebox.showinfo(APP_NAME, L("この一覧には、%s に使える武器が見つかりませんでした。",
                                            "No %s weapons were found in this inventory.") % slot_name(slot))
            return
        picker = WeaponPicker(self.root, L("%s の武器を選ぶ", "Choose %s weapons") % slot_name(slot), cands,
                              job=self.project.job, resdb=self.project.resdb)
        added = 0
        for item in picker.result:
            if self.project.add_weapon(slot, item):
                added += 1
        self.refresh(select=e["path"])
        self.say(L("%s の武器を %d 本、足しました。", "Added %d %s weapon(s).") % (
            (slot_name(slot), added) if not i18n.is_en() else (added, slot_name(slot))))

    def on_auto_waist(self):
        if getattr(self, "_stage_loading", False):
            return
        self.project.set_auto_waist(self.waist_var.get())
        if self.waist_var.get():
            self.say(L("精霊魔法の腰を自動で選びます (八輪の帯・オルペウスサッシュ)。",
                       "Elemental magic will auto-pick the waist (Hachirin-no-Obi / Orpheus's Sash)."))
        else:
            self.say(L("精霊魔法の腰をセットのままにします。", "Elemental magic will keep the waist from the set."))

    def on_pup_auto(self):
        if getattr(self, "_stage_loading", False):
            return
        self.project.set_pup_auto(self.pup_var.get())
        if self.pup_var.get():
            self.say(L("オートマトンの技の装備を先に着ます (自動の事前着替え)。",
                       "Automaton gear will be pre-equipped automatically."))
        else:
            self.say(L("オートマトンの技の装備を技が出たときに着ます。",
                       "Automaton gear will be equipped when the action goes off."))

    def on_three_stage(self):
        if getattr(self, "_stage_loading", False):
            return
        self.project.set_three_stage(self.stage_var.get())
        if self.stage_var.get() and not self.project.fast_cast:
            self.calc_fast_cast()       # if it's still 0, fill it in from the Fast Cast set
        elif not self.stage_var.get():
            self.say(L("3 段階の着替えを使いません。", "3-stage swap turned off."))

    def calc_fast_cast(self):
        """Add up Fast Cast from the gear in the Fast Cast set (sets.precast.FC) and fill it in."""
        self.update_resdb()
        items = self.project.assignments.get("sets.precast.FC")
        if not items:
            self.say(L("「詠唱の開始 (ファストキャスト)」のセットがまだ無いので、計算できません。ファストキャストを手で入れてください。",
                       "No precast (Fast Cast) set yet, so there's nothing to calculate. Enter your Fast Cast by hand."))
            return
        res_dir = self.project.resdb.res_dir if self.project.resdb is not None and self.project.resdb.available() else None
        total, rows, unknown = FCALC.set_fast_cast(res_dir, items)
        self.project.set_fast_cast(total)
        self.show_detail()      # sync the field (precast) and the 3-stage swap display (interruption)
        sep = L("・", ", ")
        detail = sep.join("%s %d" % (self.item_name(n), v) for _s, n, v in rows) or L("該当なし", "none")
        msg = L("ファストキャストのセットから %d%% と計算して入れました (%s)。",
                "Fast Cast from the set: %d%% (%s).") % (total, detail)
        if unknown:
            msg += L(" 値が分からない装備: %s (必要なら手で足してください)",
                     " Unknown values: %s (add them by hand if needed)") % sep.join(self.item_name(u) for u in unknown)
        if not res_dir:
            msg += L(" (res が見つからないので、オーグメントの値だけです)", " (res not found, so only augment values were counted)")
        self.say(msg)

    def on_fast_cast(self):
        if getattr(self, "_stage_loading", False):
            return
        self.project.set_fast_cast(self.fc_var.get())
        self.fc_advice.config(text=FCALC.advice(self.project.fast_cast, self.project.job))

    def ws_label(self, en):
        """Turn a WS's English name into "Japanese name (English name)" (English name alone without res, and in English mode)."""
        if i18n.is_en():
            return en
        for it in CH.choices(self.project.resdb, "ws", self.project.job):
            if it["en"] == en and it["ja"] != en:
                return "%s (%s)" % (it["ja"], en)
        return en

    def apply_ammo(self, e, items):
        """Assign the chosen ammo to its role. Special ammo then asks which WS to use it for. If several are chosen, the first one wins."""
        item = items[0]
        role = e["ammo_role"]
        name = self.item_name(item.name)
        if role != "special":
            self.project.set_ammo(role, item)
            self.refresh(select=e["path"])
            self.say(L("%s を、%s にしました。", "Set %s as %s.") % (name, e["title"]))
            return
        self.update_resdb()
        ws = CH.choices(self.project.resdb, "ws", self.project.job)
        if not ws:
            messagebox.showwarning(APP_NAME, L("WS の一覧を作れませんでした (Windower の res が見つかりません)。\n先に data フォルダーを選んでください。",
                                               "Couldn't build the weapon skill list (Windower's res wasn't found).\n"
                                               "Choose your data folder first."))
            return
        picker = NamePicker(self.root, L("%s を使う WS を選ぶ", "Choose weapon skills for %s") % name, ws,
                            note=L("選んだ WS の瞬間だけ %s を着て、終わったら物理の弾に戻します。",
                                   "%s is equipped only for the chosen weapon skills, then swaps back to your physical ammo.") % name)
        for w in picker.result:
            self.project.set_ws_ammo(w["en"], item)
        self.refresh(select=e["path"])
        if picker.result:
            self.say(L("%s を、%d 個の WS で使うようにしました。", "%s will be used for %d weapon skill(s).")
                     % (name, len(picker.result)))

    def clear_assignment(self):
        e = self.current()
        if e:
            self.project.clear(e["path"])
            self.refresh(select=e["path"])

    def remove_custom(self):
        e = self.current()
        if e and e["custom"]:
            self.project.remove_custom(e["path"])
            self.refresh()

    def say(self, text):
        self.status.config(text=text)

    # --- Output ---
    def preview(self):
        win = tk.Toplevel(self.root)
        win.title(L("出力する Lua の確認", "Preview Lua"))
        win.geometry("860x620")
        txt = tk.Text(win, wrap="none")
        txt.pack(fill="both", expand=True)
        self.update_resdb()     # so the WS type (where its set goes) can be looked up in res even right after "Open work"
        txt.insert("1.0", self.project.to_lua())
        txt.config(state="disabled")

    def make_lua(self):
        self.update_resdb()     # so the WS type (where its set goes) can be looked up in res even right after "Open work"
        if not self.project.has_work(self.project.job):
            messagebox.showinfo(APP_NAME, L("まだ、どのセットにも装備が割り当てられていません。", "No gear has been assigned to any set yet."))
            return
        d = self.data_dir.get().strip()
        if not d or not os.path.isdir(d):
            messagebox.showwarning(APP_NAME, L("GearSwap の data フォルダーを選んでください。", "Please choose your GearSwap data folder."))
            return
        if self.project.job == "PLD" and self.project.three_stage and not self.project.fast_cast:
            # With Fast Cast at 0, the spell finishes before the landing gear goes on (Cure gear never gets worn)
            if not messagebox.askyesno(APP_NAME, L("3 段階の着替えを使いますが、ファストキャストが 0% のままです。\n"
                                                   "このままだと、着弾の装備 (ケアルなど) に替える前に詠唱が終わってしまいます。\n\n"
                                                   "「詠唱の開始 (ファストキャスト)」の「装備から計算」で入れてから作るのがおすすめです。\n"
                                                   "このまま作りますか?",
                                                   "3-stage swap is on, but Fast Cast is still 0%.\n"
                                                   "Spells will finish before the landing gear (Cure etc.) goes on.\n\n"
                                                   "We recommend setting it with \"Calculate from gear\" in the precast (Fast Cast) set first.\n"
                                                   "Make the Lua anyway?")):
                return
        found = conflicts.find_conflicts(d, self.project.job)
        if found:
            lines = ["\n".join("・%s\n    %s" % (p, why) for p, why in found)]
            if not messagebox.askyesno(APP_NAME, L("次のファイルが、キットの出力を上書きするかもしれません。\n\n%s\n\n"
                                                   "このまま Lua を作りますか。",
                                                   "These files may override the kit's output:\n\n%s\n\n"
                                                   "Make the Lua anyway?") % lines[0], icon="warning"):
                return
        target = os.path.join(d, "%s.lua" % self.project.job)
        if os.path.exists(target) and not messagebox.askyesno(
                APP_NAME, L("%s はすでにあります。\n今のファイルは、同じ場所にバックアップを残してから、上書きします。\n続けますか。",
                            "%s already exists.\nA backup of the current file will be kept in the same folder before overwriting.\n"
                            "Continue?") % target):
            return
        G.MISSING_DATA.clear()
        try:
            path, backup = self.project.write_lua(d)
        except OSError as ex:
            messagebox.showerror(APP_NAME, L("書き込めませんでした。\n%s", "Couldn't write the file.\n%s") % ex)
            return
        msg = L("作りました。\n%s", "Done.\n%s") % path
        if backup:
            msg += L("\n\n元のファイルは、こちらに残しました。\n%s", "\n\nYour previous file was backed up here:\n%s") % backup
        msg += L("\n\nゲーム内で //lua r gearswap、またはジョブを変えて、読み込んでください。",
                 "\n\nIn game, run //lua r gearswap or change jobs to load it.")
        orphans = getattr(self.project, "orphans", [])
        if orphans:
            msg += (L("\n\n次のセットは、キットの一覧に無くなった項目なので、出力しませんでした (作業のファイルには残っています)。"
                      "\n使うなら、今の一覧の項目に割り当て直してください。\n・",
                      "\n\nThese sets are no longer in the kit's list, so they weren't written (they're still in your work file)."
                      "\nTo use them, reassign them to a set in the current list.\n・") + "\n・".join(orphans))
        if G.MISSING_DATA:
            # Without the data files, the per-move set mappings (pet moves, Blue Magic) are left out of the Lua: say so
            msg += (L("\n\n注意: キットのデータのファイルが読めなかったので、そのファイルを使う対応 (ペットの技・青魔法の分類) は、"
                      "出力に入っていません。キットを入れ直してください。\n・",
                      "\n\nWarning: some of the kit's data files couldn't be read, so the mappings that use them "
                      "(pet moves, Blue Magic types) are not in the file. Please reinstall the kit.\n・")
                    + "\n・".join(sorted(G.MISSING_DATA)))
            messagebox.showwarning(APP_NAME, msg)
        else:
            messagebox.showinfo(APP_NAME, msg)
        self.say(L("%s を作りました。", "Created %s.") % path)

    # --- Saving work ---
    def save_project(self):
        path = filedialog.asksaveasfilename(title=L("作業を保存", "Save work"), defaultextension=".json",
                                            filetypes=[("JSON", "*.json")],
                                            initialfile="%s_kit.json" % self.project.job)
        if path:
            try:
                atomic_write(path, self.project.to_json())
            except OSError as ex:
                messagebox.showerror(APP_NAME, L("保存できませんでした。\n%s", "Couldn't save.\n%s") % ex)
                return
            self.project_path = path
            self.remember_file("last_project", path)
            self.say(L("作業を保存しました。", "Work saved."))

    def open_project(self):
        path = filedialog.askopenfilename(title=L("作業を開く", "Open work"), filetypes=[("JSON", "*.json")])
        if path:
            self.load_project_file(path)

    def load_project_file(self, path, quiet=False):
        """Load a work file and show it. With quiet, read failures aren't reported (auto-open at launch). Returns whether it opened."""
        try:
            with open(path, encoding="utf-8") as f:
                self.project = Project.from_json(f.read())
        except Exception as ex:      # report instead of crashing even on JSON of a different shape (from another tool, or hand-edited)
            if not quiet:
                messagebox.showerror(APP_NAME, L("作業のファイルとして読めませんでした。\n%s", "Couldn't read this as a work file.\n%s") % ex)
            return False
        self.project_path = path
        self.remember_file("last_project", path)
        self.job_var.set(self.project.job)
        self.weapons_var.set(self.project.include_weapons)
        self.project.set_resdb(None)
        self.update_resdb()          # reattach res to the new work and match the action dropdown to the opened job
        self.show_lockstyle()
        self.update_recv_auto_box()
        self.refresh()
        self.say(L("作業を開きました。", "Work opened. ") + ("" if not quiet else L("(前回の作業: %s)", "(last session: %s)") % path))
        return True


def main():
    root = tk.Tk()
    # Window icon (in the EXE, icon.ico is bundled with --include-data-files and read from next to __file__ in the extraction folder)
    icon = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
    if os.path.exists(icon):
        try:
            root.iconbitmap(default=icon)  # default= also applies it to windows opened later (language picker, lists, etc.)
        except tk.TclError:
            pass
    settings = load_settings()
    code = settings.get("lang")
    if code not in i18n.LANGS:
        # First launch: ask for the language first, save it, then build the main window
        root.withdraw()
        code = ask_first_language(root)
        settings["lang"] = code
        save_settings(settings)
        root.deiconify()
    i18n.set_lang(code)
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
