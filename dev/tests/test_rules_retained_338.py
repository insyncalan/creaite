"""The retained-rules test for the slimmed creaite-rules.md (#338, #327 part C).

Every non-negotiable and every "never" in the rules file at origin/v262-line is listed below with its exact words (taken from that file, and
from the file after the 2.6.2 VIP/follow rules diff where the two agree). Each must still be in the imported rules (CORE) or, for the long
mechanism text only, word for word in system/templates/creaite-reference.md (MOVED). The slimmed rules come from the tree when the diff is
already applied, otherwise from a scratch copy with dev/proposals/338/creaite-rules*.diff applied (the right one for the tree's state).
Mutants: removing the line that holds a rule, or turning its "never" into "may", turns the check red."""
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RULES = REPO / "system/creaite-rules.md"
REFERENCE = REPO / "system/templates/creaite-reference.md"
DIFFS = [REPO / "dev/proposals/338/creaite-rules.diff", REPO / "dev/proposals/338/creaite-rules.after-chain.diff"]
CHAIN_MARK = "People you follow first"          # the 2.6.2 VIP/follow rules diff is in the file

# Non-negotiables and the "never" clauses that must stay in the imported rules, exact words.
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
    'the operating system',
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
    'never by the model',
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
    'Never an online-only OneDrive file, `99 Archive` (or the old `_Archive`, `zz Archive`), `_Templates` or `99 System`',
    'Never changed by an update',
    'Never sends, never creates email',
    'never `node`, never outside the vault',
    'never are',
    "never by ask creaite), and back, only on the live server's own approval card",
    'never by copying files by hand',
    'never connect to Microsoft 365 for real data, and work from `dev/BUILD',
    'never copy tracker rows',
    'never covers minutes, reports, health changes, new decisions, a decision being recorded or withdrawn, or new risks',
    'never depends on them',
    'never draft on their own',
    'never dropped by project matching or an ignore rule',
    'never edit it in a live vault',
    'never extracted',
    'never extracted, never read by the sweep or an unattended run, never in a client report',
    'never from a process an ask creaite run started (`backup',
    'never in it',
    'never in the development repository',
    "never in the development repository, not when that day's backup or zip failed, and never from a process an ask creaite run started (`backup",
    'never list',
    'never list for everything else |',
    'never list)',
    'never list, so ask creaite cannot install, change or remove it, and no permission rule allows `launchctl`',
    "never one of Alan's notes, BL-301)",
    'never reads or downloads an online-only file, and `doctor',
    'never reads, writes or moves anything there',
    'never scheduled',
    'never sent',
    "never the newest of a kind, never in the development repository, not when that day's backup or zip failed, and never from a process an ask creaite run started (`backup",
    'never touches the root `CLAUDE',
    'never triggers anything',
    'never` prints the never list)',
]

# "never" clauses of mechanism text: moved word for word to the reference file (enforcement is in code, not in the prompt).
MOVED = [
    'never (the table is in `dev/BUILD',
    "never Claude's",
    "never a proposal or creaite's staging records), and any `Bash` that isn't one creaite script run on its own (and never `permissions",
    'never about a person)',
    'never any text, passcode or PIN, BL-42 phase 3), `intake-cleared',
    'never automatically)',
    "never by ask creaite or the page's own storage",
    'never by the model, is its own confirmation',
    'never deleted',
    'never drafts, stages or writes a report (reports are made and edited in the Reporting hub) | Specified |',
    'never edit it by hand |',
    'never ending in `original`), the older `<CODE>-partner',
    'never extracted by the sweep or an unattended run',
    'never extracted, internal by default), and search and ask creaite read them as they read documents',
    'never hidden |',
    'never in a release)',
    'never into)',
    'never join links or passcodes',
    'never leave the laptop',
    "never list (also inside a script's arguments), any direct `Edit` or `Write` outside `system/staging/drafts/` (`system/staging/` in a confirmed request",
    'never list names macOS places (`Library/Keychains`, browser profiles under `Library/Application Support`) and would not protect `%APPDATA%`',
    'never list, and changes files only through `filechange',
    'never message text',
    'never message text, BL-99',
    'never mid-job',
    'never needed to run creaite)',
    "never overwrites a file creaite didn't write or one Alan edited (those get a number), replaces creaite's own unchanged page for the same meeting and day after a copy to `system/backups/files/`, and records what it wrote in `system/staging/prep-pages",
    'never path in every argument form, an unquoted `#`, `**` or a `~` followed by anything but `/`, `reach',
    'never raises',
    'never runs in the development repository',
    'never stops by itself)',
    'never text',
    'never text)',
    'never text), `agendas',
    'never text), `notes-sent',
    'never text), `run-usage',
    "never the text of a prompt, a skill's arguments, a reply, a name or a path",
    'never the text or the name of a file',
]

LINE_ONLY = [
    'never call or label a person a VIP, or say who is one, in anything creaite writes or may show or share',
    'VIPs still work unlabelled (their alerts, first in Review, the early warning)',
    'BL-288',
]      # the VIP wording before the 2.6.2 follow rules diff

CHAIN_ONLY = [
    'Never use the word VIP, or any other label of importance',
    'and never say in any of them who is followed',
    'Hidden stays private to each laptop',
    'BL-288',
    'it never sends, updates or deletes one',
]     # the wording after it


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


def missing(slim, reference, chain):
    """The rules that are no longer where they must be: CORE in the rules, MOVED in the reference, the state's VIP wording in the rules."""
    out = [p for p in CORE if p not in slim]
    out += [p for p in MOVED if p not in reference]
    out += [p for p in (CHAIN_ONLY if chain else LINE_ONLY) if p not in slim]
    return out


class RetainedRules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if shutil.which("git") is None:
            raise unittest.SkipTest("git is needed to apply the diff on a scratch copy")
        cls.orig, cls.slim = states()
        cls.chain = CHAIN_MARK in cls.orig
        cls.ref = REFERENCE.read_text(encoding="utf-8")

    def test_the_fixture_is_the_current_files_own_words(self):
        bad = [p for p in CORE + MOVED + (CHAIN_ONLY if self.chain else LINE_ONLY) if p not in self.orig]
        self.assertEqual(bad, [], "a fixture phrase is not in the unslimmed rules, so the fixture is wrong")

    def test_every_non_negotiable_and_never_is_still_there(self):
        self.assertEqual(missing(self.slim, self.ref, self.chain), [])

    def test_the_non_negotiables_section_keeps_all_ten_bullets(self):
        sec = re.search(r"## Non-negotiables\n(.*?)\n## ", self.slim, re.S).group(1)
        for name in ("Local, with one exception", "Approval before writes", "ask creaite is the administrator", "Open:", "Sensitive, on one card",
                     "Never:", "One writer", "The schema is the rulebook", "Source on every row", "Confidential material"):
            self.assertIn("**" + name, sec)

    def test_the_rules_are_at_least_half_smaller(self):
        self.assertLessEqual(len(self.slim.encode()), 0.5 * len(self.orig.encode()), "the slimmed rules must be at most half the size")

    def test_the_rules_point_to_the_reference_and_it_says_it_never_loosens_them(self):
        self.assertIn("system/templates/creaite-reference.md", self.slim)
        self.assertIn("never loosens `creaite-rules.md`", self.ref)

    def test_the_skills_table_and_dates_survive(self):
        rows = [ln for ln in self.slim.splitlines() if ln.startswith('| "')]
        self.assertGreaterEqual(len(rows), 12)                 # build_dashboard reads these rows
        self.assertIn("DD-MM-YYYY", self.slim)
        self.assertIn("YYYY-MM-DD", self.slim)

    def test_the_diffs_apply_forward_and_reverse(self):
        self.assertEqual(git_apply(self.orig, DIFFS[1 if self.chain else 0]), self.slim)
        self.assertEqual(git_apply(self.slim, DIFFS[1 if self.chain else 0], reverse=True), self.orig)

    def test_mutants_turn_it_red(self):
        count = 0
        for p in CORE:
            lines = self.slim.splitlines(keepends=True)
            kept = "".join(ln for ln in lines if p not in ln)
            self.assertIn(p, missing(kept, self.ref, self.chain), "deleting the line holding %r stays green" % p)
            count += 1
            weak = self.slim.replace(p, re.sub(r"(?i)\bnever\b", "may", p).replace("Only ", "Also "))
            if weak != self.slim:
                self.assertIn(p, missing(weak, self.ref, self.chain), "weakening %r stays green" % p)
        for p in MOVED:
            self.assertIn(p, missing(self.slim, self.ref.replace(p, ""), self.chain), "deleting %r from the reference stays green" % p)
            count += 1
        self.assertGreater(count, 100)


if __name__ == "__main__":
    unittest.main()
