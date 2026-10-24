"""#280 (round 3): a minutes proposal whose file operation can't run (its transcript is no longer in the inbox) never blocks Apply.

Run: python3 dev/tests/test_held_missing_source.py      (quick tier: no Chrome)
Alan's vault: three approved minutes proposals each failed Apply with "copy: source not found", because their transcripts had left the
inbox while the drafts stayed in system/staging/drafts. Builds a throwaway vault (test_tracker.Vault), stages minutes with the real
minutes.py, approves them, removes the transcript and runs the real scripts:
- Apply (skips until tracker.py takes dev/proposals/280/tracker.py.diff): the held proposal is left in staging, named, its minutes back
  in Review with the reason; a second, valid proposal is applied.
- Page (needs Google Chrome): the held row says why and offers Approve without the transcript and Discard, never Approve.
- Review (runs now): the row says why; "approve N --without-transcript" files the minutes without the transcript copy; "reject N --discard"
  sets the proposal aside in system/staging/discarded/, writing nothing.
"""
import json
import os
import re
import socket
import subprocess
import sys
import time
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_tracker import Vault, action, make_draft  # noqa: E402


def meeting_fp(prop):
    """The fingerprint the page sends as `expect` for a staged meeting's minutes row (2.6.3: the route refuses a decision without it)."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system/scripts"))
    import build_dashboard
    return build_dashboard.block_fp(json.loads(Path(prop).read_text(encoding="utf-8"))["meeting"])

REPO = Path(__file__).resolve().parents[2]
DAY, TITLE = "2026-10-20", "Supplier checkpoint"
TRANSCRIPT = f"inbox/{DAY} Supplier checkpoint.vtt"
DRAFT = f"system/staging/drafts/{DAY} Supplier checkpoint.docx"
VTT = "WEBVTT\n\n00:00:01.000 --> 00:00:05.000\n<v Alan Carter>Morning all, first the supplier.</v>\n"
ITEM = {"table": "actions", "section": "Actions", "values": {"project": "ABC", "description": "Chase the supplier's plan",
                                                              "owner": "Alan Carter", "due_date": "2030-06-10"}}
HELD_IN_TRACKER = "_hold_missing_sources" in (REPO / "system/scripts/tracker.py").read_text(encoding="utf-8")
HELD_IN_SERVER = "without-transcript" in (REPO / "system/scripts/live_server.py").read_text(encoding="utf-8")


class HeldMissingSource(unittest.TestCase):
    def setUp(self):
        self.now = os.environ.get("CREAITE_NOW")
        os.environ["CREAITE_NOW"] = f"{DAY} 18:00"
        self.v = Vault()
        self.v.run("init")
        self.root = self.v.root
        (self.root / TRANSCRIPT).write_text(VTT, encoding="utf-8")
        make_draft(self.root / DRAFT)

    def tearDown(self):
        self.v.cleanup()
        if self.now is None:
            os.environ.pop("CREAITE_NOW", None)
        else:
            os.environ["CREAITE_NOW"] = self.now

    def stage_gone(self, approve=True):
        """Minutes staged by minutes.py and approved (items too), then the transcript leaves the inbox."""
        f = self.root / "system/staging/drafts/meeting.json"
        f.write_text(json.dumps({"title": TITLE, "date": DAY, "projects": ["ABC"], "transcript": TRANSCRIPT, "draft": DRAFT,
                                 "items": [ITEM]}), encoding="utf-8")
        r = self.v.run("stage", str(f), script="minutes.py", ok=False, cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        prop = sorted((self.root / "system/staging").glob("proposed-*.json"))[-1]
        data = json.loads(prop.read_text(encoding="utf-8"))
        self.assertTrue(any(o.get("op") == "copy" and o.get("from") == "transcript" for o in data["meeting"]["file_ops"]))
        if approve:
            data["meeting"]["minutes_decision"] = "approved"
            for i in data["items"]:
                i["decision"] = "approved"
            prop.write_text(json.dumps(data, indent=2), encoding="utf-8")
        (self.root / TRANSCRIPT).unlink()
        return prop

    def read(self, prop):
        return json.loads(prop.read_text(encoding="utf-8"))

    def number(self):
        rows = json.loads(self.v.run("list", "--json", script="review.py", cwd=self.root).stdout)
        return next(r["n"] for r in rows if r["ref"] == "meeting")

    # ── Apply ─────────────────────────────────────────────────────────────────────────────────────────
    @unittest.skipUnless(HELD_IN_TRACKER, "tracker.py has not taken dev/proposals/280/tracker.py.diff yet")
    def test_a_missing_transcript_is_held_and_the_other_proposal_applies(self):
        held = self.stage_gone()
        other = self.v.propose("2026-10-21-0900", [action(1, description="Book the pilot review", source="dashboard")])
        r = self.v.run("apply", ok=False, cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Held in Review, not applied", r.stdout)
        self.assertIn(held.name, r.stdout)
        self.assertIn("transcript no longer in the inbox", r.stdout)
        self.assertNotIn("Apply stopped", r.stdout)
        self.assertIn("Book the pilot review", [a["description"] for a in self.v.rows("actions")])
        self.assertNotIn("Chase the supplier's plan", [a["description"] for a in self.v.rows("actions")])
        self.assertFalse(other.exists(), "the valid proposal was applied and moved to applied/")
        data = self.read(held)
        self.assertEqual(data["meeting"]["minutes_decision"], "pending", "the minutes go back to Review")
        self.assertIn("transcript no longer in the inbox", data["meeting"].get("held", ""))
        self.assertFalse(any(i.get("applied") for i in data["items"]), "nothing of the held proposal is written")
        r = self.v.run("apply", ok=False, cwd=self.root)              # still held, never an Apply stopped
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("Apply stopped", r.stdout)

    @unittest.skipUnless(HELD_IN_TRACKER, "tracker.py has not taken dev/proposals/280/tracker.py.diff yet")
    def test_a_named_apply_of_the_held_proposal_holds_it_too(self):
        held = self.stage_gone()
        r = self.v.run("apply", held.name, ok=False, cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Held in Review, not applied", r.stdout)
        self.assertEqual(self.read(held)["meeting"]["minutes_decision"], "pending")

    # ── Review ────────────────────────────────────────────────────────────────────────────────────────
    def test_review_says_why_and_approve_needs_the_choice(self):
        held = self.stage_gone(approve=False)
        rows = self.v.run("list", script="review.py", cwd=self.root).stdout
        self.assertIn("transcript no longer in the inbox", rows)
        r = self.v.run("approve", str(self.number()), script="review.py", ok=False, cwd=self.root)
        self.assertIn("not approved", r.stdout)
        self.assertIn("--without-transcript", r.stdout)
        self.assertEqual(self.read(held)["meeting"]["minutes_decision"], "pending")

    def test_approve_without_the_transcript_copy_then_apply_files_the_minutes(self):
        held = self.stage_gone(approve=False)
        r = self.v.run("approve", str(self.number()), "--without-transcript", "--as-staged", script="review.py", ok=False,
                       cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Minutes approved", r.stdout)
        m = self.read(held)["meeting"]
        self.assertEqual(m["minutes_decision"], "approved")
        self.assertFalse([o for o in m["file_ops"] if o.get("from") == "transcript" or o.get("path") == TRANSCRIPT])
        self.assertEqual(m["transcript_dropped"]["path"], TRANSCRIPT)
        self.assertNotIn("held", m)
        data = self.read(held)
        data["items"] = [{**i, "decision": "approved"} for i in data["items"]]
        held.write_text(json.dumps(data, indent=2), encoding="utf-8")
        r = self.v.run("apply", ok=False, cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Chase the supplier's plan", [a["description"] for a in self.v.rows("actions")])
        self.assertTrue(list(self.root.glob(f"projects/*/minutes/{DAY} *")), "the minutes are filed")
        self.assertFalse(list(self.root.glob(f"projects/*/transcripts/{DAY} *")))

    def test_without_transcript_is_refused_while_the_transcript_is_there(self):
        f = self.root / "system/staging/drafts/meeting.json"
        f.write_text(json.dumps({"title": TITLE, "date": DAY, "projects": ["ABC"], "transcript": TRANSCRIPT, "draft": DRAFT,
                                 "items": [ITEM]}), encoding="utf-8")
        self.v.run("stage", str(f), script="minutes.py", cwd=self.root)
        r = self.v.run("approve", str(self.number()), "--without-transcript", script="review.py", ok=False, cwd=self.root)
        self.assertIn("still there", r.stdout)

    def test_discard_sets_the_proposal_aside_and_writes_nothing(self):
        held = self.stage_gone(approve=False)
        before = self.v.snapshot()[0]
        r = self.v.run("reject", str(self.number()), "--discard", script="review.py", ok=False, cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(held.exists())
        self.assertTrue((self.root / "system/staging/discarded" / held.name).is_file())
        self.assertEqual(self.v.snapshot()[0], before, "nothing reaches the tracker")
        self.assertNotIn(TITLE, self.v.run("list", script="review.py", cwd=self.root).stdout)

    def test_discard_is_refused_for_minutes_that_can_be_filed(self):
        f = self.root / "system/staging/drafts/meeting.json"
        f.write_text(json.dumps({"title": TITLE, "date": DAY, "projects": ["ABC"], "transcript": TRANSCRIPT, "draft": DRAFT,
                                 "items": [ITEM]}), encoding="utf-8")
        self.v.run("stage", str(f), script="minutes.py", cwd=self.root)
        r = self.v.run("reject", str(self.number()), "--discard", script="review.py", ok=False, cwd=self.root)
        self.assertNotEqual(r.returncode, 0)
        self.assertTrue(list((self.root / "system/staging").glob("proposed-*.json")))

    def test_a_review_number_that_isnt_one_is_a_plain_refusal(self):
        """"approve abc" (or "reject abc --discard") is one plain line and exit 2, never a ValueError traceback."""
        for args in (("approve", "abc"), ("approve", "2-x"), ("reject", "abc", "--discard"), ("approve", "abc", "--without-transcript")):
            r = self.v.run(*args, script="review.py", ok=False, cwd=self.root)
            self.assertEqual(r.returncode, 2, args)
            self.assertNotIn("Traceback", r.stdout + r.stderr, args)
            self.assertNotIn("ValueError", r.stdout + r.stderr, args)
            self.assertIn("review number", r.stdout, args)      # "not a review number" (or the #280 follow-up's discard words)
            self.assertEqual(len(r.stdout.strip().splitlines()), 1, args)

    def test_the_dashboard_row_is_marked_held(self):
        self.stage_gone(approve=False)
        self.v.run(script="build_dashboard.py", cwd=self.root)
        html = (self.root / "dashboard.html").read_text(encoding="utf-8")
        self.assertTrue('"held": "transcript no longer in the inbox' in html or '"held":"transcript no longer in the inbox' in html,
                        "the Review row carries the reason")



@unittest.skipUnless(HELD_IN_SERVER, "live_server.py has not taken dev/proposals/280/live_server-held.py.diff yet")
class HeldThroughTheServer(unittest.TestCase):
    """Review's two buttons go through POST /api/review: decision "discard", and approve with mode "without-transcript"."""
    def setUp(self):
        self.now = os.environ.get("CREAITE_NOW")
        os.environ["CREAITE_NOW"] = f"{DAY} 18:00"
        self.v = Vault()
        self.v.run("init")
        self.root = self.v.root
        with socket.socket() as sk:
            sk.bind(("127.0.0.1", 0))
            port = sk.getsockname()[1]
        self.base = f"http://127.0.0.1:{port}"
        self.proc = subprocess.Popen([sys.executable, str(self.root / "system/scripts/live_server.py")],
                                     env={**os.environ, "CREAITE_PORT": str(port)}, stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                urllib.request.urlopen(self.base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        page = urllib.request.urlopen(self.base + "/").read().decode()
        self.token = json.loads(re.search(r'id="data">(.*?)</script>', page, re.S).group(1).replace("<\\/", "</"))["token"]

    def tearDown(self):
        self.proc.terminate()
        self.proc.wait(timeout=10)
        self.v.cleanup()
        if self.now is None:
            os.environ.pop("CREAITE_NOW", None)
        else:
            os.environ["CREAITE_NOW"] = self.now

    def post(self, path, body):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())

    def staged(self):
        (self.root / TRANSCRIPT).write_text(VTT, encoding="utf-8")
        make_draft(self.root / DRAFT)
        f = self.root / "system/staging/drafts/meeting.json"
        f.write_text(json.dumps({"title": TITLE, "date": DAY, "projects": ["ABC"], "transcript": TRANSCRIPT, "draft": DRAFT,
                                 "items": [ITEM]}), encoding="utf-8")
        self.v.run("stage", str(f), script="minutes.py", cwd=self.root)
        (self.root / TRANSCRIPT).unlink()
        return sorted((self.root / "system/staging").glob("proposed-*.json"))[-1]

    def test_discard_through_the_server(self):
        prop = self.staged()
        res = self.post("/api/review", {"file": prop.name, "ref": "meeting", "decision": "discard", "expect": meeting_fp(prop)})
        self.assertTrue(res["ok"], res)
        self.assertTrue((self.root / "system/staging/discarded" / prop.name).is_file())

    def test_approve_without_the_transcript_through_the_server(self):
        prop = self.staged()
        res = self.post("/api/review", {"file": prop.name, "ref": "meeting", "decision": "approved",
                                        "modes": ["without-transcript", "as-staged"], "expect": meeting_fp(prop)})
        self.assertTrue(res["ok"], res)
        self.assertEqual(json.loads(prop.read_text(encoding="utf-8"))["meeting"]["minutes_decision"], "approved")

    def test_an_unknown_decision_is_refused(self):
        prop = self.staged()
        res = self.post("/api/review", {"file": prop.name, "ref": "meeting", "decision": "delete", "expect": meeting_fp(prop)})
        self.assertFalse(res["ok"])
        self.assertTrue(prop.exists())



class HeldRowOnThePage(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        populate(v)
        root = v.root
        (root / TRANSCRIPT).write_text(VTT, encoding="utf-8")
        make_draft(root / DRAFT)
        f = root / "system/staging/drafts/meeting.json"
        f.write_text(json.dumps({"title": TITLE, "date": DAY, "projects": ["ABC"], "transcript": TRANSCRIPT, "draft": DRAFT,
                                 "items": [ITEM]}), encoding="utf-8")
        v.run("stage", str(f), script="minutes.py", cwd=root)
        (root / TRANSCRIPT).unlink()

    def test_the_held_row_offers_the_two_ways_out(self):
        b = self.b
        b.wait("REV.some(x=>x.ref==='meeting'&&x.held)", timeout=15)
        self.assertIn("transcript no longer in the inbox", b.eval("REV.find(x=>x.ref==='meeting').held"))
        n = b.eval("REV.find(x=>x.ref==='meeting').n")
        row = f'#v-intake-review tr.irprop[data-irn="{n}"]'      # 2.6: the Intake page's row (#232), its meeting opens
        b.eval(f"go('intake-review', {n})")
        b.wait(f"!!document.querySelector('{row} [data-ira=held-approve]')", timeout=10)
        self.assertEqual(b.eval("document.querySelectorAll('#v-intake-review [data-ira=held-discard]').length"), 1)
        self.assertEqual(b.eval(f"!!document.querySelector('{row} [data-ira=approve]')"), False, "no plain Approve on a held row")
        self.assertIn("Approve the minutes without the transcript copy",
                      b.eval(f"document.querySelector('{row} [data-ira=held-approve]').title"))
        # Intake has no right-click menu on a proposal (the old Review's cxReview); A on the row says why and offers the way out
        b.eval(f"irApprove({n})")
        b.wait("(document.body.innerText||'').includes('Approve the minutes without the transcript copy')", timeout=5)
        b.wait("/Approve without it/.test((document.getElementById('snackU')||{}).textContent||'')", timeout=5)
        self.assertEqual(b.eval("heldLines('Apply 4: 1 written\\nHeld in Review, not applied: proposed-x.json minutes (A): gone').length"), 1)
        self.assertEqual(b.errors, [])


if __name__ == "__main__":
    unittest.main()
