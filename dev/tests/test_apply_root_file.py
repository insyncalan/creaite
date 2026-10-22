"""#280 follow-up (Cap's 2.5.4 review): every apply the live server runs names its staged proposal by its path, never a bare file name.

Run: python3 dev/tests/test_apply_root_file.py      (in-process, over a throwaway vault; no Chrome, no server)

tracker.py apply resolves a bare name in the vault root before system/staging/ (resolve_proposal), so a file of the same name in the
root (an ask creaite run can create one: a root .json is an ordinary create) would be applied in place of the staged proposal.
/api/apply {only} already passes "system/staging/" + name (dev/proposals/280/live_server.py.diff). These are the four other routes:
edit_apply (Approve on a change card), confirmed_apply_one (Go ahead in ask creaite), page_move (Delete note, Move back) and
notes_apply_now (Find updates' Apply). Each one is run for real; just before tracker.py apply runs, a file of the same name holding
another approved change is planted in the vault root. The staged change must be written, the root file left exactly as it was and
its change never written. A static check covers the same rule in review.py (Approve minutes) and report_server.py (a report's
Approve), which are not guarded and pass the path already.

The live server tests skip until live_server.py takes dev/proposals/280-followup/live_server-followup.py.diff
(CREAITE_UNSKIP_280FU=1 runs them anyway, to see them fail first). Everything is fictional and temporary.
"""
import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_dashboard import populate  # noqa: E402
from test_tracker import Vault  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "system/scripts"
FOLLOWUP = 'run("tracker.py", "apply", "system/staging/" + f.name)'
TAKEN = FOLLOWUP in (SCRIPTS / "live_server.py").read_text(encoding="utf-8") or os.environ.get("CREAITE_UNSKIP_280FU") == "1"

# Planted by the stand-in run(), just before the real tracker.py apply: the same name in the vault root, another approved change.
PLANT = """
import json, pathlib, paths, live_server as ls
real, seen = ls.run, []
def run(script, *args):
    if script == "tracker.py" and args and args[0] == "apply" and len(args) > 1:
        name = pathlib.Path(args[1]).name
        planted = paths.ROOT / name
        planted.write_text(json.dumps({"created": "2026-10-21T12:00:00", "source_run": "dashboard", "files": [],
            "items": [{"n": 1, "op": "update", "table": "actions", "id": "ABC-A-001",
                       "changes": {"latest_update": "From the root"}, "match": "strong", "flags": [],
                       "decision": "approved"}]}), encoding="utf-8")
        seen.append([name, planted.read_text(encoding="utf-8")])
    return real(script, *args)
ls.run = run
SPEC = {"source_run": "cx-edit", "items": [{"op": "update", "table": "actions", "id": "ABC-A-001",
                                            "changes": {"latest_update": "From staging"}}]}
"""


@unittest.skipUnless(TAKEN, "live_server.py has not taken dev/proposals/280-followup/live_server-followup.py.diff yet")
class ApplyNamesTheStagedFile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        populate(cls.v)

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def py(self, code):
        src = f"import sys, json; sys.path.insert(0, 'system/scripts')\n{PLANT}\n{code}"
        r = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True, cwd=self.v.root)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def latest(self):
        return next(a for a in self.v.rows("actions") if a["id"] == "ABC-A-001")["latest_update"]

    def assert_staged_only(self, got, route):
        seen, ok = got["seen"], got["ok"]
        self.assertEqual(len(seen), 1, f"{route}: one apply, with a root namesake planted")
        name, raw = seen[0]
        planted = self.v.root / name
        try:
            self.assertTrue(ok, f"{route}: {got.get('message')}")
            self.assertNotIn("From the root", self.latest() or "", f"{route}: the vault-root namesake was applied")
            self.assertIn("From staging", self.latest() or "", f"{route}: the staged proposal was not applied")
            self.assertTrue(planted.is_file(), f"{route}: the root file is left where it was")
            self.assertEqual(planted.read_text(encoding="utf-8"), raw, f"{route}: the root file is never read or changed")
        finally:
            planted.unlink(missing_ok=True)
            self.reset()

    def reset(self):
        """ABC-A-001's latest update back to a known value, through tracker.py, for the next route."""
        p = self.v.propose("reset-" + str(abs(hash(self.id())) % 10 ** 8), [
            {"n": 1, "op": "update", "table": "actions", "id": "ABC-A-001", "changes": {"latest_update": "Reset"},
             "match": "strong", "flags": [], "decision": "approved"}])
        self.v.run("apply", str(p))

    def test_edit_apply(self):
        got = self.py("card, why = ls.server_edit_card('t', json.dumps(SPEC).encode('utf-8'))\n"
                      "out = ls.edit_apply(ls.EDITS[card['card']])\n"
                      "print(json.dumps({'seen': seen, 'ok': out.get('ok'), 'message': out.get('message')}))")
        self.assert_staged_only(got, "edit_apply")

    def test_page_move(self):
        got = self.py("apply_id, why = ls.page_move(SPEC)\n"
                      "print(json.dumps({'seen': seen, 'ok': bool(apply_id), 'message': why}))")
        self.assert_staged_only(got, "page_move")

    def test_confirmed_apply_one(self):
        got = self.py("import time\n"
                      "f = paths.STAGING / 'proposed-2026-10-21-121000-ask.json'\n"
                      "data = {'created': '2026-10-21T12:10:00', 'source_run': 'cx-edit', 'files': [], 'items': [\n"
                      "    {'n': 1, 'op': 'update', 'table': 'actions', 'id': 'ABC-A-001', 'changes': {'latest_update': 'From staging'},\n"
                      "     'match': 'strong', 'flags': [], 'decision': 'approved'}]}\n"
                      "f.write_text(json.dumps(data), encoding='utf-8')\n"
                      "class Run:\n"
                      "    id = 'a1'\n"
                      "out = ls.confirmed_apply_one(Run(), f, data)\n"
                      "print(json.dumps({'seen': seen, 'ok': out.get('ok'), 'message': out.get('message')}))")
        self.assert_staged_only(got, "confirmed_apply_one")

    def test_notes_apply_now(self):
        got = self.py("import notes_find\n"
                      "name = 'proposed-2026-10-21-122000-note.json'\n"
                      "(paths.STAGING / name).write_text(json.dumps({'created': '2026-10-21T12:20:00', 'source_run': 'note',\n"
                      "    'files': [], 'items': [{'n': 1, 'op': 'update', 'table': 'actions', 'id': 'ABC-A-001',\n"
                      "    'changes': {'latest_update': 'From staging'}, 'match': 'strong', 'flags': [], 'decision': 'approved'}]}),\n"
                      "    encoding='utf-8')\n"
                      "notes_find.record = lambda *a, **k: []\n"               # the note's own bookkeeping is not what is tested
                      "notes_find.note_of = lambda rel: {'name': 'A note'}\n"
                      "ls.note_sent_lines = lambda *a, **k: []\n"
                      "out = ls.notes_apply_now('projects/x/notes/A note.md', {'file': name, 'items': 1, 'files': 0})\n"
                      "print(json.dumps({'seen': seen, 'ok': out.get('ok'), 'message': out.get('message')}))")
        self.assert_staged_only(got, "notes_apply_now")


class EveryApplyCallPassesThePath(unittest.TestCase):
    """No script runs tracker.py apply with a bare proposal name (name, f.name, p.name, prop.name)."""
    BARE = re.compile(r'"apply", (?:\w+\.)?name\b')
    GUARDED = {"live_server.py"}

    def test_no_bare_name(self):
        for f in sorted(SCRIPTS.glob("*.py")):
            if f.name in self.GUARDED and not TAKEN:
                continue                                  # guarded: checked once the follow-up diff is applied
            for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                if "tracker.py" in line or '"apply"' in line:
                    self.assertIsNone(self.BARE.search(line), f"{f.name}:{i} passes a bare name to tracker.py apply: {line.strip()}")


if __name__ == "__main__":
    unittest.main()
