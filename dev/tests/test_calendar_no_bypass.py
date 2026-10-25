"""#375 E1, slice S4: nothing reads the saved calendar except through calendar_gateway.

Run: python3 dev/tests/test_calendar_no_bypass.py      (quick tier: plain code)

Fails with the list of lines in system/scripts that open, load or read calendar.json (paths.CALENDAR or the file name) outside the files
allowed to: calendar_gateway.py (the one read path), invite_clean.py (legacy read_calendar until S5), sweep.py (the writer: its save and
rescrub) and live_server.py (stat only). Mutant: the test must see a bypass planted in a reader.
"""
import re
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "system" / "scripts"
ALLOWED = {"calendar_gateway.py", "invite_clean.py", "sweep.py", "live_server.py"}
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

    def test_sweep_reads_only_in_its_writer_paths(self):
        lines = [n for n, ln in enumerate((SCRIPTS / "sweep.py").read_text(encoding="utf-8").splitlines(), 1) if READ.search(ln.split("#")[0])]
        self.assertLessEqual(len(lines), 2, f"sweep.py reads calendar.json outside its writer paths: {lines}")


if __name__ == "__main__":
    unittest.main()
