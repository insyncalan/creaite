"""#212: creaite 2.2.0's hand checks (dev/handchecks/v2.2.0.md), automated against a vault made from the release zip.

Run them all, fill the Results table and make the screenshot sheet:  python3 dev/tools/handcheck.py v2.2.0
Run this file on its own (it makes the vault itself):                 python3 dev/tests/handchecks/test_v220.py

One method per check, `test_cNN_…`, its docstring quoting the check. Numbering follows the Product Manager's sheet (39 checks).
Most of 2.2.0 already has its own tests in dev/tests (each check names them); those checks CALL the named tests instead of
repeating them: `run_named` runs the named tests in a fresh process (their own throwaway vault and server, never the live
vault, never Microsoft 365, the stand-in Claude), and the check passes when every one ran and passed, none skipped. Where the
sheet is about the hand-check vault itself (doctor, the Today headings, the rail's width, the report's room, the themes) the
check drives that vault. Classes:
  StartUp        1           doctor and the page errors (shared vault)
  HelpChecks     2 to 7      Help: search, ? panel, twelve jobs, What's new, the cards, the word count (7 is measured)
  TodayChecks    8 to 17     Today: the day band, popups, past days, weekends, commitments, Intake and Review, day roll, health bars
  RailChecks     18 to 21    the left side bar and the hover standard (19 is measured)
  EditorChecks   22 to 27, 29   Notes and the editors
  ReportChecks   28, 30, 31, 32   the report sheet, the banner (30 is measured), Health, Prep (own vault)
  SmallChecks    33 to 38    ask creaite, the sweep window, the board, one Esc, the run usage record
  Themes         39          the screenshot sheet (judgement)
Kinds: the sheet's own kinds, confirmed or changed as built (KIND below); a part of a check that only a person with the real
Claude, Word or Outlook can do is said in NOTES, because a LIVE_ONLY entry would replace the scripted Pass.
Desktop (1400 px) and 900 px only for the sheet (Alan, 15-10-2026).
"""
import ast
import json
import os
import re
import subprocess
import sys
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hcbase
import measure
from hcbase import NOTES, SCREENS, HandcheckCase

HERE = Path(__file__).resolve().parent
TESTS = HERE.parent
REPO = HERE.parents[2]

# The kind of each check, as built. The sheet's map is the starting point; the changes are noted beside the sets.
KIND = {**{n: "scriptable" for n in (*range(1, 7), *range(8, 19), *range(20, 30), 31, 32, *range(33, 39))},
        **{n: "measurable" for n in (7, 19, 30)},
        **{n: "judgement" for n in (39,)}}
# Changes from the sheet's map (the sheet's kind in brackets): 12 and 25 scriptable (judgement: tests exist on main); 31 scriptable
# with a screenshot (judgement); 28 scriptable with screenshots (judgement: its checklist tests exist); 36 and 37 scriptable
# (judgement: tests exist); 13 scriptable (the rename, position and fold are read from the page); 7 and 19 measured; 27 scriptable
# (live only: the paste into Outlook is the only hand part).

# A whole check that only a person can do. None in 2.2.0: every check has a scripted part. The hand parts are in NOTES.
LIVE_ONLY = {}
HAND_PARTS = {
    24: "the wording of a real suggestion needs the real Claude (the stand-in answers with a fixed reply)",
    27: "pasting the copied email into Outlook (table, colours, bold) can only be seen in Outlook; edit and Copy are scripted",
    28: "checklist boxes in Word need Word (the Word round trip is scripted); the toolbar's look is on the screenshot sheet",
    31: "the wording of a real health draft needs the real Claude; the evidence list and nothing-saved-until-accepted are scripted",
    35: "a real sweep needs real mail, Teams and calendar; the window and the cap are scripted",
}
for _n, _t in HAND_PARTS.items():
    NOTES.setdefault(_n, "hand part: " + _t)


# ── calling the tests the sheet names ────────────────────────────────────────

def _classes(path):
    """{class: (own test names, all test names including those inherited within the module)} for a test file."""
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    classes = {c.name: c for c in tree.body if isinstance(c, ast.ClassDef)}

    def own(c):
        return {f.name for f in c.body if isinstance(f, ast.FunctionDef) and f.name.startswith("test")}

    def every(c):
        found = set(own(c))
        for base in c.bases:
            if isinstance(base, ast.Name) and base.id in classes:
                found |= every(classes[base.id])
        return found
    return {name: (own(c), every(c)) for name, c in classes.items()}


def resolve(file, tokens):
    """The unittest ids (Class.method) for the tokens: a bare method name means every class that defines it; Class.method is
    checked (inheritance within the file counts). Returns (ids, problems)."""
    path = TESTS / f"{file}.py"
    if not path.exists():
        return [], [f"{file}.py is not on main"]
    classes = _classes(path)
    ids, problems = [], []
    for t in tokens:
        if "." in t:
            cls, name = t.split(".", 1)
            if cls in classes and name in classes[cls][1]:
                ids.append(t)
            else:
                problems.append(f"{file}::{t} is not on main")
        else:
            hits = [c for c, (own, _) in classes.items() if t in own]
            ids += [f"{c}.{t}" for c in hits]
            if not hits:
                problems.append(f"{file}::{t} is not on main")
    return ids, problems


def run_named(file, tokens, timeout=1500):
    """Run the named tests of dev/tests/<file>.py in a fresh process. Returns (ok, message, count). The process gets no CREAITE_*
    variable (the hand-check vault's pinned clock and port are not theirs); each test builds its own throwaway vault."""
    ids, problems = resolve(file, tokens)
    if problems:
        return False, "; ".join(problems), 0
    env = {k: v for k, v in os.environ.items() if not k.startswith("CREAITE_")}
    try:
        r = subprocess.run([sys.executable, str(TESTS / f"{file}.py"), *ids], cwd=REPO, env=env, capture_output=True, text=True,
                           timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, f"{file}: timed out after {timeout} s", len(ids)
    out = r.stdout + r.stderr
    ran = re.search(r"Ran (\d+) tests?", out)
    skipped = re.search(r"skipped=(\d+)", out)
    if r.returncode != 0:
        why = [ln for ln in out.splitlines() if ln.startswith(("FAIL:", "ERROR:", "AssertionError", "Error"))][:4]
        return False, f"{file}: " + " | ".join(why or out.strip().splitlines()[-3:]), len(ids)
    if skipped:
        return False, f"{file}: {skipped.group(1)} of the named tests were skipped (Chrome missing?)", len(ids)
    if not ran or int(ran.group(1)) != len(ids):
        return False, f"{file}: ran {ran.group(1) if ran else '?'} tests, expected {len(ids)}", len(ids)
    return True, "", len(ids)


class Named:
    """`self.named(n, file, *tokens, …)`: call the named tests; any number of (file, tokens) pairs via `named_many`."""

    def named(self, n, file, *tokens):
        self.named_many(n, (file, tokens))

    def named_many(self, n, *pairs):
        total, failed = 0, []
        for file, tokens in pairs:
            ok, msg, count = run_named(file, tokens)
            total += count
            if not ok:
                failed.append(msg)
        self.assertEqual(failed, [], "\n".join(failed))
        self.note(n, f"{total} existing tests called, all passed: " + ", ".join(f for f, _ in pairs))

    def note(self, n, text):
        NOTES[n] = "; ".join(x for x in (NOTES.get(n), text) if x)


class NamedCase(Named, unittest.TestCase):
    """A class of checks that only call named tests: no vault, server or Chrome of its own."""

    def setUp(self):
        n = int(self._testMethodName[6:8])
        if hcbase.only() and n not in hcbase.only():
            self.skipTest("not in --only")


class V220Case(Named, HandcheckCase):
    """A class that drives the hand-check vault itself (and may also call named tests)."""
    width, height = 1400, 1000

    def note(self, n, text):
        Named.note(self, n, text)

    def api(self, path, body=None):
        """POST to the live server as the page does (its token); the JSON answer."""
        token = self.b.eval("D.token")
        req = urllib.request.Request(self.base + path, data=json.dumps(body or {}).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": token})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            try:
                return json.loads(e.read().decode())
            except ValueError:
                return {"ok": False, "message": f"HTTP {e.code}"}


SCREENS.update({
    "reports": ("go('reports')", "!!document.querySelector('#v-reports tbody tr')"),
    "notes": ("go('notes','FAL')", "!!document.getElementById('notesNew')"),
    "weekly": ("go('weekly',{code:'FAL'})", "document.querySelector('#v-weekly section[data-id=current_state]')"),
})


# ── Start-up ─────────────────────────────────────────────────────────────────

class StartUp(V220Case):
    """Doctor and the page errors. The shared vault: nothing here changes data."""

    def test_c01_doctor(self):
        """1. `system/scripts/run doctor.py` → every check passes; visit every screen once → Settings › Diagnostics says "No
        errors in the last 7 days"."""
        code, out = self.run_in_vault("doctor.py")
        failed = [ln for ln in out.splitlines() if ln.startswith("FAIL")]
        self.assertEqual(failed, [], "\n".join(failed))
        self.assertEqual(code, 0, out[-500:])
        summary = re.search(r"(\d+) passed, (\d+) failed", out)
        b = self.b
        names = ["today", "work", "review", "intake", "files", "activity", "projects", "cockpit", "people", "help",
                 "settings-essentials", "settings-advanced", "settings-health", "reports", "notes"]
        for name in names:
            with self.subTest(name):
                self.screen(name)
        self.assertEqual(b.errors, [], "page errors")
        diag = b.eval("api('/api/diagnostics',{}).then(r=>r)")
        self.assertEqual((diag or {}).get("errors"), [], f"Diagnostics lists errors: {str((diag or {}).get('errors'))[:200]}")
        self.note(1, (summary.group(0) if summary else "doctor passed") + f"; {len(names)} screens, 0 page errors; Diagnostics clean")


# ── Help (#158, #176, #201) ──────────────────────────────────────────────────

class HelpChecks(V220Case):
    """Help's finding tests are called; check 7 reads the Help source the release carries."""

    def test_c02_help_search(self):
        """2. Help has one search: type a word, a plural and a word that is not there; press `/` in Help; ⌘K shows how-tos by
        title and the best three by line → results by part with the match marked; no result says "Nothing in Help for …" and
        offers ask creaite."""
        self.named(2, "test_help_finding", "test_search_finds_a_word_a_plural_and_nothing",
                   "test_slash_focuses_the_search_in_help_and_is_ask_creaite_elsewhere",
                   "test_cmdk_lists_how_tos_by_title_and_the_best_three_by_line")

    def test_c03_question_mark_panel_and_foot_line(self):
        """3. Press ? on a screen → a panel on the right lists two to five jobs for that screen; Esc closes it and returns
        focus; it never sits open beside ask creaite; a quiet "Press ? for help with …" line is at the foot of each of the eight
        screens."""
        self.named(3, "test_help_finding",
                   "test_the_question_mark_panel_opens_closes_with_esc_and_never_sits_with_ask_creaite",
                   "test_the_foot_line_is_on_the_eight_screens")

    def test_c04_home_of_twelve_jobs(self):
        """4. Help opens on a home of twelve jobs; each card opens its page."""
        self.named(4, "test_help_finding", "test_the_twelve_jobs_each_resolve_to_a_page",
                   "test_the_jobs_grid_and_every_screen_id_resolve_in_the_page")

    def test_c05_whats_new_tab(self):
        """5. A What's new tab, newest first, with the plain notes of every release; the installed version's notes are in it; a
        release without notes is refused."""
        self.named(5, "test_help_finding", "test_whats_new_is_a_fourth_tab_newest_first",
                   "test_the_installed_versions_notes_are_there", "test_a_release_without_its_notes_is_refused")
        # and in the hand-check vault itself: the tab is drawn, with this release's notes
        b = self.b
        self.screen("help")
        tabs = b.eval("[...document.querySelectorAll('#v-help [role=tab]')].map(t=>t.textContent.trim())")
        self.assertIn("What's new", tabs)
        self.note(5, "the vault's Help tabs: " + ", ".join(tabs))

    def test_c06_printed_cards(self):
        """6. The printed guides are now a one-page first-day card and a two-page top-12 card. (The look is judgement.)"""
        self.named(6, "test_help_finding", "test_the_first_day_card_is_the_loop_the_first_hour_and_the_four_rules",
                   "test_the_top_12_card_lists_the_twelve_jobs_with_their_page_names")

    def test_c07_reference_pages_shorter(self):
        """7. The big Reference pages read shorter; no page over about 600 words. Measured on the Help source in the vault, with
        help_acceptance's word count. Alan relaxed the target on 17-10-2026 (about 22,000 words for the Reference, trimming
        further in #176), so the Reference as a whole is held to that and the longest pages are reported."""
        import help_acceptance as ha
        text = (self.vault / "system/templates/help.md").read_text(encoding="utf-8")
        pages = ha.parse_pages(text)
        ref = sorted(((ha.words("\n".join(p["lines"]) + " " + p["title"]), p["title"]) for p in pages if p["part"] == "Reference"),
                     reverse=True)
        total = sum(n for n, _ in ref)
        self.assertLessEqual(total, 22000, f"the Reference is {total} words; Alan's relaxed target is about 22,000")
        self.assertLess(total, 24137, "the Reference is shorter than before the trim (24,137 words by the commit's count)")
        over = [f"{t} {n}" for n, t in ref if n > 600]
        self.note(7, f"Reference {total} words in {len(ref)} pages; the longest: " + ", ".join(f"{t} {n}" for n, t in ref[:3])
                  + f". {len(over)} pages are over 600 words: the sheet's 'no page over about 600' was set before Alan relaxed the "
                    "target on 17-10-2026 (about 22,000 for the Reference; trimming on in #176)")
