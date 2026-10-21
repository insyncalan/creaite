"""The 2.5.3 classes (#259), as probes that run on any 2.5.x tree: the routes on a live server in a throwaway vault (the audience test's
harness), fictional data only. Each case prints one line:   ### CASE <name> | LEAK|PASS|HELD|CTRL-FAIL | evidence
  LEAK      a client file (or a filed client report) holds hidden text, or a hidden ID written loosely was not found
  HELD      creaite refused, nothing client-facing was made or filed
  PASS      a clean case, or a control that did what it should
  CTRL-FAIL a control (a thing that should be allowed) was blocked: over-blocking, a functional fault, not a leak
Usage: python probe.py <tree root> <variant>   variants: launder, apply, apply-steerco, p16, m4"""
import json
import os
import sqlite3
import subprocess
import sys
import unittest
from contextlib import closing
from pathlib import Path

ROOT = Path(sys.argv.pop(1))
VARIANT = sys.argv.pop(1)
sys.path.insert(0, str(ROOT / "dev" / "tests"))
sys.path.insert(0, str(ROOT / "system" / "scripts"))
sys.path.insert(0, str(ROOT / "system" / "scripts" / "vendor"))
import test_client_audience as A  # noqa: E402
import test_report_export_save as S  # noqa: E402
import creaite_doc  # noqa: E402

WEEK = A.WEEK
DRAFT = f"system/staging/drafts/{S.CLIENT_STEM}.html"
FILED_NAME = f"{S.CLIENT_STEM}.html"
SECRET = "ZEBRAPAY quiet words"        # words no gate knows: only the derived audience keeps them out of a client file
PLAIN = ["SECRETFIELD", "secretfield-zebrapay", "ZEBRAPAY"]


def case(name, status, ev=""):
    print(f"### CASE {name} | {status} | {str(ev)[:200]}", flush=True)


class P(A.Audience):
    # ── helpers (the same as the tree's own tests use, written out here so they exist on every 2.5.x tree) ─────────────────────
    def db(self):
        con = sqlite3.connect(self.v.root / "system/tracker.db")
        con.row_factory = sqlite3.Row
        return con

    def hidden_action(self):
        with closing(self.db()) as con:
            return dict(con.execute("SELECT id, description FROM actions WHERE project='ABC' AND client_visible=0 LIMIT 1").fetchone())

    def save(self, doc, version):
        s = self.post("/api/report/save", {"doc": doc, "base_version": version})
        if not s.get("ok"):
            raise RuntimeError("save refused: " + str(s)[:200])
        return s

    def approve(self):
        return self.post("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "force": True})

    def filed(self):
        return self.reports / FILED_NAME

    def on_disk(self, edit):
        """The saved draft file edited outside creaite (ask creaite's way, or any local process)."""
        f = self.draft_file()
        text = f.read_text(encoding="utf-8")
        d = creaite_doc.loads(text)
        edit(d)
        d["layout"]["order"] = [s["id"] for s in d["sections"]]
        m = creaite_doc.BLOCK.search(text)
        f.write_text(text[:m.start(1)] + creaite_doc.data_json(d) + text[m.end(1):], encoding="utf-8")

    def text_of(self, p):
        import zipfile
        if p.suffix == ".docx":
            with zipfile.ZipFile(p) as z:
                return "".join(z.read(n).decode("utf-8", "ignore") for n in z.namelist())
        return p.read_text(encoding="utf-8", errors="ignore")

    def outputs(self):
        """{name: text} of every client output made now: the html and docx exports, and the filed report after Approve."""
        out = {}
        for fmt in ("html", "docx"):
            e = self.export(fmt, "client", on_clash="number")
            if e.get("ok"):
                p = self.v.root / e["path"]
                out[fmt] = self.text_of(p)
        a = self.approve()
        if a.get("ok"):
            f = self.filed()
            out["filed"] = f.read_text(encoding="utf-8") if f.is_file() else ""
        return out

    def holding(self, outs, needles):
        return {k: [n for n in needles if n.lower() in v.lower()] for k, v in outs.items() if any(n.lower() in v.lower() for n in needles)}

    def apply(self, p):
        return subprocess.run([sys.executable, "system/scripts/tracker.py", "apply", p.name], cwd=self.v.root, capture_output=True,
                              text=True, env={**os.environ, "CREAITE_NOW": S.NOW})

    def undo(self):
        subprocess.run([sys.executable, "system/scripts/tracker.py", "undo"], cwd=self.v.root, capture_output=True,
                       env={**os.environ, "CREAITE_NOW": S.NOW})

    # ── trust laundering: an edited filed client report exported twice ────────────────────────────────────────────────────────
    def approved_with_edit(self):
        r = self.fresh()
        self.save(r["doc"], r["version"])
        a = self.approve()
        if not a.get("ok"):
            raise RuntimeError("approve refused: " + str(a)[:200])
        f = self.filed()
        text = f.read_text(encoding="utf-8")
        d = creaite_doc.loads(text)
        d["sections"].append({"id": "free_sneak", "type": "freetext", "heading": "Notes", "default_heading": "", "hidden": False,
                              "text": f"{SECRET} for the steering group.", "audience": "client"})
        d["layout"]["order"] = [s["id"] for s in d["sections"]]
        m = creaite_doc.BLOCK.search(text)
        f.write_text(text[:m.start(1)] + creaite_doc.data_json(d) + text[m.end(1):], encoding="utf-8")

    def export_text(self, fmt):
        """One client export through client_snapshot.client_export (a process of its own), its text, the file deleted; (text, message)."""
        out = self.py(f"""
import client_snapshot, creaite_doc, zipfile
try:
    out = client_snapshot.client_export('ABC', '{WEEK}', {fmt!r})
except Exception as e:
    out = {{'ok': False, 'message': type(e).__name__ + ': ' + str(e)}}
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
        return out.get("text") or "", out.get("message") or ""

    def test_launder(self):
        orders = (("html", "html", "docx", "html"), ("docx", "docx", "html"), ("html", "docx", "docx", "html", "html"))
        for order in orders:
            self.approved_with_edit()
            for i, fmt in enumerate(order):
                text, msg = self.export_text(fmt)
                name = f"launder {'>'.join(order)} export {i + 1} ({fmt})"
                if "zebrapay" in text.lower():
                    case(name, "LEAK", f"the edited section is in export number {i + 1}")
                elif not text:
                    case(name, "HELD", msg)
                else:
                    case(name, "PASS", "exported without the edited section")
        # through the export route as well
        self.approved_with_edit()
        for i, fmt in enumerate(("html", "docx", "html", "docx")):
            e = self.export(fmt, "client", on_clash="number")
            name = f"launder route export {i + 1} ({fmt})"
            if e.get("ok"):
                p = self.v.root / e["path"]
                hit = "zebrapay" in self.text_of(p).lower()
                p.unlink()
                case(name, "LEAK" if hit else "PASS", "the edited section is in the file" if hit else "exported without the edited section")
            else:
                case(name, "HELD", str(e.get("message"))[:120])
        # control: a client text section creaite itself saved still shows (the fix must not hide the report's own words)
        r = self.fresh()
        d = r["doc"]
        d["sections"].append({"id": "free_c", "type": "freetext", "heading": "Notes", "default_heading": "", "hidden": False,
                              "text": "Plain client words for the steering group.", "audience": "client"})
        d["layout"]["order"] = [s["id"] for s in d["sections"]]
        self.save(d, r["version"])
        self.approve()
        shown = all("Plain client words for the steering group." in self.export_text(f)[0] for f in ("html", "docx", "html"))
        case("launder control: a section creaite saved still shows", "PASS" if shown else "CTRL-FAIL", "" if shown else "the report's own section was held")

    # ── the apply re-check ────────────────────────────────────────────────────────────────────────────────────────────────────
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
            blk.pop("format", None)
        elif how in ("both", "both_no_snapshot"):
            blk["kind"] = "weekly"
            blk.pop("format", None)
            if how == "both_no_snapshot":
                blk["file_ops"] = [o for o in ops if not o.get("path", "").endswith(".client.json")]
        elif how in ("extra_md", "extra_pdf", "extra_md_weekly"):
            ext = ".pdf" if how == "extra_pdf" else ".md"
            ops.insert(1, {"op": "write", "path": w["path"][:-5] + ext, "content": f"Notes: {self.hidden_text()}\n", "previous": None})
            if how == "extra_md_weekly":
                blk["kind"] = "weekly"
                blk.pop("format", None)
        elif how == "extra_copy":
            ops.insert(1, {"op": "copy", "from": "draft", "to": w["path"][:-5] + " copy.html"})
        elif how == "moved":
            w["path"] = w["path"].replace("Client report", "Weekly report")
        return data

    def leaked_files(self):
        hid = self.hidden_item()[0]
        return [f.name for f in self.v.root.joinpath("projects").rglob("*")
                if f.is_file() and f.suffix in (".html", ".md", ".pdf") and "Client report" in f.name
                and hid in f.read_text("utf-8", "ignore")]

    def test_apply(self):
        for how in ("kind_weekly", "format_gone", "both", "both_no_snapshot", "kind_internal", "extra_md", "extra_pdf",
                    "extra_md_weekly", "extra_copy", "moved"):
            p, data = self.staged()
            p.write_text(json.dumps(self.tamper(data, how), ensure_ascii=False, indent=1), encoding="utf-8")
            r = self.apply(p)
            leaked = self.leaked_files()
            stray = [f.name for f in self.reports.glob("*Client report*") if f.suffix in (".md", ".pdf")]
            name = f"apply re-check: staged client proposal edited ({how})"
            if leaked:
                case(name, "LEAK", f"apply filed {leaked} (exit {r.returncode})")
            elif r.returncode == 0:
                case(name, "LEAK", f"apply accepted the edited proposal (exit 0); stray files {stray}")
            else:
                case(name, "HELD", ((r.stdout + r.stderr).strip().splitlines() or [""])[-1][:140])
            if r.returncode == 0:
                self.undo()
            p.unlink(missing_ok=True)
        p, _data = self.staged()
        r = self.apply(p)
        ok = r.returncode == 0 and self.filed().exists()
        case("apply re-check control: the untouched proposal is filed", "PASS" if ok else "CTRL-FAIL",
             "" if ok else "the untouched proposal was refused: " + (r.stdout + r.stderr)[-120:])

    def steerco_staged(self):
        for f in list((self.v.root / "system/staging").glob("proposed-*.json")) + \
                list((self.v.root / "system/staging/drafts").glob("*Steerco*.docx")):
            f.unlink()
        spec = {"code": "ABC", "version": "client", "steerco_date": WEEK, "summary": ["Phase two is being prepared."], "force": True}
        rc = self.py("import report, io, contextlib\nbuf = io.StringIO()\nwith contextlib.redirect_stdout(buf):\n"
                     f"    rc = report.steerco_stage({spec!r})\nprint(json.dumps(rc))")
        if rc != 0:
            raise RuntimeError("steerco_stage returned " + str(rc))
        p = next((self.v.root / "system/staging").glob("proposed-*steerco*.json"))
        return p, json.loads(p.read_text(encoding="utf-8"))

    def steerco_files(self):
        return list(self.v.root.joinpath("projects").rglob("*Steerco one-pager*.docx"))

    def test_apply_steerco(self):
        import test_reports as R
        for how in ("internal", "renamed", "kind_gone"):
            for f in self.steerco_files():
                f.unlink()
            p, data = self.steerco_staged()
            blk = data["report"]
            R.edit_docx(self.v.root / blk["draft"], "Phase two is being prepared.", f"Phase two is being prepared. {self.hidden_item()[1]}.")
            blk["report_decision"] = "approved"
            if how in ("internal", "renamed"):
                blk["version"] = "internal"
            if how == "renamed":
                cp = next(o for o in blk["file_ops"] if o["op"] == "copy")
                cp["to"] = cp["to"].replace(" (client)", "")
            if how == "kind_gone":
                blk.pop("kind", None)
                blk.pop("version", None)
            p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
            r = self.apply(p)
            filed = self.steerco_files()
            name = f"apply re-check: client steerco one-pager switched ({how})"
            if filed:
                case(name, "LEAK", f"filed {[f.name for f in filed]} with a hidden title in it")
                self.undo()
            else:
                case(name, "HELD", ((r.stdout + r.stderr).strip().splitlines() or [""])[-1][:140])
            for f in self.steerco_files():
                f.unlink()

    # ── P16: a hidden item's ID written loosely, through every surface ──────────────────────────────────────────────────────
    def loose_forms(self):
        a = self.hidden_action()["id"]
        code, letter, num = a.split("-")
        n = int(num)
        positive = [f"{code}-{letter}-0{num}/1", f"{code}-{letter}-{num}.5", f"{code}-{letter}-{num}-5", f"{code}-{letter}-{num}/2026",
                    f"{code}-{letter}-{num}／1", f"12 {a}", f"{code}-{letter}-00{num}.1", f"{code}-{letter}-{num}:10",
                    " ".join(code) + f" - {letter} - {num}.5", f"{code} {letter} " + " ".join(num) + ".5",
                    " ".join(code) + f" - {letter} - " + " ".join(num), f"{code}-{letter}-0{num}", f"{code}-{letter}-{n}",
                    f"{code}-{letter}-0{n}/1"]
        negative = [f"{code} {letter} {n}/10", f"{code} {letter} {n}/10/2026", f"{code} {letter} {n}.10", f"{code} {letter} {n}:10",
                    f"{code} {letter} 12.5", f"{code} 2026/10/20", f"{code} 500, 600 and 700 users", "ABC A 4/10"]
        return positive, negative

    def surfaces(self):
        """{surface: function(text) -> findings list}"""
        def output(text):
            return self.py("import client_output\nprint(json.dumps(client_output.text_findings({'project': 'ABC', 'sections': []}, "
                           f"{text!r})))")

        def gate(text):
            return self.py("import client_leak, tracker\ncon = tracker.connect()\n"
                           f"print(json.dumps(client_leak.text_findings(con, 'ABC', {text!r})))")

        def ai(text):
            return self.py(f"import edit_ai\nprint(json.dumps(edit_ai.client_problems('ABC', {('Status: ' + text)!r})))")
        return {"output-check": output, "gate": gate, "ai-draft": ai}

    def word_body(self, forms):
        """{form: findings} through review.client_findings on the client one-pager's Word body edited to hold the form."""
        import test_reports as R
        p, data = self.steerco_staged()
        blk = data["report"]
        docx = self.v.root / blk["draft"]
        original = docx.read_bytes()
        out = {}
        for words in forms:
            docx.write_bytes(original)
            R.edit_docx(docx, "Phase two is being prepared.", f"Phase two is being prepared. {words}.")
            out[words] = self.py(f"import review\nprint(json.dumps(review.client_findings({blk!r})))")
        docx.write_bytes(original)
        return out

    def test_p16(self):
        positive, negative = self.loose_forms()
        for sname, fn in self.surfaces().items():
            for f in positive:
                got = fn(f"See {f} for the detail.")
                case(f"P16 {sname}: {f!r}", "PASS" if got else "LEAK", "found" if got else "the hidden ID passed")
            for f in negative:
                got = fn(f"Plain words: {f} is the day.")
                case(f"P16 {sname} control: {f!r}", "PASS" if not got else "CTRL-FAIL", "" if not got else f"over-blocked: {got[:1]}")
        try:
            wp = self.word_body(positive)
            wn = self.word_body(negative)
        except Exception as e:      # noqa: BLE001  the steerco one-pager could not be staged on this tree
            case("P16 word-body: could not stage the one-pager", "HELD", repr(e)[:160])
            return
        for f, got in wp.items():
            case(f"P16 word-body: {f!r}", "PASS" if got else "LEAK", "found" if got else "the hidden ID passed")
        for f, got in wn.items():
            case(f"P16 word-body control: {f!r}", "PASS" if not got else "CTRL-FAIL", "" if not got else f"over-blocked: {got[:1]}")

    # ── M4: default_heading and the layout's lists carrying words ──────────────────────────────────────────────────────────
    def plant_m4(self, d):
        for s in d["sections"]:
            s["default_heading"] = f"SECRETFIELD {s['id']}"
        lay = d.setdefault("layout", {})
        lay["hidden"] = list(lay.get("hidden") or []) + ["SECRETFIELD hidden"]
        lay["glance"] = list(lay.get("glance") or []) + ["SECRETFIELD glance"]
        lay["logos"] = list(lay.get("logos") or []) + ["SECRETFIELD logo", "partner:secretfield-zebrapay"]
        lay["milestones"] = ["SECRETFIELD milestone"]
        lay["order"] = list(lay.get("order") or []) + ["SECRETFIELD order"]

    def test_m4(self):
        for way in ("save", "disk"):
            r = self.fresh()
            if way == "save":
                self.plant_m4(r["doc"])
                sv = self.post("/api/report/save", {"doc": r["doc"], "base_version": r["version"]})
                if not sv.get("ok"):
                    case(f"M4 default_heading and layout lists via {way}", "HELD", str(sv.get("message"))[:140])
                    continue
            else:
                self.on_disk(self.plant_m4)
            outs = self.outputs()
            hit = self.holding(outs, PLAIN)
            if not outs:
                case(f"M4 default_heading and layout lists via {way}", "HELD", "no client output was made")
            else:
                case(f"M4 default_heading and layout lists via {way}", "LEAK" if hit else "PASS",
                     f"words in {sorted(hit)}" if hit else f"{sorted(outs)} made, none holds the words")


if __name__ == "__main__":
    test = {"launder": "test_launder", "apply": "test_apply", "apply-steerco": "test_apply_steerco", "p16": "test_p16",
            "m4": "test_m4"}[VARIANT]
    unittest.main(argv=["x", f"P.{test}"], verbosity=0)
