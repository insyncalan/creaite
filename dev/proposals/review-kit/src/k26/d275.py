"""2.6 area (d): Track from Review (#275) and the Minutes view v2 (#268). A line Alan CROSSES (out of the minutes) or leaves with NEITHER
(kept in the minutes only, no work item) in the minutes' Track column must not become a registered work item by any path, and a crossed
line must not appear in the follow-up email, the draft's Word/HTML/PDF export, the filed minutes or any client output made from the
tracker. A promise has no row in the minutes, so Approve minutes never registers it. Fictional data (test_minutes_approve's steering
committee: 1 = "Book the UAT environment" action, 2 = "Test data isn't anonymised" issue, 3 = an update, 4 = a decision).
Each case prints:   ### CASE <name> | LEAK|PASS|HELD|CTRL-FAIL|SKIP | evidence
  LEAK  a crossed/neither item is registered in the tracker, or a crossed line is in a follow-up, an export or a filed file
  HELD  creaite refused or stopped it (a refusal is the pass)    SKIP  the tree has not got the Track column (before #275 / #268)
Usage: python d275.py <tree root> <variant>      variants: followup, export, server, apply, promise
`apply` includes the by-hand-approval path that only dev/proposals/track-from-review/tracker-track-problems.diff (guarded) closes: it is
run on the tree as it is (LEAK until the diff is in) and again with the diff applied to the vault's copy of tracker.py (HELD)."""
import json
import os
import re
import sqlite3
import subprocess
import sys
import unittest
import zipfile
from contextlib import closing
from pathlib import Path

ROOT = Path(sys.argv.pop(1))
VARIANT = sys.argv.pop(1)
sys.path.insert(0, str(ROOT / "dev" / "tests"))
sys.path.insert(0, str(ROOT / "system" / "scripts"))
sys.path.insert(0, str(ROOT / "system" / "scripts" / "vendor"))
import test_minutes_approve as ma  # noqa: E402

MR = ROOT / "system/scripts/minutes_record.py"
HAS_TRACK = MR.is_file() and "def track_apply_problems" in MR.read_text(encoding="utf-8")
HAS_FOLLOWUP = MR.is_file() and "def followup_facts" in MR.read_text(encoding="utf-8")
DIFF = ROOT / "dev" / "proposals" / "track-from-review" / "tracker-track-problems.diff"
CROSSED, NEITHER = "Book the UAT environment", "Test data isn't anonymised"


def case(name, status, ev=""):
    print(f"### CASE {name} | {status} | {str(ev)[:200]}", flush=True)


class P(ma.Base):
    def need(self, what="the Track column"):
        if not HAS_TRACK:
            case(f"{VARIANT}: {what}", "SKIP", "this tree has no minutes_record.track_apply_problems (before #275)")
            return False
        return True

    def track(self, choices):
        self.js("import minutes_record, creaite_doc\n"
                f"d = creaite_doc.read({ma.DRAFT!r})\nd['layout'] = {{**(d.get('layout') or {{}}), 'track': {choices!r}}}\n"
                f"r = minutes_record.save_page({ma.DRAFT!r}, d)\nprint(json.dumps({{'ok': bool(r.get('ok'))}}))")

    def number(self, ref):
        rows = json.loads(self.v.run("list", "--json", script="review.py").stdout)
        return next(r["n"] for r in rows if r["file"] == self.name and r["ref"] == ref)

    def item(self, n):
        return next(i for i in self.data()["items"] if i["n"] == n)

    def set_decision(self, n, decision):
        p = self.v.root / "system/staging" / self.name
        data = json.loads(p.read_text(encoding="utf-8"))
        next(i for i in data["items"] if i["n"] == n)["decision"] = decision
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def registered(self):
        """Every tracker row's text, joined: crossed/neither words in it mean the item was registered."""
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            return " | ".join(str(c) for t in ("actions", "raid", "decisions", "promises") for r in con.execute(f"SELECT * FROM {t}") for c in r)

    def text_of(self, p):
        p = Path(p)
        if p.suffix in (".docx", ".xlsx"):
            with zipfile.ZipFile(p) as z:
                return "".join(z.read(n).decode("utf-8", "ignore") for n in z.namelist() if n.endswith(".xml"))
        if p.suffix == ".pdf":
            try:
                import pypdf
                return "\n".join(pg.extract_text() or "" for pg in pypdf.PdfReader(str(p)).pages)
            except Exception:  # noqa: BLE001
                return ""
        return p.read_text(encoding="utf-8", errors="ignore")

    def cross(self):
        self.track({"1": "n", "2": "", "4": ""})
        self.assertEqual((self.doc(ma.DRAFT).get("layout") or {}).get("track"), {"1": "n", "2": "", "4": ""})

    # ── the follow-up email and the exports ──────────────────────────────────────────────────────────────────────────────
    def test_followup(self):
        if not self.need() or not HAS_FOLLOWUP:
            if HAS_TRACK:
                case("followup: followup_facts", "SKIP", "no minutes_record.followup_facts")
            return
        self.cross()
        for ver in ("internal", "distributed"):
            r = self.js(f"import minutes_record\ntry:\n    r = minutes_record.followup_facts({ma.DRAFT!r}, {ver!r})\n"
                        "except minutes_record.RecordError as e:\n    r = {'ok': False, 'message': str(e)}\nprint(json.dumps(r))")
            if not r.get("ok"):
                case(f"followup {ver}", "HELD", str(r.get("message"))[:120])
                continue
            blob = json.dumps(r)
            case(f"followup {ver}: crossed action not listed", "LEAK" if CROSSED in blob else "PASS",
                 "the crossed action is in the follow-up" if CROSSED in blob else f"{len(r.get('items') or [])} item(s) listed, none crossed")
            case(f"followup {ver}: neither issue not listed", "LEAK" if NEITHER in blob and not any(i.get("kept") for i in r["items"]) else "PASS",
                 "the issue left with neither is listed as a work item" if NEITHER in blob else "not listed")
        self.track({})
        r = self.js(f"import minutes_record\nprint(json.dumps(minutes_record.followup_facts({ma.DRAFT!r}, 'internal')))")
        case("followup control: with no Track choice the new action is listed", "PASS" if CROSSED in json.dumps(r) else "CTRL-FAIL",
             "" if CROSSED in json.dumps(r) else "the default row is not listed")

    def test_export(self):
        if not self.need():
            return
        self.cross()
        for fmt in ("html", "docx", "pdf"):
            r = self.js("import minutes_record\ntry:\n    r = minutes_record.export(" + repr(ma.DRAFT) + f", {fmt!r})\n"
                        "except Exception as e:\n    r = {'ok': False, 'message': type(e).__name__ + ': ' + str(e)}\nprint(json.dumps(r, default=str))")
            if not r.get("ok") or not r.get("path"):
                case(f"export {fmt}", "HELD", str(r.get("message"))[:140])
                continue
            from_path = self.v.root / r["path"] if not os.path.isabs(r["path"]) else Path(r["path"])
            if not from_path.is_file():
                case(f"export {fmt}", "HELD", "no file made")
                continue
            t = self.text_of(from_path)
            if not t.strip() and fmt == "pdf":
                case(f"export {fmt}", "HELD", "pdf text unreadable here (no pypdf/Chrome): not judged")
                continue
            case(f"export {fmt}: crossed line not in the file", "LEAK" if CROSSED in t else "PASS",
                 "the crossed action is in the export" if CROSSED in t else f"{len(t)} chars, none crossed")
        e = self.js("import minutes_record\ntry:\n    r = minutes_record.export(" + repr(ma.DRAFT) + ", 'html', version='distributed')\n"
                    "except Exception as e:\n    r = {'ok': False, 'message': type(e).__name__ + ': ' + str(e)}\nprint(json.dumps(r, default=str))")
        case("export distributed of a draft", "HELD" if not e.get("ok") else "PASS", str(e.get("message") or "made")[:120])

    # ── the server paths ─────────────────────────────────────────────────────────────────────────────────────────────────
    def test_server(self):
        if not self.need():
            return
        self.cross()
        # review.py approve on the minutes: the ticked rows only
        out = self.v.run("approve", str(self.number("meeting")), script="review.py", ok=False).stdout
        self.v.run("apply", ok=False)
        reg = self.registered()
        case("server: approve minutes registers no crossed action", "LEAK" if CROSSED in reg else "PASS", "crossed action registered" if CROSSED in reg else out.strip()[:100])
        filed = self.v.root / ma.FILED
        t = filed.read_text(encoding="utf-8") if filed.is_file() else ""
        case("server: the filed minutes hold no crossed line", "LEAK" if CROSSED in t else ("PASS" if t else "HELD"), "crossed line in the filed minutes" if CROSSED in t else ("filed" if t else "minutes not filed"))

    def test_server_items(self):
        if not self.need():
            return
        self.cross()
        out1 = self.v.run("approve", str(self.number(1)), script="review.py", ok=False).stdout
        case("server: review.py approve <crossed item> is refused", "LEAK" if self.item(1)["decision"] == "approved" else "HELD", out1.strip()[:120])
        out2 = self.v.run("approve", str(self.number(2)), script="review.py", ok=False).stdout
        case("server: review.py approve <neither item> is refused", "LEAK" if self.item(2)["decision"] == "approved" else "HELD", out2.strip()[:120])
        out3 = self.v.run("bulk", script="review.py", ok=False).stdout
        bad = [n for n in (1, 2) if self.item(n)["decision"] == "approved"]
        case("server: review.py bulk leaves out crossed and neither items", "LEAK" if bad else "HELD", f"approved {bad}" if bad else out3.strip()[:120])
        r = self.js(f"import review\nprint(json.dumps(review.approve_minutes({self.name!r}, True, [1, 2])))")
        self.v.run("apply", ok=False)
        case("server: approve_minutes sent the crossed item as its own tick", "LEAK" if CROSSED in self.registered() else "HELD",
             "crossed action registered" if CROSSED in self.registered() else "not registered")

    def test_apply(self):
        if not HAS_TRACK:
            case("apply: the Track column", "SKIP", "this tree has no minutes_record.track_apply_problems (before #275)")
            return
        self.cross()
        self.set_decision(1, "approved")                           # by hand, or a stale page's save: a crossed item approved
        r = self.v.run("apply", ok=False)
        reg = self.registered()
        diff_in = "def track_problems" in (self.v.root / "system/scripts/tracker.py").read_text(encoding="utf-8")
        case("apply: a crossed item approved by hand " + ("(tracker has track_problems)" if diff_in else "(tracker without the diff)"),
             "LEAK" if CROSSED in reg else "HELD",
             "the crossed action was registered by tracker.py apply" if CROSSED in reg else (r.stdout + r.stderr).strip().splitlines()[-1][:120] if (r.stdout + r.stderr).strip() else "stopped")
        if not diff_in and DIFF.is_file():                         # the guarded proposal, applied to the vault's copy only
            self.v.run("undo", ok=False)
            self.set_decision(1, "approved")
            p = subprocess.run(["patch", "-p1", "-s", "-d", str(self.v.root), "-i", str(DIFF)], capture_output=True, text=True)
            if p.returncode:
                case("apply with tracker-track-problems.diff", "SKIP", "the diff does not apply to this tree: " + (p.stdout + p.stderr)[:100])
                return
            r = self.v.run("apply", ok=False)
            reg = self.registered()
            case("apply with tracker-track-problems.diff applied to the vault's copy", "LEAK" if CROSSED in reg else "HELD",
                 "still registered" if CROSSED in reg else ((r.stdout + r.stderr).strip().splitlines() or ["stopped"])[-1][:120])
        # a record that can't be read, with an approved item
        f = self.v.root / ma.DRAFT
        f.write_text(re.sub(r'(<script type="application/json" id="creaite-data">).*?(</script>)', r"\1{broken\2", f.read_text(encoding="utf-8"),
                            flags=re.S), encoding="utf-8")
        self.set_decision(3, "approved")
        r2 = self.js("import minutes_record\nname = " + repr(self.name) + "\ndata = json.load(open('system/staging/' + name, encoding='utf-8'))\n"
                     "print(json.dumps(minutes_record.track_apply_problems(name, data)))")
        case("apply: an unreadable record with an approved item fails closed", "HELD" if r2 else "LEAK", (r2[0] if r2 else "no problem raised")[:120])

    def test_promise(self):
        if not HAS_TRACK:
            case("promise: the Track column", "SKIP", "this tree has no minutes_record.track_apply_problems (before #275)")
            return
        from test_tracker import Vault
        v = Vault()
        try:
            v.run("init")
            (v.root / "inbox").mkdir(exist_ok=True)
            f = v.root / "system/staging/drafts/promise.json"
            f.write_text(json.dumps({"title": "[ABC] Promise check-in", "date": "2026-10-14", "projects": ["ABC"],
                                     "minutes": {"start": "12:00", "end": "12:30", "summary": ["A short check-in."], "chat": False},
                                     "items": [{"table": "actions", "values": {"project": "ABC", "description": "Draft the cutover runbook",
                                                                               "owner": "Jane Doe"}},
                                               {"table": "promises", "section": "Jane Doe, 12:05", "values": {
                                                   "project": "ABC", "promised_by": "Jane Doe", "promised_to": "Alan Carter",
                                                   "description": "Send the vendor's rate card", "due_date": "2026-10-20"}}]}), encoding="utf-8")
            r = v.run("stage", str(f), script="minutes.py", ok=False)
            names = [p.name for p in (v.root / "system/staging").glob("proposed-*.json")]
            if not names:
                case("promise: minutes staged", "HELD", (r.stdout + r.stderr).strip()[-140:])
                return
            code = ("import sys, json; sys.path.insert(0, 'system/scripts')\nimport review\n"
                    f"print(json.dumps(review.approve_minutes({names[0]!r}, True, [])))")
            a = subprocess.run([sys.executable, "-c", code], cwd=v.root, capture_output=True, text=True,
                               env={**os.environ, "CREAITE_NOW": "2026-10-14 12:00"})
            v.run("apply", ok=False)
            with closing(sqlite3.connect(v.root / "system/tracker.db")) as con:
                promises = [r[0] for r in con.execute("SELECT description FROM promises")]
                actions = [r[0] for r in con.execute("SELECT description FROM actions")]
            case("promise: a promise with no row is never registered by Approve minutes", "LEAK" if any("rate card" in p for p in promises) else "HELD",
                 f"registered {promises}" if promises else "waits in Review")
            case("promise control: the ticked action is registered", "PASS" if any("cutover runbook" in x for x in actions) else "CTRL-FAIL",
                 "" if any("cutover runbook" in x for x in actions) else (a.stdout + a.stderr)[-120:])
            # review.py bulk (Approve routine) on a promise: a promise is a routine item that Review lists, so bulk approving it is the
            # design (BL-125 A); recorded as information, not judged. The leak this probe watches for is Approve minutes registering a
            # promise the minutes show no row for (above).
            p2 = json.loads((v.root / "system/staging" / names[0]).read_text(encoding="utf-8")) if (v.root / "system/staging" / names[0]).exists() else {}
            dec = [i.get("decision") for i in p2.get("items", []) if "rate card" in json.dumps(i)]
            case("promise: after Approve minutes the promise itself waits as an item in Review", "PASS", f"decision {dec or 'applied/none'}")
        finally:
            v.cleanup()


if __name__ == "__main__":
    test = {"followup": "test_followup", "export": "test_export", "server": "test_server", "items": "test_server_items", "apply": "test_apply",
            "promise": "test_promise"}[VARIANT]
    unittest.main(argv=["x", f"P.{test}"], verbosity=0)
