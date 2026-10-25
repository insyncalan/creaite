"""#358 (v2.6.5): say what the mail check is doing. Page only; no guarded file.

Run: python3 dev/tests/test_mail_check.py     (needs Node for the classifier, Google Chrome for the browser tests; each skipped otherwise)

1. The classifier (src/core/mailCheck.js) under Node: every label kind, an allow-list on whole labels, Found N, the closing line,
   and mutants (each must fail the tests).
2. The pin: the page's marker equals live_server.PANEL_SWEEP_STEP, read as text by a regex (never imported).
3. The permanent leak gate (never relaxed): no subject, sender, command or other label text reaches the line, the badge, the live
   node, the closing line or the steps list. Static (every string the module draws is fixed) and in a browser.
4. A browser against the real live server with a stand-in `claude` that streams real tool labels: the line replaces the quip for a
   mail check only, no total or percentage, the end line, Found N from the check's own file, the badge with the chat closed, the
   announcement count, and the same at 900 px.
"""
import json
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
MC = REPO / "system/templates/dashboard/src/core/mailCheck.js"
LIVE = REPO / "system/scripts/live_server.py"
SECRET = "Zebra Quarterly Budget Teams Mail Calendar Channel"      # a subject that holds the words a loose match would hit

SCRIPT = """
const f = await import(%s); const out = {};
const L = ["Microsoft 365: outlook email search", "Microsoft 365: chat message search", "Microsoft 365: teams list chats",
  "Microsoft 365: teams list channel messages", "Microsoft 365: outlook calendar search", "Microsoft 365: read resource",
  "Microsoft 365: sharepoint search", "Searching mail", "Searching Teams chats", "Reading Teams chats", "Reading Teams channels",
  "Reading the calendar", "Reading a meeting, a message or a chat", "Searching SharePoint and OneDrive", "Staging what the sweep found",
  "ToolSearch", "Using cx-sweep", "Read SKILL.md", "Write followed.json", "Running sweep.py followed --out x",
  "Running tracker.py mail Teams Calendar Channel", "Microsoft 365: send mail", "Microsoft 365: outlook send mail", "", null, 7];
out.kinds = L.map(l => f.mcClassify(l));
let s = f.mcNew();
out.start = f.mcLine(s);
for (const l of L) s = f.mcStep(s, l);
out.after = s; out.line = f.mcLine(s); out.badge = f.mcBadge(s); out.places = f.mcPlaces(s);
let t = f.mcNew(); t = f.mcStep(t, "Microsoft 365: teams list chats"); t = f.mcStep(t, "Microsoft 365: outlook email search");
out.order = t.places; out.teamsFirstBadge = f.mcBadge(f.mcStep(f.mcNew(), "Microsoft 365: teams list chats"));
let u = f.mcStep(f.mcNew(), "Microsoft 365: read resource"); out.readOnly = [u, f.mcLine(u)];
let one = f.mcStep(f.mcStep(f.mcNew(), "Searching mail"), "Reading a meeting, a message or a chat"); out.one = f.mcLine(one);
out.isRun = [f.mcIsRun({sweep: true}), f.mcIsRun({kind: "sweep"}), f.mcIsRun({sweep: false, kind: "chat"}), f.mcIsRun(null)];
out.stamp = ["proposed-2026-10-25-0905-sweep.json", "proposed-2026-10-25-0905-sweep-3.json", "proposed-2026-10-25-0905-dashboard.json",
  "x/proposed-2026-10-25-0905-sweep.json", "proposed-2026-10-25-0905-sweepx.json", null].map(f.mcFileStamp);
const N = "new", U = "update";
const rows = [{file: "proposed-2026-10-25-0905-sweep.json", op: N, p: "ABC"}, {file: "proposed-2026-10-25-0905-sweep.json", op: N, p: ""},
  {file: "proposed-2026-10-25-0906-sweep-2.json", op: N, p: null}, {file: "proposed-2026-10-25-0905-dashboard-x.json", op: N, p: ""},
  {file: "proposed-2026-10-25-0850-sweep.json", op: N, p: ""}, {file: "proposed-2026-10-25-0920-sweep.json", op: N, p: ""}, {file: "m.docx", op: N, p: ""},
  {file: "proposed-2026-10-25-0905-sweep.json", op: U, p: ""}, {file: "proposed-2026-10-25-0906-sweep-2.json", op: U, p: "ABC"}, {file: "proposed-2026-10-25-0905-sweep.json", p: ""}];
out.found = f.mcFound(rows, "2026-10-25T09:04:10", "2026-10-25T09:10:59"); out.foundNone = f.mcFound([], "2026-10-25T09:04:10", "2026-10-25T09:10:59");
const two = f.mcStep(f.mcStep(f.mcNew(), "Searching mail"), "Reading Teams channels");
out.ends = [f.mcEnd("done", two, {n: 7, need: 4}), f.mcEnd("done", two, {n: 1, need: 1}), f.mcEnd("done", two, {n: 0, need: 0}), f.mcEnd("done", two, null),
  f.mcEnd("stopped", two, {n: 2, need: 1}), f.mcEnd("early", two, {n: 2, need: 2}), f.mcEnd("stopped", two, {n: 0, need: 0}), f.mcEnd("early", f.mcNew(), {n: 0, need: 0}),
  f.mcEnd("stopped", two, null),
  f.mcEnd("done", two, {n: 0, need: 0, upd: 3}), f.mcEnd("done", two, {n: 0, need: 0, upd: 1}), f.mcEnd("done", two, {n: 2, need: 1, upd: 3}),
  f.mcEnd("done", two, {n: 2, need: 1, upd: 0}), f.mcEnd("done", two, {n: 0, need: 0, upd: 0}), f.mcEnd("stopped", two, {n: 0, need: 0, upd: 2}),
  f.mcEnd("early", two, {n: 1, need: 0, upd: 1}), f.mcEnd("stopped", two, {n: 0, need: 0, upd: 0})];
out.stepText = ["Sweeping (stages proposals only)", "Microsoft 365: outlook email search", "Searching mail", "Running sweep.py followed --subject Q3", "Write followed-x.json", "Running tracker.py x", "ToolSearch", "Microsoft 365: nonsense"].map(f.mcStepText);
out.marker = f.MC_MARKER;
console.log(JSON.stringify(out));
"""


def run_node(path=MC, script=SCRIPT):
    src = Path(path).read_text(encoding="utf-8")
    tmp = HERE / ".mc_tmp"
    tmp.mkdir(exist_ok=True)
    f = tmp / "mailCheck.mjs"
    f.write_text(src, encoding="utf-8")
    r = subprocess.run(["node", "--input-type=module", "-e", script % json.dumps(f.as_uri())], capture_output=True, text=True, timeout=60)
    shutil.rmtree(tmp, ignore_errors=True)
    if r.returncode:
        raise RuntimeError(r.stderr)
    return json.loads(r.stdout)


def mutant(old, new):
    """Run the unit script against mailCheck.js with one change; returns the output."""
    src = MC.read_text(encoding="utf-8")
    assert old in src, old
    tmp = HERE / ".mc_mut"
    tmp.mkdir(exist_ok=True)
    f = tmp / "m.mjs"
    f.write_text(src.replace(old, new, 1), encoding="utf-8")
    r = subprocess.run(["node", "--input-type=module", "-e", SCRIPT % json.dumps(f.as_uri())], capture_output=True, text=True, timeout=60)
    shutil.rmtree(tmp, ignore_errors=True)
    return json.loads(r.stdout) if r.returncode == 0 else None


@unittest.skipUnless(shutil.which("node"), "needs Node")
class Classifier(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o = run_node()

    def test_every_label_kind(self):
        k = self.o["kinds"]
        S = lambda p: {"kind": "search", "place": p}
        self.assertEqual(k[:15], [S("mail"), S("teams"), S("teams"), S("teams"), S("calendar"), {"kind": "read"}, S(None),
                                  S("mail"), S("teams"), S("teams"), S("teams"), S("calendar"), {"kind": "read"}, S(None), None])
        # a Bash label, ToolSearch, Read and Write, the followed-people command, a send tool, nothing at all: nothing
        self.assertEqual(k[15:], [None] * 11)

    def test_an_allow_list_on_whole_labels_a_subject_changes_nothing(self):
        self.assertEqual(self.o["kinds"][20], None)               # "Running tracker.py mail Teams Calendar Channel"
        self.assertEqual(self.o["after"], {"places": ["mail", "teams", "calendar"], "searches": 12, "reads": 2})

    def test_the_line_has_no_total_no_percentage_and_no_claim_of_finished(self):
        self.assertEqual(self.o["start"], "Starting")
        self.assertEqual(self.o["line"], "Looked in so far: Outlook mail, Teams, calendar · 12 searches, 2 items read")
        self.assertNotRegex(self.o["line"], r"\bof \d|%|Done|Finished|\d/\d")
        self.assertEqual(self.o["one"], "Looked in so far: Outlook mail · 1 search, 1 item read")

    def test_places_are_a_set_in_a_fixed_order_and_a_read_is_never_a_place(self):
        self.assertEqual(self.o["order"], ["mail", "teams"])      # Teams first, mail second: still mail, Teams
        self.assertEqual(self.o["teamsFirstBadge"], "Mail check: Teams")
        self.assertEqual(self.o["readOnly"][0], {"places": [], "searches": 0, "reads": 1})
        self.assertEqual(self.o["readOnly"][1], "Starting")

    def test_the_badge_and_the_live_node_carry_places_only_never_a_counter(self):
        self.assertEqual(self.o["badge"], "Mail check: mail, Teams, calendar")
        self.assertEqual(self.o["places"], "Looked in so far: Outlook mail, Teams, calendar")
        self.assertFalse(re.search(r"\d", self.o["badge"] + self.o["places"]))

    def test_it_knows_a_mail_check_from_the_run_record(self):
        self.assertEqual(self.o["isRun"], [True, True, False, False])

    def test_found_n_counts_only_the_checks_own_files_inside_the_window(self):
        self.assertEqual(self.o["stamp"], ["2026-10-25T09:05", "2026-10-25T09:05", None, "2026-10-25T09:05", None, None])
        self.assertEqual(self.o["found"], {"n": 3, "need": 2, "upd": 2})    # not the dashboard row, not 08:50 or 09:20, not a docx, and no update items
        self.assertEqual(self.o["foundNone"], {"n": 0, "need": 0, "upd": 0})

    def test_the_closing_lines(self):
        e = self.o["ends"]
        self.assertEqual(e[0], "Finished. Looked in Outlook mail, Teams. Found 7 new, 4 need a project.")
        self.assertEqual(e[1], "Finished. Looked in Outlook mail, Teams. Found 1 new, 1 needs a project.")
        self.assertEqual(e[2], "Finished. Nothing new to review.")           # never "Found 0"
        self.assertEqual(e[3], "Finished. Open Review to see what it found.")
        self.assertEqual(e[4], "Stopped. Looked in Outlook mail, Teams. Found 2 new so far, 1 needs a project.")
        self.assertEqual(e[5], "Stopped early. Looked in Outlook mail, Teams. Found 2 new so far, 2 need a project.")
        self.assertEqual(e[6], "Stopped. Looked in Outlook mail, Teams. Nothing saved yet.")
        self.assertEqual(e[7], "Stopped early. Nothing saved yet.")
        self.assertEqual(e[8], "Stopped. Looked in Outlook mail, Teams.")
        # updates are never "nothing": update-only, mixed, new-only, neither
        self.assertEqual(e[9], "Finished. Looked in Outlook mail, Teams. No new items; 3 updates to existing items.")
        self.assertEqual(e[10], "Finished. Looked in Outlook mail, Teams. No new items; 1 update to an existing item.")
        self.assertEqual(e[11], "Finished. Looked in Outlook mail, Teams. Found 2 new, 1 needs a project, and 3 updates to existing items.")
        self.assertEqual(e[12], "Finished. Looked in Outlook mail, Teams. Found 2 new, 1 needs a project.")
        self.assertEqual(e[13], "Finished. Nothing new to review.")
        self.assertEqual(e[14], "Stopped. Looked in Outlook mail, Teams. No new items; 2 updates to existing items so far.")
        self.assertEqual(e[15], "Stopped early. Looked in Outlook mail, Teams. Found 1 new so far, none need a project, and 1 update to an existing item.")
        self.assertEqual(e[16], "Stopped. Looked in Outlook mail, Teams. Nothing saved yet.")

    PHRASES = ["sweep", "Sweep", "please sweep", "sweep mail", "sweep email", "sweep my mail", "sweep mail and teams", "sweep for ABC", "sweep mail for ABC",
               "sweep the last 7 days", "sweep mail the last 7 days", "sweep for ABC for the last 3 days", "sweep the Budget review thread", "sweep the A and B thread",
               "sweep the apply thread", "check my mail", "check mail", "check my email", "check email", "check email and teams", "check my mail and teams",
               "check my mail for ABC", "check my mail for urgent", "check mail the last 2 days", "refresh calendar", "refresh the calendar", "refresh my calendar",
               "refresh my calendar please", "sweep now", "sweep please.", "sweep and apply", "sweep then approve", "sweep for the", "sweep for me", "what did the sweep find",
               "hello", "", "  sweep   mail  ", "sweep the last 7 days and apply", "check my mail for abc", "check my mail for the last 7 days", "x" * 130,
               "sweep the last ٧ days", "check my mail the last ٣ days", "sweep for ABC for the last ١٠ days", "sweep the last ٧ days and apply", "sweep\x85mail",
               "sweep\ufeff", "sweep the ésend thread", "ſweep", "sweep the " + "é" * 60 + " thread", "sweep the " + "😀" * 71 + " thread", "x" * 120]

    def test_a_saved_chat_is_a_mail_check_by_the_servers_own_words(self):
        """The page's answer equals the server's panel_sweep for every phrasing (live_server imported only here, to compare)."""
        sys.path.insert(0, str(REPO / "system/scripts"))
        import live_server
        o = run_node(script="""const f = await import(%s); console.log(JSON.stringify(%s.map(f.mcIsAsk)));""" % ("%s", json.dumps(self.PHRASES)))
        self.assertEqual(o, [bool(live_server.panel_sweep(x)) for x in self.PHRASES])
        by = dict(zip(self.PHRASES, o))
        for yes in ("sweep the last ٧ days", "check my mail the last ٣ days", "sweep for ABC for the last ١٠ days"):
            self.assertTrue(by[yes], yes)                                                  # Arabic-Indic digits, as the server reads them
        for yes in ("check my email", "check email", "check email and teams", "refresh my calendar", "sweep", "please sweep", "check my mail"):
            self.assertTrue(by[yes], yes)
        for no in ("sweep and apply", "sweep then approve", "what did the sweep find", "hello", ""):
            self.assertFalse(by[no], no)

    def test_the_catch_ups_own_asks_count(self):
        o = run_node(script="""const f = await import(%s); console.log(JSON.stringify(f.MC_PLAIN_ASKS.map(f.mcIsAsk)));""")
        self.assertEqual(o, [True, True])
        sys.path.insert(0, str(REPO / "system/scripts"))
        import live_server
        src = LIVE.read_text(encoding="utf-8")
        page = MC.read_text(encoding="utf-8")
        for key in ("sweep", "calendar"):
            self.assertIn(live_server.PLAIN_ASK[key], re.search(r"MC_PLAIN_ASKS = (\[.*?\]);", page).group(1))
        self.assertIn("PLAIN_ASK = {", src)

    def test_drift_the_page_list_equals_the_servers_list(self):
        """DRIFT: reads live_server.py as text (ast, no import) and fails if the accepted forms and the page's copy differ by a character."""
        import ast
        tree = ast.parse(LIVE.read_text(encoding="utf-8"))
        srv = {}
        for n in tree.body:
            if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") in ("PANEL_SWEEP_WORDS", "PANEL_SWEEP_FOR", "PANEL_SWEEP_NOT", "PANEL_SWEEP_COMMON"):
                v = n.value
                srv[n.targets[0].id] = ast.literal_eval(v.args[0]) if isinstance(v, ast.Call) and getattr(v.func, "attr", "") == "compile" else \
                    sorted(ast.literal_eval(v.args[0])) if isinstance(v, ast.Call) else None
        self.assertEqual(set(srv), {"PANEL_SWEEP_WORDS", "PANEL_SWEEP_FOR", "PANEL_SWEEP_NOT", "PANEL_SWEEP_COMMON"})
        page = MC.read_text(encoding="utf-8")
        grab = lambda name: json.loads(re.search(r"^export const %s = (\".*\");$" % name, page, re.M).group(1))
        # the one intended difference: Python's \d matches every Unicode digit, so the page writes \p{Nd} (with the u flag)
        self.assertEqual(grab("MC_SWEEP_SRC"), srv["PANEL_SWEEP_WORDS"].replace("(?P<", "(?<").replace("\\d", "\\p{Nd}"))
        # the second intended difference: Python's \b is Unicode-aware, JavaScript's is not, so the page writes the word edges out
        edge = lambda rx: rx.replace("\\b", "\0", 2).replace("\0", "(?<![\\p{L}\\p{N}_])", 1).replace("\0", "(?![\\p{L}\\p{N}_])", 1)
        self.assertEqual(grab("MC_SWEEP_NOT"), edge(srv["PANEL_SWEEP_NOT"]))
        self.assertEqual(grab("MC_SWEEP_FOR"), edge(srv["PANEL_SWEEP_FOR"]))
        common = json.loads(re.search(r"^export const MC_SWEEP_COMMON = (\[.*\]);$", page, re.M).group(1))
        self.assertEqual(sorted(common), srv["PANEL_SWEEP_COMMON"])

    def test_the_drift_test_catches_a_change_on_either_side(self):
        page = MC.read_text(encoding="utf-8")
        self.assertNotEqual(page.replace("check (?:my )?", "check (?:my |the )?", 1), page)      # the mutation applies to the page's text
        mutated = json.loads(re.search(r"^export const MC_SWEEP_SRC = (\".*\");$", page.replace("check (?:my )?", "check (?:my |the )?", 1), re.M).group(1))
        server = LIVE.read_text(encoding="utf-8")
        self.assertNotIn(mutated.replace("(?<", "(?P<").replace("\\p{Nd}", "\\d"), server.replace("\n", ""))

    def test_the_steps_list_shows_fixed_phrases_only(self):
        self.assertEqual(self.o["stepText"], ["Sweeping (stages proposals only)", "Microsoft 365: outlook email search", "Searching mail",
                                              "A creaite step", "A creaite step", "A creaite step", "A creaite step", "A creaite step"])

    def test_mutants_fail(self):
        def broke(old, new, fn):
            o = mutant(old, new)
            self.assertTrue(o is None or fn(o), f"mutant survived: {old!r}")
        # a classifier that scans free text: the subject case must fail
        broke("return Object.prototype.hasOwnProperty.call(PLAIN, label) ? { kind: \"search\", place: PLAIN[label] } : null;",
              "return /mail/i.test(label) ? { kind: \"search\", place: \"mail\" } : null;", lambda o: o["kinds"][20] is not None or o["kinds"] != self.o["kinds"])
        # the highest index instead of a set: Teams before mail must fail
        broke("PLACE_ORDER.filter(p => p === c.place || s.places.includes(p))", "[c.place]", lambda o: o["order"] != ["mail", "teams"])
        # read_resource counted as a place
        broke("if (tool === READ_CHAT) return { kind: \"read\" };", "if (tool === READ_CHAT) return { kind: \"search\", place: \"mail\" };",
              lambda o: o["readOnly"][0]["places"] != [])
        # a total
        broke("return `Looked in so far: ${placeList(s, PLACE_NAMES)} · ${mcPlural(s.searches, \"search\", \"searches\")}",
              "return `Looked in so far: ${placeList(s, PLACE_NAMES)} · 1 of 4 · ${mcPlural(s.searches, \"search\", \"searches\")}", lambda o: o["line"] != self.o["line"])
        # a counter on the badge
        broke("`Mail check: ${placeList(s, PLACE_SHORT)}`", "`Mail check: ${placeList(s, PLACE_SHORT)} ${s.searches}`", lambda o: o["badge"] != self.o["badge"])
        # a dashboard row counted
        broke("sweep(?:-\\d+)?\\.json$", "(?:sweep|dashboard-x)(?:-\\d+)?\\.json$", lambda o: o["found"] != self.o["found"])
        # the raw label in the steps list
        broke("return c ? String(label) : \"A creaite step\";", "return String(label);", lambda o: o["stepText"] != self.o["stepText"])
        # update items counted as new
        broke("if (r.op === \"new\") { n++;", "if (r.op === \"new\" || r.op === \"update\") { n++;", lambda o: o["found"] != self.o["found"])
        # an update-only check described as nothing new
        broke("if (upd) return", "if (false) return", lambda o: o["ends"][9] != self.o["ends"][9])
        # updates dropped from a mixed check
        broke("${upd ? `, and ${updText}` : \"\"}", "", lambda o: o["ends"][11] != self.o["ends"][11])
        # "Found 0"
        broke("if (found.n) return `${head}${looked} Found", "if (true) return `${head}${looked} Found", lambda o: o["ends"][2] != self.o["ends"][2])


ROWS = REPO / "system/templates/dashboard/src/core/closeDayRows.js"


@unittest.skipUnless(shutil.which("node"), "needs Node")
class CloseDayRows(unittest.TestCase):
    """Close the day keeps its four rows; each ticks only from its own finished search and never from a script step."""

    @classmethod
    def setUpClass(cls):
        script = """
const f = await import(%s); const out = {};
const L = ["Searching mail", "Microsoft 365: outlook email search", "Searching Teams chats", "Reading Teams chats", "Microsoft 365: teams list chats",
  "Microsoft 365: chat message search", "Reading Teams channels", "Microsoft 365: teams list channel messages", "Reading the calendar",
  "Staging what the sweep found", "Running sweep.py stage mail Teams channel", "Matching to projects", "Reading Teams", "", null];
out.rows = L.map(f.cdSourceOf);
out.now = [f.cdNow({steps: 0, done: []}), f.cdNow({steps: 1, done: []}), f.cdNow({steps: 2, done: [1]}), f.cdNow({steps: 3, done: [0, 1]}),
  f.cdNow({steps: 4, done: [0, 1, 2]}), f.cdNow({steps: 1, done: [2]})];
console.log(JSON.stringify(out));
"""
        cls.o = run_node(ROWS, script)

    def test_rows_tick_from_their_own_whole_labels_only(self):
        self.assertEqual(self.o["rows"], [0, 0, 1, 1, 1, 1, 2, 2, -1, -1, -1, -1, -1, -1, -1])

    def test_nothing_is_now_before_the_first_step_and_matching_to_projects_is_never_now(self):
        n = self.o["now"]
        self.assertEqual(n[0], -1)             # before any step every row waits
        self.assertEqual(n[1], 0)
        self.assertEqual(n[2], 0)              # Teams chats done first: mail is still the first not done
        self.assertEqual(n[3], 2)
        self.assertEqual(n[4], -1)             # all three done: nothing shows as now, the fourth row never does
        self.assertEqual(n[5], 0)

    def test_a_mutant_that_ticks_on_free_text_fails(self):
        src = ROWS.read_text(encoding="utf-8")
        tmp = HERE / ".mc_rows"
        tmp.mkdir(exist_ok=True)
        f = tmp / "m.mjs"
        f.write_text(src.replace("return CD_LABELS.findIndex(l => l.includes(label));", "return /channel/i.test(label) ? 2 : /mail/i.test(label) ? 0 : -1;"))
        r = subprocess.run(["node", "--input-type=module", "-e", """const f = await import(%s); console.log(JSON.stringify(["Running sweep.py stage mail Teams channel"].map(f.cdSourceOf)));""" % json.dumps(f.as_uri())],
                           capture_output=True, text=True)
        shutil.rmtree(tmp, ignore_errors=True)
        self.assertNotEqual(json.loads(r.stdout), [-1])


class Pin(unittest.TestCase):
    def test_the_page_marker_equals_the_servers_marker(self):
        """Read as text, never imported (importing live_server would run it): a changed letter on either side fails."""
        server = re.search(r'^PANEL_SWEEP_STEP = "([^"\n]*)"$', LIVE.read_text(encoding="utf-8"), re.M)
        page = re.search(r'^export const MC_MARKER = "([^"\n]*)";', MC.read_text(encoding="utf-8"), re.M)
        self.assertTrue(server and page, "both constants must be plain strings on one line")
        self.assertEqual(page.group(1), server.group(1))
        self.assertEqual(server.group(1), "Sweeping (stages proposals only)")

    def test_the_pin_catches_a_one_letter_change_on_either_side(self):
        a = 'PANEL_SWEEP_STEP = "Sweeping (stages proposals only)"'
        for text, rx in ((a.replace("Sweeping", "Sweepinq"), r'^PANEL_SWEEP_STEP = "([^"\n]*)"$'),):
            self.assertNotEqual(re.search(rx, text, re.M).group(1), "Sweeping (stages proposals only)")


class LeakGate(unittest.TestCase):
    """Permanent. The module draws only fixed phrases and whole numbers; this is never relaxed."""

    def test_no_label_text_is_ever_returned_by_a_drawing_function(self):
        src = MC.read_text(encoding="utf-8")
        for fn in ("mcLine", "mcBadge", "mcPlaces", "mcEnd", "mcStepText"):
            body = src[src.index(f"export function {fn}") if f"export function {fn}" in src else src.index(f"export const {fn}"):]
            body = body[:body.index("\n}\n") if "\n}\n" in body[:900] else 400]
            self.assertNotRegex(body, r"\blabel\b.*\$\{|\$\{[^}]*label", f"{fn} must not interpolate a label")

    def test_a_vip_word_is_in_no_new_string(self):
        self.assertNotRegex(MC.read_text(encoding="utf-8").lower(), r"\bvip\b")

    @unittest.skipUnless(shutil.which("node"), "needs Node")
    def test_hostile_labels_leave_no_trace_in_any_output(self):
        script = """
const f = await import(%s); const bad = [%s, "Running sweep.py followed --subject " + %s, "Microsoft 365: " + %s, %s + " Searching mail", "Write " + %s];
let s = f.mcNew(); for (const l of bad) s = f.mcStep(s, l);
const outs = [f.mcLine(s), f.mcBadge(s), f.mcPlaces(s), f.mcEnd("done", s, {n: 1, need: 1}), f.mcEnd("early", s, null), ...bad.map(f.mcStepText)];
console.log(JSON.stringify({s, outs}));
""" % ("%s", json.dumps(SECRET), json.dumps(SECRET), json.dumps(SECRET), json.dumps(SECRET), json.dumps(SECRET))
        o = run_node(script=script)
        self.assertEqual(o["s"], {"places": [], "searches": 0, "reads": 0})
        for out in o["outs"]:
            self.assertNotIn("Zebra", out)


# ── the browser ──

FAKE = r'''#!/usr/bin/env python3
import json, sys, time
from datetime import datetime
from pathlib import Path
args = sys.argv[1:]
message = args[args.index("--") + 1]
root = Path.cwd()
out = lambda o: print(json.dumps(o), flush=True)
M = "mcp__claude_ai_Microsoft_365__"
n = [0]
def call(name, inp=None, error=False, pause=0.35):
    n[0] += 1
    out({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": f"t{n[0]}", "name": name, "input": inp or {}}]}})
    time.sleep(pause)
    out({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": f"t{n[0]}", "is_error": error, "content": "x"}]}})
out({"type": "system", "subtype": "init", "session_id": "sess-1"})
low = message.lower()
if low.startswith(("sweep", "refresh")):
    slow = (root / "slow-sweep").exists()
    if low.startswith("refresh"):
        call(M + "outlook_calendar_search")
        reply = "Calendar refreshed."
    else:
        call("Bash", {"command": "system/scripts/run sweep.py followed --subject SECRETSUBJECT Zebra Quarterly Budget Teams Mail Calendar Channel"})
        call(M + "outlook_email_search")
        call("ToolSearch")
        call(M + "outlook_email_search", error=True)
        call(M + "outlook_email_search")
        call(M + "chat_message_search")
        call(M + "read_resource")
        if slow:
            time.sleep(40)
        if (root / "fail-sweep").exists():
            sys.stderr.write("the stand-in claude failed\n")
            sys.exit(3)
        call(M + "teams_list_channel_messages")
        call(M + "read_resource")
        call(M + "outlook_calendar_search")
        call(M + "sharepoint_search")
        call("Bash", {"command": "system/scripts/run sweep.py stage x"})
        now = datetime.fromtimestamp(time.time())      # the stand-in's own wall clock, like the server it drives
        item = lambda n, proj: {"n": n, "op": "new", "table": "actions", "match": "strong" if proj else "none", "flags": [], "decision": "pending",
                                "values": {"project": proj, "description": f"Share the plan {n}", "owner": "Alan Carter", "raised": now.strftime("%Y-%m-%d"),
                                           "source": "Email · Subject: Zebra"}}
        (root / "system/staging" / f"proposed-{now:%Y-%m-%d-%H%M}-sweep.json").write_text(json.dumps(
            {"created": now.strftime("%Y-%m-%dT%H:%M:00"), "source_run": "cx-sweep", "files": [], "items": [item(1, "ABC"), item(2, "")]}))
        reply = "Swept."
else:
    reply = "All done."
out({"type": "assistant", "message": {"content": [{"type": "text", "text": reply}]}})
out({"type": "result", "result": reply, "session_id": "sess-1"})
'''

FIXED_STEPS = {"Sweeping (stages proposals only)", "A creaite step", "Microsoft 365: outlook email search", "Microsoft 365: chat message search",
               "Microsoft 365: teams list channel messages", "Microsoft 365: outlook calendar search", "Microsoft 365: read resource",
               "Microsoft 365: sharepoint search"}


try:
    from live_browser import LiveBrowserCase as _Live
except Exception:                                   # no Chrome helper here: the browser tests are not collected
    _Live = object


class MailCheckBrowser(_Live):
    width, height = 1400, 900

    @classmethod
    def load(cls, v):
        from test_dashboard import populate
        populate(v)
        fake = v.root / "fake_claude.py"
        fake.write_text(FAKE)
        fake.chmod(0o755)

    @classmethod
    def server_env(cls):
        return {"CREAITE_CLAUDE": str(cls.v.root / "fake_claude.py")}

    def begin(self, message, chat_open=True):
        b = self.b
        b.eval("openChat()" if chat_open else "closeChat()")
        b.eval(f"window.P=askLive({message!r},null).catch(()=>{{}}); 0")
        if not chat_open:
            b.eval("closeChat()")
        b.wait("RB.state==='running'", 20)

    def finish(self, timeout=90):
        self.b.wait("window.P&&RB.state!=='running'", timeout)
        self.b.pump(0.6)

    def text_of(self, sel):
        return self.b.eval(f"[...document.querySelectorAll({sel!r})].map(e=>e.textContent).join(' | ')")

    def everything(self):
        return self.b.eval("""document.body.innerText+' '+[...document.querySelectorAll('[title],[aria-label]')].map(e=>(e.title||'')+' '+(e.getAttribute('aria-label')||'')).join(' ')+' '+
          [...document.querySelectorAll('#chLog details li')].map(e=>e.textContent).join(' ')""")

    def test_the_true_line_replaces_the_quip_and_ends_with_found_n(self):
        b = self.b
        self.begin("sweep")
        b.wait("!!document.querySelector('#chLog .mcline')&&/Looked in so far: Outlook mail/.test(document.querySelector('#chLog .mcline').textContent)", 40)
        self.assertEqual(b.eval("document.querySelectorAll('#chLog .step.working .quip').length"), 0)       # the quip is replaced for a mail check
        seen = []
        for _ in range(120):
            seen.append(b.eval("(document.querySelector('#chLog .mcline')||{}).textContent||''"))
            if b.eval("RB.state")!="running":
                break
            b.pump(0.25)
        line = [x for x in seen if x][-1]
        self.assertRegex(line, r"^Looked in so far: Outlook mail, Teams, calendar · \d+ searches, \d+ items read$")
        self.assertNotRegex(" ".join(seen), r"\bof \d|%|Finished|Done")
        self.finish()
        end = b.eval("[...document.querySelectorAll('#chLog .msg.runend')].pop().textContent")
        self.assertEqual(end, "Finished. Looked in Outlook mail, Teams, calendar. Found 2 new, 1 needs a project.")
        # the permanent leak gate: nothing from the labels reaches the page
        every = self.everything()
        for bad in ("SECRETSUBJECT", "Zebra", "followed"):
            self.assertNotIn(bad, every)
        steps = b.eval("[...document.querySelectorAll('#chLog .step.steps li')].map(e=>e.textContent)")
        self.assertTrue(steps and set(steps) <= FIXED_STEPS, steps)

    def test_a_saved_mail_check_chat_shows_fixed_phrases_only(self):
        """The saved history keeps the raw step labels (a subject, the followed-people command); drawing it applies the allow-list."""
        b = self.b
        self.begin("sweep")
        self.finish()
        chat = b.eval("ASKCHAT")
        saved = "".join(f.read_text() for f in (self.v.root / "system/staging/ask").glob("*.json"))
        self.assertIn("SECRETSUBJECT", saved)                                   # the precondition: the raw label is in the saved chat
        b.reload("typeof go==='function' && LIVE")                              # the live steps are gone: only the saved chat can draw them
        b.eval(f"openChat(); loadChat({chat!r}, false); 0")
        b.wait("document.querySelectorAll('#chLog .step.steps li').length>0", 20)
        steps = b.eval("[...document.querySelectorAll('#chLog .step.steps li')].map(e=>e.textContent)")
        self.assertTrue(set(steps) <= FIXED_STEPS, steps)
        self.assertNotIn("SECRETSUBJECT", self.everything())

    def test_only_a_mail_check_loses_the_quip(self):
        b = self.b
        self.begin("hello")
        self.assertEqual(b.eval("document.querySelectorAll('#chLog .mcline').length"), 0)
        self.finish()
        self.assertEqual(b.eval("document.querySelectorAll('#chLog .msg.runend').length"), 0)

    def test_refresh_calendar_ends_with_nothing_new(self):
        self.begin("refresh calendar")
        self.finish()
        end = self.b.eval("[...document.querySelectorAll('#chLog .msg.runend')].pop().textContent")
        self.assertEqual(end, "Finished. Nothing new to review.")

    def test_the_badge_with_the_chat_closed_shows_places_only_and_fits(self):
        b = self.b
        b.eval("window.AN=[]; for (const [id,n] of [['rbL','badge'],['askLive','live'],['mcLive','node'],['chLog','log']]) { let last=document.getElementById(id).textContent; "
               "new MutationObserver(()=>{ const t=document.getElementById(id).textContent; if(t!==last){ last=t; AN.push([n,t]); } }).observe(document.getElementById(id),{childList:true,characterData:true,subtree:true}); } 0")
        self.begin("sweep", chat_open=False)
        b.wait("/Mail check: mail/.test(document.getElementById('rbL').textContent)", 40)
        o = b.eval("(()=>{ const l=document.getElementById('rbL'), r=document.getElementById('runBadge').getBoundingClientRect(); return {text:l.textContent, title:l.title, clipped:l.scrollWidth>l.clientWidth, inside:r.left>=0&&r.right<=innerWidth}; })()")
        self.assertFalse(re.search(r"\d", o["text"]))                       # never a counter in the badge
        self.assertTrue(o["inside"])
        self.finish()
        an = b.eval("AN")
        places = [t for n, t in an if n == "badge" and t.startswith("Mail check")]
        self.assertLessEqual(len(places), 3, places)                                # at most three place changes on the badge
        self.assertLessEqual(len([1 for n, t in an if n == "node" and t]), 3)
        self.assertEqual(self.b.eval("document.getElementById('mcLive').textContent"), "")
        live = [t for n, t in an if n == "live"]
        self.assertEqual(len(live), 1)                                      # one end announcement, with Found N once
        self.assertIn("Found 2 new, 1 needs a project", live[0])
        self.assertEqual(len([1 for n, t in an if n == "badge" and t.startswith("took")]), 1)

    def test_with_the_chat_open_the_closing_line_is_readable_and_the_node_is_not_the_log(self):
        b = self.b
        self.assertEqual(b.eval("(()=>{ const n=document.getElementById('mcLive'); return n.closest('#chat')!==null && !n.closest('#chLog'); })()"), True)
        self.begin("sweep")
        self.finish()
        self.assertEqual(b.eval("[...document.querySelectorAll('#chLog .msg.runend')].pop().closest('[aria-hidden=true]')"), None)
        self.assertEqual(b.eval("document.getElementById('askLive').textContent"), "")

    def test_a_reload_mid_run_rebuilds_the_line_from_the_run_record(self):
        b = self.b
        (self.v.root / "slow-sweep").write_text("")
        self.begin("sweep")
        b.wait("/Looked in so far: Outlook mail, Teams/.test(document.querySelector('#chLog .mcline')?.textContent||'')", 40)
        want = "Looked in so far: Outlook mail, Teams · 3 searches, 1 item read"     # the failed search is not counted
        b.wait(f"document.querySelector('#chLog .mcline').textContent==={want!r}", 40)
        b.reload("typeof go==='function' && LIVE")
        b.eval("openChat()")
        b.wait(f"(document.querySelector('#chLog .mcline')||{{}}).textContent==={want!r}", 40)
        after = b.eval("document.querySelector('#chLog .mcline').textContent")
        self.assertEqual(after, want)                                       # the same places and counts, replayed from the start
        self.assertEqual(b.eval("document.querySelectorAll('#chLog .step.working .quip').length"), 0)
        b.eval("stopAsk()")
        b.pump(1.0)
        (self.v.root / "slow-sweep").unlink()

    def test_the_abort_path_still_writes_a_stopped_line(self):
        """The Stop route could not reach the server: the page cancels its own read. The closing line is still drawn."""
        b = self.b
        (self.v.root / "slow-sweep").write_text("")
        self.begin("sweep")
        b.wait("/Looked in so far: Outlook mail, Teams/.test(document.querySelector('#chLog .mcline')?.textContent||'')", 40)
        b.eval("RUN.ctl.abort(); 0")
        self.finish(30)
        end = b.eval("[...document.querySelectorAll('#chLog .msg.runend')].pop().textContent")
        self.assertRegex(end, r"^Stopped\. Looked in Outlook mail, Teams\.")
        (self.v.root / "slow-sweep").unlink()
        b.pump(1.0)

    def test_a_reload_with_no_saved_reply_still_ends_with_a_line(self):
        """Reload mid-run, let the check finish while the chat is closed, then a finished run is attached again from its record."""
        b = self.b
        self.begin("sweep")
        b.reload("typeof go==='function' && LIVE")
        b.wait("RB.state==='running'||RB.state==='done'", 40)
        b.wait("RB.state!=='running'", 90)
        b.pump(1.0)
        b.eval("openChat()")
        b.pump(1.0)
        last = b.eval("[...document.querySelectorAll('#chLog .msg.runend')].map(m=>m.textContent).pop()||''")
        live = b.eval("document.getElementById('askLive').textContent")
        self.assertTrue(last.startswith("Finished.") or "Found 2 new, 1 needs a project" in live or "Finished." in live, (last, live))

    def test_stopped_and_failed_endings(self):
        b = self.b
        (self.v.root / "slow-sweep").write_text("")
        self.begin("sweep")
        b.wait("/Looked in so far: Outlook mail, Teams/.test(document.querySelector('#chLog .mcline')?.textContent||'')", 40)
        b.eval("stopAsk()")
        self.finish(60)
        end = b.eval("[...document.querySelectorAll('#chLog .msg.runend')].pop().textContent")
        self.assertRegex(end, r"^Stopped\. Looked in Outlook mail, Teams\. Nothing saved yet\.$")
        (self.v.root / "slow-sweep").unlink()
        for _ in range(40):
            if b.eval("api('/api/ask/running').then(r=>!(r.ok&&r.run&&!r.run.done))"):
                break
            b.pump(0.25)
        (self.v.root / "fail-sweep").write_text("")
        self.begin("sweep")
        self.finish()
        end = b.eval("[...document.querySelectorAll('#chLog .msg.runend')].pop().textContent")
        self.assertRegex(end, r"^Stopped early\. Looked in Outlook mail, Teams\. ")
        (self.v.root / "fail-sweep").unlink()


if _Live is not object:
    class MailCheck1400(MailCheckBrowser):
        width, height = 1400, 900

    class MailCheck900(MailCheckBrowser):
        width, height = 900, 800

if __name__ == "__main__":
    unittest.main()
