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
    item = {"n": n, "op": "update", "table": "actions", "id": ident, "match": "strong", "flags": [], "decision": "pending",
            "changes": changes, "why": "the supplier confirmed", "source": S.MAIL, **extra}
    return {k: v for k, v in item.items() if v is not None}                                   # why=None: an update with no reason (its row title is the change)


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
            upd(2, cls.cio, {"status": cls.live[cls.cio]["status"], "due_date": "2026-12-02"}, why=None),   # the status it already has: plain
            upd(3, "ABC-A-001", {"due_date": "2026-12-05"}, flags=["conflict"], why="old news"),
            upd(4, "ABC-A-998", {"due_date": "2026-12-03"}, why="gone"),
            upd(5, "ABC-A-001", {"client_message": "What it is: SECRETWORDING\nWhat it means for you: x\nWhat is being done: y"}, flags=["conflict"], why="wording")])                                        # no such item
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

    def test_a_conflict_never_shows_the_client_message_text(self):
        b = self.b
        S.open_page(b)
        row = "[...document.querySelectorAll('#v-intake-review tr.irprop[data-kind=update]')].find(t=>t.querySelector('.cfvs')&&/client messag/i.test(t.querySelector('.cfvs').textContent))"
        self.assertTrue(b.eval(f"!!({row})"))
        self.assertNotIn("SECRETWORDING", b.eval(f"({row}).textContent"))
        self.assertIn("client message: changed", b.eval(f"({row}).querySelector('.cfvs').textContent"))
        b.eval(f"({row}).querySelector('.icttl').click()")
        b.wait("!!document.querySelector('#pkUpd .cfvs')")
        self.assertNotIn("SECRETWORDING", b.eval("document.getElementById('panel').textContent"))
        self.assertIn("client message: changed", b.eval("document.querySelector('#pkUpd .cfvs').textContent"))

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

    def test_the_rows_line_names_the_item_and_says_the_latest_update_in_words(self):
        b = self.b
        S.open_page(b)
        line = b.eval(f"[...document.querySelectorAll('{ROW}')].find(t=>t.querySelector('.icchg').textContent.includes({self.uat!r})).querySelector('.icchg').textContent")
        old = self.live[self.uat]["due_date"]
        self.assertIn(f"Updates {self.uat}: {UAT} · due {old[8:10]}-{old[5:7]}-{old[:4]} → 01-12-2026 and the latest update", line)
        self.assertNotIn("The supplier confirmed", line)                                    # the long text is not in the line


class UpdatePeekSaves(LiveBrowserCase, Fixture):
    """Saving in the peek: the edited columns are written, the rest of the proposal is left as it was."""
    width, height = 1400, 1100

    @classmethod
    def load(cls, v):
        Fixture.load.__func__(cls, v)

    def staged(self, ident):
        for f in sorted((self.v.root / "system/staging").glob("proposed-*.json")):
            data = json.loads(f.read_text())
            for it in data.get("items", []):
                if it.get("id") == ident and it.get("op") == "update":
                    return f, it
        raise AssertionError(f"no staged update for {ident}")

    def n_of(self, ident):
        return self.b.eval(f"(D.review||REV).find(r=>r.kind==='update'&&r.rec.target==={ident!r}).n")

    def test_editing_the_due_date_saves_it_and_leaves_the_latest_update(self):
        b = self.b
        open_update(b, self.uat)
        n = self.n_of(self.uat)
        b.wait("!!document.querySelector('#pkUpdNote')")
        b.eval(f"pkCommit('actions','rv{n}',{{due:'2026-12-04'}},'Due date','x','y')")
        b.wait("document.querySelector('#pkProps [data-pkp=due]').textContent.includes('04-12-2026')")
        b.click("#pkPSave")
        b.wait("!document.getElementById('panel').classList.contains('on')")
        f, it = self.staged(self.uat)
        self.assertEqual(it["changes"], {"due_date": "2026-12-04", "latest_update": "The supplier confirmed a slot."})
        self.assertNotEqual(it.get("decision"), "approved")                                  # Save alone does not approve
        self.assertEqual(it.get("edited_in"), "dashboard")
        self.assertEqual(self.v.rows("actions")[0]["due_date"], self.live[self.v.rows("actions")[0]["id"]]["due_date"])   # nothing in the tracker yet

    def test_editing_the_status_and_approving_writes_it_with_the_other_columns(self):
        b = self.b
        open_update(b, self.uat)
        n = self.n_of(self.uat)
        b.wait("!!document.querySelector('#pkUpdNote')")
        b.eval(f"pkSetStatus('actions','rv{n}','Delayed')")
        b.wait("document.querySelector('#pkProps [data-pkp=st]').getAttribute('aria-label').includes('was Open, now Delayed')")
        b.click("#pkPSaveA")
        end = time.time() + 25
        row = None
        while time.time() < end:
            row = next(r for r in self.v.rows("actions") if r["id"] == self.uat)
            if row["status"] == "Delayed":
                break
            time.sleep(0.3)
        self.assertEqual((row["status"], row["due_date"], row["latest_update"]), ("Delayed", "2026-12-01", "The supplier confirmed a slot."))

    def test_a_status_edit_holds_the_row_again_and_the_line_follows(self):
        """Due and latest update are routine; add a status change in the peek and the row is held (irHold) and says so."""
        b = self.b
        open_update(b, self.uat)
        n = self.n_of(self.uat)
        b.wait("!!document.querySelector('#pkUpdNote')")
        self.assertEqual(b.eval(f"REV.find(r=>r.n==={n}).hold"), "")                          # routine before
        b.eval(f"pkSetStatus('actions','rv{n}','Delayed')")
        b.wait("document.querySelector('#pkProps [data-pkp=st]').getAttribute('aria-label').includes('now Delayed')")
        b.click("#pkPSave")
        b.wait("!document.getElementById('panel').classList.contains('on')")
        b.wait(f"REV.find(r=>r.n==={n}).hold==='status change'")
        line = b.eval(f"[...document.querySelectorAll('{ROW}')].find(t=>t.querySelector('.icchg').textContent.includes({self.uat!r})).querySelector('.icchg').textContent")
        self.assertIn("status Open → Delayed", line)
        self.assertIn("due ", line)

    def test_a_newer_edit_to_the_same_proposal_survives_a_save_from_an_older_window(self):
        """Window A opens the peek; the file then gains an owner change (another window, a cx-review edit); A edits the due date
        and saves: the owner change is still there, the due date is A's, the latest update as proposed."""
        b = self.b
        open_update(b, self.uat)
        n = self.n_of(self.uat)
        b.wait("!!document.querySelector('#pkUpdNote')")
        f, it = self.staged(self.uat)
        data = json.loads(f.read_text())
        for x in data["items"]:
            if x.get("id") == self.uat and x.get("op") == "update":
                x["changes"]["owner"] = "Omar Ali"
        f.write_text(json.dumps(data, indent=2))
        b.eval(f"pkCommit('actions','rv{n}',{{due:'2026-12-04'}},'Due date','x','y')")
        b.wait("document.querySelector('#pkProps [data-pkp=due]').textContent.includes('04-12-2026')")
        b.click("#pkPSave")
        b.wait("!document.getElementById('panel').classList.contains('on')")
        _, it = self.staged(self.uat)
        self.assertEqual(it["changes"], {"due_date": "2026-12-04", "latest_update": "The supplier confirmed a slot.", "owner": "Omar Ali"})
        self.assertNotEqual(it.get("decision"), "approved")

    def test_the_row_title_after_a_save_is_in_words(self):
        b = self.b
        open_update(b, self.cio)
        n = self.n_of(self.cio)
        b.wait("!!document.querySelector('#pkUpdNote')")
        b.eval(f"pkCommit('actions','rv{n}',{{due:'2026-12-04'}},'Due date','x','y')")
        b.wait("document.querySelector('#pkProps [data-pkp=due]').textContent.includes('04-12-2026')")
        b.click("#pkPSave")
        b.wait("!document.getElementById('panel').classList.contains('on')")
        title = b.eval(f"REV.find(r=>r.n==={n}).rec.t")
        self.assertIn("due 25-10-2026 → 04-12-2026", title)
        self.assertNotRegex(title, r"[a-z]_[a-z]")                                        # no column names ("due_date"), no raw values

    def test_a_conflict_hides_save_and_approve_and_shows_the_two_values(self):
        b = self.b
        S.open_page(b)
        b.eval("[...document.querySelectorAll('#v-intake-review tr.irprop[data-kind=update]')].find(t=>t.querySelector('.cfvs')).querySelector('.icttl').click()")
        b.wait("document.getElementById('panel').classList.contains('pkprop')")
        b.wait("!!document.querySelector('#pkUpd .cfvs')")
        self.assertTrue(b.eval("document.getElementById('pkPSaveA').hidden"))
        self.assertFalse(b.eval("document.getElementById('pkPSave').hidden"))
        b.eval("closePanel()")
        open_update(b, self.uat)
        b.wait("document.getElementById('panel').classList.contains('pkprop')")
        self.assertFalse(b.eval("document.getElementById('pkPSaveA').hidden"))                        # the next peek has it again

if __name__ == "__main__":
    unittest.main()
