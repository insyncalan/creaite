"""guard-small (1), #269 round 2 delta LOW 1 (and its round 2 review): `tracker.py apply` files a copy's source only from inbox/,
system/staging/drafts/ or the projects folder, only a plain file with one link, and only what it checked. PROPOSAL test for
dev/proposals/guard-small/tracker-copy-source.diff (tracker.py is a guarded file: Alan approves it).

Run: python3 dev/tests/test_guard_small_copy_source.py
Fail-first: GUARD_SMALL_UNPATCHED=1 python3 dev/tests/test_guard_small_copy_source.py     (the copy is left without the diff)
GUARD_SMALL_RACE=<n> sets the race rounds (3,000 by default).

Before the diff, `check_file_op` and `_op_copy` looked only at the last part of the source for a link: an absolute `from` outside
the vault, a `../` path, a source under a symlinked folder and a hard link to a file outside were all filed into the project.
Round 2 (the review of e7435aaa): the link count read from the open file could be beaten by swapping the vault name away right
after the open (the outside file's count drops back to 1: 50 leaks in 3,000 rounds); a NUL in the path raised ValueError (and
crashed every apply in card_op_problem); mode and times were set on the destination's path; a failed write left a partial
destination; sockets and long names were called links; the whole file was read into memory; any vault file (system/tracker.db,
.claude/settings.json) was accepted as a source.
"""
import os
import shutil
import socket
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from guard_small_support import in_vault, mutants_caught, scratch  # noqa: E402
from test_tracker import ABC, make_draft  # noqa: E402

DIFFS = ("tracker-copy-source.diff",)
T = "system/scripts/tracker.py"
MUTATIONS = {
    "dotdot-allowed": ("a `..` part is let through", T, ' or ".." in s.split("/"):', ":"),
    "dirs-followed": ("a folder on the way may be a link", T,
                      'nxt = os.open(part, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | os.O_NOFOLLOW, dir_fd=self.dirfd)',
                      'nxt = os.open(part, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0), dir_fd=self.dirfd)'),
    "hard-link-allowed": ("a second hard link is let through", T, " or st.st_nlink != 1 or now.st_nlink != 1:", ":"),
    "no-same-inode": ("the name isn't required to be the opened file", T,
                      "        if (now.st_dev, now.st_ino) != (st.st_dev, st.st_ino) or st.st_nlink", "        if st.st_nlink"),
    "no-recheck-after-read": ("the name isn't checked again after the read", T,
                              "            out.flush()\n            src.check_name()", "            out.flush()"),
    "copy-by-path": ("the copy reads the source again by its path", T,
                     "            for c in src.chunks():\n                h.update(c)\n                out.write(c)",
                     "            for c in [paths.resolve(src.stored).read_bytes()]:\n                h.update(c)\n                out.write(c)"),
    "any-vault-file": ("any vault file is a source", T, "        if ask or not any(", "        if ask or False and not any("),
    "ask-case-sensitive": ("uploads/ask is matched by its exact spelling only", T, '        ask = _apfs_folded(top[:4]) == ("system",',
                           '        ask = top[:4] == ("system",'),
    "ask-inode-dropped": ("the folder on the way isn't compared with uploads/ask", T,
                          "                if ask and (st.st_dev, st.st_ino) == ask:", "                if False:"),
    "fallback-overwrites": ("the no-link fallback writes over a file that appeared", T,
                            "os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW", "os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW"),
    "nul-crash": ("a NUL reaches the os calls", T, '        if not s or "\\x00" in s:', "        if not s:"),
    "temp-left": ("a failed write leaves its temporary file", T,
                  "        if os.path.lexists(tmp):\n            os.unlink(tmp)\n        raise", "        raise"),
    "chmod-by-path": ("the destination's mode is set by its path after it is placed", T,
                      "        os.unlink(tmp)\n        return h.hexdigest()",
                      "        os.unlink(tmp)\n        os.chmod(dst, stat.S_IMODE(src.st.st_mode))\n        return h.hexdigest()"),
}
DAY = "2026-10-14"
SECRET = "WEBVTT\n\nnot for the project\n"
VTT = "WEBVTT\n\n00:00:01.000 --> 00:00:05.000\n<v Alan Carter>Morning.</v>\n"
TR = f"{ABC}/transcripts"

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

# One _op_copy with something done at a set moment: "after_open" (the name, or a folder above it, swapped once the source is
# open and checked), "in_open" (the name swapped right after the file itself is opened, before its checks), "in_read" (the file
# grows while it is read), "fail_write" (the disk fills after the first chunk). Returns what was filed, or the refusal, and what
# the destination's folder holds; with "paths", the chmod and utime calls made on a path.
ONE = r'''
import errno, os, tracker
a = json.loads(sys.stdin.read())
def swap():
    if a["swap"] == "file_link":
        os.unlink(a["src"]); os.symlink(a["target"], a["src"])
    elif a["swap"] == "dir_link":
        os.rename(a["dir"], a["dir"] + ".moved"); os.symlink(a["target_dir"], a["dir"])
    elif a["swap"] == "unlink_hard":                       # the vault name of a hard link goes; a plain file takes its place
        os.unlink(a["src"]); open(a["src"], "w").write("WEBVTT\n\nplain\n")
if a["when"] == "after_open":
    real_open = tracker.open_copy_source
    def wrapped(stored):
        got = real_open(stored); swap(); return got
    tracker.open_copy_source = wrapped
elif a["when"] == "in_open":
    real_os_open = os.open
    def os_open(path, flags, *rest, **kw):
        fd = real_os_open(path, flags, *rest, **kw)
        if path == os.path.basename(a["src"]) and "dir_fd" in kw:
            swap()
        return fd
    os.open = os_open
elif a["when"] == "link_fails":                        # a file system without hard links (FAT): the fallback
    def no_link(*x, **k):
        if a.get("appear"):
            open(a["to"], "w").write("already here\n")      # a file appears in the window before the fallback writes
        raise OSError(errno.EPERM, "Operation not permitted")
    os.link = no_link
elif a["when"] in ("in_read", "fail_write"):
    real_chunks = tracker.CopySource.chunks
    def chunks(self):
        for n, c in enumerate(real_chunks(self)):
            yield c
            if a["when"] == "in_read" and n == 0:
                open(a["src"], "a").write("more\n")
            elif a["when"] == "fail_write":
                raise OSError(errno.ENOSPC, "No space left on device")
    tracker.CopySource.chunks = chunks
calls = []
if a.get("paths"):
    for fn in ("chmod", "utime"):
        def spy(p, *r, _real=getattr(os, fn), _fn=fn, **k):
            if not isinstance(p, int):
                calls.append(_fn)
            return _real(p, *r, **k)
        setattr(os, fn, spy)
blk = {"transcript": a["src_rel"]}
try:
    tracker._op_copy(1, {"op": "copy", "from": "transcript", "to": a["to"]}, blk, [])
    got = open(a["to"]).read()
except (tracker.Invalid, OSError) as e:
    got = "refused: " + str(e)
folder = os.path.dirname(a["to"])
st = os.stat(a["to"]) if os.path.exists(a["to"]) else None
print(json.dumps({"got": got, "left": sorted(os.listdir(folder)) if os.path.isdir(folder) else [], "paths": calls,
                  "mode": oct(st.st_mode & 0o777) if st else None}))
'''

# the race: a thread cycles the source's name between a plain file, a hard link to the outside file and a FIFO (each by an
# atomic rename), and a folder above a second source between a folder and a link; every filed copy is read back
RACE = r'''
import os, threading, tracker
a = json.loads(sys.stdin.read())
stop = False
def put(p, kind):
    tmp = p + ".tmp"
    try:
        if os.path.lexists(tmp):
            os.unlink(tmp)
        if kind == "plain":
            open(tmp, "w").write(a["plain"])
        elif kind == "hard":
            os.link(a["target"], tmp)
        elif kind == "fifo":
            os.mkfifo(tmp)
        else:
            os.symlink(a["target"], tmp)
        os.replace(tmp, p)
    except OSError:
        pass
def flip():
    while not stop:
        for kind in ("plain", "hard", "plain", "fifo", "plain", "link"):
            put(a["src"], kind)
        try:
            os.symlink(a["target_dir"], a["dir"] + ".tmp"); os.rename(a["dir"], a["dir"] + ".real"); os.rename(a["dir"] + ".tmp", a["dir"])
            os.unlink(a["dir"]); os.rename(a["dir"] + ".real", a["dir"])
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
        for n in ("Board pack.vtt", "Plain.vtt", "x.vtt", "Hard.vtt", "Race.vtt"):
            (cls.outside / n).write_text(SECRET)
        inbox = cls.root / "inbox"
        inbox.mkdir(exist_ok=True)
        (inbox / "plain.vtt").write_text(VTT)
        (inbox / "linked").symlink_to(cls.outside, target_is_directory=True)
        os.link(cls.outside / "Board pack.vtt", inbox / "hard.vtt")
        os.mkfifo(inbox / "fifo.vtt")
        (inbox / "folder.vtt").mkdir()
        here = os.getcwd()
        try:
            os.chdir(inbox)
            cls.sock = socket.socket(socket.AF_UNIX)
            cls.sock.bind("sock.vtt")
        finally:
            os.chdir(here)
        (cls.root / "system/staging/drafts").mkdir(parents=True, exist_ok=True)
        make_draft(cls.root / "system/staging/drafts" / f"{DAY} Steering committee.docx")
        (cls.root / TR).mkdir(parents=True, exist_ok=True)
        (cls.root / TR / "already.vtt").write_text(VTT)
        (cls.root / "system/staging/uploads/ask").mkdir(parents=True, exist_ok=True)
        (cls.root / "system/staging/uploads/plan.png").write_bytes(b"\x89PNG")              # a Current state image (BL-63)
        (cls.root / "system/staging/uploads/ask/0123456789abcdef.png").write_bytes(b"\x89PNG")
        (cls.root / "system/staging/uploads/asklink").symlink_to(cls.root / "system/staging/uploads/ask", target_is_directory=True)
        os.link(cls.root / "system/staging/uploads/ask/0123456789abcdef.png", cls.root / "system/staging/uploads/hard-ask.png")

    @classmethod
    def tearDownClass(cls):
        cls.sock.close()
        cls.v.cleanup()
        shutil.rmtree(cls.outside, ignore_errors=True)

    def check(self, sources):
        return in_vault(self.v, CHECK, sources, timeout=60)

    def one(self, **a):
        return in_vault(self.v, ONE, a, timeout=120)

    def test_sources_outside_the_allowed_places_are_refused(self):
        rel_out = os.path.relpath(self.outside / "Plain.vtt", self.root)       # ../creaite-outside-…/Plain.vtt
        got = self.check({
            "absolute": str(self.outside / "Plain.vtt"),
            "absolute_in_vault": str(self.root / "inbox/plain.vtt"),
            "dotdot": rel_out,
            "dotdot_from_inbox": "inbox/../" + rel_out,
            "dotdot_inside": "inbox/../inbox/plain.vtt",
            "linked_parent": "inbox/linked/Plain.vtt",
            "hard_link": "inbox/hard.vtt",
            "fifo": "inbox/fifo.vtt",
            "socket": "inbox/sock.vtt",
            "folder": "inbox/folder.vtt",
            "missing": "inbox/nothing.vtt",
            "nul": "inbox/plain.vtt\x00x",
            "long": "inbox/" + "a" * 300 + ".vtt",
            "empty": "",
            "tracker_db": "system/tracker.db",
            "settings": "system/config/settings.json",
            "claude_settings": ".claude/settings.json",
            "inbox_itself": "inbox",
            "staging_proposal": "system/staging/applied/x.json",
            "ask_upload": "system/staging/uploads/ask/0123456789abcdef.png",
            "ask_upper": "system/staging/uploads/ASK/0123456789abcdef.png",
            "ask_title": "system/staging/uploads/Ask/0123456789abcdef.png",
            "ask_mixed": "system/staging/uploads/aSk/0123456789abcdef.png",
            "ask_linked": "system/staging/uploads/asklink/0123456789abcdef.png",
            "ask_hard": "system/staging/uploads/hard-ask.png"})
        for name, verdict in got.items():
            with self.subTest(name):
                self.assertTrue(verdict.startswith("refused"), f"{name}: {verdict}")
        self.assertIn("not found", got["missing"])
        self.assertIn("not found", got["nul"])
        self.assertIn("not a regular file", got["socket"])
        self.assertIn("not a regular file", got["fifo"])
        self.assertIn("too long", got["long"])
        for k in ("ask_upload", "ask_upper", "ask_title", "ask_mixed"):      # APFS: any spelling is the same folder
            self.assertIn("filed only from", got[k], k)

    def test_the_ask_folder_is_refused_by_what_it_is(self):
        """Whatever the name says, a folder on the way that is uploads/ask/ (same device and inode) is refused: shown by pointing
        the check at the drafts folder."""
        code = ("import paths, tracker\n"
                "paths.ASK_UPLOADS = paths.DRAFTS\n"
                "try:\n"
                "    tracker.open_copy_source('system/staging/drafts/%s').close(); print(json.dumps('ok'))\n"
                "except tracker.Invalid as e:\n"
                "    print(json.dumps('refused: ' + str(e)))" % f"{DAY} Steering committee.docx")
        got = in_vault(self.v, code, timeout=60)
        self.assertIn("chat images are never filed", got)

    def test_plain_sources_in_the_allowed_places_pass(self):
        got = self.check({"inbox": "inbox/plain.vtt", "drafts": f"system/staging/drafts/{DAY} Steering committee.docx",
                          "dot": "./inbox/plain.vtt", "project": f"{TR}/already.vtt", "upload": "system/staging/uploads/plan.png"})
        self.assertEqual(set(got.values()), {"ok"}, got)

    def test_a_projects_root_outside_the_vault_is_a_place_too(self):
        """BL-85: with locations.projects_root outside the vault, a file in an engagement folder there is a source; a link in it
        isn't."""
        proot = Path(tempfile.mkdtemp(prefix="creaite-proot-", dir=self.root.parent))
        try:
            (proot / "Example/transcripts").mkdir(parents=True)
            (proot / "Example/transcripts/a.vtt").write_text(VTT)
            (proot / "Example/linked").symlink_to(self.outside, target_is_directory=True)
            code = ("import paths, tracker\n"
                    "s = json.loads(paths.SETTINGS.read_text()) if paths.SETTINGS.exists() else {}\n"
                    "s.setdefault('locations', {})['projects_root'] = json.loads(sys.stdin.read())\n"
                    "paths.SETTINGS.write_text(json.dumps(s))\n"
                    "out = {}\n"
                    "for k, src in (('ok', 'projects/Example/transcripts/a.vtt'), ('link', 'projects/Example/linked/Plain.vtt')):\n"
                    "    try:\n"
                    "        tracker.open_copy_source(src).close(); out[k] = 'ok'\n"
                    "    except tracker.Invalid as e:\n"
                    "        out[k] = 'refused: ' + str(e)\n"
                    "s['locations']['projects_root'] = ''; paths.SETTINGS.write_text(json.dumps(s))\n"
                    "print(json.dumps(out))")
            got = in_vault(self.v, code, str(proot), timeout=60)
        finally:
            shutil.rmtree(proot, ignore_errors=True)
        self.assertEqual(got["ok"], "ok", got)
        self.assertTrue(got["link"].startswith("refused"), got)

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
        tr, filed = f"inbox/{DAY} Steering committee.vtt", f"{TR}/{DAY} Steering committee.vtt"
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
        other = f"{TR}/{DAY} Other.vtt"
        (self.root / other).write_text("WEBVTT\n\nalready there\n")
        make_draft(self.root / "system/staging/drafts" / f"{DAY} Steering committee.docx")
        self.v.propose("m3", [], source_run="cx-minutes", meeting=meeting("c", other))
        r = self.v.run("apply", ok=False)
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual((self.root / other).read_text(), "WEBVTT\n\nalready there\n")
        (self.root / "system/staging/proposed-m3.json").unlink()

    def test_a_nul_source_is_refused_and_later_applies_still_run(self):
        """A NUL in a copy's source is 'source not found' at apply (never a crash in card_op_problem), and once that proposal is
        gone the next apply runs."""
        m = {"key": "fp:nul", "title": "T", "date": DAY, "projects": ["ABC"], "transcript": "inbox/a\x00b.vtt",
             "minutes_decision": "approved", "file_ops": [{"op": "copy", "from": "transcript", "to": f"{TR}/nul.vtt"}]}
        self.v.propose("nul", [], source_run="cx-minutes", meeting=m)
        r = self.v.run("apply", ok=False)
        said = r.stdout + r.stderr
        self.assertNotIn("Traceback", said)
        self.assertIn("source not found", said)
        (self.root / "system/staging/proposed-nul.json").unlink()
        self.assertEqual(self.v.run("apply", ok=False).returncode, 0)

    def test_a_swap_after_the_check_is_never_filed(self):
        """Deterministic: the source, or the folder above it, swapped for a link right after it was opened and checked: what is
        filed (if anything) is the plain file that was checked, never the outside file."""
        sub = self.root / "inbox/sub"
        sub.mkdir(exist_ok=True)
        (sub / "x.vtt").write_text(VTT)
        (self.root / "inbox/y.vtt").write_text(VTT)
        f = self.one(when="after_open", swap="file_link", src=str(self.root / "inbox/y.vtt"), src_rel="inbox/y.vtt",
                     target=str(self.outside / "Board pack.vtt"), to=f"{TR}/swap-1.vtt")
        d = self.one(when="after_open", swap="dir_link", src=str(sub / "x.vtt"), src_rel="inbox/sub/x.vtt", dir=str(sub),
                     target_dir=str(self.outside), to=f"{TR}/swap-2.vtt")
        for got in (f, d):
            self.assertNotIn("not for the project", got["got"], got)
        self.assertEqual(d["got"], VTT)              # the folder held open is the one read: filed as checked

    def test_a_hard_link_whose_vault_name_goes_after_the_open_is_refused(self):
        """Deterministic, the review's race: the name is a hard link to an outside file when it is opened; it is then replaced by
        a plain file, so the open file's link count is 1 again. The name no longer being that file refuses it."""
        h = self.root / "inbox/h.vtt"
        os.link(self.outside / "Hard.vtt", h)
        got = self.one(when="in_open", swap="unlink_hard", src=str(h), src_rel="inbox/h.vtt", to=f"{TR}/hard-1.vtt")
        self.assertNotIn("not for the project", got["got"], got)
        self.assertTrue(got["got"].startswith("refused"), got)

    def test_a_source_that_changes_while_it_is_read_is_refused(self):
        (self.root / "inbox/grow.vtt").write_text(VTT)
        got = self.one(when="in_read", src=str(self.root / "inbox/grow.vtt"), src_rel="inbox/grow.vtt", to=f"{TR}/grow.vtt")
        self.assertTrue(got["got"].startswith("refused"), got)
        self.assertNotIn("grow.vtt", got["left"])

    def test_a_failed_write_leaves_nothing_and_a_retry_files_it(self):
        (self.root / "inbox/full.vtt").write_text(VTT * 10)
        got = self.one(when="fail_write", src=str(self.root / "inbox/full.vtt"), src_rel="inbox/full.vtt", to=f"{TR}/full.vtt")
        self.assertTrue(got["got"].startswith("refused"), got)
        self.assertEqual([n for n in got["left"] if n == "full.vtt" or n.startswith(".creaite-copy-")], [], got)
        again = self.one(when="", src=str(self.root / "inbox/full.vtt"), src_rel="inbox/full.vtt", to=f"{TR}/full.vtt")
        self.assertEqual(again["got"], VTT * 10)

    def test_without_hard_links_the_copy_is_made_exclusively(self):
        """os.link failing (no hard links): the copy is still filed, mode kept, no temporary file left; a file that appears in
        the window before the fallback writes is kept and the copy refused."""
        src = self.root / "inbox/nolink.vtt"
        src.write_text(VTT)
        os.chmod(src, 0o640)
        ok = self.one(when="link_fails", src=str(src), src_rel="inbox/nolink.vtt", to=f"{TR}/nolink-1.vtt")
        self.assertEqual((ok["got"], ok["mode"]), (VTT, "0o640"), ok)
        self.assertEqual([n for n in ok["left"] if n.startswith(".creaite-copy-")], [], ok)
        raced = self.one(when="link_fails", appear=True, src=str(src), src_rel="inbox/nolink.vtt", to=f"{TR}/nolink-2.vtt")
        self.assertTrue(raced["got"].startswith("refused"), raced)
        self.assertEqual((self.root / TR / "nolink-2.vtt").read_text(), "already here\n")
        self.assertEqual([n for n in raced["left"] if n.startswith(".creaite-copy-")], [], raced)

    def test_mode_and_times_are_set_on_the_file_never_by_path(self):
        src = self.root / "inbox/mode.vtt"
        src.write_text(VTT)
        os.chmod(src, 0o640)
        got = self.one(when="", paths=True, src=str(src), src_rel="inbox/mode.vtt", to=f"{TR}/mode.vtt")
        self.assertEqual(got["got"], VTT)
        self.assertEqual(got["mode"], "0o640")
        self.assertEqual(got["paths"], [], "chmod or utime called with a path")
        self.assertEqual(os.stat(self.root / TR / "mode.vtt").st_mtime_ns, os.stat(src).st_mtime_ns)

    def test_the_race_leaks_nothing(self):
        """3,000 rounds with a thread cycling the source between a plain file, a hard link to the outside file, a FIFO and a
        link, and a folder above a second source between a folder and a link: no outside content is ever filed."""
        racedir = self.root / "inbox/racedir"
        racedir.mkdir(exist_ok=True)
        (racedir / "Race.vtt").write_text(VTT)
        (self.root / "inbox/race.vtt").write_text(VTT)
        got = in_vault(self.v, RACE, {"src": str(self.root / "inbox/race.vtt"), "dir": str(racedir), "plain": VTT,
                                       "target": str(self.outside / "Race.vtt"), "target_dir": str(self.outside),
                                       "src_rel": "inbox/race.vtt", "nested_rel": "inbox/racedir/Race.vtt",
                                       "n": int(os.environ.get("GUARD_SMALL_RACE", "3000"))}, timeout=1200)
        print(f"\nrace: {got}", file=sys.stderr)
        self.assertEqual(got["leaks"], 0, got)
        self.assertGreater(got["copies"], 0, got)          # the plain file was filed in between: the race was run


@unittest.skipIf(os.environ.get("GUARD_SMALL_MUTATE") or os.environ.get("GUARD_SMALL_UNPATCHED"), "the mutation run itself")
class Mutants(unittest.TestCase):
    def test_every_mutation_is_caught(self):
        missed = mutants_caught(Path(__file__), MUTATIONS, ["test_sources_outside", "test_a_swap_after", "test_a_linked_drafts",
                                                           "test_a_hard_link_whose", "test_a_source_that_changes", "test_a_nul",
                                                           "test_a_failed_write", "test_mode_and_times", "test_the_ask_folder",
                                                           "test_without_hard_links"])
        self.assertEqual(missed, [], "mutations the tests didn't notice")


if __name__ == "__main__":
    unittest.main()
