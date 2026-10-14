"""Tests for the live server's search routes (BL-07): /api/search, /api/search/preview, and the Ask run.

Run: python3 dev/tests/test_search_live.py
Starts the live server on a free port in a throwaway vault. Ask uses a stand-in `claude` (CREAITE_CLAUDE) that prints
Claude Code's stream-json format, so no real Claude call is made.
"""
import json
import os
import re
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_dashboard import populate  # noqa: E402
from test_live_server import free_port  # noqa: E402
from test_search import put  # noqa: E402
from test_tracker import ABC, Vault  # noqa: E402


FAKE_CLAUDE = r'''#!/usr/bin/env python3
import json, re, sys, time
args = sys.argv[1:]
message = args[args.index("-p") + 1]
allowed = args[args.index("--allowedTools") + 1]
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init", "session_id": "sess-search-1"})
if "slowly" in message:
    out({"type": "assistant", "message": {"content": [{"type": "text", "text": "Looking."}]}})
    time.sleep(30)
    sys.exit(0)
names = re.findall(r"\[([^\]›]+?\.(?:md|docx|vtt|pdf))( › [^\]]+)?\]", message)
cite = f"[{names[0][0]}{names[0][1]}]" if names else ""
ids = re.findall(r"^(ABC-[A-Z0-9-]+) \(", message, re.M)
text = f"Go-live moved because data access slipped {cite}. Owner: {ids[0] if ids else 'none'} [{ids[0] if ids else ''}]."
facts = {"doc_label": "Document (internal)" in message, "chars": len(message), "write_tools": "tracker.py apply" in allowed,
         "has_rules": "Cite every point" in message}
out({"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}})
out({"type": "assistant", "message": {"content": [{"type": "text", "text": "FACTS " + json.dumps(facts)}]}})
out({"type": "result", "result": text, "session_id": "sess-search-1"})
'''


def events(resp):
    """The server-sent events of a streamed response, until it ends."""
    out = []
    for raw in resp:
        line = raw.decode().strip()
        if line.startswith("data: "):
            out.append(json.loads(line[6:]))
    return out


class SearchLiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = v = Vault()
        populate(v)
        put(v, f"{ABC}/minutes/2026-09-25 Steering.md", "# Decisions\nGo-live moves because data access slipped.\n\n# Action Items\nSara to chase the CIO.")
        put(v, f"{ABC}/reports/2026-10-02 Weekly report.md", "Weekly report. Build slipping; data access is the blocker.")
        put(v, f"{ABC}/documents/Plans/2026-08-01 Plan.md", "Delivery plan. Data access request goes to the client.")
        fake = v.root / "fake_claude.py"
        fake.write_text(FAKE_CLAUDE)
        fake.chmod(0o755)
        cls.port = free_port()
        cls.base = f"http://127.0.0.1:{cls.port}"
        env = {**os.environ, "CREAITE_PORT": str(cls.port), "CREAITE_CLAUDE": str(fake)}
        cls.proc = subprocess.Popen([sys.executable, str(v.root / "system/scripts/live_server.py")], env=env,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for _ in range(50):
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

    def get(self, path, token=None):
        req = urllib.request.Request(self.base + path, headers={"X-Creaite-Token": token or self.token})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def post(self, path, body):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def search(self, q, **extra):
        return self.get("/api/search?" + urllib.parse.urlencode({"q": q, **extra}))

    def test_grouped_results(self):
        status, r = self.search("data access")
        self.assertEqual(status, 200)
        self.assertTrue(r["ok"])
        self.assertEqual(set(r["groups"]), {"items", "meetings", "reports", "documents"})
        self.assertEqual([x["title"] for x in r["groups"]["reports"]], ["2026-10-02 Weekly report"])
        self.assertEqual([x["title"] for x in r["groups"]["documents"]], ["2026-08-01 Plan"])
        self.assertEqual([x["title"] for x in r["groups"]["meetings"]], ["2026-09-25 Steering"])   # found without `index`
        self.assertTrue(any(x["id"] == "ABC-003" for x in r["groups"]["items"]))
        self.assertIn("<mark>", r["groups"]["reports"][0]["snippet"])

    def test_filters_chips_and_explicit_params(self):
        r = self.search("risks ABC data")[1]
        self.assertEqual([(c["kind"], c["value"]) for c in r["chips"]], [("type", "Risk"), ("project", "ABC")])
        self.assertEqual([x["id"] for x in r["groups"]["items"]], ["ABC-003"])
        r = self.search("data", project="DEF")[1]
        self.assertEqual(r["groups"]["items"], [])
        self.assertEqual(self.search("data", kind="report", **{"from": "2026-10-01"})[1]["groups"]["reports"][0]["kind"], "report")
        r = self.search("risks ABC data", skip="type:Risk,project:ABC")[1]
        self.assertEqual(r["chips"], [])
        self.assertEqual([c["kind"] for c in self.search("ABC", parse="0")[1]["chips"]], [])

    def test_bad_requests_and_the_token(self):
        self.assertEqual(self.search("x", **{"from": "yesterday"})[0], 400)
        self.assertEqual(self.search("x" * 400)[0], 400)
        self.assertEqual(self.get("/api/search?q=data", token="wrong")[0], 403)
        self.assertEqual(self.search("")[1]["totals"], {"items": 0, "meetings": 0, "reports": 0, "documents": 0})

    def test_it_is_read_only(self):
        before = (self.v.root / "system/tracker.db").read_bytes()
        staged = sorted(p.name for p in (self.v.root / "system/staging").iterdir())
        self.search("data access")
        self.assertEqual(sorted(p.name for p in (self.v.root / "system/staging").iterdir()), staged)
        self.assertEqual((self.v.root / "system/tracker.db").read_bytes(), before)       # the index is already current

    def test_preview(self):
        s, r = self.post("/api/search/preview", {"path": f"{ABC}/minutes/2026-09-25 Steering.md", "q": "data access"})
        self.assertTrue(r["ok"])
        self.assertIn("<mark>data</mark> <mark>access</mark>", r["html"])
        self.assertFalse(self.post("/api/search/preview", {"path": "system/tracker.db"})[1]["ok"])


    # ── part 2: the Ask run, with a stand-in `claude` ──

    def stream(self, body, timeout=60):
        req = urllib.request.Request(self.base + "/api/search/ask", data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return events(r)

    def test_answer_streams_with_sources_and_is_read_only(self):
        ev = self.stream({"q": "why did go-live move?"})
        self.assertEqual(ev[0]["type"], "sources")
        self.assertEqual(ev[0]["question"], "why did go-live move?")
        names = {s["name"] for s in ev[0]["sources"]}
        self.assertIn("2026-09-25 Steering.md", names)                                         # a source the page can link
        self.assertTrue(any(s["kind"] == "item" for s in ev[0]["sources"]))
        texts = [e["text"] for e in ev if e["type"] == "text"]
        self.assertIn("[2026-09-25 Steering.md", texts[0])                                      # a citation, from the gathered file
        facts = json.loads(texts[1].replace("FACTS ", ""))
        self.assertEqual(facts, {"doc_label": True, "chars": facts["chars"], "write_tools": False, "has_rules": True})
        self.assertLess(facts["chars"], 41000)
        done = ev[-1]
        self.assertEqual((done["type"], done["session"]), ("done", "sess-search-1"))

    def test_it_is_not_saved_as_a_chat(self):
        before = self.post("/api/chats", {})[1]["chats"]
        self.stream({"q": "who owns data access?"})
        self.assertEqual(self.post("/api/chats", {})[1]["chats"], before)          # no new chat file

    def test_stop_and_one_at_a_time(self):
        import threading
        got = []

        def run():
            try:
                got.extend(self.stream({"q": "tell me slowly", "run": "q-stoptest"}))
            except Exception as e:  # noqa: BLE001
                got.append(e)
        t = threading.Thread(target=run)
        t.start()
        time.sleep(1.5)
        status, body = self.post("/api/search/ask", {"q": "another question?"})
        self.assertEqual((status, body.get("busy")), (409, True))                              # one run at a time
        self.assertTrue(self.post("/api/ask/stop", {"run": "q-stoptest"})[1]["ok"])
        t.join(timeout=20)
        self.assertEqual(got[-2]["type"], "stopped")

    def test_reattach_replays_the_run(self):
        self.stream({"q": "who owns data access?", "run": "q-replay"})
        req = urllib.request.Request(self.base + "/api/ask/attach", data=json.dumps({"run": "q-replay"}).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        with urllib.request.urlopen(req, timeout=30) as r:
            ev = events(r)
        self.assertEqual([e["type"] for e in ev][:2], ["sources", "text"])
        self.assertEqual(ev[-1]["type"], "done")

    def test_continue_makes_a_chat_with_the_same_session(self):
        status, r = self.post("/api/search/continue", {"q": "why did go-live move?", "answer": "Because data access slipped.",
                                                        "session": "sess-search-1"})
        self.assertTrue(r["ok"])
        self.assertEqual(r["chat"], "sess-search-1")
        chat = self.post("/api/chat", {"chat": r["chat"]})[1]
        self.assertEqual([m["who"] for m in chat["messages"]], ["you", "creaite"])
        self.assertEqual(chat["messages"][1]["text"], "Because data access slipped.")
        self.assertEqual(chat["session"], "sess-search-1")
        self.assertEqual(self.post("/api/search/continue", {"q": "", "answer": ""})[0], 400)

    def test_bad_questions(self):
        self.assertEqual(self.post("/api/search/ask", {"q": ""})[0], 400)
        self.assertEqual(self.post("/api/search/ask", {"q": "x" * 700})[0], 400)


if __name__ == "__main__":
    unittest.main()
