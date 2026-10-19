import sys, base64, urllib.parse, unittest
from pathlib import Path
T = Path("${REPO_ROOT}/.claude/worktrees/review-fix/dev/tests")
sys.path.insert(0, str(T))
from test_export_page import LeakFix, page, Server  # noqa
W = "Walrus budget cut"
SVG = f'<svg xmlns="http://www.w3.org/2000/svg"><text x="1" y="9">{W}</text></svg>'
B64 = "data:image/svg+xml;base64," + base64.b64encode(SVG.encode()).decode()
PCT = "data:image/svg+xml," + urllib.parse.quote(SVG)

class Atk(LeakFix):
    def chk(self, label, pg):
        res = {}
        if not hasattr(self, "_b"):
            self._b = (("internal", self.saved(date="2026-10-09")), ("client", self.client()))
        for kind, path in self._b:
            out, why = self.build(path, pg)
            leaked = out is not None and (W in out.split("</style>",2)[-1] or "V2FscnVz" in out or "Walrus%20budget" in out or "Walrus" in out.split("</style>",2)[-1])
            tail = out.split("</style>",2)[-1] if out else ""
            probes = [x for x in (B64[30:60], PCT[25:60], "\u2063", "\u034f", "attr(lang)", "ms_ABC-005", "\\41 BC", '"ABC-" "005"') if out and x in out]
            res[kind] = why or f"KEPT probes={probes}"
        print(f"\n### {label}: {res}", flush=True)

    def test_all(self):
        C = self.wrap
        for css in ('.a::after{content:"ABC-A-001"}','.a::after{content:"\\41 BC-A-001"}','.a::after{content:"ABC-A-" "001"}','.a::after{content:"ABC-A-"/**/"001"}'):
            self.chk("ID "+css, page(css=css))
        self.chk("ID text", page(C('<p>ABC-A-001</p>')))

if __name__ == "__main__":
    unittest.main(argv=["x", "Atk.test_all"], verbosity=1)
