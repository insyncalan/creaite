"""Build dev/design-system/index.html: the creaite design system and the guide to building a new page.

Every number in the guide is read from the stylesheet snapshot (style.snapshot.css), measured on the real screens (specimens.json,
states-data.json, live-data.json, made by dev/tools/design_system_components.py) or taken from a named source file; nothing is typed in
by hand except the prose around it. Run after the snapshots are refreshed:  python3 dev/tools/design_system_guide.py
Development only."""
import json
import re
from pathlib import Path

DS = Path(__file__).resolve().parents[1] / "design-system"
css = (DS / "style.snapshot.css").read_text()
snap = json.loads((DS / "SNAPSHOT.json").read_text())
spec = json.loads((DS / "specimens.json").read_text())
live = json.loads((DS / "live-data.json").read_text())
states = json.loads((DS / "states-data.json").read_text())
inv = json.loads((DS / "inventory.json").read_text()) if (DS / "inventory.json").exists() else {}

esc = lambda s: str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def block(pat):
    i = css.index(pat)
    return css[i:css.index("}", i)]


def toks(b):
    return dict(re.findall(r"(--[a-z0-9-]+):\s*([^;]+);", b))


light = toks(block(':root[data-palette="creaite"]{'))
dark = toks(block(':root[data-palette="creaite"][data-theme="dark"]{'))
cursor_l = toks(block(':root[data-palette="Cursor"]{'))
cursor_d = toks(block(':root[data-palette="Cursor"][data-theme="dark"]{'))
scale = toks(css[css.index("/* ===== BL-325 scale"):css.index("/* ===== end BL-325 scale")])
motion = toks(block(":root{--k:1;"))
nocomment = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
rules = re.findall(r"([^{}]+)\{([^{}]*)\}", nocomment)


def used_by(t, n=4):
    sel = [s.strip().split(",")[0].strip()[:48] for s, b in rules if f"var({t})" in b and "data-palette" not in s and not s.strip().startswith("@")]
    return len(sel), sel[:n]


def lum(hexc):
    h = hexc.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def S(key):
    d = spec.get(key, {}).get("d")
    return d["html"] if d else '<span class="sub">not visible in the snapshots</span>'


def M(key):
    d = spec.get(key, {}).get("d")
    if not d:
        return ""
    return f'{d["w"]} × {d["h"]} px · text {d["fs"]}/{d["fw"]} · radius {d["br"]} · padding {d["pad"]}'


def both(name, alt):
    return (f'<img class="only-light" src="components/{name}-light.png" alt="{esc(alt)}" loading="lazy">'
            f'<img class="only-dark" src="components/{name}-dark.png" alt="{esc(alt)} (dark)" loading="lazy">')


def state_strip(key, order, label=""):
    ok = states.get(key, {}).get("light")
    if not isinstance(ok, list):
        return ""
    cells = []
    for st in order:
        if st not in ok:
            continue
        cells.append(f'<figure class="ds-st"><span class="ds-pic"><img class="only-light" src="components/state-{key}-{st}-light.png" alt="{esc(key)} {st}">'
                     f'<img class="only-dark" src="components/state-{key}-{st}-dark.png" alt="{esc(key)} {st} (dark)"></span><figcaption>{st}</figcaption></figure>')
    return f'<div class="ds-states" aria-label="States of {esc(label or key)}">{"".join(cells)}</div>'


def cell(label, html):
    return f'<figure class="ds-cell">{html}<figcaption>{esc(label)}</figcaption></figure>'


def comp(cid, title, cls, use, stage, measure="", extra="", dont="", strip=""):
    code = f'<details class="ds-code"><summary>Markup (real, to copy)</summary><button type="button" class="ds-copy">Copy</button><pre>{esc(re.sub(r"> <", ">\n<", stage))}</pre></details>' if 'not visible' not in stage and '<' in stage else ''
    return f'''<article class="ds-comp" id="c-{cid}"><header><h3>{esc(title)}</h3><code>{esc(cls)}</code></header>
<p class="ds-use">{use}</p><div class="ds-stage">{stage}</div>{code}{strip}{('<p class="ds-meas">Measured: ' + esc(measure) + '</p>') if measure else ''}{extra}{('<p class="ds-dont"><b>Not for:</b> ' + dont + '</p>') if dont else ''}</article>'''


# ------------------------------------------------------------------ foundations
colour_roles = {
    "--bg": "the page behind everything",
    "--surface": "cards, the rail, the top bar, dialogs, inputs: anything that sits on the page",
    "--sunk": "wells and hover fills: a row you point at, a track, a quiet area inside a card",
    "--ink": "primary text and strong icons",
    "--muted": "secondary text: sub-lines, labels, hints",
    "--faint": "tertiary text, placeholders, disabled hints (kept readable: see contrast)",
    "--line": "every ordinary border and divider",
    "--line-strong": "the rare stronger border (four rules only)",
    "--accent": "the one brand colour: primary buttons, links, the current page, focus",
    "--accent-ink": "text on an accent fill",
    "--accent-soft": "a tinted background: selected row, current page, a soft chip",
    "--bad": "off track, overdue, errors, destructive",
    "--bad-soft": "background for a bad state",
    "--warn": "at risk, due soon, needs attention",
    "--warn-soft": "background for a warn state",
    "--ok": "on track, done, success",
    "--ok-soft": "background for an ok state",
    "--focus": "the focus ring",
    "--inverse": "tooltips and toasts: dark in light mode, light in dark mode",
    "--inverse-ink": "text on --inverse",
}
sw = []
for t, role in colour_roles.items():
    n, ex = used_by(t)
    lh, dk = light.get(t, "?"), dark.get(t, "?")
    sw.append(f'<div class="ds-sw"><i style="background:var({t})"></i><b>{t}</b><span class="ds-hex"><span class="only-light">{lh}</span><span class="only-dark">{dk}</span></span>'
              f'<em>{role}</em><small>{n} rules use it, for example {esc(", ".join(ex[:3]))}</small></div>')
pairs = [("--ink", "--surface"), ("--muted", "--surface"), ("--faint", "--surface"), ("--accent", "--surface"), ("--accent-ink", "--accent"),
         ("--bad", "--surface"), ("--warn", "--surface"), ("--ok", "--surface"), ("--ink", "--bg"), ("--muted", "--bg"), ("--faint", "--bg"), ("--muted", "--sunk")]
crow = "".join(f'<tr><td><code>{a}</code> on <code>{b}</code></td><td>{contrast(light[a], light[b]):.2f}:1</td><td>{contrast(dark[a], dark[b]):.2f}:1</td>'
               f'<td>{"AA" if min(contrast(light[a], light[b]), contrast(dark[a], dark[b])) >= 4.5 else "large text only" if min(contrast(light[a], light[b]), contrast(dark[a], dark[b])) >= 3 else "below AA"}</td></tr>' for a, b in pairs)

fs_rows = "".join(f'<div class="ds-ty"><span style="font-size:{v}">Aa Quick brown fox</span><code>{k} · {v}</code></div>' for k, v in scale.items() if k.startswith("--fs-"))
pal_rows = "".join(f'<tr><td><code>{t}</code></td>' + ''.join(f'<td><span class="ds-chipc" style="background:{d.get(t, "")}"></span> {d.get(t, "-")}</td>' for d in (light, dark, cursor_l, cursor_d)) + '</tr>' for t in ("--bg", "--surface", "--sunk", "--ink", "--muted", "--line", "--accent", "--accent-soft", "--bad", "--warn", "--ok"))
sp = "".join(f'<div class="ds-sp"><i style="width:{n}px;height:{n}px"></i><code>{n}</code></div>' for n in (2, 4, 6, 8, 10, 12, 14, 16, 20, 24, 28, 32, 40, 48, 56, 64))
rad = "".join(f'<div class="ds-rad"><i style="border-radius:var({k})"></i><code>{k} · {scale[k]}</code></div>' for k in ("--r-sm", "--r-md", "--r-lg", "--r-xl", "--r-pill"))
shd = "".join(f'<div class="ds-shd"><i style="box-shadow:var({k})"></i><code>{k}</code></div>' for k in ("--shadow-sm", "--shadow-md", "--shadow-lg"))
zs = ", ".join(f"<code>{k}</code> {v}" for k, v in scale.items() if k.startswith("--z-"))
icons = "".join(f'<button class="ds-ic" type="button" data-name="{esc(n)}" title="Copy the name">{svg}<span>{esc(n)}</span></button>' for n, svg in live["icons"])
mot = "".join(f"<tr><td><code>{k}</code></td><td>{esc(v)}</td></tr>" for k, v in motion.items() if k != "--k")

# ------------------------------------------------------------------ patterns
def outline_lines(node, depth=0, out=None, limit=48):
    out = [] if out is None else out
    if len(out) >= limit or not isinstance(node, dict):
        return out
    t = node.get("t", "")
    x = f" ×{node['x']}" if node.get("x") else ""
    out.append("  " * depth + t + x)
    for c in node.get("c", []) or []:
        outline_lines(c, depth + 1, out, limit)
    return out


def variants(page):
    out = ''
    if (DS / 'shots' / f'{page}-900-light.png').exists():
        out += f'<details><summary>At 900 px wide</summary><img src="shots/{page}-900-light.png" alt="{page} at 900 px" loading="lazy" style="max-width:100%;border:1px solid var(--line);border-radius:var(--r-md)"></details>'
    if (DS / 'shots' / f'{page}-cursor-light.png').exists():
        out += f'<details><summary>In the Cursor palette</summary><img class="only-light" src="shots/{page}-cursor-light.png" alt="{page} in Cursor" loading="lazy" style="max-width:100%;border:1px solid var(--line);border-radius:var(--r-md)"><img class="only-dark" src="shots/{page}-cursor-dark.png" alt="{page} in Cursor, dark" loading="lazy" style="max-width:100%;border:1px solid var(--line);border-radius:var(--r-md)"></details>'
    return out


def pattern(pid, title, view, use, parts, rules_, page, outline_key=None):
    ol = live["outlines"].get(outline_key or "")
    skel = esc("\n".join(outline_lines(ol))) if ol else ""
    return f'''<article class="ds-pat" id="p-{pid}"><header><h3>{esc(title)}</h3><a href="pages/{page}.html" target="_blank">open the real screen</a></header>
<div class="ds-pat-grid"><div class="ds-shot">{both_shot(page)}</div><div class="ds-pat-text"><p class="ds-use">{use}</p>
<h4>Composition, top to bottom</h4><ol>{"".join(f"<li>{p}</li>" for p in parts)}</ol><h4>Rules</h4><ul>{"".join(f"<li>{r}</li>" for r in rules_)}</ul>
{('<details><summary>Skeleton from the running app (tag, id, classes)</summary><pre>' + skel + '</pre></details>') if skel else ''}{variants(page if page not in ('cockpit',) else '')}</div></div></article>'''


def both_shot(name):
    return (f'<img class="only-light" src="shots/{name}-light.png" alt="{name} screen, light" loading="lazy">'
            f'<img class="only-dark" src="shots/{name}-dark.png" alt="{name} screen, dark" loading="lazy">')


PAT = [
    pattern("list", "List page: a heading, controls, a table card", "files",
            "Any page that is a list of things you search, filter and open: Files, People, Activity, Projects.",
            ["<code>h1</code> (display 22/800), no breadcrumb.", "Optional <code>.sub</code> line (13 px, muted).",
             "A control row (<code>.toolbar</code>, 32 px): search input, selects, date fields, a count and Refresh at the right.",
             "View pills (<code>.vchip</code>, 28 px) when the list has named views.", "The table in a <code>.tbl</code> card: mono uppercase headers, 14 px rows."],
            ["Content sits in <code>.wrapmax</code> (max 1500 px) inside the page's 20 × 24 px padding.", "Counts and Refresh go to the right of the same row, never on a row of their own.",
             "A row's one main action is its link; row tools are icon buttons at the end.", "Empty: say the next step, in a <code>.empty</code> box inside the card."],
            "files", "files"),
    pattern("tabbed", "Tabbed list with filters (Work)", "work",
            "A list that has kinds (Actions, RAID, Decisions) and many ways to narrow it.",
            ["<code>h1</code>.", "<code>.tabs</code> for the kinds (38 px, an underline marks the selected one).",
             "The filter row: search, filter buttons (<code>.btn.fbtn</code>), the funnel (<code>.ib.bd</code> with its count) and view and layout icon buttons at the right.",
             "View pills (All open, Mine, Due soon …).", "Applied filters as removable chips with Clear all and the count (\"Showing 3 of 3\").", "The <code>.tbl</code> card."],
            ["The funnel icon button is how any list adds a filter: it carries the number of filters on.", "Applied filters are always visible and removable one at a time.",
             "Selected view pill = ink fill; the others are outlined."],
            "work", "work"),
    pattern("queue", "Triage queue (Review)", "review",
            "A queue where each row needs one decision: approve, change, reject.",
            ["<code>h1</code> and a sub-line with the counts.", "Controls: search, toggles (One at a time, Kind, Needs, Source), funnel, display, the one bulk action at the right.",
             "Groups, each with a group check box, a name and a count.", "Rows in a card: check box, the thing, its facts in muted lines, per-row actions (project, edit, Approve, reject, expand)."],
            ["Per-row actions are always the same set and in the same order.", "The bulk action is named for exactly what it covers.", "Facts that need attention are coloured (<code>--warn</code>), never bold."],
            "review", "review"),
    pattern("brief", "Today: the brief", "today",
            "A page that reads like a briefing: what to know now, in short numbered sentences.",
            ["A tinted day band (<code>--day-band</code>): mono date line, display greeting, one sentence of what matters, calendar controls.",
             "Numbered sections (Getting started, Needs attention, Your commitments, …): a display <code>h2</code> with a count, then rows.",
             "Each row: number, one sentence, tools at the right (icon button and the ⋯ menu)."],
            ["Content is a centred column, not the full width.", "One sentence per row; the tools sit at the right and stay quiet until pointed at."],
            "today", "today"),
    pattern("detail", "Detail page: breadcrumb, tabs, a grid of cards (Project)", "cockpit",
            "One thing seen from several sides: a project, a person, a report space.",
            ["Breadcrumb (<code>.crumb</code>), <code>h1</code>, a sub-line, a picker to jump to a neighbour at the right.", "Tabs (Overview, Notes).",
             "A grid of <code>.card</code>s (14 px padding, 12 px radius): the wide one first, then pairs.", "Each card: a display <code>h2</code>, its content, a quiet edit icon at the bottom right."],
            ["Cards stack with a 16 px gap; never nest a card in a card.", "Health uses the health label (icon + word + colour), not colour alone."],
            "cockpit", "projects"),
    pattern("settings", "Settings: a side list and grouped rows", "settings",
            "Many small independent choices.",
            ["<code>h1</code>.", "A left column: a search box and a list of groups (Essentials, People and projects, Advanced, Health).",
             "Group cards: a display title, then rows."],
            ["A row is a label and one line of help at the left, the control at the right (<code>.srow</code>, 56 px).", "Every row says what it changes and what its default is; a dot marks one that you changed, with Reset.",
             "Controls are the standard ones: check boxes, switches, selects, time and text inputs."],
            "settings", "settings"),
    pattern("doc", "Document page: a sheet on a tinted canvas (Weekly report)", "weekly",
            "A page you write, approve and export, shown as the paper it will become.",
            ["Breadcrumb, <code>h1</code>, a sub-line.", "A bar: zoom, Show as exported at the left; Export and the one primary action (Approve and file) at the right.",
             "The A4 sheet on a grey canvas, zoomable 40–80%."],
            ["The sheet is the page's own paper: its fonts and colours are the report's, not the app's.", "Exactly one primary button in the bar."],
            "weekly", "projects"),
    pattern("two-pane", "Two panes: a list and a reader (Notes)", "notes",
            "Content you browse on the left and read or edit on the right.",
            ["Breadcrumb, <code>h1</code>, a sub-line and a + button at the right.", "Tabs.", "Left: a labelled list with a search box and a collapse chevron. Right: a card with the content, or an empty state that says what the thing is for."],
            ["The empty state explains the thing in one sentence, then shows what to do.", "The collapse control keeps its place."],
            "notes", "notes"),
    pattern("docs", "Documentation: tabs over a long page (Help)", "help",
            "Reading, not working: guides and references.",
            ["Tabs at the top (Start here, How do I…, Reference).", "A hero: mono label, large display title, a short paragraph.", "Cards, each one idea, with the one gate highlighted in <code>--warn-soft</code>."],
            ["Page-specific styles (Help has its own palette) stay inside the page.", "Short sentences; one idea per card."],
            "help", "help"),
    pattern("cards-sections", "Sections of cards (Intake)", "intake",
            "A page of separate jobs, each a card with its own action.",
            ["<code>h1</code> and a sub-line.", "A card per job (Calendar import, Upload files, Quick capture), each with a display title, its controls and its table.", "Empty states inside the card."],
            ["One primary button per card at most.", "Controls repeat only if they do different things."],
            "intake", "projects"),
]
PAT.append(pattern("prep", "Prep: three columns around one meeting", "prep",
            "A working page for one thing you are about to do: a meeting.",
            ["Breadcrumb, <code>h1</code>, a row of chips (kind, date and time, project, health, series position).", "Actions at the left (Refresh research, Draft agenda); the save note and Print at the right.",
             "Tabs (Prep, Invite, History).", "Three columns: an outline list at the left; the editors in the middle (mono labels, a ✦ Shape control, then \"In play\" rows with a Raise / Note / Skip switch); cards at the right (When and who, Latest reporting, This series)."],
            ["The outline lists exactly what is on the page, in order.", "Editors save as you type and say so (\"Saved as you type\").", "Facts about other things come as cards at the side, never inline."],
            "prep"))
PAT.append(pattern("client-doc", "Document page, client version (Client report)", "clientreport",
            "The same sheet pattern as the weekly report, seen as the client sees it.",
            ["The same bar and sheet as the weekly report.", "Only client-visible items, in the client's words; what is left out is listed, with the reason, before any export."],
            ["Never anything marked Sensitive or partner-only.", "The one primary action is still alone in the bar."],
            "clientreport"))
PAT.append(pattern("minutes", "Document page with a side panel (Minutes)", "minutes",
            "The Document pattern when the sheet needs its source beside it.",
            ["Breadcrumb, <code>h1</code>, a sub-line (project, date, status).", "A bar: zoom and Show as exported, an open-checks chip; then version, view switch, Transcript, Export and the one primary (Approve minutes).",
             "The sheet on its canvas; at the right a Transcript panel with its own search and the turns, each with a time tag that scrolls the transcript."],
            ["Time tags sit on the sheet's lines and link to the panel; the panel closes with its ✕.", "A toast says what happened at the foot (\"7 new items in Review\")."],
            "minutes"))
PAT.append(pattern("reports", "Roll-up table across projects (Reports)", "reports",
            "One row per project for a recurring job, with the state of each and an Open button.",
            ["Breadcrumb, <code>h1</code>, a sub-line, and a week stepper at the right (a pair of ink-selected buttons).", "A tinted note that says what needs doing, with a two-way switch (Needs me | All projects).",
             "A <code>.tbl</code> of projects: health, internal state as a chip, client state as a chip, and Open (primary on the row that needs you)."],
            ["State is a chip (Due, Not drafted, Filed), never colour alone.", "The note under the table says what Open does."],
            "reports"))
PAT.append(pattern("reporting", "A space for one thing over time (Reporting)", "reporting",
            "Everything about one project's reporting: a list of weeks and the two reports for the chosen week.",
            ["Breadcrumb, <code>h1</code>, a sub-line.", "Left: a stack of week cards (the chosen one outlined), each with its state chips.", "Right: two cards (Weekly report, Client report) each with a preview, two facts and its actions; then a tinted call-to-action strip; then a card for what was filed."],
            ["Only the next sensible action is primary; the rest are plain; a blocked one says why (\"Approve the internal report first\").", "A dashed tinted strip offers the combined action."],
            "reporting"))
PAT.append(pattern("person", "Detail page: a person (People)", "person",
            "Everything a person has with you: their work, what closed lately, decisions they made.",
            ["Breadcrumb, <code>h1</code>, a sub-line; actions at the right (Draft email, Hand over, an edit icon).", "A one-line summary of figures (open actions, open risks and issues, overdue, projects).",
             "Cards, each with a display title and a count: Open work (with its own <code>.tbl</code>), Closed in the last 14 days, Decisions made."],
            ["An empty card says so in one plain line (\"Nothing closed lately.\").", "Counts are in the title, not in a badge."],
            "person"))
PAT.append(pattern("milestones", "A single-purpose view with a switch (Milestones)", "milestones",
            "One visual thing with two ways of looking at it (Plan | Movement) and an Internal | Client view.",
            ["Breadcrumb, <code>h1</code>, a project picker and the one primary (Add milestone) at the right.", "Two <code>.seg</code> switches.", "A card holding the plan: a month strip with Today marked."],
            ["The client view is the plain card: no pills or notes.", "The Add button is the only primary."],
            "milestones"))
PAT = [p for p in PAT]

# ------------------------------------------------------------------ components
C = []
C.append(comp("type", "Headings and text", "h1 · h2 · h3 · .sub",
              "h1 titles a page; h2 titles a card or a section; h3 titles a block inside one; <code>.sub</code> is the muted line beneath a title.",
              f'<div class="ds-col">{S("h1")}{S("sub")}{S("h2")}{S("h3")}</div>',
              "h1 " + M("h1") + " · .sub " + M("sub"),
              dont="a heading made by hand from bold text."))
C.append(comp("btn", "Button", ".btn  (.primary, .quiet)",
              "<b>.btn</b> is the standard action. <b>.btn.primary</b> is the one main action in a region (an accent fill; Approve, Add, Run). <b>.btn.quiet</b> is a text-style action with no border (accent text, soft fill on hover).",
              '<div class="ds-row">' + cell(".btn", S("btn")) + cell(".btn.primary", S("btn-primary")) + cell(".btn.quiet", S("btn").replace('class="btn"', 'class="btn quiet"')) + '</div>',
              "button " + M("btn") + " · primary " + M("btn-primary"),
              dont="two primaries side by side, or a primary for something that is not the main thing here.",
              strip=state_strip("btn", ["default", "hover", "focus", "active", "disabled"], "button") + state_strip("btn-primary", ["default", "hover", "focus", "active", "disabled"], "primary button") + state_strip("btn-quiet", ["default", "hover", "focus", "active"], "quiet button")))
C.append(comp("mini", "Mini button", ".mini", "A compact action inside a dense row (Draft, Project, Details).",
              f'<div class="ds-row">{S("mini")}</div>', M("mini"), strip=state_strip("mini", ["default", "hover", "focus", "active", "disabled"], "mini")))
C.append(comp("ib", "Icon button", ".ib  (.sm, .bd)", "A button that is only an icon. Always has an <code>aria-label</code> and a <code>data-tip</code> tooltip. <code>.sm</code> only makes the icon 16 px; <code>.bd</code> draws a border (use it in a control row, like the funnel).",
              f'<div class="ds-row">{cell(".ib.sm", S("ib-sm"))}{cell(".ib.bd (funnel)", S("ib-bd"))}{cell(".iconbtn", S("iconbtn"))}</div>', M("ib-sm"),
              dont="an unlabelled icon, or an icon whose meaning is not obvious without its tooltip in a place people use once.",
              strip=state_strip("ib", ["default", "hover", "focus", "active"], "icon button") + state_strip("ib-bd", ["default", "hover", "focus", "active"], "bordered icon button")))
C.append(comp("seg", "Segmented control", ".seg", "Two to four mutually exclusive options that change how the same content is shown (List | Board).",
              f'<div class="ds-row">{S("seg")}</div>', M("seg")))
C.append(comp("vchip", "View pill", ".vchip", "A named view or a quick filter. One group has exactly one selected; <code>aria-pressed=\"true\"</code> fills it with ink.",
              f'<div class="ds-row">{S("vchip")}</div>', "pill 28 px high · text 13 px · radius 12",
              strip=state_strip("vchip", ["default", "hover", "focus", "active"], "pill") + state_strip("vchip-on", ["default", "hover", "focus"], "selected pill")))
C.append(comp("tags", "Tag, chip, count, file type, key hint", ".tag · .chip · .fchip · .badge · .ftype · kbd",
              "Small labels. <code>.tag</code> is plain muted text by default (a status word); <code>.chip</code> is a small pill; <code>.fchip</code> is a removable filter; <code>.badge</code> is the rail's count only (it only draws inside the side bar: see the side-bar item below); <code>.ftype</code> marks a file kind; <code>kbd</code> shows a key.",
              f'<div class="ds-row">{cell(".tag", S("tag"))}{cell(".chip", S("chip"))}{cell(".fchip", S("fchip"))}{cell(".ftype", S("ftype"))}{cell("kbd", S("kbd"))}</div>',
              "tag " + M("tag") + " · chip " + M("chip") + " · fchip " + M("fchip"),
              dont="a count badge anywhere but the rail (use the count in text)."))
C.append(comp("health", "Health", ".health", "The state of a project: icon, word and colour together (On track, At risk, Off track). Never colour alone.",
              f'<div class="ds-row">{S("health")}</div>', M("health")))
C.append(comp("input", "Text input and select", "input · select", "Standard fields are 32 px high with an 8 px radius and 13 px text.",
              f'<div class="ds-row">{cell("input", S("input"))}{cell("select", S("select"))}</div>', "input " + M("input") + " · select " + M("select"),
              extra='<p class="ds-meas">Other field heights exist by context: the top-bar search is 36 px, the vault search 40 px, a date field inside a dense row 28 px.</p>',
              strip=state_strip("input", ["default", "hover", "focus", "disabled"], "input") + state_strip("select", ["default", "hover", "focus", "disabled"], "select")))
C.append(comp("date-error", "Field error", ".dwrap + its message", "A mistake in a typed date is shown at the field, in the error colour, with the format it expects; nothing is saved from it.",
              '<div class="ds-shotbox">' + both("date-invalid", "a date field with a typed mistake") + '</div>', "message in --bad; the field keeps what you typed"))
C.append(comp("date", "Date field", ".dwrap  + the popup calendar", "Every date is a text field in DD-MM-YYYY with a calendar button; the button opens the popup calendar (below). Dates can also be typed in words in some fields.",
              f'<div class="ds-row">{S("dwrap")}</div>', M("dwrap")))
C.append(comp("check", "Check box, switch, setting row", "input[type=checkbox] · .switch · .srow", "A check box is one of several; a switch is on or off right now. A setting row puts its label and one line of help at the left, its control at the right.",
              f'<div class="ds-col">{S("srow")}</div>', "switch " + M("switch") + " · row " + M("srow"),
              strip=state_strip("check", ["default", "hover", "focus", "checked", "disabled"], "check box") + state_strip("switch", ["default", "hover", "focus", "checked", "disabled"], "switch")))
C.append(comp("tabs", "Tabs", ".tabs", "Different content of the same kind on one page. The selected tab has an accent underline.",
              f'<div class="ds-col">{S("tabs")}</div>', M("tabs"), strip=state_strip("tab", ["default", "hover", "focus"], "tab") + state_strip("tab-on", ["default", "hover", "focus"], "selected tab")))
C.append(comp("tree", "Folder list", "#tree  (button.l1 · .l2 · .l3)", "A hierarchy you pick one place in, with counts at the right.",
              f'<div class="ds-col" style="max-width:300px">{S("tree")}</div>', M("tree"), strip=state_strip("tree-row", ["default", "hover", "focus"], "folder row")))
C.append(comp("tbl", "Table", ".tbl", "A card with a 12 px radius holding a table: mono, uppercase, letter-spaced headers; 14 px body; rows 49–59 px depending on content.",
              f'<div class="ds-col">{S("tbl")}</div>', M("tbl"), strip=state_strip("table-row", ["default", "hover"], "table row") + state_strip("link", ["default", "hover", "focus"], "link")))
C.append(comp("card", "Card", ".card", "A group of related content on the page: 12 px radius, 14 px padding, a 16 px gap below.",
              f'<div class="ds-col">{S("card")}</div>', M("card"), dont="a card inside a card."))
C.append(comp("empty", "Empty state", ".empty", "Says what is missing and the next step, in plain words.", f'<div class="ds-col">{S("empty")}</div>', M("empty")))
C.append(comp("rail", "Side bar item", ".rail .nv", "One page in the side bar: icon, label, optional count. The current page is a tonal pill with an accent bar.",
              '<p class="sub">Shown as it is in the app below (states).</p>', "item 36 px high · text 13/500 · radius 8",
              strip=state_strip("rail-item", ["default", "hover", "focus"], "rail item") + state_strip("rail-item-current", ["default", "hover"], "current page")))

# dynamic components (live screenshots)
D = []
D.append(("menu-list", "Dropdown menu", ".ddmenu", "A list of choices under the control that opened it. Closes on Esc, a pick or a click outside."))
D.append(("menu-filter", "Filter panel", ".ddmenu.fpmenu", "A larger menu for adding a filter: pick a field, then a value. Opened by the funnel."))
D.append(("calendar-popup", "Popup calendar", ".cal", "A month grid under a date field: today ringed, weekends marked, arrows for months."))
D.append(("toast", "Toast", "#snack  (.mtimer)", "Says what just happened, with Undo when it can be undone. Stays 10 seconds with Undo (5 otherwise) and waits while you point at it."))
D.append(("peek-panel", "Peek", "#panel.peek", "An item opens over the right half of the page, editable in place. ⌘↵ saves and closes; Esc closes."))
D.append(("dialog-customise-sidebar", "Dialog (Customise sidebar)", "dialog", "A centred card on a scrim for a short, self-contained job. Cancel and the one main action at the foot; Reset at the left when it applies."))
D.append(("command-palette", "Command palette", "#cmdk", "⌘K: search, jump, and run commands."))
D.append(("ask-panel", "ask creaite panel", "#chat", "The assistant opens over the page on the right and never squeezes it. Esc closes the panel but never stops a running request; only Stop stops it."))
D.append(("ask-running", "ask creaite while it works", "#chat", "A request in progress: the question, a folded step line (\"1 step\"), and a typing indicator while the answer arrives. Stop appears while it runs; Esc closes the panel but never stops the request."))
D.append(("ai-suggestion", "AI suggestion card", ".sheet-redraft", "A ✦ draft under the section it is for: the sparkle and a title, the suggested text, amber warnings from the check (what it leaves out, what it adds, what has no source), the source facts as outlined boxes, then Keep mine and Use this. Nothing changes until Use this. (The words in this picture come from the test stand-in, not a real model.)"))
D.append(("error-banner", "Error banner", ".errbanner", "Under the other page banners: how many errors, what kind, Investigate (opens Settings › Diagnostics), ask creaite to look, and a ✕ that dismisses it until a newer error. Shown only for an error not yet seen."))
D.append(("live-alert", "Live-server alert", "#liveAlert.on", "Shown at the top of every page when the live server is not running: what is held, and how to restart it."))
D.append(("dialog-board", "Dialog (small)", "dialog", "A short question with its answer buttons."))
D.append(("dialog-generate", "Dialog (large)", "dialog", "A larger job with settings and a result (Generate current state)."))
D.append(("dialog-person", "Dialog (form)", "dialog", "A form in a dialog: fields, then Cancel and the main action."))
COMP = [("filter-bar", "Filter bar", "Work: .toolbar + .views + .wapplied", "Search, filter buttons, the funnel with its count, the layout switch and Display, the + button; then the view pills; then the applied filters as chips with Clear all and the count."),
        ("queue-group", "Queue group", "Review: .rgroup + .tbl", "A group header (check box, name, count, how many are stale) over a card of rows that each carry their facts in muted lines and the same row actions."),
        ("work-rows", "Rows of work", "Work: .tbl.list", "A work row is two lines: the title with a state box, then the ID (a dotted link) and the project in muted text. The owner is a dotted link (You for the current user); the due date is red with \"n days late\" when it is late, otherwise plain with \"In n days\"; urgent priority is red."),
        ("brief-band", "Day band", "Today: .dayband .bandin", "A mono date line, a display greeting, one sentence of what matters, and the calendar controls, on the day tint."),
        ("brief-section", "Numbered section", "Today: .tsec  (h2.th + ol.bl)", "A display h2 with its count, then numbered one-sentence rows with their tools at the right."),
        ("settings-group", "Settings group", ".card + .srow", "A card with a display title and rows: label and one line of help at the left, the control at the right."),
        ("detail-health", "Health card", "cockpit: .card", "The health label (icon, word, colour), its six-week trend with a ? key, and the four figures that explain it."),
        ("milestone-card", "Timeline card", "cockpit and Milestones: .card", "A month strip with Today marked; the plan as shapes on a line."),
        ("page-head-crumb", "Page head with breadcrumb", ".crumb + h1 + .sub", "Where you are, what this is, and who it is for; a neighbour picker sits at the right."),
        ("notes-two-pane", "Two panes", "Notes", "A labelled list with a search box and collapse chevron beside a card that reads or edits the item, or says what the thing is for."),
        ("report-bar", "Document view", "Weekly report", "Breadcrumb, title and sub; a bar with zoom and Show as exported at the left, Export and the one primary at the right; then the sheet on a tinted canvas.")]
comp_html = "".join(f'<article class="ds-comp" id="k-{n}"><header><h3>{esc(t)}</h3><code>{esc(c)}</code></header><p class="ds-use">{u}</p><div class="ds-stage ds-shotbox">{both("comp-" + n, t)}</div></article>' for n, t, c, u in COMP)
dyn_html = "".join(f'<article class="ds-comp" id="c-{n}"><header><h3>{esc(t)}</h3><code>{esc(c)}</code></header><p class="ds-use">{u}</p><div class="ds-stage ds-shotbox">{both(f"{n}", t)}</div></article>' for n, t, c, u in D)

# ------------------------------------------------------------------ the guide
repo_steps = [
    ("Choose the pattern.", "Pick the nearest of the page patterns in section 5 (a list, a tabbed list, a queue, a brief, a detail page, settings, a document, two panes, docs, cards). If none fits, say why in the write-up before drawing anything."),
    ("Copy its snapshot.", "Quickest: copy a starter from <a href=\"templates/list.html\">templates/</a> (list, tabbed list, detail, settings). Otherwise, for a mockup copy <code>pages/&lt;pattern&gt;.html</code> (or <code>blank.html</code>) into <code>dev/mockups/</code>, change the stylesheet link to <code>../design-system/style.snapshot.css</code>, and replace the content of the <code>#v-…</code> section only. Keep the rail and the top bar."),
    ("Build the page in the standard order.", "<code>&lt;section class=\"view\" id=\"v-name\"&gt;&lt;div class=\"wrapmax\"&gt;</code>, then (if a detail page) the <code>.crumb</code>, then <code>h1</code>, then <code>.sub</code>, then the control row (<code>.toolbar</code>), then the content (cards or a <code>.tbl</code>)."),
    ("Use the components as they are.", "Buttons 32 px, one primary per region; icon buttons labelled; view pills for views; the funnel for filters; dates as text with a calendar button; counts and Refresh at the right of the control row."),
    ("Say what is empty, loading and wrong.", "Every list has an empty state that names the next step; an error says what happened and what to do; Undo accompanies every change that can be undone."),
    ("Check keyboard, dark mode and words.", "Tab through it; Esc closes the top-most thing; it works in dark (Alt+D) and in creaite and Cursor; sentence case, British English, DD-MM-YYYY, project full names."),
    ("Mark anything new.", "If you genuinely need a component that is not here, put it in one block marked <code>/* NEW */</code>, built from tokens only, and name it in the write-up so it can be added to this guide."),
]
code_steps = [
    "Add the section in <code>system/templates/dashboard/shell.html</code>: <code>&lt;section class=\"view\" id=\"v-name\" hidden&gt;&lt;div class=\"wrapmax\"&gt;…</code> (a page that draws itself leaves it empty and renders into it).",
    "Put the screen's code in <code>src/&lt;area&gt;.js</code> (or a component under <code>src/components/&lt;area&gt;/</code>, per <code>dev/COMPONENTS.md</code>): a render function that fills <code>#v-name</code>.",
    "Make <code>go('name')</code> show it: <code>core/nav.js</code> hides every <code>.view</code> and shows <code>#v-</code> + the name; give it a hash route in the same file (<code>#name=…</code>) so refresh, Back and links work.",
    "Add it to the side bar or More in <code>src/stores/rail.js</code> (<code>RAIL_ITEMS</code>) with an icon from the icon table (section 3) and, if it has a count, <code>setRailCount</code>.",
    "Register it in ⌘K if it is a place to jump to, and in Help (<code>system/templates/help.md</code>: a job and a <code>Screen:</code> line).",
    "Test it: the shared behaviour test (<code>dev/tests/test_shared_behaviour.py</code>) walks every menu, picker and dialog for keys and focus; add the page to the snapshots in <code>dev/tests/snapshots/</code> and write its own tests.",
]

kb = [("⌘K", "the command palette: search, jump to a place, run a command"), ("⌘J", "open or close ask creaite"), ("/", "open ask creaite (when you are not typing)"), ("?", "Help"),
      ("F", "add a filter (Work)"), ("D", "the Display menu (Work)"), ("⌘↵", "save and close an editor or a dialog"),
      ("Esc", "close the top-most thing: a menu or popup before the dialog or peek under it; it never stops a running request"),
      ("Alt + ↑ ↓ ← →", "move a row or a section (side bar dialog, report sections)"), ("⌘⇧N", "a note from anywhere"), ("Tab / Shift+Tab", "every control is reachable in reading order")]
kbrows = "".join(f"<tr><td><kbd>{esc(k)}</kbd></td><td>{esc(v)}</td></tr>" for k, v in kb)

voice = [
    "British English, plain and short; sentence case for headings and buttons.",
    "Dates on screen are DD-MM-YYYY (Today's day band writes them out: \"Thursday 15th October\"). Times are 24-hour.",
    "A project is called by its <b>full name</b>; the short code appears only inside an item ID (ABC-A-003) and where a code is typed.",
    "Name things by the job: Approve, Reject with a reason, Not needed, Later, Undo. Not Submit, Dismiss, OK.",
    "Never call a person a VIP in anything creaite shows or writes; the word lives only in the person's own field and Settings.",
    "Say what happened and what to do next. No developer words (a script name, \"cx-edit\", \"inbox\" for Intake).",
    "A toast says what changed; an error says what failed and how to fix it.",
]
a11y = [
    "Every icon button has an <code>aria-label</code>; every toggle has <code>aria-pressed</code> or <code>aria-checked</code>; the current page has <code>aria-current=\"page\"</code>.",
    "Targets are at least 24 × 24 px, or have room around them.",
    "The focus ring is <code>:focus-visible</code> in <code>--focus</code>; never remove it.",
    "Colour is never the only signal: health and state use an icon and a word as well.",
    "Reduced motion removes slides and fades; the delays stay the same. <code>--k</code> scales every duration.",
    "Hover popups follow the one hover standard (below); the keyboard opens them with no delay and Esc dismisses them.",
]
hover = [("Tooltip", "opens after 400 ms, closes 150 ms after leaving; the next one opens after 100 ms"), ("Card (a peek, the meeting-title popup)", "opens after 600 ms, closes 300 ms after leaving the trigger and the card"),
         ("Menu (flyouts, toolbar groups)", "opens after 200 ms, closes after 300 ms; a neighbouring menu opens after 80 ms; a diagonal move toward the menu keeps it open")]
hrows = "".join(f"<tr><td>{a}</td><td>{b}</td></tr>" for a, b in hover)

edges = ("On this line: font sizes have 19 distinct raw values, border radii 13, layers 10 raw uses in 7 values, line heights 22 distinct with no tokens, 49 distinct raw heights (Team Stark's recount, 17-10-2026). "
         "Controls come in more than one size by context (section 4); page titles are 34 px on Today and Help and 22 px elsewhere; <code>.fsel</code> is dead CSS (a 36 px, 16 px radius select no screen uses): do not copy it. #193 (tokens-193-full) tidies sizes, radii, layers and line heights.")

NAV = [("start", "Build a page"), ("rules", "Ten rules"), ("foundations", "Foundations"), ("palettes", "Palettes"), ("shell", "The app shell"), ("components", "Components"), ("patterns", "Page patterns"), ("interaction", "Interaction"),
       ("content", "Words"), ("a11y", "Accessibility"), ("check", "Checklist"), ("edges", "Rough edges"), ("version", "Version")]
ten = ["One primary button per region.", "Controls are the standard ones at their standard sizes.", "Colours are tokens only; it must work in dark and in every palette.", "Spacing, sizes, radii and layers come from the scale.",
       "Titles are display-font <code>h1</code>/<code>h2</code>; body is the text font; tables and labels use mono.", "Every list has an empty state; every change has Undo or a clear way back.",
       "Filters live in the funnel; views are pills; kinds are tabs.", "Dates are text with a calendar button, DD-MM-YYYY.", "Icons come from the app's icon table, always labelled.", "Nothing is shown that is not true; nothing changes without a visible way to undo."]

CSS = r"""/* guide chrome only: tokens only; every component specimen is the app's own markup */
html,body{height:auto;overflow:visible}body{display:block;background:var(--bg);color:var(--ink);font:400 var(--fs-md)/1.55 var(--font)}
.ds{display:grid;grid-template-columns:230px minmax(0,1fr);min-height:100vh}.ds-nav{position:sticky;top:0;align-self:start;height:100vh;overflow:auto;padding:20px 16px;border-right:1px solid var(--line);background:var(--surface)}
.ds-nav b{display:block;font:800 var(--fs-xl) var(--display);margin:0 0 4px}.ds-nav small{display:block;color:var(--muted);font-size:var(--fs-xs);margin:0 0 12px}.ds-nav a{display:block;padding:5px 10px;border-radius:var(--r-md);color:var(--ink);text-decoration:none;font-size:var(--fs-sm);font-weight:500}.ds-nav a:hover{background:var(--sunk)}.ds-nav h6{margin:14px 10px 4px;font:500 var(--fs-xs) var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.ds-ctl{display:flex;gap:6px;flex-wrap:wrap;margin:12px 0 0}.ds-ctl button{height:28px;border:1px solid var(--line);background:var(--surface);color:var(--ink);border-radius:var(--r-md);padding:0 10px;font:500 var(--fs-xs) var(--font);cursor:pointer}.ds-ctl button[aria-pressed=true]{background:var(--ink);color:var(--surface);border-color:var(--ink)}
.ds-main{padding:32px 40px 80px;max-width:1240px}.ds-main section{margin:0 0 56px;scroll-margin-top:16px}.ds-main h1{font:800 34px/1.1 var(--display);letter-spacing:-.02em;margin:0 0 8px}.ds-main h2.ds-h{font:800 26px var(--display);letter-spacing:-.01em;margin:0 0 6px;padding-top:8px;border-top:2px solid var(--ink)}.ds-lead{color:var(--muted);max-width:75ch;margin:0 0 18px}
.ds-main h3{font:700 var(--fs-xl) var(--display);margin:0}.ds-main h4{font:500 var(--fs-xs) var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:16px 0 6px}
.only-dark{display:none}:root[data-theme=dark] .only-dark{display:inline}:root[data-theme=dark] .only-light{display:none}
.ds-meta{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0 0}.ds-meta span{border:1px solid var(--line);background:var(--surface);border-radius:var(--r-pill);padding:2px 10px;font-size:var(--fs-xs);color:var(--muted)}
.ds-steps{counter-reset:s;list-style:none;margin:0;padding:0;display:grid;gap:10px}.ds-steps li{counter-increment:s;border:1px solid var(--line);background:var(--surface);border-radius:var(--r-lg);padding:12px 16px 12px 52px;position:relative}.ds-steps li::before{content:counter(s);position:absolute;left:14px;top:10px;width:26px;height:26px;border-radius:50%;background:var(--accent);color:var(--accent-ink);display:grid;place-items:center;font:700 var(--fs-sm) var(--font)}.ds-steps b{display:block}
.ds-two{display:grid;grid-template-columns:1fr 1fr;gap:16px}.ds-box{border:1px solid var(--line);background:var(--surface);border-radius:var(--r-lg);padding:14px 16px}.ds-box h3{margin:0 0 6px}.ds-box ul,.ds-box ol{margin:0;padding-left:20px}.ds-box li{margin:3px 0}
.ds-sws{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:10px}.ds-sw{border:1px solid var(--line);background:var(--surface);border-radius:var(--r-lg);padding:10px;display:grid;gap:2px;font-size:var(--fs-xs)}.ds-sw i{height:40px;border-radius:var(--r-md);border:1px solid var(--line);margin-bottom:6px}.ds-sw b{font-size:var(--fs-sm)}.ds-sw .ds-hex{font:500 var(--fs-xs) var(--mono);color:var(--muted)}.ds-sw em{font-style:normal;color:var(--ink)}.ds-sw small{color:var(--muted)}
.ds-ty{display:flex;justify-content:space-between;align-items:baseline;gap:16px;padding:6px 0;border-bottom:1px solid var(--line)}.ds-ty code,.ds-sp code,.ds-rad code,.ds-shd code,.ds-comp header code{font:500 var(--fs-xs) var(--mono);color:var(--muted)}
.ds-spx{display:flex;gap:16px;flex-wrap:wrap;align-items:end}.ds-sp{display:grid;gap:4px;justify-items:center}.ds-sp i{display:block;background:var(--accent-soft);border:1px solid var(--accent)}
.ds-radx,.ds-shdx{display:flex;gap:20px;flex-wrap:wrap}.ds-rad,.ds-shd{display:grid;gap:8px;justify-items:center}.ds-rad i{display:block;width:90px;height:56px;background:var(--sunk);border:1px solid var(--line-strong)}.ds-shd i{display:block;width:110px;height:56px;border-radius:var(--r-md);background:var(--surface)}
table.ds-t{width:100%;border-collapse:collapse;background:var(--surface);border:1px solid var(--line)}table.ds-t th,table.ds-t td{padding:7px 12px;border-bottom:1px solid var(--line);text-align:left;font-size:var(--fs-sm)}table.ds-t th{font:500 var(--fs-xs) var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--muted);background:var(--sunk)}
.ds-icons{display:grid;grid-template-columns:repeat(auto-fill,minmax(112px,1fr));gap:8px}.ds-ic{display:grid;gap:6px;justify-items:center;border:1px solid var(--line);background:var(--surface);color:var(--ink);border-radius:var(--r-md);padding:12px 6px 8px;cursor:pointer;font:500 var(--fs-xs) var(--mono)}.ds-ic:hover{border-color:var(--accent);color:var(--accent)}.ds-ic svg{width:24px;height:24px}
.ds-comp,.ds-pat{border:1px solid var(--line);background:var(--surface);border-radius:var(--r-lg);padding:16px 18px;margin:0 0 16px}.ds-comp header,.ds-pat header{display:flex;justify-content:space-between;align-items:baseline;gap:12px;flex-wrap:wrap}.ds-pat header a{font-size:var(--fs-sm)}
.ds-use{margin:6px 0 10px;max-width:80ch}.ds-stage{background:var(--bg);border:1px dashed var(--line);border-radius:var(--r-md);padding:18px}.ds-shotbox{display:flex;justify-content:center}.ds-shotbox img{max-width:100%;height:auto;max-height:560px}
.ds-row{display:flex;gap:18px;align-items:flex-start;flex-wrap:wrap}.ds-cell{margin:0;display:grid;gap:6px;justify-items:start}.ds-cell figcaption{font:500 var(--fs-xs) var(--mono);color:var(--muted)}.ds-col{display:grid;gap:12px}.ds-meas,.ds-dont{margin:10px 0 0;font-size:var(--fs-sm);color:var(--muted)}.ds-dont b{color:var(--bad)}
.ds-states{display:flex;flex-wrap:wrap;gap:12px;margin-top:12px}.ds-st{margin:0;display:grid;gap:4px;justify-items:center}.ds-st img{height:auto;max-width:260px;max-height:64px;border-radius:var(--r-sm)}.ds-st img.only-light{display:block}.ds-st img.only-dark{display:none}:root[data-theme=dark] .ds-st img.only-light{display:none}:root[data-theme=dark] .ds-st img.only-dark{display:block}.ds-st figcaption{font:500 var(--fs-2xs) var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.ds-pat-grid{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,1fr);gap:20px;margin-top:10px}.ds-shot img{width:100%;height:auto;border:1px solid var(--line);border-radius:var(--r-md)}.ds-pat-text ol,.ds-pat-text ul{margin:0;padding-left:20px}.ds-pat-text li{margin:3px 0}.ds-pat-text details{margin-top:12px}.ds-pat-text pre{font:500 var(--fs-xs)/1.5 var(--mono);background:var(--sunk);border:1px solid var(--line);border-radius:var(--r-md);padding:10px;overflow:auto;max-height:260px}
.ds-chipc{display:inline-block;width:12px;height:12px;border-radius:3px;border:1px solid var(--line);vertical-align:-1px}.ds-code{margin-top:10px}.ds-code summary{cursor:pointer;color:var(--accent);font-size:var(--fs-sm)}.ds-code pre{font:500 var(--fs-xs)/1.5 var(--mono);background:var(--sunk);border:1px solid var(--line);border-radius:var(--r-md);padding:10px;overflow:auto;max-height:260px;white-space:pre-wrap;word-break:break-all}.ds-copy{float:right;margin:6px 0 0;height:26px;border:1px solid var(--line);background:var(--surface);color:var(--ink);border-radius:var(--r-md);padding:0 10px;font:500 var(--fs-xs) var(--font);cursor:pointer}.ds-find{width:100%;height:32px;border:1px solid var(--line);border-radius:var(--r-md);background:var(--bg);color:var(--ink);padding:0 10px;font:400 var(--fs-sm) var(--font);margin:0 0 10px}
.ds-main code{font:500 .92em var(--mono);background:var(--sunk);border-radius:var(--r-sm);padding:1px 5px}.ds-comp header code{background:none;padding:0}
@media (max-width:1100px){.ds{grid-template-columns:1fr}.ds-nav{position:static;height:auto}.ds-pat-grid,.ds-two{grid-template-columns:1fr}}
"""

html = f'''<!doctype html>
<!-- creaite design system and guide to building a page. Taken from commit {snap["commit"]} ({snap["branch"]}, VERSION file {snap["version_file"]}) on {snap["taken"]}; drawn by style.snapshot.css. Generated by dev/tools/design_system_guide.py. -->
<html lang="en-GB" data-palette="creaite" data-theme="light"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>creaite design system</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500&family=Schibsted+Grotesk:wght@700;800&family=Source+Sans+3:wght@400;500;600;700&display=swap">
<link rel="stylesheet" href="style.snapshot.css">
<style>
{CSS}</style></head><body><div class="ds">
<nav class="ds-nav" aria-label="Sections"><b>creaite_</b><small>Design system and guide to building a page</small><input class=\"ds-find\" id=\"dsFind\" type=\"search\" placeholder=\"Find a component or pattern\" aria-label=\"Find a component or pattern\">
{"".join(f'<a href="#{i}">{esc(t)}</a>' for i, t in NAV)}
<h6>Components</h6>{"".join(f'<a href="#c-{c}">{esc(t)}</a>' for c, t in [("type", "Text"), ("btn", "Buttons"), ("ib", "Icon buttons"), ("vchip", "Pills"), ("tags", "Tags and chips"), ("input", "Fields"), ("tbl", "Table"), ("card", "Card"), ("menu-list", "Menus"), ("peek-panel", "Peek"), ("dialog-customise-sidebar", "Dialogs"), ("toast", "Toast"), ("ai-suggestion", "AI suggestion"), ("ask-running", "ask creaite working")])}
<h6>Patterns</h6>{"".join(f'<a href="#p-{c}">{esc(t)}</a>' for c, t in [("list", "List page"), ("tabbed", "Tabbed list"), ("queue", "Queue"), ("brief", "Brief"), ("detail", "Detail"), ("settings", "Settings"), ("doc", "Document"), ("client-doc", "Client report"), ("minutes", "Minutes"), ("reports", "Reports"), ("reporting", "Reporting space"), ("person", "Person"), ("milestones", "Milestones"), ("prep", "Prep"), ("two-pane", "Two panes"), ("docs", "Docs"), ("cards-sections", "Cards")])}
<div class="ds-ctl" role="group" aria-label="Theme"><button type="button" data-th="light" aria-pressed="true">Light</button><button type="button" data-th="dark" aria-pressed="false">Dark</button></div>
<div class="ds-ctl" role="group" aria-label="Palette"><button type="button" data-pal="creaite" aria-pressed="true">creaite</button><button type="button" data-pal="Cursor" aria-pressed="false">Cursor</button></div></nav>
<main class="ds-main"><h1>creaite design system</h1>
<p class="ds-lead">The definitive guide to how creaite looks and how to build a new page in it. Everything here is the real app: real markup, drawn by the app's own stylesheet, measured on the running screens. If this guide and the app disagree, the app is right and this guide has a fault: tell the Product Manager.</p>
<div class="ds-meta"><span>Taken from commit {esc(snap["commit"])}</span><span>{esc(snap["branch"])} (VERSION file {esc(snap["version_file"])})</span><span>{esc(snap["taken"])}</span><span>palette creaite, light and dark; also checked in Cursor</span><span>desktop and 900 px only</span></div>

<section id="start"><h2 class="ds-h">Build a page</h2><p class="ds-lead">For a mockup, and for the real thing. Seven steps; each is the whole rule.</p>
<ol class="ds-steps">{"".join(f"<li><b>{esc(a)}</b>{b}</li>" for a, b in repo_steps)}</ol>
<h3 style="margin-top:24px">Wiring a new page into the app (for the build)</h3><ol class="ds-steps">{"".join(f"<li>{s}</li>" for s in code_steps)}</ol></section>

<section id="rules"><h2 class="ds-h">Ten rules</h2><ol class="ds-steps">{"".join(f"<li>{r}</li>" for r in ten)}</ol></section>

<section id="foundations"><h2 class="ds-h">Foundations</h2>
<h3>Colour</h3><p class="ds-lead">Tokens only; never a raw hex. Each shows its light and dark value, its job, and how many rules in the stylesheet use it.</p><div class="ds-sws">{"".join(sw)}</div>
<h4>Contrast (WCAG), measured</h4><table class="ds-t"><thead><tr><th>Pair</th><th>Light</th><th>Dark</th><th>Result</th></tr></thead><tbody>{crow}</tbody></table>
<h3 style="margin-top:28px">Type</h3><div class="ds-two"><div class="ds-box"><h3>Families</h3><ul><li><b>Text</b>: {esc(light["--font"])}</li><li><b>Display</b> (h1, h2, h3): {esc(light["--display"])}</li><li><b>Mono</b> (table headers, key hints, small labels): {esc(light["--mono"])}</li></ul>
<p class="ds-meas">h1 weight 800 with −0.02em; h2 and h3 weight 700. Table headers: mono 12 px, weight 500, uppercase, letter-spaced .08em (the creaite palette's own rule).</p></div><div class="ds-box"><h3>The size scale</h3>{fs_rows}</div></div>
<h3 style="margin-top:28px">Space</h3><p class="ds-lead">A 4 px base: 2 px steps to 16, 4 px steps to 32, 8 px steps above. Written as plain pixels.</p><div class="ds-spx">{sp}</div>
<h3 style="margin-top:28px">Radius and shadow</h3><div class="ds-radx">{rad}</div><div class="ds-shdx" style="margin-top:22px">{shd}</div><p class="ds-meas">Controls use <code>--ctl-r</code> ({scale["--ctl-r"]}); cards and tables 12 px; dialogs 12–16 px.</p>
<h3 style="margin-top:28px">Layers</h3><p class="ds-meas">{zs}</p>
<h3 style="margin-top:28px">Motion</h3><table class="ds-t"><thead><tr><th>Token</th><th>Value</th></tr></thead><tbody>{mot}</tbody></table><p class="ds-meas"><code>--k</code> is 1 normally and 0 under reduced motion; every duration is multiplied by it.</p>
<h3 style="margin-top:28px">Icons ({len(live["icons"])})</h3><p class="ds-lead">The app's own icon table. 24 px grid, 1.8 px round-cap stroke, <code>currentColor</code>. Click one to copy its name. The sparkle (<code>spark</code>) is the AI mark.</p><div class="ds-icons">{icons}</div></section>

<section id="palettes"><h2 class="ds-h">Palettes: creaite and Cursor</h2><p class="ds-lead">Two palettes are tested in every release (creaite, the default, and Cursor). A page must work in both, light and dark. A palette changes colours, fonts and a few shapes; never the layout. Use the toggle at the left to see this whole guide in each.</p>
<table class="ds-t"><thead><tr><th>Token</th><th>creaite light</th><th>creaite dark</th><th>Cursor light</th><th>Cursor dark</th></tr></thead><tbody>{pal_rows}</tbody></table>
<p class="ds-meas">Cursor draws the accent as orange, the page on warm paper, and its shadows as a hairline ring; its type is its own gothic with Inter behind it. creaite is teal on cool grey with Source Sans 3, Schibsted Grotesk and JetBrains Mono. The other seven palettes exist but are not tested.</p></section>

<section id="shell"><h2 class="ds-h">The app shell</h2><p class="ds-lead">Every page lives inside the same frame. Never redraw it.</p>
<div class="ds-two"><div class="ds-box"><h3>Anatomy</h3><ul><li><b>Side bar</b> (<code>.rail</code>): {light.get("--rail-w", "224px")} wide expanded (<code>--rail-w</code>), 56 px icons only, 76 px icons with labels; items 36 px; Today first, More at the foot.</li><li><b>Top bar</b> (<code>.bar</code>): 53 px; search or jump (⌘K) at the left, ask creaite and the theme switch at the right.</li><li><b>Page</b> (<code>.view</code>): padding 20 × 24 × 40 px on the page tint; content in <code>.wrapmax</code>, max 1500 px.</li><li><b>Peek</b> (<code>#panel.peek</code>): over the right half, at least 520 px, 50% of the window.</li><li><b>ask creaite</b> panel opens over the page, never squeezing it.</li></ul></div>
<div class="ds-box"><h3>The real frame</h3><p class="ds-use">Every snapshot in <code>pages/</code> carries it. Start from <a href="blank.html">blank.html</a>.</p>{both_shot("files")}</div></div></section>

<section id="components"><h2 class="ds-h">Components</h2><p class="ds-lead">Each specimen is the app's own markup, drawn by its own stylesheet. The state pictures are the real component with the state forced (hover, focus, active, disabled), in light and dark.</p>
{"".join(C)}
<h3 style="margin:28px 0 8px">Floating and modal components (live screenshots)</h3>{dyn_html}<h3 style="margin:28px 0 8px">Composite pieces (live screenshots)</h3>{comp_html}</section>

<section id="patterns"><h2 class="ds-h">Page patterns</h2><p class="ds-lead">Seventeen ways a creaite page is put together, in a handful of families (list, queue, brief, detail, settings, document, two panes, docs). Pick the nearest; do not invent another without saying why. Each links to the real screen and shows its skeleton from the running app.</p>{"".join(PAT)}
<h3 style="margin:24px 0 8px">States every page has</h3><ul><li><b>Empty:</b> the <code>.empty</code> box (components) says what is missing and the next step.</li><li><b>Offline:</b> the live-server alert above, on every page.</li><li><b>Loading:</b> the stylesheet has no spinner or skeleton component (checked); a long job shows as steps in the ask creaite panel, or a <code>.prog</code> bar. Do not invent one.</li><li><b>Error:</b> an error banner (<code>.errbanner</code>) under the page banners, dismissible; a failed save says what to do.</li></ul>
<p class="ds-meas">The minutes view is not snapshotted (it opens from a staged meeting's Open draft in Review); it follows the Document pattern: a sheet on a tinted canvas with a bar above it, the transcript beside the draft.</p></section>

<section id="interaction"><h2 class="ds-h">Interaction</h2><div class="ds-two"><div class="ds-box"><h3>Keys</h3><table class="ds-t"><tbody>{kbrows}</tbody></table></div><div class="ds-box"><h3>The one hover standard</h3><table class="ds-t"><tbody>{hrows}</tbody></table><p class="ds-meas">From <code>src/core/hover.js</code>. Keyboard focus opens a tooltip or card with no delay; Esc dismisses it and it stays shut until the pointer leaves.</p></div></div>
<ul><li>Changes made in the page show at once and save in the background; an Undo toast follows anything undoable (10 seconds with Undo, 5 otherwise, and it waits while you point at it).</li><li>Anything that writes to the record waits for an approval; what creaite suggests always waits in Review.</li><li>Esc closes the top-most layer first (a menu or popup before the dialog or peek under it); it never stops a running request.</li></ul></section>

<section id="content"><h2 class="ds-h">Words</h2><ul>{"".join(f"<li>{v}</li>" for v in voice)}</ul></section>
<section id="a11y"><h2 class="ds-h">Accessibility</h2><ul>{"".join(f"<li>{v}</li>" for v in a11y)}</ul></section>
<section id="check"><h2 class="ds-h">Checklist before a page or a mockup is shown</h2><ol class="ds-steps"><li>Started from a snapshot or <code>blank.html</code>, linking the stylesheet copy; the file says which commit it came from.</li><li>Every existing control is an existing class at its real size.</li><li>One primary button per region; icon buttons labelled; filters in the funnel; views as pills.</li><li>Colours and sizes are tokens; it works in dark and in creaite and Cursor.</li><li>Empty, loading and error states are drawn; Undo is there for anything undoable.</li><li>Keyboard: Tab order, Esc, ⌘↵ where it saves.</li><li>Words: British English, sentence case, DD-MM-YYYY, project full names, no jargon.</li><li>Anything genuinely new is in one <code>/* NEW */</code> block and named in the write-up.</li><li>Fictional data only; no real names.</li></ol></section>
<section id="edges"><h2 class="ds-h">Rough edges (do not copy)</h2><p>{edges}</p></section>
<section id="version"><h2 class="ds-h">Version and upkeep</h2><p>Taken from commit <code>{esc(snap["commit"])}</code> on <code>{esc(snap["branch"])}</code> (its VERSION file says {esc(snap["version_file"])}; this is the v2.2.0 line, not yet cut), on {esc(snap["taken"])}. Refresh with <code>python3 dev/tools/design_system_snapshots.py --repo &lt;checkout&gt; --label &lt;branch&gt;</code>, then the components step and <code>python3 dev/tools/design_system_guide.py</code>, after the v2.2.0 cut, after #198 and #193 land, and after any release that changes how a screen looks. Team Stark checks the numbers against the code when they change (#205).</p></section>
</main></div>
<script>
const root=document.documentElement;
document.querySelectorAll('[data-th]').forEach(b=>b.addEventListener('click',()=>{{root.dataset.theme=b.dataset.th;document.querySelectorAll('[data-th]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)))}}));
document.querySelectorAll('[data-pal]').forEach(b=>b.addEventListener('click',()=>{{root.dataset.palette=b.dataset.pal;document.querySelectorAll('[data-pal]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)))}}));
document.querySelectorAll('.ds-ic').forEach(b=>b.addEventListener('click',()=>{{try{{navigator.clipboard.writeText(b.dataset.name)}}catch(e){{}}b.style.borderColor='var(--accent)'}}));
document.querySelectorAll('.ds-copy').forEach(b=>b.addEventListener('click',()=>{{const t=b.parentElement.querySelector('pre').textContent;try{{navigator.clipboard.writeText(t)}}catch(e){{}}b.textContent='Copied';setTimeout(()=>b.textContent='Copy',1200)}}));
document.getElementById('dsFind').addEventListener('input',e=>{{const q=e.target.value.toLowerCase();document.querySelectorAll('.ds-nav a').forEach(a=>{{a.style.display=(!q||a.textContent.toLowerCase().includes(q))?'':'none'}})}});
document.addEventListener('keydown',e=>{{if(e.altKey&&e.key==='d'){{root.dataset.theme=root.dataset.theme==='dark'?'light':'dark'}}}});
</script></body></html>
'''

# ------------------------------------------------------------------ starter pages: the blank shell with a real skeleton in it
def starter(name, inner, title):
    base = (DS / "blank.html").read_text()
    a = base.index('id="v-files"')
    i = base.index('<div class="wrapmax">', a) + len('<div class="wrapmax">')
    j = base.index("</div></section>", i)
    page = base[:i] + inner + base[j:]
    page = page.replace("<title>", "<title>", 1)
    (DS / "templates").mkdir(exist_ok=True)
    note = f"<!-- Starter page: {title}. The real app shell with a skeleton of real classes; replace the content, keep the structure (see ../index.html, page patterns). Stylesheet: ../style.snapshot.css. -->\n"
    page = page.replace('href="style.snapshot.css"', 'href="../style.snapshot.css"')
    (DS / "templates" / f"{name}.html").write_text(page.replace("<!doctype html>\n", "<!doctype html>\n" + note, 1))


def two_rows(tbl):
    rows = re.findall(r"<tr[ >].*?</tr>", tbl, flags=re.S)
    head, body = rows[0], rows[1:3]
    return re.sub(r"<tbody>.*</tbody>", "<tbody>" + "".join(body) + "</tbody>", tbl, flags=re.S)


tbl2 = two_rows(S("tbl"))
starter("list", f'<h1>Page title</h1><p class="sub">One line saying what this page is for.</p><div class="toolbar" style="margin-top:8px">{S("input")}{S("select")}<span style="flex:1"></span><span class="sub">2 of 2</span><button class="btn">Refresh</button></div><div style="margin-top:10px">{tbl2}</div>', "List page")
starter("tabbed-list", f'<h1>Page title</h1>{S("tabs")}<div class="toolbar">{S("input")}{S("ib-bd")}{S("seg")}</div><div class="views" style="margin-top:8px">{spec["vchip"]["d"]["html"] if spec.get("vchip",{}).get("d") else ""}</div><div style="margin-top:10px">{tbl2}</div>', "Tabbed list")
starter("detail", f'{S("crumb")}<h1>Page title</h1><p class="sub">One line saying whose this is.</p>{S("tabs")}<div style="margin-top:14px">{S("card")}{S("card")}</div>', "Detail page")
starter("settings", f'<h1>Settings group</h1><p class="sub">Rows of one control each.</p>{S("setgroup")}', "Settings group")

(DS / "index.html").write_text(html)
print("index.html", len(html), "bytes;", len(C), "components,", len(PAT), "patterns,", len(D), "floating components,", len(live["icons"]), "icons")
