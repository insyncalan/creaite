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

Every other place that draws an address from mail, Teams or the register (the source line of an item, the VIP alert's "Open the
message", the To decide rows, the prep page's sources, Settings › People's mailto, and the copy from the page back to Markdown) asks
the same `linkUrl` (class CallSites), and a source-level guard (class NoBypass, no browser) fails when a new `href=` is built without
`linkUrl`, `linkAnchor` or `sourceHref` unless it is one of the fixed internal addresses listed in INTERNAL_HREFS.
"""
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

SRC = Path(__file__).resolve().parents[2] / "system" / "templates" / "dashboard" / "src"
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


HOSTILE = ["javascript:alert(1)", "JaVaScRiPt:alert(1)", "https://bank.example@evil.example/x", "https://user:pw@evil.example/", "data:text/html,x",
           "mailto:a@b.example,c@d.example", "//evil.example/x"]


class CallSites(LiveBrowserCase):
    """#159: the places other than the two Markdown renderers that draw an address, through the real functions."""
    shared_server = True
    width, height = 1400, 1000

    def anchors(self, js):
        """Run `js` (it must return an HTML string, a SafeHTML or a host element) and list its anchors' hrefs and rels."""
        return self.b.eval("""(()=>{ const r=(%s); const d=document.createElement("div");
          if(r&&r.nodeType) d.appendChild(r); else d.innerHTML=(r&&r.s!==undefined)?r.s:String(r);
          return {a:[...d.querySelectorAll("a")].map(a=>({href:a.getAttribute("href"),rel:a.getAttribute("rel"),text:a.textContent})), text:d.textContent}; })()""" % js)

    def good(self, js_for):
        """A good https and a good mailto address keep their link, new tab, with the shared rel."""
        for url in ("https://outlook.office.com/mail/id/abc?x=1&y=2", "https://teams.microsoft.com/l/message/19:abc@thread.v2/1"):
            with self.subTest(url=url):
                r = js_for(url)
                self.assertEqual([a["href"] for a in r["a"] if a["href"] != "#"], [url])
                self.assertEqual([a["rel"] for a in r["a"] if a["href"] == url], ["noopener noreferrer"])

    def none(self, js_for):
        for url in HOSTILE:
            with self.subTest(url=url):
                r = js_for(url)
                self.assertEqual([a["href"] for a in r["a"] if a["href"] not in ("#", None)], [], "a refused address was drawn as a link")

    # an item's source line (fields.js srcHTML): Email and Teams
    def test_the_source_line_of_an_email_or_teams_item(self):
        for typ, word in (("Email", "Open in Outlook"), ("Teams", "Open in Teams")):
            f = lambda url, typ=typ: self.anchors("srcHTML(%s)" % json.dumps(f"{typ} · From: Sam Example · Subject: Plan · Sent: 2026-10-01T09:00:00 · Link: {url}"))
            self.good(f)
            self.none(f)
            r = f("https://outlook.office.com/m/1")
            self.assertEqual(r["a"][0]["text"], word)
            self.assertIn("not a web address", f("javascript:alert(1)")["text"])

    def test_review_open_source_link(self):
        for url in HOSTILE:
            r = self.anchors("rvSrcLink({nodraft:false,src:%s})" % json.dumps(f"Email · From: A · Subject: S · Sent: 2026-10-01T09:00:00 · Link: {url}"))
            with self.subTest(url=url):
                self.assertEqual([a["href"] for a in r["a"]], [], "a refused address was drawn as a link")
        r = self.anchors("rvSrcLink({nodraft:false,src:%s})" % json.dumps("Email · From: A · Subject: S · Sent: 2026-10-01T09:00:00 · Link: https://outlook.office.com/m/1"))
        self.assertEqual([(a["href"], a["rel"]) for a in r["a"]], [("https://outlook.office.com/m/1", "noopener noreferrer")])

    # the VIP alert's "Open the message" (settings.js alertPeekDraw)
    def test_the_alert_peek_open_the_message(self):
        def f(url):
            return self.b.eval("""(()=>{ document.body.insertAdjacentHTML("beforeend",'<div id="pkScroll"></div>');
              CUR={mode:"new",k:"actions",draft:{},nid:1,alert:{id:"a1",kind:"mail",who:"Sam Example",sent:"",link:%s}};
              alertPeekDraw({},"actions"); const el=document.querySelector("#pkAlert .pk-alert-from");
              const r={a:[...el.querySelectorAll("a")].map(a=>({href:a.getAttribute("href"),rel:a.getAttribute("rel"),text:a.textContent})), text:el.textContent};
              document.querySelector("#pkAlert").remove(); document.querySelector("#pkScroll").remove(); CUR=null; return r; })()""" % json.dumps(url))
        self.good(f)
        self.none(f)

    # Settings › People: the register's mailbox
    def test_a_registers_mailbox_is_linked_only_when_it_is_one_mailbox(self):
        r = self.anchors('mailLink("sam@example.com")')
        self.assertEqual([(a["href"], a["rel"]) for a in r["a"]], [("mailto:sam@example.com", "noopener noreferrer")])
        for bad in ("a@b.example,c@d.example", "javascript:alert(1)", "x@y.example?bcc=z@evil.example", "<img src=x onerror=alert(1)>"):
            with self.subTest(bad=bad):
                r = self.anchors("mailLink(%s)" % json.dumps(bad))
                self.assertEqual(r["a"], [])
                self.assertEqual(r["text"], bad)                                   # shown as text, escaped

    # the copy from the page back to Markdown (panel.js htmlToMd)
    def test_pasted_html_links_go_through_the_validator(self):
        def md(href):
            return self.b.eval("""(()=>{ const d=document.createElement("div"); d.innerHTML='<p>see <a href="'+%s+'">here</a></p>'; return htmlToMd(d); })()""" % json.dumps(href))
        for url in HOSTILE:
            with self.subTest(url=url):
                self.assertNotIn("](", md(url))
        self.assertIn("[here](https://example.com/a?b=1&c=2)", md("https://example.com/a?b=1&c=2"))

    # To decide (components/today/ToDecide.jsx)
    def test_to_decide_message_rows(self):
        def f(url):
            return self.b.eval("""(()=>{ const host=document.createElement("div"); document.body.appendChild(host);
              drawToDecide(host,{rows:[{key:"al1",kind:"message",id:"1",tag:"Message",t:"Sam: Plan",link:%s,meta:"m",acts:[]}],total:0,cap:5,open:false,
                onAct(){},onOpen(){},onReview(){},blocked(){}});
              const r={a:[...host.querySelectorAll("a.t")].map(a=>({href:a.getAttribute("href"),rel:a.getAttribute("rel"),text:a.textContent})), text:host.textContent};
              host.remove(); return r; })()""" % json.dumps(url))
        self.good(f)
        self.none(f)
        self.assertEqual(f("javascript:alert(1)")["a"][0]["text"], "Sam: Plan")        # the row is still there, and opens as any row without an address

    # the prep page and its Shape panel (components/prep/*.jsx, stores/prepShape.js sourceHref). The components return Preact elements,
    # so the test reads the element's props (no render is needed); a source with no safe address comes back as plain text (a span).
    def test_prep_sources_agree(self):
        def one(fn, typ, url):
            r = self.b.eval("""(()=>{ const v=%s({s:{type:%s,url:%s,label:"Plan"}}); const p=v.props;
              return {a:v.type==="a"?[{href:p.href,rel:p.rel,target:p.target,text:p.children}]:[], type:v.type, text:String(p.children)}; })()"""
                            % (fn, json.dumps(typ), json.dumps(url)))
            return r
        for fn in ("SourceLink", "ShapeSource"):
            for typ in ("mail", "teams"):
                with self.subTest(fn=fn, typ=typ):
                    self.good(lambda url, fn=fn, typ=typ: one(fn, typ, url))
                    self.none(lambda url, fn=fn, typ=typ: one(fn, typ, url))
                    r = one(fn, typ, "javascript:alert(1)")
                    self.assertEqual((r["type"], r["text"]), ("span", "Plan"))        # the label stays, as text
        # an http address is allowed by the shared rule in both (ShapeSource used to take https only, SourceLink anything)
        for fn in ("SourceLink", "ShapeSource"):
            self.assertEqual(one(fn, "mail", "http://intranet.example/m")["a"][0]["href"], "http://intranet.example/m")


# Where an `href=` may be written without the validator on or just above its line: fixed addresses the page builds itself, never data from
# mail, Teams, a file or a person. (file ending, start of the text from `href=`, why). Short on purpose; add to it only with a reason here.
INTERNAL_HREFS = [
    ("", r'^href=\\?"#', 'the page\'s own in-page address: "#", "#cockpit=…" and the like; a click is handled by a data- attribute'),
    ("activity.js", r'^href="\$\{actHref\(', "actHref: a hash address built from a work item or milestone id"),
    ("core/server.js", r'^href="http://127\.0\.0\.1:\$\{S\.port\}/"', "the live server's own address, from its saved port"),
    ("meetings.js", r'^href="\$\{u\}"', "a blob: address the page made itself (URL.createObjectURL) for the prep page it just built"),
    ("ask.js", r'^href="\$\{href\}"', "runClosure: href is kept only if it matches /^#[\\w=%.|:&-]*$/ (a hash address), else it is empty and nothing is drawn"),
    ("ReportingSpace.jsx", r'^href=\{(?:wHref|cHref|href)\}', "a hash address from weeklyHref or clientReportHref (href is doOpen's parameter, given one of them)"),
    ("ReportingCard.jsx", r'^href=\{(?:weeklyHref|clientReportHref)\(', "a hash address from weeklyHref or clientReportHref"),
    ("LinkPopover.jsx", r'^href=\{open\} target="_blank" rel="noopener noreferrer">Open', "`open` is linkUrl(p.href), declared above the return"),
    ("ToDecide.jsx", r'^href=\{href\} target="_blank" rel=\{LINK_REL\}', "`href` is linkUrl(r.link), declared at the top of TdLine"),
]


class NoBypass(unittest.TestCase):
    """#159, source level (no browser): a new renderer must use linkUrl. Every `href=` in the dashboard's source is either one of the
    fixed internal addresses in INTERNAL_HREFS or sits on a line (or within the two before it) that names linkUrl, linkAnchor,
    sourceHref or mailLink. A new anchor that writes an address from mail, Teams, a file or a person fails here."""

    VALIDATED = re.compile(r"linkUrl|linkAnchor|sourceHref|mailLink")

    @staticmethod
    def offenders():
        found = []
        for p in sorted(SRC.rglob("*")):
            if p.suffix not in (".js", ".jsx") or p.name == "linkUrl.js":
                continue
            lines = p.read_text(encoding="utf-8").split("\n")
            for i, line in enumerate(lines):
                for m in re.finditer(r"href=[\"{\\\\]", line):
                    # inside a line comment or a block comment's prose: skip a line that is only a comment
                    if line.lstrip().startswith(("/*", "*", "//")):
                        continue
                    tail = line[m.start():]
                    if any(str(p.relative_to(SRC)).endswith(f) and re.match(pat, tail) for f, pat, _ in INTERNAL_HREFS):
                        continue
                    ctx = "\n".join(lines[max(0, i - 2):i + 1])
                    if NoBypass.VALIDATED.search(ctx):
                        continue
                    found.append(f"{p.relative_to(SRC)}:{i + 1}: {tail[:90]}")
        return found

    def test_no_href_is_written_without_the_validator(self):
        self.assertEqual(self.offenders(), [], "an href is built from data without core/linkUrl.js (use linkAnchor, linkUrl or sourceHref)")

    def test_the_allow_list_is_documented(self):
        for f, pat, why in INTERNAL_HREFS:
            self.assertTrue(why.strip(), pat)
            re.compile(pat)
            if f:
                self.assertTrue(list(SRC.rglob(Path(f).name)), f"{f}: no such file")


if __name__ == "__main__":
    unittest.main()
