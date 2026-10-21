"""#242 (v2.5.1, Alan 19-10-2026): dismiss a Health problem so it stops counting on the sidebar.

Run: python3 dev/tests/test_health_dismiss.py   (the browser part needs Google Chrome; skipped otherwise)

- health.health() leaves out each problem named in settings.json's health.dismissed (its check id and a hash of its detail), and
  lists it under `dismissed` with the reason and date; the count is the problems left.
- A changed detail (another file, another count) is a new problem: it comes back by itself.
- A failure or warning of the engine's own integrity (the database, the bundled libraries, write access…) or of what protects
  your data and privacy (vault not synced, assistant permissions, backups, extraction scope), and any crashed check, can't be
  dismissed: it stays, `dismissable` False with the reason, even when a dismissed entry names it.
- In the real dashboard (real live server, real doctor): Dismiss with a reason drops More's count by one and lists the problem
  under Dismissed (n) with its reason and date; it survives a reload (saved in settings.json, backed up and logged as every
  settings save); Restore brings it and the count back.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "system" / "scripts"))
import health  # noqa: E402
import settings_catalogue as sc  # noqa: E402

RESULT = {"read_only": True, "checks": [
    {"id": "fts5", "name": "SQLite full-text search (FTS5)", "status": "pass", "detail": "ok"},
    {"id": "online_only", "name": "Online-only files", "status": "warn", "detail": "3 files are online-only"},
    {"id": "people_register", "name": "People register", "status": "warn", "detail": "2 people have no email"},
    {"id": "projects_root", "name": "Projects folder reachable", "status": "fail", "detail": "~/OneDrive/Engagements is missing"},
    {"id": "database", "name": "tracker.db integrity", "status": "fail", "detail": "schema changed"}]}


def entry(check_id, detail, reason="", date="2026-10-19"):
    return {"id": check_id, "detail_key": health.problem_key(check_id, detail), "reason": reason, "date": date}


class Dismissed(unittest.TestCase):

    def test_nothing_dismissed_lists_every_problem_each_with_its_key(self):
        out = health.health(RESULT, dismissed=[])
        self.assertEqual([p["id"] for p in out["problems"]], ["projects_root", "database", "online_only", "people_register"])
        self.assertEqual(out["dismissed"], [])
        keys = {p["id"]: p["key"] for p in out["problems"]}
        self.assertEqual(keys["online_only"], health.problem_key("online_only", "3 files are online-only"))
        self.assertNotEqual(health.problem_key("online_only", "3 files"), health.problem_key("online_only", "4 files"))

    def test_a_dismissed_problem_leaves_the_count_and_is_listed_with_its_reason_and_date(self):
        out = health.health(RESULT, dismissed=[entry("online_only", "3 files are online-only", "OneDrive is fine, a known folder")])
        self.assertEqual([p["id"] for p in out["problems"]], ["projects_root", "database", "people_register"])
        self.assertEqual(len(out["dismissed"]), 1)
        d = out["dismissed"][0]
        self.assertEqual((d["id"], d["title"], d["reason"], d["date"]),
                         ("online_only", "Some project files are online-only", "OneDrive is fine, a known folder", "2026-10-19"))
        self.assertEqual(d["key"], health.problem_key("online_only", "3 files are online-only"))

    def test_a_failure_that_is_not_the_engine_can_be_dismissed(self):
        out = health.health(RESULT, dismissed=[entry("projects_root", "~/OneDrive/Engagements is missing")])
        self.assertEqual([p["id"] for p in out["dismissed"]], ["projects_root"])

    def test_a_changed_detail_brings_it_back(self):
        out = health.health(RESULT, dismissed=[entry("online_only", "2 files are online-only")])
        self.assertIn("online_only", [p["id"] for p in out["problems"]])
        self.assertEqual(out["dismissed"], [])

    def test_the_engines_own_integrity_can_not_be_dismissed(self):
        out = health.health(RESULT, dismissed=[entry("database", "schema changed")])
        p = {x["id"]: x for x in out["problems"]}
        self.assertIn("database", p)
        self.assertEqual(out["dismissed"], [])
        self.assertFalse(p["database"]["dismissable"])
        self.assertIn("can't be dismissed", p["database"]["keep_why"])
        self.assertTrue(p["online_only"]["dismissable"])
        self.assertEqual(p["online_only"]["keep_why"], "")
        # a warning from the same check is the engine's too: it can't be dismissed either (#242 review)
        warn = {"checks": [{"id": "database", "name": "tracker.db integrity", "status": "warn", "detail": "old schema"}]}
        self.assertFalse(health.health(warn, dismissed=[])["problems"][0]["dismissable"])

    # ---- #242 review (v2.5.1): what protects data or privacy can never be dismissed, fail or warn, nor a crashed check ----
    SAFETY = ("vault_not_synced", "assistant_permissions", "backup_check", "offsite_backup", "extraction_scope")

    def _result(self, check_id, status, detail):
        return {"read_only": True, "checks": [
            {"id": check_id, "name": check_id, "status": status, "detail": detail},
            {"id": "tidy_up", "name": "Tidy up", "status": "warn", "detail": "has not run for a week"}]}

    def _assert_kept(self, check_id, status, detail, **extra):
        res = self._result(check_id, status, detail)
        res["checks"][0].update(extra)
        out = health.health(res, dismissed=[entry(check_id, detail, "hand-written")])
        label = f"{check_id}/{status}"
        p = {x["id"]: x for x in out["problems"]}
        self.assertIn(check_id, p, label)
        self.assertFalse(p[check_id]["dismissable"], label)
        self.assertIn("can't be dismissed", p[check_id]["keep_why"], label)
        self.assertEqual([d["id"] for d in out["dismissed"]], [], label)
        self.assertTrue(p["tidy_up"]["dismissable"], label)          # the control: an ordinary problem still may be

    def test_each_safety_check_can_not_be_dismissed_as_a_failure_or_a_warning(self):
        for check_id in self.SAFETY:
            for status in ("fail", "warn"):
                with self.subTest(check=check_id, status=status):
                    self._assert_kept(check_id, status, f"{check_id} has a problem")

    def test_a_crashed_check_can_not_be_dismissed_whatever_its_id(self):
        for check_id in ("online_only", "people_register", "projects_root", "a_check_that_does_not_exist_yet"):
            with self.subTest(check=check_id):
                self._assert_kept(check_id, "fail", "TypeError: 'NoneType' object is not subscriptable", crashed=True)
                self._assert_kept(check_id, "fail", "OSError: [Errno 13] Permission denied")        # an older doctor's result

    def test_doctor_marks_a_crashing_check(self):
        import doctor
        n, as_json, doctor.AS_JSON = len(doctor.found), doctor.AS_JSON, True

        def broken():
            raise TypeError("boom")
        try:
            doctor.check("Broken", broken)
            self.assertTrue(doctor.found[-1].get("crashed"))
            self.assertEqual(doctor.found[-1]["status"], "fail")
            doctor.check("Fine", lambda: (False, "an ordinary failure"))
            self.assertFalse(doctor.found[-1].get("crashed"))
        finally:
            doctor.AS_JSON = as_json
            del doctor.found[n:]
            del doctor.results[n:]

    def test_an_ordinary_failure_that_mentions_an_error_word_is_still_dismissable(self):
        res = self._result("online_only", "warn", "Error handling folder is missing")
        self.assertTrue(health.health(res, dismissed=[])["problems"][0]["dismissable"])

    def test_the_count_includes_the_problems_that_can_not_be_dismissed(self):
        res = {"read_only": True, "checks": [
            {"id": c, "name": c, "status": "warn", "detail": "x"} for c in self.SAFETY]}
        out = health.health(res, dismissed=[entry(c, "x") for c in self.SAFETY])
        self.assertEqual(len(out["problems"]), 5)          # what More's badge and the headline count (len of problems)
        self.assertEqual(out["dismissed"], [])

    def test_a_damaged_or_odd_list_is_ignored_not_fatal(self):
        for bad in (None, "x", [1, "a", {"id": "online_only"}, {"detail_key": 3}]):
            out = health.health(RESULT, dismissed=bad)
            self.assertEqual(len(out["problems"]), 4, bad)

    def test_it_reads_the_saved_setting_when_none_is_passed(self):
        saved = {"health": {"dismissed": [entry("people_register", "2 people have no email", "known")]}}
        orig = health.paths.load_settings
        health.paths.load_settings = lambda: saved
        try:
            out = health.health(RESULT)
        finally:
            health.paths.load_settings = orig
        self.assertEqual([p["id"] for p in out["dismissed"]], ["people_register"])

    def test_the_setting_is_in_the_defaults_and_the_catalogue(self):
        self.assertEqual(sc.defaults()["health"]["dismissed"], [])
        self.assertIn("health.dismissed", sc.CATALOGUE)
        self.assertEqual(sc.tier_of("health.dismissed"), sc.ADVANCED)


class DismissInTheDashboard(LiveBrowserCase):
    """The real live server (doctor run read only) and the real dashboard."""

    @classmethod
    def load(cls, v):
        super().load(v)
        # one warning to dismiss: #252 retired the zz Archive warning this test used; an unknown logging.level is a plain warning
        f = v.root / "system/config/settings.json"
        cfg = json.loads(f.read_text(encoding="utf-8"))
        cfg.setdefault("logging", {})["level"] = "loud"
        f.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")

    def open_health(self):
        self.b.eval("go('settings','health')")
        self.b.wait("!!document.querySelector('#healthCard .hsum')", timeout=180)

    def rows(self):
        return self.b.eval("[...document.querySelectorAll('#healthCard .hlist[aria-label=\"What needs you\"] .hrow')].map(r=>r.dataset.check)")

    def badge(self):
        return self.b.eval("healthCount.value")

    def test_dismiss_then_restore_with_the_count_and_a_reload(self):
        self.open_health()
        before = self.rows()
        self.assertGreater(len(before), 0, "the test vault has no problem to dismiss")
        n = self.badge()
        self.assertEqual(n, len(before))
        target = self.b.eval("[...document.querySelectorAll('#healthCard .hrow[data-check]')].find(r=>r.querySelector('.hdismiss'))?.dataset.check")
        self.assertTrue(target, "no problem offers Dismiss")
        row = f"document.querySelector('#healthCard .hrow[data-check={target}]')"
        self.b.eval(f"{row}.querySelector('.hdismiss').click()")
        self.b.wait(f"!!{row}.querySelector('input.hreason')")
        self.b.eval(f"(()=>{{ const i={row}.querySelector('input.hreason'); i.value='Known, and fine for now'; i.dispatchEvent(new Event('input',{{bubbles:true}})); }})()")
        self.b.eval(f"{row}.querySelector('.hdismissgo').click()")
        self.b.wait(f"healthCount.value==={n - 1}")
        self.assertNotIn(target, self.rows())
        self.b.wait("!!document.querySelector('#healthDismissed')")
        self.assertIn(f"Dismissed ({1})", self.b.eval("document.querySelector('#healthDismissed summary').textContent"))
        self.b.eval("document.querySelector('#healthDismissed').open=true")
        text = self.b.eval(f"document.querySelector('#healthDismissed [data-check={target}]').textContent")
        self.assertIn("Known, and fine for now", text)
        self.assertRegex(text, r"\b\d{2}-\d{2}-\d{4}\b")          # the date, shown DD-MM-YYYY
        cfg = json.loads((self.v.root / "system/config/settings.json").read_text())
        saved = cfg["health"]["dismissed"]
        self.assertEqual([(d["id"], d["reason"]) for d in saved], [(target, "Known, and fine for now")])
        self.assertRegex(saved[0]["date"], r"^\d{4}-\d{2}-\d{2}$")
        log = (self.v.root / "system/config/settings-log.jsonl").read_text()
        self.assertIn('"key":"health.dismissed"', log.replace(" ", ""))
        # a reload: the server leaves it out by itself
        self.b.reload("typeof go==='function' && LIVE")
        self.open_health()
        self.assertNotIn(target, self.rows())
        self.assertEqual(self.badge(), n - 1)
        # Restore
        self.b.eval("document.querySelector('#healthDismissed').open=true")
        self.b.eval(f"document.querySelector('#healthDismissed [data-check={target}] .hrestorebtn').click()")
        self.b.wait(f"healthCount.value==={n}")
        self.assertIn(target, self.rows())
        self.assertFalse(self.b.eval("!!document.querySelector('#healthDismissed')"))
        cfg = json.loads((self.v.root / "system/config/settings.json").read_text())
        self.assertEqual(cfg["health"]["dismissed"], [])
        self.b.reload("typeof go==='function' && LIVE")
        self.open_health()
        self.assertIn(target, self.rows())
        self.assertEqual(self.badge(), n)


if __name__ == "__main__":
    unittest.main()
