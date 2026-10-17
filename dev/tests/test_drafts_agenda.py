"""BL-223 (sprint-drafts-writing): draft the agenda and the invite text (POAD) from the Prep page.

Run: python3 dev/tests/test_drafts_agenda.py
The agenda is plain code (the Prep page's own selection, decisions first); a stand-in Claude (drafts_fake.py) words the POAD, so no
model is called. Nothing is sent and no invite is created: the only write is Save to Agendas, a file in the project's Agendas folder.
"""
import json
import subprocess
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import drafts_fake  # noqa: E402
from test_decisions_prep import prep_world  # noqa: E402
from test_drafts_update import DraftCase  # noqa: E402
from test_tracker import Vault  # noqa: E402
from test_dashboard import today as pinned_today  # noqa: E402

KEY = "09:00|ABC weekly"


def context(v, body):
    r = subprocess.run([sys.executable, "system/scripts/drafts.py", "context"], input=json.dumps(body), capture_output=True, text=True,
                       cwd=v.root)
    return json.loads(r.stdout)


def make_confidential(v):
    p = v.root / "system/staging/calendar.json"
    cal = json.loads(p.read_text())
    ev = cal["days"][pinned_today().isoformat()][0]
    ev.update({"sensitivity": "confidential", "body": "Board secret: the merger plan", "where": "Room 7"})
    p.write_text(json.dumps(cal))


class Agenda(unittest.TestCase):
    """The agenda in plain code: no model, no server."""

    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.cleanup)
        prep_world(self.v)

    def test_decisions_come_first_then_overdue_work_at_most_six_and_timed(self):
        ctx = context(self.v, {"kind": "agenda", "key": KEY})
        pts = ctx["extra"]["agenda"]
        kinds = [p["kind"] for p in pts]
        self.assertEqual(kinds[0], "decide")
        self.assertEqual(kinds, sorted(kinds, key=["decide", "work", "milestone", "carried"].index))
        self.assertLessEqual(len(pts), 6)
        self.assertTrue(pts[0]["point"].startswith("Decide: Extend the pilot by two weeks"))
        self.assertEqual(sum(p["minutes"] for p in pts), 60)                     # the 09:00 to 10:00 meeting
        self.assertEqual(pts[0]["at"], "09:00")
        self.assertIn("[S1] Decide: Extend the pilot", ctx["prompt"])
        self.assertIn("The invite says: Agenda: pilot extension", ctx["prompt"])
        self.assertEqual(ctx["extra"]["template"], "agenda-poad")

    def test_more_items_than_points_are_grouped_into_one(self):
        sys.path.insert(0, str(self.v.root / "system/scripts"))
        import drafts
        work = [{"id": f"ABC-A-{i:03d}", "text": f"Item {i}", "due": "2026-01-01", "_day": "2026-02-01", "owner": "Jane"} for i in range(9)]
        pts = drafts.allot([("decide", [{"id": "ABC-D-001", "text": "Choose", "type": "Decision needed"}]), ("work", work)])
        self.assertEqual(len(pts), 6)
        self.assertEqual(pts[-1]["point"], "Overdue and urgent work: 5 items (ABC-A-004, ABC-A-005, ABC-A-006, ABC-A-007, ABC-A-008)")

    def test_a_confidential_meeting_gives_only_its_title_and_times(self):
        make_confidential(self.v)
        ctx = context(self.v, {"kind": "agenda", "key": KEY})
        self.assertTrue(ctx["extra"]["confidential"])
        self.assertNotIn("Board secret", ctx["prompt"])
        self.assertNotIn("Room 7", ctx["prompt"])
        self.assertIn("ABC weekly, ", ctx["prompt"])
        self.assertIn("09:00–10:00", ctx["prompt"])

    def test_the_lighter_style_and_the_setting(self):
        self.assertEqual(context(self.v, {"kind": "agenda", "key": KEY, "style": "lite"})["extra"]["template"], "agenda-lite")
        s = json.loads((self.v.root / "system/config/settings.json").read_text())
        s.setdefault("drafting", {})["agenda_style"] = "lite"
        (self.v.root / "system/config/settings.json").write_text(json.dumps(s))
        self.assertEqual(context(self.v, {"kind": "agenda", "key": KEY})["extra"]["style"], "lite")

    def test_an_unknown_meeting_is_refused(self):
        self.assertIn("refused", context(self.v, {"kind": "agenda", "key": "23:59|No such meeting"}))


class AgendaCase(DraftCase):
    def wait_stat(self, feature, event, n):
        """The page counts without waiting for the server: poll draft-stats.json."""
        import time
        for _ in range(50):
            if (self.stats().get(feature) or {}).get(event) == n:
                return
            time.sleep(0.1)
        self.assertEqual((self.stats().get(feature) or {}).get(event), n)

    @classmethod
    def load(cls, v):
        prep_world(v)
        cls.fake = drafts_fake.install(v)

    def open_card(self):
        b = self.b
        b.eval("openPrep(prepTimed()[0],TODAY)")
        b.wait("document.querySelector('#prepDlg [data-agenda]')")
        b.click("#prepDlg [data-agenda]")                     # BL-286 B: a menu; POAD, the default style
        b.wait("document.querySelector('#prepDlg [data-agstyle=poad]')")
        b.click("#prepDlg [data-agstyle=poad]")
        b.wait("document.querySelector('#prepAgenda .drcard')", 30)


class AgendaInPrep(AgendaCase):
    def test_the_card_shows_the_poad_and_the_timed_agenda_and_copies_rich_and_plain(self):
        b = self.b
        before = (self.v.root / "system/tracker.db").read_bytes()
        staged = sorted((self.v.root / "system/staging").glob("proposed-*"))
        self.open_card()
        heads = b.eval("[...document.querySelectorAll('#prepAgenda .agparts h4')].map(h=>h.textContent)")
        self.assertEqual(heads, ["Purpose", "Objectives", "Approach", "Deliverables"])
        self.assertEqual(b.eval("document.querySelectorAll('#prepAgenda .drloose').length"), 1)     # "Decisions first…" has no source
        first = b.eval("document.querySelector('#prepAgenda .aglist li').textContent")
        self.assertIn("Decide: Extend the pilot by two weeks", first)
        b.eval("""window.__clip=[]; navigator.clipboard.write=async items=>{ for(const it of items) for(const t of it.types)
            window.__clip.push([t,await (await it.getType(t)).text()]); }; navigator.clipboard.writeText=async t=>{ window.__clip.push(['plain',t]); };""")
        b.click("#prepAgenda [data-agdo=copy]")
        b.wait("window.__clip.length===2")
        clip = dict(b.eval("window.__clip"))
        self.assertIn("<table", clip["text/html"])
        self.assertIn("<b style=\"font-weight:bold;\">Purpose</b>", clip["text/html"])
        self.assertTrue(clip["text/plain"].startswith("Purpose\nSettle the pilot extension before it lapses."))
        self.assertIn("Agenda\n09:00  Decide: Extend the pilot by two weeks", clip["text/plain"])
        self.assertNotIn("[S1]", clip["text/plain"])
        b.click("#prepAgenda [data-agdo=plain]")
        b.wait("window.__clip.length===3")
        self.assertEqual(b.eval("window.__clip[2][0]"), "plain")
        self.wait_stat("agenda", "used", 1)
        self.assertEqual(self.stats()["agenda"], {"offered": 1, "used": 1, "edited": 0, "rejected": 0})
        self.assertEqual((self.v.root / "system/tracker.db").read_bytes(), before)             # nothing written to the tracker
        self.assertEqual(sorted((self.v.root / "system/staging").glob("proposed-*")), staged)   # and nothing proposed
        self.assertEqual(b.errors, [])

    def test_save_to_agendas_writes_one_internal_file_and_never_overwrites(self):
        b = self.b
        self.open_card()
        b.click("#prepAgenda [data-agdo=save]")
        b.wait("/Saved: /.test(document.getElementById('agMsg').textContent)")
        b.click("#prepAgenda [data-agatt]")
        b.click("#prepAgenda [data-agdo=save]")
        b.wait("/\\(2\\)\\.md/.test(document.getElementById('agMsg').textContent)")
        files = {f.name[11:]: f.read_text() for f in self.v.root.glob("projects/**/*Agenda - ABC weekly*.md")}
        self.assertEqual(sorted(files), ["Agenda - ABC weekly (2).md", "Agenda - ABC weekly.md"])
        one, two = files["Agenda - ABC weekly.md"], files["Agenda - ABC weekly (2).md"]
        self.assertIn("Internal: not for sending as it is.", one)
        self.assertIn("For attendees.", two)
        self.assertIn("- Decide: Extend the pilot by two weeks", one)
        sys.path.insert(0, str(self.v.root / "system/scripts"))
        r = subprocess.run([sys.executable, "system/scripts/minutes.py", "agenda", "ABC", "--date", pinned_today().isoformat(),
                            "--title", "ABC weekly"], capture_output=True, text=True, cwd=self.v.root)
        self.assertIn("Extend the pilot by two weeks", r.stdout)                                   # Coverage reads it (BL-209)

    def test_discard_counts_a_rejection_and_the_lighter_style_has_one_part(self):
        b = self.b
        self.open_card()
        b.click("#prepAgenda [data-agdo=discard]")
        b.wait("!document.querySelector('#prepAgenda .drcard')")
        self.wait_stat("agenda", "rejected", 1)
        b.click("#prepDlg [data-agenda]")
        b.wait("document.querySelector('#prepDlg [data-agstyle=lite]')")
        b.click('#prepDlg [data-agstyle="lite"]')
        b.wait("document.querySelector('#prepAgenda .drcard')", 30)
        self.assertEqual(b.eval("document.querySelectorAll('#prepAgenda .agparts h4').length"), 1)
        b.click("#prepDlg [data-agenda]")                     # BL-286 B: the last style used is marked, and remembered
        b.wait("document.querySelector('#prepDlg [data-agstyle=lite]')")
        self.assertIn("last used", b.eval("document.querySelector('#prepDlg [data-agstyle=lite]').textContent"))
        self.assertNotIn("last used", b.eval("document.querySelector('#prepDlg [data-agstyle=poad]').textContent"))
        self.assertEqual(b.eval("localStorage.getItem('creaite-agenda-style')"), '"lite"')
        self.assertTrue(drafts_fake.prompt(self.fake).startswith("Write a short, friendly invite"))

    def test_the_button_is_off_with_the_setting(self):
        b = self.b
        b.eval("S.drafting={...(S.drafting||{}),agenda:false}; openPrep(prepTimed()[0],TODAY)")
        b.wait("document.querySelector('#prepDlg [data-agenda]')")
        self.assertEqual(b.eval("document.querySelector('#prepDlg [data-agenda]').getAttribute('aria-disabled')"), "true")


if __name__ == "__main__":
    unittest.main()
