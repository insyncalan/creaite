"""v2.5.3 (#259): the client-output leaks still open after 2.5.2 (Team Cap's verdict on #239, 20-10-2026). The data is fictional.

Run: python3 dev/tests/test_client_output_k.py

Each leak test failed on v253-release (251adff4) before its fix, except possibly test_k2_any_other_section_added_on_disk_is_never_shown
(it was first run with part of the K2 change already in place; kept as a guard); the controls passed, and so did the snapshot test, which is
new coverage of behaviour that was already right (its mutant, rendering from the file, puts the late words in the export):
  - K2 / I20: a section's stored audience "client" was trusted. A client report's section is now the client's own only when it is
    one of creaite's own client sections, or a section creaite itself saved in that file as the client's (the file's SHA-256 is the
    one filechange.py recorded for creaite's last save, or a filed report's is the one its snapshot recorded). A section written
    or flipped to "client" in a file edited outside creaite is read as the internal report's                 test_k2_*
  - K3 / I19 and P7: plain words in stored, unrendered fields (items{} values, a row's source and extra cells, tags[].text,
    layout.headings, based_on.path) and unknown inner keys never reach a client file: items, tags and based_on are derived from
    the tracker, cells and inner keys are allow-listed                                                       test_k3_*
  - P16: an item ID written "A B C - 0 0 5", "ABC-5" or "ABC-0005", and a hidden title written with hyphens or dots for its spaces
    (or spaces for its hyphens), are found by the output check (client_output.loose_findings)                test_p16_*
  - K5: logo_check.clean_svg keeps no text at all (every <text> and <tspan> is left out: the safer choice)   test_k5_*
  - the missing snapshot test: an export renders the snapshot, never the report file read again, and its mutation goes red
                                                                                                              test_snapshot_*
  - tracker.py apply re-checks a creaite-format client report's staged write: tracker.py already asks
    review.client_apply_problem of every approved report block, so no change to the guarded tracker.py is needed
    (review.creaite_client_problem: the write checked as a filed report is, and the snapshot beside it the one recorded at
    approval, naming that write's SHA-256)                                                                    test_apply_*
  - the gate itself (client_leak.findings) reads the P16 forms only with the guarded diff
    dev/proposals/client-output-k/client_leak.diff: an expected failure until it is applied                   test_p16_gate_*
"""
import json
import os
import sqlite3
import subprocess
import sys
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_client_audience as A  # noqa: E402
import test_report_export_save as S  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
import creaite_doc  # noqa: E402

WEEK = A.WEEK
DRAFT = f"system/staging/drafts/{S.CLIENT_STEM}.html"
PLAIN = ["SECRETFIELD", "ZEBRAPAY"]          # words no gate knows: only derivation and the allow-list keep them out
GATE_DIFF_IN = "loose_findings" in (Path(__file__).resolve().parents[2] / "system/scripts/client_leak.py").read_text(encoding="utf-8")
ITEM_KEYS = {"table", "id", "title", "owner", "due_date", "status", "closed", "client_owned", "type", "date", "needed_by", "made_by",
             "state", "shown_date"}


class K(A.Audience):
    """The routes on a live server in a throwaway vault (test_client_audience's harness, without its tests)."""

    # ── helpers ──────────────────────────────────────────────────────────────────────────────────────────────────────────
    def db(self):
        con = sqlite3.connect(self.v.root / "system/tracker.db")
        con.row_factory = sqlite3.Row
        return con

    def hidden_raid(self):
        with closing(self.db()) as con:
            return dict(con.execute("SELECT id, description FROM raid WHERE project='ABC' AND client_visible=0 "
                                    "AND description LIKE '%-%' LIMIT 1").fetchone())

    def hidden_action(self):
        with closing(self.db()) as con:
            return dict(con.execute("SELECT id, description FROM actions WHERE project='ABC' AND client_visible=0 LIMIT 1").fetchone())

    def save(self, doc, version):
        s = self.post("/api/report/save", {"doc": doc, "base_version": version})
        self.assertTrue(s["ok"], s)
        return s

    def approve(self):
        a = self.post("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "force": True})
        self.assertTrue(a["ok"], a)
        return a

    def on_disk(self, edit):
        """The saved draft file edited outside creaite (ask creaite's way, or any local process): `edit(doc)` on its data."""
        f = self.draft_file()
        text = f.read_text(encoding="utf-8")
        d = creaite_doc.loads(text)
        edit(d)
        d["layout"]["order"] = [s["id"] for s in d["sections"]]
        m = creaite_doc.BLOCK.search(text)                      # the data block replaced as is: nothing in this process cleans it
        f.write_text(text[:m.start(1)] + creaite_doc.data_json(d) + text[m.end(1):], encoding="utf-8")

    def outputs(self):
        """{name: text} of every client output made now: the html and docx exports, and the filed report after Approve."""
        out = {}
        for fmt in ("html", "docx"):
            e = self.export(fmt, "client", on_clash="number")
            if e.get("ok"):
                p = self.v.root / e["path"]
                out[fmt] = self.text_of(p)
        a = self.post("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "force": True})
        if a.get("ok"):
            filed = next(self.reports.glob(f"{S.CLIENT_STEM}.html"), None)
            out["filed"] = filed.read_text(encoding="utf-8") if filed else ""
        return out

    def text_of(self, p):
        import zipfile
        if p.suffix == ".docx":
            with zipfile.ZipFile(p) as z:
                return "".join(z.read(n).decode("utf-8", "ignore") for n in z.namelist())
        return p.read_text(encoding="utf-8", errors="ignore")

    def holding(self, outs, needles):
        return {k: [n for n in needles if n.lower() in v.lower()] for k, v in outs.items() if any(n.lower() in v.lower() for n in needles)}

    @staticmethod
    def block(content):
        return json.loads(creaite_doc.BLOCK.search(content).group(1))

    # ── K2 / I20: a section's audience is derived ─────────────────────────────────────────────────────────────────────────
    def test_k2_control_a_client_text_section_saved_by_creaite_shows(self):
        r = self.fresh()
        d = r["doc"]
        d["sections"].append({"id": "free_c", "type": "freetext", "heading": "Notes", "default_heading": "", "hidden": False,
                              "text": "Plain client words for the steering group.", "audience": "client"})
        d["layout"]["order"] = [s["id"] for s in d["sections"]]
        self.save(d, r["version"])
        outs = self.outputs()
        self.assertEqual(sorted(outs), ["docx", "filed", "html"], outs.keys())
        for k, v in outs.items():
            self.assertIn("Plain client words for the steering group.", v, k)

    def test_k2_a_section_flipped_to_client_on_disk_is_never_shown(self):
        """Cap's ms1-fields `secaud=client+intonly`: an internal-only text section in the client draft, its audience flipped to
        client in the file."""
        for flip in ("client", "missing", "internalflag"):
            with self.subTest(flip=flip):
                self.fresh()

                def edit(d, flip=flip):
                    s = {"id": "free_int", "type": "freetext", "heading": "Vendor notes", "default_heading": "", "hidden": False,
                         "text": "INTERNAL walrus words.", "audience": "client"}
                    if flip == "missing":
                        s.pop("audience")
                    if flip == "internalflag":
                        s["internal"] = True
                    d["sections"].append(s)
                self.on_disk(edit)
                self.assertEqual(self.holding(self.outputs(), ["walrus"]), {})

    def test_k2_any_other_section_added_on_disk_is_never_shown(self):
        """A section of creaite's own type but not one of its client sections (a table or panes section with its own id), added in
        the file, is not the client's either."""
        for typ in ("text", "panes", "table", "weird"):
            with self.subTest(type=typ):
                self.fresh()

                def edit(d, typ=typ):
                    d["sections"].append({"id": f"extra_{typ}", "type": typ, "heading": "Walrus heading", "default_heading": "",
                                          "hidden": False, "text": "INTERNAL walrus words.", "audience": "client",
                                          "panes": [{"title": "walrus", "text": "walrus pane"}]})
                self.on_disk(edit)
                self.assertEqual(self.holding(self.outputs(), ["walrus"]), {})

    def test_k2_the_draft_route_reads_a_flipped_section_as_internal(self):
        self.fresh()
        self.on_disk(lambda d: d["sections"].append({"id": "free_int", "type": "freetext", "heading": "Vendor notes",
                                                     "default_heading": "", "hidden": False, "text": "INTERNAL walrus words.",
                                                     "audience": "client"}))
        r = self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": WEEK})
        self.assertTrue(r["ok"], r)
        s = next((x for x in r["doc"]["sections"] if x["id"] == "free_int"), None)
        self.assertTrue(s is None or s.get("audience") != "client", s)

    # ── K3 / I19 and P7: stored, unrendered fields are derived or allow-listed ────────────────────────────────────────────
    def plant(self, d):
        """Plain words and unknown inner keys in every stored field Cap listed."""
        vis = next(r for s in d["sections"] for r in s.get("rows") or [] if r.get("shown", True) and r.get("ref"))
        tab = next(s for s in d["sections"] if vis in (s.get("rows") or []))
        d.setdefault("items", {}).setdefault(vis["ref"], {"id": vis["ref"]})
        d["items"][vis["ref"]].update(title="SECRETFIELD title", owner="SECRETFIELD owner", note7="ZEBRAPAY note")
        vis.update(source="SECRETFIELD source", extra9="ZEBRAPAY row key")
        vis.setdefault("cells", {})["zz_extra"] = "SECRETFIELD cell"
        tab.setdefault("columns", []).append({"key": "zz_col", "label": "ZEBRAPAY", "hint": "SECRETFIELD"})
        tw = next(s for s in d["sections"] if s["id"] == "this_week")
        tw["tags"] = [{"ref": vis["ref"], "text": "SECRETFIELD tag", "note": "ZEBRAPAY tag key"}]
        d.setdefault("layout", {}).setdefault("headings", {})["summary"] = "SECRETFIELD heading"
        d["layout"]["headings"]["zz"] = "ZEBRAPAY heading"
        d["layout"]["rows"] = {"risks": {"top": 5, "note": "SECRETFIELD rows"}}
        d["based_on"] = {"path": "SECRETFIELD/based.html", "version": 1, "note": "ZEBRAPAY based"}
        return vis["ref"]

    def assert_shape(self, content):
        b = self.block(content)
        for ref, it in (b.get("items") or {}).items():
            self.assertLessEqual(set(it), ITEM_KEYS, ref)
        for s in b["sections"]:
            cols = {c["key"] for c in s.get("columns") or []}
            for c in s.get("columns") or []:
                self.assertLessEqual(set(c), {"key", "label"})
            for r in s.get("rows") or []:
                self.assertLessEqual(set(r), {"ref", "cells", "shown", "source"})
                self.assertLessEqual(set(r.get("cells") or {}), cols, s["id"])
            for t in s.get("tags") or []:
                self.assertLessEqual(set(t), {"ref", "text"})
        self.assertLessEqual(set(b.get("based_on") or {}), {"path", "version"})

    def test_k3_plain_words_sent_to_save_never_reach_a_client_file(self):
        r = self.fresh()
        self.plant(r["doc"])
        self.save(r["doc"], r["version"])
        outs = self.outputs()
        self.assertIn("filed", outs)
        self.assertEqual(self.holding(outs, PLAIN), {})
        self.assert_shape(outs["filed"])

    def test_k3_plain_words_edited_on_disk_never_reach_a_client_file(self):
        self.fresh()
        self.on_disk(self.plant)
        outs = self.outputs()
        self.assertIn("filed", outs)
        self.assertEqual(self.holding(outs, PLAIN), {})
        self.assert_shape(outs["filed"])

    def test_k3_a_kept_item_holds_the_trackers_client_safe_facts(self):
        r = self.fresh()
        ref = self.plant(r["doc"])
        self.save(r["doc"], r["version"])
        self.approve()
        filed = next(self.reports.glob(f"{S.CLIENT_STEM}.html")).read_text(encoding="utf-8")
        got = self.block(filed)["items"].get(ref)
        want = self.py(f"""
import report_doc
facts = report_doc.client_facts_for('ABC', '{WEEK}')
print(json.dumps(next((x for t in ('actions', 'decisions', 'raid', 'milestones') for x in facts.get(t) or [] if x['id'] == {ref!r}), None)))
""")
        self.assertIsNotNone(want)
        self.assertEqual(got, want)

    def test_k3_the_facts_are_read_once_per_call_chain(self):
        """v2.6 review: a client report's facts (its approved week and its client-safe items) are read once for one call chain
        (a snapshot's shaping: force_client_audience, then clean), not once per derive, and the result is the same."""
        r = self.fresh()
        got = self.py(f"""
import copy, creaite_doc, report_doc, client_snapshot
doc = json.loads({json.dumps(json.dumps(r['doc']))})
calls = [0]
real = report_doc.baseline
def counted(*a, **k):
    calls[0] += 1
    return real(*a, **k)
report_doc.baseline = counted
shaped = client_snapshot.shaped(copy.deepcopy(doc))
once = calls[0]
again = client_snapshot.shaped(copy.deepcopy(doc))
print(json.dumps([once, calls[0] - once, shaped == again, sorted(shaped.get('items') or {{}}) == sorted(again.get('items') or {{}})]))
""")
        self.assertEqual(got, [1, 1, True, True])

    # ── P16: item IDs and titles however written ──────────────────────────────────────────────────────────────────────────
    def findings_of(self, text):
        return self.py(f"import client_output\nprint(json.dumps(client_output.text_findings({{'project': 'ABC', 'sections': []}}, "
                       f"{text!r})))")

    def test_p16_spaced_short_and_long_item_ids_are_found(self):
        a, r = self.hidden_action()["id"], self.hidden_raid()["id"]
        code, letter, num = a.split("-")
        forms = [" ".join(code) + f" - {letter} - " + " ".join(num), f"{code}-{letter}-0{num}", f"{code.lower()} {letter} 0{num}",
                 f"{code}-{letter}-{int(num)}"]
        rc, rn = r.split("-")
        forms += [f"{rc}-{int(rn)}", f"{rc}-0{rn}", " ".join(rc) + " - " + " ".join(rn), f"{rc.lower()} {int(rn)}"]
        for f in forms:
            with self.subTest(form=f):
                self.assertTrue(self.findings_of(f"See {f} for the detail."), f)

    def test_p16_a_title_with_hyphens_or_dots_for_its_spaces_is_found(self):
        t = self.hidden_raid()["description"]                     # "Vendor exits the market before go-live"
        forms = [t.replace(" ", "-"), t.replace(" ", "."), t.replace("-", " "), t.replace(" ", "_"), t.replace(" ", ". ")]
        for f in forms:
            with self.subTest(form=f):
                self.assertTrue(self.findings_of(f"Note: {f}."), f)

    def test_p16_control_no_finding_for_a_number_or_a_visible_item(self):
        with closing(self.db()) as con:
            vis = con.execute("SELECT id FROM actions WHERE project='ABC' AND client_visible=1 LIMIT 1").fetchone()[0]
        code, letter, num = vis.split("-")
        for f in ("ABC 500 users", "ABC-999", "A B C 1 2 3 4", " ".join(code) + f" - {letter} - " + " ".join(num),
                  "the market before go live", "Vendor exits"):
            with self.subTest(form=f):
                self.assertEqual(self.findings_of(f"Plain words: {f}."), [], f)

    @(lambda f: f) if GATE_DIFF_IN else unittest.expectedFailure
    def test_p16_gate_reads_the_loose_forms_once_the_guarded_diff_is_in(self):
        """The gate (client_leak.text_findings, which client_leak.findings and Save's check read) finds the P16 forms too, with
        dev/proposals/client-output-k/client_leak.diff applied (verified in a scratch copy); until then the output check above
        keeps them out of every client file."""
        a = self.hidden_action()["id"]
        code, letter, num = a.split("-")
        t = self.hidden_raid()["description"]
        for words in (" ".join(code) + f" - {letter} - " + " ".join(num), f"{code}-{letter}-0{num}", t.replace(" ", "-")):
            with self.subTest(words=words):
                got = self.py(f"import client_leak\nprint(json.dumps(client_leak.text_findings(client_leak.connect(), 'ABC', "
                              f"{('Status: ' + words)!r})))")
                self.assertTrue(got, words)

    def test_p16_an_export_holding_such_a_form_is_refused(self):
        a = self.hidden_action()["id"]
        code, letter, num = a.split("-")
        t = self.hidden_raid()["description"]
        for words in (" ".join(code) + f" - {letter} - " + " ".join(num), t.replace(" ", "-")):
            with self.subTest(words=words):
                r = self.fresh()
                next(s for s in r["doc"]["sections"] if s["id"] == "summary")["text"] = f"Status: {words}."
                self.save(r["doc"], r["version"])
                for fmt in ("html", "docx"):
                    e = self.export(fmt, "client", on_clash="number")
                    self.assertFalse(e.get("ok"), (fmt, e))
                a2 = self.post("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "force": True})
                self.assertFalse(a2.get("ok"), a2)
                self.assertEqual(list(self.reports.glob("*Client report*")), [])

    # ── K5: an SVG logo keeps no text ─────────────────────────────────────────────────────────────────────────────────────
    def test_k5_clean_svg_keeps_no_text_drawn_or_hidden(self):
        import logo_check
        svgs = [
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 40"><rect width="100" height="40" fill="#123"/>'
            '<text x="5" y="20" fill="#fff">SECRETWORD</text></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 40"><text x="5" y="20" fill="#000" font-size="0.001">SECRETWORD</text>'
            '<path d="M0 0h10v10z"/></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 40"><g opacity="0.0001"><text x="5" y="20">SECRETWORD</text></g>'
            '<path d="M0 0h10v10z"/></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 40"><text x="5" y="20" fill="#010101">A<tspan>SECRETWORD</tspan>'
            'SECRETWORD</text><path d="M0 0h10v10z"/></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 40"><text x="99" y="39" fill="#fefefe" textLength="0.5">'
            'SECRETWORD</text><path d="M0 0h10v10z"/></svg>',
        ]
        for i, s in enumerate(svgs):
            with self.subTest(case=i):
                out = logo_check.clean_svg(s.encode())
                if out is not None:
                    self.assertNotIn(b"SECRETWORD", out)
                    self.assertNotRegex(out.decode(), r"<(text|tspan)\b")

    def test_k5_control_a_logo_of_shapes_draws_the_same(self):
        import logo_check
        s = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 40"><rect width="100" height="40" fill="#123"/></svg>'
        out = logo_check.clean_svg(s)
        self.assertIsNotNone(out)
        self.assertIn(b"<rect", out)

    # ── the missing snapshot test: the export renders the snapshot, never the file ───────────────────────────────────────
    FROM_FILE = ("import client_snapshot, creaite_doc\n"
                 "client_snapshot.render_doc = lambda snap: creaite_doc.read_report(" + repr(DRAFT) + ", 'client')\n")

    def export_racing(self, patch=""):
        """client_export with the draft changed on disk after its snapshot was built and checked (`settle` runs then), as a local
        process could: the output must be the snapshot's."""
        code = patch + f"""
import client_snapshot, creaite_doc
def settle():
    d = creaite_doc.read({DRAFT!r})
    next(s for s in d['sections'] if s['id'] == 'summary')['text'] = 'ZEBRAPAY SECRETFIELD late words.'
    creaite_doc.real({DRAFT!r}).write_text(creaite_doc.dumps(d, keep_text=True), encoding='utf-8')
    return None
out = client_snapshot.client_export('ABC', '{WEEK}', 'html', settle=settle)
if out.get('ok'):
    p = creaite_doc.real(out['path'])
    out['text'] = p.read_text(encoding='utf-8')
    p.unlink()
print(json.dumps(out))
"""
        return self.py(code)

    def test_snapshot_export_renders_the_snapshot_not_the_file_read_again(self):
        self.fresh()
        out = self.export_racing()
        self.assertTrue(out["ok"], out)
        self.assertNotIn("ZEBRAPAY", out["text"])

    def test_snapshot_mutant_rendering_the_file_puts_the_late_words_in_the_export(self):
        self.fresh()
        out = self.export_racing(self.FROM_FILE)
        self.assertTrue(out["ok"], out)
        self.assertIn("ZEBRAPAY", out["text"])                   # the test above is what catches it

    # ── tracker.py apply re-checks a creaite-format client report's staged write ──────────────────────────────────────────
    def stage_and_tamper(self, extra):
        r = self.fresh()
        self.save(r["doc"], r["version"])
        staged = self.py(f"import report_doc\nprint(json.dumps(str(report_doc.stage_client({DRAFT!r}, force=True, code='ABC', "
                         f"fri='{WEEK}'))))")
        p = Path(staged) if Path(staged).is_absolute() else self.v.root / staged
        data = json.loads(p.read_text(encoding="utf-8"))
        if extra is not None:
            w = next(op for op in data["report"]["file_ops"] if op["op"] == "write" and op["path"].endswith(".html"))
            self.assertIn("</main>", w["content"])
            w["content"] = w["content"].replace("</main>", f"<p>{extra}</p></main>", 1)
            p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        return p

    def apply(self, p):
        return subprocess.run([sys.executable, "system/scripts/tracker.py", "apply", p.name], cwd=self.v.root, capture_output=True,
                              text=True, env={**os.environ, "CREAITE_NOW": S.NOW})

    def test_apply_refuses_a_staged_client_write_changed_to_hold_internal_content(self):
        hid, title, owner = self.hidden_item()
        p = self.stage_and_tamper(f"{hid}: {title}")
        r = self.apply(p)
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(list(self.reports.glob("*Client report*")), [], r.stdout)
        self.assertRegex(r.stdout + r.stderr, r"internal content|isn't client-visible")
        p.unlink(missing_ok=True)

    def test_apply_control_an_untouched_staged_client_write_is_filed(self):
        p = self.stage_and_tamper(None)
        r = self.apply(p)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(list(self.reports.glob(f"{S.CLIENT_STEM}.html")), r.stdout)


for _name in [n for n in dir(A.Audience) if n.startswith("test_")]:
    setattr(K, _name, None)                                   # only this file's tests run here


if __name__ == "__main__":
    unittest.main(verbosity=2)
