"""BL-301 A's gate: every Current state round-trips byte for byte through the one editor, before (and while) any editor
uses it.

Run: python3 dev/tests/test_one_editor_gate.py   (needs Google Chrome; skipped otherwise)

Two layers, both on what ships (the committed system/templates/vendor/tiptap/ module, no cache, no network):
  * the round-trip gate (dev/tools/tiptap_roundtrip.py) over the sample vault's Current states (`current`), every test
    fixture's (`fixtures`) and the hard cases, with the pinned Tiptap: no case may fail;
  * the same Current states through the dashboard's own wrapper (src/core/editor.js `creaiteEditor`, in the built page):
    each pane loaded, given back unchanged as it came, and, once edited and put back, written by the exact writer to the
    same bytes; the two panes joined give the Current state the editor was opened on.
If this test fails, no editor may switch to the one editor (and a switched one must go back) until it passes again.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import cdp  # noqa: E402
import shutil  # noqa: E402
import tiptap  # noqa: E402
import tiptap_roundtrip as gate  # noqa: E402
from test_tracker import Vault  # noqa: E402


@unittest.skipUnless(cdp.chrome_path(), "needs Google Chrome")
class GateOnTheVendoredModule(unittest.TestCase):
    """The gate's groups, on the vendored module."""

    def test_every_current_state_and_fixture_round_trips(self):
        cases = gate.corpus(("current", "fixtures", "hard"))
        groups = {g: sum(c.group == g for c in cases) for g in ("current", "fixtures", "hard")}
        self.assertGreaterEqual(groups["current"], 7)            # the sample vault, the demo projects and the template
        self.assertGreaterEqual(groups["fixtures"], 18)          # every fixture with a Current state
        results = gate.run(cases, gate.vendored_js(), "exact", tiptap.PINNED)
        lines, failed = gate.report(results)
        self.assertEqual(failed, 0, "\n".join(x for x in lines if not x.startswith("PASS")))


# Each text through the wrapper: unchanged (as it came), then touched (a character typed and taken out again, so the
# exact writer writes it), and the panes joined again.
WRAPPER_JS = r"""(texts => texts.map(t => {
  const out = {};
  for (const [k, md] of [["left", t[0]], ["right", t[1]]]) {
    const el = document.createElement("div"); document.body.appendChild(el);
    const h = creaiteEditor(el, {features: "current", markdown: md});
    const same = h.value();
    const ed = h.editor, v = ed.view; let p = null; ed.state.doc.descendants((n, pos) => { if (p === null && n.isText) p = pos; });
    if (p !== null) { v.dispatch(v.state.tr.insertText("x", p)); v.dispatch(v.state.tr.delete(p, p + 1)); }
    out[k] = {same, text: p !== null, touched: h.touched(), written: h.value()};
    h.destroy(); el.remove();
  }
  out.joined = joinPanes(out.left.written, out.right.written);
  return out;
}))(%s)"""


@unittest.skipUnless(cdp.chrome_path(), "needs Google Chrome")
class GateThroughTheDashboardsEditor(unittest.TestCase):
    """The dashboard's own editor (the built page) on every Current state the gate reads."""

    def test_each_pane_is_given_back_byte_for_byte(self):
        texts = {}
        for c in gate.corpus(("current", "fixtures")):
            texts.setdefault(c.source.rsplit(" (", 1)[0], {})[c.source.endswith("(right pane)")] = c.text
        pairs = sorted((v.get(False, ""), v.get(True, "")) for v in texts.values())
        v = Vault()                                      # a built page with data (the template alone has none)
        self.addCleanup(shutil.rmtree, v.root, True)
        v.run("init")
        v.run(script="build_dashboard.py")
        page = (v.root / "dashboard.html").as_uri()
        with cdp.Browser() as b:
            b.goto(page, wait_for="typeof creaiteEditor==='function'")
            got = b.eval(WRAPPER_JS % json.dumps(pairs))
        for (left, right), r in zip(pairs, got):
            with self.subTest(left=left[:60]):
                for md, side in ((left, r["left"]), (right, r["right"])):
                    self.assertEqual(side["same"], md)              # unchanged: as it came
                    self.assertEqual(side["touched"], side["text"])   # a pane with text was edited (one without: a picture)
                    self.assertEqual(side["written"], md)           # edited and put back: the exact writer, same bytes
                self.assertEqual(r["joined"], gate.docx_tools.join_panes(left, right))   # one message, as reports join it


if __name__ == "__main__":
    unittest.main()
