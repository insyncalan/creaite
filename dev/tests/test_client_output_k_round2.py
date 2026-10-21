"""v2.5.3 (#259 round 2): Team Cap's NOT READY verdict on v253-client-k c25a28fe (20-10-2026, 23:18). The data is fictional.

Run: python3 dev/tests/test_client_output_k_round2.py

Each leak test failed on c25a28fe before its fix (the controls passed); each has a mutant that puts the old behaviour back in a
process of its own and goes red (test_mutant_*):
  - HIGH 1, trust laundering: an approved, filed client report edited on disk to add a text section marked "client" is held on
    EVERY export, html and docx, not only the first. Only the snapshot Approve wrote beside that filed file vouches for it
    (client_snapshot.approved_source); a snapshot an export rebuilt is recorded as made by the export and never vouches
                                                                                                              test_h1_*
  - HIGH 2, the apply re-check: tracker.py apply derives client status and format from the files a report block names and holds
    (review.files_client, creaite_files), never from its `kind`, `version` or `format`; only Approve's own ops may run
    (a .md or .pdf written beside the report is refused); the steerco one-pager's client -> internal switch too  test_h2_*
  - MEDIUM 3: P16's loose forms in the Word client body (review.client_findings) and in AI client drafts
    (edit_ai.client_problems)                                                                                 test_m3_*
  - MEDIUM 4: a section's default_heading is derived (report_doc.SECTIONS); a layout list keeps only a known section id,
    At a glance key, logo kind or milestone ID                                                                test_m4_*
  - LOW 6: P16 edges (many separators, "/", "," and "·" between digits, zero-width spaces for a title's spaces)   test_l6_*
  - LOW 7: an unreadable draft gives a sentence, not an HTTP 500                                              test_l7_*
"""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_client_audience as A  # noqa: E402
import test_client_output_k as KK  # noqa: E402
import test_report_export_save as S  # noqa: E402
import test_reports as R  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
import creaite_doc  # noqa: E402

WEEK = A.WEEK
DRAFT = KK.DRAFT
FILED_NAME = f"{S.CLIENT_STEM}.html"
SECRET = "ZEBRAPAY quiet words"            # words no gate knows: only K2's derived audience keeps them out
# HIGH 1's old trust: any registry entry of a filed state whose source hash matches (c25a28fe's creaite_doc.creaite_wrote)
LAUNDER = ("import creaite_doc, client_snapshot, hashlib\n"
           "_real = creaite_doc.creaite_wrote\n"
           "def _old(path, raw):\n"
           "    d = hashlib.sha256(raw).hexdigest()\n"
           "    return _real(path, raw) or any(e.get('state') == 'filed' and e.get('source_sha256') == d\n"
           "                                   for e in client_snapshot.registry().values())\n"
           "creaite_doc.creaite_wrote = _old\n")
# HIGH 2's old re-check: the block's own kind, version and format taken as given, and only the writes it picks checked
OLD_APPLY = ("import review\n"
             "_real = review.creaite_client_problem\n"
             "def _old(blk, field):\n"
             "    if field != 'report_decision' or blk.get(field) != 'approved' or not review.client_block(blk):\n"
             "        return None\n"
             "    if blk.get('format') == 'creaite':\n"
             "        return None if _real(dict(blk, file_ops=[o for o in blk['file_ops'] if o.get('path', '').endswith(('.html', "
             "'.client.json')) or o.get('op') == 'remove'])) is None else 'refused'\n"
             "    return None\n"
             "review.client_apply_problem = _old\n")


class Round2(KK.K):
    """The routes on a live server in a throwaway vault (test_client_audience's harness)."""

    # ── helpers ──────────────────────────────────────────────────────────────────────────────────────────────────────────
    def filed(self):
        return self.reports / FILED_NAME

    def approved_with_edit(self):
        """An approved, filed client report, then edited on disk (ask creaite's way, or any local process) to hold a text section
        marked "client" with words no gate knows."""
        r = self.fresh()
        self.save(r["doc"], r["version"])
        self.approve()
        f = self.filed()
        text = f.read_text(encoding="utf-8")
        d = creaite_doc.loads(text)
        d["sections"].append({"id": "free_sneak", "type": "freetext", "heading": "Notes", "default_heading": "", "hidden": False,
                              "text": f"{SECRET} for the steering group.", "audience": "client"})
        d["layout"]["order"] = [s["id"] for s in d["sections"]]
        m = creaite_doc.BLOCK.search(text)
        f.write_text(text[:m.start(1)] + creaite_doc.data_json(d) + text[m.end(1):], encoding="utf-8")

    def export_text(self, fmt, patch=""):
        """One client export (through client_export, in a process of its own: `patch` runs first), its text, the file deleted."""
        out = self.py(patch + f"""
import client_snapshot, creaite_doc, zipfile
out = client_snapshot.client_export('ABC', '{WEEK}', {fmt!r})
if out.get('ok'):
    p = creaite_doc.real(out['path'])
    if p.suffix == '.docx':
        with zipfile.ZipFile(p) as z:
            out['text'] = ''.join(z.read(n).decode('utf-8', 'ignore') for n in z.namelist())
    else:
        out['text'] = p.read_text(encoding='utf-8')
    p.unlink()
print(json.dumps(out))
""")
        return out.get("text") or ""

    def exports_hold(self, order, patch=""):
        return [(i, fmt) for i, fmt in enumerate(order) if "zebrapay" in self.export_text(fmt, patch).lower()]

    # ── HIGH 1: trust laundering ─────────────────────────────────────────────────────────────────────────────────────────
    ORDERS = (("html", "html", "docx", "html"), ("docx", "docx", "html"), ("html", "docx", "docx", "html", "html"))

    def test_h1_an_edited_filed_report_is_held_on_every_export(self):
        for order in self.ORDERS:
            with self.subTest(order=order):
                self.approved_with_edit()
                self.assertEqual(self.exports_hold(order), [])

    def test_h1_also_through_the_export_route(self):
        self.approved_with_edit()
        for fmt in ("html", "docx", "html", "docx"):
            e = self.export(fmt, "client", on_clash="number")
            if e.get("ok"):
                p = self.v.root / e["path"]
                self.assertNotIn("zebrapay", self.text_of(p).lower(), fmt)
                p.unlink()

    def test_h1_registry_marks_how_each_entry_was_made(self):
        self.approved_with_edit()
        self.export_text("html")
        made = self.py("import client_snapshot\nprint(json.dumps(sorted({e.get('made') for e in "
                       "client_snapshot.registry().values()})))")
        self.assertEqual(made, ["approve", "export"])
        src = self.py(f"import client_snapshot\nprint(json.dumps(client_snapshot.approved_source({paths_of(self.filed())!r})))")
        self.assertIsNotNone(src)                 # the approved one still vouches for the file Approve filed, not for the edit

    def test_h1_control_a_client_text_section_creaite_filed_still_shows(self):
        r = self.fresh()
        d = r["doc"]
        d["sections"].append({"id": "free_c", "type": "freetext", "heading": "Notes", "default_heading": "", "hidden": False,
                              "text": "Plain client words for the steering group.", "audience": "client"})
        d["layout"]["order"] = [s["id"] for s in d["sections"]]
        self.save(d, r["version"])
        self.approve()
        for fmt in ("html", "docx", "html"):
            self.assertIn("Plain client words for the steering group.", self.export_text(fmt), fmt)

    def test_h1_a_snapshot_beside_another_file_never_vouches(self):
        """The approved snapshot is bound to its own path: copied beside another name, it vouches for nothing there."""
        self.approved_with_edit()
        got = self.py("import client_snapshot\nprint(json.dumps(client_snapshot.approved_source("
                      f"{paths_of(self.reports / 'Other.html')!r})))")
        self.assertIsNone(got)

    def test_mutant_h1_the_old_trust_shows_the_section_on_a_later_export(self):
        self.approved_with_edit()
        self.assertTrue(self.exports_hold(("html", "html", "docx"), LAUNDER))

    # ── HIGH 2: tracker.py apply derives client status and allows only Approve's ops ──────────────────────────────────────
    def staged(self):
        r = self.fresh()
        self.save(r["doc"], r["version"])
        staged = self.py(f"import report_doc\nprint(json.dumps(str(report_doc.stage_client({DRAFT!r}, force=True, code='ABC', "
                         f"fri='{WEEK}'))))")
        p = Path(staged) if Path(staged).is_absolute() else self.v.root / staged
        return p, json.loads(p.read_text(encoding="utf-8"))

    def hidden_text(self):
        hid, title, _owner = self.hidden_item()
        return f"{hid}: {title}"

    def tamper(self, data, how):
        blk = data["report"]
        ops = blk["file_ops"]
        w = next(op for op in ops if op["op"] == "write" and op["path"].endswith(".html"))
        leak = f"<p>{self.hidden_text()}</p></main>"
        if how in ("kind_weekly", "format_gone", "both", "both_no_snapshot", "kind_internal"):
            w["content"] = w["content"].replace("</main>", leak, 1)
        if how == "kind_weekly":
            blk["kind"] = "weekly"
        elif how == "kind_internal":
            blk["kind"] = "steerco"
            blk["version"] = "internal"
        elif how == "format_gone":
            blk.pop("format")
        elif how in ("both", "both_no_snapshot"):
            blk["kind"] = "weekly"
            blk.pop("format")
            if how == "both_no_snapshot":
                blk["file_ops"] = [o for o in ops if not o.get("path", "").endswith(".client.json")]
        elif how in ("extra_md", "extra_pdf", "extra_md_weekly"):
            ext = ".pdf" if how == "extra_pdf" else ".md"
            ops.insert(1, {"op": "write", "path": w["path"][:-5] + ext, "content": f"Notes: {self.hidden_text()}\n",
                           "previous": None})
            if how == "extra_md_weekly":
                blk["kind"] = "weekly"
                blk.pop("format")
        elif how == "extra_copy":
            ops.insert(1, {"op": "copy", "from": "draft", "to": w["path"][:-5] + " copy.html"})
        elif how == "moved":
            w["path"] = w["path"].replace("Client report", "Weekly report")
        return data

    HOWS = ("kind_weekly", "format_gone", "both", "both_no_snapshot", "kind_internal", "extra_md", "extra_pdf", "extra_md_weekly",
            "extra_copy", "moved")

    def leaked_files(self):
        hid = self.hidden_item()[0]
        out = []
        for f in self.v.root.joinpath("projects").rglob("*"):
            if f.is_file() and f.suffix in (".html", ".md", ".pdf") and "Client report" in f.name and hid in f.read_text("utf-8", "ignore"):
                out.append(f.name)
        return out

    def test_h2_a_staged_client_proposal_edited_after_approve_is_refused(self):
        for how in self.HOWS:
            with self.subTest(how=how):
                p, data = self.staged()
                p.write_text(json.dumps(self.tamper(data, how), ensure_ascii=False, indent=1), encoding="utf-8")
                r = self.apply(p)
                self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertEqual(self.leaked_files(), [], r.stdout)
                self.assertEqual([f.name for f in self.reports.glob("*Client report*") if f.suffix in (".md", ".pdf")], [])
                self.assertFalse(self.filed().exists(), r.stdout)
                p.unlink(missing_ok=True)

    def test_h2_control_the_untouched_proposal_is_filed(self):
        p, _data = self.staged()
        r = self.apply(p)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(self.filed().exists())

    def test_mutant_h2_the_old_recheck_files_an_edited_proposal(self):
        """The old re-check (kind and format as given; only the writes it picks) files kind: weekly with a hidden ID in it."""
        hits = []
        for how in ("kind_weekly", "format_gone", "extra_md"):
            p, data = self.staged()
            p.write_text(json.dumps(self.tamper(data, how), ensure_ascii=False, indent=1), encoding="utf-8")
            r = self.apply_patched(p, OLD_APPLY)
            if r.returncode == 0:
                hits.append(how)
            subprocess.run([sys.executable, "system/scripts/tracker.py", "undo"], cwd=self.v.root, capture_output=True,
                           env={**os.environ, "CREAITE_NOW": S.NOW})
            p.unlink(missing_ok=True)
        self.assertEqual(hits, ["kind_weekly", "format_gone", "extra_md"])

    def apply_patched(self, p, patch):
        code = (f"import sys, runpy\nsys.path.insert(0, 'system/scripts')\n{patch}"
                f"sys.argv = ['system/scripts/tracker.py', 'apply', {p.name!r}]\nrunpy.run_path(sys.argv[0], run_name='__main__')")
        return subprocess.run([sys.executable, "-c", code], cwd=self.v.root, capture_output=True, text=True,
                              env={**os.environ, "CREAITE_NOW": S.NOW})

    # the client-safe steerco one-pager switched to internal on the Word path
    def steerco_staged(self):
        for f in list((self.v.root / "system/staging").glob("proposed-*.json")) + \
                list((self.v.root / "system/staging/drafts").glob("*Steerco*.docx")):
            f.unlink()
        spec = {"code": "ABC", "version": "client", "steerco_date": WEEK, "summary": ["Phase two is being prepared."], "force": True}
        rc = self.py("import report, io, contextlib\nbuf = io.StringIO()\nwith contextlib.redirect_stdout(buf):\n"
                     f"    rc = report.steerco_stage({spec!r})\nprint(json.dumps(rc))")
        self.assertEqual(rc, 0)
        p = next((self.v.root / "system/staging").glob("proposed-*steerco*.json"))
        return p, json.loads(p.read_text(encoding="utf-8"))

    def steerco_files(self):
        return [f for f in self.v.root.joinpath("projects").rglob("*Steerco one-pager*.docx")]

    def steerco_switch(self, how):
        p, data = self.steerco_staged()
        blk = data["report"]
        R.edit_docx(self.v.root / blk["draft"], "Phase two is being prepared.",
                    f"Phase two is being prepared. {self.hidden_item()[1]}.")
        blk["report_decision"] = "approved"
        if how in ("internal", "renamed"):
            blk["version"] = "internal"
        if how == "renamed":
            cp = next(o for o in blk["file_ops"] if o["op"] == "copy")
            cp["to"] = cp["to"].replace(" (client)", "")
        if how == "kind_gone":
            blk.pop("kind")
            blk.pop("version")
        p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        return p

    def test_h2_the_steerco_client_to_internal_switch_is_refused(self):
        for how in ("internal", "renamed", "kind_gone"):
            with self.subTest(how=how):
                for f in self.steerco_files():
                    f.unlink()
                p = self.steerco_switch(how)
                r = self.apply(p)
                self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertEqual(self.steerco_files(), [], r.stdout)

    def test_h2_control_an_internal_one_pager_is_filed(self):
        for f in self.steerco_files():
            f.unlink()
        for f in list((self.v.root / "system/staging").glob("proposed-*.json")):
            f.unlink()
        spec = {"code": "ABC", "version": "internal", "steerco_date": WEEK, "summary": ["Phase two is being prepared."], "force": True}
        self.assertEqual(self.py("import report, io, contextlib\nbuf = io.StringIO()\nwith contextlib.redirect_stdout(buf):\n"
                                 f"    rc = report.steerco_stage({spec!r})\nprint(json.dumps(rc))"), 0)
        p = next((self.v.root / "system/staging").glob("proposed-*steerco*.json"))
        data = json.loads(p.read_text(encoding="utf-8"))
        data["report"]["report_decision"] = "approved"
        p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        r = self.apply(p)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(len(self.steerco_files()), 1)
        for f in self.steerco_files():
            f.unlink()

    def test_mutant_h2_the_old_recheck_files_the_switched_one_pager(self):
        for f in self.steerco_files():
            f.unlink()
        p = self.steerco_switch("internal")
        r = self.apply_patched(p, OLD_APPLY)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(len(self.steerco_files()), 1)
        for f in self.steerco_files():
            f.unlink()

    # ── MEDIUM 3: P16 in the Word client body and in AI client drafts ─────────────────────────────────────────────────────
    def loose_forms(self):
        a = self.hidden_action()["id"]
        code, letter, num = a.split("-")
        t = self.hidden_raid()["description"]
        return [" ".join(code) + f" - {letter} - " + " ".join(num), f"{code}-{letter}-0{num}", t.replace(" ", "-")]

    def word_findings(self, words, patch=""):
        p, data = self.steerco_staged()
        blk = data["report"]
        R.edit_docx(self.v.root / blk["draft"], "Phase two is being prepared.", f"Phase two is being prepared. {words}.")
        return self.py(patch + f"import review\nprint(json.dumps(review.client_findings({blk!r})))")

    def test_m3_the_steerco_word_body_reads_the_loose_forms(self):
        for words in self.loose_forms():
            with self.subTest(words=words):
                self.assertTrue(self.word_findings(words), words)

    def test_m3_control_a_clean_word_body_has_no_finding(self):
        self.assertEqual(self.word_findings("The pilot went well"), [])

    def test_mutant_m3_without_the_loose_check_the_word_body_passes(self):
        off = "import client_output\nclient_output.loose_findings = lambda *a, **k: []\n"
        self.assertEqual([w for w in self.loose_forms() if self.word_findings(w, off)], [])

    def ai_problems(self, words, patch=""):
        return self.py(patch + f"import edit_ai\nprint(json.dumps(edit_ai.client_problems('ABC', {('Status: ' + words)!r})))")

    def test_m3_ai_client_drafts_read_the_loose_forms(self):
        for words in self.loose_forms():
            with self.subTest(words=words):
                self.assertTrue(self.ai_problems(words), words)

    def test_m3_control_a_clean_ai_draft_has_no_problem(self):
        self.assertEqual(self.ai_problems("the pilot went well"), [])

    def test_mutant_m3_without_the_loose_check_ai_drafts_pass(self):
        off = "import client_output\nclient_output.loose_findings = lambda *a, **k: []\n"
        self.assertEqual([w for w in self.loose_forms() if self.ai_problems(w, off)], [])

    # ── MEDIUM 4: default_heading and the layout's lists ──────────────────────────────────────────────────────────────────
    def plant_m4(self, d):
        for s in d["sections"]:
            s["default_heading"] = f"SECRETFIELD {s['id']}"
        lay = d.setdefault("layout", {})
        lay["hidden"] = list(lay.get("hidden") or []) + ["SECRETFIELD hidden"]
        lay["glance"] = list(lay.get("glance") or []) + ["SECRETFIELD glance"]
        lay["logos"] = list(lay.get("logos") or []) + ["SECRETFIELD logo", "partner:secretfield-zebrapay"]
        lay["milestones"] = ["SECRETFIELD milestone"]
        lay["order"] = list(lay.get("order") or []) + ["SECRETFIELD order"]

    def test_m4_stored_headings_and_layout_words_never_reach_a_client_file(self):
        for way in ("save", "disk"):
            with self.subTest(way=way):
                r = self.fresh()
                if way == "save":
                    self.plant_m4(r["doc"])
                    self.post("/api/report/save", {"doc": r["doc"], "base_version": r["version"]})
                else:
                    self.on_disk(self.plant_m4)
                outs = self.outputs()
                self.assertIn("filed", outs)
                self.assertEqual(self.holding(outs, ["SECRETFIELD", "secretfield-zebrapay"]), {})
                b = self.block(outs["filed"])
                own = {sid: h for sid, _t, h in __import__("report_doc").SECTIONS["client"]}
                for s in b["sections"]:
                    if "default_heading" in s:
                        self.assertEqual(s["default_heading"], own.get(s["id"], ""), s["id"])

    def test_m4_control_known_layout_values_are_kept(self):
        shaped = self.py("import creaite_doc\n"
                         "d = {'kind': 'client', 'project': 'ABC', 'sections': [{'id': 'summary', 'type': 'text', 'default_heading': 'x'},"
                         " {'id': 'free_a', 'type': 'freetext', 'default_heading': 'y'}], 'layout': {'hidden': ['risks', 'free_a'], "
                         "'glance': ['watch'], 'logos': ['firm', 'client', 'partner'], 'milestones': ['ABC-M-001'], "
                         "'order': ['summary', 'free_a']}}\n"
                         "print(json.dumps(creaite_doc.client_shape(d)))")
        self.assertEqual(shaped["layout"]["hidden"], ["risks", "free_a"])
        self.assertEqual(shaped["layout"]["glance"], ["watch"])
        self.assertEqual(shaped["layout"]["logos"], ["firm", "client", "partner"])
        self.assertEqual(shaped["layout"]["milestones"], ["ABC-M-001"])
        self.assertEqual([s["default_heading"] for s in shaped["sections"]], ["Summary", ""])

    def test_mutant_m4_the_old_shape_keeps_the_words(self):
        old = ("import creaite_doc\ncreaite_doc._layout_known = lambda doc: {k: (lambda x: True) for k in creaite_doc.LAYOUT_LISTS}\n"
               "_s = creaite_doc._shape_section\n"
               "def _keep(s):\n    out = _s(s)\n    if out is not None and 'default_heading' in s:\n"
               "        out['default_heading'] = s['default_heading']\n    return out\n"
               "creaite_doc._shape_section = _keep\n")
        got = self.py(old + "d = {'kind': 'client', 'project': 'ABC', 'sections': [{'id': 'summary', 'type': 'text', "
                      "'default_heading': 'SECRETFIELD'}], 'layout': {'hidden': ['SECRETFIELD']}}\n"
                      "print(json.dumps(creaite_doc.client_shape(d)))")
        self.assertIn("SECRETFIELD", json.dumps(got))

    # ── LOW 6: P16 edges ──────────────────────────────────────────────────────────────────────────────────────────────────
    def test_l6_more_separators_slashes_commas_and_zero_width_spaces(self):
        a = self.hidden_action()["id"]
        code, letter, num = a.split("-")
        t = self.hidden_raid()["description"]
        forms = ["  -  ".join(code) + f" -- -- {letter} -- " + " ".join(num), f"{code}-{letter}-" + "/".join(num),
                 f"{code}-{letter}-" + ",".join(num), f"{code}-{letter}-" + "·".join(num), t.replace(" ", "\u200b")]
        for f in forms:
            with self.subTest(form=f):
                self.assertTrue(self.findings_of(f"See {f} for the detail."), f)

    def test_l6_a_padded_id_with_a_fraction_or_date_mark_after_it_is_still_found(self):
        # Cap's HIGH on round 3: the fraction/date exemption must not cover a leading zero or a long first run
        code, letter, num = self.hidden_action()["id"].split("-")
        n = int(num)
        forms = [f"{code}-{letter}-0{num}/1", " ".join(code) + f" - {letter} - {num}.5", f"{code}-{letter}-{num}-5",
                 f"{code}-{letter}-{num}/2026", f"{code} {letter} " + " ".join(num) + ".5", f"{code}-{letter}-0{n}/1",
                 f"{code}-{letter}-{num}:10", f"{code}-{letter}-00{num}.1"]
        for f in forms:
            with self.subTest(form=f):
                self.assertTrue(self.findings_of(f"See {f} for the detail."), f)

    def test_l6_control_a_short_fraction_date_or_time_after_the_code_is_no_id(self):
        for f in ("ABC A 4/10", "ABC A 4/10/2026", "ABC A 4.10", "ABC A 12.5", "ABC A 4:10"):
            with self.subTest(form=f):
                self.assertEqual(self.findings_of(f"Plain words: {f} is the day."), [], f)

    def test_l6_control_a_date_or_a_list_of_numbers_is_no_id(self):
        for f in ("ABC 2026/10/20", "ABC 500, 600 and 700 users", "A B C 1 2 3 4"):
            with self.subTest(form=f):
                self.assertEqual(self.findings_of(f"Plain words: {f}."), [], f)

    # ── LOW 7: an unreadable draft gives a sentence ───────────────────────────────────────────────────────────────────────
    def test_l7_an_unreadable_draft_is_a_sentence_not_a_fault(self):
        r = self.fresh()
        self.save(r["doc"], r["version"])
        f = self.draft_file()
        os.chmod(f, 0)
        try:
            if os.access(f, os.R_OK):
                self.skipTest("this user can read a file with no permissions (root)")
            for route, body in (("/api/report/export", {"kind": "client", "code": "ABC", "week_ending": WEEK, "fmt": "html",
                                                        "on_clash": "number"}),
                                ("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "force": True}),
                                ("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": WEEK})):
                with self.subTest(route=route):
                    got = self.post(route, body)
                    self.assertFalse(got.get("ok"), got)
                    self.assertIsInstance(got.get("message"), str)
                    self.assertTrue(got["message"].strip(), got)
        finally:
            os.chmod(f, 0o644)
        self.assertEqual(list(self.reports.glob("*Client report*")), [])


def paths_of(p):
    """A path in the throwaway vault as stored (relative to its root)."""
    parts = Path(p).parts
    i = parts.index("projects")
    return "/".join(parts[i:])


for _name in [n for n in dir(KK.K) if n.startswith("test_")]:
    setattr(Round2, _name, None)                              # only this file's tests run here


if __name__ == "__main__":
    unittest.main(verbosity=2)
