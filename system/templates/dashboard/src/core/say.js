// @ts-check
/* core/say.js (#307, v2.6.1): plain words for what Intake tells a person. Messages that come back from review.py, propose.py and
   the run engine use the engine's own words (staged, Review, proposal, tracker, file paths, ".vtt"); the page says them here, so
   the server's text stays as it is. Pure functions, no page, no server: table-driven in dev/tests/test_intake_say_307.py. */

/** The engine's words, as the page says them. Applied in order, each to the whole message. */
const REWORDS = /** @type {[RegExp, string][]} */ ([
  [/\s*\((?:inbox|system|projects)\/[^)]*\)/g, ""],                          /* a path in brackets */
  [/\b(?:inbox|system|projects)\/\S+/g, "the file"],                         /* a path on its own */
  [/set aside in the file;? nothing was written to the tracker\.?/g, "kept aside; nothing was saved."],
  [/nothing was written to the tracker/g, "nothing was saved"],
  [/transcript no longer in the inbox/g, "the transcript is no longer in Intake"],
  [/\b(\d+) of (\d+) staged for Review; (\d+) not staged\b/g, "$1 of $2 drafted; $3 not drafted"],
  [/\b0 of \d+ waiting in Review;? (\d+) couldn't be read\b/g, "Nothing was drafted. $1 couldn't be read"],
  [/\b0 of \d+ waiting in Review\b/g, "Nothing was drafted"],
  [/\b(\d+) of (\d+) waiting in Review\b/g, "$1 of $2 drafted, ready to check in Intake"],
  [/\bNot staged: process it again\b/g, "Nothing was drafted: process it again"],
  [/\bNot in Review yet\b/g, "Not drafted yet"],
  [/\bnothing was added to Review\b/g, "nothing was drafted"],
  [/\b(?:is|are) staged: the drafts are waiting in Review/g, "is ready: the drafts are waiting in Intake"],
  [/\bwaiting in Review\b/g, "waiting in Intake"],
  [/\bHeld in Review, not applied\b/g, "Held in Intake, not saved"],
  [/\bnew items? in Review\b/g, "new items to check in Intake"],
  [/\bin Review\b/g, "in Intake"],
  [/\bfor Review\b/g, "in Intake"],
  [/\bnot staged\b/gi, "not drafted"],
  [/\bstaged\b/gi, "drafted"],
  [/\bproposals\b/gi, "suggestions"],
  [/\bproposal\b/gi, "suggestion"],
  [/\bproposed\b/gi, "suggested"],
  [/\bnot applied\b/gi, "not saved"],
  [/\balready applied\b/gi, "already saved"],
  [/\bapplied\b/gi, "saved"],
  [/\bthe tracker\b/gi, "your records"],
  [/\bthe live server\b/gi, "creaite"],
  [/\bReview\b/g, "Intake"],
]);

/** A message from the engine, in the page's plain words. Keeps its capital: "Staged" gives "Drafted". @param {unknown} msg */
export function plainSay(msg) {
  let t = String(msg == null ? "" : msg);
  for (const [re, to] of REWORDS) t = t.replace(re, (...a) => {
    const m = a[0], out = to.replace(/\$(\d)/g, (_, i) => String(a[+i] ?? ""));
    return /^[A-Z]/.test(m) && /^[a-z]/.test(out) ? out[0].toUpperCase() + out.slice(1) : out;
  });
  return t;
}

/** "X needs creaite": what a button says when the page is not connected to creaite. @param {string} what */
export const needsConnection = what => `${what} needs creaite to be connected. Reopen it and try again.`;

/** What the "Saved …" toast calls the rows approved. A row is a Review row: { kind, op, rec? }. @param {any} r */
export function savedNoun(r) {
  if (!r) return ["change", "changes"];
  if (r.op === "update") return ["update", "updates"];
  switch (r.kind) {
    case "actions": return ["action", "actions"];
    case "decisions": return ["decision", "decisions"];
    case "raid": return ["risk or issue", "risks or issues"];
    case "milestones": return ["milestone change", "milestone changes"];
    case "promises": return ["promise", "promises"];
    case "draft": return /^Report/.test(String(r.rec && r.rec.t || "")) ? ["report", "reports"] : ["set of minutes", "sets of minutes"];
    case "files": return ["file change", "file changes"];
    default: return ["change", "changes"];
  }
}

/** What was just decided, from the rows decided since the last save and whether each was approved: "Saved 1 action",
    "Saved 2 actions and 1 decision", "Rejected 1 action". @param {{r: any, v: string}[]} list */
export function decidedWords(list) {
  const out = [];
  for (const verb of ["approved", "rejected"]) {
    const by = /** @type {Map<string, [number, string, string]>} */ (new Map());
    for (const x of list.filter(y => y.v === verb)) {
      const [one, many] = savedNoun(x.r), e = by.get(one) || [0, one, many];
      e[0]++; by.set(one, e);
    }
    const parts = [...by.values()].map(([n, one, many]) => `${n} ${n === 1 ? one : many}`);
    if (parts.length) out.push(`${verb === "approved" ? "Saved" : "Rejected"} ${parts.length > 1 ? parts.slice(0, -1).join(", ") + " and " + parts[parts.length - 1] : parts[0]}`);
  }
  return out.length ? out.join(". ") : "Saved";
}

/** Why a file could not be added, one line: the page's own rule, or the server's answer in plain words. @param {string} name @param {string} why */
export const addFailed = (name, why) => `${name}: ${plainSay(why).replace(/[.\s]+$/, "")}`;
