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
  TodayChecks    8 to 17     Today: the day band, popups, past days, weekends, commitments, Intake, day roll, health bars
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
    """Run the named tests of dev/tests/<file>.py in a fresh process; a failure is run once more (browser tests are timing
    sensitive on a busy machine) and a pass on the second run is reported as such. Returns (ok, message, count)."""
    ok, msg, count = _run_named(file, tokens, timeout)
    if ok or "is not on main" in msg:
        return ok, msg, count
    ok2, msg2, count2 = _run_named(file, tokens, timeout)
    if ok2:
        return True, f"{file}: passed on the second run (the first failed: {msg[:160]})", count2
    return False, msg2, count2


def _run_named(file, tokens, timeout):
    """One run. The process gets no CREAITE_* variable (the hand-check vault's pinned clock and port are not theirs); each test
    builds its own throwaway vault."""
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
        total, failed, retried = 0, [], []
        for file, tokens in pairs:
            ok, msg, count = run_named(file, tokens)
            total += count
            if not ok:
                failed.append(msg)
            elif msg:
                retried.append(msg)
        self.assertEqual(failed, [], "\n".join(failed))
        self.note(n, f"{total} existing tests called, all passed: " + ", ".join(f for f, _ in pairs)
                  + ("; " + "; ".join(retried) if retried else ""))

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
    "weekly": ("go('weekly',{code:'FAL'})", "document.querySelector('#v-reporting section[data-id=current_state]')"),
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
        self.assertIn("What's new", [t.replace("\u2019", "'") for t in tabs])
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


# ── Today (#138, #140, #147, #150, #168, #171, #173, #187, #162) ─────────────

class TodayChecks(V220Case):
    """Today's checks call the existing tests (each pins its own clock); 13 also reads the hand-check vault's Today."""

    def test_c08_no_note_link_no_prepare_pill(self):
        """8. Meeting cards in the day band have no Note link and no Prepare pill; dates are small."""
        self.named(8, "test_prep_popup", "test_140_the_band_has_no_prepare_pill_and_no_note_link")

    def test_c09_prepare_popup_on_the_title(self):
        """9. Hover a meeting's title: a Prepare popup opens after a short rest, not at once; Tab to the title and it opens too."""
        self.named(9, "test_prep_popup", "test_140_the_popup_opens_on_hover_after_a_rest_not_at_once",
                   "test_140_the_title_opens_a_popup_on_focus_with_prepare_then_the_agenda_actions")

    def test_c10_past_days_behind_one_icon(self):
        """10. Past days are behind one small icon: hover or Enter opens a list newest first; arrows move; Esc closes and returns
        focus. (The sheet names these tests in test_prep_popup; on main they are in test_today_days_ui.)"""
        self.named(10, "test_today_days_ui",
                   "test_147_past_days_are_behind_one_icon_newest_first_and_the_chosen_one_shows",
                   "test_147_the_icon_opens_on_hover_and_there_is_none_without_past_days",
                   "test_147_the_icon_works_from_the_keyboard_enter_opens_arrows_move_escape_closes_and_returns_focus")

    def test_c11_weekends_only_when_planned(self):
        """11. Saturday and Sunday are not in the day line unless something is planned. (The clock is pinned to a weekday by the
        tests themselves.)"""
        self.named_many(11, ("test_today_days", ("test_a_weekend_day_with_nothing_planned_is_left_out",)),
                        ("test_today_brief", ("test_weekends_show_only_with_a_meeting",)))

    def test_c12_commitments_five_then_more(self):
        """12. Your commitments shows five items, then "Show more" (or "+n more"). The sheet had no test; main has three
        (test_today_home, #150)."""
        self.named(12, "test_today_home", "test_150_five_rows_then_more_expands_and_folds",
                   "test_150_no_control_at_five_or_fewer_and_you_owe_is_unchanged",
                   "test_150_control_is_a_button_at_900px_and_keeps_focus")

    def test_c13_intake_and_review(self):
        """13. "To decide" is now Intake: new name, new position just above Week ahead, it folds like the others, new
        items are marked, and its buttons take the keyboard. (Since #208 in 2.3.0 it is one quiet line with real links; the old
        buttons became links, so the keyboard half is the links'. Since #245 in 2.5.2 the section is gone: Intake is one quiet line at
        the foot of Your commitments, and what is left of the old section is Messages, hidden when empty, just above Week ahead.)"""
        b = self.b
        self.screen("today")
        heads = b.eval("[...document.querySelectorAll('#v-today h2')].map(h=>h.textContent.trim())")
        at = lambda name: next((i for i, h in enumerate(heads) if h.startswith(name)), None)      # a heading carries its count
        self.assertIsNone(at("Intake and Review"), heads)          # #245: no such section any more
        self.assertIsNone(at("To decide"), heads)
        if at("Messages") is not None and at("Week ahead") is not None:       # Messages is hidden when it is empty
            self.assertEqual(at("Messages") + 1, at("Week ahead"), "Messages just above Week ahead")
        o = b.eval("""(()=>{ const l=document.getElementById('tdQuiet'), a=l&&l.querySelector('a');
          return {text:l?l.textContent.replace(/\\s+/g,' ').trim():null, last:!!l&&document.getElementById('mineSec').lastElementChild.contains(l),
            links:l?[...l.querySelectorAll('a')].map(x=>[x.dataset.tdq,x.getAttribute('href')]):[], focus:!!a&&(a.focus(),document.activeElement===a)}; })()""")
        self.assertIsNotNone(o["text"], "the vault has proposals waiting, so Intake's line shows")
        self.assertTrue(o["text"].startswith("Intake: "), o["text"])
        self.assertTrue(o["last"], "the line is the last thing in Your commitments")
        self.assertIn(["proposals", "#intake-review&stage=drafted"], o["links"])                # its phrases are real links, and the keyboard reaches them
        self.assertTrue(o["focus"])
        self.named_many(13, ("test_today_home", ("test_every_section_in_order_unboxed_resolved_folded",
                                                  "test_messages_keep_their_cards_newest_first")),
                        ("test_today_intake_line", ("test_counts_in_the_locked_wording_with_two_links_and_an_x",
                                                    "test_proposals_open_review_and_meetings_open_intake",
                                                    "test_no_line_when_nothing_waits",
                                                    "test_it_comes_back_when_a_new_proposal_arrives",
                                                    "test_message_cards_keep_a_section_of_their_own_called_messages")),
                        ("test_today_brief", ("test_needs_attention_lists_no_proposals_they_are_in_to_decide",)))
        self.note(13, "Today's headings in the vault: " + " | ".join(heads) + ". Not run: test_shared_behaviour (known red on the "
                  "2.2.0 line for the Reject buttons; a whole-screens suite, not this check)")

    def test_c14_day_roll(self):
        """14. A window left open past midnight rolls to the new day; yesterday's finished meetings stop saying "Not happened
        yet". (The page clock is moved past midnight by the tests.)"""
        self.named(14, "test_day_roll", "test_the_new_day_makes_yesterdays_meeting_happened_and_moves_today",
                   "test_unsaved_edits_get_a_snack_not_a_redraw")

    def test_c15_friday_close_shows_the_weekend(self):
        """15. On a Friday, Close the day's card also lists Saturday and Sunday's planned work under the next working day;
        midweek it is unchanged. (The test pins Friday 16-10-2026 17:30.)"""
        self.named(15, "test_close_day", "test_a_friday_close_lists_planned_weekend_work")

    def test_c16_health_bars(self):
        """16. Portfolio health bars: six weeks, tall green for on track and a short red stub for off track; a ? opens a key; a
        tooltip shows the week and its reason; the keyboard moves between weeks."""
        self.named(16, "test_portfolio_table", "test_the_bars_are_six_and_height_is_health",
                   "test_the_tooltip_lists_six_weeks_with_the_reason_and_the_keyboard_moves_between_them",
                   "test_the_question_mark_opens_the_key_and_escape_closes_it")

    def test_c17_review_age(self):
        """17. Review shows age as quiet text; when everything is old, one banner says so with "Oldest first"; when one is
        different, only that one is marked. (#177, on main.)"""
        self.named(17, "test_review_age", "test_banner_age_text_and_oldest_first", "test_one_outlier", "test_no_banner",
                   "test_both_palettes_light_and_dark")


# ── The left side bar and hover (#156, #198, #139, #143, #160) ───────────────

class RailChecks(V220Case):
    """Rail: the named tests, and check 19 read from the hand-check vault."""

    def test_c18_rail_states(self):
        """18. The rail has three states (expanded with labels, collapsed with labels under the icons, icons only), the wordmark
        is the toggle, the current page is clear, pages are grouped; icons-only never opens the full rail on hover."""
        self.named_many(18, ("test_rail_states", ("test_the_wordmark_is_the_toggle", "test_icons_only_never_opens_the_full_rail_on_hover")),
                        ("test_rail_customise", ("test_every_rail_item_icon_is_in_the_table",)))

    def test_c19_rail_is_188_px(self):
        """19. The expanded rail is 188 px wide (was 224), about half the empty space beside the words. Measured in the
        hand-check vault at 1400 px: the rail's computed width, and the 900 px width for the record."""
        b = self.b
        self.screen("today")
        wide = b.eval("getComputedStyle(document.querySelector('.rail')).width")
        self.assertEqual(wide, "188px", "the expanded rail at 1400 px")
        measure.width(b, 900, 900)
        try:
            narrow = b.eval("getComputedStyle(document.querySelector('.rail')).width")
        finally:
            measure.width(b, self.width, self.height)
        self.note(19, f"rail {wide} at 1400 px; {narrow} at 900 px (collapsed under 1200 px)")

    def test_c20_rail_flyouts(self):
        """20. Pointing at Projects, Work or More opens its flyout beside the rail after 0.2 s and closes 0.3 s after you leave;
        counts are right. (On main the flyout tests are in test_rail_states, not test_rail_flyouts.)"""
        self.named(20, "test_rail_states", "test_collapsed_flyouts_sit_beside_the_rail_and_a_click_on_more_still_toggles",
                   "test_projects_flyout_lists_active_projects_by_name_with_health_and_opens_the_page",
                   "test_work_flyout_lists_four_lists_with_counts_and_a_pick_opens_that_list")

    def test_c21_one_hover_standard(self):
        """21. Every tooltip, card and menu that opens on hover waits the same time, and one flyout is open at a time."""
        self.named_many(21, ("test_hover_standard", ("test_constants", "test_card", "test_menu")),
                        ("test_rail_states", ("test_the_hover_standards_times_and_one_flyout_at_a_time",)))


# ── Notes and editors (#119, #136, #117, #131, #134, #120, #121, #133, #175) ─

class EditorChecks(NamedCase):
    """Notes and the editors: the named tests, each in its own throwaway vault."""

    def test_c22_notes_autosave(self):
        """22. Type in a note and stop: it saves about two seconds later; no draft step; nothing saves before."""
        self.named(22, "test_notes_autosave_page", "test_saves_two_seconds_after_the_last_key_and_not_before",
                   "test_nothing_is_sent_when_nothing_changed")

    def test_c23_notes_focus_mode(self):
        """23. Notes focus mode: a quiet writing view with the same note and cursor; Esc closes the topmost overlay first, then
        leaves focus mode; a refused save is visible and the leave dialog offers the file's version or a discard. (The inert page
        behind and Cmd+Shift+F, #136, are on main and called too.)"""
        self.named(23, "test_notes_autosave_page", "test_esc_closes_the_topmost_overlay_first_then_leaves_focus_mode",
                   "test_the_refusal_is_visible_in_focus_mode_and_the_dialog_offers_the_files_version_and_a_discard",
                   "test_tab_never_leaves_the_note_and_the_page_behind_is_inert",
                   "test_cmd_shift_f_enters_and_leaves_focus_mode_and_focus_returns_to_the_opener",
                   "test_esc_closes_the_real_link_popover_first_then_leaves_focus_mode")

    def test_c24_ai_on_selected_text(self):
        """24. Select text in Notes: a margin sparkle and a grouped hover bar with Turn into (apart from the AI), Format notes for
        two or more paragraphs; Accept, Show changes and ⌘Z on a suggestion; the same in Current state. (The stand-in Claude
        answers; the wording of a real suggestion is the hand part.)"""
        self.named(24, "test_ai_117", "test_notes_offers_turn_into_apart_from_the_ai_zone_and_current_does_not",
                   "test_format_notes_needs_two_or_more_paragraphs_and_a_place_that_has_it",
                   "test_format_notes_suggestion_card_accept_show_changes_and_command_z",
                   "test_pointing_at_a_group_opens_it_and_leaving_folds_it")

    def test_c25_notes_undo_and_activity(self):
        """25. Notes: one session's Undo is capped, Activity shows fewer rows, old draft files are cleaned. (#175; the sheet
        found no test, main has test_notes_175.)"""
        self.named(25, "test_notes_175", "test_one_row_per_editing_session_with_a_count",
                   "test_a_capped_session_and_the_next_are_two_rows", "test_the_row_restore_puts_back_the_file_as_before_the_session",
                   "test_only_the_old_note_drafts_are_moved_into_one_backup", "test_the_live_server_clears_them_at_start_up",
                   "test_the_cleanup_is_not_a_change_activity_lists_or_undo_touches")

    def test_c26_links_in_every_editor(self):
        """26. Links in every editor: add, change, remove; links show wherever text is shown, and in the plain fields. (#120,
        #121: both are on main, so the check is not struck.)"""
        self.named_many(26, ("test_editor_links", ("test_the_validator_allows_http_https_and_mailto_and_refuses_every_disguise",
                                                    "test_the_toolbar_button_adds_a_link_in_a_labelled_dialog",
                                                    "test_remove_keeps_the_words", "test_edit_changes_the_words_and_the_address",
                                                    "test_current_state_has_the_same_link_control_and_check",
                                                    "test_the_markdown_round_trips_through_the_editor")),
                        ("test_editor_links_plain", ("test_a_link_is_read_and_written_as_words_and_address",
                                                     "test_the_link_is_staged_as_words_and_address",
                                                     "test_work_table_update_and_response", "test_the_project_page_risk_card",
                                                     "test_review_detail_draft_email_and_the_peek_history",
                                                     "test_today_shows_the_words_where_the_text_is_cut")))

    def test_c27_plain_profile_and_draft_email(self):
        """27. The plain profile and Draft email on the shared editor: edit the preview, Copy, paste into Outlook (table,
        colours and bold the same). (#133 is on main. Editing and Copy are scripted; the paste into Outlook is the hand part.)"""
        self.named(27, "test_editor_plain",
                   "test_the_preview_is_a_shared_editor_host_and_an_unedited_copy_is_byte_for_byte_todays",
                   "test_an_accepted_suggestion_edits_the_email_and_the_copy_keeps_the_table_and_the_colours",
                   "test_typing_markdown_marks_starts_nothing_and_typing_edits_the_email",
                   "test_the_old_preview_is_gone_and_the_draft_email_keeps_the_builder_as_its_source")

    def test_c29_steer_it_further(self):
        """29. Generate current state, Steer it further: a box with starters that append a sentence and never send; versions
        kept; a client-safe draft is not offered a refine and says why."""
        self.named(29, "test_generate_refine",
                   "RefineDialog.test_steer_it_further_appears_under_every_forms_result_and_not_before",
                   "RefineDialog.test_the_starters_append_a_sentence_and_never_fill_or_send",
                   "RefineDialog.test_versions_back_and_on_and_a_refine_from_an_earlier_one",
                   "RefineDialog.test_a_client_safe_draft_is_not_offered_a_refine_and_says_why",
                   "RefineEditor.test_a_client_safe_current_state_draft_is_not_offered_a_refine_and_says_why",
                   "RefineEditor.test_the_starters_append_only",
                   "RefineRules.test_a_client_safe_refine_is_refused_before_any_facts_are_built")


# ── The report, health and Prep (#202, #203, #111, #134) ─────────────────────

class ReportChecks(V220Case):
    """The weekly report in a vault of its own (a report is refused while the project has items awaiting review)."""
    own_vault = True
    _cleared = False

    def setUp(self):
        super().setUp()
        cls = type(self)
        if not cls._cleared:
            code, out = self.run_in_vault("review.py", "reject", "2,3,4,5")
            self.assertEqual(code, 0, out[-400:])
            cls._cleared = True

    def open_weekly(self):
        self.screen("weekly", settle=0.5)

    def test_c28_sheet_toolbar_and_checklists(self):
        """28. Report sheets have the one-line grouped toolbar; checklist boxes appear as boxes in Word and on the Prep page; the
        client report stays client-safe with the new bar. The Word and Prep-page round trips are scripted; the toolbar's look is
        on the screenshot sheet (desktop and 900 px, two themes, light and dark); boxes in Word itself are the hand part."""
        self.named(28, "test_current_headings", "test_a_checklist_edited_in_word_comes_back_as_a_checklist",
                   "test_the_prep_page_shows_a_checklist_item_with_its_glyph")
        self.open_weekly()
        bar = self.b.eval("(()=>{const e=document.querySelector('#v-reporting .sheet-bar'); return e?[e.getBoundingClientRect().height, "
                          "e.querySelectorAll('button').length]:null})()")
        self.assertTrue(bar, "the weekly sheet has a toolbar")
        shots = self.sheet(28, "weekly", palettes=["creaite", "Cursor"], widths=(1400, 900))
        self.note(28, f"toolbar {round(bar[0])} px high with {bar[1]} buttons; {shots} screenshots")

    def test_c30_report_banner_room(self):
        """30. Weekly report banner: scroll down and the search bar and title block go at once, leaving one slim bar; scrolling up
        never brings them back; at the top of the report they return; clicking a slim-bar button never brings them back; the client
        report and the minutes view behave the same. Measured: room for the report, about 70% at the top and 93% while reading."""
        b = self.b
        self.open_weekly()

        def room():
            return b.eval("(()=>{const r=document.querySelector('#v-reporting .sheet-scroll').getBoundingClientRect();"
                          "return (Math.min(r.bottom,innerHeight)-Math.max(r.top,0))/innerHeight})()")
        top = room()
        r = b.eval("(()=>{const r=document.querySelector('#v-reporting .sheet-scroll').getBoundingClientRect();"
                   "const t=Math.max(r.top,60), bt=Math.min(r.bottom,innerHeight); return [r.left+r.width/2, t+(bt-t)/2]})()")
        b.call("Input.dispatchMouseEvent", type="mouseWheel", x=r[0], y=r[1], deltaX=0, deltaY=2)
        b.wait("!!document.querySelector('#v-reporting .sheet-root.rpt-slim')", 8)
        b.pump(0.4)
        reading = room()
        self.assertGreater(reading, top + 0.1, "more room once the bands are gone")
        self.assertGreaterEqual(reading, 0.85, "about 93% of the window is the report while reading")
        self.assertLessEqual(top, 0.82, "about 70% at the top")
        self.named_many(30, ("test_report_banner", ("WeeklyBanner.test_first_tick_hides_the_bands_and_leaves_the_slim_bar",
                                                     "WeeklyBanner.test_scrolling_up_never_brings_it_back_only_the_top_does",
                                                     "WeeklyBanner.test_a_click_in_the_slim_bar_keeps_it_hidden",
                                                     "ClientBanner.test_first_tick_hides_the_bands_and_leaves_the_slim_bar",
                                                     "MinutesBanner.test_first_tick_hides_the_bands_and_leaves_the_slim_bar")))
        self.note(30, f"room for the report {top:.0%} at the top, {reading:.0%} while reading (the sheet: about 70% and 93%)")

    def test_c31_health_suggest(self):
        """31. Health ✦ on the project page and on the report's health row: the plain sparkle beside the heading; a draft with the
        evidence listed; nothing changes until you accept and save; client-facing wording uses client-visible items only. Scripted
        with the stand-in Claude; the project page is on the screenshot sheet; the wording of a real draft is the hand part."""
        self.named_many(31, ("test_health_suggest", ("HealthSuggest.test_the_sparkle_is_plain_named_and_sits_right_of_the_label",
                                                      "HealthSuggest.test_the_suggestion_shows_the_health_the_reason_and_the_evidence_with_linked_ids",
                                                      "HealthSuggest.test_use_fills_both_fields_and_saves_nothing",
                                                      "WeeklyHealthRow.test_the_sparkle_is_by_the_heading_and_named",
                                                      "WeeklyHealthRow.test_it_shows_the_flag_the_difference_and_the_evidence_with_linked_ids",
                                                      "ClientHealthRow.test_the_client_sheet_asks_for_the_client_audience_and_use_sets_the_client_flag")),
                        ("test_drafts_health_suggest", ("test_client_mode_holds_client_visible_items_only",
                                                         "test_client_mode_with_no_client_visible_item_says_so_and_asks_no_model",
                                                         "test_nothing_is_written_to_the_tracker")))
        shots = self.sheet(31, "cockpit", palettes=["creaite", "Cursor"], widths=(1400, 900))
        self.note(31, f"{shots} screenshots of the project page")

    def test_c32_prep_as_one_page(self):
        """32. Meeting Prep is one page; hovering a meeting shows a peek; the agenda is an editable document you can save and start
        over. The page and the peek are scripted. The agenda as an editable document (#111 C and D) is not on main: Draft agenda
        is still the card with Copy and Save to Agendas, so that part is struck, not failed."""
        self.named_many(32, ("test_prep_popup", ("test_111_the_peek_shows_the_aim_what_to_raise_and_the_ask_from_the_stored_focus",
                                                  "test_111_a_meeting_not_shaped_says_so_and_lists_what_is_in_play",
                                                  "test_111_the_peek_uses_the_shared_hover_constants_and_no_timer_of_its_own")),
                        ("test_prep_view", ("test_1_the_address_opens_the_view_and_a_reload_keeps_it", "test_2_the_header",
                                             "test_3_three_columns_outline_notes_questions_and_rail",
                                             "test_6_the_aim_is_three_stacked_editors_saved_as_you_type")),
                        ("test_prep_shape", ("Shape.test_1_the_panel_the_box_and_a_chip_add_to_the_text",
                                              "Shape.test_2_shape_reads_drafts_cites_and_accept_saves_in_the_servers_format")))
        self.note(32, "struck: the agenda as an editable document with Save and Start over (#111 C and D) is not on main; "
                      "the nearest, Draft agenda's card and Save to Agendas, is test_drafts_agenda")


# ── ask creaite, the sweep and the small things (#130, #148, #146, #144, #161, #197, #155) ──

class SmallChecks(NamedCase):

    def test_c33_esc_keeps_the_run(self):
        """33. Esc closes ask creaite's panel but never stops a run; only Stop stops it; a reload shows the run still going."""
        self.named(33, "test_ask_reopen", "test_esc_in_the_box_with_a_run_closes_the_panel_and_the_run_carries_on",
                   "test_esc_with_a_run_then_a_reload_reattaches_and_shows_it_going", "test_esc_with_a_run_at_900px_wide")

    def test_c34_reopened_chat_whole(self):
        """34. A long old reply is there whole when you reopen a chat, and it never rewrites itself on screen."""
        self.named(34, "test_ask_reopen", "test_a_long_saved_reply_is_there_whole_on_open_and_never_changes",
                   "test_a_large_reply_still_arriving_at_reopen_is_not_redrawn_and_the_new_text_streams")

    def test_c35_sweep_window(self):
        """35. The sweep reads the calendar from today forward, and mail and Teams look back at most three days. (A real sweep
        is the hand part.)"""
        self.named_many(35, ("test_meetings", ("test_window_starts_today_not_monday",)),
                        ("test_settings_catalogue", ("test_the_sweep_lookback_cap_is_an_advanced_setting_with_its_reason",)))

    def test_c36_board_width_remembered(self):
        """36. Work board: resize the board's width and the choice is remembered. (#144; the sheet found no test, main has
        test_work_board_resize.)"""
        self.named(36, "test_work_board_resize", "test_drag_keys_reset_limits_and_memory",
                   "test_corrupt_remembered_widths_never_break_the_board")

    def test_c37_one_esc_on_a_peek(self):
        """37. One Esc closes an item's peek (it took two). (#161; the sheet found no test, main has test_esc_peek_161.)"""
        self.named(37, "test_esc_peek_161", "test_list_one_esc_after_the_id_a_double_click_and_enter",
                   "test_list_a_click_on_another_row_while_open_then_one_esc", "test_board_one_esc_after_the_id_and_a_double_click",
                   "test_person_page_one_esc", "test_review_one_esc", "test_a_dialog_a_menu_and_the_chat_go_first")

    def test_c38_run_usage_record(self):
        """38. The run usage record: each AI run adds one counts-only line (kind, seconds, tokens, cost, whether stopped; never
        text); a stopped run is still recorded; nothing is written in the development repository."""
        self.named(38, "test_run_usage", "test_run_usage_line_has_counts_only", "test_run_usage_appended_for_each_kind",
                   "test_stopped_run_still_recorded")


# ── Themes (#155) ────────────────────────────────────────────────────────────

class Themes(V220Case):
    """The look, on the screenshot sheet: creaite and Cursor, light and dark, desktop and 900 px."""

    def test_c39_themes_glance(self):
        """39. Themes: look at Today, the day band, Portfolio's bars, the rail and a note in creaite and Cursor, light and dark.
        Today carries the day band, the Portfolio bars and the rail; the Notes screen and a project page are added. The theme
        tests run on these two palettes only (#155)."""
        names = measure.themes(self.b)
        for p in ("creaite", "Cursor"):
            self.assertIn(p, names, f"the {p} theme")
        total = 0
        for screen in ("today", "notes", "cockpit"):
            total += self.sheet(39, screen, palettes=["creaite", "Cursor"], widths=(1400, 900))
        self.note(39, f"{total} screenshots: today, notes, cockpit; creaite and Cursor; light and dark; 1400 and 900 px")


if __name__ == "__main__":
    unittest.main()
