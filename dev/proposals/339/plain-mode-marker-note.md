# Plain mode and the mail-check marker (askStream, ask.js)

Checked, no change needed. A typed "refresh calendar" starts as a guess (`plain = "guess"`: drawn plainly). The first step event settles it: only a first step equal to `MC_MARKER` flips it to a mail check (`plain = false`); any other first step keeps it plain. A mail-check object is only made when `!plain`, so a later `MC_MARKER` step in a plain run is ignored and the run cannot end as a mail check.

A plain run that never gets a step (error, stop or an immediate done) leaves `mc` null, so `mcFinish` does nothing; the run ends through the ordinary path (outcome, `askFinished`, retry offer). Nothing waits for a marker.

The one marker-only rule is deliberate: the server writes the marker as the first step of a sweep it runs, and a calendar run's first step is never that text.
