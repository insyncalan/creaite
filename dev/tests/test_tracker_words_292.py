"""#292 (2.6.4): plain wording in tracker.py's messages, the rows where no code reads the words (dev/proposals/292-tracker/README.md).

dev/proposals/292-tracker/tracker.diff and live_server.diff are put on a throwaway copy of the scripts when this tree lacks them, so the
test is the same either way. It checks, on that copy: every changed sentence is the new one and the old one is gone; every sentence
left for 2.6.5 (the ones the page, review.py or other guarded code read) is untouched; and three families come out of the real command
line in the new words. Mutant: the old words put back in one family turn the matching test red.

Run: python3 dev/tests/test_tracker_words_292.py
"""
import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import Vault, action  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / "dev/proposals/292-tracker"
TRACKER_HAS = "Nothing to save: no decided items." in (ROOT / "system/scripts/tracker.py").read_text()
SERVER_HAS = "Nothing to save: no decided items." in (ROOT / "system/scripts/live_server.py").read_text()

CHANGED = {                 # old sentence -> new sentence, in tracker.py
    "add it in Settings or with cx-edit first": "add it in Settings or ask creaite first",
    "path is outside the vault (": "path is outside your creaite folder (",
    "path must be relative to the vault root (": "path must be relative to your creaite folder (",
    "path is outside the vault and the projects folder (": "path is outside your creaite folder and the projects folder (",
    "is not in projects/, inbox/, system/staging/ or system/search/": "is not in a project folder, Intake, the waiting suggestions or the search index",
    "or decision in the tracker, so it can't carry a label": "or decision in your project record, so it can't carry a label",
    "is not in the tracker": "is not in your project record",
    "is not a project in the tracker": "is not a project in your project record",
    "new items carry no ID; tracker.py assigns it": "new items carry no ID; creaite gives them one",
    "(source or staging date)": "(the source's date or the date it was suggested)",
    "copy: the source must be a path in the vault or": "copy: the source must be a path in your creaite folder or",
    "a source is filed only from inbox/, staging drafts or uploads": "a source is filed only from Intake, your drafts or uploads",
    "copy: the source is outside the vault and": "copy: the source is outside your creaite folder and",
    "the file changed since it was staged": "the file changed since it was saved for review",
    "is not a file in inbox/": "is not a file in Intake",
    "move: path must be a stored projects/ path": "move: the path must be inside a project folder",
    "Nothing to apply: no decided items.": "Nothing to save: no decided items.",
    "is taken by a different file in this apply": "is taken by a different file in this save",
    "Left in staging, not applied:": "Left waiting, not saved:",
    "which isn't a new item written before it in this proposal": "which isn't a new item written before it in this suggestion",
    "(The database backup from before the apply is": "(The backup from before this save is",
    "Apply {apply_id} is the 1.5.0 migration": "Save {apply_id} is the 1.5.0 migration",
    "or cx-edit)": "or ask creaite)",
    "(apply {retired[0]}, in Activity)": "(save {retired[0]}, in Activity)",
    "pending proposal(s) still mention": "waiting suggestion(s) still mention",
    ". Apply or reject them first": ". Save or reject them first",
    "is a recode: applying it first, on its own. Run apply again for the other proposals.":
        "is a change of project code: saving it first, on its own. Save again for the other suggestions.",
}
LEFT = (                    # read by the page, review.py, live_server.py or other tests: 2.6.5, with the readers moved in the same step
    "Held in Review, not applied: ", "Apply stopped. Nothing was written.", "Apply failed; nothing was written.",
    "changed since this proposal was made", "a recode is applied on its own", ". Valid: ", "Usage: tracker.py undo-changes",
    "run tracker.py migrate.", "system/guard is a symlink", "Undid apply ", "Nothing applied: every decided item",
    "Apply {apply_id}: written", "after this proposal was made",
)


def vault_with_diffs():
    v = Vault()
    subprocess.run(["git", "init", "-q", str(v.root)], check=True)
    for diff, present in (("tracker.diff", TRACKER_HAS), ("live_server.diff", SERVER_HAS)):
        if not present:
            subprocess.run(["git", "apply", str(DIR / diff)], cwd=v.root, check=True)
    return v


class Words(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = vault_with_diffs()
        cls.tracker = (cls.v.root / "system/scripts/tracker.py").read_text()
        cls.server = (cls.v.root / "system/scripts/live_server.py").read_text()

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def test_every_changed_sentence_is_the_new_one_and_the_old_one_is_gone(self):
        for old, new in CHANGED.items():
            self.assertIn(new, self.tracker, new)
            quoted = [m for m in re.finditer(re.escape(old), self.tracker) if not self.tracker[:m.start()].rsplit("\n", 1)[-1].lstrip().startswith("#")]
            code = [m for m in quoted if not (new in self.tracker[max(0, m.start() - 80):m.end() + 80] and old in new)]
            self.assertEqual(code, [], f"old words still in a message: {old}")

    def test_the_server_says_the_same_nothing_to_save(self):
        self.assertIn('"message": "Nothing to save: no decided items."', self.server)
        self.assertNotIn("Nothing to apply: no decided items.", self.server)

    def test_the_sentences_other_code_reads_are_untouched(self):
        for words in LEFT:
            self.assertIn(words, self.tracker, words)


class CommandLine(unittest.TestCase):
    def fresh(self):
        v = vault_with_diffs()
        self.addCleanup(v.cleanup)
        v.run("init")
        return v

    def test_nothing_decided_says_nothing_to_save(self):
        r = self.fresh().run("apply")
        self.assertIn("Nothing to save: no decided items.", r.stdout)
        self.assertNotIn("Nothing to apply", r.stdout)

    def test_a_project_that_is_not_in_the_record_is_said_in_plain_words(self):
        v = self.fresh()
        v.propose("x", [action(1, project="XYZ", description="Order the licences")])
        r = v.run("apply", ok=False)
        self.assertIn("project XYZ is not in your project record", r.stdout + r.stderr)
        self.assertNotIn("in the tracker", r.stdout + r.stderr)

    def test_the_finishing_line_the_code_reads_is_unchanged(self):
        v = self.fresh()
        v.propose("y", [action(1, description="Order the licences")])
        r = v.run("apply")
        self.assertRegex(r.stdout, r"(?m)^Apply 1: written 1, filed 0, rejected 0")

    def test_mutant_the_old_words_put_back_turn_the_check_red(self):
        v = self.fresh()
        f = v.root / "system/scripts/tracker.py"
        f.write_text(f.read_text().replace("Nothing to save: no decided items.", "Nothing to apply: no decided items."))
        self.assertNotIn("Nothing to save", v.run("apply").stdout)
        t = f.read_text().replace("is not in your project record", "is not in the tracker")
        f.write_text(t)
        v.propose("z", [action(1, project="XYZ", description="Order the licences")])
        self.assertNotIn("in your project record", v.run("apply", ok=False).stdout)


if __name__ == "__main__":
    unittest.main(verbosity=1)
