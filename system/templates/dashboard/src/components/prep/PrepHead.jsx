// @ts-check
/* PrepHead (BL-286 part A): the Prep popup's header, in the peek's pattern. The date line ("Tomorrow · Wednesday 14th
   October · 10:00 – 10:45 · Microsoft Teams"), the title, then the chips: the project (it opens the project picker; the
   choice is remembered for the series), the series ("Every 2 weeks · 6th meeting · last 29-09-2026") and who is invited
   (initials and a count, the names on hover). A confidential meeting keeps only its title and times, so it has no
   invited chip. */
import { P, pName } from "../../core/data.js";
import { fd, TODAY } from "../../core/page.js";
import { snack } from "../../core/server.js";
import { choosePrep, hubFor } from "../../meetings.js";
import { popupRev, prepNow } from "../../stores/prepPopup.js";
import { longDay, pkAdd } from "../../today.js";
import { Icon } from "../Icon.jsx";
import { openPicker } from "../Picker.jsx";

/** "Today · Tuesday 13th October", "Tomorrow · …" or the day written out.
    @param {string} day */
export function prepDayLabel(day) {
  const lead = day === TODAY ? "Today" : day === pkAdd(TODAY, 1) ? "Tomorrow" : "";
  return lead ? `${lead} · ${longDay(day)}` : longDay(day);
}

/** Two letters for an avatar.
    @param {string} name */
export const initialsOf = name => (String(name || "").split(/[\s.@_-]+/).filter(w => /^[A-Za-z]/.test(w)).slice(0, 2)
  .map(w => w[0].toUpperCase()).join("") || "?");

/** The words the invite's recurrence gives ("weekly" → "Every week"), for the series chip without the live server.
    @param {string} r */
const cadence = r => { const s = String(r || "").toLowerCase();
  return /daily/.test(s) ? "Every day" : /fortnight|biweekly|every 2 weeks/.test(s) ? "Every 2 weeks" : /weekly/.test(s) ? "Every week"
    : /monthly/.test(s) ? "Every month" : ""; };

/** Who is invited: the live server's names (people register, BL-55), else the invite's own names.
    @param {any} m @param {any} brief @returns {{name: string, initials: string, registered: boolean}[]} */
export function invitees(m, brief) {
  if (brief && brief.people) return brief.people.invitees || [];
  const v = (m && m.invite) || {};
  return (v.attendees || []).filter((/** @type {any} */ a) => a && a.name).map((/** @type {any} */ a) =>
    ({ name: String(a.name), initials: initialsOf(a.name), registered: true }));
}

export function PrepHead() {
  popupRev.value;                                   /* redraw with the list */
  const { e, day, m, brief } = prepNow();
  if (!e) return null;
  const code = m.p || "", conf = !!(m.invite && m.invite.confidential);
  const series = brief && brief.series ? brief.series.text
    : [cadence(m.invite && m.invite.recurrence), m.last ? `last ${fd(m.last)}` : ""].filter(Boolean).join(" · ");
  const inv = conf ? [] : invitees(m, brief);
  const hub = hubFor({ eid: e.id, day, start: e.start, title: e.title });
  const name = code === "_portfolio" ? "Portfolio (all projects)" : code ? pName(code) : "";

  /** @param {MouseEvent} ev */
  const pickProject = ev => {
    const btn = /** @type {HTMLElement} */ (ev.currentTarget);
    openPicker(btn, { label: "Project", value: code,
      options: [...P.filter(p => p.active !== false || p.code === code).map(p => ({ v: p.code, label: p.name, icon: "projects" })),
        { v: "_portfolio", label: "Portfolio (all projects)", icon: "projects" }],
      onPick: async v => { if (v === code) return; await choosePrep(v);
        /* BL-316: a change offers Undo (the series is remembered for the project it had) */
        if (code) snack(`Remembered for this series: ${v === "_portfolio" ? "Portfolio (all projects)" : pName(v)}`, () => { choosePrep(code); }); } });
  };

  return (
    <div class="prephead">
      <div class="prephd">
        <div class="sub" id="prepWhen">{`${prepDayLabel(day)} · ${e.start} – ${e.end}${e.where ? " · " + e.where : ""}`}</div>
        <h2 id="prepTitle">{e.title}</h2>
        <div class="prepmeta">
          <button type="button" class={`chip prepchip${code ? "" : " need"}`} id="prepProjBtn" data-code={code} aria-haspopup="listbox"
            aria-expanded="false" aria-label={code ? `Project: ${name}. Change it (remembered for this series)` : "Choose the project for this meeting"}
            data-tip={code ? "Change the project (remembered for this series)" : "Choose the project; creaite remembers it for this series"} onClick={pickProject}>
            <span class="pdot" aria-hidden="true"></span>{code ? name : "Choose a project…"}<Icon name="chevdown" cls="nch" />
          </button>
          {m.how === "remembered" ? <span class="sub">remembered for this series</span> : null}
          {series ? <span class="chip" id="prepSeries"><Icon name="refresh" />{series}</span> : null}
          {inv.length ? (
            <span class="chip" id="prepInvited" data-tip={inv.map(p => p.name).join(", ")} aria-label={`${inv.length} invited: ${inv.map(p => p.name).join(", ")}`}>
              <span class="avs" aria-hidden="true">{inv.slice(0, 3).map((p, i) => <span key={i} class="av">{p.initials}</span>)}
                {inv.length > 3 ? <span class="av">{`+${inv.length - 3}`}</span> : null}</span>
              <span aria-hidden="true">{`${inv.length} invited`}</span>
            </span>
          ) : null}
          {hub ? <a href={`#meeting=${hub}`} class="linkbtn mhlink" data-meeting={hub} data-tip="Everything about this meeting, from invite to follow-up">Meeting page</a> : null}
        </div>
      </div>
      <button type="button" class="iconbtn" id="prepClose" aria-label="Close"><Icon name="x" /></button>
    </div>
  );
}
