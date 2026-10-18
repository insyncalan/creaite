"""BL-295: Close the day as a guided shutdown, the card (components/closeday/CloseDay.jsx) and First thing on Today.

Run: python3 dev/tests/test_close_day_card.py   (needs Google Chrome; skipped otherwise)
The clock is fixed on Tuesday 13-10-2026 at 17:30 and a stand-in Claude is used (test_close_day_guided's), so the catch-up sweep
stages one proposal and nothing reads Microsoft 365. One test per point of BL-295's Done when (dev/archive/notes/v1.9.0/V190-CLOSE-DAY-NOTE.md): the
four steps and the end line; the catch-up starting as the card opens, its progress and its find in step 1 and Loose ends; Skip and
Stop; each loose end's place kept and acted on (Review now opens Review highlighted, Work for an item, Intake for a file; a prep
page made after closing); closing during the sweep closing when it ends; nothing approved or applied; a quiet step passed over;
ask first; overdue items; Esc keeping the step; the stepper's names for a screen reader; VIP never labelled; and the next
morning's First thing on Today.
"""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from live_browser import LiveBrowserCase, pin_page_clock  # noqa: E402
import test_close_day_guided as guided  # noqa: E402  (fixes the clock, the vault's dates and the stand-in Claude)

CARD = "document.getElementById('closeDlg')"
SAID = "document.querySelector('#closeDlg [role=status]').textContent"
STEP = "document.querySelector('#closeDlg .cdsteps li[aria-current=step]')?.textContent"


class CloseDayCard(LiveBrowserCase):
    shared_server = False

    @classmethod
    def load(cls, v):
        guided.world(v)
        fake = v.root / "fake_claude.py"
        fake.write_text(guided.FAKE)
        fake.chmod(0o755)

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": guided.NOW, "CREAITE_CLAUDE": str(cls.v.root / "fake_claude.py")}

    def setUp(self):
        super().setUp()
        pin_page_clock(self.b, guided.NOW)                                     # the page's TODAY is the server's, not the runner's real day

    def tracker(self):
        return [self.v.rows(t) for t in ("actions", "raid", "decisions")]

    def open_card(self):
        b = self.b
        b.eval("go('today')")
        b.click("#dayClose")
        b.wait(f"{CARD} && {CARD}.open")

    def proposals(self):
        return {p.name: p.read_text() for p in (self.v.root / "system/staging").glob("proposed-*.json")}

    def settings(self, **day):
        cfg = self.v.root / "system/config/settings.json"
        s = json.loads(cfg.read_text())
        s.setdefault("day", {}).update(day)
        cfg.write_text(json.dumps(s, indent=2))

    def to_step(self, name):
        b = self.b
        for _ in range(4):
            if b.eval(STEP) == name:
                return
            b.click("#closeDlg [data-cdnext]")
            b.pump(0.3)
        b.wait(f"{STEP}==='{name}'")

    STEPS = ["Catch up", "Today", "Loose ends", "Tomorrow"]

    def press_to_step(self, want):
        """Reach `want` by arrow keys, waiting on the step's STATE. The card skips a step that has nothing in it, and the Today
        step has nothing until the card's data has loaded, so under load ArrowRight can pass over it (the #89 flake: the step read
        'Loose ends'): then ArrowLeft comes back, now that the data is in. A press that did not move the card is repeated only after a long
        wait. A failure prints the page's state (the step, the live region, the focused element)."""
        b, order = self.b, self.STEPS
        for _ in range(8):
            now = b.eval(STEP)
            if now == want:
                return
            key = "ArrowLeft" if order.index(now) > order.index(want) else "ArrowRight"
            b.key(key)
            for _ in range(60):                                                  # up to 30 s for this press to land
                if b.eval(STEP) != now:
                    break
                b.pump(0.5)
        state = b.eval(f"({{step: {STEP}, said: {SAID}, focus: document.activeElement && document.activeElement.outerHTML.slice(0, 120)}})")
        self.fail(f"the step never read {want!r}: {state}")

    def text(self):
        return self.b.eval(f"{CARD}.textContent")

    def test_the_four_steps_place_every_loose_end_and_end_on_a_clear_line(self):
        b = self.b
        before, staged = self.tracker(), self.proposals()
        self.open_card()
        self.assertEqual(b.eval(STEP), "Catch up")
        self.assertEqual(b.eval("document.querySelector('#closeDlg .cdbody').getAttribute('aria-label')"), "Step 1 of 4, Catch up")
        b.wait(f"/Caught up at/.test({CARD}.textContent)", 30)                # the sweep started as it opened, and ended
        self.assertIn("Tom to share the UAT plan", self.text())
        self.assertIn("1 new item for Review", self.text())
        self.assertEqual(b.eval(SAID), "Step 1 of 4, Catch up")                  # the live region names the step
        b.wait("document.activeElement && document.activeElement.matches('[data-cdnext]')")   # focus is back on Next after the card redraws
        # ← → move between the steps (press_to_step: waits on the step, and comes back with ← if the card passed over Today before its data
        # had loaded, the #89 flake).
        b.wait("document.activeElement && document.activeElement.matches('[data-cdnext]')", 60)
        self.press_to_step("Today")
        self.assertIn("Moved today", self.text())
        b.click("#closeDlg [data-cdnext]")
        b.wait(f"{STEP}==='Loose ends'")
        self.assertEqual(b.eval(SAID), "Step 3 of 4, Loose ends")
        if b.eval("!!document.querySelector('#closeDlg [data-cdmore]')"):            # more than eight: "and n more"
            self.assertEqual(b.eval("document.querySelectorAll('#closeDlg .cdloose li').length"), 8)
            b.click("#closeDlg [data-cdmore]")
            b.wait("!document.querySelector('#closeDlg [data-cdmore]')")
        t = self.text()
        for want in ("Tom to share the UAT plan", "New", "Send the cutover checklist", "Action due today", "Recording 2026-10-13.vtt",
                     "Transcript ready", "Draft the pilot charter"):
            self.assertIn(want, t)
        first = b.eval("document.querySelector('#closeDlg .cdloose li').dataset.ref")
        self.assertRegex(first, r"^p:proposed-2026-10-13-1731-sweep-\d+\.json#1$")   # the sweep's find, first
        self.assertEqual(b.eval("document.querySelector('#closeDlg .cdloose li [aria-pressed=true]').textContent"), "First thing tomorrow")
        b.click(f"#closeDlg .cdloose li[data-ref='{first}'] [data-place=review]")
        b.click("#closeDlg .cdloose li[data-ref='t:e1'] [data-place=leave]")
        self.assertEqual(b.eval(f"document.querySelector(\"#closeDlg .cdloose li[data-ref='{first}'] [aria-pressed=true]\").textContent"),
                         "Review now")
        b.click("#closeDlg [data-cdnext]")
        b.wait(f"{STEP}==='Tomorrow'")
        t = self.text()
        self.assertIn("Wednesday 14th October", t)
        self.assertIn("First thing tomorrow", t)
        self.assertRegex(t, r"Draft the pilot charter · and \d+ more")            # the first five, then a count
        self.assertNotIn("Busy", t)                                              # the private meeting is left out
        b.click("#closeDlg [data-cdprep]")
        b.wait("document.querySelector('#closeDlg [data-cdprep]').getAttribute('aria-pressed')==='true'")
        self.assertIn("Prep page queued", self.text())
        b.click("#closeDlg [data-dcdone]")
        b.wait(f"/Day closed at 17:30/.test({CARD}.textContent)", 45)
        self.assertIn("Everything has a place: 1 for Review now", self.text())
        self.assertIn("1 prep page being made", self.text())
        plan = json.loads((self.v.root / "system/staging/day-closed.json").read_text())["plans"]["2026-10-13"]
        self.assertEqual(plan["review"], [first])
        self.assertEqual((plan["left"], plan["prep"]), (1, 1))
        self.assertIn("i:" + next(a["id"] for a in self.v.rows("actions") if a["description"] == "Send the cutover checklist"), plan["first"])
        self.assertEqual(self.tracker(), before)                                 # nothing approved or applied
        self.assertEqual({k: v for k, v in self.proposals().items() if k in staged}, staged)   # no proposal decided
        self.assertNotIn("VIP", self.text())                                     # BL-288: never labelled
        for _ in range(80):                                                      # the prep page is made after closing
            q = b.eval("api('/api/day/prep',{op:'list'})")
            if q["items"] and q["items"][0]["state"] not in ("queued", "running"):
                break
            b.pump(0.5)
        self.assertEqual([i["state"] for i in q["items"]], ["made"], q)
        b.wait("/Day closed at/.test(document.getElementById('dayClose').getAttribute('aria-label'))", 45)
        b.click("#closeDlg [data-cdfinish]")                                     # Review now: Review, the find highlighted
        b.wait("VIEW==='review' && document.querySelectorAll('#reviewBody tr.hl').length===1")
        self.assertFalse(b.eval(f"{CARD}.open"))
        self.assertEqual(b.errors, [])

    def test_esc_keeps_the_step_skip_stops_a_running_sweep_and_a_quiet_step_is_passed_over(self):
        b = self.b
        (self.v.root / "slow-sweep").write_text("")
        self.open_card()
        b.wait("!!document.querySelector('#closeDlg [data-cdskip]')", 15)
        self.assertIn("Catching up", self.text())
        b.click("#closeDlg [data-cdskip]")
        b.wait(f"/Stopped|Skipped/.test({CARD}.textContent)", 15)
        b.wait("!!document.querySelector('#closeDlg [data-cdsweep]')")          # Sweep now, to start it again
        self.assertFalse([p for p in self.proposals() if "-sweep-" in p])       # skipped before it staged anything
        b.click("#closeDlg [data-cdnext]")                                      # Today is empty (nothing moved or promised):
        b.wait(f"{STEP}==='Loose ends'")                                        # passed over, and shown done
        self.assertEqual(b.eval("document.querySelectorAll('#closeDlg .cdsteps li.done').length"), 2)
        b.key("Escape")                                                         # Not yet: closes, keeps the step
        b.wait(f"!{CARD}.open")
        self.assertFalse((self.v.root / "system/staging/day-closed.json").exists())
        b.click("#dayClose")
        b.wait(f"{CARD}.open")
        self.assertEqual(b.eval(STEP), "Loose ends")
        self.assertEqual(b.eval("document.querySelectorAll('#closeDlg .cdsteps li.done').length"), 2)
        b.key("ArrowLeft")                                                      # ← goes back past the empty step too
        b.wait(f"{STEP}==='Catch up'")
        self.assertEqual(b.errors, [])

    def test_stop_ends_the_sweep_and_shows_its_progress(self):
        b = self.b
        (self.v.root / "slow-sweep").write_text("")
        self.open_card()
        b.wait("!!document.querySelector('#closeDlg [data-cdstop]')", 15)
        self.assertEqual(b.eval("document.querySelectorAll('#closeDlg .cdsrc li').length"), 4)   # the sources, as it reads them
        self.assertEqual(b.eval("document.querySelector('#closeDlg .cdsweep').getAttribute('aria-busy')"), "true")
        b.click("#closeDlg [data-cdstop]")
        b.wait(f"/Stopped/.test({CARD}.textContent)", 15)
        self.assertFalse([p for p in self.proposals() if "-sweep-" in p])
        self.assertEqual(b.errors, [])

    def test_closing_during_the_sweep_closes_when_it_ends(self):
        b = self.b
        before, staged = self.tracker(), self.proposals()
        (self.v.root / "slow-sweep").write_text("")
        self.open_card()
        b.wait("!!document.querySelector('#closeDlg [data-cdstop]')", 15)
        self.to_step("Tomorrow")
        self.assertIn("closing now closes when it finishes", self.text())
        b.click("#closeDlg [data-dcdone]")
        b.wait(f"/Closing when the sweep finishes/.test({CARD}.textContent)", 10)
        self.assertFalse((self.v.root / "system/staging/day-closed.json").exists())
        b.wait(f"/Day closed at 17:30/.test({CARD}.textContent)", 30)
        b.wait("/Day closed at/.test(document.getElementById('dayClose').getAttribute('aria-label'))", 45)
        plan = json.loads((self.v.root / "system/staging/day-closed.json").read_text())["plans"]["2026-10-13"]
        self.assertTrue(any(r.startswith("p:proposed-2026-10-13-1731-sweep-") for r in plan["first"]), plan)   # its find, unplaced
        self.assertEqual(self.tracker(), before)
        self.assertEqual({k: v for k, v in self.proposals().items() if k in staged}, staged)
        self.assertEqual(b.errors, [])

    def test_ask_first_and_review_now_opens_work_for_an_item_and_intake_for_a_file(self):
        b = self.b
        self.settings(catchup_sweep="offer")
        self.open_card()
        b.wait(f"/Catch up before you close\\?/.test({CARD}.textContent)", 10)
        self.assertTrue(b.eval("!!document.querySelector('#closeDlg [data-cdsweep]')"))
        self.assertFalse((self.v.root / "fake-calls.jsonl").exists())           # ask first: nothing started
        self.to_step("Loose ends")
        if b.eval("!!document.querySelector('#closeDlg [data-cdmore]')"):
            b.click("#closeDlg [data-cdmore]")
        t = self.text()
        self.assertIn("overdue", t)                                              # overdue items are loose ends too
        due = next(a["id"] for a in self.v.rows("actions") if a["description"] == "Send the cutover checklist")
        f = b.eval("[...document.querySelectorAll('#closeDlg .cdloose li')].find(l=>/Recording 2026-10-13/.test(l.textContent)).dataset.ref")
        b.click("#closeDlg .cdloose li:first-child")                             # focus inside, then the All row: Leave
        b.click("#closeDlg .cdall [data-place=leave]")
        b.click(f"#closeDlg .cdloose li[data-ref='i:{due}'] [data-place=review]")
        b.click(f"#closeDlg .cdloose li[data-ref='{f}'] [data-place=review]")
        self.to_step("Tomorrow")
        self.assertIn("Nothing; tomorrow's Today starts clean.", self.text())
        b.click("#closeDlg [data-dcdone]")
        b.wait(f"/Day closed at 17:30/.test({CARD}.textContent)", 45)
        self.assertIn("2 for Review now", self.text())
        plan = json.loads((self.v.root / "system/staging/day-closed.json").read_text())["plans"]["2026-10-13"]
        self.assertEqual((sorted(plan["review"]), plan["first"]), (sorted([f"i:{due}", f]), []))
        b.click("#closeDlg [data-cdfinish]")                                     # Review now: Work, the item highlighted
        b.wait("VIEW==='work' && [...document.querySelectorAll('#workTbl tr.hl')].length===1", 10)
        self.assertIn("Send the cutover checklist", b.eval("document.querySelector('#workTbl tr.hl').textContent"))
        b.wait("/Also for Review now: Intake/.test(document.body.textContent)", 5)   # then Intake, one click away
        self.assertFalse((self.v.root / "fake-calls.jsonl").exists())           # still no sweep: it was never asked for
        self.assertEqual(b.errors, [])

    def test_first_thing_heads_the_next_mornings_today(self):
        b = self.b
        due = next(a["id"] for a in self.v.rows("actions") if a["description"] == "Send the cutover checklist")
        (self.v.root / "system/staging/day-closed.json").write_text(json.dumps(
            {"days": {"2026-10-12": "18:00"}, "plans": {"2026-10-12": {"first": [f"i:{due}", "p:proposed-waiting.json#1"],
                                                                      "review": [], "left": 0, "prep": 0, "swept": None}}}))
        b.eval("reloadData().then(()=>go('today'))")
        b.wait("!document.getElementById('ftSec').hidden")
        self.assertEqual(b.eval("document.getElementById('nFt').textContent"), "from 12-10-2026")
        t = b.eval("document.getElementById('ftList').textContent")
        self.assertIn("Send the cutover checklist", t)
        self.assertIn("Draft the pilot charter", t)
        self.assertEqual(b.eval("document.querySelectorAll('#ftList li').length"), 2)
        self.assertEqual(b.eval("document.querySelector('#ftList a[data-open]').dataset.open"), f"actions:{due}")
        b.click("#ftList li:nth-child(2) a")
        b.wait("VIEW==='review' && document.querySelectorAll('#reviewBody tr.hl').length===1")
        self.assertEqual(b.errors, [])


if __name__ == "__main__":
    unittest.main()
