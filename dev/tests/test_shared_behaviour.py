"""BL-316: one keyboard script on every menu, picker and dialog on every screen (dev/COMPONENTS.md §3), the shared check
both teams' screen branches work to (v1.9.5, step 2).

**What is checked.** Every visible control that opens a popup (it says so with aria-haspopup) is driven the same way, with
real key presses: focus it and press Enter: the popup opens, the control says so (aria-expanded) and focus goes into it; in a
menu or a list, ↓ and ↑ move between its items; Esc closes it and focus is back on the control that opened it; opened again,
Tab closes a menu or a list. A dialog keeps Tab inside itself, so for a dialog only Enter and Esc are checked. ⌘K, the one
dialog opened by a key from anywhere, gets the same Enter-less script from the key; the archive prompt (#parchDlg, opened by
Archive only when the server finds open items) gets the dialog script from its Archive button. Three more dialogs no aria-haspopup
control opens each get a script of their own (KEYED, #88): the date prompt (#boardDlg: Enter on a board card's Move button, Enter on a
column), Compare a repeat (#llDlg: Enter on Compare in the peek of a proposal marked as a repeat; Esc must not also close that peek) and
the search preview (#searchPrev: Enter on a vault-search result; the preview's server answer is stood in for). Each puts the page back
as it found it, whatever it finds. **Undo:** in a second sample vault each
menu and list is opened once more and an item chosen (↓, Enter); when that saves a change, the message at the foot (or, in
the peek, its staging bar's Undo last) must offer Undo (and Undo is pressed, so the next control sees the sample as it was). Each screen is the snapshot sample vault's
(test_snapshots), at 1400 by 1000.

**Every popup in the code is counted.** inventory() reads the dashboard's source (src/ and shell.html, the building blocks'
own files left out, as check.py's OLD count does) for every place that makes a menu, picker or dialog: a Dialog, openMenu,
a Menu or MenuPanel, a FilterBar, the Picker block's lists, calendars and popovers, the old pickers (the peek's list, popover and date helpers in panel.js), the right-click menu (cxOpen), the owner
combobox, a hand-made popover (aria-controls) and a control in markup that says aria-haspopup with its own name. Each one
must be reached by the keyboard script on some screen; one that isn't is a finding ("unreached": no control on the sample's
screens opens it with aria-haspopup, so a keyboard or screen-reader user isn't told it is there).

**Known failures.** dev/tests/behaviour_expected_failures.json lists what fails today, by screen area (check.py's
OLD_AREAS), so the test passes now. A screen branch that fixes one removes its line: the test fails on a new failure and
on a listed one that now passes, so the list only shrinks. BL-316 is done when it is empty.

SB_REPORT=1 prints every opener's result as a table (the audit's raw data) and the inventory; SB_ONLY=today,work runs only
those screens (the "unreached" lines are then not judged).

The keys test runs in three files and the Undo half in two (#89; KEYS_PARTS and UNDO_PARTS): this one holds the helpers, part a, and the Chrome-less tests.

Run: python3 dev/tests/test_shared_behaviour.py   (needs Google Chrome; the inventory test runs without it)
"""
import json
import os
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "tools"))
import check  # noqa: E402
import test_ui_sweep as us  # noqa: E402

PROBE = (HERE / "behaviour_probe.js").read_text(encoding="utf-8")
EXPECTED_FILE = HERE / "behaviour_expected_failures.json"
WITNESS_FILE = HERE / "behaviour_witness.json"

# v2.0.0 (#88): Notes. "notes" is the project's Notes tab (its New note button opens #newNoteDlg); "notes-ai" is a note with its
# text selected (⌘A), which shows the AI bar and its AI menu (AiSelect). The note is made once through the real controls
# (New note, a title, Make the note, then typed words); later visits open it by its address. The sample vault is a temporary copy.
NOTE = {}


def _notes_open(b):
    b.eval("go('notes','ABC')")
    b.wait("!!document.getElementById('notesNew')", 15)


def _note_made(b):
    origin = b.eval("location.origin")
    if NOTE.get("origin") != origin:                 # each test class has a sample vault (and server) of its own
        NOTE.clear()
        NOTE["origin"] = origin
    if "path" not in NOTE:
        _notes_open(b)
        b.click("#notesNew")
        b.wait("document.getElementById('newNoteDlg').open")
        b.eval("(()=>{ const i=document.getElementById('nnTitle'); i.value='Keyboard check'; i.dispatchEvent(new Event('input',{bubbles:true})); })()")
        b.click("#nnMake")
        b.wait("noteCur.value&&noteCur.value.note.title==='Keyboard check'&&!!document.querySelector('#v-notes .nbody.ProseMirror')", 15)
        NOTE["path"] = b.eval("noteCur.value.path")
        b.eval("document.querySelector('#v-notes .nbody').cxed.focus('end')")
        b.wait("document.activeElement===document.querySelector('#v-notes .nbody')", 5)
        b.type("Phase 1 go-live probably moves two weeks.")
        b.pump(0.5)
    else:
        b.eval(f"go('notes','ABC'); location.hash='#notes=ABC&n='+encodeURIComponent({json.dumps(NOTE['path'].rsplit('/', 1)[1])})")
        b.wait(f"noteCur.value&&noteCur.value.path==={json.dumps(NOTE['path'])}&&!!document.querySelector('#v-notes .nbody [data-p]')", 15)


def _notes_ai(b):
    _note_made(b)
    b.click("#v-notes .nbody")
    for attempt in (1, 2, 3):                        # #152: a ⌘A that arrives before the editor has taken its focus selects nothing
        b.wait("document.activeElement===document.querySelector('#v-notes .nbody')", 5)
        b.frames(3)
        b.key("a", 4)                                # ⌘A: all of the text, which shows the sparkle in the margin (#117)
        try:
            b.wait("document.querySelector('#aiLayer .aispark')", 5)
            break
        except TimeoutError:
            if attempt == 3:
                raise
    b.click("#aiLayer .aispark")                     # the sparkle opens the AI bar
    b.pump(0.3)


def _notes_session(b):
    """A Working session note open (its header has the Date box and its calendar pop-up, #115). Made once through the real controls."""
    origin = b.eval("location.origin")
    if NOTE.get("origin") != origin:
        NOTE.clear()
        NOTE["origin"] = origin
    if "session" not in NOTE:
        _notes_open(b)
        b.click("#notesNew")
        b.wait("document.getElementById('newNoteDlg').open")
        b.eval("(()=>{ const i=document.getElementById('nnTitle'); i.value='Session check'; i.dispatchEvent(new Event('input',{bubbles:true})); })()")
        b.eval("document.querySelector('#newNoteDlg input[value=\"working-session\"]').click()")
        b.click("#nnMake")
        b.wait("noteCur.value&&noteCur.value.note.title==='Session check'&&!!document.getElementById('noteDateBtn')", 15)
        NOTE["session"] = b.eval("noteCur.value.path")
    else:
        b.eval(f"go('notes','ABC'); location.hash='#notes=ABC&n='+encodeURIComponent({json.dumps(NOTE['session'].rsplit('/', 1)[1])})")
        b.wait(f"noteCur.value&&noteCur.value.path==={json.dumps(NOTE['session'])}&&!!document.getElementById('noteDateBtn')", 15)


SCREENS = dict(us.SCREENS)
SCREENS.pop("cmdk", None)              # ⌘K is itself the dialog: opened by its key (CMDK below); its list is test_cmdk's
SCREENS["shell"] = ("go('today')", "!document.getElementById('v-today').hidden", ".shell")   # the sidebar and the top bar
us.SCREENS["shell"] = SCREENS["shell"]
# #251: Today's milestone rows (Needs attention) have an Options menu. The sample's UAT start (ABC-M-001) has open actions but is
# forecast outside the Due soon window, so for the keys test alone (Keys.goto; in memory only, again on every visit) it is forecast
# three days ahead. The Undo check keeps the plain Today: its menu's "Open it in Work" would leave Work filtered for later screens.
KEYS_GO = {"today": ("(()=>{ const m=P.flatMap(p=>p.ms||[]).find(m=>m[3]==='ABC-M-001'); if(m) m[8]=pkAdd(TODAY,3); go('today'); renderToday(); })()",
                     "!!document.querySelector('#attnList li[data-msattn] .dots')", "#v-today")}
SCREENS["today-days"] = ("D.calendar={fetched:TODAY+' 07:00',days:{}}; D.days={first:pkAdd(TODAY,-1),last:TODAY,today:TODAY,fetched:null,days:[{date:pkAdd(TODAY,-1),dow:'Monday',short:'Mon 1',long:'Monday',today:false,past:true,weekend:false,week:0,meetings:[],all_day:[]},"
                         "{date:TODAY,dow:'Tuesday',short:'Tue 2',long:'Tuesday',today:true,past:false,weekend:false,week:0,meetings:[],all_day:[]}]}; go('today'); renderToday()",
                         "!!document.querySelector('#todayDate .dypastbtn')", "#v-today")   # #147: the day line's earlier-days menu needs a calendar with a past day
SCREENS["notes"] = (_notes_open, "!!document.getElementById('notesNew')", "#v-notes")
SCREENS["notes-ai"] = (_notes_ai, "!!document.querySelector('#aiLayer .aibar')", "#aiLayer")
SCREENS["notes-session"] = (_notes_session, "!!document.getElementById('noteDateBtn')", "#v-notes")
us.SCREENS["notes"], us.SCREENS["notes-ai"], us.SCREENS["notes-session"] = SCREENS["notes"], SCREENS["notes-ai"], SCREENS["notes-session"]
# The sample has no approved internal week, which keeps Check and export disabled: the client draft is answered as ready here
# (nothing is written; the check and the export still go to the server, and Esc is all the script presses).
SCREENS["clientreport"] = ("(()=>{ if(!window.__crReady){ window.__crReady=1; const f=window.fetch.bind(window); window.fetch=(u,o)=>{ const r=f(u,o); "
                           "if(!String(u).endsWith('/api/report/draft')||!o||!String(o.body).includes('\"client\"')||String(o.body).includes('\"weekly\"')) return r; "
                           "return r.then(x=>x.json()).then(j=>new Response(JSON.stringify({...j,ready:true}),{headers:{'Content-Type':'application/json'}})); }; } "
                           "go('clientreport',{code:'ABC',week:'2026-10-09'}); })()", "document.querySelector('#v-reporting .wr-health')", "#v-reporting")
SCREENS["project-settings"] = ("go('psettings','ABC')", "!!document.getElementById('psArchive')", "#v-psettings")   # the Settings line: Archive's home
# #232-A: Intake with a meeting row whose Not needed button (aria-haspopup=menu, opens #irAside) shows. The sample's calendar has
# no ended meeting, so the page is given one in the page only (the model's own shape; nothing is saved).
SCREENS["intake-review"] = ("go('intake-review')", "VIEW==='intake-review' && !!document.querySelector('#v-intake-review [data-ira=notneeded]')", "#v-intake-review")
us.SCREENS["intake-review"] = SCREENS["intake-review"]      # #232 C2: test_snapshots' own "intake-review" waits for less; this one needs a row with Not needed
EXTRA = ("clientreport", "today-days", "project-settings")     # screens of this test alone: test_ui_sweep's own list (its goldens) doesn't get them
# The minutes' Approve popup is the screen here (test_ui_sweep's "minutes-approve", for the sizes): the minutes sheet behind it
# is inert and is the "minutes" screen's (likewise the deadline popover, whose button is the "minutes" screen's). The popup has no aria-haspopup opener inside it, so mnapp (KEYED) drives it.
ONLY = {"shell": ".rail,header.bar", "minutes-approve": "#mnApprove", "minutes-deadline": ".mnpop"}   # the shell's own controls, not the page inside it
# Still on the screen (settle goes back when not): its ready test, except where that test is a popup being open.
ON_SCREEN = {"work-display": "VIEW==='work'"}
# Controls whose choices are what the list shows, never a saved change: the filter bars and Work's views. The Undo check
# leaves them alone (a choice there would also change what every later screen shows).
VIEW_ONLY = (".fbtn", "#vmore", "#moreBtn", "#pmFBtn")

# #89: the screens in three parts for the keys test and two for the Undo check, each part a browser file of its own (a sample
# vault each), about 220 s and 200 s where the whole was about 650 s and 400 s. In SCREENS' order within a part; the three Notes
# screens stay together (they share the one note they make) and a dialog script (KEYED) runs with its screen. A new screen goes into
# a part (test_every_screen_is_in_exactly_one_part says so), then behaviour_witness.py refreshes behaviour_witness.json.
KEYS_PARTS = {"a": ("review", "activity", "person", "help", "settings-health", "rail-expanded", "rail-icons", "work-board", "work-panel-decision", "review-peek", "prep-popup", "milestones-move", "minutes", "minutes-deadline", "archive-ask", "notes", "notes-ai", "notes-session"),
              "b": ("work-panel", "cockpit", "people", "settings-essentials", "settings-advanced", "rail-collapsed", "activity-selected", "work-panel-details", "work-panel-raid", "work-panel-new", "work-display", "work-views", "shell", "clientreport"),
              "c": ("today", "work", "intake", "files", "projects", "milestones", "settings-people", "ask", "work-decisions", "milestone-editor", "minutes-approve", "weekly", "reports", "reporting", "today-days")}
UNDO_PARTS = {"a": ("review", "activity", "cockpit", "people", "help", "settings-essentials", "settings-advanced", "settings-health", "rail-expanded", "rail-collapsed", "activity-selected", "work-panel-raid", "work-panel-decision", "work-panel-new", "work-decisions", "work-views", "prep-popup", "milestones-move", "minutes", "minutes-deadline", "weekly", "shell"),
              "b": ("today", "work", "work-panel", "intake", "files", "projects", "milestones", "person", "settings-people", "ask", "rail-icons", "work-board", "work-panel-details", "review-peek", "work-display", "milestone-editor", "minutes-approve", "reports", "reporting", "archive-ask", "today-days", "notes", "notes-ai", "notes-session", "clientreport")}

# The screen area each screen belongs to (check.py's OLD_AREAS names), for the expected-failures list.
SCREEN_AREAS = {"today": "Today", "today-days": "Today", "work": "Work", "work-board": "Work", "work-display": "Work", "work-panel": "Peek", "work-panel-details": "Peek", "work-panel-raid": "Peek",
                "work-panel-decision": "Peek", "work-panel-new": "Peek", "meeting": "Meetings",
                "review-peek": "Review", "intake-review": "Intake", "files": "Files", "activity": "Activity", "activity-selected": "Activity", "projects": "Projects",
                "cockpit": "Projects", "milestones": "Milestones", "people": "People", "person": "People", "help": "Help",
                "ask": "ask creaite", "shell": "Shell", "cmdk": "Shell", "work-decisions": "Work", "work-views": "Work",
                "prep-popup": "Projects", "milestone-editor": "Milestones", "milestones-move": "Milestones",
                "archive-ask": "Settings", "notes": "Core", "notes-ai": "Core", "notes-session": "Core"}


def screen_area(name):
    """The area a screen belongs to (Settings' tabs are all Settings)."""
    return "Settings" if name.startswith("settings-") else SCREEN_AREAS.get(name, name)


# ---------- the inventory, read from the code ----------
def _literal(expr):
    """The literal start of a JS string expression ("…", '…' or `…` up to its first ${), or "" when it starts dynamic."""
    m = re.match(r"""\s*(?:"((?:[^"$]|\$(?!\{))*)|'((?:[^'$]|\$(?!\{))*)|`((?:[^`$]|\$(?!\{))*))""", expr)
    return next((g for g in m.groups() if g is not None), "") if m else ""


def _opening_tag(text, at):
    """The attributes of the JSX or HTML tag starting at `at`, up to its closing > (an arrow's => is not one)."""
    return re.match(r"(?:=>|[^>])*", text[at:at + 600]).group(0)


def _call(text, at):
    """The first 300 characters of a call's arguments, from just after its `(`."""
    return text[at:at + 300]


def _site(kind, block, keys, path, text, at):
    line = text.count("\n", 0, at) + 1
    return {"kind": kind, "block": block, "keys": keys, "file": path, "line": line, "area": check.old_area(path)}


def _dialogs(path, text):
    for m in re.finditer(r"<Dialog\b", text):
        tag = _opening_tag(text, m.start())
        i = re.search(r'\bid="([\w-]+)"', tag)
        if i:
            yield _site("dialog", "Dialog", [("id", i.group(1))], path, text, m.start())


def _menus(path, text):
    for m in re.finditer(r"(?<![\w.])openMenu\(", text):
        args = _call(text, m.end())
        if re.match(r"\s*anchor\s*,\s*props\s*\)", args):
            continue                                                  # the block's own definition
        i = re.search(r'\bid:\s*"([\w-]+)"', args)
        lab = re.search(r"\blabel:\s*([\"'`][^,]*)", args)
        lit = _literal(lab.group(1)).strip() if lab else ""
        keys = [("id", i.group(1))] if i else [("label", lit)] if len(lit) >= 4 else []
        yield _site("menu", "Menu", keys, path, text, m.start())
    for m in re.finditer(r"<(Menu|MenuPanel)\b", text):
        tag = _opening_tag(text, m.start())
        keys = [("id", x) for x in re.findall(r'\b(?:menuId|id)="([\w-]+)"', tag)] \
            or [("label", x) for x in re.findall(r'\blabel="([^"]+)"', tag)]
        yield _site("menu", "Menu", keys, path, text, m.start())


def _filter_bars(path, text):
    for m in re.finditer(r"(?<![\w.])drawFilterBar\(", text):
        if re.match(r"\s*host\s*,", _call(text, m.end())):
            continue
        hosts = re.findall(r'\$\("#([\w-]+)"\)', text[max(0, m.start() - 300):m.start()])
        if hosts:
            yield _site("listbox", "FilterBar", [("id", hosts[-1])], path, text, m.start())


# The old helpers' names, spelt in two parts: test_dashboard_split lists every page name a test file names as a word,
# and these are only read here, never called.
PK_LIST, PK_MK, PK_OWNER = "pk" "List", "pk" "Mk", "pk" "OwnL"


def _defined_here(text, at):
    """Whether the name at `at` is a function's own definition (`function name(`), not a call."""
    return text[max(0, at - 9):at].endswith("function ")


def _old_lists(path, text):
    for m in re.finditer(rf"(?<![\w.]){PK_LIST}\(", text):
        if _defined_here(text, m.start()):
            continue
        lab = re.search(r"\blabel:\s*([^,]+)", _call(text, m.end()))
        lit = _literal(lab.group(1)) if lab else ""
        if not lit and lab and PK_OWNER in lab.group(1):
            lit = "Owner"                                              # the owner's label: "Owner" (or "Decision maker")
        yield _site("listbox", "Picker", [("label", lit)] if lit else [("class", "pkpop")], path, text, m.start())


def _old_pickers(path, text):
    for m in re.finditer(rf'(?<![\w.]){PK_MK}\(\s*\w+\s*,\s*"(\w+)"', text):
        if m.group(1) != "pkcal":                                      # pkDate's calendar: counted below, by its caller
            yield _site("dialog", "Picker", [("class", m.group(1))], path, text, m.start())
    for m in re.finditer(r"(?<![\w.])pkDate\(", text):
        if _defined_here(text, m.start()):
            continue
        lab = re.search(r"\blabel:\s*([^,]+)", _call(text, m.end()))
        lit = _literal(lab.group(1)) if lab else ""
        yield _site("dialog", "Picker", ([("label", lit)] if lit else []) + [("class", "pkcal")], path, text, m.start())
    if re.search(r"(?<![\w.])cxOpen\(", text) and not path.endswith("panel.js"):
        at = re.search(r"(?<![\w.])cxOpen\(", text).start()
        yield _site("menu", "Menu", [("class", "cxmenu")], path, text, at)          # the right-click menu, one per file
    for m in re.finditer(r'class="combo"', text):
        i = re.search(r'\bid="([^"]+)"', text[m.end():m.end() + 200])
        lit = _literal('"' + i.group(1)) if i else ""
        yield _site("listbox", "Combobox", [("class", "combo")] + ([("id", lit)] if lit else []), path, text, m.start())


def _block_lists(path, text):
    """The Picker block's lists (openPicker), by their literal label, else any .pkpop."""
    for m in re.finditer(r"(?<![\w.])openPicker\(", text):
        if _defined_here(text, m.start()):
            continue
        lab = re.search(r"\blabel:\s*([^,]+)", _call(text, m.end()))
        lit = _literal(lab.group(1)) if lab else ""
        if not lit and lab and PK_OWNER in lab.group(1):
            lit = "Owner"
        yield _site("listbox", "Picker", [("label", lit)] if lit else [("class", "pkpop")], path, text, m.start())


def _block_calendars(path, text):
    """The Picker block's calendars (openDatePicker, and core's itemDatePicker), by their label and .pkcal."""
    for m in re.finditer(r"(?<![\w.])(?:openDatePicker|itemDatePicker)\(", text):
        if _defined_here(text, m.start()):
            continue
        lab = re.search(r"\blabel:\s*([^,]+)", _call(text, m.end()))
        lit = _literal(lab.group(1)) if lab else ""
        yield _site("dialog", "Picker", ([("label", lit)] if lit else []) + [("class", "pkcal")], path, text, m.start())


def _block_popovers(path, text):
    """The Picker block's popovers (openPopover), by their id and the option they are opened from (`via`). An empty box
    that old code fills (htmlPopover) has no id and is counted by its caller."""
    for m in re.finditer(r"(?<![\w.])openPopover\(", text):
        args = _call(text, m.end())
        if not _defined_here(text, m.start()) and re.search(r'\bid:\s*"', args):
            yield _site("dialog", "Picker", [("id", x) for x in re.findall(r'\b(?:id|via):\s*"([\w-]+)"', args)], path, text, m.start())


def _markup_openers(path, text):
    """A control in markup that says aria-haspopup: by the popup it controls, else by its own literal name (four
    characters at least); one with neither is left to the screens' sweep (it is reached there or nowhere)."""
    for m in re.finditer(r"""aria-haspopup=(?:"|\\")(menu|listbox|dialog|true)""", text):
        start = text.rfind("<", 0, m.start())
        tag = text[start:m.end() + 300].split(">", 1)[0] if start >= 0 else ""
        line = text[text.rfind("\n", 0, m.start()) + 1:m.start()].lstrip()
        if line.startswith(("*", "//", "/*")):
            continue                                                   # a comment describing it
        ctl = re.search(r'aria-controls="([^"]+)"', tag)
        lab = re.search(r'aria-label="([^"]+)"', tag)
        keys = []
        if ctl:
            tail = re.split(r"\$\{[^}]*\}", ctl.group(1))
            keys.append(("id", ctl.group(1)) if len(tail) == 1 else ("idend", tail[-1]))
        lit = _literal('"' + lab.group(1)).strip() if lab else ""
        if len(lit) >= 4:
            keys.append(("label", lit))
        if keys:
            kind = "dialog" if m.group(1) == "dialog" else m.group(1).replace("true", "menu")
            yield _site(kind, "Opener", keys, path, text, m.start())


def inventory():
    """Every place in the dashboard's source that makes a menu, picker or dialog: a list of sites, each {kind, block,
    keys, file, line, area}. `keys` are what the screens' sweep matches it by: ("id", x) an id, ("idend", x) an id's end,
    ("label", x) a name's start, ("class", x) a class."""
    out = []
    for path, text in check.old_sources().items():
        for find in (_dialogs, _menus, _filter_bars, _old_lists, _old_pickers, _block_lists, _block_calendars, _block_popovers, _markup_openers):
            out += [s for s in find(path, text) if s["keys"]]
    return out


def site_name(s):
    """One line naming a site, as the expected-failures list writes it."""
    keys = " ".join(f"{k}:{v}" for k, v in s["keys"])
    return f"{s['kind']} {s['block']} {keys} ({s['file']})"


def reached(site, seen):
    """Whether any opener's record (SB.seen) matches one of the site's keys."""
    for rec in seen:
        for k, v in site["keys"]:
            if (k == "id" and v in rec["ids"]) or (k == "idend" and any(x.endswith(v) for x in rec["ids"])) \
                    or (k == "label" and any(x.startswith(v) for x in rec["labels"])) or (k == "class" and v in rec["classes"]):
                return True
    return False


# ---------- the expected failures ----------
def expected(check_kind):
    """{(area, line)} of the known failures of one check ("keys", "undo" or "unreached")."""
    data = json.loads(EXPECTED_FILE.read_text(encoding="utf-8"))
    return {(area, x) for area, lines in data.items() if not area.startswith("_") for x in lines
            if x.startswith(check_kind + ": ")}


def witnesses():
    """{site name: the screen (or dialog script) whose run must reach that site}, from behaviour_witness.json. #89: the keys test
    runs in three files (KEYS_PARTS), and "every popup in the code is reached by some screen" cannot be asked of a part that
    sees only its own screens, so each site is judged in the part that holds its witness. A site no screen reaches has none (it is
    listed in the expected failures as "unreached"). behaviour_witness.py writes the file from a run; test_the_witnesses_cover_
    every_site_in_the_code keeps it honest."""
    return json.loads(WITNESS_FILE.read_text(encoding="utf-8"))


def judge(check_kind, found, screens=None, names=None):
    """The test's verdict on one check: `found` is {(area, line)} of today's failures. Fails on a failure not listed, and
    on a listed one that now passes (remove its line): the messages, empty when it passes. With `screens`, only the lines of those screens are judged;
    with `names` (the unreached check), only the lines of those sites."""
    exp = expected(check_kind)
    if screens is not None:
        exp = {(a, x) for a, x in exp if x.split()[1] in screens}
    if names is not None:
        exp = {(a, x) for a, x in exp if x.split(": ", 1)[1] in names}
    new, gone = sorted(found - exp), sorted(exp - found)
    msg = []
    if new:
        msg.append(f"New {check_kind} failures (fix the screen; only a deliberate exception goes into "
                   f"{EXPECTED_FILE.name}):\n" + "\n".join(f'  "{a}": "{x}"' for a, x in new))
    if gone:
        msg.append(f"Listed in {EXPECTED_FILE.name} but passing now: remove these lines:\n"
                   + "\n".join(f'  "{a}": "{x}"' for a, x in gone))
    return msg


class Inventory(unittest.TestCase):
    """The inventory is read from the code (no Chrome)."""

    def test_the_inventory_finds_every_kind_of_popup(self):
        sites = inventory()
        blocks = {s["block"] for s in sites}
        for b in ("Dialog", "Menu", "FilterBar", "Picker", "Opener"):
            self.assertIn(b, blocks)
        ids = {v for s in sites for k, v in s["keys"] if k == "id"}
        for x in ("cmdk", "llDlg", "railCust", "closeDlg", "pkMoreMenu", "chHistMenu", "wfilters", "dispMenu"):
            self.assertIn(x, ids, "a popup the code makes is missing from the inventory")
        if os.environ.get("SB_REPORT"):
            for s in sorted(sites, key=lambda s: (s["area"], s["file"], s["line"])):
                print(f"{s['area']:12} {s['file']}:{s['line']:<5} {site_name(s)}")
            print(f"{len(sites)} sites")

    def test_every_screen_is_in_exactly_one_part(self):
        """#89: the keys test and the Undo check each run in parts (KEYS_PARTS, UNDO_PARTS); every screen is in one part of each,
        in SCREENS' order, and the Notes screens (they share the note they make) are together."""
        order = list(SCREENS)
        for label, parts in (("keys", KEYS_PARTS), ("undo", UNDO_PARTS)):
            flat = [s for p in parts.values() for s in p]
            self.assertEqual(len(flat), len(set(flat)), f"{label}: a screen in two parts")
            self.assertEqual(set(flat), set(order), f"{label}: a screen in no part, or a part names a screen that is gone")
            for name, p in parts.items():
                self.assertEqual(list(p), [s for s in order if s in p], f"{label} part {name}: not in SCREENS' order")
            notes = {n for n, p in parts.items() if any(s.startswith("notes") for s in p)}
            self.assertEqual(len(notes), 1, f"{label}: the Notes screens are in more than one part")

    def test_every_part_is_run_by_exactly_one_test_file(self):
        """#89: a part nobody calls would silently skip its screens. Each key of KEYS_PARTS is run (a call of run_part with its key) by exactly
        one test file of test_shared_behaviour*.py, each key of UNDO_PARTS by exactly one of test_shared_undo*.py, and no file
        runs a part that has no screens listed."""
        for label, parts, pattern in (("keys", KEYS_PARTS, "test_shared_behaviour*.py"), ("undo", UNDO_PARTS, "test_shared_undo*.py")):
            calls = []
            for f in sorted(HERE.glob(pattern)):
                calls += [(f.name, k) for k in re.findall(r'self\.run_part\("(\w+)"\)', f.read_text(encoding="utf-8"))]
            self.assertEqual(sorted(k for _, k in calls), sorted(parts), f"{label}: each part run by one test file: {calls}")

    def test_the_witnesses_cover_every_site_in_the_code(self):
        """#89: each popup site in the code has the screen (or dialog script) whose run must reach it, or is listed as unreached.
        A new site: add it to a screen, then run the parts with SB_WITNESS=<file> and dev/tests/behaviour_witness.py."""
        wit, sites = witnesses(), {site_name(s) for s in inventory()}
        units = set(SCREENS) | {k[1] for k in SharedBehaviour.KEYED}
        listed = {x.split(": ", 1)[1] for _, x in expected("unreached")}
        self.assertEqual(sorted(set(wit) - sites), [], "a witness for a site that is not in the code any more")
        self.assertEqual(sorted(u for u in wit.values() if u not in units), [], "a witness that is not a screen or dialog script")
        self.assertEqual(sorted(sites - set(wit) - listed), [], "a site with no witness that is not listed as unreached: run behaviour_witness.py")
        self.assertEqual(sorted(listed - sites), [], "listed as unreached but not in the code any more")
        self.assertEqual(sorted(listed & set(wit)), [], "listed as unreached and has a witness: remove one")

    def test_the_expected_failures_are_well_formed(self):
        data = json.loads(EXPECTED_FILE.read_text(encoding="utf-8"))
        areas = {a for _, a in check.OLD_AREAS} | set(SCREEN_AREAS.values()) | {"Settings"}
        for area, lines in data.items():
            if area.startswith("_"):
                continue
            self.assertIn(area, areas, "an area check.py's OLD_AREAS (or SCREEN_AREAS) names")
            self.assertEqual(len(lines), len(set(lines)), f"{area}: a line listed twice")
            for x in lines:
                self.assertRegex(x, r"^(keys|undo|unreached): ", f"{area}: each line starts with its check")


class Driver:
    """The keys, shared by the two browser checks."""

    def press(self, key, wait=0.25, modifiers=0):
        self.b.key(key, modifiers)
        self.b.pump(wait)

    def state(self, i):
        return self.b.eval(f"SB.state({i})")

    def goto(self, name):
        if name in EXTRA:
            us.SCREENS[name] = SCREENS[name]
        try:
            super().goto(name)
        finally:
            if name in EXTRA:
                us.SCREENS.pop(name, None)

    def settle_screen(self, name):
        """Close whatever the last control left open; go back to the screen when something is still open."""
        b = self.b
        for _ in range(2):
            if not b.eval("SB.popups().length"):
                break
            self.press("Escape", 0.15)
        if b.eval("SB.reset()") or not b.eval(ON_SCREEN.get(name, SCREENS[name][1])):
            self.goto(name)
            b.eval(PROBE + ";true")

    def openers(self, name):
        go, ready, region = SCREENS[name]
        return self.b.eval(f"SB.openers({json.dumps(ONLY.get(name, region))})")

    def each_opener(self, name, drive):
        """drive(i, opener) for every opener on the screen, found again before each (a redraw may replace them)."""
        self.goto(name)
        self.b.eval(PROBE + ";true")
        out = []
        for o in self.openers(name):
            match = [x for x in self.openers(name) if x["sig"] == o["sig"] and x["name"] == o["name"]]
            if not match:
                continue
            out.append((o, drive(match[0]["i"], o)))
            self.settle_screen(name)
        return out


class Keys(Driver):
    """BL-316's shared behaviour test: keys, focus and Esc, and every popup in the code reached. The helpers and the script
    for one part of the screens (KEYS_PARTS; #89: three browser files of about 220 s each instead of one of about 650 s). The
    test classes that run them are SharedBehaviour here and test_shared_behaviour_b.py / _c.py."""

    def goto(self, name):
        """The screen, by its keys-test way where it has one (KEYS_GO)."""
        if name not in KEYS_GO:
            return super().goto(name)
        plain = us.SCREENS[name]
        us.SCREENS[name] = KEYS_GO[name]
        try:
            super().goto(name)
        finally:
            us.SCREENS[name] = plain

    def opened(self, i):
        """Enter on opener i: (its state, what it got wrong), or (None, why) when nothing opened."""
        self.press("Enter", 0.4)
        s = self.state(i)
        for _ in range(16):          # a list that asks the live server first (Review's "Update an existing item instead", aria-busy meanwhile) opens when it answers; the server is slower late in a long run
            if (s["open"] or s["modal"]) and not s["busy"]:
                break
            self.b.pump(0.25)
            s = self.state(i)
        if not s["open"] and not s["modal"]:
            return None, ["Enter opens nothing"]
        bad = []
        if s["expanded"] is not None and s["expanded"] != "true":
            bad.append(f"aria-expanded is {s['expanded']!r} when open")
        if not s["focusInPopup"]:
            bad.append(f"focus stays outside the popup ({s['active']})")
        return s, bad

    def arrows(self, i, s1):
        """↓ then ↑ inside a menu or a list: focus (or the active option) moves, and stays inside (a list of one has
        nowhere to move: focus only stays inside)."""
        self.press("ArrowDown")
        s2 = self.state(i)
        self.press("ArrowUp")
        s3 = self.state(i)
        if not s2["focusInPopup"] or not s3["focusInPopup"]:
            return ["↓ ↑ take focus out of the popup"]
        if s2["active"] == s1["active"] and s3["active"] == s1["active"] and s1["items"] > 1:
            return ["↓ ↑ move nothing"]
        return []

    def escape(self, i):
        """Esc: closed, focus back on the control, aria-expanded false. Returns (state, what it got wrong)."""
        self.press("Escape", 0.35)
        s = self.state(i)
        bad = []
        if s["open"] or s["modal"]:
            bad.append("Esc leaves it open")
        if not s["focusOnOpener"] and s["connected"]:
            bad.append(f"Esc doesn't return focus to the control ({s['active']})")
        if s["expanded"] not in (None, "false"):
            bad.append(f"aria-expanded is {s['expanded']!r} after Esc")
        return s, bad

    def tab_closes(self, i):
        """Opened again, Tab closes a menu or a list."""
        self.b.eval(f"SB.focus({i})")
        self.press("Enter", 0.4)
        for _ in range(16):          # as opened() does: a list that asks the live server first (aria-busy) opens when it answers; leaving it would let it open later, over the next control
            s = self.state(i)
            if s["open"] or not s["busy"]:
                break
            self.b.pump(0.25)
        if not self.state(i)["open"]:
            return []
        self.press("Tab", 0.3)
        return ["Tab leaves it open"] if self.state(i)["open"] else []

    def drive(self, i, kind):
        """The script for opener i: a list of what it got wrong (empty when it behaves). What it opened is kept for the
        inventory."""
        if not self.b.eval(f"SB.focus({i})"):
            return ["it can't take focus"]
        s1, bad = self.opened(i)
        if s1 is None:
            return bad
        self.seen.append(self.b.eval(f"SB.seen({i})"))
        dialog = kind == "dialog" or s1["modal"]
        if not dialog:
            bad += self.arrows(i, s1)
        s4, more = self.escape(i)
        bad += more
        if not dialog and s4["connected"] and not s4["open"]:
            bad += self.tab_closes(i)
        return bad

    def cmdk(self):
        """⌘K from the Today screen: the search dialog opens with focus in it; Esc closes it and focus is back where it was."""
        b = self.b
        self.goto("today")
        b.eval(PROBE + ";true")
        b.eval("document.querySelector('.rail button[data-v=\"today\"]').focus()")
        self.press("k", 0.5, modifiers=4)
        bad = []
        if not b.eval("document.getElementById('cmdk').open"):
            return ["⌘K opens nothing"]
        self.seen.append({"ids": ["cmdk"], "labels": [], "classes": []})
        if not b.eval("document.getElementById('cmdk').contains(document.activeElement)"):
            bad.append("focus stays outside the dialog")
        self.press("Escape", 0.4)
        if b.eval("document.getElementById('cmdk').open"):
            bad.append("Esc leaves it open")
        elif not b.eval("document.activeElement && document.activeElement.matches('.rail button[data-v=\"today\"]')"):
            bad.append("Esc doesn't return focus to where it was")
        return bad

    def parch(self):
        """BL-09: Archive on a project with open items opens #parchDlg only after the server lists them, so its button can't
        say aria-haspopup: Enter on ABC's Archive (its settings' Archive and close since the Settings line; it asks first, and
        Enter on that Archive goes on) opens it with focus in it; Esc closes it and focus is back on the button. Nothing is
        staged: the server only lists the open items."""
        b = self.b
        self.goto("project-settings")
        b.eval(PROBE + ";true")
        sel = json.dumps("#psArchive")
        b.eval(f"(()=>{{ const e=document.querySelector({sel}); e.scrollIntoView({{block:'center'}}); e.focus(); }})()")
        self.press("Enter", 0.5)
        b.wait("!!document.getElementById('psArchiveYes')", 10)
        b.eval("document.getElementById('psArchiveYes').focus()")
        self.press("Enter", 0.5)
        try:
            b.wait("document.getElementById('parchDlg')?.open", 20)
        except TimeoutError:
            return ["Enter opens nothing"]
        self.seen.append({"ids": ["parchDlg"], "labels": [], "classes": []})
        bad = []
        if not b.eval("document.getElementById('parchDlg').contains(document.activeElement)"):
            bad.append("focus stays outside the dialog")
        self.press("Escape", 0.4)
        if b.eval("document.getElementById('parchDlg').open"):
            bad.append("Esc leaves it open")
        elif not b.eval(f"document.activeElement===document.querySelector({sel})"):
            bad.append("Esc doesn't return focus to the control")
        return bad

    def ndel(self):
        """#124: Delete note... in the note's ... menu opens #noteDelDlg (a menu item, not an aria-haspopup control): Enter on the
        item opens it with focus in it (Cancel); Esc closes it and focus is back on the ... button (the opener is set by askDeleteNote). Nothing is deleted."""
        b = self.b
        self.goto("notes")
        _note_made(b)
        b.eval(PROBE + ";true")
        b.click(".nmorewrap .nmore")
        b.wait("!!document.querySelector('.nmorewrap [role=menu] .bad')", 5)
        b.eval("document.querySelector('.nmorewrap [role=menu] .bad').focus()")
        self.press("Enter", 0.5)
        try:
            b.wait("document.getElementById('noteDelDlg')?.open", 20)
        except TimeoutError:
            return ["Enter opens nothing"]
        self.seen.append({"ids": ["noteDelDlg"], "labels": [], "classes": []})
        bad = []
        if not b.eval("document.getElementById('noteDelDlg').contains(document.activeElement)"):
            bad.append("focus stays outside the dialog")
        self.press("Escape", 0.4)
        if b.eval("document.getElementById('noteDelDlg').open"):
            bad.append("Esc leaves it open")
        if not b.eval("document.activeElement === document.querySelector('.nmorewrap .nmore')"):
            bad.append("Esc doesn't return focus to the control")
        return bad

    def mnapp(self):
        """v2.1.0 P7: Approve minutes (a plain button, no aria-haspopup) opens #mnApprove: Enter on it opens it with focus in it;
        Esc closes it and focus is back on the button. Nothing is approved."""
        b = self.b
        self.goto("minutes")
        b.eval(PROBE + ";true")
        b.wait("document.querySelector('#mnApproveBtn:not([disabled])')", 15)
        b.eval("document.getElementById('mnApproveBtn').focus()")
        self.press("Enter", 0.5)
        try:
            b.wait("document.getElementById('mnApprove')?.open", 20)
        except TimeoutError:
            return ["Enter opens nothing"]
        self.seen.append({"ids": ["mnApprove"], "labels": [], "classes": []})
        bad = []
        if not b.eval("document.getElementById('mnApprove').contains(document.activeElement)"):
            bad.append("focus stays outside the dialog")
        self.press("Escape", 0.4)
        if b.eval("document.getElementById('mnApprove').open"):
            bad.append("Esc leaves it open")
        elif not b.eval("document.activeElement === document.getElementById('mnApproveBtn')"):
            bad.append("Esc doesn't return focus to the control")
        return bad

    def crleft(self):
        """v2.1.0 P8; #221 H1: the left-out check dialog #crLeftDlg (no control opens it now: it opens when a client export is refused, and
        with #170's Check this report): opened here from the Approve button's place, it takes focus (Cancel); Esc closes it and focus is
        back where it was. Nothing is exported."""
        b = self.b
        self.goto("clientreport")
        b.eval(PROBE + ";true")
        b.eval("document.querySelector('#v-reporting #hubApprove').focus()")
        b.eval("crDialog.value=true; runCheck(); true")
        try:
            b.wait("document.getElementById('crLeftDlg')?.open", 20)
        except TimeoutError:
            return ["Enter opens nothing"]
        self.seen.append({"ids": ["crLeftDlg"], "labels": [], "classes": []})
        b.pump(1.0)
        bad = []
        if not b.eval("document.getElementById('crLeftDlg').contains(document.activeElement)"):
            bad.append("focus stays outside the dialog")
        self.press("Escape", 0.4)
        if b.eval("document.getElementById('crLeftDlg').open"):
            bad.append("Esc leaves it open")
        elif not b.eval("document.activeElement === document.querySelector('#v-reporting #hubApprove')"):
            bad.append("Esc doesn't return focus to the control")
        return bad

    def rail(self):
        """#139: the rail's Projects and Work open a flyout on hover, and from the keyboard with → or ↓ (Enter keeps going to
        the page, as the icon always did, so the Enter script can't drive them): the list opens with focus in it and
        aria-expanded true; ↓ ↑ move inside it; Esc closes it with focus back on the button."""
        b = self.b
        self.goto("today")
        b.eval(PROBE + ";true")
        bad = []
        for v in ("work", "projects"):
            sel = f"#railMain [data-v={v}]"
            b.eval(f"document.querySelector('{sel}').focus()")
            self.press("ArrowRight", 0.5)
            self.seen.append({"ids": [f"railFly-{v}", "railFly-"], "labels": [], "classes": []})
            if b.eval(f"document.querySelector('{sel}').getAttribute('aria-expanded')") != "true":
                bad.append(f"{v}: → opens nothing")
                continue
            if not b.eval(f"!!document.activeElement.closest('#railFly-{v}')"):
                bad.append(f"{v}: focus stays outside the list")
            first = b.eval("document.activeElement.textContent")
            self.press("ArrowDown")
            self.press("ArrowUp")
            if b.eval("document.activeElement.textContent") != first or not b.eval(f"!!document.activeElement.closest('#railFly-{v}')"):
                bad.append(f"{v}: ↓ ↑ take focus out of the list")
            self.press("Escape", 0.4)
            if b.eval(f"document.querySelector('{sel}').getAttribute('aria-expanded')") != "false":
                bad.append(f"{v}: Esc leaves it open")
            elif not b.eval(f"document.activeElement===document.querySelector('{sel}')"):
                bad.append(f"{v}: Esc doesn't return focus to the button")
        return bad

    def dialog_keys(self, dlg):
        """The dialog is open (opened by Enter on the control kept in window.__back): focus is in it; Esc closes it and focus is
        back on that control."""
        b = self.b
        self.seen.append({"ids": [dlg], "labels": [], "classes": []})
        bad = []
        if not b.eval(f"document.getElementById({dlg!r}).contains(document.activeElement)"):
            bad.append("focus stays outside the dialog")
        peek = b.eval("document.getElementById('panel').classList.contains('on')")
        self.press("Escape", 0.5)
        if b.eval(f"document.getElementById({dlg!r}).open"):
            bad.append("Esc leaves it open")
        elif not b.eval("document.activeElement===window.__back"):
            bad.append("Esc doesn't return focus to the control")
        if peek and not b.eval("document.getElementById('panel').classList.contains('on')"):
            bad.append("Esc in the dialog also closed the peek")
        return bad

    def enter_on(self, control_js, ready_js, wait=20):
        """Focus the control `control_js` finds, press Enter, wait for `ready_js` (the popup open): (the problems, whether it opened)."""
        b = self.b
        b.eval(f"(()=>{{ const e={control_js}; window.__back=e; e.scrollIntoView({{block:'center'}}); e.focus(); }})()")
        self.press("Enter", 0.5)
        try:
            b.wait(ready_js, wait)
        except TimeoutError:
            return ["Enter opens nothing"], False
        return [], True

    def tidy(self, extra=""):
        """Leave the page as it was found, whatever the script did: the real api back, the board grouped by status, the marked
        repeat gone, and no dialog or peek still open. `extra` is more JS for the script's own state."""
        self.b.eval("(()=>{ if(window.__realApi){ window.api=window.__realApi; window.__realApi=null; } "
                    "const g=document.getElementById('wgrp'); if(g&&g.value!=='status'){ g.value='status'; g.dispatchEvent(new Event('change',{bubbles:true})); } "
                    + extra +
                    " document.querySelectorAll('dialog[open]').forEach(d=>{ try{ typeof closeDialog==='function'?closeDialog(d):d.close(); }catch(e){ d.close(); } }); "
                    "if(document.getElementById('panel')?.classList.contains('on')) closePanel(); })()")

    def boardask(self):
        """BL-316 (#88): the date prompt (#boardDlg), reached as a keyboard user reaches it: on the Work board grouped by due
        date, Enter on a card's Move button opens its menu, Enter on the first column asks for the date."""
        b = self.b
        try:
            self.goto("work-board")
            b.eval("(()=>{ const s=document.getElementById('wgrp'); s.value='due'; s.dispatchEvent(new Event('change',{bubbles:true})); })()")
            b.wait("groupOf(WT)==='due' && document.querySelector('#workBoard .bmv')", 15)
            bad, opened = self.enter_on("document.querySelector('#workBoard .bmv')", "!!document.getElementById('bdMoveMenu')")
            if not opened:
                return ["Enter on a card's Move button opens nothing"]
            self.press("Enter", 0.6)             # the menu opens with its first column focused
            try:
                b.wait("document.getElementById('boardDlg').open", 10)
            except TimeoutError:
                return ["Enter on a column opens nothing"]
            return self.dialog_keys("boardDlg")
        finally:
            self.tidy()

    def llcompare(self):
        """BL-221 (#88): Compare a repeat (#llDlg). The sample vault has no proposal that repeats an item, so one is marked
        as the page would mark it; its peek's Compare button, Enter opens the dialog."""
        b = self.b
        n = None
        try:
            self.goto("intake-review")
            n = b.eval("REV.find(r=>r.kind==='actions')?.n")
            if n is None:
                return ["the sample vault has no actions proposal to mark as a repeat"]
            b.eval("(()=>{ const r=REV.find(r=>r.n===%s); r.dup={id:'ABC-A-001',t:'Chase the SOW',strength:'Likely',staged:true,same:true,state:'open',project:'ABC'}; irTick.value++; openProposal(%s); })()" % (n, n))
            b.wait("document.querySelector('[data-rvll=\"cmp:%s\"]')" % n, 10)
            bad, opened = self.enter_on("document.querySelector('[data-rvll=\"cmp:%s\"]')" % n, "document.getElementById('llDlg').open")
            return self.dialog_keys("llDlg") if opened else bad
        finally:
            self.tidy("" if n is None else "const r=REV.find(r=>r.n===%s); if(r){ delete r.dup; irTick.value++; }" % n)

    def searchprev(self):
        """The search preview (#searchPrev): a vault search on Files finds a meeting's minutes; Enter on that result previews it.
        The sample vault's minutes have no text to preview (the server then opens the file instead), so the server's answer for
        /api/search/preview is the one thing stood in for, as test_snapshots does for Health."""
        b = self.b
        try:
            self.goto("files")
            b.eval("(()=>{ const real=window.api; window.__realApi=real; window.api=async(p,body)=>p==='/api/search/preview' "
                   "? {ok:true,name:'2026-10-04 Steering Minutes',html:'<p>Chase the <mark>steering</mark> actions.</p>',cut:false} : real(p,body); })()")
            b.eval("(()=>{ const i=document.getElementById('vsInput'); i.focus(); i.value='steering'; i.dispatchEvent(new Event('input',{bubbles:true})); })()")
            try:
                b.wait("[...document.querySelectorAll('#vsResults .vsr')].some(r=>r.textContent.includes('Minutes'))", 20)
            except TimeoutError:
                return ["the search finds no minutes to preview"]
            bad, opened = self.enter_on("[...document.querySelectorAll('#vsResults .vsr')].find(r=>r.textContent.includes('Minutes'))", "document.getElementById('searchPrev').open")
            return self.dialog_keys("searchPrev") if opened else bad
        finally:
            self.tidy("const i=document.getElementById('vsInput'); if(i&&i.value){ i.value=''; i.dispatchEvent(new Event('input',{bubbles:true})); }")

    # The dialogs no aria-haspopup control opens, each driven by its own script: (the screen that must be in the run, the
    # script, its name in the report and the expected-failures list, its area, what it opens).
    KEYED = (("today", "cmdk", "cmdk dialog#cmdk", "Shell", "⌘K", "Search or jump to"),
             ("archive-ask", "parch", "parch dialog#parchDlg", "Settings", "Archive ABC", "Archive a project with open items"),
             ("notes", "ndel", "ndel dialog#noteDelDlg", "Core", "Delete note…", "Delete note?"),
             ("minutes-approve", "mnapp", "mnapp dialog#mnApprove", "minutes", "Approve minutes", "Before approving"),   # #268: the box shown only for a ticked item's real problem
             ("clientreport", "crleft", "crleft dialog#crLeftDlg", "clientreport", "Check and export", "Left out of the client's report"),
             ("today", "rail", "rail menu#railFly", "Shell", "→ on Projects, Work", "Rail flyouts"),
             ("work-board", "boardask", "boardask dialog#boardDlg", "Shell", "Move ▸ a due column", "Due date for"),
             ("intake-review", "llcompare", "llcompare dialog#llDlg", "Shell", "Compare", "Looks like"),
             ("files", "searchprev", "searchprev dialog#searchPrev", "Shell", "a search result", "Preview"))

    def keyed_dialogs(self, only, report, found):
        for screen, script, sig, area, how, label in self.KEYED:
            if screen not in only:
                continue
            before = len(self.seen)
            bad = getattr(self, script)()
            self.by_unit[script] = self.seen[before:]
            if report:
                print(f"{script:16} {'dialog':8} {how:48} {label:40} {'; '.join(bad) or 'ok'}")
            if bad:
                found.add((area, f"keys: {sig} “{label}”: {'; '.join(bad)}"))

    def run_part(self, part):
        """The keys script on the screens of one part (KEYS_PARTS), then the dialogs no control opens that sit on them, and
        the unreached verdict for the sites this part is answerable for (witnesses(): a site is judged where its witness is,
        so the parts need share nothing)."""
        report = os.environ.get("SB_REPORT")
        want = set(os.environ["SB_ONLY"].split(",")) if os.environ.get("SB_ONLY") else None
        only = [s for s in KEYS_PARTS[part] if want is None or s in want]
        self.seen, found = [], set()
        self.by_unit = {}
        for name in only:
            before = len(self.seen)
            for o, bad in self.each_opener(name, lambda i, o: self.drive(i, o["kind"])):
                if report:
                    print(f"{name:16} {o['kind']:8} {o['sig'][:48]:48} {o['name'][:40]:40} {'; '.join(bad) or 'ok'}")
                if bad:
                    found.add((screen_area(name), f"keys: {name} {o['sig']} “{o['name']}”: {'; '.join(bad)}"))
            self.by_unit[name] = self.seen[before:]
        self.keyed_dialogs(only, report, found)
        if os.environ.get("SB_WITNESS"):             # behaviour_witness.py's input: what each screen and dialog script reached
            Path(os.environ["SB_WITNESS"]).write_text(json.dumps(self.by_unit), encoding="utf-8")
        units = set(only) | {k[1] for k in self.KEYED if k[0] in only}
        msg = judge("keys", found, units)
        if want is not None or not only:
            self.assertFalse(msg, "\n".join(msg))
            return                                   # only some screens: what they didn't reach isn't a finding
        msg += self.unreached(part, units, report)
        self.assertFalse(msg, "\n".join(msg))

    def unreached(self, part, units, report):
        """The messages of the unreached check for the sites this part answers for: those whose witness is one of its `units`
        (screens and dialog scripts), and those with none (listed as unreached; a part that reaches one says to remove its line)."""
        wit = witnesses()
        sites = {}
        for s in inventory():
            sites.setdefault(site_name(s), []).append(s)
        answerable = {n for n in sites if wit.get(n) in units or n not in wit}
        missed = {(s["area"], "unreached: " + n) for n in answerable for s in sites[n] if not reached(s, self.seen)}
        if report:
            print(f"Inventory: part {part}: {len(answerable)} sites it answers for, {len(missed)} not reached")
            for a, x in sorted(missed):
                print(f"  {a:12} {x}")
        return judge("unreached", missed, names=answerable)


class SharedBehaviour(Keys, us.UiSweepCase):
    """Part a of the keys test (the other two are test_shared_behaviour_b.py and _c.py)."""

    def test_every_menu_picker_and_dialog_answers_the_same_keys(self):
        self.run_part("a")


if __name__ == "__main__":
    unittest.main()
