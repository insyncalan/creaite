"""BL-179 (sprint-peek-new): New opens the work item peek, empty, instead of the Create form. A real browser against the real
live server.

Run: python3 dev/tests/test_new_item_peek.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

TODAY = date.today().isoformat()


class NewCase(LiveBrowserCase):
    def find(self, table, field, value):
        return [r for r in self.v.rows(table) if r[field] == value]

    def staged(self):
        return sorted(p.name for p in (self.v.root / "system/staging").glob("proposed-*-dashboard*.json"))

    def work(self, k="actions"):
        b = self.b
        b.eval(f"WT={k!r}; go('work')")
        b.wait("document.querySelector('#workTbl tbody tr[data-row]')")

    def new(self, k="actions", how=None):
        """Open New as Alan does: the New button, or on Decisions its menu."""
        b = self.b
        self.work(k)
        b.click("#newBtn")
        if k == "decisions":
            b.wait("newMenuOpen()")
            b.click(f'#newDecMenu [data-newd="{how or "made"}"]')
        b.wait("CUR&&CUR.mode==='new'&&document.getElementById('panel').classList.contains('peek')")
        b.pump(0.2)

    def chips(self):
        return self.b.eval("[...document.querySelectorAll('#pkProps .pk-prop>*')].map(c=>c.getAttribute('aria-label'))")

    def note(self):
        return self.b.eval("document.getElementById('pkNote').hidden?'':document.getElementById('pkNote').textContent")


class OpensEmpty(NewCase):
    shared_server = True

    def test_new_action_is_an_empty_peek_with_the_cursor_in_the_title_and_the_defaults(self):
        b = self.b
        self.new("actions")
        self.assertEqual(b.eval("document.activeElement.id"), "pkTitle")
        self.assertEqual(b.eval("document.getElementById('pkTitle').textContent"), "")
        self.assertEqual(b.eval("document.getElementById('pkTitle').dataset.ph"), "Add a title")
        prio = b.eval("S.defPriority")
        self.assertEqual(self.chips(), ["Status: Open", f"Priority: {prio}", "Owner: not set", "Due date: not set"])
        self.assertEqual(b.eval("document.querySelector('#pkProps [data-pkp=\"o\"]').textContent.trim()"), "Add owner")
        self.assertEqual(b.eval("document.querySelector('#pkId .pk-new').textContent"), "New action")
        self.assertEqual(b.eval("document.querySelector('#pkId [data-pkp=\"p\"]').textContent.trim()"), "Choose a project")   # two projects, no filter
        # the Create form is not there: no fields, no Create button, no editing
        self.assertEqual(b.eval("document.querySelectorAll('#pFields [name],#pSave,#pCancel').length"), 0)
        self.assertFalse(b.eval("EDITING"))
        for bar in ("pkLink", "pkMore", "pkPrev", "pkNext"):
            self.assertTrue(b.eval(f"document.getElementById('{bar}').hidden"), bar)
        self.assertEqual(b.errors, [])

    def test_the_project_comes_from_the_page(self):
        b = self.b
        self.work()
        b.eval("PROJF.clear(); PROJF.add('DEF'); renderWork(); openNew('actions')")
        self.assertEqual(b.eval("CUR.draft.p"), "DEF")
        self.assertEqual(b.eval("document.querySelector('#pkId [data-pkp=\"p\"]').textContent.trim()"), b.eval("pName('DEF')"))
        b.eval("closePanel(); PROJF.clear(); renderWork(); go('cockpit','ABC'); openNew('raid')")
        self.assertEqual(b.eval("CUR.draft.p"), "ABC")
        b.eval("closePanel(); go('work')")

    def test_new_raid_item_has_its_row_and_type(self):
        b = self.b
        self.new("raid")
        self.assertEqual(b.eval("[...document.querySelectorAll('#pkProps .pk-prop>*')].map(c=>c.dataset.pkp||'calc')"), ["st", "calc", "o", "due"])
        self.assertEqual(b.eval("[...document.querySelectorAll('#pkProps2 [data-pkp]')].map(c=>c.getAttribute('aria-label'))"),
                         ["Impact: Impact: Medium", "Likelihood: Likelihood: Medium"])     # the chip's words, as for an existing item
        self.assertEqual(b.eval("document.querySelector('#pkId [data-pkp=\"type\"]').textContent.trim()"), "Risk")
        self.assertEqual(b.eval("document.querySelector('#pkId .pk-new').textContent"), "New risk")
        self.assertEqual(b.eval("document.getElementById('pkDescL').textContent"), "Mitigation action")
        b.eval("closePanel(); FX.ty.clear(); FX.ty.add('Issue'); openNew('raid')")             # Work's Type filter names one
        self.assertEqual(b.eval("CUR.draft.type"), "Issue")
        self.assertEqual(b.eval("document.getElementById('pkDescL').textContent"), "Resolution action")
        b.eval("closePanel(); FX.ty.clear(); renderWork()")

    def test_record_and_ask_for_a_decision(self):
        b = self.b
        self.new("decisions", "made")
        self.assertEqual(self.chips(), ["Status: Made", f"Decision maker: {b.eval('S.me')} (you)", f"Date made: {b.eval('fd(TODAY)')}"])
        self.assertFalse(b.eval("document.getElementById('pkSrcIn').hidden"))                  # where it was decided
        self.assertIn("decided", b.eval("document.getElementById('pkSrcIn').dataset.ph"))
        b.eval("closePanel()")
        self.new("decisions", "needed")
        self.assertEqual(self.chips(), ["Status: Pending", "Decision maker: not set", "Needed by: not set"])
        self.assertIn("raised", b.eval("document.getElementById('pkSrcIn').dataset.ph"))
        b.click('#pkProps [data-pkp="st"]')
        b.wait("document.querySelector('.pkpop')")
        self.assertEqual(b.eval("[...document.querySelectorAll('.pkpop .pkopt[aria-disabled=\"true\"]')].map(o=>o.textContent)"),
                         ["WithdrawnA new decision is pending or made"])
        b.key("Escape")
        b.eval("closePanel()")
        b.eval("openRecord('decisions',DEC[0].id)")                                             # an existing one has no Source line
        self.assertTrue(b.eval("document.getElementById('pkSrcIn').hidden"))
        b.eval("closePanel()")

    def test_the_create_form_is_no_longer_reachable_for_work_items(self):
        b = self.b
        for k in ("actions", "raid", "decisions"):
            self.new(k)
            self.assertEqual(b.eval("document.querySelectorAll('#pFields [name]').length"), 0, k)
            self.assertFalse(b.eval("document.getElementById('pSave')"), k)
            b.eval("closePanel()")
        b.eval("openCk()")                                                                        # the command palette's New action
        b.wait("document.getElementById('cmdk').open")
        b.type("New action")
        b.pump(0.3)
        b.key("Enter")
        b.wait("CUR&&CUR.mode==='new'")
        self.assertTrue(b.eval("document.getElementById('panel').classList.contains('peek')"))
        self.assertEqual(b.eval("document.querySelectorAll('#pFields [name]').length"), 0)
        b.eval("closePanel()")
        b.eval("openNewMilestone('ABC')")                                                       # BL-186: a milestone opens in its editor
        b.wait("MV.add&&!document.getElementById('mvPeek').hidden")
        self.assertFalse(b.eval("!!document.querySelector('#pFields [name=\"name\"]')"))
        b.eval("mvEdClose(true)")


class FirstCommit(NewCase):
    """Each test changes data, so each has its own vault and server."""

    def proposal(self, name):
        import json
        return json.loads((self.v.root / "system/staging" / name).read_text())

    def pick(self, field, label, where="#panel"):
        b = self.b
        b.click(f'{where} [data-pkp="{field}"]')
        b.wait("document.querySelector('.pkpop')")
        b.eval(f"[...document.querySelectorAll('.pkpop .pkopt')].find(o=>o.querySelector('span').firstChild.textContent==={label!r}).click()")

    def settle(self):
        self.b.eval("pkQuiet().then(()=>true)")
        self.b.pump(0.2)

    def test_the_title_with_a_project_stages_one_new_proposal_and_later_edits_update_it(self):
        b = self.b
        self.new("actions")
        b.type("Book the steering room")
        b.key("Enter")
        self.settle()
        self.assertEqual(self.staged(), [])                                                     # no project yet: nothing staged
        self.assertEqual(self.note(), "Choose a project.")                                      # the Create form's own words
        self.assertTrue(b.eval("document.querySelector('#pkId [data-pkp=\"p\"]').classList.contains('pkbad')"))
        self.assertEqual(b.eval("document.activeElement.dataset.pkp"), "p")                    # shown on the field
        self.pick("p", b.eval("pName('ABC')"))
        self.settle()
        files = self.staged()
        self.assertEqual(len(files), 1)
        item = self.proposal(files[0])["items"]
        self.assertEqual(len(item), 1)
        self.assertEqual((item[0]["op"], item[0]["table"], item[0]["decision"]), ("new", "actions", "approved"))
        v = item[0]["values"]
        self.assertEqual((v["description"], v["project"], v["owner"], v["status"], v["raised"]), ("Book the steering room", "ABC", "TBC", "Open", TODAY))
        self.assertEqual(v["source"], f"{b.eval('S.me')} (dashboard), {TODAY}")
        self.assertEqual(self.proposal(files[0])["source_run"], "dashboard")
        self.assertFalse(b.eval("document.querySelector('#panel .pkbad')"))
        self.assertEqual(b.eval("document.getElementById('pkStN').textContent"), "1 change staged on 1 item")
        # later edits rewrite that one proposal
        self.pick("pr", "High")
        self.settle()
        b.click('#pkProps [data-pkp="due"]')
        b.wait("document.querySelector('.pkpop .pkdt')")
        b.eval("document.querySelector('.pkpop .pkdt').focus()")
        b.type("15-10-2026")
        b.key("Enter")
        self.settle()
        b.click("#pkDesc")
        b.type("Asked facilities")
        b.eval("document.getElementById('pkDesc').blur()")
        self.settle()
        self.assertEqual(self.staged(), files)
        v = self.proposal(files[0])["items"][0]["values"]
        self.assertEqual((v["priority"], v["due_date"], v["latest_update"]), ("High", "2026-10-15", "Asked facilities"))
        self.assertEqual(b.eval("document.getElementById('pkStN').textContent"), "1 change staged on 1 item")
        self.assertEqual(self.find("actions", "description", "Book the steering room"), [])     # nothing in the tracker yet
        self.assertIn("staged", b.eval("document.getElementById('pkFeed').textContent"))
        self.assertEqual(b.errors, [])

    def test_cmd_enter_commits_applies_and_closes(self):
        b = self.b
        self.work()
        b.eval("PROJF.clear(); PROJF.add('ABC'); renderWork()")
        b.click("#newBtn")
        b.wait("CUR&&CUR.mode==='new'")
        self.assertEqual(b.eval("CUR.draft.p"), "ABC")
        b.type("Send the pack")
        b.key("Enter", 4)                                                                         # ⌘↵ from the title, before it is committed
        b.wait("!CUR&&!document.getElementById('panel').classList.contains('on')", timeout=15)
        rows = self.find("actions", "description", "Send the pack")
        self.assertEqual(len(rows), 1)
        self.assertIn(f"{rows[0]['id']} created", b.eval("document.querySelector('.snack').textContent"))
        self.assertEqual(self.staged(), [])

    def test_cmd_enter_with_a_title_that_cant_be_staged_stays_open_and_says_why(self):
        b = self.b
        self.new("decisions", "made")
        self.pick("p", b.eval("pName('ABC')"))
        self.settle()
        b.click("#pkTitle")
        b.type("Use the new API")
        b.key("Enter", 4)
        self.settle()
        self.assertTrue(b.eval("CUR&&CUR.mode==='new'"))
        self.assertEqual(self.note(), "Record where the decision was made (meeting, email or document).")
        self.assertEqual(b.eval("document.activeElement.id"), "pkSrcIn")
        self.assertEqual(self.staged(), [])
        b.type("Steering, 10-10")
        b.key("Enter", 4)
        b.wait("!CUR", timeout=15)
        rows = self.find("decisions", "decision", "Use the new API")
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["status"], rows[0]["date"]), ("Made", TODAY))
        self.assertTrue(rows[0]["source"].startswith("Steering, 10-10 — recorded by"))

    def test_once_applied_the_peek_becomes_the_item_without_closing(self):
        b = self.b
        self.new("decisions", "needed")
        self.pick("p", b.eval("pName('ABC')"))
        b.click("#pkTitle")
        b.type("Extend the pilot")
        b.key("Enter")
        self.settle()
        b.click("#pkSrcIn")
        b.type("Weekly sync")
        b.key("Enter")
        self.settle()
        self.assertEqual(len(self.staged()), 1)
        b.click("#pkApply")
        b.wait("CUR&&CUR.mode==='record'", timeout=15)
        rid = b.eval("CUR.id")
        self.assertRegex(rid, r"^ABC-D-\d{3}$")
        self.assertTrue(b.eval("document.getElementById('panel').classList.contains('on')"))
        self.assertEqual(b.eval("document.querySelector('#pkId span').textContent"), rid)
        self.assertEqual(self.find("decisions", "id", rid)[0]["status"], "Pending")
        self.assertFalse(b.eval("document.getElementById('pkMore').hidden"))                  # the item's own bar again
        self.assertTrue(b.eval("document.getElementById('pkSrcIn').hidden"))
        self.pick("st", "Made")                                              # and it behaves as any item: one change, one proposal
        self.settle()
        self.assertEqual(len(self.staged()), 1)
        self.assertEqual(self.proposal(self.staged()[0])["items"][0]["op"], "update")

    def test_undo_last_unstages_it_and_a_refused_change_is_put_back(self):
        b = self.b
        self.new("actions")
        self.pick("p", b.eval("pName('ABC')"))
        b.click("#pkTitle")
        b.type("Draft the plan")
        b.key("Enter")
        self.settle()
        self.assertEqual(len(self.staged()), 1)
        b.eval("document.getElementById('pkTitle').textContent=''; document.getElementById('pkTitle').focus(); document.getElementById('pkTitle').blur()")
        self.settle()
        self.assertEqual(b.eval("CUR.draft.t"), "Draft the plan")                              # an empty title is refused
        b.click("#pkUndo")
        b.wait("CUR&&CUR.mode==='new'&&!CUR.staged")
        self.assertEqual(self.staged(), [])
        self.assertIn("no longer staged", b.eval("document.querySelector('.snack').textContent"))
        self.assertTrue(b.eval("document.getElementById('pkStage').hidden"))
        b.click("#pkTitle")
        b.key("Enter")                                                                            # committing the title again stages it again
        self.settle()
        self.assertEqual(len(self.staged()), 1)

    def test_the_create_forms_rules_hold(self):
        b = self.b
        self.new("actions")
        self.pick("p", b.eval("pName('ABC')"))
        b.click("#pkTitle")
        b.type("Client update")
        b.key("Enter")
        self.settle()
        b.click("#pkDetT")
        b.click('#pkDet [data-pksw="client"]')                                                  # client-visible waits for its messaging
        self.settle()
        v = self.proposal(self.staged()[0])["items"][0]["values"]
        self.assertEqual(v["client_visible"], 0)
        b.eval("""(()=>{ const m=document.querySelector('#pkDet [data-pkf="cm"]'); m.textContent='What it is: A slip\\nWhat it means for you: Later\\nWhat is being done: A plan'; m.blur(); })()""")
        self.settle()
        v = self.proposal(self.staged()[0])["items"][0]["values"]
        self.assertEqual(v["client_visible"], 1)
        self.assertIn("A plan", v["client_message"])
        self.pick("st", "Closed")                                                                  # the closed date, as norm sets it
        self.settle()
        v = self.proposal(self.staged()[0])["items"][0]["values"]
        self.assertEqual((v["status"], v["closed"]), ("Closed", TODAY))


class LeavingEarly(NewCase):
    def drafts(self):
        return self.b.eval("Object.keys(store.get('creaite-panel-drafts',{}))")

    def asking(self):
        return self.b.eval("!document.getElementById('pkAsk').hidden")

    def test_esc_or_a_click_away_on_an_empty_peek_stages_nothing(self):
        b = self.b
        self.new("actions")
        b.key("Escape")                                                                           # from the title
        b.wait("!CUR")
        self.new("raid")
        b.eval("document.activeElement.blur()")
        b.key("Escape")                                                                           # from outside a field
        b.wait("!CUR")
        self.new("decisions", "needed")
        b.click("#workQ")                                                                         # a click away
        b.wait("!CUR")
        self.assertEqual(self.staged(), [])
        self.assertEqual(self.drafts(), [])
        self.assertEqual(b.errors, [])

    def test_with_a_title_it_asks_keep_or_discard(self):
        b = self.b
        self.new("actions")
        b.type("Half typed")
        b.key("Escape")                                                                           # Esc keeps the words and asks
        b.wait("!document.getElementById('pkAsk').hidden")
        self.assertEqual(b.eval("document.getElementById('pkTitle').textContent"), "Half typed")
        self.assertIn("it needs a project", b.eval("document.getElementById('pkAskT').textContent"))
        self.assertEqual(b.eval("document.activeElement.dataset.pkask"), "keep")
        b.key("Escape")                                                                           # Esc on the question: back to editing
        b.wait("document.getElementById('pkAsk').hidden")
        self.assertTrue(b.eval("CUR&&CUR.mode==='new'"))
        b.click("#workQ")                                                                         # a click away asks too
        b.wait("!document.getElementById('pkAsk').hidden")
        self.assertTrue(b.eval("CUR&&CUR.mode==='new'"))
        b.click('#pkAsk [data-pkask="discard"]')
        b.wait("!CUR")
        self.assertEqual(self.drafts(), [])
        self.assertEqual(self.staged(), [])
        # another row asks first, then opens it
        self.new("actions")
        b.type("Another")
        rid = b.eval("A[0].id")
        b.eval(f"openRecord('actions',{rid!r})")
        self.assertTrue(self.asking())
        b.click('#pkAsk [data-pkask="keep"]')
        b.wait(f"CUR&&CUR.id==={rid!r}")
        self.assertEqual(self.drafts(), ["new:actions"])
        self.assertEqual(self.staged(), [])

    def test_a_staged_new_item_closes_without_asking(self):
        b = self.b
        self.work()
        b.eval("PROJF.clear(); PROJF.add('ABC'); renderWork(); openNew('actions')")
        b.type("Staged one")
        b.key("Enter")
        b.eval("pkQuiet().then(()=>true)")
        self.assertEqual(len(self.staged()), 1)
        b.key("Escape")
        b.wait("!CUR")
        self.assertEqual(self.drafts(), [])
        self.assertFalse(b.eval("document.getElementById('pkStage').hidden"))                  # the pill still shows it

    def test_an_unstaged_new_item_survives_a_reload(self):
        b = self.b
        self.new("decisions", "made")
        b.type("Adopt the new API")
        b.pump(0.5)                                                                               # kept as it is typed
        b.reload()
        b.wait("typeof go==='function' && LIVE")
        self.new("decisions", "made")
        offer = b.eval("document.getElementById('pkDraft').textContent")
        self.assertIn("An unsaved new decision from", offer)
        self.assertIn("Adopt the new API", offer)
        b.click('#pkDraft [data-pknd="restore"]')
        self.assertEqual(b.eval("CUR.draft.t"), "Adopt the new API")
        self.assertEqual(b.eval("document.activeElement.id"), "pkTitle")
        self.assertEqual(self.staged(), [])                                                       # nothing reaches the vault yet
        b.eval("closePanel()")                                                                    # it has a title: asks
        self.assertTrue(self.asking())
        b.click('#pkAsk [data-pkask="discard"]')
        b.wait("!CUR")
        self.new("decisions", "made")
        self.assertTrue(b.eval("document.getElementById('pkDraft').hidden"))
        b.eval("closePanel()")

    def test_a_create_form_draft_and_an_old_one(self):
        b = self.b
        b.eval("store.set('creaite-panel-drafts',{'new:actions':{fields:{t:'From the old form',due:'15-10-2026'},at:Date.now(),base:''}})")
        self.new("actions")
        b.click('#pkDraft [data-pknd="restore"]')
        self.assertEqual(b.eval("[CUR.draft.t, CUR.draft.due]"), ["From the old form", "2026-10-15"])   # the form kept dates as typed
        b.eval("CUR.draft.t=''; document.getElementById('pkTitle').textContent=''; closePanel()")
        b.eval("store.set('creaite-panel-drafts',{'new:raid':{fields:{t:'Old'},at:Date.now()-8*864e5,base:'',peek:1}})")
        self.new("raid")
        self.assertIn("more than 7 days old", b.eval("document.getElementById('pkDraft').textContent"))
        self.assertEqual(self.drafts(), [])
        b.eval("closePanel()")


if __name__ == "__main__":
    unittest.main()
