"""BL-301 part A: the Tiptap round-trip gate's runner and corpus (dev/tools/tiptap_roundtrip.py), and creaite's exact
writer (dev/tiptap/writer.js, source.js) when the pinned Tiptap is on this machine.

Run: python3 dev/tests/test_tiptap_roundtrip.py   (needs Google Chrome; the runner tests are skipped without it)

The runner is given a fake bundle (window.CreaiteTiptap.roundTripAll written here: it encodes "&" as upstream Tiptap
does, fails on "boom" and reports "lossy" as not faithful), so no network and no real Tiptap are needed. The real
writer's tests run only when `python3 dev/tools/tiptap.py fetch` has filled dev/.cache (they never download anything):
the whole gate must pass, and an edited document must be written in creaite's style.
"""
import contextlib
import hashlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import cdp  # noqa: E402
import esbuild  # noqa: E402
import tiptap  # noqa: E402
import tiptap_roundtrip as gate  # noqa: E402

FAKE_BUNDLE = """var CreaiteTiptap = { PINNED: "%s", roundTripAll: function (texts, features, mode, html) {
  return texts.map(function (t) {
    if (t === "boom") return { error: "boom" };
    if (t === "lossy") return { out: t, faithful: false };
    if (html) return { out: t.replace(/<[^>]+>/g, "") };
    if (features === "notes") return { out: t + "!" };
    return { out: mode === "exact" ? t : t.replace(/&/g, "&amp;") };
  });
} };""" % tiptap.PINNED


def pinned_tiptap_here():
    """True when the pinned Tiptap packages and esbuild are already in dev/.cache (nothing is downloaded to check)."""
    try:
        ready = esbuild.target(esbuild.platform_key()).is_file()
    except Exception:  # noqa: BLE001 - an unknown platform: no esbuild
        return False
    root = tiptap.modules_dir()
    return ready and all(tiptap.is_unpacked(root / name, sha) for name, _, sha in tiptap.PACKAGES)


@unittest.skipUnless(cdp.chrome_path(), "needs Google Chrome")
class RunnerTest(unittest.TestCase):
    """run() and report() on a tiny fixture."""

    def test_pass_fail_and_error(self):
        """Each case's result comes back in order; a changed text and an error both fail, with where and why."""
        cases = [gate.Case("current", "same", "Plain text."), gate.Case("current", "amp", "Q&A"),
                 gate.Case("minutes", "err", "boom"), gate.Case("constructs", "note", "x", "notes")]
        results = gate.run(cases, FAKE_BUNDLE, "upstream")
        self.assertEqual([(c.source, o, e) for c, o, e in results],
                         [("same", "Plain text.", None), ("amp", "Q&amp;A", None), ("err", None, "boom"),
                          ("note", "x!", None)])
        lines, failed = gate.report(results)
        self.assertEqual(failed, 3)
        self.assertEqual(lines[0], "PASS [current] same")
        self.assertIn("FAIL [current] amp  at 2:", lines[1])
        self.assertEqual(lines[2], "FAIL [minutes] err  error: boom")
        self.assertEqual(lines[-1], "round-trip: current 1/2 pass, minutes 0/1 pass, constructs 0/1 pass; 3 failed")

    def test_mode_is_passed_through(self):
        """The exact writer is the default; the mode reaches the page's roundTripAll."""
        self.assertEqual(gate.run([gate.Case("current", "amp", "Q&A")], FAKE_BUNDLE)[0][1], "Q&A")
        self.assertEqual(gate.run([gate.Case("current", "amp", "Q&A")], FAKE_BUNDLE, "upstream")[0][1], "Q&amp;A")

    def test_unfaithful_fails_even_when_the_bytes_match(self):
        """The writer's own check (faithful: false) fails the case, whatever came back."""
        (case, out, error), = gate.run([gate.Case("hard", "lossy", "lossy")], FAKE_BUNDLE)
        self.assertEqual(out, "lossy")
        self.assertEqual(error, gate.UNFAITHFUL)
        self.assertEqual(gate.report([(case, out, error)])[1], 1)

    def test_expected_loss_and_typed_html(self):
        """A case with `expect` passes on exactly that, and fails on its own text; an html case goes to the page as
        html."""
        cases = [gate.Case("hard", "known loss", "a&b", expect="a&b"),
                 gate.Case("hard", "loss changed", "a&b", expect="a and b"),
                 gate.Case("hard", "typed", "<p>Hi</p>", expect="Hi", html=True)]
        lines, failed = gate.report(gate.run(cases, FAKE_BUNDLE))
        self.assertEqual(failed, 1)
        self.assertEqual([line.split(" [")[0] for line in lines[:3]], ["PASS", "FAIL", "PASS"])

    def test_a_different_tiptap_fails_loudly(self):
        """The bundle must report the pinned version: after an upgrade the gate stops until it is re-checked."""
        other = FAKE_BUNDLE.replace(f'PINNED: "{tiptap.PINNED}"', 'PINNED: "9.9.9"')
        with self.assertRaises(gate.VersionError) as e:
            gate.run([gate.Case("current", "s", "a")], other, pinned=tiptap.PINNED)
        self.assertIn("9.9.9", str(e.exception))
        self.assertEqual(gate.run([gate.Case("current", "s", "a")], FAKE_BUNDLE, pinned=tiptap.PINNED)[0][1], "a")

    def test_script_end_tag_in_the_bundle_is_safe(self):
        """A bundle holding "</script" (as a string) still loads."""
        results = gate.run([gate.Case("current", "s", "a")], FAKE_BUNDLE + '\nvar s = "</script>";')
        self.assertEqual(results[0][1], "a")


class CorpusTest(unittest.TestCase):
    """The corpus readers on fixtures."""

    def setUp(self):
        """A private folder for each test."""
        self.tmp = Path(tempfile.mkdtemp(prefix="creaite-tiptap-gate-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_current_state_panes(self):
        """A project's Current state is read as the dashboard's editor gets it (guidance line dropped), one case per
        pane; a project without the section gives none."""
        one = self.tmp / "ABC Alpha"
        one.mkdir()
        (one / "CLAUDE.md").write_text("# ABC\n\n## Current state\n\n_Rewritten weekly._\n\nLeft **text**.\n\n"
                                       "<!-- creaite: second pane -->\n\nRight text.\n\n## Next\n\nNot this.\n")
        two = self.tmp / "DEF Beta"
        two.mkdir()
        (two / "CLAUDE.md").write_text("# DEF\n\n## Brief\n\nNo current state.\n")
        cases = gate.current_cases(self.tmp, demo=False)
        self.assertEqual([(c.group, c.text) for c in cases], [("current", "Left **text**."), ("current", "Right text.")])
        self.assertTrue(cases[0].source.endswith("ABC Alpha/CLAUDE.md (left pane)"))

    def test_minutes_values(self):
        """Every string in a dict literal with a SUMMARY key; flags and values built from variables are skipped."""
        src = self.tmp / "fixture.py"
        src.write_text('title = "T"\nV = {"MEETING_TITLE": title, "SUMMARY": ["One.", "Two & three."],\n'
                       '     "UPDATES": [{"heading": "SOW", "items": [{"flag": "PRIORITY", "text": "Sign it."}]}],\n'
                       '     "ACTIONS": [{"A_OWNER": "Sara", "A_TEXT": "Send it"}], "OPEN_QUESTIONS": []}\n'
                       'OTHER = {"not": "minutes"}\n')
        texts = [c.text for c in gate.minutes_cases((str(src),))]
        self.assertEqual(texts, ["One.", "Two & three.", "SOW", "Sign it.", "Sara", "Send it"])

    def test_constructs_are_canonical(self):
        """The constructs are in md_normalise's form (what creaite stores), and the notes-only ones use notes."""
        cases = gate.construct_cases()
        self.assertTrue(any(c.source == "nested list" and c.text.startswith("- Data access\n  - ") for c in cases))
        self.assertEqual({c.features for c in cases if c.source.endswith("(notes)")}, {"notes"})

    def test_hard_cases_reader(self):
        """The JSON keeps CRLF and trailing spaces byte for byte; features name the case; html cases carry html."""
        path = self.tmp / "hard.json"
        path.write_text(json.dumps([
            {"name": "crlf", "text": "a\r\nb  \n", "why": "w"},
            {"name": "table", "features": "notes", "text": "| a |", "expect": "| a |", "why": "w"},
            {"name": "typed", "html": "<p>x</p>", "expect": "x", "why": "w"}]))
        cases = gate.hard_cases(path)
        self.assertEqual([(c.source, c.text, c.wanted, c.features, c.html) for c in cases],
                         [("crlf", "a\r\nb  \n", "a\r\nb  \n", "current", False),
                          ("table (notes)", "| a |", "| a |", "notes", False),
                          ("typed", "<p>x</p>", "x", "current", True)])

    def test_the_hard_cases_file(self):
        """dev/tiptap/hard-cases.json: every case named once, with why; text or html; html cases say what they give;
        and it holds the forms the gate promises (tables, comments, CRLF, trailing spaces, nesting, bracketed links)."""
        raw = json.loads(gate.HARD_CASES.read_text(encoding="utf-8"))
        names = [c["name"] for c in raw]
        self.assertEqual(len(names), len(set(names)))
        for c in raw:
            self.assertTrue(c.get("why"), c["name"])
            self.assertEqual(("text" in c) + ("html" in c), 1, c["name"])
            if "html" in c:
                self.assertIn("expect", c, c["name"])
        texts = [c.get("text", "") for c in raw]
        for needle in ("| --- |", "<!-- creaite: second pane -->", "\r\n", "  \n", "\n  1. ", "[the [1] plan]"):
            self.assertTrue(any(needle in t for t in texts), needle)
        self.assertEqual(len(gate.hard_cases()), len(raw))


@unittest.skipUnless(cdp.chrome_path() and pinned_tiptap_here(),
                     "needs Google Chrome and the pinned Tiptap in dev/.cache (python3 dev/tools/tiptap.py fetch)")
class ExactWriterTest(unittest.TestCase):
    """The real bundle: the whole gate passes, and an edited document is written in creaite's style."""

    @classmethod
    def setUpClass(cls):
        """One bundle for the class."""
        cls.bundle = tiptap.bundle().decode("utf-8")

    def test_the_gate_passes(self):
        """Every case of every group comes back byte for byte (or exactly as its known loss says)."""
        lines, failed = gate.report(gate.run(gate.corpus(), self.bundle, "exact", tiptap.PINNED))
        self.assertEqual(failed, 0, "\n".join(line for line in lines if not line.startswith("PASS")))

    def test_edits(self):
        """A table edited loses its source and is written fresh; new italic is "_" beside a kept "*"; two lists side
        by side can't be written apart, and the writer says so."""
        script = """(() => {
          const T = CreaiteTiptap, out = {};
          const ed = T.createEditor(null, { markdown: "| Name      |    Role |\\n|:----------|--------:|\\n| Sara | Sponsor |",
            features: "notes" });
          let pos = null;
          ed.state.doc.descendants((n, p) => { if (n.isText && n.text === "Sponsor") pos = p; });
          ed.commands.insertContentAt({ from: pos, to: pos + 7 }, "Owner");
          out.table = T.markdownOf(ed);
          const ed2 = T.createEditor(null, { markdown: "- a" });
          ed2.commands.insertContentAt(ed2.state.doc.content.size, { type: "bulletList", content: [{ type: "listItem",
            content: [{ type: "paragraph", content: [{ type: "text", text: "b" }] }] }] });
          out.lists = T.markdownOf(ed2);
          const ed3 = T.createEditor(null, { markdown: "Old *style* here." });
          ed3.commands.insertContentAt(ed3.state.doc.content.size - 1, [{ type: "text", text: " and " },
            { type: "text", text: "new", marks: [{ type: "italic" }] }]);
          out.italic = T.markdownOf(ed3);
          return out;
        })()"""
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "w.html"
            page.write_text(gate.PAGE.format(js=self.bundle.replace("</script", "<\\/script")), encoding="utf-8")
            with cdp.Browser() as b:
                b.goto(page.as_uri(), wait_for="!!window.CreaiteTiptap")
                got = b.eval(script)
        self.assertEqual(got["table"], {"markdown": "| Name | Role |\n| :--- | ---: |\n| Sara | Owner |", "faithful": True})
        self.assertEqual(got["italic"], {"markdown": "Old *style* here. and _new_", "faithful": True})
        self.assertFalse(got["lists"]["faithful"])


def fake_run(cases, bundle_js, mode="exact", pinned=None):
    """run() without a browser: upstream Tiptap's known changes (entities, `_` italic, 3-space nesting, comments
    dropped, trailing space), so --private has failures to describe."""
    out = []
    for c in cases:
        t = c.text.replace("&", "&amp;").replace("_urgent_", "*urgent*").replace("\n  1. ", "\n   1. ")
        t = re.sub(r"<!--.*?-->\n*", "", t, flags=re.S).replace("  \n", "\n")
        out.append((c, t, "boom: " + c.text if "Kraken" in c.text else None))
    return out


class VaultTest(unittest.TestCase):
    """--vault and --private on a fixture vault: the real Current states are found, nothing from them is printed, and
    nothing is written. The browser part is faked (fake_run)."""

    SECRET = ("Zanzibar", "Quokka", "Marmalade", "Kraken", "Pelican", "Halibut", "Ostrich", "Juniper", "Walrus")

    def setUp(self):
        """A fixture vault whose projects live outside it (locations.projects_root, as in OneDrive), with a register."""
        self.tmp = Path(tempfile.mkdtemp(prefix="creaite-tiptap-vault-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.vault = self.tmp / "vault"
        (self.vault / "system" / "config").mkdir(parents=True)
        root = self.tmp / "Engagements"
        (self.vault / "system" / "config" / "settings.json").write_text(
            json.dumps({"locations": {"projects_root": str(root)}}))
        (root / "_Portfolio").mkdir(parents=True)
        (root / "_Portfolio" / "project-register.md").write_text(
            "| Code | Name | Folder under projects/ |\n|---|---|---|\n| ABC | Alpha | Zanzibar Programme |\n"
            "| DEF | Beta | Quokka Programme |\n| GHI | Gamma | Not There |\n")
        (root / "_Portfolio" / "PORTFOLIO.md").write_text("## Current state\n\nWalrus portfolio text.\n")
        (root / "Unregistered").mkdir()
        (root / "Unregistered" / "CLAUDE.md").write_text("## Current state\n\nWalrus.\n")
        abc = root / "Zanzibar Programme"
        abc.mkdir()
        (abc / "CLAUDE.md").write_text(
            "# ABC\n\n## Current state\n\n_Rewritten weekly._\n\nMarmalade Q&A is _urgent_ now.  \n"
            "Pelican next.\n\n![Halibut plan](images/missing.png)\n\n<!-- creaite: second pane -->\n\n"
            "1. Ostrich\n  1. Juniper\n\n## Brief\n\nWalrus not this.\n")
        dfe = root / "Quokka Programme"
        dfe.mkdir()
        (dfe / "CLAUDE.md").write_text("# DEF\n\n## Current state\n\n<!-- Halibut note -->\n\nKraken plain.\n")

    def snapshot(self):
        """Every file and folder under the fixture, with its bytes' hash and its modified time."""
        out = {}
        for d, dirs, files in os.walk(self.tmp):
            for name in dirs + files:
                f = Path(d) / name
                out[str(f)] = (f.is_dir() or hashlib.sha256(f.read_bytes()).hexdigest(), f.stat().st_mtime_ns)
        return out

    def main(self, *args):
        """(exit code, stdout, stderr) of the gate's command line, with the browser part faked."""
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(gate, "run", fake_run), mock.patch.object(gate.tiptap, "bundle", lambda: b""), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = gate.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_finds_the_current_states(self):
        """Each registered project's Current state, read as the dashboard reads it (guidance dropped), one case per
        pane, with ids only; the portfolio, an unregistered folder and a missing one give none. paths is put back."""
        root_before = gate.paths.ROOT
        cases = gate.vault_cases(self.vault)
        self.assertEqual([c.source for c in cases], ["ABC pane 1", "ABC pane 2", "DEF pane 1"])
        self.assertEqual(cases[0].text, "Marmalade Q&A is _urgent_ now. Pelican next.\n\n![Halibut plan](images/missing.png)")
        self.assertEqual(cases[1].text, "1. Ostrich\n  1. Juniper")
        self.assertEqual(gate.paths.ROOT, root_before)
        self.assertEqual(gate.paths.projects_root(), root_before / "projects")

    def test_default_layout(self):
        """With no projects_root the vault's own projects/ folder is read, the code from each folder's name."""
        v = self.tmp / "plain"
        (v / "projects" / "XYZ Zanzibar").mkdir(parents=True)
        (v / "projects" / "XYZ Zanzibar" / "CLAUDE.md").write_text("## Current state\n\nQuokka.\n")
        self.assertEqual([(c.source, c.text) for c in gate.vault_cases(v)], [("XYZ pane 1", "Quokka.")])

    def test_private_prints_no_vault_text(self):
        """--private and --private --json: ids, pass or fail, lengths and the kind of difference, never the text."""
        before = self.snapshot()
        code, out, err = self.main("--vault", str(self.vault), "--private")
        self.assertEqual(code, 1)
        for word in self.SECRET + ("Programme", "Rewritten", "urgent", "plain", "next", str(self.tmp)):
            self.assertNotIn(word, out + err)
        lines = out.splitlines()
        self.assertTrue(lines[0].startswith("FAIL [current] ABC pane 1  "))
        self.assertIn("escaped `&` (written as an entity)", lines[0])
        self.assertIn("FAIL [current] ABC pane 2  ", lines[1])
        self.assertIn("numbered list item (nested): list indent", lines[1])
        self.assertEqual(lines[2], "FAIL [current] DEF pane 1  {} bytes  editor error".format(
            len("<!-- Halibut note -->\n\nKraken plain.")))
        self.assertEqual(lines[-1], "round-trip: current 0/3 pass; 3 failed")

        code, out, err = self.main("--vault", str(self.vault), "--private", "--json")
        self.assertEqual(code, 1)
        for word in self.SECRET + ("Programme", str(self.tmp)):
            self.assertNotIn(word, out + err)
        rows = json.loads(out)
        self.assertEqual([r["id"] for r in rows], ["ABC pane 1", "ABC pane 2", "DEF pane 1"])
        self.assertEqual(set(rows[0]), {"id", "group", "pass", "bytes", "out_bytes", "byte_offset", "construct", "kind"})
        self.assertEqual(rows[2]["error"], "editor error")
        self.assertEqual(self.snapshot(), before, "the gate wrote to the vault or the projects folder")

    def test_unreadable_vault_says_nothing_of_it(self):
        """A missing projects folder stops the run with a message that holds no path or text."""
        (self.vault / "system" / "config" / "settings.json").write_text(
            json.dumps({"locations": {"projects_root": str(self.tmp / "Zanzibar")}}))
        code, out, err = self.main("--vault", str(self.vault), "--private")
        self.assertEqual(code, 2)
        self.assertNotIn("Zanzibar", out + err)


class ClassifyTest(unittest.TestCase):
    """classify(): where and how a text came back changed, with no text in the answer."""

    def test_kinds(self):
        """Each known change is named, at the right byte offset (multi-byte characters counted as bytes)."""
        cases = [("Q&A", "Q&amp;A", (1, "paragraph", "escaped `&` (written as an entity)")),
                 ("£ < x", "£ &lt; x", (3, "paragraph", "escaped `<` (written as an entity)")),
                 ("The _x_ y", "The *x* y", (4, "paragraph, italic", "italic `_` vs `*`")),
                 ("1. a\n  1. b", "1. a\n   1. b", (7, "numbered list item (nested)", "list indent")),
                 ("<!-- c -->\n\nT", "\n\nT", (0, "HTML comment", "HTML comment changed or dropped")),
                 ("a  \nb", "a\nb", (1, "paragraph", "trailing space dropped")),
                 ("w_r", "w\\_r", (1, "paragraph", "escaped `_` (backslash added)")),
                 ("see https://x.y", "see [https://x.y](https://x.y)", (4, "paragraph, bare URL", "bare URL written as a link")),
                 ("abc", "abd", (2, "paragraph", "a letter or digit became a letter or digit"))]
        for a, b, want in cases:
            self.assertEqual(gate.classify(a, b), want, a)
        self.assertIsNone(gate.classify("same", "same"))


if __name__ == "__main__":
    unittest.main()
