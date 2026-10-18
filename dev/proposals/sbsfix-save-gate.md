# sbsfix: refuse client-gate findings at the client draft save (proposal, not done)

Context: Team Cap's provisional verdict on editable Side by side (#135 comment 6254920560), finding 1. v2.5.0 now runs the client gate
in the page BEFORE Match internal copies (`stores/clientReport.js` `matchInternal`, `POST /api/report/match-check`), so the draft no
longer receives internal words from that route.

Not done on the server: making `report_doc.save_draft` / `/api/report/save` refuse or strip a client document that has
`client_leak.findings`. It is not small and safe: `make_safe` can only drop item references, there is no safe "strip" of free text, and
refusing a save on any finding would stop Alan saving work in progress (a client draft that names an owner while he rewrites it) and
would change the Approve and export rules (they refuse, with the findings listed, and that is the intended place). It also touches
`report_doc.save_draft`, which other suites pin.

Option if Alan wants the belt and braces: save still succeeds, but the answer carries `findings` and the draft is marked
`meta.unsafe = true`, which the page shows as a banner and which `/api/report/export` and `/approve` already refuse on. No behaviour is
weakened. Needs `report_doc.save_draft` (not guarded) and a test in test_client_gate.py.
