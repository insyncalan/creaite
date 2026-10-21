"""Does a Markdown picture line in a client report's pane/health/text section pull any file into the client Word? Fictional data."""
import sys, unittest, tempfile, shutil
from pathlib import Path
ROOT = Path(sys.argv.pop(1))
sys.path.insert(0, str(ROOT / "dev" / "tests"))
import test_report_exports as T
from test_report_exports import tiny_png, ABC, ITEMS

class P(T.Base):
    def test_md(self):
        out = Path(tempfile.mkdtemp(prefix="mdp-")); self.addCleanup(shutil.rmtree, out, True)
        (out / "secret.png").write_bytes(tiny_png(77, 13))
        (self.v.root / ABC / "documents").mkdir(parents=True, exist_ok=True)
        (self.v.root / ABC / "documents" / "vault.png").write_bytes(tiny_png(66, 14))
        rel = "../" * 12 + str(out / "secret.png").lstrip("/")
        secs = [
          {"id": "health", "type": "health", "heading": "Health", "default_heading": "Health", "hidden": False,
           "text": f"Fine.\n\n![h]({out}/secret.png)", "data": {"flag": "On track"}},
          {"id": "summary", "type": "text", "heading": "Summary", "default_heading": "Summary", "hidden": False,
           "text": f"Words.\n\n![t]({rel})"},
          {"id": "current_state", "type": "panes", "heading": "Current state", "default_heading": "Current state", "hidden": False,
           "panes": [{"title": "Where", "text": "Booked.\n\n![p](documents/vault.png)"}]}]
        r = self.py("from pathlib import Path\nimport paths, docx_tools, zipfile, client_check\n"
                    f"doc = creaite_doc.new('client', 'ABC', 'Client report', '2026-10-16', {secs!r}, items={ITEMS!r}, audience='client')\n"
                    "o = Path(paths.DRAFTS) / 'md.docx'\nheld = None\ntry:\n    creaite_doc.word_export(doc, o)\n    held = 'NOT-HELD'\nexcept creaite_doc.DocError as e:\n    held = str(e)[:200]\nimport client_snapshot\ncreaite_doc.word_export(doc, o, token=client_snapshot.TOKEN)\nz = zipfile.ZipFile(o)\n"
                    "lo = client_check.left_out(doc)\n"
                    "print(json.dumps([sorted(list(docx_tools.image_size(z.read(n))) for n in z.namelist() if n.startswith('word/media/')),"
                    " lo.get('ready'), [f.get('message', f) if isinstance(f, dict) else f for f in lo.get('findings') or []][:5], held]))")
        print("\n### " + ("NOT-HELD direct client word_export: a client Word file was made without the checked copy" if r[3] == "NOT-HELD"
                         else "HELD direct client word_export: " + str(r[3])))
        print("### media sizes:", r[0], "| gate ready:", r[1], "findings:", r[2])
        print("### outside (77,13) embedded:", [77, 13] in r[0], "| vault doc (66,14) embedded:", [66, 14] in r[0])
if __name__ == "__main__":
    unittest.main(argv=["x", "P.test_md"], verbosity=0)
