// BL-216, BL-217 (sprint-ui-sweep): measuring helpers injected into the page as window.AUD by test_ui_sweep.py (from the UI sweep audit).
window.AUD = (() => {
  const SEL = 'a[href],a[data-go],button,input:not([type=hidden]),select,textarea,summary,[role=button],[role=checkbox],[role=tab],[role=switch],[role=menuitem],[role=menuitemcheckbox],[role=option],[role=link],[role=radio],[role=slider],[role=separator][tabindex],[tabindex]:not([tabindex="-1"]),[contenteditable="true"],[contenteditable=""]';
  const vis = e => {
    const r = e.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) return false;
    if (e.closest('[hidden],[inert]')) return false;
    const s = getComputedStyle(e);
    if (s.visibility === 'hidden') return false;
    // clipped away (visually hidden helpers)
    if (s.clipPath && s.clipPath !== 'none' && r.width <= 2) return false;
    let p = e.parentElement;
    while (p) { const ps = getComputedStyle(p); if (ps.display === 'none') return false; p = p.parentElement; }
    return true;
  };
  const zone = e => e.closest('.rail') ? 'rail' : e.closest('header.bar') ? 'header' : e.closest('#chat') ? 'ask' : e.closest('#panel') ? 'panel'
    : e.closest('dialog[open]') ? 'dialog' : e.closest('.view') ? 'view' : 'other';
  const cls = e => [...e.classList].filter(c => !/^(on|active|sel|selected|open|hov|focus|cur|now|past|dirty|busy)$/.test(c)).slice(0, 3);
  const sig = e => {
    const tag = e.tagName.toLowerCase();
    let me = tag;
    if (e.id && !/\d{2,}/.test(e.id)) me += '#' + e.id;
    else {
      const c = cls(e); if (c.length) me += '.' + c.join('.');
      const da = [...e.attributes].map(a => a.name).filter(n => n.startsWith('data-') && !/^data-(tip|n|i|id|row|k|v|key|code)$/.test(n)).slice(0, 1);
      if (da.length) me += '[' + da[0] + ']';
      if (tag === 'input') me += `[type=${e.type}]`;
      if (!e.classList.length && !da.length) { const role = e.getAttribute('role'); if (role) me += `[role=${role}]`; }
    }
    if (me.includes('#')) return me;
    let p = e.parentElement, ctx = '';
    while (p && p !== document.body) {
      if (p.id && !/\d{2,}/.test(p.id)) { ctx = '#' + p.id; break; }
      p = p.parentElement;
    }
    let mid = '';
    const par = e.parentElement;
    if (par && par.id === '' && par.classList.length && !(ctx && par === p)) mid = '.' + [...par.classList][0] + ' ';
    return (ctx ? ctx + ' ' : '') + mid + me;
  };
  const faded = e => { let p = e; while (p && p !== document.body) { if (+getComputedStyle(p).opacity < 0.05) return true; p = p.parentElement; } return false; };
  const label = e => (e.getAttribute('aria-label') || e.getAttribute('title') || e.dataset.tip || e.textContent || e.value || e.placeholder || '').trim().replace(/\s+/g, ' ').slice(0, 40);
  const targets = root => {
    const set = new Set([...document.querySelectorAll(SEL)]);
    // delegated click targets: the topmost element with a pointer cursor
    for (const e of document.querySelectorAll('body *')) {
      if (set.has(e)) continue;
      const s = getComputedStyle(e);
      if (s.cursor !== 'pointer' && s.cursor !== 'col-resize' && s.cursor !== 'ew-resize') continue;
      const ps = e.parentElement && getComputedStyle(e.parentElement);
      if (ps && ps.cursor === s.cursor) continue;
      if (e.closest(SEL)) continue;
      if (e.tagName === 'LABEL') continue;
      set.add(e);
    }
    const out = [];
    for (const e of set) {
      if (!vis(e)) continue;
      // a child of another target (e.g. a span inside a button) is part of that target
      let anc = e.parentElement, inner = false;
      while (anc) { if (set.has(anc) && anc.tagName !== 'LABEL') { inner = true; break; } anc = anc.parentElement; }
      if (inner && !e.matches('input,button,select,textarea,a[href]')) continue;
      out.push(e);
    }
    return out;
  };
  const effRect = e => {
    let r = e.getBoundingClientRect();
    let lab = null;
    if (e.matches('input[type=checkbox],input[type=radio],input[type=file],input[type=color]')) lab = e.closest('label') || (e.id && document.querySelector(`label[for="${CSS.escape(e.id)}"]`));
    if (!lab && typeof TICK24 === 'string' && e.matches('input[type=checkbox]') && e.parentElement && e.parentElement.matches(TICK24)) {
      const h = e.parentElement.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2;
      const L = Math.max(h.left, cx - 12), R = Math.min(h.right, cx + 12), T = Math.max(h.top, cy - 12), B = Math.min(h.bottom, cy + 12);
      return { r: { left: L, right: R, top: T, bottom: B, width: R - L, height: B - T }, via: 'tick24' };
    }
    if (lab && vis(lab)) { const l = lab.getBoundingClientRect(); if (l.width * l.height > r.width * r.height) return { r: l, via: 'label' }; }
    return { r, via: '' };
  };
  const inline = e => {
    if (!e.matches('a')) return false;
    if (getComputedStyle(e).display !== 'inline') return false;
    const p = e.parentElement; if (!p) return false;
    const txt = (p.textContent || '').trim(), mine = (e.textContent || '').trim();
    return txt.length > mine.length + 15;
  };
  function sizes(scopeSel) {
    const all = targets().map(e => ({ e, ...effRect(e) }));
    const rows = [];
    const small = all.filter(t => t.r.width < 23.5 || t.r.height < 23.5);
    const cx = r => ({ x: r.left + r.width / 2, y: r.top + r.height / 2 });
    const distRect = (c, r) => { const dx = Math.max(r.left - c.x, 0, c.x - r.right), dy = Math.max(r.top - c.y, 0, c.y - r.bottom); return Math.hypot(dx, dy); };
    for (const t of small) {
      const z = zone(t.e);
      if (scopeSel && !(t.e.closest(scopeSel) || ['dialog', 'other'].includes(z) || (scopeSel === '#panel' && z === 'panel') || (scopeSel === '#chat' && z === 'ask'))) {
        if (!['rail', 'header'].includes(z)) continue;
      }
      const c = cx(t.r);
      let spaced = true, near = null;
      for (const o of all) {
        if (o === t || o.e.contains(t.e) || t.e.contains(o.e)) continue;
        const osmall = o.r.width < 23.5 || o.r.height < 23.5;
        const dd = osmall ? Math.hypot(c.x - cx(o.r).x, c.y - cx(o.r).y) : distRect(c, o.r) + 12;
        if (dd < 24 - 0.01) { spaced = false; near = o.e; break; }
      }
      rows.push({
        zone: z, sig: sig(t.e), label: label(t.e), w: Math.round(t.r.width * 10) / 10, h: Math.round(t.r.height * 10) / 10,
        via: t.via, spaced, inline: inline(t.e), disabled: !!t.e.disabled || t.e.getAttribute('aria-disabled') === 'true',
        near: near ? sig(near) : '', faded: faded(t.e), tag: t.e.tagName.toLowerCase(), type: t.e.type || t.e.getAttribute('role') || ''
      });
    }
    return { total: all.length, rows };
  }
  // ---------- reflow ----------
  function reflow(scopeSel) {
    const W = innerWidth, H = innerHeight;
    const doc = document.scrollingElement;
    const res = { W, pageX: doc.scrollWidth - doc.clientWidth, rail: Math.round((document.querySelector('.rail') || { getBoundingClientRect: () => ({ width: 0 }) }).getBoundingClientRect().width) };
    const scope = document.querySelector(scopeSel);
    const cont = scopeSel.startsWith('#v-') ? scope : scope;
    res.scopeX = scope ? Math.max(0, scope.scrollWidth - scope.clientWidth) : 0;
    res.scopeW = scope ? Math.round(scope.getBoundingClientRect().width) : 0;
    // culprits: elements that run past the scope's right edge (or the window), not inside an inner horizontal scroller
    const sr = scope ? scope.getBoundingClientRect() : { left: 0, right: W };
    const right = Math.min(sr.right, W);
    const scroller = el => { let p = el.parentElement; while (p && p !== scope) { const s = getComputedStyle(p); if (/(auto|scroll|hidden|clip)/.test(s.overflowX) && p.scrollWidth > p.clientWidth + 1) return p; p = p.parentElement; } return null; };
    const culprits = [];
    if (scope) for (const e of scope.querySelectorAll('*')) {
      const r = e.getBoundingClientRect(); if (r.width < 1 || r.height < 1) continue;
      if (r.right <= right + 1) continue;
      if (!vis(e)) continue;
      const sc = scroller(e);
      const pr = e.parentElement.getBoundingClientRect();
      if (pr.right > right + 1 && e.parentElement !== scope) continue; // report the outermost one
      culprits.push({ sig: sig(e), over: Math.round(r.right - right), w: Math.round(r.width), inner: sc ? sig(sc) : '' });
    }
    // de-dupe by sig
    const cmap = {}; for (const c of culprits) { const k = c.sig + '|' + c.inner; if (!cmap[k] || cmap[k].over < c.over) cmap[k] = { ...c, n: (cmap[k] ? cmap[k].n : 0) + 1 }; else cmap[k].n++; }
    res.culprits = Object.values(cmap).sort((a, b) => b.over - a.over).slice(0, 12);
    // inner horizontal scrollers (acceptable for tables, but note them)
    res.inner = [];
    if (scope) for (const e of [scope, ...scope.querySelectorAll('*')]) {
      if (e === scope) continue;
      const s = getComputedStyle(e);
      if (/(auto|scroll)/.test(s.overflowX) && e.scrollWidth > e.clientWidth + 1 && vis(e)) res.inner.push({ sig: sig(e), by: e.scrollWidth - e.clientWidth });
    }
    // clipped text: own text, overflow hidden, wider content, no ellipsis
    const clip = {};
    if (scope) for (const e of scope.querySelectorAll('*')) {
      if (![...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) continue;
      const s = getComputedStyle(e);
      if (!/(hidden|clip)/.test(s.overflowX) && !/(hidden|clip)/.test(s.overflow)) continue;
      if (e.scrollWidth <= e.clientWidth + 1 && e.scrollHeight <= e.clientHeight + 2) continue;
      if (!vis(e)) continue;
      const k = sig(e); const ell = s.textOverflow === 'ellipsis' || +s.webkitLineClamp > 0;
      if (!clip[k]) clip[k] = { sig: k, n: 0, ell, by: 0, text: (e.textContent || '').trim().slice(0, 40) };
      clip[k].n++; clip[k].by = Math.max(clip[k].by, e.scrollWidth - e.clientWidth, e.scrollHeight - e.clientHeight);
    }
    res.clipped = Object.values(clip);
    // controls covered by something else, or unreachable (clipped by an overflow:hidden ancestor / off screen)
    const cov = {}, unr = {};
    const ts = targets().filter(e => !scope || scope.contains(e));
    for (const e of ts) {
      e.scrollIntoView({ block: 'center', inline: 'center' });
      if (typeof xcueAll === 'function') xcueAll();   // the "more columns" cue follows a scroll on the next frame; measure what a person sees
      const r = e.getClientRects()[0] || e.getBoundingClientRect(); const x = r.left + r.width / 2, y = r.top + r.height / 2;   // a link that wraps: the middle of its first line
      let bad = x < 0 || x > W || y < 0 || y > H;
      let p = e.parentElement; while (!bad && p && p !== document.body) { const s = getComputedStyle(p); if (s.overflowX !== 'visible' || s.overflowY !== 'visible') { const pr = p.getBoundingClientRect(); if (x < pr.left - 1 || x > pr.right + 1 || y < pr.top - 1 || y > pr.bottom + 1) bad = true; } p = p.parentElement; }
      const k = sig(e);
      if (bad) { (unr[k] = unr[k] || { sig: k, n: 0, label: label(e) }).n++; continue; }
      const hit = document.elementFromPoint(x, y);
      if (hit && !(hit === e || e.contains(hit) || hit.contains(e) || (e.closest('label') && e.closest('label').contains(hit)))) {
        (cov[k] = cov[k] || { sig: k, n: 0, by: sig(hit), label: label(e) }).n++;
      }
    }
    res.covered = Object.values(cov); res.unreachable = Object.values(unr);
    if (scope) scope.scrollTo(0, 0); scrollTo(0, 0);
    document.querySelectorAll('.view').forEach(v => v.scrollTo(0, 0));
    return res;
  }
  // ---------- forced colours ----------
  const alpha = c => { const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return 1; const p = m[1].split(',').map(Number); return p.length > 3 ? p[3] : 1; };
  const bgOf = e => { let p = e; while (p) { const c = getComputedStyle(p).backgroundColor; if (alpha(c) > 0.05) return c.replace(/rgba\(([^,]+),([^,]+),([^,]+),[^)]+\)/, 'rgb($1,$2,$3)').replace(/\s/g, ''); p = p.parentElement; } return 'rgb(255,255,255)'; };
  const visibleBg = e => { const c = getComputedStyle(e).backgroundColor; if (alpha(c) < 0.05) return ''; const n = c.replace(/rgba\(([^,]+),([^,]+),([^,]+),[^)]+\)/, 'rgb($1,$2,$3)').replace(/\s/g, ''); return n === bgOf(e.parentElement || document.body) ? '' : n; };
  const edges = e => { const s = getComputedStyle(e); return ['Top', 'Right', 'Bottom', 'Left'].filter(k => parseFloat(s['border' + k + 'Width']) > 0 && s['border' + k + 'Style'] !== 'none' && alpha(s['border' + k + 'Color']) > 0.05).length; };
  const box = e => { const s = getComputedStyle(e); return { edges: edges(e), bg: visibleBg(e), shadow: s.boxShadow !== 'none', outline: s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) > 0 }; };
  function boxes(scopeSel) {
    const scope = document.querySelector(scopeSel), out = {};
    const ctl = 'a[href],a[data-go],a[data-nav],a[data-open],button,input:not([type=checkbox]):not([type=radio]):not([type=range]):not([type=hidden]),select,textarea,[role=button],[role=tab],[role=switch],[role=checkbox]:not(input),.chip,.vchip,.tag,.pill,.badge,.fsel';
    for (const e of document.querySelectorAll(ctl)) {
      if (scope && !scope.contains(e) && !e.closest('.rail,header.bar')) continue;
      if (!vis(e)) continue;
      const k = (e.closest('.rail,header.bar') ? 'shell: ' : '') + sig(e);
      if (!out[k]) out[k] = { sig: k, n: 0, el: e, label: label(e) };
      out[k].n++;
    }
    return out;
  }
  function stateSig(e) {
    const s = getComputedStyle(e), b = getComputedStyle(e, '::before'), a = getComputedStyle(e, '::after');
    const pe = x => x.content && x.content !== 'none' && x.content !== 'normal' && x.display !== 'none' ? [x.content, alpha(x.backgroundColor) > .05 && !/^rgba?\(255, 255, 255/.test(x.backgroundColor) ? x.backgroundColor : '', edges2(x), x.width, x.height].join('/') : '';
    const svg = e.querySelector('svg'); const ss = svg ? getComputedStyle(svg) : null;
    return [edges(e), s.borderTopColor, s.borderLeftColor, s.borderBottomWidth, s.outlineStyle, s.fontWeight, s.textDecorationLine, visibleBg(e), s.color, pe(b), pe(a), ss ? ss.fill + ss.stroke + ss.color : ''].join('|');
  }
  function edges2(x) { return ['Top', 'Right', 'Bottom', 'Left'].map(k => parseFloat(x['border' + k + 'Width']) > 0 && x['border' + k + 'Style'] !== 'none' ? x['border' + k + 'Color'] : '').join(','); }
  function states(scopeSel) {
    const scope = document.querySelector(scopeSel);
    const st = '[aria-current]:not([aria-current=false]),[aria-selected=true],[aria-pressed=true],[aria-checked=true]:not(input),[aria-expanded=true],.on:not(.panel):not(#chat):not(.peek),.active,.sel';
    const out = {};
    for (const e of document.querySelectorAll(st)) {
      if (scope && !scope.contains(e) && !e.closest('.rail,header.bar')) continue;
      if (!vis(e) || e.matches('dialog,.view,#panel,#chat,.panel,.menu,.pop')) continue;
      // a sibling of the same kind without the state
      const kind = x => x.tagName + '|' + (x.getAttribute('role') || '') + '|' + cls(x).join('.');
      const par = e.parentElement; if (!par) continue;
      const sib = [...par.parentElement ? par.parentElement.querySelectorAll(e.tagName) : []].find(x => x !== e && kind(x) === kind(e) && !x.matches(st) && vis(x));
      if (!sib) continue;
      const k = (e.closest('.rail,header.bar') ? 'shell: ' : '') + sig(e) + ' ' + ['aria-current', 'aria-selected', 'aria-pressed', 'aria-checked', 'aria-expanded'].filter(a => e.hasAttribute(a) && e.getAttribute(a) !== 'false').map(a => `[${a}]`).join('') + (e.matches('.on,.active,.sel') ? ' (.on/.active/.sel)' : '');
      if (out[k]) continue;
      out[k] = { sig: k, e, sib, label: label(e) };
    }
    return out;
  }
  function markers(scopeSel) {
    const scope = document.querySelector(scopeSel), out = {};
    for (const e of (scope || document).querySelectorAll('*')) {
      const r = e.getBoundingClientRect(); if (r.width < 3 || r.height < 3 || r.width > 18 || r.height > 18) continue;
      if ((e.textContent || '').trim() || e.querySelector('svg,img') || e.matches('svg,svg *,img,input')) continue;
      if (!vis(e)) continue;
      const s = getComputedStyle(e); if (alpha(s.backgroundColor) < .05 || edges(e)) continue;
      const k = sig(e); if (!out[k]) out[k] = { sig: k, n: 0, e, title: e.getAttribute('title') || e.getAttribute('aria-label') || '' }; out[k].n++;
    }
    return out;
  }
  return { sizes, reflow, boxes, states, markers, box, stateSig, sig, label, visibleBg, vis, targets, zone };
})();
