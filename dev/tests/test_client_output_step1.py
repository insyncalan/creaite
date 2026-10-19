"""v2.5.1 client output, step 1 (#239): what a client report's files hold is what was checked. The data is fictional.

Run: python3 dev/tests/test_client_output_step1.py        (the PDF cases need Chrome; skipped without it)

Each test is a review repro of v2.5.0 (dev/proposals/client-output-snapshot.md), failing on it and passing after step 1:
  (a) keys the gate never reads (a top-level key, a section's `ref` or `milestones`) never reach the filed client file
      (creaite_doc.client_shape: one allow-list, used by clean, the gate and filing)          test_a_*
  (b) the header's logos, project name, client, kind and audience are derived, never trusted: a stored logo path (another
      project's logo, an internal picture, a file outside the vault) or a logo unticked since is never drawn  test_b_*
  (c) every client export's OUTPUT (the Word XML, the HTML markup, the PDF text and the pictures) is checked again after it is
      made; a finding deletes it and nothing is filed                                          test_c_*
  (d) the client export reads one document under the save route's lock and renders exactly the one it checked   test_d_*
  (e) the minutes routes refuse a file that is a client report by any sign                      test_e_*
  (f) a page posted with a client export is never what is written                              test_f_*
  and: a text section's audience must be exactly "client" to show (test_text_section_*), and the look-alike letters the
  review found are read as the letters they look like (test_look_alike_*).
"""
import json
import re
import sys
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_client_audience as A  # noqa: E402
import test_report_export_save as S  # noqa: E402
from test_dashboard import png  # noqa: E402
from test_tracker import ABC  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
import creaite_doc  # noqa: E402

WEEK = A.WEEK
DRAFT = f"system/staging/drafts/{S.CLIENT_STEM}.html"


class Step1(A.Audience):
    """The routes on a live server in a throwaway vault (test_client_audience's harness, without its tests)."""

    def write_draft(self, d):
        """ask creaite's way: the draft file in drafts/ written directly."""
        self.draft_file().write_text(creaite_doc.dumps(d, keep_text=True), encoding="utf-8")

    def raw_block(self, f):
        return json.loads(creaite_doc.BLOCK.search(Path(f).read_text(encoding="utf-8")).group(1))

    def media(self, docx):
        with zipfile.ZipFile(docx) as z:
            return [z.read(n) for n in z.namelist() if n.startswith("word/media/")]

    def holds_picture(self, docx, data):
        from docx_tools import strip_image_metadata
        return any(m in (data, strip_image_metadata(data)) for m in self.media(docx))

    def drafts_made(self):
        return sorted(p.name for p in (self.v.root / "system/staging/drafts").glob("*")
                      if re.search(r"\.(docx|pdf)$|\(read only\)| print\.html$", p.name))

    # ── (a) the allow-list ──────────────────────────────────────────────────────────────────────────────────────────────
    def test_a_keys_the_gate_never_reads_never_reach_the_filed_client_file(self):
        self.fresh()
        hid, title, owner = self.hidden_item()
        payload = f"{owner} owns {hid} {title}. Confidential. Internal only: walrus."
        d = creaite_doc.read(self.draft_file())
        d["notes_for_alan"] = payload                         # a top-level key the gate never read
        sec = next(s for s in d["sections"] if not s.get("hidden") and s["type"] != "header")
        sec["ref"] = payload                                  # a section's `ref` (skipped as an item reference)
        sec["milestones"] = [payload]                         # `milestones` outside `data` (skipped too)
        self.write_draft(d)
        a = self.post("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "force": True})
        self.assertTrue(a["ok"], a)
        filed = self.v.root / a["path"]
        raw = self.raw_block(filed)
        self.assertNotIn("notes_for_alan", raw)
        self.assertEqual([s["id"] for s in raw["sections"] if "ref" in s or "milestones" in s], [])
        self.assertEqual(self.scan(filed, [hid, title, owner, "walrus"]), [])
        for fmt in self.formats():
            self.assertTrue(self.export(fmt, "client", on_clash="number")["ok"], fmt)
        self.assertEqual(self.reports_hold([hid, title, owner, "walrus"]), {})

    def test_a_client_shape_keeps_only_known_keys(self):
        out = self.py("d = {'format': 'creaite-doc', 'schema': 1, 'kind': 'client', 'audience': 'client', 'project': 'ABC', "
                      "'title': 'Client report', 'date': '2026-10-09', 'x': 1, 'meta': {'locked': True, 'y': 2}, "
                      "'layout': {'order': ['s'], 'z': 3}, 'sources': [{'ref': 'tracker', 'label': 'l', 'q': 4}], "
                      "'sections': [{'id': 's', 'type': 'table', 'heading': 'H', 'ref': 'r', 'milestones': ['m'], "
                      "'data': {'milestones': ['ABC-M-001', {'k': 1}], 'w': 5}, 'columns': [{'key': 'a', 'label': 'A', 'v': 6}], "
                      "'rows': [{'ref': 'ABC-A-003', 'cells': {'a': 'x'}, 'shown': True, 'u': 7}]}]}\n"
                      "print(json.dumps(creaite_doc.client_shape(d)))")
        self.assertNotIn("x", out)
        self.assertEqual(out["meta"], {"locked": True})
        self.assertEqual(out["layout"], {"order": ["s"]})
        self.assertEqual(out["sources"], [{"ref": "tracker", "label": "l"}])
        s = out["sections"][0]
        self.assertEqual(sorted(s), ["columns", "data", "heading", "id", "rows", "type"])
        self.assertEqual(s["data"], {"milestones": ["ABC-M-001"]})
        self.assertEqual(s["columns"], [{"key": "a", "label": "A"}])
        self.assertEqual(s["rows"], [{"ref": "ABC-A-003", "cells": {"a": "x"}, "shown": True}])

    # ── (b) the header derived, never trusted ───────────────────────────────────────────────────────────────────────────
    def test_b_a_stored_logo_path_is_never_drawn_or_filed(self):
        import tempfile
        root = self.v.root
        logos = root / "system/branding/logos"
        logos.mkdir(parents=True, exist_ok=True)
        other, internal, outside = png(31, 7, (1, 2, 3)), png(29, 11, (4, 5, 6)), png(23, 13, (7, 8, 9))
        (logos / "DEF-client.png").write_bytes(other)                       # another project's client logo
        (root / ABC / "images").mkdir(parents=True, exist_ok=True)
        (root / ABC / "images/internal-org-chart.png").write_bytes(internal)  # an internal project picture
        od = Path(tempfile.mkdtemp())
        (od / "secret.png").write_bytes(outside)                            # a file outside the vault
        try:
            r = self.fresh()
            doc = r["doc"]
            stored = [{"kind": "client", "path": "system/branding/logos/DEF-client.png"},
                      {"kind": "partner", "path": f"{ABC}/images/internal-org-chart.png"},
                      {"kind": "firm", "path": str(od / "secret.png")}]
            self.section(doc, "header").setdefault("data", {})["logos"] = stored
            self.assertTrue(self.post("/api/report/save", {"doc": doc, "base_version": r["version"]})["ok"])
            d = self.raw_block(self.draft_file())                          # and edited on disk once more
            self.section(d, "header")["data"]["logos"] = stored
            self.write_draft(d)
            e = self.export("docx", "client")
            self.assertTrue(e["ok"], e)
            for label, data in (("other project's logo", other), ("internal picture", internal), ("outside file", outside)):
                self.assertFalse(self.holds_picture(self.reports / e["name"], data), label)
            a = self.post("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "force": True})
            self.assertTrue(a["ok"], a)
            text = (root / a["path"]).read_text(encoding="utf-8")
            for bad in ("DEF-client.png", "internal-org-chart", str(od)):
                self.assertNotIn(bad, text)
        finally:
            (logos / "DEF-client.png").unlink(missing_ok=True)

    def test_b_a_logo_unticked_since_the_draft_was_made_is_not_drawn(self):
        root = self.v.root
        mem = root / ABC / "CLAUDE.md"
        before = mem.read_text()
        logos = root / "system/branding/logos"
        logos.mkdir(parents=True, exist_ok=True)
        partner = png(37, 9, (9, 9, 1))
        (logos / "ABC-partner-nimbus-works.png").write_bytes(partner)
        try:
            t = re.sub(r"- \*\*(Partners|Client report logos):\*\*[^\n]*\n", "", before)
            mem.write_text(t.rstrip("\n") + "\n- **Partners:** Nimbus Works\n- **Client report logos:** firm, client, partner\n")
            r = self.fresh()
            self.assertTrue(any("nimbus" in x["path"] for x in self.section(r["doc"], "header")["data"]["logos"]))
            mem.write_text(mem.read_text().replace("- **Client report logos:** firm, client, partner",
                                                   "- **Client report logos:** firm, client").replace("- **Partners:** Nimbus Works\n", ""))
            r = self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": WEEK})
            self.assertFalse(any("nimbus" in x["path"] for x in self.section(r["doc"], "header")["data"]["logos"]))
            self.assertTrue(self.post("/api/report/save", {"doc": r["doc"], "base_version": r["version"]})["ok"])
            e = self.export("docx", "client")
            self.assertTrue(e["ok"], e)
            self.assertFalse(self.holds_picture(self.reports / e["name"], partner))
        finally:
            mem.write_text(before)
            (logos / "ABC-partner-nimbus-works.png").unlink(missing_ok=True)

    # ── (c) the output checked after it is made ─────────────────────────────────────────────────────────────────────────
    BUGGY_RENDER = ("_real = creaite_doc.section_html\n"
                    "def _leaky(s, items, doc=None):\n"
                    "    return _real(s, items, doc) + '<p>' + creaite_doc.esc(PAYLOAD) + '</p>'\n"
                    "creaite_doc.section_html = _leaky\n"
                    "_parts = creaite_doc._Word.parts\n"
                    "creaite_doc._Word.parts = lambda self, s: _parts(self, s) + [('e', [{'md': PAYLOAD}])]\n")

    def export_in_process(self, fmt, patch):
        hid, title, owner = self.hidden_item()
        code = (f"PAYLOAD = {json.dumps(f'{owner} owns {hid} {title}. This is confidential.')}\n" + patch +
                f"out = creaite_doc.export({DRAFT!r}, {fmt!r}, file_beside=False, open_after=False, kind='client')\n"
                "print(json.dumps(out))")
        return self.py(code)

    def test_c_a_renderer_that_leaks_is_caught_and_nothing_is_kept(self):
        self.fresh()
        for fmt in self.formats():
            with self.subTest(fmt=fmt):
                before = self.drafts_made()
                out = self.export_in_process(fmt, self.BUGGY_RENDER)
                self.assertFalse(out["ok"], out)
                self.assertTrue(out.get("findings"), out)
                self.assertEqual(self.drafts_made(), before)                 # the made file was deleted
        self.assertEqual(self.reports_hold(self.needles()), {})

    def test_c_a_picture_not_in_the_allowed_set_is_caught(self):
        import tempfile
        od = Path(tempfile.mkdtemp())
        (od / "secret.png").write_bytes(png(21, 17, (3, 1, 4)))
        self.fresh()
        patch = f"creaite_doc._Word.logos = lambda self, s: [{{'images': [{{'image': {str(od / 'secret.png')!r}, 'width': 40}}]}}]\n"
        before = self.drafts_made()
        out = self.export_in_process("docx", patch)
        self.assertFalse(out["ok"], out)
        self.assertTrue(any("picture" in f for f in out.get("findings") or []), out)
        self.assertEqual(self.drafts_made(), before)

    def test_c_a_clean_client_export_passes_the_output_check(self):
        self.fresh()
        for fmt in self.formats():
            out = self.export_in_process(fmt, "")
            self.assertTrue(out["ok"], (fmt, out))
            (self.v.root / out["path"]).unlink()

    # ── (d) one document, under the lock ────────────────────────────────────────────────────────────────────────────────
    def test_d_a_save_during_a_client_export_is_never_what_is_filed(self):
        r = self.fresh()
        hid, title, owner = self.hidden_item()
        leaky = self.add_payload(r["doc"])
        for sec in leaky["sections"]:
            if sec["id"] == "free_x":
                sec["text"] = f"{owner} owns {hid} {title}. This is confidential. Internal only: keep."
        code = f"""
import threading, report_server, report_doc
lock = threading.Lock()
report_server.routes(lock, lambda *a: (0, ''), lambda: None)
real = client_check.left_out
leaky = json.loads({json.dumps(json.dumps(leaky))})
held = []
def racing(doc, con=None):
    out = real(doc, con)
    held.append(lock.locked())                       # the check runs under the save route's lock
    s = report_doc.save_draft(leaky, None)          # a save landing after the check (the live server's would wait for the lock)
    assert s['ok'], s
    return out
client_check.left_out = racing
class H:
    def send(self, code, body):
        self.body = body
h = H()
report_server.guarded(report_server.export_route)(h, {{'kind': 'client', 'code': 'ABC', 'week_ending': '{WEEK}', 'fmt': 'docx'}})
gate = client_leak.findings(creaite_doc.read_report({DRAFT!r}, 'client'))
print(json.dumps({{'answer': h.body, 'gate_on_saved_draft': gate, 'held': held}}))
"""
        out = self.py(code)
        self.assertTrue(out["gate_on_saved_draft"], out)                  # the leaky save did land on disk
        self.assertEqual(out["held"], [True])
        self.assertTrue(out["answer"].get("ok") and out["answer"].get("saved"), out["answer"])   # the checked one was filed
        self.assertEqual(self.reports_hold([hid, title, owner, "confidential", "Internal only"]), {})

    # ── (e) the minutes routes ──────────────────────────────────────────────────────────────────────────────────────────
    def minutes_export(self, rel, fmt="docx"):
        return self.post("/api/minutes/export", {"path": rel, "format": fmt, "file_beside": True})

    def test_e_a_client_draft_edited_to_say_minutes_is_refused_by_the_minutes_routes(self):
        needles = self.needles()
        self.fresh()
        self.tamper_kind("minutes", "internal")
        for fmt in ("docx", "html"):
            r = self.minutes_export(DRAFT, fmt)
            self.assertFalse(r.get("ok"), r)
            self.assertIsNone(r.get("path"), r)
        v = self.post("/api/minutes/draft", {"path": DRAFT})
        self.assertFalse(v.get("ok"), v)
        self.assertEqual(self.drafts_made(), [])
        self.assertEqual(self.reports_hold(needles), {})

    def test_e_a_filed_client_report_edited_to_say_minutes_is_refused(self):
        needles = self.needles()
        self.fresh()
        a = self.post("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "force": True})
        self.assertTrue(a["ok"], a)
        f = self.v.root / a["path"]
        text = f.read_text()
        m = creaite_doc.BLOCK.search(text)
        d = self.add_payload(json.loads(m.group(1)))
        d["kind"], d["audience"] = "minutes", "internal"
        f.write_text(text[:m.start(1)] + creaite_doc.data_json(d) + text[m.end(1):], encoding="utf-8")
        r = self.minutes_export(a["path"])
        self.assertFalse(r.get("ok"), r)
        held = self.reports_hold(needles)
        held.pop(f.name, None)                          # the file this test edited holds them; nothing else may
        self.assertEqual(held, {})

    def test_e_a_client_report_renamed_out_of_its_pattern_is_refused_by_its_data(self):
        self.fresh()
        d = self.add_payload(creaite_doc.read(self.draft_file()))
        d["kind"], d["audience"] = "minutes", "internal"
        neutral = self.v.root / "system/staging/drafts/2026-10-09 Steering notes.html"
        neutral.write_text(creaite_doc.dumps(d, keep_text=True), encoding="utf-8")
        try:
            r = self.minutes_export("system/staging/drafts/2026-10-09 Steering notes.html")
            self.assertFalse(r.get("ok"), r)
        finally:
            neutral.unlink(missing_ok=True)

    def test_e_real_minutes_still_export(self):
        doc = creaite_doc.new("minutes", "ABC", "Steering", "2026-10-06",
                              [{"id": "notes", "type": "text", "heading": "Notes", "text": "The plan was agreed."}])
        f = self.v.root / "system/staging/drafts/2026-10-06 Steering.html"
        f.write_text(creaite_doc.dumps(doc), encoding="utf-8")
        try:
            r = self.post("/api/minutes/export", {"path": "system/staging/drafts/2026-10-06 Steering.html", "format": "html",
                                                  "file_beside": False})
            self.assertTrue(r.get("ok"), r)
            (self.v.root / r["path"]).unlink(missing_ok=True)
        finally:
            f.unlink(missing_ok=True)

    # ── (f) a posted page ───────────────────────────────────────────────────────────────────────────────────────────────
    def test_f_a_page_posted_with_a_client_export_is_never_written(self):
        r = self.fresh()
        s = self.post("/api/report/save", {"doc": r["doc"], "base_version": r["version"]})
        self.assertTrue(s["ok"], s)
        html = ('<div id="v-client"><div class="page"><p>Replace the walrus vendor before renewal - Priya Okafor is on it.</p>'
                '<p>Vendor shortlist cut to two after the pricing review.</p></div></div>')
        page = {"html": html, "css": ".page{color:#123}", "palette": "creaite", "version": s["version"]}
        for fmt in ["html"] + (["pdf"] if S.HAVE_CHROME else []):
            e = self.export(fmt, "client", on_clash="number", page=page)
            self.assertTrue(e.get("ok"), e)
            self.assertEqual(self.scan(self.v.root / e["path"], ["walrus", "Priya Okafor", "Vendor shortlist"]), [], fmt)
            self.assertTrue(e.get("plain"), e)

    # ── a text section's audience, and look-alike letters ───────────────────────────────────────────────────────────────
    def test_text_section_shows_only_when_its_audience_is_exactly_client(self):
        for aud, shown in (("internal", False), ("Internal", False), (" internal", False), ("weekly", False), (None, False),
                           ("Client", False), (" client", False), ("client", True)):
            doc = {"format": "creaite-doc", "schema": 1, "kind": "client", "audience": "client", "project": "ABC",
                   "title": "Client report", "date": WEEK,
                   "sections": [{"id": "free_int", "type": "freetext", "heading": "Vendor notes", "hidden": False,
                                 "text": "Our walrus margin plan for the renewal.", "audience": aud}]}
            with self.subTest(audience=aud):
                self.assertEqual("walrus" in creaite_doc.render(doc, editing=False), shown)

    def test_look_alike_letters_are_read_as_the_letters_they_look_like(self):
        import edit_ai
        for disguised, plain in (("ѕ", "s"), ("ԁ", "d"), ("у", "y"), ("օ", "o"), ("ꓮ", "A")):
            self.assertEqual(edit_ai.normal(disguised), plain, hex(ord(disguised)))
        hid, title, _owner = self.hidden_item()
        subs = {"s": "ѕ", "d": "ԁ", "y": "у", "o": "օ"}
        r = self.fresh()
        for text in ("".join(subs.get(c, c) for c in title) + ".", "ꓮ" + hid[1:] + " is late.",
                     "Thiѕ iѕ cօnfiԁential."):
            with self.subTest(text=text):
                doc = dict(r["doc"], sections=r["doc"]["sections"] + [
                    {"id": "free_x", "type": "freetext", "heading": "Notes", "default_heading": "", "hidden": False, "text": text,
                     "audience": "client"}])
                m = self.post("/api/report/match-check", {"docs": [doc]})
                self.assertTrue(m["findings"][0], (text, m))


for _name in [n for n in dir(A.Audience) if n.startswith("test_")]:
    setattr(Step1, _name, None)                               # only this file's tests run here


if __name__ == "__main__":
    unittest.main(verbosity=2)
