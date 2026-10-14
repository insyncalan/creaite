"""BL-229 step 4 (v1.7.0): pin docx_tools.fill_xml before it is split. 85 real calls, recorded while test_reports,
test_steerco, test_minutes_review and test_adhoc_docs ran (11 Word templates: minutes, weekly, client, steering and
one-off documents, with table rows, topic groups, paragraph lists, Markdown entries, empty lists and plain values), are
filled again and compared with the XML the code made before the split (dev/tests/pinned/fill_xml.json.gz).

Run: python3 dev/tests/test_fill_xml_pinned.py     (quick tier: no Chrome, no vault)
"""
import gzip
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "system" / "scripts"))
sys.path.insert(0, str(REPO / "system" / "scripts" / "vendor"))
import docx_tools  # noqa: E402

CORPUS = Path(__file__).resolve().parent / "pinned" / "fill_xml.json.gz"


class Pinned(unittest.TestCase):
    maxDiff = None

    def test_every_recorded_fill_is_unchanged(self):
        corpus = json.loads(gzip.decompress(CORPUS.read_bytes()))
        for n, case in enumerate(corpus["cases"]):
            with self.subTest(case=n, template=case["xml"]):
                got = docx_tools.fill_xml(corpus["templates"][case["xml"]], case["values"])
                self.assertEqual(got, case["expected"])
        self.assertEqual(len(corpus["cases"]), 85)


if __name__ == "__main__":
    unittest.main()
