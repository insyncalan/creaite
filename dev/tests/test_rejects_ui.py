"""BL-315 (v1.9.2), the screens: Rejects, in real life, in a real browser against the real live server (Team 2's routes on
v192-reject-reasons). One test per Done-when point:

- Review selects as Work does (click, ⌘-click, Shift-click, Space, Esc) and the bar shows the split, Select all, Approve,
  Reject with a reason (R) and ✕;
- R, the bar, ✕ and ▾ (and Shift+R, the row's menu with Shift+F10, the peek's Reject) all open the one menu: "Reject n
  because", the seven on 1 to 7, Use each guess (G), No reason (0); Esc closes it and focus goes back;
- a number key, G and 0 reject one or many with the right reasons; Duplicate records the item it names, or asks for it;
- the guesses show on the rows in grey and G uses them;
- a batch's Undo puts every row back in Review;
- a rejected row stays greyed with its chip until Review is left; the chip changes its reason (with Undo), and so does
  Activity › Quality › What you rejected;
- Approve instead approves a rejected item in one step; a new risk goes back to Review and its proposal opens (never
  approved in bulk);
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
        b.eval("go('review')")
        b.wait("document.querySelector('#reviewBody tr[data-n]')")
        b.wait("Object.keys(rjGuesses.value).length>=4", 15)                 # the guesses have come

    def n(self, text):
        return self.b.eval(f"(REV.find(r=>r.rec.t.startsWith({text!r})&&!r.done)||{{}}).n")

    def row(self, text):
        return f'#reviewBody tr[data-n="{self.n(text)}"]'

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

    def pick_rows(self, *texts):
        b = self.b
        ns = [self.n(t) for t in texts]
        b.eval(f"RHL.clear(); {json.dumps(ns)}.forEach(n=>RHL.add(n)); rvSyncChk(); renderReview()")
        b.wait("!document.getElementById('rvbar').hidden")
        return ns

    def click_text(self, text, modifiers=0):
        """A real click on a row's own words (the title cell's centre can be a link to a person)."""
        b = self.b
        pos = b.eval(f"""(()=>{{ const td=document.querySelector('{self.row(text)} td.title'); td.scrollIntoView({{block:'center'}}); const w=document.createTreeWalker(td,NodeFilter.SHOW_TEXT);
          let t; while((t=w.nextNode())&&!t.textContent.trim()); const r=document.createRange(); r.selectNodeContents(t); const q=r.getBoundingClientRect();
          return {{x:q.left+Math.min(20,q.width/2),y:q.top+q.height/2}}; }})()""")
        for kind in ("mouseMoved", "mousePressed", "mouseReleased"):
            b.call("Input.dispatchMouseEvent", type=kind, x=pos["x"], y=pos["y"], button="left", clickCount=1, modifiers=modifiers)
        b.pump(0.1)

    def menu_open(self):
        self.b.wait("!!document.getElementById('rvReason') && document.getElementById('rvReason').contains(document.activeElement)")

    # ── 1. Review selects as Work does; the bar ──
    def test_selection_and_the_bar(self):
        b = self.b
        self.open_review()
        self.click_text(THANKS)
        self.assertEqual(b.eval("RHL.size"), 1)
        self.click_text(PLAIN, modifiers=4)                                        # ⌘-click adds
        self.assertEqual(b.eval("RHL.size"), 2)
        self.click_text(PLAIN, modifiers=4)                                        # and removes
        self.assertEqual(b.eval("RHL.size"), 1)
        self.click_text(RISK, modifiers=8)                                         # Shift-click: the range
        self.assertEqual(sorted(b.eval("[...RHL]")), sorted([self.n(PLAIN), self.n(RISK)]))   # from the anchor (PLAIN) to RISK
        bar = b.eval("document.getElementById('rvbar').textContent")
        self.assertRegex(bar, r"\d+ selected")
        self.assertRegex(bar, r"\d+ can be approved together")
        self.assertIn("needs individual approval", bar)                           # the new risk
        self.assertIn("Reject with a reason", bar)
        self.assertEqual(b.eval("document.getElementById('bulkReject').getAttribute('aria-haspopup')"), "menu")
        self.assertEqual(b.eval("document.querySelector('#bulkReject .kbd').textContent"), "R")
        self.assertIsNone(b.eval("document.getElementById('bulkRejectWhy')"))
        self.assertTrue(b.eval("!!document.getElementById('rvClear')"))
        b.key("Escape")                                                            # Esc clears
        b.wait("RHL.size===0 && document.getElementById('rvbar').hidden")
        b.eval(f"RSEL=[...document.querySelectorAll('#reviewBody tr[data-n]')].findIndex(t=>+t.dataset.n==={self.n(PLAIN)}); renderReview()")
        b.key(" ")                                                                 # Space toggles
        b.wait("RHL.size===1")
        self.assertIn("Select all", b.eval("document.getElementById('rvAll').textContent"))

    # ── 2. R, the bar, ✕ and ▾ open the one menu ──
    def test_every_way_in_opens_the_one_menu(self):
        b = self.b
        self.open_review()
        want = [*SEVEN, "Use each guess", "No reason"]
        # a row's ✕
        b.click(self.row(PLAIN) + " [data-act=r]")
        self.menu_open()
        self.assertEqual(self.menu_texts(), want)
        self.assertEqual(b.eval("[...document.querySelectorAll('#rvReason .kbd')].map(k=>k.textContent)"), [*"1234567", "G", "0"])
        self.assertEqual(b.eval("document.getElementById('rvReason').getAttribute('aria-label')"), "Reject this because")
        self.assertEqual(b.eval("document.getElementById('rvReason').getAttribute('role')"), "menu")
        self.assertEqual(b.eval(f"document.querySelector('{self.row(PLAIN)} [data-act=r]').getAttribute('aria-expanded')"), "true")
        self.assertEqual(b.eval("document.querySelector('#rvReason [data-reason=guess]').getAttribute('aria-disabled')"), "true")   # no guess for it
        b.key("ArrowDown")
        self.assertEqual(b.eval("document.activeElement.dataset.reason"), "Duplicate")
        b.key("End")
        self.assertEqual(b.eval("document.activeElement.dataset.reason"), "")
        b.key("Escape")                                                            # Esc closes; focus back on ✕
        b.wait("!document.getElementById('rvReason')")
        self.assertEqual(b.eval("document.activeElement.dataset.act"), "r")
        self.assertEqual(b.eval(f"document.querySelector('{self.row(PLAIN)} [data-act=r]').getAttribute('aria-expanded')"), "false")
        # a row's ▾
        b.click(self.row(THANKS) + " [data-act=rr]")
        self.menu_open()
        self.assertIsNone(b.eval("document.querySelector('#rvReason [data-reason=guess]').getAttribute('aria-disabled')"))
        self.assertIn("(Chatter)", b.eval("document.querySelector('#rvReason [data-reason=guess]').textContent"))
        b.key("Escape")
        b.wait("!document.getElementById('rvReason')")
        # R on the cursor row, and Shift+R
        b.eval(f"RHL.clear(); RSEL=[...document.querySelectorAll('#reviewBody tr[data-n]')].findIndex(t=>+t.dataset.n==={self.n(PLAIN)}); renderReview(); document.activeElement.blur()")
        b.key("r")
        self.menu_open()
        b.key("Escape")
        b.wait("!document.getElementById('rvReason')")
        b.key("R", modifiers=8)
        self.menu_open()
        b.key("Escape")
        b.wait("!document.getElementById('rvReason')")
        # the bar, for several
        self.pick_rows(THANKS, CAL, ROOM)
        b.click("#bulkReject")
        self.menu_open()
        self.assertEqual(b.eval("document.getElementById('rvReason').getAttribute('aria-label')"), "Reject 3 because")
        self.assertEqual(b.eval("document.getElementById('bulkReject').getAttribute('aria-expanded')"), "true")
        b.key("Escape")
        b.wait("!document.getElementById('rvReason')")
        self.assertEqual(b.eval("document.activeElement.id"), "bulkReject")
        # R with rows highlighted: the menu for all of them
        b.eval("document.activeElement.blur()")
        b.key("r")
        self.menu_open()
        self.assertEqual(b.eval("document.getElementById('rvReason').getAttribute('aria-label')"), "Reject 3 because")
        b.key("Escape")
        b.wait("!document.getElementById('rvReason')")
        # the row's menu: Shift+F10 on the cursor row, then Reject with a reason…
        b.eval(f"RHL.clear(); RSEL=[...document.querySelectorAll('#reviewBody tr[data-n]')].findIndex(t=>+t.dataset.n==={self.n(PLAIN)}); renderReview(); document.activeElement.blur()")
        b.eval('document.body.dispatchEvent(new KeyboardEvent("keydown",{key:"F10",shiftKey:true,bubbles:true}))')
        b.wait("!!document.querySelector('.cxmenu')")
        labels = b.eval("[...document.querySelectorAll('.cxmenu [role=menuitem] span')].map(s=>s.textContent)")
        self.assertIn("Reject with a reason…", labels)
        b.eval("[...document.querySelectorAll('.cxmenu [role=menuitem]')].find(x=>x.textContent.includes('Reject with a reason')).focus()")
        b.key("Enter")
        self.menu_open()
        b.key("Escape")
        b.wait("!document.getElementById('rvReason')")
        # the peek's Reject
        b.click(self.row(PLAIN) + " td.title", count=2)
        b.wait("!!document.getElementById('pkReject') && document.getElementById('pkReject').offsetParent!==null")
        b.click("#pkReject")
        self.menu_open()
        self.assertEqual(b.eval("document.getElementById('pkReject').getAttribute('aria-expanded')"), "true")
        b.key("Escape")
        b.wait("!document.getElementById('rvReason')")
        self.assertTrue(b.eval("document.getElementById('panel').classList.contains('on')"))   # Esc leaves the peek open
        self.assertFalse(b.eval("/VIP/.test(document.getElementById('rjMenuHost').textContent)"))

    # ── 3. a number key, G and 0 reject one or many with the right reasons ──
    def test_number_keys_g_and_0_reject_with_the_right_reasons(self):
        b = self.b
        self.open_review()
        self.pick_rows(THANKS, CAL)
        b.key("r")
        self.menu_open()
        b.key("3")                                                                 # Chatter, for both
        b.wait("!document.getElementById('rvReason')")
        its = self.wait_rejected([1, 4])
        self.assertEqual({its[1]["reject_reason"], its[4]["reject_reason"]}, {"Chatter"})
        b.wait("/Rejected 2 as Chatter/.test(document.getElementById('rvresult').textContent)", 15)
        # 0: no reason, on the cursor row
        b.wait(f"!!REV.find(r=>r.rec.t==={PLAIN!r}&&!r.done)")
        b.eval(f"RHL.clear(); RSEL=[...document.querySelectorAll('#reviewBody tr[data-n]')].findIndex(t=>+t.dataset.n==={self.n(PLAIN)}); renderReview(); document.activeElement.blur()")
        b.key("r")
        self.menu_open()
        b.key("0")
        its = self.wait_rejected([5])
        self.assertNotIn("reject_reason", its[5])
        # G on one row: its own guess
        b.wait(f"!!REV.find(r=>r.rec.t==={ROOM!r}&&!r.done)")
        b.click(self.row(ROOM) + " [data-act=rr]")
        self.menu_open()
        b.key("g")
        its = self.wait_rejected([3])
        self.assertEqual(its[3]["reject_reason"], "Doesn't need tracking")
        # 7 for one row, by the mouse this time
        b.wait(f"!!REV.find(r=>r.rec.t==={KEYS!r}&&!r.done)")
        b.click(self.row(KEYS) + " [data-act=r]")
        self.menu_open()
        b.click('#rvReason [data-reason="For another team"]')
        its = self.wait_rejected([7])
        self.assertEqual(its[7]["reject_reason"], "For another team")
        # the reasons reach the tracker's record and the quality view
        got = self.reasons()
        self.assertTrue({("Chatter", None), ("Doesn't need tracking", None), ("For another team", None)} <= got, got)
        self.assertIn((None, None), got)
        b.wait("((D.quality||{}).reasons||[]).some(r=>r.reason==='Chatter')", 15)
        self.assertEqual(b.eval("D.quality.reasons.find(r=>r.reason==='Chatter').n"), 2)

    # ── 4. the guesses show and G uses them; Duplicate records the item ──
    def test_the_guesses_show_and_g_uses_them(self):
        b = self.b
        self.open_review()
        self.assertIn("guess: Chatter", b.eval(f"document.querySelector('{self.row(THANKS)}').textContent"))
        self.assertIn("guess: Doesn't need tracking", b.eval(f"document.querySelector('{self.row(ROOM)}').textContent"))
        self.assertIn(f"guess: Duplicate (looks like {self.dup_id})", b.eval(f"document.querySelector('{self.row(self.dup_text)}').textContent"))
        self.assertNotIn("guess:", b.eval(f"document.querySelector('{self.row(PLAIN)}').textContent"))
        self.assertEqual(b.eval(f"getComputedStyle(document.querySelector('{self.row(THANKS)} .rvguess')).color"),
                         b.eval(f"getComputedStyle(document.querySelector('{self.row(THANKS)} .why')).color"))   # grey, as the line it is on
        self.pick_rows(THANKS, self.dup_text, ROOM, CAL, PLAIN)
        b.click("#bulkReject")
        self.menu_open()
        self.assertIn("4 of 5 have a guess", b.eval("document.querySelector('#rvReason [data-reason=guess]').title"))
        b.key("G", modifiers=8)
        its = self.wait_rejected([1, 2, 3, 4, 5])
        self.assertEqual([its[r].get("reject_reason") for r in (1, 2, 3, 4, 5)], ["Chatter", "Duplicate", "Doesn't need tracking", "Chatter", None])
        self.assertEqual(its[2].get("duplicate_of"), self.dup_id)
        self.assertIn(("Duplicate", self.dup_id), self.reasons())
        b.wait("/Rejected 5 with their guesses/.test(document.getElementById('rvresult').textContent)", 15)

    # ── 5. a batch's Undo restores all ──
    def test_a_batch_undo_puts_every_row_back(self):
        b = self.b
        self.open_review()
        ns = self.pick_rows(THANKS, ROOM, PLAIN)
        b.key("r")
        self.menu_open()
        b.key("1")
        self.wait_rejected([1, 3, 5])
        b.wait("/Rejected 3 as Not an action/.test(document.getElementById('rvresult').textContent)", 15)
        self.assertEqual(b.eval("document.querySelectorAll('#reviewBody tr[data-gone]').length"), 3)
        b.wait("document.getElementById('snack').classList.contains('on') && document.getElementById('snackU').style.display!=='none'")
        b.click("#snackU")                                                         # the message's one Undo
        b.wait(f"[{THANKS!r},{ROOM!r},{PLAIN!r}].every(t=>REV.some(r=>r.rec.t===t&&!r.done))", 20)
        b.wait("document.querySelectorAll('#reviewBody tr[data-gone]').length===0")
        for ref in (1, 3, 5):
            self.assertEqual(self.item(ref)["decision"], "pending")
        self.assertEqual(b.eval("RHL.size"), 3)                                    # back as they were, highlighted
        self.assertEqual(len(ns), 3)
        b.wait("/Back in Review: 3/.test(document.getElementById('snackT').textContent)")

    # ── 6. a rejected row stays greyed with its chip; the chip changes the reason; leaving Review clears it ──
    def test_the_chip_changes_the_reason_and_undo_puts_it_back(self):
        b = self.b
        self.open_review()
        b.click(self.row(THANKS) + " [data-act=rr]")
        self.menu_open()
        b.key("3")
        self.wait_rejected([1])
        chip = '#reviewBody tr[data-gone] [data-rjchip]'
        b.wait(f"!!document.querySelector('{chip}')", 15)
        self.assertEqual(b.eval(f"document.querySelector('{chip}').textContent"), "Rejected · Chatter")
        self.assertEqual(b.eval(f"document.querySelector('{chip}').getAttribute('aria-label')"), "Rejected · Chatter: change the reason")
        self.assertIsNone(b.eval("document.querySelector('#reviewBody tr[data-gone]').dataset.n||null"))     # no cursor number
        self.assertIn(THANKS, b.eval("document.querySelector('#reviewBody tr[data-gone]').textContent"))
        b.click(chip)
        self.menu_open()
        self.assertEqual(b.eval("document.getElementById('rvReason').getAttribute('aria-label')"), "Rejected because")
        self.assertEqual(b.eval("document.querySelector('#rvReason [aria-current=true]').dataset.reason"), "Chatter")
        b.key("2")                                                                 # Duplicate: no item named, so it asks
        b.wait("document.activeElement && document.activeElement.id==='rjDupId'")
        self.assertEqual(b.eval("document.getElementById('rvReason').getAttribute('aria-label')"), "Duplicate of which item?")
        b.type("abc-a-zz")
        b.key("Enter")
        b.wait("!!document.getElementById('rjDupBad')")                            # not an ID: said, nothing sent
        b.eval("document.getElementById('rjDupId').select()")
        b.type(self.dup_id.lower())
        b.key("Enter")
        b.wait(f"document.querySelector('{chip}') && document.querySelector('{chip}').textContent==='Rejected · Duplicate ({self.dup_id})'", 20)
        for _ in range(200):
            it = self.item(1)
            if it.get("reject_reason") == "Duplicate" and it.get("applied"):
                break
            b.pump(0.1)
        self.assertEqual((it["reject_reason"], it.get("duplicate_of")), ("Duplicate", self.dup_id))
        b.wait("[...document.querySelectorAll('#reviewBody tr[data-gone]')].length===1", 10)
        rows = [r for r in self.v.rows("rejected") if r["reason"] == "Duplicate"]
        self.assertEqual([r["duplicate_of"] for r in rows], [self.dup_id])         # the record follows: one row, updated
        b.wait("/Reason changed to Duplicate/.test(document.getElementById('snackT').textContent)")
        b.click("#snackU")                                                         # the change has its Undo
        b.wait(f"document.querySelector('{chip}') && document.querySelector('{chip}').textContent==='Rejected · Chatter'", 20)
        for _ in range(200):
            it = self.item(1)
            if it.get("reject_reason") == "Chatter" and it.get("applied"):
                break
            b.pump(0.1)
        self.assertEqual(it.get("reject_reason"), "Chatter")
        self.assertNotIn("duplicate_of", it)
        # the ▾ on the greyed row opens the same menu
        b.click("#reviewBody tr[data-gone] [data-rjrr]")
        self.menu_open()
        b.key("Escape")
        b.wait("!document.getElementById('rvReason')")
        # leaving Review: the greyed rows go
        b.eval("go('today')")
        b.eval("go('review')")
        b.wait("document.querySelectorAll('#reviewBody tr[data-gone]').length===0 && rjGone.value.length===0")

    # ── 7. Approve instead: one step; a new risk goes back to Review and opens ──
    def test_approve_instead_in_one_step_and_the_bulk_rule(self):
        b = self.b
        self.open_review()
        self.pick_rows(PLAIN, RISK)
        b.key("r")
        self.menu_open()
        b.key("1")
        self.wait_rejected([5, 6])
        b.wait("document.querySelectorAll('#reviewBody tr[data-gone]').length===2", 15)
        ok = '#reviewBody tr[data-gone] [data-rjok]'
        self.assertEqual(b.eval(f"[...document.querySelectorAll('{ok}')].map(x=>x.textContent)"), ["Approve instead", "Approve instead"])
        b.click("#reviewBody tr[data-gone=\"proposed-rj.json#5\"] [data-rjok]")
        b.wait(f"A.some(a=>a.t==={PLAIN!r})", 20)                                   # approved and applied in one step
        b.wait("/Approved instead: 1/.test(document.getElementById('rvresult').textContent)")
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
        b.wait("document.querySelectorAll('#reviewBody tr[data-gone]').length===2", 15)
        # the new risk: never approved in bulk; back in Review, its proposal opened
        b.click("#reviewBody tr[data-gone=\"proposed-rj.json#6\"] [data-rjok]")
        b.wait(f"REV.some(r=>r.rec.t==={RISK!r}&&!r.done)", 20)
        b.wait("CUR && CUR.mode==='proposal' && document.getElementById('panel').classList.contains('on')", 10)
        self.assertFalse(b.eval(f"R.some(r=>r.t==={RISK!r})"))
        self.assertEqual(self.item(6)["decision"], "pending")
        self.assertIn("1 needs approving on its own", b.eval("document.getElementById('rvresult').textContent"))

    # ── 6b, 7b. Activity › Quality › What you rejected: the chip, Approve instead and Undo ──
    def test_activity_lists_the_rejects_with_the_chip(self):
        b = self.b
        self.open_review()
        self.pick_rows(THANKS, ROOM, KEYS)
        b.key("r")
        self.menu_open()
        b.key("g")
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
        # Undo from the list: back in Review
        b.click('#qRejects li[data-rjkey="proposed-rj.json#3"] [data-rjundo]')
        b.wait("!document.querySelector('#qRejects li[data-rjkey=\"proposed-rj.json#3\"]')", 20)
        self.assertEqual(self.item(3)["decision"], "pending")
        # Approve instead from the list
        b.click('#qRejects li[data-rjkey="proposed-rj.json#7"] [data-rjok]')
        b.wait(f"A.some(a=>a.t==={KEYS!r})", 20)
        b.wait("!document.querySelector('#qRejects li[data-rjkey=\"proposed-rj.json#7\"]')", 20)

    # ── 8. Duplicate with no item named asks: the look-alikes, an ID, or none ──
    def test_duplicate_asks_for_the_item(self):
        b = self.b
        self.open_review()
        b.click(self.row(PLAIN) + " [data-act=rr]")
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
        b.click(self.row(self.dup_text) + " [data-act=rr]")
        self.menu_open()
        self.assertIn(f"of {self.dup_id}", b.eval("document.querySelector('#rvReason [data-reason=Duplicate]').textContent"))
        b.key("2")
        its = self.wait_rejected([2])
        self.assertEqual(its[2].get("duplicate_of"), self.dup_id)


class RejectsNarrow(LiveBrowserCase):
    """320 px: the bar, the menu and the greyed rows fit, with no sideways scroll."""
    width, height = 320, 800

    @classmethod
    def load(cls, v):
        RejectsUI.load.__func__(cls, v)

    def test_320_px_no_sideways_scroll(self):
        b = self.b
        b.eval("go('review')")
        b.wait("document.querySelector('#reviewBody tr[data-n]')")
        n = b.eval(f"REV.find(r=>r.rec.t==={THANKS!r}).n")
        b.eval(f"RHL.clear(); RHL.add({n}); rvSyncChk(); renderReview()")
        b.wait("!document.getElementById('rvbar').hidden")
        b.eval("document.activeElement.blur()")
        b.key("r")
        b.wait("!!document.getElementById('rvReason')")
        box = b.eval("(()=>{ const r=document.getElementById('rvReason').getBoundingClientRect(); return [r.left,r.right,innerWidth]; })()")
        self.assertGreaterEqual(box[0], 0)
        self.assertLessEqual(box[1], box[2])
        self.assertLessEqual(b.eval("document.documentElement.scrollWidth"), b.eval("innerWidth"))
        b.key("3")
        b.wait("!!document.querySelector('#reviewBody tr[data-gone] [data-rjchip]')", 20)
        self.assertLessEqual(b.eval("document.documentElement.scrollWidth"), b.eval("innerWidth"))
        self.assertFalse(b.eval("/\\bVIP\\b/.test(document.getElementById('reviewBody').textContent)"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
