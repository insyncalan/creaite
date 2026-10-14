// @ts-check
/* core/state.js (BL-231 step 2b): the page's shared state, one object: `shared`.

   An ES module's top-level bindings are read-only to the modules that import them, so a top-level `let` that code
   outside its own module reads or assigns lives here instead, as shared.X. (It is called `shared`, not `st`, because `st` is a local name for a status in
   about 70 places.) Its owner sets its first value where the `let`
   used to be (`let VIEW="today"` became `shared.VIEW="today"`), and every module reads and writes shared.X.

   The fields are listed once, by owner. core/globals.js puts an accessor for each field on window (window.VIEW reads and
   writes shared.VIEW), for the tests. The list was measured on 13-10-2026 (a top-level `let` named outside its own
   module, or by a test); since every area became a module (BL-231 step 2b), every module reads and writes them as
   shared.X. */
export const shared = {
  // core/page.js: set where its `let` was
  LOADING: undefined,
  // core/data.js: set where its `let` was
  ACT: undefined, REG: undefined,
  // core/server.js: set where its `let` was
  DATA_AT: undefined, DIAGSENT: undefined, HELD: undefined, LIVE: undefined, LIVELINK: undefined, PENDING: undefined,
  UNDO: undefined, VQ: undefined, VSTATE: undefined, VW: undefined,
  // core/nav.js: set where its `let` was
  COCK: undefined, FROMPROJ: undefined, NAVSTATE: undefined, PERSON: undefined, VIEW: undefined,
  // core/fields.js: set where its `let` was
  CAL: undefined, CI: undefined, COMBO: undefined,
  // rail: set where its `let` was
  RAILCFG: undefined,
  // projects: set where its `let` was
  CURED: undefined, CURRD: undefined, DRH: undefined, EV: undefined, GEN: undefined, PDBASE: undefined,
  PDKEY: undefined, PDOFFER: undefined, PDT: undefined, PKDRC: undefined, PREPDAY: undefined, PREPEV: undefined, PREPPEEK: undefined,
  // work: set where its `let` was
  CE: undefined, COLORD: undefined, COLVIS: undefined, CR: undefined, DR: undefined, FPK: undefined, FPQ: undefined,
  HLA: undefined, HLALL: undefined, HLC: undefined, LAYCHOSEN: undefined, MKEYHELD: undefined, PTAB: undefined,
  RVA: undefined, RZ: undefined, SAVED: undefined, SEL: undefined, WQ: undefined, WT: undefined, WVIEW: undefined,
  XCQ: undefined,
  // panel: set where its `let` was
  CUR: undefined, DRF: undefined, EDITING: undefined, PKNT: undefined, PKPOP: undefined, PKQ: undefined, PKSRC: undefined,
  // milestones: set where its `let` was
  MSCODE: undefined, MSNEXT: undefined, MV: undefined, MVAUD: undefined, MVQ: undefined, MVREADY: undefined,
  STALE: undefined,
  // review: set where its `let` was
  MNEWIO: undefined, MREVLEFT: undefined, RF: undefined, RSEL: undefined, RVLEFT: undefined, RVSTATS: undefined,
  RV_MAX: undefined,
  // files: set where its `let` was
  FBUSY: undefined, FLAST: undefined, FSEL: undefined, FSELFILE: undefined,
  // activity: set where its `let` was
  ACTF: undefined,
  // settings: set where its `let` was
  HAND: undefined, MCREATED: undefined, MCREATEDOF: undefined, PKDONE: undefined, PKS: undefined, PKSEQ: undefined,
  PSORT: undefined, SCAT: undefined, SETROW: undefined, SQ: undefined, WSNEW: undefined,
  // ask: set where its `let` was
  AC: undefined, ASKCHAT: undefined, ASKQ: undefined, ASKSESSION: undefined, BUSY: undefined, CK: undefined,
  CKI: undefined, CKPICK: undefined, IMGURL: undefined, PIMG: undefined, QDECK: undefined, QNOW: undefined,
  RBMARKED: undefined, RBOUT: undefined, RUN: undefined, RUNLABEL: undefined, SHOWN: undefined,
  // meetings: set where its `let` was
  MEETING: undefined, PREPRUN: undefined, QCT: undefined,
  // help: set where its `let` was
  HELPARG: undefined,
  // drafts: set where its `let` was
  DE: undefined,
  // main: the start-up (HASH0, the address as opened; HADHASH, whether the page opened on an address)
  HADHASH: undefined, HASH0: undefined,
};
