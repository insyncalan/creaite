"""BL-86: creaite as an installable Chrome app, started by a launcher.

Run: python3 dev/tests/test_app_launcher.py   (the browser part needs Google Chrome; skipped otherwise)
Real servers on free ports in throwaway vaults, a stub browser for the launcher, and a stand-in `claude` for the not-mid-job
test. Nothing real is opened or touched.
"""
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase, free_port  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_tracker import Vault  # noqa: E402

SLOW_CLAUDE = r'''#!/usr/bin/env python3
import json, sys, time
print(json.dumps({"type": "system", "subtype": "init", "session_id": "sess-slow-1"}), flush=True)
time.sleep(6)
print(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "Done."}]}}), flush=True)
print(json.dumps({"type": "result", "session_id": "sess-slow-1", "result": "Done."}), flush=True)
'''
STUB_BROWSER = '#!/bin/bash\necho "$@" >> "{log}"\n'


def get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def alive(port):
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1)
        return True
    except OSError:
        return False


def wait_until(fn, seconds=15, every=0.2):
    end = time.time() + seconds
    while time.time() < end:
        if fn():
            return True
        time.sleep(every)
    return False


class RoutesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        populate(cls.v)
        cls.port = free_port()
        cls.base = f"http://127.0.0.1:{cls.port}"
        cls.proc = subprocess.Popen([sys.executable, str(cls.v.root / "system/scripts/live_server.py")],
                                    env={**os.environ, "CREAITE_PORT": str(cls.port)}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        assert wait_until(lambda: alive(cls.port))
        html = get(cls.base + "/")[2].decode()
        cls.html = html
        cls.token = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)
        cls.v.cleanup()

    def test_the_manifest_describes_an_installable_app(self):
        status, headers, body = get(self.base + "/manifest.webmanifest")
        m = json.loads(body)
        self.assertEqual((status, headers["Content-Type"].split(";")[0]), (200, "application/manifest+json"))
        self.assertEqual((m["name"], m["start_url"], m["scope"], m["display"]), ("creaite", "/", "/", "standalone"))
        self.assertEqual(m["theme_color"], "#18181B")                                        # Stage's graphite (BL-272)
        got = {(i["sizes"], i["purpose"]) for i in m["icons"]}
        self.assertEqual(got, {("192x192", "any"), ("512x512", "any"), ("512x512", "maskable")})
        for i in m["icons"]:
            status, headers, png = get(self.base + i["src"])
            w, h = struct.unpack(">II", png[16:24])
            self.assertEqual((status, headers["Content-Type"].split(";")[0], f"{w}x{h}"), (200, "image/png", i["sizes"]))

    def test_the_icons_are_kept_in_templates_and_built_from_the_svg(self):
        repo = Path(__file__).resolve().parents[2]
        for n in ("icon-192.png", "icon-512.png", "icon-maskable-512.png", "sw.js", "offline.html"):
            self.assertTrue((repo / "system/templates/app" / n).is_file(), n)
        for n in ("creaite-icon-stage.svg", "creaite-icon-stage-small.svg"):                  # Stage (BL-272)
            self.assertTrue((repo / "dev/icon" / n).is_file(), n)
        for n, size in (("icon-192.png", 192), ("icon-512.png", 512), ("icon-maskable-512.png", 512), ("icon-dev-512.png", 512)):
            png = (repo / "system/templates/app" / n).read_bytes()
            self.assertEqual(struct.unpack(">II", png[16:24]), (size, size), n)

    def test_the_dashboard_links_the_manifest_and_a_theme_colour(self):
        self.assertIn('<link rel="manifest" href="/manifest.webmanifest">', self.html)
        self.assertRegex(self.html, r'<meta name="theme-color" content="#[0-9A-Fa-f]{6}">')
        self.assertIn('register("/sw.js")', self.html)
        self.assertIn("install the app again and reconnect the vault", self.html)             # the port note in Settings

    def test_the_service_worker_and_the_offline_page(self):
        status, headers, body = get(self.base + "/sw.js")
        self.assertEqual((status, headers["Content-Type"].split(";")[0], headers["Service-Worker-Allowed"]), (200, "text/javascript", "/"))
        self.assertIn('"/offline"', body.decode())
        status, headers, body = get(self.base + "/offline")
        page = body.decode()
        self.assertEqual(status, 200)
        for text in ("The live server isn't running", "launch.py", "Check again"):
            self.assertIn(text, page)
        self.assertNotIn("projects", page.lower().replace("projects folder", ""))              # no vault data in a static page

    def test_the_app_files_answer_only_this_machine(self):
        for path in ("/manifest.webmanifest", "/sw.js", "/offline", "/app/icon-192.png"):
            self.assertEqual(get(self.base + path, {"Host": "evil.example"})[0], 403, path)
        self.assertEqual(get(self.base + "/app/../system/tracker.db")[0], 404)
        self.assertEqual(get(self.base + "/app/nothing.png")[0], 404)

    def test_here_needs_the_token_and_stop_stops_a_server_started_by_hand(self):
        req = urllib.request.Request(self.base + "/api/here", data=b"{}", method="POST", headers={"Content-Type": "application/json"})
        with self.assertRaises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(req)
        self.assertEqual(e.exception.code, 403)
        body = json.loads(e.exception.read())               # a stale page says so, rather than "Not allowed"
        self.assertTrue(body["stale"])
        self.assertIn("Reload", body["message"])
        ok = urllib.request.Request(self.base + "/api/here", data=b"{}", method="POST",
                                    headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        self.assertEqual(json.loads(urllib.request.urlopen(ok).read()), {"ok": True, "launched": False})


class LauncherCase(unittest.TestCase):
    """launch.py in a throwaway vault, with a stub browser; the servers it starts use a short stop timer."""

    def setUp(self):
        self.v = Vault()
        populate(self.v)
        self.port = free_port()
        self.log = self.v.root / "browser.log"
        self.stub = self.v.root / "stub-browser.sh"
        self.stub.write_text(STUB_BROWSER.format(log=self.log))
        self.stub.chmod(0o755)
        slow = self.v.root / "slow_claude.py"
        slow.write_text(SLOW_CLAUDE)
        slow.chmod(0o755)
        self.env = {**os.environ, "CREAITE_PORT": str(self.port), "CREAITE_BROWSER": str(self.stub), "CREAITE_STOP_AFTER": "3",
                    "CREAITE_STOP_CHECK": "0.5", "CREAITE_CLAUDE": str(slow)}
        self.servers = []

    def tearDown(self):
        if alive(self.port):
            try:
                tok = self.token()
                urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{self.port}/api/stop", data=b"{}", method="POST",
                                                              headers={"Content-Type": "application/json", "X-Creaite-Token": tok}))
            except (OSError, ValueError):
                pass
        for p in self.servers:
            if p.poll() is None:
                p.terminate()
                p.wait(timeout=10)
        self.v.cleanup()

    def launch(self, *args, env=None, ok=None):
        r = subprocess.run([sys.executable, str(self.v.root / "system/scripts/launch.py"), *args], cwd=tempfile.gettempdir(),
                           env=env or self.env, capture_output=True, text=True, timeout=60)
        if ok is not None:
            self.assertEqual(r.returncode, ok, r.stdout + r.stderr)
        return r

    def calls(self, n=1):
        """What the stub browser was asked to open (it runs a moment after the launcher returns)."""
        wait_until(lambda: self.log.exists() and len(self.log.read_text().splitlines()) >= n, 5)
        return self.log.read_text().splitlines() if self.log.exists() else []

    def token(self):
        html = get(f"http://127.0.0.1:{self.port}/")[2].decode()
        return json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]

    def here(self, tok=None):
        tok = tok or self.token()
        urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{self.port}/api/here", data=b"{}", method="POST",
                                                      headers={"Content-Type": "application/json", "X-Creaite-Token": tok}))
        return tok

    def test_it_starts_the_server_and_opens_an_app_window(self):
        r = self.launch(ok=0)
        self.assertIn("Starting the live server", r.stdout)
        self.assertTrue(alive(self.port))
        self.assertEqual(self.calls(), [f"--app=http://127.0.0.1:{self.port}/"])
        # BL-212: /health names no vault; the launcher's own question tells this vault's server from another's
        self.assertEqual(json.loads(get(f"http://127.0.0.1:{self.port}/health")[2]), {"ok": True})
        self.assertNotIn(self.v.root.name, get(f"http://127.0.0.1:{self.port}/health")[2].decode())

    def test_a_running_server_is_reused_not_started_twice(self):
        self.launch(ok=0)
        pid = subprocess.run(["lsof", "-ti", f"tcp:{self.port}", "-sTCP:LISTEN"], capture_output=True, text=True).stdout.split()
        r = self.launch(ok=0)
        self.assertIn("already running", r.stdout)
        self.assertEqual(subprocess.run(["lsof", "-ti", f"tcp:{self.port}", "-sTCP:LISTEN"], capture_output=True, text=True).stdout.split(), pid)
        self.assertEqual(len(self.calls(2)), 2)                       # a second window, no second server

    def test_the_port_comes_from_settings_when_not_given(self):
        cfg = self.v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text())
        data["live_mode"]["port"] = self.port
        cfg.write_text(json.dumps(data))
        env = {k: v for k, v in self.env.items() if k != "CREAITE_PORT"}
        self.launch(env=env, ok=0)
        self.assertTrue(alive(self.port))
        self.assertIn(f"127.0.0.1:{self.port}", self.calls()[0])

    def test_another_vault_on_the_port_is_reported_not_taken_over(self):
        other = Vault()
        try:
            srv = subprocess.Popen([sys.executable, str(other.root / "system/scripts/live_server.py")],
                                   env={**os.environ, "CREAITE_PORT": str(self.port)}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.servers.append(srv)
            self.assertTrue(wait_until(lambda: alive(self.port)))
            r = self.launch(ok=1)
            self.assertIn("another creaite vault", r.stdout)
            self.assertFalse(self.log.exists())
        finally:
            for s in self.servers:
                s.terminate()
                s.wait(timeout=10)
            other.cleanup()

    def test_without_chrome_the_default_browser_opens_and_it_says_so(self):
        marker = self.v.root / "default-browser.log"
        opener = self.v.root / "opener.sh"
        opener.write_text(f'#!/bin/bash\necho "$@" >> "{marker}"\n')
        opener.chmod(0o755)
        env = {**self.env, "CREAITE_BROWSER": "/nonexistent/chrome", "BROWSER": f"{opener} %s"}
        r = self.launch(env=env, ok=0)
        self.assertIn("Chrome wasn't found", r.stdout)
        self.assertTrue(wait_until(lambda: marker.exists()))
        self.assertIn(f"http://127.0.0.1:{self.port}/", marker.read_text())
        self.assertFalse(self.log.exists())

    def test_a_server_it_started_stops_a_minute_after_the_window_closes_here_shortened(self):
        self.launch(ok=0)
        tok = self.token()                                                                 # opening the page counts as "here"
        for _ in range(4):                                                                 # open for about 4 seconds, past the 3-second timer
            time.sleep(1)
            self.here(tok)
        self.assertTrue(alive(self.port))
        self.assertTrue(wait_until(lambda: not alive(self.port), 10), "it should stop after the pings stop")
        self.assertIn("stopping the live server", (self.v.root / "system/staging/live-server.log").read_text())

    def test_it_never_stops_in_the_middle_of_a_job(self):
        self.launch(ok=0)
        tok = self.token()
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/ask", data=json.dumps({"message": "slow job"}).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": tok})
        started = time.time()
        resp = urllib.request.urlopen(req, timeout=30)                                     # the stand-in takes six seconds
        time.sleep(4.5)                                                                    # well past the 3-second timer, job still running
        self.assertTrue(alive(self.port), "the server must wait for the running job")
        body = resp.read().decode()
        self.assertIn("Done.", body)
        self.assertGreater(time.time() - started, 5.5)
        self.assertTrue(wait_until(lambda: not alive(self.port), 10), "…and stop once it has finished")

    def test_a_server_started_by_hand_never_stops_by_itself(self):
        srv = subprocess.Popen([sys.executable, str(self.v.root / "system/scripts/live_server.py")], env={**self.env}, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
        self.servers.append(srv)
        self.assertTrue(wait_until(lambda: alive(self.port)))
        time.sleep(5)                                                                      # no pings, well past the 3 seconds
        self.assertTrue(alive(self.port))
        self.launch(ok=0)                                                                  # the launcher reuses it and doesn't make it stop
        time.sleep(5)
        self.assertTrue(alive(self.port))

    def test_stop_in_settings_stops_it_but_not_mid_job(self):
        self.launch(ok=0)
        tok = self.token()
        stop = lambda: json.loads(urllib.request.urlopen(urllib.request.Request(  # noqa: E731
            f"http://127.0.0.1:{self.port}/api/stop", data=b"{}", method="POST",
            headers={"Content-Type": "application/json", "X-Creaite-Token": tok})).read())
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/ask", data=json.dumps({"message": "slow job"}).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": tok})
        resp = urllib.request.urlopen(req, timeout=30)
        self.here(tok)
        refused = stop()
        self.assertFalse(refused["ok"])
        self.assertIn("still running", refused["message"])
        resp.read()
        self.assertTrue(stop()["ok"])
        self.assertTrue(wait_until(lambda: not alive(self.port), 10))

    def test_make_launcher_makes_an_app_and_a_command_file(self):
        dest = Path(tempfile.mkdtemp(prefix="creaite-apps-"))
        self.addCleanup(shutil.rmtree, dest, True)          # BL-172 (sprint-polish-2)
        (self.v.root / ".creaite-dev").unlink(missing_ok=True)          # a live vault: creaite.app (BL-305)
        self.launch("make-launcher", "--dest", str(dest), ok=0)
        app = dest / "creaite.app"
        exe = app / "Contents/MacOS/creaite"
        self.assertTrue(os.access(exe, os.X_OK))
        self.assertIn("system/scripts/run launch.py", exe.read_text())                  # BL-237: through the wrapper
        self.assertNotIn(sys.executable, exe.read_text())                               # no Python baked in
        plist = (app / "Contents/Info.plist").read_text()
        self.assertIn("<string>creaite</string>", plist)
        if (app / "Contents/Resources/creaite.icns").exists():
            self.assertIn("CFBundleIconFile", plist)
        self.launch("make-launcher", "--where", "vault", "--dest", str(dest), ok=0)
        cmd = dest / "creaite.command"
        self.assertTrue(os.access(cmd, os.X_OK))
        self.assertIn("launch.py", cmd.read_text())
        self.assertEqual(self.launch("make-launcher", "--where", "elsewhere").returncode, 2)


    # ===== BL-305 (sprint-launch-apply): one launcher per vault =====
    def other_vault(self, dev):
        """A second throwaway vault: the development repository (dev) or a live vault."""
        w = Vault()
        self.addCleanup(w.cleanup)
        (w.root / ".creaite-dev").write_text("") if dev else (w.root / ".creaite-dev").unlink(missing_ok=True)
        return w

    def make(self, vault, dest, *extra):
        return subprocess.run([sys.executable, str(vault.root / "system/scripts/launch.py"), "make-launcher", "--dest", str(dest),
                               *extra], cwd=tempfile.gettempdir(), env=self.env, capture_output=True, text=True, timeout=60)

    def opens(self, app):
        return Path(re.search(r'^cd "(.+?)" && exec ', (app / "Contents/MacOS/creaite").read_text(), re.M).group(1))

    def test_the_live_vault_and_the_development_repository_make_two_launchers_side_by_side(self):
        dest = Path(tempfile.mkdtemp(prefix="creaite-apps-"))
        self.addCleanup(shutil.rmtree, dest, True)
        live, dev = self.other_vault(dev=False), self.other_vault(dev=True)
        self.assertEqual(self.make(live, dest).returncode, 0)
        r = self.make(dev, dest)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(sorted(a.name for a in dest.glob("*.app")), ["creaite (dev).app", "creaite.app"])   # neither replaced
        self.assertTrue(self.opens(dest / "creaite.app").samefile(live.root))
        self.assertTrue(self.opens(dest / "creaite (dev).app").samefile(dev.root))
        lp, dp = ((dest / n / "Contents/Info.plist").read_text() for n in ("creaite.app", "creaite (dev).app"))
        self.assertIn("<key>CFBundleDisplayName</key><string>creaite</string>", lp)
        self.assertIn("<key>CFBundleDisplayName</key><string>creaite (dev)</string>", dp)
        self.assertIn("<string>app.creaite.launcher</string>", lp)
        self.assertIn("<string>app.creaite.launcher.dev</string>", dp)       # two apps to macOS, not one
        icons = [dest / n / "Contents/Resources/creaite.icns" for n in ("creaite.app", "creaite (dev).app")]
        if all(i.exists() for i in icons):                                              # sips and iconutil: macOS only
            self.assertNotEqual(icons[0].read_bytes(), icons[1].read_bytes())           # the DEV-marked icon
        self.assertEqual(self.make(dev, dest).returncode, 0)                             # its own launcher is remade freely

    def test_a_launcher_that_opens_another_vault_is_replaced_only_when_asked(self):
        dest = Path(tempfile.mkdtemp(prefix="creaite-apps-"))
        self.addCleanup(shutil.rmtree, dest, True)
        first, second = self.other_vault(dev=False), self.other_vault(dev=False)
        self.assertEqual(self.make(first, dest).returncode, 0)
        r = self.make(second, dest)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("opens another vault", r.stdout)
        self.assertIn("--replace", r.stdout)
        self.assertTrue(self.opens(dest / "creaite.app").samefile(first.root))          # left as it was
        r = self.make(second, dest, "--replace")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(self.opens(dest / "creaite.app").samefile(second.root))

    def test_doctor_warns_when_the_launcher_opens_another_vault(self):
        home = Path(tempfile.mkdtemp(prefix="creaite-home-"))                           # a throwaway HOME: never ~/Applications
        self.addCleanup(shutil.rmtree, home, True)
        live, dev = self.other_vault(dev=False), self.other_vault(dev=True)
        env = {**self.env, "HOME": str(home)}
        doctor = lambda v: subprocess.run([sys.executable, str(v.root / "system/scripts/doctor.py")], cwd=tempfile.gettempdir(),
                                          env=env, capture_output=True, text=True, timeout=120).stdout
        self.assertIn("PASS  Launcher opens this vault", doctor(live))                  # none yet: it's optional
        self.make(dev, home / "Applications")
        self.assertIn("PASS  Launcher opens this vault", doctor(live))                  # the dev launcher is the dev repository's
        (home / "Applications/creaite (dev).app").rename(home / "Applications/creaite.app")   # creaite.app opening the dev repository
        out = doctor(live)
        self.assertIn("WARN  Launcher opens this vault", out)
        self.assertIn("opens another vault", out)
        self.assertIn("make-launcher --replace", out)
    # ===== end BL-305 =====

    def agent_env(self):
        d = Path(tempfile.mkdtemp(prefix="creaite-agents-"))
        self.addCleanup(shutil.rmtree, d, True)
        return d, {**self.env, "CREAITE_AGENT_DIR": str(d), "CREAITE_NO_LAUNCHCTL": "1"}

    def test_the_login_agent_is_written_removed_and_reported_without_touching_launchd(self):
        import plistlib
        d, env = self.agent_env()
        (self.v.root / ".creaite-dev").unlink(missing_ok=True)          # a live vault, not the development repository
        self.launch("agent", "install", env=env, ok=0)
        files = list(d.glob("app.creaite.*.plist"))
        self.assertEqual(len(files), 1)
        plist = plistlib.loads(files[0].read_bytes())
        self.assertEqual(plist["Label"], files[0].stem)
        self.assertEqual(plist["ProgramArguments"][0], "/bin/sh")                      # BL-237: the wrapper picks the Python
        self.assertTrue(plist["ProgramArguments"][1].endswith("system/scripts/run"))
        self.assertEqual(plist["ProgramArguments"][2:], ["live_server.py"])
        self.assertTrue(Path(plist["WorkingDirectory"]).samefile(self.v.root))
        self.assertTrue(plist["RunAtLoad"])
        self.assertEqual(plist["KeepAlive"], {"SuccessfulExit": False})
        self.assertNotIn("CREAITE_LAUNCHED", plist["EnvironmentVariables"])       # so the server never stops when a window closes
        self.assertIn("PATH", plist["EnvironmentVariables"])
        if shutil.which("plutil"):                                                 # macOS only; skipped where it is missing
            lint = subprocess.run(["plutil", "-lint", str(files[0])], capture_output=True, text=True)
            self.assertEqual(lint.returncode, 0, lint.stdout + lint.stderr)
        self.launch("agent", "install", env=env, ok=0)                            # again: replaced, not duplicated
        self.assertEqual(len(list(d.glob("*.plist"))), 1)
        self.assertIn("Agent file:", self.launch("agent", "status", env=env, ok=0).stdout)
        self.launch("agent", "remove", env=env, ok=0)
        self.assertEqual(list(d.glob("*.plist")), [])
        self.assertIn("No login agent", self.launch("agent", "remove", env=env, ok=0).stdout)

    def test_an_agent_under_an_earlier_label_is_replaced_and_removed(self):
        d, env = self.agent_env()
        (self.v.root / ".creaite-dev").unlink(missing_ok=True)
        slug = re.sub(r"[^a-z0-9]+", "-", self.v.root.name.lower()).strip("-")
        old, other = d / f"example.old.creaite.{slug}.plist", d / "example.old.creaite.another-vault.plist"
        old.write_text("x"); other.write_text("x")
        self.assertIn("earlier name", self.launch("agent", "install", env=env, ok=0).stdout)
        self.assertFalse(old.exists())
        self.assertTrue(other.exists())                                            # another vault's agent is left alone
        self.assertEqual(len(list(d.glob("app.creaite.*.plist"))), 1)
        self.launch("agent", "remove", env=env, ok=0)
        old.write_text("x")
        self.assertIn("earlier name", self.launch("agent", "remove", env=env, ok=0).stdout)
        self.assertFalse(old.exists())

    def test_the_login_agent_is_refused_in_the_development_repository_and_for_unknown_words(self):
        d, env = self.agent_env()
        (self.v.root / ".creaite-dev").write_text("")
        r = self.launch("agent", "install", env=env)
        self.assertEqual(r.returncode, 1)
        self.assertIn("development repository", r.stdout)
        self.assertEqual(list(d.glob("*.plist")), [])
        self.assertEqual(self.launch("agent", "enable", env=env).returncode, 2)
        self.assertEqual(self.launch("agent", env=env).returncode, 2)


class AppBrowserTests(LiveBrowserCase):
    """The page in a real Chrome: the manifest and the theme colour, and the offline page once the server has stopped."""

    def test_the_manifest_is_valid_in_chrome_and_the_theme_colour_follows_the_mode(self):
        b = self.b
        self.assertEqual(b.eval("document.querySelector('link[rel=manifest]').href"), self.base + "/manifest.webmanifest")
        manifest = b.eval("fetch('/manifest.webmanifest').then(r=>r.json())")
        self.assertEqual(manifest["display"], "standalone")
        light = b.eval("(()=>{ S.theme='Light'; applyTheme(); return [document.querySelector('meta[name=theme-color]').content, getComputedStyle(document.documentElement).getPropertyValue('--bg').trim()]; })()")
        dark = b.eval("(()=>{ S.theme='Dark'; applyTheme(); return [document.querySelector('meta[name=theme-color]').content, getComputedStyle(document.documentElement).getPropertyValue('--bg').trim()]; })()")
        self.assertEqual(light[0], light[1])
        self.assertEqual(dark[0], dark[1])
        self.assertNotEqual(light[0], dark[0])

    def test_the_page_says_it_is_still_here_every_ten_seconds(self):
        self.assertEqual(self.b.eval("typeof D.token==='string' && SERVED"), True)
        hits = self.b.eval("""new Promise(res=>{ let n=0; const real=window.fetch; window.fetch=(u,o)=>{ if(String(u).includes('/api/here')) n++; return real(u,o); };
          setTimeout(()=>{ window.fetch=real; res(n); }, 21000); })""")
        self.assertGreaterEqual(hits, 2)

    def test_the_service_worker_shows_the_offline_page_when_the_server_is_stopped(self):
        b = self.b
        self.assertTrue(b.eval("Promise.race([navigator.serviceWorker.ready.then(r=>!!r.active),new Promise(r=>setTimeout(()=>r(false),15000))])"))
        for _ in range(40):                                                          # the worker caches the offline page as it installs
            if b.eval("caches.keys().then(k=>k.length>0)"):
                break
            time.sleep(0.25)
        self.assertTrue(b.eval("caches.keys().then(k=>k.length>0)"))
        self.proc.terminate()
        self.proc.wait(timeout=10)
        b.goto(self.base + "/", wait_for="document.readyState==='complete'")
        b.wait("document.title.includes(\"isn't running\")", 10)
        self.assertIn("Check again", b.eval("document.body.innerText"))

    def test_a_page_opened_before_a_restart_says_reload(self):
        """BL-174: after a restart the page's token is old; its next request shows the banner with Reload, not a bare refusal."""
        b = self.b
        self.assertTrue(b.eval("document.getElementById('staleAlert').hidden"))
        self.proc.terminate()
        self.proc.wait(timeout=10)
        self.proc = subprocess.Popen([sys.executable, str(self.v.root / "system/scripts/live_server.py")],
                                     env={**os.environ, "CREAITE_PORT": str(self.port)}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.assertTrue(wait_until(lambda: alive(self.port)))
        r = b.eval("api('/api/apply',{})")
        self.assertFalse(r["ok"])
        self.assertIn("Reload", r["message"])
        b.wait("!document.getElementById('staleAlert').hidden")
        text = b.eval("document.getElementById('staleAlert').innerText")
        self.assertIn("restarted", text)
        self.assertNotIn("Not allowed", text)
        self.assertEqual(b.eval("document.getElementById('staleReload').textContent"), "Reload")
        b.click("#staleReload")
        b.wait("typeof go==='function' && LIVE && document.getElementById('staleAlert') && document.getElementById('staleAlert').hidden", 20)
        self.assertTrue(b.eval("api('/api/here',{}).then(r=>r.ok)"))


if __name__ == "__main__":
    unittest.main()
