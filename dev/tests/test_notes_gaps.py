"""BL-301 B gaps (v20-notes-gaps): pictures in notes, a renamed title renames the file, a Working session's date and attendees
edited after it is made. /api/notes/* on a live server over a throwaway vault.

Run: python3 dev/tests/test_notes_gaps.py

  - a picture is created through filechange.py in the notes folder's _images/ (logged, undoable; a taken name gets a number),
    only PNG or JPEG, 2 MB at most; an opened note carries its pictures for the editor;
  - after a save that changed the title, /api/notes/rename moves the file to the new name through filechange.py (a move, backed up
    and undoable, made with the route's own one-time approval), a taken name gets a number, and [[old]] links in other notes point
    at the new title through filechange.py; a note with unsaved typing is listed, never touched; nothing moves when the name fits;
  - a Working session note's date and attendees change with a save.
"""
import base64
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_notes_tab  # noqa: E402
from test_tracker import ABC  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


class NotesGaps(test_notes_tab.NotesServer):
    test_1_templates_make_notes_through_filechange = None          # part B's own tests run in their own file
    test_2_draft_then_save_once_and_undo = None
    test_3_changed_outside_is_never_overwritten = None
    test_4_list_portfolio_and_refusals = None
    test_5_dashboard_data_and_files = None
    test_6_saves_in_one_editing_session_keep_one_backup = None

    def new(self, title, **kw):
        r = self.post("/api/notes/new", {"code": "ABC", "template": kw.pop("template", "blank"), "title": title, **kw})
        self.assertTrue(r["ok"], r)
        return r

    def undo(self, n):
        return subprocess.run([sys.executable, str(self.v.root / "system/scripts/filechange.py"), "undo", str(n)],
                              cwd=self.v.root, capture_output=True, text=True)

    def test_a_picture_goes_in_images_through_filechange(self):
        r = self.new("With a picture")
        data = base64.b64encode(PNG).decode()
        a = self.post("/api/notes/image", {"path": r["note"]["path"], "name": "Org chart.png", "data": data})
        self.assertTrue(a["ok"], a)
        self.assertRegex(a["ref"], r"^_images/\d{4}-\d{2}-\d{2}-org-chart\.png$")
        b = self.post("/api/notes/image", {"path": r["note"]["path"], "name": "Org chart.png", "data": data})
        self.assertRegex(b["ref"], r"-org-chart-2\.png$", "a taken name gets a number")
        f = self.folder() / a["ref"]
        self.assertEqual(f.read_bytes(), PNG)
        made = [e for e in self.log() if e.get("op") == "create" and "/_images/" in e["path"]]
        self.assertEqual(len(made), 2)
        self.assertTrue(all(e["via"] == "dashboard" for e in made))
        self.assertEqual(self.post("/api/notes/image", {"path": r["note"]["path"], "name": "x.gif", "data": base64.b64encode(b"GIF89a").decode()})["status"], 415)
        big = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * (2 * 1024 * 1024)).decode()
        self.assertEqual(self.post("/api/notes/image", {"path": r["note"]["path"], "name": "big.png", "data": big})["status"], 413)
        self.assertEqual(self.post("/api/notes/image", {"path": f"{ABC}/CLAUDE.md", "data": data})["status"], 404)
        body = f"Before.\n\n![The org chart]({a['ref']})\n"
        s = self.post("/api/notes/save", {"path": r["note"]["path"], "body": body, "base": r["base"]})
        self.assertTrue(s["ok"], s)
        got = self.post("/api/notes/get", {"path": r["note"]["path"]})
        self.assertTrue(got["images"][a["ref"]].startswith("data:image/png;base64,"))
        self.assertEqual(self.undo(made[-1]["id"]).returncode, 0)
        self.assertFalse((self.folder() / b["ref"]).exists(), "a picture is undoable")

    def test_b_renamed_title_renames_the_file_and_its_links(self):
        r = self.new("Vendor positions")
        rel = r["note"]["path"]
        other = self.new("Pricing call")
        s0 = self.post("/api/notes/save", {"path": other["note"]["path"], "body": "See [[Vendor positions]] and [[vendor positions|their view]].\n",
                                           "base": other["base"]})
        self.assertTrue(s0["ok"], s0)
        typing = self.new("Half typed")
        self.post("/api/notes/save", {"path": typing["note"]["path"], "body": "Also [[Vendor positions]].\n", "base": typing["base"]})
        self.post("/api/notes/draft", {"path": typing["note"]["path"], "body": "Still typing", "base": "x"})
        self.new("Supplier positions")                                    # the new name is taken: the file gets a number
        s = self.post("/api/notes/save", {"path": rel, "changes": {"title": "Supplier positions"}, "base": r["base"]})
        self.assertTrue(s["ok"], s)
        same = self.post("/api/notes/rename", {"path": rel, "base": "stale", "old": "Vendor positions"})
        self.assertFalse(same["ok"], "a rename is checked against the saved text")
        m = self.post("/api/notes/rename", {"path": rel, "base": s["base"], "old": "Vendor positions"})
        self.assertTrue(m["ok"], m)
        self.assertTrue(m["renamed"])
        self.assertEqual(m["note"]["file"], "Supplier positions-2.md")
        self.assertFalse((self.v.root / rel).exists())
        self.assertTrue((self.v.root / m["note"]["path"]).is_file())
        moves = [e for e in self.log() if e.get("op") == "move"]
        self.assertEqual(len(moves), 1)
        self.assertEqual(moves[0]["via"], "dashboard")
        self.assertTrue(moves[0]["approved"], "made with the route's one-time approval")
        text = (self.v.root / other["note"]["path"]).read_text()
        self.assertIn("[[Supplier positions]] and [[Supplier positions|their view]]", text)
        self.assertEqual(m["relinked"], [other["note"]["path"]])
        self.assertEqual([x["path"] for x in m["listed"]], [typing["note"]["path"]])
        self.assertIn("[[Vendor positions]]", (self.v.root / typing["note"]["path"]).read_text(), "a note being typed is never touched")
        again = self.post("/api/notes/rename", {"path": m["note"]["path"], "base": m["base"], "old": "Supplier positions"})
        self.assertFalse(again["renamed"], "nothing moves when the name fits")
        relinks = [e for e in self.log() if e.get("op") == "edit" and e.get("why") == "a link to a note whose title changed"]
        self.assertEqual(len(relinks), 1)
        self.assertEqual(self.undo(moves[0]["id"]).returncode, 0, "the move is undoable")
        self.assertTrue((self.v.root / rel).is_file())

    def test_c_working_session_date_and_with_edited_later(self):
        r = self.new("Workshop", template="working-session", date="2026-10-13", **{"with": ["Omar Ali"]})
        s = self.post("/api/notes/save", {"path": r["note"]["path"], "changes": {"date": "2026-10-14", "with": ["Omar Ali", "Lena Park"]},
                                          "base": r["base"]})
        self.assertTrue(s["ok"], s)
        self.assertEqual(s["note"]["date"], "2026-10-14")
        self.assertEqual(s["note"]["with"], ["Omar Ali", "Lena Park"])
        bad = self.post("/api/notes/save", {"path": r["note"]["path"], "changes": {"date": "14-10-2026"}, "base": s["base"]})
        self.assertTrue(bad.get("unchanged"), "a date not stored YYYY-MM-DD is never written")


if __name__ == "__main__":
    unittest.main()
