"""v2.3.0 #153: "I sent it" logs the work, Copy ID and title, one name (Draft email).

Run: python3 dev/tests/test_sent_it_person_menu.py   (needs Google Chrome; skipped otherwise)

Real Chrome against the real live server, the clock pinned with CREAITE_NOW (Tuesday 13-10-2026). Nothing is sent. I sent it in the
Draft email pane and in a person's popup (update and chase modes) stages one dated Latest update per ticked item through the
peek's own staging (a proposal already approved, source_run dashboard), records chases.json as before (item IDs, date, mode),
returns to the item or closes the popup, and one Undo takes the whole batch back. Unticked items are untouched. Then
More > Copy ID and title, and the names.
"""
import glob
import json
import sqlite3
import sys
from contextlib import closing
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_draft_chase_pane import CLIPBOARD, ChaseCase  # noqa: E402
from test_tracker import action  # noqa: E402



def shown(b):
    """The page's own today, as Alan reads it (DD-MM-YYYY)."""
    return b.eval("fd(TODAY)")


def staged(root, item_id):
    """Every staged dashboard proposal's update item for item_id: [(file, item)]."""
    out = []
    for f in sorted(glob.glob(str(root / "system/staging/proposed-*-dashboard*.json"))):
        data = json.loads(Path(f).read_text())
        for it in data.get("items", []):
            if it.get("id") == item_id and it.get("op") == "update":
                out.append((f, it))
    return out


class SentCase(ChaseCase):
    @classmethod
    def load(cls, v):
        super().load(v)
        v.propose("more", [
            action(8, description="Send the test scripts", owner="Sara Example", due_date="2026-10-08", priority="High", raised="2026-10-05",
                   latest_update="Scripts half written", source="Email · Subject: scripts · Sent: 2026-10-05 10:00"),
            action(9, description="Book the UAT room", owner="Sara Example", due_date="2026-10-09", raised="2026-10-05",
                   source="Email · Subject: room · Sent: 2026-10-05 10:00"),
            action(11, description="Confidential: review the retention terms", owner="Sara Example", due_date="2026-10-08", raised="2026-10-05",
                   latest_update="Terms with legal", source="Email · Subject: terms · Sent: 2026-10-05 10:00"),
            action(10, description="Confirm the go-live checklist", owner="Sara Example", due_date="2026-10-30", raised="2026-10-05",
                   source="Email · Subject: checklist · Sent: 2026-10-05 10:00"),
        ])
        v.run("apply")
        ids = {r["description"]: r["id"] for r in v.rows("actions")}
        cls.s_scripts, cls.s_room, cls.s_check = ids["Send the test scripts"], ids["Book the UAT room"], ids["Confirm the go-live checklist"]
        cls.s_conf = ids["Confidential: review the retention terms"]

    def chase_records(self):
        f = self.v.root / "system/staging/chases.json"
        return json.loads(f.read_text())["chases"] if f.exists() else []

    def open_person_email(self, mode):
        self.b.eval("S.ownDomains=['client.com','example.com']")                              # every item starts ticked, as for a colleague
        self.b.eval(f"go('person','Sara Example'); openDraftEmail('Sara Example',{mode!r})")
        self.b.wait("document.getElementById('deDlg').open&&document.querySelector('#deInc [data-deit]')")

    def undo(self):
        self.b.click("#snackU")
        self.b.pump(0.6)


class PaneISentIt(SentCase):
    shared_server = True

    def test_chase_stages_the_dated_update_returns_to_the_item_and_undo_removes_it(self):
        b = self.b
        self.chase(self.theirs)
        b.eval(CLIPBOARD)
        b.click("#chCopyText")
        b.click("#chSent")
        b.wait("document.getElementById('pkChase').hidden")
        self.assertTrue(b.eval("!document.getElementById('pkScroll').hidden"), "back on the open item")
        got = staged(self.v.root, self.theirs)
        self.assertEqual(len(got), 1)
        f, it = got[0]
        data = json.loads(Path(f).read_text())
        self.assertEqual(data["source_run"], "dashboard")
        self.assertEqual(data["items"][0]["decision"], "approved")
        upd = it["changes"]["latest_update"]
        first, _, rest = upd.partition("\n")
        self.assertRegex(first, rf"^{shown(b)}: Chased Sara Example by message \(reminder 1\); reply asked for by \d\d-\d\d-2026\.$")
        self.assertEqual(rest, "Plan in draft, waiting on the test environment dates")      # the earlier update is kept under it
        self.assertEqual(it["note"], "Draft email: I sent it")
        self.assertNotIn("Dear", json.dumps(data))                                           # never the email's text
        recs = json.loads((self.v.root / "system/staging/chases.json").read_text())["chases"]
        self.assertEqual([(r["ids"], r["mode"]) for r in recs], [([self.theirs], "chase")])
        self.assertEqual(b.eval("document.getElementById('snackT').textContent"), "Logged.")
        self.undo()
        self.assertEqual(staged(self.v.root, self.theirs), [])
        self.assertEqual(b.eval(f"REC('actions',{self.theirs!r}).upd"), "Plan in draft, waiting on the test environment dates")
        self.assertEqual(b.errors, [])

    def test_zz_failed_staging_message_survives_the_pane_closing(self):
        b = self.b
        self.chase(self.theirs)
        b.eval("window.__w=shared.VW.write; shared.VW.write=async()=>{ throw new Error('disk full') }")       # the staging write fails
        try:
            b.click("#chSent")
            b.wait("document.getElementById('pkChase').hidden")
            b.pump(0.6)
            self.assertIn("couldn't be staged", b.eval("document.getElementById('snackT').textContent"))
        finally:
            b.eval("shared.VW.write=window.__w")
        self.assertEqual(staged(self.v.root, self.theirs), [])

    def test_undo_leaves_a_proposal_staged_after_the_press(self):
        b = self.b
        self.chase(self.theirs)
        b.click("#chSent")
        b.wait("document.getElementById('pkChase').hidden")
        b.eval(f"pkCommit('actions',{self.mine!r},{{pr:'Urgent'}},'Priority','Medium','Urgent')")
        b.wait(f"PKS.some(s=>s.id==={self.mine!r})")
        self.undo()
        self.assertEqual(staged(self.v.root, self.theirs), [])
        self.assertEqual(len(staged(self.v.root, self.mine)), 1, "the later proposal survives")
        self.assertEqual(b.eval("PKS.map(s=>s.id)"), [self.mine])
        self.assertEqual(b.errors, [])

    def test_via_email_by_default_and_a_second_press_does_not_log_twice(self):
        b = self.b
        self.chase(self.theirs)
        before = len(staged(self.v.root, self.theirs))
        b.eval("(()=>{ const x=document.getElementById('chSent'); x.click(); x.click(); })()")
        b.wait("document.getElementById('pkChase').hidden")
        b.pump(0.5)
        got = staged(self.v.root, self.theirs)
        self.assertEqual(len(got) - before, 1)
        self.assertIn("by email (reminder", got[-1][1]["changes"]["latest_update"])
        self.undo()

    def test_help_and_decision_wording(self):
        b = self.b
        self.chase(self.mine)
        b.click("#chSent")
        b.wait("document.getElementById('pkChase').hidden")
        line = staged(self.v.root, self.mine)[0][1]["changes"]["latest_update"].split("\n")[0]
        self.assertRegex(line, rf"^{shown(b)}: Asked \S+ \S+ by email for \S.*\.$")
        self.assertNotIn("reply asked", line)
        self.undo()
        self.chase(self.decision, "decisions")
        b.click("#chSent")
        b.wait("document.getElementById('pkChase').hidden")
        line = staged(self.v.root, self.decision)[0][1]["changes"]["reasoning"].split("\n")[0]
        self.assertRegex(line, rf"^{shown(b)}: Asked Jane Doe for a decision by email; reply asked for by \d\d-\d\d-2026\.$")
        self.undo()


class PopupISentIt(SentCase):
    shared_server = False

    def test_update_mode_logs_every_ticked_item_one_undo_unticked_untouched(self):
        b = self.b
        self.open_person_email("update")
        self.assertTrue(b.eval("!!document.getElementById('deSent')"), "the button is there in update mode")
        b.eval(f"(()=>{{ const c=document.querySelector('#deInc [data-deit=\"actions:{self.s_check}\"]'); if(c.checked) c.click(); }})()")
        picked = b.eval("[...document.querySelectorAll('#deInc [data-deit]')].filter(c=>c.checked).map(c=>c.dataset.deit.split(':')[1])")
        self.assertNotIn(self.s_check, picked)
        self.assertGreaterEqual(len(picked), 3)
        b.click("#deSent")
        b.wait("!document.getElementById('deDlg').open")
        self.assertEqual(b.eval("document.getElementById('snackT').textContent"), f"Logged on {len(picked)} items.")
        for i in picked:
            f = "reasoning" if i.startswith("ABC-D") else "latest_update"
            ch = staged(self.v.root, i)
            self.assertEqual(len(ch), 1, i)
            self.assertRegex(ch[0][1]["changes"][f].split("\n")[0], rf"^{shown(b)}: Emailed Sara Example by email asking for an update\.$")
        self.assertEqual(staged(self.v.root, self.s_check), [])                              # unticked: untouched
        recs = json.loads((self.v.root / "system/staging/chases.json").read_text())["chases"]
        self.assertEqual(len(recs), 1)
        self.assertEqual((sorted(recs[0]["ids"]), recs[0]["mode"]), (sorted(picked), "update"))
        self.undo()
        for i in picked:
            self.assertEqual(staged(self.v.root, i), [], i)
        self.assertEqual(b.errors, [])

    def test_undo_removes_exactly_the_batch_not_the_last_n_staged(self):
        """Something else is staged between the press and the Undo: Undo takes out the batch's proposals and leaves that one."""
        b = self.b
        self.open_person_email("update")
        b.eval(f"(()=>{{ const c=document.querySelector('#deInc [data-deit=\"actions:{self.s_check}\"]'); if(c.checked) c.click(); }})()")
        picked = b.eval("[...document.querySelectorAll('#deInc [data-deit]')].filter(c=>c.checked).map(c=>c.dataset.deit.split(':')[1])")
        b.click("#deSent")
        b.wait("!document.getElementById('deDlg').open")
        self.assertEqual(b.eval("document.getElementById('snackT').textContent"), f"Logged on {len(picked)} items.")
        b.eval(f"pkCommit('actions',{self.s_check!r},{{pr:'Urgent'}},'Priority','Medium','Urgent')")
        b.wait(f"PKS.some(s=>s.id==={self.s_check!r})")
        b.eval("document.getElementById('snackU')&&1")
        self.assertTrue(b.eval("!!document.getElementById('snackU')"), "the toast's Undo is still offered")
        self.undo()
        for i in picked:
            self.assertEqual(staged(self.v.root, i), [], i)
        other = staged(self.v.root, self.s_check)
        self.assertEqual(len(other), 1, "the proposal staged afterwards survives")
        self.assertEqual(other[0][1]["changes"], {"priority": "Urgent"})
        self.assertEqual(b.eval("PKS.map(s=>s.id)"), [self.s_check])
        self.assertEqual(b.errors, [])

    def test_chase_mode_writes_the_chase_line_with_the_reminder_number(self):
        b = self.b
        self.open_person_email("chase")
        b.eval("document.querySelectorAll('#deInc [data-deit]').forEach(i=>{ if(!i.checked) i.click(); })")
        n = b.eval("document.querySelectorAll('#deInc [data-deit]').length")
        b.eval("document.getElementById('deReply').value='15-10-2026'; document.getElementById('deReply').dispatchEvent(new Event('input',{bubbles:true}))")
        b.click("#deSent")
        b.wait("!document.getElementById('deDlg').open")
        ch = staged(self.v.root, self.s_scripts)
        self.assertEqual(len(ch), 1)
        self.assertEqual(ch[0][1]["changes"]["latest_update"].split("\n")[0],
                         f"{shown(b)}: Chased Sara Example by email (reminder 1); reply asked for by 15-10-2026.")
        self.assertEqual(staged(self.v.root, self.s_check), [])                              # not overdue: not in a chase
        self.assertGreaterEqual(n, 2)

    def test_nothing_ticked_writes_nothing(self):
        b = self.b
        self.open_person_email("update")
        b.eval("document.querySelectorAll('#deInc [data-deit]').forEach(i=>{ if(i.checked) i.click(); })")
        b.click("#deSent")
        b.pump(0.5)
        self.assertTrue(b.eval("document.getElementById('deDlg').open"))
        self.assertFalse((self.v.root / "system/staging/chases.json").exists())


class LogEdges(SentCase):
    shared_server = True

    def test_a_confidential_item_logs_the_short_form(self):
        """Finding 4: who and how only, no reminder number, reply-by or detail. The pane and the popup refuse to offer a confidential
        item, so the logger is called as the page calls it, for an item that became confidential after the pane opened."""
        b = self.b
        for mode, word in (("chase", "Chased"), ("update", "Emailed")):
            b.eval(f"sentLog([{{k:'actions',id:{self.s_conf!r}}}],{{name:'Sara Example',mode:{mode!r},replyBy:'2026-10-19',chases:{{{self.s_conf!r}:{{n:2}}}}}}); 0")
            b.wait(f"PKS.some(s=>s.id==={self.s_conf!r})")
            b.pump(0.4)
            line = staged(self.v.root, self.s_conf)[-1][1]["changes"]["latest_update"].split("\n")[0]
            self.assertEqual(line, f"{shown(b)}: {word} Sara Example by email.")
            self.undo()
            self.assertEqual(staged(self.v.root, self.s_conf), [])

    def test_the_copy_choice_does_not_leak_into_the_next_popup(self):
        """Finding 5: Copy as plain text in one popup, then a new popup: I sent it without copying says email."""
        b = self.b
        self.open_person_email("update")
        b.eval(CLIPBOARD)
        b.click("#deCopyText")
        b.pump(0.4)
        b.eval("document.getElementById('deDlg').close()")
        self.open_person_email("update")
        b.click("#deSent")
        b.wait("!document.getElementById('deDlg').open")
        b.pump(0.4)
        line = staged(self.v.root, self.s_scripts)[-1][1]["changes"]["latest_update"].split("\n")[0]
        self.assertIn("by email asking for an update", line)
        self.undo()

    def test_a_failure_while_logging_leaves_the_popup_button_usable(self):
        """Finding 6: if staging throws, the button is enabled again and the person is told."""
        b = self.b
        self.open_person_email("update")
        b.eval("window.__q=shared.PKQ; shared.PKQ={then(){ throw new Error('boom') }}; 0")
        try:
            b.click("#deSent")
            b.pump(0.8)
            self.assertFalse(b.eval("document.getElementById('deSent').disabled"))
            self.assertIn("Couldn't log", b.eval("document.getElementById('snackT').textContent"))
        finally:
            b.eval("shared.PKQ=window.__q")
        b.eval("document.getElementById('deDlg').close()")

    def test_a_failure_while_logging_in_the_pane_lets_it_go_back(self):
        b = self.b
        self.chase(self.theirs)
        b.eval("window.__q=shared.PKQ; shared.PKQ={then(){ throw new Error('boom') }}; 0")
        try:
            b.click("#chSent")
            b.wait("document.getElementById('pkChase').hidden")
            b.pump(0.5)
            self.assertIn("couldn't be staged", b.eval("document.getElementById('snackT').textContent"))      # recorded once; the pane doesn't hang
        finally:
            b.eval("shared.PKQ=window.__q")

    def test_two_or_more_items_each_get_their_own_chase_line(self):
        """#153 (Alan): every ticked item is logged, once, with its own reminder number and the reply-by date."""
        b = self.b
        self.open_person_email("chase")
        b.eval("document.getElementById('deReply').value='19-10-2026'; document.getElementById('deReply').dispatchEvent(new Event('input',{bubbles:true}))")
        picked = b.eval("[...document.querySelectorAll('#deInc [data-deit]')].filter(c=>c.checked).map(c=>c.dataset.deit.split(':')[1])")
        self.assertGreaterEqual(len(picked), 2)
        before = {i: len(staged(self.v.root, i)) for i in picked}
        b.click("#deSent")
        b.wait("!document.getElementById('deDlg').open")
        b.pump(0.4)
        for i in picked:
            ch = staged(self.v.root, i)
            self.assertEqual(len(ch), before[i] + 1, i)
            ch = ch[-1:]
            f = "reasoning" if i.startswith("ABC-D") else "resp" if "-R-" in i else "latest_update"
            first = ch[0][1]["changes"].get(f) or " ".join(map(str, ch[0][1]["changes"].values()))
            self.assertRegex(first.split("\n")[0], rf"^{shown(b)}: Chased Sara Example by email \(reminder \d+\); reply asked for by 19-10-2026\.$", i)
        self.undo()

    def test_a_retry_after_one_item_fails_logs_only_that_item_and_counts_the_chase_once(self):
        """#153 (Alan): one item's staging fails, the toast names it, the popup stays; pressing again logs only it, with no second record."""
        b = self.b
        self.open_person_email("update")
        picked = b.eval("[...document.querySelectorAll('#deInc [data-deit]')].filter(c=>c.checked).map(c=>c.dataset.deit.split(':')[1])")
        self.assertGreaterEqual(len(picked), 2)
        before = {i: len(staged(self.v.root, i)) for i in picked}
        recs0 = self.chase_records()
        b.eval("window.__w=shared.VW.write; window.__n=0; shared.VW.write=async function(...a){ if(window.__n++===0) throw new Error('disk full'); return window.__w.apply(this,a); }; 0")
        try:
            b.click("#deSent")
            b.pump(1.0)
            self.assertTrue(b.eval("document.getElementById('deDlg').open"), "the popup stays so the missing item can be retried")
            self.assertRegex(b.eval("document.getElementById('snackT').textContent"), r"Couldn't log ABC-[A-Z]-\d+")
            self.assertFalse(b.eval("document.getElementById('deSent').disabled"))
        finally:
            b.eval("shared.VW.write=window.__w")
        done_first = [i for i in picked if len(staged(self.v.root, i)) > before[i]]
        self.assertEqual(len(done_first), len(picked) - 1)
        b.eval("document.getElementById('deSent').click()")
        b.wait("!document.getElementById('deDlg').open")
        b.pump(0.4)
        for i in picked:
            self.assertEqual(len(staged(self.v.root, i)), before[i] + 1, i)                       # once each, none doubled
        recs = self.chase_records()
        self.assertEqual(len(recs), len(recs0) + 1, "the chase is recorded once, not again on the retry")
        self.assertEqual(sorted(recs[-1]["ids"]), sorted(picked))

    def test_fix5_switching_the_mode_mid_retry_starts_a_new_send(self):
        """fix5: a failed update-mode press, then a switch to Chase overdue items: the chase is a new send (its own record, mode chase,
        each ticked item logged with the chase line), never the update send's record carried over."""
        b = self.b
        self.open_person_email("update")
        recs0 = self.chase_records()
        b.eval("window.__w=shared.VW.write; window.__n=0; shared.VW.write=async function(...a){ if(window.__n++===0) throw new Error('disk full'); return window.__w.apply(this,a); }; 0")
        try:
            b.click("#deSent")
            b.pump(1.0)
            self.assertTrue(b.eval("document.getElementById('deDlg').open"))
        finally:
            b.eval("shared.VW.write=window.__w")
        old = b.eval("shared.DE.sendId")
        self.assertTrue(old)
        self.assertEqual(self.chase_records()[-1]["mode"], "update")
        b.eval("document.querySelector('[data-demode=\"chase\"]').click()")
        b.wait("shared.DE&&shared.DE.mode==='chase'&&document.querySelector('#deInc [data-deit]')")
        self.assertFalse(b.eval("shared.DE.sendId"), "a new mode is a new send")
        picked = b.eval("[...document.querySelectorAll('#deInc [data-deit]')].filter(c=>c.checked).map(c=>c.dataset.deit.split(':')[1])")
        self.assertTrue(picked)
        before = {i: len(staged(self.v.root, i)) for i in picked}
        b.eval("document.getElementById('deSent').click()")                                     # the failure's toast sits over it
        b.wait("!document.getElementById('deDlg').open")
        b.pump(0.4)
        recs = self.chase_records()
        self.assertEqual(len(recs), len(recs0) + 2, "the update send and the chase send are recorded once each")
        self.assertEqual((recs[-1]["mode"], sorted(recs[-1]["ids"])), ("chase", sorted(picked)))
        for i in picked:
            ch = staged(self.v.root, i)
            self.assertEqual(len(ch), before[i] + 1, i)
            self.assertRegex(ch[-1][1]["changes"]["latest_update"].split("\n")[0], rf"^{shown(b)}: Chased Sara Example by email", i)
        self.assertEqual(b.errors, [])

    def test_fix5_a_mode_changed_in_place_is_a_new_send_too(self):
        """fix5: however the mode changes after a failed press, the next press is a new send under the new mode."""
        b = self.b
        self.open_person_email("update")
        recs0 = self.chase_records()
        b.eval("window.__w=shared.VW.write; window.__n=0; shared.VW.write=async function(...a){ if(window.__n++===0) throw new Error('disk full'); return window.__w.apply(this,a); }; 0")
        try:
            b.click("#deSent")
            b.pump(1.0)
        finally:
            b.eval("shared.VW.write=window.__w")
        old = b.eval("shared.DE.sendId")
        b.eval("shared.DE.mode='chase'; document.getElementById('deSent').click()")
        b.wait("!document.getElementById('deDlg').open")
        b.pump(0.4)
        recs = self.chase_records()
        self.assertEqual(len(recs), len(recs0) + 2)
        self.assertEqual(recs[-1]["mode"], "chase")
        self.assertNotEqual(b.eval("Object.keys(shared.SENT).pop()"), old)
        self.assertEqual(b.errors, [])

    def test_the_review_menu_has_two_plain_draft_email_items_for_an_overdue_item(self):
        """#153 (Alan): no 'Chase <name>' label; both items are plain Draft email and each opens the right mode in the popup."""
        b = self.b
        labels = b.eval(f"cxWork('actions',{self.s_scripts!r}).map(x=>x.label||'')")
        self.assertFalse([x for x in labels if x.startswith("Chase")], labels)
        self.assertEqual(labels.count("Draft email"), 2, labels)
        for index, mode in ((0, "update"), (1, "chase")):
            b.eval(f"cxWork('actions',{self.s_scripts!r}).filter(x=>x.label==='Draft email')[{index}].run()")
            b.wait("document.getElementById('deDlg').open")
            self.assertEqual(b.eval("DE.mode"), mode)
            b.eval("document.getElementById('deDlg').close()")

    def test_undo_after_the_entry_is_gone_says_so(self):
        """Finding 7: an Undo for something already applied or undone says so instead of doing nothing."""
        b = self.b
        b.eval("pkUndoLast({name:'gone-dashboard.json',k:'actions',id:'X-1'})")
        b.wait("/already/i.test(document.getElementById('snackT').textContent)")


class CopyIdAndNames(SentCase):
    shared_server = True

    def test_copy_id_copies_the_id_two_spaces_and_the_title(self):
        b = self.b
        self.open(self.theirs)
        b.eval(CLIPBOARD)
        b.click("#pkMore")
        b.wait("!!document.getElementById('pkMoreMenu')")
        names = b.eval("[...document.querySelectorAll('#pkMoreMenu [role=menuitem]')].map(x=>x.textContent.trim())")
        self.assertIn("Copy ID and title", names)
        b.eval("[...document.querySelectorAll('#pkMoreMenu [role=menuitem]')].find(x=>x.textContent.includes('Copy ID and title')).click()")
        b.wait("CLIP.length===1")
        self.assertEqual(b.eval("CLIP[0]['text/plain']"), f"{self.theirs}  Share the UAT plan")
        self.assertEqual(b.eval("pkIdText('X-1',{t:'  A  b\\n c '})"), "X-1  A b c")

    def test_one_name_in_the_page_strings(self):
        html = (Path(__file__).resolve().parents[2] / "system/templates/dashboard.html").read_text()
        self.assertNotRegex(html, r"Draft (a )?chase")
        self.assertIn("Draft email", html)


if __name__ == "__main__":
    unittest.main()


class ActivityReadsTheNote(SentCase):
    shared_server = True

    def test_the_applied_note_reads_in_plain_words_and_is_escaped(self):
        """After apply, Activity words the history-only note plainly: the item, then "note: Draft email: I sent it"."""
        sys.path.insert(0, str(self.v.root / "system/scripts"))
        import build_dashboard
        self.v.propose("sentnote", [{"n": 1, "op": "update", "table": "actions", "id": self.s_room, "match": "strong", "flags": [], "decision": "approved",
                                     "changes": {"latest_update": "01-10-2026: Emailed Sara Example by email asking for an update."},
                                     "note": "Draft email: I sent it"}], source_run="dashboard")
        self.v.run("apply")
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            con.row_factory = sqlite3.Row
            lines = [a for a in build_dashboard.activity(con, {}) if a["id"] == self.s_room and a["change"].startswith("note")]
        self.assertEqual([a["change"] for a in lines], ["note: Draft email: I sent it"])
        self.assertNotIn("<", lines[0]["what"])
        b = self.b
        b.eval("go('activity')")
        b.eval("""ACT=[Object.assign({},%s,{item:'Book <b>the</b> room',change:'note: Draft email: I sent it <i>x</i>',id:%r})]; renderActivity();""" % (json.dumps(lines[0]), self.s_room))
        b.wait("document.querySelector('#actTbl tr[data-row],#actTbl .actchg')")
        cell = b.eval("document.querySelector('#actTbl .actchg').innerText")
        self.assertIn("note: Draft email: I sent it <i>x</i>", cell)                       # escaped: shown as text, not markup
        self.assertEqual(b.eval("document.querySelectorAll('#actTbl .actchg b, #actTbl .actchg i').length"), 0)
        self.assertEqual(b.errors, [])
