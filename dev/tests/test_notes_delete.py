"""#124: Delete note (Alan, 15-10-2026): the confirm box in the Notes tab AND the one approval card for the move into _Archive.

Run: python3 dev/tests/test_notes_delete.py

What is covered, on a live server over a throwaway vault (and, for the shapes, a vault whose projects are in a fake OneDrive):
- POST /api/notes/delete puts exactly one change card up ("Delete note “…”", one "Move file … → …/_Archive/<notes folder>/…"
  line) and moves nothing; Reject moves nothing; Approve moves the note through tracker.py apply (a `move` of kind "notes");
- the route alone never moves anything: no card answered, a wrong card, a used card and an expired request all leave the note;
- after the move: the notes list, the search index, Mentioned in (the other notes' links, left as written: missing) drop it;
  Files › Archived lists it with Move back; undo (tracker.py undo, the toast's Undo) brings it back, and so does Move back
  (kind "notes_back"), never onto a note that is there;
- a name taken in _Archive gets -2; a stale save, typing not yet saved, a path that isn't a note and a bad request are refused;
- never while ask creaite has read outside content (the rename's rule); a confidential note deletes the same way;
- ask creaite can't do it: _Archive stays never for classify(), propose.py stages a "notes" move only from the server's own
  snapshot, a CHANGE card with one is refused;
- reach.archive_move_problem's "notes" and "notes_back" are exactly the one-note shape, in both layouts.
Everything is fictional and temporary.
"""
import json
import subprocess
import sys
import unittest
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_notes_tab  # noqa: E402
from test_onedrive_projects import OneDriveCase  # noqa: E402
from test_tracker import ABC  # noqa: E402


class NotesDelete(test_notes_tab.NotesServer):
    test_1_templates_make_notes_through_filechange = None          # part B's own tests run in their own file
    test_2_draft_then_save_once_and_undo = None
    test_3_changed_outside_is_never_overwritten = None
    test_4_list_portfolio_and_refusals = None
    test_5_dashboard_data_and_files = None

    def new(self, title, **kw):
        r = self.post("/api/notes/new", {"code": kw.pop("code", "ABC"), "template": kw.pop("template", "blank"), "title": title, **kw})
        self.assertTrue(r["ok"], r)
        return r

    def archive(self):
        return self.v.root / ABC / "_Archive" / "notes"

    def titles(self, code="ABC"):
        return [n["title"] for n in self.post("/api/notes/list", {"code": code})["notes"]]

    def files(self):
        req = urllib.request.Request(self.base + "/api/files", headers={"X-Creaite-Token": self.token})
        return json.loads(urllib.request.urlopen(req).read())

    def run_at(self, script, *args):
        return subprocess.run([sys.executable, str(self.v.root / "system/scripts" / script), *args], cwd=self.v.root,
                              capture_output=True, text=True)

    def indexed(self):
        r = subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts'); import tracker; "
                            "print(json.dumps([str(f) for f, _, _ in tracker.index_files()]))"],
                           cwd=self.v.root, capture_output=True, text=True)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def delete(self, r):
        return self.post("/api/notes/delete", {"path": r["note"]["path"], "base": r["base"]})

    def test_a_one_card_reject_moves_nothing_approve_moves_undo_restores(self):
        r = self.new("Working session")
        other = self.new("Points at it")
        f, o = self.folder() / "Working session.md", self.folder() / "Points at it.md"
        text = o.read_text().replace("\n\n", "\n\nSee [[Working session]] for the detail.\n\n", 1)
        o.write_text(text)
        d = self.delete(r)
        self.assertTrue(d["ok"], d)
        card = d["card"]
        self.assertEqual(card["title"], "Delete note “Working session” (move it to the archive)")
        self.assertEqual(card["lines"], [f"Move file {ABC}/notes/Working session.md → {ABC}/_Archive/notes/Working session.md"])
        self.assertTrue(card["valid"])
        self.assertEqual(self.post("/api/edit/pending", {})["card"]["card"], card["card"])            # exactly that one card
        self.assertTrue(f.is_file())                                                                   # nothing moved yet
        self.assertEqual(self.post("/api/edit/reject", {"card": card["card"]})["ok"], True)
        self.assertTrue(f.is_file())                                                                   # Reject: left where it is
        self.assertFalse(self.archive().exists())
        self.assertFalse(self.post("/api/edit/approve", {"card": card["card"]})["ok"])                # used once
        self.assertTrue(f.is_file())
        d = self.delete(r)
        done = self.post("/api/edit/approve", {"card": d["card"]["card"]})
        self.assertTrue(done["ok"], done)
        self.assertFalse(f.exists())
        self.assertTrue((self.archive() / "Working session.md").is_file())
        self.assertNotIn("Working session", self.titles())                                             # the list drops it
        self.assertIn("[[Working session]]", o.read_text())                                            # the link stays, missing
        backlinks = [n["title"] for n in self.post("/api/notes/list", {"code": "ABC"})["notes"] if "Working session" in n["links"]]
        self.assertEqual(backlinks, ["Points at it"])                         # Mentioned in: a link to a note that isn't listed
        self.assertFalse(any(x.endswith("Working session.md") for x in self.indexed()))               # not indexed
        stored = f"{ABC}/notes/Working session.md"
        self.assertIn(stored, [a["path"] for a in self.files()["archived"]])                           # Files › Archived
        self.assertEqual(self.post("/api/notes/get", {"path": stored})["status"], 404)                 # not a note any more
        u = self.post("/api/undo", {"apply_id": done["apply_id"]})                                    # the toast's Undo
        self.assertTrue(u["ok"], u)
        self.assertTrue(f.is_file())
        self.assertFalse((self.archive() / "Working session.md").exists())
        self.assertIn("Working session", self.titles())
        self.assertTrue(any(x.endswith("Working session.md") for x in self.indexed()))
        self.assertNotIn(stored, [a["path"] for a in self.files()["archived"]])
        self.assertEqual(other["ok"], True)

    def test_b_move_back_from_files_never_onto_a_note_that_is_there(self):
        r = self.new("Lessons")
        self.assertTrue(self.post("/api/edit/approve", {"card": self.delete(r)["card"]["card"]})["ok"])
        stored = f"{ABC}/notes/Lessons.md"
        back = self.post("/api/files/move-back", {"path": stored})
        self.assertTrue(back["ok"], back)
        card = self.post("/api/edit/pending", {})["card"]
        self.assertEqual(card["lines"], [f"Move file {ABC}/_Archive/notes/Lessons.md → {stored}"])
        self.assertTrue(self.post("/api/edit/approve", {"card": card["card"]})["ok"])
        self.assertTrue((self.folder() / "Lessons.md").is_file())
        self.assertIn("Lessons", self.titles())
        again = self.post("/api/notes/get", {"path": stored})                                       # deleted again
        self.assertTrue(self.post("/api/edit/approve", {"card": self.delete(again)["card"]["card"]})["ok"])
        self.new("Lessons")                                                                           # a new note takes the name
        got = self.post("/api/files/move-back", {"path": stored})
        self.assertFalse(got["ok"])
        self.assertIn("already in its place", got["message"])                                         # never overwritten

    def test_c_a_name_taken_in_the_archive_gets_a_number(self):
        for _ in range(2):
            r = self.new("Same name")
            self.assertTrue(self.post("/api/edit/approve", {"card": self.delete(r)["card"]["card"]})["ok"])
        self.assertTrue((self.archive() / "Same name.md").is_file())
        self.assertTrue((self.archive() / "Same name-2.md").is_file())
        archived = {a["path"] for a in self.files()["archived"]}
        self.assertIn(f"{ABC}/notes/Same name.md", archived)

    def test_d_refusals_and_no_move_without_the_card(self):
        r = self.new("Kept")
        f, path = self.folder() / "Kept.md", r["note"]["path"]
        self.assertEqual(self.post("/api/notes/delete", {"path": path, "base": r["base"], "to": "x"})["status"], 400)
        self.assertEqual(self.post("/api/notes/delete", {"path": 3})["status"], 400)
        self.assertEqual(self.post("/api/notes/delete", {"path": f"{ABC}/CLAUDE.md", "base": ""})["status"], 404)
        stale = self.post("/api/notes/delete", {"path": path, "base": "0" * 16})
        self.assertFalse(stale["ok"])
        self.assertIn("changed since it was saved", stale["message"])
        self.post("/api/notes/draft", {"path": path, "body": "typing", "base": r["base"]})
        typing = self.delete(r)
        self.assertFalse(typing["ok"])
        self.assertIn("typing not yet saved", typing["message"])
        for x in (self.v.root / "system/staging/drafts/notes").glob("*.json"):
            x.unlink()                                                        # the typing dropped: now it may go on the card
        d = self.delete(r)                                                                           # a card, never answered
        self.assertTrue(d["ok"])
        self.assertFalse(self.post("/api/edit/approve", {"card": "e-0000000000000000"})["ok"])       # a card that isn't there
        self.assertTrue(f.is_file())
        self.assertFalse(self.archive().joinpath("Kept.md").exists())
        self.post("/api/edit/reject", {"card": d["card"]["card"]})

    def test_e_never_while_ask_creaite_has_read_outside_content(self):
        r = self.new("Outside")
        run = self.v.root / "system/guard/run.json"
        run.parent.mkdir(parents=True, exist_ok=True)
        run.write_text(json.dumps({"run": "r-test", "mode": "chat", "marked": ["mail"]}))
        try:
            got = self.delete(r)
            self.assertFalse(got["ok"])
            self.assertTrue(got.get("wait"))
            self.assertIn("outside content", got["message"])
            self.assertIsNone(self.post("/api/edit/pending", {})["card"])
        finally:
            run.unlink()
        self.assertTrue((self.folder() / "Outside.md").is_file())

    def test_f_a_confidential_note_deletes_the_same_way(self):
        r = self.new("Private")
        s = self.post("/api/notes/save", {"path": r["note"]["path"], "body": "The numbat negotiation position.\n",
                                          "changes": {"confidential": True}, "base": r["base"]})
        self.assertTrue(s["ok"] and s["note"]["confidential"], s)
        d = self.post("/api/notes/delete", {"path": s["note"]["path"], "base": s["base"]})
        self.assertTrue(d["ok"], d)
        self.assertNotIn("numbat", json.dumps(d))                                                   # no text on the card
        self.assertTrue(self.post("/api/edit/approve", {"card": d["card"]["card"]})["ok"])
        self.assertTrue((self.archive() / "Private.md").is_file())

    def test_g_ask_creaite_cant_delete_a_note_this_way(self):
        r = self.new("Not from a chat")
        spec = self.py_json(f"import archive; print(json.dumps(archive.note_delete_spec({r['note']['path']!r})))")[0]
        self.assertEqual(spec["file_changes"]["archive"], "notes")
        f = self.v.root / "system/staging/drafts/del.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(spec))
        out = self.run_at("propose.py", "stage", str(f))
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("deleted from the Notes tab", out.stdout)
        card = self.py_json("import live_server as ls\n"
                            "class Run:\n    id, chat, session = 'r1', None, None\n    events = []\n"
                            "    def emit(self, kind, **k): self.events.append([kind, k])\n"
                            "r = Run(); ls.build_edit_card(r, 'Done.\\nCHANGE: system/staging/drafts/del.json | Delete it')\n"
                            "print(json.dumps(r.events))")
        self.assertIsNone(card[0][1]["card"])
        self.assertIn("never from ask creaite", card[0][1]["refused"])
        arch = self.archive() / "Not from a chat.md"
        kinds = self.py_json(f"import reach; print(json.dumps([reach.classify({str(arch)!r}, op)[0] for op in "
                             "('read', 'create', 'change', 'move', 'delete')]))")
        self.assertEqual(set(kinds), {"never"})
        self.assertTrue((self.folder() / "Not from a chat.md").is_file())

    def py_json(self, code):
        src = f"import sys, json; sys.path.insert(0, 'system/scripts')\n{code}"
        r = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True, cwd=self.v.root)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])


class NoteShapes(OneDriveCase):
    """reach.archive_move_problem's "notes" and "notes_back": one note, into (or back from) its own folder's _Archive."""

    def problems(self, cases, kind):
        return self.py("import reach; c = " + json.dumps(cases) + "\n"
                       f"print(json.dumps({{k: reach.archive_move_problem(x, y, {kind!r}) for k, (x, y) in c.items()}}))")

    def test_the_one_note_shape_in_onedrive(self):
        e = "projects/Example Programme"
        notes = self.root / "Example Programme" / "08 Notes"
        notes.mkdir(parents=True, exist_ok=True)
        for n in ("Note.md", "Plan.txt", ".hidden.md"):
            (notes / n).write_text("x")
        (notes / "_images").mkdir(exist_ok=True)
        (notes / "_images" / "a.png").write_bytes(b"\x89PNG")
        (self.root / "Example Programme" / "02 Meetings" / "Minutes" / "Note.md").write_text("x")
        (self.root / "_Portfolio" / "08 Notes").mkdir(parents=True, exist_ok=True)
        (self.root / "_Portfolio" / "08 Notes" / "Cross.md").write_text("x")
        ok = {"same name": (f"{e}/08 Notes/Note.md", f"{e}/_Archive/08 Notes/Note.md"),
              "numbered": (f"{e}/08 Notes/Note.md", f"{e}/_Archive/08 Notes/Note-2.md"),
              "the portfolio": ("projects/_portfolio/08 Notes/Cross.md", "projects/_portfolio/_Archive/08 Notes/Cross.md")}
        self.assertEqual(self.problems(ok, "notes"), {k: None for k in ok})
        bad = {"another engagement": (f"{e}/08 Notes/Note.md", "projects/Digital Enablement/_Archive/08 Notes/Note.md"),
               "another name": (f"{e}/08 Notes/Note.md", f"{e}/_Archive/08 Notes/Other.md"),
               "a zero number": (f"{e}/08 Notes/Note.md", f"{e}/_Archive/08 Notes/Note-02.md"),
               "not a number": (f"{e}/08 Notes/Note.md", f"{e}/_Archive/08 Notes/Note-x.md"),
               "another folder": (f"{e}/08 Notes/Note.md", f"{e}/_Archive/02 Meetings/Minutes/Note.md"),
               "minutes as a note": (f"{e}/02 Meetings/Minutes/Note.md", f"{e}/_Archive/02 Meetings/Minutes/Note.md"),
               "not Markdown": (f"{e}/08 Notes/Plan.txt", f"{e}/_Archive/08 Notes/Plan.txt"),
               "hidden": (f"{e}/08 Notes/.hidden.md", f"{e}/_Archive/08 Notes/.hidden.md"),
               "a picture": (f"{e}/08 Notes/_images/a.png", f"{e}/_Archive/08 Notes/_images/a.png"),
               "the folder": (f"{e}/08 Notes", f"{e}/_Archive/08 Notes"),
               "the projects root's _Archive": (f"{e}/08 Notes/Note.md", "projects/_Archive/Example Programme/08 Notes/Note.md"),
               "dot dot": (f"{e}/08 Notes/../08 Notes/Note.md", f"{e}/_Archive/08 Notes/Note.md")}
        for k, why in self.problems(bad, "notes").items():
            self.assertTrue(why, k)
        self.assertTrue(self.problems({"x": ok["same name"]}, "reports")["x"], "a note is never a report")
        (self.root / "Example Programme" / "_Archive" / "08 Notes").mkdir(parents=True)
        (self.root / "Example Programme" / "_Archive" / "08 Notes" / "Gone.md").write_text("x")
        back = {"back": (f"{e}/_Archive/08 Notes/Gone.md", f"{e}/08 Notes/Gone.md")}
        self.assertEqual(self.problems(back, "notes_back"), {"back": None})
        wrong = {"elsewhere": (f"{e}/_Archive/08 Notes/Gone.md", f"{e}/02 Meetings/Minutes/Gone.md"),
                 "the other way": (f"{e}/08 Notes/Note.md", f"{e}/_Archive/08 Notes/Note.md")}
        for k, why in self.problems(wrong, "notes_back").items():
            self.assertTrue(why, k)

    def test_the_spec_in_onedrive(self):
        notes = self.root / "Example Programme" / "08 Notes"
        notes.mkdir(parents=True, exist_ok=True)
        (notes / "Stakeholders.md").write_text("---\ntitle: Stakeholders\nconfidential: true\n---\n\nThe secret body.\n")
        spec, why = self.py("import archive; print(json.dumps(archive.note_delete_spec('projects/Example Programme/08 Notes/Stakeholders.md')))")
        self.assertIsNone(why)
        self.assertEqual(spec["file_changes"]["file_ops"], [{"op": "move", "from": "projects/Example Programme/08 Notes/Stakeholders.md",
                                                             "to": "projects/Example Programme/_Archive/08 Notes/Stakeholders.md"}])
        self.assertEqual(spec["file_changes"]["project"], "ABC")
        self.assertNotIn("secret", json.dumps(spec))                       # only the title is read, for the card
        self.assertEqual(self.py("import archive; print(json.dumps(archive.note_delete_spec('projects/Example Programme/CLAUDE.md')))")[1],
                         "that isn't a note that is there")


if __name__ == "__main__":
    unittest.main()
