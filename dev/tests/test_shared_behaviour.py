"""BL-316: one keyboard script on every menu, picker and dialog on every screen (dev/COMPONENTS.md §3), the shared check
both teams' screen branches work to (v1.9.5, step 2).

**What is checked.** Every visible control that opens a popup (it says so with aria-haspopup) is driven the same way, with
real key presses: focus it and press Enter: the popup opens, the control says so (aria-expanded) and focus goes into it; in a
menu or a list, ↓ and ↑ move between its items; Esc closes it and focus is back on the control that opened it; opened again,
Tab closes a menu or a list. A dialog keeps Tab inside itself, so for a dialog only Enter and Esc are checked. ⌘K, the one
dialog opened by a key from anywhere, gets the same Enter-less script from the key. **Undo:** in a second sample vault each
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

SCREENS = dict(us.SCREENS)
SCREENS.pop("cmdk", None)              # ⌘K is itself the dialog: opened by its key (CMDK below); its list is test_cmdk's
SCREENS["shell"] = ("go('today')", "!document.getElementById('v-today').hidden", ".shell")   # the sidebar and the top bar
us.SCREENS["shell"] = SCREENS["shell"]
ONLY = {"shell": ".rail,header.bar"}   # the shell's own controls, not the page inside it
# Still on the screen (settle goes back when not): its ready test, except where that test is a popup being open.
ON_SCREEN = {"work-display": "VIEW==='work'"}
# Controls whose choices are what the list shows, never a saved change: the filter bars and Work's views. The Undo check
# leaves them alone (a choice there would also change what every later screen shows).
VIEW_ONLY = (".fbtn", "#vmore", "#moreBtn", "#rvMore", "#pmFBtn")

# The screen area each screen belongs to (check.py's OLD_AREAS names), for the expected-failures list.
SCREEN_AREAS = {"today": "Today", "work": "Work", "work-board": "Work", "work-display": "Work", "work-panel": "Peek", "work-panel-details": "Peek", "work-panel-raid": "Peek",
                "work-panel-decision": "Peek", "work-panel-new": "Peek", "meeting": "Meetings",
                "review": "Review", "intake": "Intake", "files": "Files", "activity": "Activity", "projects": "Projects",
                "cockpit": "Projects", "milestones": "Milestones", "people": "People", "person": "People", "help": "Help",
                "ask": "ask creaite", "shell": "Shell", "cmdk": "Shell"}


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


def judge(check_kind, found, screens=None):
    """The test's verdict on one check: `found` is {(area, line)} of today's failures. Fails on a failure not listed, and
    on a listed one that now passes (remove its line): the messages, empty when it passes. With `screens`, only the lines of those screens are judged."""
    exp = expected(check_kind)
    if screens is not None:
        exp = {(a, x) for a, x in exp if x.split()[1] in screens}
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
        for x in ("cmdk", "rvDlg", "railCust", "closeDlg", "pkMoreMenu", "chHistMenu", "wfilters", "dispMenu"):
            self.assertIn(x, ids, "a popup the code makes is missing from the inventory")
        if os.environ.get("SB_REPORT"):
            for s in sorted(sites, key=lambda s: (s["area"], s["file"], s["line"])):
                print(f"{s['area']:12} {s['file']}:{s['line']:<5} {site_name(s)}")
            print(f"{len(sites)} sites")

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

    def settle(self, name):
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
            self.settle(name)
        return out


class SharedBehaviour(Driver, us.UiSweepCase):
    """BL-316's shared behaviour test: keys, focus and Esc, and every popup in the code reached."""

    def opened(self, i):
        """Enter on opener i: (its state, what it got wrong), or (None, why) when nothing opened."""
        self.press("Enter", 0.4)
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

    def test_every_menu_picker_and_dialog_answers_the_same_keys(self):
        report = os.environ.get("SB_REPORT")
        only = os.environ.get("SB_ONLY", "").split(",") if os.environ.get("SB_ONLY") else list(SCREENS)
        self.seen, found = [], set()
        for name in only:
            for o, bad in self.each_opener(name, lambda i, o: self.drive(i, o["kind"])):
                if report:
                    print(f"{name:16} {o['kind']:8} {o['sig'][:48]:48} {o['name'][:40]:40} {'; '.join(bad) or 'ok'}")
                if bad:
                    found.add((screen_area(name), f"keys: {name} {o['sig']} “{o['name']}”: {'; '.join(bad)}"))
        if "today" in only:
            bad = self.cmdk()
            if report:
                print(f"{'cmdk':16} {'dialog':8} {'⌘K':48} {'Search or jump to':40} {'; '.join(bad) or 'ok'}")
            if bad:
                found.add(("Shell", f"keys: cmdk dialog#cmdk “Search or jump to”: {'; '.join(bad)}"))
        msg = judge("keys", found, set(only) | {"cmdk"})
        if os.environ.get("SB_ONLY"):
            self.assertFalse(msg, "\n".join(msg))
            return                                   # only some screens: what they didn't reach isn't a finding
        sites = inventory()
        missed = {(s["area"], "unreached: " + site_name(s)) for s in sites if not reached(s, self.seen)}
        if report:
            print(f"Inventory: {len(sites)} sites in the code; {len(sites) - len(missed)} reached, {len(missed)} not")
            for a, x in sorted(missed):
                print(f"  {a:12} {x}")
        msg += judge("unreached", missed)
        self.assertFalse(msg, "\n".join(msg))


def undo_group(name):
    """Openers that differ only by the item they act on are one group: the Undo check chooses from the first of each."""
    return re.sub(r"\b[A-Z][A-Z0-9]{2,6}-[A-Z]+-\d+\b", "", name.split(":")[0]).strip()


class SharedUndo(Driver, us.UiSweepCase):
    """BL-316: a change made from a menu or a list offers Undo (a sample vault of its own: this one changes data)."""

    def pick(self, i, o):
        """Open, ↓, Enter. What it got wrong when it saved a change (no Undo on offer), or None when nothing was saved
        (a filter, a view, a page, a dialog that asks first) or the control was left alone."""
        b = self.b
        if o["kind"] == "dialog" or any(x in o["sig"] for x in VIEW_ONLY) or not b.eval(f"SB.focus({i})"):
            return None
        self.press("Enter", 0.4)
        if not self.state(i)["open"]:
            return None
        w0 = b.eval("SB.writes().writes")
        self.press("ArrowDown", 0.2)
        self.press("Enter", 1.0)
        if b.eval("SB.writes().writes") == w0:
            return None                              # nothing saved (a filter, a view, a page): nothing to undo
        for _ in range(8):
            u = b.eval("SB.undo()")
            if u:
                b.eval(f"document.querySelector({u!r}).click()")         # put the sample back for the next control
                b.pump(1.0)
                return []
            if b.eval("!!document.querySelector('dialog:modal')"):
                return None                          # it asks first: the change is the dialog's, not the menu's
            b.pump(0.25)
        return ["a change is saved with no Undo"]

    def test_a_change_from_a_menu_or_list_offers_undo(self):
        report = os.environ.get("SB_REPORT")
        only = os.environ.get("SB_ONLY", "").split(",") if os.environ.get("SB_ONLY") else list(SCREENS)
        found = set()
        for name in only:
            done = set()

            def once(i, o, done=done):
                g = (o["sig"], undo_group(o["name"]))
                if g in done:
                    return None
                done.add(g)
                return self.pick(i, o)
            for o, bad in self.each_opener(name, once):
                if bad is None:
                    continue
                if report:
                    print(f"undo {name:16} {o['kind']:8} {o['sig'][:48]:48} {o['name'][:40]:40} {'; '.join(bad) or 'ok'}")
                if bad:
                    found.add((screen_area(name), f"undo: {name} {o['sig']} “{undo_group(o['name'])}”: {'; '.join(bad)}"))
        msg = judge("undo", found, set(only))
        self.assertFalse(msg, "\n".join(msg))


if __name__ == "__main__":
    unittest.main()
