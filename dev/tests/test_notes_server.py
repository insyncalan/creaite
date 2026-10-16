"""BL-301 (v20-notes-server): notes, the server side. No dashboard.

Run: python3 dev/tests/test_notes_server.py

  - a note's front matter round-trips (known keys in order, an unknown key kept, lists and flags read whatever was written);
  - the four templates make a note, a Working session one with its date and people; names are safe and a taken one gets a number;
  - notes-sent.json keeps paragraph numbers, fingerprints and item IDs, never text; a changed or new paragraph is unsent again;
  - the notes folder: `notes/` in the default layout, `08 Notes` with a projects folder (the default even when the saved
    `locations.folders` predates it); made for a new project (added when the skeleton lacks it); listed as its own kind, never
    as documents, pictures in `_images` left out;
  - search indexes notes as kind `note` (front matter left out, the meeting date or last update as its date), finds them in a Notes
    group and with the type word "notes", previews them without front matter, and keeps a confidential note's text out of what
    it gathers for Claude; an index built by an older release is rebuilt once;
  - notes are never extracted, and doctor doesn't ask for a notes folder that hasn't been made yet.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_dashboard import populate  # noqa: E402
from test_onedrive_projects import OneDriveCase, touch  # noqa: E402
from test_tracker import ABC, Vault  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "system" / "scripts"))
import notes  # noqa: E402

STAKEHOLDER = """---
title: Mia Hale
created: 2026-10-01
updated: 2026-10-12
tags: [stakeholder, client]
pinned: true
confidential: false
---

Mia prefers a short written summary before each steering meeting.

She worries about the zephyrine data access dates.
"""
SECRET = """---
title: Negotiation position
created: 2026-10-02
updated: 2026-10-03
tags: [commercial]
pinned: false
confidential: true
---

Our walk-away on the zephyrine extension is twelve weeks.
"""
SESSION = """---
title: Working session with Omar
created: 2026-10-05
updated: 2026-10-09
tags: [working session]
pinned: false
confidential: false
date: 2026-10-05
with: [Omar Haddad]
---

Agreed the cut-over plan.
"""


def run_py(vault, code):
    src = f"import sys, json; sys.path.insert(0, {str(vault.root / 'system/scripts')!r})\n{code}"
    r = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True, cwd=tempfile.gettempdir())
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout.strip().splitlines()[-1])


class Format(unittest.TestCase):
    def test_front_matter_round_trips_with_unknown_keys_kept(self):
        meta, body = notes.parse(STAKEHOLDER)
        self.assertEqual(meta, {"title": "Mia Hale", "created": "2026-10-01", "updated": "2026-10-12",
                                "tags": ["stakeholder", "client"], "pinned": True, "confidential": False})
        self.assertTrue(body.startswith("Mia prefers"))
        self.assertEqual(notes.render(meta, body), STAKEHOLDER)
        meta["mood"] = "calm"
        meta2, body2 = notes.parse(notes.render(meta, body))
        self.assertEqual((meta2, body2), (meta, body))
        self.assertTrue(notes.render(meta, body).split("\n")[7].startswith("mood: "))          # after the known keys

    def test_lists_flags_and_awkward_titles_are_read_whatever_was_written(self):
        meta, _ = notes.parse("---\ntitle: \"[Draft] true\"\nwith: Omar Haddad, Sara Khan\nconfidential: yes\ntags: []\n---\nx")
        self.assertEqual(meta, {"title": "[Draft] true", "with": ["Omar Haddad", "Sara Khan"], "confidential": True, "tags": []})
        self.assertEqual(notes.parse(notes.render(meta, "x"))[0], meta)
        self.assertEqual(notes.parse("Just text\n"), ({}, "Just text\n"))                      # no front matter: all body
        self.assertEqual(notes.parse("---\ntitle: open\nno end"), ({}, "---\ntitle: open\nno end"))

    def test_a_save_sets_updated_and_keeps_created(self):
        meta = notes.touched({"title": "x", "created": "2026-09-01"}, date(2026, 10, 13))
        self.assertEqual((meta["created"], meta["updated"]), ("2026-09-01", "2026-10-13"))
        self.assertEqual(notes.touched({}, date(2026, 10, 13))["created"], "2026-10-13")

    def test_the_four_templates(self):
        for name in notes.TEMPLATES:
            meta, body = notes.parse(notes.template(name, "Kick-off", today=date(2026, 10, 13)))
            self.assertEqual((meta["title"], meta["created"], meta["updated"]), ("Kick-off", "2026-10-13", "2026-10-13"))
            self.assertIs(meta["confidential"], False)
            self.assertEqual("date" in meta, name == "working-session")
        meta, body = notes.parse(notes.template("working-session", "Cut-over", today=date(2026, 10, 13), when="2026-10-14",
                                                people=["Omar Haddad", " "]))
        self.assertEqual((meta["date"], meta["with"]), ("2026-10-14", ["Omar Haddad"]))
        self.assertIn("## Agreed", body)
        with self.assertRaises(ValueError):
            notes.template("wiki", "x")

    def test_file_names_are_safe(self):
        self.assertEqual(notes.file_name('Q3: plan / "draft"?'), "Q3 plan draft")
        self.assertEqual(notes.file_name("..hidden"), "hidden")
        self.assertEqual(notes.file_name("  "), "Untitled note")

    def test_paragraphs_are_numbered_from_one(self):
        self.assertEqual(notes.paragraphs("One\nstill one\n\n\nTwo\n"), [(1, "One\nstill one"), (2, "Two")])
        self.assertEqual(notes.fingerprint("a  b\n"), notes.fingerprint("a b"))


class Sent(unittest.TestCase):
    def setUp(self):
        self.v = Vault()

    def tearDown(self):
        self.v.cleanup()

    def test_what_was_sent_is_kept_beside_the_note_without_its_text(self):
        o = run_py(self.v, """import notes, paths
rel = 'projects/ABC Example Programme/notes/Catch-up.md'
body = 'Omar to send the plan by Friday.\\n\\nThe zephyrine risk is real.\\n\\nNothing here.'
notes.record_sent(rel, [(1, 'Omar to send the plan by Friday.', ['ABC-A-010']), (2, 'The zephyrine risk is real.', ['ABC-R-004'])],
                  '2026-10-13 09:30')
first = [n for n, _ in notes.unsent(rel, body)]
moved = 'New line first.\\n\\n' + body.replace('real.', 'very real.')
print(json.dumps({'raw': paths.NOTES_SENT.read_text(), 'first': first, 'again': [n for n, _ in notes.unsent(rel, moved)],
                  'ticks': notes.sent_ids(rel, moved)}))""")
        self.assertNotIn("Omar to send", o["raw"])
        self.assertNotIn("zephyrine", o["raw"])
        rec = json.loads(o["raw"])["notes"]["projects/ABC Example Programme/notes/Catch-up.md"]
        self.assertEqual([(r["p"], r["ids"], r["at"]) for r in rec], [(1, ["ABC-A-010"], "2026-10-13 09:30"), (2, ["ABC-R-004"], "2026-10-13 09:30")])
        self.assertEqual(o["first"], [3])                       # only the line that gave nothing is left
        self.assertEqual(o["again"], [1, 3, 4])                 # a new line, the changed one, and the one that gave nothing
        self.assertEqual(o["ticks"], {"2": ["ABC-A-010"]})      # the sent line, moved down one, keeps its tick


class Checks:
    """Shared by both layouts. The case sets self.v and self.folder (the ABC notes folder) and self.stored (its stored path)."""

    def files(self):
        return run_py(self.v, "import paths\nprint(json.dumps([[f.name, k] for f, k, s in paths.project_files('ABC')]))")

    def test_notes_are_their_own_kind_never_documents(self):
        rows = self.files()
        self.assertIn(["Mia Hale.md", "notes"], rows)
        self.assertIn(["Negotiation position.md", "notes"], rows)
        self.assertFalse([r for r in rows if r[0] in ("Mia Hale.md", "plan.png") and r[1] != "notes"])
        self.assertNotIn(["plan.png", "notes"], rows)                                       # pictures are not notes
        o = run_py(self.v, "import paths\nprint(json.dumps([f.name for f in paths.document_files('ABC')]))")
        self.assertFalse({"Mia Hale.md", "plan.png"} & set(o))

    def test_never_extracted(self):
        o = run_py(self.v, "import paths\nprint(json.dumps([str(d) for d in paths.extract_dirs('ABC')]))")
        self.assertFalse([d for d in o if Path(d) == self.folder])

    def test_is_note(self):
        o = run_py(self.v, f"""import paths
print(json.dumps([paths.is_note({self.stored + '/Mia Hale.md'!r}), paths.is_note({self.stored + '/_images/plan.png'!r}),
                  paths.is_note({str(self.folder / 'Mia Hale.md')!r})]))""")
        self.assertEqual(o, [True, False, True])

    def test_search_finds_notes_as_notes(self):
        o = run_py(self.v, """import search, tracker
r = search.search('zephyrine')
rows = tracker.connect().execute("SELECT path, kind, date, content FROM vault_search WHERE kind = 'note' ORDER BY path").fetchall()
t = search.search('notes cut-over')
print(json.dumps({'notes': [[x['title'], x['kind'], x['opens']['type']] for x in r['groups']['notes']], 'docs': r['groups']['documents'],
                  'rows': [[x[0].rsplit('/', 1)[1], x[1], x[2], x[3]] for x in rows],
                  'typed': [c['label'] for c in t['chips']], 'typed_groups': {g: len(v) for g, v in t['groups'].items()}}))""")
        self.assertEqual(sorted(o["notes"]), [["Mia Hale", "note", "preview"], ["Negotiation position", "note", "preview"]])
        self.assertEqual(o["docs"], [])
        rows = {r[0]: r for r in o["rows"]}
        self.assertEqual(rows["Mia Hale.md"][2], "2026-10-12")                          # last updated
        self.assertEqual(rows["Working session with Omar.md"][2], "2026-10-05")              # the meeting's date
        self.assertNotIn("confidential:", rows["Mia Hale.md"][3])                       # front matter left out
        self.assertIn("stakeholder, client", rows["Mia Hale.md"][3])                    # but the tags are searchable
        self.assertIn("Notes", o["typed"])
        self.assertEqual(o["typed_groups"]["notes"], 1)
        self.assertEqual(o["typed_groups"]["documents"], 0)

    def test_preview_leaves_the_front_matter_out(self):
        o = run_py(self.v, f"import search\nprint(json.dumps(search.preview({self.stored + '/Mia Hale.md'!r}, 'zephyrine')))")
        self.assertTrue(o["ok"])
        self.assertIn("<mark>zephyrine</mark>", o["html"])
        self.assertNotIn("pinned", o["html"])

    def test_a_confidential_notes_text_is_kept_from_claude(self):
        o = run_py(self.v, "import search\nc = search.context('zephyrine')\nprint(json.dumps([c['text'], [s['name'] for s in c['sources']]]))")
        self.assertIn("Mia prefers", o[0])
        self.assertIn("Note (internal)", o[0])
        self.assertNotIn("walk-away", o[0])
        self.assertIn("1 confidential note(s) also matched", o[0])
        self.assertNotIn("Negotiation position.md", o[1])


def write_notes(folder):
    touch(folder / "Mia Hale.md", STAKEHOLDER)
    touch(folder / "Negotiation position.md", SECRET)
    touch(folder / "Working session with Omar.md", SESSION)
    touch(folder / "_images" / "plan.png", b"\x89PNG")


class DefaultLayout(Checks, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        populate(cls.v)
        cls.folder = (cls.v.root / ABC / "notes").resolve()
        cls.stored = f"{ABC}/notes"
        write_notes(cls.folder)

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def test_portfolio_notes_are_indexed_under_the_portfolio(self):
        touch(self.v.root / "projects/_portfolio/notes/Unfiled thought.md", "---\ntitle: Unfiled thought\n---\n\nquuxberry idea\n")
        o = run_py(self.v, "import search\nprint(json.dumps([[x['title'], x['project']] for x in search.search('quuxberry')['groups']['notes']]))")
        self.assertEqual(o, [["Unfiled thought", "_portfolio"]])

    def test_an_index_built_by_an_older_release_is_rebuilt_once(self):
        o = run_py(self.v, """import tracker, json as j
tracker.build_index()
fresh = tracker.index_state()
s = j.loads(tracker.index_stamp().read_text()); s.pop('version')
tracker.index_stamp().write_text(j.dumps(s))
print(json.dumps([fresh, tracker.index_state()]))""")
        self.assertEqual(o, [[False, ""], [True, "built by an older release"]])

    def test_a_new_project_gets_a_notes_folder(self):
        ops = json.loads(self.v.run("new-project", "--code", "JKL", "--name", "Local One", script="propose.py").stdout)["file_changes"]["file_ops"]
        self.assertIn({"op": "mkdir", "path": "projects/JKL Local One/notes"}, ops)


class OutsideRoot(Checks, OneDriveCase):
    """The saved `locations.folders` predates notes: the default, 08 Notes, applies."""

    def setUp(self):
        super().setUp()
        self.folder = self.eng("ABC", "08 Notes").resolve()
        self.stored = "projects/Example Programme/08 Notes"
        write_notes(self.folder)

    def test_the_folder_is_08_notes_and_doctor_does_not_ask_for_one_not_made(self):
        o = self.py("import paths, doctor\nprint(json.dumps([str(paths.folder('DEF', 'notes')), doctor.mapped_folders()[1]]))")
        self.assertEqual(o[0], str(self.eng("DEF", "08 Notes")))
        self.assertNotIn("08 Notes", o[1])

    def test_doctor_flags_a_notes_folder_shared_with_another_kind(self):
        """#124: Delete note moves the notes folder's files, so it must be a folder of its own."""
        o = self.py("import paths, doctor\nreal = paths.locations\nout = [doctor.notes_folder_own()[0]]\n"
                    "for n in ('04 Reporting/Weekly', '04 reporting', '02 Meetings/Minutes/Notes', '.', '08 Notes/'):\n"
                    "    paths.locations = lambda n=n: {**real(), 'folders': {**real()['folders'], 'notes': n}}\n"
                    "    out.append(doctor.notes_folder_own())\n"
                    "print(json.dumps(out))")
        self.assertTrue(o[0])
        for (ok, why), n in zip(o[1:5], ("weekly_reports", "client_reports", "minutes", "transcripts")):
            self.assertFalse(ok, why)
            self.assertIn(n, why)
        self.assertTrue(o[5][0], o[5])

    def test_a_new_project_gets_08_notes_when_the_skeleton_lacks_it_and_only_once(self):
        ops = json.loads(self.v.run("new-project", "--code", "GHI", "--name", "Green Harbour Pilot", script="propose.py").stdout)["file_changes"]["file_ops"]
        self.assertEqual([o for o in ops if o.get("path") == "projects/Green Harbour Pilot/08 Notes"], [{"op": "mkdir", "path": "projects/Green Harbour Pilot/08 Notes"}])
        (self.root / "_Templates" / "_Skeleton" / "08 Notes").mkdir()
        ops = json.loads(self.v.run("new-project", "--code", "GHI", "--name", "Green Harbour Pilot", script="propose.py").stdout)["file_changes"]["file_ops"]
        self.assertEqual(len([o for o in ops if o.get("path") == "projects/Green Harbour Pilot/08 Notes"]), 1)


if __name__ == "__main__":
    unittest.main()
