"""#283: the Minutes view's Read again is its own run kind, not an ask creaite message. Pressing it (after the bar's ask) is Alan's
go-ahead to draft one meeting's minutes afresh from its transcript, and the run is fenced to that: #264's Process for that one
transcript, a minutes record only.

Run: python3 dev/tests/test_reextract.py      (quick tier: no Chrome; one live server with a stand-in Claude)

- reextract.py (plain code): the request checked (a pending minutes record of a transcript; nothing of it applied or approved;
  its transcript still there; not already being read again); the fixed prompt and label; the earlier proposal set aside and put
  back; the new draft taking its place with the Track choices carried where the item is the same (an update by its item, a new
  item by its wording), the counts and the closure line; Stop or a failure putting the earlier one back and setting the new one
  aside; a question; Undo; recovery at the server's start; the usage kind.
- The guard hook's mode "reextract" (reach.py, a guarded diff in dev/proposals/283-reextract/): Process's rules for the one
  transcript in the run's record, plus a minutes record only (a spec with a Word "draft", or with no "minutes", is refused),
  no `docx_tools.py fill` and no `search.py enrich`; every record command, another file's spec, refresh, propose.py stage and
  filechange.py refused; Process itself unchanged.
- Through the live server (a guarded diff): POST /api/minutes/reextract runs the kind "reextract" under the hook's mode
  "reextract", the stand-in Claude stages the meeting afresh with the real minutes.py stage, the new draft takes the earlier
  one's place with the Track choices carried, nothing is applied; Undo (POST /api/minutes/reextract/undo) puts the earlier one
  back; Stop puts it back too; token, Host and Origin are checked; a second run while one is going is a 409; the usage line's
  kind is "reextract".
- The page: the Minutes view's button is Read again (plain words), asks first, calls reLive and never writes into ask creaite.

The tests that need the guarded diffs are expected failures until they are applied (APPLIED below); they pass with them.
"""
import json
import os
import re
import subprocess
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "system" / "scripts"))
from test_tracker import Vault  # noqa: E402

APPLIED = "PROCESS_MODES" in (REPO / "system/scripts/reach.py").read_text(encoding="utf-8") and \
    "/api/minutes/reextract" in (REPO / "system/scripts/live_server.py").read_text(encoding="utf-8")
needs_diff = (lambda f: f) if APPLIED else unittest.expectedFailure      # fail first: passes once the guarded diffs are applied


def in_vault(v, code, arg=None):
    """Run Python `code` in the vault (paths.ROOT is the vault there); its JSON output (the last line)."""
    r = subprocess.run([sys.executable, "-c", "import json, sys, time; sys.path.insert(0, 'system/scripts')\n" + code],
                       input=json.dumps(arg), cwd=v.root, capture_output=True, text=True, timeout=120)
    if r.returncode:
        raise AssertionError(r.stderr + r.stdout)
    return json.loads(r.stdout.strip().splitlines()[-1])


def again_spec():
    """The same meeting read again: the first action the same, the second worded a little differently, the third gone, a new
    action, the decision and the risk the same."""
    import test_minutes_editor as me
    spec = me.meeting_spec()
    items = spec["items"]
    items[1] = {**items[1], "values": {**items[1]["values"], "description": "Book the UAT test environment by Friday"}}
    new = {"table": "actions", "values": {"project": "ABC", "description": "Confirm the training plan date", "owner": "Jane Doe"}}
    spec["items"] = [items[0], items[1], new, items[3], items[4]]
    return spec


def staged(v):
    """{name: its record's stored path} for the proposals waiting in Review for a meeting's transcript (populate's own proposal,
    with no meeting, left out). A new draft can take the earlier one's file name (made in the same minute), never its record's."""
    out = {}
    for p in (v.root / "system/staging").glob("proposed-*.json"):
        m = json.loads(p.read_text(encoding="utf-8")).get("meeting") or {}
        if m.get("transcript"):
            out[p.name] = m.get("draft")
    return out


def r_keep():
    """reextract.KEEP, read from the module's text (the test process never imports the vault's scripts)."""
    return int(re.search(r"^KEEP = (\d+)", (REPO / "system/scripts/reextract.py").read_text(encoding="utf-8"), re.M).group(1))


def staged_names(v):
    return sorted(staged(v))


class Fixture:
    """A throwaway vault with the fictional steering committee staged as a minutes record (test_minutes_editor's)."""

    def make(self):
        import test_minutes_editor as me
        from test_dashboard import populate
        self.v = Vault()
        populate(self.v)
        self.proposal = me.stage_meeting(self.v)
        self.data = json.loads((self.v.root / "system/staging" / self.proposal).read_text(encoding="utf-8"))
        self.draft = self.data["meeting"]["draft"]

    def set_track(self, choices):
        in_vault(self.v, "import creaite_doc, minutes_record; a = json.loads(sys.stdin.read()); d = creaite_doc.read(a[0]); "
                         "d['layout'] = {**(d.get('layout') or {}), 'track': a[1]}; "
                         "minutes_record.save_record(a[0], d, 'test', via='dashboard'); print('1')", [self.draft, choices])

    def stage_again(self):
        f = self.v.root / "system/staging/drafts/again.json"
        f.write_text(json.dumps(again_spec()), encoding="utf-8")
        self.v.run("stage", str(f), script="minutes.py")


class Helpers(Fixture, unittest.TestCase):
    """reextract.py: plain code, in a throwaway vault (no guarded file needed)."""

    def setUp(self):
        self.make()

    def tearDown(self):
        self.v.cleanup()

    def test_the_request_is_checked(self):
        got = in_vault(self.v, "import reextract as r; a = json.loads(sys.stdin.read()); "
                               "print(json.dumps([r.validate_request(x) for x in a]))",
                       [{"proposal": self.proposal}, {"proposal": "../x.json"}, {"proposal": "proposed-nope.json"},
                        {"proposal": self.proposal, "extra": 1}, "x"])
        (ctx, why), bad, gone, extra, odd = got
        self.assertIsNone(why)
        self.assertEqual((ctx["proposal"], ctx["draft"], ctx["projects"]), (self.proposal, self.draft, ["ABC"]))
        self.assertTrue(ctx["transcript"].startswith("inbox/") and ctx["transcript"].endswith(".vtt"))
        self.assertEqual(bad, [None, "Open the minutes from Review first."])
        self.assertIn("approved or have gone", gone[1])
        self.assertEqual(extra[1], "Bad request.")
        self.assertEqual(odd[1], "Bad request.")
        for _, w in (bad, gone, extra):
            for banned in ("re-extract", "proposal", "stage", "system/", ".json"):
                self.assertNotIn(banned, w.lower())                         # dev/PLAIN-WORDS.md

    def test_what_stops_a_read_again(self):
        p = self.v.root / "system/staging" / self.proposal
        cases = {}
        for name, change in (("approved", lambda d: d["items"][0].update(decision="approved")),
                             ("applied", lambda d: d["items"][0].update(applied=True)),
                             ("by_others", lambda d: d["meeting"].update(kind="minutes by others")),
                             ("no_transcript", lambda d: d["meeting"].pop("transcript")),
                             ("word", lambda d: d["meeting"].update(draft="system/staging/drafts/x.docx"))):
            d = json.loads(json.dumps(self.data))
            change(d)
            p.write_text(json.dumps(d), encoding="utf-8")
            cases[name] = in_vault(self.v, f"import reextract as r; print(json.dumps(r.validate_request({{'proposal': {self.proposal!r}}})[1]))")
        p.write_text(json.dumps(self.data), encoding="utf-8")
        self.assertIn("approved and waiting to be saved", cases["approved"])
        self.assertIn("already saved", cases["applied"])
        self.assertIn("transcript", cases["by_others"])
        self.assertIn("no transcript", cases["no_transcript"])
        self.assertIn("edited in creaite", cases["word"])
        t = self.v.root / self.data["meeting"]["transcript"]
        t.unlink()
        self.assertIn("can't be found", in_vault(self.v, f"import reextract as r; print(json.dumps(r.validate_request({{'proposal': {self.proposal!r}}})[1]))"))

    def test_the_prompt_and_label_are_fixed(self):
        prompt, label = in_vault(self.v, "import reextract as r; c, _ = r.validate_request({'proposal': json.loads(sys.stdin.read())}); print(json.dumps([r.build_prompt(c), r.label(c)]))", self.proposal)
        t = self.data["meeting"]["transcript"]
        self.assertIn(f"1. path: {json.dumps(t)}\n", prompt)
        self.assertIn('title: "[ABC] Steering committee"', prompt)
        self.assertIn("never docx_tools.py fill", prompt)
        self.assertIn("Skip the step that enriches the search", prompt)
        self.assertIn("QUESTION: <the path as listed>", prompt)
        self.assertEqual(label, "Read a meeting's transcript again")
        self.assertNotIn("Steering", label)                                     # never the title or a path

    def test_hold_then_nothing_back_puts_it_back(self):
        got = in_vault(self.v, "import reextract as r; c, _ = r.validate_request({'proposal': json.loads(sys.stdin.read())}); "
                               "h = r.hold(c, 'x-test-1'); import paths\n"
                               "gone = not (paths.STAGING / c['proposal']).exists(); again = r.validate_request({'proposal': c['proposal']})[1]\n"
                               "out = r.finish('x-test-1', time.time(), [], 'done'); twice = r.finish('x-test-1', time.time(), [], 'done')\n"
                               "print(json.dumps([gone, again, out, twice, (paths.STAGING / c['proposal']).exists()]))", self.proposal)
        gone, again, out, twice, back = got
        self.assertTrue(gone, "set aside while the run drafts afresh")
        self.assertIn("approved or have gone", again)
        self.assertEqual(out["state"], "put_back")
        self.assertEqual(out["line"], "Nothing new came back from the transcript: your earlier minutes are back as they were.")
        self.assertEqual(twice, out, "settled once")
        self.assertTrue(back)

    def test_the_new_draft_takes_the_place_with_the_track_choices(self):
        self.set_track({"2": "n", "4": "y"})                       # crossed the UAT action, ticked the decision
        started = in_vault(self.v, "import reextract as r; c, _ = r.validate_request({'proposal': json.loads(sys.stdin.read())}); "
                                   "r.hold(c, 'x-test-2'); print(time.time())", self.proposal)
        self.stage_again()
        new = [n for n, rec in staged(self.v).items() if rec != self.draft]
        self.assertEqual(len(new), 1)
        out = in_vault(self.v, "import reextract as r; print(json.dumps(r.finish('x-test-2', json.loads(sys.stdin.read()), [], 'done')))",
                       started)
        self.assertEqual(out["state"], "replaced", out)
        self.assertEqual(out["proposal"], new[0])
        self.assertEqual((out["items"], out["new"], out["gone"], out["kept"]), (5, 1, 1, 2), out)
        self.assertEqual(out["line"], "Read again: 5 items found in the meeting (1 new, 1 no longer there); your choices kept on 2. "
                                      "Your earlier version is set aside: Undo brings it back.")
        rec = in_vault(self.v, "import creaite_doc; print(json.dumps(creaite_doc.read(json.loads(sys.stdin.read()))))", out["path"])
        self.assertEqual(rec["layout"]["track"], {"2": "n", "4": "y"})       # the reworded UAT action and the decision
        self.assertEqual(rec["meta"]["proposal"], new[0])
        self.assertEqual(staged_names(self.v), new, "only the new draft in Review")
        hold = self.v.root / "system/staging/reextract/x-test-2"
        self.assertTrue((hold / self.proposal).is_file() and (hold / "record.html").is_file())
        self.assertFalse((self.v.root / self.draft).exists(), "the earlier record is set aside too")
        self.assertEqual(json.loads((hold / "hold.json").read_text())["state"], "replaced")
        undo = in_vault(self.v, "import reextract as r; print(json.dumps([r.undo('x-test-2'), r.undo('x-test-2')]))")
        self.assertEqual(undo[0], {"ok": True, "message": "Your earlier minutes are back.", "proposal": self.proposal, "path": self.draft})
        self.assertFalse(undo[1]["ok"], "once")
        self.assertEqual(staged(self.v), {self.proposal: self.draft})
        self.assertTrue((self.v.root / self.draft).is_file())
        self.assertTrue((hold / "unused" / new[0]).is_file(), "the new one kept aside, never deleted")

    def test_undo_waits_when_the_new_draft_was_approved_or_its_place_is_taken(self):
        started = in_vault(self.v, "import reextract as r; c, _ = r.validate_request({'proposal': json.loads(sys.stdin.read())}); "
                                   "r.hold(c, 'x-test-3'); print(time.time())", self.proposal)
        self.stage_again()
        in_vault(self.v, "import reextract as r; print(json.dumps(r.finish('x-test-3', json.loads(sys.stdin.read()), [], 'done')))", started)
        new = self.v.root / "system/staging" / staged_names(self.v)[0]
        d = json.loads(new.read_text())
        d["items"][0]["decision"] = "approved"
        new.write_text(json.dumps(d))
        got = in_vault(self.v, "import reextract as r; print(json.dumps(r.undo('x-test-3')))")
        self.assertFalse(got["ok"])
        self.assertIn("undo that first", got["message"])

    def test_stop_sets_the_new_one_aside_and_puts_the_earlier_one_back(self):
        started = in_vault(self.v, "import reextract as r; c, _ = r.validate_request({'proposal': json.loads(sys.stdin.read())}); "
                                   "r.hold(c, 'x-test-4'); print(time.time())", self.proposal)
        self.stage_again()
        code = ("import reextract as r; a = json.loads(sys.stdin.read()); ev = []\n"
                "class R: started = a; stop = True\n"
                "R.emit = staticmethod(lambda k, **d: ev.append([k, d]))\n"
                "ls = r.lines('x-test-4'); ls['ended'](R()); print(json.dumps([ls['stopped'](R()), ev]))")
        line, ev = in_vault(self.v, code, started)
        self.assertEqual(line, "Stopped: your earlier minutes are back as they were.")
        self.assertEqual(ev[0][0], "reextract")
        self.assertEqual(ev[0][1]["state"], "put_back")
        self.assertNotIn("line", ev[0][1], "the event carries names and counts, never words to show twice")
        self.assertEqual(staged_names(self.v), [self.proposal])
        self.assertEqual(len(list((self.v.root / "system/staging/reextract/x-test-4/unused").glob("proposed-*.json"))), 1)

    def test_a_question_puts_it_back_and_says_it(self):
        t = self.data["meeting"]["transcript"]
        code = ("import reextract as r; a = json.loads(sys.stdin.read()); c, _ = r.validate_request({'proposal': a[0]}); "
                "r.hold(c, 'x-test-5'); ev = []\n"
                "class R: started = time.time(); said = a[1]\n"
                "R.emit = staticmethod(lambda k, **d: ev.append(d))\n"
                "print(json.dumps([r.closer('x-test-5')(R()), ev]))")
        closure, ev = in_vault(self.v, code, [self.proposal, [f"QUESTION: {t} | Which project is it?\nQUESTION: inbox/other.vtt | No"]])
        self.assertEqual(ev[0]["state"], "needs")
        self.assertEqual(ev[0]["question"], "Which project is it?")
        self.assertEqual(closure["line"], "Needs you: Which project is it? Your earlier minutes are back as they were.")
        self.assertEqual(closure["href"], f"#minutes={self.draft}")
        self.assertEqual(staged_names(self.v), [self.proposal])

    def test_a_new_draft_naming_another_project_date_or_title_is_refused(self):
        """#283 review M1: the transcript's text (or a slip) could name another project, date or title in the new draft; its file
        steps would then copy the minutes into that project's folders on approval. The earlier draft's values hold: such a draft
        is set aside, never takes the place, and the earlier minutes come back."""
        for n, (change, words) in enumerate(((lambda s: s.update(projects=["ABC", "DEF"]), "project"),
                                             (lambda s: s.update(date="2026-09-30"), "date"),
                                             (lambda s: s.update(title="Budget review"), "title"))):
            with self.subTest(words):
                run = f"x-m1-{n}"
                started = in_vault(self.v, "import reextract as r; c, _ = r.validate_request({'proposal': json.loads(sys.stdin.read())}); "
                                           f"r.hold(c, '{run}'); print(time.time())", self.proposal)
                spec = again_spec()
                change(spec)
                f = self.v.root / "system/staging/drafts/again.json"
                f.write_text(json.dumps(spec), encoding="utf-8")
                self.v.run("stage", str(f), script="minutes.py")
                self.assertEqual(len(staged(self.v)), 1, "the run staged its draft")
                out = in_vault(self.v, "import reextract as r; a = json.loads(sys.stdin.read()); "
                                       "print(json.dumps(r.finish(a[0], a[1], [], 'done')))", [run, started])
                self.assertEqual(out["state"], "put_back", out)
                self.assertIn(f"the new draft names a different {words}", out["line"])
                self.assertTrue(out["line"].endswith("Your earlier minutes are back as they were."), out["line"])
                for banned in ("re-extract", "proposal", "stage", "sweep", "system/", ".json"):
                    self.assertNotIn(banned, out["line"].lower())                   # dev/PLAIN-WORDS.md
                self.assertEqual(staged(self.v), {self.proposal: self.draft}, "the earlier minutes back, as they were")
                self.assertTrue((self.v.root / self.draft).is_file())
                self.assertEqual(len(list((self.v.root / f"system/staging/reextract/{run}/unused").glob("proposed-*.json"))), 1,
                                 "the new draft kept aside, never deleted")

    def test_the_closer_settles_a_fault_as_failed(self):
        """#283 review L2: a fault while settling a finished run still puts the earlier minutes back (never left held until the
        server restarts)."""
        code = ("import reextract as r; a = json.loads(sys.stdin.read()); c, _ = r.validate_request({'proposal': a}); "
                "r.hold(c, 'x-l2-1'); ev = []\n"
                "class R: started = time.time(); said = []\n"
                "R.emit = staticmethod(lambda k, **d: ev.append(d))\n"
                "real = r._new_ones\n"
                "r._new_ones = lambda *x: (_ for _ in ()).throw(OSError('boom')) if not ev and not getattr(r, '_t', 0) "
                "and not setattr(r, '_t', 1) else real(*x)\n"
                "print(json.dumps([r.closer('x-l2-1')(R()), ev]))")
        closure, ev = in_vault(self.v, code, self.proposal)
        self.assertFalse(closure["ok"])
        self.assertTrue(closure["line"].startswith("Couldn't finish: your earlier minutes are back"), closure)
        self.assertEqual(ev[-1]["state"], "put_back")
        self.assertEqual(staged_names(self.v), [self.proposal])

    def test_old_holds_are_pruned_but_never_one_still_holding_earlier_minutes(self):
        """#283 review L4: a hold "kept_aside" still holds Alan's earlier minutes (their name was taken): never removed."""
        code = ("import reextract as r, paths, json as j; root = r.hold_root(); root.mkdir(parents=True, exist_ok=True)\n"
                "for i in range(r.KEEP + 3):\n"
                "    d = root / f'x-old-{i:03d}'; d.mkdir()\n"
                "    st = 'kept_aside' if i == 0 else 'put_back'\n"
                "    (d / 'hold.json').write_text(j.dumps({'run': d.name, 'state': st, 'at': i}))\n"
                "r._prune(); print(json.dumps(sorted(p.name for p in root.iterdir())))")
        left = in_vault(self.v, code)
        self.assertIn("x-old-000", left, "a hold still holding the earlier minutes is never removed")
        self.assertEqual(len(left), r_keep() + 1, left)

    def test_recover_puts_back_a_hold_left_by_a_run_that_never_finished(self):
        in_vault(self.v, "import reextract as r; c, _ = r.validate_request({'proposal': json.loads(sys.stdin.read())}); r.hold(c, 'x-test-6'); "
                         "print(1)", self.proposal)
        self.stage_again()
        got = in_vault(self.v, "import reextract as r; print(json.dumps([r.recover(), r.recover()]))")
        self.assertEqual(got, [[self.proposal], []])
        self.assertEqual(staged_names(self.v), [self.proposal], "the earlier one back; what the run made set aside")

    def test_the_usage_monitor_has_the_kind_and_its_label(self):
        import usage_log
        self.assertIn("reextract", usage_log.KINDS)
        self.assertEqual(usage_log.line_for("reextract")["kind"], "reextract")
        panel = (REPO / "system/templates/dashboard/src/components/activity/UsagePanel.jsx").read_text(encoding="utf-8")
        self.assertIn('reextract: "Read again"', panel)


class ThePage(unittest.TestCase):
    """The Minutes view's button: plain words, its own route, never ask creaite (static: the Chrome tier draws it)."""

    def test_the_button_calls_its_own_run_and_never_ask_creaite(self):
        src = (REPO / "system/templates/dashboard/src/components/minutes/MinutesView.jsx").read_text(encoding="utf-8")
        api = (REPO / "system/templates/dashboard/src/core/intakeApi.js").read_text(encoding="utf-8")
        self.assertNotIn("ckAsk", src)
        self.assertNotIn("chIn", src)
        self.assertIn("reLive(v.proposal", src)
        self.assertIn('runRoute("/api/minutes/reextract",{proposal},"x"', api)
        self.assertIn('api("/api/minutes/reextract/undo",{run})', api)
        shown = " ".join(re.findall(r'(?:aria-label|data-tip)="([^"]*)"', src[src.index("function ReadAgain"):])) + " " + \
            " ".join(re.findall(r">([^<>{}]+)<", src[src.index("function ReadAgain"):src.index("/** Approve minutes")]))
        for banned in ("re-extract", "extract", "proposal", "stage", "apply", "ask creaite"):
            self.assertNotIn(banned, shown.lower(), banned)
        built = (REPO / "system/templates/dashboard.html").read_text(encoding="utf-8")
        self.assertIn("/api/minutes/reextract", built, "the page is rebuilt")


class Fence(Fixture, unittest.TestCase):
    """The guard hook's mode "reextract", as Claude Code calls it (reach.decide), in a throwaway vault."""

    @classmethod
    def setUpClass(cls):
        cls.f = Fixture()
        cls.f.make()
        cls.v, cls.t = cls.f.v, cls.f.data["meeting"]["transcript"]
        drafts = cls.v.root / "system/staging/drafts"
        spec = {**again_spec(), "transcript": cls.t}
        (drafts / "mine.json").write_text(json.dumps(spec))
        (drafts / "word.json").write_text(json.dumps({**{k: v for k, v in spec.items() if k != "minutes"},
                                                      "draft": "system/staging/drafts/x.docx"}))
        (drafts / "nominutes.json").write_text(json.dumps({k: v for k, v in spec.items() if k != "minutes"}))
        (drafts / "other.json").write_text(json.dumps({**spec, "transcript": "inbox/other.vtt"}))
        (cls.v.root / "inbox/other.vtt").write_text("WEBVTT\n")

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def decide(self, calls, mode="reextract"):
        """{name: allowed} for each (tool, input), with the run record the server writes for the run."""
        code = ("import reach; a = json.loads(sys.stdin.read()); reach.start_run('x-1', a['mode'], {}, None, files=[a['t']]); "
                "print(json.dumps({k: reach.decide(t, i, a['mode'], 'x-1')[0] for k, (t, i) in a['calls'].items()}))")
        return in_vault(self.v, code, {"mode": mode, "calls": calls, "t": self.t})

    def run_(self, words):
        return ("Bash", {"command": "system/scripts/run " + words})

    def test_the_minutes_steps_for_its_one_transcript_pass(self):
        """What Read again needs gets through (in mode "reextract" with the diffs, and under a plain chat's rules today)."""
        root = str(self.v.root)
        got = self.decide({
            "read_transcript": self.run_(f"minutes.py transcript {json.dumps(self.t)}"),
            "write_spec": ("Write", {"file_path": f"{root}/system/staging/drafts/new-spec.json"}),
            "stage": self.run_("minutes.py stage system/staging/drafts/mine.json"),
            "read_skill": ("Read", {"file_path": f"{root}/.claude/skills/cx-minutes/SKILL.md"})})
        for name, ok in got.items():
            with self.subTest(name):
                self.assertTrue(ok, name)

    @needs_diff
    def test_everything_else_is_refused(self):
        root = str(self.v.root)
        got = self.decide({
            "word_draft_spec": self.run_("minutes.py stage system/staging/drafts/word.json"),
            "no_minutes_spec": self.run_("minutes.py stage system/staging/drafts/nominutes.json"),
            "another_file": self.run_("minutes.py stage system/staging/drafts/other.json"),
            "fill": self.run_("docx_tools.py fill system/templates/minutes-template.docx system/staging/drafts/v.json "
                              "system/staging/drafts/x.docx"),
            "enrich": self.run_("search.py enrich set --path x --summary 'a' --tags 'b'"),
            "refresh": self.run_("minutes.py refresh proposed-x.json"),
            "apply": self.run_("tracker.py apply"), "undo": self.run_("tracker.py undo"),
            "approve": self.run_("review.py approve 1"), "reject": self.run_("review.py reject 1"),
            "propose_stage": self.run_("propose.py stage system/staging/drafts/mine.json"),
            "filechange": self.run_("filechange.py delete inbox/other.vtt --why x"),
            "write_proposal": ("Write", {"file_path": f"{root}/system/staging/proposed-x.json"}),
            "write_hold": ("Write", {"file_path": f"{root}/system/staging/reextract/x-1/hold.json"}),
            "write_record": ("Write", {"file_path": f"{root}/{self.f.draft}"}),
            "write_other_draft": ("Write", {"file_path": f"{root}/system/staging/drafts/mine.json"}),
            "read_home": ("Read", {"file_path": str(Path.home() / ".zshrc")})})     # Microsoft 365 and the web: the run's lists
        for name, ok in got.items():
            with self.subTest(name):
                self.assertFalse(ok, name)

    @needs_diff
    def test_a_word_draft_is_refused_even_from_the_runs_own_values_file(self):
        """The fill a Process run may make (the template, from a values file it wrote, into a new draft) is refused in Read again:
        by its own rule, not only by Process's checks."""
        code = ("import reach, paths; a = json.loads(sys.stdin.read()); out = {}\n"
                "for mode in ('process', 'reextract'):\n"
                "    run = 'x-w-' + mode; reach.start_run(run, mode, {}, None, files=[a])\n"
                "    f = paths.DRAFTS / f'values-{mode}.json'\n"
                "    ok = reach.decide('Write', {'file_path': str(f)}, mode, run)[0]; f.write_text('{}')\n"
                "    reach.post_tool('Write', {'file_path': str(f)}, run, None, mode)\n"      # round 3: the run's tool has returned
                "    c = f'system/scripts/run docx_tools.py fill system/templates/minutes-template.docx {paths.rel(f)} system/staging/drafts/w-{mode}.docx'\n"
                "    out[mode] = [ok, reach.decide('Bash', {'command': c}, mode, run)]\n"
                "print(json.dumps(out))")
        got = in_vault(self.v, code, self.t)
        self.assertEqual(got["process"], [True, [True, ""]], "Process may fill from its own values file")
        self.assertTrue(got["reextract"][0])
        self.assertEqual(got["reextract"][1], [False, "Read again drafts a minutes record only: no Word draft is filled"])

    @needs_diff
    def test_process_is_unchanged_and_the_modes_never_mix(self):
        code = ("import reach; a = json.loads(sys.stdin.read()); reach.start_run('x-2', 'process', {}, None, files=[a]); "
                "s = 'system/scripts/run minutes.py stage system/staging/drafts/word.json'\n"
                "print(json.dumps([reach.decide('Bash', {'command': s}, 'process', 'x-2')[1], "
                "reach.decide('Bash', {'command': s.replace('word', 'mine')}, 'reextract', 'x-2')[0]]))")
        process_why, mixed = in_vault(self.v, code, self.t)
        self.assertNotIn("minutes record only", process_why)                     # Process keeps its Word draft rule
        self.assertFalse(mixed, "a reextract hook never takes a Process run's record as its own")


# The stand-in Claude for the server tests. For a Read again run (the hook's --mode reextract) it asks the run's own hook about a
# few calls (exactly as Claude Code would, from --settings) and records each verdict, then writes the meeting spec for the path in
# its message and runs the real minutes.py stage. A message with "slow" in the vault's slow-reextract file waits first (for Stop).
FAKE = r'''#!/usr/bin/env python3
import json, re, subprocess, sys, time
from pathlib import Path
args = sys.argv[1:]
prompt = args[args.index("--") + 1] if "--" in args else ""
root = Path.cwd()
settings = args[args.index("--settings") + 1] if "--settings" in args else ""
verdicts, results = {}, []
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init", "session_id": "sess-x"})
def hook(tool, inp):
    cmd = json.loads(settings)["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    return subprocess.run(cmd, shell=True, cwd=root, input=json.dumps({"tool_name": tool, "tool_input": inp}),
                          capture_output=True, text=True, timeout=60).returncode
if "--mode reextract" in settings:
    if (root / "slow-reextract").exists():
        time.sleep(20)
    path = json.loads(re.search(r"1\. path: (\".*\")", prompt).group(1))
    spec = json.loads((root / "again.json").read_text())
    spec["transcript"] = path
    verdicts = {k: hook("Bash", {"command": c}) for k, c in {
        "apply": "system/scripts/run tracker.py apply", "fill": "system/scripts/run docx_tools.py fill "
        "system/templates/minutes-template.docx system/staging/drafts/v.json system/staging/drafts/x.docx",
        "refresh": "system/scripts/run minutes.py refresh x"}.items()}
    f = root / "system/staging/drafts/again-spec.json"
    if hook("Write", {"file_path": str(f)}) == 0:
        f.write_text(json.dumps(spec))
        post = json.loads(settings)["hooks"].get("PostToolUse")    # #264 round 3: Claude Code runs it once the tool returns
        if post:
            subprocess.run(post[0]["hooks"][0]["command"], shell=True, cwd=root, capture_output=True, timeout=60,
                           input=json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(f)}}), text=True)
        verdicts["edit_own_spec"] = hook("Edit", {"file_path": str(f)})       # its own file once its print is recorded
        cmd = "system/scripts/run minutes.py stage system/staging/drafts/again-spec.json"
        out({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": cmd}}]}})
        if hook("Bash", {"command": cmd}) == 0:
            r = subprocess.run([sys.executable, "system/scripts/minutes.py", "stage", "system/staging/drafts/again-spec.json"],
                               cwd=root, capture_output=True, text=True)
            results.append(r.returncode)
        else:
            results.append("refused")
        out({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1", "content": "done"}]}})
    said = "Staged.\nCONFIRM: Apply it | Applies\nPERMISSION: Bash(python3 system/scripts/tracker.py apply*) | to apply"
else:
    said = "Plain chat."
with (root / "fake-calls.jsonl").open("a") as fh:
    fh.write(json.dumps({"prompt": prompt, "args": args, "verdicts": verdicts, "results": results}) + "\n")
out({"type": "assistant", "message": {"content": [{"type": "text", "text": said}]}})
out({"type": "result", "result": said, "session_id": "sess-x", "num_turns": 2, "usage": {"input_tokens": 10, "output_tokens": 5}})
'''


class ThroughTheServer(Fixture, unittest.TestCase):
    """The live server with the stand-in Claude: Read again drafts the meeting afresh, and nothing else."""

    @classmethod
    def setUpClass(cls):
        from test_live_server import free_port
        cls.f = Fixture()
        cls.f.make()
        v = cls.v = cls.f.v
        (v.root / "again.json").write_text(json.dumps(again_spec()), encoding="utf-8")
        fake = v.root / "fake_claude.py"
        fake.write_text(FAKE)
        fake.chmod(0o755)
        cfg = v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text(encoding="utf-8"))
        data.setdefault("backups", {})["daily"] = False
        data.setdefault("vip", {})["enabled"] = False
        cfg.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        cls.port = free_port()
        cls.base = f"http://127.0.0.1:{cls.port}"
        cls.proc = subprocess.Popen([sys.executable, str(v.root / "system/scripts/live_server.py")], cwd=v.root,
                                    env={**os.environ, "CREAITE_PORT": str(cls.port), "CREAITE_CLAUDE": str(fake)},
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(300):
            try:
                urllib.request.urlopen(cls.base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        html = urllib.request.urlopen(cls.base + "/").read().decode()
        cls.token = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)
        cls.v.cleanup()

    def post(self, path, body, token=None, headers=None):
        """(status, events or JSON) for a POST."""
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": token or self.token,
                                              **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                text, status = r.read().decode(), r.status
        except urllib.error.HTTPError as e:
            with e:
                return e.code, json.loads(e.read() or b"{}")
        if text.startswith("data: ") or "\n\ndata: " in text:
            return status, [json.loads(x[6:]) for x in text.split("\n\n") if x.startswith("data: ")]
        return status, json.loads(text or "{}")

    def current(self):
        """The pending minutes proposal now in Review (one at a time here)."""
        names = staged_names(self.v)
        self.assertEqual(len(names), 1, names)
        return names[0]

    @needs_diff
    def test_1_read_again_drafts_afresh_and_undo_puts_it_back(self):
        before, rows = self.current(), [self.v.rows(t) for t in ("actions", "raid", "decisions")]
        self.f.proposal, self.f.draft = before, json.loads((self.v.root / "system/staging" / before).read_text())["meeting"]["draft"]
        self.f.set_track({"2": "n"})
        status, evs = self.post("/api/minutes/reextract", {"proposal": before, "run": "x-srv-1"})
        self.assertEqual(status, 200, evs)
        kinds = [e["type"] for e in evs]
        for card in ("confirm", "editcard", "fieldcard", "changes", "cant", "permission"):
            self.assertNotIn(card, kinds)                                       # no go-ahead, no card, no permission offer
        ev = next(e for e in evs if e["type"] == "reextract")
        self.assertEqual(ev["state"], "replaced", evs)
        closure = next(e for e in evs if e["type"] == "closure")
        self.assertTrue(closure["line"].startswith("Read again: 5 items found in the meeting"), closure)
        self.assertEqual(closure["href"], f"#minutes={ev['path']}")
        after = self.current()
        self.assertNotEqual(staged(self.v)[after], self.f.draft, "a new draft (it may take the earlier file name)")
        self.assertEqual(ev["proposal"], after)
        self.assertEqual([self.v.rows(t) for t in ("actions", "raid", "decisions")], rows, "nothing applied")
        c = [json.loads(x) for x in (self.v.root / "fake-calls.jsonl").read_text().splitlines()][-1]
        a = c["args"]
        self.assertIn("--mode reextract", a[a.index("--settings") + 1])
        self.assertEqual(c["verdicts"], {"apply": 2, "fill": 2, "refresh": 2, "edit_own_spec": 0})
        hooks = json.loads(a[a.index("--settings") + 1])["hooks"]
        post = hooks["PostToolUse"][0]["hooks"][0]["command"]                       # H1: round 3's Post, in its own mode
        self.assertTrue("--mode reextract" in post and post.endswith("--event post"), post)
        self.assertEqual(c["results"], [0])
        self.assertIn("--strict-mcp-config", a)                                 # no MCP server at all
        denied = a[a.index("--disallowedTools") + 1]
        for d in ("WebFetch", "mcp__claude_ai_Microsoft_365__outlook_email_search", "Bash(python3 system/scripts/tracker.py apply*)",
                  "Bash(python3 system/scripts/docx_tools.py fill*)", "Bash(python3 system/scripts/search.py enrich*)",
                  "Bash(python3 system/scripts/minutes.py refresh*)", "Bash(python3 system/scripts/filechange.py*)"):
            self.assertIn(d, denied)
        allowed = a[a.index("--allowedTools") + 1].split(",")
        self.assertFalse(any(t.startswith("mcp__") or "docx_tools.py fill" in t or "enrich" in t for t in allowed), allowed)
        self.assertNotIn(str(Path.home()), [a[i + 1] for i, x in enumerate(a) if x == "--add-dir"], "never the home folder")
        self.assertIn("#283", a[a.index("--append-system-prompt") + 1])
        usage = [json.loads(x) for x in (self.v.root / "system/staging/run-usage.jsonl").read_text().splitlines()]
        self.assertEqual(usage[-1]["kind"], "reextract")
        status, got = self.post("/api/minutes/reextract/undo", {"run": "x-srv-1"})
        self.assertEqual((status, got["ok"], got["proposal"]), (200, True, before), got)
        self.assertEqual(staged(self.v), {before: self.f.draft})

    @needs_diff
    def test_2_only_this_pages_own_requests_and_a_checked_proposal(self):
        name = self.current()
        for headers, token in (({}, "forged"), ({"Host": "evil.example"}, None), ({"Origin": "https://evil.example"}, None)):
            with self.subTest(headers=headers, token=token):
                status, got = self.post("/api/minutes/reextract", {"proposal": name}, token=token, headers=headers)
                self.assertEqual(status, 403, got)
                status, got = self.post("/api/minutes/reextract/undo", {"run": "x-srv-1"}, token=token, headers=headers)
                self.assertEqual(status, 403, got)
        status, got = self.post("/api/minutes/reextract", {"proposal": "../../CLAUDE.md"})
        self.assertEqual(status, 400, got)
        self.assertEqual(self.current(), name)

    @needs_diff
    def test_3_one_run_at_a_time_and_stop_puts_it_back(self):
        name = self.current()
        (self.v.root / "slow-reextract").write_text("1")
        got = {}
        t = threading.Thread(target=lambda: got.update(r=self.post("/api/minutes/reextract", {"proposal": name, "run": "x-srv-3"})))
        t.start()
        try:
            for _ in range(100):
                status, running = self.post("/api/ask/running", {})
                if running.get("run") and not running["run"].get("done"):
                    break
                time.sleep(0.05)
            self.assertEqual(staged_names(self.v), [], "set aside while it runs")
            status, busy = self.post("/api/minutes/reextract", {"proposal": name})
            self.assertEqual(status, 400, busy)                                  # it is set aside: nothing to read again now
            status, busy = self.post("/api/minutes/reextract/undo", {"run": "x-srv-1"})
            self.assertEqual(status, 409, busy)
            self.post("/api/ask/stop", {"run": "x-srv-3"})
        finally:
            t.join(timeout=60)
            (self.v.root / "slow-reextract").unlink()
        evs = got["r"][1]
        closure = next(e for e in evs if e["type"] == "closure")
        self.assertEqual(closure["line"], "Stopped: your earlier minutes are back as they were.")
        self.assertEqual(staged_names(self.v), [name])


if __name__ == "__main__":
    unittest.main()
