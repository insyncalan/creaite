"""Build creaite's Word templates from Alan's approved sample minutes (house style).

Run: python3 dev/tools/build_templates.py [sample.docx]
(default sample: system/branding/SAMPLE MINUTES … .docx, which is kept out of git)

Writes system/templates/minutes-template.docx, weekly-report-template.docx, client-report-template.docx and
adhoc-template.docx (BL-75: the exemplar blocks `report.py adhoc` clones to build one-off documents: registers, lists).
Name templates after the sample to build only those: `build_templates.py [sample.docx] adhoc`.
The sample supplies the look: styles, bullet numbering, theme, the black wordmark, and the exact paragraph and table
formatting (Calibri body in Charcoal, section headings with a Signal Green rule, Charcoal table headers).
Everything client-specific is removed: the body text is replaced by placeholders, and the sensitivity-label
properties, label markings (RESTRICTED), web extensions and document properties are dropped. Labels are applied by
Word when Alan saves (decision 2026-10-05, option C); creaite never copies them.
"""
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# The first SAMPLE MINUTES file in the (git-ignored) branding folder; its own name is never written here.
SAMPLE = next(iter(sorted((ROOT / "system/branding").glob("SAMPLE MINUTES*.docx"))),
              ROOT / "system/branding/SAMPLE MINUTES.docx")
OUT = ROOT / "system/templates"
TABLE_WIDTH = 9350

DROP = re.compile(r"docProps/custom\.xml$|word/webextensions/")
W_NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def strip_ids(xml):
    return re.sub(r' w14:(paraId|textId)="[^"]*"| w:rsid\w*="[^"]*"', "", xml)


def set_text(para, text):
    """Put text in the paragraph's first text run and drop its other text runs."""
    runs = re.findall(r"<w:r>(?:(?!</w:r>).)*?<w:t(?: [^>]*)?>[^<]*</w:t>(?:(?!</w:r>).)*?</w:r>", para, re.S)
    first = runs[0]
    new_first = re.sub(r"<w:t(?: [^>]*)?>[^<]*</w:t>", f'<w:t xml:space="preserve">{text}</w:t>', first, count=1)
    para = para.replace(first, new_first, 1)
    for r in runs[1:]:
        para = para.replace(r, "", 1)
    return re.sub(r"<w:lastRenderedPageBreak/>", "", para)


class Parts:
    """The sample's building blocks."""

    def __init__(self, sample):
        with zipfile.ZipFile(sample) as z:
            self.parts = {i.filename: (i, z.read(i.filename)) for i in z.infolist()}
        doc = self.parts["word/document.xml"][1].decode("utf-8")
        self.head = doc[:doc.index("<w:body>") + len("<w:body>")]
        self.sect = re.findall(r"<w:sectPr.*?</w:sectPr>", doc, re.S)[-1]
        body = doc[doc.index("<w:body>") + len("<w:body>"):]
        blocks = [strip_ids(b) for b in re.findall(r"<w:p [^>]*>.*?</w:p>|<w:tbl>.*?</w:tbl>", body, re.S)]
        blocks = [re.sub(r"^<w:p [^>]*>", "<w:p>", b) for b in blocks]
        text = lambda b: "".join(re.findall(r"<w:t[^>]*>([^<]*)", b))  # noqa: E731
        find = lambda t: next(b for b in blocks if text(b) == t)  # noqa: E731
        starts = lambda t: next(b for b in blocks if text(b).startswith(t))  # noqa: E731
        self.wordmark = blocks[0]
        self.title, subtitle, self.when, self.attendees = blocks[1], blocks[2], blocks[3], blocks[4]
        self.heading = find("Executive Summary")
        self.para = starts("This was a joint")
        self.topic = find("Meeting Purpose &amp; Framing")
        self.bullet = starts("William opened by framing")
        self.table = next(b for b in blocks if b.startswith("<w:tbl>"))
        self.spacer = next(b for b in blocks if not re.search(r"<w:t[ >]", b) and "<w:drawing" not in b)
        self.subtitle = subtitle.replace('<w:spacing w:after="160"/>', '<w:spacing w:after="40"/>')
        self.status = subtitle.replace('w:val="24"', 'w:val="18"')
        self.source = self.status.replace("<w:i/><w:iCs/>", "").replace('w:val="18"', 'w:val="16"').replace(
            '<w:spacing w:after="160"/>', '<w:spacing w:before="320" w:after="0"/>')

    def h(self, text):
        return set_text(self.heading, text)

    def p(self, block, text):
        return set_text(getattr(self, block), text)

    def grid(self, columns):
        """A table in the sample's style: [(header, placeholder name, width share)], one data row of placeholders."""
        rows = re.findall(r"<w:tr>.*?</w:tr>", self.table, re.S)
        head_cell = re.search(r"<w:tc>.*?</w:tc>", rows[0], re.S).group()
        data_cell = re.search(r"<w:tc>.*?</w:tc>", rows[1], re.S).group()
        total = sum(c[2] for c in columns)
        widths = [round(TABLE_WIDTH * c[2] / total) for c in columns]

        def cell(template, width, text):
            c = re.sub(r'<w:tcW w:w="\d+"', f'<w:tcW w:w="{width}"', template, count=1)
            para = re.search(r"<w:p>.*?</w:p>", c, re.S).group()
            return c.replace(para, set_text(para, text), 1)

        def row(template_row, template_cell, texts):
            start = template_row[:template_row.index("<w:tc>")]
            return start + "".join(cell(template_cell, w, t) for w, t in zip(widths, texts)) + "</w:tr>"

        tbl_head = self.table[:self.table.index("<w:tblGrid>")]
        grid = "<w:tblGrid>" + "".join(f'<w:gridCol w:w="{w}"/>' for w in widths) + "</w:tblGrid>"
        return (tbl_head + grid + row(rows[0], head_cell, [c[0] for c in columns])
                + row(rows[1], data_cell, ["{{%s}}" % c[1] for c in columns]) + "</w:tbl>" + self.spacer)

    def write(self, out, body):
        doc = self.head + "".join(body) + self.sect + "</w:body></w:document>"
        blank_hdr = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:hdr {W_NS}><w:p/></w:hdr>'
        blank_ftr = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:ftr {W_NS}><w:p/></w:ftr>'
        title = re.sub(r"\{\{\w+\}\}", "", out.stem.replace("-template", "").replace("-", " ")).capitalize()
        core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<cp:coreProperties '
                'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
                'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
                f'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>{title}</dc:title>'
                '<dc:creator>creaite</dc:creator></cp:coreProperties>')
        result = []
        for name, (info, raw) in self.parts.items():
            if DROP.search(name):
                continue
            if name == "word/document.xml":
                raw = doc.encode("utf-8")
            elif re.match(r"word/header\d+\.xml$", name):
                raw = blank_hdr.encode("utf-8")
            elif re.match(r"word/footer\d+\.xml$", name):
                raw = blank_ftr.encode("utf-8")
            elif name == "docProps/core.xml":
                raw = core.encode("utf-8")
            elif name == "_rels/.rels":
                raw = re.sub(r'<Relationship [^>]*Target="(docProps/custom\.xml|word/webextensions/[^"]*)"[^>]*/>', "",
                             raw.decode("utf-8")).encode("utf-8")
            elif name == "[Content_Types].xml":
                raw = re.sub(r'<Override [^>]*PartName="/(docProps/custom\.xml|word/webextensions/[^"]*)"[^>]*/>', "",
                             raw.decode("utf-8")).encode("utf-8")
            result.append((info, raw))
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for info, raw in result:
                z.writestr(info, raw)
        print(f"Wrote {out.relative_to(ROOT)}")


def minutes(s):
    return [s.wordmark, s.p("title", "{{MEETING_TITLE}}"), s.p("subtitle", "Minutes of Meeting"),
            s.p("status", "{{STATUS_LINE}}"), s.p("when", "{{MEETING_WHEN}}"), s.p("attendees", "Attendees: {{ATTENDEES}}"),
            s.h("Executive Summary"), s.p("para", "{{SUMMARY}}"),
            s.h("Updates"), s.p("topic", "{{UPDATES_HEADING}}"), s.p("bullet", "{{UPDATES_ITEM}}"),
            s.h("Decisions"), s.p("bullet", "{{DECISIONS}}"),
            s.h("Risks, Issues, Assumptions &amp; Dependencies"), s.p("bullet", "{{RISKS_ISSUES}}"),
            s.h("Action Items"), s.grid([("Owner", "A_OWNER", 26), ("Task", "A_TEXT", 50), ("Deadline", "A_DUE", 17.5)]),
            s.h("Open Questions / Escalations"), s.p("bullet", "{{OPEN_QUESTIONS}}"),
            s.p("source", "Source: {{SOURCE}}")]


def weekly(s):
    return [s.wordmark, s.p("title", "{{PROJECT_NAME}}"), s.p("subtitle", "Weekly Report"),
            s.p("status", "{{STATUS_LINE}}"), s.p("when", "Week ending {{WEEK_ENDING}}"),
            s.p("attendees", "{{HEALTH_LINE}}"),
            s.h("Summary"), s.p("para", "{{SUMMARY}}"),
            s.h("Current State"), s.p("para", "{{CURRENT_STATE}}"), s.p("para", "{{IMAGES}}"),
            s.h("Progress This Week"), s.p("bullet", "{{PROGRESS}}"),
            s.h("Focus for Next Week"), s.p("bullet", "{{NEXT_WEEK}}"),
            s.h("Milestones"), s.grid([("Milestone", "M_TEXT", 34), ("Forecast", "M_DATE", 15), ("Baseline", "M_BASE", 15),
                                       ("% complete", "M_PCT", 12), ("Status", "M_STATUS", 18)]),
            s.h("Overdue Actions"), s.grid([("ID", "O_ID", 14), ("Action", "O_TEXT", 46), ("Owner", "O_OWNER", 24),
                                            ("Due", "O_DUE", 14)]),
            s.h("Top Risks and Issues"), s.grid([("ID", "R_ID", 12), ("Description", "R_TEXT", 52),
                                                 ("Priority", "R_PRIORITY", 12), ("Owner", "R_OWNER", 22)]),
            s.h("Decisions This Week"), s.p("bullet", "{{DECISIONS}}"),
            s.h("Help Needed"), s.p("bullet", "{{HELP_NEEDED}}"),
            s.p("source", "Source: {{SOURCE}}"),
            s.p("topic", "{{STYLE_TOPIC}}")]   # style sample for Current state sub-headings; removed when filled (BL-47)


def client(s):
    return [s.wordmark, s.p("title", "{{PROJECT_NAME}}"), s.p("subtitle", "Status Report"),
            s.p("status", "{{STATUS_LINE}}"), s.p("when", "{{CLIENT_NAME}} · {{PERIOD_START}} to {{PERIOD_END}}"),
            s.p("attendees", "{{HEALTH_LINE}}"),
            s.h("Summary"), s.p("para", "{{SUMMARY}}"),
            s.h("Progress"), s.p("bullet", "{{PROGRESS}}"),
            s.h("Milestones"), s.grid([("Milestone", "M_TEXT", 44), ("Date", "M_DATE", 18), ("% complete", "M_PCT", 12),
                                       ("Status", "M_STATUS", 20)]),
            s.h("Actions for {{CLIENT_NAME}}"), s.grid([("Action", "C_TEXT", 56), ("Owner", "C_OWNER", 24), ("Due", "C_DUE", 14)]),
            s.h("Our Commitments"), s.grid([("Commitment", "U_TEXT", 56), ("Owner", "U_OWNER", 24), ("Due", "U_DUE", 14)]),
            s.h("Decisions"), s.p("bullet", "{{DECISIONS}}"),
            s.h("Risks and Issues"), s.p("bullet", "{{CLIENT_RISKS}}"),
            s.h("Next Steps"), s.p("bullet", "{{NEXT_STEPS}}"),
            s.h("Input Needed"), s.p("bullet", "{{INPUT_NEEDED}}"),
            s.p("source", "{{REPORT_DATE}}")]


def adhoc(s):
    """One of each block a one-off document is made of (BL-75). `docx_tools.build_adhoc` clones them, so the table
    here has a single header cell and a single data cell; it makes as many columns and rows as the document needs."""
    return [s.wordmark, s.p("title", "{{TITLE}}"), s.p("subtitle", "{{SUBTITLE}}"), s.p("status", "{{STATUS_LINE}}"),
            s.p("when", "{{WHEN}}"), s.h("{{HEADING}}"), s.p("para", "{{PARA}}"), s.p("bullet", "{{BULLET}}"),
            s.grid([("{{HEAD}}", "CELL", 1)]), s.p("source", "{{SOURCE}}")]


def steerco(s):
    """The steering-committee one-pager (BL-92): status, what changed, milestones, top risks, decisions needed, blockers, flow and
    the next period. report.py leaves out a section that has nothing to say (it removes the heading and what follows it)."""
    return [s.wordmark, s.p("title", "{{PROJECT_NAME}}"), s.p("subtitle", "Steering Committee One-Pager"),
            s.p("status", "{{STATUS_LINE}}"), s.p("when", "{{STEERCO_WHEN}}"), s.p("attendees", "{{HEALTH_LINE}}"),
            s.h("Overall Status"), s.p("para", "{{STATUS_TEXT}}"),
            s.h("What Changed"), s.p("bullet", "{{CHANGES}}"),
            s.h("Milestones"), s.grid([("Milestone", "M_TEXT", 38), ("Forecast", "M_DATE", 16), ("Baseline", "M_BASE", 16),
                                       ("Status", "M_STATUS", 22)]),
            s.h("Top Risks and Issues"), s.grid([("ID", "R_ID", 12), ("Description and response", "R_TEXT", 56),
                                                 ("Priority", "R_PRIORITY", 12), ("Owner", "R_OWNER", 20)]),
            s.h("Decisions Needed"), s.p("bullet", "{{DECISIONS_NEEDED}}"),
            s.h("Blockers"), s.p("bullet", "{{BLOCKERS}}"),
            s.h("Flow"), s.p("para", "{{FLOW}}"),
            s.h("Next Period"), s.p("bullet", "{{NEXT_PERIOD}}"),
            s.p("source", "Source: {{SOURCE}}")]


BUILDERS = {"minutes": ("minutes-template.docx", minutes), "weekly": ("weekly-report-template.docx", weekly),
            "client": ("client-report-template.docx", client), "adhoc": ("adhoc-template.docx", adhoc),
            "steerco": ("steerco-template.docx", steerco)}


if __name__ == "__main__":
    args = sys.argv[1:]
    sample = Path(args.pop(0)) if args and args[0].endswith(".docx") else SAMPLE
    s = Parts(sample)
    for name in args or list(BUILDERS):
        file, build = BUILDERS[name]
        s.write(OUT / file, build(s))
