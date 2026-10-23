"""#283 (Team Cap's H-1, v2.6.1): a hold.json planted in system/staging/reextract/ must move, write and delete NOTHING.

Run: python3 dev/tests/test_reextract_planting.py

Until Team Cap's review a model run could create system/staging/reextract/<run>/hold.json with filechange.py, and the live server's
start-up recover() trusted it: it moved a file named in the hold into the engine and to a path outside the vault. Two fixes:
- reextract.py (plain code) checks EVERY field it reads from a manifest (_clean): put back, settle (finish), Undo and recover() all go
  through it; a manifest that isn't creaite's is ignored, with a plain debug line and no move, no delete, no write.
- reach.py (a guarded diff, dev/proposals/283-reextract/reach.diff): a write under system/staging/reextract/ is a RECORD, so
  filechange.py and the hook refuse it. The rule's tests skip until that diff is applied.

Every planting test snapshots the whole vault (apart from the debug log) before and after and expects the same bytes, and that the
named outside files do not exist. Run it with and without the guarded chain applied: the plain-code half passes in both states.
"""
import hashlib
import json
import os
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "system" / "scripts"))
from test_reextract import Fixture, in_vault  # noqa: E402

RULE = "system/staging/reextract" in (REPO / "system/scripts/reach.py").read_text(encoding="utf-8")
needs_rule = (lambda f: f) if RULE else unittest.skip("the reach.diff rule is not applied")

RUN = "plant-0001"


def snapshot(root, skip=("system/logs",)):
    """{relative path: sha256 or 'link:<target>'} for every file and link under root, the debug log left out."""
    out = {}
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x != "__pycache__"]
        rel = os.path.relpath(d, root)
        if any(rel == s or rel.startswith(s + os.sep) for s in skip):
            dirs[:] = []
            continue
        for n in dirs + files:
            p = Path(d) / n
            r = str(p.relative_to(root))
            if p.is_symlink():
                out[r] = "link:" + os.readlink(p)
            elif p.is_file():
                out[r] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


class Planting(Fixture, unittest.TestCase):
    def setUp(self):
        self.make()
        self.outside = Path(self.v.root).parent / "outside-the-vault-planted.html"
        self.evil = self.v.root / "system/scripts/evilplant.py"
        self.outside_planted = False                    # True when a test made the outside file itself (a link's target)

    def tearDown(self):
        self.outside.unlink(missing_ok=True)
        self.v.cleanup()

    def hold_dir(self):
        d = self.v.root / "system/staging/reextract" / RUN
        d.mkdir(parents=True, exist_ok=True)
        return d

    def manifest(self, **over):
        h = {"run": RUN, "state": "held", "at": 1.0, "proposal": "proposed-zzplant.json", "draft": "system/staging/drafts/planted.html",
             "transcript": self.data["meeting"]["transcript"], "date": "2026-10-01", "title": "Planted", "projects": ["ABC"]}
        h.update(over)
        return h

    def plant(self, h, link=None):
        """A hold with manifest h, a planted proposal and a planted record in it (and a link, when asked)."""
        d = self.hold_dir()
        (d / "hold.json").write_text(json.dumps(h), encoding="utf-8")
        (d / "proposed-zzplant.json").write_text(json.dumps({"meeting": {"transcript": "x"}, "items": []}), encoding="utf-8")
        (d / "record.html").write_text("<html>planted record</html>", encoding="utf-8")
        if link:
            os.symlink(*link)
        return d

    def nothing_moves(self, calls):
        """Run `calls` (Python in the vault) and expect the vault byte for byte as it was, and no planted outside file."""
        before = snapshot(self.v.root)
        in_vault(self.v, calls)
        self.assertEqual(snapshot(self.v.root), before)
        self.assertFalse(self.evil.exists())
        self.assertEqual(self.outside.exists(), self.outside_planted)

    def every_way_in(self, h, link=None, undo=False):
        self.plant(h, link)
        run = "import reextract as r\n"
        self.nothing_moves(run + "r.recover(); r.recover(); print(1)")
        self.nothing_moves(run + f"r.put_back({RUN!r}); r.put_back({RUN!r}, 'x', 'needs', 'q'); print(1)")
        self.nothing_moves(run + f"r.finish({RUN!r}, 0, (), 'failed'); r.finish({RUN!r}, 0, (), 'done'); print(1)")
        self.nothing_moves(run + f"print(json.dumps(r.undo({RUN!r})))")
        self.nothing_moves(run + "r._prune(); print(1)")

    # held holds: recover, put back, settle
    def test_a_draft_that_names_an_engine_file_moves_nothing(self):
        self.every_way_in(self.manifest(draft="system/scripts/evilplant.py"))

    def test_a_draft_that_is_an_absolute_path_moves_nothing(self):
        self.every_way_in(self.manifest(draft=str(self.outside)))

    def test_a_draft_that_climbs_out_moves_nothing(self):
        self.every_way_in(self.manifest(draft="system/staging/drafts/../../scripts/evilplant.html"))
        self.every_way_in(self.manifest(draft="../outside-the-vault-planted.html"))

    def test_a_draft_that_is_not_directly_in_drafts_moves_nothing(self):
        self.every_way_in(self.manifest(draft="system/staging/drafts/sub/planted.html"))
        self.every_way_in(self.manifest(draft="system/staging/planted.html"))

    def test_a_draft_that_is_not_a_minutes_record_moves_nothing(self):
        (self.v.root / "system/staging/drafts/notarecord.html").write_text("<html>just a page</html>", encoding="utf-8")
        self.every_way_in(self.manifest(draft="system/staging/drafts/notarecord.html"))

    def test_a_draft_that_is_a_link_moves_nothing(self):
        link = (str(self.outside), str(self.v.root / "system/staging/drafts/linked.html"))
        self.outside.write_text("<html>outside</html>", encoding="utf-8")
        self.outside_planted = True
        self.every_way_in(self.manifest(draft="system/staging/drafts/linked.html"), link=link)
        self.assertTrue(self.outside.exists(), "the outside file itself is untouched")

    def test_a_proposal_that_is_not_a_proposal_name_moves_nothing(self):
        for bad in ("system/scripts/evilplant.py", "../../scripts/evilplant.py", "proposed-../../x.json", "/etc/hosts",
                    "proposed-x.json/../../y", "evilplant.py", ["proposed-x.json"], None, ""):
            self.every_way_in(self.manifest(proposal=bad))

    def test_a_manifest_of_the_wrong_shape_moves_nothing(self):
        for over in ({"run": "other-run"}, {"state": "unheard-of"}, {"at": "yesterday"}, {"projects": "ABC"}, {"projects": [1]},
                     {"transcript": 5}, {"title": None}, {"new_proposal": "system/scripts/x.py", "state": "replaced"},
                     {"new_draft": "system/scripts/x.py", "state": "replaced"}):
            self.every_way_in(self.manifest(**over))

    def test_a_hold_that_is_not_a_plain_file_moves_nothing(self):
        d = self.hold_dir()
        real = self.v.root / "system/staging/real-hold.json"
        real.write_text(json.dumps(self.manifest(draft="system/scripts/evilplant.py")), encoding="utf-8")
        os.symlink(real, d / "hold.json")
        (d / "proposed-zzplant.json").write_text("{}", encoding="utf-8")
        self.nothing_moves(f"import reextract as r; r.recover(); r.put_back({RUN!r}); print(1)")

    # replaced holds: Undo
    def test_undo_of_a_planted_replaced_hold_moves_nothing(self):
        for over in ({"draft": "system/scripts/evilplant.py"}, {"draft": str(self.outside)},
                     {"proposal": "system/scripts/evilplant.py"}, {"new_proposal": "../../scripts/evilplant.py"},
                     {"new_draft": "system/scripts/evilplant.py"}):
            self.every_way_in(self.manifest(**{"state": "replaced", "new_proposal": "proposed-zznew.json",
                                               "new_draft": "system/staging/drafts/new.html", **over}))

    def test_a_manifest_creaite_wrote_still_works(self):
        """The control: the real thing is not refused (test_reextract covers every outcome)."""
        in_vault(self.v, "import reextract as r; c, _ = r.validate_request({'proposal': json.loads(sys.stdin.read())}); "
                         "r.hold(c, 'x-ok-0001'); print(1)", self.proposal)
        got = in_vault(self.v, "import reextract as r; print(json.dumps(r.recover()))")
        self.assertEqual(got, [self.proposal])

    # the guarded half
    @needs_rule
    def test_filechange_and_the_hook_refuse_a_write_under_reextract(self):
        """The hook lets a `filechange.py` Bash call through (filechange decides), so the proof is filechange's own refusal; a direct
        Write is refused by the hook in every mode, a confirmed run too."""
        code = ("import reach\n"
                "p = 'system/staging/reextract/abcdef1/hold.json'\n"
                "out = {'classify': [reach.classify(p, op, marked=m)[0] for op in ('create', 'change', 'delete') for m in (False, True)],\n"
                "       'write': {m: reach.decide('Write', {'file_path': str(reach.paths.ROOT / p), 'content': '{}'}, m, 'r-test')[0]\n"
                "                 for m in ('ask', 'sweep', 'confirmed')}}\n"
                "print(json.dumps(out))")
        got = in_vault(self.v, code)
        self.assertEqual(set(got["classify"]), {"never"})
        self.assertEqual(got["write"], {"ask": False, "sweep": False, "confirmed": False})
        (self.v.root / "system/staging/drafts/h.json").write_text(json.dumps(self.manifest()), encoding="utf-8")
        for where in ("system/staging/reextract/abcdef1/hold.json", "system/staging/reextract/abcdef1/record.html"):
            r = self.v.run("create", where, "--from", "system/staging/drafts/h.json", script="filechange.py", ok=False, cwd=self.v.root)
            self.assertNotEqual(r.returncode, 0, r.stdout)
            self.assertFalse((self.v.root / where).exists())

    @needs_rule
    def test_the_live_servers_own_hold_is_unaffected_by_the_rule(self):
        """reextract.py writes with plain Python (not filechange): hold, put back and settle still work with the rule in."""
        in_vault(self.v, "import reextract as r; c, _ = r.validate_request({'proposal': json.loads(sys.stdin.read())}); "
                         "r.hold(c, 'x-rule-0001'); print(r.put_back('x-rule-0001')['state'] == 'put_back' and 1)", self.proposal)
        self.assertTrue((self.v.root / "system/staging" / self.proposal).is_file())


if __name__ == "__main__":
    unittest.main()
