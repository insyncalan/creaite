"""#291 walk, after Apply stopped: an item or minutes held in Review say so on their row, in plain words, and the apply's message
says what was held and why.

Run: python3 dev/tests/test_held_visible.py      (the page tests need Google Chrome)
- Row (quick tier): an item flagged invalid carries its reason in plain words (`bad`), and its row's why says it can't be saved.
- Page: the invalid item's row shows the reason and its Approve is off (A says why); held minutes show "Held: …" on the row, not
  only in the tip; the apply's message tells a held item from a file that has gone.
- Apply (skips until tracker.py takes dev/proposals/280/tracker.py.diff): approve an item carrying `raised`, Apply holds it, and
  its row in Review says why.
"""
import json
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_tracker import Vault, make_draft  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
HELD_ITEMS = "#280" in (REPO / "system/scripts/tracker.py").read_text(encoding="utf-8")
DAY = "2026-10-20"
SWEEP = "proposed-2026-10-20-0905-sweep.json"
REASON = ("unknown field(s) for decisions: raised. Valid: project, decision, made_by, client_visible, date, status "
          "(`propose.py fields decisions` lists them.)")
TRANSCRIPT = f"inbox/{DAY} Supplier checkpoint.vtt"
DRAFT = f"system/staging/drafts/{DAY} Supplier checkpoint.docx"
VTT = "WEBVTT\n\n00:00:01.000 --> 00:00:05.000\n<v Alan Carter>Morning all, first the supplier.</v>\n"


def sweep_proposal(flagged):
    """A mail-and-Teams proposal: a valid action, and a new decision carrying `raised` (flagged invalid, or not yet)."""
    dec = {"n": 2, "op": "new", "table": "decisions", "match": "strong", "flags": ["invalid"] if flagged else [],
           "decision": "pending", "values": {"project": "ABC", "decision": "Pilot extended by two weeks",
                                             "made_by": "Alan Carter", "raised": DAY, "source": "Teams chat Pilot"}}
    if flagged:
        dec["invalid_reason"] = REASON
    return {"created": f"{DAY}T09:05:00", "source_run": "sweep", "files": [],
            "items": [{"n": 1, "op": "new", "table": "actions", "match": "strong", "flags": [], "decision": "pending",
                       "values": {"project": "ABC", "description": "Send the pilot plan to the supplier",
                                  "owner": "Alan Carter", "due_date": "2030-06-10", "source": "Teams chat Pilot"}}, dec]}


class InvalidRow(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.v.run("init")

    def tearDown(self):
        self.v.cleanup()

    def test_the_row_carries_the_reason_in_plain_words(self):
        (self.v.root / "system/staging" / SWEEP).write_text(json.dumps(sweep_proposal(True)), encoding="utf-8")
        self.v.run(script="build_dashboard.py", cwd=self.v.root)
        html = (self.v.root / "dashboard.html").read_text(encoding="utf-8")
        data = json.loads(html.split('id="data">', 1)[1].split("</script>", 1)[0].replace("<\\/", "</"))
        row = next(r for r in data["review"] if r.get("file") == SWEEP and r["kind"] == "decisions")
        self.assertEqual(row.get("bad"), "it has a field the tracker doesn't keep (raised)")
        self.assertEqual(row["why"], "Can't be saved as it is")
        ok = next(r for r in data["review"] if r.get("file") == SWEEP and r["kind"] == "actions")
        self.assertNotIn("bad", ok)


class HeldOnThePage(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        populate(v)
        root = v.root
        (root / "system/staging" / SWEEP).write_text(json.dumps(sweep_proposal(True)), encoding="utf-8")
        (root / "inbox").mkdir(exist_ok=True)
        (root / TRANSCRIPT).write_text(VTT, encoding="utf-8")
        make_draft(root / DRAFT)
        f = root / "system/staging/drafts/meeting.json"
        f.write_text(json.dumps({"title": "Supplier checkpoint", "date": DAY, "projects": ["ABC"], "transcript": TRANSCRIPT,
                                 "draft": DRAFT, "items": []}), encoding="utf-8")
        v.run("stage", str(f), script="minutes.py", cwd=root)
        (root / TRANSCRIPT).unlink()

    def row(self, js_find):
        b = self.b
        b.wait(f"REV.some({js_find})", timeout=15)
        b.eval("go('review')")
        n = b.eval(f"REV.find({js_find}).n")
        b.wait(f"!!document.querySelector('#reviewBody tr[data-n=\"{n}\"]')", timeout=10)
        return n, b.eval(f"document.querySelector('#reviewBody tr[data-n=\"{n}\"]').innerText")

    def test_an_invalid_item_says_why_on_its_row_and_cannot_be_approved(self):
        b = self.b
        n, text = self.row(f"x=>x.file==='{SWEEP}'&&x.kind==='decisions'")
        self.assertIn("Can't be saved as it is: it has a field the tracker doesn't keep (raised)", text)
        self.assertIn("Edit it or reject it", text)
        self.assertTrue(b.eval(f"document.querySelector('#reviewBody tr[data-n=\"{n}\"] [data-act=a]').disabled"))
        b.eval(f"decide({n},'approved')")
        b.wait("(document.body.innerText||'').includes(\"Can't be saved as it is\")", timeout=5)
        prop = json.loads((self.v.root / "system/staging" / SWEEP).read_text(encoding="utf-8"))
        self.assertEqual(prop["items"][1]["decision"], "pending", "never approved as it is")
        self.assertFalse(b.eval(f"rvBulkOK(REV.find(x=>x.n==={n}))"), "never in a bulk approve")
        self.assertEqual(b.errors, [])

    def test_held_minutes_say_why_on_the_row(self):
        _, text = self.row("x=>x.kind==='draft'&&!!x.held")
        self.assertIn("Held: transcript no longer in the inbox", text)
        self.assertEqual(self.b.errors, [])

    def test_the_apply_message_tells_a_held_item_from_a_missing_file(self):
        b = self.b
        b.wait("typeof heldWords==='function'", timeout=10)
        item = "Held in Review, not applied: proposed-x.json item 2: unknown field(s) for decisions: raised"
        mins = "Held in Review, not applied: proposed-y.json minutes (Supplier checkpoint): transcript no longer in the inbox (inbox/a.vtt)"
        self.assertEqual(b.eval(f"heldWords({json.dumps(item)})"),
                         ". 1 item is held in Review: it can't be saved as it is")
        self.assertEqual(b.eval(f"heldWords({json.dumps(mins)})"),
                         ". 1 proposal is held in Review: a file to be filed has gone")
        self.assertEqual(b.eval(f"heldWords({json.dumps(item + chr(10) + item + chr(10) + mins)})"),
                         ". 2 items are held in Review: they can't be saved as they are. "
                         "1 proposal is held in Review: a file to be filed has gone")
        self.assertEqual(b.eval("heldWords('Apply 3: 2 written')"), "")


@unittest.skipUnless(HELD_ITEMS, "tracker.py has not taken dev/proposals/280/tracker.py.diff yet")
class HeldAfterApply(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        populate(v)
        (v.root / "system/staging" / SWEEP).write_text(json.dumps(sweep_proposal(False)), encoding="utf-8")

    def test_approve_then_apply_leaves_the_item_in_review_saying_why(self):
        b = self.b
        b.wait(f"REV.some(x=>x.file==='{SWEEP}'&&x.kind==='decisions')", timeout=15)
        b.eval("go('review')")
        n = b.eval(f"REV.find(x=>x.file==='{SWEEP}'&&x.kind==='decisions').n")
        b.wait(f"!!document.querySelector('#reviewBody tr[data-n=\"{n}\"] [data-act=a]')", timeout=10)
        b.click(f'#reviewBody tr[data-n="{n}"] [data-act=a]')
        b.wait("(document.body.innerText||'').includes('1 item is held in Review')", timeout=20)
        b.wait(f"REV.some(x=>x.file==='{SWEEP}'&&x.kind==='decisions'&&!x.done&&!!x.bad)", timeout=15)
        n = b.eval(f"REV.find(x=>x.file==='{SWEEP}'&&x.kind==='decisions').n")
        time.sleep(0.3)
        text = b.eval(f"document.querySelector('#reviewBody tr[data-n=\"{n}\"]').innerText")
        self.assertIn("Can't be saved as it is: it has a field the tracker doesn't keep (raised)", text)
        self.assertEqual(b.errors, [])


if __name__ == "__main__":
    unittest.main()
