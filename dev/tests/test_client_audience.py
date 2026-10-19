"""v2.5.0 audience bypass: a client report is a client report whatever its `audience` says. The data is fictional.

Run: python3 dev/tests/test_client_audience.py        (the PDF checks need Chrome; skipped without it)

A client report (kind "client") saved with audience "internal" (or the key left out), or a draft file edited on disk to say so, used
to be saved, approved and exported with hidden item IDs, titles and owners, "confidential", "Internal only:", a creaite:item/ link
and an internal-audience text section, the gate finding nothing. Now:
  - the save route (and Approve with a document sent) refuses a client-kind document whose audience isn't "client"
    (creaite_doc.check_audience);
  - a stored report is read for the draft route, Approve, filing and every export with creaite_doc.read_report, which reads a
    client report as one (its audience client, its project name and client derived again), so Approve and every export are refused with the gate's findings and nothing reaches the Reports folder;
  - stage_client and client_check.left_out normalise on their own too (each checked here with a reader that doesn't normalise).
The control (a normal client draft, audience "client") saves, approves and exports as before.
"""
import json
import os
import subprocess
import sys
import unittest
import zipfile
import html as htmllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_report_export_save as S  # noqa: E402

SCRIPTS = Path(__file__).resolve().parents[2] / "system" / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SCRIPTS / "vendor"))
import creaite_doc  # noqa: E402

WEEK = "2026-10-09"
MISSING = object()
HEAD = "import sys, json; sys.path.insert(0, 'system/scripts')\nimport client_check, client_leak, creaite_doc, report_doc\n"


def pdf_text(p):
    """The PDF's text, through the bundled pypdf (pdftotext may be missing)."""
    import pypdf
    return "\n".join(page.extract_text() or "" for page in pypdf.PdfReader(str(p)).pages)


class Audience(unittest.TestCase):
    """The routes on a live server in a throwaway vault (test_report_export_save's harness, without its own tests)."""
    setUpClass = classmethod(S.ExportSave.setUpClass.__func__)
    tearDownClass = classmethod(S.ExportSave.tearDownClass.__func__)
    post, section, reports, setUp = S.ExportSave.post, S.ExportSave.section, S.ExportSave.reports, S.ExportSave.setUp
    weekly, client, export, formats = S.ExportSave.weekly, S.ExportSave.client, S.ExportSave.export, S.ExportSave.formats

    def hidden_item(self):
        import sqlite3
        from contextlib import closing
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            return con.execute("SELECT id, description, owner FROM actions WHERE client_visible=0 AND owner<>'' LIMIT 1").fetchone()

    def needles(self):
        hid, title, owner = self.hidden_item()
        return [hid, title, owner, "confidential", "Internal only", "walrus"]

    def payload(self):
        hid, title, owner = self.hidden_item()
        return f"{owner} owns {hid} {title}. This is confidential. Internal only: keep. [the plan](creaite:item/{hid})"

    def add_payload(self, doc):
        doc["sections"] = [s for s in doc["sections"] if s["id"] not in ("free_x", "free_int")]
        doc["sections"].append({"id": "free_x", "type": "freetext", "heading": "Notes", "default_heading": "", "hidden": False,
                                "text": self.payload(), "audience": "client"})
        doc["sections"].append({"id": "free_int", "type": "freetext", "heading": "Vendor notes", "default_heading": "",
                                "hidden": False, "text": "INTERNAL walrus words.", "audience": "internal"})
        doc["layout"]["order"] = [s["id"] for s in doc["sections"]]
        return doc

    @staticmethod
    def set_audience(doc, audience):
        if audience is MISSING:
            doc.pop("audience", None)
        else:
            doc["audience"] = audience
        return doc

    def scan(self, p, needles):
        p = Path(p)
        if p.suffix == ".docx":
            with zipfile.ZipFile(p) as z:
                t = "".join(z.read(n).decode("utf-8", "ignore") for n in z.namelist() if n.endswith(".xml"))
        elif p.suffix == ".pdf":
            t = pdf_text(p)
        else:
            t = p.read_text(encoding="utf-8", errors="ignore")
        t = htmllib.unescape(t).lower()
        return [n for n in needles if n.lower() in t]

    def reports_hold(self, needles):
        """The client report files in the Reports folder that hold any needle (the internal weekly report rightly holds them)."""
        return {f.name: hit for f in self.reports.glob("*Client report*") if f.is_file() for hit in [self.scan(f, needles)] if hit}

    def draft_file(self):
        return self.v.root / "system/staging/drafts" / f"{S.CLIENT_STEM}.html"

    def py(self, code):
        r = subprocess.run([sys.executable, "-c", HEAD + code], cwd=self.v.root, env={**os.environ, "CREAITE_NOW": S.NOW},
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def fresh(self):
        """A clean client draft (the internal week approved); the draft route's answer."""
        self.draft_file().unlink(missing_ok=True)          # an earlier subtest's draft
        for f in self.reports.glob("*Client report*"):          # and its filed or exported client report
            f.unlink()
        self.client()
        r = self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": WEEK})
        self.assertTrue(r["ok"], r)
        return r

    def tamper_on_disk(self, audience):
        """ask creaite's way: the saved draft file edited directly, the payload in and the audience changed."""
        f = self.draft_file()
        d = self.add_payload(creaite_doc.read(f))
        d["audience"] = "client"
        text = creaite_doc.dumps(d, keep_text=True)
        old = '"audience": "client",\n "project"'
        self.assertIn(old, text)
        new = {MISSING: '"project"'}.get(audience) or f'"audience": {json.dumps(audience)},\n "project"'
        f.write_text(text.replace(old, new, 1), encoding="utf-8")
        raw = json.loads(creaite_doc.BLOCK.search(f.read_text()).group(1))
        self.assertEqual(raw.get("audience", "<missing>"), "<missing>" if audience is MISSING else audience)
        self.assertIn(self.hidden_item()[0], f.read_text())

    # ── the save route ──────────────────────────────────────────────────────────────────────────────────────────────────
    def test_save_route_refuses_a_client_report_whose_audience_is_not_client(self):
        for audience in ("internal", MISSING, "distributed", "Client", "weekly", None):
            with self.subTest(audience=audience):
                r = self.fresh()
                before = self.draft_file().read_bytes()
                doc = self.set_audience(self.add_payload(r["doc"]), audience)
                sv = self.post("/api/report/save", {"doc": doc, "base_version": r["version"]})
                self.assertFalse(sv["ok"], sv)
                self.assertRegex(sv["message"], r"(?i)audience")
                self.assertEqual(self.draft_file().read_bytes(), before)                 # nothing was saved
                self.assertEqual(self.reports_hold(self.needles()), {})

    def test_approve_with_a_document_sent_refuses_an_internal_audience(self):
        for audience in ("internal", MISSING):
            with self.subTest(audience=audience):
                r = self.fresh()
                before = self.draft_file().read_bytes()
                doc = self.set_audience(self.add_payload(r["doc"]), audience)
                a = self.post("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "force": True,
                                                       "doc": doc, "base_version": r["version"]})
                self.assertFalse(a["ok"], a)
                self.assertEqual(self.draft_file().read_bytes(), before)
                self.assertEqual(self.reports_hold(self.needles()), {})

    # ── a draft file edited on disk ─────────────────────────────────────────────────────────────────────────────────────
    def test_a_draft_edited_on_disk_is_read_as_client_and_refused_at_approve_and_every_export(self):
        needles = self.needles()
        for audience in ("internal", MISSING, "distributed"):
            with self.subTest(audience=audience):
                self.fresh()
                self.tamper_on_disk(audience)
                d = self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": WEEK})
                self.assertEqual(d["doc"]["audience"], "client")                         # read as a client document
                self.assertTrue(d["findings"], d)
                a = self.post("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "force": True})
                self.assertFalse(a["ok"], a)
                self.assertIn("possible internal content", a["message"])
                for fmt in self.formats():
                    e = self.export(fmt, "client", on_clash="number")
                    self.assertFalse(e["ok"], (fmt, e))
                    self.assertTrue(e.get("findings"), (fmt, e))
                self.assertEqual(self.reports_hold(needles), {})

    # ── a draft whose kind was edited on disk ───────────────────────────────────────────────────────────────────────────
    def tamper_kind(self, kind, audience):
        f = self.draft_file()
        text = f.read_text()
        m = creaite_doc.BLOCK.search(text)
        d = self.add_payload(json.loads(m.group(1)))
        for key, value in (("kind", kind), ("audience", audience)):
            if value is MISSING:
                d.pop(key, None)
            else:
                d[key] = value
        f.write_text(text[:m.start(1)] + creaite_doc.data_json(d) + text[m.end(1):], encoding="utf-8")
        self.assertIn(self.hidden_item()[0], f.read_text())

    def test_a_draft_whose_kind_was_edited_on_disk_is_refused_at_approve_and_every_export(self):
        needles = self.needles()
        for kind in ("weekly", "minutes", MISSING, ["client"], "Client"):
            for audience in ("internal", MISSING):
                with self.subTest(kind=kind, audience=audience):
                    self.fresh()
                    self.tamper_kind(kind, audience)
                    a = self.post("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "force": True})
                    self.assertFalse(a["ok"], a)
                    self.assertRegex(a["message"], r"(?i)isn't this report|isn't a creaite|kind")
                    for fmt in self.formats():
                        e = self.export(fmt, "client", on_clash="number")
                        self.assertFalse(e["ok"], (fmt, e))
                    self.assertEqual(list(self.reports.glob("*Client report*")), [])     # nothing filed or exported
                    self.assertEqual(self.reports_hold(needles), {})

    # ── one read between the gate and the output (time of check, time of use) ──────────────────────────────────────────
    def swap_after_first_read(self):
        """Python run in the vault: every read of the client draft after the first finds the payload version on disk (a file
        replaced whole between the gate's read and any later one)."""
        f = self.draft_file()
        clean = f.read_text()
        m = creaite_doc.BLOCK.search(clean)
        d = self.add_payload(json.loads(m.group(1)))
        dirty = clean[:m.start(1)] + creaite_doc.data_json(d) + clean[m.end(1):]
        (self.v.root / "dirty.txt").write_text(dirty, encoding="utf-8")
        return ("import pathlib\n_orig = creaite_doc.read\n"
                "def _read(p):\n    d = _orig(p)\n"
                f"    if pathlib.Path(str(creaite_doc.real(p))).name == {f.name!r}:\n"
                f"        pathlib.Path({str(f)!r}).write_text(pathlib.Path('dirty.txt').read_text())\n"
                "    return d\ncreaite_doc.read = _read\n"
                "class H:\n    def send(self, code, body):\n        self.out = body\n        return body\n")

    def test_export_builds_from_the_document_it_checked(self):
        for fmt in self.formats():
            with self.subTest(fmt=fmt):
                self.fresh()
                out = self.py(self.swap_after_first_read() + "import report_server\nh = H()\n"
                              f"report_server.export_route(h, {{'kind': 'client', 'code': 'ABC', 'week_ending': {WEEK!r}, "
                              f"'fmt': {fmt!r}, 'on_clash': 'number'}})\nprint(json.dumps(h.out))")
                self.assertTrue(out["ok"], out)
                self.assertEqual(self.scan(self.v.root / out["path"], self.needles()), [], fmt)

    def test_approve_files_the_document_it_checked(self):
        self.fresh()
        out = self.py(self.swap_after_first_read() +
                      f"p = report_doc.stage_client({str(self.draft_file())!r}, force=True, code='ABC', fri={WEEK!r})\n"
                      "prop = json.loads(p.read_text())\np.unlink()\n"
                      "print(json.dumps([o.get('content') or '' for o in prop['report']['file_ops'] if o.get('op') == 'write']))")
        self.assertEqual(len(out), 1, out)
        low = out[0].lower()
        self.assertEqual([n for n in self.needles() if n.lower() in low], [])

    # ── a weekly report is always internal ──────────────────────────────────────────────────────────────────────────────
    def weekly_file(self):
        return self.v.root / "system/staging/drafts" / f"{S.WEEKLY_STEM}.html"

    def test_a_weekly_report_saved_with_a_client_audience_is_refused(self):
        for audience in ("client", "distributed"):
            with self.subTest(audience=audience):
                r = self.post("/api/report/draft", {"kind": "weekly", "code": "ABC", "week_ending": WEEK})
                self.assertTrue(r["ok"], r)
                doc = dict(r["doc"], audience=audience)
                sv = self.post("/api/report/save", {"doc": doc, "base_version": r["version"]})
                self.assertFalse(sv["ok"], sv)
                self.assertRegex(sv["message"], r"(?i)audience")

    def test_a_weekly_draft_edited_on_disk_to_a_client_audience_is_exported_as_internal(self):
        for audience in ("client", "distributed"):
            with self.subTest(audience=audience):
                for f in self.reports.glob("*Weekly report*"):
                    f.unlink()
                self.weekly_file().unlink(missing_ok=True)
                self.weekly()
                f = self.weekly_file()
                text = f.read_text()
                self.assertIn('"audience": "internal"', text)
                f.write_text(text.replace('"audience": "internal"', f'"audience": "{audience}"', 1), encoding="utf-8")
                d = self.post("/api/report/draft", {"kind": "weekly", "code": "ABC", "week_ending": WEEK})
                self.assertEqual(d["doc"]["audience"], "internal")
                for fmt in ("html", "docx"):
                    e = self.export(fmt, "weekly", on_clash="number")
                    self.assertTrue(e["ok"], (fmt, e))
                    p = self.v.root / e["path"]
                    if fmt == "html":
                        page = p.read_text()
                        self.assertIn('<div class="sub">Internal</div>', page)
                        self.assertNotIn('<div class="sub">Client</div>', page)
                        self.assertNotIn('<div class="sub">Distributed</div>', page)
                    else:
                        self.assertEqual(self.scan(p, ["Client · Draft", "Distributed · Draft"]), [])

    # ── the minutes routes never open a report ──────────────────────────────────────────────────────────────────────────
    def as_minutes(self, f):
        text = f.read_text()
        m = creaite_doc.BLOCK.search(text)
        d = self.add_payload(json.loads(m.group(1)))
        d["kind"], d["audience"] = "minutes", "internal"
        f.write_text(text[:m.start(1)] + creaite_doc.data_json(d) + text[m.end(1):], encoding="utf-8")

    def test_a_client_report_edited_to_say_minutes_is_never_exported_by_the_minutes_route(self):
        self.fresh()
        a = self.post("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "force": True})
        self.assertTrue(a["ok"], a)
        filed = self.v.root / a["path"]
        filed_text = filed.read_text()
        self.fresh()                                     # a client draft again
        filed.write_text(filed_text, encoding="utf-8")   # and the filed report back
        for f in (self.draft_file(), filed):
            with self.subTest(file=f.parent.name):
                self.as_minutes(f)
                rel = str(f.relative_to(self.v.root))
                for fmt in ("html", "docx"):
                    e = self.post("/api/minutes/export", {"path": rel, "format": fmt, "file_beside": True})
                    self.assertFalse(e["ok"], (fmt, e))
                d = self.post("/api/minutes/draft", {"path": rel})
                self.assertFalse(d.get("ok"), d)
                others = [x for folder in (self.reports, self.v.root / "system/staging/drafts") for x in folder.glob("*")
                          if x.is_file() and x not in (self.draft_file(), filed) and x.suffix in (".html", ".docx", ".pdf")]
                self.assertEqual({x.name: h for x in others for h in [self.scan(x, self.needles())] if h
                                  and "Weekly report" not in x.name}, {})

    # ── a typed export name never names the other report ────────────────────────────────────────────────────────────────
    def test_a_weekly_export_cannot_be_renamed_to_a_client_reports_name(self):
        self.weekly()
        for new in (S.CLIENT_STEM, S.CLIENT_STEM + ".html", "x client REPORT - y"):
            with self.subTest(new=new):
                before = sorted(x.name for x in self.reports.glob("*"))
                e = self.export("html", "weekly", on_clash="rename", new_name=new)
                self.assertFalse(e["ok"], e)
                self.assertEqual(sorted(x.name for x in self.reports.glob("*")), before)
        e = self.export("html", "weekly", on_clash="rename", new_name="Board pack")      # an ordinary name still works
        self.assertTrue(e["ok"], e)

    # ── each boundary on its own, with a reader that doesn't normalise ──────────────────────────────────────────────────
    def raw_reader(self):
        return ("import re\n_raw = lambda p: json.loads(creaite_doc.BLOCK.search(creaite_doc.real(p).read_text()).group(1))\n"
                "creaite_doc.read = _raw\n")

    def test_read_report_reads_a_client_kind_as_client(self):
        self.fresh()
        self.tamper_on_disk("internal")
        out = self.py(f"print(json.dumps(creaite_doc.read_report({str(self.draft_file())!r}).get('audience')))")
        self.assertEqual(out, "client")
        self.fresh()
        self.tamper_on_disk(MISSING)
        self.assertEqual(self.py(f"print(json.dumps(creaite_doc.read_report({str(self.draft_file())!r}).get('audience')))"), "client")

    def test_stage_client_normalises_on_its_own(self):
        self.fresh()
        self.tamper_on_disk("internal")
        out = self.py(self.raw_reader() + f"assert creaite_doc.read({str(self.draft_file())!r})['audience'] == 'internal'\n"
                      f"try:\n    report_doc.stage_client({str(self.draft_file())!r}, force=True)\n    print(json.dumps('staged'))\n"
                      "except report_doc.ReportError as e:\n    print(json.dumps(str(e)))")
        self.assertIn("possible internal content", out)

    def test_left_out_normalises_on_its_own(self):
        self.fresh()
        self.tamper_on_disk("internal")
        out = self.py(self.raw_reader() + f"d = creaite_doc.read({str(self.draft_file())!r})\nassert d['audience'] == 'internal'\n"
                      "print(json.dumps(client_check.left_out(d)['findings']))")
        self.assertTrue(out)

    # ── the header fields the gate never reads: project_name and client ─────────────────────────────────────────────────
    def header_payload(self):
        hid, title, owner = self.hidden_item()
        return f"{owner} {hid} {title} confidential Internal only: keep"

    def assert_clean_files(self):
        needles = self.needles()
        self.assertEqual(self.reports_hold(needles), {})
        names = " ".join(f.name for f in self.reports.glob("*")).lower()
        self.assertEqual([n for n in needles if n.lower() in names], [])

    def approve_and_export(self):
        a = self.post("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "force": True})
        self.assertTrue(a["ok"], a)
        filed = self.v.root / a["path"]
        self.assertTrue(filed.is_file(), a)
        raw = json.loads(creaite_doc.BLOCK.search(filed.read_text()).group(1))
        self.assertEqual((raw["project_name"], raw["client"]), ("Example Programme", "Example Client Ltd"))
        for fmt in self.formats():
            e = self.export(fmt, "client", on_clash="number")
            self.assertTrue(e["ok"], (fmt, e))
        self.assert_clean_files()

    def test_header_fields_sent_to_save_are_derived_again(self):
        for field in ("project_name", "client"):
            with self.subTest(field=field):
                r = self.fresh()
                doc = dict(r["doc"], **{field: self.header_payload()})
                sv = self.post("/api/report/save", {"doc": doc, "base_version": r["version"]})
                self.assertTrue(sv["ok"], sv)
                self.assertEqual(sv["path"], f"system/staging/drafts/{S.CLIENT_STEM}.html")
                raw = json.loads(creaite_doc.BLOCK.search(self.draft_file().read_text()).group(1))
                self.assertEqual(raw[field], {"project_name": "Example Programme", "client": "Example Client Ltd"}[field])
                self.approve_and_export()

    def test_header_fields_edited_on_disk_are_derived_again(self):
        for field in ("project_name", "client"):
            with self.subTest(field=field):
                self.fresh()
                f = self.draft_file()
                text = f.read_text()
                raw = json.loads(creaite_doc.BLOCK.search(text).group(1))
                old = f'"{field}": {json.dumps(raw[field], ensure_ascii=False)}'
                self.assertIn(old, text)
                f.write_text(text.replace(old, f'"{field}": {json.dumps(self.header_payload())}', 1), encoding="utf-8")
                self.assertIn(self.hidden_item()[0], f.read_text())
                self.approve_and_export()

    def test_header_fields_sent_with_approve_are_derived_again(self):
        for field in ("project_name", "client"):
            with self.subTest(field=field):
                r = self.fresh()
                doc = dict(r["doc"], **{field: self.header_payload()})
                a = self.post("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "force": True,
                                                       "doc": doc, "base_version": r["version"]})
                self.assertTrue(a["ok"], a)
                self.assertEqual(list((self.v.root / "system/staging/drafts").glob("*confidential*")), [])
                filed = json.loads(creaite_doc.BLOCK.search((self.v.root / a["path"]).read_text()).group(1))
                self.assertEqual((filed["project_name"], filed["client"]), ("Example Programme", "Example Client Ltd"))
                self.assert_clean_files()

    def test_header_fields_edited_on_disk_are_derived_again_in_an_export_of_the_draft(self):
        for field in ("project_name", "client"):
            with self.subTest(field=field):
                self.fresh()
                f = self.draft_file()
                text = f.read_text()
                raw = json.loads(creaite_doc.BLOCK.search(text).group(1))
                f.write_text(text.replace(f'"{field}": {json.dumps(raw[field], ensure_ascii=False)}',
                                          f'"{field}": {json.dumps(self.header_payload())}', 1), encoding="utf-8")
                for fmt in self.formats():
                    self.assertTrue(self.export(fmt, "client", on_clash="number")["ok"], fmt)     # no approve: the draft itself
                self.assert_clean_files()

    def test_a_client_named_in_the_request_is_ignored(self):
        self.fresh()
        r = self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": WEEK, "client": self.header_payload()})
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["doc"]["client"], "Example Client Ltd")
        e = self.post("/api/report/export", {"kind": "client", "code": "ABC", "week_ending": WEEK, "fmt": "docx",
                                             "client": self.header_payload()})
        self.assertTrue(e["ok"], e)
        self.assert_clean_files()

    # ── (B) another project's item in a client report ───────────────────────────────────────────────────────────────────
    def other_item(self):
        import sqlite3
        from contextlib import closing
        import test_reports as R
        db = self.v.root / "system/tracker.db"
        q = "SELECT id FROM actions WHERE project = 'DEF' AND description = 'Migrate the zephyr ledger'"
        with closing(sqlite3.connect(db)) as con:
            hit = con.execute(q).fetchone()
        if not hit:
            self.v.propose("def", [{"n": 1, "op": "new", "table": "projects", "match": "strong", "flags": [], "decision": "approved",
                                    "values": {"code": "DEF", "name": "Other Programme"}}])
            self.v.run("apply")
            self.v.propose("other", [R.new("actions", 1, project="DEF", description="Migrate the zephyr ledger", owner="Omar Ali",
                                           raised="2026-10-01", client_visible=1,
                                           client_message=R.CLIENT_MSG.replace("statement of work", "quokka sheet"), source="s")])
            self.v.run("apply")
            with closing(sqlite3.connect(db)) as con:
                hit = con.execute(q).fetchone()
        return hit[0]

    def test_another_projects_item_is_dropped_from_a_client_report(self):
        oid = self.other_item()
        r = self.fresh()
        doc = r["doc"]
        sec = next(x for x in doc["sections"] if x.get("rows"))
        row = dict(sec["rows"][0], ref=oid, shown=True)
        sec["rows"].append(row)
        doc["items"][oid] = {**(doc["items"].get(sec["rows"][0]["ref"]) or {}), "id": oid, "title": "zephyr quokka",
                             "client_message": "quokka sheet"}
        sv = self.post("/api/report/save", {"doc": doc, "base_version": r["version"]})
        self.assertTrue(sv["ok"], sv)
        self.assertNotIn(oid, self.draft_file().read_text())
        # and a draft edited on disk to hold it again
        f = self.draft_file()
        d = json.loads(creaite_doc.BLOCK.search(f.read_text()).group(1))
        next(x for x in d["sections"] if x["id"] == sec["id"])["rows"].append(row)
        d["items"][oid] = {"id": oid, "title": "zephyr quokka", "client_message": "quokka sheet"}
        text = f.read_text()
        m = creaite_doc.BLOCK.search(text)
        f.write_text(text[:m.start(1)] + creaite_doc.data_json(d) + text[m.end(1):], encoding="utf-8")
        self.assertIn(oid, f.read_text())
        a = self.post("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "force": True})
        self.assertTrue(a["ok"], a)
        for fmt in self.formats():
            self.assertTrue(self.export(fmt, "client", on_clash="number")["ok"], fmt)
        self.assertEqual(self.reports_hold([oid, "zephyr", "quokka"]), {})

    # ── (D) the filed client file's data block ──────────────────────────────────────────────────────────────────────────
    def test_the_filed_client_file_holds_only_creaites_own_meta_sources_and_layout(self):
        """Words the gate doesn't flag never reach the filed data block; protected words are refused by the gate (rc-a5's
        client_leak reads meta, sources and layout) and nothing is filed."""
        for p, gated in (("Quokkameta tidings", False), (self.header_payload(), True)):
            with self.subTest(gated=gated):
                r = self.fresh()
                doc = r["doc"]
                doc["meta"] = {**doc["meta"], "note": p, "period_start": p}
                doc["sources"] = [{"ref": "tracker", "label": p}, {"ref": "x", "label": p}]
                doc["layout"] = {**doc["layout"], "zzz": p}
                sv = self.post("/api/report/save", {"doc": doc, "base_version": r["version"]})
                self.assertTrue(sv["ok"], sv)
                a = self.post("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "force": True})
                if gated:
                    self.assertFalse(a["ok"], a)
                    self.assertIn("possible internal content", a["message"])
                    self.assertEqual(list(self.reports.glob("*Client report*")), [])
                    continue
                self.assertTrue(a["ok"], a)
                filed = self.v.root / a["path"]
                raw = json.loads(creaite_doc.BLOCK.search(filed.read_text()).group(1))
                self.assertEqual(set(raw["meta"]) - {"period_start", "period_end", "locked", "facts_on", "facts_week"}, set())
                self.assertEqual([x["ref"] for x in raw["sources"]], ["tracker"])
                self.assertNotIn("zzz", raw["layout"])
                self.assertEqual(self.scan(filed, ["quokkameta"] + self.needles()), [])

    # ── the helpers ─────────────────────────────────────────────────────────────────────────────────────────────────────
    def test_is_client_and_force_client_audience(self):
        self.assertTrue(creaite_doc.is_client({"kind": "client", "audience": "internal"}))
        self.assertTrue(creaite_doc.is_client({"kind": "client"}))
        self.assertTrue(creaite_doc.is_client({"kind": "minutes", "audience": "distributed"}))
        self.assertTrue(creaite_doc.is_client({"kind": "weekly", "audience": "client"}))
        self.assertFalse(creaite_doc.is_client({"kind": "weekly", "audience": "internal"}))
        self.assertFalse(creaite_doc.is_client({"kind": "minutes"}))
        for a in ("internal", "distributed", None, "weekly"):
            self.assertEqual(creaite_doc.force_client_audience({"kind": "client", "audience": a})["audience"], "client")
        self.assertEqual(creaite_doc.force_client_audience({"kind": "client"})["audience"], "client")
        self.assertEqual(creaite_doc.force_client_audience({"kind": "minutes", "audience": "distributed"})["audience"], "distributed")
        self.assertEqual(creaite_doc.force_client_audience({"kind": "weekly", "audience": "client"}),
                         {"kind": "weekly", "audience": "client"})

    # ── control ─────────────────────────────────────────────────────────────────────────────────────────────────────────
    def test_control_a_normal_client_report_saves_approves_and_exports(self):
        r = self.fresh()
        self.assertEqual(r["doc"]["audience"], "client")
        next(s for s in r["doc"]["sections"] if s["id"] == "summary")["text"] = "Phase two starts once the paperwork is signed."
        sv = self.post("/api/report/save", {"doc": r["doc"], "base_version": r["version"]})
        self.assertTrue(sv["ok"], sv)
        for fmt in self.formats():
            e = self.export(fmt, "client", on_clash="number")
            self.assertTrue(e["ok"], (fmt, e))
            self.assertEqual(self.scan(self.v.root / e["path"], ["Phase two starts"]), ["Phase two starts"], fmt)
        a = self.post("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "force": True})
        self.assertTrue(a["ok"], a)
        self.assertEqual(self.reports_hold(self.needles()), {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
