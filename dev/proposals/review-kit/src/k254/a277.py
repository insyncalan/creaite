"""2.5.4 area (a): #277, a creaite document whose project is not a string. `creaite_doc.check` refuses it, and the six report routes that take a
document (/api/report/match-check, check, save, pick, reshow, approve) answer HTTP 200 with ok:false and one plain sentence: never a fault
(HTTP 500), never the document's text echoed back, and nothing written (the vault's files and the database are the same after as before).
Fictional data only; the canary sits in a section's text.
Each case prints:   ### CASE <name> | LEAK|PASS|HELD|CTRL-FAIL|SKIP | evidence
  LEAK  a non-string project is accepted by check, or a route answers a fault (5xx), ok:true, no sentence, echoes the canary or writes a file
  HELD  creaite refused it with a sentence (the design)      PASS  a control (a string project, no project) behaves as before
Usage: python a277.py <tree root> <variant>      variants: check (creaite_doc.check on its own), routes (the six routes on a live server), all (both)
A tree without the #277 line in creaite_doc.check is judged on what it does, not on its branch name: it shows LEAK (a fault where a refusal belongs)."""
import copy
import hashlib
import json
import sys
import unittest
import urllib.error
from pathlib import Path

ROOT = Path(sys.argv.pop(1))
VARIANT = sys.argv.pop(1)
sys.path.insert(0, str(ROOT / "dev" / "tests"))
sys.path.insert(0, str(ROOT / "system" / "scripts"))
sys.path.insert(0, str(ROOT / "system" / "scripts" / "vendor"))
import test_client_audience as A  # noqa: E402
import creaite_doc  # noqa: E402

CANARY = "KITCANARY277 the quarter's quiet words"
BAD = [("list", ["ABC"]), ("two-item list", ["ABC", "DEF"]), ("empty list", []), ("int", 7), ("float", 7.5), ("dict", {"code": "ABC"}),
       ("nested list", [["ABC"]]), ("true", True), ("false", False)]
DIRECT_ONLY = [("tuple", ("ABC",)), ("bytes", b"ABC"), ("set", {"ABC"})]       # not JSON: only a direct call can carry them
ROUTES = ("match-check", "check", "save", "pick", "reshow", "approve")


def case(name, status, ev=""):
    print(f"### CASE {name} | {status} | {str(ev)[:200]}", flush=True)


class P(A.Audience):
    def tree_state(self):
        """sha of every file in the vault (the database too) except logs: a refusal writes nothing."""
        h = hashlib.sha256()
        for f in sorted(self.v.root.rglob("*")):
            rel = f.relative_to(self.v.root).as_posix()
            if f.is_file() and not rel.startswith(("system/logs/", "system/guard/", ".git/")) and "__pycache__" not in rel:
                h.update(rel.encode())
                try:
                    h.update(f.read_bytes())
                except OSError:
                    pass
        return h.hexdigest()

    def call(self, route, body):
        try:
            return 200, self.post("/api/report/" + route, body)
        except urllib.error.HTTPError as e:
            raw = e.read().decode(errors="replace")
            try:
                return e.code, json.loads(raw)
            except ValueError:
                return e.code, {"raw": raw}

    def test_check(self):
        base = creaite_doc.new("client", "ABC", "Client report", "2026-10-09")
        creaite_doc.check(base)
        for label, bad in BAD + DIRECT_ONLY:
            try:
                creaite_doc.check({**base, "project": bad})
            except creaite_doc.DocError as e:
                case(f"check refuses project {label}", "HELD", str(e)[:100])
            except Exception as e:  # noqa: BLE001
                case(f"check refuses project {label}", "LEAK", f"a fault, not a refusal: {type(e).__name__}: {str(e)[:80]}")
            else:
                case(f"check refuses project {label}", "LEAK", "the document with a non-string project was accepted")
        for label, ok in (("None", None), ("empty string", "")):
            try:
                creaite_doc.check({**base, "project": ok})
                case(f"control: project {label} is not this check's refusal", "PASS", "accepted as before")
            except creaite_doc.DocError as e:
                case(f"control: project {label} is not this check's refusal", "CTRL-FAIL", str(e)[:100])

    def body(self, route, doc):
        sec = next(s["id"] for s in doc["sections"])
        return {"match-check": {"docs": [doc]}, "check": {"doc": doc}, "save": {"doc": doc, "base_version": doc.get("version")},
                "pick": {"doc": doc}, "reshow": {"doc": doc, "section": sec, "refs": []},
                "approve": {"kind": "client", "code": "ABC", "week_ending": A.WEEK, "force": True, "doc": doc,
                            "base_version": doc.get("version")}}[route]

    def test_routes(self):
        d = self.fresh()["doc"]
        d["sections"].append({"id": "free_277", "type": "freetext", "heading": "Notes", "default_heading": "", "hidden": False,
                              "text": CANARY, "audience": "client"})
        d["layout"]["order"] = [s["id"] for s in d["sections"]]
        for route in ROUTES:                                                       # controls first: a string project is not refused for its type
            status, r = self.call(route, self.body(route, copy.deepcopy(d)))
            case(f"control {route}: a string project is answered", "PASS" if status == 200 else "CTRL-FAIL", f"HTTP {status}, ok {r.get('ok')}")
        for label, bad in BAD:
            for route in ROUTES:
                sent = copy.deepcopy(d)
                sent["project"] = bad
                state0 = self.tree_state()
                status, r = self.call(route, self.body(route, sent))
                wrote = self.tree_state() != state0
                raw = json.dumps(r, default=str)
                problems = []
                if status != 200:
                    problems.append(f"HTTP {status}")
                if r.get("ok") is not False:
                    problems.append(f"ok is {r.get('ok')!r}")
                if not str(r.get("message") or "").strip() or r.get("raw") is not None:
                    problems.append("no plain sentence")
                if "Traceback" in raw or "TypeError" in raw or "unhashable" in raw:
                    problems.append("a fault text")
                if CANARY in raw:
                    problems.append("the document's text is echoed")
                if "findings" in r or "sections" in r or "doc" in r:
                    problems.append("a result body")
                if wrote:
                    problems.append("a file was written")
                name = f"{route} with project {label}"
                case(name, "LEAK" if problems else "HELD", "; ".join(problems) if problems else str(r.get("message"))[:100])


if __name__ == "__main__":
    tests = {"check": ["test_check"], "routes": ["test_routes"], "all": ["test_check", "test_routes"]}[VARIANT]
    unittest.main(argv=["x"] + [f"P.{t}" for t in tests], verbosity=0)
