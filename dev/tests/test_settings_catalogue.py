"""BL-320 (v192-settings-server): the settings catalogue, Reset and Health, server side.

Run: python3 dev/tests/test_settings_catalogue.py

- Every key in system/templates/settings-defaults.json has a catalogue entry (group, Essentials or Advanced, label, one line,
  the reason for its default), and every entry names a default key: this fails when a setting is added without one.
- "changed" is a value that differs from its default; Reset puts it back through the dashboard's own save path (a backup in
  system/backups/settings-<stamp>.json, the whole file, one settings-log.jsonl line per key) and refuses set-up-only keys.
- Health runs doctor read only (--read-only --json: no test files written) and lists only the problems, with the Fix it each
  would offer marked not built (guard decisions), the rest counted.
- The routes answer only with the page's token.
"""
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_dashboard import populate  # noqa: E402
from test_tracker import REPO, Vault  # noqa: E402

sys.path.insert(0, str(REPO / "system" / "scripts"))
import settings_catalogue as sc  # noqa: E402
import health  # noqa: E402
import health_fixes  # noqa: E402

PROBE = r'''
import json, sys
sys.path.insert(0, "system/scripts")
import settings_catalogue as sc
op, arg = sys.argv[1], json.loads(sys.argv[2])
if op == "reset":
    try:
        out = sc.reset(arg)
    except sc.ResetRefused as e:
        out = {"refused": str(e)}
else:
    out = sc.catalogue()
print(json.dumps(out))
'''


class Catalogue(unittest.TestCase):
    """The catalogue against settings-defaults.json, with no vault."""

    def setUp(self):
        self.flat = sc.flatten(sc.defaults())

    def test_every_default_key_has_an_entry_and_every_entry_a_default(self):
        self.assertEqual(sorted(set(self.flat) - set(sc.CATALOGUE)), [], "settings-defaults.json keys with no catalogue entry")
        self.assertEqual(sorted(set(sc.CATALOGUE) - set(self.flat)), [], "catalogue entries with no default")

    def test_each_entry_is_written_out(self):
        for key, (group, label, line, reason) in sc.CATALOGUE.items():
            self.assertIn(group, sc.GROUP_ORDER, key)
            for part in (label, line, reason):
                self.assertTrue(part.strip(), key)
            self.assertLessEqual(len(line), 140, key)

    def test_the_essentials_are_about_sixteen_rows_of_real_settings(self):
        self.assertTrue(14 <= len(sc.ESSENTIAL_ROWS) <= 24, len(sc.ESSENTIAL_ROWS))      # #97: two quiet-hours rows
        sections = []
        for section, label, line, keys in sc.ESSENTIAL_ROWS:
            sections.append(section)
            self.assertTrue(label and line and keys)
            for k in keys:
                self.assertIn(k, self.flat, k)
                self.assertEqual(sc.CATALOGUE[k][0], section, f"{k} sits in its Essentials row's section")
                self.assertNotIn(k, sc.FIXED, k)
        self.assertEqual(list(dict.fromkeys(sections)), ["You", "Your day", "Saving and review", "People I follow",
                                                         "Look and help", "Safety"])
        self.assertTrue({"sweep.due_from", "dashboard.theme", "backups.daily", "vip.check_minutes"} <=
                        {k for r in sc.ESSENTIAL_ROWS for k in r[3]})

    def test_the_sweep_lookback_cap_is_an_advanced_setting_with_its_reason(self):      # #146
        key = "sweep.max_lookback_days"
        self.assertEqual(self.flat[key], 3)
        self.assertEqual(sc.CATALOGUE[key][0], "Sweep")
        self.assertIn("three days", sc.CATALOGUE[key][3].lower())
        self.assertNotIn(key, {k for r in sc.ESSENTIAL_ROWS for k in r[3]})            # Advanced, not Essentials
        self.assertEqual(json.loads((REPO / "system/config/settings.json").read_text())["sweep"]["max_lookback_days"], 3)

    def test_fixed_keys_are_settings(self):
        self.assertTrue(set(sc.FIXED) <= set(sc.CATALOGUE))
        self.assertIn("locations.projects_root", sc.FIXED)

    def test_changed_compares_with_the_default(self):
        cfg = json.loads(json.dumps(sc.defaults()))
        cfg["sweep"]["due_from"] = "06:30"
        cfg["work"]["weekend_days"] = ["Sunday", "Saturday"]                 # the same days in another order: not a change
        del cfg["review"]["stale_after_days"]                                # missing: the default applies, not a change
        rows = {r["key"]: r for r in sc.catalogue(cfg)["settings"]}
        self.assertTrue(rows["sweep.due_from"]["changed"])
        self.assertEqual((rows["sweep.due_from"]["value"], rows["sweep.due_from"]["default"]), ("06:30", "07:00"))
        self.assertFalse(rows["work.weekend_days"]["changed"])
        self.assertFalse(rows["review.stale_after_days"]["changed"])
        self.assertEqual(rows["review.stale_after_days"]["value"], 7)
        self.assertEqual(rows["sweep.due_from"]["tier"], "essentials")
        self.assertEqual(rows["review.stale_after_days"]["tier"], "advanced")
        self.assertIn("sweep.ignore", rows)                                  # a list of rules is one setting
        self.assertIn("prep.series", rows)                                   # a map is one setting
        self.assertNotIn("vip._about", rows)


class InAVault(unittest.TestCase):
    """Reset in a real temporary vault, through the dashboard's save path."""

    def setUp(self):
        self.v = Vault()
        self.cfg = self.v.root / "system/config/settings.json"
        self.log = self.v.root / "system/config/settings-log.jsonl"

    def tearDown(self):
        self.v.cleanup()

    def probe(self, op, arg=None):
        r = subprocess.run([sys.executable, "-c", PROBE, op, json.dumps(arg)], cwd=self.v.root, capture_output=True, text=True,
                           timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def set(self, dotted, value):
        data = json.loads(self.cfg.read_text())
        o = data
        *head, last = dotted.split(".")
        for k in head:
            o = o.setdefault(k, {})
        o[last] = value
        self.cfg.write_text(json.dumps(data, indent=2) + "\n")

    def backups(self):
        return sorted((self.v.root / "system/backups").glob("settings-*.json"))

    def test_reset_writes_the_default_with_a_backup_and_a_log_line(self):
        self.set("sweep.due_from", "06:30")
        self.set("review.spot_check_every", 4)
        before_text, before_backups = self.cfg.read_text(), self.backups()
        cat = {r["key"]: r for r in self.probe("catalogue")["settings"]}
        self.assertTrue(cat["sweep.due_from"]["changed"] and cat["review.spot_check_every"]["changed"])
        out = self.probe("reset", ["sweep.due_from", "review.spot_check_every", "review.due_soon_days"])
        self.assertEqual(out, {"reset": ["sweep.due_from", "review.spot_check_every"], "unchanged": ["review.due_soon_days"]})
        data = json.loads(self.cfg.read_text())
        self.assertEqual((data["sweep"]["due_from"], data["review"]["spot_check_every"]), ("07:00", 10))
        self.assertTrue(self.cfg.read_text().endswith("}\n"))
        new = [b for b in self.backups() if b not in before_backups]
        self.assertEqual(len(new), 1)
        self.assertEqual(new[0].read_text(), before_text)                    # the file as it was before the reset
        self.assertRegex(new[0].name, r"^settings-\d{4}-\d{2}-\d{2}-\d{6}(-\d+)?\.json$")
        lines = [json.loads(x) for x in self.log.read_text().splitlines()[-2:]]
        self.assertEqual([(x["key"], x["old"], x["new"]) for x in lines],
                         [("sweep.due_from", "06:30", "07:00"), ("review.spot_check_every", 4, 10)])
        self.assertRegex(lines[0]["at"], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
        self.assertNotIn(" ", self.log.read_text().splitlines()[-1].split('"at":')[0])   # compact, as the page writes it
        cat = {r["key"]: r for r in self.probe("catalogue")["settings"]}
        self.assertFalse(cat["sweep.due_from"]["changed"])
        self.assertEqual(cat["sweep.due_from"]["last_changed"], lines[0]["at"])

    def test_reset_of_a_default_value_writes_nothing(self):
        before = (self.cfg.read_text(), self.backups(), self.log.read_text() if self.log.exists() else "")
        self.assertEqual(self.probe("reset", ["sweep.due_from"]), {"reset": [], "unchanged": ["sweep.due_from"]})
        self.assertEqual(before, (self.cfg.read_text(), self.backups(), self.log.read_text() if self.log.exists() else ""))

    def test_unknown_and_set_up_only_keys_are_refused_before_anything_is_written(self):
        self.set("sweep.due_from", "06:30")
        before = self.cfg.read_text()
        for keys in (["sweep.due_from", "no.such.key"], ["locations.projects_root"], ["vip._about"], ["live_mode.port"]):
            self.assertIn("refused", self.probe("reset", keys), keys)
        self.assertEqual(self.cfg.read_text(), before)


class Health(unittest.TestCase):
    """Health from doctor's checks: problems only, plain words, fixes not built; doctor --read-only writes nothing."""

    def test_problems_only_failures_first_with_unbuilt_fixes(self):
        result = {"read_only": True, "checks": [
            {"id": "fts5", "name": "SQLite full-text search (FTS5)", "status": "pass", "detail": "ok"},
            {"id": "offsite_backup", "name": "Off-laptop backup copy", "status": "warn", "detail": "no copy yet"},
            {"id": "launcher_vault", "name": "Launcher opens this vault", "status": "warn", "detail": f"{Path.home()}/x.app"},
            {"id": "database", "name": "tracker.db integrity", "status": "fail", "detail": "schema changed"},
            {"id": "brand_new_check", "name": "Something new", "status": "warn", "detail": "d"}]}
        out = health.health(result)
        self.assertEqual(out["fine"], 1)
        self.assertEqual([p["id"] for p in out["problems"]], ["database", "offsite_backup", "launcher_vault", "brand_new_check"])
        p = {x["id"]: x for x in out["problems"]}
        self.assertEqual(p["launcher_vault"]["title"], "Your launcher opens another vault")
        self.assertEqual(p["launcher_vault"]["detail"], "~/x.app")
        self.assertIn("make-launcher", p["launcher_vault"]["fix"]["would_run"])
        self.assertEqual(p["database"]["fix"]["kind"], "migrate")
        self.assertEqual(p["brand_new_check"]["title"], "Something new")     # a check Health doesn't know yet is still shown
        # BL-320 Fix it (health_fixes): "no copy yet" is mended by the built OneDrive fix; the launcher's detail here doesn't say
        # "opens another vault", so its fix stays the manual step, as every fix the guard decision doesn't cover
        self.assertEqual({k: x["fix"]["built"] for k, x in p.items()},
                         {"database": False, "offsite_backup": True, "launcher_vault": False, "brand_new_check": False})
        self.assertEqual((p["offsite_backup"]["fix"]["id"], p["offsite_backup"]["fix"]["button"]), ("offsite", "Make it now"))
        self.assertEqual([f["id"] for f in out["standalone"]], ["icon", "m365"])
        self.assertTrue(all(f["built"] for f in out["standalone"]))

    def test_every_doctor_check_has_plain_words(self):
        src = (REPO / "system/scripts/doctor.py").read_text()
        ids = re.findall(r'^\s+check\("[^"]+", (\w+)\)', src, re.M)
        self.assertGreater(len(ids), 20)
        self.assertEqual([i for i in ids if i not in health.PLAIN and i not in ("refused_commands", "record_refusals",
                                                                                 "script_policy")], [])
        self.assertTrue(all(kind in health.FIXES for _, kind in health.PLAIN.values()))

    def test_doctor_read_only_writes_no_test_file(self):
        v = Vault()
        try:
            populate(v)
            history = v.root / "system/history"
            shutil.rmtree(history, ignore_errors=True)        # the usual run makes it while probing; a read-only one must not
            r = subprocess.run([sys.executable, str(v.root / "system/scripts/doctor.py"), "--read-only", "--json"], cwd=v.root,
                               capture_output=True, text=True, timeout=120)
            out = json.loads(r.stdout.strip().splitlines()[-1])
            self.assertTrue(out["read_only"])
            self.assertGreater(len(out["checks"]), 20)
            self.assertEqual({c["id"]: c["status"] for c in out["checks"]}["writable"], "pass")
            self.assertFalse(history.exists())
            plain = subprocess.run([sys.executable, str(v.root / "system/scripts/doctor.py")], cwd=v.root,
                                   capture_output=True, text=True, timeout=120)
            self.assertIn("passed,", plain.stdout)                           # the usual lines are unchanged
            self.assertRegex(plain.stdout, r"(?m)^(PASS|WARN|FAIL)  ")
            self.assertTrue(history.exists())
        finally:
            v.cleanup()


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Routes(unittest.TestCase):
    """The routes through a real live server: token-checked, catalogue, reset, health."""

    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        populate(cls.v)
        cls.port = free_port()
        cls.base = f"http://127.0.0.1:{cls.port}"
        cls.proc = subprocess.Popen([sys.executable, str(cls.v.root / "system/scripts/live_server.py")], stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL, env={**os.environ, "CREAITE_PORT": str(cls.port),
                                                                    "CREAITE_NO_LAUNCH": "1"})
        for _ in range(100):
            try:
                urllib.request.urlopen(cls.base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        html = urllib.request.urlopen(cls.base + "/", timeout=60).read().decode()
        cls.token = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)
        cls.v.cleanup()

    def post(self, path, body, token=True):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", **({"X-Creaite-Token": self.token} if token else {})})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            raw = e.read()
            e.close()
            try:
                return e.code, json.loads(raw or b"{}")
            except ValueError:
                return e.code, {}

    def test_no_token_no_answer(self):
        for path in ("/api/settings/catalogue", "/api/settings/reset", "/api/health"):
            code, _ = self.post(path, {"key": "sweep.due_from"}, token=False)
            self.assertIn(code, (401, 403), path)

    def test_catalogue_and_reset(self):
        code, cat = self.post("/api/settings/catalogue", {})
        self.assertEqual(code, 200)
        self.assertTrue(cat["ok"])
        self.assertEqual(len(cat["essentials"]), len(sc.ESSENTIAL_ROWS))
        self.assertEqual({r["key"] for r in cat["settings"]}, set(sc.CATALOGUE))
        cfg = self.v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text())
        data["vip"]["check_minutes"] = 5
        cfg.write_text(json.dumps(data, indent=2) + "\n")
        code, out = self.post("/api/settings/reset", {"key": "vip.check_minutes"})
        self.assertEqual((code, out["reset"]), (200, ["vip.check_minutes"]))
        self.assertEqual(json.loads(cfg.read_text())["vip"]["check_minutes"], 30)
        self.assertFalse({r["key"]: r for r in out["catalogue"]["settings"]}["vip.check_minutes"]["changed"])
        self.assertEqual(self.post("/api/settings/reset", {"key": "locations.projects_root"})[0], 403)
        self.assertEqual(self.post("/api/settings/reset", {})[0], 400)

    def test_health(self):
        code, out = self.post("/api/health", {})
        self.assertEqual(code, 200)
        self.assertTrue(out["ok"], out)
        self.assertTrue(out["read_only"])
        self.assertGreater(out["fine"], 10)
        self.assertTrue(all(p["severity"] in ("warn", "fail") for p in out["problems"]))
        self.assertTrue(all(p["fix"]["id"] in health_fixes.FIXES for p in out["problems"] if p["fix"]["built"]))
        self.assertEqual([f["id"] for f in out["standalone"]], ["icon", "m365"])
        self.assertEqual(list(self.v.root.rglob(".doctor-write-test")), [])


class SafeSettings(unittest.TestCase):
    """#146: ask creaite may change the sweep's lookback settings (live_server.SAFE_SETTINGS names the keys it may write)."""

    def test_the_sweep_lookback_settings_are_in_the_safe_list(self):
        text = (REPO / "system/scripts/live_server.py").read_text(encoding="utf-8")
        block = text[text.index("SAFE_SETTINGS = ("):].split(")" + chr(10), 1)[0]
        for key in ("sweep.first_run_lookback_days", "sweep.max_lookback_days"):
            self.assertIn(f'"{key}"', block)


if __name__ == "__main__":
    unittest.main()
