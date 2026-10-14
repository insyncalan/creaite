"""BL-229 step 4 (v1.7.0): pin prep_page.context before it is split. It runs on test_prep_page_content's vault (the
prep world: decisions pending, late and to revisit, overdue and due-soon actions, weekly and client reports, a meeting
today called "ABC weekly") and its whole JSON is compared with the saved expectation in dev/tests/pinned/prep/.

The fixture's dates are relative to its modules' TODAY: here that is fixed (Friday 09-10-2026, as in test_steerco), and so
is the clock the scripts read (CREAITE_NOW), so the output is the same on every day. The vault path and the port are
normalised.

Run: python3 dev/tests/test_prep_context_pinned.py     (quick tier: no Chrome)
Record (only before the split, or for a reviewed change): CREAITE_PIN_RECORD=1 python3 dev/tests/test_prep_context_pinned.py
"""
import json
import os
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_prep_page_content as P  # noqa: E402  (its Vaulted fixture; none of its tests run here)
import test_dashboard  # noqa: E402
import test_decisions_prep  # noqa: E402

FIXED = date(2026, 10, 9)
for _m in (P, test_dashboard, test_decisions_prep):    # the fixture's dates are d(n) from each module's TODAY
    _m.TODAY = FIXED
os.environ["CREAITE_NOW"] = f"{FIXED} 08:30"           # and the scripts' clock (sweep.now, build_dashboard.now)

PINNED = Path(__file__).resolve().parent / "pinned" / "prep"
RECORD = os.environ.get("CREAITE_PIN_RECORD") == "1"
KEYS = {"abc_weekly": "09:00|ABC weekly", "not_in_the_calendar": "09:00|No such meeting"}


class Pinned(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        P.Vaulted.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def test_context(self):
        for name, key in KEYS.items():
            with self.subTest(name):
                r = self.v.run("context", key, script="prep_page.py", ok=False)
                out = r.stdout[r.stdout.index("{"):] if "{" in r.stdout else r.stdout
                data = json.loads(out)
                data.pop("port", None)                     # the live server's port: the machine's, not the context's
                text = json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False).replace(str(self.v.root.resolve()), "<VAULT>").replace(str(self.v.root), "<VAULT>")
                text = f"exit {r.returncode}\n" + text + "\n"
                f = PINNED / f"{name}.json"
                if RECORD:
                    PINNED.mkdir(parents=True, exist_ok=True)
                    f.write_text(text, encoding="utf-8")
                self.assertEqual(text, f.read_text(encoding="utf-8"), f"{name}: prep_page.context changed")


if __name__ == "__main__":
    unittest.main()
