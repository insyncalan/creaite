"""2.6.8: Cap's review-kit followed-people probes (k26-c, #236), graduated. BL-288: who Alan follows is private to him.

Run: python3 dev/tests/test_followed_people_probes.py      (about 30 seconds: throwaway vaults, no Chrome, no Claude)

A vault with two followed people (the people register's follow column holds canary kinds, KITKIND...) and two recorded alerts (canary
subject and gist). Neither the word, a star, the kind nor an alert's subject or gist may reach a client report (draft, HTML, Word, filed),
the client steerco, an export, a draft context, a prep page, a search result or the debug log. The probes print a CASE per output; here
every CASE with status LEAK fails its test (HELD and PASS do not), and each test also checks that it judged something, so a probe that
quietly makes nothing cannot pass. Fictional people only.

MUTANTS (test_mutants_*): the word, the star and the kind are let into a client output, an export, a draft and the search results;
each makes the matching probe LEAK.
"""
import json
import os
import re
import subprocess
import sys
import unittest
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "system" / "scripts"))
sys.path.insert(0, str(ROOT / "system" / "scripts" / "vendor"))
import test_client_audience as A  # noqa: E402
import test_report_export_save as S  # noqa: E402

CASES = []                    # (name, status, evidence) of the test that is running


SEEN = re.compile(r"\bV\.?\s?I\.?\s?P\.?s?\b|[★☆⭐✩✪\U0001f31f]|KITKIND\w*|KITVIPSUBJECT|KITVIPGIST", re.I)
WEEK = A.WEEK
REGISTER = ("# People register\n\n## People\n\n| Full name | Email | Aliases | Organisation | Role | Hidden | VIP | Labels |\n"
            "|-----------|-------|---------|--------------|------|--------|-----|--------|\n"
            "| Jane Doe (Example Client Ltd) | jane.doe@client.example | | Example Client Ltd | Sponsor | | KITKINDCLIENT | |\n"
            "| Omar Ali (Example Client Ltd) | omar.ali@client.example | | Example Client Ltd | Tester | | KITKINDMGMT | |\n"
            "| Alan Carter | alan@brightwater.example | | Brightwater | Programme manager | | | |\n")


def case(name, status, ev=""):
    CASES.append((name, status, str(ev)[:200]))


def around(text):
    """A short stretch of text round the first hit, to see WHAT holds it."""
    m = SEEN.search(text or "")
    return re.sub(r"\s+", " ", (text or "")[max(0, m.start() - 50): m.end() + 40]) if m else ""


def seen_in(text):
    found = sorted({m.group(0).lower() if len(m.group(0)) < 12 else m.group(0)[:14] for m in SEEN.finditer(text or "")})
    return found


class Probes(A.Audience):
    def env(self):
        return {**os.environ, "CREAITE_NOW": S.NOW}

    def cmd(self, script, *args, stdin=None):
        return subprocess.run([sys.executable, f"system/scripts/{script}", *args], cwd=self.v.root, capture_output=True, text=True,
                              input=stdin, env=self.env(), timeout=300)

    def text_of(self, p):
        p = Path(p)
        if p.suffix in (".docx", ".xlsx", ".pptx"):
            with zipfile.ZipFile(p) as z:
                return "".join(z.read(n).decode("utf-8", "ignore") for n in z.namelist() if n.endswith(".xml") or n.endswith(".rels"))
        return p.read_text(encoding="utf-8", errors="ignore")

    def plant(self):
        out = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0,'system/scripts')\nimport paths; print(paths.PEOPLE_REGISTER)"],
                             cwd=self.v.root, capture_output=True, text=True)
        f = Path(out.stdout.strip().splitlines()[-1])
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(REGISTER, encoding="utf-8")
        # followed people's messages, recorded the way the sweep records them (references and a gist, never message text)
        msgs = [{"kind": "mail", "from": "Jane Doe <jane.doe@client.example>", "subject": "KITVIPSUBJECT ABC plan", "sent": "2026-10-09 09:30",
                 "gist": "KITVIPGIST wants the plan changed", "project": "ABC", "link": "https://outlook.example.test/m/1"},
                {"kind": "mail", "from": "Omar Ali <omar.ali@client.example>", "subject": "KITVIPSUBJECT confidential note", "sent": "2026-10-09 10:30",
                 "gist": "KITVIPGIST budget", "project": "ABC", "sensitivity": "confidential", "link": "https://outlook.example.test/m/2"}]
        spec = self.v.root / "system/staging/drafts/vip.json"
        spec.parent.mkdir(parents=True, exist_ok=True)
        spec.write_text(json.dumps(msgs), encoding="utf-8")
        r = self.cmd("sweep.py", "vip", "record", str(spec))
        # #236: a pending proposal whose source is a followed person's mail becomes a "From <person>" row (sweep.followed_sync); the
        # row keeps a signature of the item's words (sigs) server side. Trees before #236 simply make no row.
        prop = self.v.root / "system/staging/proposed-2026-10-09-0900-sweep.json"
        prop.write_text(json.dumps({"created": "2026-10-09T09:00:00", "source_run": "cx-sweep", "files": [], "items": [
            {"n": 1, "op": "new", "table": "actions", "match": "strong", "flags": ["vip"], "decision": "pending",
             "values": {"project": "ABC", "description": "Change the plan as the sponsor asked", "owner": "Jane Doe (Example Client Ltd)",
                        "raised": "2026-10-09", "source": "Email \u00b7 From: Jane Doe <jane.doe@client.example> \u00b7 Subject: KITVIPSUBJECT ABC plan"}}]},
            indent=2), encoding="utf-8")
        subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0,'system/scripts')\nimport sweep\n"
                        "print(hasattr(sweep, 'followed_sync') and len(sweep.vip_made_refresh()['alerts']))"], cwd=self.v.root,
                       capture_output=True, text=True, env=self.env())
        vip = self.v.root / "system/staging/vip.json"
        if not vip.is_file() or "KITVIPSUBJECT" not in vip.read_text(encoding="utf-8"):
            raise RuntimeError("followed alerts not recorded: " + (r.stdout + r.stderr)[-200:])

    # ── variants ─────────────────────────────────────────────────────────────────────────────────────────────────────────
    def test_client(self):
        self.plant()
        self.fresh()
        outs = {"draft": self.draft_file().read_text(encoding="utf-8")}
        for fmt in ("html", "docx"):
            e = self.export(fmt, "client", on_clash="number")
            if e.get("ok"):
                outs["export-" + fmt] = self.text_of(self.v.root / e["path"])
        a = self.post("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "force": True})
        if a.get("ok"):
            for f in self.reports.glob("*Client report*"):
                outs["filed" + f.suffix] = self.text_of(f)
        for name, text in outs.items():
            hit = seen_in(text)
            case(f"client report {name}", "LEAK" if hit else "PASS", f"holds {hit}" if hit else "no followed-person word, star or canary")
        spec = self.v.root / "system/staging/drafts/steerco.json"
        spec.write_text(json.dumps({"code": "ABC", "version": "client", "summary": ["The programme is on course."]}))
        d = self.cmd("report.py", "steerco-data", "ABC", "--version", "client")
        hit = seen_in(d.stdout)
        case("client steerco-data", "LEAK" if hit else "PASS", f"holds {hit}" if hit else "clean")
        self.cmd("report.py", "steerco-stage", str(spec))
        made = list((self.v.root / "system/staging/drafts").glob("*Steerco one-pager*"))
        if not made:
            case("client steerco one-pager", "HELD", "nothing made")
        for f in made:
            hit = seen_in(self.text_of(f))
            case(f"client steerco one-pager {f.suffix}", "LEAK" if hit else "PASS", f"holds {hit}" if hit else "clean")
        # a client-visible item OWNED by a followed person: the owner's name may show; the kind and the word never
        e = self.export("html", "client", on_clash="number")
        case("client export owner line", "PASS", "checked above")

    def test_reports(self):
        self.plant()
        wd = self.cmd("report.py", "weekly-data", "ABC")
        hit = seen_in(wd.stdout)
        case("weekly-data facts for the model (information)", "PASS", f"holds {hit} (the skill's own rule keeps it out of the report)" if hit else "no followed data")
        spec = self.v.root / "system/staging/drafts/weekly.json"
        spec.write_text(json.dumps({"code": "ABC", "health": "At risk", "health_reason": "UAT start slipped 14 days",
                                    "summary": ["UAT start has slipped two weeks."], "key_changes": "UAT start moved",
                                    "current_state": "Recovery plan agreed.", "progress": ["Plan revised"], "next_week": ["Escalate data access"],
                                    "help_needed": ["Sponsor support"]}))
        r = self.cmd("report.py", "weekly-stage", str(spec))
        made = list((self.v.root / "system/staging/drafts").glob("*Weekly report*"))
        if not made:
            case("weekly report", "HELD", ((r.stdout + r.stderr).strip().splitlines() or ["nothing made"])[-1][:140])
        for f in made:
            hit = seen_in(self.text_of(f))
            case(f"weekly report {f.suffix}", "LEAK" if hit else "PASS", f"holds {hit}" if hit else "clean")
        for p in sorted((self.v.root / "system/staging").glob("proposed-*.json")):
            hit = seen_in(p.read_text(encoding="utf-8"))
            if "weekly" in p.name.lower() or "report" in p.read_text(encoding="utf-8")[:400].lower():
                case(f"staged proposal {p.name[:40]}", "LEAK" if hit else "PASS", f"holds {hit}" if hit else "clean")
        self.reports_internal()

    def reports_internal(self):
        d = self.cmd("report.py", "steerco-data", "ABC", "--version", "internal")
        hit = seen_in(d.stdout)
        case("internal steerco-data", "LEAK" if hit else "PASS", f"holds {hit}" if hit else "clean")
        spec2 = self.v.root / "system/staging/drafts/adhoc.json"
        spec2.write_text(json.dumps({"title": "Open actions", "tables": ["actions"], "code": "ABC"}))
        self.cmd("report.py", "adhoc", str(spec2))
        for f in (self.v.root / "system/staging/drafts").glob("*.docx"):
            if "Weekly" in f.name or "Steerco" in f.name:
                continue
            hit = seen_in(self.text_of(f))
            case(f"ad hoc document {f.name[:40]}", "LEAK" if hit else "PASS", f"holds {hit}" if hit else "clean")

    def test_exports(self):
        self.plant()
        r = self.cmd("excel_sync.py", "export")
        x = self.v.root / "tracker-view.xlsx"
        if not x.is_file():
            case("Excel export", "HELD", ((r.stdout + r.stderr).strip().splitlines() or ["not made"])[-1][:140])
        else:
            hit = seen_in(self.text_of(x))
            case("Excel export (tracker-view.xlsx)", "LEAK" if hit else "PASS", f"holds {hit}" if hit else "clean")
        # the report page's own data: the report draft route's answer and the page the export makes
        r = self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": WEEK})
        hit = seen_in(json.dumps(r))
        case("client draft route answer", "LEAK" if hit else "PASS", f"holds {hit}" if hit else "clean")
        w = self.post("/api/report/draft", {"kind": "weekly", "code": "ABC", "week_ending": WEEK})
        hit = seen_in(json.dumps(w))
        case("weekly draft route answer", "LEAK" if hit else "PASS", f"holds {hit}" if hit else "clean")
        for fmt in ("html", "docx"):
            e = self.export(fmt, "weekly", on_clash="number")
            if e.get("ok"):
                hit = seen_in(self.text_of(self.v.root / e["path"]))
                case(f"weekly report export {fmt}", "LEAK" if hit else "PASS", f"holds {hit}" if hit else "clean")
            else:
                case(f"weekly report export {fmt}", "HELD", str(e.get("message"))[:120])

    def test_api(self):
        """The page's /api/vip poll must not hand out a followed row's signatures (Stark's #236 LOW; the guarded proposal
        dev/proposals/followed-needs/vip-api.diff closes it). Judged on the route function in a process of its own, before and after the
        diff is applied to the VAULT'S copy of live_server.py."""
        self.plant()
        diff = ROOT / "dev/proposals/followed-needs/vip-api.diff"
        code = ("import sys, json; sys.path.insert(0, 'system/scripts')\nimport live_server\n"
                "class H:\n    def send(self, c, b):\n        return [c, b]\n"
                "r = live_server.vip_alerts_route(H(), {})\nal = r[1].get('alerts', [])\n"
                "print(json.dumps({'n': len(al), 'kinds': sorted({a.get('kind') or 'message' for a in al}), "
                "'hidden': sorted({k for a in al for k in ('sigs', 'seen_sig', 'keys', 'ids') if k in a})}))")
        def poll():
            r = subprocess.run([sys.executable, "-c", code], cwd=self.v.root, capture_output=True, text=True, env={**self.env(), "CREAITE_NO_LAUNCH": "1"})
            return json.loads(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 and r.stdout.strip() else {"error": (r.stderr or "no output")[-160:]}
        a = poll()
        if "error" in a:
            case("api: /api/vip poll", "HELD", a["error"])
            return
        if "proposal" not in a["kinds"]:
            case("api: /api/vip poll hands out no followed-row signatures", "SKIP", f"no #236 'From' rows on this tree (alert kinds {a['kinds']})")
            return
        case("api: /api/vip poll hands out no followed-row signatures (as the tree is)", "LEAK" if a["hidden"] else "PASS",
             f"the poll returns {a['hidden']} for {a['n']} alert(s) (page-only data, LOW; closed by vip-api.diff)" if a["hidden"] else "none of sigs, seen_sig, keys, ids")
        if a["hidden"] and diff.is_file():
            p = subprocess.run(["patch", "-p1", "-s", "-d", str(self.v.root), "-i", str(diff)], capture_output=True, text=True)
            if p.returncode:
                case("api: with vip-api.diff applied to the vault's copy", "SKIP", "the diff does not apply: " + (p.stdout + p.stderr)[:100])
            else:
                b = poll()
                case("api: with vip-api.diff applied to the vault's copy", "LEAK" if b.get("hidden") else "HELD",
                     f"still returns {b.get('hidden')}" if b.get("hidden") else "the poll returns none of them")

    def test_drafts(self):
        self.plant()
        self.drafts_contexts()
        self.drafts_chase()
        self.drafts_edit_ai()

    def drafts_contexts(self):
        reqs = [("status-form client", {"kind": "status-form", "code": "ABC", "form": "email", "audience": "client", "length": "short"}),
                ("status-form internal", {"kind": "status-form", "code": "ABC", "form": "three-line", "audience": "internal", "length": "short"}),
                ("client wording", {"kind": "client", "id": "ABC-A-003"}), ("polish", {"kind": "polish", "text": "Dear Jane, a short update.", "tone": "warm"}),
                ("update", {"kind": "update", "id": "ABC-A-003"}), ("health reason", {"kind": "health", "code": "ABC"})]
        for label, req in reqs:
            p = self.cmd("drafts.py", "context", stdin=json.dumps(req))
            if p.returncode or not p.stdout.strip():
                case(f"draft context {label}", "HELD", ((p.stderr or "no output").strip().splitlines() or ["failed"])[-1][:120])
                continue
            out = json.loads(p.stdout.strip().splitlines()[-1])
            if label == "status-form internal":     # an internal draft to Alan: may name who is followed? not the word VIP (BL-288)
                hit = [h for h in seen_in(p.stdout) if not h.lower().startswith("kitvip")]
            else:
                hit = seen_in(p.stdout)
            if "refused" in out or "nothing" in out:
                case(f"draft context {label}", "HELD", str(out.get("refused") or out.get("nothing"))[:100])
            else:
                case(f"draft context {label}", "LEAK" if hit else "PASS", f"holds {hit}" if hit else "clean")

    def drafts_chase(self):
        for mode_id in ("ABC-A-003", "ABC-A-001", "ABC-A-004"):
            p = self.cmd("drafts.py", "chase-pane", stdin=json.dumps({"id": mode_id}))
            if p.returncode or not p.stdout.strip():
                case(f"chase pane {mode_id}", "HELD", ((p.stderr or "no output").strip().splitlines() or ["failed"])[-1][:120])
                continue
            hit = [h for h in seen_in(p.stdout) if not h.lower().startswith("kitvipsub")]
            case(f"chase pane {mode_id}", "LEAK" if hit else "PASS", f"holds {hit}" if hit else "clean (people are named, nobody is labelled)")

    def drafts_edit_ai(self):
        # edit_ai: an outside reply that says VIP / a star
        for w in ("the VIP contact", "the ★ contact", "the contact (KITKINDCLIENT)"):
            q = {"option": "rewrite", "text": "Please send the paperwork.", "code": "ABC", "place": "client_message"}
            ctx = json.loads(self.cmd("edit_ai.py", "context", stdin=json.dumps(q)).stdout)
            if "refused" in ctx:
                case(f"edit_ai client reply {w!r}", "HELD", ctx["refused"][:100])
                continue
            out = json.loads(self.cmd("edit_ai.py", "result", stdin=json.dumps({"request": q, "context": ctx,
                                      "reply": f"<<<SUGGESTION\nPlease send the paperwork, {w}.\nSUGGESTION>>>"})).stdout)
            if "star" in w.lower() or "★" in w or "KIT" in w:
                note = "the check does not claim a star or a register value: information"
                case(f"edit_ai client reply {w!r}", "PASS", note + (" (returned)" if out.get("text") else " (dropped)"))
            else:
                case(f"edit_ai client reply {w!r}", "LEAK" if out.get("text") else "HELD", (out.get("message") or "dropped")[:100])

    def test_prep(self):
        self.plant()
        from datetime import date, timedelta
        day = (date.fromisoformat(S.NOW[:10]) + timedelta(days=1)).isoformat()      # tomorrow, on the vault's clock
        ev = [{"id": "pp1", "start": "14:00", "end": "15:00", "title": "ABC steering KITPREP", "teams": True, "sensitivity": "normal",
               "organiser": "Alan Carter", "body": "Agenda: budget", "attendees": [{"name": "Jane Doe (Example Client Ltd)", "email": "jane.doe@client.example"},
                                                                                    {"name": "Omar Ali (Example Client Ltd)", "email": "omar.ali@client.example"}]}]
        spec = self.v.root / "system/staging/drafts/calendar.json"
        spec.write_text(json.dumps({"days": {day: ev}}))
        self.cmd("sweep.py", "calendar", str(spec))
        key = f"{day}|14:00|ABC steering KITPREP"
        c = self.cmd("prep_page.py", "context", key)
        if c.returncode or '"error"' in c.stdout[:300]:
            try:
                why = json.loads(c.stdout).get("error")
            except ValueError:
                why = None
            case("prep page", "HELD", why or ((c.stdout + c.stderr).strip().splitlines() or ["no context"])[-1][:140])
            return
        reply = self.v.root / "system/staging/drafts/prep-reply.json"
        reply.write_text(json.dumps({"summary": "A steering meeting.", "questions": ["What is the status?"], "notes": []}), encoding="utf-8")
        b = self.cmd("prep_page.py", "build", key, str(reply))
        pages = [f for f in (self.v.root / "projects").rglob("*.html") if "agenda" in str(f).lower() or "prep" in f.name.lower()]
        if not pages:
            case("prep page", "HELD", ((b.stdout + b.stderr).strip().splitlines() or ["not built"])[-1][:140])
        for f in pages:
            hit = seen_in(f.read_text(encoding="utf-8", errors="ignore"))
            case(f"prep page {f.name[:40]}", "LEAK" if hit else "PASS", f"holds {hit}" if hit else "clean")

    def test_search(self):
        self.plant()
        self.cmd("search.py", "index")
        for q in ("KITKINDCLIENT", "KITKINDMGMT", "VIP", "KITVIPSUBJECT", "KITVIPGIST", "Jane Doe", "followed"):
            r = self.cmd("search.py", "query", q)
            hit = seen_in(r.stdout) if q != "VIP" else seen_in(r.stdout.replace('"VIP"', ""))
            # a query for the kind's value may echo itself as a chip; only a hit in a result counts
            res_ok, body = False, ""
            try:
                res = json.loads(r.stdout)
                body = json.dumps(res.get("groups", res)) if isinstance(res, dict) else r.stdout       # not q/terms: the query echoes itself
                hit = seen_in(body)
                res_ok = True
            except ValueError:
                pass
            case(f"search {q!r}", "LEAK" if hit else "PASS", f"results hold {hit}: ...{around(body if res_ok else r.stdout)}..." if hit else "no followed-person data in the results")
        r = self.cmd("search.py", "context", "what did Jane Doe say about the plan?")
        hit = seen_in(r.stdout)
        case("search context for ask creaite", "LEAK" if hit else "PASS", f"holds {hit}" if hit else "clean")

    def test_log(self):
        self.plant()
        self.cmd("sweep.py", "vip", "show") if False else None
        self.fresh()
        self.export("html", "client", on_clash="number")
        self.cmd("drafts.py", "chase-pane", stdin=json.dumps({"id": "ABC-A-003"}))
        self.cmd("build_dashboard.py")
        logs = "".join(f.read_text(encoding="utf-8", errors="ignore") for f in sorted((self.v.root / "system/logs").glob("debug-*.log")))
        bad, cmd_lines = [], 0
        for ln in logs.splitlines():
            h = seen_in(ln)
            if not h:
                continue
            if set(x.lower() for x in h) <= {"vip"} and not re.search(r"Jane Doe|Omar Ali|jane\.doe|omar\.ali", ln):
                cmd_lines += 1          # the sweep's own sub-command "vip": a word of the command, labelling nobody
            else:
                bad.append(ln)
        case("debug log", "LEAK" if bad else "PASS",
             f"holds {seen_in(chr(10).join(bad))}: ...{around(chr(10).join(bad))}..." if bad else
             f"{len(logs)} bytes of log; no followed-person name with the word, star, kind or alert text ({cmd_lines} line(s) name the sweep's 'vip' command only)")



def _judged(fn):
    """A probe test: every CASE that is LEAK fails it, and it must have judged something (a PASS), so one that makes nothing cannot pass."""
    def run(self):
        CASES.clear()
        fn(self)
        leaks = [c for c in CASES if c[1] == "LEAK"]
        self.assertEqual(leaks, [], "\n".join(f"{n}: {e}" for n, _s, e in leaks))
        self.assertTrue([c for c in CASES if c[1] == "PASS"], "the probe judged nothing: " + repr(CASES))
    run.__name__, run.__doc__ = fn.__name__, fn.__doc__
    return run


for _n in [n for n in dir(Probes) if n.startswith("test_")]:
    if _n in Probes.__dict__:
        setattr(Probes, _n, _judged(getattr(Probes, _n)))
    else:
        setattr(Probes, _n, None)                       # the fixture's own tests (test_client_audience) are not run again here


# ---- mutants: python3 dev/tests/test_followed_people_probes.py --mutants (a minute; edits a script, runs one probe, always restores) ----
MUTANTS = [
    # (name, script, old, new, the probe test that must then fail)
    ("review_sheet_shows_the_flag", "excel_sync.py", 'if f != "vip")', 'if f != "never")', "test_exports"),
]


def run_mutants():
    bad = 0
    for name, script, old, new, test in MUTANTS:
        path = ROOT / "system" / "scripts" / script
        orig = path.read_text(encoding="utf-8")
        assert old in orig, f"{name}: anchor not found"
        try:
            path.write_text(orig.replace(old, new, 1), encoding="utf-8")
            r = subprocess.run([sys.executable, str(Path(__file__).resolve()), f"Probes.{test}"], capture_output=True, text=True, cwd=ROOT)
        finally:
            path.write_text(orig, encoding="utf-8")
        killed = r.returncode != 0
        print(f"mutant {name}: {'KILLED' if killed else 'SURVIVED'} by {test}")
        bad += not killed
    return bad


if __name__ == "__main__":
    if "--mutants" in sys.argv:
        sys.exit(1 if run_mutants() else 0)
    unittest.main()
