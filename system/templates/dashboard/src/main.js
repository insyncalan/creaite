// @ts-check
/* The dashboard's script (BL-231 step 2b). dev/tools/build_dashboard_js.py bundles this file and everything it
   imports with the pinned esbuild into one IIFE, `var CREAITE=(()=>{…})();`, the page's one app <script>.
   `split_dashboard.py build` puts it there.

   Core comes first, then each area, in today's order. Every module's exports are this module's exports, so `page`
   below is every name; publish() puts the ones on purpose on window (core/globals.js). Then the page starts: each
   module's load-time steps (its boot…() functions) and the start-up, in today's order (the order the blocks had in
   the one script before BL-231). The modules import each other; none reads another's value while it loads
   (test_dashboard_split checks it), so the order esbuild runs them in doesn't matter. */
import * as page from "./main.js";

export * from "./core/index.js";

export * from "./rail.js";

export * from "./today.js";

export * from "./projects.js";

export * from "./work.js";

export * from "./panel.js";

export * from "./milestones.js";

export * from "./intake.js";

export * from "./review.js";

export * from "./files.js";

export * from "./activity.js";

export * from "./settings.js";

export * from "./ask.js";

export * from "./meetings.js";

export * from "./help.js";
export * from "./helpscreen.js";

export * from "./drafts.js";

export * from "./components/StatusDot.jsx";   /* BL-256: the components (dev/COMPONENTS.md) */
export * from "./components/Menu.jsx";
export * from "./components/Picker.jsx";   /* BL-316: choose a value, a calendar, a small popover */
export * from "./components/Combobox.jsx";   /* BL-316 */
export * from "./components/Peek.jsx";   /* BL-316: a side peek's frame */
export * from "./components/mount.js";
export * from "./components/Icon.jsx";
export * from "./components/Dialog.jsx";
export * from "./components/dialogs/PageDialogs.jsx";   /* BL-316: the page's dialogs, each a Dialog */
export * from "./components/Chip.jsx";
export * from "./components/TextEditor.jsx";   /* BL-301 A: the one editor as a block */
export * from "./components/report/Sheet.jsx";   /* v2.1.0 P5: the A4 sheet */
export * from "./components/report/sheetLib.js";
export * from "./components/report/redraft.js";   /* #90: the ✦ (redraftAnswer is what the tests drive) */

export * from "./components/peek/ChasePane.jsx";   /* BL-298: Draft email in the peek */
export * from "./components/Tabs.jsx";
export * from "./components/FilterBar.jsx";   /* BL-316: the filter bars of Work, Review and Settings › People */
export * from "./components/Toast.jsx";   /* BL-316: the message at the foot of the page */
export * from "./components/prep/PrepPage.jsx";   /* BL-286 D: Meetings › Prep */
export * from "./components/settings/Health.jsx";   /* #159: runHealthFix is tested by name (test_link_renderers) */
export * from "./components/prep/PrepShape.jsx";   /* #159: its source link is tested by name (test_link_renderers) */
export * from "./stores/prep.js";
export * from "./components/today/DayTabs.jsx";
export * from "./components/today/DayCurve.jsx";
export * from "./components/today/DayMeetings.jsx";
export * from "./stores/today.js";
export * from "./components/closeday/CloseDay.jsx";
export * from "./components/closeday/FirstThing.jsx";
export * from "./components/IconButton.jsx";   /* BL-319: Today as one home */
export * from "./components/today/ToDecide.jsx";
export * from "./components/today/WeekAhead.jsx";

export * from "./components/review/RejectMenu.jsx";   /* BL-315 */
export * from "./components/review/ContextMenu.jsx";   /* BL-316: the right-click menu */

export * from "./components/review/RejectsList.jsx";

export * from "./stores/rejects.js";

export * from "./components/notes/CaptureDrawer.jsx";   /* BL-301 C: the capture drawer */
export * from "./stores/capture.js";
export * from "./components/AiSelect.jsx";   /* BL-301 D: AI on selected text */
export * from "./stores/aiEdit.js";
export * from "./components/LinkPopover.jsx";   /* #120: links in the rich editors */
export * from "./core/linkUrl.js";
export * from "./core/linkText.js";   /* #121: links in plain text */
export * from "./core/editorLink.js";

import { bootAiSelect } from "./components/AiSelect.jsx";
import { bootLinkPopover } from "./components/LinkPopover.jsx";

export * from "./components/peek/SneakPeek.jsx";   /* BL-322: Sneak peek */
export * from "./components/peek/PeekProps.jsx";   /* BL-316: the peek's properties as Chips */

export * from "./sneak.js";
export * from "./notes.js";   /* BL-301 B: the Notes tab */
export * from "./stores/notes.js";
export * from "./components/notes/FindUpdates.jsx";   /* BL-301 E: Find updates, the panel beside a note */
export * from "./components/notes/DeleteNote.jsx";   /* #124: Delete note, its confirm box and the card */
export * from "./stores/findUpdates.js";
export * from "./stores/reporting.js";   /* BL-337: Reports and the reporting space */
export * from "./components/reporting/ReportingSpace.jsx";
export * from "./components/reporting/ReportsPage.jsx";
export * from "./components/reporting/ReportingCard.jsx";
export * from "./stores/reportingSettings.js";   /* H3 (#221): the client report setting, per project */
export * from "./components/report/hub/ClientReportPanel.jsx";   /* H3 (#221): the hub's Client report settings panel */

import { bootActivity0071, bootActivity0072, bootActivity0205 } from "./activity.js";
import { bootAsk0080, bootAsk0089, bootAsk0090, bootAsk0094, bootAsk0095, bootAsk0096, bootAsk0098, bootAsk0101, bootAsk0102, bootAsk0105, bootAsk0107, bootAsk0109, bootAsk0113, bootAsk0117, bootAsk0118, bootAsk0119, bootAsk0120, bootAsk0207, bootAsk0208, reattach } from "./ask.js";
import { bootData } from "./core/data.js";
import { bootDayRoll } from "./core/dayroll.js";
import { bootDialogs } from "./components/dialogs/PageDialogs.jsx";
import { bootLostClick, bootTooltips } from "./core/dom.js";
import { bootCalendar, bootCmdEnter, bootDateWords, bootOwnerCombo, bootSources, bootTickBoxes, bootWeekendNote } from "./core/fields.js";
import { publish } from "./core/globals.js";
import { bootCopyCommand, bootKeyboard } from "./core/keys.js";
import { bootMotionHooks } from "./core/motion.js";
import { bootTopBar } from "./core/topbar.js";   /* #207 */
import { bootCountLinks, bootGoLinks, bootNav, bootOpenAll, bootTabTitle, navWrite, parseHash, restoreNav } from "./core/nav.js";
import { bootDevTag, bootMotion, bootTheme, bootThemeButton, S } from "./core/page.js";
import { bootDebugLog, bootEventStream, bootLive, bootPageRefresh, bootPulse, bootToast, checkLive, renderBadge, status, vaultInit } from "./core/server.js";
import { shared } from "./core/state.js";
import { bootDrafts0129, bootDrafts0160, bootDrafts0196, bootDrafts0202, bootDrafts0203, bootDrafts0204 } from "./drafts.js";
import { bootFiles0068, bootFiles0069 } from "./files.js";
import { bootNotes } from "./notes.js";
import { bootHelp0091, bootHelp0158, bootHelp0161, bootHelp0162, firstHelp } from "./help.js";
import { bootHelpScreen } from "./helpscreen.js";
import { bootIntake0053, bootIntake0134, bootIntake0135, bootIntake0136, bootIntake0137, inboxBadge } from "./intake.js";
import { bootPrepShape } from "./stores/prepShape.js";
import { bootMeetings0125, bootMeetings0126, bootMeetings0143, bootMeetings0144, bootMeetings0145, bootMeetings0201, openFromAddress } from "./meetings.js";
import { bootMilestones0051, bootMilestones0172, bootMilestones0184, bootMilestones0185, bootMilestones0186, bootMilestones0188, bootMilestones0189, bootMilestones0190, bootMilestones0191, bootMilestones0192 } from "./milestones.js";
import { bootPanel0050, bootPanel0165, bootPanel0166, bootPanelChase, bootPanel0167, bootPanel0168, bootPanel0169, bootPanel0171, bootPanel0173, bootPanel0174, bootPanel0175, bootPanel0176, bootPanel0177, bootPanel0178, bootPanel0179, bootPanel0181, bootPanel0182, bootPanel0197, bootPanel0198, bootPanel0199, bootPanel0200 } from "./panel.js";
import { bootProjects0029, bootProjects0054, bootProjects0055, bootProjects0056, bootProjects0058, bootProjects0059, bootProjects0081, bootProjects0083, bootProjects0124 } from "./projects.js";
import { bootSneak } from "./sneak.js";
import { bootRail0007, bootRail0077 } from "./rail.js";
import { bootReview0060, bootReview0061, bootReview0063, bootReview0064, bootReview0065, bootReview0067, bootReview0193, bootReview0195, bootReview0209, bootReview0315 } from "./review.js";
import { bootSettings0073, bootSettings0076, bootSettings0078, bootSettings0079, bootSettings0127, bootSettings0138, bootSettings0140, bootSettings0155, bootSettings0163 } from "./settings.js";
import { bootToday0026, bootToday0027, bootToday0028, bootToday0159, bootToday0164, bootToday319 } from "./today.js";
import { bootWork0031, bootWork0034, bootWork0035, bootWork0036, bootWork0038, bootWork0039, bootWork0040, bootWork0041, bootWork0130, bootWork0132, bootWork0133, bootWork0147, bootWork0148, bootWork0150 } from "./work.js";

publish(page);

/* ======================= the load-time steps and the start-up, in today's order ======================= */
bootDialogs();   /* BL-316: first, so every step after finds the dialogs' inner ids */
bootTooltips();
bootAiSelect();   /* BL-301 D: before any editor is made */
bootLinkPopover();   /* #120: likewise */
bootLostClick();
bootDevTag();
bootRail0007();
bootTheme();
bootMotion();
bootData();
bootToast();
bootLive();
bootNav();
bootTopBar();   /* #207 */
bootCountLinks();
bootGoLinks();
bootToday0026();
bootToday0027();
bootToday0028();
bootToday319();   /* BL-319 */
bootProjects0029();
bootWork0031();
bootWork0034();
bootWork0035();
bootWork0036();
bootWork0038();
bootWork0039();
bootWork0040();
bootWork0041();
bootSources();
bootCalendar();
bootDateWords();
bootOwnerCombo();
bootPanel0050();
bootMilestones0051();
bootIntake0053();
bootProjects0054();
bootProjects0055();
bootProjects0056();
bootCmdEnter();
bootProjects0058();
bootProjects0059();
bootReview0060();
bootReview0061();
bootTickBoxes();
bootReview0063();
bootReview0064();
bootReview0065();
bootReview0067();
bootFiles0068();
bootFiles0069();
bootActivity0071();
bootActivity0072();
bootSettings0073();
bootSettings0076();
bootRail0077();
bootSettings0078();
bootSettings0079();
bootAsk0080();
bootProjects0081();
bootProjects0083();
bootAsk0089();
bootAsk0090();
bootHelp0091();
bootAsk0094();
bootAsk0095();
bootAsk0096();
bootAsk0098();
bootAsk0101();
bootAsk0102();
bootAsk0105();
bootAsk0107();
bootAsk0109();
bootAsk0113();
bootAsk0117();
bootAsk0118();
bootAsk0119();
bootAsk0120();
bootThemeButton();
bootCopyCommand();
bootKeyboard();
bootProjects0124();
bootMeetings0125();
bootMeetings0126();
bootSettings0127();
bootDrafts0129();
bootWork0130();
bootWork0132();
bootWork0133();
bootIntake0134();
bootIntake0135();
bootIntake0136();
bootIntake0137();
bootSettings0138();
bootTabTitle();
bootSettings0140();
bootPulse();
bootEventStream();
bootMeetings0143();
bootMeetings0144();
bootMeetings0145();
bootWork0147();
bootWork0148();
bootWork0150();
/* ======================= start ======================= */
status(); renderBadge(); inboxBadge(); vaultInit(); checkLive(); setInterval(checkLive,(S.healthSecs||30)*1000); reattach();
/* open on the place named in the address (BL-38): #review, #cockpit=ABC, #work=raid&p=ABC, …&item=ABC-003 */
shared.HADHASH=!!location.hash&&!/^#openfile=/.test(location.hash);
openFromAddress();                                                       /* BL-126: clears the address, so what follows is a plain start */
shared.HASH0=location.hash;   /* BL-186: the address as opened (the Milestones page is restored once its block has run) */
restoreNav(/^#?milestones(=|&|$)/.test(location.hash||"")?null:parseHash(location.hash)); navWrite(false);   /* BL-231: milestone and meeting addresses aren't restored here (as before their blocks taught parseHash them): the Milestones page is restored by its own block below */
firstHelp();
shared.LOADING=false;
bootDebugLog();
bootSettings0155();
bootMotionHooks();
bootOpenAll();
bootHelp0158();
bootToday0159();
bootDrafts0160();
bootHelp0161();
bootHelp0162();
bootHelpScreen();
bootSettings0163();
bootToday0164();
bootPanel0165();
bootPanel0166();
bootPanelChase();
bootSneak();
bootPanel0167();
bootPanel0168();
bootPanel0169();
bootPanel0171();
bootMilestones0172();
bootPanel0173();
bootPanel0174();
bootPanel0175();
bootPanel0176();
bootPanel0177();
bootPanel0178();
bootPanel0179();
bootWeekendNote();
bootPanel0181();
bootPanel0182();
bootMilestones0184();
bootMilestones0185();
bootMilestones0186();
bootMilestones0188();
bootMilestones0189();
bootMilestones0190();
bootMilestones0191();
bootMilestones0192();
bootReview0193();
bootReview0195();
bootDrafts0196();
bootPanel0197();
bootPanel0198();
bootPanel0199();
bootPanel0200();
bootMeetings0201();
bootPrepShape();   /* BL-286 C: Shape the meeting's switch */
bootDrafts0202();
bootDrafts0203();
bootDrafts0204();
bootActivity0205();
bootAsk0207();
bootAsk0208();
bootReview0209();
bootReview0315();
bootNotes();   /* BL-301 B */
bootDayRoll();   /* #171 */
bootPageRefresh();   /* BL-327: last, once everything is drawn */
