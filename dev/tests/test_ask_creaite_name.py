"""Sprint 5 item 5 (BL-105): the assistant is "ask creaite", in lower case everywhere Alan reads it.

Run: python3 dev/tests/test_ask_creaite_name.py   (the browser test needs Google Chrome; skipped otherwise)
A sentence that starts with it keeps it lower case too. Code identifiers (askBtn, openChat) and the BRD's history are unchanged, and
dev/BRD.md, BACKLOG.md, BUILD.md, HANDOVER.md, the sprint briefs, release notes and the dated reference design are history, so they
aren't checked. The teal colour in the creaite teal theme (done on main) must still be there.
"""
import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
WRONG = re.compile(r"Ask creaite", re.I)          # any capital in the name: "Ask creaite", "ASK CREAITE", "Ask Creaite"


def tracked(*patterns):
    out = subprocess.run(["git", "ls-files", *patterns], cwd=REPO, capture_output=True, text=True).stdout.split("\n")
    return [REPO / f for f in out if f and not f.endswith(".bak")]


def capitalised(path):
    """The places in a file where the name has a capital letter."""
    text = path.read_text(encoding="utf-8", errors="ignore")
    return [m.group() for m in WRONG.finditer(text) if m.group() != "ask creaite"]


class StaticTests(unittest.TestCase):
    def test_the_dashboard_template_help_and_guides_never_capitalise_it(self):
        for rel in ("system/templates/dashboard.html", "system/templates/help.md", "system/templates/guide-first-day.html",
                    "system/templates/guide-how-to.html"):
            self.assertEqual(capitalised(REPO / rel), [], rel)

    def test_the_rules_skills_scripts_and_spec_never_capitalise_it(self):
        files = [REPO / "system/creaite-rules.md", REPO / "dev/dashboard-spec.md", *tracked(".claude/skills", "system/scripts/*.py")]
        files = [f for f in files if "vendor" not in f.parts]
        self.assertGreater(len(files), 20)
        bad = {str(f.relative_to(REPO)): capitalised(f) for f in files if capitalised(f)}
        self.assertEqual(bad, {})

    def test_the_tests_agree_with_the_page(self):
        bad = {f.name: capitalised(f) for f in tracked("dev/tests/*.py") if f.name != Path(__file__).name and capitalised(f)}
        self.assertEqual(bad, {})

    def test_it_is_still_called_something_in_the_page(self):
        text = (REPO / "system/templates/dashboard.html").read_text(encoding="utf-8")
        self.assertGreater(text.count("ask creaite"), 20)                                            # the name is used, in lower case
        self.assertIn('<span class="asklab">ask creaite</span>', text)                               # the search bar's button
        self.assertIn('aria-label="Resize ask creaite"', text)

    def test_the_teal_in_the_creaite_theme_is_kept(self):
        text = (REPO / "system/templates/dashboard.html").read_text(encoding="utf-8")
        self.assertIn(':root[data-palette="creaite"] #askBtn,:root[data-palette="creaite"] .chh h2{color:var(--accent)}', text)

    def test_code_identifiers_are_unchanged(self):
        text = (REPO / "system/templates/dashboard.html").read_text(encoding="utf-8")
        for ident in ("askBtn", "openChat", "askPerson", "vsAskBtn"):
            self.assertIn(ident, text)

    def test_history_is_left_alone(self):
        self.assertIn("Ask creaite", (REPO / "dev/BRD.md").read_text(encoding="utf-8"))              # the BRD's history keeps its capitals


class RenderedTests(unittest.TestCase):
    def test_the_built_dashboard_has_no_capitalised_name(self):
        from test_tracker import Vault
        v = Vault()
        try:
            populate(v)
            subprocess.run([sys.executable, str(v.root / "system/scripts/build_dashboard.py")], cwd=v.root, check=True, capture_output=True)
            html = (v.root / "dashboard.html").read_text(encoding="utf-8")
            self.assertEqual([m.group() for m in WRONG.finditer(html) if m.group() != "ask creaite"], [])
            self.assertIn("ask creaite", html)
        finally:
            v.cleanup()


class VisibleTests(LiveBrowserCase):
    shared_server = True

    def test_what_alan_sees_says_ask_creaite_in_lower_case(self):
        b = self.b
        b.eval("go('files')")
        b.wait("document.getElementById('vsAskBtn')")
        self.assertEqual(b.eval("document.querySelector('#vsAskBtn .asklab').textContent"), "ask creaite")
        self.assertIn("ask creaite", b.eval("document.getElementById('vsAskBtn').title"))
        b.eval("openChat()")
        b.wait("document.getElementById('chat').classList.contains('on')")
        heading = b.eval("document.querySelector('#chat .chh h2').textContent")
        self.assertEqual(heading.lower(), heading)                                                   # the panel heading, lower case
        self.assertIn("ask creaite", heading)
        for view in ("today", "work", "files", "settings"):
            b.eval(f"go({view!r})")
            self.assertEqual(b.eval("(document.body.innerText.match(/Ask creaite/gi)||[]).filter(x=>x!=='ask creaite')"), [], view)
        self.assertEqual(b.errors, [])

    def test_the_command_palette_and_help_say_it_in_lower_case(self):
        b = self.b
        labels = b.eval("ckItems('ask').map(i=>i.l+' '+(i.h||''))")
        self.assertEqual([x for x in labels if re.search("Ask creaite", x)], [])


if __name__ == "__main__":
    unittest.main()
