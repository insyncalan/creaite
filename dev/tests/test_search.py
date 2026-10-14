"""Tests for vault search (BL-07): the index, the query parser, search, the Ask context and enrichment.

Run: python3 dev/tests/test_search.py
Each test builds a throwaway vault (test_tracker.Vault) and runs the real scripts there.
"""
import json
import sqlite3
import sys
import time
import unittest
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import ABC, Vault, action  # noqa: E402


def pdf_file(content, font=b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>", extra=(), compress=True):
    """A valid one-page PDF (catalog, page tree, font, cross-reference table) showing `content`, a content stream;
    `extra` adds objects from 6 up (BL-275: pypdf needs the page tree the old stand-in lacked)."""
    data = zlib.compress(content) if compress else content
    stream = (b"<< /Length " + str(len(data)).encode() + (b" /Filter /FlateDecode" if compress else b"") + b" >>\nstream\n"
              + data + b"\nendstream")
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
            stream, font, *extra]
    out, offsets = bytearray(b"%PDF-1.4\n"), []
    for n, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += str(n).encode() + b" 0 obj\n" + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 " + str(len(objs) + 1).encode() + b"\n0000000000 65535 f \n"
    out += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer\n<< /Size " + str(len(objs) + 1).encode() + b" /Root 1 0 R >>\nstartxref\n" + str(xref).encode() + b"\n%%EOF\n"
    return bytes(out)


def pdf(text, compress=True):
    """A one-page PDF whose content stream is Flate-compressed (what most PDF tools write), or plain (BL-228)."""
    return pdf_file(f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("latin-1"), compress=compress)


def put(v, rel, text):
    p = v.root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(text if isinstance(text, bytes) else text.encode("utf-8"))
    return p


class IndexTests(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.v.run("init")

    def tearDown(self):
        self.v.cleanup()

    def query(self, text, *args):
        return json.loads(self.v.run("query", text, *args).stdout)

    def test_reports_and_pdf_text_are_indexed(self):
        put(self.v, f"{ABC}/reports/2026-10-02 Weekly report.md", "Weekly report: build is slipping because of data access")
        put(self.v, f"{ABC}/documents/Contract.pdf", pdf("Vendor contract renewal terms"))
        put(self.v, f"{ABC}/documents/Scanned.pdf", b"%PDF-1.4 binary \x00\x01 no text here")
        self.assertIn("Indexed 3 file(s)", self.v.run("index").stdout)
        hit = self.query("slipping")
        self.assertEqual((hit[0]["kind"], hit[0]["date"], hit[0]["project"]), ("report", "2026-10-02", "ABC"))
        self.assertEqual(self.query("renewal")[0]["path"], f"{ABC}/documents/Contract.pdf")      # PDF text
        self.assertEqual(self.query("Scanned")[0]["path"], f"{ABC}/documents/Scanned.pdf")      # unreadable: by name only
        self.assertEqual(self.query("binary"), [])

    def test_word_forms_and_prefixes(self):
        put(self.v, f"{ABC}/documents/Plan.md", "The UAT start slipped by two weeks")
        self.v.run("index")
        self.assertEqual(len(self.query("slip")), 1)             # stemming: slip finds slipped
        self.assertEqual(len(self.query("slipping")), 1)
        self.assertEqual(len(self.query("weeks")), 1)
        self.assertEqual(len(self.query("wee")), 1)              # the last word matches as a prefix (as you type)
        self.assertEqual(self.query("start xyz"), [])

    def test_an_index_made_before_word_forms_is_recreated(self):
        put(self.v, f"{ABC}/documents/Plan.md", "The start slipped")
        db = self.v.root / "system/tracker.db"
        with sqlite3.connect(db) as con:
            con.execute("DROP TABLE vault_search")
            con.execute("CREATE VIRTUAL TABLE vault_search USING fts5(path, project, kind, date, content)")
        self.assertIn("recreated with word forms and rebuilt (1 file(s))", self.v.run("migrate").stdout)
        self.assertEqual(len(self.query("slip")), 1)                                   # migrate filled it; no `index` needed
        with sqlite3.connect(db) as con:
            self.assertIn("porter", con.execute("SELECT sql FROM sqlite_master WHERE name = 'vault_search'").fetchone()[0])

    def test_apply_keeps_the_index_fresh(self):
        self.v.run("index")
        self.assertEqual(self.query("rollout"), [])
        spec = {"created": "2026-10-04T09:00:00", "source_run": "cx-edit", "files": [], "items": [],
                "file_changes": {"title": "Plan", "project": "ABC", "file_changes_decision": "approved", "file_ops": [
                    {"op": "write", "path": f"{ABC}/documents/Rollout plan.md", "content": "Rollout plan for the pilot",
                     "previous": None}]}}
        (self.v.root / "system/staging/proposed-plan.json").write_text(json.dumps(spec))
        self.v.run("apply")
        self.assertEqual(self.query("rollout")[0]["path"], f"{ABC}/documents/Rollout plan.md")     # no `index` run by hand
        self.v.run("undo")
        self.assertEqual(self.query("rollout"), [])                                                  # and after undo

    def py(self, code):
        """Run a snippet against this vault's own scripts (its paths.py, so nothing leaks between vaults)."""
        import subprocess
        r = subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts'); import tracker\n" + code],
                           cwd=self.v.root, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout) if r.stdout.strip() else None

    def test_staleness_is_a_cheap_check(self):
        state = "print(json.dumps(tracker.index_state()))"
        self.assertEqual(self.py(state), [True, "never built"])
        self.py("tracker.build_index()")
        self.assertEqual(self.py(state), [False, ""])
        time.sleep(0.05)
        put(self.v, f"{ABC}/documents/New.md", "new")
        self.assertEqual(self.py(state), [True, "files added or removed"])
        self.py("tracker.build_index()")
        time.sleep(0.05)
        (self.v.root / f"{ABC}/documents/New.md").write_text("changed")
        self.assertEqual(self.py(state), [True, "files changed"])


NOW = "2026-10-07 10:00"           # a Wednesday


class SearchBase(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.v.run("init")

    def tearDown(self):
        self.v.cleanup()

    def s(self, *args):
        import os
        import subprocess
        r = subprocess.run([sys.executable, str(self.v.root / "system/scripts/search.py"), *args], cwd=self.v.root,
                           capture_output=True, text=True, env={**os.environ, "CREAITE_NOW": NOW})
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)


class ParserTests(SearchBase):
    def parse(self, text):
        out = self.s("parse", text)
        return out["terms"], [(c["kind"], c["value"]) for c in out["chips"]]

    def test_project_codes(self):
        self.assertEqual(self.parse("ABC data access"), (["data", "access"], [("project", "ABC")]))
        self.assertEqual(self.parse("abc slipped"), (["slipped"], [("project", "ABC")]))          # any case
        self.assertEqual(self.parse("XYZ plan"), (["XYZ", "plan"], []))                              # not a project here
        self.assertEqual(self.parse("ABC-A-003"), (["ABC-A-003"], []))                               # an item ID stays a word

    def test_people_aliases_and_emails(self):
        self.assertEqual(self.parse("Sara Example UAT"), (["UAT"], [("person", "Sara Example")]))
        self.assertEqual(self.parse("what did Sara say"), (["say"], [("person", "Sara Example")]))   # an alias
        self.assertEqual(self.parse("omar@def.example"), ([], [("person", "Omar Ali")]))
        self.assertEqual(self.parse("Alan budget"), (["budget"], [("person", "Alan Carter")]))        # Alan's short forms
        self.assertEqual(self.parse("who ac I")[1], [])                                               # "AC" needs capitals
        self.assertEqual(self.parse("AC budget"), (["budget"], [("person", "Alan Carter")]))

    def test_types(self):
        self.assertEqual(self.parse("risks"), ([], [("type", "Risk")]))
        self.assertEqual(self.parse("open issues and decisions"), (["open"], [("type", "Issue"), ("type", "decision")]))
        self.assertEqual(self.parse("steering minutes"), (["steering"], [("type", "minutes")]))
        self.assertEqual(self.parse("weekly report")[1], [("type", "report")])
        self.assertEqual(self.parse("vendor documents")[1], [("type", "documents")])

    def test_dates(self):
        def date_of(text):
            chip = next(c for c in self.s("parse", text)["chips"] if c["kind"] == "date")
            return chip["from"], chip["to"]
        self.assertEqual(date_of("today"), ("2026-10-07", "2026-10-07"))
        self.assertEqual(date_of("yesterday"), ("2026-10-06", "2026-10-06"))
        self.assertEqual(date_of("last week"), ("2026-09-28", "2026-10-04"))                         # Monday to Sunday
        self.assertEqual(date_of("this week"), ("2026-10-05", "2026-10-11"))
        self.assertEqual(date_of("last month"), ("2026-09-01", "2026-09-30"))
        self.assertEqual(date_of("this month"), ("2026-10-01", "2026-10-31"))
        self.assertEqual(date_of("since 01-09-2026"), ("2026-09-01", None))
        self.assertEqual(date_of("since 2026-09-01"), ("2026-09-01", None))
        self.assertEqual(date_of("in September"), ("2026-09-01", "2026-09-30"))
        self.assertEqual(date_of("in November"), ("2025-11-01", "2025-11-30"))                      # the latest one that's passed
        self.assertEqual(date_of("in March 2026"), ("2026-03-01", "2026-03-31"))
        self.assertEqual(date_of("steering 01-10-2026"), ("2026-10-01", "2026-10-01"))
        label = next(c["label"] for c in self.s("parse", "last month")["chips"])
        self.assertEqual(label, "Last month (01-09-2026 to 30-09-2026)")                               # shown DD-MM-YYYY
        self.assertEqual(self.parse("in the plan"), (["plan"], []))

    def test_everything_at_once_and_stopwords(self):
        terms, chips = self.parse("risks ABC Sara since 01-09-2026 data access")
        self.assertEqual(terms, ["data", "access"])
        self.assertEqual({c[0] for c in chips}, {"type", "project", "person", "date"})
        self.assertEqual(self.parse("what is the")[0], ["what", "is", "the"])                       # never empties the search
        self.assertEqual(self.parse('"data access" ABC')[0], ["data access"])                        # a quoted phrase stays whole


class SearchTests(SearchBase):
    def setUp(self):
        super().setUp()
        v = self.v
        v.propose("items", [
            action(1, description="Escalate the data access delay to the client CIO", owner="Sara Example",
                   raised="2026-09-10"),
            action(2, description="Book the UAT environment", owner="Omar Ali", raised="2026-10-01"),
            {"n": 3, "op": "new", "table": "raid", "match": "strong", "flags": [], "decision": "approved",
             "values": {"project": "ABC", "type": "Risk", "description": "Data access slipped, so UAT may slip",
                        "impact": "High", "likelihood": "High", "owner": "Sara Example", "raised": "2026-09-20",
                        "source": f"{ABC}/minutes/x.md — Risks"}},
            {"n": 4, "op": "new", "table": "decisions", "match": "strong", "flags": [], "decision": "approved",
             "values": {"project": "ABC", "decision": "Go-live moves by two weeks", "made_by": "Jane Doe",
                        "date": "2026-09-25", "source": f"{ABC}/minutes/x.md — Decisions"}}])
        v.run("apply")
        put(v, f"{ABC}/minutes/2026-09-25 Steering.md", "# Decisions\nGo-live moves because data access slipped.\n\n# Action Items\nSara to chase.")
        put(v, f"{ABC}/transcripts/2026-09-25 Steering.vtt", "WEBVTT\n\n00:00:01.000 --> 00:00:05.000\n<v Sara Example>The data access is still late</v>")
        put(v, f"{ABC}/reports/2026-10-02 Weekly report.md", "Weekly report. Build slipping; data access is the blocker.")
        put(v, f"{ABC}/documents/Plans/2026-08-01 Plan.md", "Delivery plan. Data access request goes to the client.")
        put(v, "projects/_portfolio/minutes/2026-10-05 Portfolio.md", "Portfolio review: vendor capacity.")
        v.run("index")

    def q(self, *args):
        return self.s("query", *args)

    def titles(self, res, group):
        return [r["title"] for r in res["groups"][group]]

    def test_grouped_results_with_snippets_dates_and_where_they_open(self):
        r = self.q("data access")
        self.assertEqual([c["kind"] for c in r["chips"]], [])
        self.assertEqual(set(r["groups"]), {"items", "meetings", "reports", "documents"})
        self.assertEqual({x["id"] for x in r["groups"]["items"]}, {"ABC-A-001", "ABC-003"})
        self.assertEqual(sorted(self.titles(r, "meetings")), ["2026-09-25 Steering", "2026-09-25 Steering"])
        self.assertEqual(self.titles(r, "reports"), ["2026-10-02 Weekly report"])
        self.assertEqual(self.titles(r, "documents"), ["2026-08-01 Plan"])
        item = next(x for x in r["groups"]["items"] if x["id"] == "ABC-A-001")
        self.assertEqual((item["kind"], item["project"], item["date_shown"], item["opens"]),
                         ("action", "ABC", "10-09-2026", {"type": "item", "table": "actions", "id": "ABC-A-001"}))
        self.assertIn("<mark>data</mark> <mark>access</mark>", item["snippet"])                    # highlighted
        meet = r["groups"]["meetings"][0]
        self.assertEqual((meet["date_shown"], meet["opens"]["type"], meet["opens"]["q"]), ("25-09-2026", "preview", "data access"))
        self.assertIn("<mark>", meet["snippet"])
        self.assertEqual(r["groups"]["documents"][0]["opens"]["type"], "file")
        self.assertEqual(r["groups"]["reports"][0]["opens"]["type"], "file")
        self.assertTrue(r["groups"]["reports"][0]["date_shown"].startswith("02-10-2026"))

    def test_chips_filter_and_come_back(self):
        r = self.q("risks ABC data")
        self.assertEqual([(c["kind"], c["value"]) for c in r["chips"]], [("type", "Risk"), ("project", "ABC")])
        self.assertEqual([x["id"] for x in r["groups"]["items"]], ["ABC-003"])
        self.assertEqual(r["groups"]["meetings"] + r["groups"]["reports"] + r["groups"]["documents"], [])   # risks: items only
        r = self.q("Sara data access")                                                              # a person: items she owns, files naming her
        self.assertEqual({x["id"] for x in r["groups"]["items"]}, {"ABC-A-001", "ABC-003"})
        self.assertEqual(self.titles(r, "meetings"), ["2026-09-25 Steering"])                       # the transcript names her
        r = self.q("data access since 01-10-2026")
        self.assertEqual(r["groups"]["items"], [])
        self.assertEqual(self.titles(r, "reports"), ["2026-10-02 Weekly report"])
        r = self.q("data access in September")
        self.assertEqual({x["id"] for x in r["groups"]["items"]}, {"ABC-A-001", "ABC-003"})
        self.assertEqual(r["groups"]["reports"], [])
        self.assertEqual(self.titles(self.q("minutes data access"), "meetings"), ["2026-09-25 Steering"])

    def test_removed_chips_and_explicit_filters(self):
        r = self.q("risks ABC data", "--skip", "type:Risk")
        self.assertEqual([c["kind"] for c in r["chips"]], ["project"])
        self.assertGreater(len(r["groups"]["items"]), 1)                                            # no longer risks only
        r = self.q("data", "--project", "ABC", "--kind", "decision", "--from", "2026-09-01")
        self.assertEqual([(c["kind"], c["value"]) for c in r["chips"]],
                         [("project", "ABC"), ("type", "decision"), ("date", "2026-09-01..")])
        self.assertEqual(r["groups"]["items"], [])                                                  # the decision doesn't say "data"
        self.assertEqual([x["id"] for x in self.q("go-live", "--kind", "decision")["groups"]["items"]], ["ABC-D-004"])
        self.assertEqual(self.q("ABC", "--no-parse")["chips"], [])                                  # words as typed

    def test_only_filters_lists_by_date_and_nothing_searches_nothing(self):
        r = self.q("decisions last month")
        self.assertEqual([x["id"] for x in r["groups"]["items"]], ["ABC-D-004"])
        self.assertEqual(self.q("")["totals"], {"items": 0, "meetings": 0, "reports": 0, "documents": 0})

    def test_word_forms_item_ids_and_project_scope(self):
        self.assertEqual({x["id"] for x in self.q("slip")["groups"]["items"]}, {"ABC-003"})          # LIKE: slipped contains slip
        self.assertEqual(self.titles(self.q("slip"), "reports"), ["2026-10-02 Weekly report"])      # stemming: slipping
        self.assertEqual(self.q("ABC-A-002")["groups"]["items"][0]["id"], "ABC-A-002")
        self.assertEqual(self.titles(self.q("vendor"), "meetings"), ["2026-10-05 Portfolio"])
        self.assertEqual(self.q("vendor", "--project", "ABC")["groups"]["meetings"], [])

    def test_each_group_is_capped_at_twenty(self):
        for i in range(25):
            put(self.v, f"{ABC}/documents/Note {i:02d}.md", f"A note about the zebra crossing {i}")
        self.v.run("index")
        r = self.q("zebra")
        self.assertEqual((len(r["groups"]["documents"]), r["totals"]["documents"]), (20, 25))

    def test_documents_can_be_left_out(self):
        cfg = self.v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text())
        data["search"] = {"include_documents": False}
        cfg.write_text(json.dumps(data))
        self.assertEqual(self.q("plan")["groups"]["documents"], [])

    def test_a_stale_index_is_rebuilt_by_the_search(self):
        import time
        time.sleep(0.05)
        put(self.v, f"{ABC}/documents/Late.md", "A note about the quokka")
        r = self.q("quokka")
        self.assertTrue(r["rebuilt"])
        self.assertEqual(self.titles(r, "documents"), ["Late"])
        self.assertFalse(self.q("quokka")["rebuilt"])

    def test_context_gathers_passages_with_sections_and_tracker_rows(self):
        c = self.s("context", "why did go-live move?", "--json")
        text = c["text"]
        self.assertIn("Question: why did go-live move?", text)
        self.assertIn("Today is 07-10-2026.", text)
        self.assertIn("Words searched for: go-live, move", text)                                    # question words dropped
        self.assertIn("[2026-09-25 Steering.md › Decisions] — Meeting minutes, 25-09-2026, ABC", text)
        self.assertIn("Go-live moves because data access slipped.", text)
        self.assertIn("ABC-D-004 (ABC) — Decision, made by Jane Doe, on 25-09-2026: Go-live moves by two weeks", text)
        self.assertEqual({s["kind"] for s in c["sources"]} >= {"minutes", "item"}, True)
        self.assertIn({"name": "ABC-D-004", "path": "", "kind": "item", "table": "decisions", "project": "ABC"}, c["sources"])

    def test_context_labels_documents_and_honours_filters_and_the_setting(self):
        text = self.s("context", "what is the delivery plan?", "--json")["text"]
        self.assertIn("[2026-08-01 Plan.md] — Document (internal), 01-08-2026, ABC", text)
        text = self.s("context", "go-live since 01-10-2026", "--json")["text"]
        self.assertNotIn("Steering.md", text)                                                      # before the date
        cfg = self.v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text())
        data["search"] = {"include_documents": False}
        cfg.write_text(json.dumps(data))
        self.assertNotIn("Plan.md", self.s("context", "what is the delivery plan?", "--json")["text"])

    def test_context_keeps_to_the_size_budget(self):
        for i in range(30):
            put(self.v, f"{ABC}/minutes/2026-09-{i % 28 + 1:02d} Weekly sync {i}.md", "# Updates\n" + f"Data access update {i}. " * 60)
        self.v.run("index")
        full = self.s("context", "data access update", "--json")["text"]
        self.assertGreater(len(full), 5000)
        self.assertLessEqual(len(full), 40000)                                                     # the default budget
        cfg = self.v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text())
        data["search"] = {"ask_budget_chars": 3000}
        cfg.write_text(json.dumps(data))
        small = self.s("context", "data access update", "--json")
        self.assertLessEqual(len(small["text"]), 3000)
        self.assertIn("Question: data access update", small["text"])                               # the question always survives
        self.assertTrue(small["sources"])

    def test_preview_is_limited_to_indexed_files(self):
        pv = self.s("preview", f"{ABC}/minutes/2026-09-25 Steering.md", "data access")
        self.assertTrue(pv["ok"])
        self.assertIn("<mark>data</mark> <mark>access</mark>", pv["html"])
        self.assertFalse(self.s("preview", "system/config/settings.json")["ok"])
        self.assertFalse(self.s("preview", "../outside.txt")["ok"])


class EnrichmentTests(SearchBase):
    """A two-line summary and topic tags written once when a meeting or report is processed, then searched by keyword."""

    def setUp(self):
        super().setUp()
        put(self.v, f"{ABC}/minutes/2026-09-25 Steering.md", "# Decisions\nGo-live moves by two weeks.")
        put(self.v, "projects/_portfolio/minutes/2026-09-25 Steering.md", "# Decisions\nGo-live moves by two weeks.")   # a copy
        put(self.v, f"{ABC}/minutes/2026-10-05 Sync.md", "Short sync about the pilot.")
        put(self.v, f"{ABC}/reports/2026-10-02 Weekly report.md", "Build is slipping.")
        put(self.v, f"{ABC}/documents/Plan.md", "A plan.")

    def enrich(self, *args, ok=True):
        import subprocess
        r = subprocess.run([sys.executable, str(self.v.root / "system/scripts/search.py"), "enrich", *args], cwd=self.v.root,
                           capture_output=True, text=True)
        if ok:
            self.assertEqual(r.returncode, 0, r.stderr)
        return r

    def sidecar(self, rel):
        import hashlib
        return self.v.root / "system/search" / (hashlib.sha256(rel.encode()).hexdigest() + ".json")

    def test_set_writes_a_sidecar_per_path(self):
        a, b = f"{ABC}/minutes/2026-09-25 Steering.md", "projects/_portfolio/minutes/2026-09-25 Steering.md"
        out = self.enrich("set", "--path", a, "--path", b, "--summary", "Go-live moved by two weeks.\nData access is the cause.",
                          "--tags", "Go-Live, data access, UAT, data access").stdout
        self.assertIn("Wrote 2 summary file(s)", out)
        rec = json.loads(self.sidecar(a).read_text())
        self.assertEqual(rec, {"path": a, "summary": "Go-live moved by two weeks.\nData access is the cause.",
                               "tags": ["go-live", "data access", "uat"]})                 # lower case, no duplicates
        self.assertTrue(self.sidecar(b).exists())

    def test_set_refuses_what_isnt_a_summary_or_a_meeting(self):
        ok = ("--summary", "One line.", "--tags", "a, b, c")
        path = f"{ABC}/minutes/2026-10-05 Sync.md"
        self.assertIn("three to eight", self.enrich("set", "--path", path, "--summary", "One line.", "--tags", "a, b", ok=False).stderr)
        self.assertIn("three to eight", self.enrich("set", "--path", path, "--summary", "x", "--tags", "a,b,c,d,e,f,g,h,i", ok=False).stderr)
        self.assertIn("one or two lines", self.enrich("set", "--path", path, "--summary", "a\nb\nc", "--tags", "a,b,c", ok=False).stderr)
        for bad in (f"{ABC}/documents/Plan.md", "/etc/passwd", f"{ABC}/minutes/../../x.md", "system/config/settings.json"):
            self.assertIn("isn't a minutes, transcript or report path", self.enrich("set", "--path", bad, *ok, ok=False).stderr, bad)
        self.assertFalse((self.v.root / "system/search").exists() and any((self.v.root / "system/search").glob("*.json")))

    def test_the_summary_and_tags_are_searched(self):
        self.v.run("index")
        self.assertEqual(self.s("query", "escalation")["groups"]["meetings"], [])           # the words aren't in the file
        self.enrich("set", "--path", f"{ABC}/minutes/2026-10-05 Sync.md", "--summary", "Escalation to the client CIO over the pilot.",
                    "--tags", "pilot, escalation, supplier delay")
        r = self.s("query", "supplier delay")                                                   # found: the index is stale, so it rebuilds
        self.assertTrue(r["rebuilt"])
        self.assertEqual([x["title"] for x in r["groups"]["meetings"]], ["2026-10-05 Sync"])
        self.assertEqual([x["title"] for x in self.s("query", "escalation")["groups"]["meetings"]], ["2026-10-05 Sync"])
        self.assertIn("<mark>Escalation</mark>", self.s("query", "escalation")["groups"]["meetings"][0]["snippet"])

    def test_a_filter_only_search_shows_the_summary(self):
        self.enrich("set", "--path", f"{ABC}/reports/2026-10-02 Weekly report.md", "--summary", "Build slipping; data access is the blocker.",
                    "--tags", "build, data access, slip")
        r = self.s("query", "reports last week" if False else "reports since 01-10-2026")
        self.assertEqual(r["groups"]["reports"][0]["snippet"], "Build slipping; data access is the blocker.")

    def test_missing_lists_meetings_and_reports_without_a_summary(self):
        out = self.enrich("--missing", "--json").stdout
        miss = json.loads(out)
        self.assertEqual([m["path"] for m in miss], [f"{ABC}/minutes/2026-10-05 Sync.md", f"{ABC}/reports/2026-10-02 Weekly report.md",
                                                     f"{ABC}/minutes/2026-09-25 Steering.md"])   # newest first; documents aren't listed
        steering = miss[2]
        self.assertEqual(sorted(steering["paths"]), sorted([f"{ABC}/minutes/2026-09-25 Steering.md",
                                                            "projects/_portfolio/minutes/2026-09-25 Steering.md"]))
        self.assertIn("(also 1 other copy)", self.enrich("--missing").stdout)
        # a summary for either copy covers the meeting
        self.enrich("set", "--path", "projects/_portfolio/minutes/2026-09-25 Steering.md", "--summary", "Go-live moved.",
                    "--tags", "go-live, schedule, decision")
        self.assertEqual(len(json.loads(self.enrich("--missing", "--json").stdout)), 2)
        for rel in (f"{ABC}/minutes/2026-10-05 Sync.md", f"{ABC}/reports/2026-10-02 Weekly report.md"):
            self.enrich("set", "--path", rel, "--summary", "A summary.", "--tags", "a, b, c")
        self.assertIn("Every indexed meeting and report has a summary.", self.enrich("--missing").stdout)

    def test_a_copied_meeting_is_enriched_once(self):
        self.enrich("set", "--path", f"{ABC}/minutes/2026-09-25 Steering.md", "--summary", "Go-live moved.", "--tags", "go-live, schedule, decision")
        self.v.run("index")
        hits = self.s("query", "schedule")["groups"]["meetings"]
        self.assertEqual(len(hits), 1)                                                       # the two copies are one entry
        self.assertEqual(hits[0]["project"], "ABC _portfolio")


if __name__ == "__main__":
    unittest.main()
