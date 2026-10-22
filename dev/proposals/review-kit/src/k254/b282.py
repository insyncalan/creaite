"""2.5.4 area (b): #282, the minutes' Actions section reads "Actions" in the exports where an older record stored "Action Items" (wording only,
`minutes_record.actions_wording`). The wording must never be the way Internal-only text reaches a distributed file: the distributed version is
filtered first (`distributed_of`), then re-worded, and the exports differ from the same export with the wording logic off in the heading word
and nothing else. Fictional meeting: a client-visible action, an Internal-only action (a marked row), an Internal-only summary line (a marked line),
filed as an OLD record whose Actions section stores "Action Items", exported internal and distributed, as HTML and as Word.
Each case prints:   ### CASE <name> | LEAK|PASS|HELD|CTRL-FAIL|SKIP | evidence
  LEAK  an Internal-only word is in a distributed output, or an export differs from the wording-off export in more than the heading word
  HELD  creaite refused the export (a refusal is the pass)   SKIP  the tree has no `actions_wording` (before #282): the heading cases only
Usage: python b282.py <tree root> <variant>      variants: export (internal and distributed, html and docx), drafts (the working copy and the files left behind), all (both)"""
import json
import re
import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(sys.argv.pop(1))
VARIANT = sys.argv.pop(1)
sys.path.insert(0, str(ROOT / "dev" / "tests"))
sys.path.insert(0, str(ROOT / "system" / "scripts"))
sys.path.insert(0, str(ROOT / "system" / "scripts" / "vendor"))
import test_minutes_approve as ma  # noqa: E402

MR = ROOT / "system/scripts/minutes_record.py"
HAS_WORDING = MR.is_file() and "def actions_wording" in MR.read_text(encoding="utf-8")
INT_ACTION, INT_LINE, VIS_ACTION = "Renegotiate the KITINTACT supplier margin", "KITINTLINE the board pack is for us only", "Circulate the KITVIS agenda pack"
INTERNAL_WORDS = ("KITINTACT", "KITINTLINE", "Renegotiate", "board pack is for us only")


def case(name, status, ev=""):
    print(f"### CASE {name} | {status} | {str(ev)[:200]}", flush=True)


ORIG_SPEC = ma.spec


def spec():
    s = ORIG_SPEC()
    s["minutes"]["summary"] = ["The committee met.", INT_LINE]
    v = {"project": "ABC"}
    s["items"] += [{"table": "actions", "values": {**v, "description": VIS_ACTION, "owner": "Jane Doe"}},      # n 8: client-visible
                   {"table": "actions", "values": {**v, "description": INT_ACTION, "owner": "Alan Carter"}}]   # n 9: marked Internal only
    return s


ma.spec = spec


def text_of(p):
    p = Path(p)
    if p.suffix == ".docx":
        with zipfile.ZipFile(p) as z:
            x = z.read("word/document.xml").decode("utf-8", "ignore")
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", x.replace("</w:p>", "\n"))).strip()
    return p.read_text(encoding="utf-8", errors="ignore")


def visible(html):
    """The words of a creaite HTML export (the data block and the style/script dropped)."""
    h = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", html)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h)).strip()


class P(ma.Base):
    def mark_old_record(self):
        """The record as an older tree stored it (Actions section headed "Action Items"), with the Internal-only line and row marked."""
        page = self.doc()
        for s in page["sections"]:
            if s.get("id") == "actions":
                s["heading"] = "Action Items"
                s["default_heading"] = "Action Items"
        page["layout"] = {**(page.get("layout") or {}), "distributed": True,
                          "internal_only": [{"section": "summary", "text": INT_LINE}, {"section": "actions", "ref": "@9"}]}
        r = self.js("import minutes_record\n" f"r = minutes_record.save_page({ma.DRAFT!r}, {page!r})\nr.pop('doc', None)\nprint(json.dumps(r))")
        self.assertTrue(r["ok"], r)
        a = self.approve(group=True, own=[4, 5, 6, 7])
        self.assertTrue(a["ok"], a)

    def export(self, fmt, version, off=False):
        pre = "import minutes_record\n" + ("minutes_record.actions_wording = lambda d: d\n" if off else "")
        r = self.js(pre + "try:\n    r = minutes_record.export(" + repr(ma.FILED) + f", {fmt!r}, True, version={version!r})\n"
                    "except Exception as e:\n    r = {'ok': False, 'message': type(e).__name__ + ': ' + str(e)}\nprint(json.dumps(r, default=str))")
        if not r.get("ok") or not r.get("path"):
            return None, str(r.get("message"))[:140]
        p = self.v.root / r["path"]
        return (text_of(p), "made") if p.is_file() else (None, "no file made")

    def test_export(self):
        self.mark_old_record()
        got = {}
        for version in ("internal", "distributed"):
            for fmt in ("html", "docx"):
                t, why = self.export(fmt, version)
                name = f"{version} {fmt}"
                if t is None:
                    case(f"{name}: export", "HELD", why)
                    continue
                got[(version, fmt)] = t
                body = visible(t) if fmt == "html" else t
                if version == "distributed":
                    hit = [w for w in INTERNAL_WORDS if w.lower() in t.lower()]
                    case(f"{name}: no Internal-only text", "LEAK" if hit else "PASS", f"found {hit}" if hit else f"{len(t)} chars, none of {len(INTERNAL_WORDS)} words")
                    case(f"{name} control: the client-visible action is there", "PASS" if "KITVIS" in t else "CTRL-FAIL", "" if "KITVIS" in t else "over-filtered")
                else:
                    case(f"{name} control: the Internal-only text is kept for the internal version", "PASS" if "KITINTACT" in t and "KITINTLINE" in t else "CTRL-FAIL",
                         "" if "KITINTACT" in t else "the internal export lost the marked text")
                if HAS_WORDING:
                    shown = re.search(r"\bActions\b", body) is not None
                    old = re.search(r"\bAction Items\b", body) is not None
                    case(f"{name}: the heading reads Actions", "PASS" if shown and not old else "LEAK" if old else "CTRL-FAIL",
                         "Actions, not Action Items" if shown and not old else ("'Action Items' is still in the file" if old else "no Actions heading"))
                else:
                    case(f"{name}: the heading reads Actions", "SKIP", "this tree has no minutes_record.actions_wording (before #282)")
        if not HAS_WORDING:
            return
        # the same export with the wording logic off: only the heading word may differ
        for (version, fmt), t in got.items():
            off, why = self.export(fmt, version, off=True)
            if off is None:
                case(f"{version} {fmt}: wording-off export", "CTRL-FAIL", why)
                continue
            a = visible(t) if fmt == "html" else t
            b = visible(off) if fmt == "html" else off
            case(f"{version} {fmt} control: with the wording off the old record still says Action Items", "PASS" if "Action Items" in b else "CTRL-FAIL",
                 "" if "Action Items" in b else "the record does not store the old heading: the comparison proves nothing")
            b = re.sub(r"\bAction Items\b", "Actions", b)
            same = a == b
            if not same:
                wa, wb = a.split(), b.split()
                extra = [w for w in set(wa) ^ set(wb)][:8]
            case(f"{version} {fmt}: only the heading word differs from the wording-off export", "PASS" if same else "LEAK",
                 "identical once 'Action Items' is read as 'Actions'" if same else f"differs beyond the heading: {extra}")

    def test_drafts(self):
        self.mark_old_record()
        for fmt in ("html", "docx"):
            self.export(fmt, "distributed")
        left = [f.name for f in (self.v.root / "system/staging/drafts").iterdir() if "(distributed)" in f.name]
        case("distributed: no working copy is left in drafts", "LEAK" if left else "PASS", f"left {left}" if left else "none left")
        stray = [str(f.relative_to(self.v.root)) for f in self.v.root.rglob("*") if f.is_file() and "KITINT" in f.read_text(encoding="utf-8", errors="ignore")
                 and "(distributed)" in f.name]
        case("distributed: no file named (distributed) holds an Internal-only word", "LEAK" if stray else "PASS", f"{stray}" if stray else "none")


if __name__ == "__main__":
    tests = {"export": ["test_export"], "drafts": ["test_drafts"], "all": ["test_export", "test_drafts"]}[VARIANT]
    unittest.main(argv=["x"] + [f"P.{t}" for t in tests], verbosity=0)
