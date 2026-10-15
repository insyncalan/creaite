"""BL-149: no dead ends into Claude Code. A reminder's own button drafts the report through ask creaite; Approve on a draft in
Review goes through review.py (and Approve all routine still never covers minutes); a conflicting proposal shows both versions
with Keep current and Use this one, which settle it through review.py and apply with Undo. A real browser against the real
live server, with a stand-in `claude`.

Run: python3 dev/tests/test_no_dead_ends.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

FAKE = r'''#!/usr/bin/env python3
import json, sys
args = sys.argv[1:]
message = args[args.index("-p") + 1]
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init", "session_id": "sess-1"})
out({"type": "assistant", "message": {"content": [{"type": "text", "text": "Drafting: " + message}]}})
out({"type": "result", "result": "ok", "session_id": "sess-1"})
'''


def conflict_proposal(v, n, name):
    """An edit to ABC-A-002's owner made before a newer change: the apply held it as a conflict."""
    v.propose(name, [{"n": n, "op": "update", "table": "actions", "id": "ABC-A-002",
                      "changes": {"owner": "Omar Ali"}, "based_on": "2000-01-01T00:00:00",
                      "flags": ["conflict"], "conflict_reason": "ABC-A-002 changed after this proposal was made",
                      "decision": "pending", "source": "Alan (cx-edit)"}])


class NoDeadEnds(LiveBrowserCase):
    width, height = 1400, 900

    @classmethod
    def load(cls, v):
        from test_dashboard import populate
        populate(v)
        conflict_proposal(v, 1, "conflict")
        fake = v.root / "fake_claude.py"
        fake.write_text(FAKE)
        fake.chmod(0o755)

    @classmethod
    def server_env(cls):
        return {"CREAITE_CLAUDE": str(cls.v.root / "fake_claude.py")}

    def owner(self):
        return self.v.rows("actions")[1]["owner"] if self.v.rows("actions")[1]["id"] == "ABC-A-002" else \
            next(r["owner"] for r in self.v.rows("actions") if r["id"] == "ABC-A-002")

    def test_a_reminder_has_its_own_button_and_no_command_line(self):
        b = self.b
        b.eval("go('today')")
        b.pump(0.3)
        rows = json.loads(b.eval("JSON.stringify([...document.querySelectorAll('#attnList li.rem')].map(li=>[li.dataset.id,(li.querySelector('.rmgo [data-d=run]')||{dataset:{}}).dataset.tip||'',(li.querySelector('.rmgo [data-d=run]')||{getAttribute:()=>''}).getAttribute('aria-label'),li.querySelector('.tb p')?li.querySelector('.tb p').textContent:'']))"))
        # BL-319: the reminder's own button is an icon, named on hover (data-tip) and to a screen reader (the action, then the reminder)
        weekly = [r for r in rows if r[0].startswith("weekly:")]
        client = [r for r in rows if r[0].startswith("client:")]
        self.assertTrue(weekly and client, rows)
        self.assertEqual(weekly[0][1], "Draft weekly report")
        self.assertEqual(client[0][1], "Draft client report")
        self.assertTrue(weekly[0][2].startswith("Draft weekly report: ") and client[0][2].startswith("Draft client report: "), rows)
        for r in rows:
            self.assertNotIn("Claude Code", r[3])                          # the command is not the instruction
        rid = weekly[0][0]
        b.click(f'#attnList li.rem[data-id="{rid}"] .rmgo [data-d="run"]')
        b.wait("document.querySelectorAll('#chLog .msg.a.md').length>0", 20)
        self.assertIn("Drafting: weekly report", b.eval("document.querySelector('#chLog .msg.a.md').textContent"))
        b.wait("!RUN && !BUSY", 20)
        b.eval("setLive(false); renderToday()")                            # live server down: the command is the footnote
        b.pump(0.2)
        txt = b.eval(f"document.querySelector('#attnList li.rem[data-id=\"{rid}\"] .tb p').textContent")
        self.assertIn("Claude Code", txt)
        run = f"document.querySelector('#attnList li.rem[data-id=\"{rid}\"] .rmgo [data-d=run]')"
        self.assertEqual(b.eval(f"{run}.getAttribute('aria-disabled')"), "true")      # blocked, still focusable, says why
        self.assertEqual(b.eval(f"{run}.dataset.tip"), "Needs the live server")
        b.eval("setLive(true)")

    def test_approve_on_a_draft_goes_through_review_py_and_routine_skips_minutes(self):
        b = self.b
        b.eval("go('review')")
        b.pump(0.3)
        b.eval("""window.CALLS=[]; { const a=api; api=function(u,body){ if(u==='/api/review'){ CALLS.push(body); return Promise.resolve({ok:true,message:'Approved 1.'}); } return a.apply(this,arguments); }; }""")
        n = b.eval("REV.find(r=>r.kind==='draft').n")
        b.click(f'#reviewBody tr[data-n="{n}"] [data-act="a"]')
        b.pump(0.3)
        calls = json.loads(b.eval("JSON.stringify(CALLS)"))
        self.assertEqual(len(calls), 1)
        self.assertEqual((calls[0]["ref"], calls[0]["decision"]), ("meeting", "approved"))   # review.py's checks run
        self.assertNotIn("Claude Code", b.eval("document.getElementById('snackT').textContent"))
        self.assertFalse(b.eval("rvMatching().filter(rvBulkOK).some(r=>r.kind==='draft')"))   # Approve all routine never covers minutes
        b.eval("openProposal(%d)" % n)
        self.assertIn("press Approve here", b.eval("document.getElementById('snackT').textContent"))

    def test_a_conflict_shows_both_versions_and_two_buttons(self):
        b = self.b
        b.eval("go('review')")
        b.pump(0.3)
        n = b.eval("REV.find(r=>(r.flags||[]).includes('conflict')).n")
        row = f'#reviewBody tr[data-n="{n}"]'
        self.assertFalse(b.eval(f"!!document.querySelector('{row} [data-act=\"a\"]')"))   # no plain Approve
        txt = b.eval(f"document.querySelector('{row}').textContent")
        self.assertIn("Now: Sara Example", txt)
        self.assertIn("This one: Omar Ali", txt)
        self.assertIn("Keep current", txt)
        self.assertIn("Use this one", txt)
        before = self.owner()
        b.click(f'{row} [data-act="co"]')
        b.wait("!REV.some(r=>(r.flags||[]).includes('conflict')&&!r.done)", 60)     # the apply behind it can take a while on a loaded runner
        for _ in range(120):
            if self.owner() == "Omar Ali":
                break
            b.pump(0.25)
        self.assertEqual((before, self.owner()), ("Sara Example", "Omar Ali"))   # the edit replaced the newer change
        self.assertFalse(b.eval("document.querySelector('#chat').classList.contains('on')"))   # settled on the row, not in the chat


class KeepCurrent(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        from test_dashboard import populate
        populate(v)
        conflict_proposal(v, 1, "conflict")

    def test_keep_current_rejects_the_edit(self):
        b = self.b
        b.eval("go('review')")
        b.pump(0.3)
        n = b.eval("REV.find(r=>(r.flags||[]).includes('conflict')).n")
        b.click(f'#reviewBody tr[data-n="{n}"] [data-act="ck"]')
        b.wait("!REV.some(r=>(r.flags||[]).includes('conflict')&&!r.done)", 60)
        b.pump(0.5)
        owner = next(r["owner"] for r in self.v.rows("actions") if r["id"] == "ABC-A-002")
        self.assertEqual(owner, "Sara Example")
        data = json.loads((self.v.root / "system/staging/applied/proposed-conflict.json").read_text()) \
            if (self.v.root / "system/staging/applied/proposed-conflict.json").exists() \
            else json.loads((self.v.root / "system/staging/proposed-conflict.json").read_text())
        self.assertEqual(data["items"][0]["decision"], "rejected")


if __name__ == "__main__":
    unittest.main()
