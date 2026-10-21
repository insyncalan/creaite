"""Fuzz the v2.5.0 picture-path fix. Fictional data only. argv[1] = worktree root."""
import sys, os, json, shutil, tempfile, unittest, zipfile
from pathlib import Path
ROOT = Path(sys.argv.pop(1))
sys.path.insert(0, str(ROOT / "dev" / "tests"))
sys.path.insert(0, str(ROOT / "system" / "scripts"))
from test_report_exports import ABC, ITEMS, Base
from test_word_export_227 import png
import docx_tools

OUT, OWN, OTHER, HARD = (77, 13), (31, 17), (45, 19), (53, 23)


def sizes(p):
    with zipfile.ZipFile(p) as z:
        return [list(docx_tools.image_size(z.read(n))) for n in z.namelist() if n.startswith("word/media/")]


class F(Base):
    def setUp(self):
        super().setUp()
        self.out = Path(tempfile.mkdtemp(prefix="fz-")); self.addCleanup(shutil.rmtree, self.out, True)
        (self.out / "x.png").write_bytes(png(*OUT))
        (self.v.root / "x.png").write_bytes(png(*OUT))
        (self.v.root / "projects" / "x.png").write_bytes(png(*OUT))
        proj = self.v.root / ABC
        self.proj = proj
        (proj / "images").mkdir(parents=True, exist_ok=True)
        (proj / "images" / "own.png").write_bytes(png(*OWN))
        (proj / "documents").mkdir(exist_ok=True)
        (proj / "documents" / "doc.png").write_bytes(png(*OWN))
        (self.out / "h.png").write_bytes(png(*HARD)); os.link(self.out / "h.png", proj / "images" / "hard.png")   # hard link to an outside file
        (proj / "images" / "lnk.png").symlink_to(self.out / "x.png")
        # another project
        others = [p for p in (self.v.root / "projects").iterdir() if p.is_dir() and p.name != Path(ABC).name and not p.name.startswith("_")]
        self.other = others[0] if others else None
        if self.other:
            (self.other / "images").mkdir(exist_ok=True)
            (self.other / "images" / "theirs.png").write_bytes(png(*OTHER))
        o = str(self.out / "x.png")
        self.refs = [o, "../x.png", "../../x.png", "../../../x.png", "images/../../x.png", "images/../../../x.png", "images//" + o.lstrip("/"),
                     "images/%2e%2e/%2e%2e/%2e%2e/x.png", "images\\..\\..\\..\\x.png", "file://" + o, "~/x.png", "C:/x.png", "C:\\x.png",
                     "//server/share/x.png", "\\\\server\\share\\x.png", "images/x\x00.png", "images/" + "a/" * 2000 + "x.png",
                     "IMAGES/../../../x.png", "Images/own.png", "images/./own.png", "./images/own.png", "images/hard.png", "images/lnk.png",
                     "documents/doc.png", "images/theirs.png", "_images/../../../../x.png", "_images/x.png",
                     "/" + o.lstrip("/"), "///" + o.lstrip("/"), "images/own.png", "images/own.png#", "images/own.png?x=1",
                     "%2fx.png", "images/..%2f..%2f..%2fx.png", "data:image/png;base64,AAAA", "http://example.invalid/x.png"]
        if self.other:
            self.refs.append(f"../{self.other.name.replace(' ', '%20')}/images/theirs.png")

    def md(self, refs):
        lines = "\n".join(f"![leak]({r})" for r in refs)
        extra = (f"\n[![a]({self.out}/x.png)](https://example.invalid)\n![a][r]\n\n[r]: {self.out}/x.png\n<img src=\"{self.out}/x.png\">\n"
                 f"![a](<{self.out}/x.png>)\n![a]( {self.out}/x.png )\n![a]({self.out}/x.png \"t\")\n| ![a]({self.out}/x.png) | b |\n|---|---|\n| c | d |\n"
                 f"- ![a]({self.out}/x.png)\n> ![a]({self.out}/x.png)\n   ![a]({self.out}/x.png)   ")
        return lines + extra

    def secs(self, md):
        return [
            {"id": "health", "type": "health", "heading": "Health", "default_heading": "Health", "hidden": False, "text": md, "data": {"flag": "On track"}},
            {"id": "summary", "type": "text", "heading": "Summary", "default_heading": "Summary", "hidden": False, "text": md},
            {"id": "risks", "type": "table", "heading": "Risks", "default_heading": "Risks", "hidden": False, "text": md,
             "columns": [{"key": "id", "label": "ID"}], "rows": [{"ref": "ABC-002", "cells": {"id": md}, "shown": True}]},
            {"id": "milestones", "type": "timeline", "heading": "Milestones", "default_heading": "Milestones", "hidden": False, "text": md,
             "data": {"milestones": ["ABC-M-001"]}},
            {"id": "current_state", "type": "panes", "heading": "Current state", "default_heading": "Current state", "hidden": False,
             "text": md, "panes": [{"title": md, "text": md}]}]

    def run_code(self, kind, audience, refs, token):
        secs = self.secs(self.md(refs))
        return ("from pathlib import Path\nimport paths\n"
                + ("try:\n    import client_snapshot\n    TOK = client_snapshot.TOKEN\nexcept ImportError:\n    TOK = None\n" if token else "")
                + f"doc = creaite_doc.new({kind!r}, 'ABC', 'Report', '2026-10-16', {secs!r}, items={ITEMS!r}, audience={audience!r})\n"
                "o = Path(paths.DRAFTS) / 'fz.docx'\n"
                + ("creaite_doc.word_export(doc, o, token=TOK) if TOK is not None else creaite_doc.word_export(doc, o)\n" if token else "creaite_doc.word_export(doc, o)\n")
                + "h = creaite_doc.render(doc, editing=False)\n"
                "print(json.dumps([str(o), h.count('data:image'), 'x.png' in h]))")

    def run_one(self, kind, audience, refs, token=False):
        """The Word export of a document built here. v2.5.1+: a client report is made only by client_snapshot.client_export, so the
        call without client_snapshot.TOKEN is refused (a HELD line, not a leak); with the token it is the renderer under test."""
        import subprocess
        r = subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts'); import creaite_doc\n"
                            + self.run_code(kind, audience, refs, token)], cwd=self.v.root, capture_output=True, text=True)
        if r.returncode != 0:
            last = [ln for ln in r.stderr.splitlines() if ln.strip()][-1:] or ["(no message)"]
            print(f"### HELD {kind}/{audience}{'' if token else ' direct'}: {last[0][:200]}")
            return None
        got = json.loads(r.stdout.strip().splitlines()[-1])
        print('### html data images:', got[1], 'names x.png:', got[2])
        return sizes(got[0])

    def test_word(self):
        res = {}
        for kind, aud in (("client", "client"), ("client", "internal"), ("weekly", "internal"), ("client", "distributed")):
            variants = (False, True) if kind == "client" else (False,)
            for token in variants:
                s = self.run_one(kind, aud, self.refs, token)
                if s is None:
                    continue
                label = f"{kind}/{aud}" + ("" if token or kind != "client" else " direct")
                res[label] = s
                print(f"\n### {kind}/{aud}: HARD={list(HARD) in s} OUT={list(OUT) in s} OWN={list(OWN) in s} OTHER={list(OTHER) in s} n={len(s)}"
                      + ("" if token or kind != "client" else " (made without the checked copy)"))
                self.assertNotIn(list(OUT), s, f"{kind}/{aud} leaks outside file")
                self.assertNotIn(list(OTHER), s, f"{kind}/{aud} other project")

    def test_funcs(self):
        r = self.py("import paths\nf = paths.project_dir('ABC')\n"
                    f"refs = {self.refs!r}\n"
                    "out=[]\n"
                    "for x in refs:\n"
                    "    a = paths.resolve_image(f, x)\n"
                    "    try: ok = a.is_file()\n"
                    "    except Exception as e: ok = 'ERR '+type(e).__name__\n"
                    "    b = paths.image_file(f, x)\n"
                    "    out.append([x[:60], ok, str(a.resolve())[-40:] if ok is True else '', bool(b)])\n"
                    "print(json.dumps(out))")
        for row in r:
            if row[1] is True or row[3]:
                print("### reachable:", row)
            if isinstance(row[1], str):
                print("### error:", row)


if __name__ == "__main__":
    unittest.main(verbosity=1)
