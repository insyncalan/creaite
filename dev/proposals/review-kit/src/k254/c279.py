"""2.5.4 area (c): #279, a Prep page for a meeting with no project ("No project" is the saved value `_portfolio`; not yet chosen is the same all-projects
view). The page is Internal and says it is never sent; it is filed in the portfolio's Agendas folder and nowhere else; research stored for another
project is never shown under, or filed again for, this meeting (stale); a file creaite did not write, and a page Alan edited since, are never
overwritten; two meetings with one title on one day keep their own pages. Fictional data: the test suite's prep world (ABC, DEF) and a meeting
"Quarterly catch-up".
Each case prints:   ### CASE <name> | LEAK|PASS|HELD|CTRL-FAIL|SKIP | evidence
  LEAK  the page is not marked Internal / never sent, a file lands outside the portfolio's Agendas folder, another project's research is shown or
        refiled, or a file is overwritten / replaced that creaite did not write or Alan edited
  SKIP  the tree refuses a meeting with no project ("Choose the meeting's project in the Prep brief first", before #279): nothing is built, nothing leaks
Usage: python c279.py <tree root> <variant>      variants: page (marking, folder), overwrite, same-title, stale (another project's research), all (the four)"""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(sys.argv.pop(1))
VARIANT = sys.argv.pop(1)
sys.path.insert(0, str(ROOT / "dev" / "tests"))
sys.path.insert(0, str(ROOT / "system" / "scripts"))
sys.path.insert(0, str(ROOT / "system" / "scripts" / "vendor"))
from test_decisions_prep import prep_world  # noqa: E402
from test_prep_reimagined import py  # noqa: E402
from test_tracker import Vault  # noqa: E402

TITLE = "Quarterly catch-up"
STALE = "KITSTALE279 the ABC supplier is about to walk"
OTHER = "KITOTHER279 DEF budget research"
FOREIGN = "<html>KITFOREIGN279 Alan's own agenda file, not written by creaite</html>"


def case(name, status, ev=""):
    print(f"### CASE {name} | {status} | {str(ev)[:200]}", flush=True)


class P(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        prep_world(self.v)
        cal = self.v.root / "system/staging/calendar.json"
        data = json.loads(cal.read_text())
        for evs in data["days"].values():
            evs[0]["title"] = TITLE
        cal.write_text(json.dumps(data))
        self.key = f"09:00|{TITLE}"

    def tearDown(self):
        self.v.cleanup()

    def remember(self, code):
        py(self.v, f"import paths; p = paths.SETTINGS if hasattr(paths, 'SETTINGS') else paths.ROOT / 'system/config/settings.json'; "
                   f"s = json.loads(p.read_text()); s.setdefault('prep', {{}}).setdefault('series', {{}})['quarterly catch up'] = {code!r}; "
                   f"p.write_text(json.dumps(s)); print(json.dumps(1))")

    def opens(self, label="a meeting with no project opens"):
        """True when the tree opens a prep page for a meeting with no project; else False after printing the SKIP."""
        c = py(self.v, f"import prep_page; c = prep_page.context({self.key!r}); print(json.dumps({{'error': c.get('error'), 'project': c.get('project')}}))")
        if c.get("error"):
            case(label, "SKIP", f"before #279, the tree answers: {str(c['error'])[:100]}")
            return False
        return True

    def build(self, code, reply, key=None):
        self.remember(code)
        out = py(self.v, "import prep_page\ntry:\n    rel, page = prep_page.build(" + repr(key or self.key) + f", {reply!r})\n    r = [rel, page]\n"
                 "except ValueError as e:\n    r = [None, str(e)]\nprint(json.dumps(r))")
        return out[0], out[1]

    def prep_files(self):
        return sorted(str(f.relative_to(self.v.root)) for f in (self.v.root / "projects").rglob("*Prep -*") if f.is_file())

    def text(self, rel):
        return (self.v.root / rel).read_text(encoding="utf-8", errors="ignore")

    # ── the page itself ──────────────────────────────────────────────────────────────────────────────────────────────────
    def test_page(self):
        if not self.opens("page: a meeting with no project opens"):
            return
        for how, code in (("No project (chosen)", "_portfolio"), ("not chosen yet", "")):
            self.setUp_clean()
            rel, page = self.build(code, {"about": "KITNP about the quarter", "notes": [{"text": "KITNP note"}]})
            if not rel:
                case(f"{how}: the page is built", "HELD", str(page)[:120])
                continue
            filed = self.text(rel)
            for label, doc in (("the returned page", page), ("the filed file", filed)):
                miss = [w for w, ok in (("Internal tag", re.search(r'class="internal"[^>]*>\s*Internal\s*<', doc) is not None),
                                         ("never sent", "never sent" in doc), ("not for the client", "not for the client" in doc)) if not ok]
                case(f"{how}: {label} is marked Internal and never sent", "LEAK" if miss else "PASS",
                     f"missing {miss}" if miss else "Internal tag, 'not for the client', 'never sent'")
            folder = py(self.v, "import paths; print(json.dumps(paths.rel(paths.folder('_portfolio', 'agendas'))))")
            files = self.prep_files()
            outside = [f for f in files if not f.startswith(folder + "/")]
            case(f"{how}: filed under the portfolio's Agendas folder only", "LEAK" if outside or rel not in files or not rel.startswith(folder + "/") else "PASS",
                 f"outside {outside}, returned {rel}" if outside or not rel.startswith(folder + "/") else f"{len(files)} page(s), all in {folder}")
            view = py(self.v, f"import prep_view; v = prep_view.view({self.key!r}); print(json.dumps(v, default=str))")
            tagged = (view.get("model") or {}).get("meeting", {}).get("project")
            case(f"{how}: the in-app page is the all-projects view", "PASS" if tagged == "_portfolio" else "LEAK", f"project {tagged!r}")

    def setUp_clean(self):
        """A new vault for each way (a page filed before would be this meeting's own)."""
        self.tearDown()
        self.setUp()

    def test_overwrite(self):
        if not self.opens("overwrite: a meeting with no project opens"):
            return
        self.remember("_portfolio")
        target = py(self.v, f"import prep_page; t, r = prep_page.place(prep_page.context({self.key!r})); print(json.dumps(prep_page.paths.rel(t)))")
        f = self.v.root / target
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(FOREIGN, encoding="utf-8")
        rel, _ = self.build("_portfolio", {"about": "first"})
        case("a file creaite did not write is not overwritten", "LEAK" if f.read_text(encoding="utf-8") != FOREIGN else "PASS",
             "Alan's file was replaced" if f.read_text(encoding="utf-8") != FOREIGN else f"kept; the page went to {rel}")
        case("... and the page was written beside it under another name", "PASS" if rel and rel != target and (self.v.root / rel).is_file() else "LEAK",
             f"{rel}" if rel and rel != target else "no separate page")
        # a page creaite wrote and Alan then edited
        own = self.v.root / rel
        own.write_text(own.read_text(encoding="utf-8") + "\n<!-- KITEDIT279 Alan's note -->", encoding="utf-8")
        edited = own.read_bytes()
        rel2, _ = self.build("_portfolio", {"about": "second"})
        case("a page Alan edited since is not overwritten", "LEAK" if own.read_bytes() != edited else "PASS",
             "the edited page was replaced" if own.read_bytes() != edited else f"kept; the new page went to {rel2}")
        # creaite's own unchanged page is still replaced (control)
        rel3, _ = self.build("_portfolio", {"about": "third"})
        rel4, _ = self.build("_portfolio", {"about": "fourth"})
        case("control: creaite's own unchanged page is replaced in place", "PASS" if rel3 == rel4 else "CTRL-FAIL", f"{rel3} / {rel4}")

    def test_same_title(self):
        if not self.opens("same title: a meeting with no project opens"):
            return
        self.remember("_portfolio")
        cal = self.v.root / "system/staging/calendar.json"
        data = json.loads(cal.read_text())
        for evs in data["days"].values():
            evs.append({**evs[0], "id": "t2", "start": "11:00", "end": "12:00"})
        cal.write_text(json.dumps(data))
        one, _ = self.build("_portfolio", {"about": "KITFIRST first meeting"})
        two, _ = self.build("_portfolio", {"about": "KITSECOND second meeting"}, key="11:00|" + TITLE)
        ok = bool(one and two and one != two and "KITFIRST" in self.text(one) and "KITSECOND" in self.text(two))
        case("two meetings with one title on one day keep their own pages", "PASS" if ok else "LEAK",
             f"{one} / {two}" if ok else f"the second replaced the first or lost it: {one} / {two}")
        again, _ = self.build("_portfolio", {"about": "KITAGAIN again"}, key="11:00|" + TITLE)
        case("control: a meeting's own page is still replaced by its own rebuild", "PASS" if again == two else "CTRL-FAIL", f"{two} / {again}")

    # ── research stored for another project ──────────────────────────────────────────────────────────────────────────────
    def switched(self, was, now_code, label):
        """Research built for `was`, then the series is switched to `now_code`: nothing of it is shown, filed again or changed."""
        self.setUp_clean()
        rel, _ = self.build(was, {"about": STALE, "notes": [{"text": STALE + " note"}]})
        if not rel:
            case(f"{label}: research built for {was or 'nothing'}", "HELD", "not built")
            return
        before = self.v.root.joinpath(rel).read_bytes()
        self.remember(now_code)
        v = py(self.v, f"import prep_view; print(json.dumps(prep_view.view({self.key!r}), default=str))")
        blob = json.dumps(v, default=str)
        case(f"{label}: the earlier research is not in the page shown", "LEAK" if STALE in blob else "PASS",
             "the other project's research is shown" if STALE in blob else f"project {(v.get('model') or {}).get('meeting', {}).get('project')!r}, stale {bool(v.get('stale'))}")
        case(f"{label}: the page says the research was for another project", "PASS" if v.get("stale") else "LEAK", f"stale {v.get('stale')}")
        day = py(self.v, f"import prep_page; print(json.dumps(prep_page.context({self.key!r})['day']))")
        out = py(self.v, f"import prep_view; print(json.dumps(prep_view.regenerate({self.key!r}, {day!r}), default=str))")
        files = self.prep_files()
        case(f"{label}: Regenerate does not file the old research again", "LEAK" if out is not None or len(files) != 1 else "PASS",
             f"regenerate gave {out}, files {files}" if out is not None or len(files) != 1 else "None; one page, unchanged")
        case(f"{label}: the earlier page is kept unchanged", "PASS" if self.v.root.joinpath(rel).read_bytes() == before else "LEAK", rel)
        rel2, page = self.build(now_code, {"about": OTHER})
        if rel2:
            case(f"{label}: a new page for the new project holds none of the old research", "LEAK" if STALE in page or STALE in self.text(rel2) else "PASS",
                 rel2)

    def test_stale(self):
        if not self.opens("stale: a meeting with no project opens"):
            return
        self.switched("ABC", "_portfolio", "ABC -> No project")
        self.switched("_portfolio", "ABC", "No project -> ABC")
        self.switched("ABC", "DEF", "ABC -> DEF")
        self.switched("ABC", "ZZZ", "ABC -> a code that is no project")


if __name__ == "__main__":
    one = {"page": "test_page", "overwrite": "test_overwrite", "same-title": "test_same_title", "stale": "test_stale"}
    tests = list(one.values()) if VARIANT == "all" else [one[VARIANT]]
    unittest.main(argv=["x"] + [f"P.{t}" for t in tests], verbosity=0)
