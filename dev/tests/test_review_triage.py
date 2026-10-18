"""BL-133 stage A: Review triage and mass change, in a real browser against the real live server.

Run: python3 dev/tests/test_review_triage.py   (needs Google Chrome; skipped otherwise)

The vault holds test_dashboard.populate's portfolio plus a mixed queue: three files of routine actions (four each), items that need a
project, a new risk, a new decision, a closing update, a conflict, and items from mail, Teams and the dashboard, some of them stale.
"""
import json
import os
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_tracker import action  # noqa: E402

MAIL = "Email · From: Priya Nair <priya.nair@client.example> · Subject: Data residency · Sent: 2026-10-08 09:00 · Link: https://outlook.office365.com/owa/?ItemID=x"
TEAMS = "Teams · Chat: Omar"


def pending(item):
    item = dict(item)
    item["decision"] = "pending"
    return item


def created(days_ago):
    fixed = os.environ.get("CREAITE_NOW")                                  # #177: days come from creaite's clock, never the real date
    now = datetime.strptime(fixed, "%Y-%m-%d %H:%M") if fixed else datetime.now()
    return (now - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:00")   # same time of day: whole days at any hour (09:00 read 0 days before 09:00)


def load_queue(v):
    for f in range(3):                                                  # twelve routine actions across three files
        items = [pending(action(i + 1, project="ABC" if (f + i) % 2 else "DEF", description=f"Batch {f} item {i}", owner="Sara Example",
                                due_date="2026-12-01", source=MAIL if f == 0 else TEAMS if f == 1 else "Dashboard (Alan), 2026-10-08"))
                 for i in range(4)]
        p = v.propose(f"2026-10-0{f + 1}-0900-batch{f}", items)
        data = json.loads(p.read_text())
        data["created"] = created(20 if f == 0 else 1)                 # the first file is stale
        p.write_text(json.dumps(data, indent=2))
    mixed = [
        pending({**action(1, description="Confirm data residency with legal", owner="Mia Hale", source=MAIL), "match": "possible"}),
        pending({**action(2, description="Send pilot invoice to finance", source=MAIL), "match": "possible"}),
        pending({"n": 3, "op": "new", "table": "raid", "match": "strong", "flags": [], "values": {"project": "ABC", "type": "Risk",
                 "description": "Scope creep from the pilot dataset", "owner": "Alan Carter", "impact": "High", "likelihood": "Medium", "source": TEAMS}}),
        pending({"n": 4, "op": "new", "table": "decisions", "match": "strong", "flags": [], "values": {"project": "ABC",
                 "decision": "Approve the revised timeline", "made_by": "Sara Example", "date": "2026-10-07", "source": TEAMS}}),
        pending({**action(5, description="A routine one with a conflict", source=TEAMS), "flags": ["conflict"]}),
        pending({"n": 6, "op": "update", "table": "actions", "id": "ABC-A-001", "match": "strong", "flags": [], "changes": {"status": "Closed"}, "source": TEAMS}),
        pending({"n": 7, "op": "update", "table": "projects", "id": "ABC", "match": "strong", "flags": [], "changes": {"health": "At risk", "health_reason": "Test"}, "source": TEAMS}),
    ]
    v.propose("2026-10-05-0900-mixed", mixed)


class Triage(LiveBrowserCase):
    width, height = 1500, 1100

    @classmethod
    def load(cls, v):
        populate(v)
        load_queue(v)
        for p in (v.root / "system/staging").glob("proposed-*.json"):   # only batch 0 is stale, whatever today is (propose stamps a fixed 2026-10-04)
            if not p.name.endswith("-batch0.json"):
                data = json.loads(p.read_text())
                data["created"] = created(1)
                p.write_text(json.dumps(data, indent=2))

    def open_review(self):
        b = self.b
        b.eval("go('review')")
        b.wait("document.querySelector('#reviewBody tr[data-n]')")
        return b

    def staged(self):
        out = {}
        for p in sorted((self.v.root / "system/staging").glob("proposed-*.json")):
            out[p.name] = json.loads(p.read_text())
        for p in sorted((self.v.root / "system/staging/applied").glob("proposed-*.json")):
            out[p.name] = json.loads(p.read_text())
        return out

    def test_twelve_approvals_across_three_files_none_lost(self):
        b = self.open_review()
        ns = b.eval("REV.filter(r=>/^Batch /.test(r.rec.t)).map(r=>r.n)")
        self.assertEqual(len(ns), 12)
        b.eval(f"RHL.clear(); CHK.clear(); {json.dumps(ns)}.forEach(n=>{{ RHL.add(n); CHK.add(n); }}); renderReview()")
        b.click("#bulkApprove")
        b.wait("/Approved 12/.test(document.getElementById('snackT').textContent) || /Applied 12/.test(document.getElementById('snackT').textContent)", 20)
        b.wait("!REV.some(r=>/^Batch /.test(r.rec.t))", 20)
        made = [r["description"] for r in self.v.rows("actions") if r["description"].startswith("Batch ")]
        self.assertEqual(len(made), 12, made)


    # ── the bar and the bulk rule ──
    def select(self, ns):
        self.b.eval(f"RHL.clear(); {json.dumps(ns)}.forEach(n=>RHL.add(n)); rvSyncChk(); renderReview()")

    def test_the_bar_counts_and_the_split(self):
        b = self.open_review()
        self.assertTrue(b.eval("document.getElementById('rvbar').hidden"))
        info = b.eval("REV.filter(r=>!r.done).map(r=>({n:r.n,t:r.rec.t,ok:rvBulkOK(r),why:rvBulkOK(r)?'':rvWhyNot(r)[0]}))")
        pick = [next(i for i in info if i["ok"]), next(i for i in info if i["t"].startswith("Scope creep")),
                next(i for i in info if i["t"].startswith("Confirm data residency")), next(i for i in info if "conflict" in i["t"])]
        self.select([p["n"] for p in pick])
        self.assertFalse(b.eval("document.getElementById('rvbar').hidden"))
        self.assertEqual(b.eval("document.getElementById('rvCount').textContent"), "4 selected")
        split = b.eval("document.getElementById('rvSplit').textContent")
        self.assertEqual(split, "1 can be approved together · 1 needs individual approval · 1 needs a project · 1 has a conflict")
        why = b.eval("document.querySelector('#rvSplit .rvwhy').title")
        self.assertIn("Scope creep from the pilot dataset: new risk is never approved in bulk", why)       # named on hover
        self.assertEqual(b.eval("[document.getElementById('bulkApprove').textContent, document.getElementById('bulkReject').textContent]"), ["Approve (1)", "Reject with a reason R"])   # BL-315
        self.assertEqual(b.eval("document.getElementById('bulkReject').getAttribute('aria-label')"), "Reject 4 proposals with a reason")
        total = b.eval("rvMatching().length")
        self.assertEqual(b.eval("document.getElementById('rvAll').textContent"), f"Select all {total}")

    def test_the_bulk_rule_holds_for_every_excluded_kind(self):
        b = self.open_review()
        b.click("#reviewBody tr[data-n]:not(.mparent) td:first-child input")      # #229: the row is one line shorter, its centre is now the source link
        b.click("#rvAll")
        b.pump(0.2)
        und = b.eval("REV.filter(r=>!r.done).length")
        self.assertEqual(b.eval("RHL.size"), und)
        excluded = b.eval("REV.filter(r=>!r.done&&!rvBulkOK(r)).map(r=>r.rec.t)")
        kinds = b.eval("REV.filter(r=>!r.done&&!rvBulkOK(r)).map(r=>r.indiv?r.why:r.kind==='draft'?'draft':!r.p?'no project':(r.flags||[]).join())")
        for want in ("New risk", "New decision", "Closing update", "Health change", "draft", "no project", "conflict"):
            self.assertTrue(any(want.lower() in k.lower() for k in kinds), (want, kinds))
        b.click("#bulkApprove")
        b.wait("/Approved \\d+/.test(document.getElementById('rvresult').textContent)", 20)
        b.wait("!REV.some(r=>/^Batch /.test(r.rec.t))", 20)
        self.assertIn("partial", b.eval("document.getElementById('rvresult').textContent"))
        made = {r["description"] for r in self.v.rows("actions")}
        self.assertNotIn("A routine one with a conflict", made)
        self.assertNotIn("Confirm data residency with legal", made)
        self.assertFalse(any(r["description"].startswith("Scope creep") for r in self.v.rows("raid")))
        self.assertFalse(any(r["decision"].startswith("Approve the revised timeline") for r in self.v.rows("decisions")))
        self.assertNotEqual(next(r for r in self.v.rows("actions") if r["id"] == "ABC-A-001")["status"], "Closed")
        left = b.eval("REV.filter(r=>!r.done).map(r=>r.rec.t)")
        for t in excluded:
            self.assertIn(t, left)
        b.click("#rvShow")                                                             # Show them highlights what is left
        self.assertEqual(sorted(b.eval("[...RHL].map(n=>rvKey(REV.find(r=>r.n===n)))")), sorted(b.eval("RVLEFT")))

    def test_reject_covers_individual_items_but_not_minutes(self):
        b = self.open_review()
        ns = b.eval("REV.filter(r=>!r.done&&(/^Scope creep|^Approve the revised/.test(r.rec.t)||r.kind==='draft')).map(r=>r.n)")
        self.select(ns)
        b.click("#bulkReject")                                                         # BL-315: the reasons menu, then No reason
        b.wait("!!document.getElementById('rvReason')")
        b.key("0")
        b.wait("/Rejected 2/.test(document.getElementById('rvresult').textContent)", 20)
        self.assertEqual(b.eval("REV.filter(r=>r.kind==='draft'&&!r.done).length"), 1)          # the minutes stay
        rejected = [json.loads(p.read_text()) for p in (self.v.root / "system/staging").glob("proposed-*mixed*.json")] + \
                   [json.loads(p.read_text()) for p in (self.v.root / "system/staging/applied").glob("proposed-*mixed*.json")]
        self.assertEqual(sorted(i["decision"] for d in rejected for i in d["items"] if i["n"] in (3, 4)), ["rejected", "rejected"])

    def test_set_project_then_approve_and_one_learning_card(self):
        b = self.open_review()
        ns = b.eval("REV.filter(r=>!r.done&&!r.p&&r.file.includes('mixed')).map(r=>r.n)")
        self.assertEqual(len(ns), 2)
        self.select(ns)
        self.assertEqual(b.eval("document.getElementById('bulkApprove').textContent"), "Approve (0)")
        b.eval("(()=>{ const s=document.querySelector('#rvbar select[data-rvset=p]'); s.value='ABC'; s.dispatchEvent(new Event('change',{bubbles:true})); })()")
        b.wait("REV.filter(r=>r.p==='ABC'&&r.edited).length===2", 10)
        data = json.loads(next((self.v.root / "system/staging").glob("proposed-*mixed*.json")).read_text())
        items = {i["n"]: i for i in data["items"]}
        self.assertEqual([(items[n]["values"]["project"], items[n]["match"], items[n]["edited_in"]) for n in (1, 2)], [("ABC", "strong", "dashboard")] * 2)
        self.assertEqual(b.eval("document.getElementById('bulkApprove').textContent"), "Approve (2)")       # now routine
        self.assertLessEqual(b.eval("document.querySelectorAll('#rvresult [data-rvlearn]').length"), 1)   # one card, one signal per sender
        b.click("#bulkApprove")
        b.wait("/Approved 2/.test(document.getElementById('rvresult').textContent)", 20)
        made = {r["description"]: r["project"] for r in self.v.rows("actions")}
        self.assertEqual(made.get("Confirm data residency with legal"), "ABC")

    def test_per_item_refusals_are_listed_and_the_rest_change(self):
        b = self.open_review()
        abc = b.eval("REV.find(r=>/^Batch 0/.test(r.rec.t)&&r.p==='ABC').n")
        dfn = b.eval("REV.find(r=>/^Batch 0/.test(r.rec.t)&&r.p==='DEF').n")
        self.select([abc, dfn])
        self.assertTrue(b.eval("document.querySelector('#rvbar select[data-rvset=ms]').disabled"))       # different projects: not offered
        b.eval("rvSet('ms','ABC-M-001')")
        b.wait("/Left out/.test(document.getElementById('snackT').textContent)", 10)
        self.assertIn("not a milestone of Digital Enablement", b.eval("document.getElementById('snackT').textContent"))
        self.assertEqual(b.eval(f"[REV.find(r=>r.n==={abc}).rec.ms, REV.find(r=>r.n==={dfn}).rec.ms||null]"), ["ABC-M-001", None])
        b.click("#snackU")                                                             # one Undo for the change
        b.wait(f"!REV.find(r=>r.n==={abc}).rec.ms", 10)
        b.eval("rvSet('due','2020-01-01')")
        b.wait("/Nothing changed/.test(document.getElementById('snackT').textContent)", 10)
        self.assertIn("can't be in the past", b.eval("document.getElementById('snackT').textContent"))

    def test_one_undo_reverses_a_batch(self):
        b = self.open_review()
        ns = b.eval("REV.filter(r=>/^Batch 1/.test(r.rec.t)).map(r=>r.n)")
        self.select(ns)
        b.click("#bulkApprove")
        b.wait("/Approved 4/.test(document.getElementById('rvresult').textContent)", 20)
        b.wait("!REV.some(r=>/^Batch 1/.test(r.rec.t))", 20)
        self.assertEqual(len([r for r in self.v.rows("actions") if r["description"].startswith("Batch 1")]), 4)
        self.assertIn("Approved 4", b.eval("document.getElementById('rvresult').textContent"))
        b.click("#rvUndo")
        b.wait("REV.filter(r=>/^Batch 1/.test(r.rec.t)&&!r.done).length===4", 20)
        self.assertEqual(len([r for r in self.v.rows("actions") if r["description"].startswith("Batch 1")]), 0)

    def test_select_all_counts_collapsed_minutes_and_a_shift_range_skips_them(self):
        b = self.open_review()
        b.click("#reviewBody tr.mparent [data-act=t]")                                # collapse the minutes
        b.wait("!document.querySelector('#reviewBody tr.mchild')")
        kids = b.eval("kidsOf(REV.find(r=>isMin(r)),'*').map(r=>r.n)")
        trs = b.eval("[...document.querySelectorAll('#reviewBody tr[data-n]')].map(t=>+t.dataset.n)")
        i = trs.index(b.eval("REV.find(r=>isMin(r)).n"))
        b.click(f'#reviewBody tr[data-n="{trs[i - 1]}"] td.title')
        b.click(f'#reviewBody tr[data-n="{trs[i]}"] td.title', modifiers=8)      # to the collapsed minutes themselves
        self.assertFalse(set(b.eval("[...RHL]")) & set(kids))                           # a range never reaches them
        b.click("#rvAll")
        self.assertTrue(set(kids) <= set(b.eval("[...RHL]")))                           # Select all is the stated exception
        self.assertEqual(b.eval("RHL.size"), b.eval("rvMatching().length"))

    def test_filters_group_and_the_age_text(self):
        b = self.open_review()
        self.assertEqual(b.eval("document.querySelectorAll('#reviewBody .tag.stale:not(.dupt):not(.rvold)').length"), 0)   # #177: no Stale chip
        self.assertNotIn("stale", b.eval("document.getElementById('rvSub').textContent"))
        ages = b.eval("[...document.querySelectorAll('#reviewBody tr[data-n] .rvage')].map(e=>e.textContent)")
        self.assertEqual(sum(1 for a in ages if a in ("19 days", "20 days")), 4)
        self.assertIn("1 day", ages)
        b.click('#rvfilters [data-rvf="nd"]')
        b.click('#rvf-nd input[data-fk="nd"][value="stale"]')
        b.pump(0.2)
        self.assertEqual(sorted(b.eval("rvShown().map(r=>r.rec.t)")), sorted(f"Batch 0 item {i}" for i in range(4)))
        self.assertIn("Showing 4 of", b.eval("document.getElementById('rvapplied').textContent"))
        b.click('#rvf-nd [data-neg="1"]')                                             # is not
        b.pump(0.2)
        self.assertFalse(any(t.startswith("Batch 0") for t in b.eval("rvShown().map(r=>r.rec.t)")))
        self.assertIn("not", b.eval("document.querySelector('#rvapplied .fchip.neg').textContent"))
        b.click("#rvClearF")
        b.click('#rvfilters [data-rvf="k"]')
        b.click('#rvf-k input[data-fk="k"][value="raid"]')
        b.pump(0.2)
        self.assertEqual(set(b.eval("rvShown().filter(r=>!isMin(r)).map(r=>r.kind)")), {"raid"})        # minutes stay as the heading of their items
        self.assertIn("(0)", b.eval("document.getElementById('routineBtn').textContent"))       # the routine count follows the filters
        b.click("#rvClearF")
        b.click('#rvfilters [data-rvf="src"]')
        b.click('#rvf-src input[data-fk="src"][value="Mail"]')
        b.pump(0.2)
        self.assertTrue(b.eval("rvShown().every(r=>rvSrcKind(r)==='Mail')"))
        b.click("#rvClearF")
        b.click("#rvDispBtn")
        b.eval("(()=>{ const s=document.getElementById('rvGrp'); s.value='source'; s.dispatchEvent(new Event('change',{bubbles:true})); })()")
        b.pump(0.2)
        heads = b.eval("document.querySelectorAll('#reviewBody .rgroup').length")
        self.assertEqual(heads, b.eval("new Set(REV.filter(r=>!r.done).map(r=>r.file)).size"))
        b.eval("(()=>{ const s=document.getElementById('rvOrd'); s.value='age'; s.dispatchEvent(new Event('change',{bubbles:true})); s.value='kind'; s.dispatchEvent(new Event('change',{bubbles:true})); const g=document.getElementById('rvGrp'); g.value='kind'; g.dispatchEvent(new Event('change',{bubbles:true})); })()")
        self.assertEqual(b.eval("[...document.querySelectorAll('#reviewBody .rgroup h2')].map(h=>h.querySelector('.rgc').previousSibling.textContent.trim())")[0], "Actions")
        self.assertEqual(b.errors, [])

    def test_the_preview_and_the_large_batch_prompt(self):
        b = self.open_review()
        b.click("#routineBtn")
        b.wait("document.getElementById('rvDlg').open")
        n = b.eval("rvMatching().filter(rvBulkOK).length")
        self.assertEqual(b.eval("document.getElementById('rvDlgOk').textContent"), f"Approve {n}")
        body = b.eval("document.getElementById('rvDlgBody').textContent")
        self.assertIn("not included", body)
        self.assertIn("individual approval", body)
        b.click("#rvDlgCancel")
        b.wait("!document.getElementById('rvDlg').open")
        self.assertEqual(b.eval("REV.filter(r=>r.done).length"), 0)                    # Cancel changes nothing
        # filtered to Mail, Approve all routine acts on that only
        b.eval("RVF.src.add('Mail'); renderReview()")
        b.click("#routineBtn")
        b.wait("document.getElementById('rvDlg').open")
        mail = b.eval("rvMatching().filter(rvBulkOK).length")
        self.assertEqual(b.eval("document.getElementById('rvDlgOk').textContent"), f"Approve {mail}")
        b.click("#rvDlgOk")
        b.wait(f"/Approved {mail}/.test(document.getElementById('rvresult').textContent)", 20)
        self.assertEqual(len([r for r in self.v.rows("actions") if r["description"].startswith("Batch 1")]), 0)   # Teams: untouched
        # a batch over the limit asks first
        b.eval("RVF.src.clear(); RV_MAX=2; renderReview()")
        ns = b.eval("REV.filter(r=>!r.done&&rvBulkOK(r)).map(r=>r.n)")
        self.select(ns)
        b.click("#bulkApprove")
        b.wait("document.getElementById('rvDlg').open")
        b.click("#rvDlgCancel")

    def settle(self):
        """No data reload in flight and none queued from the live-update stream."""
        self.b.wait("PULSE.reloads===0 && !EVS.timer && !PULSE.busy", 30)

    def test_auto_advance_keys_and_its_setting(self):
        b = self.open_review()
        b.eval("RSEL=[...document.querySelectorAll('#reviewBody tr[data-n]')].findIndex(t=>/^Batch 2/.test(REV.find(r=>r.n===+t.dataset.n).rec.t)); renderReview()")
        first = b.eval("+document.querySelectorAll('#reviewBody tr[data-n]')[RSEL].dataset.n")
        b.key("a")
        b.wait(f"REV.find(r=>r.n==={first}).done==='approved'", 15)
        b.wait(f"+document.querySelectorAll('#reviewBody tr[data-n]')[RSEL].dataset.n!=={first}", 5)
        nxt = b.eval("REV.find(r=>r.n===+document.querySelectorAll('#reviewBody tr[data-n]')[RSEL].dataset.n)")
        self.assertFalse(nxt.get("done"))                                              # moved to the next undecided row
        first_t = b.eval(f"REV.find(r=>r.n==={first}).rec.t")
        # Cmd/Ctrl+Z undoes it. With auto-apply on, the decision is applied 600 ms later and only then is there an Undo (the
        # apply's): wait for it as long as an apply can take under load (dev-test-steadiness: it was 10 s)
        b.wait("!!UNDO", 30)
        b.key("z", modifiers=4)
        b.wait(f"REV.some(r=>r.rec.t==={first_t!r}&&!r.done)", 15)
        self.settle()
        # with the setting off, the cursor stays
        b.eval("S.rvAdvance=false")
        b.eval(f"RSEL=[...document.querySelectorAll('#reviewBody tr[data-n]')].findIndex(t=>REV.find(r=>r.n===+t.dataset.n).rec.t==={nxt['rec']['t']!r}); renderReview()")
        ri = b.eval("RSEL")
        b.eval("document.getElementById('snackT').textContent=''")
        b.key("r")                                                                     # BL-315: R opens the menu; 0 rejects
        b.wait("!!document.getElementById('rvReason')")
        b.key("0")
        b.wait(f"!REV.some(r=>r.rec.t==={nxt['rec']['t']!r}&&!r.done)", 15)
        self.assertEqual(b.eval("RSEL"), ri)
        # dev-test-steadiness: the rejection is applied 600 ms later and the page reloads its data then. A reload restores the
        # selection it saw when it began, so one that lands during the keys below can undo Shift+J's or Cmd+A's selection
        # (an apply is slower under load, so it lands later). Wait for that apply and its reload first.
        b.wait("/^Rejected 1 without a reason/.test(document.getElementById('snackT').textContent)", 30)   # BL-315: said once the apply is done
        self.settle()
        # Shift+J extends; Cmd/Ctrl+A selects all shown
        b.eval("RHL.clear(); RVA=null; renderReview()")
        b.key("J", modifiers=8)
        self.assertEqual(b.eval("RHL.size"), 2)
        b.key("a", modifiers=4)
        self.assertEqual(b.eval("RHL.size"), b.eval("rvMatching().length"))
        self.assertEqual(b.eval("document.getElementById('rvresult').getAttribute('role')"), "status")

    def test_the_empty_queue_says_what_happened(self):
        b = self.open_review()
        b.eval("REV.forEach(r=>{ if(!r.done) r.done='rejected'; }); RVSTATS={approved:3,rejected:2,edited:1}; renderReview()")
        text = b.eval("document.getElementById('reviewBody').textContent")
        self.assertIn("Nothing left to review", text)
        self.assertIn("approved 3 · rejected 2 · edited 1", text)
        self.assertTrue(b.eval("!!document.querySelector('#reviewBody [data-go=activity]') && !!document.querySelector('#reviewBody [data-ask=sweep]')"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
