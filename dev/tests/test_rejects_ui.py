"""BL-315 (v1.9.2), the screens: Rejects, in real life, in a real browser against the real live server (Team 2's routes on
v192-reject-reasons). One test per Done-when point:

#232 C2: on the one Intake page. The old Review page's multi-select bar, batch reject, greyed rows with their chip, the guess shown on a
row and Shift+F10's row menu went with the page (multi-select was not built; the Intake page takes one row at a time). What is tested:

- ✕ on a row, R on a focused row and the peek's Reject all open the one menu: "Reject this because", the seven on 1 to 7,
  Use each guess (G), No reason (0); Esc closes it and focus goes back;
- a number key, G and 0 reject with the right reasons; Duplicate records the item it names, or asks for it;
- the guesses load for the rows and G uses a row's own;
- the message's Undo puts the row back in Intake;
- Activity › Quality › What you rejected changes a reason (with Undo), undoes a reject and approves instead; a new risk goes back to
  Intake and its proposal opens (never approved in bulk);
- the reasons reach `rejected.reason` and the quality view;
- at 320 px nothing scrolls sideways, and no "VIP" label appears.

Run: python3 dev/tests/test_rejects_ui.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_tracker import action  # noqa: E402

SEVEN = ["Not an action", "Duplicate", "Chatter", "Already done", "Wrong project", "Doesn't need tracking", "For another team"]
THANKS, DUP, ROOM, CAL, PLAIN, RISK, KEYS = ("Thanks all for joining, great session", "DUP", "Order sandwiches for Friday lunch",
                                            "Check calendars for a workshop next week", "Prepare the migration cut-over runbook",
                                            "Vendor team availability in November", "Write the keyboard test plan")


def pending(item, **kw):
    return {**item, "decision": "pending", **kw}


class RejectsUI(LiveBrowserCase):
    width, height = 1500, 1000

    @classmethod
    def load(cls, v):
        populate(v)
        v.run("migrate")
        open_ = next(r for r in v.rows("actions") if r["status"] == "Open" and r["project"] == "ABC")
        cls.dup_id, cls.dup_text = open_["id"], open_["description"] + " please"
        v.propose("rj", [
            pending(action(1, description=THANKS)),                                           # guess: Chatter
            pending(action(2, description=cls.dup_text)),                                     # guess: Duplicate of an open item
            pending(action(3, description=ROOM, owner="")),                                   # guess: Doesn't need tracking
            pending(action(4, description=CAL, owner="")),                                    # guess: Chatter (scheduling)
            pending(action(5, description=PLAIN)),                                            # no guess
            pending({"n": 6, "op": "new", "table": "raid", "match": "strong", "flags": [],
                     "values": {"project": "ABC", "type": "Risk", "description": RISK, "owner": "Alan Carter", "impact": "High",
                                "likelihood": "Medium", "raised": "2026-10-01", "source": "Teams · test"}}),   # approved on its own
            pending(action(7, description=KEYS)),
        ], source_run="cx-minutes")

    # ── helpers ──
    def open_review(self):
        b = self.b
        b.eval("go('intake-review')")
        b.wait("!!document.querySelector('#v-intake-review [data-irsec=other]') && !!document.querySelector('#v-intake-review [data-irsec=other]').parentElement.querySelector('tr.irprop')")
        b.wait("Object.keys(rjGuesses.value).length>=4", 15)                 # the guesses have come

    def n(self, text):
        return self.b.eval(f"(REV.find(r=>r.rec.t.startsWith({text!r})&&!r.done)||{{}}).n")

    def row(self, text):
        return f'#v-intake-review tr.irprop[data-irn="{self.n(text)}"]'

    def item(self, ref):
        for d in ("system/staging", "system/staging/applied"):
            p = self.v.root / d / "proposed-rj.json"
            if p.exists():
                try:
                    items = json.loads(p.read_text())["items"]
                except (ValueError, KeyError):  # caught mid-write by the server: not there yet, wait_rejected asks again
                    return None
                return next((i for i in items if i["n"] == ref), None)
        return None

    def wait_rejected(self, refs, timeout=20):
        """Each item's proposal says rejected and is applied (the page applies after a decision)."""
        refs = list(refs)
        for _ in range(int(timeout / 0.1)):
            its = [self.item(r) for r in refs]
            if all(i and i.get("decision") == "rejected" and i.get("applied") for i in its):
                return {r: i for r, i in zip(refs, its)}
            self.b.pump(0.1)
        raise AssertionError(f"not rejected and applied: {[(r, self.item(r)) for r in refs]}")

    def reasons(self):
        return {(r["reason"], r["duplicate_of"]) for r in self.v.rows("rejected")}

    def menu_texts(self):
        return self.b.eval("[...document.querySelectorAll('#rvReason [role=menuitem]')].map(b=>b.querySelector('span').textContent)")

    def reject_button(self, text):
        return self.row(text) + " [data-ira=reject]"

    def menu_open(self):
        self.b.wait("!!document.getElementById('rvReason') && document.getElementById('rvReason').contains(document.activeElement)")

    # ── 1. ✕, R and the peek's Reject open the one menu ──
    def test_every_way_in_opens_the_one_menu(self):
        b = self.b
        self.open_review()
        want = [*SEVEN, "Use each guess", "No reason"]
        # a row's ✕
        b.click(self.reject_button(PLAIN))
        self.menu_open()
        self.assertEqual(self.menu_texts(), want)
        self.assertEqual(b.eval("[...document.querySelectorAll('#rvReason .kbd')].map(k=>k.textContent)"), [*"1234567", "G", "0"])
        self.assertEqual(b.eval("document.getElementById('rvReason').getAttribute('aria-label')"), "Reject this because")
        self.assertEqual(b.eval("document.getElementById('rvReason').getAttribute('role')"), "menu")
        self.assertEqual(b.eval(f"document.querySelector('{self.reject_button(PLAIN)}').getAttribute('aria-expanded')"), "true")
        self.assertEqual(b.eval("document.querySelector('#rvReason [data-reason=guess]').getAttribute('aria-disabled')"), "true")   # no guess for it
        b.key("ArrowDown")
        self.assertEqual(b.eval("document.activeElement.dataset.reason"), "Duplicate")
        b.key("End")
        self.assertEqual(b.eval("document.activeElement.dataset.reason"), "")
        b.key("Escape")                                                            # Esc closes; focus back on ✕
        b.wait("!document.getElementById('rvReason')")
        self.assertEqual(b.eval("document.activeElement.dataset.ira"), "reject")
        self.assertEqual(b.eval(f"document.querySelector('{self.reject_button(PLAIN)}').getAttribute('aria-expanded')"), "false")
        # a row with a guess: the menu offers it
        b.click(self.reject_button(THANKS))
        self.menu_open()
        self.assertIsNone(b.eval("document.querySelector('#rvReason [data-reason=guess]').getAttribute('aria-disabled')"))
        self.assertIn("(Chatter)", b.eval("document.querySelector('#rvReason [data-reason=guess]').textContent"))
        b.key("Escape")
        b.wait("!document.getElementById('rvReason')")
        # R on a focused row
        b.eval(f"document.querySelector('{self.row(PLAIN)}').focus()")
        b.key("r")
        self.menu_open()
        b.key("Escape")
        b.wait("!document.getElementById('rvReason')")
        # the peek's Reject
        b.click(self.row(PLAIN) + " td.title", inset=3)
        b.wait("!!document.getElementById('pkReject') && document.getElementById('pkReject').offsetParent!==null")
        b.click("#pkReject")
        self.menu_open()
        self.assertEqual(b.eval("document.getElementById('pkReject').getAttribute('aria-expanded')"), "true")
        b.key("Escape")
        b.wait("!document.getElementById('rvReason')")
        self.assertTrue(b.eval("document.getElementById('panel').classList.contains('on')"))   # Esc leaves the peek open
        self.assertFalse(b.eval("/VIP/.test(document.getElementById('rjMenuHost').textContent)"))

    # ── 2. a number key, G and 0 reject with the right reasons ──
    def test_number_keys_g_and_0_reject_with_the_right_reasons(self):
        b = self.b
        self.open_review()
        b.click(self.reject_button(THANKS))
        self.menu_open()
        b.key("3")                                                                 # Chatter
        b.wait("!document.getElementById('rvReason')")
        its = self.wait_rejected([1])
        self.assertEqual(its[1]["reject_reason"], "Chatter")
        b.wait("/Rejected 1 as Chatter/.test(document.getElementById('snackT').textContent)", 15)
        # 0: no reason, with R on the focused row
        b.wait(f"!!REV.find(r=>r.rec.t==={PLAIN!r}&&!r.done)")
        b.eval(f"document.querySelector('{self.row(PLAIN)}').focus()")
        b.key("r")
        self.menu_open()
        b.key("0")
        its = self.wait_rejected([5])
        self.assertNotIn("reject_reason", its[5])
        # G on one row: its own guess
        b.wait(f"!!REV.find(r=>r.rec.t==={ROOM!r}&&!r.done)")
        b.click(self.reject_button(ROOM))
        self.menu_open()
        b.key("g")
        its = self.wait_rejected([3])
        self.assertEqual(its[3]["reject_reason"], "Doesn't need tracking")
        # 7 for one row, by the mouse this time
        b.wait(f"!!REV.find(r=>r.rec.t==={KEYS!r}&&!r.done)")
        b.click(self.reject_button(KEYS))
        self.menu_open()
        b.click('#rvReason [data-reason="For another team"]')
        its = self.wait_rejected([7])
        self.assertEqual(its[7]["reject_reason"], "For another team")
        # the reasons reach the tracker's record and the quality view
        got = self.reasons()
        self.assertTrue({("Chatter", None), ("Doesn't need tracking", None), ("For another team", None)} <= got, got)
        self.assertIn((None, None), got)
        b.wait("((D.quality||{}).reasons||[]).some(r=>r.reason==='Chatter')", 15)
        self.assertEqual(b.eval("D.quality.reasons.find(r=>r.reason==='Chatter').n"), 1)

    # ── 3. the guesses load and G uses a row's own; Duplicate records the item ──
    def test_the_guesses_load_and_g_uses_a_rows_own(self):
        b = self.b
        self.open_review()
        guesses = b.eval("Object.fromEntries(Object.entries(rjGuesses.value).map(([k,g])=>[k,g.reason]))")
        self.assertEqual([guesses.get(f"proposed-rj.json#{i}") for i in (1, 2, 3, 4, 5)], ["Chatter", "Duplicate", "Doesn't need tracking", "Chatter", None])
        b.click(self.reject_button(self.dup_text))
        self.menu_open()
        self.assertIn("Duplicate", b.eval("document.querySelector('#rvReason [data-reason=guess]').textContent"))
        b.key("G", modifiers=8)
        its = self.wait_rejected([2])
        self.assertEqual(its[2].get("reject_reason"), "Duplicate")
        self.assertEqual(its[2].get("duplicate_of"), self.dup_id)
        self.assertIn(("Duplicate", self.dup_id), self.reasons())

    # ── 4. the message's Undo puts the row back ──
    def test_the_undo_puts_the_row_back(self):
        b = self.b
        self.open_review()
        b.click(self.reject_button(THANKS))
        self.menu_open()
        b.key("1")
        self.wait_rejected([1])
        b.wait("/Rejected 1 as Not an action/.test(document.getElementById('snackT').textContent)", 15)
        b.wait("document.getElementById('snack').classList.contains('on') && document.getElementById('snackU').style.display!=='none'")
        b.click("#snackU")                                                         # the message's Undo
        b.wait(f"REV.some(r=>r.rec.t=={THANKS!r}&&!r.done)", 20)
        self.assertEqual(self.item(1)["decision"], "pending")
        b.wait("/Back in Intake: 1/.test(document.getElementById('snackT').textContent)")

    # ── 5. Approve instead: one step; a new risk goes back to Intake and opens ──
    def test_approve_instead_from_the_rejects_list_and_the_bulk_rule(self):
        b = self.b
        self.open_review()
        for text in (PLAIN, RISK):
            b.click(self.reject_button(text))
            self.menu_open()
            b.key("1")
        self.wait_rejected([5, 6])
        b.eval("go('activity')")
        b.click("#actTabQ")
        b.wait("document.querySelectorAll('#qRejects li[data-rjkey]').length>=2", 15)
        b.click('#qRejects li[data-rjkey="proposed-rj.json#5"] [data-rjok]')
        b.wait(f"A.some(a=>a.t==={PLAIN!r})", 20)                                   # approved and applied in one step
        b.wait("/Approved instead: 1/.test(document.getElementById('snackT').textContent)")
        self.assertEqual([r["reason"] for r in self.v.rows("rejected")].count("Not an action"), 1)   # its reject row went; the risk's stays
        self.assertEqual(self.item(5)["decision"], "approved")
        b.click("#snackU")                                                         # Undo: rejected again, with its reason
        b.wait(f"!A.some(a=>a.t==={PLAIN!r})", 20)
        for _ in range(200):
            it = self.item(5)
            if it.get("decision") == "rejected" and it.get("applied"):
                break
            b.pump(0.1)
        self.assertEqual((it["decision"], it.get("reject_reason")), ("rejected", "Not an action"))
        # the new risk: never approved in bulk; back in Intake, its proposal opened
        b.eval("go('activity')")
        b.click("#actTabQ")
        b.wait("!!document.querySelector('#qRejects li[data-rjkey=\"proposed-rj.json#6\"] [data-rjok]')", 15)
        b.pump(1.5)                                                                # the list is drawn again after the Undo's reload: click the settled one
        for _ in range(3):                                                         # (a click on the list as it was redrawn is lost: try again)
            b.click('#qRejects li[data-rjkey="proposed-rj.json#6"] [data-rjok]')
            try:
                b.wait(f"REV.some(r=>r.rec.t==={RISK!r}&&!r.done)", 8)
                break
            except TimeoutError:
                b.eval("go('activity')")
                b.click("#actTabQ")
                b.wait("!!document.querySelector('#qRejects li[data-rjkey=\"proposed-rj.json#6\"] [data-rjok]')", 15)
        b.wait(f"REV.some(r=>r.rec.t==={RISK!r}&&!r.done)", 20)
        b.wait("VIEW==='intake-review' && CUR && CUR.mode==='proposal' && document.getElementById('panel').classList.contains('on')", 10)
        self.assertFalse(b.eval(f"R.some(r=>r.t==={RISK!r})"))
        self.assertEqual(self.item(6)["decision"], "pending")
        self.assertIn("1 needs approving on its own", b.eval("document.getElementById('snackT').textContent"))

    # ── 6. Activity › Quality › What you rejected: the chip, a new reason, Approve instead and Undo ──
    def test_activity_lists_the_rejects_with_the_chip(self):
        b = self.b
        self.open_review()
        for text, key in ((THANKS, "g"), (ROOM, "g"), (KEYS, "0")):
            b.click(self.reject_button(text))
            self.menu_open()
            b.key(key)
            b.wait(f"!REV.some(r=>r.rec.t.startsWith({text!r})&&!r.done)", 20)
        self.wait_rejected([1, 3, 7])
        b.eval("go('activity')")
        b.click("#actTabQ")
        b.wait("document.querySelectorAll('#qRejects li[data-rjkey]').length>=3", 15)
        line = '#qRejects li[data-rjkey="proposed-rj.json#1"]'
        self.assertEqual(b.eval(f"document.querySelector('{line} [data-rjchip]').textContent"), "Rejected · Chatter")
        b.click(f"{line} [data-rjchip]")
        self.menu_open()
        b.key("1")                                                                 # Not an action
        b.wait(f"document.querySelector('{line} [data-rjchip]') && document.querySelector('{line} [data-rjchip]').textContent==='Rejected · Not an action'", 20)
        for _ in range(200):
            if (self.item(1) or {}).get("reject_reason") == "Not an action" and self.item(1).get("applied"):
                break
            b.pump(0.1)
        self.assertIn(("Not an action", None), self.reasons())
        # Undo from the list: back in Intake
        b.click('#qRejects li[data-rjkey="proposed-rj.json#3"] [data-rjundo]')
        b.wait("!document.querySelector('#qRejects li[data-rjkey=\"proposed-rj.json#3\"]')", 20)
        self.assertEqual(self.item(3)["decision"], "pending")
        # Approve instead from the list
        b.click('#qRejects li[data-rjkey="proposed-rj.json#7"] [data-rjok]')
        b.wait(f"A.some(a=>a.t==={KEYS!r})", 20)
        b.wait("!document.querySelector('#qRejects li[data-rjkey=\"proposed-rj.json#7\"]')", 20)

    # ── 7. Duplicate with no item named asks: the look-alikes, an ID, or none ──
    def test_duplicate_asks_for_the_item(self):
        b = self.b
        self.open_review()
        b.click(self.reject_button(PLAIN))
        self.menu_open()
        b.key("2")
        b.wait("!!document.getElementById('rjDupH') && !document.querySelector('#rvReason .rjwait')", 15)
        self.assertTrue(b.eval("!!document.querySelector('#rvReason [data-dupof=\"\"]')"))     # Don't name it
        b.key("Escape")                                                            # back to the reasons
        b.wait("!document.getElementById('rjDupH') && !!document.querySelector('#rvReason [data-reason]')")
        b.key("2")
        b.wait("!!document.getElementById('rjDupH') && !document.querySelector('#rvReason .rjwait')", 15)
        b.click('#rvReason [data-dupof=""]')
        its = self.wait_rejected([5])
        self.assertEqual((its[5]["reject_reason"], its[5].get("duplicate_of")), ("Duplicate", None))
        # a row whose look-alike is known records it with no question
        b.click(self.reject_button(self.dup_text))
        self.menu_open()
        self.assertIn(f"of {self.dup_id}", b.eval("document.querySelector('#rvReason [data-reason=Duplicate]').textContent"))
        b.key("2")
        its = self.wait_rejected([2])
        self.assertEqual(its[2].get("duplicate_of"), self.dup_id)


class RejectsNarrow(LiveBrowserCase):
    """320 px: the menu fits, with no sideways scroll."""
    width, height = 320, 800

    @classmethod
    def load(cls, v):
        RejectsUI.load.__func__(cls, v)

    def test_320_px_no_sideways_scroll(self):
        b = self.b
        b.eval("go('intake-review')")
        b.wait("!!document.querySelector('#v-intake-review [data-irsec=other]') && !!document.querySelector('#v-intake-review [data-irsec=other]').parentElement.querySelector('tr.irprop')")
        n = b.eval(f"REV.find(r=>r.rec.t==={THANKS!r}).n")
        b.eval(f"document.querySelector('#v-intake-review tr.irprop[data-irn=\"{n}\"]').focus()")
        b.key("r")
        b.wait("!!document.getElementById('rvReason')")
        box = b.eval("(()=>{ const r=document.getElementById('rvReason').getBoundingClientRect(); return [r.left,r.right,innerWidth]; })()")
        self.assertGreaterEqual(box[0], 0)
        self.assertLessEqual(box[1], box[2])
        self.assertLessEqual(b.eval("document.documentElement.scrollWidth"), b.eval("innerWidth"))
        b.key("3")
        b.wait(f"!REV.some(r=>r.n=={n}&&!r.done)", 20)
        self.assertLessEqual(b.eval("document.documentElement.scrollWidth"), b.eval("innerWidth"))
        self.assertFalse(b.eval("/\\bVIP\\b/.test(document.getElementById('v-intake-review').textContent)"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
