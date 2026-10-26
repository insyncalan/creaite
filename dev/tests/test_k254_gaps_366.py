"""#366 step 4 (part A): the review kit's k254 probes (2.5.4: #277, #279, #280) as tests, for the gaps step 1's audit found.

The kit (team-cap-reviewkit-26d, src/k254/) checked four things the existing tests cover only in part:
- d (#280, client-leak): a proposal Apply holds because its transcript has left the inbox. Its reason ("transcript no longer in the
  inbox (inbox/<file>)") and the transcript's file name, which here holds a client's name, belong on the Review row (dashboard.html),
  in the proposal itself and in review.py's and apply's answers. test_held_missing_source checks those places; nothing checked they
  are the only ones. Here every other file the vault holds after the hold and the outputs a person or client is handed (the debug
  log, the Excel export, tracker.db and its backups, the weekly, client and steerco drafts, the search index and its results, the
  drafts contexts, other staging files) is read for them. A mutant (the reason written into the debug log, in the vault's own copy
  of tracker.py, never the repo's) shows the scan sees the leak: the kit's held_reason_logged, which no test caught.
- e (#280): POST /api/apply {only}. The kit's 40 hostile values (paths, types, staging files that are not proposals, look-alikes,
  root-only names; 8 also with hold_peek) each answer "nothing was applied" and change nothing: no database row, no backup, no staged
  proposal, no planted namesake in the vault root. test_save_not_blocked sends 5 of them.
- a (#277): a document whose project is not a string. test_match_check_project_code covers match-check; here check, save, pick,
  reshow and approve too answer 200, ok false, one sentence, never the document's text, and write nothing; creaite_doc.check refuses
  the types only a direct call can carry (tuple, bytes, set).
- c (#279): a no-project prep page (saved "_portfolio", or not chosen yet) is marked Internal and "never sent", in the page returned
  and the file filed; a file creaite didn't write and a page Alan edited in the portfolio's Agendas folder are never overwritten. A
  mutant (the kit's prep_internal_off, in the vault's copy of prep_view.py) shows the check sees a page without the mark.

Fictional data only: the suite's sample vault (ABC Example Programme, DEF), and a client called Yarrowfield in a transcript's name.

Run: python3 dev/tests/test_k254_gaps_366.py      (quick tier: no Chrome)
"""
import copy
import hashlib
import json
import os
import re
import sqlite3
import sys
import unittest
import urllib.error
import urllib.request
import zipfile
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_client_audience import Audience as _Audience, WEEK  # noqa: E402  (its harness: a live server in a populated vault)
from test_dashboard import populate  # noqa: E402
from test_decisions_prep import prep_world  # noqa: E402
from test_prep_reimagined import py  # noqa: E402
from test_tracker import Vault, action, make_draft  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
import creaite_doc  # noqa: E402

DAY = "2026-10-20"
NAME = "Yarrowfield"                                          # a fictional client, in the transcript's FILE NAME only
TRANSCRIPT = f"inbox/{DAY} {NAME} steering.vtt"
DRAFT = f"system/staging/drafts/{DAY} Supplier checkpoint.docx"
REASONS = ("no longer in the inbox", "Held in Review", "not applied")
HELD_LOG = 'debuglog.warn("tracker", f"apply: held {p.name} in Review: a file to be filed has gone")'


def text_of(p):
    """A file's text; a zip (docx, xlsx, a backup zip) member by member."""
    try:
        if zipfile.is_zipfile(p):
            with zipfile.ZipFile(p) as z:
                return b"".join(z.read(n) for n in z.namelist()).decode("utf-8", "ignore")
        return p.read_bytes().decode("utf-8", "ignore")
    except (OSError, zipfile.BadZipFile):
        return ""


def category(rel):
    r = rel.lower()
    for test, cat in ((lambda: r.startswith("system/logs/"), "debug log"), (lambda: r.endswith(".xlsx"), "Excel export"),
                      (lambda: r.startswith("system/backups/") or r.endswith(".db"), "tracker database and backups"),
                      (lambda: r.startswith("system/search/"), "search index"), (lambda: "client report" in r, "client report"),
                      (lambda: "steerco" in r, "steerco one-pager"), (lambda: "weekly report" in r, "weekly report"),
                      (lambda: r.startswith("system/staging/"), "other staging file")):
        if test():
            return cat
    return "other file"


class HeldReasonStaysPut(unittest.TestCase):
    """k254-d: after a held Apply, the reason and the transcript's name are only where they are meant to be."""

    @classmethod
    def setUpClass(cls):
        cls.now = os.environ.get("CREAITE_NOW")
        os.environ["CREAITE_NOW"] = f"{DAY} 18:00"
        cls.v = Vault()
        populate(cls.v)
        cls.root = cls.v.root
        cls.held, cls.said = hold(cls.v, other=True)
        cls.listed = cls.v.run("list", script="review.py", cwd=cls.root).stdout
        cls.streams = cls.outputs()

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()
        if cls.now is None:
            os.environ.pop("CREAITE_NOW", None)
        else:
            os.environ["CREAITE_NOW"] = cls.now

    @classmethod
    def outputs(cls):
        """Every output a person or a client could be handed, made after the hold; the printed ones are returned."""
        v, root, out = cls.v, cls.root, {}
        run = lambda script, *a, stdin=None: __import__("subprocess").run(          # noqa: E731
            [sys.executable, str(root / "system/scripts" / script), *a], cwd=root, capture_output=True, text=True, input=stdin)
        v.run(script="build_dashboard.py", cwd=root)
        v.run("export", script="excel_sync.py", cwd=root)
        drafts = root / "system/staging/drafts"
        specs = {"weekly-stage": {"code": "ABC", "health": "At risk", "health_reason": "UAT start slipped 14 days", "summary": ["UAT slipped."],
                                  "key_changes": "UAT moved", "current_state": "Recovery plan agreed.", "progress": ["Plan revised"],
                                  "next_week": ["Escalate"], "help_needed": ["Support"], "force": True},
                 "client-stage": {"code": "ABC", "period_start": "2026-10-05", "summary": ["On course."], "progress": ["Plan revised"],
                                  "next_steps": ["Escalate"], "force": True}}
        for version in ("client", "internal"):
            specs[f"steerco-stage {version}"] = {"code": "ABC", "version": version, "summary": ["The programme is on course."], "force": True}
        for cmd, spec in specs.items():
            f = drafts / f"k254-{cmd.replace(' ', '-')}.json"
            f.write_text(json.dumps(spec), encoding="utf-8")
            out[cmd] = run("report.py", cmd.split()[0], str(f))
        for args in (("weekly-data", "ABC"), ("client-data", "ABC"), ("steerco-data", "ABC", "--version", "client"),
                     ("steerco-data", "ABC", "--version", "internal"), ("adhoc-data", "actions", "--project", "ABC")):
            out[" ".join(args)] = run("report.py", *args)
        for q in (NAME, "steering", "Supplier checkpoint", "inbox", "transcript"):
            r = run("search.py", "query", q)
            try:
                res = json.loads(r.stdout)
            except ValueError:
                res = r.stdout
            r.stdout = json.dumps({k: res.get(k) for k in ("groups", "totals")} if isinstance(res, dict) else res)   # the results, not the query's echo
            out[f"search query {q}"] = r
        out["search context"] = run("search.py", "context", "what happened at the supplier checkpoint?")
        for audience in ("client", "internal"):
            req = {"kind": "status-form", "code": "ABC", "form": "email", "audience": audience, "length": "short"}
            out[f"drafts context {audience}"] = run("drafts.py", "context", stdin=json.dumps(req))
        return out

    # ── controls: the reason is where it must be ────────────────────────────────────────────────────────────────────
    def test_control_apply_and_review_name_the_held_proposal_and_why(self):
        self.assertIn("Held in Review, not applied", self.said)
        self.assertIn(NAME, self.said)
        self.assertIn("no longer in the inbox", self.listed)
        self.assertIn("no longer in the inbox", self.held.read_text(encoding="utf-8"))
        self.assertIn("no longer in the inbox", (self.root / "dashboard.html").read_text(encoding="utf-8"))
        self.assertIn("Book the pilot review", [a["description"] for a in self.v.rows("actions")], "the other proposal applied")

    def test_control_every_output_was_made(self):
        for name, r in self.streams.items():
            self.assertEqual(r.returncode, 0, f"{name}: {(r.stdout + r.stderr)[-300:]}")
        made = {category(f.relative_to(self.root).as_posix()) for f in self.root.rglob("*") if f.is_file()}
        for cat in ("debug log", "Excel export", "tracker database and backups", "search index", "client report",
                    "steerco one-pager", "weekly report", "other staging file"):
            self.assertIn(cat, made, f"no {cat} was made, so the scan would prove nothing")

    # ── the scan ────────────────────────────────────────────────────────────────────────────────────────────────────
    def test_no_file_but_the_review_row_the_proposal_and_the_draft_holds_the_name_or_the_reason(self):
        self.assertEqual(leaks(self.root, self.held), {})

    def test_the_debug_log_holds_neither_the_reason_nor_the_transcripts_name(self):
        log = "".join(text_of(f) for f in (self.root / "system/logs").glob("*.log"))
        self.assertIn(self.held.name, log, "control: the hold is logged, by the proposal's name")
        for w in (NAME, *REASONS, "inbox/", ".vtt"):            # minutes.py's own line ("draft + transcript copied on approval") is by design
            self.assertNotIn(w, log)

    def test_no_printed_output_holds_the_name_or_the_reason(self):
        for name, r in self.streams.items():
            if name in ("client-stage", "weekly-stage") or name.startswith("steerco-stage"):
                continue                                         # their files are scanned; their lines name the drafts
            with self.subTest(output=name):
                for w in (NAME, *REASONS):
                    self.assertNotIn(w, r.stdout)

    def test_mutant_the_reason_in_the_debug_log_is_seen(self):
        """Proof the scan sees the leak (the kit's held_reason_logged): the reason written into the log by the vault's own copy of
        tracker.py, never the repo's."""
        os.environ["CREAITE_NOW"] = f"{DAY} 18:00"
        v = Vault()
        self.addCleanup(v.cleanup)
        v.run("init")
        script = v.root / "system/scripts/tracker.py"
        text = script.read_text(encoding="utf-8")
        self.assertEqual(text.count(HELD_LOG), 1, "the held log line moved: update HELD_LOG")
        script.write_text(text.replace(HELD_LOG, HELD_LOG.replace("a file to be filed has gone", "{why}")), encoding="utf-8")
        held, said = hold(v)
        self.assertIn("Held in Review, not applied", said)
        self.assertIn("debug log", leaks(v.root, held), "the scan finds the reason in the debug log")


def hold(v, other=False):
    """Minutes staged by the real minutes.py and approved, the transcript then gone from the inbox, and Apply (with, if `other`, a
    valid proposal beside it, so the apply writes and backs up). Returns the held proposal and apply's answer."""
    root = v.root
    (root / "inbox").mkdir(exist_ok=True)
    (root / TRANSCRIPT).write_text("WEBVTT\n\n00:00:01.000 --> 00:00:05.000\n<v Alan Carter>Morning all.</v>\n", encoding="utf-8")
    make_draft(root / DRAFT)
    f = root / "system/staging/drafts/meeting.json"
    f.write_text(json.dumps({"title": "Supplier checkpoint", "date": DAY, "projects": ["ABC"], "transcript": TRANSCRIPT, "draft": DRAFT,
                             "items": [{"table": "actions", "section": "Actions", "values": {
                                 "project": "ABC", "description": "Chase the supplier's plan", "owner": "Alan Carter",
                                 "due_date": "2030-06-10"}}]}), encoding="utf-8")
    before = {p.name for p in (root / "system/staging").glob("proposed-*.json")}
    v.run("stage", str(f), script="minutes.py", cwd=root)
    prop = next(p for p in (root / "system/staging").glob("proposed-*.json") if p.name not in before)
    data = json.loads(prop.read_text(encoding="utf-8"))
    data["meeting"]["minutes_decision"] = "approved"
    for i in data["items"]:
        i["decision"] = "approved"
    prop.write_text(json.dumps(data, indent=2), encoding="utf-8")
    (root / TRANSCRIPT).unlink()
    if other:
        v.propose("2026-10-21-0900", [action(1, description="Book the pilot review", source="dashboard")])
    r = v.run("apply", cwd=root)
    return prop, r.stdout + r.stderr


def leaks(root, held):
    """{category: [file (words)]} for every vault file outside creaite's engine that holds the client's name or the held reason,
    except the places meant for them: the Review row (dashboard.html and its history snapshot), the proposal and its draft minutes
    (and a file-change backup of that draft). The search index is in tracker.db, which is scanned like any other file."""
    allowed = {"dashboard.html", f"system/staging/{held.name}", DRAFT}
    out = {}
    for f in sorted(root.rglob("*")):
        rel = f.relative_to(root).as_posix()
        if not f.is_file() or rel in allowed or rel.startswith(("system/scripts/", "system/templates/", "system/branding/", ".git/")) \
                or "__pycache__" in rel or re.fullmatch(r"system/history/dashboard-[^/]+\.html", rel):     # only the dashboard snapshot
            continue
        if rel.startswith("system/backups/files/") and f.name == Path(DRAFT).name:
            continue
        t = text_of(f)
        found = [w for w in (NAME, *REASONS) if w in t]
        if found:
            out.setdefault(category(rel), []).append(f"{rel} ({', '.join(found)})")
    return out


# ── k254-e: /api/apply {only} ─────────────────────────────────────────────────────────────────────────────────────────
N1 = "proposed-2026-10-21-120000-dashboard.json"          # the named save (ABC-A-001)
N2 = "proposed-2026-10-21-130000-dashboard.json"          # another staged save (ABC-A-002)
ROOTONLY = "proposed-2026-10-21-140000-dashboard.json"    # in the vault ROOT only (ABC-A-003)
OLD = "proposed-2026-10-20-1757-2.json"                   # an older staged proposal with an invalid approved item
SKIPDIRS = ("system/scripts/", "system/templates/", "system/branding/", "system/logs/", "system/guard/", ".git/")
PEEK_TOO = ("path: system/staging/<name>", "path: system/staging/../../<name>", "path: absolute root namesake", "staging: applied/<name>",
            "type: [name]", "look-alike: upper case", "root only: a root file", "type: true")


def only_values(root):
    """The kit's 40 values (e280.values), labelled."""
    return [
        ("path: system/staging/<name>", "system/staging/" + N1), ("path: ./<name>", "./" + N1), ("path: ../staging/<name>", "../staging/" + N1),
        ("path: system/staging/../../<name>", "system/staging/../../" + N1), ("path: absolute staging path", f"{root}/system/staging/{N1}"),
        ("path: absolute root namesake", f"{root}/{N1}"), ("path: <name>/", N1 + "/"), ("path: ..\\<name>", "..\\" + N1),
        ("path: ../tracker.db", "../tracker.db"), ("path: system/tracker.db", "system/tracker.db"), ("path: %2e%2e/<name>", "%2e%2e/" + N1),
        ("path: ~/<name>", "~/" + N1),
        ("type: true", True), ("type: 1", 1), ("type: 0", 0), ("type: null", None), ("type: [name]", [N1]), ("type: {name}", {"name": N1}),
        ("type: [name, name2]", [N1, N2]), ("type: empty string", ""), ("type: a space", " "), ("type: 1.5", 1.5),
        ("type: name + NUL", N1 + "\x00"), ("type: name + newline", N1 + "\n"),
        ("staging: last-sweep.txt", "last-sweep.txt"), ("staging: calendar.json", "calendar.json"), ("staging: vip.json", "vip.json"),
        ("staging: run-log.txt", "run-log.txt"), ("staging: proposed-notes.txt", "proposed-notes.txt"), ("staging: applied/<name>", "applied/" + N1),
        ("staging: drafts/x.json", "drafts/x.json"),
        ("look-alike: upper case", N1.upper()), ("look-alike: <name>.bak", N1 + ".bak"), ("look-alike: <name> + space", N1 + " "),
        ("look-alike: space + <name>", " " + N1), ("look-alike: proposed-.json", "proposed-.json"),
        ("look-alike: Proposed-", N1.replace("proposed", "Proposed", 1)), ("look-alike: .JSON", N1[:-5] + ".JSON"),
        ("root only: a root file", ROOTONLY), ("root only: <name>/", ROOTONLY + "/"),
    ]


class OnlyNamesOneStagedProposal(unittest.TestCase):
    """k254-e: {only} is a staged proposal's bare file name and nothing else; anything else writes nothing."""
    setUpClass = classmethod(_Audience.setUpClass.__func__)
    tearDownClass = classmethod(_Audience.tearDownClass.__func__)
    post = _Audience.post

    def call(self, body):
        try:
            return 200, self.post("/api/apply", body)
        except urllib.error.HTTPError as e:
            return e.code, {"raw": e.read().decode(errors="replace")}

    def files(self):
        out = {}
        for f in self.v.root.rglob("*"):
            rel = f.relative_to(self.v.root).as_posix()
            if f.is_file() and not rel.startswith(SKIPDIRS) and "__pycache__" not in rel and f.suffix != ".tmp":
                out[rel] = f.read_bytes()
        return out

    def owners(self):
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            return dict(con.execute("SELECT id, owner FROM actions WHERE id IN ('ABC-A-001', 'ABC-A-002', 'ABC-A-003')").fetchall())

    def prop(self, id_, owner):
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            ts = con.execute("SELECT updated_at FROM actions WHERE id=?", (id_,)).fetchone()[0]
        return json.dumps({"created": "2026-10-21T12:00:00", "source_run": "dashboard", "files": [], "items": [
            {"n": 1, "op": "update", "table": "actions", "id": id_, "changes": {"owner": owner}, "based_on": ts, "match": "strong",
             "flags": [], "decision": "approved"}]})

    def plant(self):
        st = self.v.root / "system/staging"
        (st / N1).write_text(self.prop("ABC-A-001", "Named One"), encoding="utf-8")
        (st / N2).write_text(self.prop("ABC-A-002", "Other Staged"), encoding="utf-8")
        (self.v.root / N1).write_text(self.prop("ABC-A-003", "From Root"), encoding="utf-8")      # a namesake in the vault ROOT
        (self.v.root / ROOTONLY).write_text(self.prop("ABC-A-003", "Root Only"), encoding="utf-8")
        for f in (self.v.root / N1, self.v.root / ROOTONLY):
            self.addCleanup(f.unlink, missing_ok=True)
        (st / OLD).write_text(json.dumps({"created": "2026-10-20T17:57:00", "source_run": "minutes", "files": [],
                                          "meeting": {"key": "fp:2026-10-20|supplier checkpoint", "title": "Supplier checkpoint",
                                                      "date": "2026-10-20", "projects": ["ABC"], "minutes_decision": "pending"},
                                          "items": [{"n": 1, "op": "new", "table": "decisions", "match": "strong", "flags": [],
                                                     "decision": "approved", "values": {
                                                         "project": "ABC", "decision": "Go with option B", "made_by": "Alan Carter",
                                                         "raised": "2026-10-20", "source": "minutes Supplier checkpoint"}}]}), encoding="utf-8")
        (st / "calendar.json").write_text("{}", encoding="utf-8")
        (st / "vip.json").write_text("[]", encoding="utf-8")
        (st / "proposed-notes.txt").write_text("not a proposal", encoding="utf-8")
        (st / "applied").mkdir(exist_ok=True)
        (st / "applied" / N1).write_text(self.prop("ABC-A-002", "From Applied"), encoding="utf-8")
        (st / "drafts").mkdir(exist_ok=True)
        (st / "drafts/x.json").write_text(self.prop("ABC-A-002", "From Drafts"), encoding="utf-8")

    def test_forty_hostile_values_apply_nothing_and_the_exact_name_applies_its_own_alone(self):
        self.plant()
        snap, owners = self.files(), self.owners()
        backups = sorted(p.name for p in (self.v.root / "system/backups").glob("*"))
        values = only_values(self.v.root)
        self.assertEqual(len(values), 40)
        for label, value in values:
            for body in ({"only": value}, *([{"hold_peek": True, "only": value}] if label.startswith(PEEK_TOO) else [])):
                with self.subTest(label=label, hold_peek="hold_peek" in body):
                    status, r = self.call(body)
                    self.assertEqual(status, 200, r)
                    self.assertIs(r.get("ok"), False, r)
                    self.assertIn("nothing was applied", str(r.get("message")))
                    self.assertEqual(self.owners(), owners, "no database change")
                    now = self.files()
                    self.assertEqual(sorted(set(now) ^ set(snap)) + [k for k in snap if now.get(k, snap[k]) != snap[k]], [],
                                     "no file changed: no backup, no staged proposal, no root namesake")
        self.assertEqual(sorted(p.name for p in (self.v.root / "system/backups").glob("*")), backups, "no backup")
        # the control: the exact name applies that proposal alone, never its root namesake or another staged one
        status, r = self.call({"hold_peek": True, "only": N1})
        self.assertTrue(r.get("ok"), r)
        got = self.owners()
        self.assertEqual((got["ABC-A-001"], got["ABC-A-002"], got["ABC-A-003"]), ("Named One", owners["ABC-A-002"], owners["ABC-A-003"]))
        self.assertTrue((self.v.root / "system/staging" / N2).is_file() and (self.v.root / "system/staging" / OLD).is_file())
        self.assertEqual((self.v.root / N1).read_bytes(), snap[N1], "the root namesake is never read")
        self.assertTrue(self.post("/api/undo", {"apply_id": r["apply_id"]})["ok"])


# ── k254-a: a document whose project is not a string ──────────────────────────────────────────────────────────────────
CANARY = "KITCANARY277 the quarter's quiet words"
BAD = [("list", ["ABC"]), ("two-item list", ["ABC", "DEF"]), ("empty list", []), ("int", 7), ("float", 7.5), ("dict", {"code": "ABC"}),
       ("nested list", [["ABC"]]), ("true", True), ("false", False)]
ROUTES = ("match-check", "check", "save", "pick", "reshow", "approve")
PROJECT_REFUSALS = ("Its project must be one project code.", "Say which report: weekly or client, and the project's code.")


class NonStringProjectOnEveryRoute(unittest.TestCase):
    """k254-a: the six report routes that take a document refuse a non-string project plainly and write nothing."""
    setUpClass = classmethod(_Audience.setUpClass.__func__)
    tearDownClass = classmethod(_Audience.tearDownClass.__func__)
    post, section, reports, setUp = _Audience.post, _Audience.section, _Audience.reports, _Audience.setUp
    weekly, client, fresh, draft_file = _Audience.weekly, _Audience.client, _Audience.fresh, _Audience.draft_file

    def test_check_refuses_every_non_string_project_even_ones_json_cant_carry(self):
        base = creaite_doc.new("client", "ABC", "Client report", "2026-10-09")
        creaite_doc.check(base)
        for label, bad in BAD + [("tuple", ("ABC",)), ("bytes", b"ABC"), ("set", {"ABC"})]:
            with self.subTest(project=label), self.assertRaises(creaite_doc.DocError):
                creaite_doc.check({**base, "project": bad})

    def tree(self):
        h = hashlib.sha256()
        for f in sorted(self.v.root.rglob("*")):
            rel = f.relative_to(self.v.root).as_posix()
            if f.is_file() and not rel.startswith(("system/logs/", "system/guard/", ".git/")) and "__pycache__" not in rel:
                h.update(rel.encode() + b"\0" + f.read_bytes())
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

    def body(self, route, doc):
        return {"match-check": {"docs": [doc]}, "check": {"doc": doc}, "save": {"doc": doc, "base_version": doc.get("version")},
                "pick": {"doc": doc}, "reshow": {"doc": doc, "section": self.table_id(doc), "refs": ["ABC-A-001"]},
                "approve": {"kind": "client", "code": "ABC", "week_ending": WEEK, "force": True, "doc": doc,
                            "base_version": doc.get("version")}}[route]

    @staticmethod
    def table_id(doc):
        return next(s["id"] for s in doc["sections"] if s.get("type") == "table")

    def test_each_route_refuses_a_non_string_project_with_a_sentence_and_writes_nothing(self):
        d = self.fresh()["doc"]
        d["sections"].append({"id": "free_277", "type": "freetext", "heading": "Notes", "default_heading": "", "hidden": False,
                              "text": CANARY, "audience": "client"})
        d["layout"]["order"] = [s["id"] for s in d["sections"]]
        for route in ROUTES:                                       # control: a string project is answered and accepted (Cap's MEDIUM 1)
            status, r = self.call(route, self.body(route, copy.deepcopy(d)))
            self.assertEqual((status, r.get("ok")), (200, True), (route, r))
            if route == "save":                                    # the save bumps the draft's version: approve sends the new one
                d["version"] = r["version"]
        for label, bad in BAD:
            for route in ROUTES:
                with self.subTest(route=route, project=label):
                    sent = copy.deepcopy(d)
                    sent["project"] = bad
                    status, r = self.call(route, self.body(route, sent))
                    self.assertIn(str(r.get("message") or ""), PROJECT_REFUSALS, (route, r))     # refused for its type, nothing else
        for label, bad in BAD:
            for route in ROUTES:
                with self.subTest(route=route, project=label):
                    sent = copy.deepcopy(d)
                    sent["project"] = bad
                    before = self.tree()
                    status, r = self.call(route, self.body(route, sent))
                    raw = json.dumps(r, default=str)
                    self.assertEqual(status, 200, r)
                    self.assertIs(r.get("ok"), False, r)
                    self.assertTrue(str(r.get("message") or "").strip(), r)
                    for fault in ("Traceback", "TypeError", "unhashable", CANARY):
                        self.assertNotIn(fault, raw)
                    self.assertFalse({"findings", "sections", "doc"} & set(r), r)
                    self.assertEqual(self.tree(), before, "nothing written")


# ── k254-c: the no-project prep page ──────────────────────────────────────────────────────────────────────────────────
TITLE = "Quarterly catch-up"
FOREIGN = "<html>KITFOREIGN279 Alan's own agenda file, not written by creaite</html>"
MARKS = ('<span class="internal">Internal</span> ', "client · never sent</span><h1>")


def unmarked(page):
    """What a page lacks of the Internal marking (empty when it has it all), on what a reader sees: HTML comments are taken out
    first, since prep_view's own comment says "not for the client" too (Cap's LOW 2)."""
    page = re.sub(r"<!--.*?-->", "", page, flags=re.S)
    return [w for w, ok in (("Internal tag", re.search(r'class="internal"[^>]*>\s*Internal\s*<', page)),
                            ("never sent", "never sent" in page), ("not for the client", "not for the client" in page)) if not ok]


class NoProjectPrepPage(unittest.TestCase):
    """k254-c: a no-project prep page is Internal and never sent, and never overwrites a file creaite didn't write or Alan edited."""
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.cleanup)
        prep_world(self.v)
        cal = self.v.root / "system/staging/calendar.json"
        data = json.loads(cal.read_text())
        for evs in data["days"].values():
            evs[0]["title"] = TITLE
        cal.write_text(json.dumps(data))
        self.key = f"09:00|{TITLE}"

    def remember(self, code):
        py(self.v, "import paths; p = paths.ROOT / 'system/config/settings.json'; s = json.loads(p.read_text()); "
                   f"s.setdefault('prep', {{}}).setdefault('series', {{}})['quarterly catch up'] = {code!r}; "
                   "p.write_text(json.dumps(s)); print(json.dumps(1))")

    def build(self, code, about):
        self.remember(code)
        return py(self.v, f"import prep_page; rel, page = prep_page.build({self.key!r}, {{'about': {about!r}}}); print(json.dumps([rel, page]))")

    def agendas(self):
        return py(self.v, "import paths; print(json.dumps(paths.rel(paths.folder('_portfolio', 'agendas'))))")

    def test_the_page_is_internal_and_never_sent_chosen_or_not(self):
        for code in ("_portfolio", ""):
            with self.subTest(project=code or "not chosen"):
                rel, page = self.build(code, f"KITNP about the quarter {code}")
                self.assertTrue(rel.startswith(self.agendas() + "/"), rel)
                self.assertEqual(unmarked(page), [], "the page returned")
                self.assertEqual(unmarked((self.v.root / rel).read_text(encoding="utf-8")), [], "the page filed")

    def test_a_foreign_file_and_an_edited_page_are_never_overwritten(self):
        self.remember("_portfolio")
        target = py(self.v, f"import prep_page; t, r = prep_page.place(prep_page.context({self.key!r})); print(json.dumps(prep_page.paths.rel(t)))")
        self.assertTrue(target.startswith(self.agendas() + "/"), target)
        foreign = self.v.root / target
        foreign.parent.mkdir(parents=True, exist_ok=True)
        foreign.write_text(FOREIGN, encoding="utf-8")
        rel, _ = self.build("_portfolio", "first")
        self.assertEqual(foreign.read_text(encoding="utf-8"), FOREIGN, "a file creaite didn't write is kept")
        self.assertNotEqual(rel, target)
        self.assertTrue((self.v.root / rel).is_file(), "the page went beside it under another name")
        own = self.v.root / rel
        own.write_text(own.read_text(encoding="utf-8") + "\n<!-- KITEDIT279 Alan's note -->", encoding="utf-8")
        edited = own.read_bytes()
        rel2, _ = self.build("_portfolio", "second")
        self.assertEqual(own.read_bytes(), edited, "a page Alan edited is kept")
        self.assertNotEqual(rel2, rel)
        self.assertTrue(rel2.startswith(self.agendas() + "/"), rel2)
        rel3, _ = self.build("_portfolio", "third")
        self.assertEqual(rel3, rel2, "control: creaite's own unchanged page is replaced in place")
        self.assertEqual((foreign.read_text(encoding="utf-8"), own.read_bytes()), (FOREIGN, edited))

    def test_mutant_a_page_without_the_internal_mark_is_seen(self):
        """Proof the check sees the leak (the kit's prep_internal_off), in the vault's own copy of prep_view.py, never the repo's."""
        script = self.v.root / "system/scripts/prep_view.py"
        text = script.read_text(encoding="utf-8")
        for m in MARKS:
            self.assertEqual(text.count(m), 1, f"the mark moved: update MARKS ({m})")
        script.write_text(text.replace(MARKS[0], "", 1).replace(MARKS[1], "client</span><h1>", 1), encoding="utf-8")
        rel, page = self.build("_portfolio", "KITNP mutant")
        self.assertIn("Internal tag", unmarked(page))
        self.assertIn("never sent", unmarked((self.v.root / rel).read_text(encoding="utf-8")))


del _Audience                           # its harness is borrowed above; its own tests run in test_client_audience.py


if __name__ == "__main__":
    unittest.main(verbosity=2)
