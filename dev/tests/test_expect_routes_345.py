"""2.6.4 (#345): `expect` (the item's 12-hex fingerprint) on every route that decides an item, on a real live server over a
throwaway copy. 2.6.3 made it required at POST /api/review; this covers the five that decided by (file, ref) alone: /api/review/reject,
/api/review/rejected (approve instead), /api/review/repeat, /api/review/retarget and /api/minutes/approve.

The guarded diff (dev/proposals/345/live_server.diff) is applied to the throwaway copy when this tree lacks it, so the tests are the
same either way. For each route: no fingerprint declines the whole request in plain words and changes nothing; a malformed one or one
for a different item (the list moved on) the same; the right one goes through to review.py. A request with several rows is all or
none. review.py's own commands (ask creaite, the Excel import) never use these routes and still work without it. Mutants: the check
taken out of each route in turn, and out of the shared helper, turn the matching test red.

Run: python3 dev/tests/test_expect_routes_345.py
"""
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system/scripts"))
from test_tracker import Vault  # noqa: E402
import build_dashboard  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DIFF = ROOT / "dev/proposals/345/live_server.diff"
HAS_DIFF = "def expect_refusal" in (ROOT / "system/scripts/live_server.py").read_text()
MISSING = "This page didn't say which item it meant"
CHANGED = "has changed since you looked at it"
BAD = "can't check which item that is"

MUTANTS = {          # the line each route runs, and what stands in for it
    "reject": ("why = rows_refusal(found)", "why = None"),
    "approve-instead": ('why = expect_refusal([(r.get("file"), key_ref(k), r.get("expect")) for r, k in zip(rows, keys)])', "why = None"),
    "repeat": ('        why = expect_refusal([(req.get("file"), req.get("ref"), req.get("expect"))])          # 2.6.4 (#345)\n',
               "        why = None\n"),
    "retarget": ('        why = expect_refusal([(req.get("file"), req.get("ref"), req.get("expect"))])          # 2.6.4 (#345); an undo',
                 "        why = None  # 2.6.4 (#345); an undo"),
    "minutes": ('why = expect_refusal([(req.get("file"), "meeting", req.get("expect"))]) if pending_file(req.get("file")) else None',
                "why = None"),
    "minutes-skip": ('if pending_file(req.get("file")) else None', 'if current_fp(req.get("file"), "meeting") else None'),
}


def action(n, text):
    return {"n": n, "op": "new", "table": "actions", "match": "strong", "flags": [], "decision": "pending",
            "values": {"project": "ABC", "description": text, "owner": "Alan Carter", "due_date": "2027-01-15",
                       "source": "projects/ABC Example/minutes/2026-10-01 Steering.docx — Actions"}}


class Server:
    def __init__(self, mutate=None, helper_mutant=False):
        self.home = Path(tempfile.mkdtemp(prefix="creaite-e345-")).resolve()
        self.v = Vault()
        d = self.v.root
        subprocess.run(["git", "init", "-q", str(d)], check=True)
        if not HAS_DIFF:
            subprocess.run(["git", "apply", str(DIFF)], cwd=d, check=True)
        f = d / "system/scripts/live_server.py"
        t = f.read_text()
        if helper_mutant:                                  # the shared check always says yes
            old = "    if any(e is None for _, _, e in rows):\n"
            assert old in t
            f.write_text(t.replace(old, "    return None\n" + old, 1))
        elif mutate:
            old, new = MUTANTS[mutate]
            assert old in t, mutate
            f.write_text(t.replace(old, new, 1))
        self.v.run("init")
        (d / ".creaite-dev").unlink(missing_ok=True)
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        self.base = f"http://127.0.0.1:{self.port}"
        env = {**os.environ, "HOME": str(self.home), "CREAITE_PORT": str(self.port), "CREAITE_NO_LAUNCHCTL": "1", "CREAITE_NO_LAUNCH": "1"}
        self.proc = subprocess.Popen([sys.executable, str(d / "system/scripts/live_server.py")], env=env,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(150):
            try:
                urllib.request.urlopen(self.base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        html = urllib.request.urlopen(self.base + "/").read().decode()
        self.token = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]
        self.n = 0

    def close(self):
        self.proc.terminate()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        self.v.cleanup()
        shutil.rmtree(self.home, ignore_errors=True)

    def post(self, path, **body):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST", headers={
            "Content-Type": "application/json", "X-Creaite-Token": self.token, "Sec-Fetch-Site": "same-origin", "Origin": self.base})
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            with e:
                return json.loads(e.read() or b"{}")

    def stage(self):
        self.n += 1
        return self.v.propose(f"2026-10-21-09{self.n:02d}-r", [action(1, "Alpha item"), action(2, "Bravo item"), action(3, "Charlie item")]).name

    def path(self, name):
        return self.v.root / "system/staging" / name

    def data(self, name):
        return json.loads(self.path(name).read_text())

    def fp(self, name, ref):
        d = self.data(name)
        return build_dashboard.block_fp(d[ref]) if isinstance(ref, str) else build_dashboard.item_fp(next(i for i in d["items"] if i["n"] == ref))

    def decisions(self, name):
        return {i["n"]: i["decision"] for i in self.data(name)["items"]}

    def take_out(self, name, text):
        d = self.data(name)
        d["items"] = [i for i in d["items"] if i["values"]["description"] != text]
        for k, it in enumerate(d["items"], 1):
            it["n"] = k
        self.path(name).write_text(json.dumps(d))

    def stage_minutes(self):
        self.n += 1
        name = f"proposed-2026-10-21-09{self.n:02d}-m.json"
        self.path(name).write_text(json.dumps({
            "created": "2026-10-21T09:00:00", "source_run": "cx-minutes", "files": [],
            "meeting": {"key": "abc-steering-2026-10-21", "title": "Steering", "project": "ABC", "projects": ["ABC"], "date": "2026-10-21",
                        "draft": "system/staging/drafts/2026-10-21 Steering.html", "minutes_decision": "pending", "file_ops": []},
            "items": [action(1, "Alpha item")]}))
        return name


def plain(message):
    return not re.search(r"Traceback|\.py\b|/|proposed-|\bapply\b|\bproposal\b|\bstaged?\b", message or "")


class Decline:
    """What a declined request looks like, whichever route: not ok, one of the three plain messages, nothing written."""

    def check(self, r, which):
        self.assertFalse(r.get("ok"), r)
        self.assertIn(which, r.get("message", ""), r)
        self.assertTrue(plain(r["message"]), r)


class Routes(unittest.TestCase, Decline):
    @classmethod
    def setUpClass(cls):
        cls.s = Server()

    @classmethod
    def tearDownClass(cls):
        cls.s.close()

    # ── reject ─────────────────────────────────────────────────────────────────
    def test_reject_without_expect_declines_the_whole_request(self):
        s = self.s
        name = s.stage()
        rows = [{"file": name, "ref": 1, "expect": s.fp(name, 1)}, {"file": name, "ref": 2}]       # one row has none
        r = s.post("/api/review/reject", rows=rows, reason="Chatter")
        self.check(r, MISSING)
        self.assertEqual(r.get("rejected"), [])
        self.assertEqual(s.decisions(name), {1: "pending", 2: "pending", 3: "pending"})

    def test_reject_with_a_malformed_or_other_items_expect_declines_everything(self):
        s = self.s
        name = s.stage()
        alpha, bravo = s.fp(name, 1), s.fp(name, 2)
        for bad, which in (("Bravo item", BAD), ("", BAD), (7, BAD), ("ABCDEF123456", BAD), (alpha, CHANGED)):
            r = s.post("/api/review/reject", rows=[{"file": name, "ref": 2, "expect": bad}, {"file": name, "ref": 3, "expect": s.fp(name, 3)}],
                       reason="Chatter")
            self.check(r, which)
        self.assertEqual(s.decisions(name), {1: "pending", 2: "pending", 3: "pending"})
        self.assertNotEqual(alpha, bravo)

    def test_reject_with_the_right_expect_rejects_those_rows_only(self):
        s = self.s
        name = s.stage()
        r = s.post("/api/review/reject", rows=[{"file": name, "ref": 1, "expect": s.fp(name, 1)}, {"file": name, "ref": 3, "expect": s.fp(name, 3)},
                                               {"file": "proposed-gone.json", "ref": 1}], reason="Chatter")
        self.assertTrue(r.get("ok"), r)
        self.assertEqual(s.decisions(name), {1: "rejected", 2: "pending", 3: "rejected"})
        self.assertEqual(r["gone"], [{"file": "proposed-gone.json", "ref": 1}])           # a row that is gone needs no fingerprint

    def test_reject_after_the_list_moved_on_declines(self):
        s = self.s
        name = s.stage()
        bravo = s.fp(name, 2)
        s.take_out(name, "Alpha item")                       # Bravo is item 1 now; ref 2 is Charlie
        r = s.post("/api/review/reject", rows=[{"file": name, "ref": 2, "expect": bravo}], reason="Chatter")
        self.check(r, CHANGED)
        self.assertEqual(s.decisions(name), {1: "pending", 2: "pending"})

    # ── approve instead ────────────────────────────────────────────────────────
    def rejected(self, s):
        name = s.stage()
        fp = s.fp(name, 2)
        r = s.post("/api/review/reject", rows=[{"file": name, "ref": 2, "expect": fp}], reason="Chatter")
        self.assertTrue(r.get("ok"), r)
        self.assertEqual(s.decisions(name)[2], "rejected")
        return name, fp

    def test_approve_instead_needs_the_items_expect(self):
        s = self.s
        name, fp = self.rejected(s)
        for row, which in (({"file": name, "ref": 2}, MISSING), ({"file": name, "ref": 2, "expect": "nope"}, BAD),
                           ({"file": name, "ref": 2, "expect": s.fp(name, 1)}, CHANGED)):
            self.check(s.post("/api/review/rejected", rows=[row], how="approve"), which)
            self.assertEqual(s.decisions(name)[2], "rejected")
        r = s.post("/api/review/rejected", rows=[{"file": name, "ref": 2, "expect": fp}], how="approve")
        self.assertTrue(r.get("ok"), r)
        self.assertEqual(s.decisions(name)[2], "approved")

    def test_undo_and_a_changed_reason_need_no_expect(self):
        s = self.s
        name, _ = self.rejected(s)
        r = s.post("/api/review/rejected", rows=[{"file": name, "ref": 2}], how="reason", reason="Duplicate", duplicate_of="")
        self.assertNotIn(MISSING, json.dumps(r))
        r = s.post("/api/review/rejected", rows=[{"file": name, "ref": 2}], how="undo")
        self.assertTrue(r.get("ok"), r)
        self.assertEqual(s.decisions(name)[2], "pending")

    def test_approve_instead_with_several_rows_is_all_or_none(self):
        s = self.s
        name = s.stage()
        r = s.post("/api/review/reject", rows=[{"file": name, "ref": k, "expect": s.fp(name, k)} for k in (1, 2)], reason="Chatter")
        self.assertTrue(r.get("ok"), r)
        r = s.post("/api/review/rejected", how="approve", rows=[{"file": name, "ref": 1, "expect": s.fp(name, 1)}, {"file": name, "ref": 2}])
        self.check(r, MISSING)
        self.assertEqual(s.decisions(name), {1: "rejected", 2: "rejected", 3: "pending"})

    # ── repeat and retarget ────────────────────────────────────────────────────
    def test_repeat_and_retarget_need_the_items_expect_and_decide_nothing_without_it(self):
        s = self.s
        name = s.stage()
        before = s.path(name).read_bytes()
        for path, extra in (("/api/review/repeat", {"how": "keep"}), ("/api/review/repeat", {"how": "merge"}),
                            ("/api/review/retarget", {"id": "ABC-A-001"})):
            self.check(s.post(path, file=name, ref=2, **extra), MISSING)
            self.check(s.post(path, file=name, ref=2, expect="zz", **extra), BAD)
            self.check(s.post(path, file=name, ref=2, expect=s.fp(name, 1), **extra), CHANGED)
        self.assertEqual(s.path(name).read_bytes(), before)

    def test_repeat_and_retarget_with_the_right_expect_reach_review(self):
        s = self.s
        name = s.stage()
        for path, extra in (("/api/review/repeat", {"how": "keep"}), ("/api/review/retarget", {"id": "ABC-A-001"})):
            r = s.post(path, file=name, ref=2, expect=s.fp(name, 2), **extra)
            for words in (MISSING, CHANGED, BAD):
                self.assertNotIn(words, r.get("message", ""), (path, r))          # review.py answers (here: not a repeat, no such item)
            self.assertFalse(r.get("ok"), r)

    def test_undoing_a_retarget_needs_no_expect(self):
        r = self.s.post("/api/review/retarget", file="proposed-nope.json", ref=2, undo=True)
        self.assertNotIn(MISSING, r.get("message", ""))

    def test_a_proposal_that_is_gone_still_says_so_first(self):
        for path, extra in (("/api/review/repeat", {"how": "keep"}), ("/api/review/retarget", {"id": "ABC-A-001"})):
            r = self.s.post(path, file="proposed-nope.json", ref=2, **extra)
            self.assertIn("no longer pending", r.get("message", ""))
        r = self.s.post("/api/review/reject", rows=[{"file": "proposed-nope.json", "ref": 2}], reason="Chatter")
        self.assertIn("no longer pending", r.get("message", ""))

    # ── Approve minutes ────────────────────────────────────────────────────────
    def test_approve_minutes_needs_the_minutes_expect_and_changes_nothing_without_it(self):
        s = self.s
        name = s.stage_minutes()
        before = s.path(name).read_bytes()
        self.check(s.post("/api/minutes/approve", file=name, group=True, own=[]), MISSING)
        self.check(s.post("/api/minutes/approve", file=name, group=True, own=[], expect="x"), BAD)
        self.check(s.post("/api/minutes/approve", file=name, group=True, own=[], expect=s.fp(name, 1)), CHANGED)   # an item's, not the minutes'
        self.assertEqual(s.path(name).read_bytes(), before)
        r = s.post("/api/minutes/approve", file=name, group=True, own=[], expect=s.fp(name, "meeting"))
        for words in (MISSING, CHANGED, BAD):
            self.assertNotIn(words, r.get("message", ""))                         # the minutes' own checks answer (no draft here)

    def test_approve_minutes_on_a_file_without_a_minutes_block_still_needs_the_fingerprint(self):
        s = self.s
        name = s.stage()                                    # waiting, but holds items only: the old check skipped it
        before = s.path(name).read_bytes()
        self.check(s.post("/api/minutes/approve", file=name, group=True, own=[]), MISSING)
        self.check(s.post("/api/minutes/approve", file=name, group=True, own=[], expect=s.fp(name, 1)), CHANGED)
        self.assertEqual(s.path(name).read_bytes(), before)

    def test_approve_minutes_for_a_file_that_is_gone_says_so(self):
        r = self.s.post("/api/minutes/approve", file="proposed-nope.json", group=True, own=[])
        self.assertIn("no longer pending", r.get("message", ""))

    # ── review.py itself ───────────────────────────────────────────────────────
    def test_review_py_commands_still_work_without_expect(self):
        s = self.s
        name = s.stage()
        subprocess.run([sys.executable, str(s.v.root / "system/scripts/review.py"), "list", "--json"], cwd=s.v.root, check=True, capture_output=True)
        n = next(r["n"] for r in json.loads(subprocess.run([sys.executable, str(s.v.root / "system/scripts/review.py"), "list", "--json"],
                                                           cwd=s.v.root, capture_output=True, text=True).stdout) if r["file"] == name and r["ref"] == 2)
        r = subprocess.run([sys.executable, str(s.v.root / "system/scripts/review.py"), "reject", str(n)], cwd=s.v.root, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(s.decisions(name)[2], "rejected")


class Mutants(unittest.TestCase, Decline):
    """Each route's check taken out on its own turns its test red; so does the shared check."""

    def run_mutant(self, mutate=None, helper=False):
        s = Server(mutate=mutate, helper_mutant=helper)
        try:
            return s, s.stage(), s.stage_minutes()
        except Exception:
            s.close()
            raise

    def test_reject_without_its_check_decides_without_a_fingerprint(self):
        s, name, _ = self.run_mutant("reject")
        try:
            r = s.post("/api/review/reject", rows=[{"file": name, "ref": 2}], reason="Chatter")
            self.assertTrue(r.get("ok"), "the mutant lets it through, which Routes.test_reject_without_expect... would catch")
        finally:
            s.close()

    def test_approve_instead_without_its_check_decides_without_a_fingerprint(self):
        s, name, _ = self.run_mutant("approve-instead")
        try:
            s.post("/api/review/reject", rows=[{"file": name, "ref": 2, "expect": s.fp(name, 2)}], reason="Chatter")
            r = s.post("/api/review/rejected", rows=[{"file": name, "ref": 2}], how="approve")
            self.assertTrue(r.get("ok"), r)
        finally:
            s.close()

    def test_repeat_without_its_check_reaches_review_without_a_fingerprint(self):
        s, name, _ = self.run_mutant("repeat")
        try:
            r = s.post("/api/review/repeat", file=name, ref=2, how="keep")
            self.assertNotIn(MISSING, r.get("message", ""))
        finally:
            s.close()

    def test_retarget_without_its_check_reaches_review_without_a_fingerprint(self):
        s, name, _ = self.run_mutant("retarget")
        try:
            r = s.post("/api/review/retarget", file=name, ref=2, id="ABC-A-001")
            self.assertNotIn(MISSING, r.get("message", ""))
        finally:
            s.close()

    def test_approve_minutes_without_its_check_settles_and_decides_without_a_fingerprint(self):
        s, _, mins = self.run_mutant("minutes")
        try:
            r = s.post("/api/minutes/approve", file=mins, group=True, own=[])
            self.assertNotIn(MISSING, r.get("message", ""))
        finally:
            s.close()

    def test_approve_minutes_that_skips_a_file_with_no_minutes_block_decides_without_a_fingerprint(self):
        s, name, _ = self.run_mutant("minutes-skip")
        try:
            r = s.post("/api/minutes/approve", file=name, group=True, own=[])
            self.assertNotIn(MISSING, r.get("message", ""))
        finally:
            s.close()

    def test_a_shared_check_that_always_passes_lets_a_changed_item_through(self):
        s, name, _ = self.run_mutant(helper=True)
        try:
            bravo = s.fp(name, 2)
            s.take_out(name, "Alpha item")
            r = s.post("/api/review/reject", rows=[{"file": name, "ref": 2, "expect": bravo}], reason="Chatter")
            self.assertTrue(r.get("ok"), r)                       # Charlie rejected on Bravo's fingerprint
            self.assertEqual(s.decisions(name)[2], "rejected")
        finally:
            s.close()


class Wording(unittest.TestCase):
    """The three messages are plain words and the page's stale-row check recognises the changed one."""

    def test_the_messages(self):
        text = DIFF.read_text(encoding="utf-8") if not HAS_DIFF else (ROOT / "system/scripts/live_server.py").read_text(encoding="utf-8")
        for m in re.findall(r'^\+?EXPECT_(?:MISSING|BAD|CHANGED) = "(.*)"', text, re.M):
            self.assertTrue(plain(m), m)
        js = (ROOT / "system/templates/dashboard/src/core/server.js").read_text(encoding="utf-8")
        self.assertIn("has changed since you looked at it", js)               # REVIEW_CHANGED: the page's answer to the changed message


class UndoWords(unittest.TestCase):
    """review.js:440 (Approve instead's Undo) reads the re-reject reply: a declined one is said as declined, not as "Rejected again"."""
    SAY = ROOT / "system/templates/dashboard/src/core/say.js"

    def words(self, say_js, replies, count):
        code = ("import { rejectedAgainWords as w } from 'file://%s';\n"
                "const m = JSON.parse(process.argv[1]); process.stdout.write(w(m[0], m[1]));") % say_js
        r = subprocess.run(["node", "--input-type=module", "-e", code, json.dumps([replies, count])], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    @unittest.skipUnless(shutil.which("node"), "needs node")
    def test_the_words(self):
        self.assertEqual(self.words(self.SAY, [{"ok": True}, {"ok": True}], 3), "Rejected again: 3")
        self.assertEqual(self.words(self.SAY, [], 2), "Rejected again: 2")                       # the in-place path made no calls
        declined = self.words(self.SAY, [{"ok": True}, {"ok": False, "message": "That item has changed since you looked at it, so nothing was changed. Look at the list again."}], 2)
        self.assertTrue(declined.startswith("Not rejected again: That item has changed"), declined)
        self.assertNotIn("Rejected again: 2", declined)
        self.assertEqual(self.words(self.SAY, [None], 1), "Not rejected again: nothing was changed")
        self.assertTrue(plain(declined))

    @unittest.skipUnless(shutil.which("node"), "needs node")
    def test_mutant_that_ignores_the_replies_says_rejected_again(self):
        src = self.SAY.read_text(encoding="utf-8")
        old = "i = list.findIndex(r => !r || !r.ok);"
        self.assertIn(old, src)
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "say.mjs"
            f.write_text(src.replace(old, "i = -1;"), encoding="utf-8")
            self.assertEqual(self.words(f, [{"ok": False, "message": "no"}], 1), "Rejected again: 1")

    def test_the_page_reads_the_replies_and_only_marks_the_rows_rejected_when_all_were(self):
        js = (ROOT / "system/templates/dashboard/src/review.js").read_text(encoding="utf-8")
        self.assertIn('replies.push(await api("/api/review/reject"', js)
        self.assertIn("if(replies.every(r=>r&&r.ok)) rjAddGone(", js)
        self.assertIn("snack(rejectedAgainWords(replies,back.length))", js)
        self.assertNotIn("snack(`Rejected again: ${back.length}`)", js)


class Page(unittest.TestCase):
    """The page sends the fingerprint on every path that reaches one of the five routes."""

    def test_every_call_sends_expect(self):
        src = (ROOT / "system/templates/dashboard/src/review.js").read_text(encoding="utf-8")
        for call in ('api("/api/review/repeat",{file:r.file,ref:r.ref,how,...rvExp(r)})', 'api("/api/review/retarget",{...at,id,...rvExp(r)})',
                     'api("/api/review/reject",{rows:L.map(r=>({file:r.file,ref:r.ref,...rvExp(r)})),...body})',
                     'rows:rows.map(r=>({file:r.file,ref:r.ref,...rvExp(r)})),how,',
                     'api("/api/review/reject",{rows:L.map(x=>({file:x.file,ref:x.ref,...rvExp(x)})),...b})'):
            self.assertIn(call, src)
        self.assertEqual(len(re.findall(r'api\("/api/review/(?:repeat|retarget|reject)"', src)), 5)       # no call outside these five (undo of a retarget is one)
        mins = (ROOT / "system/templates/dashboard/src/stores/minutes.js").read_text(encoding="utf-8")
        self.assertIn('...(meeting && meeting.fp ? { expect: meeting.fp } : {})', mins)
        self.assertIn('REVIEW_CHANGED.test(r.message || "")) { await reloadData();', mins)

    def test_the_recent_rejects_carry_their_fingerprint(self):
        import quality
        data = {"created": "2026-10-21T09:00:00", "items": []}
        it = {"n": 4, "op": "new", "table": "actions", "decision": "rejected", "values": {"description": "x", "project": "ABC"}}
        row = quality.reject_row("proposed-2026-10-21-0900-r.json", data, it)
        self.assertEqual(row["fp"], build_dashboard.item_fp(it))


if __name__ == "__main__":
    unittest.main(verbosity=1)
