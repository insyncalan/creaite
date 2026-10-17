"""#159: every renderer that draws a link goes through the ONE link validator and anchor builder (core/linkUrl.js).

Run: python3 dev/tests/test_link_renderers.py   (needs Google Chrome; skipped otherwise)

The two Markdown renderers (panel.js `mdInline`, which draws Current state, Help and notes, and ask.js `chatMdInline`, which draws
creaite's replies) used to keep their own https/mailto checks. Done when, in both:
- an address with a name and password in it (https://bank.example@evil.example) and a mailto: list or one with a cc/bcc are NOT links
  (the text stays visible as written);
- a link opens in a new tab with rel="noopener noreferrer", the same as every other link creaite draws;
- the emphasis pass (bold, italic, strike) never touches an anchor's attributes: an address with * or _ or ~~ in it keeps its
  href byte for byte;
- an address that came through the HTML-escaped text ("&" as "&amp;") is judged as the address it is, not as an entity.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

REFUSED = [
    "https://user:pw@evil.example/", "https://bank.example@evil.example/x", "http://a@b.example",
    "mailto:a@b.example,c@d.example", "mailto:a@b.example?bcc=x@evil.example", "mailto:a@b.example?cc=x@evil.example",
    "mailto:a%40evil.example%2Cb@good.example", "mailto:a@b.example;c@d.example",
    "javascript:alert(1)", "https://example.com/&#106;x", "https://example.com/&colon;x", "https://аpple.com/",
]
ALLOWED = {
    "https://example.com/a?b=1&c=2": "https://example.com/a?b=1&c=2",
    "mailto:a@b.example": "mailto:a@b.example",
    "mailto:a@b.example?subject=Hi&body=Hello": "mailto:a@b.example?subject=Hi&body=Hello",
    "HTTPS://Example.com/Path": "https://Example.com/Path",
}
# addresses the emphasis pass could reach into: * _ and ~~ inside the address
EMPHASIS = [
    "https://example.com/_a_/b", "https://example.com/x/_y_", "https://example.com/**b**", "https://example.com/*a*", "https://example.com/~~s~~",
    "https://example.com/a_b_c", "mailto:a@b.example?subject=_hi_",
]
ATTRS = ["href", "target", "rel"]


class LinkRenderers(LiveBrowserCase):
    shared_server = True
    width, height = 1400, 1000

    def rendered(self, fn, text):
        """The anchors a renderer draws for `text`: [{href, rel, target, attrs, text}] and the visible text."""
        return self.b.eval("""(()=>{ const d=document.createElement("div"); d.innerHTML=%s(%s);
          return {a:[...d.querySelectorAll("a")].map(a=>({href:a.getAttribute("href"),rel:a.getAttribute("rel"),target:a.getAttribute("target"),
            attrs:a.getAttributeNames(),html:a.innerHTML,text:a.textContent})), text:d.textContent, inner:d.querySelectorAll("b,i,s,strong,em,del,u").length}; })()"""
                           % (fn, json.dumps(text)))

    def both(self, text):
        return {"mdInline": self.rendered("mdInline", text), "mdChat": self.rendered("mdChat", text)}

    def test_userinfo_lists_and_hidden_receivers_are_not_links(self):
        for url in REFUSED:
            for fn, r in self.both(f"see [here]({url}) now").items():
                with self.subTest(fn=fn, url=url):
                    self.assertEqual(r["a"], [], "refused address drawn as a link")
                    self.assertIn("[here](", r["text"])                  # the text stays visible, as written

    def test_a_link_opens_in_a_new_tab_with_the_shared_rel(self):
        for url, href in ALLOWED.items():
            for fn, r in self.both(f"[site]({url})").items():
                with self.subTest(fn=fn, url=url):
                    self.assertEqual(len(r["a"]), 1)
                    a = r["a"][0]
                    self.assertEqual(a["href"], href)
                    self.assertEqual(a["rel"], "noopener noreferrer")
                    self.assertEqual(a["target"], "_blank")
                    self.assertEqual(a["attrs"], ATTRS)                  # nothing else, in the one builder's order
                    self.assertEqual(a["text"], "site")

    def test_the_emphasis_pass_never_changes_an_anchors_attributes(self):
        for url in EMPHASIS:
            for fn, r in self.both(f"a [the link]({url}) b").items():
                with self.subTest(fn=fn, url=url):
                    self.assertEqual(len(r["a"]), 1)
                    a = r["a"][0]
                    self.assertEqual(a["href"], url)                     # byte for byte
                    self.assertEqual(a["rel"], "noopener noreferrer")
                    self.assertEqual(a["attrs"], ATTRS)
                    self.assertEqual(r["inner"], 0)                      # no b, i or s was made out of the address

    def test_words_around_and_inside_a_link_are_still_emphasised(self):
        for fn in ("mdInline", "mdChat"):
            r = self.rendered(fn, "**bold** and [**strong** link](https://example.com/_a_) and *it*")
            with self.subTest(fn=fn):
                self.assertEqual(r["a"][0]["href"], "https://example.com/_a_")
                self.assertRegex(r["a"][0]["html"], r"^<(b|strong)>strong</(b|strong)> link$")
                self.assertEqual(r["inner"], 3)                           # bold before, strong in the link, italic after

    def test_a_marker_character_in_the_text_cannot_pull_in_another_link(self):
        r = self.rendered("mdInline", "[a](https://example.com/one) \u00010\u0001 \u00011\u0001")
        self.assertEqual([a["href"] for a in r["a"]], ["https://example.com/one"])

    def test_work_item_links_still_work_beside_web_links(self):
        r = self.b.eval("""(()=>{ const d=document.createElement("div"); d.innerHTML=mdInline("[ABC-A-001 · _x_](creaite:item/ABC-A-001) and [w](https://example.com/_q_)");
          return {oi:[...d.querySelectorAll("a.itemref")].map(a=>a.dataset.oi), href:[...d.querySelectorAll("a:not(.itemref)")].map(a=>a.getAttribute("href"))}; })()""")
        self.assertEqual(r, {"oi": ["ABC-A-001"], "href": ["https://example.com/_q_"]})

    def test_the_shared_builder_is_what_both_use(self):
        """linkAnchor and unescHtml are the one place an anchor is built."""
        r = self.b.eval("""({ok:linkAnchor("https://example.com/a?b=1&c=2","<b>x</b>"), bad:linkAnchor("https://u:p@evil.example/","x"),
          list:linkAnchor("mailto:a@b.example,c@d.example","x"), js:linkAnchor("javascript:alert(1)","x"),
          un:unescHtml("a&amp;b &lt;c&gt; &quot;d&quot; &amp;amp;"), esc:linkAnchor("https://example.com/?a=1&amp;b","x")})""")
        self.assertEqual(r["ok"], '<a href="https://example.com/a?b=1&amp;c=2" target="_blank" rel="noopener noreferrer"><b>x</b></a>')
        self.assertIsNone(r["bad"])
        self.assertIsNone(r["list"])
        self.assertIsNone(r["js"])
        self.assertEqual(r["un"], 'a&b <c> "d" &amp;')
        self.assertIsNone(r["esc"])                                       # an entity in a raw address is refused


if __name__ == "__main__":
    unittest.main()
