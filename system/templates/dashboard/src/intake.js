// @ts-check
/* intake.js: retired in 2.6.0 (#232 C2). The old Intake page (its sections, Calendar import, the upload table) is gone: the one Intake page is
   components/intakeReview/, and what it and Today share with the server is core/intakeApi.js. This empty shell only re-exports that module so a
   stray import keeps working; nothing imports it. It is deleted in a later release (Q12: thin now, delete after). */
export * from "./core/intakeApi.js";
