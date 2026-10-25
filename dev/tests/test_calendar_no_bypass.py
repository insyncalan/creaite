"""#375 E1, slice S4: nothing reads the saved calendar except through calendar_gateway.

Run: python3 dev/tests/test_calendar_no_bypass.py      (quick tier: plain code)

Fails with the list of lines in system/scripts that open, load or read calendar.json (paths.CALENDAR or the file name) outside the files
allowed to: calendar_gateway.py (the one read path), invite_clean.py (legacy read_calendar until S5), sweep.py (S4: no longer) and live_server.py (stat only). Mutant: the test must see a bypass planted in a reader.
"""
import re
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "system" / "scripts"
ALLOWED = {"calendar_gateway.py", "invite_clean.py", "live_server.py"}    # sweep.py is NOT allowed (S4): its writers read via calendar_gateway.read_raw
# a read of the file's content: read_text/open/json.load on paths.CALENDAR, or an open of the literal name
READ = re.compile(r"(paths\.CALENDAR\s*\.\s*(read_text|read_bytes|open)\b|open\(\s*paths\.CALENDAR\b|json\.load\(\s*open\(\s*paths\.CALENDAR"
                  r"|(read_text|read_bytes|open)\([^)\n]*calendar\.json)")


def bypasses(root=SCRIPTS):
    found = []
    for f in sorted(root.glob("*.py")):
        if f.name in ALLOWED:
            continue
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if READ.search(line.split("#")[0]):
                found.append(f"{f.name}:{n}: {line.strip()}")
    return found


class NoBypass(unittest.TestCase):
    def test_no_reader_opens_calendar_json_itself(self):
        self.assertEqual(bypasses(), [], "read the calendar through calendar_gateway.read(<purpose>), not the file")

    def test_the_check_sees_a_planted_bypass(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "reader.py").write_text('import json\ndata = json.loads(paths.CALENDAR.read_text(encoding="utf-8"))\n', encoding="utf-8")
            self.assertEqual(len(bypasses(Path(d))), 1)

    def test_sweep_reads_the_calendar_only_through_the_gateway(self):
        text = (SCRIPTS / "sweep.py").read_text(encoding="utf-8")
        lines = [n for n, ln in enumerate(text.splitlines(), 1) if READ.search(ln.split("#")[0])]
        self.assertEqual(lines, [], f"sweep.py opens calendar.json itself: {lines}")
        self.assertIn("calendar_gateway.read_raw()", text)

    def test_sweep_writes_only_stamped_rows(self):
        """The one atomic write of calendar.json in sweep.py: the save (rows from stamp_rows) and the rescrub (_rescrubbed stamps)."""
        text = (SCRIPTS / "sweep.py").read_text(encoding="utf-8")
        writes = [ln.strip() for ln in text.splitlines() if "write_text_atomic(paths.CALENDAR" in ln]
        self.assertEqual(len(writes), 2, writes)
        self.assertIn("calendar_gateway.stamp_rows(days)", text)
        self.assertIn("shape[\"clean\"] = calendar_gateway.CLEAN", text)


if __name__ == "__main__":
    unittest.main()
