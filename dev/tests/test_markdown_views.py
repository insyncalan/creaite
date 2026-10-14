"""BL-196: formatted text, never raw markdown. A real browser against the real live server: release notes with a heading,
bold, a nested list, a link, code and HTML tags render in Settings › creaite version › Review release without raw markers
and without running a tag; the link opens safely; headings sit under the card's own; Copy copies the original text. The same
renderer (mdChat, BL-109) draws a run's confirmation text and a Markdown file's preview in Intake.

Run: python3 dev/tests/test_markdown_views.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

NOTES = """# creaite 9.9.9 (Beta)

A **bold** start with `inline code` and a [link](https://example.com/notes).

## New

- **First** thing
  - a nested point
- Second thing <img src=x onerror="window.RAN=1"> and <script>window.RAN=2</script>

Then, in order:

1. one
2. two

```
python3 system/scripts/update.py
```
"""

PLAN = {"ok": True, "plan": {"from": "1.5.1", "to": "9.9.9", "released": "2026-10-11", "notes": NOTES, "replaced": [], "added": [],
                             "removed": [], "left": [], "settings": {}}}


class MarkdownViews(LiveBrowserCase):
    shared_server = True
    width, height = 1400, 1000

    def release_notes(self):
        b = self.b
        b.eval("go('settings','version')")
        b.wait("!!document.getElementById('updCard') && /Installed|Needs the live server/.test(document.getElementById('updCard').textContent)", 15)
        b.pump(0.5)                                                         # the card has drawn itself (it is redrawn once)
        b.eval(f"""(()=>{{ window.RAN=0; const plan={json.dumps(PLAN)};
          if(!document.getElementById('updPlan')){{ const d=document.createElement('div'); d.id='updPlan'; document.getElementById('updCard').appendChild(d); }}
          const real=api; window.api=async (u,b)=>u==='/api/update/inspect'?plan:real(u,b); api=window.api;
          updReview('releases',false); }})()""")
        b.wait("!!document.querySelector('#updPlan .relnotes .mdv')", 10)
        b.pump(0.3)
        return b

    def test_release_notes_are_formatted_and_no_tag_runs(self):
        b = self.release_notes()
        r = b.eval("""(()=>{ const v=document.querySelector('#updPlan .relnotes .mdv'), a=v.querySelector('a');
          return {text:v.textContent, html:v.innerHTML, ran:window.RAN, imgs:v.querySelectorAll('img,script').length,
            heads:[...v.querySelectorAll('[role=heading]')].map(h=>[h.getAttribute('aria-level'),h.textContent]),
            strong:[...v.querySelectorAll('strong')].map(x=>x.textContent), code:[...v.querySelectorAll('code')].map(x=>x.textContent),
            nested:v.querySelectorAll('ul li ul li').length, ol:v.querySelectorAll('ol li').length,
            link:a&&[a.getAttribute('href'),a.getAttribute('rel'),a.getAttribute('target'),a.textContent],
            ws:getComputedStyle(v).whiteSpace}; })()""")
        for raw in ("**", "## ", "# creaite", "```", "](", "- **"):
            self.assertNotIn(raw, r["text"], raw)                           # no raw markers
        self.assertEqual(r["ran"], 0)                                       # the tags never ran…
        self.assertEqual(r["imgs"], 0)                                      # …and never became elements
        self.assertIn("<img src=x", r["text"])                              # they are shown as text
        self.assertEqual(r["heads"], [["3", "creaite 9.9.9 (Beta)"], ["4", "New"]])   # under the card's h2, in order
        self.assertIn("bold", r["strong"])
        self.assertIn("First", r["strong"])
        self.assertIn("inline code", r["code"])
        self.assertIn("python3 system/scripts/update.py", r["code"])
        self.assertEqual(r["nested"], 1)
        self.assertEqual(r["ol"], 2)
        self.assertEqual(r["link"], ["https://example.com/notes", "noopener", "_blank", "link"])
        self.assertEqual(r["ws"], "normal")

    def test_copy_copies_the_original_text(self):
        b = self.release_notes()
        b.eval("window.COPIED=null; navigator.clipboard.writeText=t=>{ window.COPIED=t; return Promise.resolve(); }")
        b.click("#updNotesCopy")
        b.pump(0.2)
        self.assertEqual(b.eval("window.COPIED"), NOTES)

    def test_readable_in_every_theme_light_and_dark(self):
        b = self.release_notes()
        from live_browser import theme_names
        for theme in theme_names()[:3]:
            for mode in ("light", "dark"):
                b.eval(f"document.documentElement.dataset.palette={json.dumps(theme)}; document.documentElement.dataset.theme='{mode}'")
                b.pump(0.1)
                ok = b.eval("""(()=>{ const v=document.querySelector('#updPlan .relnotes .mdv'), c=getComputedStyle(v);
                  return c.color!==c.backgroundColor && getComputedStyle(v.querySelector('a')).color!==c.backgroundColor; })()""")
                self.assertTrue(ok, (theme, mode))

    def test_a_confirmation_and_a_markdown_preview_are_formatted(self):
        b = self.b
        b.eval("openChat()")
        b.pump(0.3)
        b.eval("window.RAN=0; void confirmCard('Build it','Make **one** file in `drafts/` <b onmouseover=\"window.RAN=1\">x</b>','Go ahead',null,true)")
        b.pump(0.2)
        r = b.eval("""(()=>{ const c=[...document.querySelectorAll('#chLog .confirm')].pop();
          return {strong:c.querySelector('.mdv strong')?.textContent, code:c.querySelector('.mdv code')?.textContent, b:c.querySelectorAll('.mdv b').length,
                  text:c.textContent}; })()""")
        self.assertEqual(r["strong"], "one")
        self.assertEqual(r["code"], "drafts/")
        self.assertEqual(r["b"], 0)
        self.assertIn("<b onmouseover", r["text"])
        b.eval("""(()=>{ const real=api; api=async (u,bd)=>u==='/api/inbox/preview'?{ok:true,name:'note.md',text:'# Note\\n\\n- **one**\\n- two'}:real(u,bd);
          window.viaServer=()=>true; previewInbox('inbox/note.md'); })()""")
        b.wait("document.getElementById('inPrev').open", 5)
        r = b.eval("""({pre:document.getElementById('inPrevText').hidden, md:document.getElementById('inPrevMd').hidden,
          items:document.querySelectorAll('#inPrevMd li').length, head:document.querySelector('#inPrevMd [role=heading]')?.getAttribute('aria-level')})""")
        self.assertEqual(r, {"pre": True, "md": False, "items": 2, "head": "3"})
        b.eval("""(()=>{ api=async (u,bd)=>({ok:true,name:'t.vtt',text:'WEBVTT **not markdown**'}); previewInbox('inbox/t.vtt'); })()""")
        b.pump(0.3)
        self.assertEqual(b.eval("[document.getElementById('inPrevText').hidden, document.getElementById('inPrevText').textContent]"),
                         [False, "WEBVTT **not markdown**"])                # a transcript stays its own text


if __name__ == "__main__":
    unittest.main()
