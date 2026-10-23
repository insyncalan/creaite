"""#300: start creaite when I sign in. The page half, the launcher's state, Health's suggestion and the guarded proposal.

- launch.py agent status --json: one JSON line with the real state (installed, loaded, on, supported, folder); never writes;
- Health: "creaite won't start by itself after a restart" while the agent is off on a Mac live vault, dismissible, never in the
  development repository (.creaite-dev) and not once it is on;
- the page: until the live server has the routes the switch says "Not available yet" and nothing is broken; with a stubbed pair of
  routes (the guarded proposal's contract) the switch shows the state, asks first, turns it on or off, the Terminal commands (in Help) print the
  user's own folder (filled in at run time, never written in code) and Today's first-run question answers Yes or Not now;
- the proposal (dev/proposals/300/live_server.diff) applies and reverses cleanly, and its routes work against a stubbed launcher;
- no real folder or name in the source (test_no_real_names covers the repo).

Run: python3 dev/tests/test_autostart_300.py   (the browser part needs Google Chrome; skipped otherwise)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
from live_browser import LiveBrowserCase  # noqa: E402
from test_tracker import Vault  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "system/templates/dashboard/src"
PROPOSAL = ROOT / "dev/proposals/300/live_server.diff"


def routes_exist():
    """True once the guarded diff is applied (the live server has the autostart routes)."""
    return "/api/autostart/status" in (ROOT / "system/scripts/live_server.py").read_text()


class LauncherState(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.d = self.v.root
        self.addCleanup(self.v.cleanup) if hasattr(self.v, "cleanup") else None
        self.agents = Path(tempfile.mkdtemp(prefix="creaite-300-agents-"))
        self.addCleanup(shutil.rmtree, self.agents, True)
        (self.d / ".creaite-dev").unlink(missing_ok=True)                  # a live vault, as the agent needs
        self.env = {**os.environ, "CREAITE_AGENT_DIR": str(self.agents), "CREAITE_NO_LAUNCHCTL": "1"}

    def launch(self, *a):
        return subprocess.run([sys.executable, str(self.d / "system/scripts/launch.py"), *a], cwd=self.d, env=self.env,
                              capture_output=True, text=True, timeout=60)

    def state(self):
        r = self.launch("agent", "status", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = r.stdout.strip().splitlines()
        self.assertEqual(len(lines), 1)
        return json.loads(lines[0])

    def test_state_follows_install_and_remove_and_writes_nothing(self):
        st = self.state()
        self.assertEqual((st["installed"], st["on"], st["supported"]), (False, False, True))
        self.assertEqual(Path(st["folder"]).resolve(), self.d.resolve())
        self.assertEqual(list(self.agents.iterdir()), [])                     # a read: nothing written
        self.assertEqual(self.launch("agent", "install").returncode, 0)
        st = self.state()
        self.assertTrue(st["installed"] and st["on"])
        self.assertEqual(self.launch("agent", "remove").returncode, 0)
        self.assertFalse(self.state()["on"])

    def test_the_development_repository_is_never_supported(self):
        (self.d / ".creaite-dev").write_text("")
        st = self.state()
        self.assertTrue(st["dev"])
        self.assertFalse(st["supported"])
        self.assertNotEqual(self.launch("agent", "install").returncode, 0)

    def test_plain_status_and_unknown_words_are_as_before(self):
        self.assertIn("Agent file:", self.launch("agent", "status").stdout)
        self.assertEqual(self.launch("agent", "status", "--yaml").returncode, 2)

    def test_health_suggests_it_while_off_and_only_in_a_live_vault(self):
        script = ("import sys, json; sys.path.insert(0, 'system/scripts'); import health, launch\n"
                  "doc = {'checks': [], 'passed': 0, 'failed': 0}\n"
                  "ids = lambda: [p['id'] for p in health.health(doc, dismissed=[])['problems']]\n"
                  "out = {'dev': ids()}\n"
                  "import os; os.remove('.creaite-dev')\n"
                  "out['off'] = ids()\n"
                  "p = health.health(doc, dismissed=[])['problems'][0]\n"
                  "out['title'] = p['title']; out['dismissable'] = p['dismissable']\n"
                  "d = [{'detail_key': p['key'], 'reason': 'no', 'date': '2026-10-22'}]\n"
                  "out['dismissed'] = ids() if False else [q['id'] for q in health.health(doc, dismissed=d)['problems']]\n"
                  "launch.agent_install()\n"
                  "out['on'] = ids()\n"
                  "print(json.dumps(out))\n")
        (self.d / ".creaite-dev").write_text("")
        r = subprocess.run([sys.executable, "-c", script], cwd=self.d, env=self.env, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(out["dev"], [])
        if sys.platform != "darwin":                                         # the suggestion is for a Mac
            self.skipTest("the agent is macOS only")
        self.assertEqual(out["off"], ["autostart"])
        self.assertEqual(out["title"], "creaite won't start by itself after a restart")
        self.assertTrue(out["dismissable"])
        self.assertEqual(out["dismissed"], [])
        self.assertEqual(out["on"], [])


class Proposal(unittest.TestCase):
    @unittest.skipIf(routes_exist(), "the guarded diff is already applied; it is covered by its own routes now")
    def test_it_applies_and_reverses_cleanly_and_its_routes_answer(self):
        v = Vault()
        d = v.root
        subprocess.run(["git", "init", "-q", str(d)], check=True)
        self.assertEqual(subprocess.run(["git", "apply", "--check", str(PROPOSAL)], cwd=d).returncode, 0)
        subprocess.run(["git", "apply", str(PROPOSAL)], cwd=d, check=True)
        self.assertEqual(subprocess.run(["git", "apply", "-R", "--check", str(PROPOSAL)], cwd=d).returncode, 0)
        script = r'''
import sys, json
sys.path.insert(0, "system/scripts")
import live_server as ls
sent = []
class H:
    client_address = ("127.0.0.1", 1)
    headers = {"Sec-Fetch-Site": "same-origin", "Origin": "http://127.0.0.1:8765"}     # the open page's own call (page_call)
    class server: server_address = ("127.0.0.1", 8765)
    def host_ok(self): return True
    def send(self, code, body): sent.append((code, body))
state = {"on": False, "supported": True, "dev": False, "installed": False, "loaded": False, "folder": "x"}
calls = []
def fake(script, *args):
    calls.append(args)
    if args[:2] == ("agent", "status"): return 0, json.dumps(state)
    state["on"] = args[1] == "install"; return 0, "ok"
ls.run = fake
ls.autostart_status_route(H(), {})
ls.autostart_set_route(H(), {"on": True})
ls.autostart_set_route(H(), {"on": "yes"})
state["supported"] = False; state["dev"] = True
ls.autostart_set_route(H(), {"on": True})
first = list(sent)
first_installs = [c for c in calls if c[1] == "install"]
import tempfile, pathlib
tmp = pathlib.Path(tempfile.mkdtemp())
state.update(supported=True, dev=False, on=False)
runs = {}
for name, content in (("absent", None), ("in_progress", '{"run": "r-1", "mode": "chat", "marked": []}'), ("marked", '{"marked": ["read mail"]}'),
                      ("bad_json", "{not json"), ("not_a_dict", "[1]"), ("unreadable", "DIR"), ("empty", "{}")):
    f = tmp / name
    if content == "DIR":
        f.mkdir()
    elif content is not None:
        f.write_text(content)
    ls.reach.RUN_FILE = f
    before = len([c for c in calls if c[1] == "install"])
    sent.clear()
    ls.autostart_set_route(H(), {"on": True})
    runs[name] = {"ok": sent[0][1]["ok"], "msg": sent[0][1].get("message", ""), "installed": len([c for c in calls if c[1] == "install"]) - before}
    state["on"] = False
print(json.dumps({"runs": runs, "first": first, "installs": first_installs, "routes": sorted(k for k in ls.SETUP_ROUTES if "autostart" in k)}))
'''
        r = subprocess.run([sys.executable, "-c", script], cwd=d, capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        out = json.loads(r.stdout.strip().splitlines()[-1])
        runs = out["runs"]
        for name in ("in_progress", "marked", "bad_json", "not_a_dict", "unreadable"):     # busy, and failing closed
            self.assertFalse(runs[name]["ok"], name)
            self.assertEqual(runs[name]["installed"], 0, name)
            self.assertNotRegex(runs[name]["msg"], r"run\.json|launch\.py|guard|json", name)
        self.assertIn("ask creaite is working", runs["in_progress"]["msg"])
        self.assertIn("ask creaite is working", runs["marked"]["msg"])
        self.assertIn("can't tell", runs["bad_json"]["msg"])
        self.assertIn("can't tell", runs["unreadable"]["msg"])
        for name in ("absent", "empty"):                                                    # no run: the user's own click goes through
            self.assertTrue(runs[name]["ok"], name)
            self.assertEqual(runs[name]["installed"], 1, name)
        s = out["first"]
        self.assertEqual(s[0][1]["on"], False)
        self.assertTrue(s[0][1]["ok"])
        self.assertTrue(s[1][1]["ok"] and s[1][1]["on"])
        self.assertEqual(s[2][0], 400)
        self.assertFalse(s[3][1]["ok"])
        self.assertIn("development copy", s[3][1]["message"])
        self.assertEqual(len(out["installs"]), 1)                              # only the one real turn-on
        self.assertEqual(out["routes"], ["/api/autostart/set", "/api/autostart/status"])
        for m in (x[1].get("message", "") for x in s):
            self.assertNotRegex(m, r"launch\.py|\.plist|system/")             # words, never the script's own text


STUB = r"""
window.__as = {on: false, supported: true, calls: []};
const real = window.fetch.bind(window);
window.fetch = (u, o) => {
  const p = String(u);
  if (!p.startsWith('/api/autostart/')) return real(u, o);
  const body = o && o.body ? JSON.parse(o.body) : {};
  window.__as.calls.push([p, body]);
  let out;
  if (p.endsWith('/status')) out = {ok: true, supported: window.__as.supported, dev: false, installed: window.__as.on, loaded: window.__as.on, on: window.__as.on, folder: '/Users/example/My Programmes/creaite'};
  else { window.__as.on = !!body.on; out = {ok: true, message: body.on ? 'creaite will start when you sign in.' : "creaite won't start when you sign in."}; }
  return Promise.resolve(new Response(JSON.stringify(out), {status: 200, headers: {'Content-Type': 'application/json'}}));
};
"""


class AutostartPage(LiveBrowserCase):
    shared_server = True

    def settings(self, stub):
        b = self.b
        b.eval("try{localStorage.removeItem('creaite-autostart-asked')}catch(e){}")
        if stub:
            b.eval(STUB)
            b.eval("asStatus(true)")                              # the stub's answer, not one cached from real routes
            b.pump(0.5)
        b.eval("go('settings','health')")
        b.wait("!!document.querySelector('#asCard')", 20)
        b.pump(0.5)
        if stub:
            b.eval("window.ASR=false; asRefresh().then(()=>{ window.ASR=true; })")
            b.wait("window.ASR===true", 10)                                  # the card may have been drawn from the real status (a Linux runner says "Only on a Mac")
        if stub and routes_exist():
            # #300 review M1: with the real routes the page's own refresh (started at boot, or by opening Settings) can answer after the
            # stub went in and put the real vault's folder over the stub's. Ask again through the stub until its answer is the one held.
            for _ in range(20):
                b.eval("asStatus(true)")
                b.pump(0.3)
                if b.eval("!!(window.AS && AS.status && String(AS.status.folder).startsWith('/Users/example'))"):
                    break
            else:
                self.fail("the stubbed status never replaced the real one")

    @unittest.skipIf(routes_exist(), "the live server has the routes, so there is nothing to degrade")
    def test_without_the_routes_the_card_degrades_cleanly(self):
        self.settings(False)
        b = self.b
        self.assertIn("Not available yet", b.eval("document.querySelector('#asCard').textContent"))
        self.assertFalse(b.eval("!!document.querySelector('#asSwitch')"))
        self.assertTrue(b.eval("!!document.querySelector('#dangerCard, #liveStop')"))      # Stop is untouched

    def test_the_switch_asks_first_and_changes_the_real_state(self):
        self.settings(True)
        b = self.b
        b.wait("!!document.querySelector('#asSwitch')", 10)
        self.assertEqual(b.eval("document.querySelector('#asState').textContent"), "Off")
        b.click("#asSwitch")
        b.wait("!!document.querySelector('#asConfirm')", 5)
        self.assertEqual(b.eval("window.__as.calls.filter(c=>c[0].endsWith('/set')).length"), 0)    # asked first, nothing changed
        b.click("[data-ascancel]")
        b.wait("!document.querySelector('#asConfirm')", 5)
        self.assertFalse(b.eval("window.__as.on"))
        b.click("#asSwitch")
        b.wait("!!document.querySelector('#asGo')", 5)
        b.click("#asGo")
        b.wait("window.__as.on===true && document.querySelector('#asState') && document.querySelector('#asState').textContent==='On'", 10)
        self.assertIn("Turn off", b.eval("document.querySelector('#asSwitch').textContent"))
        b.click("#asSwitch")
        b.wait("!!document.querySelector('#asGo')", 5)
        b.click("#asGo")
        b.wait("window.__as.on===false && document.querySelector('#asState').textContent==='Off'", 10)

    def test_the_terminal_note_prints_the_users_own_folder(self):
        self.settings(True)
        b = self.b
        self.assertFalse(b.eval("!!document.querySelector('#asCmd-install')"))        # not in Settings: Help has the block
        b.click("#asTerm a")                                                          # the pointer opens Help's section
        b.wait("!!document.querySelector('#asHelp #asCmd-install')", 10)
        b.eval("window.__copied=null; navigator.clipboard.writeText=t=>{window.__copied=t; return Promise.resolve();}")
        b.click("[data-ascopy='remove']")
        b.wait("window.__copied!==null", 5)
        self.assertTrue(b.eval("window.__copied").endswith("agent remove"))
        on = b.eval("document.querySelector('#asCmd-install').textContent")
        off = b.eval("document.querySelector('#asCmd-remove').textContent")
        self.assertEqual(on, "cd '/Users/example/My Programmes/creaite'\nsystem/scripts/run launch.py agent install")
        self.assertEqual(off, "cd '/Users/example/My Programmes/creaite'\nsystem/scripts/run launch.py agent remove")

    def test_unsupported_machine_shows_no_switch(self):
        self.settings(False)
        b = self.b
        b.eval(STUB + "window.__as.supported=false;")
        b.eval("go('settings','health')")                       # redrawn with the stub's answer
        b.eval("asRefresh && asRefresh()")
        b.pump(0.5)
        self.assertFalse(b.eval("!!document.querySelector('#asSwitch')"))

    def test_first_run_question_yes_and_not_now(self):
        b = self.b
        b.eval("try{localStorage.removeItem('creaite-autostart-asked')}catch(e){}")
        b.eval(STUB)
        for _ in range(20):                                       # a real status asked at boot can answer after the stub went in: ask until the stub's answer is the one held
            b.eval("asStatus(true)")
            b.pump(0.3)
            if b.eval("!!(window.AS && AS.status && String(AS.status.folder).startsWith('/Users/example'))"):
                break
        else:
            self.fail("the stubbed status never replaced the real one")
        b.eval("asStatus(true).then(()=>{ go('today'); renderSetup(); })")
        b.pump(0.8)
        if not b.eval("!!document.querySelector('#setupList')"):
            self.skipTest("the sample vault has finished set-up, so the checklist is not up")
        b.wait("!!document.querySelector('#asQ')", 10)
        self.assertIn("Start creaite automatically when you sign in?", b.eval("document.querySelector('#asQ').textContent"))
        b.click("[data-asq='no']")
        b.wait("!document.querySelector('#asQ')", 10)
        self.assertFalse(b.eval("window.__as.on"))
        self.assertEqual(b.eval("window.__as.calls.filter(c=>c[0].endsWith('/set')).length"), 0)   # Not now changes nothing
        b.eval("try{localStorage.removeItem('creaite-autostart-asked')}catch(e){}; renderSetup()")
        b.wait("!!document.querySelector('#asQ')", 10)
        b.click("[data-asq='yes']")
        b.wait("window.__as.on===true", 10)


class Source(unittest.TestCase):
    def test_no_absolute_folder_is_written_in_the_source(self):
        text = (SRC / "autostart.js").read_text() + PROPOSAL.read_text()
        self.assertNotRegex(text, r"/Users/|/home/|C:\\\\")


if __name__ == "__main__":
    unittest.main()
