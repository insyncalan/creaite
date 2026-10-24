"""#355 (2.6.4b): three small follow-ups, each with a mutant that must go red.

1. a rename of the filed minutes rewrites an update item's top-level source, not only values.source (minutes_destination._rewrite);
2. a refused Approve minutes clears the "Filed as" note (stores/minutes.js calls dismissFiled);
3. only the Run now button sends the consent flag for a held queue (ask.js).
Run: python3 dev/tests/test_355_followups.py      (quick tier: no Chrome)
"""
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "system/scripts"))
SRC = REPO / "system/templates/dashboard/src"
OLD = "projects/ABC Example/minutes/2026-10-14 Steering.html"
NEW = "projects/ABC Example/minutes/2026-10-14 Steering (pm).html"


def rewrite_fn(text):
    """The _rewrite function of the given source text, compiled alone."""
    m = re.search(r"^def _rewrite\(.*?(?=^def _save)", text, re.S | re.M)
    ns = {}
    exec(m.group(0), ns)
    return ns["_rewrite"]


def data():
    return {"meeting": {"file_ops": [{"op": "copy", "to": OLD}], "source_map": {OLD: "t.vtt"}},
            "items": [{"op": "new", "values": {"source": OLD + " (item 1)"}},
                      {"op": "update", "source": OLD + " (item 2)", "values": {"status": "done"}},
                      {"op": "update", "source": "other.html", "values": {}}]}


class Rewrite(unittest.TestCase):
    TEXT = (REPO / "system/scripts/minutes_destination.py").read_text(encoding="utf-8")

    def test_an_update_items_top_level_source_follows_the_rename(self):
        d = data()
        rewrite_fn(self.TEXT)(d, OLD, NEW)
        self.assertEqual(d["items"][0]["values"]["source"], NEW + " (item 1)")
        self.assertEqual(d["items"][1]["source"], NEW + " (item 2)")
        self.assertEqual(d["items"][2]["source"], "other.html")
        self.assertEqual(d["meeting"]["file_ops"][0]["to"], NEW)

    def test_mutant_values_only_leaves_the_top_level_source(self):
        mutant = self.TEXT.replace('for holder in (it.get("values") or {}, it):', 'for holder in (it.get("values") or {},):')
        self.assertNotEqual(mutant, self.TEXT)
        d = data()
        rewrite_fn(mutant)(d, OLD, NEW)
        self.assertEqual(d["items"][1]["source"], OLD + " (item 2)")        # the fault the mutant brings back


class Page(unittest.TestCase):
    MIN = (SRC / "stores/minutes.js").read_text(encoding="utf-8")
    ASK = (SRC / "ask.js").read_text(encoding="utf-8")

    def test_a_refused_approve_clears_the_filed_note(self):
        self.assertRegex(self.MIN, r"forgetRenamed\(v\.proposal\);\s*\n\s*if \(!r \|\| !r\.ok\) dismissFiled\(\);")
        self.assertRegex(self.MIN, r"import \{[^}]*\bdismissFiled\b[^}]*\} from \"\./minutesFiling\.js\"")

    def test_mutant_without_the_clear_leaves_the_note(self):
        mutant = self.MIN.replace("if (!r || !r.ok) dismissFiled();", "")
        self.assertNotRegex(mutant, r"if \(!r \|\| !r\.ok\) dismissFiled\(\)")

    def test_only_run_now_sends_the_consent_flag(self):
        sends = re.findall(r'api\("/api/ask/queue",\{op:"resume"[^}]*\}\)', self.ASK)
        flagged = [s for s in sends if "run_now:true" in s]
        self.assertEqual(len(sends), 2, sends)                                # queueResume and the Run now click
        self.assertEqual(len(flagged), 1, sends)
        self.assertIn("run_now:true", self.ASK[self.ASK.index("if(go){"):self.ASK.index("if(go){") + 120])
        qr = self.ASK[self.ASK.index("export async function queueResume"):][:260]
        self.assertNotIn("run_now", qr)                                       # the automatic restart after a card carries none

    def test_mutant_flag_on_the_automatic_restart_is_caught(self):
        mutant = self.ASK.replace('{op:"resume"}', '{op:"resume",run_now:true}')
        qr = mutant[mutant.index("export async function queueResume"):][:260]
        self.assertIn("run_now", qr)


if __name__ == "__main__":
    unittest.main()
