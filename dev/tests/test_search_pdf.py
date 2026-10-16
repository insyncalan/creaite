"""Tests for BL-275: readable PDFs in search, with the bundled pypdf (saved emails, BL-276, are in test_search_eml.py).

Run: python3 dev/tests/test_search_pdf.py
Each test builds a throwaway vault (test_tracker.Vault) and runs the real scripts there.
"""
import io
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_search import pdf, pdf_file, put  # noqa: E402
from test_tracker import ABC, Vault  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
VENDOR = REPO / "system" / "scripts" / "vendor"


def unicode_pdf(text):
    """A PDF like Word's or PowerPoint's: a Type0 font whose two-byte glyph codes mean nothing without its ToUnicode
    table, so the standard-library reader finds no text and pypdf finds it all."""
    chars = sorted(set(text))
    code = {c: 0x0100 + i for i, c in enumerate(chars)}
    shown = "".join(f"{code[c]:04X}" for c in text).encode()
    cmap = (b"/CIDInit /ProcSet findresource begin\n12 dict begin\nbegincmap\n"
            b"/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def\n/CMapName /Adobe-Identity-UCS def\n"
            b"/CMapType 2 def\n1 begincodespacerange\n<0000> <FFFF>\nendcodespacerange\n"
            + str(len(chars)).encode() + b" beginbfchar\n"
            + b"".join(f"<{code[c]:04X}> <{ord(c):04X}>\n".encode() for c in chars)
            + b"endbfchar\nendcmap\nCMapName currentdict /CMap defineresource pop\nend\nend")
    font = b"<< /Type /Font /Subtype /Type0 /BaseFont /Calibri /Encoding /Identity-H /DescendantFonts [6 0 R] /ToUnicode 7 0 R >>"
    cid = (b"<< /Type /Font /Subtype /CIDFontType2 /BaseFont /Calibri "
           b"/CIDSystemInfo << /Registry (Adobe) /Ordering (Identity) /Supplement 0 >> /DW 500 >>")
    tounicode = b"<< /Length " + str(len(cmap)).encode() + b" >>\nstream\n" + cmap + b"\nendstream"
    return pdf_file(b"BT /F1 12 Tf 72 720 Td <" + shown + b"> Tj ET", font=font, extra=(cid, tounicode))


def encrypted_pdf(text):
    """A password-protected copy of a plain PDF, made with the bundled pypdf (RC4, which needs no other library)."""
    sys.path.insert(0, str(VENDOR))
    try:
        import pypdf
    finally:
        sys.path.remove(str(VENDOR))
    w = pypdf.PdfWriter(clone_from=io.BytesIO(pdf(text)))
    w.encrypt("secret-pass", algorithm="RC4-128")
    out = io.BytesIO()
    w.write(out)
    return out.getvalue()


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.v.run("init")

    def tearDown(self):
        self.v.cleanup()

    def query(self, text):
        """The paths a search finds."""
        return [h["path"] for h in json.loads(self.v.run("query", text).stdout)]

    def py(self, code, *flags):
        """Run Python in the vault with tracker imported; returns stdout."""
        r = subprocess.run([sys.executable, *flags, "-c", "import sys, json; sys.path.insert(0, 'system/scripts'); "
                            "import tracker\n" + code], cwd=self.v.root, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def debug_on(self):
        """Turn the debug log's level to debug in this vault."""
        f = self.v.root / "system/config/settings.json"
        s = json.loads(f.read_text(encoding="utf-8"))
        s.setdefault("logging", {})["level"] = "debug"
        f.write_text(json.dumps(s), encoding="utf-8")

    def debug_log(self):
        """Everything in this vault's debug log."""
        return "".join(f.read_text(encoding="utf-8") for f in sorted((self.v.root / "system/logs").glob("debug-*.log")))


class PdfTests(Base):
    def test_a_word_style_pdf_is_found_by_its_body(self):
        put(self.v, f"{ABC}/documents/Exported deck.pdf", unicode_pdf("Quarterly hyperscaler capacity forecast"))
        put(self.v, f"{ABC}/documents/Plain.pdf", pdf("Uncompressed vendor onboarding checklist", compress=False))
        put(self.v, f"{ABC}/documents/Packed.pdf", pdf("Compressed sovereign tenancy memo"))
        self.assertIn("Indexed 3 file(s)", self.v.run("index").stdout)
        self.assertEqual(self.query("hyperscaler"), [f"{ABC}/documents/Exported deck.pdf"])     # ToUnicode fonts
        self.assertEqual(self.query("onboarding"), [f"{ABC}/documents/Plain.pdf"])              # BL-228's case
        self.assertEqual(self.query("tenancy"), [f"{ABC}/documents/Packed.pdf"])

    def test_encrypted_and_damaged_pdfs_are_indexed_by_name_with_a_debug_line(self):
        self.debug_on()
        put(self.v, f"{ABC}/documents/Locked.pdf", encrypted_pdf("Confidential settlement figures"))
        whole = pdf("Damaged appendix wording")
        put(self.v, f"{ABC}/documents/Damaged.pdf", whole[:len(whole) // 3])
        put(self.v, f"{ABC}/documents/Junk.pdf", b"%PDF-1.7\n\x00\x01\x02 not a pdf at all")
        r = self.v.run("index")
        self.assertIn("Indexed 3 file(s)", r.stdout)
        self.assertEqual(r.stderr.strip(), "")                                                  # pypdf stays quiet
        self.assertEqual(self.query("settlement"), [])
        self.assertEqual(self.query("Locked"), [f"{ABC}/documents/Locked.pdf"])
        self.assertEqual(self.query("Damaged"), [f"{ABC}/documents/Damaged.pdf"])
        log = self.debug_log()
        self.assertIn(f"PDF not read (encrypted, ValueError): {ABC}/documents/Locked.pdf", log)
        for word in ("settlement", "Confidential", "appendix", "secret-pass"):
            self.assertNotIn(word, log)                                                         # paths only, never text

    def test_without_pypdf_the_standard_library_reader_is_used(self):
        put(self.v, f"{ABC}/documents/Simple.pdf", pdf("Fallback reader works"))
        out = self.py("sys.modules['pypdf'] = None\nfrom pathlib import Path\n"
                      f"print(tracker.pdf_text(Path('{ABC}/documents/Simple.pdf')))")
        self.assertEqual(out.strip(), "Fallback reader works")

    def test_pypdf_loads_and_reads_with_no_optional_library(self):
        put(self.v, f"{ABC}/documents/Exported.pdf", unicode_pdf("Isolated import check"))
        block = ("import importlib.abc\nclass No(importlib.abc.MetaPathFinder):\n"
                 "    def find_spec(self, name, path=None, target=None):\n"
                 "        if name.split('.')[0] in ('cryptography', 'Crypto', 'PIL', 'fontTools', 'brotli', 'Brotli'):\n"
                 "            raise ImportError(name)\nsys.meta_path.insert(0, No())\nfrom pathlib import Path\n")
        out = self.py(block + f"print(tracker.pdf_text(Path('{ABC}/documents/Exported.pdf')))\n"
                      "import pypdf; print(pypdf.__file__.replace(chr(92), '/').split('/system/scripts/')[1])", "-I")
        self.assertEqual(out.split("\n")[:2], ["Isolated import check", "vendor/pypdf/__init__.py"])

    def test_a_scanned_pdf_with_no_text_layer_is_indexed_by_name(self):
        image_only = b"q 200 0 0 200 72 500 cm BI /W 2 /H 2 /CS /G /BPC 8 ID \x00\xff\xff\x00 EI Q"   # a scan: an image, no text
        put(self.v, f"{ABC}/documents/Scanned letter.pdf", pdf_file(image_only, compress=False))
        r = self.v.run("index")
        self.assertIn("Indexed 1 file(s)", r.stdout)
        self.assertEqual(r.stderr.strip(), "")
        self.assertEqual(self.query("Scanned"), [f"{ABC}/documents/Scanned letter.pdf"])
        out = self.py(f"from pathlib import Path\nprint(repr(tracker.pdf_text(Path('{ABC}/documents/Scanned letter.pdf'))))")
        self.assertEqual(out.strip(), "''")

    def test_a_long_pdf_is_read_only_up_to_the_limit(self):
        sys.path.insert(0, str(VENDOR))
        try:
            import pypdf
        finally:
            sys.path.remove(str(VENDOR))
        w = pypdf.PdfWriter()
        for n in range(6):
            w.add_page(pypdf.PdfReader(io.BytesIO(pdf(f"Page {n} of the procurement appendix wording"))).pages[0])
        out = io.BytesIO()
        w.write(out)
        put(self.v, f"{ABC}/documents/Long.pdf", out.getvalue())
        got = self.py("import pypdf\nfrom pathlib import Path\ncalls = []\nread = pypdf.PageObject.extract_text\n"
                      "pypdf.PageObject.extract_text = lambda self, *a, **k: calls.append(1) or read(self, *a, **k)\n"
                      f"t = tracker.pdf_text(Path('{ABC}/documents/Long.pdf'), limit=60)\n"
                      "print(json.dumps([len(t), len(calls), t.startswith('Page 0')]))")
        self.assertEqual(json.loads(got), [60, 2, True])                                        # cut, and pages 3 to 6 never read
        self.assertIn("Indexed 1 file(s)", self.v.run("index").stdout)
        self.assertEqual(self.query("procurement"), [f"{ABC}/documents/Long.pdf"])

    def test_an_online_only_pdf_is_never_read(self):
        put(self.v, f"{ABC}/documents/Away.pdf", pdf("Placeholder budget wording"))
        put(self.v, f"{ABC}/documents/Here.pdf", pdf("Local budget wording"))
        self.py("import paths\nfrom pathlib import Path\npaths.is_online_only = lambda p: Path(p).name == 'Away.pdf'\n"
                "read = tracker.pdf_text\n"
                "def guard(p, *a, **k):\n    assert p.name != 'Away.pdf', 'an online-only file was read'\n    return read(p, *a, **k)\n"
                "tracker.pdf_text = guard\nprint(tracker.build_index())")
        self.assertEqual(self.query("budget"), [f"{ABC}/documents/Here.pdf"])
        self.assertEqual(self.query("Away"), [])

    def test_the_index_is_rebuilt_once_for_the_new_readers(self):
        self.py("tracker.build_index()")
        stamp = self.v.root / "system/search/index-built.json"
        old = json.loads(stamp.read_text(encoding="utf-8"))
        self.assertEqual(old.get("readers"), 4)                                                 # v2.1.0 P1 after BL-275's 3
        for before in (3, 2, None):                                                                # an index from 1.9.0 to 1.9.2, or 1.8
            if before is None:
                old.pop("readers")
            else:
                old["readers"] = before
            stamp.write_text(json.dumps(old), encoding="utf-8")
            self.assertEqual(json.loads(self.py("print(json.dumps(tracker.index_state()))")), [True, "file readers changed"])
        self.py("tracker.build_index()")
        self.assertEqual(json.loads(self.py("print(json.dumps(tracker.index_state()))")), [False, ""])


class VendorTests(unittest.TestCase):
    def test_pypdf_and_its_dependency_are_in_the_manifest_and_match(self):
        sys.path.insert(0, str(REPO / "system" / "scripts"))
        import doctor
        self.assertEqual(doctor.vendor_problems(), ([], [], []))
        files = json.loads((VENDOR / "manifest.json").read_text(encoding="utf-8"))["files"]
        self.assertIn("pypdf/__init__.py", files)
        self.assertIn("typing_extensions.py", files)                                            # pypdf needs it on 3.9 and 3.10
        self.assertEqual((VENDOR / "pypdf" / "_version.py").read_text(encoding="utf-8").split('"')[1], "6.19.0")
        for lib in ("pypdf-6.19.0", "typing_extensions-4.15.0"):
            self.assertTrue((VENDOR / "licenses" / f"{lib}-LICENSE.txt").is_file(), lib)
        readme = (VENDOR / "README.md").read_text(encoding="utf-8")
        self.assertIn("pypdf", readme)
        self.assertIn("| typing_extensions 4.15.0", readme)
        self.assertIn("PSF-2.0", readme)                                                        # its licence, recorded
        self.assertEqual([f.name for f in (VENDOR / "licenses").glob("pypdf-*")], ["pypdf-6.19.0-LICENSE.txt"])

    def test_pypdf_is_pure_python(self):
        compiled = [f.name for f in (VENDOR / "pypdf").rglob("*") if f.suffix in (".so", ".pyd", ".dylib", ".c")]
        self.assertEqual(compiled, [])


if __name__ == "__main__":
    unittest.main()
