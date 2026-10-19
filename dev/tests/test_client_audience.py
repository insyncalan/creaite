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
        r = self.fresh()
        doc = r["doc"]
        p = self.header_payload()
        doc["meta"] = {**doc["meta"], "note": p, "period_start": p}
        doc["sources"] = [{"ref": "tracker", "label": p}, {"ref": "x", "label": p}]
        doc["layout"] = {**doc["layout"], "zzz": p}
        sv = self.post("/api/report/save", {"doc": doc, "base_version": r["version"]})
        self.assertTrue(sv["ok"], sv)
        a = self.post("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "force": True})
        self.assertTrue(a["ok"], a)
        filed = self.v.root / a["path"]
        raw = json.loads(creaite_doc.BLOCK.search(filed.read_text()).group(1))
        self.assertEqual(set(raw["meta"]) - {"period_start", "period_end", "locked", "facts_on", "facts_week"}, set())
        self.assertEqual([x["ref"] for x in raw["sources"]], ["tracker"])
        self.assertNotIn("zzz", raw["layout"])
        self.assertEqual(self.scan(filed, self.needles()), [])

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
