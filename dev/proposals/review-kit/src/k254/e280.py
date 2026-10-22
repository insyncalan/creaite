"""2.5.4 area (e): #280, `{only: <name>}` on POST /api/apply (a save applies only the proposal it wrote). The value is a staged proposal's file name
and nothing else: whatever else it holds (a path in any form, an option or a type that is not a name, a staging file that is not a proposal, a look-alike
name) the route answers ok:false "... nothing was applied" and writes nothing: no apply, no backup, no change to the database, to any staged
proposal, or to a file of the same name in the vault ROOT (a planted namesake, as an ask creaite run could make: a root .json is an ordinary create).
Forty representative values (12 path forms, 12 types and options, 7 staging files that are not proposals, 7 look-alikes, 2 root-only names), each sent as
{only: x} and 8 of them also with hold_peek; then the exact name as a control: only that proposal is applied, never its root namesake.
Each case prints:   ### CASE <name> | LEAK|PASS|HELD|CTRL-FAIL|SKIP | evidence
  LEAK  a value applied something (the evidence says what: the database, a staged proposal, the root namesake, a new file)
  HELD  the route refused it (nothing changed)    CTRL-FAIL  the exact name was not applied alone
  SKIP  the tree's live_server.py has no `only` (before #280): judged with dev/proposals/280/live_server.py.diff applied to the VAULT'S copy
Usage: python e280.py <tree root> <variant>      variants: only"""
import hashlib
import json
import os
import re
import socket
import sqlite3
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request
from contextlib import closing
from pathlib import Path

ROOT = Path(sys.argv.pop(1))
VARIANT = sys.argv.pop(1)
sys.path.insert(0, str(ROOT / "dev" / "tests"))
sys.path.insert(0, str(ROOT / "system" / "scripts"))
sys.path.insert(0, str(ROOT / "system" / "scripts" / "vendor"))
from test_dashboard import populate  # noqa: E402
from test_tracker import Vault  # noqa: E402
import kitshim  # noqa: E402

N1 = "proposed-2026-10-21-120000-dashboard.json"          # the named save (ABC-A-001)
N2 = "proposed-2026-10-21-130000-dashboard.json"          # another staged save (ABC-A-002): never touched by an `only` for N1
ROOTONLY = "proposed-2026-10-21-140000-dashboard.json"    # a file in the vault ROOT only (ABC-A-003): never applied
OLD = "proposed-2026-10-20-1757-2.json"                   # an older staged proposal with an invalid approved item
SKIPDIRS = ("system/scripts/", "system/templates/", "system/branding/", "system/logs/", "system/guard/", ".git/")


def case(name, status, ev=""):
    print(f"### CASE {name} | {status} | {str(ev)[:200]}", flush=True)


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def values(root):
    return [
        # path forms
        ("path: system/staging/<name>", "system/staging/" + N1), ("path: ./<name>", "./" + N1), ("path: ../staging/<name>", "../staging/" + N1),
        ("path: system/staging/../../<name> (the root namesake)", "system/staging/../../" + N1), ("path: absolute staging path", f"{root}/system/staging/{N1}"),
        ("path: absolute root namesake", f"{root}/{N1}"), ("path: <name>/", N1 + "/"), ("path: ..\\<name>", "..\\" + N1),
        ("path: ../tracker.db", "../tracker.db"), ("path: system/tracker.db", "system/tracker.db"), ("path: %2e%2e/<name>", "%2e%2e/" + N1),
        ("path: ~/<name>", "~/" + N1),
        # types and options
        ("type: true", True), ("type: 1", 1), ("type: 0", 0), ("type: null", None), ("type: [name]", [N1]), ("type: {name}", {"name": N1}),
        ("type: [name, name2]", [N1, N2]), ("type: empty string", ""), ("type: a space", " "), ("type: 1.5", 1.5), ("type: name + NUL", N1 + "\x00"),
        ("type: name + newline", N1 + "\n"),
        # staging files that are not proposals
        ("staging: last-sweep.txt", "last-sweep.txt"), ("staging: calendar.json", "calendar.json"), ("staging: vip.json", "vip.json"),
        ("staging: run-log.txt", "run-log.txt"), ("staging: proposed-notes.txt", "proposed-notes.txt"), ("staging: applied/<name>", "applied/" + N1),
        ("staging: drafts/x.json", "drafts/x.json"),
        # look-alikes
        ("look-alike: upper case", N1.upper()), ("look-alike: <name>.bak", N1 + ".bak"), ("look-alike: <name> + space", N1 + " "),
        ("look-alike: space + <name>", " " + N1), ("look-alike: proposed-.json", "proposed-.json"),
        ("look-alike: Proposed-...", N1.replace("proposed", "Proposed", 1)), ("look-alike: .JSON", N1[:-5] + ".JSON"),
        # root-only
        ("root only: a root file with no staged namesake", ROOTONLY), ("root only: ...json/", ROOTONLY + "/"),
    ]


class P(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = v = Vault()
        populate(v)
        live = v.root / "system/scripts/live_server.py"
        cls.has_only = '"only" in req' in live.read_text(encoding="utf-8")
        cls.patched = ""
        if not cls.has_only:
            ok, why = kitshim.apply_280(v.root, ROOT, "live_server_only")
            cls.patched = "live_server.py.diff applied to the vault's copy" if ok else "NOT applied: " + why
        cls.port = free_port()
        cls.base = f"http://127.0.0.1:{cls.port}"
        env = {**os.environ, "CREAITE_PORT": str(cls.port)}
        cls.proc = subprocess.Popen([sys.executable, str(v.root / "system/scripts/live_server.py")], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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

    def post(self, path, body):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            raw = e.read().decode(errors="replace")
            try:
                return e.code, json.loads(raw)
            except ValueError:
                return e.code, {"raw": raw}

    # ── state ────────────────────────────────────────────────────────────────────────────────────────────────────────────
    def files(self):
        out = {}
        for f in self.v.root.rglob("*"):
            rel = f.relative_to(self.v.root).as_posix()
            if f.is_file() and not rel.startswith(SKIPDIRS) and "__pycache__" not in rel and f.suffix != ".tmp":
                try:
                    out[rel] = f.read_bytes()
                except OSError:
                    pass
        return out

    def ids(self):
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            return [r[0] for r in con.execute("SELECT id FROM actions ORDER BY id LIMIT 3")]

    def owner(self, id_):
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            r = con.execute("SELECT owner FROM actions WHERE id=?", (id_,)).fetchone()
        return r[0] if r else None

    def change(self, id_, owner):
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            ts = con.execute("SELECT updated_at FROM actions WHERE id=?", (id_,)).fetchone()[0]
        return {"n": 1, "op": "update", "table": "actions", "id": id_, "changes": {"owner": owner}, "based_on": ts, "match": "strong",
                "flags": [], "decision": "approved"}

    def prop(self, id_, owner):
        return json.dumps({"created": "2026-10-21T12:00:00", "source_run": "dashboard", "files": [], "items": [self.change(id_, owner)]})

    def plant(self):
        st = self.v.root / "system/staging"
        (st / N1).write_text(self.prop(self.I1, "Named One"), encoding="utf-8")
        (st / N2).write_text(self.prop(self.I2, "Other Staged"), encoding="utf-8")
        (self.v.root / N1).write_text(self.prop(self.I3, "From Root"), encoding="utf-8")            # same name as the staged save, in the ROOT
        (self.v.root / ROOTONLY).write_text(self.prop(self.I3, "Root Only"), encoding="utf-8")
        (st / OLD).write_text(json.dumps({"created": "2026-10-20T17:57:00", "source_run": "minutes", "files": [],
                                          "meeting": {"key": "fp:2026-10-20|supplier checkpoint", "title": "Supplier checkpoint", "date": "2026-10-20",
                                                      "projects": ["ABC"], "minutes_decision": "pending"},
                                          "items": [{"n": 1, "op": "new", "table": "decisions", "match": "strong", "flags": [], "decision": "approved",
                                                     "values": {"project": "ABC", "decision": "Go with option B", "made_by": "Alan Carter",
                                                                "raised": "2026-10-20", "source": "minutes Supplier checkpoint"}}]}), encoding="utf-8")
        (st / "calendar.json").write_text("{}", encoding="utf-8")
        (st / "vip.json").write_text("[]", encoding="utf-8")
        (st / "proposed-notes.txt").write_text("not a proposal", encoding="utf-8")

    def restore(self, snap):
        now = self.files()
        for rel in set(now) - set(snap):
            (self.v.root / rel).unlink(missing_ok=True)
        for rel, raw in snap.items():
            f = self.v.root / rel
            if now.get(rel) != raw:
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_bytes(raw)

    def what_changed(self, before):
        after = self.files()
        out = []
        for rel in sorted(set(before) | set(after)):
            if before.get(rel) != after.get(rel):
                out.append(rel + (" (new)" if rel not in before else " (gone)" if rel not in after else ""))
        return out

    def test_only(self):
        if not self.has_only:
            case("the route takes {only}", "SKIP", "this tree's live_server.py has no `only` (before #280); judged with " + self.patched)
        tag = "" if self.has_only else " (live_server.py.diff applied to the vault's copy)"
        if self.patched.startswith("NOT"):
            case("the route takes {only}" + tag, "SKIP", self.patched)
            return
        self.I1, self.I2, self.I3 = self.ids()
        self.plant()
        snap = self.files()
        a1, a2, a3 = (self.owner(i) for i in (self.I1, self.I2, self.I3))
        for label, v in values(self.v.root):
            for mode, body in (("only", {"only": v}), ("hold_peek+only", {"hold_peek": True, "only": v})):
                if mode != "only" and not (label.startswith(("path: system/staging/<", "path: system/staging/../", "path: absolute root", "staging: applied", "type: [name]",
                                                             "look-alike: upper", "root only: a root", "type: true"))):
                    continue
                try:
                    status, r = self.post("/api/apply", body)
                except (urllib.error.URLError, OSError) as e:
                    case(f"{mode} {label}", "LEAK", f"the server failed: {e}"[:150])
                    self.restore(snap)
                    continue
                changed = self.what_changed(snap)
                owners = [self.owner(i) for i in (self.I1, self.I2, self.I3)]
                wrote = changed or owners != [a1, a2, a3]
                msg = str(r.get("message") or "")
                refused = status == 200 and r.get("ok") is False and "nothing was applied" in msg
                if wrote or r.get("ok"):
                    case(f"{mode} {label}", "LEAK", f"HTTP {status}, ok {r.get('ok')}; changed {changed[:4]}; owners {owners}"[:195])
                    self.restore(snap)
                elif refused:
                    case(f"{mode} {label}", "HELD", msg[:100])
                else:
                    case(f"{mode} {label}", "HELD", f"HTTP {status} {msg[:100] or str(r)[:100]} (nothing written)")
        # the exact name: only that proposal, never its root namesake
        for mode, body in (("only", {"only": N1}), ("hold_peek+only", {"hold_peek": True, "only": N1})):
            self.restore(snap)
            status, r = self.post("/api/apply", body)
            owners = [self.owner(i) for i in (self.I1, self.I2, self.I3)]
            changed = self.what_changed(snap)
            st = self.v.root / "system/staging"
            alone = (owners[0] == "Named One" and owners[1] == a2 and owners[2] == a3 and (st / N2).is_file() and (st / OLD).is_file()
                     and (self.v.root / N1).read_text(encoding="utf-8") == self.prop(self.I3, "From Root") and (self.v.root / ROOTONLY).is_file())
            case(f"control {mode}: the exact name applies that proposal alone", "PASS" if r.get("ok") and alone else "CTRL-FAIL" if not owners[2] in ("From Root", "Root Only") else "LEAK",
                 f"owners {owners}; changed {changed[:4]}" if not (r.get("ok") and alone) else f"{self.I1} {owners[0]!r}; the other staged save, the older proposal and both root files are untouched")
            if owners[2] in ("From Root", "Root Only"):
                case(f"{mode}: the planted root namesake is never applied", "LEAK", f"{self.I3} owner is {owners[2]!r}")
            else:
                case(f"{mode}: the planted root namesake is never applied", "PASS", f"{self.I3} owner is still {owners[2]!r}")
        self.restore(snap)


if __name__ == "__main__":
    unittest.main(argv=["x", "P.test_only"], verbosity=0)
