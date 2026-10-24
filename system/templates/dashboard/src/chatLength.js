// @ts-check
/* ===== #335 ===== Chat length warning. A long chat costs more with every message, because the whole conversation is read again.
   After `assistant.long_chat_turns` of your messages (setting, default 30) the panel shows one quiet line above the box:
   "Continue fresh with a summary". Accepting starts a new chat (the old one stays in History) and puts a short summary in the
   message box: a line on what you asked about, then the last few turns as text. It is built here, from the messages on
   screen, so no run is made. Nothing is sent to Claude until you add your question and press Send. "Not now" hides the line
   for this chat. Counts only: no text leaves the page, nothing is stored. */
import { newChat, chPut } from "./ask.js";
import { $, $$ } from "./core/dom.js";
import { shared } from "./core/state.js";
import { viaServer } from "./core/server.js";
import { loadCatalogue, settingOf } from "./stores/settings.js";

export const LONG_TURNS = 30, LAST_TURNS = 4, ASKED_ABOUT = 5, LINE_MAX = 160, SUMMARY_MAX = 1800;
/** chats whose line was dismissed with Not now (this page only) @type {Set<string>} */
const NOTNOW = new Set();
let CATLOADED = false;

/** @param {string} s @param {number} n */
const clip = (s, n) => { s = String(s || "").replace(/\s+/g, " ").trim(); return s.length > n ? s.slice(0, n - 1).trimEnd() + "…" : s; };
/** Your messages and creaite's replies as they are on screen, in order. @returns {{who: string, text: string}[]} */
export function chatTurns() {
  /** @type {{who: string, text: string}[]} */
  const out = [];
  for (const m of $$("#chLog .msg.u, #chLog .msg.a.md, #chLog .msg.a:not(.info):not(.runask)")) {
    const u = m.classList.contains("u"), t = clip(m.textContent, 600);
    if (t) out.push({ who: u ? "you" : "creaite", text: t });
  }
  return out;
}
/** The number of your messages in the chat on screen. */
export const chatLength = () => $$("#chLog .msg.u").length;
/** The limit from the setting, else the default; never below 5. */
export function longLimit() {
  const s = settingOf("assistant.long_chat_turns"), n = Number(s ? s.value : LONG_TURNS);
  return Number.isFinite(n) && n >= 5 ? Math.round(n) : LONG_TURNS;
}
/** The summary text for the new chat's message box. @param {{who: string, text: string}[]} turns */
export function summaryOf(turns) {
  const asked = turns.filter(t => t.who === "you");
  const about = asked.slice(0, ASKED_ABOUT).map(t => "- " + clip(t.text, LINE_MAX));
  const last = turns.slice(-LAST_TURNS).map(t => (t.who === "you" ? "You: " : "creaite: ") + clip(t.text, 400));
  let s = `Continuing from an earlier chat of ${asked.length} messages.\n\nWhat I asked about:\n${about.join("\n")}\n\nThe last few turns:\n${last.join("\n")}\n\nNext: `;
  if (s.length > SUMMARY_MAX) s = s.slice(0, SUMMARY_MAX - 7).trimEnd() + "…\n\nNext: ";
  return s;
}
/** Show or hide the line for the chat on screen. */
export function chatLengthSync() {
  const box = $("#chLong"); if (!box) return;
  const n = chatLength(), lim = longLimit(), key = String(shared.ASKCHAT || ""), on = !!shared.ASKCHAT && n >= lim && !NOTNOW.has(key);
  box.hidden = !on;
  const t = $("#chLongText"); if (t && on) t.textContent = `This chat is long (${n} messages), so each reply takes longer and costs more.`;
}
/** Continue fresh: a new chat, the summary in the box, nothing sent. */
export function chatContinueFresh() {
  if (shared.BUSY) return;
  const text = summaryOf(chatTurns());
  newChat();
  chPut(text);
  chatLengthSync();
}
export function bootChatLength() {
  const log = $("#chLog"), box = $("#chLong"); if (!log || !box) return;
  let t = 0;
  new MutationObserver(() => { clearTimeout(t); t = window.setTimeout(chatLengthSync, 120); }).observe(log, { childList: true });
  $("#chLongGo").addEventListener("click", chatContinueFresh);
  $("#chLongNo").addEventListener("click", () => { NOTNOW.add(String(shared.ASKCHAT || "")); chatLengthSync(); $("#chIn").focus(); });
  if (viaServer() && !CATLOADED) { CATLOADED = true; loadCatalogue().then(chatLengthSync); }
}
