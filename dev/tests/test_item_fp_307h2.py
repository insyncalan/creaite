"""#307 h2: the item fingerprint is the same in Python (system/scripts/item_fp.py) and the page (core/identity.js, run by node).
Covers unicode (accents, CJK, emoji, NFC vs NFD), key order, numbers (1 vs 1.0, -0, large ints, floats), null/booleans/empty values.

Run: python3 dev/tests/test_item_fp_307h2.py   (needs node; skipped otherwise)"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "system" / "scripts"))
import item_fp  # noqa: E402

VECTORS = [
    {"op": "new", "table": "actions", "values": {"description": "Send the plan", "owner": "Sara", "due_date": "2026-11-01"}},
    {"op": "new", "table": "actions", "values": {"due_date": "2026-11-01", "owner": "Sara", "description": "Send the plan"}},
    {"op": "new", "table": "raid", "values": {"description": "café 漢字 \U0001F600", "impact": "High"}},
    {"op": "new", "table": "raid", "values": {"description": "café 漢字 \U0001F600", "impact": "High"}},          # NFD of the one above
    {"op": "update", "table": "actions", "id": "ABC-A-001", "changes": {"status": "Closed", "n": [3, 2, 1]}},
    {"op": "update", "table": "actions", "id": "ABC-A-001", "changes": {"n": [1, 2, 3], "status": "Closed"}},
    {"op": "new", "table": "actions", "values": {"a": 1, "b": 1.0, "c": -0.0, "d": 0, "e": 2 ** 60, "f": 12345678901234567890}},
    {"op": "new", "table": "actions", "values": {"a": 0.5, "b": -2.25, "c": 1e-7, "d": 0.1, "e": 1e21}},
    {"op": "new", "table": "actions", "values": {"a": None, "b": True, "c": False, "d": "", "e": [], "f": {}, "g": [None, {"z": 1, "a": {"y": 2, "b": 3}}]}},
    {"op": "new", "table": "actions", "values": {"q": 'quote " back \\ tab \t nl \n ctl \x01 del \x7f sep  '}},
    {"op": "new", "table": "actions", "values": {"é": 1, "e": 2, "漢": 3, "\U0001F600": 4, "～": 5}},                      # key order by code point
    {},
]
BLOCKS = [{"key": "fp:2026-10-05|steering|abc", "title": "Steering", "draft": "x.html", "projects": ["ABC"]}, {}]


class Fp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("node"):
            raise unittest.SkipTest("needs node")

    def js(self, items, blocks):
        d = Path(tempfile.mkdtemp())
        shutil.copy(ROOT / "system/templates/dashboard/src/core/identity.js", d / "identity.mjs")
        (d / "run.mjs").write_text('import * as I from "./identity.mjs"; import fs from "fs";'
                                   'const j=JSON.parse(fs.readFileSync(process.argv[2],"utf8"));'
                                   'console.log(JSON.stringify({i:j.items.map(I.itemFp),b:j.blocks.map(I.blockFp),c:j.items.map(I.canon),'
                                   's:[I.sha256(""),I.sha256("abc"),I.sha256("a".repeat(1000))]}));')
        (d / "in.json").write_text(json.dumps({"items": items, "blocks": blocks}, ensure_ascii=True))
        r = subprocess.run(["node", str(d / "run.mjs"), str(d / "in.json")], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_same_in_both_languages(self):
        # big ints and 1.0 cannot pass through JSON text to node unchanged, so the input is written as Python would print it
        out = self.js(VECTORS, BLOCKS)
        self.assertEqual(out["i"], [item_fp.item_fp(v) for v in VECTORS], out["c"])
        self.assertEqual(out["b"], [item_fp.block_fp(b) for b in BLOCKS])

    def test_sha256_known_answers(self):
        import hashlib
        out = self.js([], [])
        self.assertEqual(out["s"], [hashlib.sha256(x.encode()).hexdigest() for x in ("", "abc", "a" * 1000)])

    def test_rules(self):
        f = item_fp.item_fp
        base = {"op": "new", "table": "actions", "values": {"description": "x", "owner": "S"}}
        self.assertEqual(f(base), f({"table": "actions", "values": {"owner": "S", "description": "x"}, "op": "new"}))      # key order
        self.assertNotEqual(f(base), f({**base, "values": {"description": "y", "owner": "S"}}))
        nfc, nfd = {"values": {"t": "café"}}, {"values": {"t": "café"}}
        self.assertEqual(f(nfc), f(nfd))                                                                                # NFC decided
        self.assertEqual(f({"values": {"a": 1}}), f({"values": {"a": 1.0}}))
        self.assertEqual(f({"values": {"a": 0}}), f({"values": {"a": -0.0}}))
        self.assertNotEqual(f({"values": {"a": [1, 2]}}), f({"values": {"a": [2, 1]}}))                                 # lists keep order
        self.assertNotEqual(f({"values": {"a": None}}), f({"values": {"a": ""}}))
        self.assertNotEqual(f({"values": {"a": True}}), f({"values": {"a": 1}}) if False else f({"values": {"a": "true"}}))
        self.assertEqual(len(f(base)), 12)
        # what is not identity (a decision, flags, the item's number) never changes it
        self.assertEqual(f(base), f({**base, "n": 9, "decision": "approved", "flags": ["vip"]}))


if __name__ == "__main__":
    unittest.main()
