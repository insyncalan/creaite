"""#368b: a sent line written with link markup, markdown marks or table bars is found and cut (Python), and the page reads the same
(parity in test_sent_parity_368.py). Fictional names only. The client_leak.py proposal (dev/proposals/368/client_leak.py.diff) is
applied to a copy and checked through the live text check.

Run: python3 dev/tests/test_sent_links_368.py     (quick tier: no Chrome, no model)
"""
import json
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "system" / "scripts"))
import linktext  # noqa: E402
from test_tracker import Vault  # noqa: E402

DIFF = ROOT / "dev" / "proposals" / "368" / "client_leak.py.diff"
ROWS = {
    "link on the last word": "17-10-2026: Chased Sara by [email](https://example.com).",
    "link on the date": "[17-10-2026](https://example.com): Chased Sara by email.",
    "link on the verb": "17-10-2026: [Chased](https://example.com) Sara by email.",
    "link with an address the export refuses": "[17-10-2026](javascript:alert): Chased Sara by email.",
    "escaped hyphens": "17\\-10\\-2026: Chased Sara by email.",
    "emphasis inside the verb": "17-10-2026: Cha*sed* Sara by email.",
    "emphasis inside by": "17-10-2026: Chased Sara b*y* email.",
    "underscore and strike marks": "17-10-2026: C~~ha~~sed Sara b_y_ email.",
    "bold line": "**17-10-2026: Chased Sara by email.**",
    "table cells": "| 17-10-2026: | Chased Sara | by email |",
}
LOOK_ALIKE_BUT_NOT = [
    "[email](https://example.com) was sent by Sara on 17-10-2026",
    "17-10-2026 | Meeting | held by email thread",
    "Chased [Sara](https://example.com) by email yesterday",
    "snake_case and *emphasis* in a sentence about 17-10-2026",
    "| Item | Owner |\n| Chased | Sara |",
]


class Rows(unittest.TestCase):
    def test_every_row_is_found(self):
        for name, t in ROWS.items():
            self.assertTrue(linktext.sent_has(t), name)

    def test_every_row_is_cut_and_the_rest_kept(self):
        for name, t in ROWS.items():
            out = linktext.sent_strip("Keep [this](https://example.com)\n" + t + "\nand *this*")
            self.assertEqual(out, "Keep [this](https://example.com)\nand *this*", (name, out))

    def test_a_link_in_a_run_in_line_is_cut_whole(self):
        self.assertEqual(linktext.sent_strip("Waiting. [17-10-2026](https://example.com): Chased Sara by email."), "Waiting.")

    def test_look_alikes_are_left_alone(self):
        for t in LOOK_ALIKE_BUT_NOT:
            self.assertFalse(linktext.sent_has(t), t)
            self.assertEqual(linktext.sent_strip(t), t, t)

    def mutant(self, **patch):
        old = {k: getattr(linktext, k) for k in patch}
        for k, v in patch.items():
            setattr(linktext, k, v)
        try:
            return {n: linktext.sent_has(t) for n, t in ROWS.items()}
        finally:
            for k, v in old.items():
                setattr(linktext, k, v)

    def test_mutants_are_caught(self):
        got = self.mutant(_link_pieces=lambda plain: ([], []))
        self.assertFalse(got["link on the last word"] and got["link on the date"] and got["link on the verb"])
        self.assertFalse(got["link with an address the export refuses"])
        got = self.mutant(_MARKS="")
        self.assertFalse(got["escaped hyphens"] or got["emphasis inside the verb"] or got["emphasis inside by"])
        orig = linktext._sent_map
        got = self.mutant(_sent_map=lambda plain: orig(plain.replace("|", "x")))
        self.assertFalse(got["table cells"])


class Timing(unittest.TestCase):
    """The regexes stay linear: repeated tokens, a long text of one kind, ASCII and not."""
    BIG = ["é" * 500000 + "x" * 500000, "17-10-2026: chased " * 55000, "[a](https://example.com) " * 40000, "[" * 500000, "*_" * 500000,
           "| a " * 250000, "x" * 1000000, "17-10-2026: Chased Sara by [email](https://example.com) " * 15000, "\\" * 1000000, "[a](" * 250000]

    def test_python_is_fast_on_1mb(self):
        for t in self.BIG:
            t0 = time.time()
            linktext.sent_has(t)
            linktext.sent_strip(t)
            self.assertLess(time.time() - t0, 6, repr(t[:20]))

    def test_the_text_check_runs_each_form_once(self):
        t = "é" * 1000000
        t0 = time.time()
        for _ in range(3):
            linktext.sent_has(t)
        self.assertLess(time.time() - t0, 3)


@unittest.skipUnless(DIFF.exists(), "no proposal")
class PatchedTextCheck(unittest.TestCase):
    """client_leak.py.diff applied to a copy of main's client_leak.py, run through text_findings in a scratch vault."""

    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        cls.v.run("init")
        tmp = Path(tempfile.mkdtemp())
        (tmp / "system" / "scripts").mkdir(parents=True)
        shutil.copy(ROOT / "system" / "scripts" / "client_leak.py", tmp / "system" / "scripts" / "client_leak.py")
        r = subprocess.run(["git", "apply", str(DIFF)], cwd=tmp, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        cls.patched = (tmp / "system" / "scripts" / "client_leak.py").read_text()
        (Path(cls.v.root) / "system" / "scripts" / "client_leak.py").write_text(cls.patched)

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def run_check(self, texts):
        code = ("import sys, json, sqlite3, time\nsys.path.insert(0, 'system/scripts')\nimport client_leak\n"
                "con = sqlite3.connect('system/tracker.db'); con.row_factory = sqlite3.Row\n"
                "texts = json.loads(sys.stdin.read()); t0 = time.time()\n"
                "out = [client_leak.text_findings(con, 'ABC', t) for t in texts]\n"
                "print(json.dumps([out, time.time() - t0]))")
        r = subprocess.run([sys.executable, "-c", code], cwd=self.v.root, input=json.dumps(texts), capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def findings(self, texts):
        return self.run_check(texts)[0]

    def test_the_diff_adds_the_three_forms(self):
        self.assertIn("forms = {as_shown(text), text}", self.patched)
        self.assertIn("_context_findings(con, code, text, low, ids, raw)", self.patched)

    def test_every_row_gives_a_chase_log_finding(self):
        for t, found in zip(ROWS.values(), self.findings(list(ROWS.values()))):
            self.assertTrue([f for f in found if "chase log" in f], (t, found))

    def test_look_alikes_give_none(self):
        for t, found in zip(LOOK_ALIKE_BUT_NOT, self.findings(LOOK_ALIKE_BUT_NOT)):
            self.assertEqual([f for f in found if "chase log" in f], [], t)

    def test_one_megabyte_through_the_text_check_is_fast(self):
        for t in ("\u00e9" * 1000000, "17-10-2026: chased " * 55000):
            _, took = self.run_check([t])
            self.assertLess(took, 8, repr(t[:12]))        # the whole text check, three forms of the text each read once

if __name__ == "__main__":
    unittest.main()
