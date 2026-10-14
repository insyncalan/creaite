"""BL-186 stage B (sprint-milestones): Milestones: Plan and Movement, the cockpit's card and the milestone editor, as the mockup
(dev/mockups/milestones-views-mockup.html) sets them out. A real browser against the real live server, on milestone_data's project.

Run: python3 dev/tests/test_milestones_page.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
import milestone_data  # noqa: E402
from milestone_data import d  # noqa: E402


class Case(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        milestone_data.load(v)

    def setUp(self):
        super().setUp()
        self.b.eval("try{ localStorage.removeItem('creaite.cockpit.milestones.view'); localStorage.removeItem('creaite.cockpit.milestones.details'); }catch(e){}")
        # BL-244 (sprint-milestone-ui) made Client the first-visit view; these tests start in Internal view, as BL-186's did
        # (test_milestone_ui checks the default)
        self.b.eval("MVAUD='int'; try{ localStorage.setItem('creaite.cockpit.milestones.view','int'); }catch(e){}")
        self.b.eval("S.autoApply=true")

    def cockpit(self):
        self.b.eval("go('cockpit','ABC')")
        self.b.wait("document.getElementById('mvCard')")

    def page(self, view="plan"):
        self.b.eval(f"mvOpenPage('ABC','{view}')")
        self.b.wait("VIEW==='milestones'&&document.querySelector('#v-milestones .mv-card')")

    def ms(self, id_):
        return next(m for m in self.v.rows("milestones") if m["id"] == id_)

    def until(self, fn, seconds=20):
        end = time.time() + seconds
        while time.time() < end:
            if fn():
                return True
            self.b.pump(0.2)
        return False

    def edit(self, id_):
        self.b.click(f'#v-milestones .mv-prow[data-mvedit="{id_}"]')
        self.b.wait(f"MV.peek==='{id_}'&&!document.getElementById('mvPeek').hidden")


class CardAndPage(Case):
    def test_the_card_shows_the_plan_and_its_pencil_opens_the_page(self):
        b = self.b
        self.cockpit()
        card = b.eval("(()=>{ const c=document.getElementById('mvCard'); return {cls:c.className, pill:c.querySelector('.mv-pill').innerText, move:/Movement/.test(c.innerText), add:!!c.querySelector('[data-msnew]')}; })()")
        self.assertIn("internal", card["cls"])
        self.assertEqual(card["pill"].strip().upper(), "INTERNAL VIEW")
        self.assertFalse(card["move"])                                          # the card never shows Movement
        self.assertFalse(card["add"])                                           # the pencil no longer adds
        self.assertEqual(b.eval("getComputedStyle(document.getElementById('mvCard')).borderTopStyle"), "solid")   # BL-244: a bright border
        self.assertEqual(b.eval("document.getElementById('mvPencil').getAttribute('aria-label')"), "Open milestones: Plan and Movement")
        b.click("#mvPencil")
        b.wait("VIEW==='milestones'")
        self.assertEqual(b.eval("location.hash"), "#milestones=ABC&v=plan")
        self.assertEqual(b.eval("[...document.querySelectorAll('#v-milestones .crumb a, #v-milestones .crumb [aria-current]')].map(e=>e.textContent)"),
                         ["Projects", "Example Programme", "Milestones"])
        self.assertIn("Example Programme milestones", b.eval("document.title"))
        self.assertEqual(b.eval("document.querySelector('.rail button[data-v=\"projects\"]').getAttribute('aria-current')"), "page")
        self.assertTrue(b.eval("MV.peek===null&&document.getElementById('mvPeek')===null||document.getElementById('mvPeek').hidden"))
        b.click('#v-milestones .crumb a[data-proj="ABC"]')                       # the breadcrumb returns to the cockpit
        b.wait("VIEW==='cockpit'&&COCK==='ABC'")
        self.assertEqual(b.errors, [])

    def test_the_switch_flips_the_card_only_and_is_remembered(self):
        b = self.b
        self.cockpit()
        rest = "document.querySelector('#v-cockpit .evrow').innerText+document.querySelector('#v-cockpit .cock').innerText.replace(document.getElementById('mvCard').innerText,'')"
        before = b.eval(rest)
        sw = b.eval("[document.getElementById('mvSwap').getAttribute('aria-pressed'),document.getElementById('mvSwap').getAttribute('aria-label')]")
        self.assertEqual(sw, ["false", "Switch to client view"])
        b.click("#mvSwap")
        b.wait("document.getElementById('mvCard').classList.contains('client')")
        self.assertEqual(b.eval("[document.getElementById('mvSwap').getAttribute('aria-pressed'),document.getElementById('mvSwap').getAttribute('aria-label')]"),
                         ["true", "Switch to internal view"])
        c = b.eval("(()=>{ const c=document.getElementById('mvCard'); return {pill:!!c.querySelector('.mv-pill'), int:!!c.querySelector('.mv-pill.int'), note:!!c.querySelector('.mv-hidenote'), style:getComputedStyle(c).borderTopStyle, text:c.innerText}; })()")
        self.assertFalse(c["pill"])                                             # BL-244: the Client view is plain, with no pill
        self.assertFalse(c["int"])                                              # the internal mark is absent in Client view
        self.assertFalse(c["note"])
        self.assertEqual(c["style"], "solid")
        self.assertNotIn("Security review", c["text"])
        self.assertNotIn("Dates suggest", c["text"])
        self.assertIn("Expected later", c["text"])                              # the client's words
        self.assertEqual(b.eval(rest), before)                                  # the rest of the cockpit is unchanged
        b.reload()
        b.wait("typeof go==='function'&&LIVE")
        self.cockpit()
        self.assertTrue(b.eval("document.getElementById('mvCard').classList.contains('client')"))   # remembered
        self.page()
        self.assertTrue(b.eval("document.getElementById('mvACli').getAttribute('aria-pressed')==='true'"))   # the same choice on the page

    def test_the_details_toggle_is_on_the_left_and_remembered(self):
        b = self.b
        self.cockpit()
        x = b.eval("(()=>{ const t=document.querySelector('#mvCard [data-mvact=det]').getBoundingClientRect(), c=document.getElementById('mvCard').getBoundingClientRect(); return [t.left-c.left, c.right-t.right]; })()")
        self.assertLess(x[0], x[1])
        b.click("#mvCard [data-mvact=det]")
        b.wait("document.getElementById('mvRows-card').hidden")
        self.assertTrue(b.eval("!!document.querySelector('#mvCard .mv-stripwrap')"))   # the line stays
        b.reload()
        b.wait("typeof go==='function'&&LIVE")
        self.cockpit()
        self.assertTrue(b.eval("document.getElementById('mvRows-card').hidden"))
        self.assertEqual(b.eval("document.querySelector('#mvCard [data-mvact=det]').textContent.trim()"), "Show milestone details")

    def test_the_line_keeps_achieved_milestones_and_never_overlaps_labels(self):
        b = self.b
        self.page()
        ach = b.eval("[...document.querySelectorAll('#v-milestones .mv-mk.achieved')].map(e=>e.getAttribute('aria-label'))")
        self.assertTrue(any("Build complete (platform)" in a and "achieved" in a for a in ach))
        self.assertTrue(b.eval("[...document.querySelectorAll('#v-milestones .mv-lab.ok span')].some(s=>s.textContent==='" + milestone_data.d(-28)[8:10] + "-" + milestone_data.d(-28)[5:7] + "-" + milestone_data.d(-28)[:4] + "')"))
        overlap = b.eval("""(()=>{ const L=[...document.querySelectorAll('#v-milestones .mv-lab')].map(e=>{ const r=e.getBoundingClientRect(); return [r.left,r.top,r.right,r.bottom]; });
          for(let i=0;i<L.length;i++) for(let j=i+1;j<L.length;j++){ const a=L[i], c=L[j]; if(a[0]<c[2]-1&&c[0]<a[2]-1&&a[1]<c[3]-1&&c[1]<a[3]-1) return [i,j]; } return null; })()""")
        self.assertIsNone(overlap)
        rings = b.eval("[...document.querySelectorAll('#v-milestones .mv-lab.gl')].map(e=>e.innerText.replace(/\\s+/g,' '))")
        self.assertTrue(any("Expected" in r and "Go-live" in r for r in rings))
        b.click("#mvACli")                                                      # the ring follows Visible to client
        b.wait("document.getElementById('mvPlanCard').classList.contains('client')")
        rings = b.eval("[...document.querySelectorAll('#v-milestones .mv-lab.gl')].map(e=>e.innerText)")
        self.assertTrue(any("Go-live" in r for r in rings))
        self.assertFalse(any("UAT start" in r for r in rings))                  # UAT start is internal: no ring for the client

    def test_client_view_hides_internal_milestones_notes_and_movement(self):
        b = self.b
        self.page("move")
        self.assertIn("Request re-submitted", b.eval("document.getElementById('mvNote')?.value||''"))
        b.click("#mvACli")
        b.wait("MV.view==='plan'&&document.getElementById('mvVMove').getAttribute('aria-disabled')==='true'")
        self.assertEqual(b.eval("location.hash"), "#milestones=ABC&v=plan")
        text = b.eval("document.getElementById('v-milestones').innerText")
        for internal in ("Security review", "UAT start", "Internal only", "Dates suggest", "Request re-submitted", "Rebaselined", "Revised from", "Moved"):
            self.assertNotIn(internal, text)
        self.assertIn("Late", text)                                             # an overdue milestone reads Late to the client
        b.click("#mvVMove")
        b.wait("document.getElementById('snackT').textContent.includes('internal only')")
        self.assertEqual(b.eval("MV.view"), "plan")

    def test_back_forward_and_reload_keep_the_page_the_view_and_the_milestone(self):
        b = self.b
        self.cockpit()
        b.click("#mvPencil")
        b.wait("VIEW==='milestones'")
        b.click("#mvVMove")
        b.wait("location.hash==='#milestones=ABC&v=movement'")
        b.click('#v-milestones [data-mvsel="ABC-M-007"]')
        b.click('#mvDetail [data-mvedit="ABC-M-007"]')
        b.wait("location.hash==='#milestones=ABC&v=movement&ms=ABC-M-007'")
        b.reload()
        b.wait("typeof go==='function'&&LIVE&&VIEW==='milestones'&&MV.peek==='ABC-M-007'", 20)
        self.assertEqual(b.eval("MV.view"), "move")
        b.eval("history.back()")
        b.wait("location.hash==='#milestones=ABC&v=plan'")
        b.eval("history.back()")
        b.wait("VIEW==='cockpit'")
        b.eval("history.forward()")
        b.wait("VIEW==='milestones'&&MV.view==='plan'")
        self.assertEqual(b.errors, [])

    def test_the_slip_metric_opens_movement_in_internal_view(self):
        b = self.b
        self.cockpit()
        b.click("#mvSwap")
        b.wait("MVAUD==='cli'")
        b.click("#v-cockpit [data-msjump]")
        b.wait("VIEW==='milestones'&&MV.view==='move'")
        self.assertEqual(b.eval("MVAUD"), "int")
        self.assertIn("Switched to Internal view", b.eval("document.getElementById('snackT').textContent"))
        self.assertIn("Internal only: never in client output", b.eval("document.getElementById('v-milestones').innerText"))

    def test_the_palette_search_and_citations_open_the_page(self):
        b = self.b
        b.eval("openNewMilestone('ABC')")
        b.wait("VIEW==='milestones'&&MV.add&&!document.getElementById('mvPeek').hidden")
        self.assertEqual(b.eval("document.activeElement.id"), "mvName")
        b.eval("go('today')")
        b.eval("openMilestone('ABC-M-005')")
        b.wait("VIEW==='milestones'&&MV.peek==='ABC-M-005'")
        self.assertEqual(b.eval("location.hash"), "#milestones=ABC&v=plan&ms=ABC-M-005")


class Editor(Case):
    def test_state_rules_reason_suggestion_and_achieved(self):
        b = self.b
        self.page()
        self.edit("ABC-M-007")                                                  # Go-live: the dates say Slipped
        self.assertIn("Following the dates", b.eval("document.querySelector('#mvPeek .mv-explain').innerText"))
        b.click('#mvPeek [data-mvstate="ontrack"]')                             # better than the dates: a reason is required
        b.wait("document.getElementById('mvFlWhy')")
        b.click('#mvPeek [data-mvpk="flok"]')
        self.assertIn("better than the dates suggest", b.eval("document.getElementById('mvFlErr').textContent"))
        b.eval("document.getElementById('mvFlWhy').value='Vendor confirmed a recovery plan'")
        b.click('#mvPeek [data-mvpk="flok"]')
        self.assertTrue(self.until(lambda: self.ms("ABC-M-007")["state"] == "On track"))
        self.assertEqual(self.ms("ABC-M-007")["state_reason"], "Vendor confirmed a recovery plan")
        b.wait("document.querySelector('#mvPeek [data-mvpk=usesug]')")
        b.click('#mvPeek [data-mvpk="usesug"]')                                 # "Use Slipped" returns to the dates
        self.assertTrue(self.until(lambda: self.ms("ABC-M-007")["state"] is None))
        b.wait("mvGet('ABC','ABC-M-007').manual===false")                         # the page has the applied change
        b.wait("MV.peek==='ABC-M-007'&&document.querySelector('#mvPeek [data-mvstate=overdue]')")
        b.click('#mvPeek [data-mvstate="overdue"]')                             # worse than the dates: the reason is optional
        b.wait("document.getElementById('mvFlWhy')")
        self.assertIn("(optional)", b.eval("document.querySelector('#mvPeek .mv-inl').innerText"))
        b.click('#mvPeek [data-mvpk="flok"]')
        self.assertTrue(self.until(lambda: self.ms("ABC-M-007")["state"] == "Overdue"))
        b.wait("mvGet('ABC','ABC-M-007').state==='overdue'")
        b.wait("document.querySelector('#mvPeek [data-mvstate=achieved]')")
        b.click('#mvPeek [data-mvstate="achieved"]')                            # Achieved asks for the date
        b.wait("document.getElementById('mvFlDate')")
        b.click('#mvPeek [data-mvpk="flok"]')
        self.assertTrue(self.until(lambda: self.ms("ABC-M-007")["status"] == "Done"))
        m = self.ms("ABC-M-007")
        self.assertEqual((m["state"], m["actual_date"], m["percent_complete"]), ("Achieved", d(0), 100))
        self.assertEqual(b.errors, [])

    def test_the_forecast_comes_from_the_calendar_and_asks_why(self):
        b = self.b
        self.page()
        self.edit("ABC-M-006")
        b.click("#mvFc")
        b.wait("!document.getElementById('mvCal').hidden")
        self.assertTrue(b.eval("[...document.querySelectorAll('#mvCal button.wk')].every(x=>/weekend/.test(x.getAttribute('aria-label')))"))
        self.assertEqual(b.eval("document.querySelectorAll('#mvCal input').length"), 0)   # never typed
        b.key("ArrowDown")                                                       # a week later, by keyboard
        b.key("Enter")
        b.wait("document.getElementById('mvFcWhy')")
        self.assertEqual(b.eval("document.getElementById('mvCal').hidden"), True)
        b.click("#v-milestones h1")                                             # waiting for its reason: the editor stays
        b.wait("document.getElementById('snackT').textContent.includes('Finish or cancel the pending change first')")
        self.assertFalse(b.eval("document.getElementById('mvPeek').hidden"))
        b.eval("document.getElementById('mvFcWhy').value='Licences arrive late'")
        b.click('#mvPeek [data-mvpk="fcok"]')
        self.assertTrue(self.until(lambda: self.ms("ABC-M-006")["forecast_date"] == d(30)))
        notes = [r["new_value"] for r in self.v.rows("change_log") if r["item_id"] == "ABC-M-006" and r["field"] == "note"]
        self.assertEqual(notes, ["Licences arrive late"])

    def test_an_outside_click_closes_with_its_exceptions(self):
        b = self.b
        self.page()
        self.edit("ABC-M-005")
        b.click("#mvOwner")                                                     # a people list is open: the first click closes only it
        b.wait("!document.getElementById('mvPop').hidden")
        b.click("#v-milestones h1")
        b.wait("document.getElementById('mvPop').hidden")
        self.assertFalse(b.eval("document.getElementById('mvPeek').hidden"))
        b.eval("document.querySelector('#v-milestones .mv-prow[data-mvedit=\"ABC-M-004\"]').scrollIntoView()")
        b.click('#v-milestones .mv-lab[data-mvedit="ABC-M-003"]') if False else b.eval("document.querySelector('#v-milestones .mv-prow[data-mvedit=\"ABC-M-004\"]').click()")
        b.wait("MV.peek==='ABC-M-004'&&!document.getElementById('mvPeek').hidden")   # another milestone switches
        b.click("#v-milestones h1")
        b.wait("document.getElementById('mvPeek').hidden")                      # an ordinary click outside closes it

    def test_add_milestone_keeps_the_editor_open_and_creates_it(self):
        b = self.b
        self.page()
        b.click("#mvAdd")
        b.wait("MV.add&&!document.getElementById('mvPeek').hidden")
        b.pump(0.3)
        self.assertFalse(b.eval("document.getElementById('mvPeek').hidden"))   # the opening click isn't an outside click
        b.type("Training delivered")
        b.key("Enter")
        self.assertTrue(self.until(lambda: any(m["name"] == "Training delivered" for m in self.v.rows("milestones"))))
        b.wait("MV.peek&&document.getElementById('mvName').value==='Training delivered'")
        new = next(m for m in self.v.rows("milestones") if m["name"] == "Training delivered")
        self.assertEqual(b.eval("MV.peek"), new["id"])
        b.click("#mvAgr")                                                       # its first agreed date is a calendar pick, not a rebaseline
        b.wait("!document.getElementById('mvCal').hidden")
        b.click("#mvCal [data-mvtoday]")
        self.assertTrue(self.until(lambda: self.ms(new["id"])["baseline_date"] == d(0)))
        self.assertEqual(self.v.rows("decisions")[-1]["decision"].startswith("Go-live"), True)   # no new decision

    def test_owner_progress_description_and_client_view(self):
        b = self.b
        self.page()
        self.edit("ABC-M-005")
        b.click("#mvOwner")
        b.wait("!document.getElementById('mvPop').hidden")
        b.type("Omar")
        b.key("Enter")
        self.assertTrue(self.until(lambda: self.ms("ABC-M-005")["owner"] == "Omar Ali"))
        b.wait("document.getElementById('mvOwner').textContent.includes('Omar Ali')")
        b.eval("const n=document.getElementById('mvNum'); n.value='45'; n.dispatchEvent(new Event('change',{bubbles:true}))")
        self.assertTrue(self.until(lambda: self.ms("ABC-M-005")["percent_complete"] == 45))
        b.wait("document.getElementById('mvNum').value==='45'")
        b.click("#mvCli")                                                        # visible waits for its wording
        b.wait("!document.getElementById('mvCw').disabled")
        self.assertEqual(self.ms("ABC-M-005")["client_visible"], 0)
        b.eval("const c=document.getElementById('mvCw'); c.value='Testing starts once the data is in.'; c.dispatchEvent(new Event('change',{bubbles:true}))")
        self.assertTrue(self.until(lambda: self.ms("ABC-M-005")["client_visible"] == 1))
        self.assertEqual(self.ms("ABC-M-005")["client_message"], "Testing starts once the data is in.")


class Movement(Case):
    def test_rebaseline_stages_a_proposal_with_its_decision(self):
        b = self.b
        self.page("move")
        b.click('#v-milestones [data-mvsel="ABC-M-008"]')
        b.wait("MV.sel==='ABC-M-008'")
        self.assertIn("Movement by reporting week", b.eval("document.getElementById('mvDetail').innerText"))
        b.click('#mvDecide [data-mvadj="rebase"]')
        b.wait("document.getElementById('mvRbForm')")
        b.click('#mvRbForm [data-mvrb="ok"]')
        self.assertIn("Choose who agreed it", b.eval("document.getElementById('mvRbErr').textContent"))
        b.click("#mvRbAdd")
        b.wait("!document.getElementById('mvPop').hidden")
        b.type("Sara")
        b.key("Enter")
        b.wait("document.querySelectorAll('#mvRbForm .mv-chip').length===1")
        b.eval("document.getElementById('mvRbWhy').value='Hypercare follows the new go-live'")
        b.click('#mvRbForm [data-mvrb="ok"]')
        b.wait("document.getElementById('snackT').textContent.includes('Staged for Review')")
        props = [json.loads(p.read_text()) for p in (self.v.root / "system/staging").glob("proposed-*-dashboard*.json")]
        item = next(i for p in props for i in p["items"] if i.get("rebaseline"))
        self.assertEqual((item["decision"], item["changes"]["baseline_date"], item["rebaseline"]["agreed_with"]), ("pending", d(118), ["Sara Example"]))
        self.assertEqual(self.ms("ABC-M-008")["baseline_date"], d(111))           # nothing changes until it is approved
        n = b.eval("REV.find(r=>r.file&&JSON.stringify(r).includes('ABC-M-008')).n")
        b.eval(f"decide({n},'approved')")
        self.assertTrue(self.until(lambda: self.ms("ABC-M-008")["baseline_date"] == d(118)))
        self.assertTrue(any(x["made_by"] == "Sara Example" and "Hypercare" in x["decision"] for x in self.v.rows("decisions")))

    def test_hold_recover_and_escalate_are_staged_for_review(self):
        b = self.b
        self.page("move")
        b.click('#v-milestones [data-mvsel="ABC-M-004"]')
        for k, text in (("hold", "Waiting on the client's security team"), ("recover", "Recover data access: call the client CIO"),
                        ("escalate", None)):
            b.click(f'#mvDecide [data-mvadj="{k}"]')
            b.wait("document.getElementById('mvAdjWhy')")
            if text:
                b.eval(f"document.getElementById('mvAdjWhy').value={text!r}")
            b.click("#mvAdjForm [data-mvadjok]")
            b.wait("document.getElementById('snackT').textContent.includes('Staged for Review')")
        items = [i for p in (self.v.root / "system/staging").glob("proposed-*-dashboard*.json") for i in json.loads(p.read_text())["items"]]
        kinds = sorted((i["table"], i["values"].get("status", "")) for i in items)
        self.assertEqual(kinds, [("actions", ""), ("decisions", "Made"), ("decisions", "Pending")])
        self.assertTrue(all(i["decision"] == "pending" for i in items))
        self.assertEqual(next(i for i in items if i["table"] == "actions")["values"]["milestone"], "ABC-M-004")

    def test_the_internal_note_saves_on_leaving_the_box(self):
        b = self.b
        self.page("move")
        b.click('#v-milestones [data-mvsel="ABC-M-007"]')
        b.wait("document.getElementById('mvNote')")
        b.eval("const n=document.getElementById('mvNote'); n.value='Steering asked for a weekly view'; n.dispatchEvent(new Event('change',{bubbles:true}))")
        self.assertTrue(self.until(lambda: self.ms("ABC-M-007")["internal_note"] == "Steering asked for a weekly view"))

    def test_the_chart_and_log_come_from_the_history(self):
        b = self.b
        self.page("move")
        b.click('#v-milestones [data-mvsel="ABC-M-007"]')
        detail = b.eval("document.getElementById('mvDetail').innerText")
        self.assertIn("Rebaselined: agreed date", detail)
        self.assertIn("Forecast moved", detail)
        self.assertIn("Decision ABC-D-", detail)
        self.assertGreaterEqual(b.eval("document.querySelectorAll('#mvDetail svg.mv-tr circle').length"), 3)
        row = b.eval("document.querySelector('#v-milestones [data-mvsel=\"ABC-M-007\"]').innerText")
        self.assertIn("vs original", row)
        self.assertIn("Moved 3×", row)
        self.assertIn("No range yet: 0 of 8 closed milestones with history", detail)    # BL-184: no closed milestone slipped three times


if __name__ == "__main__":
    unittest.main()
