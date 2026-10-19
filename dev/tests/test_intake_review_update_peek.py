"""#232-B (release 2.6): an update proposal opens the whole item in the peek (the app's right-hand panel) from Intake and Review.
The item as it is now, the changed fields marked `was → now` (against the live tracker row, not the proposal's own "from"), the
note "What changes if you approve" and the "If approved" activity line saying the same, a changed latest update shown old over new,
Status, Due and Latest update editable and every other field read-only, a conflict with no Save and approve, a target that has
gone falling back to the old form, and the update in the Previous and Next order. Nothing reaches the tracker until it is approved.

Run: python3 dev/tests/test_intake_review_update_peek.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import intake_review_support as S  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402

ROW = "#v-intake-review tr.irprop"
UAT, DEF = "Book UAT environment", "Agree pilot success criteria"


def upd(n, ident, changes, **extra):
    return {"n": n, "op": "update", "table": "actions", "id": ident, "match": "strong", "flags": [], "decision": "pending",
            "changes": changes, "why": "the supplier confirmed", "source": S.MAIL, **extra}


class Fixture:
    """The sample vault, the mail and meeting proposals, and four updates from a sweep."""

    @classmethod
    def load(cls, v):
        S.load(v)
        ids = {r["description"]: r["id"] for r in v.rows("actions")}
        cls.uat, cls.cio = ids[UAT], ids[DEF]
        cls.live = {r["id"]: r for r in v.rows("actions")}
        p = v.propose("2026-10-09-1000-sweep", [
            upd(1, cls.uat, {"due_date": "2026-12-01", "latest_update": "The supplier confirmed a slot."}),
            upd(2, cls.cio, {"status": cls.live[cls.cio]["status"], "due_date": "2026-12-02"}, why="same status"),   # the status it already has: plain
            upd(3, "ABC-A-001", {"due_date": "2026-12-05"}, flags=["conflict"], why="old news"),
            upd(4, "ABC-A-998", {"due_date": "2026-12-03"}, why="gone")])                                        # no such item
        data = json.loads(p.read_text())
        data["source_run"] = "cx-sweep"
        p.write_text(json.dumps(data, indent=2))


def click_update(b, ident):
    b.eval(f"[...document.querySelectorAll('{ROW}')].find(t=>t.querySelector('.icchg').textContent.includes({ident!r})).querySelector('.icttl').click()")


def open_update(b, ident):
    S.open_page(b)
    click_update(b, ident)
    b.wait("document.getElementById('panel').classList.contains('on')")


class UpdatePeek(LiveBrowserCase, Fixture):
    shared_server = True
    width, height = 1400, 1100

    @classmethod
    def load(cls, v):
        Fixture.load.__func__(cls, v)

    def chips(self):
        return self.b.eval("[...document.querySelectorAll('#pkProps .pk-chip, #pkProps2 .pk-chip')].map(c=>({n:(c.getAttribute('aria-label')||'').split(':')[0], "
                           "chg:c.classList.contains('chg'), ro:c.classList.contains('ro'), t:c.textContent.trim(), al:c.getAttribute('aria-label')}))")

    def test_the_whole_item_with_the_changed_fields_marked(self):
        b = self.b
        open_update(b, self.uat)
        b.wait("document.getElementById('panel').classList.contains('pkprop') && !!document.querySelector('#pkUpd')")
        self.assertIn("Update proposal", b.eval("document.getElementById('pkId').textContent"))
        self.assertIn(self.uat, b.eval("document.getElementById('pkId').textContent"))
        self.assertEqual(b.eval("document.getElementById('pkTitle').textContent"), UAT)                                    # the item's own text
        self.assertFalse(b.eval("document.getElementById('pkTitle').cxed.editor.isEditable"))                         # the item's own text is read-only here
        by = {c["n"]: c for c in self.chips()}
        self.assertEqual(set(by) >= {"Status", "Owner", "Due date", "Priority", "Project", "Workstream", "Milestone", "Client-visible"}, True, list(by))
        old = self.live[self.uat]["due_date"]
        fd = lambda iso: f"{iso[8:10]}-{iso[5:7]}-{iso[:4]}"          # noqa: E731
        self.assertTrue(by["Due date"]["chg"])
        self.assertIn(f"was {fd(old)}, now 01-12-2026", by["Due date"]["al"])
        for plain in ("Status", "Owner", "Priority", "Project", "Workstream", "Milestone", "Client-visible"):
            self.assertFalse(by[plain]["chg"], plain)
        for ro in ("Owner", "Priority", "Project", "Workstream", "Milestone", "Client-visible"):
            self.assertTrue(by[ro]["ro"], ro)
        self.assertFalse(by["Status"]["ro"])                                  # Status and Due are editable
        self.assertFalse(by["Due date"]["ro"])
        self.assertTrue(b.eval("!!document.querySelector('#pkProps [data-pkp=st]') && !!document.querySelector('#pkProps [data-pkp=due]') && !document.querySelector('#pkProps [data-pkp=o], #pkProps [data-pkp=pr], #pkProps [data-pkp=p]')"))

    def test_the_note_the_chips_and_the_if_approved_line_say_the_same(self):
        b = self.b
        open_update(b, self.uat)
        b.wait("!!document.querySelector('#pkUpdNote')")
        old = self.live[self.uat]["due_date"]
        want = (f"What changes if you approve: {self.uat} · {UAT}: due date {old[8:10]}-{old[5:7]}-{old[:4]} → 01-12-2026 and the latest update. "
                "The rest of the item stays as it is.")
        self.assertEqual(b.eval("document.getElementById('pkUpdNote').textContent"), want)
        pending = b.eval("document.querySelector('#pkFeed .pk-fe.pending').textContent")
        self.assertIn("If approved", pending)
        self.assertIn(f"Due date {old[8:10]}-{old[5:7]}-{old[:4]} → 01-12-2026", pending)
        self.assertIn("Latest update replaced", pending)
        self.assertIn("Last updated", b.eval("document.getElementById('pkUpdLast').textContent"))
        self.assertIn("Activity on " + self.uat, b.eval("document.getElementById('pkUpdLast').textContent"))

    def test_the_latest_update_shows_the_old_over_the_new_and_edits(self):
        b = self.b
        open_update(b, self.uat)
        b.wait("!!document.querySelector('#pkUpdWas .updiff')")
        was = self.live[self.uat]["latest_update"]
        self.assertIn("Now", b.eval("document.getElementById('pkUpdWas').textContent"))
        self.assertEqual(b.eval("document.getElementById('pkDescL').textContent"), "New latest update")
        self.assertEqual(b.eval("document.getElementById('pkDesc').textContent"), "The supplier confirmed a slot.")
        self.assertNotEqual(b.eval("document.querySelector('#pkUpdWas s')?.textContent"), "The supplier confirmed a slot.")
        if was:
            self.assertEqual(b.eval("document.querySelector('#pkUpdWas s').textContent"), was)
        self.assertTrue(b.eval("document.getElementById('pkDesc').cxed.editor.isEditable"))                           # the latest update is editable

    def test_a_status_the_item_already_has_is_plain_and_the_note_leaves_it_out(self):
        b = self.b
        open_update(b, self.cio)
        b.wait("!!document.querySelector('#pkUpdNote')")
        by = {c["n"]: c for c in self.chips()}
        self.assertFalse(by["Status"]["chg"], by["Status"])
        self.assertTrue(by["Due date"]["chg"], by["Due date"])
        note = b.eval("document.getElementById('pkUpdNote').textContent")
        self.assertIn("due date", note)
        self.assertNotIn("status", note)

    def test_the_target_that_has_gone_falls_back_to_the_old_form(self):
        b = self.b
        S.open_page(b)
        click_update(b, "ABC-A-998")
        b.wait("document.getElementById('panel').classList.contains('on')")
        self.assertFalse(b.eval("document.getElementById('panel').classList.contains('peek')"))
        self.assertIn("Proposed value", b.eval("document.getElementById('panel').textContent"))
        self.assertIn("no longer in the tracker", b.eval("document.getElementById('snack')?.textContent||document.body.textContent"))

    def test_previous_and_next_include_the_updates(self):
        b = self.b
        open_update(b, self.uat)
        b.wait("document.getElementById('panel').classList.contains('pkprop')")
        first = b.eval("irPeek.value")
        fwd, back = ("#pkNext", "#pkPrev") if not b.eval("document.getElementById('pkNext').disabled") else ("#pkPrev", "#pkNext")
        self.assertFalse(b.eval(f"document.querySelector({fwd!r}).disabled"))                      # an update has a neighbour in the order
        b.click(fwd)
        b.wait(f"irPeek.value!=={first!r}")
        b.click(back)
        b.wait(f"irPeek.value==={first!r}")
        self.assertIn(self.uat, b.eval("document.getElementById('pkId').textContent"))


if __name__ == "__main__":
    unittest.main()
