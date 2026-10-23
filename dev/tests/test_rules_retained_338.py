"""The retained-rules test for the slimmed creaite-rules.md (#338, #327 part C).

The rules file at origin/v262-line (and, where the two agree, the file after the 2.6.2 VIP/follow rules diff) is the standard. Below, in its
exact words:
  CORE     non-negotiables and "never" clauses that must still be in the IMPORTED rules, verbatim;
  REWORDED the original words and the shorter words that now carry the same rule in the imported rules (both checked);
  MAPPED   "never" clauses that describe what a record holds or how code enforces a rule: kept word for word in the reference file, with a
           pointer line that stays in the rules (the reason is stated);
  LINE_ONLY / CHAIN_ONLY  the VIP wording before and after the 2.6.2 follow rules diff.
Every "never" clause found in the original must be in one of these (or be a 6-word-or-longer clause present verbatim in the rules), so a
new clause cannot be dropped unnoticed. The slimmed rules come from the tree when the diff is applied, otherwise from a scratch copy with
dev/proposals/338/creaite-rules*.diff applied. Mutants: deleting the line that holds a rule, or turning "never" into "may", turns it red."""
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RULES = REPO / "system/creaite-rules.md"
REFERENCE = REPO / "system/templates/creaite-reference.md"
REF_PATH = "system/templates/creaite-reference.md"
DIFFS = [REPO / "dev/proposals/338/creaite-rules.diff", REPO / "dev/proposals/338/creaite-rules.after-chain.diff"]
CHAIN_MARK = "People you follow first"          # the 2.6.2 VIP/follow rules diff is in the file

CORE = [
    'stay in this folder on the laptop and never live in a synced folder',
    'a closed daily backup zip of what rebuilds the vault',
    "(never ask creaite's chats or their images, and never `vip.json`",
    'The live database, the git folder and the working files are never synced',
    'Never personal cloud storage, a web service or a published page.',
    'Nothing reaches `system/tracker.db` until Alan approves it.',
    'Unattended (scheduled) runs only write proposals to `system/staging/`.',
    'new risks, new decisions, milestone moves and health changes start unticked',
    'Files change only when Alan asks, and every change has a way back',
    'which are enforced in code it cannot change',
    'never by its prompt',
    'backed up first, logged and undoable',
    "a permission or settings file (including ask creaite's own)",
    'anything outside the vault and the projects folder',
    'a delete or a move',
    "another person's file (a transcript, sent minutes or a report, a client's document)",
    'more than ten files in one request',
    'anything but staging after it has read outside content',
    '**Decline** none',
    'bound to that exact change, used once, at most 30 minutes old',
    'ask creaite can ask for a change but never grant it',
    'ask creaite can never make it (#255; Alan, 20-10-2026)',
    'secrets (`~/.ssh`, `~/.aws`, keychains, password stores, browser profiles and saved logins)',
    'browser profiles and saved logins), the operating system, the places that run commands on their own',
    'the places that run commands on their own (shell start-up files, LaunchAgents, `.git`)',
    "the database, the engine, `creaite-rules.md`, `VERSION`, releases and creaite's own records",
    'remove a safety entry',
    'is refused whatever is approved',
    'Microsoft 365 actions stay off',
    'Only `system/scripts/tracker.py apply` writes to the database.',
    'Never edit `system/tracker.db` with ad-hoc SQL',
    'never write to `tracker-view.xlsx` except through `excel_sync.py export`',
    "never loosen `schema.sql` to make data fit without Alan's agreement",
    'Each item references its file, email or chat.',
    'Exclude anything marked confidential or restricted from client reports unless Alan says otherwise.',
    'do **not** run the session-start rules',
    'never connect to Microsoft 365 for real data',
    'Never use a skip-permissions mode',
    'ask creaite reads them, never changes them',
    'Runtime never pip installs',
    'Never store an absolute path',
    'Nothing is written unattended.',
    'Creating never overwrites',
    'Never an online-only OneDrive file',
    'Archiving (BL-10, BL-03) deletes nothing.',
    'bulk approval never covers minutes, new decisions or new risks',
    'ask creaite never drafts, stages or writes a report',
    'Lines marked `Client-safe: no` never appear in client reports',
    'no permission rule allows `launchctl`',
    'Only `minutes/` and `transcripts/` are ever extracted',
    "never a proposal or creaite's staging records",
    'never `permissions.py` or `propose.py setting`',
    'never from an ask creaite run',
    'Transcripts, agendas, documents and applied proposals are never archived.',
    'never overwriting',
    'nothing from `documents/` goes into a client report unless Alan explicitly says so',
    'Never in the development repository (`.creaite-dev`)',
    'never the text of mail, minutes, notes or chats',
    'One machine only: there is no multi-machine lock.',
    'never mix the two in one place',
    'show and accept dates as **DD-MM-YYYY**',
    '**Store** dates as **YYYY-MM-DD**',
    'Never changed by an update.',
    'Never sends, never creates email',
    'decisions, milestones and open items never are',
    'never copy tracker rows',
    'is moved here, never deleted',
    'creaite never depends on them',
    'Reminders (never draft on their own',
    'never in a client report; search',
    'recorded beside the note in `system/staging/notes-sent.json`, never in it',
    'never runs in the development repository',
    'logos stay in the git-ignored folder and never leave the laptop',
    'never `node`, never outside the vault',
    'are never scheduled',
    'It never touches the root `CLAUDE.md` or any data.',
    'a document changing never triggers anything',
    "refuses the never list (also inside a script's arguments)",
    'only the version he confirmed',
    'such a proposal could still remove or copy a note, undoably',
    "Only Alan's **Find updates** on a note turns its lines into tracker changes",
    'anything more ("sweep and apply", an image, a confirmed request) is a plain chat',
    '`propose.py stage` and any direct write outside `system/staging/drafts/`',
    "a note's pictures (`_images/`), a file in a subfolder of the notes folder and everything else in OneDrive still mark",
    'A note is not outside content (BL-301; Alan, 15-10-2026)',
    'they are for discussion only, nothing is extracted from them, and they are deleted with their chat',
    'skipped whatever the saved list says',
    'never edit it by hand',
    'macOS, the primary and only tested platform',
    'never by the model',
    'a confidential meeting keeps only its title and times, BL-98',
    'never drafts, stages or writes a report',
    'never extracted, internal by default)',
]

REWORDED = {'never extracted by the sweep or an unattended run': 'never extracted, never read by the sweep or an unattended run', "never overwrites a file creaite didn't write": "never overwrite a file creaite didn't write", 'The page is marked Internal and is never sent': 'are marked Internal and never sent', "the server's own write, never Claude's": 'written by the live server, never by Claude', 'Restoring a project leaves items archived for their age archived': 'restoring a project leaves items archived for their age archived', "with each invite's body as plain text": "`calendar.json` keeps each invite's body as plain text", "Alan's own Usage review notes": "`usage-reviews.jsonl` Alan's own notes", 'Windows: best effort, untested (Alan, 11-10-2026)': 'Windows** is best effort and untested (Alan, 11-10-2026)', 'never message text, BL-99': 'never message text, join links, passcodes or PINs'}

# clause -> (why it may live in the reference, the pointer text that stays in the rules; REF_PATH = the reference line in the header)
MAPPED = {
    'never (the table is in `dev/BUILD': ('mechanism text for reach.py, the live server or the launcher (enforced in code; summarised in the rules file)', 'system/templates/creaite-reference.md'),
    'never about a person)': ('a description of what a staging or log record contains (code writes it; the rule is the staging row in the rules file)', 'never message text, join links, passcodes or PINs'),
    'never any text, passcode or PIN, BL-42 phase 3), `intake-cleared': ('a description of what a staging or log record contains (code writes it; the rule is the staging row in the rules file)', 'never message text, join links, passcodes or PINs'),
    'never automatically)': ('a description of what a staging or log record contains (code writes it; the rule is the staging row in the rules file)', 'never message text, join links, passcodes or PINs'),
    "never by ask creaite or the page's own storage": ('a description of what a staging or log record contains (code writes it; the rule is the staging row in the rules file)', 'never message text, join links, passcodes or PINs'),
    'never ending in `original`), the older `<CODE>-partner': ('a description of what a staging or log record contains (code writes it; the rule is the staging row in the rules file)', 'never message text, join links, passcodes or PINs'),
    'never hidden |': ('a description of what a staging or log record contains (code writes it; the rule is the staging row in the rules file)', 'never message text, join links, passcodes or PINs'),
    'never in a release)': ('a description of what a staging or log record contains (code writes it; the rule is the staging row in the rules file)', 'never message text, join links, passcodes or PINs'),
    'never into)': ('a description of what a staging or log record contains (code writes it; the rule is the staging row in the rules file)', 'never message text, join links, passcodes or PINs'),
    'never join links or passcodes': ('a description of what a staging or log record contains (code writes it; the rule is the staging row in the rules file)', 'never message text, join links, passcodes or PINs'),
    'never list names macOS places (`Library/Keychains`, browser profiles under `Library/Application Support`) and would not protect `%APPDATA%`': ('mechanism text for reach.py, the live server or the launcher (enforced in code; summarised in the rules file)', 'system/templates/creaite-reference.md'),
    'never mid-job': ('mechanism text for reach.py, the live server or the launcher (enforced in code; summarised in the rules file)', 'system/templates/creaite-reference.md'),
    'never needed to run creaite)': ('mechanism text for reach.py, the live server or the launcher (enforced in code; summarised in the rules file)', 'system/templates/creaite-reference.md'),
    'never path in every argument form, an unquoted `#`, `**` or a `~` followed by anything but `/`, `reach': ('mechanism text for reach.py, the live server or the launcher (enforced in code; summarised in the rules file)', 'system/templates/creaite-reference.md'),
    'never raises': ('a description of what a staging or log record contains (code writes it; the rule is the staging row in the rules file)', 'never message text, join links, passcodes or PINs'),
    "never sends, called by the live server's route)": ('mechanism text for reach.py, the live server or the launcher (enforced in code; summarised in the rules file)', 'system/templates/creaite-reference.md'),
    'never stops by itself)': ('mechanism text for reach.py, the live server or the launcher (enforced in code; summarised in the rules file)', 'system/templates/creaite-reference.md'),
    'never text': ('a description of what a staging or log record contains (code writes it; the rule is the staging row in the rules file)', 'never message text, join links, passcodes or PINs'),
    'never text)': ('a description of what a staging or log record contains (code writes it; the rule is the staging row in the rules file)', 'never message text, join links, passcodes or PINs'),
    'never text), `agendas': ('a description of what a staging or log record contains (code writes it; the rule is the staging row in the rules file)', 'never message text, join links, passcodes or PINs'),
    'never text), `drafted': ('a description of what a staging or log record contains (code writes it; the rule is the staging row in the rules file)', 'never message text, join links, passcodes or PINs'),
    'never text), `notes-sent': ('a description of what a staging or log record contains (code writes it; the rule is the staging row in the rules file)', 'never message text, join links, passcodes or PINs'),
    'never text), `run-usage': ('a description of what a staging or log record contains (code writes it; the rule is the staging row in the rules file)', 'never message text, join links, passcodes or PINs'),
    "never the text of a prompt, a skill's arguments, a reply, a name or a path": ('a description of what a staging or log record contains (code writes it; the rule is the staging row in the rules file)', 'never message text, join links, passcodes or PINs'),
    'never the text or the name of a file': ('a description of what a staging or log record contains (code writes it; the rule is the staging row in the rules file)', 'never message text, join links, passcodes or PINs'),
    'never their text': ('a description of what a staging or log record contains (code writes it; the rule is the staging row in the rules file)', 'never message text, join links, passcodes or PINs'),
    'never` prints the never list)': ('mechanism text for reach.py, the live server or the launcher (enforced in code; summarised in the rules file)', 'system/templates/creaite-reference.md'),
}

FRAGMENTS = set(['Never', 'never are', 'never extracted', 'never in it', 'never list', 'never list)', 'never list, and changes files only through `filechange', 'never overwriting'])      # not rules by themselves: the bare word, "never list", or a clause the CORE phrases already hold whole

LINE_ONLY = [
    'never call or label a person a VIP, or say who is one, in anything creaite writes or may show or share',
    'VIPs still work unlabelled (their alerts, first in Review, the early warning)',
    'BL-288',
    'Never sends, never creates email drafts',
    'never call or label a person a VIP, or say who is one, in anything creaite writes or may show or share',
    'never creates email drafts',
]      # before the 2.6.2 follow rules diff

CHAIN_ONLY = [
    'Never use the word VIP, or any other label of importance',
    'and never say in any of them who is followed',
    'Hidden stays private to each laptop',
    'BL-288',
    'it never sends, updates or deletes one',
    'Never use the word VIP, or any other label of importance, in anything a client can see or that creaite writes, exports or shares',
    'never do it, and every other Microsoft 365 action stays refused',
    'never is (BL-288, revised',
    'never say in any of them who is followed',
    'never sends',
    'never sends, updates or deletes one, ask creaite can never do it, and every other Microsoft 365 action stays refused',
    'never shown, exported or shared (code, `vip',
]     # after it


def git_apply(text, diff, reverse=False):
    """`text` with `diff` applied (or reversed) on a scratch copy of system/creaite-rules.md; None if it does not apply."""
    d = Path(tempfile.mkdtemp(prefix="creaite-test-338-"))
    try:
        (d / "system").mkdir()
        (d / "system/creaite-rules.md").write_text(text, encoding="utf-8")
        cmd = ["git", "apply"] + (["-R"] if reverse else []) + [str(diff)]
        r = subprocess.run(cmd, cwd=d, capture_output=True, text=True)
        return (d / "system/creaite-rules.md").read_text(encoding="utf-8") if r.returncode == 0 else None
    finally:
        shutil.rmtree(d, ignore_errors=True)


def states():
    """(original, slim) for the tree's state, whichever way round the tree is."""
    tree = RULES.read_text(encoding="utf-8")
    if "creaite-reference.md" in tree:
        for diff in DIFFS:
            orig = git_apply(tree, diff, reverse=True)
            if orig is not None:
                return orig, tree
        raise AssertionError("the slimmed rules are in the tree but no 338 diff reverses on them")
    for diff in DIFFS:
        slim = git_apply(tree, diff)
        if slim is not None:
            return tree, slim
    raise AssertionError("no 338 diff applies to the tree's creaite-rules.md")


def never_clauses(text):
    """Every "never" clause: from the word to the next . ; : or line end."""
    out = set()
    for m in re.finditer(r"(?i)\bnever\b", text):
        end = next((i for i in range(m.end(), len(text)) if text[i] in ".;:\n"), len(text))
        out.add(text[m.start():end].strip(" ,"))
    return out


def missing(slim, reference, chain):
    """The rules that are no longer where they must be."""
    out = [p for p in CORE if p not in slim]
    out += [new for new in REWORDED.values() if new not in slim]
    for clause, (_why, pointer) in MAPPED.items():
        if pointer not in slim:
            out.append(pointer)
        if clause not in reference and clause_in_state(clause, chain):
            out.append(clause)
    out += [p for p in (CHAIN_ONLY if chain else LINE_ONLY) if p not in slim]
    return out


def clause_in_state(clause, chain):
    """Whether a MAPPED clause exists in the original of the tree's state (some are only in the post-chain wording)."""
    return True if chain else clause in STATE["orig"]


STATE = {"orig": ""}


def unaccounted(orig, slim):
    """Never clauses of the original that nothing above or the rules themselves hold."""
    fixture = CORE + CHAIN_ONLY + LINE_ONLY + list(REWORDED)
    bad = []
    for c in sorted(never_clauses(orig)):
        low = c.lower()
        if c in MAPPED or c in FRAGMENTS:
            continue
        if any((low in k.lower() or k.lower() in low) and len(k.split()) >= 3 for k in fixture):
            continue
        if len(c.split()) >= 6 and c in slim:
            continue
        bad.append(c)
    return bad


class RetainedRules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if shutil.which("git") is None:
            raise unittest.SkipTest("git is needed to apply the diff on a scratch copy")
        cls.orig, cls.slim = states()
        STATE["orig"] = cls.orig
        cls.chain = CHAIN_MARK in cls.orig
        cls.ref = REFERENCE.read_text(encoding="utf-8")

    def test_the_fixture_is_the_current_files_own_words(self):
        bad = [p for p in CORE + list(REWORDED) + (CHAIN_ONLY if self.chain else LINE_ONLY) if p not in self.orig]
        self.assertEqual(bad, [], "a fixture phrase is not in the unslimmed rules, so the fixture is wrong")

    def test_every_non_negotiable_and_never_is_still_there(self):
        self.assertEqual(missing(self.slim, self.ref, self.chain), [])

    def test_every_never_clause_of_the_original_is_accounted_for(self):
        self.assertEqual(unaccounted(self.orig, self.slim), [], "a never clause is in neither the fixture nor the imported rules")

    def test_mapped_clauses_are_not_rules_of_behaviour(self):
        for clause, (why, pointer) in MAPPED.items():
            self.assertTrue(why and pointer, clause)
            self.assertIn(pointer, self.slim, "no pointer line in the rules for: " + clause)
            if clause_in_state(clause, self.chain):
                self.assertIn(clause, self.ref, "a moved clause is not in the reference: " + clause)

    def test_the_non_negotiables_section_keeps_all_ten_bullets(self):
        sec = re.search(r"## Non-negotiables\n(.*?)\n## ", self.slim, re.S).group(1)
        for name in ("Local, with one exception", "Approval before writes", "ask creaite is the administrator", "Open:", "Sensitive, on one card",
                     "Never:", "One writer", "The schema is the rulebook", "Source on every row", "Confidential material"):
            self.assertIn("**" + name, sec)

    def test_the_rules_are_at_least_half_smaller(self):
        self.assertLessEqual(len(self.slim.encode()), 0.5 * len(self.orig.encode()), "the slimmed rules must be at most half the size")

    def test_the_rules_point_to_the_reference_and_it_says_it_never_loosens_them(self):
        self.assertIn(REF_PATH, self.slim)
        self.assertIn("never loosens `creaite-rules.md`", self.ref)

    def test_the_skills_table_and_dates_survive(self):
        rows = [ln for ln in self.slim.splitlines() if ln.startswith('| "')]
        self.assertGreaterEqual(len(rows), 12)                 # build_dashboard reads these rows
        self.assertIn("DD-MM-YYYY", self.slim)
        self.assertIn("YYYY-MM-DD", self.slim)

    def test_the_diffs_apply_forward_and_reverse(self):
        self.assertEqual(git_apply(self.orig, DIFFS[1 if self.chain else 0]), self.slim)
        self.assertEqual(git_apply(self.slim, DIFFS[1 if self.chain else 0], reverse=True), self.orig)

    def test_the_line_diff_adds_no_chain_wording(self):
        line_slim = git_apply(self.orig, DIFFS[0]) if not self.chain else None
        if line_slim is not None:
            for word in ("Follow check", "Create draft in Outlook", "People you follow"):
                self.assertNotIn(word, line_slim)

    def test_mutants_turn_it_red(self):
        count = 0
        for p in CORE + list(REWORDED.values()):
            kept = "".join(ln for ln in self.slim.splitlines(keepends=True) if p not in ln)
            self.assertIn(p, missing(kept, self.ref, self.chain), "deleting the line holding %r stays green" % p)
            weak = self.slim.replace(p, re.sub(r"(?i)\bnever\b", "may", p).replace("Only ", "Also "))
            if weak != self.slim:
                self.assertIn(p, missing(weak, self.ref, self.chain), "weakening %r stays green" % p)
            count += 1
        for _clause, (_why, pointer) in MAPPED.items():
            kept = "".join(ln for ln in self.slim.splitlines(keepends=True) if pointer not in ln)
            self.assertIn(pointer, missing(kept, self.ref, self.chain))
            count += 1
        self.assertGreater(count, 100)


if __name__ == "__main__":
    unittest.main()
