"""BL-227 (sprint-drafts-writing): one set of facts, many forms (Generate's Form and the Steering committee and Sponsor audiences).

Run: python3 dev/tests/test_drafts_forms.py
Plain code chooses the facts (status_facts.py); a stand-in Claude (drafts_fake.py) words them, so no model is called. A form other
than the Current state is shown with Copy and never saved.
"""
import json
import subprocess
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import drafts_fake  # noqa: E402
from test_dashboard import d, populate  # noqa: E402
from test_drafts_update import DraftCase  # noqa: E402
from test_tracker import ABC, Vault, action  # noqa: E402


def secret_world(v):
    populate(v)
    v.propose("secret", [action(30, description="Confidential: renegotiate the supplier's fee", due_date=d(-6), priority="Urgent")])
    v.run("apply")


def run(v, *args, stdin=None):
    r = subprocess.run([sys.executable, *args], input=stdin, capture_output=True, text=True, cwd=v.root)
    return r.stdout


class Facts(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.cleanup)
        secret_world(self.v)

    def sheet(self, audience):
        out = run(self.v, "system/scripts/status_facts.py", "facts", "ABC", "--audience", audience, "--json")
        return json.loads(out)

    def test_steering_and_sponsor_drop_the_sensitive_lines_and_renumber(self):
        internal = self.sheet("internal")
        self.assertIn("renegotiate the supplier", internal["text"])
        for audience in ("steering", "sponsor"):
            f = self.sheet(audience)
            self.assertNotIn("renegotiate the supplier", f["text"])
            self.assertIn(f"{audience} audience", f["text"])
            fids = [ln["fid"] for p in f["parts"] for ln in p["lines"]]
            self.assertEqual(fids, [f"F{i}" for i in range(1, len(fids) + 1)])
            self.assertTrue(fids)

    def test_the_current_state_material_takes_the_new_audiences(self):
        out = run(self.v, "system/scripts/report.py", "current-context", "ABC", "--audience", "steering")
        self.assertIn("Audience: the steering committee.", out)
        self.assertNotIn("renegotiate the supplier", out)

    def context(self, **body):
        return json.loads(run(self.v, "system/scripts/drafts.py", "context", stdin=json.dumps({"kind": "status-form", "code": "ABC", **body})))

    def test_each_form_carries_its_voice_and_length(self):
        for form, limit in (("three", "at most 60 words and 3 lines"), ("email", "at most 120 words and 1 line"),
                            ("teams", "at most 50 words and 3 lines"), ("steering", "at most 150 words")):
            ctx = self.context(form=form)
            self.assertIn(f"FORM: {form}", ctx["prompt"])
            self.assertIn(limit, ctx["prompt"])
            self.assertIn("How this form reads", ctx["prompt"])
            self.assertTrue(ctx["sources"])
        self.assertIn("Exactly three lines", self.context(form="three")["prompt"])
        self.assertIn("at most 40 words", self.context(form="steering", length="short")["prompt"])

    def test_client_safe_holds_nothing_internal(self):
        ctx = self.context(form="email", audience="client")
        if "nothing" in ctx:                                    # nothing client-visible in the fixture: no model is asked at all
            self.assertIn("empty", ctx["nothing"])
            return
        self.assertNotIn("Escalate data access", ctx["prompt"])
        self.assertNotIn("renegotiate", ctx["prompt"])

    def test_an_unknown_form_or_audience_is_refused(self):
        self.assertIn("refused", self.context(form="poem"))
        self.assertIn("refused", self.context(form="three", audience="board"))

    def test_the_length_check_is_plain_code(self):
        sys.path.insert(0, str(self.v.root / "system/scripts"))
        import drafts
        ctx = {"kind": "status-form", "sources": [{"ref": "S1"}], "extra": {"form": "three", "words": 60, "lines": 3}}
        out = drafts.result({}, ctx, "One. [S1]\nTwo. [S1]\nThree. [S1]\nFour. [S1]")
        self.assertEqual(out["lines"], 4)
        self.assertEqual(out["length_notes"], ["4 lines: this form takes 3."])


class FormsCase(DraftCase):
    @classmethod
    def load(cls, v):
        secret_world(v)
        cls.fake = drafts_fake.install(v)

    def test_generate_with_a_form_streams_a_draft_and_saves_nothing(self):
        memory = (self.v.root / ABC / "CLAUDE.md").read_text()
        got = self.b.eval("""(async()=>{ const r=await fetch('/api/current/generate',{method:'POST',headers:{'Content-Type':'application/json','X-Creaite-Token':D.token},
            body:JSON.stringify({code:'ABC',form:'three',audience:'sponsor'})}); return await r.text(); })()""")
        events = [json.loads(ln[6:]) for ln in got.splitlines() if ln.startswith("data: ")]
        draft = next(e for e in events if e["type"] == "draft")
        self.assertEqual(draft["text"], "UAT is at risk.\nData access is late.\nNext: escalate to the CIO.")
        self.assertEqual(draft["lines"], 3)
        self.assertEqual(draft["length_notes"], [])
        self.assertIn("Audience: the sponsor.", drafts_fake.prompt(self.fake))
        self.assertNotIn("renegotiate", drafts_fake.prompt(self.fake))
        run_id = next(e.get("run") for e in events if e["type"] == "done")
        self.b.eval(f"api('/api/ask/ack',{{run:{json.dumps(run_id)}}})")
        self.assertEqual((self.v.root / ABC / "CLAUDE.md").read_text(), memory)

    def pick(self, trigger, label):
        """#110: choose from one of the dialog's menus (the Picker block's list), by the option's words."""
        b = self.b
        b.click(trigger)
        b.wait("document.querySelector('.pkpop [role=option]')")
        b.eval(f"[...document.querySelectorAll('.pkpop [role=option]')].find(o=>o.textContent.trim().startsWith({label!r})).click()")

    def test_the_dialog_writes_a_teams_message_with_copy_and_no_save(self):
        b = self.b
        memory = (self.v.root / ABC / "CLAUDE.md").read_text()
        b.eval("openGen('ABC')")
        b.wait("document.getElementById('genDlg').open&&document.querySelector('#genFormKind')")
        self.pick("#genFormKind", "Teams message")
        self.assertEqual(b.eval("document.getElementById('genLen').getAttribute('aria-disabled')"), "true")        # Length dims; the reason is on hover
        self.assertEqual(b.eval("document.getElementById('genLen').title"), "At most 50 words")
        self.assertEqual(b.eval("document.getElementById('genGoT').textContent"), "Write it")
        b.click("#genGo")
        b.wait("document.querySelector('#genOut .drcard')", 30)
        self.assertTrue(b.eval("document.getElementById('genDlg').open"))
        self.assertIn("Quick update: UAT is at risk", b.eval("document.querySelector('#genOut .drtext').textContent"))
        self.assertIsNone(b.eval("document.querySelector('#genOut [data-gfdo=rich]')"))       # Teams: plain text only
        self.assertEqual(b.eval("[...document.querySelectorAll('#genOut button')].map(x=>x.textContent)"), ["Discard", "Copy as plain text"])
        self.assertEqual(b.eval("document.getElementById('genDlg').querySelector('h2').textContent"), "Write a Teams message")
        b.eval("window.__clip=[]; navigator.clipboard.writeText=async t=>{ window.__clip.push(t); };")
        b.click("#genOut [data-gfdo=plain]")
        b.wait("window.__clip.length===1")
        self.assertEqual(b.eval("window.__clip[0]"), "Quick update: UAT is at risk because data access is late.")
        for _ in range(50):
            if (self.stats().get("forms") or {}).get("used") == 1:
                break
            time.sleep(0.1)
        self.assertEqual(self.stats()["forms"]["used"], 1)
        self.assertFalse(b.eval("!!CURED"))                                                  # the Current state editor never opened
        self.assertEqual((self.v.root / ABC / "CLAUDE.md").read_text(), memory)
        self.assertEqual(b.errors, [])

    def test_forms_off_greys_the_other_forms(self):
        """BL-290: with Forms off the four other forms are greyed with the reason, and a remembered one falls back to Current state."""
        b = self.b
        try:
            b.eval("S.drafting={...(S.drafting||{}),forms:false}; GEN.form='email'; openGen('ABC')")
            b.wait("document.getElementById('genDlg').open&&document.querySelector('#genFormKind')")
            self.assertEqual(b.eval("document.getElementById('genFormKind').dataset.v"), "current")           # the remembered one fell back
            b.click("#genFormKind")
            b.wait("document.querySelector('.pkpop [role=option]')")
            st = b.eval("""[...document.querySelectorAll('.pkpop [role=option]')].map(x=>[x.firstElementChild.firstChild.textContent,x.getAttribute('aria-disabled'),x.getAttribute('aria-selected'),(x.querySelector('.h')||{}).textContent||''])""")
            self.assertEqual([(k, d, p) for k, d, p, _ in st], [("Current state", None, "true"), ("Steering note", "true", "false"), ("Three-line update", "true", "false"),
                                                                ("Email paragraph", "true", "false"), ("Teams message", "true", "false")])
            self.assertTrue(all("is off in Settings › Advanced › AI drafts" in t for k, d, _, t in st if d))
            b.eval("[...document.querySelectorAll('.pkpop [role=option]')].find(o=>o.textContent.startsWith('Teams')).click()")        # refused
            self.assertEqual(b.eval("GEN.form"), "current")
            self.assertEqual(b.eval("document.querySelector('#genDlg h2').textContent"), "Generate current state")
            self.assertEqual(b.eval("document.getElementById('genGoT').textContent"), "Generate")
        finally:
            b.eval("S.drafting={...(S.drafting||{}),forms:true}; document.getElementById('genDlg').close()")

    def test_the_current_state_form_is_generate_as_before(self):
        b = self.b
        b.eval("store.set('creaite-gen-form','steering'); GEN.form='steering'; openGen('ABC')")
        b.wait("document.getElementById('genDlg').open")
        self.assertEqual(b.eval("document.querySelector('#genDlg h2').textContent"), "Write a steering note")           # a remembered form keeps its own title
        self.pick("#genFormKind", "Current state")
        self.assertEqual(b.eval("document.querySelector('#genDlg h2').textContent"), "Generate current state")
        self.assertIsNone(b.eval("document.getElementById('genLen').getAttribute('aria-disabled')"))
        b.click("#genAud")
        b.wait("document.querySelector('.pkpop [role=option]')")
        self.assertEqual(b.eval("[...document.querySelectorAll('.pkpop [role=option]')].map(x=>x.textContent.trim())"),
                         ["Internal", "Client-safe", "Steering committee", "Sponsor"])

    def test_the_title_says_an_before_a_vowel(self):
        """#110: "Write an email paragraph", not "a email paragraph"."""
        b = self.b
        b.eval("GEN.form='current'; openGen('ABC')")
        b.wait("document.getElementById('genDlg').open")
        titles = {}
        for label in ("Email paragraph", "Steering note", "Three-line update", "Teams message"):
            self.pick("#genFormKind", label)
            titles[label] = b.eval("document.querySelector('#genDlg h2').textContent")
        self.assertEqual(titles, {"Email paragraph": "Write an email paragraph", "Steering note": "Write a steering note",
                                  "Three-line update": "Write a three-line update", "Teams message": "Write a Teams message"})
        b.eval("document.getElementById('genDlg').close()")


if __name__ == "__main__":
    unittest.main()
