// @ts-check
/* PrepToolbar (BL-286 parts A and B): the Prep popup's one toolbar. Shape this meeting (AI, part C: shown once shaping
   has registered itself), then Open prep page (primary: the page inside creaite, Meetings › Prep, #prep=<key>), and Draft
   agenda on the right, a menu in the pattern of Work's New decision: POAD, POAD lite (the last one used is marked and
   remembered) and Include who's invited. */
import { snack, viaServer } from "../../core/server.js";
import { draftWhyNot } from "../../drafts.js";
import { agendaInvited, agendaStyle, draftAgenda, prepPageOf, setAgendaInvited, setAgendaStyle } from "../../meetings.js";
import { popupRev, prepNow, prepShape, prepViewHref } from "../../stores/prepPopup.js";
import { closeShape, shapeKey } from "../../stores/prepShape.js";
import { Icon } from "../Icon.jsx";
import { Menu } from "../Menu.jsx";

/** Open the meeting's prep page inside creaite: the popup closes and the address becomes #prep=<key>.
    @param {string} key @param {string} day */
export function openPrepView(key, day) {
  const d = /** @type {HTMLDialogElement | null} */ (document.getElementById("prepDlg"));
  if (d && d.open) d.close();
  location.hash = prepViewHref(key, day);
}

export function PrepToolbar() {
  popupRev.value;
  const { e, day, key, m } = prepNow();
  if (!e) return null;
  const code = m.p || "", conf = !!(m.invite && m.invite.confidential), page = prepPageOf(e, day);
  const live = viaServer(), shape = prepShape.value;
  const openWhy = !code ? "Choose the project first" : !live ? "creaite isn’t running" : "";
  const openTip = openWhy || (page ? `Open the prep page (saved ${page.when})` : "Research the meeting and open its prep page in creaite");
  const why = draftWhyNot("agenda"), style = agendaStyle(), withInv = agendaInvited();
  return (
    <div class="preptb" role="toolbar" aria-label="Meeting prep">
      {shape && code ? (
        <button type="button" class="btn ai" data-prepshape="1" aria-pressed={shapeKey.value === key ? "true" : "false"} data-tip="Tell creaite how you want to run this meeting"
          onClick={() => shape(key)}><Icon name="spark" />Shape this meeting</button>
      ) : null}
      <button type="button" class="btn primary" data-prepview="1" aria-disabled={openWhy ? "true" : undefined} data-tip={openTip}
        onClick={() => { if (!code) { snack("Choose the project first"); return; } if (!live) { snack("The Prep page needs the live server"); return; }
          openPrepView(key, day); }}>Open prep page</button>
      <span class="sp"></span>
      {code ? (
        <Menu label="Draft agenda" icon="spark" btnCls="btn agbtn" data={{ agenda: "1" }} why={why} onBlocked={() => snack(why)}
          tip="Draft the invite text and a timed agenda from this meeting's items, to copy into the invite" menuLabel="Draft agenda"
          items={[
            { id: "poad", icon: "list", name: "POAD", mark: style === "poad" ? "last used" : "", data: { agstyle: "poad" },
              line: "Purpose, objectives, approach, deliverables. The full structure, for a decision meeting or a workshop." },
            { id: "lite", icon: "filetext", name: "POAD lite", mark: style === "lite" ? "last used" : "", data: { agstyle: "lite" },
              line: "A short, friendly paragraph, with a bulleted agenda only when the meeting has distinct steps." },
            { id: "sep", sep: true },
            { id: "invited", icon: "people", name: "Include who's invited", checked: withInv && !conf, disabled: conf, data: { aginvited: "1" },
              line: conf ? "A confidential meeting keeps no attendee list." : "Adds the attendee list to the invite text." },
          ]}
          onPick={id => { if (id === "invited") { setAgendaInvited(!withInv); popupRev.value++; return; }
            closeShape(); setAgendaStyle(id); popupRev.value++; draftAgenda().finally(() => { popupRev.value++; }); }} />
      ) : null}
    </div>
  );
}
