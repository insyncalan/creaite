"""#291 walk, after Apply stopped: an item or minutes held in Review say so on their row, in plain words, and the apply's message
says what was held and why. On the 2.6 line the rows are the Intake page's (#232: components/intakeReview/proposals.jsx), so
the page tests drive `#v-intake-review tr.irprop` and the page's own words say "held in Intake".

Run: python3 dev/tests/test_held_visible.py      (the page tests need Google Chrome)
- Row (quick tier): an item flagged invalid carries its reason in plain words (`bad`), and its row's why says it can't be saved.
- Page: the invalid item's row shows the reason and its Approve is off (A says why); held minutes show "Held: …" on the row, not
  only in the tip; the apply's message tells a held item from a file that has gone.
- Fixed in the peek (#291 fix): the invalid item opened and saved in the peek is checked again with the tracker's own check:
  the field the tracker doesn't keep is left out, the row stops saying it can't be saved, Approve is on, and approving then
  applying writes it (the apply part skips until tracker.py takes the #280 diffs).
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
ROW = '#v-intake-review tr.irprop[data-irn="%s"]'   # a proposal's row on the Intake page
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
        n = b.eval(f"REV.find({js_find}).n")
        b.eval(f"go('intake-review', {n})")                                  # its meeting (if any) opens
        b.wait(f"!!document.querySelector('{ROW % n}')", timeout=10)
        return n, b.eval(f"document.querySelector('{ROW % n}').innerText")

    def test_an_invalid_item_says_why_on_its_row_and_cannot_be_approved(self):
        b = self.b
        n, text = self.row(f"x=>x.file==='{SWEEP}'&&x.kind==='decisions'")
        self.assertIn("Can't be saved as it is: it has a field the tracker doesn't keep (raised)", text)
        self.assertIn("Edit it or reject it", text)
        self.assertTrue(b.eval(f"document.querySelector('{ROW % n} [data-ira=approve]').disabled"))
        b.eval(f"irApprove({n})")                                                  # what A on the row does
        b.wait("(document.body.innerText||'').includes(\"Can't be saved as it is\")", timeout=5)
        prop = json.loads((self.v.root / "system/staging" / SWEEP).read_text(encoding="utf-8"))
        self.assertEqual(prop["items"][1]["decision"], "pending", "never approved as it is")
        self.assertFalse(b.eval(f"rvBulkOK(REV.find(x=>x.n==={n}))"), "never in a bulk approve")
        self.assertEqual(b.errors, [])

    def test_held_minutes_say_why_on_the_row(self):
        n, text = self.row("x=>x.kind==='draft'&&!!x.held")
        self.assertIn("Held: the transcript is no longer in Intake", text)
        b = self.b
        self.assertFalse(b.eval(f"!!document.querySelector('{ROW % n} [data-ira=approve]')"), "never Approve as staged")
        self.assertTrue(b.eval(f"!!document.querySelector('{ROW % n} [data-ira=held-approve]')"))
        self.assertTrue(b.eval(f"!!document.querySelector('{ROW % n} [data-ira=held-discard]')"))
        b.eval(f"irApprove({n})")                                                  # A on the row says why
        b.wait("(document.body.innerText||'').includes('Approve the minutes without the transcript copy')", timeout=5)
        self.assertEqual(b.errors, [])

    def test_the_apply_message_tells_a_held_item_from_a_missing_file(self):
        b = self.b
        b.wait("typeof heldWords==='function'", timeout=10)
        item = "Held in Review, not applied: proposed-x.json item 2: unknown field(s) for decisions: raised"
        mins = "Held in Review, not applied: proposed-y.json minutes (Supplier checkpoint): transcript no longer in the inbox (inbox/a.vtt)"
        self.assertEqual(b.eval(f"heldWords({json.dumps(item)})"),
                         ". 1 item is held in Intake: it can't be saved as it is")
        self.assertEqual(b.eval(f"heldWords({json.dumps(mins)})"),
                         ". 1 suggestion is held in Intake: a file to be filed has gone")
        self.assertEqual(b.eval(f"heldWords({json.dumps(item + chr(10) + item + chr(10) + mins)})"),
                         ". 2 items are held in Intake: they can't be saved as they are. "
                         "1 suggestion is held in Intake: a file to be filed has gone")
        self.assertEqual(b.eval("heldWords('Apply 3: 2 written')"), "")


class FixedInThePeek(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        populate(v)
        (v.root / "system/staging" / SWEEP).write_text(json.dumps(sweep_proposal(True)), encoding="utf-8")

    def test_saving_the_fixed_item_in_the_peek_lifts_the_hold(self):
        b = self.b
        find = f"x=>x.file==='{SWEEP}'&&x.kind==='decisions'"
        b.wait(f"REV.some({find})", timeout=15)
        n = b.eval(f"REV.find({find}).n")
        b.eval(f"go('intake-review', {n})")
        row = ROW % n
        b.wait(f"!!document.querySelector('{row} [data-ira=approve]')", timeout=10)
        self.assertTrue(b.eval(f"document.querySelector('{row} [data-ira=approve]').disabled"), "held before the fix")
        b.eval(f"openProposal({n})")
        b.wait("!!document.querySelector('#pkPropTop .pk-bad')", timeout=10)
        self.assertIn("Saving leaves out raised", b.eval("document.querySelector('#pkPropTop').innerText"))
        b.eval(f"shared.CUR.draft.t='Pilot extended by three weeks'; shared.CUR.draft.date='{DAY}'")   # the date it was made
        b.eval("pkPropSave(false)")
        b.wait(f"REV.some(x=>x.file==='{SWEEP}'&&x.kind==='decisions'&&!x.bad)", timeout=20)
        prop = json.loads((self.v.root / "system/staging" / SWEEP).read_text(encoding="utf-8"))
        vals = prop["items"][1]["values"]
        self.assertNotIn("raised", vals, "the field the tracker doesn't keep is left out")
        self.assertEqual(vals["decision"], "Pilot extended by three weeks")
        n = b.eval(f"REV.find({find}).n")
        b.eval(f"go('intake-review', {n})")
        row = ROW % n
        b.wait(f"!!document.querySelector('{row} [data-ira=approve]')&&!document.querySelector('{row} [data-ira=approve]').disabled",
               timeout=10)
        self.assertNotIn("Can't be saved as it is", b.eval(f"document.querySelector('{row}').innerText"))
        self.assertNotIn("can't be saved", b.eval(f"rvWhyNot(REV.find(x=>x.n==={n}))[1]"), "a new decision, approved on its own")
        self.assertEqual(b.errors, [])
        if not HELD_ITEMS:
            self.skipTest("approve and apply: tracker.py has not taken dev/proposals/280/tracker.py.diff yet")
        b.click(f"{row} [data-ira=approve]")
        prop_file = self.v.root / "system/staging" / SWEEP
        deadline = time.time() + 10
        while time.time() < deadline and prop_file.exists() and \
                json.loads(prop_file.read_text(encoding="utf-8"))["items"][1].get("decision") != "approved":
            time.sleep(0.2)
        if prop_file.exists():
            item = json.loads(prop_file.read_text(encoding="utf-8"))["items"][1]
            self.assertNotIn("invalid", item.get("flags") or [], "the approval clears the stored flag")
        b.eval("applyNow()")
        db = self.v.root / "system/tracker.db"
        deadline = time.time() + 30
        import sqlite3
        while time.time() < deadline:
            con = sqlite3.connect(db)
            got = con.execute("SELECT count(*) FROM decisions WHERE decision = 'Pilot extended by three weeks'").fetchone()[0]
            con.close()
            if got:
                break
            time.sleep(0.5)
        self.assertEqual(got, 1, "approved and applied, the fixed item is written")
        self.assertEqual(b.errors, [])


@unittest.skipUnless(HELD_ITEMS, "tracker.py has not taken dev/proposals/280/tracker.py.diff yet")
class HeldAfterApply(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        populate(v)
        (v.root / "system/staging" / SWEEP).write_text(json.dumps(sweep_proposal(False)), encoding="utf-8")

    def test_approve_then_apply_leaves_the_item_in_review_saying_why(self):
        b = self.b
        b.wait(f"REV.some(x=>x.file==='{SWEEP}'&&x.kind==='decisions')", timeout=15)
        n = b.eval(f"REV.find(x=>x.file==='{SWEEP}'&&x.kind==='decisions').n")
        b.eval(f"go('intake-review', {n})")
        b.wait(f"!!document.querySelector('{ROW % n} [data-ira=approve]')", timeout=10)
        b.click(f'{ROW % n} [data-ira=approve]')
        b.wait("(document.body.innerText||'').includes('1 item is held in Intake')", timeout=20)
        b.wait(f"REV.some(x=>x.file==='{SWEEP}'&&x.kind==='decisions'&&!x.done&&!!x.bad)", timeout=15)
        n = b.eval(f"REV.find(x=>x.file==='{SWEEP}'&&x.kind==='decisions').n")
        b.eval(f"go('intake-review', {n})")
        b.wait(f"!!document.querySelector('{ROW % n}')", timeout=10)
        time.sleep(0.3)
        text = b.eval(f"document.querySelector('{ROW % n}').innerText")
        self.assertIn("Can't be saved as it is: it has a field the tracker doesn't keep (raised)", text)
        self.assertEqual(b.errors, [])


if __name__ == "__main__":
    unittest.main()
