"""#124: Delete note (Alan, 15-10-2026): the confirm box in the Notes tab moves the note into the archive folder (paths.ARCHIVE:
99 Archive today, 99 Archive after #252); #255 (Alan, 20-10-2026): with no approval card, the click is the approval
(dev/tests/test_delete_note_no_card.py has the route's own guards).

Run: python3 dev/tests/test_notes_delete.py

What is covered, on a live server over a throwaway vault (and, for the shapes, a vault whose projects are in a fake OneDrive):
- POST /api/notes/delete/now (the page's own call) moves the note through tracker.py apply (a `move` of kind "notes") with no
  card; #124's card route has gone;
- after the move: the notes list, the search index, Mentioned in (the other notes' links, left as written: missing) drop it;
  Files › Archived lists it with Move back; undo (tracker.py undo, the toast's Undo) brings it back, and so does Move back
  (kind "notes_back"), never onto a note that is there;
- a name taken in the archive folder gets -2; a stale save, typing not yet saved, a path that isn't a note and a bad request are refused;
- never while ask creaite has read outside content (the rename's rule); a confidential note deletes the same way;
- ask creaite can't do it: the archive folder stays never for classify(), propose.py stages a "notes" move only from the server's own
  snapshot, a CHANGE card with one is refused;
- reach.archive_move_problem's "notes" and "notes_back" are exactly the one-note shape, in both layouts.
- a name taken between the check and the move is never overwritten (os.link, never os.rename over a file), and Undo or an
  apply that moves a note waits for NOTES_LOCK (LOCK first), as a note's card does: tracker.py never starts while it is held;
- a one-file move never follows a symlink (a note, an archived note or one swapped in at the last moment), a failed unlink
  leaves one name, and an unreadable proposal or apply record counts as a note move (the lock is taken).
Everything is fictional and temporary.
"""
import json
import os
import subprocess
import re
import sys
import time
import unittest
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_notes_tab  # noqa: E402
from test_onedrive_projects import OneDriveCase  # noqa: E402
from test_tracker import ABC  # noqa: E402

# The archive folder's name, as paths.py has it (99 Archive today, 99 Archive after #252), read without importing paths here.
ARCHIVE = re.search(r'^ARCHIVE = "([^"]+)"', (Path(__file__).resolve().parent.parent.parent / "system/scripts/paths.py")
                    .read_text(encoding="utf-8"), re.M).group(1)

os.environ.setdefault("CREAITE_NO_LAUNCH", "1")          # /api/open answers the path, never starts an app


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
        return self.v.root / ABC / ARCHIVE / "notes"

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

    def page(self, path, body):
        """#255: the open page's own call. A "busy" answer (another job, e.g. the daily backup, holds the lock: nothing moved)
        is asked again for up to a minute; every other answer is returned as is."""
        for _ in range(120):
            got = self.page_once(path, body)
            if not (isinstance(got, dict) and got.get("busy") is True):
                return got
            time.sleep(0.5)
        return got

    def page_once(self, path, body):
        """One call: its token and Chrome's same-origin marks."""
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token,
                                              "Origin": self.base, "Sec-Fetch-Site": "same-origin"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return {"status": e.code, **json.loads(e.read().decode())}

    def delete(self, r):
        """#255: Delete note from the page: moved at once, no card."""
        return self.page("/api/notes/delete/now", {"path": r["note"]["path"], "base": r["base"]})

    def move_back(self, path):
        """#255: a deleted note's Move back from the page: at once, no card."""
        return self.page("/api/files/move-back/now", {"path": path})

    def test_a_delete_moves_at_once_undo_restores(self):
        r = self.new("Working session")
        other = self.new("Points at it")
        f, o = self.folder() / "Working session.md", self.folder() / "Points at it.md"
        text = o.read_text().replace("\n\n", "\n\nSee [[Working session]] for the detail.\n\n", 1)
        o.write_text(text)
        done = self.delete(r)                                                                          # #255: no card
        self.assertTrue(done["ok"], done)
        self.assertIsNone(self.post("/api/edit/pending", {})["card"])
        self.assertEqual(done["message"], "Moved “Working session” to the archive.")                # L4: the note named
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
        self.assertEqual(u["moves"], [])                                                               # L3: back as it was
        self.assertTrue(f.is_file())
        self.assertFalse((self.archive() / "Working session.md").exists())
        self.assertIn("Working session", self.titles())
        self.assertTrue(any(x.endswith("Working session.md") for x in self.indexed()))
        self.assertNotIn(stored, [a["path"] for a in self.files()["archived"]])
        self.assertEqual(other["ok"], True)

    def test_b_move_back_from_files_never_onto_a_note_that_is_there(self):
        r = self.new("Lessons")
        self.assertTrue(self.delete(r)["ok"])
        stored = f"{ABC}/notes/Lessons.md"
        self.assertFalse(self.post("/api/files/move-back", {"path": stored})["ok"])                 # #255: never the card
        self.assertIsNone(self.post("/api/edit/pending", {})["card"])
        back = self.move_back(stored)
        self.assertTrue(back["ok"], back)
        self.assertEqual(back["to"], stored)
        self.assertTrue((self.folder() / "Lessons.md").is_file())
        self.assertIn("Lessons", self.titles())
        again = self.post("/api/notes/get", {"path": stored})                                       # deleted again
        self.assertTrue(self.delete(again)["ok"])
        self.new("Lessons")                                                                           # a new note takes the name
        new = (self.folder() / "Lessons.md").read_text()
        at = next(a["at"] for a in self.files()["archived"] if a["path"] == stored)
        done = self.move_back(at)                                                 # Jarvis 16-10: back as Lessons-2, never over it
        self.assertTrue(done["ok"], done)
        self.assertEqual(done["to"], f"{ABC}/notes/Lessons-2.md")
        self.assertEqual(done["message"], "Moved “Lessons” back to its notes folder as “Lessons-2” (a note has its old name).")
        self.assertEqual((self.folder() / "Lessons.md").read_text(), new)                             # the new note untouched
        self.assertTrue((self.folder() / "Lessons-2.md").is_file())

    def test_c_a_name_taken_in_the_archive_gets_a_number(self):
        for _ in range(2):
            r = self.new("Same name")
            self.assertTrue(self.delete(r)["ok"])
        self.assertTrue((self.archive() / "Same name.md").is_file())
        self.assertTrue((self.archive() / "Same name-2.md").is_file())
        archived = {a["path"] for a in self.files()["archived"]}
        self.assertIn(f"{ABC}/notes/Same name.md", archived)

    def test_d_refusals_and_no_move_but_the_page_s_own(self):
        r = self.new("Kept")
        f, path = self.folder() / "Kept.md", r["note"]["path"]
        self.assertEqual(self.page("/api/notes/delete/now", {"path": path, "base": r["base"], "to": "x"})["status"], 400)
        self.assertEqual(self.page("/api/notes/delete/now", {"path": 3})["status"], 400)
        self.assertEqual(self.page("/api/notes/delete/now", {"path": f"{ABC}/CLAUDE.md", "base": ""})["status"], 404)
        stale = self.page("/api/notes/delete/now", {"path": path, "base": "0" * 16})
        self.assertFalse(stale["ok"])
        self.assertIn("changed since you opened it", stale["message"])
        self.assertEqual(self.post("/api/notes/delete/now", {"path": path, "base": r["base"]})["status"], 403)   # not the page's
        self.assertEqual(self.post("/api/notes/delete", {"path": path, "base": r["base"]})["status"], 404)       # #124's card: gone
        self.assertTrue(f.is_file())
        self.assertFalse(self.archive().joinpath("Kept.md").exists())
        self.assertIsNone(self.post("/api/edit/pending", {})["card"])

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
        d = self.page("/api/notes/delete/now", {"path": s["note"]["path"], "base": s["base"]})
        self.assertTrue(d["ok"], d)
        self.assertNotIn("numbat", json.dumps(d))                                                   # no text in the answer
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

    # ── M1: Delete note moves only the version the box was opened on ──
    def test_h_typing_after_the_box_opened_refuses_and_keeps_the_text(self):
        r = self.new("Still typing")
        f, path = self.folder() / "Still typing.md", r["note"]["path"]
        s = self.post("/api/notes/save", {"path": path, "body": "Typed after the confirm box.\n", "base": r["base"]})   # an autosave
        self.assertTrue(s["ok"], s)
        got = self.delete(r)                                                                          # the version first shown
        self.assertFalse(got["ok"])
        self.assertTrue(got["stale"])
        self.assertEqual(got["message"], "Not deleted: the note changed since you opened it. Open it again and try once more.")
        self.assertIn("Typed after the confirm box.", f.read_text())                                  # kept, unmoved
        self.assertFalse((self.archive() / "Still typing.md").exists())
        done = self.page("/api/notes/delete/now", {"path": path, "base": s["base"]})                  # the new version
        self.assertTrue(done["ok"], done)
        self.assertIn("Typed after the confirm box.", (self.archive() / "Still typing.md").read_text())   # the version confirmed

    def test_i_a_save_from_another_window_refuses_the_delete(self):
        r = self.new("Two windows")
        f, path = self.folder() / "Two windows.md", r["note"]["path"]
        other = self.post("/api/notes/get", {"path": path})                                           # window 2 has it open
        s = self.post("/api/notes/save", {"path": path, "body": "Window two's typing.\n", "base": other["base"]})    # #119: window 2 saves as it types
        self.assertTrue(s["ok"], s)
        got = self.delete(r)                                                                          # window 1's box, opened before
        self.assertFalse(got["ok"])
        self.assertIn("changed since you opened it", got["message"])
        self.assertTrue(f.is_file())
        self.assertIn("Window two's typing.", f.read_text())                                          # nothing lost
        done = self.page("/api/notes/delete/now", {"path": path, "base": s["base"]})
        self.assertTrue(done["ok"], done)
        self.assertEqual(self.post("/api/notes/save", {"path": path, "body": "x", "base": s["base"]})["status"], 404)   # a window that missed it

    def test_j_apply_waits_for_notes_lock_and_lock_order(self):
        r = self.new("Raced")
        rel = r["note"]["path"]
        got = self.py_json(
            "import threading, time, live_server as ls, notes\n"
            f"c = {{'valid': True, '_note': {{'path': {rel!r}, 'sha': '0' * 16}}, 'state': 'pending', 'id': 'e-x'}}\n"
            "out = {}\n"
            "ls.NOTES_LOCK.acquire()\n"
            "t = threading.Thread(target=lambda: out.update(ls.note_card_apply(c))); t.start(); time.sleep(0.4)\n"
            "waited = t.is_alive() and not out\n"
            "ls.NOTES_LOCK.release(); t.join(10)\n"
            "print(json.dumps([waited, out, c['state']]))")
        self.assertTrue(got[0])                                                          # held off while a save holds the lock
        self.assertTrue(got[1]["stale"])
        self.assertEqual(got[2], "pending")
        lines = (HERE.parents[1] / "system/scripts/live_server.py").read_text().splitlines()
        held = 0
        for i, ln in enumerate(lines):                                                  # LOCK, then NOTES_LOCK: never the reverse
            if ln.strip() != "with NOTES_LOCK:":
                continue
            held += 1
            ind = len(ln) - len(ln.lstrip())
            for x in lines[i + 1:]:
                if x.strip() and len(x) - len(x.lstrip()) <= ind:
                    break
                self.assertFalse("with LOCK" in x or "LOCK.acquire" in x or "VIP_WRITE" in x, x)
        self.assertGreaterEqual(held, 6)

    # ── M2: two deleted notes of one name ──
    def test_k_two_deletes_of_one_name_move_back_and_open_the_right_one(self):
        for word in ("first", "second"):
            r = self.new("Twice")
            s = self.post("/api/notes/save", {"path": r["note"]["path"], "body": f"The {word} one.\n", "base": r["base"]})
            self.assertTrue(self.page("/api/notes/delete/now", {"path": s["note"]["path"], "base": s["base"]})["ok"])
        rows = [a for a in self.files()["archived"] if a["path"] == f"{ABC}/notes/Twice.md"]
        self.assertEqual(sorted(a["at"] for a in rows), [f"{ABC}/{ARCHIVE}/notes/Twice-2.md", f"{ABC}/{ARCHIVE}/notes/Twice.md"])
        second = next(a["at"] for a in rows if a["at"].endswith("Twice-2.md"))
        opened = self.post("/api/open", {"path": second})                                          # Open: that file, read in place
        self.assertTrue(opened["ok"], opened)
        self.assertIn("The second one.", Path(opened["path"]).read_text())
        back = self.move_back(second)
        self.assertTrue(back["ok"], back)
        self.assertEqual(back["to"], f"{ABC}/notes/Twice.md")
        self.assertIn("The second one.", (self.folder() / "Twice.md").read_text())                 # the row's own note
        self.assertIn("The first one.", (self.archive() / "Twice.md").read_text())                 # the other stays archived
        first = [a for a in self.files()["archived"] if a["path"] == f"{ABC}/notes/Twice.md"]
        self.assertEqual([a["at"] for a in first], [f"{ABC}/{ARCHIVE}/notes/Twice.md"])

    # ── L2, #255: no card and nothing for Review: the move is applied at once, and only it ──
    def test_l_nothing_waits_in_review_or_on_a_card(self):
        r = self.new("No staging")
        d = self.delete(r)
        self.assertTrue(d["ok"], d)
        self.assertIsNone(self.post("/api/edit/pending", {})["card"])
        self.assertEqual(list(self.v.root.joinpath("system/staging").glob("proposed-*.json")), [])
        self.assertFalse((self.folder() / "No staging.md").exists())
        other = self.py_json("import live_server as ls; print(json.dumps(ls.edit_public({'id': 'e', 'run': None, 'chat': None, "
                             "'title': 't', 'state': 'pending', 'valid': True, 'clash': [], 'lines': [], 'problems': [], "
                             "'expires': 0, 'kind': 'reports_back'})['stage']))")
        self.assertTrue(other)                                                                      # other kinds unchanged

    # ── L3: Undo says what it did ──
    def test_m_undo_after_a_note_took_the_name(self):
        r = self.new("Taken back")
        done = self.delete(r)
        self.new("Taken back")
        u = self.post("/api/undo", {"apply_id": done["apply_id"]})
        self.assertTrue(u["ok"], u)
        self.assertEqual(u["moves"], [f"restored {ABC}/notes/Taken back.md as Taken back-2.md: a note took its name"])
        self.assertTrue((self.folder() / "Taken back-2.md").is_file())
        self.assertFalse((self.archive() / "Taken back.md").exists())
        report = self.py_json("import reach, tracker\nreach.NOTES_BACK_RENAMES = False\n"
                              f"import pathlib; d = pathlib.Path({str(self.archive())!r}); d.mkdir(parents=True, exist_ok=True)\n"
                              "(d / 'Taken back.md').write_text('x')\nout = []\n"
                              f"tracker._reverse_move({{'from': '{ABC}/notes/Taken back.md', 'to': '{ABC}/{ARCHIVE}/notes/Taken back.md', "
                              "'kind': 'notes'}, out)\nprint(json.dumps(out))")
        self.assertEqual(report, [f"skipped moving {ABC}/{ARCHIVE}/notes/Taken back.md back: {ABC}/notes/Taken back.md is there again"])

    def test_n_move_back_renames_switch_off_refuses(self):
        r = self.new("Switch")
        self.assertTrue(self.delete(r)["ok"])
        self.new("Switch")
        got = self.py_json(
            "import reach, archive, tracker\nreach.NOTES_BACK_RENAMES = False\n"
            f"spec, why = archive.back_spec('{ABC}/{ARCHIVE}/notes/Switch.md')\n"
            f"shape = reach.archive_move_problem('{ABC}/{ARCHIVE}/notes/Switch.md', '{ABC}/notes/Switch-2.md', 'notes_back')\n"
            "try:\n"
            f"    tracker.check_move({{'from': '{ABC}/{ARCHIVE}/notes/Switch.md', 'to': '{ABC}/notes/Switch-2.md'}}, {{'archive': 'notes_back'}}); chk = None\n"
            "except tracker.Invalid as e:\n    chk = str(e)\n"
            "reach.NOTES_BACK_RENAMES = True\n"
            f"on = reach.archive_move_problem('{ABC}/{ARCHIVE}/notes/Switch.md', '{ABC}/notes/Switch-2.md', 'notes_back')\n"
            "try:\n"
            f"    tracker.check_move({{'from': '{ABC}/{ARCHIVE}/notes/Switch.md', 'to': '{ABC}/notes/Switch-3.md'}}, {{'archive': 'notes_back'}}); ok = None\n"
            "except tracker.Invalid as e:\n    ok = str(e)\n"
            "try:\n"
            f"    tracker.check_move({{'from': '{ABC}/{ARCHIVE}/notes/Switch.md', 'to': '{ABC}/notes/Other.md'}}, {{'archive': 'notes_back'}}); other = None\n"
            "except tracker.Invalid as e:\n    other = str(e)\n"
            "print(json.dumps([spec, why, shape, chk, on, ok, other]))")
        spec, why, shape, chk, on, ok, other = got
        self.assertIsNone(spec)
        self.assertIn("already in its place", why)                                      # False: refused, as before
        self.assertTrue(shape)
        self.assertTrue(chk)
        self.assertIsNone(on)                                                            # True: the -2 shape passes
        self.assertIsNone(ok)                                                            # only the free-name suffix differs
        self.assertTrue(other)                                                           # never another name

    # ── Jarvis 16-10: a name taken between the check and the move is never overwritten (os.rename would replace it) ──
    def test_o_a_name_taken_at_the_last_moment_is_never_overwritten(self):
        got = self.py_json(
            "import errno, os, pathlib, reach, tracker, paths\n"
            f"note, arc = pathlib.Path({str(self.folder())!r}), pathlib.Path({str(self.archive())!r})\n"
            "arc.mkdir(parents=True, exist_ok=True)\n"
            "tracker.card_move_problem = lambda *a: None       # the mover past the card's marker (#124 F3, tested on its own)\n"
            "real = tracker._move\n"
            "def racing(a, b, kind):\n"
            "    if not racing.done:\n"
            "        racing.done = True\n"
            "        b.write_text('the new note')          # a new note takes the name after the check\n"
            "    return real(a, b, kind)\n"
            "def undo(name):\n"
            "    (arc / name).write_text('the archived one'); racing.done = False; out = []\n"
            f"    tracker._reverse_move({{'from': '{ABC}/notes/' + name, 'to': '{ABC}/{ARCHIVE}/notes/' + name, 'kind': 'notes'}}, out)\n"
            "    return out\n"
            "tracker._move = racing\n"
            "on = undo('Late.md')\n"
            "on_files = [(note / 'Late.md').read_text(), (note / 'Late-2.md').read_text(), (arc / 'Late.md').exists()]\n"
            "reach.NOTES_BACK_RENAMES = False\n"
            "off = undo('Later.md')\n"
            "off_files = [(note / 'Later.md').read_text(), (arc / 'Later.md').read_text()]\n"
            "reach.NOTES_BACK_RENAMES = True\n"
            "(note / 'Apply.md').write_text('the note to delete'); racing.done = False\n"
            "try:\n"
            f"    tracker._op_move(1, {{'from': '{ABC}/notes/Apply.md', 'to': '{ABC}/{ARCHIVE}/notes/Apply.md'}}, {{'archive': 'notes'}}, [])\n"
            "    applied = None\n"
            "except tracker.Invalid as e:\n"
            "    applied = str(e)\n"
            "apply_files = [(note / 'Apply.md').read_text(), (arc / 'Apply.md').read_text()]\n"
            "tracker._move = real\n"
            "def no_links(a, b):\n"
            "    raise OSError(errno.ENOTSUP, 'no hard links here')\n"
            "os.link = no_links                                # the fallback: the check, then os.rename\n"
            "(arc / 'Fall.md').write_text('archived'); (note / 'Fall.md').write_text('there')\n"
            "try:\n"
            "    real(arc / 'Fall.md', note / 'Fall.md', 'notes'); fall = None\n"
            "except FileExistsError:\n"
            "    fall = 'refused'\n"
            "fall_files = [(note / 'Fall.md').read_text(), (arc / 'Fall.md').read_text()]\n"
            "real(arc / 'Fall.md', note / 'Fall-2.md', 'reports')\n"
            "print(json.dumps([on, on_files, off, off_files, applied, apply_files, fall, fall_files, (note / 'Fall-2.md').read_text()]))")
        on, on_files, off, off_files, applied, apply_files, fall, fall_files, moved = got
        self.assertEqual(on, [f"restored {ABC}/notes/Late.md as Late-2.md: a note took its name"])
        self.assertEqual(on_files, ["the new note", "the archived one", False])                        # the next free name
        self.assertEqual(off, [f"skipped moving {ABC}/{ARCHIVE}/notes/Later.md back: {ABC}/notes/Later.md is there again"])
        self.assertEqual(off_files, ["the new note", "the archived one"])                              # both as they were
        self.assertIn("already exists", applied)                                                        # the apply rolls back
        self.assertEqual(apply_files, ["the note to delete", "the new note"])
        self.assertEqual(fall, "refused")
        self.assertEqual(fall_files, ["there", "archived"])
        self.assertEqual(moved, "archived")

    # ── Team Cap's review F2: the wait is proven, never timing: tracker.py undo or apply never starts while a save holds the lock ──
    def test_p_undo_and_apply_wait_for_notes_lock(self):
        r = self.new("Undo raced")
        self.assertTrue(self.delete(r)["ok"])
        staged = self.v.root / "system/staging/proposed-2026-10-16-hand.json"
        got = self.py_json(
            "import pathlib, threading, time, live_server as ls\n"
            f"note, arc = pathlib.Path({str(self.folder() / 'Undo raced.md')!r}), pathlib.Path({str(self.archive() / 'Undo raced.md')!r})\n"
            "calls, held, real_run = [], [False], ls.run\n"
            "def run(script, *args):\n"
            "    calls.append([script, args[0] if args else '', held[0]])     # recorded as it starts, before the subprocess\n"
            "    return real_run(script, *args)\n"
            "ls.run = run\n"
            "class F:\n"
            "    def __init__(self): self.out = {}\n"
            "    def send(self, code, body): self.out.update(body)\n"
            "def raced(route, work, ready):\n"
            "    f = F(); held[0] = True; ls.NOTES_LOCK.acquire()\n"
            "    t = threading.Thread(target=lambda: route(f, {}), daemon=True); t.start()\n"
            "    end = time.time() + 20\n"
            "    while not ready() and time.time() < end: time.sleep(0.02)\n"
            "    time.sleep(1.5)                               # long past the moment an unlocked route would have started its work\n"
            "    during = {'ready': ready(), 'started': [c for c in calls if c[0] == 'tracker.py' and c[1] == work and c[2]],\n"
            "              'out': dict(f.out), 'note': note.exists(), 'arc': arc.exists(), 'alive': t.is_alive()}\n"
            "    held[0] = False; ls.NOTES_LOCK.release(); t.join(60)\n"
            "    return during, f.out\n"
            "before = ls.undo_note_move()\n"
            "u_during, u_out = raced(ls.Handler.undo, 'undo', lambda: any(c[1] == 'read' and c[2] for c in calls))\n"
            "after = [note.exists(), arc.exists()]\n"
            "quiet = ls.staged_note_move()\n"
            f"p = pathlib.Path({str(staged)!r})\n"
            "p.write_text(json.dumps({'items': [], 'files': [{'archive': 'notes_back', 'file_ops': []}]}))\n"
            "hand = ls.staged_note_move()\n"
            "a_during, a_out = raced(ls.Handler.apply, 'apply', lambda: True)\n"
            "a_ran = any(c[1] == 'apply' and not c[2] for c in calls)\n"
            "p.unlink(missing_ok=True)\n"
            "print(json.dumps([before, u_during, u_out.get('ok'), after, quiet, hand, a_during, a_ran]))")
        before, u_during, ok, after, quiet, hand, a_during, a_ran = got
        self.assertTrue(before)                                    # the latest apply moved a note: Undo takes NOTES_LOCK
        self.assertTrue(u_during["ready"])                         # Undo got as far as its own check (LOCK held, the applies read)
        self.assertEqual(u_during["started"], [])                  # but tracker.py undo never started while the lock was held
        self.assertEqual(u_during["out"], {})
        self.assertTrue(u_during["alive"])
        self.assertEqual([u_during["note"], u_during["arc"]], [False, True])     # the note still archived, nothing restored
        self.assertTrue(ok)                                        # released: Undo completes
        self.assertEqual(after, [True, False])                     # and the note is back
        self.assertFalse(quiet)                                    # nothing staged moves a note: no NOTES_LOCK
        self.assertTrue(hand)                                      # a hand-staged notes_back move: the apply takes NOTES_LOCK (tracker.py then refuses the move: no card marker, #124 F3)
        self.assertEqual(a_during["started"], [])                  # tracker.py apply never started while the lock was held
        self.assertEqual(a_during["out"], {})
        self.assertTrue(a_during["alive"])
        self.assertTrue(a_ran)                                     # released: the apply ran

    # ── Team Cap's review F1: a one-file move never follows a symlink, in the apply or in Undo ──
    def test_q_a_symlinked_note_is_never_followed(self):
        other = self.new("Other note")
        got = self.py_json(
            "import os, pathlib, tracker\n"
            f"note, arc, root = pathlib.Path({str(self.folder())!r}), pathlib.Path({str(self.archive())!r}), pathlib.Path({str(self.v.root)!r})\n"
            "arc.mkdir(parents=True, exist_ok=True)\n"
            "outside = root / 'outside.txt'; outside.write_text('not a note')\n"
            "inner = note / 'Other note.md'\n"
            "tracker.card_move_problem = lambda *a: None       # the mover past the card's marker (#124 F3, tested on its own)\n"
            "def st(): return [os.stat(outside).st_nlink, os.stat(inner).st_nlink, outside.read_text()]\n"
            f"def fop(name, back=False):\n"
            f"    n, a = '{ABC}/notes/' + name, '{ABC}/{ARCHIVE}/notes/' + name\n"
            "    return ({'from': a, 'to': n}, {'archive': 'notes_back'}) if back else ({'from': n, 'to': a}, {'archive': 'notes'})\n"
            "def refused(call):\n"
            "    try:\n"
            "        call(); return None\n"
            "    except tracker.Invalid as e:\n"
            "        return str(e)\n"
            "out = {}\n"
            "for name, target in (('Link out.md', outside), ('Link note.md', inner)):\n"
            "    os.symlink(target, note / name)\n"
            "    out[name] = [refused(lambda: tracker.check_move(*fop(name))),               # the apply's check\n"
            "                 refused(lambda: tracker._op_move(1, *fop(name), [])),           # and the mover, past the check\n"
            "                 os.path.islink(note / name), os.path.lexists(arc / name)]\n"
            "real_link = os.link\n"
            "def swap(src, dst, **kw):                     # a symlink swapped in between the check and the link\n"
            "    os.unlink(src); os.symlink(outside, src)\n"
            "    return real_link(src, dst, **kw)\n"
            "(note / 'Swap.md').write_text('mine'); os.link = swap\n"
            "out['swap'] = [refused(lambda: tracker._op_move(1, *fop('Swap.md'), [])), os.path.islink(note / 'Swap.md'),\n"
            "               os.path.lexists(arc / 'Swap.md')]\n"
            "os.supports_follow_symlinks = set()\n"
            "if os.path.lexists(note / 'Swap.md'): os.unlink(note / 'Swap.md')\n"
            "(note / 'Swap.md').write_text('mine')\n"
            "out['swap_no_flag'] = [refused(lambda: tracker._op_move(1, *fop('Swap.md'), [])), os.path.islink(note / 'Swap.md'),\n"
            "                       os.path.lexists(arc / 'Swap.md')]\n"
            "os.link = real_link\n"
            "os.symlink(note / 'Nowhere.md', arc / 'Dangling.md'); (note / 'Dangling.md').write_text('to delete')\n"
            "out['dest'] = [refused(lambda: tracker._op_move(1, *fop('Dangling.md'), [])), (note / 'Dangling.md').read_text(),\n"
            "               os.path.lexists(note / 'Nowhere.md')]\n"
            "for name, target in (('Back out.md', outside), ('Back note.md', inner)):\n"
            "    os.symlink(target, arc / name); rep = []\n"
            f"    tracker._reverse_move({{'from': '{ABC}/notes/' + name, 'to': '{ABC}/{ARCHIVE}/notes/' + name, 'kind': 'notes'}}, rep)\n"
            "    out[name] = [rep, os.path.islink(arc / name), os.path.lexists(note / name)]\n"
            "(arc / 'Back swap.md').write_text('archived'); os.link = swap; rep = []\n"
            f"tracker._reverse_move({{'from': '{ABC}/notes/Back swap.md', 'to': '{ABC}/{ARCHIVE}/notes/Back swap.md', 'kind': 'notes'}}, rep)\n"
            "os.link = real_link\n"
            "out['back_swap'] = [rep, os.path.islink(arc / 'Back swap.md'), os.path.lexists(note / 'Back swap.md')]\n"
            "out['st'] = st()\n"
            "print(json.dumps(out))")
        for name in ("Link out.md", "Link note.md"):
            chk, mover, still, archived = got[name]
            self.assertIn("never follows a symlink", chk)
            self.assertIn("is a symlink", mover)
            self.assertEqual([still, archived], [True, False])                     # the symlink stays; nothing in 99 Archive
        for case in ("swap", "swap_no_flag"):                                      # with and without follow_symlinks=False
            self.assertIn("is a symlink", got[case][0])
            self.assertEqual(got[case][1:], [True, False])
        self.assertIn("already exists", got["dest"][0])                            # a symlink at the destination is a taken name
        self.assertEqual(got["dest"][1:], ["to delete", False])                    # never followed to make its target
        for name in ("Back out.md", "Back note.md", "back_swap"):
            rep, still, back = got[name]
            self.assertEqual(len(rep), 1)
            self.assertIn("it is a symlink now", rep[0])
            self.assertEqual([still, back], [True, False])
        self.assertEqual(got["st"], [1, 1, "not a note"])                          # nothing outside, or the other note, linked
        self.assertTrue((self.folder() / "Other note.md").is_file(), other)

    # ── Team Cap's review M7: the unlink fails after the link: the new name is removed and the error raised ──
    def test_r_a_failed_unlink_leaves_one_name(self):
        got = self.py_json(
            "import errno, os, pathlib, tracker\n"
            f"note, arc = pathlib.Path({str(self.folder())!r}), pathlib.Path({str(self.archive())!r})\n"
            "arc.mkdir(parents=True, exist_ok=True); a, b = note / 'Unlink.md', arc / 'Unlink.md'; a.write_text('kept')\n"
            "real_unlink, seen = os.unlink, []\n"
            "def once(p, *args, **kw):\n"
            "    seen.append(str(p)); os.unlink = real_unlink\n"
            "    raise PermissionError(errno.EPERM, 'not now', str(p))\n"
            "os.unlink = once\n"
            "try:\n"
            "    tracker._move(a, b, 'notes'); err = None\n"
            "except PermissionError as e:\n"
            "    err = e.strerror\n"
            "os.unlink = real_unlink\n"
            "print(json.dumps([err, seen, a.read_text(), os.path.lexists(b), os.stat(a).st_nlink]))")
        err, seen, text, second, links = got
        self.assertEqual(err, "not now")                                           # re-raised
        self.assertEqual(seen, [str(self.folder() / "Unlink.md")])                 # the source's unlink failed
        self.assertEqual([text, second, links], ["kept", False, 1])                # the new link removed: one name, as it was

    # ── Team Cap's review M8 (and F4): unreadable counts as a move, so the lock is taken ──
    def test_s_unreadable_counts_as_a_note_move(self):
        got = self.py_json(
            "import pathlib, live_server as ls, paths\n"
            "bad = paths.STAGING / 'proposed-2026-10-16-bad.json'; bad.write_text('{not json')\n"
            "staged_bad = ls.staged_note_move(); bad.unlink()\n"
            "staged_clean = ls.staged_note_move()\n"
            "def rec(ops): return json.dumps([{'apply_id': 1, 'undone_at': None, 'file_ops': ops}])\n"
            "answers = {'failed': (1, ''), 'not json': (0, 'not json'), 'bad ops': (0, rec('garbage')),\n"
            "           'not records': (0, rec('[1]')), 'no id': (0, json.dumps([{'undone_at': None}])),\n"
            "           'no move': (0, rec(json.dumps([{'op': 'copy', 'to': 'x'}]))),\n"
            "           'a note move': (0, rec(json.dumps([{'op': 'move', 'kind': 'notes'}])))}\n"
            "out = {}\n"
            "for k, v in answers.items():\n"
            "    ls.run = lambda *a, v=v: v\n"
            "    out[k] = ls.undo_note_move()\n"
            "print(json.dumps([staged_bad, staged_clean, out]))")
        staged_bad, staged_clean, undo = got
        self.assertTrue(staged_bad)
        self.assertFalse(staged_clean)
        self.assertEqual(undo, {"failed": True, "not json": True, "bad ops": True, "not records": True, "no id": True,
                                "no move": False, "a note move": True})

    def py_json(self, code):
        src = f"import sys, json; sys.path.insert(0, 'system/scripts')\n{code}"
        r = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True, cwd=self.v.root)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])


class NoteShapes(OneDriveCase):
    """reach.archive_move_problem's "notes" and "notes_back": one note, into (or back from) its own folder's 99 Archive."""

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
        ok = {"same name": (f"{e}/08 Notes/Note.md", f"{e}/99 Archive/08 Notes/Note.md"),
              "numbered": (f"{e}/08 Notes/Note.md", f"{e}/99 Archive/08 Notes/Note-2.md"),
              "the portfolio": ("projects/_portfolio/08 Notes/Cross.md", "projects/_portfolio/99 Archive/08 Notes/Cross.md")}
        self.assertEqual(self.problems(ok, "notes"), {k: None for k in ok})
        bad = {"another engagement": (f"{e}/08 Notes/Note.md", "projects/Digital Enablement/99 Archive/08 Notes/Note.md"),
               "another name": (f"{e}/08 Notes/Note.md", f"{e}/99 Archive/08 Notes/Other.md"),
               "a zero number": (f"{e}/08 Notes/Note.md", f"{e}/99 Archive/08 Notes/Note-02.md"),
               "not a number": (f"{e}/08 Notes/Note.md", f"{e}/99 Archive/08 Notes/Note-x.md"),
               "another folder": (f"{e}/08 Notes/Note.md", f"{e}/99 Archive/02 Meetings/Minutes/Note.md"),
               "minutes as a note": (f"{e}/02 Meetings/Minutes/Note.md", f"{e}/99 Archive/02 Meetings/Minutes/Note.md"),
               "not Markdown": (f"{e}/08 Notes/Plan.txt", f"{e}/99 Archive/08 Notes/Plan.txt"),
               "hidden": (f"{e}/08 Notes/.hidden.md", f"{e}/99 Archive/08 Notes/.hidden.md"),
               "a picture": (f"{e}/08 Notes/_images/a.png", f"{e}/99 Archive/08 Notes/_images/a.png"),
               "the folder": (f"{e}/08 Notes", f"{e}/99 Archive/08 Notes"),
               "the projects root's 99 Archive": (f"{e}/08 Notes/Note.md", "projects/99 Archive/Example Programme/08 Notes/Note.md"),
               "dot dot": (f"{e}/08 Notes/../08 Notes/Note.md", f"{e}/99 Archive/08 Notes/Note.md")}
        for k, why in self.problems(bad, "notes").items():
            self.assertTrue(why, k)
        self.assertTrue(self.problems({"x": ok["same name"]}, "reports")["x"], "a note is never a report")
        (self.root / "Example Programme" / "99 Archive" / "08 Notes").mkdir(parents=True)
        (self.root / "Example Programme" / "99 Archive" / "08 Notes" / "Gone.md").write_text("x")
        back = {"back": (f"{e}/99 Archive/08 Notes/Gone.md", f"{e}/08 Notes/Gone.md")}
        self.assertEqual(self.problems(back, "notes_back"), {"back": None})
        wrong = {"elsewhere": (f"{e}/99 Archive/08 Notes/Gone.md", f"{e}/02 Meetings/Minutes/Gone.md"),
                 "the other way": (f"{e}/08 Notes/Note.md", f"{e}/99 Archive/08 Notes/Note.md"),
                 "another name": (f"{e}/99 Archive/08 Notes/Gone.md", f"{e}/08 Notes/Other.md"),
                 "a zero number": (f"{e}/99 Archive/08 Notes/Gone.md", f"{e}/08 Notes/Gone-02.md"),
                 "unicode digits": (f"{e}/99 Archive/08 Notes/Gone.md", f"{e}/08 Notes/Gone-\u0662.md"),
                 "not Markdown": (f"{e}/99 Archive/08 Notes/Gone.md", f"{e}/08 Notes/Gone-2.txt")}
        for k, why in self.problems(wrong, "notes_back").items():
            self.assertTrue(why, k)
        renamed = {"a free name": (f"{e}/99 Archive/08 Notes/Gone.md", f"{e}/08 Notes/Gone-2.md")}
        self.assertEqual(self.problems(renamed, "notes_back"), {"a free name": None})       # NOTES_BACK_RENAMES

    def test_note_number_is_ascii_digits_only(self):
        got = self.py("import reach; print(json.dumps([reach._note_name('Note.md', n) for n in "
                      "('Note-2.md', 'Note-9999.md', 'Note-\u0662.md', 'Note-\u00b2.md', 'Note-\uff12.md', 'Note-02.md', "
                      "'Note-10000.md', 'Note-.md')]))")
        self.assertEqual(got, [True, True, False, False, False, False, False, False])

    def test_the_spec_in_onedrive(self):
        notes = self.root / "Example Programme" / "08 Notes"
        notes.mkdir(parents=True, exist_ok=True)
        (notes / "Stakeholders.md").write_text("---\ntitle: Stakeholders\nconfidential: true\n---\n\nThe secret body.\n")
        spec, why = self.py("import archive; print(json.dumps(archive.note_delete_spec('projects/Example Programme/08 Notes/Stakeholders.md')))")
        self.assertIsNone(why)
        self.assertEqual(spec["file_changes"]["file_ops"], [{"op": "move", "from": "projects/Example Programme/08 Notes/Stakeholders.md",
                                                             "to": "projects/Example Programme/99 Archive/08 Notes/Stakeholders.md"}])
        self.assertEqual(spec["file_changes"]["project"], "ABC")
        self.assertNotIn("secret", json.dumps(spec))                       # only the title is read, for the card
        self.assertEqual(self.py("import archive; print(json.dumps(archive.note_delete_spec('projects/Example Programme/CLAUDE.md')))")[1],
                         "that isn't a note that is there")


if __name__ == "__main__":
    unittest.main()
