"""creaite 2.6.10's hand checks that need no browser (sheet dev/handchecks/v2.6.10.md). 2.6.10 holds #385 (a project's folder in a
place of its own), #250 (fetch transcripts as they appear), #329 (shareable minutes and the lines about a Sensitive item), #370 (a
missed mail and Teams check, and smaller fixes) and, if it lands, #374 (file paths and Show in Finder). #366 is tests only and #386
is not in 2.6.10. All data is fictional; no browser, no network, no Claude.

The sheet holds only judgement and live-only checks (numbers 1 to 8, tagged below). The tests are numbered from 11 and cover the
rest, including the draft's check 3 (the archive beside each project) and the open points.

  11  version    VERSION is a version the tooling accepts, 2.6.9 or later
  12  notes      once VERSION is 2.6.10: What's new has the 2.6.10 section above 2.6.9 naming the shipped items; plain notes and sheet exist
  13  public     once VERSION is 2.6.10: the notes carry no GUARDED marker or real names; whats_new.py finds the section
  14  guides     once VERSION is 2.6.10: both guides carry 2.6.10 and no earlier 2.6 string; the first-day guide names the 2.6.10 zip
  15  guarded    no guarded file differs from the 2.6.9 release (tag v2.6.9, else the merge base with v269-release) except through
                 the diffs the two 2.6.10 chains list (GUARDED-2.6.10.chain, then GUARDED-2.6.10b.chain), byte for byte; once VERSION
                 is 2.6.10, every listed diff is in and nothing pends
  16  chain      every diff the two 2.6.10 chains list exists and has the sha256 its list records (the approved bytes are frozen)
  17  pin        both 2.6.10 chain pins in guarded_chain.py match their lists, and each chain has its marked commit
  20  #385       a project's own folder: the mapping, its checks on save, a missing folder reported and never made, the archive slot
                 beside the folder (test_project_paths_385, test_project_paths_385_p2)
  21  #385       the four approved guarded diffs on a throwaway vault (test_project_paths_385_guarded)
  22  #385       the backup holds the setting: locations.project_paths lives in settings.json, and the zip carries system/config/
  25  #250       fetch transcripts: off by default, its catalogue row and wording, confidential and private meetings never fetched,
                 no minutes made (test_fetch_transcripts, test_fetch_settle, test_transcript_hold, the hostile tests)
  27  #250       G3, the live server's side of the fetch (test_live_fetch_250; skipped until the G3 diff lands)
  28  #250       G4, the rules bullet (test_rules_retained_338; skipped until the G4 diff lands)
  29  #329       shareable minutes: the words in the built page, and the shareable tests that need no browser
  30  #370       a missed check: Today and Health wording, Check now, the 24-hour retry time, and slices 1 and 2's tests
  31  #370       slice 3, the guarded live server patch (the second 2.6.10 chain) and its tests
  32  #374       file paths and Show in Finder (in 2.6.10)
  33  #366       the tests-only item's tests pass
  34  unchanged  approve and undo, and Health's Check now route, as before
  35  claims     the 2.6.10 notes never name #386 or #366, and name #374, #250, #385 and #370 only once their code (guarded part
                 too) is in

Run (from the repository root):  python3 dev/tests/handchecks/test_v2610.py      (about four minutes: the reused tests run one at a time)
"""
import hashlib
import itertools
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "system" / "scripts"))
sys.path.insert(0, str(REPO / "dev" / "tools"))
sys.path.insert(0, str(REPO / "dev" / "tests"))

GUARDED = ["system/creaite-rules.md", "system/scripts/tracker.py", "system/scripts/filechange.py", "system/scripts/reach.py",
           "system/scripts/permissions.py", "system/scripts/backup.py", "system/scripts/update.py", "system/scripts/live_server.py",
           "system/scripts/client_leak.py", "system/scripts/edit_ai.py", "system/scripts/draft_delivery.py", ".claude/settings.json"]
SCRIPTABLE = (11, 12, 13, 14, 15, 16, 17, 20, 21, 22, 25, 27, 28, 29, 30, 31, 32, 33, 34, 35)
KIND = {**{n: "scriptable" for n in SCRIPTABLE},
        1: "judgement", 2: "live-only", 3: "live-only", 4: "live-only", 5: "judgement", 6: "judgement", 7: "live-only",
        8: "live-only"}
LIVE_ONLY = {
    1: "with Alan: a project's own folder set with a ~ path; does the Folder row read plainly (wording)",
    2: "with Alan: a real offline OneDrive folder; creaite says it is missing and makes nothing, and works again when it is back",
    3: "with Alan: a real ended Teams meeting with a transcript reaches Intake from a dashboard check (real Microsoft 365)",
    4: "with Alan: the transcript links his real account returns are recognised (real Microsoft 365)",
    5: "with Alan: the shareable minutes warning's wording, on a meeting with a Sensitive decision",
    6: "with Alan: the Folder row, Activity's file and project names, and Show in Finder in the real Finder (only if #374 ships)",
    7: "with Alan: Microsoft 365 unavailable at a real check; Today's and Health's notice reads right and clears after a check",
    8: "with Alan: one approve and undo, Check now on Today (real Microsoft 365), open Files",
}
# The draft's checks and open points, and where each is covered (the sheet's table says the same).
DRAFT = {
    "check 1": (1, 20, 22), "check 2": (2, 20, 21), "check 3": (20, 21), "check 4": (3, 25, 27), "check 5": (4,),
    "check 6": (5, 29), "check 7": (6, 32), "check 8": (7, 30, 31), "check 9": (8, 34),
    "open point 1": (30, 31), "open point 2": (29,), "open point 3": (32, 35), "open point 4": (15, 16, 21),
    "open point 5": (25, 27, 28), "open point 6": (35,),
}
NOT_CUT = "VERSION is {}: this is the 2.6.10 release-shape check; it runs only at 2.6.10 (a later release's own test pins its shape)"
CHAIN = "dev/proposals/GUARDED-2.6.10.chain"
MARKER = "Guarded 2.6.10 chain:"
CHAIN_B = "dev/proposals/GUARDED-2.6.10b.chain"                     # the second 2.6.10 chain: #370 slice 3 rev 2, after G3
MARKER_B = "Guarded 2.6.10 chain (370 slice 3):"
CHAINS = ((CHAIN, MARKER), (CHAIN_B, MARKER_B))
S3_DIFF = "dev/proposals/370/live_server-370s3-rev2.diff"
S3_SHA256 = "4c56677a60ccd2ac932d837fd470f77bc6c919949bcfca51fd4cb1ba187cc1cf"
S3_TESTS = ("test_job_prompts_370", "test_handle_error_370", "test_catalogue_503_370")


def read(p):
    return (REPO / p).read_text(encoding="utf-8")


def git(*a):
    return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True)


def run_test(rel, *names):
    return subprocess.run([sys.executable, str(REPO / rel), *names], cwd=REPO, capture_output=True, text=True)


def version():
    return read("VERSION").strip()


def vkey(v):
    return tuple(int(x) for x in v.split("."))


def cut():
    return version() == "2.6.10"


def baseline_ref():
    """The 2.6.9 release: the tag v2.6.9, else the merge base with v269-release; None when neither exists here."""
    if git("rev-parse", "-q", "--verify", "refs/tags/v2.6.9").returncode == 0:
        return "refs/tags/v2.6.9"
    for ref in ("v269-release", "origin/v269-release"):
        if git("rev-parse", "-q", "--verify", ref).returncode == 0:
            mb = git("merge-base", ref, "HEAD").stdout.strip()
            if mb:
                return mb
    return None


# ---- what has landed (each marker is a name the approved diff or the branch adds) -------------------------------------------
def landed_385_guarded():
    return "def mapped_roots" in read("system/scripts/reach.py")


def landed_250_g3():
    return "def _fetch_finish" in read("system/scripts/live_server.py")


def landed_250_g4():
    return "Transcripts fetched by a sweep (#250)" in read("system/creaite-rules.md")


def landed_370_s3():
    return "RUN_LIMITS_370" in read("system/scripts/live_server.py")


def landed_374():
    return (REPO / "system/templates/dashboard/src/core/finderReveal.js").exists()


def chain_entries(chains=(CHAIN, CHAIN_B)):
    """[(diff path, [files it changes], sha256 the list records)] in landing order, the first 2.6.10 chain then the second; the
    first sha256 in the comment lines above a diff line is that diff's (later ones name other bytes, such as a result)."""
    out, sha = [], None
    for ln in (l for c in chains for l in read(c).splitlines()):
        s = ln.strip()
        if s.startswith("#"):
            m = re.search(r"sha256 ([0-9a-f]{64})", s)
            sha = sha or (m.group(1) if m else None)
            continue
        if s:
            p = REPO / s
            targets = re.findall(r"^\+\+\+ b/(\S+)", p.read_text(encoding="utf-8"), re.M) if p.exists() else []
            out.append((s, targets, sha))
            sha = None
    return out


def changed_guarded(ref):
    """Guarded files whose working-tree bytes differ from `ref` (committed or not)."""
    return sorted(git("diff", "--name-only", ref, "--", *GUARDED).stdout.split())


def applied(ref, f, diffs):
    """The bytes of f at ref with `diffs` applied in order, or None when one does not apply."""
    base = subprocess.run(["git", "show", f"{ref}:{f}"], cwd=REPO, capture_output=True)
    if base.returncode:
        return None
    with tempfile.TemporaryDirectory() as d:
        t = Path(d) / f
        t.parent.mkdir(parents=True)
        t.write_bytes(base.stdout)
        for diff in diffs:
            r = subprocess.run(["git", "apply", f"--include={f}", str(REPO / diff)], cwd=d, capture_output=True, text=True)
            if r.returncode:
                return None
        return t.read_bytes()


def spec_2610(marker=MARKER):
    """(guarded_chain, the spec for a 2.6.10 marker) once guarded_chain.py knows it; else (module, None)."""
    import guarded_chain as gc
    for k in dir(gc):
        if k.endswith("_MARKER") and getattr(gc, k) == marker:
            pre = k[:-len("_MARKER")]
            return gc, (marker, getattr(gc, pre + "_FILE", None), pre + "_SHA256")
    return gc, None


def wn_section():
    wn = read("system/templates/help/whats-new.md")
    if "## creaite 2.6.10\n" not in wn:
        return None
    return wn.split("## creaite 2.6.10\n", 1)[1].split("## creaite 2.6.9\n", 1)[0]


def plain_notes():
    p = REPO / "dev/release-notes/2.6.10-plain.md"
    return p.read_text(encoding="utf-8") if p.exists() else None


def shipped():
    return ["#385", "#250", "#329", "#370"] + (["#374"] if landed_374() else [])


class V2610(unittest.TestCase):
    def run_all(self, *files):
        """Each test file in turn (one process at a time); a missing file is a failure (it pins the behaviour)."""
        for f in files:
            rel = f"dev/tests/{f}.py"
            with self.subTest(f):
                self.assertTrue((REPO / rel).exists(), f"{rel} is missing")
                r = run_test(rel)
                self.assertEqual(r.returncode, 0, f"{rel} failed:\n" + (r.stderr or r.stdout)[-1500:])

    # ---- the release shape (skipped until the cut) --------------------------------------------------------------------------
    def test_c11_version(self):
        v = version()
        self.assertRegex(v, r"^\d+\.\d+\.\d+$")
        self.assertGreaterEqual(vkey(v), (2, 6, 9))

    def test_c12_notes(self):
        if not cut():
            self.skipTest(NOT_CUT.format(version()))
        wn = read("system/templates/help/whats-new.md")
        heads = re.findall(r"^## creaite (\d+\.\d+\.\d+)\s*$", wn, re.M)
        self.assertEqual(heads[:2], ["2.6.10", "2.6.9"])
        sec = wn_section()
        for n in shipped():
            self.assertIn(f"({n})", sec, f"What's new for 2.6.10 does not name {n}")
        self.assertTrue((REPO / "dev/release-notes/2.6.10-plain.md").exists())
        sheet = read("dev/handchecks/v2.6.10.md")
        self.assertGreaterEqual(len(re.findall(r"(?m)^\d+\. \*\*", sheet)), 8)
        self.assertIn("Not in 2.6.10", sheet)

    def test_c13_public_text(self):
        if not cut():
            self.skipTest(NOT_CUT.format(version()))
        for t in (wn_section(), plain_notes()):
            self.assertEqual(t.count("<!--"), t.count("-->"))
            self.assertNotIn("GUARDED", t)
        import whats_new
        self.assertTrue(whats_new.has("2.6.10"))
        r = run_test("dev/tests/test_no_real_names.py")
        self.assertEqual(r.returncode, 0, (r.stderr or r.stdout)[-1500:])

    def test_c14_guides(self):
        if not cut():
            self.skipTest(NOT_CUT.format(version()))
        for g in ("guide-first-day.html", "guide-how-to.html"):
            t = read(f"system/templates/{g}")
            self.assertIn("creaite 2.6.10 ·", t)
            self.assertNotRegex(t, r"creaite 2\.6\.\d ·")
            self.assertNotRegex(t, r"creaite-2\.6\.\d\.zip")
        self.assertIn("creaite-2.6.10.zip", read("system/templates/guide-first-day.html"))

    # ---- the guarded files and the 2.6.10 chain ------------------------------------------------------------------------------
    def test_c15_guarded_only_through_the_chain(self):
        """Each changed guarded file equals its 2.6.9 bytes with some of the listed diffs for it applied, in the listed order (the
        diffs apply in any order, so a part landing is allowed before the cut). At the cut: every listed diff in, nothing pending."""
        ref = baseline_ref()
        if ref is None:
            self.skipTest("neither the tag v2.6.9 nor v269-release exists here")
        entries = chain_entries()
        listed = sorted({t for _, ts, _ in entries for t in ts})
        changed = changed_guarded(ref)
        self.assertLessEqual(set(changed), set(listed),
                             f"guarded files changed since 2.6.9 outside the 2.6.10 chain: {sorted(set(changed) - set(listed))} "
                             "(they must travel as diffs under dev/proposals)")
        for f in changed:
            mine = [d for d, ts, _ in entries if f in ts]
            now = (REPO / f).read_bytes()
            ok = None
            for k in range(len(mine), 0, -1):
                for sub in itertools.combinations(mine, k):
                    if applied(ref, f, sub) == now:
                        ok = sub
                        break
                if ok:
                    break
            with self.subTest(f):
                self.assertIsNotNone(ok, f"{f} is not its 2.6.9 bytes plus listed diffs ({mine}): an edit outside the approved chain")
                if cut():
                    self.assertEqual(list(ok), mine, f"{f}: at the cut every listed diff for it is in")
        if cut():
            self.assertEqual(changed, listed, "at the cut every file the chain lists carries its diffs")
            for c in (CHAIN, CHAIN_B):
                self.assertNotRegex(read(c), r"(?m)^#\s*PENDING", f"at the cut nothing in {c} is pending")

    def test_c16_chain_bytes_frozen(self):
        entries = chain_entries()
        self.assertGreaterEqual(len(chain_entries((CHAIN,))), 6, "the 2.6.10 chain lists the six approved diffs (#385 x4, #250 G3 and G4)")
        self.assertEqual(chain_entries((CHAIN_B,)), [(S3_DIFF, ["system/scripts/live_server.py"], S3_SHA256)],
                         "the second 2.6.10 chain lists the #370 slice 3 rev 2 diff alone, with its approved sha256")
        for diff, targets, sha in entries:
            with self.subTest(diff):
                self.assertTrue((REPO / diff).exists(), f"{diff} is listed but missing")
                self.assertTrue(targets, f"{diff} changes no file")
                self.assertLessEqual(set(targets), set(GUARDED), f"{diff} changes a file that is not guarded")
                self.assertIsNotNone(sha, f"{diff} has no recorded sha256 on the line above it")
                self.assertEqual(hashlib.sha256((REPO / diff).read_bytes()).hexdigest(), sha,
                                 f"{diff} is not the approved bytes (the list records {sha})")

    def test_c17_chain_pin(self):
        for chain, marker in CHAINS:
            with self.subTest(chain):
                gc, spec = spec_2610(marker)
                self.assertIsNotNone(spec, f"guarded_chain.py has no pin for {marker!r}")
                self.assertEqual(spec[1], chain)
                pin = getattr(gc, spec[2], "")
                self.assertTrue(pin, f"the pin for {chain} is empty")
                self.assertEqual(gc.chain_digest(REPO, "HEAD", spec), pin, f"the pin is not the list in {chain}")
                self.assertNotIn("NOT pinned", read(chain).splitlines()[0])
                subjects = git("log", "--no-merges", "--format=%s").stdout.splitlines()
                self.assertTrue([s for s in subjects if s.startswith(marker)], f"no commit subject starts with {marker!r}")
        self.assertFalse(MARKER.startswith(MARKER_B) or MARKER_B.startswith(MARKER), "one 2.6.10 marker prefixes the other")
        self.run_all("test_guarded_chain")

    # ---- #385 a project's own folder (the draft's checks 1 to 3, open point 4) ----------------------------------------------
    def test_c20_project_own_folder(self):
        self.run_all("test_project_paths_385", "test_project_paths_385_p2")

    def test_c21_project_own_folder_guarded(self):
        self.run_all("test_project_paths_385_guarded")

    def test_c22_backup_holds_the_setting(self):
        import backup
        self.assertIn("system/config/", backup.RESTORABLE)
        self.assertIn("project_paths", read("system/scripts/paths.py"))
        defaults = json.loads(read("system/templates/settings-defaults.json"))
        self.assertIn("project_paths", defaults.get("locations", {}), "locations.project_paths is not a setting in settings.json")

    # ---- #250 fetch transcripts (the draft's checks 4 and 5, open point 5) --------------------------------------------------
    def test_c25_fetch_transcripts(self):
        defaults = json.loads(read("system/templates/settings-defaults.json"))
        self.assertIs(defaults["sweep"]["fetch_transcripts"], False, "fetching transcripts must be off by default")
        import settings_catalogue as sc
        row = sc.CATALOGUE["sweep.fetch_transcripts"]
        self.assertEqual(row[:2], ("Checking mail and Teams", "Fetch transcripts as they appear"))
        self.assertIn("Confidential meetings are never fetched.", row[2])
        t = read("system/scripts/transcripts.py")
        used = set(re.findall(r"\bminutes\.([a-z_]+)\(", t))
        self.assertLessEqual(used, {"processed_on", "stem"}, f"transcripts.py calls minutes.{sorted(used)}: a fetch must never make minutes")
        self.assertNotRegex(t, r"DRAFTS|staging/drafts", "a fetch must never write a draft")
        self.run_all("test_fetch_transcripts", "test_fetch_settle", "test_transcript_hold", "test_hostile_250",
                     "test_fetch_transcripts_hostile")

    def test_c27_fetch_live_server(self):
        if not landed_250_g3():
            self.skipTest("waits for the #250 G3 guarded diff (live_server-250.diff, marker Run._fetch_finish)")
        self.run_all("test_live_fetch_250")

    def test_c28_fetch_rules(self):
        if not landed_250_g4():
            self.skipTest("waits for the #250 G4 guarded diff (creaite-rules-250.diff)")
        self.run_all("test_rules_retained_338")

    # ---- #329 shareable minutes (the draft's check 6, open point 2) ----------------------------------------------------------
    def test_c29_shareable_minutes(self):
        page = read("system/templates/dashboard.html")
        for w in ("Review these lines before sharing", "Hold back with it", "Show in the shareable version", "Use a plain heading"):
            self.assertIn(w, page, f"the built page lacks {w!r}")
        self.run_all("test_minutes_shareable_329")

    # ---- #370 a missed check and smaller fixes (the draft's check 8, open point 1) -------------------------------------------
    def test_c30_missed_check(self):
        page = read("system/templates/dashboard.html")
        self.assertIn("Today's mail and Teams check didn't run.", page)
        self.assertIn("sweepFailedRun", page, "Today's notice has no Check now button")
        import health
        import health_fixes
        self.assertEqual(health.PLAIN["sweep_failed"][0], "A mail and Teams check didn't run")
        fix = health_fixes.FIXES["sweep_failed"]
        self.assertEqual((fix["title"], fix["button"]), ("A mail and Teams check didn't run", "Check now"))
        self.assertEqual(fix.get("body"), {"force": True}, "Health's Check now must start a missed check, never only offer one")
        self.run_all("test_sweep_failed_370", "test_log_level_health_370", "test_page_errors_370", "test_stale_events_370")

    def test_c31_smaller_fixes_s3(self):
        """Slice 3 is the second 2.6.10 chain: its names are in live_server.py, and its own tests pass. Those tests come with the #370
        branch (an ordinary merge, not the chain): until VERSION is 2.6.10 a missing one is skipped, at the cut it is a failure."""
        self.assertTrue(landed_370_s3(), "#370 slice 3 (the second 2.6.10 chain, marker RUN_LIMITS_370) is not in live_server.py")
        live = read("system/scripts/live_server.py")
        for name in ("def run_limits(kind)", "def _count_refusal(self, part)", "self._count_refusal(part)",
                     "def handle_error(self, request, client_address)", "def catalogue_lasting(e)"):
            self.assertIn(name, live, f"live_server.py lacks slice 3's {name!r}")
        present = [t for t in S3_TESTS if (REPO / f"dev/tests/{t}.py").exists()]
        for t in S3_TESTS:
            if t not in present:
                with self.subTest(t):
                    if cut():
                        self.fail(f"dev/tests/{t}.py is missing at the cut (it comes with the #370 branch)")
                    self.skipTest(f"dev/tests/{t}.py comes with the #370 branch, not merged here yet")
        self.run_all(*present)

    # ---- #374 file paths (the draft's check 7, open point 3) ------------------------------------------------------------------
    def test_c32_file_paths(self):
        if not landed_374():
            self.skipTest("waits for #374 (team-cap-374-rebased: Activity names, Show in Finder, the Folder row's real location)")
        self.assertRegex(read("system/templates/dashboard/src/core/finderReveal.js"), r"FINDER_REVEAL\s*=\s*true",
                         "#374's flip: Show in Finder selects the file itself")
        self.run_all("test_folder_real_location", "test_reveal_in_finder_374")

    # ---- #366, and nothing else changed --------------------------------------------------------------------------------------
    def test_c33_tests_only_item(self):
        self.run_all("test_track_crossed_366", "test_calendar_client_outputs", "test_confidential_paths")

    def test_c34_nothing_else_changed(self):
        r = run_test("dev/tests/test_tracker.py", "TrackerTests.test_apply_then_undo_restores_exact_state",
                     "TrackerTests.test_undo_skips_items_changed_since")
        self.assertEqual(r.returncode, 0, (r.stderr or r.stdout)[-1500:])
        self.run_all("test_health_fixes")

    def test_c35_notes_claim_only_what_is_in(self):
        texts = {n: t for n, t in (("What's new 2.6.10", wn_section()), ("2.6.10-plain.md", plain_notes())) if t is not None}
        if not texts:
            self.skipTest("no 2.6.10 notes yet")
        rules = {"#374": landed_374(), "#250": landed_250_g3(), "#385": landed_385_guarded(), "#370": landed_370_s3()}
        for name, t in texts.items():
            with self.subTest(name):
                for n in ("#386", "#366"):
                    self.assertNotIn(f"({n})", t, f"{name} names {n}, which is not in 2.6.10's notes")
                for n, ok in rules.items():
                    if f"({n})" in t:
                        self.assertTrue(ok, f"{name} names {n} but its code (with its guarded part) is not in the tree")


if __name__ == "__main__":
    unittest.main()
