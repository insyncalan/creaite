"""#255 (Alan, 20-10-2026): Delete note on the Notes tab needs no approval card: the click is the approval, and it is undoable.

Run: python3 dev/tests/test_delete_note_no_card.py      (one live server over a throwaway vault; no Chrome)

The guarded half (reach.py, tracker.py, live_server.py, creaite-rules.md) is a proposal: dev/proposals/delete-note-no-card/. Until
it is applied, the tests that need it (marked with needs_255 and the reason) are expected failures, so this branch stays green;
once reach.PAGE_MOVES exists they run as normal tests. CREAITE_255_FORCE=1 runs their bodies anyway (the fail-first evidence).
CREAITE_MUTANT=<name> breaks one safeguard in the throwaway vault's copy of the scripts (MUTANTS below); class Mutations runs
each mutant against its own test and requires it to go red.

What is covered (the issue's (a) to (g)):
(a) Delete note from the page moves the note into <engagement>/<archive folder>/<notes folder>/ with no card pending, one files-log line
    and no marker left; the same route without the token, with another Host, or without the browser's same-origin marks moves
    nothing; the same move written into staging by hand is never applied; the old card route has gone.
(b) ask creaite can't delete a note on its own: filechange.py move (never: the archive folder) and delete (a card), a hand-staged or
    drafted proposal, a CHANGE card, and the new route (it has no HTTP tool: WebFetch and curl are denied and the hook refuses
    curl; the token is in no file and no run's environment; a script's plain call with the token is refused).
(c) a note changed since it was shown is refused with a plain message and left in place.
(d) a name taken in the archive gets -2.
(e) Undo and Move back restore it exactly (bytes and modification time); a note's Move back is direct too, never a card.
(f) reports_back and a project's archive keep their card; the direct Move back refuses a report.
(g) a path outside the notes folder, a folder, two files, a symlink (also to a sibling note), a name with .., another case or
    Unicode form of the name, a name with a line break, a linked archive folder, a move into another engagement: refused.
Also: a failed apply leaves nothing in staging; the apply's number is tracker.py's own; Undo is in the files log too.
The archive folder is paths.ARCHIVE (ARCHIVE below: _Archive today, 99 Archive after #252); a note in an older name's folder
still moves back. Everything is fictional and temporary.
"""
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import unicodedata
import unittest
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
from test_notes_tab import free_port  # noqa: E402
from test_tracker import ABC, Vault  # noqa: E402

os.environ.setdefault("CREAITE_NO_LAUNCH", "1")

# The archive folder's name, as paths.py has it (_Archive today, 99 Archive after #252), read without importing paths here.
ARCHIVE = re.search(r'^ARCHIVE = "([^"]+)"', (REPO / "system/scripts/paths.py").read_text(encoding="utf-8"), re.M).group(1)
DIFF_IN = "PAGE_MOVES = " in (REPO / "system/scripts/reach.py").read_text(encoding="utf-8")
FORCE = os.environ.get("CREAITE_255_FORCE") == "1"


def needs_255(reason):
    """A test that needs the #255 guarded diff: an expected failure (with `reason`) until it is applied, then a normal test."""
    def wrap(fn):
        if DIFF_IN:
            return fn
        if FORCE:
            return unittest.expectedFailure(fn)

        def fails(self):
            raise AssertionError(f"needs the #255 guarded diff (dev/proposals/delete-note-no-card/): {reason}")
        fails.__name__, fails.__doc__ = fn.__name__, fn.__doc__
        return unittest.expectedFailure(fails)
    return wrap


# Each mutant breaks one safeguard in the throwaway vault's scripts (file, the exact text, its replacement).
MUTANTS = {
    "any-file": ("archive.py", '    """None when `spec` is one note\'s Delete note or Move back',
                 '    return None\n    """None when `spec` is one note\'s Delete note or Move back'),
    "no-unchanged-check": ("live_server.py", "if not base or base != notes.text_sha(", "if False and base != notes.text_sha("),
    "no-token": ("live_server.py", 'if self.headers.get("X-Creaite-Token") != TOKEN:', "if False:"),
    "ask-calls-route": ("live_server.py", "    same-origin marks (Sec-Fetch-Site same-origin, an Origin naming this server's port on a loopback host).\"\"\"\n",
                        "    same-origin marks (Sec-Fetch-Site same-origin, an Origin naming this server's port on a loopback host).\"\"\"\n"
                        "    return True\n"),
    "ask-has-http": ("live_server.py", '"Bash(curl *)", "WebFetch", ', ""),
    "no-symlink-guard": ("live_server.py", "    if p.is_symlink():                                 # never followed: notes_target's",
                         "    if False:                                 # never followed: notes_target's"),
    "keep-failed-proposal": ("live_server.py", "        if code:                                       # not applied (or raised)",
                             "        if False:                                       # not applied (or raised)"),
    "latest-apply-id": ("live_server.py", '    m = re.search(r"^Apply (\\d+): ", out, re.M)', "    m = None"),
    "same-site-ok": ("live_server.py", '(handler.headers.get("Sec-Fetch-Site") or "").lower() != "same-origin"',
                     '(handler.headers.get("Sec-Fetch-Site") or "").lower() not in ("same-origin", "same-site", "none")'),
    "any-name-variant": ("live_server.py", "    if not listed:\n", "    if False:\n"),
    "control-names": ("live_server.py", '    if re.search(r"[\\x00-\\x1f\\x7f-\\x9f\\u2028\\u2029]", p.name):', "    if False:"),
    "linked-archive": ("archive.py", "    why = archive_folder_problem(base)\n    if why:\n        return None, why\n", ""),
    "no-undo-record": ("live_server.py", "                page_move_undone(latest)", "                pass"),
}


def folds_names():
    """Whether this file system finds a file by another case of its name (macOS's APFS does; Linux's ext4 doesn't)."""
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "Fold.md").write_text("x")
        return (Path(d) / "fOLD.md").exists()


def mutate(root, name):
    """Apply mutant `name` to the vault at `root`; SystemExit(97) when its text isn't there (a stale mutant never passes)."""
    script, old, new = MUTANTS[name]
    f = root / "system/scripts" / script
    text = f.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(97)
    f.write_text(text.replace(old, new), encoding="utf-8")


class Server(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        cls.v.run("init")
        if os.environ.get("CREAITE_MUTANT"):
            mutate(cls.v.root, os.environ["CREAITE_MUTANT"])
        cls.port = free_port()
        cls.base = f"http://127.0.0.1:{cls.port}"
        cls.proc = subprocess.Popen([sys.executable, str(cls.v.root / "system/scripts/live_server.py")],
                                    env={**os.environ, "CREAITE_PORT": str(cls.port)},
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(150):
            try:
                urllib.request.urlopen(cls.base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        html = urllib.request.urlopen(cls.base + "/").read().decode()
        cls.token = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)
        cls.v.cleanup()

    # ── calls ──
    def call(self, path, body, headers=None, method="POST"):
        """One call; a "busy" answer (LOCK held by the server's own background job, e.g. the daily backup a minute after start-up)
        is asked again for up to a minute, as the page's "Try again in a moment" says: nothing moved on a busy answer."""
        for _ in range(120):
            got = self.call_once(path, body, headers, method)
            if not (isinstance(got, dict) and got.get("busy") is True):
                return got
            time.sleep(0.5)
        return got

    def call_once(self, path, body, headers=None, method="POST"):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode() if method == "POST" else None,
                                     method=method, headers={"Content-Type": "application/json", **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return {"status": e.code, **json.loads(e.read().decode() or "{}")}

    def page_headers(self):
        """What the open page's fetch sends: its token, and Chrome's same-origin marks."""
        return {"X-Creaite-Token": self.token, "Origin": self.base, "Sec-Fetch-Site": "same-origin"}

    def post(self, path, body):
        return self.call(path, body, {"X-Creaite-Token": self.token})

    def page(self, path, body):
        return self.call(path, body, self.page_headers())

    def py_json(self, code):
        src = f"import sys, json; sys.path.insert(0, 'system/scripts')\n{code}"
        r = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True, cwd=self.v.root)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def run_at(self, script, *args, env=None):
        return subprocess.run([sys.executable, str(self.v.root / "system/scripts" / script), *args], cwd=self.v.root,
                              capture_output=True, text=True, env={**os.environ, **(env or {})})

    # ── the vault ──
    def new(self, title, code="ABC"):
        r = self.post("/api/notes/new", {"code": code, "template": "blank", "title": title})
        self.assertTrue(r["ok"], r)
        return r

    def folder(self):
        return self.v.root / ABC / "notes"

    def archive(self):
        return self.v.root / ABC / ARCHIVE / "notes"

    def files_log(self):
        p = self.v.root / "system/config/files-log.jsonl"
        return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []

    def markers(self):
        g = self.v.root / "system/guard"
        return sorted(f.name for f in g.glob("move-*")) if g.is_dir() else []

    def archived(self):
        req = urllib.request.Request(self.base + "/api/files", headers={"X-Creaite-Token": self.token})
        return json.loads(urllib.request.urlopen(req).read())["archived"]

    def delete_now(self, r):
        return self.page("/api/notes/delete/now", {"path": r["note"]["path"], "base": r["base"]})

    def hand_staged(self, kind, src, dst):
        """A proposal for the move written into staging by hand, through the page's /api/fs (as any page script could)."""
        spec = {"source_run": "dashboard", "applied_on_card": True, "items": [],
                "file_changes": {"title": "by hand", "archive": kind, "file_changes_decision": "approved",
                                 "file_ops": [{"op": "move", "from": src, "to": dst}]}}
        rel = f"system/staging/proposed-2026-10-20-hand-{kind}.json"
        self.assertEqual(self.post("/api/fs", {"op": "write", "path": rel, "text": json.dumps(spec)}), {"ok": True})
        self.addCleanup(lambda: (self.v.root / rel).unlink(missing_ok=True))
        return rel


class DeleteNoteNoCard(Server):
    def odd_files(self):
        """A folder named like a note and a symlinked "note" (to the project's CLAUDE.md) in the notes folder, removed after."""
        d, link = self.folder() / "Dir.md", self.folder() / "Linked.md"
        d.mkdir(parents=True, exist_ok=True)
        if not os.path.lexists(link):
            os.symlink(self.v.root / ABC / "CLAUDE.md", link)
        self.addCleanup(lambda: (link.unlink(missing_ok=True), d.rmdir() if d.is_dir() else None))
        return link

    # ── (a) ──
    @needs_255("the direct route /api/notes/delete/now is in the live_server.py diff")
    def test_a_the_page_deletes_at_once_with_no_card(self):
        r = self.new("Working session")
        f, dest = self.folder() / "Working session.md", self.archive() / "Working session.md"
        before = len(self.files_log())
        d = self.delete_now(r)
        self.assertTrue(d["ok"], d)
        self.assertTrue(d["moved"])
        self.assertEqual(d["message"], "Moved “Working session” to the archive.")
        self.assertEqual(d["to"], f"{ABC}/{ARCHIVE}/notes/Working session.md")
        self.assertFalse(f.exists())
        self.assertTrue(dest.is_file())
        self.assertIsNone(self.post("/api/edit/pending", {})["card"])                         # no card, ever
        self.assertEqual(self.markers(), [])                                                   # the one-time marker is gone
        log = self.files_log()[before:]
        self.assertEqual([(e["op"], e["path"], e["to"], e["apply"], e["via"]) for e in log],
                         [("note-archive", f"{ABC}/notes/Working session.md", d["to"], d["apply_id"], "dashboard")])
        listed = self.py_json("import filechange; print(json.dumps(sorted({e.get('op') for e in filechange.entries() "
                              "if e.get('op') in filechange.CHANGE_OPS})))")
        self.assertNotIn("note-archive", listed)                     # a record only: filechange.py never lists or undoes it

    @needs_255("the direct route and its page_call check are in the live_server.py diff")
    def test_a_only_the_page_s_own_call_moves_it(self):
        r = self.new("Callers")
        f, body = self.folder() / "Callers.md", {"path": r["note"]["path"], "base": r["base"]}
        h = self.page_headers()
        tries = {"no token": {k: v for k, v in h.items() if k != "X-Creaite-Token"},
                 "a wrong token": {**h, "X-Creaite-Token": "x" * 32},
                 "another Host": {**h, "Host": "creaite.example"},
                 "no browser marks": {"X-Creaite-Token": self.token},
                 "cross-site": {**h, "Sec-Fetch-Site": "cross-site"},
                 "same-site": {**h, "Sec-Fetch-Site": "same-site"},                          # same-origin only
                 "same-site, in capitals": {**h, "Sec-Fetch-Site": "SAME-SITE"},
                 "none (a typed address or bookmark)": {**h, "Sec-Fetch-Site": "none"},
                 "an empty mark": {**h, "Sec-Fetch-Site": ""},
                 "another site's Origin": {**h, "Origin": "http://elsewhere.example"},
                 "another port": {**h, "Origin": f"http://127.0.0.1:{self.port + 1}"},
                 "no Origin": {k: v for k, v in h.items() if k != "Origin"},
                 "a file:// page": {**h, "Origin": "null"},
                 "user info": {**h, "Origin": f"http://127.0.0.1:{self.port}@elsewhere.example"},
                 "a lookalike host": {**h, "Origin": f"http://localhost.elsewhere.example:{self.port}"},
                 "a path": {**h, "Origin": f"{self.base}/x"},
                 "no port": {**h, "Origin": "http://127.0.0.1"}}
        for why, headers in tries.items():
            got = self.call("/api/notes/delete/now", body, headers)
            self.assertEqual(got.get("status"), 403, (why, got))
            self.assertTrue(f.is_file(), why)
        self.assertEqual(self.call("/api/notes/delete/now", {}, h, method="GET").get("status"), 404)   # never a GET route
        self.assertEqual(self.post("/api/notes/delete", body).get("status"), 404)            # #124's card route has gone
        self.assertTrue(f.is_file())
        self.assertIsNone(self.post("/api/edit/pending", {})["card"])

    @needs_255("tracker.py's refusal for a page move names Delete note (the tracker.py diff)")
    def test_a_the_same_move_staged_by_hand_is_never_applied(self):
        self.new("By hand")
        src, dst = f"{ABC}/notes/By hand.md", f"{ABC}/{ARCHIVE}/notes/By hand.md"
        rel = self.hand_staged("notes", src, dst)
        r = self.post("/api/apply", {})
        self.assertTrue(r["ok"], r)
        self.assertIn(f"Left in staging, not applied: {Path(rel).name} file_changes_decision: move: {src} is moved only by "
                      "Delete note or Move back on the dashboard (the live server's own button)", r["message"].replace("Left waiting, not saved:", "Left in staging, not applied:"))
        self.assertTrue((self.folder() / "By hand.md").is_file())
        self.assertFalse((self.archive() / "By hand.md").exists())

    # ── (b) ──
    def test_b_ask_creaite_cant_move_or_delete_a_note_through_filechange(self):
        """filechange.py: a move into the archive folder is never; a delete, in an ask creaite run, is a card (exit 3, a request only)."""
        self.new("Chat move")
        src = f"{ABC}/notes/Chat move.md"
        out = self.run_at("filechange.py", "move", src, f"{ABC}/{ARCHIVE}/notes/Chat move.md", "--why", "tidy")
        self.assertNotEqual(out.returncode, 0)
        self.assertTrue((self.folder() / "Chat move.md").is_file())
        run = self.v.root / "system/guard/run.json"
        run.parent.mkdir(parents=True, exist_ok=True)
        run.write_text(json.dumps({"run": "r-255", "mode": "chat"}))
        try:
            out = self.run_at("filechange.py", "delete", src, "--why", "tidy")
        finally:
            run.unlink()
        self.assertEqual(out.returncode, 3, out.stdout + out.stderr)                          # Needs approval: the card
        self.assertTrue((self.folder() / "Chat move.md").is_file())

    def test_b_ask_creaite_cant_stage_or_card_a_note_s_move(self):
        r = self.new("Chat stage")
        spec = self.py_json(f"import archive; print(json.dumps(archive.note_delete_spec({r['note']['path']!r})))")[0]
        f = self.v.root / "system/staging/drafts/del-255.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(spec))
        out = self.run_at("propose.py", "stage", str(f))
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("Not staged", out.stdout)
        f.write_text(json.dumps(spec))
        card = self.py_json("import live_server as ls\n"
                            "class Run:\n    id, chat, session = 'r1', None, None\n    events = []\n"
                            "    def emit(self, kind, **k): self.events.append([kind, k])\n"
                            "r = Run(); ls.build_edit_card(r, 'Done.\\nCHANGE: system/staging/drafts/del-255.json | Delete it')\n"
                            "print(json.dumps(r.events))")
        self.assertIsNone(card[0][1]["card"])
        self.assertIn("never from ask creaite", card[0][1]["refused"])
        src, dst = r["note"]["path"], spec["file_changes"]["file_ops"][0]["to"]
        rel = self.hand_staged("notes", src, dst)
        out = self.run_at("tracker.py", "apply", Path(rel).name)                             # Terminal, by name
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("is moved only by", out.stdout)
        self.assertTrue((self.folder() / "Chat stage.md").is_file())

    def test_b_ask_creaite_has_no_way_to_call_the_page_s_routes(self):
        """No HTTP tool (WebFetch and curl denied, the hook refuses curl and any non-creaite command), no creaite script that
        posts to the server or knows the token, and the token is in no file and no run's environment."""
        got = self.py_json(
            "import live_server as ls, reach\n"
            f"url = 'http://127.0.0.1:{self.port}/api/notes/delete/now'\n"
            "cmds = [f'curl -X POST {url}', f'python3 -c \"import urllib.request; urllib.request.urlopen({url!r})\"',\n"
            "        f'system/scripts/run live_server.py {url}', 'wget ' + url, 'nc 127.0.0.1 80']\n"
            "print(json.dumps({'deny': ls.DENY_TOOLS, 'hook': [reach.hook_decision('Bash', {'command': c}, 'chat', 'r1')[0] for c in cmds],\n"
            "                  'env': sorted(ls.run_env().values())}))")
        self.assertIn("WebFetch", got["deny"])
        self.assertIn("Bash(curl *)", got["deny"])
        self.assertEqual(got["hook"], [False] * 5)
        self.assertNotIn(self.token, json.dumps(got["env"]))
        posters = [p.name for p in (self.v.root / "system/scripts").glob("*.py")
                   if "X-Creaite-Token" in p.read_text(encoding="utf-8", errors="ignore") and p.name != "live_server.py"]
        self.assertEqual(posters, [])
        for p in [*self.v.root.glob("*"), *(x for b in ("system", "projects", ".claude") for x in (self.v.root / b).rglob("*"))]:
            if p.is_file() and not p.is_symlink() and p.stat().st_size < 4_000_000 and "__pycache__" not in p.parts:
                self.assertNotIn(self.token.encode(), p.read_bytes(), p)

    @needs_255("page_call (the browser's same-origin marks) is in the live_server.py diff")
    def test_b_a_script_s_plain_call_with_the_token_is_refused(self):
        r = self.new("Script call")
        got = self.call("/api/notes/delete/now", {"path": r["note"]["path"], "base": r["base"]}, {"X-Creaite-Token": self.token})
        self.assertEqual(got.get("status"), 403, got)
        got = self.call("/api/files/move-back/now", {"path": r["note"]["path"]}, {"X-Creaite-Token": self.token})
        self.assertEqual(got.get("status"), 403, got)
        self.assertTrue((self.folder() / "Script call.md").is_file())

    # ── (c) ──
    @needs_255("the unchanged-since-shown check of the direct route is in the live_server.py diff")
    def test_c_a_note_changed_since_it_was_shown_is_refused_and_left(self):
        r = self.new("Changed")
        f = self.folder() / "Changed.md"
        s = self.post("/api/notes/save", {"path": r["note"]["path"], "body": "Typed in another window.\n", "base": r["base"]})
        self.assertTrue(s["ok"], s)
        got = self.delete_now(r)                                                               # the version first shown
        self.assertFalse(got["ok"], got)
        self.assertTrue(got["stale"])
        self.assertEqual(got["message"], "Not deleted: the note changed since you opened it. Open it again and try once more.")
        self.assertIn("Typed in another window.", f.read_text())
        self.assertFalse((self.archive() / "Changed.md").exists())
        self.assertFalse(self.page("/api/notes/delete/now", {"path": r["note"]["path"], "base": ""})["ok"])   # no version: no
        self.assertTrue(f.is_file())
        done = self.page("/api/notes/delete/now", {"path": r["note"]["path"], "base": s["base"]})            # the new version
        self.assertTrue(done["ok"], done)
        self.assertIn("Typed in another window.", (self.archive() / "Changed.md").read_text())

    @needs_255("the LOCK rule of the direct route is in the live_server.py diff")
    def test_c_nothing_lands_while_the_note_is_checked_and_moved(self):
        """LOCK, then NOTES_LOCK: while a save holds NOTES_LOCK the route waits (LOCK held, nothing staged or applied), then moves;
        while another job holds LOCK it moves nothing and says so."""
        r = self.new("Locked")
        got = self.py_json(
            "import threading, time, live_server as ls\n"
            "calls, real = [], ls.run\n"
            "def run(script, *a):\n    calls.append(script); return real(script, *a)\n"
            "ls.run = run\n"
            "class H:\n"
            "    client_address = ('127.0.0.1', 1)\n"
            "    class server:\n        server_address = ('127.0.0.1', 8765)\n"
            "    headers = {'Origin': 'http://127.0.0.1:8765', 'Sec-Fetch-Site': 'same-origin', 'Host': '127.0.0.1:8765'}\n"
            "    def __init__(self): self.out = {}\n"
            "    def host_ok(self): return True\n"
            "    def send(self, code, body): self.out = dict(body, code=code)\n"
            f"req = {{'path': {r['note']['path']!r}, 'base': {r['base']!r}}}\n"
            "busy = H(); ls.LOCK.acquire(); ls.notes_delete_now_route(busy, req); ls.LOCK.release()\n"
            "h = H(); ls.NOTES_LOCK.acquire()\n"
            "t = threading.Thread(target=lambda: ls.notes_delete_now_route(h, req), daemon=True); t.start(); time.sleep(1.5)\n"
            "during = [dict(h.out), list(calls), t.is_alive(), ls.LOCK.locked()]\n"
            "ls.NOTES_LOCK.release(); t.join(60)\n"
            "print(json.dumps([busy.out, during, h.out]))")
        busy, (out, calls, alive, locked), done = got
        self.assertFalse(busy["ok"], busy)
        self.assertTrue(busy["busy"])
        self.assertEqual([out, calls, alive, locked], [{}, [], True, True])                   # waiting, LOCK held, nothing run
        self.assertTrue(done["ok"], done)
        self.assertTrue((self.archive() / "Locked.md").is_file())

    @needs_255("the direct route keeps the rename's rule (live_server.py diff)")
    def test_c_never_while_ask_creaite_has_read_outside_content(self):
        r = self.new("Outside")
        run = self.v.root / "system/guard/run.json"
        run.parent.mkdir(parents=True, exist_ok=True)
        run.write_text(json.dumps({"run": "r-test", "mode": "chat", "marked": ["mail"]}))
        try:
            got = self.delete_now(r)
        finally:
            run.unlink()
        self.assertFalse(got["ok"], got)
        self.assertTrue(got.get("wait"))
        self.assertIn("outside content", got["message"])
        self.assertTrue((self.folder() / "Outside.md").is_file())

    # ── (d) ──
    @needs_255("the direct route is in the live_server.py diff")
    def test_d_a_name_taken_in_the_archive_gets_a_number(self):
        for n in range(3):
            d = self.delete_now(self.new("Same name"))
            self.assertTrue(d["ok"], d)
            self.assertTrue(d["to"].endswith("Same name.md" if n == 0 else f"Same name-{n + 1}.md"), d["to"])
        for name in ("Same name.md", "Same name-2.md", "Same name-3.md"):
            self.assertTrue((self.archive() / name).is_file(), name)

    # ── (e) ──
    @needs_255("the direct routes are in the live_server.py diff")
    def test_e_undo_and_move_back_restore_it_exactly(self):
        r = self.new("Exact")
        f = self.folder() / "Exact.md"
        f.write_text(f.read_text() + "A line with ü and – in it.\n", encoding="utf-8")
        old = os.stat(f).st_mtime_ns - 7_000_000_000
        os.utime(f, ns=(old, old))
        r = self.post("/api/notes/get", {"path": r["note"]["path"]})
        raw = f.read_bytes()
        d = self.page("/api/notes/delete/now", {"path": f"{ABC}/notes/Exact.md", "base": r["base"]})
        self.assertTrue(d["ok"], d)
        self.assertEqual((self.archive() / "Exact.md").read_bytes(), raw)
        self.assertEqual(os.stat(self.archive() / "Exact.md").st_mtime_ns, old)
        before = len(self.files_log())
        u = self.post("/api/undo", {"apply_id": d["apply_id"]})                                # the toast's Undo
        self.assertTrue(u["ok"], u)
        self.assertEqual([(e["op"], e["path"], e["to"], e["apply"]) for e in self.files_log()[before:]],      # L3: logged too
                         [("note-restored", d["to"], f"{ABC}/notes/Exact.md", d["apply_id"])])
        self.assertEqual(f.read_bytes(), raw)
        self.assertEqual(os.stat(f).st_mtime_ns, old)
        self.assertFalse((self.archive() / "Exact.md").exists())
        self.assertEqual(sorted((self.v.root / "system/staging").glob("proposed-*.json")), [])  # nothing waits in Review
        d = self.page("/api/notes/delete/now", {"path": f"{ABC}/notes/Exact.md", "base": r["base"]})
        self.assertTrue(d["ok"], d)
        at = next(a["at"] for a in self.archived() if a["path"] == f"{ABC}/notes/Exact.md")
        self.assertFalse(self.post("/api/files/move-back", {"path": at})["ok"])               # a note's Move back: never the card
        self.assertIsNone(self.post("/api/edit/pending", {})["card"])
        before = len(self.files_log())
        b = self.page("/api/files/move-back/now", {"path": at})                                # Move back, at once
        self.assertTrue(b["ok"], b)
        self.assertEqual(b["message"], "Moved “Exact” back to its notes folder.")
        self.assertEqual(f.read_bytes(), raw)
        self.assertEqual(os.stat(f).st_mtime_ns, old)
        self.assertIsNone(self.post("/api/edit/pending", {})["card"])
        self.assertEqual([e["op"] for e in self.files_log()[before:]], ["note-back"])
        self.assertEqual(self.markers(), [])
        before = len(self.files_log())
        u = self.post("/api/undo", {"apply_id": b["apply_id"]})                                # Undo of the Move back
        self.assertTrue(u["ok"], u)
        self.assertFalse(f.exists())
        self.assertEqual([(e["op"], e["path"], e["to"]) for e in self.files_log()[before:]],
                         [("note-rearchived", f"{ABC}/notes/Exact.md", at)])

    @needs_255("the direct Move back is in the live_server.py diff")
    def test_e_move_back_never_onto_a_note_that_has_the_name(self):
        d = self.delete_now(self.new("Lessons"))
        self.assertTrue(d["ok"], d)
        self.new("Lessons")
        new = (self.folder() / "Lessons.md").read_text()
        at = next(a["at"] for a in self.archived() if a["path"] == f"{ABC}/notes/Lessons.md")
        b = self.page("/api/files/move-back/now", {"path": at})
        self.assertTrue(b["ok"], b)
        self.assertEqual(b["message"], "Moved “Lessons” back to its notes folder as “Lessons-2” (a note has its old name).")
        self.assertEqual((self.folder() / "Lessons.md").read_text(), new)
        self.assertTrue((self.folder() / "Lessons-2.md").is_file())

    @unittest.skipUnless("ARCHIVE99" in (Path(__file__).resolve().parents[2] / "system/scripts/reach.py").read_text(encoding="utf-8"),
                         "needs the #252 guarded diff (dev/proposals/archive-99/guarded.diff): a move back out of the old _Archive")
    @needs_255("the direct Move back is in the live_server.py diff")
    def test_e_a_note_in_the_old_archive_folder_still_moves_back(self):
        """#252: new archives go into paths.ARCHIVE (99 Archive after it), but a note deleted before then is in the old _Archive
        folder, and its Move back still works from there. With ARCHIVE still _Archive (today) the note is simply there."""
        d = self.delete_now(self.new("Old place"))
        self.assertTrue(d["ok"], d)
        old = f"{ABC}/_Archive/notes/Old place.md"
        if d["to"] != old:                                     # put it where an earlier delete left it, and say so in its apply
            (self.v.root / old).parent.mkdir(parents=True, exist_ok=True)
            (self.v.root / d["to"]).rename(self.v.root / old)
            con = sqlite3.connect(self.v.root / "system/tracker.db")
            (ops,) = con.execute("SELECT file_ops FROM applies WHERE apply_id = ?", (d["apply_id"],)).fetchone()
            recs = [dict(r, to=old) if r.get("to") == d["to"] else r for r in json.loads(ops)]
            con.execute("UPDATE applies SET file_ops = ? WHERE apply_id = ?", (json.dumps(recs), d["apply_id"]))
            con.commit()
            con.close()
        self.assertIn(old, [a["at"] for a in self.archived()])
        b = self.page("/api/files/move-back/now", {"path": old})
        self.assertTrue(b["ok"], b)
        self.assertEqual(b["message"], "Moved “Old place” back to its notes folder.")
        self.assertTrue((self.folder() / "Old place.md").is_file())
        self.assertFalse((self.v.root / old).exists())

    # ── (f) ──
    def test_f_a_report_s_move_back_and_a_project_s_archive_keep_their_card(self):
        from test_archive_move_back import DUE, archive_old_files
        abc = archive_old_files(self.v.root)
        stored = f"projects/{abc.name}/{DUE[1]}"
        r = self.post("/api/files/move-back", {"path": stored})
        self.assertTrue(r["ok"], r)
        self.assertTrue(r["card"])
        card = self.post("/api/edit/pending", {})["card"]
        self.assertTrue(card and card["valid"], card)
        self.assertTrue((abc / ARCHIVE / DUE[1]).is_file())                                # nothing moved yet
        self.post("/api/edit/reject", {"card": card["card"]})
        p = self.post("/api/project/archive", {"code": "ABC", "action": "archive", "cancel_open": True})
        self.assertTrue(p.get("card"), p)                                                      # a project's archive: the card
        pending = self.post("/api/edit/pending", {})["card"]
        self.assertTrue(pending)
        self.post("/api/edit/reject", {"card": pending["card"]})
        self.assertTrue((self.v.root / ABC).is_dir())
        if DIFF_IN:                                                                           # the direct Move back: notes only
            got = self.page("/api/files/move-back/now", {"path": stored})
            self.assertFalse(got["ok"], got)
            self.assertIn("anything else goes on the approval card", got["message"])
            self.assertTrue((abc / ARCHIVE / DUE[1]).is_file())
            self.assertFalse((abc / DUE[1]).exists())

    def test_f_the_lists_agree(self):
        got = self.py_json("import archive, propose, reach\n"
                           "print(json.dumps([list(reach.CARD_ONLY_MOVES), sorted(propose.SERVER_CARD_ONLY), list(archive.PAGE_MOVES),\n"
                           "                  list(getattr(reach, 'PAGE_MOVES', archive.PAGE_MOVES))]))")
        card_only, server_only, page, reach_page = got
        self.assertEqual(sorted(card_only), server_only)            # every page move is still made only by the live server
        self.assertEqual(page, ["notes", "notes_back"])
        self.assertEqual(reach_page, page)
        self.assertTrue(set(page) <= set(card_only))
        self.assertIn("reports_back", card_only)

    # ── (g) ──
    def test_g_page_move_problem_takes_exactly_one_note_s_move(self):
        r = self.new("Shape")
        got = self.py_json(
            "import copy, archive\n"
            f"spec, _ = archive.note_delete_spec({r['note']['path']!r})\n"
            "op = spec['file_changes']['file_ops'][0]\n"
            "def v(f):\n    s = copy.deepcopy(spec); f(s); return archive.page_move_problem(s)\n"
            "out = {'ok': archive.page_move_problem(spec), 'kind ok': archive.page_move_problem(spec, 'notes'),\n"
            "       'wrong kind': archive.page_move_problem(spec, 'notes_back'),\n"
            "       'two files': v(lambda s: s['file_changes']['file_ops'].append(dict(op))),\n"
            "       'no file': v(lambda s: s['file_changes'].update(file_ops=[])),\n"
            "       'an item': v(lambda s: s.update(items=[{'table': 'actions'}])),\n"
            "       'reports_back': v(lambda s: s['file_changes'].update(archive='reports_back')),\n"
            "       'archive': v(lambda s: s['file_changes'].update(archive='archive')),\n"
            "       'a remove': v(lambda s: s['file_changes']['file_ops'][0].update(op='remove')),\n"
            "       'not a note': v(lambda s: s['file_changes']['file_ops'][0].update(to=op['to'][:-3] + '.docx')),\n"
            "       'dot dot': v(lambda s: s['file_changes']['file_ops'][0].update(**{'from': op['from'].replace('/notes/', '/notes/../')})),\n"
            "       'absolute': v(lambda s: s['file_changes']['file_ops'][0].update(to='/tmp/x.md')),\n"
            "       'extra key': v(lambda s: s['file_changes']['file_ops'][0].update(why='x')),\n"
            "       'extra block key': v(lambda s: s['file_changes'].update(file_changes_decision='approved')),\n"
            "       'not a dict': archive.page_move_problem([spec])}\n"
            "print(json.dumps(out))")
        self.assertIsNone(got.pop("ok"))
        self.assertIsNone(got.pop("kind ok"))
        for why, problem in got.items():
            self.assertTrue(problem, why)

    def test_g_the_mover_refuses_any_other_shape(self):
        """reach.archive_move_problem "notes": one .md directly in a notes folder, into that engagement's own archive folder."""
        self.new("Mover")
        other = self.v.root / "projects/DEF Other Programme/notes"
        other.mkdir(parents=True, exist_ok=True)
        (self.folder() / "_images").mkdir(parents=True, exist_ok=True)
        (self.folder() / "_images/pic.md").write_text("x")
        (self.folder() / "Picture.png").write_bytes(b"\x89PNG")
        self.odd_files()
        src = f"{ABC}/notes/Mover.md"
        cases = {"other engagement": (src, f"projects/DEF Other Programme/{ARCHIVE}/notes/Mover.md"),
                 "portfolio": (src, f"projects/_portfolio/{ARCHIVE}/notes/Mover.md"),
                 "outside the notes folder": (f"{ABC}/CLAUDE.md", f"{ABC}/{ARCHIVE}/notes/CLAUDE.md"),
                 "a subfolder": (f"{ABC}/notes/_images/pic.md", f"{ABC}/{ARCHIVE}/notes/_images/pic.md"),
                 "a folder": (f"{ABC}/notes/Dir.md", f"{ABC}/{ARCHIVE}/notes/Dir.md"),
                 "not a note": (f"{ABC}/notes/Picture.png", f"{ABC}/{ARCHIVE}/notes/Picture.png"),
                 "a symlink": (f"{ABC}/notes/Linked.md", f"{ABC}/{ARCHIVE}/notes/Linked.md"),
                 "dot dot": (f"{ABC}/notes/../notes/Mover.md", f"{ABC}/{ARCHIVE}/notes/Mover.md"),
                 "renamed": (src, f"{ABC}/{ARCHIVE}/notes/Other.md"),
                 "deeper": (src, f"{ABC}/{ARCHIVE}/notes/x/Mover.md")}
        got = self.py_json("import reach; c = " + json.dumps(cases) + "\n"
                           "print(json.dumps({k: reach.archive_move_problem(x, y, 'notes') for k, (x, y) in c.items()}))")
        for why, problem in got.items():
            self.assertTrue(problem, why)
        self.assertIsNone(self.py_json(f"import reach; print(json.dumps(reach.archive_move_problem({src!r}, "
                                       f"{f'{ABC}/{ARCHIVE}/notes/Mover.md'!r}, 'notes')))"))

    @needs_255("the direct route is in the live_server.py diff")
    def test_g_the_route_refuses_anything_but_one_note(self):
        r = self.new("Only this")
        link = self.odd_files()
        base = r["base"]
        for why, body, status in (
                ("outside the notes folder", {"path": f"{ABC}/CLAUDE.md", "base": base}, 404),
                ("a folder", {"path": f"{ABC}/notes/Dir.md", "base": base}, 404),
                ("two files", {"path": [r["note"]["path"], f"{ABC}/notes/Other.md"], "base": base}, 400),
                ("a destination", {"path": r["note"]["path"], "base": base, "to": f"{ABC}/{ARCHIVE}/notes/x.md"}, 400),
                ("dot dot", {"path": f"{ABC}/notes/../CLAUDE.md", "base": base}, 404),
                ("dot dot to a note", {"path": f"{ABC}/notes/../notes/Only this.md", "base": base}, 404),
                ("no version", {"path": r["note"]["path"]}, 400)):
            got = self.page("/api/notes/delete/now", body)
            self.assertEqual(got.get("status"), status, (why, got))
        got = self.page("/api/notes/delete/now", {"path": f"{ABC}/notes/Linked.md", "base": base})
        self.assertEqual(got.get("status"), 404, got)                                          # a symlink: not a note, never moved
        self.assertTrue(link.is_symlink())
        self.assertTrue((self.v.root / ABC / "CLAUDE.md").is_file())
        self.assertTrue((self.folder() / "Only this.md").is_file())
        self.assertFalse(self.page("/api/files/move-back/now", {"path": f"{ABC}/notes/Only this.md"})["ok"])   # not archived
        self.assertTrue((self.folder() / "Only this.md").is_file())
        self.assertFalse(self.archive().joinpath("Only this.md").exists())

    @needs_255("the direct route's symlink check is in the live_server.py diff")
    def test_g_a_symlink_to_a_sibling_note_is_refused(self):
        """notes_target finds Alias.md (its target is a note in the same folder) and its stored path is the target's: without the
        route's own symlink check, Delete note on Alias would archive Real.md."""
        r = self.new("Real")
        real, alias = self.folder() / "Real.md", self.folder() / "Alias.md"
        os.symlink("Real.md", alias)
        self.addCleanup(lambda: alias.unlink(missing_ok=True))
        raw = real.read_bytes()
        for base in (r["base"], "a stale version"):
            got = self.page("/api/notes/delete/now", {"path": f"{ABC}/notes/Alias.md", "base": base})
            self.assertEqual(got, {"ok": False, "message": "Not deleted: that isn't a note that is there."}, base)
        self.assertTrue(alias.is_symlink())
        self.assertEqual(real.read_bytes(), raw)
        self.assertEqual([p.name for p in self.archive().glob("*.md") if p.name.startswith(("Real", "Alias"))]
                         if self.archive().is_dir() else [], [])

    @needs_255("the direct route's name check is in the live_server.py diff")
    def test_g_another_case_or_unicode_form_of_the_name_is_refused(self):
        """A file system that folds case or Unicode form (macOS) finds the note by a variant of its name: refused, as the folder
        lists another name (where it doesn't fold, the variant isn't there: 404). Nothing moves either way."""
        r = self.new("Café plan")
        name = next(n for n in os.listdir(self.folder()) if n.startswith("Caf") and n.endswith(".md"))
        other = unicodedata.normalize("NFD" if unicodedata.is_normalized("NFC", name) else "NFC", name)
        self.assertNotEqual(other, name)
        for why, variant in (("case", name[:-3].swapcase() + ".md"), ("Unicode form", other)):
            got = self.page("/api/notes/delete/now", {"path": f"{ABC}/notes/{variant}", "base": r["base"]})
            if folds_names():                                                 # found by the variant: the name check refuses it
                self.assertEqual(got, {"ok": False, "message": "Not deleted: that isn't a note that is there."}, why)
            else:                                                             # not found: notes_target's own 404
                self.assertEqual(got, {"status": 404, "ok": False, "message": "That note isn't there any more."}, why)
        self.assertIn(name, os.listdir(self.folder()))
        self.assertFalse(self.archive().is_dir() and any(n.lower().startswith("caf") for n in os.listdir(self.archive())))

    @needs_255("the direct route's control-character check is in the live_server.py diff")
    def test_g_a_name_with_a_line_break_is_refused(self):
        """A file made outside creaite can have a line break in its name: never moved (its name would split the debug log's line)."""
        r = self.new("Plain")
        odd = self.folder() / "Two\nlines.md"
        odd.write_bytes((self.folder() / "Plain.md").read_bytes())
        self.addCleanup(lambda: odd.unlink(missing_ok=True))
        g = self.post("/api/notes/get", {"path": f"{ABC}/notes/Two\nlines.md"})
        self.assertTrue(g.get("ok"), g)
        got = self.page("/api/notes/delete/now", {"path": f"{ABC}/notes/Two\nlines.md", "base": g["base"]})
        self.assertEqual(got, {"ok": False, "message": "Not deleted: the note's name has a line break or another control "
                                                       "character in it. Rename the file first."})
        self.assertTrue(odd.is_file())
        self.assertTrue(r["ok"])

    def linked_archive(self):
        """ABC's archive folder as a link to a folder outside the vault (the real one kept aside and put back after); the outside folder."""
        arch, kept = self.v.root / ABC / ARCHIVE, self.v.root / ABC / f"{ARCHIVE}-kept"
        if arch.is_dir():
            arch.rename(kept)
        outside = Path(tempfile.mkdtemp())
        os.symlink(outside, arch)

        def put_back():
            arch.unlink()
            if kept.is_dir():
                kept.rename(arch)
            shutil.rmtree(outside, ignore_errors=True)
        self.addCleanup(put_back)
        return outside

    def test_g_a_linked_archive_folder_is_refused_by_archive_py(self):
        r = self.new("Linked archive")
        outside = self.linked_archive()
        got = self.py_json(f"import archive; print(json.dumps(archive.note_delete_spec({r['note']['path']!r})))")
        self.assertEqual(got, [None, f"the {ARCHIVE} folder isn't a plain folder in the project (a link or a file has its name), so "
                                     "nothing moves"])
        self.assertEqual(list(outside.iterdir()), [])

    @needs_255("the direct routes are in the live_server.py diff")
    def test_g_a_linked_archive_folder_is_a_plain_answer_not_an_error(self):
        """L6: Delete note into a linked archive folder, and Move back out of one: a plain refusal (no 500, no absolute path)."""
        r = self.new("Into a link")
        d = self.delete_now(self.new("Out of a link"))
        self.assertTrue(d["ok"], d)
        at = next(a["at"] for a in self.archived() if a["path"] == f"{ABC}/notes/Out of a link.md")
        kept = self.v.root / ABC / ARCHIVE
        outside = self.linked_archive()
        shutil.copytree(self.v.root / ABC / f"{ARCHIVE}-kept", outside, dirs_exist_ok=True)
        want = f"the {ARCHIVE} folder isn't a plain folder in the project (a link or a file has its name), so nothing moves."
        got = self.delete_now(r)
        self.assertEqual(got, {"ok": False, "message": f"Not deleted: {want}"})
        got = self.page("/api/files/move-back/now", {"path": at})
        self.assertEqual(got, {"ok": False, "message": f"Not moved back: {want}"})
        self.assertTrue((self.folder() / "Into a link.md").is_file())
        self.assertFalse((self.folder() / "Out of a link.md").exists())
        self.assertTrue((outside / "notes" / "Out of a link.md").is_file())
        self.assertFalse((outside / "notes" / "Into a link.md").exists())
        self.assertTrue(kept.is_symlink())

    # ── the mover's own steps (in this process, over the same vault) ──
    @needs_255("page_move is in the live_server.py diff")
    def test_h_a_failed_apply_leaves_nothing_in_staging(self):
        """L1: page_move stages the move, then the apply fails (or the marker can't be written): the proposal is removed."""
        r = self.new("Fails")
        staged = sorted(p.name for p in (self.v.root / "system/staging").glob("proposed-*.json"))
        got = self.py_json(
            "import contextlib, live_server as ls, archive\n"
            f"spec, _ = archive.note_delete_spec({r['note']['path']!r})\n"
            "real = ls.run\n"
            "def failing(script, *a):\n"
            "    return (1, 'refused for the test') if script == 'tracker.py' and a[:1] == ('apply',) else real(script, *a)\n"
            "ls.run = failing\nfailed = ls.page_move(spec)\nls.run = real\n"
            "@contextlib.contextmanager\ndef no_marker(name):\n    raise OSError('no marker')\n    yield\n"
            "ls.card_moves_allowed = no_marker\nraised = ls.page_move(spec)\n"
            "print(json.dumps([failed, raised]))")
        self.assertEqual(got, [[None, "refused for the test"], [None, "the move couldn't be recorded (OSError)"]])
        self.assertEqual(sorted(p.name for p in (self.v.root / "system/staging").glob("proposed-*.json")), staged)
        self.assertTrue((self.folder() / "Fails.md").is_file())
        self.assertEqual(self.markers(), [])

    @needs_255("page_move is in the live_server.py diff")
    def test_h_the_apply_number_is_tracker_s_own(self):
        """L4: the number Undo is given is the one tracker.py apply printed, not the latest in the applies record (another
        process may have applied in between)."""
        r = self.new("Numbered")
        got = self.py_json(
            "import live_server as ls, archive\n"
            f"spec, _ = archive.note_delete_spec({r['note']['path']!r})\n"
            "ls.latest_apply = lambda: 999999\n"
            "moved = ls.page_move(spec)\n"
            "code, out = ls.run('tracker.py', 'read', 'applies')\n"
            "print(json.dumps([moved, max(a['apply_id'] for a in json.loads(out) if not a['undone_at'])]))")
        (apply_id, why), real = got
        self.assertEqual((apply_id, why), (real, None))
        self.assertTrue((self.archive() / "Numbered.md").is_file())


# Each mutant, and the test that must go red with it.
TARGETS = {"any-file": "test_g_page_move_problem_takes_exactly_one_note_s_move",
           "no-unchanged-check": "test_c_a_note_changed_since_it_was_shown_is_refused_and_left",
           "no-token": "test_a_only_the_page_s_own_call_moves_it",
           "ask-calls-route": "test_b_a_script_s_plain_call_with_the_token_is_refused",
           "ask-has-http": "test_b_ask_creaite_has_no_way_to_call_the_page_s_routes",
           "no-symlink-guard": "test_g_a_symlink_to_a_sibling_note_is_refused",
           "keep-failed-proposal": "test_h_a_failed_apply_leaves_nothing_in_staging",
           "latest-apply-id": "test_h_the_apply_number_is_tracker_s_own",
           "same-site-ok": "test_a_only_the_page_s_own_call_moves_it",
           "any-name-variant": "test_g_another_case_or_unicode_form_of_the_name_is_refused",
           "control-names": "test_g_a_name_with_a_line_break_is_refused",
           "linked-archive": "test_g_a_linked_archive_folder_is_refused_by_archive_py",
           "no-undo-record": "test_e_undo_and_move_back_restore_it_exactly"}


class Mutations(unittest.TestCase):
    """Each safeguard, broken in a throwaway vault, turns its test red (and the mutant's text is really there)."""

    def red(self, mutant):
        script, old, _new = MUTANTS[mutant]
        self.assertEqual((REPO / "system/scripts" / script).read_text(encoding="utf-8").count(old), 1, mutant)
        r = subprocess.run([sys.executable, str(Path(__file__).resolve()), f"DeleteNoteNoCard.{TARGETS[mutant]}"],
                           capture_output=True, text=True, env={**os.environ, "CREAITE_MUTANT": mutant}, timeout=600)
        self.assertNotEqual(r.returncode, 0, f"{mutant} survived:\n{r.stderr[-2000:]}")
        self.assertNotEqual(r.returncode, 97, mutant)
        self.assertRegex(r.stderr, r"FAILED \((failures|errors)=1\)", mutant)
        self.assertNotIn("setUpClass", r.stderr, mutant)

    def test_m1_let_any_file_through(self):
        self.red("any-file")

    @needs_255("the mutated text is in the live_server.py diff")
    def test_m2_skip_the_unchanged_since_shown_check(self):
        self.red("no-unchanged-check")

    @needs_255("the token test needs the direct route (live_server.py diff)")
    def test_m3_drop_the_token_check(self):
        self.red("no-token")

    @needs_255("page_call is in the live_server.py diff")
    def test_m4_let_ask_creaite_call_the_route(self):
        self.red("ask-calls-route")

    def test_m5_give_ask_creaite_an_http_tool(self):
        self.red("ask-has-http")

    @needs_255("the symlink check is in the live_server.py diff")
    def test_m6_follow_a_symlink_to_a_sibling_note(self):
        self.red("no-symlink-guard")

    @needs_255("page_move is in the live_server.py diff")
    def test_m7_leave_a_failed_apply_s_proposal_in_staging(self):
        self.red("keep-failed-proposal")

    @needs_255("page_move is in the live_server.py diff")
    def test_m8_take_the_latest_apply_s_number(self):
        self.red("latest-apply-id")

    @needs_255("page_call is in the live_server.py diff")
    def test_m9_let_same_site_and_none_through(self):
        self.red("same-site-ok")

    @unittest.skipUnless(folds_names(), "this file system doesn't find a file by another case of its name")
    @needs_255("the name check is in the live_server.py diff")
    def test_m10_take_another_form_of_the_name(self):
        self.red("any-name-variant")

    @needs_255("the control-character check is in the live_server.py diff")
    def test_m11_move_a_name_with_a_line_break(self):
        self.red("control-names")

    def test_m12_follow_a_linked_archive(self):
        self.red("linked-archive")

    @needs_255("the Undo record is in the live_server.py diff")
    def test_m13_leave_undo_out_of_the_files_log(self):
        self.red("no-undo-record")


if __name__ == "__main__":
    unittest.main(verbosity=2)
