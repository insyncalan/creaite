"""#346: a run whose set-up fails leaves nothing behind (no guard record, no stray process) and the next ask runs.

  python3 -I probe_346_runsetup.py NEW_ZIP BASE_ZIP WORK_DIR [--label 2.6.4] [--control] [--keep]

  a  Real live server: an ask whose set-up fails (a NUL in the message makes the process start refuse it) is answered with
     a plain message, leaves no system/guard/run.json, /api/ask/running shows no run, and the next ask runs (not "busy").
     This part also passes on the base, so on its own it does not discriminate.
  b  The vault's own live_server.py, imported in a child process with a stand-in Popen and a run table that refuses entries
     (the set-up fails after the process started): the fixed code leaves no run.json and ends the process; the base leaves
     run.json behind and ends nothing. This is the check that discriminates.
Expected on 2.6.4 (base 2.6.3): all PASS. With --control the b check FAILS (run.json left behind, process not ended).
No real claude is used; the child never starts a server.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402
from common import rec  # noqa: E402

CHILD = r'''
import sys, json, tempfile, os
from pathlib import Path
from unittest import mock
vault = Path(sys.argv[1]); scratch = Path(sys.argv[2])
os.environ["TMPDIR"] = str(scratch)
sys.path.insert(0, str(vault / "system/scripts"))
os.chdir(vault)
import live_server
tmp = Path(tempfile.mkdtemp(dir=scratch)); (tmp / "chats").mkdir()
ended = []
class Proc:
    stdout = stderr = None; pid = 999999
class Full(dict):
    def __setitem__(self, k, v): raise RuntimeError("late")
patches = [mock.patch.object(live_server.reach, "GUARD", tmp), mock.patch.object(live_server.reach, "RUN_FILE", tmp / "run.json"),
           mock.patch.object(live_server.reach, "SESSIONS_FILE", tmp / "marked.json"), mock.patch.object(live_server.paths, "ASK_CHATS", tmp / "chats"),
           mock.patch.object(live_server, "run_usage", lambda *a, **k: None), mock.patch.object(live_server.threading, "Thread"),
           mock.patch.object(live_server.subprocess, "Popen", lambda cmd, **k: Proc()), mock.patch.object(live_server, "RUNS", Full()),
           mock.patch.object(live_server, "end_process", lambda p: ended.append(p))]
for p in patches: p.start()
out = {"setup_failed": False}
try:
    live_server.Run("r-346", "hello", None, "chat-x", None)
except RuntimeError as e:
    out = {"setup_failed": True, "error": str(e), "run_json_left_behind": (tmp / "run.json").exists(), "process_ended": bool(ended)}
print("CHILD " + json.dumps(out))
'''


def main():
    a = C.parse(__doc__)
    v = C.V("p346", identity="Sam Reid", calendar=False)

    def calls():
        f = v.r.dir / "fake_claude_calls.log"
        return len(f.read_text().splitlines()) if f.exists() else 0

    try:
        v.start(browser=False)
        runjson = v.vault / "system/guard/run.json"
        c, t = v.post("/api/ask", {"message": "hello\u0000there", "chat": "c1"}, timeout=30)
        time.sleep(1)
        c2, r = v.pj("/api/ask/running", {})
        left = runjson.exists()
        n0 = calls()
        c3, t3 = v.post("/api/ask", {"message": "a normal question", "chat": "c2"}, timeout=40)
        time.sleep(2)
        busy = "busy" in t3.lower() or "already" in t3.lower() or c3 == 409
        rec("346a real server: a failed set-up leaves no guard record and the next ask runs",
            not left and c3 == 200 and not busy and calls() == n0 + 1,
            f"failed ask HTTP {c} {t[:90]!r}; run.json left {left}; /api/ask/running={str(r)[:80]}; next ask HTTP {c3}, stand-in calls {calls() - n0}")
    finally:
        v.close()

    # b: in-process, no server
    v = C.V("p346b", identity=None, calendar=False)
    try:
        child = v.r.dir / "child346.py"
        child.write_text(CHILD)
        scratch = v.r.dir / "tmp"
        p = subprocess.run([sys.executable, "-I", str(child), str(v.vault), str(scratch)], cwd=v.vault, capture_output=True, text=True, env=v.script_env(), timeout=120)
        line = [x for x in p.stdout.splitlines() if x.startswith("CHILD ")]
        out = json.loads(line[0][6:]) if line else {}
        rec("346b set-up fails after the process started: no run.json left behind and the process is ended",
            out.get("setup_failed") is True and out.get("run_json_left_behind") is False and out.get("process_ended") is True,
            f"{out or (p.stdout + p.stderr)[-300:]}")
    finally:
        v.close()
    return C.finish(a)


if __name__ == "__main__":
    C.run(main)
