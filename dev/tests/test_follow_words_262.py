"""2.6.2: the follow flag is shown in the app, the word VIP never is (BL-288 revised; Alan, 23-10-2026). The user-visible
strings that used to say VIP (Help, the register template, the settings text, the session and sweep lines, the dashboard's
visible text, the skills' headings) say "follow" now. The enforcing code (drafts.VIP_RE and the rest) and the internal names
(vip.* keys, vip.json, sweep.py vip) keep the word and are not looked at here.

Run: python3 dev/tests/test_follow_words_262.py     (quick tier: no Chrome, no vault)
"""
import json
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WORD = re.compile(r"\bVIPs?\b")


def read(rel):
    return (REPO / rel).read_text(encoding="utf-8")


def visible_literals(js):
    """Single-line string and template literals of a script that contain the word, with block comments, whole-line comments and
    trailing line comments removed (a multi-line template is not looked at: the dashboard's visible text is in single-line ones)."""
    js = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), js, flags=re.S)
    out = []
    for l in js.split("\n"):
        if l.lstrip().startswith("//"):
            continue
        l = re.sub(r"\s//\s.*$", "", l)
        out += [m.group(0) for m in re.finditer(r"\"[^\"]*\"|'[^']*'|`[^`]*`", l)
                if WORD.search(m.group(0)) and m.group(0) != '"VIP"']       # "VIP" alone is the older register column's name
    return out


class FollowWords(unittest.TestCase):
    def test_help_has_no_vip(self):
        h = read("system/templates/help.md")
        self.assertIsNone(WORD.search(h))
        self.assertIn("## Never miss a message from someone you follow", h)
        self.assertIn("(#never-miss-a-message-from-someone-you-follow)", h)
        self.assertNotIn("never-miss-a-vip", h)
        self.assertIn("`follow Mia Hale`", h)

    def test_register_template_column_is_follow(self):
        t = read("system/templates/people-register-template.md")
        self.assertIn("| Hidden | Follow | Labels |", t)
        self.assertIn("- **Follow:**", t)
        # the one place the old column is named: the sentence saying it is still read
        left = [l for l in t.split("\n") if WORD.search(l)]
        self.assertEqual(len(left), 1)
        self.assertIn("older register", left[0])

    def test_settings_defaults_about(self):
        d = json.loads(read("system/templates/settings-defaults.json"))
        self.assertIsNone(WORD.search(d["vip"]["_about"]))      # the key stays: an internal name

    def test_printed_lines(self):
        s = read("system/scripts/sweep.py")
        self.assertIn("print(f\"Followed: {len(new)} new alert", s)
        self.assertIn("print(f\"Marked {n} follow alert", s)
        self.assertNotIn("print(f\"VIP:", s)
        self.assertNotIn("Marked {n} VIP", s)
        self.assertIsNone(WORD.search(re.search(r"def build_prompt.*?\n\n\n", read("system/scripts/calendar_refresh.py"), re.S).group(0)))

    def test_built_dashboard_shows_no_vip(self):
        page = read("system/templates/dashboard.html")
        parts = re.split(r"(<script\b[^>]*>.*?</script>|<style\b[^>]*>.*?</style>)", page, flags=re.S)
        html = "".join(p for p in parts if not p.startswith(("<script", "<style")))
        self.assertIsNone(WORD.search(re.sub(r"<!--.*?-->", "", html, flags=re.S)))
        for p in parts:
            if p.startswith("<script"):
                self.assertEqual(visible_literals(p), [])

    def test_dashboard_source_literals(self):
        for f in sorted((REPO / "system/templates/dashboard/src").rglob("*.js*")):
            self.assertEqual(visible_literals(f.read_text(encoding="utf-8")), [], f.name)

    def test_register_writes_follow_and_reads_both(self):
        j = read("system/templates/dashboard/src/stores/peopleRegister.js")
        self.assertIn("r.extra.Follow =", j)
        self.assertIn("x.Follow || x.VIP", j)
        self.assertIn("delete r.extra.VIP", j)

    def test_skills_headings_and_alias(self):
        sw = read(".claude/skills/cx-sweep/SKILL.md")
        self.assertIn("## People you follow (BL-99)", sw)
        self.assertNotIn("## VIPs", sw)
        self.assertNotIn("**VIPs first**", sw)
        ed = read(".claude/skills/cx-edit/SKILL.md")
        self.assertIn('"follow Mia Hale"', ed)
        self.assertIn("still understood", ed)                    # the old phrase, one release
        for s in ("cx-sweep", "cx-edit"):
            for l in read(f".claude/skills/{s}/SKILL.md").split("\n"):
                if WORD.search(l) and s == "cx-edit":
                    self.assertIn("older", l)                    # only the alias and the old column are named


if __name__ == "__main__":
    unittest.main()
