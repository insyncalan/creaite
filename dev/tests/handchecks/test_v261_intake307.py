"""#307 (v2.6.1) Intake reliability: one browser check per Intake path where a button can end silent, leave the row or the counts
alone, or answer in words a person shouldn't read. Written from Team Cap's audit of the PUBLISHED 2.6.0 flow (issue #307): each check
names the path, drives it with real mouse and keyboard events in headless Chrome against the live server of a vault made from the
release zip (the demo portfolio, the stand-in Claude, never Microsoft 365), and reads what a person sees (rows, the stage counts, the
sidebar number, the toast) and what the record holds.

Run on its own (makes the vault itself):  python3 dev/tests/handchecks/test_v261_intake307.py
Against a given release zip:              CREAITE_HC_BASE=x CREAITE_HC_DIR=<run folder> CREAITE_HC_ZIP=<zip> python3 dev/tests/handchecks/test_v261_intake307.py
(CREAITE_HC_BASE only stops the module making a shared session of its own; each class here makes a vault of its own.)

  AddFiles307   1 to  6   the Add files arrow and dropping files
  Approve307   10 to 16   Approve on the Minutes view, on the Intake minutes row, on an item row, Approve routine
  Held307      20 to 24   held minutes (transcript gone): Approve without the transcript, Discard, the editor, key A
  Stale307     30 to 32   a row or view that changed elsewhere (Claude Code, a second tab, a scheduled run)
  SetAside307  40 to 44   Later, Not needed, Restore, Process that stages nothing, Process that fails

Red on 2.6.0 where the audit found a defect (the note says which); green where 2.6.1 fixes it. The checks that pass on 2.6.0 protect
the path from now on. Fictional data only (the demo portfolio's people); every check makes its own meetings so none leans on another.
"""
import json
import re
import shutil
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))      # dev/tests
from hcbase import HandcheckCase, NOTES, db_rows  # noqa: E402

KIND = {n: "scriptable" for n in (*range(1, 7), *range(10, 17), *range(20, 25), *range(30, 33), *range(40, 45))}
LIVE_ONLY = {}

NOTES.clear()

READY = "typeof go==='function' && LIVE"
INTAKE = "VIEW==='intake-review' && !document.getElementById('v-intake-review').hidden && !!document.querySelector('#v-intake-review tr.irmeet')"
# Words a person shouldn't meet in a result (Plain words, 2.6.1): the old names, file paths, command flags, an item's number.
CODE_WORDS = re.compile(r"\bstaged\b|\bproposals?\b|\bReview\b|inbox/|system/|\.json\b|\.vtt\b|--[a-z]|\bitem \d+\b|^\d+:\s|\bapply\b", re.M)

WATCH = r"""(()=>{
  if (window.__w) { window.__w.snacks.length = 0; return true; }
  window.__w = {snacks: []};
  let last = "";
  const tick = () => {
    const t = ((document.getElementById('snackT') || {}).innerText || '').trim();
    const w = document.getElementById('snack');
    const on = !!(w && w.classList.contains('on'));
    const u = document.getElementById('snackU');
    const act = (u && u.offsetParent !== null && getComputedStyle(u).visibility !== 'hidden') ? (u.innerText || '').trim() : '';
    const key = t + '|' + act;
    if (t && on && key !== last) window.__w.snacks.push({text: t, act: act});
    last = on ? key : '';
  };
  new MutationObserver(tick).observe(document.body, {childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ['class']});
  setInterval(tick, 100);
  return true; })()"""


def vtt(who="Sara Khan", said="I will circulate the reading list."):
    return f"WEBVTT\n\n00:00:01.000 --> 00:00:05.000\n<v {who}>{said}</v>\n"


class Intake307(HandcheckCase):
    """The page and the vault's helpers shared by the checks below. Each class makes a vault of its own (its checks change data)."""
    own_vault = True
    width, height = 1400, 1300
    _n = 0

    # ── the vault ──

    def today(self):
        return date.fromisoformat((self.now or str(date.today()))[:10])

    def stage(self, name, held=False, event_id=None, project="FAL", day=None):
        """Stage a fictional meeting `name` as minutes with the vault's own minutes.py (as cx-minutes does): a transcript in the
        inbox, minutes with two actions, a decision and a risk. held=True takes the transcript away afterwards (the held state).
        Returns (proposal file name, transcript path)."""
        Intake307._n += 1
        day = day or (self.today() - timedelta(days=1 + Intake307._n % 5)).isoformat()
        tr = f"inbox/{day} {name}.vtt"
        (self.vault / "inbox").mkdir(exist_ok=True)
        (self.vault / tr).write_text(vtt(), encoding="utf-8")
        p = {"project": project}
        spec = {"title": f"[{project}] {name}", "date": day, "event_id": event_id, "projects": [project], "transcript": tr,
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
        spec_file = drafts / f"hc307-{re.sub('[^A-Za-z0-9]+', '-', name)}.json"
        spec_file.write_text(json.dumps(spec), encoding="utf-8")
        before = set(self.proposals())
        code, out = self.run_in_vault("minutes.py", "stage", str(spec_file.relative_to(self.vault)))
        self.assertEqual(code, 0, f"minutes.py stage failed: {out[-300:]}")
        new = [q for q in self.proposals() if q not in before]
        self.assertTrue(new, "no proposal was staged")
        if held:
            (self.vault / tr).unlink()
        return new[0], tr

    def proposals(self):
        return sorted(p.name for p in (self.vault / "system/staging").glob("proposed-*.json"))

    def count(self, table):
        return db_rows(self.vault, f"select count(*) c from {table}")[0]["c"]

    def cli_approve(self, needle, kinds=None):
        """Approve and apply a minutes proposal or its items from outside the page (what a second tab or Claude Code does)."""
        code, out = self.run_in_vault("review.py", "list", "--json")
        rows = json.loads(out[out.index("["):out.rindex("]") + 1])
        ns = [str(r["n"]) for r in rows if needle in r["text"] and (not kinds or r["kind"] in kinds)]
        self.assertTrue(ns, f"nothing pending named {needle}")
        self.assertEqual(self.run_in_vault("review.py", "approve", ",".join(ns))[0], 0)
        self.assertEqual(self.run_in_vault("tracker.py", "apply")[0], 0)

    # ── the page ──

    def open_intake(self, meeting=None):
        """Load the page afresh (so it holds the vault's data now), open Intake and, with `meeting`, that meeting's row."""
        b = self.b
        b.reload(READY)
        b.eval("go('intake-review')")
        b.wait(INTAKE, 30)
        b.pump(0.6)
        if meeting:
            self.open_row(meeting)
        b.eval(WATCH)

    def open_row(self, needle):
        b = self.b
        state = b.eval("(()=>{const r=[...document.querySelectorAll('#v-intake-review tr.irmeet')].find(r=>r.innerText.includes(%s)); "
                       "if(!r) return null; r.setAttribute('data-hc','row'); return r.getAttribute('aria-expanded')||'false'})()" % json.dumps(needle))
        self.assertIsNotNone(state, f"no row on the Intake page with {needle}")
        if state != "true":
            b.click("tr.irmeet[data-hc=row] td.title")
            b.pump(0.6)
        b.eval("document.querySelectorAll('[data-hc]').forEach(x=>x.removeAttribute('data-hc'))")

    def props(self):
        return self.b.eval("[...document.querySelectorAll('#v-intake-review tr.irprop')].map(r=>({n:+r.dataset.irn,kind:r.dataset.kind,"
                           "text:r.innerText.replace(/\\n+/g,' | '),btns:[...r.querySelectorAll('button')].map(x=>x.dataset.ira||x.getAttribute('aria-label')||x.innerText.trim())}))")

    def prop(self, kind, needle):
        rows = [r for r in self.props() if r["kind"] == kind and needle in r["text"]]
        self.assertTrue(rows, f"no {kind} row with {needle}: {[r['text'][:40] for r in self.props()]}")
        return rows[0]

    def row_text(self, needle):
        return self.b.eval("(()=>{const r=[...document.querySelectorAll('#v-intake-review tr.irmeet')].find(r=>r.innerText.includes(%s)); "
                           "return r? r.innerText.replace(/\\n+/g,' | ') : null})()" % json.dumps(needle))

    def counts(self):
        """The stage numbers on the page and the sidebar's, as a person reads them."""
        txt = self.b.eval("(document.querySelector('#v-intake-review .icpipe')||{}).innerText||''").replace("\n", " ")
        out = {}
        for key, word in (("arrived", "Arrived"), ("drafted", "Drafted"), ("approved", "Approved"), ("all", "Show all")):
            m = re.search(r"(\d+)\s*" + word, txt)
            out[key] = int(m.group(1)) if m else None
        m = re.search(r"(\d+)\s*(?:proposals?|suggestions?) to check", txt)
        out["to_check"] = int(m.group(1)) if m else None
        label = self.b.eval("(document.querySelector('button.nv[data-v=review]')||{getAttribute:()=>''}).getAttribute('aria-label')") or ""
        m = re.search(r"(\d+) waiting", label)
        out["sidebar"] = int(m.group(1)) if m else 0
        return out

    def toasts(self):
        return [(x["text"], x["act"]) for x in (self.b.eval("(window.__w||{snacks:[]}).snacks") or [])]

    def toast_texts(self):
        return [t for t, _ in self.toasts()]

    def settle(self, seconds=2.5):
        self.b.pump(seconds)

    def click_row_button(self, n, ira):
        self.b.click(f"#v-intake-review tr.irprop[data-irn='{n}'] [data-ira={ira}]")

    def go_minutes(self, proposal):
        b = self.b
        b.eval(f"go('minutes',{{file:{json.dumps(proposal)}}})")
        b.wait("!!document.getElementById('mnApproveBtn') && !document.getElementById('mnApproveBtn').disabled", 30)
        b.pump(0.8)
        b.eval(WATCH)

    def approve_in_view(self, anyway=True):
        """Press Approve minutes; if the box about a ticked item's problem appears, answer it with Approve anyway."""
        b = self.b
        b.click("#mnApproveBtn")
        b.pump(1.2)
        for _ in range(2):                  # the box about a problem, then (#324) the File the minutes box
            if anyway and b.eval("!!document.querySelector('dialog[open]')"):
                b.eval("[...document.querySelectorAll('dialog[open] button')].find(x=>/^(Approve|File and approve)/.test(x.innerText.trim())).setAttribute('data-hc','go')")
                b.click("dialog[open] button[data-hc=go]")
                b.eval("document.querySelectorAll('[data-hc]').forEach(x=>x.removeAttribute('data-hc'))")
                b.pump(1.0)
        b.pump(2.5)

    def assertPlain(self, text, what="the message"):
        bad = CODE_WORDS.findall(text)
        self.assertEqual(bad, [], f"{what} has words a person shouldn't read ({bad}): {text[:160]}")


# ───────────────────────────── Add files ─────────────────────────────

class AddFiles307(Intake307):
    """Checks 1 to 6: the upload arrow beside Process all ready, and dropping files on the page."""

    def make_files(self):
        d = Path(tempfile.mkdtemp(prefix="hc307-files-"))
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        (d / "2026-10-21 FAL weekly sync.vtt").write_text(vtt(), encoding="utf-8")
        (d / "ORX design notes.txt").write_text("Notes of the design meeting. Decision: use the new login.\n", encoding="utf-8")
        (d / "notes.xlsx").write_text("x", encoding="utf-8")
        (d / "empty.vtt").write_text("", encoding="utf-8")
        return d

    def pick(self, files):
        """A real click on the arrow; the chooser is intercepted (headless has no dialog) and answered with `files`."""
        b = self.b
        b.call("Page.setInterceptFileChooserDialog", enabled=True)
        n0 = len(b.events)
        b.click("[data-irpick]")
        b.pump(0.8)
        opened = [e for e in b.events[n0:] if e.get("method") == "Page.fileChooserOpened"]
        self.assertTrue(opened, "the click on Add files opened no file chooser, and said nothing")
        b.call("DOM.setFileInputFiles", files=[str(f) for f in files], backendNodeId=opened[-1]["params"]["backendNodeId"])
        b.pump(2.5)

    def test_c01_the_arrow_opens_the_file_chooser_and_is_named(self):
        """1. A real click on the upload arrow opens the file chooser (several files allowed); its label and tooltip say Add files."""
        self.open_intake()
        b = self.b
        label = b.eval("document.querySelector('[data-irpick]').getAttribute('aria-label')")
        tip = b.eval("document.querySelector('[data-irpick]').dataset.tip")
        self.assertTrue(label.startswith("Add files"), f"the arrow's label: {label}")
        self.assertTrue((tip or "").startswith("Add files"), f"the arrow's tooltip: {tip}")
        b.call("Page.setInterceptFileChooserDialog", enabled=True)
        n0 = len(b.events)
        b.click("[data-irpick]")
        b.pump(0.8)
        opened = [e for e in b.events[n0:] if e.get("method") == "Page.fileChooserOpened"]
        self.assertTrue(opened, "no file chooser opened")
        self.assertEqual(opened[-1]["params"]["mode"], "selectMultiple")
        self.assertEqual(b.errors, [])

    def test_c02_chosen_files_become_rows_with_a_plain_message(self):
        """2. Files chosen with the arrow appear as rows (size, likely project, kind) and the message says how many were added."""
        self.open_intake()
        d = self.make_files()
        self.pick([d / "2026-10-21 FAL weekly sync.vtt", d / "ORX design notes.txt"])
        b = self.b
        b.wait("document.getElementById('v-intake-review').innerText.includes('FAL weekly sync')", 20)
        said = " ".join(self.toast_texts())
        self.assertIn("2 files added", said)
        self.assertPlain(said)
        row = self.row_text("FAL weekly sync")
        self.assertIn("KB", row, "the row shows no size")
        self.assertIn("Falcon Data Platform", row, "the row shows no likely project")
        self.assertRegex(row, r"[Tt]ranscript", "the row shows no kind")

    def test_c03_a_file_that_cannot_be_added_is_named_in_the_last_message(self):
        """3. One good file and one the page refuses (.xlsx): the message left on screen says which file was not added and why."""
        self.open_intake()
        d = self.make_files()
        self.pick([d / "notes.xlsx", d / "2026-10-21 FAL weekly sync.vtt"])
        self.b.pump(1.0)
        last = self.toast_texts()[-1] + " || NOTE: " + self.b.eval("(document.querySelector('[data-iraddfail]')||{innerText:''}).innerText")
        print("\nC03:", last)
        self.assertTrue("notes.xlsx" in last or re.search(r"only \.vtt|supported|type", last),
                        f"the message left on screen hides which file failed and why: {last!r} (all: {self.toast_texts()})")

    def test_c04_an_empty_file_says_why_at_the_end(self):
        """4. An empty file in a batch: the final message says it was empty (the reason isn't overwritten by '1 file added')."""
        self.open_intake()
        d = self.make_files()
        self.pick([d / "empty.vtt", d / "ORX design notes.txt"])
        self.b.pump(1.0)
        last = (self.toast_texts()[-1] + " || NOTE: " + self.b.eval("(document.querySelector('[data-iraddfail]')||{innerText:''}).innerText")).lower()
        print("\nC04:", last)
        self.assertIn("empty", last, f"the empty file's reason is gone by the end: {self.toast_texts()}")

    def test_c05_dropping_a_file_on_the_page_adds_it(self):
        """5. Dropping a file anywhere on Intake shows the drop overlay, adds the file and says so; an unsupported one says why."""
        self.open_intake()
        d = self.make_files()
        b = self.b
        data = {"items": [], "files": [str(d / "2026-10-21 FAL weekly sync.vtt")], "dragOperationsMask": 1}
        b.call("Input.dispatchDragEvent", type="dragEnter", x=500, y=400, data=data)
        b.call("Input.dispatchDragEvent", type="dragOver", x=500, y=400, data=data)
        b.pump(0.3)
        self.assertTrue(b.eval("!!document.querySelector('.icdrop.on')"), "no drop overlay while dragging")
        b.call("Input.dispatchDragEvent", type="drop", x=500, y=400, data=data)
        b.pump(2.5)
        self.assertIn("1 file added", " ".join(self.toast_texts()))
        self.assertTrue((self.vault / "inbox" / "2026-10-21 FAL weekly sync.vtt").is_file())
        bad = {"items": [], "files": [str(d / "notes.xlsx")], "dragOperationsMask": 1}
        for kind in ("dragEnter", "dragOver", "drop"):
            b.call("Input.dispatchDragEvent", type=kind, x=500, y=400, data=bad)
        b.pump(1.5)
        nt = self.b.eval("(document.querySelector('[data-iraddfail]')||{innerText:''}).innerText"); print("\nC05:", self.toast_texts(), "NOTE:", nt)
        self.assertIn("notes.xlsx", self.toast_texts()[-1] + nt)

    def test_c06_a_failed_upload_says_so(self):
        """6. When the server can't take the file (the request fails), the page says the files couldn't be added; it never ends silent."""
        self.open_intake()
        d = self.make_files()
        b = self.b
        b.eval("window.__api = api; api = async (u, body) => { if (String(u).includes('/api/inbox/upload')) throw new Error('offline'); return window.__api(u, body); }; true")
        self.pick([d / "ORX design notes.txt"])
        b.pump(1.0)
        said = " ".join(self.toast_texts()) + " " + self.b.eval("(document.querySelector('[data-iraddfail]')||{innerText:''}).innerText")
        print("\nC06:", said, "| api stub took:", self.b.eval("typeof window.__api"))
        self.assertTrue(said.strip(), "an upload that failed said nothing at all")
        self.assertNotIn("1 file added", said)


# ───────────────────────────── Approve ─────────────────────────────

class Approve307(Intake307):
    """Checks 10 to 16: Approve in the Minutes view, on the Intake minutes row, on an item row, and Approve routine."""

    def test_c10_minutes_view_approve_files_the_minutes_and_moves_the_counts(self):
        """10. Approve minutes in the Minutes view: the work items are registered, the row leaves Drafted, the toast says what happened with Undo."""
        prop, _ = self.stage("Alpha huddle")
        self.open_intake()
        before, actions = self.counts(), self.count("actions")
        self.go_minutes(prop)
        self.approve_in_view()
        said = " ".join(self.toast_texts())
        self.assertIn("Minutes approved", said)
        self.assertTrue(any(a == "Undo" for _, a in self.toasts()), "no Undo on the result")
        self.assertEqual(self.count("actions"), actions + 2)
        self.open_intake()
        after = self.counts()
        self.assertEqual(after["drafted"], before["drafted"] - 1, f"Drafted didn't move: {before} -> {after}")
        rt = self.row_text("Alpha huddle"); print("\nC10 row:", rt)
        self.assertTrue(rt is None or "Done" in rt, "the row stayed on Intake, not as Done")

    def test_c11_approving_a_dropped_file_s_minutes_leaves_a_trace_in_the_counts(self):
        """11. Minutes made from a dropped transcript, once approved, count in Approved this week (or keep a Done row): they don't vanish."""
        prop, _ = self.stage("Bravo huddle")
        self.open_intake()
        before = self.counts()
        self.go_minutes(prop)
        self.approve_in_view()
        self.open_intake()
        after = self.counts()
        done_row = self.row_text("Bravo huddle")
        self.assertTrue(after["approved"] == before["approved"] + 1 or done_row,
                        f"approved minutes left no trace: Approved this week {before['approved']} -> {after['approved']}, no Done row")

    def test_c12_a_calendar_meeting_moves_to_approved_when_its_minutes_are_approved(self):
        """12. A calendar meeting's minutes, once approved, show the meeting as Done and Approved this week goes up by one."""
        cal = json.loads((self.vault / "system/staging/calendar.json").read_text(encoding="utf-8"))
        day, ev = next((d, m) for d, ms in cal["days"].items() for m in ms if m["title"] == "ORX design review")
        prop, tr = self.stage("ORX design review", event_id=ev["id"], project="ORX", day=day)
        f = self.vault / tr
        f.write_text(f"WEBVTT\n\nNOTE\nEvent ID: {ev['id']}\n\n" + f.read_text(encoding="utf-8").split("WEBVTT\n\n", 1)[1], encoding="utf-8")
        self.open_intake()
        before = self.counts()
        self.go_minutes(prop)
        self.approve_in_view()
        self.open_intake()
        after = self.counts()
        self.assertEqual(after["approved"], before["approved"] + 1, f"{before} -> {after}")

    def test_c13_an_item_row_says_what_was_saved_in_plain_words(self):
        """13. Approve on an item row of minutes: the action is registered, the row leaves, the sidebar number drops by one, and the toast
        says what was saved (an action is not 'a decision') without code words."""
        self.stage("Charlie huddle")
        self.open_intake("Charlie huddle")
        row = self.prop("actions", "Charlie huddle lanterns")
        before, actions = self.counts(), self.count("actions")
        self.click_row_button(row["n"], "approve")
        self.settle()
        self.assertEqual(self.count("actions"), actions + 1)
        after = self.counts()
        self.assertEqual(after["sidebar"], before["sidebar"] - 1, f"{before} -> {after}")
        self.assertFalse([r for r in self.props() if "Charlie huddle lanterns" in r["text"]], "the row stayed")
        said = " ".join(self.toast_texts())
        self.assertTrue(said, "no result shown")
        self.assertNotIn("decision", said.lower(), f"an action is reported as a decision: {said}")
        self.assertPlain(said)

    def test_c14_approve_on_the_intake_minutes_row_ends_visibly(self):
        """14. Approve on the minutes row in Intake never ends silent: either the minutes are approved (toast, row leaves) or the page
        takes you to the Minutes view's box that says what needs a look."""
        self.stage("Delta huddle")
        self.open_intake("Delta huddle")
        row = self.prop("draft", "Delta huddle")
        self.click_row_button(row["n"], "approve")
        self.settle(3.5)
        ended = bool(self.toast_texts()) or self.b.eval("VIEW") == "minutes" or self.row_text("Delta huddle") is None
        self.assertTrue(ended, "Approve on the minutes row did nothing visible")

    def test_c15_approve_routine_moves_the_group_and_says_how_many(self):
        """15. Approve routine on a minutes group: the routine items are registered, the rows leave, the toast says how many and has Undo."""
        self.stage("Echo huddle")
        self.open_intake("Echo huddle")
        before, actions = self.counts(), self.count("actions")
        self.b.click("#v-intake-review [data-ira=routine]")
        self.settle(3.5)
        self.assertEqual(self.count("actions"), actions + 2)
        self.assertLess(self.counts()["to_check"], before["to_check"])
        said = " ".join(self.toast_texts())
        self.assertRegex(said, r"Approved 2")
        self.assertTrue(any(a == "Undo" for _, a in self.toasts()), "no Undo on the result")
        self.assertPlain(said)

    def test_c16_approve_routine_on_mail_says_how_many_in_words(self):
        """16. Approve routine on the From mail and Teams group: registered, the row leaves, and the message names what was approved."""
        self.open_intake()
        b = self.b
        b.eval("(()=>{const f=document.querySelector('[data-irfold=mail]'); if(f && /Show/.test(f.innerText)) f.click(); return 1})()")
        b.pump(0.6)
        self.assertTrue(b.eval("!!document.querySelector('[data-irsec=mail] [data-ira=routine], #v-intake-review [data-ira=routine]')"), "no routine group on the mail section")
        actions = self.count("actions")
        b.click("#v-intake-review [data-ira=routine]")
        self.settle(3.5)
        self.assertGreater(self.count("actions"), actions)
        said = " ".join(self.toast_texts())
        self.assertRegex(said, r"[Aa]pproved \d+")
        print("\nC16:", said)
        self.assertNotRegex(said, r"\d+ routine\b(?! items?\b)", f"'routine' used as a noun with no noun: {said}")


# ───────────────────────────── Held minutes ─────────────────────────────

class Held307(Intake307):
    """Checks 20 to 24: minutes whose transcript has left the inbox (a vault in use can hold several of them)."""

    def test_c20_approve_without_the_transcript_files_the_minutes(self):
        """20. Approve without the transcript on a held row: the minutes are filed without the transcript copy, the ticked items are
        registered, a plain message with Undo says so, and the held note is gone from the row (it never stays held and silent)."""
        self.stage("Foxtrot huddle", held=True)
        self.open_intake("Foxtrot huddle")
        row = self.prop("draft", "Foxtrot huddle")
        self.assertIn("held-approve", row["btns"])
        before, actions = self.counts(), self.count("actions")
        self.click_row_button(row["n"], "held-approve")
        self.settle(3.5)
        self.assertEqual(self.count("actions"), actions + 2, "nothing was registered: the approval is still held")
        said = " ".join(self.toast_texts())
        self.assertIn("without the transcript", said)
        self.assertPlain(said)
        self.assertTrue(any(a == "Undo" for _, a in self.toasts()), "no Undo on the result")
        self.assertNotIn("Held:", self.row_text("Foxtrot huddle") or "", "the row still says it is held")
        self.assertLess(self.counts()["to_check"], before["to_check"])

    def test_c21_a_held_row_offers_both_ways_out_and_never_a_plain_approve(self):
        """21. A held minutes row says why in words and offers Approve without the transcript and Discard, not a plain Approve."""
        self.stage("Golf huddle", held=True)
        self.open_intake("Golf huddle")
        row = self.prop("draft", "Golf huddle")
        self.assertIn("held-approve", row["btns"])
        self.assertIn("held-discard", row["btns"])
        self.assertNotIn("approve", row["btns"])
        self.assertIn("Held:", row["text"])

    def test_c22_discard_a_held_row_in_plain_words(self):
        """22. Discard on a held row: the row leaves, Drafted drops, the minutes are kept aside, and the message names no file path."""
        self.stage("Hotel huddle", held=True)
        self.open_intake("Hotel huddle")
        row = self.prop("draft", "Hotel huddle")
        before = self.counts()
        self.click_row_button(row["n"], "held-discard")
        self.settle(3.5)
        self.assertIsNone(self.row_text("Hotel huddle"), "the row stayed")
        self.assertEqual(self.counts()["drafted"], before["drafted"] - 1)
        self.assertTrue(list((self.vault / "system/staging/discarded").glob("*.json")), "nothing was kept aside")
        said = " ".join(self.toast_texts())
        self.assertTrue(said, "no result shown")
        self.assertPlain(said)

    def test_c23_the_minutes_editor_files_held_minutes_in_place(self):
        """23. Approve minutes in the editor on held minutes: no trip to another page. It says in plain words the transcript is gone and
        offers File without the transcript copy right there; pressing it files the minutes (items registered) and the failed try changed nothing."""
        prop, _ = self.stage("India huddle", held=True)
        self.open_intake()
        actions = self.count("actions")
        self.go_minutes(prop)
        version = self.b.eval("(document.querySelector('.sheet-status')||{}).innerText")
        self.b.click("#mnApproveBtn")
        self.b.pump(1.5)
        if self.b.eval("!!document.querySelector('dialog[open]')"):
            self.b.eval("[...document.querySelectorAll('dialog[open] button')].find(x=>/^Approve/.test(x.innerText.trim())).setAttribute('data-hc','go')")
            self.b.click("dialog[open] button[data-hc=go]")
        self.b.pump(2.0)
        shown = self.toasts()
        said = " ".join(t for t, _ in shown)
        self.assertTrue(any("without the transcript copy" in a for _, a in shown) or
                        self.b.eval("!!([...document.querySelectorAll('#v-minutes button, dialog[open] button')].find(x=>/without the transcript copy/i.test(x.innerText)))"),
                        f"no way to file without the transcript in place: {shown}")
        self.assertPlain(said, "the editor's message")
        self.assertEqual(self.count("actions"), actions, "the failed try registered something")
        self.assertEqual(self.b.eval("(document.querySelector('.sheet-status')||{}).innerText"), version, "the failed try changed the minutes")
        if any("without the transcript copy" in a for _, a in shown):
            self.b.click("#snackU")
            self.b.pump(3.0)
            self.assertEqual(self.count("actions"), actions + 2, "File without the transcript copy registered nothing")

    def test_c24_key_a_on_a_held_row_offers_the_fix_in_plain_words(self):
        """24. A on a held minutes row says why in words (no path, no 'proposal') and offers Approve without the transcript on the toast."""
        self.stage("Juliet huddle", held=True)
        self.open_intake("Juliet huddle")
        row = self.prop("draft", "Juliet huddle")
        self.b.eval(f"document.querySelector(\"tr.irprop[data-irn='{row['n']}']\").focus()")
        self.b.key("a")
        self.b.pump(2.0)
        shown = self.toasts()
        self.assertTrue(shown, "A on a held row did nothing visible")
        self.assertTrue(any(a for _, a in shown), f"no button to approve without the transcript: {shown}")
        self.assertPlain(shown[-1][0])


# ───────────────────────────── Stale rows ─────────────────────────────

class Stale307(Intake307):
    """Checks 30 to 32: the page shows a row or view that has changed since (approved in Claude Code, a second tab, a scheduled run)."""

    def test_c30_a_stale_row_never_approves_another_item(self):
        """30. The minutes row is on screen, the same minutes are approved elsewhere (the list renumbers); pressing Approve on the stale
        row must not register anything else, and must say the minutes are already filed."""
        self.stage("Kilo huddle")
        self.stage("Lima huddle")
        self.stage("Mike huddle")
        self.open_intake("Kilo huddle")
        row = self.prop("draft", "Kilo huddle")
        self.b.eval("window.HK=document.querySelector(\"#v-intake-review tr.irprop[data-irn='%s'] [data-ira=approve]\"); !!window.HK" % row["n"])
        self.cli_approve("Kilo huddle", ("Minutes",))
        counts = {t: self.count(t) for t in ("actions", "decisions", "raid")}
        self.settle(3.0)
        conn = self.b.eval("window.HK.isConnected")
        shown = self.b.eval("window.HK.isConnected ? window.HK.closest('tr').innerText.replace(/\\n+/g,' | ') : null")
        kilo_left = self.b.eval("[...document.querySelectorAll('#v-intake-review tr.irprop[data-kind=draft]')].some(t=>t.innerText.includes('Kilo huddle') && t.querySelector('[data-ira=approve]'))")
        print("\nC30 held button connected:", conn, "row now shows:", shown, "| a Kilo row with Approve still drawn:", kilo_left)
        if conn:
            self.b.eval("window.HK.click()")
        else:
            self.assertFalse(kilo_left, "the stale Kilo row still offers Approve")
            self.b.eval("window.HK.click()")     # PROBE ONLY: a detached node (no person can press it): what would the handler do?
        self.settle(3.5)
        now = {t: self.count(t) for t in ("actions", "decisions", "raid")}
        self.assertEqual(now, counts, f"pressing Approve on a stale row registered something else: {counts} -> {now}; toast {self.toast_texts()}")
        said = " ".join(self.toast_texts()).lower()
        print("C30 toasts:", self.toast_texts(), "counts", counts, "->", now)
        if conn:
            self.assertTrue("already" in said or "no longer" in said, f"nothing said the minutes were already approved: {self.toast_texts()}")

    def test_c31_a_stale_minutes_view_says_the_minutes_are_already_filed(self):
        """31. The Minutes view is open, the minutes are approved elsewhere, Approve minutes is pressed: the page says they were already
        approved (not 'That file isn't there') and the view shows them as filed."""
        prop, _ = self.stage("November huddle")
        self.open_intake()
        self.go_minutes(prop)
        self.cli_approve("November huddle", ("Minutes",))
        self.approve_in_view()
        said = " ".join(self.toast_texts())
        self.assertNotIn("isn't there", said)
        self.assertRegex(said.lower(), r"already|no longer waiting|has been approved|filed", f"unhelpful message: {said!r}")

    def test_c32_a_stale_approve_routine_changes_nothing_and_says_so(self):
        """32. Approve routine when its items were approved elsewhere: nothing is approved, the minutes aren't edited, and the message says
        there was nothing left (not 'Approved 0 items … 2 lines taken out')."""
        self.stage("Oscar huddle")
        self.open_intake("Oscar huddle")
        self.cli_approve("Oscar huddle", ("Action",))
        log = self.count("change_log")
        self.b.click("#v-intake-review [data-ira=routine]")
        self.settle(3.5)
        said = " ".join(self.toast_texts())
        self.assertTrue(said, "no result shown")
        self.assertNotIn("lines taken out", said)
        self.assertEqual(self.count("change_log"), log, "the stale press still changed the record")


# ───────────────────────────── Later, Not needed, Restore, Process ─────────────────────────────

class SetAside307(Intake307):
    """Checks 40 to 44: Later, Not needed, Restore and Process, on files dropped into the inbox."""

    def drop(self, name):
        (self.vault / "inbox" / name).write_text(vtt(), encoding="utf-8")

    def mark(self, needle):
        ok = self.b.eval("(()=>{const r=[...document.querySelectorAll('#v-intake-review tr.irmeet')].find(r=>r.innerText.includes(%s)); "
                         "if(!r) return false; r.setAttribute('data-hc','row'); return true})()" % json.dumps(needle))
        self.assertTrue(ok, f"no row {needle}")

    def unmark(self):
        self.b.eval("document.querySelectorAll('[data-hc]').forEach(x=>x.removeAttribute('data-hc'))")

    def sections(self):
        return self.b.eval("Object.fromEntries([...document.querySelectorAll('.irsec[data-irsec=later],.irsec[data-irsec=not_needed]')].map(x=>[x.dataset.irsec,+(x.querySelector('.rgc')||{}).innerText]))")

    def test_c40_later_moves_the_row_and_undo_brings_it_back(self):
        """40. Later on a file row: the row leaves Arrived, the Later list holds it, the toast says so with Undo, and Undo brings it back."""
        self.drop("2026-10-20 Papa planning.vtt")
        self.open_intake()
        before = self.counts()
        self.mark("Papa planning")
        self.b.click("tr[data-hc=row] [data-ira=later]")
        self.unmark()
        self.settle()
        self.assertIsNone(self.row_text("Papa planning"))
        self.assertEqual(self.counts()["arrived"], before["arrived"] - 1)
        self.assertEqual(self.sections().get("later"), 1)
        self.assertTrue(any(a == "Undo" for _, a in self.toasts()))
        self.b.click("#snackU")
        self.settle()
        self.assertIsNotNone(self.row_text("Papa planning"), "Undo didn't bring the row back")
        self.assertEqual(self.counts()["arrived"], before["arrived"])

    def test_c41_not_needed_takes_a_reason_and_restore_brings_it_back(self):
        """41. Not needed asks for a reason, sets the row aside with it, and Restore in the list brings it back with a message."""
        self.drop("2026-10-20 Quebec planning.vtt")
        self.open_intake()
        before = self.counts()
        self.mark("Quebec planning")
        self.b.click("tr[data-hc=row] button[aria-label='Not needed, with a reason']")
        self.unmark()
        self.b.pump(0.6)
        self.assertTrue(self.b.eval("!!document.querySelector('#irAside [data-reason]')"), "no reasons offered")
        self.b.click("#irAside [data-reason]")
        self.settle()
        self.assertIsNone(self.row_text("Quebec planning"))
        self.assertEqual(self.sections().get("not_needed"), 1)
        self.assertEqual(self.counts()["arrived"], before["arrived"] - 1)
        self.b.eval("(()=>{const f=document.querySelector('[data-irfold=not_needed]'); if(f && /Show/.test(f.innerText)) f.click(); return 1})()")
        self.b.pump(0.5)
        self.b.eval("window.__w.snacks.length=0")
        self.b.click("#v-intake-review [data-ira=restore]")
        self.settle()
        self.assertIsNotNone(self.row_text("Quebec planning"))
        self.assertIn("Restored", " ".join(self.toast_texts()))

    def test_c42_restoring_a_file_that_has_left_intake_says_so(self):
        """42. Restore on a set-aside file that is no longer in the inbox: the page says it is gone; it does not claim 'Restored'."""
        self.drop("2026-10-20 Romeo planning.vtt")
        self.open_intake()
        self.mark("Romeo planning")
        self.b.click("tr[data-hc=row] [data-ira=later]")
        self.unmark()
        self.settle()
        (self.vault / "inbox" / "2026-10-20 Romeo planning.vtt").unlink()
        self.b.eval("(()=>{const f=document.querySelector('[data-irfold=later]'); if(f && /Show/.test(f.innerText)) f.click(); return 1})()")
        self.b.pump(0.5)
        self.b.eval("window.__w.snacks.length=0")
        self.b.click("#v-intake-review [data-ira=restore]")
        self.settle()
        said = " ".join(self.toast_texts())
        self.assertTrue(said, "no result shown")
        self.assertNotIn("Restored", said, f"claims a restore that cannot have happened: {said}")

    def test_c43_process_that_stages_nothing_says_why_in_plain_words(self):
        """43. Make minutes when the run produces nothing: the row stays in Arrived, says why in plain words (no 'staged'), the counts don't move."""
        self.drop("2026-10-20 Sierra planning.vtt")
        self.open_intake()
        before = self.counts()
        self.mark("Sierra planning")
        self.b.click("tr[data-hc=row] [data-ira=process]")
        self.unmark()
        self.b.wait("!document.querySelector('[data-ira=processing]') && !document.querySelector('[data-ira=stop]')", 60)
        self.b.pump(2.0)
        row = self.row_text("Sierra planning")
        self.assertIsNotNone(row)
        self.assertEqual(self.counts()["arrived"], before["arrived"])
        print("\nC43 row:", row, "| toasts:", self.toast_texts())
        self.assertPlain(row.replace("2026-10-20 Sierra planning.vtt", "<file name>") + " " + " ".join(self.toast_texts()), "the row's result")
        self.assertRegex(row, r"Couldn't|Needs you|not made|No minutes|Not drafted yet", "the row doesn't say what happened")

    def test_c44_process_that_fails_says_so_on_the_row(self):
        """44. Make minutes when the model run fails: the row says it couldn't and why in words, and the file stays where it was."""
        self.drop("2026-10-20 Tango planning.vtt")
        (self.vault / "fake_mode.txt").write_text("fail")
        self.addCleanup((self.vault / "fake_mode.txt").unlink, missing_ok=True)
        self.open_intake()
        self.mark("Tango planning")
        self.b.click("tr[data-hc=row] [data-ira=process]")
        self.unmark()
        self.b.wait("!document.querySelector('[data-ira=processing]') && !document.querySelector('[data-ira=stop]')", 60)
        self.b.pump(2.0)
        row = self.row_text("Tango planning")
        self.assertIsNotNone(row)
        self.assertIn("Couldn't", row)
        self.assertPlain(" ".join(self.toast_texts()), "the failure message")
        self.assertTrue((self.vault / "inbox" / "2026-10-20 Tango planning.vtt").is_file())


if __name__ == "__main__":
    unittest.main()
