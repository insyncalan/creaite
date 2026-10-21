"""guard-small (1), #269 round 2 delta LOW 1: `tracker.py apply` files a copy's source only from inside the vault or the projects
folder. PROPOSAL test for dev/proposals/guard-small/tracker-copy-source.diff (tracker.py is a guarded file: Alan approves it).

Run: python3 dev/tests/test_guard_small_copy_source.py
Fail-first: GUARD_SMALL_UNPATCHED=1 python3 dev/tests/test_guard_small_copy_source.py     (the copy is left without the diff)

Before the diff, `check_file_op` and `_op_copy` looked only at the last part of the source for a link: an absolute `from` outside
the vault, a `../` path, a source under a symlinked folder and a hard link to a file outside were all filed into the project.
The diff opens the source one folder at a time from the vault (or the projects root) with O_NOFOLLOW, refuses `..` and absolute
paths, a non-regular file and a second hard link, and copies from the very file it checked (so a swap after the check, of the
file or of a folder above it, is never filed). A plain inbox/ or drafts/ source still files, identical content onto an existing
file is still a no-op and differing content is still refused.
"""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from guard_small_support import mutants_caught, scratch, in_vault  # noqa: E402
from test_tracker import ABC, make_draft  # noqa: E402

DIFFS = ("tracker-copy-source.diff",)
T = "system/scripts/tracker.py"
MUTATIONS = {
    "dotdot-allowed": ("a `..` part is let through", T, ' or ".." in s.split("/"):', ":"),
    "dirs-followed": ("a folder on the way may be a link", T,
                      'nxt = os.open(part, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | os.O_NOFOLLOW, dir_fd=fd)',
                      'nxt = os.open(part, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0), dir_fd=fd)'),
    "hard-link-allowed": ("a second hard link is let through", T, " or st.st_nlink != 1:", ":"),
    "copy-by-path": ("the copy reads the source again by its path after the check", T,
                     '    with os.fdopen(fd, "rb") as f:\n        data = f.read()\n',
                     '    os.close(fd)\n    data = paths.resolve(op_source(fop, blk)).read_bytes()\n'),
}
DAY = "2026-10-14"
SECRET = "WEBVTT\n\nnot for the project\n"
VTT = "WEBVTT\n\n00:00:01.000 --> 00:00:05.000\n<v Alan Carter>Morning.</v>\n"

# check_file_op on a meeting block whose transcript is each given source; "ok" or the refusal
CHECK = r'''
import tracker
out = {}
for name, src in json.loads(sys.stdin.read()).items():
    blk = {"transcript": src, "draft": src}
    try:
        tracker.check_file_op({"op": "copy", "from": "transcript", "to": "projects/ABC Example Programme/transcripts/x.vtt"}, blk)
        out[name] = "ok"
    except tracker.Invalid as e:
        out[name] = "refused: " + str(e)
print(json.dumps(out))
'''

# _op_copy after a check, with the source (or a folder above it) swapped between the check and the copy, deterministically
SWAP = r'''
import os, shutil, tracker
a = json.loads(sys.stdin.read())
real_open = tracker.open_copy_source
def swapped(stored):
    got = real_open(stored)
    if a["what"] == "file":
        os.unlink(a["src"]); os.symlink(a["target"], a["src"])
    else:
        os.rename(a["dir"], a["dir"] + ".moved"); os.symlink(a["target_dir"], a["dir"])
    return got
tracker.open_copy_source = swapped
blk = {"transcript": a["src"]}
fop = {"op": "copy", "from": "transcript", "to": a["to"]}
try:
    tracker._op_copy(1, fop, blk, [])
    print(json.dumps(open(a["to"]).read()))
except tracker.Invalid as e:
    print(json.dumps("refused: " + str(e)))
'''

# the race: a thread flips the source between a plain file and a link (and a folder above it between a folder and a link)
RACE = r'''
import os, threading, tracker
a = json.loads(sys.stdin.read())
stop = False
def flip():
    while not stop:
        for p, kind in ((a["src"], "file"), (a["dir"], "dir")):
            tmp = p + ".tmp"
            try:
                if kind == "file":
                    os.symlink(a["target"], tmp); os.replace(tmp, p)
                    open(tmp, "w").write(a["plain"]); os.replace(tmp, p)
                else:
                    os.symlink(a["target_dir"], tmp); os.rename(p, p + ".real"); os.rename(tmp, p)
                    os.unlink(p); os.rename(p + ".real", p)
            except OSError:
                pass
t = threading.Thread(target=flip); t.start()
leaks = copies = 0
try:
    for i in range(a["n"]):
        for src in (a["src_rel"], a["nested_rel"]):
            to = "projects/ABC Example Programme/transcripts/race-%d-%d.vtt" % (i, len(src))
            try:
                blk = {"transcript": src}
                tracker.check_file_op({"op": "copy", "from": "transcript", "to": to}, blk)
                tracker._op_copy(1, {"op": "copy", "from": "transcript", "to": to}, blk, [])
                copies += 1
                if "not for the project" in open(to).read():
                    leaks += 1
            except (tracker.Invalid, OSError):
                pass
finally:
    stop = True; t.join()
print(json.dumps({"leaks": leaks, "copies": copies}))
'''


class CopySourceStaysInTheVault(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = scratch(DIFFS, MUTATIONS)
        cls.root = cls.v.root
        cls.outside = Path(tempfile.mkdtemp(prefix="creaite-outside-", dir=cls.root.parent))   # a sibling: reachable by ../
        (cls.outside / "Board pack.vtt").write_text(SECRET)
        (cls.outside / "Plain.vtt").write_text(SECRET)          # no second hard link: only the link on the way refuses it
        inbox = cls.root / "inbox"
        inbox.mkdir(exist_ok=True)
        (inbox / "plain.vtt").write_text(VTT)
        (inbox / "linked").symlink_to(cls.outside, target_is_directory=True)
        os.link(cls.outside / "Board pack.vtt", inbox / "hard.vtt")
        os.mkfifo(inbox / "fifo.vtt")
        (inbox / "folder.vtt").mkdir()
        (cls.root / "system/staging/drafts").mkdir(parents=True, exist_ok=True)
        make_draft(cls.root / "system/staging/drafts" / f"{DAY} Steering committee.docx")

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()
        shutil.rmtree(cls.outside, ignore_errors=True)

    def check(self, sources):
        return in_vault(self.v, CHECK, sources, timeout=60)

    def test_sources_outside_the_vault_are_refused(self):
        rel_out = os.path.relpath(self.outside / "Board pack.vtt", self.root)       # ../creaite-outside-…/Board pack.vtt
        got = self.check({
            "absolute": str(self.outside / "Board pack.vtt"),
            "absolute_in_vault": str(self.root / "inbox/plain.vtt"),
            "dotdot": rel_out,
            "dotdot_from_inbox": "inbox/../" + rel_out,
            "dotdot_inside": "inbox/../inbox/plain.vtt",
            "linked_parent": "inbox/linked/Plain.vtt",
            "hard_link": "inbox/hard.vtt",
            "fifo": "inbox/fifo.vtt",
            "folder": "inbox/folder.vtt",
            "missing": "inbox/nothing.vtt",
            "empty": ""})
        for name, verdict in got.items():
            with self.subTest(name):
                self.assertTrue(verdict.startswith("refused"), f"{name}: {verdict}")
        self.assertIn("not found", got["missing"])

    def test_plain_sources_in_the_vault_pass(self):
        got = self.check({"inbox": "inbox/plain.vtt", "drafts": f"system/staging/drafts/{DAY} Steering committee.docx",
                          "dot": "./inbox/plain.vtt"})
        self.assertEqual(got, {"inbox": "ok", "drafts": "ok", "dot": "ok"})

    def test_a_linked_drafts_folder_is_refused(self):
        """The drafts folder itself swapped for a link to a folder outside: its 'draft' is never filed."""
        d = self.root / "system/staging/drafts"
        os.rename(d, str(d) + ".real")
        try:
            (self.outside / f"{DAY} Steering committee.docx").write_text(SECRET)
            d.symlink_to(self.outside, target_is_directory=True)
            got = self.check({"linked_drafts": f"system/staging/drafts/{DAY} Steering committee.docx"})
        finally:
            if d.is_symlink():
                d.unlink()
            os.rename(str(d) + ".real", d)
        self.assertTrue(got["linked_drafts"].startswith("refused"), got)

    def test_a_meeting_is_still_filed_and_existing_files_kept(self):
        """The whole apply: a plain transcript and the Word draft are filed; the same proposal's copy onto identical content is a
        no-op; a copy onto a file with other content is refused, and that file is kept."""
        tr, filed = f"inbox/{DAY} Steering committee.vtt", f"{ABC}/transcripts/{DAY} Steering committee.vtt"
        (self.root / tr).write_text(VTT)

        def meeting(key, to):
            return {"key": f"fp:{DAY}|steering committee|{key}", "title": "Steering committee", "date": DAY, "projects": ["ABC"],
                    "draft": f"system/staging/drafts/{DAY} Steering committee.docx", "transcript": tr, "minutes_decision": "approved",
                    "file_ops": [{"op": "copy", "from": "draft", "to": f"{ABC}/minutes/{DAY} Steering committee {key}.docx"},
                                 {"op": "copy", "from": "transcript", "to": to}]}
        self.v.propose("m1", [], source_run="cx-minutes", meeting=meeting("a", filed))
        self.v.run("apply")
        self.assertEqual((self.root / filed).read_text(), VTT)
        self.assertTrue((self.root / f"{ABC}/minutes/{DAY} Steering committee a.docx").is_file())
        make_draft(self.root / "system/staging/drafts" / f"{DAY} Steering committee.docx")
        self.v.propose("m2", [], source_run="cx-minutes", meeting=meeting("b", filed))     # same content: nothing to copy
        self.v.run("apply")
        self.assertEqual((self.root / filed).read_text(), VTT)
        other = f"{ABC}/transcripts/{DAY} Other.vtt"
        (self.root / other).write_text("WEBVTT\n\nalready there\n")
        make_draft(self.root / "system/staging/drafts" / f"{DAY} Steering committee.docx")
        self.v.propose("m3", [], source_run="cx-minutes", meeting=meeting("c", other))
        r = self.v.run("apply", ok=False)
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual((self.root / other).read_text(), "WEBVTT\n\nalready there\n")

    def test_a_swap_after_the_check_is_never_filed(self):
        """Deterministic: the source (or the folder above it) is swapped for a link to the outside file right after it was checked
        and opened; what is filed is what was checked."""
        sub = self.root / "inbox/sub"
        sub.mkdir(exist_ok=True)
        (sub / "x.vtt").write_text(VTT)
        (self.root / "inbox/y.vtt").write_text(VTT)
        to1, to2 = (f"{ABC}/transcripts/swap-{n}.vtt" for n in (1, 2))
        got_file = in_vault(self.v, SWAP, {"what": "file", "src": "inbox/y.vtt", "target": str(self.outside / "Board pack.vtt"),
                                            "to": to1}, timeout=60)
        got_dir = in_vault(self.v, SWAP, {"what": "dir", "src": "inbox/sub/x.vtt", "dir": str(sub), "target_dir": str(self.outside),
                                           "to": to2}, timeout=60)
        self.assertEqual(got_file, VTT)                     # filed, and what was filed is the plain file that was checked
        self.assertEqual(got_dir, VTT)

    def test_the_race_leaks_nothing(self):
        """3,000 rounds with a thread flipping the source between a plain file and a link, and a folder above another source
        between a folder and a link (as Team Cap's copy-link race): no outside content is ever filed."""
        racedir = self.root / "inbox/racedir"
        racedir.mkdir(exist_ok=True)
        (racedir / "Board pack.vtt").write_text(VTT)
        (self.root / "inbox/race.vtt").write_text(VTT)
        got = in_vault(self.v, RACE, {"src": str(self.root / "inbox/race.vtt"), "dir": str(racedir), "plain": VTT,
                                       "target": str(self.outside / "Board pack.vtt"), "target_dir": str(self.outside),
                                       "src_rel": "inbox/race.vtt", "nested_rel": "inbox/racedir/Board pack.vtt",
                                       "n": int(os.environ.get("GUARD_SMALL_RACE", "3000"))}, timeout=900)
        self.assertEqual(got["leaks"], 0, got)
        self.assertGreater(got["copies"], 0, got)          # the plain file was filed in between: the race was run


@unittest.skipIf(os.environ.get("GUARD_SMALL_MUTATE") or os.environ.get("GUARD_SMALL_UNPATCHED"), "the mutation run itself")
class Mutants(unittest.TestCase):
    def test_every_mutation_is_caught(self):
        missed = mutants_caught(Path(__file__), MUTATIONS, ["test_sources_outside", "test_a_swap_after", "test_a_linked_drafts"])
        self.assertEqual(missed, [], "mutations the tests didn't notice")


if __name__ == "__main__":
    unittest.main()
