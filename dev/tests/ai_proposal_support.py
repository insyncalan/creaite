"""#132 round 1 and round 2 proposals (dev/proposals/ai-models/round1, round2): what their tests share. Not a test file itself.

The proposal's guarded changes are diff files, not applied to this branch. Each test builds a throwaway vault from this
branch (test_tracker.make_vault), applies the diffs it is about there with `git apply` (in order), and runs its checks in a
subprocess against that vault's scripts, so nothing here imports the patched files into the test process and nothing touches
this repository's own files.

CREAITE_PROPOSAL_UNPATCHED=1 builds the same vault without applying any diff: every test of the proposal must then fail
(that is how "each test fails when its hunk is reverted" is checked; see the README).

Round 2 (vault2) stacks on round 1: round 1's diffs except G1c (R1_BASE; test_guard_pinned must pass unchanged without it), then
the round 2 diffs named, in order. Under CREAITE_PROPOSAL_UNPATCHED=1 a round 2 vault gets round 1 only. CREAITE_PROPOSAL_DIFFS2
points at a folder of round 2 diffs with one hunk left out (the hunk-by-hunk check).
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import REPO, make_vault  # noqa: E402

ROUND1 = Path(os.environ.get("CREAITE_PROPOSAL_DIFFS") or REPO / "dev" / "proposals" / "ai-models" / "round1")   # the
#                         override is for the hunk-by-hunk check only (a folder of the same diffs with one hunk left out)
UNPATCHED = os.environ.get("CREAITE_PROPOSAL_UNPATCHED") == "1"
ROUND2 = Path(os.environ.get("CREAITE_PROPOSAL_DIFFS2") or REPO / "dev" / "proposals" / "ai-models" / "round2")
R1_BASE = ("g1-key-store", "g2-model-list", "g3-chosen-model", "g5-confidential-only-claude")
R2_ALL = ("g4-direct-call", "g6-limit-card", "g7-quick-edit-retry", "g9-health", "g10-fake-switch-and-tested-key",
          "s1-search-never-reads")


def diff_path(name):
    """The proposal's diff file by its short name (g1-key-store, …; "r2/g4-direct-call" is round 2's)."""
    return ROUND2 / f"{name[3:]}.diff" if name.startswith("r2/") else ROUND1 / f"{name}.diff"


def apply(root, names):
    """Apply the proposal's diffs, in order, to a vault's files (root holds system/scripts/…). Raises on any that won't apply."""
    for name in names:
        r = subprocess.run(["git", "apply", "--whitespace=nowarn", str(diff_path(name))], cwd=root, capture_output=True,
                           text=True)
        if r.returncode != 0:
            raise AssertionError(f"{name}.diff doesn't apply:\n{r.stderr}")


def vault(*names, patched=True):
    """A throwaway vault with the named diffs applied (none when patched is False, or under CREAITE_PROPOSAL_UNPATCHED=1)."""
    root = make_vault()
    if patched and not UNPATCHED:
        apply(root, names)
    return root


def vault2(*names, r1=R1_BASE):
    """A throwaway vault with round 1's diffs (R1_BASE: all but G1c) and then the named round 2 diffs (in R2_ALL's order, each
    with the ones before it). Under CREAITE_PROPOSAL_UNPATCHED=1, round 1's only."""
    root = make_vault()
    upto = max((R2_ALL.index(n) for n in names), default=-1)
    apply(root, list(r1) + ([] if UNPATCHED else [f"r2/{n}" for n in R2_ALL[:upto + 1]]))
    return root


def populated(root):
    """The vault with test_dashboard's small fictional portfolio (ABC Example Programme, DEF Digital Enablement) in its tracker."""
    from test_dashboard import populate
    from test_tracker import Vault
    v = Vault.__new__(Vault)
    v.root = root
    populate(v)
    return root


def fake_home():
    """A stand-in home folder holding the secrets the never list names (an SSH key, a keychain file): nothing real."""
    home = Path(tempfile.mkdtemp(prefix="creaite-home-"))
    for rel in (".ssh/id_rsa", "Library/Keychains/login.keychain-db", "Documents/notes.txt"):
        (home / rel).parent.mkdir(parents=True, exist_ok=True)
        (home / rel).write_text("stand-in, not a secret\n")
    return home


def run_py(root, code, env=None, timeout=120):
    """Run Python code in the vault (cwd = the vault, its system/scripts first on the path) and return what it printed last,
    as JSON."""
    prelude = "import sys, json, os\nsys.path.insert(0, 'system/scripts')\n"
    e = {k: v for k, v in os.environ.items() if k not in ("CREAITE_FAKE_PROVIDERS",)}
    e.update(env or {})
    r = subprocess.run([sys.executable, "-c", prelude + code], cwd=root, capture_output=True, text=True, env=e, timeout=timeout)
    if r.returncode != 0:
        raise AssertionError(f"the check failed in the vault:\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")
    lines = [x for x in r.stdout.splitlines() if x.strip()]
    return json.loads(lines[-1]) if lines else None


# ── Round 2: a fake provider over HTTPS on 127.0.0.1 (no real provider, no network) ─────────────────────────────────────────
KEY = "fake-good-0123456789abcdefTESTONLY"         # a stand-in key: never a real one


def make_cert():
    """(folder, cert, key): a certificate for 127.0.0.1 made by openssl for this test, trusted only by a context given it."""
    import shutil
    tmp = Path(tempfile.mkdtemp(prefix="creaite-tls-"))
    cert, key = str(tmp / "cert.pem"), str(tmp / "key.pem")
    subprocess.run([shutil.which("openssl") or "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", key,
                    "-out", cert, "-days", "2", "-subj", "/CN=127.0.0.1", "-addext", "subjectAltName=IP:127.0.0.1"],
                   check=True, capture_output=True)
    return tmp, cert, key


def chat_server(cert, key):
    """A fake chat provider: POST answers by its `mode` ("ok" with `reply`, "401", "429", "500", "redirect", "big", "notjson",
    "empty", "slow"); every request is kept in `seen` as {method, path, headers, body}. Call .shutdown() when done."""
    import http.server
    import socketserver
    import ssl
    import threading
    import time

    class Fake(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            srv = self.server
            raw = self.rfile.read(int(self.headers.get("Content-Length") or 0))
            srv.seen.append({"method": "POST", "path": self.path, "headers": dict(self.headers), "body": raw.decode("utf-8")})
            mode = srv.mode
            if mode == "slow":
                time.sleep(3)
            if mode in ("401", "403", "429", "500"):
                return self.answer(int(mode), json.dumps({"error": {"message": f"echo {raw.decode()[:200]}"}}).encode())
            if mode == "redirect":
                return self.answer(307, b"", {"Location": "https://other.invalid/v1/chat/completions"})
            if mode == "big":
                return self.answer(200, json.dumps({"choices": [{"message": {"content": "x" * 400_000}}]}).encode())
            if mode == "notjson":
                return self.answer(200, b"<html>hello</html>")
            if mode == "empty":
                return self.answer(200, json.dumps({"choices": [{"message": {"content": ""}}]}).encode())
            body = {"choices": [{"message": {"role": "assistant", "content": srv.reply}}],
                    "usage": {"prompt_tokens": 120, "completion_tokens": 40}}
            return self.answer(200, json.dumps(body).encode())

        def answer(self, code, body, headers=None):
            self.send_response(code)
            for k, v in (headers or {}).items():
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
        daemon_threads = True

    srv = Server(("127.0.0.1", 0), Fake)
    srv.seen, srv.mode, srv.reply = [], "ok", "<<<SUGGESTION\nA tidier sentence.\nSUGGESTION>>>"
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert, key)
    srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    srv.base = f"https://127.0.0.1:{srv.server_address[1]}"
    return srv


# Python run in the vault (run_py): OpenAI "connected" with test stand-ins (an in-memory store holding KEY, the fake lister),
# the direct call pointed at the fake server (its certificate trusted only here), `jobs` chosen and accepted, written to the
# vault's settings so the live server reads them; claude -p replaced by a recorder (`launched`) that answers `CLAUDE_REPLY`.
OPENAI_SETUP = r'''
import ssl, io, time, threading, providers as pv, settings_catalogue as sc, paths, live_server as L
a = json.loads(%r)
p = paths.ROOT / "system" / "config" / "settings.json"
cfg = json.loads(p.read_text())
cfg.setdefault("ai", {})["providers"] = pv.connect_changes("openai", ["fake-flagship", "fake-small"], ["fake-flagship", "fake-small"],
                                                         cfg)["ai.providers"]
cfg["ai"]["jobs"] = dict(a.get("jobs") or {})                   # the rest at their defaults
cfg["ai"]["accepted_weaker"] = [f"{j}={m}" for j, m in (a.get("jobs") or {}).items()]
cfg["ai"]["on_limit"] = a.get("on_limit", "ask")
p.write_text(json.dumps(cfg))
store = pv.MemoryStore(); store.put("openai", a["key"])
pv._BACKEND["pair"] = (store, pv.FakeLister())
pv._DIRECT["caller"] = pv.DirectCaller(base={"openai": a["base"]}, context=ssl.create_default_context(cafile=a["cert"]),
                                       timeout=a.get("timeout", 5))
launched = []
CLAUDE_REPLY = a.get("claude_reply", ["<<<SUGGESTION\nClaude's tidier sentence.\nSUGGESTION>>>"])
class Proc:
    def __init__(self, cmd, cwd=None, env=None, **kw):
        launched.append(cmd)
        reply = CLAUDE_REPLY[min(len(launched), len(CLAUDE_REPLY)) - 1]
        lines = reply if isinstance(reply, list) else [{"type": "assistant", "message": {"content": [{"type": "text", "text": reply}]}},
                                                         {"type": "result", "result": reply}]
        self.stdout = io.StringIO("".join(json.dumps(x) + "\n" for x in lines))
        self.stderr, self.returncode, self.pid = io.StringIO(""), 0, 0
    def wait(self, timeout=None): return 0
    def poll(self): return 0
    def kill(self): pass
    def terminate(self): pass
REAL_POPEN = L.subprocess.Popen
def popen(cmd, *args, **kw):
    """claude -p goes to the recorder; anything else (creaite's own scripts) runs."""
    return Proc(cmd, **kw) if isinstance(cmd, list) and cmd[1:2] == ["-p"] else REAL_POPEN(cmd, *args, **kw)
L.subprocess.Popen = popen
class H:
    def __init__(self): self.sent, self.events = [], None
    def send(self, code, body): self.sent.append([code, body])
    def follow(self, r):
        end = time.time() + 30
        while not r.done and time.time() < end:
            time.sleep(0.05)
        self.events = [e for e in r.events]
def suggest(req):
    h = H(); L.edit_ai_route(h, dict({"option": "rewrite", "place": "notes", "code": "ABC"}, **req)); return h
'''


def openai_setup(srv, cert, jobs=None, **more):
    """OPENAI_SETUP filled in for one test's vault."""
    return OPENAI_SETUP % json.dumps(dict({"base": srv.base, "cert": cert, "key": KEY, "jobs": jobs or {}}, **more))
