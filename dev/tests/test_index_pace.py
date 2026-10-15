"""Plan item #95: the search index, built in a thread of the live server, gives the first page its turn.

Run: python3 dev/tests/test_index_pace.py
Each test builds a throwaway vault (test_tracker.Vault) and runs the real tracker.py there. Reading a PDF is pure Python and
holds the interpreter lock; without a pause after each file and page, a page built in the same process was about ten times slower
while a full index ran (2.6 to 3.1 s against 0.2 s in a 236-file vault). The tests count the pauses (exact) and check that the
command line is not slowed and the index is the same. The speed-up itself is not asserted here: it needs a vault of a couple of
hundred files and a loaded interpreter to show, and a timing check in a small throwaway vault did not reproduce it reliably.
"""
import json
import subprocess
import sys
import unittest
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_search import put  # noqa: E402
from test_tracker import ABC, Vault  # noqa: E402



def pdf_pages(n, words):
    """A valid PDF of n pages, each showing `words` (a long line of text, so that reading it takes real time)."""
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [" + b" ".join(f"{3 + 2 * i} 0 R".encode() for i in range(n)) + b"] /Count " + str(n).encode() + b" >>"]
    for i in range(n):
        shown = b"BT /F1 12 Tf 72 720 Td 14 TL " + b" ".join(b"(" + w + b") Tj T*" for w in words) + b" ET"
        data = zlib.compress(shown)
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 {3 + 2 * n} 0 R >> >> "
                    f"/Contents {4 + 2 * i} 0 R >>".encode())
        objs.append(b"<< /Length " + str(len(data)).encode() + b" /Filter /FlateDecode >>\nstream\n" + data + b"\nendstream")
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    out, offsets = bytearray(b"%PDF-1.4\n"), []
    for k, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += str(k).encode() + b" 0 obj\n" + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 " + str(len(objs) + 1).encode() + b"\n0000000000 65535 f \n" + b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer\n<< /Size " + str(len(objs) + 1).encode() + b" /Root 1 0 R >>\nstartxref\n" + str(xref).encode() + b"\n%%EOF\n"
    return bytes(out)


class Base(unittest.TestCase):
    PAGES = 12
    PDFS, REPEAT = 6, 12          # how many PDFs, and how many times the eight words repeat on each page

    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        words = [b"platform", b"migration", b"billing", b"customer", b"assistant", b"latency", b"milestone", b"vendor"] * self.REPEAT
        for i in range(self.PDFS):
            put(self.v, f"{ABC}/documents/Contract {i}.pdf", pdf_pages(self.PAGES, words))
        for i in range(10):
            put(self.v, f"{ABC}/documents/Plan {i}.md", f"# Plan {i}\n\nbilling migration plan {i}")

    def tearDown(self):
        self.v.cleanup()

    def py(self, code):
        """Run Python in the vault with tracker imported; returns stdout."""
        r = subprocess.run([sys.executable, "-c", "import sys, json, threading, time, os; sys.path.insert(0, 'system/scripts'); "
                            "import tracker\n" + code], cwd=self.v.root, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout


class PaceTests(Base):
    COUNT = ("naps = []\nreal = time.sleep\n"
             "def counted(s):\n    naps.append((s, threading.current_thread() is threading.main_thread()))\n    real(s)\n"
             "tracker.time.sleep = counted\n")

    def test_a_thread_pauses_after_each_file_and_each_pdf_page(self):
        got = self.py(self.COUNT + "t = threading.Thread(target=lambda: tracker.build_index(full=True)); t.start(); t.join()\n"
                      "print(json.dumps([len(naps), sorted({s for s, _ in naps}), any(m for _, m in naps)]))")
        count, lengths, on_main = json.loads(got)
        files = 6 + 10 + 0                     # the PDFs and the notes written above (the register and memory files add a few more)
        self.assertGreaterEqual(count, 6 * Base.PAGES + files)          # a pause per PDF page and one per file read
        self.assertEqual(lengths, [tracker_pace()])                # one short pause, never longer than the lock's own turn
        self.assertFalse(on_main)

    def test_the_command_line_is_never_slowed_and_the_result_is_the_same(self):
        main = self.py(self.COUNT + "tracker.build_index(full=True)\nprint(len(naps))")
        self.assertEqual(main.strip(), "0")                         # `tracker.py index` and an apply's refresh run on the main thread
        paced = json.loads(self.py("t = threading.Thread(target=lambda: tracker.build_index(full=True)); t.start(); t.join()\n"
                                   "import sqlite3\nc = sqlite3.connect('system/tracker.db')\n"
                                   "print(json.dumps(c.execute('SELECT path, length(content) FROM vault_search ORDER BY path').fetchall()))"))
        plain = json.loads(self.py("tracker.INDEX_PACE = 0\nt = threading.Thread(target=lambda: tracker.build_index(full=True)); t.start(); t.join()\n"
                                   "import sqlite3\nc = sqlite3.connect('system/tracker.db')\n"
                                   "print(json.dumps(c.execute('SELECT path, length(content) FROM vault_search ORDER BY path').fetchall()))"))
        self.assertEqual(paced, plain)
        self.assertGreater(len(paced), 10)


def tracker_pace():
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
    import tracker
    return tracker.INDEX_PACE


if __name__ == "__main__":
    unittest.main()
