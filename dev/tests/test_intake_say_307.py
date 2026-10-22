"""#307 (7, 8): Intake says things in plain words. Table-driven checks of core/say.js (the words helper), and a scan of the
Intake page's source for the engine's words in strings a person reads.

Run: python3 dev/tests/test_intake_say_307.py   (needs node)
"""
import json
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_plain_words as pw  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "system/templates/dashboard/src"
SAY = SRC / "core/say.js"

# The Intake page's code: every string a person reads there. (core/server.js is scanned by test_plain_words; its Intake-facing
# helpers applySoon and applyWords are checked below.)
FILES = ["review.js", "core/intakeApi.js", "core/say.js", "stores/minutes.js", "stores/intakeReview.js"] + \
        sorted(str(p.relative_to(SRC)) for p in (SRC / "components/intakeReview").glob("*"))
# Cap's list (#307): the engine's words a person must not read in Intake. Case-sensitive "Review" (the old page's name).
BANNED = {
    "staged": re.compile(r"\bstag(?:e|ed|es|ing)\b", re.I), "Review": re.compile(r"\bReview\b"),
    "proposal": re.compile(r"\bpropos(?:al|als|ed)\b", re.I), "apply": re.compile(r"\bappl(?:y|ies|ied|ying)\b", re.I),
    "tracker": re.compile(r"\btrackers?\b", re.I), "live server": re.compile(r"\blive server\b", re.I),
    "sweep": re.compile(r"\bsweep\b", re.I), "path": re.compile(r"(?<![\w.])(?:system|projects|inbox)/|\.vtt\b|\.json\b"),
}
# A message that names a keyboard command or a fixed Claude Code phrase is allowed to say "Claude Code", not the words above.


def say(msgs):
    code = ("import { plainSay as say, decidedWords, addFailed, needsConnection } from 'file://%s';\n"
            "const m = JSON.parse(process.argv[1]);\n"
            "process.stdout.write(JSON.stringify(m.map(x => x[0] === 'say' ? say(x[1]) : x[0] === 'decided' ? decidedWords(x[1]) : "
            "x[0] === 'fail' ? addFailed(x[1], x[2]) : needsConnection(x[1]))));") % SAY
    out = subprocess.run(["node", "--input-type=module", "-e", code, json.dumps(msgs)], capture_output=True, text=True)
    if out.returncode:
        raise AssertionError(out.stderr)
    return json.loads(out.stdout)


@unittest.skipUnless(shutil.which("node"), "needs node")
class SayWords(unittest.TestCase):
    def test_engine_messages_in_plain_words(self):
        rows = [
            ("The file is staged: the drafts are waiting in Review.", "The file is ready: the drafts are waiting in Intake."),
            ("All 3 files are ready: the drafts are waiting in Review.", "All 3 files are ready: the drafts are waiting in Intake."),
            ("Not staged: process it again, or ask creaite", "Nothing was drafted: process it again, or ask creaite"),
            ("0 of 1 staged for Review; 1 not staged.", "0 of 1 drafted; 1 not drafted."),
            ("2 of 3 waiting in Review; 1 couldn't be read", "2 of 3 drafted, ready to check in Intake; 1 couldn't be read"),
            ("Stopped: nothing was added to Review", "Stopped: nothing was drafted"),
            ("Discarded 1. Steering: set aside in system/staging/discarded/proposed-x.json; nothing was written to the tracker.",
             "Discarded 1. Steering: kept aside; nothing was saved."),
            ("Held: transcript no longer in the inbox (inbox/2026-10-22 call.vtt)", "Held: the transcript is no longer in Intake"),
            ("2 new items in Review", "2 new items to check in Intake"),
            ("Held in Review, not applied: x", "Held in Intake, not saved: x"),
            ("Approve the minutes without the transcript copy, or discard the proposal", "Approve the minutes without the transcript copy, or discard the suggestion"),
            ("Rejecting writes nothing to the tracker", "Rejecting writes nothing to your records"),
            ("Nothing to say here", "Nothing to say here"),
        ]
        got = say([["say", a] for a, _ in rows])
        for (a, want), g in zip(rows, got):
            self.assertEqual(g, want, a)

    def test_every_result_is_clean(self):
        raw = ["The file is staged: the drafts are waiting in Review.", "Not staged: process it again", "Discarded 1. x: set aside in system/staging/discarded/p.json; nothing was written to the tracker.",
               "Held: transcript no longer in the inbox (inbox/a.vtt)", "Held in Review, not applied: a", "Applied 1 proposal", "In Review: the live server stopped"]
        for g in say([["say", a] for a in raw]):
            for name, rx in BANNED.items():
                self.assertIsNone(rx.search(g), f"{name!r} left in {g!r}")

    def test_decided_words_name_the_kind_and_count(self):
        a, b, d, m = ({"kind": "actions", "op": "new"}, {"kind": "actions", "op": "new"}, {"kind": "decisions", "op": "new"}, {"kind": "draft", "rec": {"t": "Minutes: x"}})
        got = say([["decided", [{"r": a, "v": "approved"}]],                         # an ACTION is not "1 decision"
                   ["decided", [{"r": a, "v": "approved"}, {"r": b, "v": "approved"}, {"r": d, "v": "approved"}]],
                   ["decided", [{"r": m, "v": "rejected"}]],
                   ["decided", [{"r": {"kind": "raid"}, "v": "approved"}, {"r": a, "v": "rejected"}]],
                   ["decided", [{"r": {"kind": "actions", "op": "update"}, "v": "approved"}]]])
        self.assertEqual(got, ["Saved 1 action", "Saved 2 actions and 1 decision", "Rejected 1 set of minutes",
                               "Saved 1 risk or issue. Rejected 1 action", "Saved 1 update"])

    def test_add_failed_names_the_file_and_why(self):
        got = say([["fail", "notes.xlsx", "isn't a type Intake takes"], ["fail", "empty.vtt", "That file is empty."],
                   ["conn", "Checking"]])
        self.assertEqual(got[0], "notes.xlsx: isn't a type Intake takes")
        self.assertEqual(got[1], "empty.vtt: That file is empty")
        self.assertNotIn("live server", got[2])


class IntakeSourceWords(unittest.TestCase):
    """No string in the Intake page's code says a banned word to a person (a comment, a regular expression, a class name or a
    command passed to the server is not a string a person reads: test_plain_words' lexer skips them)."""

    def test_no_banned_word_in_what_a_person_reads(self):
        bad = []
        for f in FILES:
            for s, off in pw.js_strings((SRC / f).read_text()):
                if not pw.is_candidate(s, set()):
                    continue
                t = re.sub(r"<[^>]+>", "", s)
                for name, rx in BANNED.items():
                    if rx.search(t):
                        bad.append(f"{f}@{off} {name}: {s[:110]!r}")
        self.assertEqual(bad, [], "\n" + "\n".join(bad))


if __name__ == "__main__":
    unittest.main()
