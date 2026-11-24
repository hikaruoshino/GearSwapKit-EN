"""Exercise dummy song selection, compact layouts and save status with Tk widgets."""
import json
from pathlib import Path
import sys
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as A
from project import Project


SONGS = ["Army's Paeon", "Army's Paeon II", "Army's Paeon III", "Army's Paeon IV", "Mage's Ballad"]


class DummySongGUI(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)
        self.enterContext(patch.object(A, "SETTINGS", str(self.folder / "settings.json")))
        self.addCleanup(A.i18n.set_lang, A.i18n.lang())
        self.root = tk.Tk()
        self.addCleanup(self.root.destroy)
        self.gui = A.App(self.root)
        self.gui.project.set_job("BRD")

    def prepare_res(self):
        res = self.folder / "res"
        res.mkdir()
        (res / "jobs.lua").write_text('[10]={id=10,ens="BRD"},', encoding="utf-8")
        (res / "skills.lua").write_text('[40]={id=40,en="Singing",ja="歌唱"},', encoding="utf-8")
        rows = []
        for i, name in enumerate(SONGS + ["Foe Requiem", "Honor March", "Aria of Passion", "Cure"], 1):
            kind = "WhiteMagic" if name == "Cure" else "BardSong"
            targets = 32 if name == "Foe Requiem" else 1
            rows.append(f'[{i}]={{id={i},en="{name}",ja="テスト曲{i}",type="{kind}",skill=40,'
                        f'levels={{[10]={i}}},targets={targets}}},')
        (res / "spells.lua").write_text("\n".join(rows), encoding="utf-8")
        data = self.folder / "addons" / "GearSwap" / "data"
        data.mkdir(parents=True)
        self.gui.data_dir.set(str(data))

    def edit_songs(self, interact):
        def widgets(parent):
            for child in parent.winfo_children():
                yield child
                yield from widgets(child)

        def operate(win):
            self.root.update()
            controls = list(widgets(win))
            box = next(w for w in controls if isinstance(w, tk.Listbox))
            query = next(w for w in controls if isinstance(w, A.ttk.Entry) and not isinstance(w, A.ttk.Combobox))
            interact(box, query)
            apply = next(w for w in controls if isinstance(w, A.ttk.Button)
                         and w.cget("text") == A.L("選択を適用", "Apply selection"))
            apply.invoke()

        with patch.object(self.root, "wait_window", side_effect=operate) as dialog, \
                patch.object(A.messagebox, "showwarning", side_effect=AssertionError):
            self.gui.edit_dummy_songs()
            dialog.assert_called_once()

    def click_song(self, box, index):
        x, y, _, height = box.bbox(index)
        for event in ("<ButtonPress-1>", "<ButtonRelease-1>"):
            box.event_generate(event, x=x + 1, y=y + height // 2)

    def test_click_fifth_and_search_back(self):
        self.prepare_res()
        def choose(box, query):
            self.assertEqual(box.size(), 5)
            self.assertEqual(box.curselection(), (0, 1, 2, 3))
            self.click_song(box, 4)
            query.insert(0, "テスト曲5")
            self.assertEqual(box.curselection(), (0,))
            query.delete(0, "end")
            self.assertEqual(box.curselection(), (0, 1, 2, 3, 4))

        for lang in ("ja", "en"):
            with self.subTest(lang=lang):
                A.i18n.set_lang(lang)
                self.gui.project.set_dummy_songs(SONGS[:4])
                self.edit_songs(choose)
                self.assertEqual(self.gui.project.dummy_songs, SONGS)

    def test_button_at_700_with_all_jobs(self):
        self.root.geometry("700x600")
        for job in A.C.ALL_JOBS:
            self.gui.project.set_job(job)
            self.gui.project.set_lockstyle(1)
        self.gui.project.set_job("BRD")
        for lang in ("ja", "en"):
            with self.subTest(lang=lang):
                A.i18n.set_lang(lang)
                self.gui.refresh()
                self.root.update()
                btn = self.gui.dummy_button
                self.assertTrue(btn.winfo_ismapped())
                self.assertGreaterEqual(btn.winfo_width(), btn.winfo_reqwidth())
                self.assertLessEqual(btn.winfo_rootx() + btn.winfo_width(), self.root.winfo_rootx() + 700)

    def test_clear_shows_unsaved_until_saved(self):
        A.i18n.set_lang("ja")
        self.gui.project.set_dummy_songs(SONGS)
        self.gui.project_path = str(self.folder / "work.json")
        self.assertTrue(self.gui.save_current())
        self.prepare_res()
        self.edit_songs(lambda box, query: box.selection_clear(0, "end"))
        self.assertFalse(self.gui.project.has_changes("BRD"))
        self.assertTrue(self.gui.has_unsaved())
        self.assertIn("未保存", self.gui.status.cget("text"))
        self.assertNotIn("BRD", self.gui.jobs_lbl.cget("text"))
        with patch.object(A.messagebox, "askyesno", return_value=False) as confirm:
            self.gui.on_close()
            confirm.assert_called_once()
        self.assertTrue(self.gui.save_current())
        self.assertFalse(self.gui.has_unsaved())
        self.assertNotIn("未保存", self.gui.status.cget("text"))

    def test_new_project_back_to_empty_closes_without_saving(self):
        self.prepare_res()
        self.edit_songs(lambda box, query: self.click_song(box, 0))
        self.assertTrue(self.gui.has_unsaved())
        self.edit_songs(lambda box, query: self.click_song(box, 0))
        self.assertFalse(self.gui.project.has_changes("BRD"))
        self.assertFalse(self.gui.has_unsaved())
        with patch.object(self.root, "destroy") as close, patch.object(A, "atomic_write") as write, \
                patch.object(A.filedialog, "asksaveasfilename") as ask:
            self.gui.on_close()
            close.assert_called_once()
            write.assert_not_called()
            ask.assert_not_called()

    def test_unset_and_explicit_empty_round_trip(self):
        for names in (None, [], SONGS):
            with self.subTest(names=names):
                pr = Project.from_json(json.dumps({"job": "BRD", "dummy_songs": names}))
                self.assertFalse(pr.load_warnings)
                saved = json.loads(pr.to_json())["jobs"].get("BRD", {})
                self.assertEqual(saved.get("dummy_songs"), names)
                self.assertEqual(Project.from_json(pr.to_json()).to_json(), pr.to_json())

    def test_validate_names_before_saving(self):
        pr = self.gui.project
        pr.set_dummy_songs([" Army's Paeon ", SONGS[0], None, {}, "A\nB", "bad()", ""])
        self.assertEqual(pr.dummy_songs, SONGS[:1])
        self.assertEqual(len(pr.load_warnings), 5)
        for malformed in ("wrong", ["bad()"]):
            pr.set_dummy_songs(malformed)
            self.assertEqual(pr.dummy_songs, SONGS[:1])
        pr.set_dummy_songs(None)
        self.assertFalse(pr.has_changes("BRD"))


if __name__ == "__main__":
    unittest.main()
