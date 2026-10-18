"""BL-224 (sprint-drafts-writing): follow-up and chase emails on the one Draft email builder.

Run: python3 dev/tests/test_drafts_email.py
draftEmail is plain code in the page (no model); Polish the wording uses a stand-in Claude (drafts_fake.py). Nothing is ever sent and no
Outlook draft is made: copying writes nothing, and the only record is "I sent it" in system/staging/chases.json (references only).
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
from test_dashboard import d  # noqa: E402
from test_dashboard import today as _cx_today  # noqa: E402
from test_drafts_update import DraftCase  # noqa: E402
from test_tracker import ABC, Vault, action  # noqa: E402

TODAY = _cx_today().isoformat()


def shown(iso):
    return f"{iso[8:10]}-{iso[5:7]}-{iso[:4]}"


def build(b, o):
    """draftEmail in the page, with a fixed clock and the given options."""
    return b.eval("(()=>{ const o=%s; if(o.picked) o.picked=new Set(o.picked); return draftEmail({now:new Date('2026-10-12T09:00:00'),today:TODAY,"
                  "dueSoon:7,names:{ABC:'Example Programme'},from:'Alan',...o}); })()" % json.dumps(o))


ITEM = lambda i, o, due, **v: {"k": "actions", "id": f"ABC-A-{i:03d}", "p": "ABC", "t": f"Task {i}", "due": due, "pr": "Medium", "o": o, **v}  # noqa: E731


class FollowupFacts(unittest.TestCase):
    """drafts.py followup: the attendees (the calendar, then the register) and the minutes' own summary paragraph."""

    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.cleanup)
        self.v.run("init")
        (self.v.root / f"{ABC}/minutes").mkdir(parents=True, exist_ok=True)
        (self.v.root / f"{ABC}/minutes/{TODAY} ABC weekly.md").write_text(
            "# ABC weekly\n\n## Executive summary\n\nThe pilot is extended by two weeks.\nData access is the main risk.\n\n## Decisions\n\n- Extend\n")
        self.cal({"sensitivity": "normal"})

    def cal(self, extra):
        ev = {"id": "e1", "start": "09:00", "end": "10:00", "title": "ABC weekly", "attendees": [
            {"name": "Sara Example", "email": "sara@example.com"}, {"name": "Alan Carter", "email": "alan@example.com"}], **extra}
        (self.v.root / "system/staging/calendar.json").write_text(json.dumps({"days": {TODAY: [ev]}}))

    def facts(self):
        body = {"eid": "e1", "files": [f"{ABC}/minutes/{TODAY} ABC weekly.md", "../etc/passwd"]}
        r = subprocess.run([sys.executable, "system/scripts/drafts.py", "followup"], input=json.dumps(body), capture_output=True, text=True,
                           cwd=self.v.root)
        return json.loads(r.stdout)

    def test_the_attendees_without_alan_and_the_summary_paragraph(self):
        f = self.facts()
        self.assertEqual(f["attendees"], [{"name": "Sara Example", "email": "sara@example.com"}])
        self.assertEqual(f["summary"], "The pilot is extended by two weeks. Data access is the main risk.")

    def test_a_confidential_meeting_gives_no_attendees_and_no_summary(self):
        self.cal({"sensitivity": "confidential"})
        f = self.facts()
        self.assertEqual((f["attendees"], f["summary"]), ([], ""))
        self.assertIn("Confidential", f["note"])

    def test_the_chase_log_holds_references_only(self):
        run = lambda *a: subprocess.run([sys.executable, "system/scripts/drafts.py", *a], capture_output=True, text=True, cwd=self.v.root)  # noqa: E731
        self.assertEqual(run("chase", "record", "--ids", "ABC-A-001,not an id,ABC-A-002").returncode, 0)
        data = json.loads((self.v.root / "system/staging/chases.json").read_text())
        self.assertEqual(data, {"chases": [{"ids": ["ABC-A-001", "ABC-A-002"], "date": TODAY, "mode": "chase"}]})
        self.assertEqual(run("chase", "record", "--ids", "hello").returncode, 1)
        self.assertEqual(json.loads(run("chases").stdout)["ABC-A-001"], {"n": 1, "last": TODAY})


class EmailCase(DraftCase):
    @classmethod
    def load(cls, v):
        drafts_fake.load(v)
        v.propose("chase", [action(20, owner="Sara Example", due_date=d(-4), description="Send the test plan"),
                            action(21, owner="Sara Example", due_date=d(-2), description="Confidential: board pack figures"),
                            action(22, owner="Sara Example", due_date=d(9), description="Review the cut-over plan")])
        v.run("apply")
        cls.fake = drafts_fake.install(v)

    def chases_file(self):
        p = self.v.root / "system/staging/chases.json"
        return json.loads(p.read_text()) if p.exists() else None


class Builder(EmailCase):
    def test_the_followup_groups_actions_by_owner_with_the_lead_first(self):
        o = {"mode": "followup", "title": "ABC weekly", "day": "2026-10-12", "codes": ["ABC"], "summary": "The pilot is extended.",
             "attendees": [{"name": "Jane Doe", "email": "jane@example.com"}, {"name": "Sara Example", "email": "sara@example.com"}],
             "lead": "Sara Example",
             "items": [ITEM(1, "Omar Ali", "2026-10-20"), ITEM(2, "Jane Doe", "2026-10-15"), ITEM(3, "Sara Example", "2026-10-30"),
                       {"k": "decisions", "id": "ABC-D-004", "p": "ABC", "t": "Extend the pilot", "by": "Jane Doe"}]}
        em = build(self.b, o)
        t = em["text"]
        self.assertTrue(t.index("Sara Example\n") < t.index("Jane Doe\n") < t.index("Omar Ali\n"), t)
        self.assertIn("Good morning, all,", t)
        self.assertIn("Summary\nThe pilot is extended.", t)
        self.assertIn("Decisions\n  • Extend the pilot (Jane Doe)", t)
        self.assertEqual(em["to"], "jane@example.com; sara@example.com")
        self.assertEqual(em["subject"], "ABC · ABC weekly: follow-up and actions")
        self.assertIn("on Monday 12-10-2026", t)
        o["lead"] = ""
        t = build(self.b, o)["text"]
        self.assertTrue(t.index("Jane Doe\n") < t.index("Sara Example\n") < t.index("Omar Ali\n"))   # attendees in order

    def test_the_chase_tone_follows_the_log(self):
        items = [ITEM(1, "Sara Example", "2026-10-01")]
        base = {"mode": "chase", "name": "Sara Example", "items": items}
        first = build(self.b, {**base, "chased": {}})
        self.assertIn("A quick reminder", first["text"])
        self.assertEqual(first["subject"], "ABC-A-001 · Reminder")
        second = build(self.b, {**base, "chased": {"ABC-A-001": {"n": 1, "last": "2026-10-03"}}})
        self.assertIn("following up on my earlier note of 03-10-2026", second["text"])
        self.assertIn("Chased 03-10-2026, once", second["text"])
        self.assertEqual(second["subject"], "ABC-A-001 · Second reminder")
        firm = build(self.b, {**base, "chased": {"ABC-A-001": {"n": 2, "last": "2026-10-08"}}})
        self.assertIn("I have chased them twice, most recently on 08-10-2026", firm["text"])
        self.assertIn("Please reply with a firm date", firm["text"])
        self.assertEqual(firm["level"], 2)

    def test_the_chase_log_lines_never_reach_an_email_body_whoever_it_goes_to(self):   # #153
        line = "17-10-2026: Chased Sara Example by email (reminder 1); reply asked for by 19-10-2026."
        risk = {"k": "raid", "id": "ABC-R-001", "p": "ABC", "type": "Risk", "t": "Env not ready", "due": "2026-10-01", "pr": "High",
                "resp": "Agree dates\n" + line, "upd": "Waiting on the vendor\n" + line}
        only = {**risk, "id": "ABC-R-002", "resp": "- " + line, "upd": line.replace("Chased", "chased")}
        for mode in ("update", "chase"):
            em = build(self.b, {"mode": mode, "name": "Sara Example", "includeUpdate": True, "items": [risk, only]})
            blob = em["text"] + em["html"]
            for bit in ("Chased", "chased", "reminder 1", "reply asked for", "by email"):
                self.assertNotIn(bit, blob, (mode, bit))
            self.assertIn("Agree dates", em["text"])
            self.assertIn("Waiting on the vendor", em["text"])
            self.assertIn("Response: none recorded yet", em["text"])

    def test_the_update_request_is_unchanged_and_the_cover_replaces_only_the_opening(self):
        o = {"name": "Sara Example", "items": [ITEM(1, "Sara Example", "2026-10-01")]}
        plain = build(self.b, o)
        self.assertIn("I hope you're well.", plain["text"])
        self.assertEqual(plain["subject"], "ABC-A-001 · Update request")
        polished = build(self.b, {**o, "cover": "A new opening."})
        self.assertEqual(polished["text"].replace("A new opening.", plain["text"].split("\n")[2]), plain["text"])


class Popup(EmailCase):
    def open_person(self, mode):
        b = self.b
        b.eval(f"openDraftEmail('Sara Example','{mode}')")
        b.wait("document.getElementById('deDlg')&&document.getElementById('deDlg').open")

    def test_the_chase_offers_only_overdue_items_and_never_a_confidential_one(self):
        b = self.b
        self.open_person("chase")
        ids = b.eval("[...document.querySelectorAll('#deInc [data-deit]')].map(i=>i.dataset.deit)")
        self.assertIn("actions:ABC-A-006", ids)
        self.assertNotIn("actions:ABC-A-008", ids)                           # not overdue
        self.assertNotIn("actions:ABC-A-007", ids)                           # confidential: never offered
        self.assertIn("left out", b.eval("document.getElementById('deBody').textContent"))
        self.assertEqual(b.eval("document.querySelector('[data-demode=chase]').getAttribute('aria-pressed')"), "true")
        self.assertIn("not chased before", b.eval("document.querySelector('.dechase').textContent"))
        self.assertEqual(b.errors, [])

    def test_copying_writes_nothing_and_i_sent_it_writes_one_record_and_steps_up(self):
        b = self.b
        self.open_person("chase")
        b.eval("document.querySelectorAll('#deInc [data-deit]').forEach(i=>{ if(!i.checked) i.click(); })")
        b.eval("""window.__clip=[]; navigator.clipboard.write=async items=>{ window.__clip.push('rich'); };
                  navigator.clipboard.writeText=async t=>{ window.__clip.push(t); };""")
        b.click("#deCopyHtml")
        b.click("#deCopyText")
        b.wait("window.__clip.length===2")
        self.assertIsNone(self.chases_file())
        b.click("#deSent")
        b.wait("!document.getElementById('deDlg').open")                      # v2.3.0 #153: it logs the items and closes
        data = self.chases_file()
        self.assertEqual(len(data["chases"]), 1)
        rec = data["chases"][0]
        self.assertEqual(set(rec), {"ids", "date", "mode"})
        self.assertIn("ABC-A-006", rec["ids"])
        self.assertEqual(rec["mode"], "chase")
        self.open_person("chase")
        self.assertIn("A second reminder", b.eval("document.querySelector('.dechase').textContent"))
        b.eval("document.querySelectorAll('#deInc [data-deit]').forEach(i=>{ if(!i.checked) i.click(); })")
        self.assertIn("following up on my earlier note", b.eval("document.getElementById('dePrev').textContent"))

    def test_an_outside_address_unticks_internal_items_in_every_mode(self):
        b = self.b
        for mode in ("update", "chase"):
            self.open_person(mode)
            self.assertTrue(b.eval("DE.outside"))                         # no address on record counts as outside
            self.assertEqual(b.eval("[...document.querySelectorAll('#deInc [data-deit]')].filter(i=>i.checked).length"), 0)
            b.eval("document.getElementById('deDlg').close()")

    def test_the_followup_from_the_meeting_page_reads_attendees_and_summary_from_the_server(self):
        b = self.b
        (self.v.root / f"{ABC}/minutes/{TODAY} ABC weekly.md").write_text("## Summary\n\nThe pilot is extended.\n\n## Actions\n")
        (self.v.root / "system/staging/calendar.json").write_text(json.dumps({"days": {TODAY: [{"id": "e9", "start": "09:00", "end": "10:00",
            "title": "ABC weekly", "attendees": [{"name": "Sara Example", "email": "sara@example.com"}]}]}}))
        b.eval(f"""D.hub={{tk1:{{key:'calendar:e9',eid:'e9',title:'ABC weekly',day:TODAY,start:'09:00',p:['ABC'],steps:[],counts:{{}},promised:[],coverage:[],
            files:['{ABC}/minutes/{TODAY} ABC weekly.md'],items:[{{k:'actions',id:'ABC-A-006',state:'Open'}},{{k:'actions',id:'ABC-A-007',state:'Open'}},
            {{k:'decisions',id:'ABC-D-009',state:'Made'}}]}}}}; openFollowup('tk1')""")
        b.wait("DE&&DE.attendees.length===1", 20)
        self.assertEqual(b.eval("DE.summary"), "The pilot is extended.")
        ids = b.eval("[...document.querySelectorAll('#deInc [data-deit]')].map(i=>i.dataset.deit)")
        self.assertNotIn("actions:ABC-A-007", ids)                           # confidential: never offered
        self.assertIn("sara@example.com", b.eval("document.getElementById('deTo').textContent"))
        self.assertTrue(b.eval("DE.outside"))                                # example.com isn't one of the own domains
        self.assertEqual(b.errors, [])


class Polish(EmailCase):
    def test_polish_rewords_the_opening_only_and_use_puts_it_in_the_email(self):
        b = self.b
        b.eval("openDraftEmail('Sara Example','chase')")
        b.wait("document.querySelector('#deDlg [data-depolish]')")
        b.eval("document.querySelectorAll('#deInc [data-deit]').forEach(i=>{ if(!i.checked) i.click(); })")
        b.click('#deDlg [data-detone="firm"]')
        b.click("#deDlg [data-depolish]")
        b.wait("document.querySelector('#dePolish .drcard')", 30)
        p = drafts_fake.prompt(self.fake)
        self.assertIn("in a firm tone", p)
        self.assertIn("A quick reminder about the items below", p)                       # the chase's own opening
        self.assertNotIn("ABC-A-006", p)                                    # the table never goes to the model
        self.assertNotIn("Send the test plan", p)
        b.click("#dePolish [data-depo=use]")
        b.wait("document.getElementById('dePrev').textContent.includes('A gentle nudge on the items below')")
        self.assertIn("ABC-A-006", b.eval("document.getElementById('dePrev').textContent"))
        for _ in range(50):
            if (self.stats().get("email") or {}).get("used") == 1:
                break
            time.sleep(0.1)
        self.assertEqual(self.stats()["email"]["offered"], 1)
        self.assertEqual(self.stats()["email"]["used"], 1)

    def test_polish_off_greys_the_row_and_says_why(self):
        """BL-290: with Polish off the row stays, its tone chips disabled and the Polish button greyed with the reason."""
        b = self.b
        try:
            b.eval("S.drafting={...(S.drafting||{}),email:false}; openDraftEmail('Sara Example','chase')")
            b.wait("document.getElementById('deDlg').open&&document.querySelector('#deBody .deopts')")
            self.assertTrue(b.eval("!!document.querySelector('#deDlg .detone')"), "the Polish row is kept")
            btn = "document.querySelector('#deDlg [data-depolish]')"
            self.assertEqual(b.eval(f"{btn}.getAttribute('aria-disabled')"), "true")
            self.assertIn("is off in Settings › Advanced › AI drafts", b.eval(f"{btn}.dataset.tip"))
            self.assertTrue(b.eval("[...document.querySelectorAll('#deDlg [data-detone]')].every(x=>x.disabled)"))
            b.click("#deDlg [data-depolish]")
            b.pump(0.3)
            self.assertIsNone(b.eval("document.querySelector('#dePolish .drcard,#dePolish .drstatus')"))
        finally:
            b.eval("S.drafting={...(S.drafting||{}),email:true}; document.getElementById('deDlg').close()")

    def test_a_confidential_paragraph_is_refused(self):
        reply, _ = self.draft({"kind": "polish", "text": "About the restricted board pack.", "tone": "warm"})
        self.assertIn("confidential or restricted", reply["message"])


if __name__ == "__main__":
    unittest.main()
