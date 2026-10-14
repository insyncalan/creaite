"""BL-206: Close the day.

Run: python3 dev/tests/test_close_day.py   (the browser half needs Google Chrome; skipped otherwise)
The clock is fixed to Friday 16-10-2026 17:30, so "tomorrow" is Monday 19-10-2026 (the next working day). The fixture day closes
an action and records a decision, and leaves an action Alan owns waiting in Review. Monday has two meetings, one with a prep page.
Closing writes only system/staging/day-closed.json; nothing reaches the tracker and nothing is sent.
"""
import json
import os
import sqlite3
import subprocess
import sys
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_tracker import ABC, Vault  # noqa: E402

NOW = "2026-10-16 17:30"
ENV = {**os.environ, "CREAITE_NOW": NOW}
PREP = ABC + "/agendas/2026-10-19 ABC Steering prep.html"


def load(v):
    populate(v)
    st = v.root / "system/staging"
    v.propose("today", [{"n": 1, "op": "update", "table": "actions", "id": "ABC-A-002", "changes": {"status": "Closed", "closed": "2026-10-16"},
                         "decision": "approved"},
                        {"n": 2, "op": "new", "table": "decisions", "values": {"project": "ABC", "decision": "Keep the pilot scope", "made_by": "Alan Carter",
                                                                               "date": "2026-10-16", "source": "s"}, "match": "strong", "flags": [], "decision": "approved"}])
    v.run("apply")
    with closing(sqlite3.connect(v.root / "system/tracker.db")) as con:
        last = con.execute("SELECT max(apply_id) FROM applies").fetchone()[0]
        con.execute("UPDATE change_log SET at = '2026-10-16 15:00:00' WHERE apply_id = ?", (last,))
        con.commit()
    p = v.propose("waiting", [{"n": 1, "op": "new", "table": "actions", "values": {"project": "ABC", "description": "Send Sara the revised plan",
                                                                                 "owner": "Alan Carter", "raised": "2026-10-16", "source": "s"},
                               "match": "strong", "flags": [], "decision": "pending"}])
    data = json.loads(p.read_text())
    data["created"] = "2026-10-16T11:00:00"
    p.write_text(json.dumps(data))
    (st / "calendar.json").write_text(json.dumps({"fetched": "2026-10-16 07:00", "days": {
        "2026-10-17": [{"id": "w1", "start": "10:00", "end": "11:00", "title": "Saturday thing"}],
        "2026-10-19": [{"id": "m1", "start": "10:00", "end": "11:00", "title": "ABC Steering", "teams": True},
                       {"id": "m2", "start": "14:00", "end": "14:30", "title": "ABC Design review", "teams": True}]}}))
    (v.root / ABC / "agendas").mkdir(parents=True, exist_ok=True)
    (v.root / PREP).write_text("<html></html>")
    (st / "prep-pages.json").write_text(json.dumps({PREP: {"sha": "x", "key": "2026-10-19|10:00|ABC Steering", "day": "2026-10-19", "at": "2026-10-16 09:00"}}))
    (st / "day-closed.json").write_text(json.dumps({"days": {"2026-10-15": "18:10"}}))
    cfg = v.root / "system/config/settings.json"                    # BL-295: no catch-up sweep in this test (no stand-in Claude)
    s = json.loads(cfg.read_text())
    s.setdefault("day", {})["catchup_sweep"] = "off"
    cfg.write_text(json.dumps(s, indent=2))
    subprocess.run([sys.executable, str(v.root / "system/scripts/build_dashboard.py")], cwd=v.root, env=ENV, capture_output=True)


def day(v):
    r = subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts')\nimport build_dashboard as b\n"
                        "print(json.dumps(b.collect()['day']))"], cwd=v.root, capture_output=True, text=True, env=ENV)
    return json.loads(r.stdout.strip().splitlines()[-1])


class CloseData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        load(cls.v)
        cls.d = day(cls.v)

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def test_the_days_counts(self):
        self.assertEqual(self.d["moved"]["closed"], 1)
        self.assertEqual(self.d["moved"]["decisions"], 1)
        self.assertEqual(self.d["moved"]["applied"], 2)

    def test_today_s_promises_are_the_actions_you_own_still_waiting(self):
        self.assertEqual([p["t"] for p in self.d["promised"]], ["Send Sara the revised plan"])

    def test_a_friday_skips_the_weekend_and_lists_the_missing_prep_page(self):
        tm = self.d["tomorrow"]
        self.assertEqual(tm["day"], "2026-10-19")
        self.assertEqual([(m["title"], m["prep"]) for m in tm["meetings"]], [("ABC Steering", True), ("ABC Design review", False)])
        self.assertTrue(self.d["friday"])

    def test_the_last_closed_day_and_the_nudge_from_17_30_by_default(self):
        self.assertEqual(self.d["last"], {"day": "2026-10-15", "at": "18:10"})
        self.assertIsNone(self.d["closed"])
        self.assertIsNone(self.d["from"])                 # this vault's settings have no close_from: no nudge
        defaults = json.loads((Path(__file__).resolve().parents[2] / "system/templates/settings-defaults.json").read_text())
        self.assertEqual(defaults["day"]["close_from"], "17:30")       # BL-320 (Alan, 14-10-2026): the accepted mockup's default


class CloseBrowser(LiveBrowserCase):
    shared_server = False

    @classmethod
    def load(cls, v):
        load(v)

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": NOW}

    def tracker(self):
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            return [con.execute(f"SELECT * FROM {t} ORDER BY 1").fetchall() for t in ("actions", "raid", "decisions", "change_log")]

    def test_the_card_closes_the_day_and_writes_only_the_record(self):
        # BL-295: the card is now a guided shutdown in four steps (test_close_day_card has the rest); the catch-up sweep is off here
        b = self.b
        before = self.tracker()
        staged = sorted(p.name for p in (self.v.root / "system/staging").glob("proposed-*.json"))
        b.eval("go('today')")
        b.wait("document.querySelector('#dayClose[data-dclose]')")      # BL-270: a door icon at the band's bottom right
        self.assertIn("last closed", b.eval("document.getElementById('dayClose').getAttribute('aria-label')"))
        b.click("#dayClose")
        b.wait("document.getElementById('closeDlg').open")
        step = "document.querySelector('#closeDlg .cdsteps li[aria-current=step]')?.textContent"
        b.wait(f"{step}==='Today'")                                          # a quiet Catch up (off) is passed over
        text = b.eval("document.getElementById('closeDlg').textContent")
        for want in ("Moved today", "1 action closed", "1 decision recorded", "You promised today", "Send Sara the revised plan",
                     "Friday 16th October"):
            self.assertIn(want, text)
        self.assertTrue(b.eval("!!document.querySelector('#closeDlg [data-dcadd]')"))
        b.click("#closeDlg [data-cdnext]")
        b.wait(f"{step}==='Loose ends'")
        b.click("#closeDlg [data-cdnext]")
        b.wait(f"{step}==='Tomorrow'")
        text = b.eval("document.getElementById('closeDlg').textContent")
        for want in ("Monday 19th October", "the next working day", "Prep page made", "Make prep page", "Friday"):
            self.assertIn(want, text)
        b.click("#closeDlg [data-dcdone]")
        b.wait("/Day closed at/.test(document.getElementById('closeDlg').textContent)")
        b.wait("/Day closed at/.test(document.getElementById('dayClose').getAttribute('aria-label'))")
        self.assertTrue(b.eval("document.getElementById('dayClose').classList.contains('closed')"))
        rec = json.loads((self.v.root / "system/staging/day-closed.json").read_text())["days"]
        self.assertIn("2026-10-16", rec)
        self.assertEqual(self.tracker(), before)
        self.assertEqual(sorted(p.name for p in (self.v.root / "system/staging").glob("proposed-*.json")), staged)
        self.assertEqual(b.errors, [])

    def test_not_yet_leaves_it_open_and_cmdk_offers_it(self):
        b = self.b
        b.eval("openCk(); const i=document.getElementById('cmdkIn'); i.value='close the day'; i.dispatchEvent(new Event('input'))")
        b.wait("CK.length && CK[0].l==='Close the day'")
        b.key("Enter")
        b.wait("document.getElementById('closeDlg').open")
        b.wait("!!document.querySelector('#closeDlg [data-dcnot],#closeDlg [data-cdback]')")
        b.key("Escape")                                                       # Esc is Not yet
        b.wait("!document.getElementById('closeDlg').open")
        self.assertFalse((self.v.root / "system/staging/day-closed.json").read_text().count("2026-10-16"))


if __name__ == "__main__":
    unittest.main()
