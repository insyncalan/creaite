"""#307 (v2.6.1) Intake row identity and the fix pass's three open defects: one browser check per finding of Team Cap's independent
review of the #307 fix pass (issue #307, 'independent review, #307 fix pass a 9bba78a2, b 815eb3b0, c f4bbf59c'; line head
origin/v261-line2 bcc008f5). Each check names the finding it pins. Written to be RED on bcc008f5 for the right reason (the defect, not a
flake) and GREEN once the defect is fixed; the HIGH ones read what the record holds, so a fix that withdraws the stale row, refuses the
press or approves the right item all pass, and only saving the WRONG item fails.

Run on its own (makes the vault itself):  python3 dev/tests/handchecks/test_v261_intake307_identity.py
Against a given release zip:              CREAITE_HC_BASE=x CREAITE_HC_DIR=<run folder> CREAITE_HC_ZIP=<zip> python3 dev/tests/handchecks/test_v261_intake307_identity.py
(CREAITE_HC_BASE only stops the module making a shared session of its own; the class here makes a vault of its own.)

  Identity307   50 to 56   a row is its proposal file + item, but the engine renumbers items inside a file, so a stale row, or one
                           whose file was written again under the same name, must never save, reject or overwrite ANOTHER item
                57         Approve routine on a meeting with a minutes record applies the Track column (the #275 M-c regression)
                58         Add files: a file name too long for the disk names no vault path and no raw exception
                59         rejected minutes are not counted under Approved this week

  50  finding 1 (HIGH, 307a)   A1  the file renumbered behind the page, page not refreshed: the Bravo row's Approve saves Charlie
  51  finding 1 (HIGH, 307a)   A2  the same after the live-update quick refresh, for a press already on its way (the button the
                                   person was looking at is pressed after the new list landed)
  52  finding 1 (HIGH, 307a)   A3  a file deleted and written again under the same name with new content: the Delta row saves Echo
  53  finding 1 (HIGH, 307a)   A3b the same after the quick refresh, for a press already on its way
  54  finding 1 (HIGH, 307a)   the same file renumbering, Reject on the Bravo row rejects Charlie (irReject is not checked either)
  55  finding 1 (HIGH, 307a)   A7  /api/review matches file + ref only. Pins the contract the review proposes: the call carries
                                   `expect` (text of the item the person saw) and the server refuses when the item at ref no
                                   longer shows it. If the fix names that field differently, rename it here
  56  finding 3 (HIGH, panel.js, older)  A4  the peek's Save and approve acts on the item that now has the peek's list number and
                                   overwrites it with the peek's fields (Charlie's proposal is lost, Bravo is approved twice)
  57  finding 2 (HIGH, 307a)   the REGRESSION: irApproveRoutine looks for the minutes row in groups.routine, but it sits in
                                   groups.needs, so the Track column is never applied (dev/tests/test_minutes_track_review.py: 5 red)
  58  finding 5 (MEDIUM-LOW, 307c)  a 300-character file name shows 'OSError: [Errno 63] File name too long: <absolute vault path>'
  59  finding 4 (MEDIUM, 307b)  rejected minutes from a dropped transcript count under Approved this week and get a Done row

Dated 23-10-2026. Fictional data only (the demo portfolio's people); every check makes its own files with names no other check uses.
"""
import json
import re
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))      # dev/tests
from hcbase import HandcheckCase, NOTES, db_rows  # noqa: E402

_SCRIPTS = Path(__file__).resolve().parents[3] / "system/scripts"
_REVIEW_EXPECT = "_main_with_expect" in (_SCRIPTS / "review.py").read_text() and "--expect=" in (_SCRIPTS / "live_server.py").read_text()   # 2.6.2 (#314)

KIND = {n: "scriptable" for n in range(50, 60)}
LIVE_ONLY = {}

NOTES.clear()

READY = "typeof go==='function' && LIVE"
INTAKE = "VIEW==='intake-review' && !document.getElementById('v-intake-review').hidden && !!document.querySelector('#v-intake-review tr.irmeet')"
MAIL = ("Email · From: Priya Nair <priya.nair@meridian.example> · Subject: Harbour works · Sent: {day} 09:00 · "
        "Link: https://outlook.example.test/owa/?ItemID=hc307identity")

# What the page said, as a person sees it: every toast (text and its action), recorded by a MutationObserver and a timer
WATCH = r"""(()=>{
  if (window.__w) { window.__w.snacks.length = 0; return true; }
  window.__w = {snacks: []};
  let last = "";
  const tick = () => {
    const t = ((document.getElementById('snackT') || {}).innerText || '').trim();
    const w = document.getElementById('snack');
    const on = !!(w && w.classList.contains('on'));
    if (t && on && t !== last) window.__w.snacks.push(t);
    last = on ? t : '';
  };
  new MutationObserver(tick).observe(document.body, {childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ['class']});
  setInterval(tick, 100);
  return true; })()"""

# Files dropped on the page with the browser's own File and DataTransfer (a name of 300 characters cannot exist on the disk)
DROP = r"""(specs=>{
  const dt = new DataTransfer();
  for (const s of specs) dt.items.add(new File([s.text], s.name, {type: ''}));
  const tgt = document.querySelector('#v-intake-review') || document.body;
  for (const type of ['dragenter', 'dragover', 'drop']) tgt.dispatchEvent(new DragEvent(type, {bubbles: true, cancelable: true, dataTransfer: dt}));
  return true; })(%s)"""


def names(tag):
    """Alpha, Bravo and Charlie, each check with names of its own (so no row of another check's file can answer for it)."""
    return (f"Alpha lantern check {tag}", f"Bravo anchor weigh {tag}", f"Charlie gazebo paint {tag}")


def vtt(who="Sara Khan", said="I will circulate the reading list."):
    return f"WEBVTT\n\n00:00:01.000 --> 00:00:05.000\n<v {who}>{said}</v>\n"


class Identity307(HandcheckCase):
    """The page and the vault's helpers for the checks below. One vault for the class: every check stages files of its own."""
    own_vault = True
    width, height = 1400, 1300
    _n = 0

    # ── the vault ──

    def today(self):
        return date.fromisoformat((self.now or str(date.today()))[:10])

    def staging(self, name):
        return self.vault / "system/staging" / name

    def sweep_file(self, descs, tag):
        """A pending mail proposal (what cx-sweep stages), one new action per description, numbered 1..n in a file of its own.
        Names are minutes apart in the order made, so a later file always lists after an earlier one. Returns the file name."""
        Identity307._n += 1
        day = self.today().isoformat()
        name = f"proposed-{day}-{10 + Identity307._n:02d}00-sweep-{tag}.json"
        due = (self.today() + timedelta(days=30)).isoformat()
        items = [{"n": k, "op": "new", "table": "actions", "match": "strong", "flags": [], "decision": "pending",
                  "values": {"project": "FAL", "description": d, "owner": "Sara Khan", "due_date": due, "source": MAIL.format(day=day)}}
                 for k, d in enumerate(descs, 1)]
        self.staging(name).write_text(json.dumps({"created": f"{day}T09:00:00", "source_run": "cx-sweep", "files": [], "items": items},
                                                 indent=2), encoding="utf-8")
        return name

    def take_out(self, name, desc):
        """What sweep._take_item and _unstage_in do (the VIP card's Undo): remove one pending item from the file and renumber the
        rest in place, under the same file name."""
        p = self.staging(name)
        d = json.loads(p.read_text(encoding="utf-8"))
        d["items"] = [i for i in d["items"] if i["values"].get("description") != desc]
        for k, it in enumerate(d["items"], 1):
            it["n"] = k
        p.write_text(json.dumps(d, indent=2), encoding="utf-8")

    def rewrite_same_name(self, name, old, new):
        """A file deleted and written again under the same name with a different item (minutes.py and sweep.py name files to the
        minute, so an apply that moves one to applied/ and a stage in the same minute meet again)."""
        p = self.staging(name)
        d = json.loads(p.read_text(encoding="utf-8"))
        p.unlink()
        for it in d["items"]:
            if it["values"].get("description") == old:
                it["values"]["description"] = new
        p.write_text(json.dumps(d, indent=2), encoding="utf-8")

    def staged(self, name):
        p = self.staging(name)
        return json.loads(p.read_text(encoding="utf-8"))["items"] if p.exists() else []

    def descs(self, table="actions", column="description"):
        return sorted(r[column] for r in db_rows(self.vault, f"select {column} from {table}"))

    def cli_approve(self, needle):
        """Approve and apply the pending row whose text has `needle` from outside the page (what Claude Code or a second tab does)."""
        _, out = self.run_in_vault("review.py", "list", "--json")
        rows = json.loads(out[out.index("["):out.rindex("]") + 1])
        ns = [str(r["n"]) for r in rows if needle in r["text"]]
        self.assertTrue(ns, f"nothing pending named {needle}")
        self.assertEqual(self.run_in_vault("review.py", "approve", ",".join(ns))[0], 0)
        self.assertEqual(self.run_in_vault("tracker.py", "apply")[0], 0)

    # ── the page ──

    def open_intake(self, needle):
        """Load the page afresh, open Intake, unfold the mail section and wait until the row `needle` is drawn."""
        b = self.b
        b.reload(READY)
        b.eval("go('intake-review')")
        b.wait(INTAKE, 30)
        b.eval("(()=>{const f=document.querySelector('[data-irfold=mail]'); if(f && /Show/.test(f.innerText)) f.click(); return 1})()")
        b.wait(self.row_js(needle) + "!==null", 30)
        b.eval(WATCH)

    @staticmethod
    def row_js(needle):
        return ("(()=>{const t=[...document.querySelectorAll('#v-intake-review tr.irprop')].find(t=>t.innerText.includes(%s)); "
                "return t||null})()" % json.dumps(needle))

    def press(self, needle, button="approve"):
        """A real click on `button` of the row `needle`, as drawn now. False when the page has no such row or button any more (a
        fix that withdraws a stale row leaves nothing to press, which is a pass: the check is about what is SAVED)."""
        b = self.b
        found = b.eval("(()=>{const t=%s; const x=t&&t.querySelector('[data-ira=%s]'); if(!x) return false; x.setAttribute('data-hc','go'); return true})()"
                       % (self.row_js(needle), button))
        if found:
            b.click("[data-hc=go]")
            b.eval("document.querySelectorAll('[data-hc]').forEach(x=>x.removeAttribute('data-hc'))")
        return found

    def grab(self, needle, button="approve"):
        """Hold on to the button the person is looking at, to press it after the list has changed (a press already on its way)."""
        self.assertTrue(self.b.eval("(()=>{const t=%s; window.HB=t&&t.querySelector('[data-ira=%s]'); return !!window.HB})()"
                                    % (self.row_js(needle), button)), f"no {button} on {needle}")

    def quick_refresh(self):
        """The live-update refresh of just some items (recordsRefresh): REV is laid down again, renumbered, without the model."""
        ident = db_rows(self.vault, "select id from actions limit 1")[0]["id"]
        self.b.eval("window.QR=false; refreshRecords([%s]).then(()=>{ window.QR=true; })" % json.dumps(ident))
        self.b.wait("window.QR===true", 30)

    def toasts(self):
        return list(self.b.eval("(window.__w||{snacks:[]}).snacks") or [])

    def after_press(self):
        """Wait until the page has said something, then until its background saves have finished."""
        b = self.b
        try:
            b.wait("window.__w.snacks.length>0", 30)
        except TimeoutError:
            self.fail("the press ended silent: no message at all")
        b.eval("window.SS=false; savesSettled().then(()=>{ window.SS=true; })")
        b.wait("window.SS===true", 30)

    def saved(self, base):
        return [d for d in self.descs() if d not in base]

    def pending(self, name, desc):
        return any(i["values"]["description"] == desc and i.get("decision") == "pending" for i in self.staged(name))

    # ───────────────── 50 to 53: Approve on a row whose item moved or changed behind the page ─────────────────

    def renumber_case(self, refresh, tag):
        alpha, bravo, charlie = names(tag)
        name = self.sweep_file((alpha, bravo, charlie), tag)
        self.open_intake(bravo)
        if refresh:
            self.grab(bravo)
        self.take_out(name, alpha)                      # Alpha taken out; Bravo is now item 1 and Charlie item 2
        base = self.descs()
        if refresh:
            self.quick_refresh()
            self.b.eval("window.HB.click()")
            pressed = True
        else:
            pressed = self.press(bravo)
        if pressed:
            self.after_press()
        got = self.saved(base)
        print(f"\n  toasts {self.toasts()} saved {got}")
        self.assertNotIn(charlie, got, "WRONG ITEM: the Bravo row's Approve saved Charlie")
        self.assertIn(got, ([], [bravo]), f"only Bravo or nothing may be saved: {got}")
        self.assertTrue(self.pending(name, charlie), "Charlie's proposal left Intake without being approved")

    def test_c50_bravo_row_after_the_file_was_renumbered_never_saves_charlie(self):
        """50. Pins finding 1 (A1). Intake shows Alpha, Bravo and Charlie from one file; the file is renumbered behind the page (Alpha
        taken out, as the VIP card's Undo does) and the page is NOT refreshed. Approve on the Bravo row must not save Charlie."""
        self.renumber_case(False, "a1")

    def test_c51_bravo_row_after_the_quick_refresh_never_saves_charlie(self):
        """51. Pins finding 1 (A2): the same, the page has taken the live-update quick refresh (REV renumbered) and the press that was
        already on its way (the button held before the refresh) lands after it. It must not save Charlie."""
        self.renumber_case(True, "a2")

    def same_name_case(self, refresh, tag):
        delta, echo = f"Delta harbour survey {tag}", f"Echo pier inspection {tag}"
        name = self.sweep_file([delta], tag)
        self.open_intake(delta)
        if refresh:
            self.grab(delta)
        self.rewrite_same_name(name, delta, echo)
        base = self.descs()
        if refresh:
            self.quick_refresh()
            self.b.eval("window.HB.click()")
            pressed = True
        else:
            pressed = self.press(delta)
        if pressed:
            self.after_press()
        got = self.saved(base)
        print(f"\n  toasts {self.toasts()} saved {got}")
        self.assertNotIn(echo, got, "WRONG ITEM: the Delta row's Approve saved Echo (same file name, new content)")
        self.assertIn(got, ([], [delta]))
        self.assertTrue(self.pending(name, echo), "Echo's proposal left Intake without being approved")

    def test_c52_delta_row_after_the_file_was_written_again_never_saves_echo(self):
        """52. Pins finding 1 (A3). The proposal file is deleted and written again under the same name with a different item; the
        page is not refreshed. Approve on the Delta row must not save Echo."""
        self.same_name_case(False, "a3")

    def test_c53_delta_row_after_the_quick_refresh_never_saves_echo(self):
        """53. Pins finding 1 (A3b): the same, after the quick refresh, for a press already on its way."""
        self.same_name_case(True, "a3b")

    def test_c54_reject_on_the_bravo_row_after_a_renumber_never_rejects_charlie(self):
        """54. Pins finding 1 (irReject): the file is renumbered behind the page; Reject on the Bravo row, and the reason it asks for,
        must not reject Charlie."""
        alpha, bravo, charlie = names("rj")
        name = self.sweep_file((alpha, bravo, charlie), "rj")
        self.open_intake(bravo)
        self.take_out(name, alpha)
        b = self.b
        if self.press(bravo, "reject"):
            try:
                b.wait("!!document.querySelector('#rvReason [data-reason]') || window.__w.snacks.length>0", 15)
            except TimeoutError:
                self.fail("Reject on a row opened no menu and said nothing")
            if b.eval("!!document.querySelector('#rvReason [data-reason]')"):
                b.eval("document.querySelector('#rvReason [data-reason]').setAttribute('data-hc','pick')")
                b.click("[data-hc=pick]")
            self.after_press()
        rejected = [i["values"]["description"] for i in self.staged(name) if i.get("decision") == "rejected"]
        print(f"\n  toasts {self.toasts()} rejected {rejected}")
        self.assertNotIn(charlie, rejected, "WRONG ITEM: the Bravo row's Reject rejected Charlie")
        self.assertTrue(self.pending(name, charlie), "Charlie's proposal was decided by a press on Bravo")

    @unittest.expectedFailure if not _REVIEW_EXPECT else (lambda f: f)   # an expected failure until the guarded review.py --expect <fp> + /api/review pass-through (#314, 2.6.2) is in this tree
    def test_c55_the_review_route_refuses_when_the_item_at_ref_is_not_the_one_the_page_showed(self):
        """55. Pins finding 1 (A7). The page calls /api/review with file + ref, and the server matched on those alone. With `expect`
        (the text the person saw) the item at ref 2 is now Charlie, so the call must be refused and Charlie left pending.
        Expected to fail until 2.6.2 (#314): a raw route call, a second tab or a fast renumber in the window before guardFresh can
        still act on a different item of the user's own pending list."""
        alpha, bravo, charlie = names("rt")
        name = self.sweep_file((alpha, bravo, charlie), "rt")
        self.open_intake(bravo)
        self.take_out(name, alpha)                      # Bravo is item 1, Charlie item 2
        b = self.b
        sys.path.insert(0, str(_SCRIPTS))
        import build_dashboard
        fp = next(build_dashboard.item_fp(i) for i in json.loads(self.staging(name).read_text())["items"] if i["values"]["description"] == bravo)
        b.eval("window.RR=null; api('/api/review',{file:%s,ref:2,decision:'rejected',modes:[],expect:%s}).then(x=>{window.RR=x})"
               % (json.dumps(name), json.dumps(fp)))
        b.wait("!!window.RR", 30)
        said = b.eval("window.RR")
        print(f"\n  route said {said}")
        self.assertFalse(said.get("ok"), f"the route said ok for an item that is not the one the caller meant: {said}")
        self.assertTrue(self.pending(name, charlie), "WRONG ITEM: the route rejected Charlie for a caller who meant Bravo")

    def test_c56_the_peek_save_and_approve_never_overwrites_another_item(self):
        """56. Pins finding 3 (A4, panel.js, older than #307). The peek is open on Bravo; an item in an EARLIER file is approved and
        applied elsewhere, so every later list number moves down; the live update arrives; Save and approve is pressed. It must not
        write Bravo's fields into Charlie's item (two Bravo items, Charlie lost, Bravo approvable twice)."""
        alpha, bravo, charlie = names("pk")
        zulu = "Zulu earlier item pk"
        self.sweep_file([zulu], "pk0")
        mine = self.sweep_file((alpha, bravo, charlie), "pk1")
        self.open_intake(bravo)
        b = self.b
        self.assertTrue(b.eval("(()=>{const t=%s; const c=t&&t.querySelector('td.title'); if(!c) return false; c.setAttribute('data-hc','peek'); return true})()"
                               % self.row_js(bravo)))
        b.click("[data-hc=peek]")
        b.eval("document.querySelectorAll('[data-hc]').forEach(x=>x.removeAttribute('data-hc'))")
        b.wait("typeof pkRev==='function' && !!pkRev()", 15)
        self.assertEqual(b.eval("pkRev().rec.t"), bravo)
        self.cli_approve(zulu)                          # approved and applied elsewhere: every later REV number moves down
        self.quick_refresh()
        print(f"\n  the peek now names: {b.eval('(pkRev()||{rec:{}}).rec.t')}")
        base = self.descs()
        b.click("#pkPSaveA")
        self.after_press()
        got = self.saved(base)
        descs = [i["values"]["description"] for i in self.staged(mine)]
        print(f"  saved {got}; the file now holds {descs}")
        self.assertIn(charlie, descs + got, "Charlie's proposal was overwritten by the peek's save")
        self.assertLessEqual(descs.count(bravo), 1, "Bravo is now in the file twice: the real one is still pending and can be approved again")
        self.assertLessEqual(got.count(bravo), 1)
        self.assertNotIn(charlie, got, "WRONG ITEM approved from the peek")

    # ───────────────── 57: the Track column under Approve routine ─────────────────

    def stage_minutes(self, name):
        """Stage fictional minutes `name` with the vault's own minutes.py (as cx-minutes does): a transcript in the inbox, minutes
        kept as a record with two actions (one for Lena Fischer, one for Sara Khan), a decision and a risk. Returns the proposal file."""
        Identity307._n += 1
        day = (self.today() - timedelta(days=1 + Identity307._n % 5)).isoformat()
        tr = f"inbox/{day} {name}.vtt"
        (self.vault / "inbox").mkdir(exist_ok=True)
        (self.vault / tr).write_text(vtt(), encoding="utf-8")
        p = {"project": "FAL"}
        spec = {"title": f"[FAL] {name}", "date": day, "event_id": None, "projects": ["FAL"], "transcript": tr,
                "coverage": [{"point": "Overview", "verdict": "Covered"}],
                "minutes": {"start": "10:00", "end": "11:00", "chat": False, "attendees": "Alan Carter, Lena Fischer, Sara Khan",
                            "summary": [{"text": "The group reviewed the plan.", "turn": 1}],
                            "updates": [{"heading": "Plan", "items": [{"text": "Lena is revising the plan.", "at": "00:00:01"}]}],
                            "open_questions": []},
                "items": [{"table": "actions", "turn": 1, "values": {**p, "description": f"Polish the {name} lanterns", "owner": "Lena Fischer",
                                                                       "due_date": (self.today() + timedelta(days=14)).isoformat()}},
                          {"table": "actions", "turn": 1, "values": {**p, "description": f"Weigh the {name} anchors", "owner": "Sara Khan",
                                                                       "due_date": (self.today() + timedelta(days=21)).isoformat()}},
                          {"table": "decisions", "at": "00:00:01", "values": {**p, "decision": f"Retire the {name} gazebo", "made_by": "Rashid Al Suwaidi"}},
                          {"table": "raid", "turn": 1, "values": {**p, "type": "Risk", "description": f"The {name} harbour may flood", "owner": "Lena Fischer"}}]}
        drafts = self.vault / "system/staging/drafts"
        drafts.mkdir(parents=True, exist_ok=True)
        spec_file = drafts / f"hc307i-{re.sub('[^A-Za-z0-9]+', '-', name)}.json"
        spec_file.write_text(json.dumps(spec), encoding="utf-8")
        before = {q.name for q in (self.vault / "system/staging").glob("proposed-*.json")}
        code, out = self.run_in_vault("minutes.py", "stage", str(spec_file.relative_to(self.vault)))
        self.assertEqual(code, 0, f"minutes.py stage failed: {out[-300:]}")
        new = [q.name for q in (self.vault / "system/staging").glob("proposed-*.json") if q.name not in before]
        self.assertTrue(new, "no proposal was staged")
        return new[0]

    def test_c57_approve_routine_under_a_minutes_record_applies_the_track_column(self):
        """57. Pins finding 2 (the #275 M-c regression, 5 red in test_minutes_track_review). In the minutes view the second action is
        crossed out in the Track column; on Intake, Approve routine under that meeting must register the ticked action, reject the
        crossed one ('Removed in the minutes') and leave the minutes themselves waiting for their own Approve."""
        prop = self.stage_minutes("Kilo huddle")
        ticked, crossed = "Polish the Kilo huddle lanterns", "Weigh the Kilo huddle anchors"
        b = self.b
        b.reload(READY)
        b.eval(f"go('minutes',{{file:{json.dumps(prop)}}})")
        b.wait("!!document.querySelector('#v-minutes tr.mi')", 30)
        self.assertEqual(b.eval("document.querySelector(\"#v-minutes tr.mi[data-n='2'] .mntrk button.n\") ? true : false"), True,
                         "the minutes view has no Track control on the second action")
        b.click("#v-minutes tr.mi[data-n='2'] .mntrk button.n")
        b.wait("document.querySelector(\"#v-minutes tr.mi[data-n='2']\").dataset.trk==='n'", 15)
        record = self.staged_record_path(prop)
        self.wait_until(lambda: re.search(r'"track"\s*:\s*\{\s*"2"\s*:\s*"n"', record.read_text(encoding="utf-8", errors="replace")),
                        "the Track choice saved with the minutes")
        b.eval("irOpen.value=null; go('intake-review', (REV.find(r=>r.kind==='draft'&&r.ref==='meeting'&&r.file===%s)||{}).n)" % json.dumps(prop))
        b.wait("!!document.querySelector('#v-intake-review tr.icsubhead.routine.child [data-ira=routine]')", 30)
        b.eval(WATCH)
        actions = self.descs()
        b.click("#v-intake-review tr.icsubhead.routine.child [data-ira=routine]")
        self.after_press()
        reg = [d for d in self.descs() if d not in actions]
        items = {i["n"]: i for i in self.staged(prop)}
        print(f"\n  toasts {self.toasts()} registered {reg}; item 2: {items[2].get('decision')} {items[2].get('reject_reason')}")
        self.assertIn(ticked, reg, "the ticked action was not registered")
        self.assertNotIn(crossed, reg, "the crossed action was registered")
        self.assertEqual(items[2].get("decision"), "rejected", "the crossed item is still pending: Approve routine did not apply the Track column")
        self.assertEqual(items[2].get("reject_reason"), "Removed in the minutes")
        self.assertNotIn("Nothing routine to approve", " ".join(self.toasts()))
        self.assertNotIn("Retire the Kilo huddle gazebo", self.descs("decisions", "decision"), "the bulk rule: a decision is never registered by Approve routine")
        self.assertNotIn("The Kilo huddle harbour may flood", self.descs("raid"), "the bulk rule: a risk is never registered by Approve routine")

    def wait_until(self, fn, what, timeout=30):
        """Poll a condition on the vault's files (the page keeps answering meanwhile); fail with `what` when it never holds."""
        import time
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if fn():
                return
            self.b.pump(0.2)
        self.fail(f"never happened: {what}")

    def staged_record_path(self, prop):
        """The minutes record (a creaite .html in the project's folder) the staged proposal points at."""
        meeting = json.loads(self.staging(prop).read_text(encoding="utf-8")).get("meeting") or {}
        rel = meeting.get("draft") or ""
        self.assertTrue(rel, "the staged minutes name no draft file")
        path = self.vault / rel
        if not path.exists():
            from_paths = list(self.vault.rglob(Path(rel).name))
            self.assertTrue(from_paths, f"minutes record {rel} not found")
            path = from_paths[0]
        return path

    # ───────────────── 58: Add files, a name too long ─────────────────

    def test_c58_a_file_name_too_long_for_the_disk_names_no_vault_path(self):
        """58. Pins finding 5 (307c). A file with a 300-character name is dropped on Intake. Whatever the page says (the note under the
        toolbar and the toast) must not carry the server's raw exception or the vault's absolute path; it names the file and says it
        could not be saved."""
        name = ("L" * 300) + ".vtt"
        self.open_intake_page()
        b = self.b
        b.eval(DROP % json.dumps([{"name": name, "text": vtt()}]))
        try:
            b.wait("!!((document.querySelector('[data-iraddfail]')||{innerText:''}).innerText||'').trim() || window.__w.snacks.length>0", 60)
        except TimeoutError:
            self.fail("dropping the file ended silent")
        note = b.eval("(document.querySelector('[data-iraddfail]')||{innerText:''}).innerText")
        said = " | ".join([note] + self.toasts())
        print(f"\n  said: {said[:400]}")
        for where in {str(self.vault), str(self.vault.resolve())}:
            self.assertNotIn(where, said, "the vault's absolute path is on screen")
        self.assertNotRegex(said, r"/(?:Users|private|var|tmp|home)/", "an absolute path is on screen")
        self.assertNotRegex(said, r"OSError|Errno|Traceback", "the server's raw exception is on screen")
        self.assertIn("LLLL", said, "the note does not name the file")

    def open_intake_page(self):
        b = self.b
        b.reload(READY)
        b.eval("go('intake-review')")
        b.wait(INTAKE, 30)
        b.eval(WATCH)

    # ───────────────── 59: rejected minutes are not "Approved this week" ─────────────────

    def approved_this_week(self):
        txt = self.b.eval("(document.querySelector('#v-intake-review .icpipe')||{}).innerText||''").replace("\n", " ")
        m = re.search(r"(\d+)\s*Approved", txt)
        return int(m.group(1)) if m else None

    def test_c59_rejected_minutes_are_not_counted_as_approved_this_week(self):
        """59. Pins finding 4 (307b). Minutes made from a dropped transcript are REJECTED (not wanted) and the rejection is applied.
        tracker.py writes a processed.txt line for them too, '… | not filed | 0'; Intake must not count that line under Approved
        this week or give it a Done row."""
        prop = self.stage_minutes("Lima huddle")
        self.open_intake_page()
        b = self.b
        b.wait("document.getElementById('v-intake-review').innerText.includes('Lima huddle')", 30)
        before = self.approved_this_week()
        _, out = self.run_in_vault("review.py", "list", "--json")
        rows = json.loads(out[out.index("["):out.rindex("]") + 1])
        ns = [str(r["n"]) for r in rows if r["file"] == prop]          # the minutes and the items made from them: all not wanted
        self.assertIn("meeting", [r.get("ref") for r in rows if r["file"] == prop], "the staged minutes are not in the review list")
        self.assertEqual(self.run_in_vault("review.py", "reject", ",".join(ns))[0], 0)
        self.assertEqual(self.run_in_vault("tracker.py", "apply")[0], 0)
        lines = (self.vault / "system/processed.txt").read_text(encoding="utf-8").splitlines()
        print(f"\n  processed.txt, last lines: {lines[-2:]}")
        self.assertTrue(any("lima huddle" in x and x.rstrip().endswith("| 0") for x in lines),
                        "the rejection left no processed.txt line (no items filed) to test against")
        self.open_intake_page()
        after = self.approved_this_week()
        row = b.eval("(()=>{const r=[...document.querySelectorAll('#v-intake-review tr.irmeet')].find(r=>r.innerText.includes('Lima huddle')); "
                     "return r? r.innerText.replace(/\\n+/g,' | ') : null})()")
        print(f"  Approved this week {before} -> {after}; a row for the meeting: {row}")
        self.assertEqual(after, before, f"rejected minutes were counted under Approved this week: {before} -> {after}")
        self.assertTrue(row is None or "Done" not in row, f"rejected minutes have a Done row: {row}")


if __name__ == "__main__":
    unittest.main()
