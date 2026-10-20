"""v2.5.1 client output, step 2 (#239): every client file is made from one checked, immutable snapshot. The data is fictional.

Run: python3 dev/tests/test_client_output_step2.py        (the PDF cases need Chrome; skipped without it)

dev/proposals/client-output-snapshot.md is the design; each test fails on step 1 (v251-step1) and passes on step 2:
  - Approve writes the snapshot beside the filed report (`<name>.client.json`), its SHA-256 in system/staging/client-snapshots.json
    (hashes and counts only), and Undo takes it back                                                  test_snapshot_*
  - client_export reads only the snapshot: one changed on disk (hash) is refused; a filed report edited by hand since is
    checked again on its own text ("can't be exported again: ..."); a filed report from before 2.5.1 builds one on its first
    export                                                                                             test_export_*, test_migration_*
  - creaite_doc.export, _make_export and word_export refuse a client report unless client_export calls them (its token)  test_token_*
  - the snapshot is read and rendered under the save route's lock                                     test_lock_*
  - known gap C: a picture added for the internal report is never drawn into a client report; a client report's own picture is
    `_images/client-<name>`, drawn only with the bytes its snapshot recorded; a logo changed since is not drawn  test_gap_c_*, test_logo_*
  - Show as exported for a client report is the server's render of a preview snapshot (marked Preview, nothing written), and its
    answer names the report it is of (P12, server tier)                                               test_preview_*
  - real HTTP: saves racing exports never put a needle in a filed client file                         test_race_*
  - a whole-output scan: every client output (.html, .docx, .pdf, the filed data block, the snapshot) holds no needle  test_whole_*
Mutation proofs (CREAITE_STEP2_MUTANTS=1): with each new guard switched off in the live server, its named test goes red.
"""
import copy
import hashlib
import json
import os
import re
import sys
import threading
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_client_audience as A  # noqa: E402
import test_report_export_save as S  # noqa: E402
from test_dashboard import png  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
import creaite_doc  # noqa: E402

WEEK = A.WEEK
DRAFT = f"system/staging/drafts/{S.CLIENT_STEM}.html"
SNAP = f"projects/ABC Example Programme/reports/{S.CLIENT_STEM}.client.json"
REGISTRY = "system/staging/client-snapshots.json"
NEVER = "ZEBRAPAY-SECRETFIELD"           # words no gate knows: only the snapshot's hash keeps them out


class Step2(A.Audience):
    """The routes on a live server in a throwaway vault (test_client_audience's harness, without its tests)."""

    def approve(self):
        a = self.post("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "force": True})
        self.assertTrue(a["ok"], a)
        return a

    def filed(self):
        r = self.fresh()
        self.assertTrue(self.post("/api/report/save", {"doc": r["doc"], "base_version": r["version"]})["ok"])
        return self.approve()

    def registry(self):
        p = self.v.root / REGISTRY
        return json.loads(p.read_text())["snapshots"] if p.is_file() else {}

    def entry(self, stored):
        """The registry's entry for a snapshot (keyed by the SHA-256 of its stored path: the registry names no report)."""
        return self.registry().get(hashlib.sha256(stored.encode()).hexdigest())

    def stored(self, state):
        return f"system/staging/client-snapshots/{S.CLIENT_STEM} ({state}).client.json"

    def media(self, docx):
        with zipfile.ZipFile(docx) as z:
            return [z.read(n) for n in z.namelist() if n.startswith("word/media/")]

    def holds_picture(self, docx, data):
        from docx_tools import strip_image_metadata
        return any(m in (data, strip_image_metadata(data)) for m in self.media(docx))

    def client_text(self, extra):
        """The draft on disk with one more shown client text section."""
        d = creaite_doc.read(self.draft_file())
        d["sections"] = [s for s in d["sections"] if s["id"] != "free_c"] + [
            {"id": "free_c", "type": "freetext", "heading": "Pictures", "default_heading": "", "hidden": False, "text": extra,
             "audience": "client"}]
        d["layout"]["order"] = [s["id"] for s in d["sections"]]
        self.draft_file().write_text(creaite_doc.dumps(d, keep_text=True), encoding="utf-8")

    def images(self):
        f = self.v.root / "projects/ABC Example Programme/reports/_images"
        f.mkdir(parents=True, exist_ok=True)
        return f

    # ── the snapshot ────────────────────────────────────────────────────────────────────────────────────────────────────
    def test_snapshot_approve_writes_it_beside_the_filed_report_and_records_its_hash(self):
        a = self.filed()
        snap = self.v.root / SNAP
        self.assertTrue(snap.is_file(), a)
        text = snap.read_text()
        self.assertIn(hashlib.sha256(text.encode()).hexdigest(), self.entry(SNAP)["hashes"])
        filed = (self.v.root / a["path"]).read_text()
        data = json.loads(text)
        self.assertEqual(data["source"]["sha256"], hashlib.sha256(filed.encode()).hexdigest())
        self.assertEqual((data["format"], data["project"], data["week_ending"], data["state"]), ("creaite-client-snapshot", "ABC", WEEK, "filed"))
        self.assertNotIn("health_diff", data["doc"].get("meta") or {})
        for x in data["logos"]:
            self.assertEqual(sorted(x), ["kind", "name", "sha256", "stripped"])          # by name and hash, never a path
            self.assertNotIn("/", x["name"])
        # the registry holds hashes, dates, codes and counts only: never a word of the report
        reg = json.dumps(self.registry())
        for word in ("Example Client", "Example Programme", "UAT", "Client report"):
            self.assertNotIn(word, reg)
        self.assertEqual(self.scan(snap, self.needles()), [])

    def test_snapshot_is_not_listed_among_the_reports(self):
        self.filed()
        names = self.py("import paths\nprint(json.dumps([f.name for f, _l in paths.report_files('ABC')]))")
        self.assertTrue(any(n.endswith(".html") and "Client report" in n for n in names), names)
        self.assertFalse(any(n.endswith(".client.json") for n in names), names)

    def test_snapshot_undo_takes_it_back_with_the_filing(self):
        import subprocess
        self.filed()
        self.assertTrue((self.v.root / SNAP).is_file())
        r = subprocess.run([sys.executable, "system/scripts/tracker.py", "undo"], cwd=self.v.root, capture_output=True, text=True,
                           env={**os.environ, "CREAITE_NOW": S.NOW})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse((self.v.root / SNAP).exists(), r.stdout)

    # ── client_export reads only the snapshot ───────────────────────────────────────────────────────────────────────────
    def test_export_a_snapshot_changed_on_disk_is_refused(self):
        self.filed()
        snap = self.v.root / SNAP
        data = json.loads(snap.read_text())
        sec = next(s for s in data["doc"]["sections"] if not s.get("hidden") and s["type"] not in ("header",))
        sec["heading"] = NEVER                                    # words the report never had, which no gate knows
        snap.write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
        for fmt in ("html", "docx"):
            e = self.export(fmt, "client", on_clash="number")
            self.assertFalse(e.get("ok"), e)
            self.assertRegex(e["message"], r"changed outside creaite")
        held = self.reports_hold([NEVER])
        held.pop(Path(SNAP).name, None)                         # the snapshot this test edited holds it; nothing else may
        self.assertEqual(held, {})

    def test_export_of_a_filed_report_renders_the_snapshot_not_the_file(self):
        """A filed file edited by hand since its Approve no longer matches its snapshot's source: it is checked again on its own
        text, and a hidden item in it is refused ("can't be exported again")."""
        a = self.filed()
        f = self.v.root / a["path"]
        text = f.read_text()
        m = creaite_doc.BLOCK.search(text)
        d = self.add_payload(json.loads(m.group(1)))
        f.write_text(text[:m.start(1)] + creaite_doc.data_json(d) + text[m.end(1):], encoding="utf-8")
        e = self.export("docx", "client")
        self.assertFalse(e.get("ok"), e)
        self.assertRegex(e["message"], r"can't be exported again")
        self.assertTrue(e.get("findings"), e)
        held = self.reports_hold(self.needles())
        held.pop(f.name, None)                                   # the file this test edited holds them; nothing else may
        self.assertEqual(held, {})

    def test_export_a_hand_edit_with_unknown_words_on_a_filed_file_is_not_what_is_exported(self):
        """A filed file whose text changed (words no gate knows) is exported from a snapshot built from that text, checked: the
        approved snapshot is never paired with another file."""
        a = self.filed()
        e1 = self.export("docx", "client")
        self.assertTrue(e1["ok"], e1)
        reg_before = self.entry(SNAP)["hashes"]
        f = self.v.root / a["path"]
        f.write_text(f.read_text().replace("</main>", f"<p>{NEVER}</p></main>", 1), encoding="utf-8")   # the page, not the data
        e2 = self.export("html", "client", on_clash="number")
        self.assertTrue(e2["ok"], e2)
        self.assertEqual(self.scan(self.v.root / e2["path"], [NEVER]), [])       # rendered from the data, never the page
        self.assertEqual(self.entry(SNAP)["hashes"], reg_before)

    # ── migration ───────────────────────────────────────────────────────────────────────────────────────────────────────
    def test_migration_a_filed_report_from_before_builds_a_snapshot_on_its_first_export(self):
        a = self.filed()
        (self.v.root / SNAP).unlink()                            # as 2.5.0 filed it: no snapshot
        reg = self.v.root / REGISTRY
        reg.unlink()
        e = self.export("docx", "client")
        self.assertTrue(e["ok"], e)
        self.assertEqual(self.entry(self.stored("filed"))["state"], "filed", self.registry())
        self.assertTrue((self.v.root / self.stored("filed")).is_file())
        self.assertTrue((self.v.root / a["path"]).is_file())     # the filed file is untouched

    def test_migration_a_draft_from_before_builds_a_snapshot_and_a_failing_one_says_why(self):
        self.fresh()
        reg = self.v.root / REGISTRY
        reg.unlink(missing_ok=True)
        e = self.export("html", "client", on_clash="number")
        self.assertTrue(e["ok"], e)
        self.assertEqual(self.entry(self.stored("draft"))["state"], "draft", self.registry())
        self.tamper_on_disk("client")                            # the payload: a hidden item, its owner, "confidential"
        e = self.export("docx", "client")
        self.assertFalse(e["ok"], e)
        self.assertRegex(e["message"], r"can't be exported|possible internal content")
        self.assertTrue(e.get("findings"), e)

    # ── the token ───────────────────────────────────────────────────────────────────────────────────────────────────────
    def test_token_creaite_doc_refuses_a_client_report_not_from_client_export(self):
        self.fresh()
        out = self.py(f"out = creaite_doc.export({DRAFT!r}, 'docx', file_beside=False, open_after=False, kind='client')\n"
                      "d = creaite_doc.read_report(" + repr(DRAFT) + ", 'client')\n"
                      "import paths\n"
                      "w = m = None\n"
                      "try:\n    creaite_doc.word_export(d, paths.DRAFTS / 'x.docx')\nexcept creaite_doc.DocError as e:\n    w = str(e)\n"
                      "try:\n    creaite_doc._make_export(d, 'html', 'x')\nexcept creaite_doc.DocError as e:\n    m = str(e)\n"
                      "print(json.dumps({'export': out, 'word': w, 'make': m}))")
        self.assertFalse(out["export"]["ok"], out)
        self.assertRegex(out["export"]["message"], r"checked copy")
        self.assertRegex(out["word"] or "", r"checked copy")
        self.assertRegex(out["make"] or "", r"checked copy")
        self.assertEqual([p.name for p in (self.v.root / "system/staging/drafts").glob("x.*")], [])

    def test_token_minutes_and_weekly_exports_need_none(self):
        self.weekly()
        out = self.py("w = creaite_doc.export('system/staging/drafts/2026-10-09 Weekly report - Example Programme.html', 'html', "
                      "file_beside=False, open_after=False, kind='weekly')\nprint(json.dumps(w))")
        self.assertTrue(out["ok"], out)
        (self.v.root / out["path"]).unlink()

    # ── the lock ────────────────────────────────────────────────────────────────────────────────────────────────────────
    def test_lock_the_snapshot_is_read_and_rendered_under_the_save_routes_lock(self):
        self.fresh()
        code = f"""
import threading, report_server, client_snapshot
lock = threading.Lock()
report_server.routes(lock, lambda *a: (0, ''), lambda: None)
seen = []
real_load, real_make = client_snapshot.load, creaite_doc._make_export
def load(*a, **k):
    seen.append(('load', lock.locked()))
    return real_load(*a, **k)
def make(*a, **k):
    seen.append(('make', lock.locked()))
    return real_make(*a, **k)
client_snapshot.load, creaite_doc._make_export = load, make
class H:
    def send(self, code, body):
        self.body = body
h = H()
report_server.guarded(report_server.export_route)(h, {{'kind': 'client', 'code': 'ABC', 'week_ending': '{WEEK}', 'fmt': 'html',
                                                        'on_clash': 'number'}})
print(json.dumps({{'answer': h.body, 'seen': seen, 'after': lock.locked()}}))
"""
        out = self.py(code)
        self.assertTrue(out["answer"].get("ok"), out)
        self.assertEqual(out["seen"], [["load", True], ["make", True]], out)
        self.assertFalse(out["after"])

    # ── known gap C: pictures, and logos ────────────────────────────────────────────────────────────────────────────────
    def test_gap_c_a_picture_added_for_the_internal_report_is_never_in_a_client_file(self):
        internal = png(27, 15, (6, 6, 1))
        (self.images() / "internal-raid.png").write_bytes(internal)
        self.fresh()
        self.client_text("![raid](_images/internal-raid.png)")
        for fmt in ("docx", "html"):
            e = self.export(fmt, "client", on_clash="number")
            self.assertFalse(e.get("ok"), e)
            self.assertTrue(any("internal report" in f for f in e.get("findings") or []), e)
        self.assertEqual([f.name for f in self.reports.glob("*Client report*") if f.suffix in (".docx", ".html")], [])
        c = self.post("/api/report/check", {"doc": creaite_doc.read(self.draft_file())})       # the check says so before any export
        self.assertTrue(any("internal report" in f for f in c["left_out"]["findings"]), c)

    def test_gap_c_a_client_reports_own_picture_is_named_so_and_drawn(self):
        import base64
        own = png(25, 19, (2, 7, 2))
        r = self.post("/api/report/image", {"code": "ABC", "name": "site.png", "data": base64.b64encode(own).decode(), "kind": "client"})
        self.assertTrue(r["ok"], r)
        self.assertRegex(r["ref"], r"^_images/client-")
        w = self.post("/api/report/image", {"code": "ABC", "name": "site.png", "data": base64.b64encode(own).decode()})
        self.assertNotRegex(w["ref"], r"^_images/client-")                    # the internal report's picture keeps its name
        self.fresh()
        self.client_text(f"![site]({r['ref']})")
        e = self.export("docx", "client")
        self.assertTrue(e["ok"], e)
        self.assertTrue(self.holds_picture(self.reports / e["name"], own))
        shown = self.post("/api/report/images", {"code": "ABC", "kind": "client", "refs": [r["ref"], w["ref"]]})
        self.assertEqual(sorted(shown["images"]), [r["ref"]])                 # the client editor draws only its own pictures

    def test_gap_c_a_picture_changed_after_approve_is_not_drawn_from_the_snapshot(self):
        import base64
        own, swapped = png(25, 19, (2, 7, 2)), png(25, 19, (9, 0, 9))
        r = self.post("/api/report/image", {"code": "ABC", "name": "plan.png", "data": base64.b64encode(own).decode(), "kind": "client"})
        self.fresh()
        self.client_text(f"![plan]({r['ref']})")
        self.approve()
        (self.v.root / "projects/ABC Example Programme/reports" / r["ref"]).write_bytes(swapped)   # same name, other bytes
        e = self.export("docx", "client")
        self.assertTrue(e["ok"], e)
        self.assertFalse(self.holds_picture(self.reports / e["name"], swapped))

    def test_logo_a_logo_changed_after_approve_is_not_drawn_from_the_snapshot(self):
        logos = self.v.root / "system/branding/logos"
        logos.mkdir(parents=True, exist_ok=True)
        f = logos / "ABC-client.png"
        before = f.read_bytes() if f.exists() else None
        f.write_bytes(png(33, 11, (1, 8, 1)))
        try:
            self.filed()
            changed = png(33, 11, (8, 1, 8))
            f.write_bytes(changed)
            e = self.export("docx", "client")
            self.assertTrue(e["ok"], e)
            self.assertFalse(self.holds_picture(self.reports / e["name"], changed))
        finally:
            if before is None:
                f.unlink(missing_ok=True)
            else:
                f.write_bytes(before)

    # ── Show as exported: the server's render of a preview snapshot ────────────────────────────────────────────────────
    def tree(self):
        h = hashlib.sha256()
        for base in (self.v.root / "projects", self.v.root / "system/staging"):
            for p in sorted(base.rglob("*")):
                if p.is_file() and p.suffix not in (".log", ".jsonl"):
                    h.update(str(p).encode() + p.read_bytes())
        return h.hexdigest()

    def test_preview_show_as_exported_is_the_servers_render_and_writes_nothing(self):
        self.fresh()
        before = self.tree()
        v = self.post("/api/report/exported-view", {"kind": "client", "code": "ABC", "week_ending": WEEK})
        self.assertTrue(v["ok"], v)
        self.assertTrue(v["preview"])
        self.assertEqual((v["identity"]["code"], v["identity"]["week_ending"]), ("ABC", WEEK))
        self.assertIn("<main", v["html"])
        self.assertNotIn("creaite-data", v["html"])
        self.assertEqual(self.tree(), before)
        e = self.export("html", "client", on_clash="number")
        exported = (self.v.root / e["path"]).read_text()
        self.assertEqual(re.sub(r"\s+", " ", v["html"]), re.sub(r"\s+", " ", exported))    # the same page the export files

    def test_preview_of_a_report_that_would_leak_shows_no_page(self):
        self.fresh()
        self.tamper_on_disk("client")
        v = self.post("/api/report/exported-view", {"kind": "client", "code": "ABC", "week_ending": WEEK})
        self.assertFalse(v["ok"], v)
        self.assertNotIn("html", v)
        self.assertTrue(v["findings"], v)

    def test_preview_P12_the_answer_names_the_report_it_is_of(self):
        self.fresh()
        v = self.post("/api/report/exported-view", {"kind": "client", "code": "ABC", "week_ending": "2026-10-07"})
        self.assertEqual(v["identity"]["week_ending"], WEEK)                  # the Friday asked for, never another report's
        w = self.post("/api/report/exported-view", {"kind": "weekly", "code": "ABC", "week_ending": WEEK})
        self.assertFalse(w["ok"], w)

    def test_preview_a_posted_page_is_ignored(self):
        """The exported-page route takes no page: a page sent with the export is never what is written (kept for one release)."""
        r = self.fresh()
        s = self.post("/api/report/save", {"doc": r["doc"], "base_version": r["version"]})
        page = {"html": f'<div class="page"><p>{NEVER}</p></div>', "css": ".page{color:#123}", "palette": "creaite",
                "version": s["version"]}
        e = self.export("html", "client", on_clash="number", page=page)
        self.assertTrue(e["ok"], e)
        self.assertEqual(self.scan(self.v.root / e["path"], [NEVER]), [])
        self.assertTrue(e.get("page_ignored"), e)                         # v2.5.1 step 3: and the answer says so
        e = self.export("html", "client", on_clash="number")
        self.assertNotIn("page_ignored", e)                               # control: no page sent, nothing said

    # ── real HTTP: saves racing exports ─────────────────────────────────────────────────────────────────────────────────
    def test_race_saves_racing_exports_never_put_a_needle_in_a_filed_client_file(self):
        r = self.fresh()
        hid, title, owner = self.hidden_item()
        clean = copy.deepcopy(r["doc"])
        leaky = self.add_payload(copy.deepcopy(r["doc"]))
        for sec in leaky["sections"]:
            if sec["id"] == "free_x":
                sec["text"] = f"{owner} owns {hid} {title}. This is confidential."
        stop = threading.Event()

        def saver():
            i = 0
            while not stop.is_set():
                self.post("/api/report/save", {"doc": leaky if i % 2 else clean, "base_version": None})
                i += 1
        t = threading.Thread(target=saver, daemon=True)
        t.start()
        leaked, made = [], 0
        try:
            for i in range(int(os.environ.get("CREAITE_RACE_N") or 80)):
                e = self.post("/api/report/export", {"kind": "client", "code": "ABC", "week_ending": WEEK,
                                                     "fmt": "docx" if i % 4 == 0 else "html", "on_clash": "number"})
                if e.get("ok"):
                    made += 1
                    hit = self.scan(self.v.root / e["path"], [hid, owner, "confidential"])
                    if hit:
                        leaked.append((e["name"], hit))
        finally:
            stop.set()
            t.join(timeout=60)
        self.assertGreater(made, 0)
        self.assertEqual(leaked, [])

    # ── the whole output ────────────────────────────────────────────────────────────────────────────────────────────────
    def test_whole_every_client_output_holds_no_needle(self):
        r = self.fresh()
        hid, title, owner = self.hidden_item()
        d = r["doc"]
        d["sections"].append({"id": "free_y", "type": "freetext", "heading": "Notes", "default_heading": "", "hidden": True,
                              "text": f"{owner} owns {hid} {title}. Confidential.", "audience": "client"})
        d["sections"].append({"id": "free_int", "type": "freetext", "heading": "Vendor", "default_heading": "", "hidden": False,
                              "text": "INTERNAL walrus words.", "audience": "internal"})
        d["layout"]["order"] = [s["id"] for s in d["sections"]]
        self.assertTrue(self.post("/api/report/save", {"doc": d, "base_version": r["version"]})["ok"])
        made = []
        for fmt in self.formats():
            e = self.export(fmt, "client", on_clash="number")
            self.assertTrue(e["ok"], e)
            made.append(self.v.root / e["path"])
        a = self.approve()
        made += [self.v.root / a["path"], self.v.root / SNAP]
        for fmt in self.formats():
            e = self.export(fmt, "client", on_clash="number")
            self.assertTrue(e["ok"], e)
            made.append(self.v.root / e["path"])
        needles = [hid, title, owner, "confidential", "walrus"]
        self.assertEqual({p.name: self.scan(p, needles) for p in made if self.scan(p, needles)}, {})
        for p in (self.v.root / "system/staging/client-snapshots").glob("*.json"):
            self.assertEqual(self.scan(p, needles), [], p.name)


    # ── mutation proofs: each new guard switched off in this process, its scenario goes red ─────────────────────────────
    def export_in_process(self, patch, fmt="docx"):
        """The export route run in a process of its own on this vault, with `patch` (a guard switched off) first."""
        code = patch + f"""
import report_server
class H:
    def send(self, code, body):
        self.body = body
h = H()
report_server.guarded(report_server.export_route)(h, {{'kind': 'client', 'code': 'ABC', 'week_ending': '{WEEK}', 'fmt': '{fmt}',
                                                        'on_clash': 'number'}})
print(json.dumps(h.body))
"""
        return self.py(code)

    HASH_OFF = ("import client_snapshot\n"
                "client_snapshot._filed_current = lambda stored, text: True\n"
                "_load = client_snapshot.load\n"
                "def load(stored, code, fri):\n"
                "    client_snapshot.entry = lambda s: {'hashes': [client_snapshot.sha(open(client_snapshot.paths.resolve(s)).read())]}\n"
                "    return _load(stored, code, fri)\n"
                "client_snapshot.load = load\n")
    TOKEN_OFF = "creaite_doc.client_token_ok = lambda doc, token: True\n"
    TABLES_OFF = "creaite_doc.tables_in_force = lambda: None\n"
    GAP_C_OFF = "import client_snapshot\ncreaite_doc.CLIENT_PICTURE = ''\nclient_snapshot.CLIENT_PICTURE = ''\n"

    def test_mutant_hash_check_off_exports_a_snapshot_changed_on_disk(self):
        self.test_export_a_snapshot_changed_on_disk_is_refused()
        self.assertFalse(self.export_in_process("", "html").get("ok"))
        e = self.export_in_process(self.HASH_OFF, "html")
        self.assertTrue(e.get("ok"), e)
        self.assertEqual(self.scan(self.v.root / e["path"], [NEVER]), [NEVER])      # the guard is what kept it out

    def test_mutant_token_off_lets_creaite_doc_export_a_client_report(self):
        self.fresh()
        call = f"out = creaite_doc.export({DRAFT!r}, 'html', file_beside=False, open_after=False, kind='client')\nprint(json.dumps(out))"
        self.assertFalse(self.py(call)["ok"])
        out = self.py(self.TOKEN_OFF + call)
        self.assertTrue(out["ok"], out)
        (self.v.root / out["path"]).unlink()

    def test_mutant_tables_off_draws_a_picture_changed_after_approve(self):
        import base64
        own, swapped = png(25, 19, (2, 7, 2)), png(25, 19, (9, 0, 9))
        r = self.post("/api/report/image", {"code": "ABC", "name": "plan.png", "data": base64.b64encode(own).decode(), "kind": "client"})
        self.fresh()
        self.client_text(f"![plan]({r['ref']})")
        self.approve()
        (self.v.root / "projects/ABC Example Programme/reports" / r["ref"]).write_bytes(swapped)
        e = self.export_in_process("")
        self.assertTrue(e["ok"], e)
        self.assertFalse(self.holds_picture(self.reports / e["name"], swapped))
        e = self.export_in_process(self.TABLES_OFF)
        self.assertTrue(e["ok"], e)
        self.assertTrue(self.holds_picture(self.reports / e["name"], swapped))

    def test_mutant_gap_c_off_draws_the_internal_reports_picture(self):
        internal = png(27, 15, (6, 6, 1))
        (self.images() / "internal-raid.png").write_bytes(internal)
        self.fresh()
        self.client_text("![raid](_images/internal-raid.png)")
        self.assertFalse(self.export_in_process("").get("ok"))
        e = self.export_in_process(self.GAP_C_OFF)
        self.assertTrue(e["ok"], e)
        self.assertTrue(self.holds_picture(self.reports / e["name"], internal))

    def test_mutant_lock_off_reads_the_snapshot_outside_the_lock(self):
        self.fresh()
        code = f"""
import contextlib, threading, report_server, client_snapshot
lock = threading.Lock()
report_server.routes(lock, lambda *a: (0, ''), lambda: None)
client_snapshot.locked = contextlib.nullcontext
seen = []
_load = client_snapshot.load
def load(*a, **k):
    seen.append(lock.locked())
    return _load(*a, **k)
client_snapshot.load = load
class H:
    def send(self, code, body):
        self.body = body
h = H()
report_server.guarded(report_server.export_route)(h, {{'kind': 'client', 'code': 'ABC', 'week_ending': '{WEEK}', 'fmt': 'html',
                                                        'on_clash': 'number'}})
print(json.dumps({{'seen': seen}}))
"""
        self.assertEqual(self.py(code)["seen"], [False])                      # test_lock_* asserts [True]: it goes red


for _name in [n for n in dir(A.Audience) if n.startswith("test_")]:
    setattr(Step2, _name, None)                               # only this file's tests run here


if __name__ == "__main__":
    unittest.main(verbosity=2)
