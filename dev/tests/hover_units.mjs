// #143: core/hover.js on a fake clock (no real waiting). Run by test_hover_standard.py: node hover_units.mjs <path to hover.mjs>
// Prints one JSON object: case name -> "ok" or the failure text.
const H = await import(process.argv[2]);

/** A clock the cases move by hand. */
function clock() {
  let now = 0, id = 0; const timers = new Map();
  return {
    set: (fn, ms) => { const i = ++id; timers.set(i, { at: now + ms, fn }); return i; },
    clear: i => { timers.delete(i); },
    tick(ms) {
      const end = now + ms;
      for (;;) {
        const due = [...timers].filter(([, t]) => t.at <= end).sort((a, b) => a[1].at - b[1].at)[0];
        if (!due) break;
        timers.delete(due[0]); now = due[1].at; due[1].fn();
      }
      now = end;
    },
  };
}
/** A trigger's handlers that note what happened. */
function spy(rect) {
  const s = { isOpen: false, opened: 0, closed: 0 };
  s.h = { open: () => { s.isOpen = true; s.opened++; }, close: () => { s.isOpen = false; s.closed++; }, rect, isOpen: () => s.isOpen };
  return s;
}
const eq = (a, b, why) => { if (a !== b) throw new Error(`${why}: expected ${b}, got ${a}`); };

const cases = {
  "constants are the accepted numbers"() {
    eq([H.TIP_OPEN, H.TIP_CLOSE, H.TIP_NEXT].join(), "400,150,100", "tooltip");
    eq([H.CARD_OPEN, H.CARD_CLOSE].join(), "600,300", "card");
    eq([H.MENU_OPEN, H.MENU_CLOSE, H.MENU_NEXT].join(), "200,300,80", "menu");
  },
  "card: opens after 600 ms, not before"() {
    const c = clock(), g = H.hoverGroup("card", c), a = spy();
    g.enter("a", a.h); c.tick(599); eq(a.isOpen, false, "at 599"); c.tick(1); eq(a.isOpen, true, "at 600");
  },
  "card: closes 300 ms after leaving, not before"() {
    const c = clock(), g = H.hoverGroup("card", c), a = spy();
    g.enter("a", a.h); c.tick(600); g.leave("a"); c.tick(299); eq(a.isOpen, true, "at 299"); c.tick(1); eq(a.isOpen, false, "at 300");
  },
  "card: leaving before it opened cancels the open"() {
    const c = clock(), g = H.hoverGroup("card", c), a = spy();
    g.enter("a", a.h); c.tick(300); g.leave("a"); c.tick(2000); eq(a.opened, 0, "opened");
  },
  "card: moving onto the card keeps it; leaving the card closes it after 300 ms"() {
    const c = clock(), g = H.hoverGroup("card", c), a = spy();
    g.enter("a", a.h); c.tick(600); g.leave("a"); c.tick(200); g.panelEnter(); c.tick(5000); eq(a.isOpen, true, "on the card");
    g.panelLeave(); c.tick(299); eq(a.isOpen, true, "299 after the card"); c.tick(1); eq(a.isOpen, false, "300 after the card");
  },
  "card: coming back to the trigger inside the grace keeps it"() {
    const c = clock(), g = H.hoverGroup("card", c), a = spy();
    g.enter("a", a.h); c.tick(600); g.leave("a"); c.tick(250); g.enter("a", a.h); c.tick(5000); eq(a.isOpen, true, "open"); eq(a.opened, 1, "opened once");
  },
  "card: a neighbour card waits the full 600 ms"() {
    const c = clock(), g = H.hoverGroup("card", c), a = spy(), b = spy();
    g.enter("a", a.h); c.tick(600); g.leave("a"); g.enter("b", b.h); c.tick(599); eq(b.isOpen, false, "b at 599"); c.tick(1); eq(b.isOpen, true, "b at 600"); eq(a.isOpen, false, "a shut for b");
  },
  "card: Esc closes at once and it stays shut until the pointer has left"() {
    const c = clock(), g = H.hoverGroup("card", c), a = spy();
    g.enter("a", a.h); c.tick(600); eq(g.dismiss(), true, "dismissed"); eq(a.isOpen, false, "shut at once");
    g.enter("a", a.h); c.tick(5000); eq(a.isOpen, false, "not again while the pointer stays");
    g.leave("a"); g.enter("a", a.h); c.tick(600); eq(a.isOpen, true, "again after leaving");
  },
  "card: keyboard focus opens with no delay; blur closes at once"() {
    const c = clock(), g = H.hoverGroup("card", c), a = spy();
    g.focus("a", a.h); eq(a.isOpen, true, "no tick"); g.blur("a"); eq(a.isOpen, false, "blur");
  },
  "menu: opens after 200 ms, not before"() {
    const c = clock(), g = H.hoverGroup("menu", c), a = spy();
    g.enter("a", a.h); c.tick(199); eq(a.isOpen, false, "at 199"); c.tick(1); eq(a.isOpen, true, "at 200");
  },
  "menu: closes 300 ms after leaving, not before"() {
    const c = clock(), g = H.hoverGroup("menu", c), a = spy();
    g.enter("a", a.h); c.tick(200); g.leave("a"); c.tick(299); eq(a.isOpen, true, "at 299"); c.tick(1); eq(a.isOpen, false, "at 300");
  },
  "menu: a neighbour opens 80 ms after the pointer reaches it while one is open"() {
    const c = clock(), g = H.hoverGroup("menu", c), a = spy(), b = spy();
    g.enter("a", a.h); c.tick(200); g.leave("a"); g.enter("b", b.h); c.tick(79); eq(b.isOpen, false, "b at 79");
    c.tick(1); eq(b.isOpen, true, "b at 80"); eq(a.isOpen, false, "a shut when b opened"); c.tick(5000); eq(b.isOpen, true, "b stays");
  },
  "menu: with none open a menu still waits 200 ms"() {
    const c = clock(), g = H.hoverGroup("menu", c), a = spy(), b = spy();
    g.enter("a", a.h); c.tick(200); g.leave("a"); c.tick(300); eq(a.isOpen, false, "a shut");
    g.enter("b", b.h); c.tick(199); eq(b.isOpen, false, "b at 199"); c.tick(1); eq(b.isOpen, true, "b at 200");
  },
  "menu: the pointer on the list keeps it; leaving the list closes after 300 ms"() {
    const c = clock(), g = H.hoverGroup("menu", c), a = spy();
    g.enter("a", a.h); c.tick(200); g.leave("a"); c.tick(250); g.panelEnter(); c.tick(5000); eq(a.isOpen, true, "on the list");
    g.panelLeave(); c.tick(300); eq(a.isOpen, false, "closed");
  },
  "menu: a diagonal move inside the safe triangle does not close it"() {
    const c = clock(), g = H.hoverGroup("menu", c), box = { left: 100, top: 0, right: 200, bottom: 100 }, a = spy(() => box);
    g.enter("a", a.h); c.tick(200); g.leave("a", { x: 10, y: 10 });
    for (const p of [{ x: 30, y: 20 }, { x: 50, y: 30 }, { x: 70, y: 40 }, { x: 90, y: 50 }]) { c.tick(250); g.move(p); eq(a.isOpen, true, `still open at ${p.x}`); }
    c.tick(250); eq(a.isOpen, true, "open before the grace is up"); g.panelEnter(); c.tick(5000); eq(a.isOpen, true, "stays once on the list");
  },
  "menu: a move outside the safe triangle closes it after 300 ms"() {
    const c = clock(), g = H.hoverGroup("menu", c), box = { left: 100, top: 0, right: 200, bottom: 100 }, a = spy(() => box);
    g.enter("a", a.h); c.tick(200); g.leave("a", { x: 10, y: 10 });
    c.tick(250); g.move({ x: 10, y: 400 }); c.tick(49); eq(a.isOpen, true, "49 after the last move in time"); c.tick(1); eq(a.isOpen, false, "closed");
  },
  "menu: Esc closes at once"() {
    const c = clock(), g = H.hoverGroup("menu", c), a = spy();
    g.enter("a", a.h); c.tick(200); eq(g.dismiss(), true, "dismissed"); eq(a.isOpen, false, "shut");
  },
  "menu: Esc while waiting to open cancels the open"() {
    const c = clock(), g = H.hoverGroup("menu", c), a = spy();
    g.enter("a", a.h); c.tick(100); g.dismiss(); c.tick(1000); eq(a.opened, 0, "opened");
  },
  "menu: keyboard focus opens with no delay"() {
    const c = clock(), g = H.hoverGroup("menu", c), a = spy();
    g.focus("a", a.h); eq(a.isOpen, true, "no tick");
  },
  "menu: only one is open at a time"() {
    const c = clock(), g = H.hoverGroup("menu", c), a = spy(), b = spy();
    g.focus("a", a.h); g.focus("b", b.h); eq(a.isOpen, false, "a"); eq(b.isOpen, true, "b"); eq(g.current, "b", "current");
  },
  "release: the keyboard has taken the menu, so the pointer leaving no longer closes it"() {
    const c = clock(), g = H.hoverGroup("menu", c), a = spy();
    g.enter("a", a.h); c.tick(200); g.release("a"); g.leave("a"); c.tick(5000);
    eq(a.isOpen, true, "still open"); eq(a.closed, 0, "never closed"); eq(g.current, null, "the group let go");
  },
  "release: the pointer leaving and coming back does not claim the menu again"() {
    const c = clock(), g = H.hoverGroup("menu", c), a = spy();
    g.enter("a", a.h); c.tick(200); g.release("a"); g.leave("a"); c.tick(100); g.enter("a", a.h); c.tick(200); g.leave("a"); g.enter("a", a.h); c.tick(5000);
    eq(a.isOpen, true, "still open"); eq(a.closed, 0, "never closed"); eq(g.current, null, "still the keyboard's");
  },
  "release: once the menu has closed, the pointer opens it again as usual"() {
    const c = clock(), g = H.hoverGroup("menu", c), a = spy();
    g.enter("a", a.h); c.tick(200); g.release("a"); a.h.close(); g.leave("a"); g.enter("a", a.h); c.tick(200); eq(a.isOpen, true, "open again after 200 ms");
  },
  "release: Esc is no longer the group's once released"() {
    const c = clock(), g = H.hoverGroup("menu", c), a = spy();
    g.enter("a", a.h); c.tick(200); g.release("a"); eq(g.dismiss(), false, "nothing for the group to dismiss"); eq(a.isOpen, true, "left open for the menu's own Esc");
  },
  "release: drops a hover open still waiting (a click came first)"() {
    const c = clock(), g = H.hoverGroup("menu", c), a = spy();
    g.enter("a", a.h); c.tick(100); g.release("a"); c.tick(2000); eq(a.opened, 0, "opened");
  },
  "safe triangle geometry"() {
    const r = { left: 100, top: 0, right: 200, bottom: 100 }, [p, q, s] = H.safeTriangle({ x: 10, y: 10 }, r);
    eq(H.inTriangle({ x: 60, y: 30 }, p, q, s), true, "inside"); eq(H.inTriangle({ x: 60, y: 300 }, p, q, s), false, "outside");
  },
};

const out = {};
for (const [name, fn] of Object.entries(cases)) { try { fn(); out[name] = "ok"; } catch (e) { out[name] = String(e.message || e); } }
console.log(JSON.stringify(out));
