"""creaite 2.5.3's hand checks (Natasha's sheet, origin/pm-intake-briefs:dev/handchecks/drafts/v2.5.3-DRAFT.md, 23 checks), automated
against a vault made from the release zip (the fictional demo portfolio: Falcon Data Platform).

Run them all, fill the Results table and make the screenshot sheet:  python3 dev/tools/handcheck.py v2.5.3
Run this file on its own (it makes the vaults itself):               python3 dev/tests/handchecks/test_v253.py

One method per check, `test_cNN_...`, NN the sheet's number, its docstring quoting the check. Checks 24 to 32 are not on the sheet:
they are the other items 2.5.3 holds that the sheet leaves out (#264 Process, #265 Calendar refresh, #269 minutes stage, the apply
re-check of a client Word draft, #174 the report-named draft guard); the Product Manager can number them in.

How a check is wired:
  Wrapped253   1 to 5, 7, 10 to 13   run the feature's own tests, named in CHECKS (as test_v240.py does), each in a fresh process
               with its own throwaway vault. 1 to 5 are #259 (branch v253-client-k): until that branch is in the checkout their
               tests are not there and the checks skip, saying so.
  Notes253     8, 9, 14, 16, 17        UI in an own vault: Delete note, Undo, the "99 Archive" folder, a folder renamed by hand
  Guards253    15, 18, 22, 32          the guard and the settings, Review at 900 and 1440 px, the report-named draft guard
  Reviews253   20, 21                  Activity > Usage > Your reviews
  Stood253     23 to 31                a vault whose Claude is a stand-in answering the Process, calendar and draft runs (never a
                                       real model, never Microsoft 365): #272 (23), #264 (24 to 26), #265 (27 to 29), #269 (30), apply (31)
  6, 19 are live only (the real client logo; the real OneDrive archive folder).

Mutants: HC253_MUTANT=<name> breaks one thing in a throwaway vault's copy of the engine (never in the repository) before its
server starts; the check that guards it must then fail. `MUTANTS` below lists them. Fail-first proof, one at a time:
    HC253_MUTANT=archive-name python3 dev/tests/handchecks/test_v253.py Notes253.test_c14_new_archives_go_to_99_archive
Desktop (1400 px) and 900 px only.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))      # dev/tests, for the stand-ins this borrows
from test_v230 import V230Case
from hcbase import NOTES, only

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]

KIND = {n: "scriptable" for n in range(1, 33) if n not in (6, 19)}
LIVE_ONLY = {6: "a real client export with the real logo needs the real logo file and Word or the browser's print view",
             19: "the real company OneDrive archive folder, renamed once, with Alan"}
NOTES.update({
    24: "the stand-in Claude stages the files through the real minutes.py stage; a real model's reading is live only",
    27: "the stand-in Claude saves the calendar through the real sweep.py calendar; Microsoft 365 itself is live only",
    23: "the stand-in Claude answers the Suggest run; a real model's wording is live only",
})

FAL = "FAL Falcon Data Platform"

# name: (file in the vault, text it must hold once, what replaces it). Applied to the vault's copy, never to the repository.
MUTANTS = {
    # #252: new archives go to "_Archive" again
    "archive-name": ("system/scripts/paths.py", 'ARCHIVE = "99 Archive"', 'ARCHIVE = "_Archive"'),
    # #255: Delete note goes back to asking for the card (the page tries the old route first)
    "delete-card": ("system/templates/dashboard.html", 'api("/api/notes/delete/now", { path: n4.path, base })',
                    'api("/api/notes/delete", { path: n4.path, base })'),
    # #265: join links and passcodes are kept in the saved calendar
    "calendar-strip": ("system/scripts/sweep.py", '    body = invite_text(ev.get("body"))\n    if body:',
                       '    body = str(ev.get("body") or "")\n    if body:'),
    # #265: a confidential meeting keeps its place, organiser and body
    "calendar-confidential": ("system/scripts/sweep.py", '    if sens == "confidential":\n        row["sensitivity"] = "confidential"\n    elif not private:',
                              '    if False:\n        row["sensitivity"] = "confidential"\n    elif not private:'),
    # #269: minutes.py stage takes a transcript by a full path
    "stage-fullpath": ("system/scripts/minutes_spec.py", 's.startswith(("/", "~"))', 's.startswith(("~",))'),
    # #264: Process goes to a route that is not there (the page then fails the run)
    "process-route": ("system/templates/dashboard.html", 'fetch("/api/intake/process"', 'fetch("/api/intake/processx"'),
    # #265: Refresh goes to a route that is not there
    "refresh-route": ("system/templates/dashboard.html", 'fetch("/api/calendar/refresh"', 'fetch("/api/calendar/refreshx"'),
    # #259: an approved client draft changed afterwards is filed
    "client-apply": ("system/scripts/review.py", 'if blk.get("checked_sha256") != file_sha(draft):', 'if False:'),
    # #174: a report-named draft is let through the hook
    "guard-174": ("system/scripts/reach.py", "def report_named_draft_refusal(command):", "def report_named_draft_refusal(command):\n    return None"),
    # #272: a refusal reply is written into the field
    "suggest-nothing": ("system/scripts/drafts.py", "    if note:                                                # #272", "    if False:                                               # #272"),
    # #264: Process selected opens ask creaite even for a transcript already in Intake
    "process-opens-chat": ("system/templates/dashboard.html", "      let now = m5;\n      if (!m5.loaded) {", "      let now = m5;\n      openChat();\n      if (!m5.loaded) {"),
    # #252: Settings' Never read no longer lists 99 Archive
    "never-read": ("system/config/settings.json", '      "99 Archive",\n', ''),
    # #238: a review note is not written to the file
    "usage-save": ("system/scripts/usage_reviews.py", "    rec, why = clean(req)\n    if why:\n        return None, why\n    f = review_file(root)",
                   "    return load(root), None\n    rec, why = clean(req)\n    if why:\n        return None, why\n    f = review_file(root)"),
    # #238: the CSV carries a column the notes do not have
    "usage-csv": ("system/templates/dashboard.html", "r4.saw, r4.decided])]", "r4.saw, r4.decided, r4.path])]"),
    # #271: Review's tables go wider than the page again
    "review-sideways": ("system/templates/dashboard.html", "#reviewBody td.title{width:100%;max-width:0;overflow-wrap:anywhere}",
                        "#reviewBody td.title{width:auto}"),
}


def apply_mutant(vault):
    """HC253_MUTANT: break one thing in this vault's engine, and fail loudly if the text to break isn't there once."""
    name = os.environ.get("HC253_MUTANT", "")
    if not name:
        return
    rel, old, new = MUTANTS[name]
    if old is None:
        raise RuntimeError(f"mutant {name} is not defined yet")
    p = Path(vault) / rel
    text = p.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise RuntimeError(f"mutant {name}: {rel} holds the text to break {text.count(old)} times, not once")
    p.write_text(text.replace(old, new), encoding="utf-8")


# ── the feature's own tests, per check ───────────────────────────────────────

TESTS = HERE.parent
K = "test_client_output_k.py"            # #259: branch v253-client-k (not in v253-release yet)
PROPS = "test_client_output_properties.py"
ARCH = "test_archive_99.py"
NOCARD = "test_delete_note_no_card.py"
LOGS = "test_log_hygiene.py"

# check number: [(file in dev/tests, a test name or part of one)]; the check passes when each ran, none failed or was skipped
CHECKS = {
    1: [(K, "test_k2_a_section_flipped_to_client_on_disk_is_never_shown"), (K, "test_k2_any_other_section_added_on_disk_is_never_shown"),
        (K, "test_k2_control_a_client_text_section_saved_by_creaite_shows")],
    2: [(K, "test_k3_plain_words_sent_to_save_never_reach_a_client_file"), (K, "test_k3_plain_words_edited_on_disk_never_reach_a_client_file"),
        (PROPS, "test_P18_stored_fields_are_derived_and_items_are_the_facts")],
    3: [(PROPS, "test_P07_unknown_keys_at_any_depth"), (K, "test_k3_a_kept_item_holds_the_trackers_client_safe_facts")],
    4: [(K, "test_p16_spaced_short_and_long_item_ids_are_found"), (K, "test_p16_a_title_with_hyphens_or_dots_for_its_spaces_is_found"),
        (K, "test_p16_an_export_holding_such_a_form_is_refused")],
    5: [(K, "test_snapshot_export_renders_the_snapshot_not_the_file_read_again")],
    7: [("test_work_saved_cols_tolerant.py", "test_each_malformed_saved_layout_loads_every_tab"),
        ("test_work_saved_cols_tolerant.py", "test_a_change_on_a_missing_tab_saves_that_tab_alone")],
    10: [(NOCARD, "test_f_a_report_s_move_back_and_a_project_s_archive_keep_their_card"),
         (NOCARD, "test_a_the_same_move_staged_by_hand_is_never_applied"),
         ("test_card_only_moves.py", "test_c_a_hand_staged_report_move_back_is_refused")],
    11: [(NOCARD, "test_c_never_while_ask_creaite_has_read_outside_content"), (NOCARD, "test_b_ask_creaite_cant_move_or_delete_a_note_through_filechange"),
         ("test_notes_delete.py", "test_f_a_confidential_note_deletes_the_same_way")],
    12: [(LOGS, "test_a_route_error_logs_its_class_and_route_once_a_minute"), (LOGS, "test_an_apply_that_raises_logs_its_class_and_route_only"),
         (LOGS, "test_a_background_thread_error_logs_its_class_and_thread_once")],
    13: [(LOGS, "test_the_done_line_has_counts_and_no_names"), (LOGS, "test_a_failed_apply_logs_not_ok_and_never_its_message"),
         (LOGS, "test_no_call_passes_free_text")],
    14: [(ARCH, "test_a_project_archive_goes_to_99_archive_beside_an_old_folder"),
         (ARCH, "test_the_monthly_reports_move_goes_to_99_archive_and_leaves_a_file_already_in_an_old_one"),
         (ARCH, "test_delete_note_and_the_reports_move_write_only_to_99_archive")],
    15: [(ARCH, "test_archive_goes_to_99_archive_then_an_old_name_restore_works_with_undo"),
         (ARCH, "test_a_saved_list_without_the_old_names_still_skips_them"), (ARCH, "test_an_archived_project_resolves_under_each_name")],
    16: [(ARCH, "test_old_folders_stay_as_they_are_and_nothing_mentions_them"), (ARCH, "test_restore_follows_the_folder_wherever_it_is_called")],
    17: [(ARCH, "test_files_archived_lists_and_opens_every_file"), (ARCH, "test_old_stored_paths_resolve_into_the_renamed_folder")],
}
WAITS = {n: (K,) for n in (1, 2, 3, 4, 5)}


def run_ref(file, name):
    """One named test in a process of its own. (ok, note); the note says why not."""
    try:
        r = subprocess.run([sys.executable, "-m", "unittest", "-k", name, file[:-3]], cwd=TESTS, capture_output=True, text=True, timeout=900)
    except subprocess.TimeoutExpired:
        return False, f"{file}::{name}: timed out after 900 s"
    out = r.stdout + r.stderr
    ran = re.search(r"Ran (\d+) test", out)
    n = int(ran.group(1)) if ran else 0
    if r.returncode == 0 and n >= 1 and "skipped" not in out:
        return True, f"{n} test(s) in {file}"
    why = "skipped (no Chrome?)" if r.returncode == 0 and n >= 1 else next(
        (ln for ln in reversed(out.strip().splitlines()) if re.match(r"(\w*Error|AssertionError|FAILED|Error)", ln)), out.strip()[-200:])
    return False, f"{file}::{name}: {why}"[:300]


def named(case, refs, waits=()):
    """Run the tests a check names. Skips (saying why) when a file or test isn't in this checkout; fails when one fails."""
    for w in waits:
        if not (TESTS / w).exists():
            case.skipTest(f"waiting for the branch that brings {w} (#259, v253-client-k): not in this checkout")
    for f, name in refs:
        src = (TESTS / f).read_text(encoding="utf-8") if (TESTS / f).exists() else ""
        if f"def {name}" not in src:
            case.skipTest(f"{f}::{name} is not in this checkout")
    bad = [note for ok, note in (run_ref(f, name) for f, name in refs) if not ok]
    if bad:
        case.fail("; ".join(bad))
    return ", ".join(name for _, name in refs)



_SESSION = []


def hc_session():
    """The session the vaults of this module are made with: handcheck.py's folder and zip, or one made now (no shared vault)."""
    if _SESSION:
        return _SESSION[0]
    import handcheck
    if os.environ.get("CREAITE_HC_DIR"):
        s = handcheck.Session(os.environ["CREAITE_HC_DIR"])
        if os.environ.get("CREAITE_HC_ZIP"):
            s.zip = Path(os.environ["CREAITE_HC_ZIP"])
    else:
        s = handcheck.Session()
        unittest.addModuleCleanup(lambda: (s.close(), shutil.rmtree(s.dir, ignore_errors=True)))
    _SESSION.append(s)
    return s


class Case253(V230Case):
    """A vault of its own (made from the zip, with HC253_MUTANT applied) and, when the class names one, a stand-in Claude."""
    own_vault = True

    @classmethod
    def stand_in(cls, vault):
        """The path of the stand-in Claude for this class's server, or None for the hand-check vault's own."""
        return None

    @classmethod
    def start_server(cls):
        s = hc_session()
        cls._hc = s
        cls.vault = s.make_vault(f"vault-{cls.__name__}")
        cls.now = os.environ.get("CREAITE_HC_NOW") or s.now
        cls.v = None
        apply_mutant(cls.vault)
        cls.prepare(cls.vault)
        fake = cls.stand_in(cls.vault)
        orig = s.server_env
        if fake:
            s.server_env = lambda root, port: {**orig(root, port), "CREAITE_CLAUDE": str(fake)}
        try:
            cls.proc, cls.base = s.start_server(cls.vault)
        finally:
            if fake:
                del s.server_env

    @classmethod
    def prepare(cls, vault):
        """Put the class's files in the vault before its server starts."""

    @property
    def fal(self):
        return self.vault / "projects" / FAL

    def card(self):
        """The approval cards in ask creaite's log (titles)."""
        return self.b.eval("[...document.querySelectorAll('#chLog .edcard')].map(c=>c.querySelector('b').textContent)")

    def chat_shut(self):
        return not self.b.eval("document.getElementById('chat').classList.contains('on')")


# ── #255 and #252: notes and the archive folder ──────────────────────────────

class Notes253(Case253):
    """Checks 8, 9, 14, 16 and 17: Delete note moves a note into the project's archive at once, in "99 Archive"."""

    def make(self, code, title):
        b = self.b
        b.eval(f"go('notes',{json.dumps(code)})")
        b.wait("!!document.getElementById('notesNew')", 15)
        b.click("#notesNew")
        b.wait("document.getElementById('newNoteDlg').open")
        b.eval(f"(()=>{{ const i=document.getElementById('nnTitle'); i.value={json.dumps(title)}; i.dispatchEvent(new Event('input',{{bubbles:true}})); }})()")
        b.eval("document.querySelector('#newNoteDlg input[value=\"blank\"]').click()")
        b.click("#nnMake")
        b.wait("!document.getElementById('newNoteDlg').open", 10)
        b.wait(f"noteCur.value&&noteCur.value.note.title==={json.dumps(title)}&&!!document.querySelector('.nbody.ProseMirror')", 15)
        b.eval("noteFlush()")
        b.wait("noteSave.value.state==='saved'", 15)

    def delete_open_note(self, title):
        """Alan opens the note's … menu, chooses Delete note…, and presses Delete note in the box. Returns the toast's words."""
        b = self.b
        b.click(".nmorewrap .nmore")
        b.wait("!!document.querySelector('.nmorewrap [role=menu] .bad')")
        b.click(".nmorewrap [role=menu] .bad")
        b.wait("document.getElementById('noteDelDlg').open")
        self.assertEqual(b.eval("document.getElementById('ndelH').textContent"), f"Delete “{title}”?")
        b.click("#ndelGo")
        b.wait(f"!noteCur.value||noteCur.value.note.title!=={json.dumps(title)}", 20)
        b.wait("document.querySelector('.snack') && document.querySelector('.snack').textContent.includes('archive')", 10)
        return b.eval("document.querySelector('.snack').textContent")

    def wait_file(self, f, want=True):
        for _ in range(150):
            if f.exists() == want:
                break
            self.b.pump(0.1)
        return f.exists() == want

    def files_log(self):
        f = self.vault / "system/config/files-log.jsonl"
        return [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines()] if f.exists() else []

    def archived_row(self, title):
        """Files › Archived has refreshed and lists the deleted note: its row (name, stored path, place)."""
        b = self.b
        b.eval("go('files')")
        b.wait("!!document.getElementById('filesTbl')", 15)
        b.eval("refreshFiles(true)")
        b.wait(f"(D.files_archived||[]).some(f=>f.n==={json.dumps(title + '.md')})", 20)
        return b.eval(f"D.files_archived.find(f=>f.n==={json.dumps(title + '.md')})")

    def test_c08_delete_note_moves_it_at_once_with_no_card(self):
        """8. (#255) On the Notes tab, Delete note moves the note to the archive at once, with no approval card: Notes › a note's … menu ›
        Delete note…, then Delete note in the box; the note leaves the list and its folder, a toast says it moved to the archive,
        and ask creaite stays shut with no card in it."""
        b = self.b
        self.make("FAL", "Hand check delete")
        f = self.fal / "notes" / "Hand check delete.md"
        self.assertTrue(f.is_file())
        said = self.delete_open_note("Hand check delete")
        self.assertIn("Moved “Hand check delete” to the archive", said)
        self.assertEqual(self.card(), [], "no approval card")
        self.assertTrue(self.chat_shut(), "ask creaite stays shut")
        self.assertFalse(f.exists())
        self.assertNotIn("Hand check delete", b.eval("[...document.querySelectorAll('.nlist .ni b')].map(x=>x.textContent)"))
        self.note(8, "moved at once, no card")

    def test_c09_undo_brings_the_note_back_unchanged_and_the_delete_is_logged(self):
        """9. (#255) Undo brings the note back, unchanged; the delete is backed up and logged (it is Alan's own action, so it is not under
        Activity › What ask creaite changed): the same bytes and file date come back, and the files log has the delete and the Undo."""
        b = self.b
        self.make("FAL", "Hand check undo")
        f = self.fal / "notes" / "Hand check undo.md"
        before, mtime = f.read_bytes(), f.stat().st_mtime_ns
        self.delete_open_note("Hand check undo")
        moved = [r for r in self.files_log() if "Hand check undo" in json.dumps(r) and "note-archive" in json.dumps(r)]
        self.assertEqual(len(moved), 1, "the delete is in the files log")
        b.eval("[...document.querySelectorAll('.snack button')].find(x=>/Undo/.test(x.textContent)).click()")
        self.assertTrue(self.wait_file(f), "Undo puts the note back in its notes folder")
        self.assertEqual((f.read_bytes(), f.stat().st_mtime_ns), (before, mtime), "unchanged: its bytes and its date")
        for _ in range(50):
            if any("note-restored" in json.dumps(r) and "Hand check undo" in json.dumps(r) for r in self.files_log()):
                break
            b.pump(0.1)
        else:
            self.fail("the Undo is in the files log too")
        self.note(9, "bytes and date unchanged after Undo; delete and Undo both in the files log")

    def test_c14_new_archives_go_to_99_archive(self):
        """14. (#252) A deleted note goes to a folder named "99 Archive" inside the project's folder, even where the project already holds
        an old `_Archive` folder (which keeps what it had, and gets nothing new); a project archive and the report archive go to
        `99 Archive` too (the feature's own tests, run beside)."""
        old = self.fal / "_Archive" / "notes"
        old.mkdir(parents=True, exist_ok=True)
        (old / "Earlier note.md").write_text("An earlier release archived this.\n", encoding="utf-8")
        self.make("FAL", "Hand check archive")
        self.delete_open_note("Hand check archive")
        self.assertTrue((self.fal / "99 Archive" / "notes" / "Hand check archive.md").is_file(), "in 99 Archive")
        self.assertFalse((old / "Hand check archive.md").exists(), "not in _Archive")
        self.assertEqual(sorted(p.name for p in old.iterdir()), ["Earlier note.md"], "the old folder is as it was")
        named(self, CHECKS[14])
        self.note(14, "99 Archive/notes got the note; _Archive/notes untouched; project and report archives by the feature's tests")

    def test_c16_nothing_moves_by_itself_and_a_folder_renamed_by_hand_is_followed(self):
        """16. (#252) There is no rename offer and no migration: Health says nothing about archive folders, an old-named folder stays as it
        is, and when Alan renames a `99 Archive` folder to `_Archive` by hand, Files › Archived still lists the note and Move back puts
        it back at once with no card."""
        b = self.b
        orx = self.vault / "projects" / "ORX Orbit Customer App"
        (self.fal / "zz Archive").mkdir(parents=True, exist_ok=True)
        (self.fal / "zz Archive" / "Old report.md").write_text("kept as it is\n", encoding="utf-8")
        self.make("ORX", "Renamed archive note")
        self.delete_open_note("Renamed archive note")
        arch = orx / "99 Archive"
        self.assertTrue((arch / "notes" / "Renamed archive note.md").is_file())
        arch.rename(orx / "_Archive")
        self.screen("settings-health")
        b.pump(1.0)
        health = b.eval("document.getElementById('healthCard').innerText.toLowerCase()")
        for word in ("rename", "zz archive", "_archive"):
            self.assertNotIn(word, health, f"Health says nothing about archive folders ({word})")
        self.assertEqual([p.name for p in (self.fal / "zz Archive").iterdir()], ["Old report.md"], "nothing moved by itself")
        self.archived_row("Renamed archive note")
        b.eval("document.querySelector('#fquick [data-q=\"archived\"]').click()")
        sel = "#filesTbl [data-moveback$='/Renamed archive note.md']"
        b.wait(f"!!document.querySelector({json.dumps(sel)})", 15)
        b.eval(f"document.querySelector({json.dumps(sel)}).click()")
        f = orx / "notes" / "Renamed archive note.md"
        self.assertTrue(self.wait_file(f), "Move back brings the note back from the renamed folder")
        self.assertEqual(self.card(), [], "no approval card")
        named(self, CHECKS[16])
        self.note(16, "no rename offer in Health; old folder untouched; Move back out of the hand-renamed _Archive")

    def test_c17_stored_paths_are_unchanged_and_files_finds_the_archived_note(self):
        """17. (#252) Stored paths stay `projects/<folder>/…`: Files › Archived lists a deleted note under its project's folder, and
        that stored path resolves to the file inside `99 Archive`."""
        self.make("FAL", "Hand check stored")
        self.delete_open_note("Hand check stored")
        row = self.archived_row("Hand check stored")
        self.assertTrue(row["path"].startswith("projects/FAL Falcon Data Platform/"), row)
        where = self.py(f"import paths\nprint(json.dumps(paths.rel(paths.resolve({row['at']!r}))))")
        self.assertEqual(where, "projects/FAL Falcon Data Platform/99 Archive/notes/Hand check stored.md")
        self.assertTrue((self.vault / where).is_file())
        named(self, CHECKS[17])
        self.note(17, "Files lists it under projects/FAL…; resolve gives 99 Archive/notes")


# ── #252 the guard, #174 the report-named draft guard, #271 Review ───────────

class Guards253(Case253):
    """Checks 15, 18, 22 and 32: nothing here changes data; the vault is made once for the four."""

    def hook(self, command, mode="ask"):
        """The guard hook as an ask creaite run calls it (reach.py hook); (exit code, what it said). 2 is a refusal."""
        r = subprocess.run([str(self.vault / "system/scripts/run"), "reach.py", "hook", "--run", "hc253", "--mode", mode],
                           cwd=self.vault, capture_output=True, text=True, timeout=60,
                           input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command}}),
                           env={**os.environ, "CREAITE_NOW": self.now or ""})
        return r.returncode, r.stderr + r.stdout

    def test_c15_old_archive_names_are_still_read_and_skipped_and_restore_works(self):
        """15. (#252) An existing `_Archive` or `zz Archive` folder is still treated as an archive for one release: ask creaite is refused a
        file in any of the three archive folders (so it is never read or indexed), a folder merely named like one is ordinary, and a
        restore from either old name works (the feature's own tests, run beside)."""
        for name in ("99 Archive", "_Archive", "zz Archive"):
            code, out = self.run_in_vault("reach.py", "classify", f"projects/{FAL}/{name}/notes/Old.md", "read")
            self.assertNotEqual(code, 0, f"{name}: refused")
            self.assertIn(f"{name} is never read or written by creaite", out)
        for name in ("99 Archivement", "Archive"):
            code, out = self.run_in_vault("reach.py", "classify", f"projects/{FAL}/{name}/notes/Old.md", "read")
            self.assertEqual(code, 0, f"{name}: an ordinary folder ({out})")
            self.assertEqual(json.loads(out)["kind"], "ordinary")
        named(self, CHECKS[15])
        self.note(15, "all three archive names refused to ask creaite, look-alikes ordinary; restore from an old name by the feature's tests")

    def test_c18_the_default_never_read_list_and_health_know_the_new_name(self):
        """18. (#252) Settings › Advanced › Never read lists `99 Archive` (and still the two old names), and Health, with an old-named
        archive folder in a project, raises no problem about it."""
        self.screen("settings-advanced")
        shown = self.b.eval("document.getElementById('set-more').innerText")
        for name in ("99 Archive", "_Archive", "zz Archive"):
            self.assertIn(name, shown, f"Never read lists {name}")
        listed = json.loads((self.vault / "system/config/settings.json").read_text(encoding="utf-8"))["locations"]["never_index"]
        self.assertIn("99 Archive", listed)
        (self.fal / "zz Archive").mkdir(parents=True, exist_ok=True)
        code, out = self.run_in_vault("doctor.py")
        self.assertNotIn("zz Archive", out, "doctor makes no complaint about an old archive name")
        self.screen("settings-health")
        self.b.pump(1.0)
        health = self.b.eval("document.getElementById('healthCard').innerText")
        self.assertNotIn("zz Archive", health)
        self.assertNotIn("_Archive", health)
        self.note(18, "Never read shows 99 Archive; no archive-name problem in Health or doctor")

    def test_c32_a_report_named_draft_is_refused_to_ask_creaite_and_an_ordinary_one_is_not(self):
        """32. (#174) In an ask creaite chat, a Word draft named like a report (weekly, client or report in the title or file name) is
        refused through every builder (report.py adhoc and weekly-stage, docx_tools.py fill), however it is typed; "reports are the user's
        to edit" is the reason. An ordinary document (open risks, minutes) goes through."""
        d = self.vault / "system/staging/drafts"
        d.mkdir(parents=True, exist_ok=True)
        (d / "hc-weekly.json").write_text(json.dumps({"title": "Falcon Data Platform Weekly report"}), encoding="utf-8")
        (d / "hc-risks.json").write_text(json.dumps({"title": "Open risks register"}), encoding="utf-8")
        run = "system/scripts/run"
        refused = [f"{run} report.py adhoc system/staging/drafts/hc-weekly.json",
                   f"{run} report.py weekly-stage system/staging/drafts/hc-risks.json",
                   "python3 system/scripts/report.py client-stage system/staging/drafts/hc-risks.json",
                   f"{run} docx_tools.py fill system/templates/minutes-template.docx system/staging/drafts/v.json "
                   "'system/staging/drafts/2026-10-21 Falcon Weekly report.docx'"]
        for cmd in refused:
            code, out = self.hook(cmd)
            self.assertEqual(code, 2, f"{cmd} should be refused ({out})")
            self.assertIn("reports are the user's to edit", out, cmd)
        for cmd in (f"{run} report.py adhoc system/staging/drafts/hc-risks.json",
                    f"{run} docx_tools.py fill system/templates/minutes-template.docx system/staging/drafts/v.json "
                    "'system/staging/drafts/2026-10-21 Falcon Steering minutes.docx'"):
            code, out = self.hook(cmd)
            self.assertEqual(code, 0, f"{cmd} should go through ({out})")
        self.note(32, "4 report-named builders refused with the reason; 2 ordinary documents let through")

    def test_c22_review_never_scrolls_sideways_with_an_expanded_item(self):
        """22. (#271) Review, a minutes row opened with its "n items" toggle, a child item with a very long source and a reject guess: at
        900 px and at 1440 px the page and the tables do not scroll sideways, no "more columns" cue shows, the meta line ends in an ellipsis
        with the full source in its tip, and Approve, Reject and Project stay visible and clickable."""
        import test_review_no_sideways as nsw
        b = self.b
        for width in (900, 1440):
            b.resize(width, 900)
            b.eval("go('review')")
            b.wait("!!document.querySelector('#reviewBody tr.mparent')", 20)
            self.assertGreater(b.eval(nsw.MAKE_LONG), 0, "no minutes row with items to expand")
            b.pump(0.6)
            s = b.eval(nsw.STATE)
            self.assertFalse(s["pageOver"], f"{width}: the page scrolls sideways")
            self.assertEqual(s["over"], 0, f"{width}: a Review table is wider than its frame")
            self.assertEqual(s["cue"], 0, f"{width}: the 'more columns' cue shows")
            kids = [r for r in s["rows"] if r["child"]]
            self.assertTrue(kids, "expanded items")
            for r in s["rows"]:
                self.assertTrue(r["approve"] and r["reject"] and r["project"], f"{width}: {r}")
            for r in kids:
                self.assertTrue(r["clipped"] and r["ellipsis"] and r["full"], f"{width}: the long meta line truncates with its full text in the tip: {r}")
        self.note(22, "no sideways scroll at 900 and 1440 with long sources expanded")


# ── the stand-in Claude ──────────────────────────────────────────────────────

# The calendar the stand-in "reads" (made-up people; a join link, meeting ID, passcode and dial-in in the first invite, and a confidential
# meeting with a body of its own)
INVITE_BODY = ("Agenda: budget and the pilot plan\\nJoin here https://teams.microsoft.com/l/meetup-join/19%3ameeting_abc\\n"
               "Meeting ID: 812 3456 7890\\nPasscode: 4321\\nDial-in +44 20 7946 0000,,998877#")
EVENTS = """{today: [
    {"id": "ev-r1", "start": "23:00", "end": "23:30", "title": "Pilot readiness review", "where": "Microsoft Teams Meeting", "teams": True,
     "organiser": "Jane Doe", "sensitivity": "normal", "body": "%s", "attendees": ["Sam Lee"]},
    {"id": "ev-r2", "start": "23:30", "end": "23:45", "title": "Supplier checkpoint", "where": "Room 2", "teams": False,
     "organiser": "Jane Doe", "sensitivity": "normal"},
    {"id": "ev-r3", "start": "23:45", "end": "23:55", "title": "Board strategy session", "where": "Room 9", "teams": True,
     "organiser": "Jane Doe", "sensitivity": "confidential", "body": "Secret agenda https://zoom.us/j/1?pwd=abc",
     "attendees": ["Sam Lee"]}]}""" % INVITE_BODY

DISPATCH = r'''#!/usr/bin/env python3
import os, sys
a = sys.argv[1:]
settings = a[a.index("--settings") + 1] if "--settings" in a else ""
here = os.path.dirname(os.path.abspath(__file__))
if "--mode process" in settings:
    target = "fake_process.py"
elif "--mode calendar" in settings:
    target = "fake_calendar.py"
elif os.path.exists(os.path.join(here, "fake_draft.py.reply")):
    target = "fake_draft.py"
else:
    target = "fake_plain.py"
os.execv(sys.executable, [sys.executable, os.path.join(here, target), *a])
'''

PLAIN = r'''#!/usr/bin/env python3
import json
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init", "session_id": "sess-p"})
out({"type": "assistant", "message": {"content": [{"type": "text", "text": "Plain chat."}]}})
out({"type": "result", "result": "Plain chat.", "session_id": "sess-p"})
'''


def write_stand_in(vault, today):
    """The stand-in Claude in `vault`: one dispatcher over the Process, calendar and draft stand-ins the feature tests use (borrowed
    from them so they stay one thing), pointed at the demo's Falcon project and today's date. Returns the dispatcher's path."""
    from test_calendar_refresh import FAKE as CALENDAR
    from test_intake_process import FAKE as PROCESS
    from test_suggest_nothing_272 import FAKE as DRAFT
    process = PROCESS.replace('"ABC"', '"FAL"').replace("ABC-A-001", "FAL-A-001").replace("2026-10-20", today)
    start, end = CALENDAR.index('{"days": {today: ['), CALENDAR.index('"sensitivity": "normal"}]}}') + len('"sensitivity": "normal"}]}}')
    calendar = CALENDAR[:start] + '{"days": ' + EVENTS + "}" + CALENDAR[end:]
    for name, text in (("fake_process.py", process), ("fake_calendar.py", calendar), ("fake_draft.py", DRAFT), ("fake_plain.py", PLAIN),
                       ("fake_claude.py", DISPATCH)):
        f = Path(vault) / name
        f.write_text(text, encoding="utf-8")
        f.chmod(0o755)
    return Path(vault) / "fake_claude.py"


VTT = """WEBVTT

NOTE
Title: {title}

00:00:01.000 --> 00:00:06.000
<v Alan Carter>Let's go through the {title}.</v>

00:00:06.000 --> 00:00:12.000
<v Jane Doe>We agreed the pilot starts on 2 November.</v>

00:00:12.000 --> 00:00:18.000
<v Omar Haddad>I'll send the readiness checklist by Friday.</v>
"""


class Stood253(Case253):
    """Checks 23 to 31: a vault whose Claude is a stand-in that answers Intake's Process, Calendar import's Refresh and Suggest the way
    the feature tests' stand-ins do. Each check sets up what it needs and does not rely on the order."""

    @classmethod
    def stand_in(cls, vault):
        return write_stand_in(vault, cls._hc.today.isoformat())

    @classmethod
    def prepare(cls, vault):
        cfg = Path(vault) / "system/config/settings.json"
        data = json.loads(cfg.read_text(encoding="utf-8"))
        data.setdefault("vip", {})["check_minutes"] = 100000
        cfg.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    @property
    def day(self):
        return self.now[:10]

    def put_inbox(self, name, title=None):
        f = self.vault / "inbox" / name
        f.parent.mkdir(exist_ok=True)
        f.write_text(VTT.format(title=title or Path(name).stem[11:]), encoding="utf-8")
        return f

    def open_intake(self):
        b = self.b
        b.reload("typeof go==='function' && LIVE")
        b.eval("go('inbox')")
        b.wait("!!document.getElementById('inboxGo')", 15)

    def state(self, name):
        return self.b.eval(f"(()=>{{ const tr=[...document.querySelectorAll('#inboxTbl tr[data-inf]')].find(t=>t.dataset.inf.endsWith({name!r})); "
                           "return tr?tr.cells[6].innerText.trim():''; })()")

    def select_files(self, pattern):
        self.b.eval(f"INSEL.clear(); D.inbox.filter(f=>/{pattern}/.test(f.name)).forEach(f=>INSEL.add(f.path)); renderInbox()")

    # ── #264 Process ──

    def test_c24_process_stages_the_ticked_intake_files_and_ask_creaite_stays_shut(self):
        """24. (#264) Intake › Upload files: tick two transcripts and press Process: each row says "Draft ready in Review" and both
        meetings are in Review, with no go-ahead card and without ask creaite opening."""
        b = self.b
        self.put_inbox(f"{self.day} Pilot readiness review.vtt")
        self.put_inbox(f"{self.day} Supplier checkpoint.vtt")
        self.open_intake()
        self.select_files("Pilot readiness|Supplier checkpoint")
        self.assertEqual(b.eval("document.getElementById('inboxGo').textContent"), "Process 2 selected")
        b.click("#inboxGo")
        b.wait("[...document.querySelectorAll('#inboxTbl tr[data-inf]')].filter(t=>/Pilot readiness|Supplier checkpoint/.test(t.dataset.inf)"
               "&&/Draft ready/.test(t.cells[6].innerText)).length===2", timeout=90)
        self.assertTrue(self.chat_shut(), "ask creaite stays shut")
        self.assertEqual(b.eval("document.querySelectorAll('#chLog .confirm').length"), 0, "no go-ahead card")
        self.assertIsNone(b.eval("RUN"))
        b.eval("go('review')")
        b.wait("document.body.innerText.includes('Pilot readiness review')&&document.body.innerText.includes('Supplier checkpoint')", 20)
        self.note(24, "two files staged, Draft ready on both rows, panel shut")

    def test_c25_a_question_the_run_cannot_answer_is_on_its_row_and_ask_creaite_opens_only_when_asked(self):
        """25. (#264) A transcript the run cannot place: its row says "Needs you" with the question ("Which project is this meeting
        for?"); ask creaite does not open or get a message until Alan presses "Ask creaite about this", which only fills in the question."""
        b = self.b
        self.put_inbox(f"{self.day} Unclear call.vtt")
        self.open_intake()
        self.select_files("Unclear")
        b.click("#inboxGo")
        b.wait("[...document.querySelectorAll('#inboxTbl tr[data-inf]')].some(t=>/Needs you/.test(t.cells[6].innerText))", timeout=90)
        self.assertIn("Which project is this meeting for?", self.state("Unclear call.vtt"))
        self.assertTrue(self.chat_shut())
        self.assertFalse(b.eval("(document.getElementById('chIn')||{}).value||''"), "nothing typed for Alan yet")
        b.eval("[...document.querySelectorAll('#inboxTbl tr[data-inf]')].find(t=>/Unclear/.test(t.dataset.inf)).querySelector('[data-inask]').click()")
        b.wait("(document.getElementById('chIn')||{}).value.includes('Which project is this meeting for?')")
        self.assertEqual(b.eval("document.querySelectorAll('#chLog .msg.u').length"), 0, "filled in, never sent")

    def test_c26_process_selected_on_a_meeting_already_loaded_does_not_open_ask_creaite(self):
        """26. (#264) Intake › Calendar import: a meeting whose transcript is already in Intake, ticked and Process selected: its row
        goes to "Draft ready in Review" and ask creaite does not open (it opens only when a transcript has first to be loaded)."""
        b = self.b
        cal = self.vault / "system/staging/hc-cal.json"
        cal.write_text(json.dumps({"days": {self.day: [{"id": "hc-9", "start": "07:00", "end": "07:30", "title": "Falcon weekly sync",
                                                       "where": "Microsoft Teams Meeting", "teams": True, "organiser": "Jane Doe",
                                                       "sensitivity": "normal"}]}}))
        code, out = self.run_in_vault("sweep.py", "calendar", cal)
        self.assertEqual(code, 0, out)
        f = self.vault / "inbox" / f"{self.day} Falcon weekly sync.vtt"
        f.write_text(VTT.format(title="Falcon weekly sync").replace("NOTE\n", f"NOTE\nMeeting: Falcon weekly sync\nEvent ID: hc-9\n"),
                     encoding="utf-8")
        self.open_intake()
        row = "document.querySelector('#mtgBody tr[data-mid=\"hc-9\"]')"
        b.wait(f"!!{row}", 20)
        self.assertIn("Loaded", b.eval(f"{row}.innerText"), "the transcript is already in Intake")
        b.eval("MSEL.clear(); MSEL.add('hc-9'); renderMeetings()")
        self.assertEqual(b.eval("document.getElementById('mtgGo').textContent"), "Process 1 selected")
        b.click("#mtgGo")
        b.wait(f"/Draft ready|Couldn/.test({row}.cells[6].innerText)", timeout=90)
        self.assertIn("Draft ready", b.eval(f"{row}.cells[6].innerText"))
        self.assertTrue(self.chat_shut(), "ask creaite stayed shut")
        self.assertEqual(b.eval("document.querySelectorAll('#chLog .msg.u').length"), 0)

    # ── #265 Calendar refresh ──

    def refresh(self):
        """Intake › Calendar import › Refresh, to the end. Returns the number of chat messages Alan has in ask creaite before it."""
        b = self.b
        self.open_intake()
        b.wait("!!document.getElementById('mtgRefresh')&&!document.getElementById('mtgRefresh').disabled", 15)
        said = b.eval("document.querySelectorAll('#chLog .msg.u').length")
        b.click("#mtgRefresh")
        b.wait("[...document.querySelectorAll('#mtgBody tr[data-mid] td.title')].some(t=>/Pilot readiness review/.test(t.innerText))"
               "&&document.getElementById('mtgRefresh').textContent==='Refresh'", timeout=90)
        return said

    def saved_day(self):
        cal = json.loads((self.vault / "system/staging/calendar.json").read_text(encoding="utf-8"))
        return cal, {e["id"]: e for e in cal["days"].get(self.day, [])}

    def test_c27_refresh_reads_the_calendar_as_its_own_job_and_ask_creaite_stays_shut(self):
        """27. (#265) Intake › Calendar import › Refresh: the meetings appear ("Calendar read…" line), the button shows Stop while it works
        and Refresh again at the end, and ask creaite neither opens nor gets a message."""
        b = self.b
        said = self.refresh()
        self.assertTrue(b.eval("document.getElementById('mtgRead').textContent").startswith("Calendar read"))
        self.assertTrue(self.chat_shut(), "ask creaite stays shut")
        self.assertEqual(b.eval("document.querySelectorAll('#chLog .msg.u').length"), said, "nothing said in a chat")
        self.assertIsNone(b.eval("RUN"))
        _, day = self.saved_day()
        self.assertTrue({"ev-r1", "ev-r2", "ev-r3"} <= set(day), list(day))

    def test_c28_the_saved_calendar_keeps_no_join_link_or_passcode(self):
        """28. (#265) After Refresh, the saved calendar and the page hold the invite's agenda line but no Teams join link, meeting ID,
        passcode or dial-in number."""
        self.refresh()
        cal, day = self.saved_day()
        saved = json.dumps(cal)
        for secret in ("teams.microsoft.com", "meetup-join", "4321", "812 3456", "998877", "7946", "zoom.us", "Passcode"):
            self.assertNotIn(secret, saved, f"the saved calendar holds {secret!r}")
            self.assertFalse(self.b.eval(f"JSON.stringify(D).includes({json.dumps(secret)})"), f"the page holds {secret!r}")
        self.assertIn("Agenda: budget and the pilot plan", day["ev-r1"].get("body", ""), "the ordinary agenda line stays")

    def test_c29_a_confidential_meeting_keeps_only_its_title_and_times(self):
        """29. (#265) A confidential meeting in the refreshed calendar keeps its title and times and nothing else: no place, organiser,
        Teams mark, body or attendees."""
        self.refresh()
        _, day = self.saved_day()
        row = day["ev-r3"]
        self.assertEqual((row["title"], row["start"], row["end"]), ("Board strategy session", "23:45", "23:55"))
        self.assertEqual(row.get("sensitivity"), "confidential")
        self.assertEqual(row.get("where"), "")
        self.assertIs(row.get("teams"), False)
        self.assertIs(row.get("organiser"), False)
        for key in ("body", "attendees", "recurrence"):
            self.assertNotIn(key, row)
        self.assertNotIn("Secret agenda", json.dumps(day))
        self.assertIn("Pilot readiness review", day["ev-r1"]["title"], "an ordinary meeting keeps its place and organiser")
        self.assertEqual(day["ev-r1"]["where"], "Microsoft Teams Meeting")

    # ── #269 minutes stage ──

    def spec(self, name, transcript, title="Pilot readiness review"):
        f = self.vault / "system/staging/drafts" / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({"title": title, "date": self.day, "projects": ["FAL"], "transcript": transcript,
                                 "minutes": {"start": "10:00", "end": "10:30", "attendees": "Alan Carter",
                                             "summary": ["The meeting went through the plan."],
                                             "updates": [{"heading": "Plan", "items": ["On track."]}], "open_questions": []},
                                 "items": [{"table": "actions", "values": {"project": "FAL", "description": "Send the checklist",
                                                                         "owner": "Alan Carter", "raised": self.day}}]}), encoding="utf-8")
        return f"system/staging/drafts/{name}"

    def test_c30_stage_takes_a_meeting_only_from_intake_or_the_project_folders(self):
        """30. (#269) Staging minutes from a spec that names a transcript outside Intake and the project folders (a full path in the home
        folder, or a step out of Intake with ..) is refused in a plain sentence, nothing is staged and the file is untouched; a
        transcript in Intake stages as usual."""
        import tempfile
        outside = Path(tempfile.mkdtemp(prefix="creaite-hc253-"))
        self.addCleanup(shutil.rmtree, outside, True)
        secret = outside / "Private interview.vtt"
        secret.write_text(VTT.format(title="Private interview"), encoding="utf-8")
        before = sorted(p.name for p in (self.vault / "system/staging").glob("proposed-*.json"))
        for transcript, why in ((str(secret), "never a full or home path"), (f"inbox/../../{outside.name}/Private interview.vtt", "can't step out")):
            code, out = self.run_in_vault("minutes.py", "stage", self.spec("hc-bad.json", transcript, "Private interview"))
            self.assertEqual(code, 1, out)
            self.assertIn("Not staged:", out)
            self.assertIn(why, out)
            self.assertEqual(sorted(p.name for p in (self.vault / "system/staging").glob("proposed-*.json")), before, "nothing staged")
            self.assertTrue(secret.is_file(), "the file is untouched")
        self.put_inbox(f"{self.day} Pilot readiness review.vtt")
        code, out = self.run_in_vault("minutes.py", "stage", self.spec("hc-ok.json", f"inbox/{self.day} Pilot readiness review.vtt"))
        self.assertEqual(code, 0, out)
        self.assertEqual(len(sorted(p.name for p in (self.vault / "system/staging").glob("proposed-*.json"))), len(before) + 1)
        self.note(30, "full path and .. refused with the reason, nothing staged; the Intake transcript staged")

    # ── #259 client output ──

    def legacy_client_draft(self, plain=True):
        """An older Word client report proposal (what v2.5.0 left in Review) for the demo's Falcon project; (proposal, draft)."""
        fix = REPO / "dev/tests/fixtures/client-migration"
        data = json.loads(json.dumps(json.loads((fix / "word-client-report.proposal.json").read_text(encoding="utf-8")))
                          .replace("ABC", "FAL").replace("Example Programme", "Falcon Data Platform"))
        draft = self.vault / data["report"]["draft"]
        draft.parent.mkdir(parents=True, exist_ok=True)
        draft.write_bytes((fix / "word-client-report.docx").read_bytes())
        import test_reports as R
        R.edit_docx(draft, "Alan Carter", "Sam Lee")          # a name that owns no internal items, so the client check is quiet
        prop = self.vault / "system/staging/proposed-2026-10-09-1300-client-FAL.json"
        prop.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return prop, draft

    def report_n(self):
        code, out = self.run_in_vault("review.py", "list", "--json")
        self.assertEqual(code, 0, out)
        return next(r["n"] for r in json.loads(out[out.index("["):]) if r["ref"] == "report")

    def test_c31_an_approved_client_word_draft_changed_afterwards_is_not_filed(self):
        """31. (#259) A client report approved in Review, then changed (a sentence of internal wording added to its Word draft) before it
        is applied: Apply stops, says it isn't the file whose client check passed, nothing is filed and the report goes back to
        pending; approved again as it was, it is filed."""
        import test_reports as R
        prop, draft = self.legacy_client_draft()
        reports = self.fal / "reports"
        filed = lambda: sorted(p.name for p in reports.glob("*Client report - Falcon*"))
        self.assertEqual(filed(), [])
        code, out = self.run_in_vault("review.py", "approve", str(self.report_n()))
        self.assertIn("Approved 1.", out)
        R.edit_docx(draft, "Phase two is being prepared.", "Phase two is being prepared. Vendor exits the market before go-live.")
        code, out = self.run_in_vault("tracker.py", "apply")
        self.assertNotEqual(code, 0, out)
        self.assertIn("isn't the file whose client check passed", out)
        self.assertEqual(filed(), [], "nothing filed")
        self.assertEqual(json.loads(prop.read_text(encoding="utf-8"))["report"]["report_decision"], "pending", "back in Review")
        # the draft as it was: approved again, it is filed
        R.edit_docx(draft, " Vendor exits the market before go-live.", "")
        code, out = self.run_in_vault("review.py", "approve", str(self.report_n()))
        self.assertIn("Approved 1.", out)
        code, out = self.run_in_vault("tracker.py", "apply")
        self.assertEqual(code, 0, out)
        self.assertEqual(filed(), ["2026-10-09 Client report - Falcon Data Platform.docx"])
        self.note(31, "changed draft refused at apply and back to pending; the clean one filed")

    # ── #272 Suggest ──

    def test_c23_suggest_with_nothing_to_go_on_writes_nothing_and_says_so(self):
        """23. (#272) A risk's Suggest button when the model has nothing to base a suggestion on (it answers NO_SUGGESTION, or says it
        can't): the response field is left as it was, nothing is staged, and a plain note under the button says what it would have
        drawn on; the note goes with the next edit. A decision's reasoning and options and an action's update come back as nothing too."""
        b = self.b
        (self.vault / "fake_draft.py.reply").write_text("No passage or closed-risk response was supplied, so I can't suggest a specific "
                                                        "action. Jane Doe should set out the response.", encoding="utf-8")
        rid = "FAL-005"
        stored = self.py("print(json.dumps(sqlite3.connect('system/tracker.db').execute(\"select response_action from raid where id='FAL-005'\").fetchone()[0]))")
        b.reload("typeof go==='function' && LIVE")
        b.eval(f"openRecord('raid','{rid}')")
        b.wait("document.querySelector('#pkDescDr [data-draft=thinking][data-drf=resp]')", 20)
        field = "document.getElementById('pkDesc').textContent"
        before = b.eval(field)
        self.assertTrue(before.startswith(stored[:20]), "the response as the panel shows it")
        b.click("#pkDescDr [data-draft=thinking]")
        b.wait("document.querySelector('#pkAiDraft .drnone')", 60)
        note = b.eval("document.querySelector('#pkAiDraft .drnone').innerText").strip()
        self.assertEqual(note, "Nothing to suggest from: no meeting passage and no closed risks with a response")
        self.assertIsNone(b.eval("document.querySelector('#pkAiDraft .drcard')"), "no draft card")
        self.assertEqual(b.eval(field), before, "the field is as it was")
        self.assertNotIn("can't suggest", b.eval("document.getElementById('panel').innerText"))
        self.assertEqual(b.eval("PKS.length"), 0, "nothing staged")
        b.eval("document.getElementById('pkDesc').dispatchEvent(new InputEvent('input',{bubbles:true}))")
        b.wait("!document.querySelector('#pkAiDraft .drnone')", 10)
        # the same for a decision's reasoning and options, an action's update and Sneak peek's update: the draft step answers "nothing"
        refusal = "I can't suggest anything here: no passage was supplied."
        for kind, table, field, extra in (("thinking", "decisions", "reasoning", {}), ("thinking", "decisions", "options", {}),
                                          ("update", "actions", None, {"since": "2026-10-01"}), ("sneak-update", "actions", None, {"mode": "tidy"})):
            ctx = json.dumps({"request": {}, "context": {"kind": kind, "feature": kind, "sources": [], "item": {"id": "FAL-X", "table": table, "field": field, **extra}},
                              "reply": refusal})
            r = subprocess.run([str(self.vault / "system/scripts/run"), "drafts.py", "result"], cwd=self.vault, input=ctx, capture_output=True,
                               text=True, env={**os.environ, "CREAITE_NOW": self.now or ""})
            self.assertEqual(r.returncode, 0, r.stderr)
            got = json.loads(r.stdout)
            self.assertTrue(got.get("nothing") and not got.get("text"), f"{kind}/{field}: {got}")


# ── the checks that run the feature's own tests ──────────────────────────────

class Wrapped253(unittest.TestCase):
    """Checks 1 to 5, 7 and 10 to 13: each runs the tests CHECKS names, in fresh processes with throwaway vaults of their own."""

    def setUp(self):
        n = int(self._testMethodName[6:8])
        if only() and n not in only():
            self.skipTest("not in --only")

    def run_check(self, n):
        done = named(self, CHECKS[n], WAITS.get(n, ()))
        NOTES[n] = f"ran {done}"[:280]

    def test_c01_a_stored_client_audience_is_not_trusted(self):
        """1. (#259) A section whose stored audience says "client" is not trusted: the audience is worked out from the report, so a
        stored "client" on an internal-only section (set on disk, or added there) does not put it in a client export."""
        self.run_check(1)

    def test_c02_hidden_words_in_stored_fields_are_caught(self):
        """2. (#259) Plain words in stored fields that are not drawn (an item's values, a row's source or extra cells, tags, headings,
        the based-on path) are checked: a hidden item's words there are refused or dropped, and do not reach the filed report's data block."""
        self.run_check(2)

    def test_c03_unknown_inner_keys_are_dropped(self):
        """3. (#259) Unknown inner keys in an item are dropped, not kept."""
        self.run_check(3)

    def test_c04_oddly_written_item_ids_are_read_as_the_item_they_mean(self):
        """4. (#259) An item ID written oddly ("A B C - 0 0 5", "ABC-5", "ABC-0005") is read as the item it means and hidden when that
        item is hidden."""
        self.run_check(4)

    def test_c05_the_snapshot_test_exists_and_passes(self):
        """5. (#259) The snapshot test that was missing is present and passes: an export renders the checked snapshot, not the file read
        again (a draft changed on disk after the check puts nothing into the export)."""
        self.run_check(5)

    def test_c07_partly_saved_work_columns_open_fine(self):
        """7. (#256) With saved column choices that hold only some of Actions, RAID and Decisions, the Work page opens, shows the saved
        columns for the tabs that have them, fills in the others, and changes nothing you saved."""
        self.run_check(7)

    def test_c10_other_card_only_moves_are_unchanged(self):
        """10. (#255) The one-time approval for other card-only moves (a report, a project folder) still applies; a hand-staged
        proposal still cannot remove a note without the marker."""
        self.run_check(10)

    def test_c11_the_guard_is_not_loosened(self):
        """11. (#255) A confidential note, and a note deleted after ask creaite read outside content, behave as before (the guard is not
        loosened): ask creaite cannot delete a note, and a delete after outside content is refused."""
        self.run_check(11)

    def test_c12_a_server_failure_logs_its_cause(self):
        """12. (#253) A server failure that used to log an unhandled 500 now logs its cause (an error kind and where, never text)."""
        self.run_check(12)

    def test_c13_logs_still_hold_no_text(self):
        """13. (#253) After a sweep and after a failure the debug log still holds counts and IDs only."""
        self.run_check(13)


# ── #238 Your reviews ────────────────────────────────────────────────────────

REV_PANEL = "document.querySelector('#actUsage')"
REV_ROWS = "[...document.querySelectorAll('#actUsage table[aria-label=\"Your reviews\"] tbody tr')].map(tr=>[...tr.children].map(c=>c.textContent))"
CAPTURE = """(()=>{ window.__csv=[]; const mk=URL.createObjectURL.bind(URL);
  URL.createObjectURL=b=>{ window.__csv.push({blob:b}); return mk(b); };
  HTMLAnchorElement.prototype.click=function(){ const c=window.__csv[window.__csv.length-1]; if(c){ c.name=this.download; c.href=this.href; } };
  return true; })()"""
READ_CSV = "(async()=>{ const c=window.__csv[0]; return c?{name:c.name, type:c.blob.type, text:await c.blob.text(), n:window.__csv.length}:null; })()"


class Reviews253(Case253):
    """Checks 20 and 21: Activity › Usage › Your reviews (an own vault: the first check saves a note)."""

    def open_usage(self):
        b = self.b
        b.eval("go('activity')")
        b.wait("!!document.querySelector('#actTabU')", 15)
        b.click("#actTabU")
        b.wait(f"!{REV_PANEL}.hidden && !!document.querySelector('#uRevAdd')", 15)

    def add_note(self, saw, decided):
        b = self.b
        b.click("#uRevAdd")
        b.wait("!!document.querySelector('#uRevForm')")
        b.eval(f"""(()=>{{ const set=(s,v)=>{{ const e=document.querySelector(s); e.value=v; e.dispatchEvent(new Event('input',{{bubbles:true}})); }};
          set('#uRevSaw',{json.dumps(saw)}); set('#uRevDec',{json.dumps(decided)}); return true; }})()""")
        b.click("#uRevSave")
        b.wait("!document.querySelector('#uRevForm')", 15)

    def test_c20_a_review_note_is_saved_with_its_date_and_kept_after_a_reload(self):
        """20. (#238) On the Usage tab, add a review note: it is saved with its date and is still there after a reload."""
        b = self.b
        self.open_usage()
        today = b.eval("document.querySelector('#uRevAdd') && fd(TODAY)")
        self.add_note("Start load about 21,000 tokens a run", "Trim the rules file first")
        first = b.eval(REV_ROWS)[0]
        self.assertEqual(first, [today, "Start load about 21,000 tokens a run", "Trim the rules file first"])
        b.reload("typeof go==='function' && LIVE")
        self.open_usage()
        self.assertIn([today, "Start load about 21,000 tokens a run", "Trim the rules file first"], b.eval(REV_ROWS), "kept after a reload")
        self.note(20, f"saved as {today} and kept after a reload")

    def test_c21_download_as_csv_gives_the_notes_and_nothing_else(self):
        """21. (#238) Download as CSV gives the notes (date, what you saw, what you decided) and nothing else."""
        b = self.b
        self.open_usage()
        self.add_note("Cost up on last week, mostly the sweep", "Move the sweep to 08:00")
        b.eval(CAPTURE)
        b.click("#uRevCsv")
        b.wait("window.__csv.length===1")
        got = b.eval(READ_CSV)
        self.assertTrue(got["name"].endswith("creaite usage reviews.csv"), got["name"])
        self.assertTrue(got["type"].startswith("text/csv"), got["type"])
        lines = [ln for ln in got["text"].lstrip("\ufeff").split("\r\n") if ln]
        self.assertEqual(lines[0].lower().replace('"', ""), "date,what you saw,what you decided")
        shown = b.eval(REV_ROWS)
        self.assertEqual(len(lines) - 1, len(shown), "one row per note on the page, and nothing else")
        mine = [ln for ln in lines[1:] if "Cost up on last week, mostly the sweep" in ln]
        self.assertEqual(len(mine), 1)
        self.assertIn("Move the sweep to 08:00", mine[0])
        for ln in lines[1:]:
            self.assertEqual(ln.count('","'), 2, "three cells: date, what you saw, what you decided")
        self.note(21, "header and one row of three cells per note")


if __name__ == "__main__":
    unittest.main()
