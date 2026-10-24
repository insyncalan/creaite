"""Tests for live_server.py (Step 4c).

Run: python3 dev/tests/test_live_server.py
Starts the server on a free port in a throwaway vault with fictional data. ask creaite uses a stand-in `claude`
(CREAITE_CLAUDE) that prints Claude Code's stream-json format, so no real Claude call is made.
"""
import json
import re
import socket
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_dashboard import CHROME, populate  # noqa: E402
from test_tracker import ABC, Vault, make_draft  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from split_dashboard import readable_page  # noqa: E402

FAKE_CLAUDE = r'''#!/usr/bin/env python3
import json, sys, time
args = sys.argv[1:]
allowed = args[args.index("--allowedTools") + 1]
message = args[args.index("--") + 1]
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init", "session_id": "sess-1"})
if message.startswith("Draft the Current state"):   # BL-46
    out({"type": "assistant", "message": {"content": [{"type": "text", "text": "Recovery is **on track**.\n\nSOURCES:\n- tracker"}]}})
    out({"type": "result", "result": "ok", "session_id": "sess-g"})
    sys.exit(0)
if message.startswith("slow"):           # Stop tests (BL-33): thinking, or a write step that takes 4 s
    out({"type": "assistant", "message": {"content": [{"type": "text", "text": "Started."}]}})
    if message == "slow write":
        out({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "w1", "name": "Bash",
             "input": {"command": "python3 system/scripts/tracker.py apply"}}]}})
        time.sleep(4)
        out({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "w1", "content": "ok"}]}})
    time.sleep(30)
    sys.exit(0)
out({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t1", "name": "Bash",
     "input": {"command": "python3 system/scripts/tracker.py read actions"}},
    {"type": "tool_use", "id": "t2", "name": "Bash", "input": {"command": "sqlite3 system/tracker.db"}}]}})
out({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1", "content": "[]"},
    {"type": "tool_result", "tool_use_id": "t2", "is_error": True, "content": "denied"}]}})
can_apply = "tracker.py apply" in allowed
text = "Write tools allowed." if can_apply else "Here's what I'd do.\nCONFIRM: Close ABC-A-001 | Stage a proposal closing it"
out({"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}})
out({"type": "result", "result": text, "session_id": "sess-1"})
'''


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class LiveServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = v = Vault()
        populate(v)
        make_draft(v.root / "system/staging/drafts/Draft minutes.docx")   # a real Word draft for review.py
        fake = v.root / "fake_claude.py"
        fake.write_text(FAKE_CLAUDE)
        fake.chmod(0o755)
        cls.port = free_port()
        cls.base = f"http://127.0.0.1:{cls.port}"
        env = {**__import__("os").environ, "CREAITE_PORT": str(cls.port), "CREAITE_CLAUDE": str(fake)}
        cls.proc = subprocess.Popen([sys.executable, str(v.root / "system/scripts/live_server.py")], env=env,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for _ in range(50):
            try:
                urllib.request.urlopen(cls.base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        html = urllib.request.urlopen(cls.base + "/").read().decode()
        cls.html = html
        cls.data = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))
        cls.token = cls.data["token"]

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)
        cls.v.cleanup()

    def post(self, path, body, token=None, headers=None):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": token or self.token,
                                              **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read().decode()
                return r.status, (json.loads(raw) if r.headers.get_content_type() == "application/json" else raw)
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def test_health_and_page(self):
        with urllib.request.urlopen(self.base + "/health") as r:
            self.assertIsNone(r.headers["Access-Control-Allow-Origin"])       # BL-212: no cross-origin reads
            self.assertEqual(json.loads(r.read()), {"ok": True})                # BL-212: no vault name, no port
        self.assertTrue(self.data["live"])
        self.assertEqual(self.data["vault_path"], str(self.v.root.resolve()))   # given to the page, never stored
        self.assertNotIn(str(self.v.root), (self.v.root / "dashboard.html").read_text(encoding="utf-8"))

    def test_token_and_host_required(self):
        self.assertEqual(self.post("/api/fs", {"op": "read", "path": "system/config/settings.json"}, token="x")[0], 403)
        self.assertEqual(self.post("/api/apply", {}, headers={"Host": f"evil.example:{self.port}"})[0], 403)
        req = urllib.request.Request(self.base + "/api/data")        # no token
        with self.assertRaises(urllib.error.HTTPError):
            urllib.request.urlopen(req)

    def test_file_allowlist(self):
        ok = self.post("/api/fs", {"op": "read", "path": f"{ABC}/CLAUDE.md"})[1]
        self.assertIn("Current state", ok["text"])
        for op, path in (("write", "system/scripts/x.py"), ("read", "system/tracker.db"),
                         ("read", "projects/../system/tracker.db"), ("remove", "system/config/settings.json"),
                         ("write", "/etc/passwd")):
            self.assertEqual(self.post("/api/fs", {"op": op, "path": path, "text": "x"})[0], 403, (op, path))
        self.assertEqual(self.post("/api/open", {"path": "system/tracker.db"})[0], 403)

    def test_open_launches_nothing_when_no_launch_is_set(self):     # BL-171: the suite once started Word on a throwaway draft
        st, r = self.post("/api/open", {"path": "system/staging/drafts/Draft minutes.docx"})
        self.assertEqual(st, 200)
        self.assertEqual((r["ok"], r["launched"]), (True, False))
        self.assertTrue(r["path"].endswith("system/staging/drafts/Draft minutes.docx"))

    def test_save_apply_and_undo(self):
        a1 = next(a for a in self.data["actions"] if a["id"] == "ABC-A-001")
        prop = {"created": "2026-10-05T10:00:00", "source_run": "dashboard", "files": [], "items": [
            {"n": 1, "op": "update", "table": "actions", "id": "ABC-A-001", "changes": {"owner": "Live Test"},
             "based_on": a1["updated_at"], "match": "strong", "flags": [], "decision": "approved"}]}
        self.assertTrue(self.post("/api/fs", {"op": "write", "path": "system/staging/proposed-2026-10-05-100000-dashboard.json",
                                              "text": json.dumps(prop)})[1]["ok"])
        res = self.post("/api/apply", {})[1]
        self.assertTrue(res["ok"], res)
        owner = lambda: next(a["owner"] for a in self.v.rows("actions") if a["id"] == "ABC-A-001")  # noqa: E731
        self.assertEqual(owner(), "Live Test")
        stale = self.post("/api/undo", {"apply_id": res["apply_id"] - 1})[1]
        self.assertFalse(stale["ok"])                                   # only the latest apply can be undone
        self.assertIn("later change", stale["message"])
        self.assertTrue(self.post("/api/undo", {"apply_id": res["apply_id"]})[1]["ok"])
        self.assertNotEqual(owner(), "Live Test")

    def test_review_runs_review_py_checks(self):
        fname = "proposed-pending.json"
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
        import build_dashboard
        fp = build_dashboard.block_fp(json.loads((self.v.root / "system/staging" / fname).read_text())["meeting"])     # 2.6.3: expect is required
        res = self.post("/api/review", {"file": fname, "ref": "meeting", "decision": "approved", "expect": fp})[1]
        self.assertNotIn("labelled", res["message"])                    # BL-121: no label check
        res = self.post("/api/review", {"file": fname, "ref": "meeting", "decision": "approved",
                                        "modes": ["as-staged", "unlabelled"], "expect": fp})[1]      # an old page's "unlabelled" mode is ignored
        self.assertTrue(res["ok"], res)
        data = json.loads((self.v.root / "system/staging" / fname).read_text())
        self.assertEqual(data["meeting"]["minutes_decision"], "approved")
        gone = self.post("/api/review", {"file": "proposed-nope.json", "ref": 1, "decision": "approved"})[1]
        self.assertIn("no longer pending", gone["message"])

    def ask(self, body):
        req = urllib.request.Request(self.base + "/api/ask", data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        with urllib.request.urlopen(req, timeout=60) as r:
            return [json.loads(ln[6:]) for ln in r.read().decode().splitlines() if ln.startswith("data: ")]

    def test_ask_streams_and_asks_before_writing(self):
        evs = self.ask({"message": "Close ABC-A-001"})
        kinds = [e["type"] for e in evs]
        self.assertEqual(kinds, ["step", "text", "confirm", "done"])
        self.assertEqual(evs[0]["label"], "Running tracker.py read actions")   # refused sqlite3 attempt not shown
        self.assertNotIn("CONFIRM:", evs[1]["text"])
        self.assertEqual((evs[2]["title"], evs[2]["body"]), ("Close ABC-A-001", "Stage a proposal closing it"))
        self.assertEqual(evs[3]["session"], "sess-1")
        evs = self.ask({"message": "Go ahead", "confirmed": "Close ABC-A-001", "session": "sess-1"})
        self.assertIn({"type": "text", "text": "Write tools allowed."}, evs)    # write tools only once confirmed
        self.assertNotIn("confirm", [e["type"] for e in evs])

    def test_learn_signal(self):
        """BL-28: the dashboard's "Remember this" stages a register change through propose.py; bad input refused."""
        status, res = self.post("/api/learn", {"code": "ABC", "kind": "sender", "value": "sam@client.com"})
        self.assertTrue(res["ok"], res)
        staged = sorted((self.v.root / "system/staging").glob("proposed-*-edit.json"))
        self.assertTrue(any("sam@client.com" in p.read_text() for p in staged))
        for p in staged:
            p.unlink()
        self.assertFalse(self.post("/api/learn", {"code": "ABC", "kind": "keyword", "value": "pilot"})[1]["ok"])
        self.assertFalse(self.post("/api/learn", {"code": "ABC", "kind": "sender", "value": "a|b"})[1]["ok"])
        self.assertFalse(self.post("/api/learn", {"code": "ABC", "kind": "sender", "value": "me@brightwater.example"})[1]["ok"])

    def ask_and_stop(self, body, after=2.0):
        import threading
        import time
        got = {}
        t = threading.Thread(target=lambda: got.update(evs=self.ask(body)))
        start = time.time()
        t.start()
        time.sleep(after)
        status, res = self.post("/api/ask/stop", {"run": body["run"]})
        t.join(20)
        return res, got.get("evs", []), time.time() - start

    def test_stop_read_only_at_once(self):
        """BL-33: a read-only request stops at once; the chat keeps the partial exchange, marked stopped."""
        (self.v.root / "system/staging/ask/sess-1.json").unlink(missing_ok=True)
        res, evs, took = self.ask_and_stop({"message": "slow think", "run": "run-read-1"})
        self.assertEqual((res["ok"], res["deferred"]), (True, False))
        self.assertLess(took, 10)
        self.assertIn({"type": "stopped", "after_step": False, "timed_out": False}, evs)
        rec = json.loads((self.v.root / "system/staging/ask/sess-1.json").read_text())
        self.assertEqual((rec["messages"][-1]["text"], rec["messages"][-1]["stopped"]), ("Started.", True))
        self.assertFalse(self.post("/api/ask/stop", {"run": "run-read-1"})[1]["ok"])     # nothing left running

    def test_stop_write_after_the_running_step(self):
        """BL-33: a confirmed write isn't cut off mid-step: the step finishes, then the run stops."""
        res, evs, took = self.ask_and_stop({"message": "slow write", "confirmed": "Apply", "run": "run-write-1"})
        self.assertEqual((res["ok"], res["deferred"]), (True, True))
        self.assertLess(took, 10)                                                # not the fake's 30 s
        self.assertIn({"type": "step", "label": "Running tracker.py apply"}, evs)   # the step finished
        self.assertIn({"type": "stopped", "after_step": True, "timed_out": False}, evs)

    def wait_done(self, run, limit=15):
        import time
        end = time.time() + limit
        while time.time() < end:
            r = self.post("/api/ask/running", {})[1]["run"]
            if not r or r["id"] != run or r["done"]:
                return r
            time.sleep(0.2)
        return None

    def test_closing_the_page_doesnt_stop_a_run(self):
        """BL-37: a disconnect leaves the run going; attach replays it and follows; only Stop ends it."""
        import socket
        import time
        body = json.dumps({"message": "slow think", "run": "run-keep-1"}).encode()
        sock = socket.create_connection(("127.0.0.1", self.port))
        sock.sendall(b"POST /api/ask HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Type: application/json\r\n"
                     + f"X-Creaite-Token: {self.token}\r\nContent-Length: {len(body)}\r\n\r\n".encode() + body)
        time.sleep(2.0)
        sock.close()                                                             # the page goes away
        time.sleep(1.0)
        running = self.post("/api/ask/running", {})[1]["run"]
        self.assertEqual((running["id"], running["done"], running["message"]), ("run-keep-1", False, "slow think"))
        busy = self.post("/api/ask", {"message": "another"})
        self.assertEqual(busy[0], 409)                                           # one run at a time
        import threading
        got = {}
        t = threading.Thread(target=lambda: got.update(evs=self.attach("run-keep-1")))
        t.start()
        time.sleep(1.0)
        self.assertTrue(self.post("/api/ask/stop", {"run": "run-keep-1"})[1]["ok"])
        t.join(15)
        evs = got["evs"]
        self.assertEqual(evs[0], {"type": "text", "text": "Started."})          # replayed from the start
        self.assertEqual([e["type"] for e in evs][-2:], ["stopped", "done"])
        self.post("/api/ask/ack", {"run": "run-keep-1"})
        self.assertIsNone(self.post("/api/ask/running", {})[1]["run"])

    def attach(self, run):
        req = urllib.request.Request(self.base + "/api/ask/attach", data=json.dumps({"run": run}).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        with urllib.request.urlopen(req, timeout=60) as r:
            return [json.loads(ln[6:]) for ln in r.read().decode().splitlines() if ln.startswith("data: ")]

    def test_safety_timeout_ends_an_unwatched_run(self):
        import socket
        import time
        f = self.v.root / "system/config/settings.json"
        old = f.read_text()
        cfg = json.loads(old)
        cfg.setdefault("assistant", {})["run_timeout_minutes"] = 0.05             # 3 seconds
        f.write_text(json.dumps(cfg))
        try:
            body = json.dumps({"message": "slow think", "run": "run-time-1"}).encode()
            sock = socket.create_connection(("127.0.0.1", self.port))
            sock.sendall(b"POST /api/ask HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Type: application/json\r\n"
                         + f"X-Creaite-Token: {self.token}\r\nContent-Length: {len(body)}\r\n\r\n".encode() + body)
            time.sleep(1.0)
            sock.close()
            time.sleep(6)
            evs = self.attach("run-time-1")
            self.assertIn({"type": "stopped", "after_step": False, "timed_out": True}, evs)
        finally:
            f.write_text(old)
            self.post("/api/ask/ack", {"run": "run-time-1"})

    def test_interrupted_runs_marked_at_start(self):
        """BL-37: a run still going when the server stopped shows as Interrupted next time."""
        import subprocess
        import sys as _sys
        f = self.v.root / "system/staging/ask/int-chat-1.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({"chat": "int-chat-1", "title": "Q", "updated": "2026-10-05T09:00:00", "messages": [
            {"who": "you", "text": "Q", "run": "r-1"}, {"who": "creaite", "text": "Half", "steps": [], "run": "r-1",
                                                        "running": True}]}))
        code = "import sys; sys.path.insert(0, 'system/scripts'); import live_server; live_server.mark_interrupted()"
        subprocess.run([_sys.executable, "-c", code], cwd=self.v.root, check=True)
        last = json.loads(f.read_text())["messages"][-1]
        self.assertEqual((last.get("running"), last.get("interrupted")), (None, True))
        f.unlink()

    def test_generate_current_state(self):
        """BL-46: the draft streams back like ask creaite, is kept out of chat history, and bad input is refused."""
        before = sorted(p.name for p in (self.v.root / "system/staging/ask").glob("*.json")) \
            if (self.v.root / "system/staging/ask").exists() else []
        req = urllib.request.Request(self.base + "/api/current/generate", method="POST", data=json.dumps(
            {"code": "ABC", "from": "2026-10-01", "to": "2026-10-09", "sources": ["tracker", "minutes"], "note": "pilot",
             "run": "gen-test-1"}).encode(), headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        with urllib.request.urlopen(req, timeout=60) as r:
            evs = [json.loads(ln[6:]) for ln in r.read().decode().splitlines() if ln.startswith("data: ")]
        self.assertIn({"type": "text", "text": "Recovery is **on track**.\n\nSOURCES:\n- tracker"}, evs)
        self.assertEqual(evs[-1]["type"], "done")
        after = sorted(p.name for p in (self.v.root / "system/staging/ask").glob("*.json")) \
            if (self.v.root / "system/staging/ask").exists() else []
        # not a chat of Alan's: BL-326 keeps a run creaite started only in the day's runs-YYYY-MM-DD history chat
        self.assertEqual(before, [n for n in after if not n.startswith("runs-")])
        self.post("/api/ask/ack", {"run": "gen-test-1"})
        self.assertEqual(self.post("/api/current/generate", {"code": "abc"})[0], 400)
        self.assertEqual(self.post("/api/current/generate", {"code": "ABC", "from": "01-10-2026"})[0], 400)

    def test_unknown_route_is_reported_plainly(self):
        """An older server answers a newer page's call with 404 "Not found"; the page turns that into "restart it"."""
        self.assertEqual(self.post("/api/no-such-route", {}), (404, {"ok": False, "message": "Not found"}))
        page = readable_page()     # BL-231: the source; the bundle reprints the code
        self.assertIn('if(r.status===404&&j.message==="Not found") j.message=OLDSERVER;', page)

    def test_inbox_preview_remove_restore(self):
        """Inbox files can be previewed (text, Word) and removed to backups, with undo; nothing outside the inbox."""
        inbox = self.v.root / "inbox"
        (inbox / "Call notes.txt").write_text("Sara confirmed the pilot.", encoding="utf-8")
        make_draft(inbox / "Steering.docx")
        (inbox / "Deck.pdf").write_bytes(b"%PDF-1.4")
        st, r = self.post("/api/inbox/preview", {"path": "inbox/Call notes.txt"})
        self.assertEqual((st, r["text"], r["cut"]), (200, "Sara confirmed the pilot.", False))
        st, r = self.post("/api/inbox/preview", {"path": "inbox/Steering.docx"})
        self.assertTrue(r["ok"] and r["text"].strip())                          # Word text extracted
        self.assertEqual(self.post("/api/inbox/preview", {"path": "inbox/Deck.pdf"})[1], {"ok": True, "open": True})
        self.assertEqual(self.post("/api/inbox/preview", {"path": "inbox/../CLAUDE.md"})[0], 404)
        self.assertEqual(self.post("/api/inbox/preview", {"path": "system/tracker.db"})[0], 404)
        st, r = self.post("/api/inbox/remove", {"path": "inbox/Call notes.txt"})
        self.assertFalse((inbox / "Call notes.txt").exists())
        self.assertTrue(r["kept"].startswith("system/backups/inbox-removed/") and (self.v.root / r["kept"]).is_file())
        self.assertFalse(self.post("/api/inbox/restore", {"kept": "system/tracker.db"})[1]["ok"])
        st, back = self.post("/api/inbox/restore", {"kept": r["kept"]})
        self.assertEqual(back["path"], "inbox/Call notes.txt")
        for n in ("Call notes.txt", "Steering.docx", "Deck.pdf"):
            (inbox / n).unlink()

    def test_inbox_upload(self):
        """BL-42: meeting files into inbox/, 25 MB at most, safe names, never overwriting."""
        import base64
        b64 = lambda raw: base64.b64encode(raw).decode()  # noqa: E731
        st, r1 = self.post("/api/inbox/upload", {"name": "../ABC sync?.vtt", "data": b64(b"WEBVTT")})
        self.assertEqual((st, r1["name"]), (200, "ABC sync.vtt"))                 # path stripped, name cleaned
        st, r2 = self.post("/api/inbox/upload", {"name": "ABC sync.vtt", "data": b64(b"WEBVTT 2")})
        self.assertEqual(r2["name"], "ABC sync (2).vtt")                          # never overwrites
        self.assertEqual((self.v.root / "inbox/ABC sync.vtt").read_bytes(), b"WEBVTT")
        self.assertEqual(self.post("/api/inbox/upload", {"name": "x.exe", "data": b64(b"MZ")})[0], 415)
        self.assertEqual(self.post("/api/inbox/upload", {"name": "big.txt", "data": b64(b"a" * (25 * 1024 * 1024 + 1))})[0], 413)
        for n in ("ABC sync.vtt", "ABC sync (2).vtt"):
            (self.v.root / "inbox" / n).unlink()

    def test_image_upload(self):
        """Add image (BL-12): PNG or JPEG only, 2 MB at most, only into system/staging/uploads/."""
        import base64
        png = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 20).decode()
        self.assertEqual(self.post("/api/fs", {"op": "upload", "path": "system/staging/uploads/a.png", "data": png})[0], 200)
        self.assertTrue((self.v.root / "system/staging/uploads/a.png").read_bytes().startswith(b"\x89PNG"))
        text = base64.b64encode(b"not an image").decode()
        self.assertEqual(self.post("/api/fs", {"op": "upload", "path": "system/staging/uploads/b.png", "data": text})[0], 415)
        big = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * (2 * 1024 * 1024)).decode()
        self.assertEqual(self.post("/api/fs", {"op": "upload", "path": "system/staging/uploads/c.png", "data": big})[0], 413)
        for bad in ("projects/ABC/images/x.png", "system/staging/uploads/x.svg", "system/staging/uploads/../x.png"):
            self.assertEqual(self.post("/api/fs", {"op": "upload", "path": bad, "data": png})[0], 403)

    def test_chat_history_kept_in_the_vault(self):
        """BL-20: each exchange is kept in system/staging/ask/<chat>.json; History lists and reopens it."""
        (self.v.root / "system/staging/ask/sess-1.json").unlink(missing_ok=True)   # the fake always answers as sess-1
        first = self.ask({"message": "What's overdue for ABC?"})[-1]
        self.assertEqual(first["chat"], "sess-1")                               # a new chat is named by its session
        self.ask({"message": "And for DEF?", "session": "sess-1", "chat": "sess-1"})
        rec = json.loads((self.v.root / "system/staging/ask/sess-1.json").read_text())
        self.assertEqual(rec["title"], "What's overdue for ABC?")
        self.assertEqual([m["who"] for m in rec["messages"]][-4:], ["you", "creaite", "you", "creaite"])
        self.assertEqual(rec["messages"][-1]["steps"], ["Running tracker.py read actions"])
        status, listing = self.post("/api/chats", {})
        self.assertIn("sess-1", [c["chat"] for c in listing["chats"]])
        status, one = self.post("/api/chat", {"chat": "sess-1"})
        self.assertEqual((status, one["session"]), (200, "sess-1"))
        self.assertEqual(self.post("/api/chat", {"chat": "../tracker"})[0], 404)  # never outside the history folder

    def test_only_ten_chats_kept(self):
        """BL-32: starting an 11th chat deletes the oldest; the list shows at most 10."""
        folder = self.v.root / "system/staging/ask"
        folder.mkdir(parents=True, exist_ok=True)
        for f in folder.glob("*.json"):
            f.unlink()
        for i in range(10):
            (folder / f"old-chat-{i:02d}.json").write_text(json.dumps(
                {"chat": f"old-chat-{i:02d}", "title": f"Q{i}", "updated": f"2026-10-01T09:{i:02d}:00", "messages": []}))
        (self.v.root / "system/staging/ask/sess-1.json").unlink(missing_ok=True)
        self.ask({"message": "A new question"})
        names = sorted(f.stem for f in folder.glob("*.json"))
        self.assertEqual(len(names), 10)
        self.assertNotIn("old-chat-00", names)                                   # the oldest went
        self.assertIn("sess-1", names)
        self.assertEqual(len(self.post("/api/chats", {})[1]["chats"]), 10)


LIVE_SCRIPT = r"""
<script>
(async()=>{ const out={errors:[]}, wait=ms=>new Promise(r=>setTimeout(r,ms));
  try{
    await checkLive(); out.live=LIVE&&viaServer(); out.vaultBtn=!!document.getElementById("vaultBtn");
    // BL-176: a change in the peek is staged (not applied, whatever auto-apply says); Apply applies it, and Undo reverses it
    openRecord("actions","ABC-A-001"); await pkCommit("actions","ABC-A-001",{o:"Omar Ali"},"Owner","",""); out.staged=PKS.length; closePanel();
    await pkApply(); out.afterSave=A.find(a=>a.id==="ABC-A-001").o; out.snack=document.getElementById("snackT").textContent; out.stagedAfter=PKS.length;
    await UNDO(); await wait(300); out.afterUndo=A.find(a=>a.id==="ABC-A-001").o;
    // quick decisions are applied together
    const routine=REV.find(r=>r.kind==="actions"&&r.p); await decide(routine.n,"approved"); await wait(2500);
    out.routineApplied=!REV.some(r=>r.file===routine.file&&r.ref===routine.ref);
    // a draft goes through review.py: its checks answer in the panel
    const draft=REV.find(r=>r.kind==="draft"); await decide(draft.n,"approved"); await wait(1500);
    out.draftMsg=[...document.querySelectorAll("#chLog .msg")].map(m=>m.textContent).join(" | ");
    out.draftButtons=[...document.querySelectorAll("#chLog [data-rv]")].map(b=>b.dataset.rv);
  }catch(e){ out.errors.push(String(e&&e.stack||e)); }
  const pre=document.createElement("pre"); pre.id="result"; pre.textContent=JSON.stringify(out); document.body.appendChild(pre); })();
</script>
"""


class OutsideContentTable(unittest.TestCase):
    """BL-141's table of what marks a run, as the server hands it to reach.start_run. BL-301 (Alan, 15-10-2026): one of Alan's
    notes is exempt; nothing else changed (test_notes_guard.py reads notes, pictures and transcripts through the hook)."""

    def test_the_table(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
        import live_server
        import permissions
        t = live_server.OUTSIDE_CONTENT
        self.assertEqual(sorted(t), ["folders", "notes_exempt", "outside_vault", "tools"])
        self.assertEqual(t["folders"], ["inbox", "transcripts", "documents"])
        self.assertIs(t["outside_vault"], True)
        self.assertIs(t["notes_exempt"], True)
        self.assertEqual(t["tools"], [*permissions.m365_read_tools(), "WebFetch", "WebSearch"])


@unittest.skipUnless(CHROME.exists(), "Google Chrome not installed")
class LivePageTests(unittest.TestCase):
    """The page served live, in headless Chrome: saves applied at once, undo, review checks. (ask creaite's stream is
    tested at the server above and in test_dashboard_editing.py; headless Chrome's simulated clock doesn't advance a
    streamed download.)"""

    @classmethod
    def setUpClass(cls):
        import os
        import shutil
        import tempfile
        cls.v = v = Vault()
        populate(v)
        make_draft(v.root / "system/staging/drafts/Draft minutes.docx")
        fake = v.root / "fake_claude.py"
        fake.write_text(FAKE_CLAUDE)
        fake.chmod(0o755)
        inject = v.root / "inject.html"
        inject.write_text(LIVE_SCRIPT)
        port = free_port()
        env = {**os.environ, "CREAITE_PORT": str(port), "CREAITE_CLAUDE": str(fake), "CREAITE_TEST_INJECT": str(inject)}
        server = subprocess.Popen([sys.executable, str(v.root / "system/scripts/live_server.py")], env=env,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(50):
                try:
                    urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1)
                    break
                except OSError:
                    time.sleep(0.1)
            profile = tempfile.mkdtemp(prefix="creaite-chrome-")
            cmd = [str(CHROME), "--headless", "--disable-gpu", f"--user-data-dir={profile}", "--no-first-run",
                   "--disable-component-update", "--disable-background-networking", "--virtual-time-budget=15000",
                   "--dump-dom", f"http://127.0.0.1:{port}/"]
            try:
                out = subprocess.run(cmd, capture_output=True, timeout=90).stdout
            except subprocess.TimeoutExpired as e:
                out = e.stdout or b""
            shutil.rmtree(profile, ignore_errors=True)
        finally:
            server.terminate()
            server.wait(timeout=10)
        m = re.search(r'<pre id="result">(.*?)</pre>', out.decode("utf-8", "ignore"), re.S)
        assert m, "the live page didn't finish the scripted steps"
        cls.r = json.loads(m.group(1).replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&amp;", "&"))

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def test_live_page(self):
        r = self.r
        self.assertEqual(r["errors"], [])
        self.assertTrue(r["live"])
        self.assertFalse(r["vaultBtn"])                          # no folder access needed when served live
        self.assertEqual((r["staged"], r["stagedAfter"]), (1, 0))   # BL-176: staged, then applied by Apply
        self.assertEqual(r["afterSave"], "Omar Ali")          # applied and reloaded
        self.assertIn("Saved 1 change", r["snack"])
        self.assertNotEqual(r["afterUndo"], "Omar Ali")       # Undo reversed the apply
        self.assertTrue(r["routineApplied"])
        self.assertNotIn("labelled", r["draftMsg"])                  # BL-121: no label question, no label buttons
        self.assertNotIn("unlabelled", r["draftButtons"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
