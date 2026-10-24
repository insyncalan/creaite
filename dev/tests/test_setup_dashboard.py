"""BL-166 (sprint-polish-2): set-up in the dashboard where it can be.

Run: python3 dev/tests/test_setup_dashboard.py   (the browser cases need Google Chrome; skipped otherwise)

The live server's /api/setup/run runs only fixed steps (the health check, doctor.py; Rebuild, build_dashboard.py and the Excel
export), each only if ask creaite's existing allow list already permits that exact command; the launcher (launch.py, on no
allow list) and Microsoft 365 (connected in Claude) stay as Copy and Check again. Settings › System › Set-up and the first-run
checklist use them. Nothing here changes a permission: .claude/settings.json and the allow lists are untouched.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_tracker import Vault  # noqa: E402

PROBE = r'''
import json, sys
sys.path.insert(0, "system/scripts")
import live_server as L
calls = []
L.run = lambda *a: (calls.append(list(a)), (0, "PASS  x\n1 passed, 0 failed." if a[0] == "doctor.py" else "No unimported edits." if a[1:] == ("changed",) else "ok"))[1]
class H:
    def send(self, code, body): self.out = (code, body)
out = {}
for step in sys.argv[1:]:
    h = H(); calls.clear(); L.setup_run_route(h, {"step": step}); out[step] = {"code": h.out[0], "body": h.out[1], "calls": list(calls)}
out["allowed"] = {k: L.setup_allowed(c, t) for k, c, t in [("doctor", ["doctor.py"], "read"), ("build-as-read", ["build_dashboard.py"], "read"),
    ("build", ["build_dashboard.py"], "write"), ("export", ["excel_sync.py", "export"], "write"), ("launcher", ["launch.py", "make-launcher"], "write"),
    ("permissions", ["permissions.py", "projects-root"], "write"), ("setting", ["propose.py", "setting", "x"], "write"), ("server", ["live_server.py"], "write")]}
print(json.dumps(out))
'''


class Routes(unittest.TestCase):
    """The routes, called in-process with the script runner recorded: each step runs only its own commands."""

    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        populate(cls.v)

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def probe(self, *steps):
        r = subprocess.run([sys.executable, "-c", PROBE, *steps], cwd=self.v.root, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def test_each_step_runs_only_its_script(self):
        out = self.probe("health", "rebuild")
        self.assertEqual(out["health"]["calls"], [["doctor.py"]])
        self.assertTrue(out["health"]["body"]["passed"])
        self.assertEqual(out["rebuild"]["calls"], [["build_dashboard.py"], ["excel_sync.py", "changed"], ["excel_sync.py", "export"]])
        self.assertIn("Dashboard rebuilt.", out["rebuild"]["body"]["message"])

    def test_anything_else_is_refused_and_nothing_runs(self):
        out = self.probe("launcher", "doctor.py", "../x", "")
        for k in ("launcher", "doctor.py", "../x", ""):
            self.assertEqual(out[k]["code"], 400, k)
            self.assertEqual(out[k]["calls"], [], k)

    def test_only_what_the_allow_list_already_permits(self):
        a = self.probe()["allowed"]
        self.assertEqual(a, {"doctor": True, "build-as-read": False, "build": True, "export": True, "launcher": False,
                             "permissions": False, "setting": True, "server": False})

    def test_the_real_routes_through_the_server(self):
        """The real scripts: the health check prints doctor's lines; Rebuild rewrites the dashboard and exports Excel."""
        r = subprocess.run([sys.executable, "-c", PROBE.replace("L.run = lambda", "_unused = lambda"), "health", "rebuild"],
                           cwd=self.v.root, capture_output=True, text=True, timeout=240)
        out = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertTrue(any(ln.startswith("PASS") for ln in out["health"]["body"]["lines"]))
        self.assertTrue(out["rebuild"]["body"]["ok"], out["rebuild"]["body"])
        self.assertTrue((self.v.root / "dashboard.html").exists())
        self.assertTrue((self.v.root / "tracker-view.xlsx").exists())


class Page(LiveBrowserCase):
    shared_server = False

    @classmethod
    def server_env(cls):
        cls.home = Path(tempfile.mkdtemp(prefix="creaite-home-"))
        return {"HOME": str(cls.home)}

    def tearDown(self):
        super().tearDown()
        shutil.rmtree(self.home, ignore_errors=True)

    def clip(self):
        self.b.eval("window.CLIP=[]; navigator.clipboard.writeText=t=>{ CLIP.push(t); return Promise.resolve(); }")

    def open_setup(self):
        b = self.b
        b.eval("go('settings','setup')")
        b.wait("document.getElementById('suCard') && SU.status")
        b.pump(0.3)

    def test_the_health_check_runs_from_the_page(self):
        self.open_setup()
        self.b.click("#suHealth")
        self.b.wait("SU.health && document.querySelector('#suCard .sures')", 90)
        self.assertRegex(self.b.eval("document.querySelector('#suCard [role=status]').textContent"), r"\d+ passed, \d+ failed\.")

    def test_rebuild_is_shown_first_and_runs_on_the_click(self):
        b = self.b
        self.open_setup()
        before = (self.v.root / "dashboard.html").stat().st_mtime if (self.v.root / "dashboard.html").exists() else 0
        b.click("#suRebuild")
        self.assertIn("Excel view", b.eval("document.getElementById('suConfirm').textContent"))
        b.click("[data-sucancel]")
        self.assertFalse(b.eval("!!document.getElementById('suConfirm')"))
        b.click("#suRebuild")
        b.click("#suRebuildGo")
        b.wait("/Dashboard rebuilt/.test(document.getElementById('snackT').textContent)", 120)
        self.assertGreater((self.v.root / "dashboard.html").stat().st_mtime, before)

    def test_microsoft_365_copy_and_check_again(self):
        b = self.b
        self.open_setup()
        self.assertFalse(b.eval("!!document.querySelector('#suCard [data-sucopy=\"m365\"]')"), "#291: no typed command on the page")
        b.click('#suCard [data-sucheck="m365"]')
        b.wait("/Not confirmed yet/.test(document.getElementById('snackT').textContent)", 10)
        (self.v.root / "system/staging/last-sweep.txt").write_text("2026-10-10 07:05\n", encoding="utf-8")   # the first sweep has run
        b.click('#suCard [data-sucheck="m365"]')
        b.wait("/is connected/.test(document.getElementById('snackT').textContent)", 10)
        b.wait("document.querySelector('#suCard').textContent.includes('Connected')", 5)
        self.assertFalse(b.eval("!!document.querySelector('#suCard [data-sucheck=\"m365\"]')"))

    def test_the_launcher_copy_and_check_again(self):
        b = self.b
        self.open_setup()
        self.clip()
        b.click('#diagCard [data-sucopy="launch"]')           # #291 Tier 1: the one step to type lives in Diagnostics
        b.wait("CLIP.length")
        self.assertTrue(b.eval("CLIP[0]").endswith("&& python3 system/scripts/launch.py make-launcher"))
        self.assertIn(str(self.v.root.resolve()).replace("/private", ""), b.eval("CLIP[0]").replace("/private", ""))
        b.click('#suCard [data-sucheck="launch"]')
        b.wait("/No launcher yet/.test(document.getElementById('snackT').textContent)", 10)
        (self.home / "Applications/creaite.app").mkdir(parents=True)                          # as make-launcher leaves it
        b.click('#suCard [data-sucheck="launch"]')
        b.wait("/launcher is made/.test(document.getElementById('snackT').textContent)", 10)
        self.assertIn("~/Applications/creaite.app", b.eval("document.getElementById('suCard').textContent"))

    def test_the_checklist_row_has_copy_and_check_again(self):
        b = self.b
        b.eval("go('today')")
        b.wait("document.querySelector('#setupList [data-sucheck=\"m365\"]')")
        self.assertFalse(b.eval("!!document.querySelector('#setupList [data-sucopy]')"), "#291: no typed command on Today")
        self.assertIn("can’t", b.eval("document.querySelector('#setupList li').textContent"))
        (self.v.root / "system/staging/last-sweep.txt").write_text("2026-10-10 07:05\n", encoding="utf-8")
        b.click('#setupList [data-sucheck="m365"]')
        b.wait("[...document.querySelectorAll('#setupList li')].some(li=>li.classList.contains('done')&&/Microsoft 365/.test(li.textContent))", 10)
        # the row above just changed: wait until the link has stopped moving; a redraw between press and release can lose the click
        # (logged under load: still on #today after 5 s, no page error), so press again (click_until: up to 3 presses, 15 s)
        b.click_until('#setupList [data-setopen="setup"]', "VIEW==='settings' && document.getElementById('suCard')", timeout=15, exact=True)


if __name__ == "__main__":
    unittest.main()
