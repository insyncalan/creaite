"""2.6.8 review (catastrophic backtracking): no calendar text, however many punctuation marks it holds, may slow the cleaning.

Run: python3 dev/tests/test_invite_clean_timing.py      (quick tier: plain code, about ten seconds)

An earlier version of the separator run (`[.,;!?]*SEP[.,;!?]*` inside a repeated group) took 14 s for "Password " + 32 dots and doubled per
mark. Now: 2000-character runs of '.', '. ', '.:', ':.', '…', ' . ', '!', '?', ',', ';', '..', '. . ' after EVERY label form of the
sweep, through scrub, invite_text (one line, a line then a value, <td> and <li> fragments) and the label-phrase patterns, each under
LIMIT seconds; and a seeded fuzz (seed 232) of random strings over punctuation, spaces, '-', ':' and a label word, up to 200 characters.
Every call also runs under a 5 second alarm, so a regression fails the test quickly instead of hanging the suite.
Mutant: the old nested form restored must trip the alarm.
"""
import importlib.util
import itertools
import random
import signal
import sys
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parents[1] / "system" / "scripts"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SCRIPTS))
import invite_clean as I  # noqa: E402
from test_invite_clean_sweep import FORMS  # noqa: E402

LIMIT = 0.2                 # seconds per call; the real figure is a few milliseconds, the margin is for a loaded CI machine
ALARM = 5.0
RUNS = [".", ". ", ".:", ":.", "…", " . ", "!", "?", ",", ";", "..", ". . "]


def timed(fn, *args):
    """(elapsed seconds, result); raises TimeoutError after ALARM seconds (the regex engine checks signals as it runs)."""
    def stop(*_a):
        raise TimeoutError("took more than %s s" % ALARM)
    old = signal.signal(signal.SIGALRM, stop)
    signal.setitimer(signal.ITIMER_REAL, ALARM)
    t0 = time.time()
    try:
        out = fn(*args)
        return time.time() - t0, out
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


def paths_of(mod, text, run):
    """The calls made for one label form and one run."""
    yield "scrub", mod.scrub, (text, 140)
    yield "invite_text line", mod.invite_text, ("Agenda\n" + text,)
    yield "invite_text then value", mod.invite_text, (text.split(run)[0] + "\nhunter\nEnd",)
    yield "td", mod.invite_text, ("<td>" + text + "</td><td>hunter</td>",)
    yield "li", mod.invite_text, ("<ul><li>" + text + "</li><li>hunter</li></ul>",)
    yield "is_secret", mod.is_secret, (text,)
    yield "open phrase", mod._BARE_OPEN.search, (text,)
    yield "end phrase", mod._BARE_END.search, (text,)
    yield "alone", mod._alone, (text,)


class Timing(unittest.TestCase):
    def test_long_runs_after_every_label(self):
        slow, n = [], 0
        for form, run in itertools.product(FORMS, RUNS):
            text = form + " " + (run * (2000 // len(run) + 1))[:2000]
            for name, fn, args in paths_of(I, text, run):
                took, _out = timed(fn, *args)
                n += 1
                if took > LIMIT:
                    slow.append((round(took, 3), name, form, run))
        self.assertGreater(n, 3000)
        self.assertEqual(slow[:6], [], f"{len(slow)} of {n} calls took more than {LIMIT} s")

    def test_seeded_fuzz(self):
        rnd = random.Random(232)
        alphabet = [".", ":", " ", "!", "?", ";", ",", "…", "-", "Password", "PIN", "Passcode", "Key", "Meeting ID", "reset", "\n", "<td>", "x"]
        slow = []
        for _ in range(1500):
            text = "".join(rnd.choice(alphabet) for _ in range(rnd.randint(20, 200)))[:200]
            for fn, args in ((I.scrub, (text, 140)), (I.invite_text, (text,))):
                took, _out = timed(fn, *args)
                if took > LIMIT:
                    slow.append((round(took, 3), text[:60]))
        self.assertEqual(slow[:5], [])

    def test_the_old_nested_form_trips_the_alarm(self):
        src = (SCRIPTS / "invite_clean.py").read_text(encoding="utf-8")
        old = 'SEPRUN = rf"[.,;!?]?{BARE_SEPARATORS}"'
        collapse = "    s = _SE_RUN.sub(_ellipsis, s)\n"
        self.assertIn(old, src)
        self.assertIn(collapse, src)
        nested = 'SEPRUN = rf"(?:[.,;!?]*{BARE_SEPARATORS}[.,;!?]*|\\.{{2,}}|(?:\\.\\s*){{3,}})"'
        spec = importlib.util.spec_from_loader("invite_clean_nested", loader=None)
        mod = importlib.util.module_from_spec(spec)
        mod.__file__ = str(SCRIPTS / "invite_clean.py")
        exec(compile(src.replace(old, nested, 1).replace(collapse, "", 1), "invite_clean_nested", "exec"), mod.__dict__)
        global ALARM
        keep, ALARM = ALARM, 2.0
        try:
            with self.assertRaises(TimeoutError):
                timed(mod.scrub, "Password " + "." * 34, 140)
        finally:
            ALARM = keep


if __name__ == "__main__":
    unittest.main()
