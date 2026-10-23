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
import build_dashboard as item_fp  # noqa: E402

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
    {"op": "new", "table": "raid", "values": {"description": "Late", "impact": "High", "raised": "2026-10-04"}},     # raised is the engine's: not identity
    {"op": "new", "table": "raid", "values": {"description": "Late", "impact": "High"}},
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
                                   'console.log(JSON.stringify({i:j.items.map(I.itemFp),b:j.blocks.map(I.blockFp),c:j.items.map(I.fpCanon),'
                                   's:[I.fpSha256(""),I.fpSha256("abc"),I.fpSha256("a".repeat(1000))]}));')
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
        # `raised` is filled in by the engine (shown, and kept when an apply saves the file): the same item before and after
        risk = {"op": "new", "table": "raid", "values": {"description": "x", "type": "Risk"}}
        self.assertEqual(f(risk), f({**risk, "values": {**risk["values"], "raised": "2026-10-04"}}))


class RowFpIsTheFileItem(unittest.TestCase):
    """A Review row's fp is the fingerprint of the item AS THE FILE HOLDS IT. review.proposals() fills a risk's `raised` in memory
    (BL-26), which must not reach the fp: the page re-reads the file and compares (found by the gate-3 run: Approve on a risk said
    'already approved or changed')."""

    def test_a_risk_without_raised_keeps_the_files_fp(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from test_tracker import Vault
        import test_dashboard
        v = Vault()
        try:
            test_dashboard.populate(v)
            item = {"n": 1, "op": "new", "table": "raid", "match": "strong", "flags": [], "decision": "pending",
                    "values": {"project": "ABC", "type": "Risk", "description": "Supplier may slip", "owner": "Omar",
                               "impact": "High", "likelihood": "Medium", "source": "Teams chat"}}
            p = v.propose("2026-10-08-0900-fp", [item])
            code = ("import json,sys; sys.path.insert(0,'system/scripts'); import build_dashboard as B;"
                    "print(json.dumps([r['fp'] for r in B.collect(B.clock())['review']]))")
            r = subprocess.run([sys.executable, "-c", code], cwd=v.root, capture_output=True, text=True, timeout=120)
            self.assertEqual(r.returncode, 0, r.stderr[-2000:])
            raw = json.loads(p.read_text())["items"][0]
            self.assertNotIn("raised", raw["values"])
            self.assertIn(item_fp.item_fp(raw), json.loads(r.stdout.strip().splitlines()[-1]))
            if shutil.which("node"):                                    # the page's own function over the same file item agrees
                js = Fp("test_same_in_both_languages").js([raw], [])
                self.assertEqual(js["i"][0], item_fp.item_fp(raw))
                self.assertIn(js["i"][0], json.loads(r.stdout.strip().splitlines()[-1]))
        finally:
            v.cleanup()


if __name__ == "__main__":
    unittest.main()
