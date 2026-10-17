"""BL-176, BL-177 and BL-175 (sprint-peek): the work item peek, Review's proposals in its layout, and the Work and Review
toolbars. A real browser against the real live server, from the mockup's own checks (dev/mockups/work-item-peek-mockup.html).

Run: python3 dev/tests/test_work_item_peek.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import new  # noqa: E402

META, CTRL = 4, 2
TODAY = date.today().isoformat()


def pending_decision(v):
    """A pending decision and a client-visible action beside the usual sample data."""
    v.propose("peek-extra", [new("decisions", 1, project="ABC", decision="Extend the pilot", made_by="Sara Example", status="Pending",
                                 needed_by=TODAY, source="Alan (cx-edit)"),
                             new("actions", 2, project="ABC", description="Tell the client about the slip", owner="Alan Carter",
                                 client_visible=1, client_message="What it is: A slip\nWhat it means for you: Two weeks later\n"
                                 "What is being done: A recovery plan", source="Alan (cx-edit)")])
    v.run("apply")


class PeekCase(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        from test_dashboard import populate
        populate(v)
        pending_decision(v)

    def staged(self):
        return sorted(p.name for p in (self.v.root / "system/staging").glob("proposed-*-dashboard.json"))

    def others(self):
        return sorted(p.name for p in (self.v.root / "system/staging").glob("proposed-*.json") if not p.name.endswith("-dashboard.json"))

    def action(self, id_):
        return next(r for r in self.v.rows("actions") if r["id"] == id_)

    def open(self, k="actions", id_=None, click=True):
        b = self.b
        b.eval(f"WT={k!r}; go('work')")
        b.wait("document.querySelector('#workTbl tbody tr[data-row]')")
        id_ = id_ or b.eval({"actions": "A", "raid": "R", "decisions": "DEC"}[k] + ".find(x=>x.p==='ABC').id")
        if click:
            b.wait(f"document.querySelector('#workTbl tr[data-row=\"{id_}\"] a.rowid')")
            b.click_until(f'#workTbl tr[data-row="{id_}"] a.rowid',                 # #152: a click lost to a redraw is pressed again
                          f"CUR&&CUR.id==={id_!r}&&document.getElementById('panel').classList.contains('peek')")
        else:
            b.eval(f"openRecord({k!r},{id_!r})")
        b.wait(f"CUR&&CUR.id==={id_!r}&&document.getElementById('panel').classList.contains('peek')")
        b.pump(0.3)
        return id_

    def pick(self, field, label):
        b = self.b
        b.click(f'#panel [data-pkp="{field}"]')
        b.wait("document.querySelector('.pkpop')")
        b.eval(f"[...document.querySelectorAll('.pkpop .pkopt')].find(o=>o.querySelector('span').firstChild.textContent==={label!r}).click()")

    def text(self, sel, value):
        b = self.b
        b.click(sel)
        b.eval(f"(()=>{{ const t=document.querySelector({sel!r}); t.textContent={value!r}; t.blur(); }})()")

    def note(self):
        return self.b.eval("document.getElementById('pkNote').hidden?'':document.getElementById('pkNote').textContent")


class OpensEditable(PeekCase):
    shared_server = True

    def test_the_title_key_row_and_free_text_are_live_with_no_edit_save_or_cancel(self):
        b = self.b
        self.open()
        self.assertEqual(b.eval("document.getElementById('pkTitle').getAttribute('contenteditable')"), "true")
        self.assertEqual(b.eval("document.getElementById('pkTitle').cxed.features"), "plain")   # BL-301 A: the one editor, plain text
        self.assertEqual(b.eval("document.getElementById('pkTitle').getAttribute('role')"), "textbox")
        self.assertEqual(b.eval("document.getElementById('pkTitle').getAttribute('aria-label')"), "Action")
        self.assertEqual(b.eval("document.getElementById('pkDesc').getAttribute('aria-label')"), "Latest update")
        self.assertEqual(b.eval("[...document.querySelectorAll('#pkProps [data-pkp]')].map(c=>c.dataset.pkp)"), ["st", "pr", "o", "due"])
        for name in b.eval("[...document.querySelectorAll('#pkProps [data-pkp]')].map(c=>c.getAttribute('aria-label'))"):
            self.assertRegex(name, r"^(Status|Priority|Owner|Due date): .+")                 # the field name and its value
        self.assertEqual(b.eval("document.querySelectorAll('#pEdit,#pSave,#pCancel,#panel details.morefields').length"), 0)
        self.assertEqual(b.eval("getComputedStyle(document.getElementById('editBanner')).display"), "none")
        self.assertEqual(b.eval("document.getElementById('pKeys').getBoundingClientRect().height"), 0)
        self.assertFalse(b.eval("EDITING"))
        b.key("e")                                                                              # E is retired: nothing changes
        b.pump(0.2)
        self.assertFalse(b.eval("EDITING"))
        self.assertEqual(b.errors, [])

    def test_each_kind_has_its_own_row_and_free_text(self):
        b = self.b
        self.open("raid")
        self.assertEqual(b.eval("[...document.querySelectorAll('#pkProps .pk-prop>*')].map(c=>c.dataset.pkp||'calc')"), ["st", "calc", "o", "due"])
        self.assertEqual(b.eval("[...document.querySelectorAll('#pkProps2 [data-pkp]')].map(c=>c.dataset.pkp)"), ["imp", "lik"])
        self.assertTrue(b.eval("!!document.querySelector('#pkId [data-pkp=\"type\"]')"))
        kind = b.eval("curObj().type")
        want = {"Risk": "Mitigation action", "Issue": "Resolution action", "Assumption": "Validation action", "Dependency": "Management action"}[kind]
        self.assertEqual(b.eval("document.getElementById('pkDescL').textContent"), want)
        issue = b.eval("(R.find(r=>r.type==='Issue')||{}).id")
        if issue:
            b.eval(f"openRecord('raid',{issue!r})")
            self.assertEqual(b.eval("document.getElementById('pkDescL').textContent"), "Resolution action")
        self.open("decisions", b.eval("DEC.find(d=>d.st==='Pending').id"), click=False)
        self.assertEqual(b.eval("[...document.querySelectorAll('#pkProps [data-pkp]')].map(c=>c.dataset.pkp)"), ["st", "o", "due"])
        self.assertEqual(b.eval("document.querySelector('#pkProps [data-pkp=\"due\"]').getAttribute('aria-label').split(':')[0]"), "Needed by")
        self.assertEqual(b.eval("document.getElementById('pkDescL').textContent"), "Reasoning")
        self.open("decisions", b.eval("DEC.find(d=>d.st==='Made').id"), click=False)
        self.assertEqual(b.eval("[...document.querySelectorAll('#pkProps [data-pkp]')].map(c=>c.dataset.pkp)"), ["st", "o", "date"])

    def test_an_empty_value_is_a_prompt_and_overdue_is_red_with_a_tag(self):
        b = self.b
        late = b.eval("A.find(a=>OPENST(a.st)&&a.due&&a.due<TODAY).id")
        self.open(id_=late)
        chip = "document.querySelector('#pkProps [data-pkp=\"due\"]')"
        self.assertTrue(b.eval(f"{chip}.classList.contains('late')"))
        self.assertIn("overdue", b.eval(f"{chip}.textContent"))
        decision = b.eval("DEC.find(d=>d.st==='Pending').id")
        b.eval(f"DEC.find(d=>d.id==={decision!r}).by=''; openRecord('decisions',{decision!r})")
        self.assertEqual(b.eval("document.querySelector('#pkProps [data-pkp=\"o\"]').textContent.trim()"), "Add decision maker")
        self.assertTrue(b.eval("document.querySelector('#pkProps [data-pkp=\"o\"]').classList.contains('empty')"))


class Overlay(PeekCase):
    shared_server = True

    def geom(self):
        return json.loads(self.b.eval("""JSON.stringify({w:document.querySelector('.content').getBoundingClientRect().width,
          row:document.querySelector('#workTbl tbody tr[data-row]').getBoundingClientRect().top, panel:(r=>[r.left,r.width,r.right])(document.getElementById('panel').getBoundingClientRect())})"""))

    def test_over_the_page_half_the_window_never_under_520_and_clear_of_the_chat(self):
        b = self.b
        if b.eval("innerWidth>=1200 && document.querySelector('.rail').getBoundingClientRect().width>100"):
            b.click("#railTog")          # #156: the rail is open from 1200px; this test is about the peek beside the chat, so collapse it
        for width in (1400, 1100):
            b.resize(width, 900)
            b.eval("closePanel(); closeChat(); go('work')")
            b.pump(0.3)
            before = self.geom()
            self.open()
            after = self.geom()
            self.assertEqual((after["w"], after["row"]), (before["w"], before["row"]), width)   # the page doesn't move
            self.assertGreaterEqual(after["panel"][1], 520)
            b.eval("openChat()")
            b.pump(0.4)
            p, c = self.geom()["panel"], b.eval("document.getElementById('chat').getBoundingClientRect().left")
            self.assertLessEqual(p[2], c + 1, width)                                          # never under the chat
            self.assertGreaterEqual(p[1], 520, width)
            b.eval("closeChat()")
            b.pump(0.3)
            self.assertEqual(self.geom()["panel"], after["panel"], width)                       # closing the chat leaves it as it was
        b.resize(1400, 900)

    def test_outside_click_esc_another_row_and_j_k(self):
        b = self.b
        b.resize(1400, 900)
        first = self.open()
        rows = b.eval("[...document.querySelectorAll('#workTbl tr[data-row]')].map(r=>r.dataset.row)")
        second = rows[1]
        b.click(f'#workTbl tr[data-row="{second}"] a.rowid')                                    # another row swaps it
        b.wait(f"CUR&&CUR.id==={second!r}")
        b.eval("document.activeElement.blur()")
        b.key("k")                                                                              # K: back to the first
        b.wait(f"CUR&&CUR.id==={first!r}")
        b.key("j")
        b.wait(f"CUR&&CUR.id==={second!r}")
        b.click("#pkPrev")
        b.wait(f"CUR&&CUR.id==={first!r}")
        b.key("Escape")                                                                         # BL-122: the highlight first
        b.key("Escape")                                                                         # then the peek
        b.wait("!document.getElementById('panel').classList.contains('on')")
        self.open()
        b.click("#workQ")                                                                       # a click outside closes it
        b.wait("!document.getElementById('panel').classList.contains('on')")
        self.open()
        b.click("#pkExpand")
        rail = b.eval("document.querySelector('.rail').getBoundingClientRect().width")
        b.wait(f"Math.abs(document.getElementById('panel').getBoundingClientRect().width-{1400 - rail})<=1")
        b.click("#pkClose")
        b.wait("!document.getElementById('panel').classList.contains('on')")
        self.open()
        self.assertLess(b.eval("document.getElementById('panel').getBoundingClientRect().width"), 1000)   # back to half when opened again


class Staging(PeekCase):
    def test_three_edits_are_three_proposals_undo_last_removes_only_the_newest_and_apply_writes_them(self):
        b = self.b
        id_ = self.open()
        before = self.action(id_)
        others = self.others()
        self.pick("pr", "Low")
        b.wait("PKS.length===1", 10)
        self.assertTrue(b.eval(f"!!document.querySelector('#workTbl tr[data-row=\"{id_}\"] .pkdot')"))   # the row says it has staged changes
        self.pick("st", "Delayed")                                                              # (now Delayed: All open, Open only, no longer lists it)
        b.wait("PKS.length===2", 10)
        self.text("#pkDesc", "Chased on Friday")
        b.wait("PKS.length===3", 10)
        files = self.staged()
        self.assertEqual(len(files), 3)                                                         # each edit its own proposal
        self.assertEqual(self.action(id_), before)                                              # nothing in the tracker yet
        self.assertEqual(b.eval("document.getElementById('pkStN').textContent"), "3 changes staged on 1 item")
        self.assertIn("staged", b.eval("document.getElementById('pkLast').textContent"))
        self.assertEqual(b.eval("document.querySelectorAll('#pkFeed .pk-pill.st').length"), 3)
        first = json.loads((self.v.root / "system/staging" / files[0]).read_text())
        self.assertEqual((first["source_run"], first["items"][0]["decision"], first["items"][0]["changes"]), ("dashboard", "approved", {"priority": "Low"}))
        self.assertIn("based_on", first["items"][0])
        self.assertNotIn("based_on", json.loads((self.v.root / "system/staging" / files[1]).read_text())["items"][0])
        b.click("#pkUndo")                                                                      # Undo last: only the newest
        b.wait("PKS.length===2", 10)
        self.assertEqual(self.staged(), files[:2])
        self.assertEqual(self.others(), others)                                                 # the sweep's and minutes' are untouched
        self.assertNotEqual(b.eval(f"REC('actions',{id_!r}).upd"), "Chased on Friday")
        b.click("#pkApply")
        b.wait("PKS.length===0&&/Applied 2 changes/.test(document.getElementById('snackT').textContent)", 20)
        row = self.action(id_)
        self.assertEqual((row["priority"], row["status"]), ("Low", "Delayed"))
        self.assertEqual(self.staged(), [])
        self.assertTrue(b.eval("document.getElementById('pkStage').hidden"))
        self.assertGreaterEqual(b.eval("document.querySelectorAll('#pkFeed .pk-pill.ap').length"), 2)   # staged, then applied
        self.assertEqual(b.eval("document.querySelectorAll('#pkFeed .pk-pill.st').length"), 0)

    def test_the_feed_tabs_filter(self):
        b = self.b
        id_ = self.open()
        self.text("#pkDesc", "An update")
        b.wait("PKS.length===1", 10)
        self.pick("pr", "Low")
        b.wait("PKS.length===2", 10)
        counts = {}
        for tab in ("all", "act", "upd", "src"):
            b.click(f'#pkTabs [data-pktab="{tab}"]')
            counts[tab] = b.eval("document.querySelectorAll('#pkFeed .pk-fe').length")
            self.assertEqual(b.eval("document.querySelector('#pkTabs [aria-selected=\"true\"]').dataset.pktab"), tab)
        self.assertEqual(b.eval("[...document.querySelectorAll('#pkTabs [role=tab]')].map(t=>t.textContent)"), ["All", "Activity", "Updates", "Source"])
        self.assertEqual(counts["all"], counts["act"] + counts["upd"] + counts["src"])
        self.assertGreaterEqual(counts["upd"], 1)
        self.assertGreaterEqual(counts["src"], 1)
        b.click('#pkTabs [data-pktab="src"]')
        self.assertIn("Steering", b.eval("document.getElementById('pkFeed').textContent"))
        self.assertEqual(id_, b.eval("CUR.id"))


class Rules(PeekCase):
    def test_closing_sets_the_closed_date_and_reopening_clears_it(self):
        b = self.b
        id_ = self.open()
        self.pick("st", "Closed")
        b.wait("PKS.length===1", 10)
        self.assertEqual(b.eval("PKS[0].patch"), {"st": "Closed", "closed": TODAY})
        self.assertIn("Closed date set", b.eval("document.getElementById('pkFeed').textContent"))
        self.pick("st", "Open")
        b.wait("PKS.length===2", 10)
        self.assertEqual(b.eval("PKS[1].patch"), {"st": "Open", "closed": ""})
        b.key("Enter", modifiers=META)                                                          # ⌘↵ from a chip: applies, closes
        b.wait("!document.getElementById('panel').classList.contains('on')", 20)
        b.wait("PKS.length===0", 20)
        row = self.action(id_)
        self.assertEqual((row["status"], row["closed"]), ("Open", None))

    def test_made_decisions(self):
        b = self.b
        pend = self.open("decisions", self.b.eval("DEC.find(d=>d.st==='Pending').id"), click=False)
        self.pick("st", "Made")
        b.wait("PKS.length===1", 10)
        self.assertEqual(b.eval("PKS[0].patch"), {"st": "Made", "date": TODAY})                 # Made fills Date made
        b.click('#panel [data-pkp="st"]')
        b.wait("document.querySelector('.pkpop')")
        self.assertEqual(b.eval("document.querySelector('.pkpop .pkopt').getAttribute('aria-disabled')"), "true")   # no way back to pending
        b.key("Escape")
        b.wait("!document.querySelector('.pkpop')")
        self.assertEqual(b.eval("document.activeElement.dataset.pkp"), "st")                   # Esc: back to the chip
        self.assertTrue(b.eval("document.getElementById('panel').classList.contains('on')"))
        self.assertEqual(pend, b.eval("CUR.id"))

    def test_client_visible_waits_for_messaging_and_clearing_it_is_refused(self):
        b = self.b
        id_ = self.open(id_=self.b.eval("A.find(a=>a.p==='ABC'&&!a.client&&OPENST(a.st)).id"), click=False)
        b.click("#pkDetT")
        b.click('#pkDet [data-pksw="client"]')
        b.wait("document.activeElement&&document.activeElement.dataset.pkf==='cm'", 5)
        self.assertIn("client messaging", self.note())
        self.assertEqual(b.eval("PKS.length"), 0)
        self.text('#pkDet [data-pkf="cm"]', "What it is: Access approvals\nWhat it means for you:\nWhat is being done:")   # one heading: not enough
        b.pump(0.3)
        self.assertEqual(b.eval("PKS.length"), 0)
        self.assertIn("Nothing saved", self.note())
        self.text('#pkDet [data-pkf="cm"]', "What it is: Access approvals\nWhat it means for you: UAT may slip\nWhat is being done: Escalated")
        b.wait("PKS.length===1", 10)
        self.assertEqual(sorted(b.eval("Object.keys(PKS[0].patch)")), ["client", "cm"])        # both, together
        visible = b.eval("A.find(a=>a.client&&a.cm&&a.t==='Tell the client about the slip').id")
        b.eval(f"openRecord('actions',{visible!r})")
        self.assertEqual(b.eval("document.getElementById('pkDetT').getAttribute('aria-expanded')"), "true")   # opens by itself
        msg = b.eval("document.querySelector('#pkDet [data-pkf=\"cm\"]').textContent")
        self.text('#pkDet [data-pkf="cm"]', "")
        b.pump(0.3)
        self.assertIn("old wording was kept", self.note())
        self.assertEqual(b.eval("document.querySelector('#pkDet [data-pkf=\"cm\"]').textContent"), msg)
        self.assertEqual(b.eval("PKS.length"), 1)
        self.assertEqual(id_, b.eval("PKS[0].id"))

    def test_empty_title_bad_date_and_priority(self):
        b = self.b
        self.open()
        title = b.eval("document.getElementById('pkTitle').textContent")
        self.text("#pkTitle", "")
        b.pump(0.3)
        self.assertEqual(b.eval("document.getElementById('pkTitle').textContent"), title)
        self.assertIn("is needed", self.note())
        b.click('#panel [data-pkp="due"]')
        b.wait("document.querySelector('.pkpop .pkdt')")
        b.click(".pkpop .pkdt")
        b.type("the 45th")
        b.key("Enter")
        self.assertIn("Use DD-MM-YYYY", b.eval("document.querySelector('.pkpop .pkerr').textContent"))
        b.eval("document.querySelector('.pkpop .pkdt').value=''")
        # "+3d" was a Saturday on a Wednesday: the weekend question waited and nothing was staged (14-10-2026). The
        # number of days is now the first from 3 that lands on a working day other than the item's own due date.
        today, cur = date.fromisoformat(b.eval("TODAY")), b.eval("curObj().due") or ""
        n, want = next((n, (today + timedelta(days=n)).isoformat()) for n in range(3, 10)
                       if (today + timedelta(days=n)).weekday() < 5 and (today + timedelta(days=n)).isoformat() != cur)
        b.type(f"+{n}d")
        b.key("Enter")
        b.wait("PKS.length===1", 10)
        self.assertEqual(b.eval("PKS[0].patch.due"), want)                                   # words understood
        b.eval("closePanel()")
        self.open("raid", self.b.eval("R.find(r=>r.imp==='High'&&r.lik==='High').id"), click=False)
        self.pick("imp", "Low")
        b.wait("PKS.length===2", 10)
        self.assertIn("Priority recalculated: Urgent → High", b.eval("document.getElementById('pkFeed').textContent"))
        self.assertEqual(b.eval("curObj().pr"), "High")


class Pickers(PeekCase):
    shared_server = True

    def test_keyboard_and_inside_the_window_at_1100_with_the_chat(self):
        b = self.b
        b.resize(1100, 900)
        self.open()
        b.eval("openChat()")
        b.pump(0.4)
        for field in ("st", "pr", "o", "due"):
            b.click(f'#panel [data-pkp="{field}"]')
            b.wait("document.querySelector('.pkpop')")
            r = json.loads(b.eval("JSON.stringify(document.querySelector('.pkpop').getBoundingClientRect())"))
            self.assertGreaterEqual(r["left"], 0, field)
            self.assertLessEqual(r["right"], 1100, field)
            self.assertLessEqual(r["bottom"], 900, field)
            self.assertTrue(b.eval("(()=>{ const r=document.querySelector('.pkpop').getBoundingClientRect(); return document.querySelector('.pkpop').contains(document.elementFromPoint(r.left+20,r.top+20)); })()"), field)   # on top, over the chat
            b.key("Escape")
            b.wait("!document.querySelector('.pkpop')")
        b.click('#panel [data-pkp="pr"]')
        b.wait("document.querySelector('.pkpop')")
        start = b.eval("document.activeElement.textContent.trim()")
        b.key("ArrowDown")
        self.assertNotEqual(b.eval("document.activeElement.textContent.trim()"), start)
        b.key("ArrowUp")
        self.assertEqual(b.eval("document.activeElement.textContent.trim()"), start)
        b.key("Escape")
        self.assertTrue(b.eval("document.getElementById('chat').classList.contains('on')"))    # the chat stays open beside it
        b.resize(1400, 900)


class CommandEnter(PeekCase):
    def test_from_the_title_and_from_details_and_with_control(self):
        b = self.b
        id_ = self.open()
        b.click("#pkTitle")
        b.eval("document.getElementById('pkTitle').textContent='Title by command enter'")
        b.key("Enter", modifiers=META)
        b.wait("!document.getElementById('panel').classList.contains('on')&&PKS.length===0", 20)
        self.assertEqual(self.action(id_)["description"], "Title by command enter")
        self.open(id_=id_)
        b.click("#pkDetT")
        b.click('#pkDet [data-pkp="ws"]')
        b.wait("document.querySelector('.pkpop')")
        b.key("Enter", modifiers=CTRL)                                                           # a picker open: it closes first
        b.wait("!document.getElementById('panel').classList.contains('on')", 10)
        b.wait("/Nothing to apply/.test(document.getElementById('snackT').textContent)", 5)
        self.assertFalse(b.eval("!!document.querySelector('.pkpop')"))


class Review(PeekCase):
    def test_a_proposal_opens_in_the_same_layout_with_its_footer_and_notes(self):
        b = self.b
        b.eval("go('review')")
        b.wait("document.querySelector('#reviewBody tr[data-n]')")
        n = b.eval("REV.find(r=>!r.done&&r.kind==='actions'&&!r.p).n")
        b.eval(f"openProposal({n})")
        b.wait("document.getElementById('panel').classList.contains('pkprop')")
        self.assertTrue(b.eval("!!document.querySelector('#pkTitle[contenteditable]')"))
        self.assertEqual(b.eval("[...document.querySelectorAll('#pkFoot2 button')].map(x=>x.textContent.trim())"), ["Reject", "Cancel", "Save", "Save and approve"])
        top = b.eval("document.getElementById('pkPropTop').textContent")
        self.assertIn("Editing a proposal", top)
        self.assertIn("Choose a project before saving.", top)
        self.pick("pr", "Low")
        b.pump(0.3)
        self.assertEqual((b.eval("CUR.draft.pr"), b.eval("PKS.length")), ("Low", 0))           # held in the proposal, not staged
        b.click("#pkPSaveA")
        b.wait("document.getElementById('pkNote').textContent.includes('Choose a project')", 5)
        b.eval(f"pkCommit('actions','rv{n}',{{p:'DEF'}},'Project','','')")
        b.click("#pkPSave")
        b.wait("!document.getElementById('panel').classList.contains('on')", 10)
        self.assertEqual(b.eval(f"[REV.find(r=>r.n=={n}).done||false, REV.find(r=>r.n=={n}).p, REV.find(r=>r.n=={n}).rec.pr]"), [False, "DEF", "Low"])
        n2 = b.eval("REV.find(r=>!r.done&&r.kind==='raid').n")
        b.eval(f"openProposal({n2})")
        b.wait("document.getElementById('panel').classList.contains('pkprop')")
        t2 = b.eval(f"REV.find(r=>r.n=={n2}).rec.t")
        b.click("#pkReject")                                                    # BL-315: the reasons menu; 0 is no reason
        b.wait("!!document.getElementById('rvReason')")
        b.key("0")
        b.wait(f"!REV.some(r=>r.rec.t==={t2!r}&&!r.done)", 15)


class Toolbar(PeekCase):
    shared_server = True

    def test_icons_on_the_right_no_keys_chip_and_menus_inside_the_window(self):
        b = self.b
        if b.eval("document.querySelector('.rail').getBoundingClientRect().width>100"):
            b.click("#railTog")          # #156: the rail is open from 1200px; the toolbar's one-row check is about the toolbar, so collapse it
        for width in (1400, 1100, 900):
            b.resize(width, 900)
            b.eval("closePanel(); go('work')")
            b.wait("document.querySelector('#workTbl tbody tr[data-row]')")
            self.assertEqual(b.eval("document.querySelectorAll('.keyschip').length"), 0)
            x = json.loads(b.eval("""JSON.stringify((()=>{ const r=s=>document.querySelector(s).getBoundingClientRect();
              const fields=[...document.querySelectorAll('#wfilters>.dd:not(.wfold) .fbtn:not(#moreBtn)')].map(e=>e.getBoundingClientRect().right);
              return {fields:Math.max(...fields), funnel:r('#moreBtn').left, lay:r('#wlay').left, disp:r('#dispBtn').left, nw:r('#newBtn').left, top:r('#moreBtn').top, fieldTop:document.querySelector('#stBtn')?r('#stBtn').top:null}; })())"""))
            if x["fieldTop"] is not None and abs(x["fieldTop"] - x["top"]) < 8:
                self.assertGreater(x["funnel"], x["fields"], width)                              # the funnel is with the icons, on the right
            self.assertLess(x["funnel"], x["lay"], width)
            self.assertLess(x["lay"], x["disp"], width)
            self.assertLess(x["disp"], x["nw"], width)
            for btn, menu in (("#moreBtn", "#moreMenu"), ("#dispBtn", "#dispMenu")):
                b.click(btn)
                b.pump(0.4)
                r = json.loads(b.eval(f"JSON.stringify(document.querySelector('{menu}').getBoundingClientRect())"))
                self.assertGreaterEqual(r["left"], 0, (width, menu))
                self.assertLessEqual(r["right"], width, (width, menu))
                b.key("Escape")
                b.eval("closeDisp&&closeDisp(); document.querySelectorAll('#wfilters .ddmenu.on').forEach(m=>m.classList.remove('on'))")
            b.eval("go('review')")
            b.wait("document.querySelector('#reviewBody tr[data-n]')")
            self.assertEqual(b.eval("document.querySelectorAll('.keyschip').length"), 0)
            b.click("#rvMore")
            b.pump(0.4)
            r = json.loads(b.eval("JSON.stringify(document.getElementById('rvPick').getBoundingClientRect())"))
            self.assertGreaterEqual(r["left"], 0, width)
            self.assertLessEqual(r["right"], width, width)
            b.key("Escape")
        b.resize(1400, 900)


if __name__ == "__main__":
    unittest.main()
