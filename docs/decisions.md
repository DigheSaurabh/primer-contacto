# Decisions

Newest first: what was decided and why.

## Nov 18, 2026

- **One shared set of forms for all pilot teachers, with a `teacher_id` field.** Replaces "one setup per teacher" (Nov 14). Form A asks "Who are you?"; Form B sends each teacher to their own section, which lists only their open requests, and the script refuses an update to another teacher's request. One sheet makes teacher comparisons easy (the studio comparison view). *Schema change: tell Dr. Drury.*
- **Teacher names are never stored or committed.** The sheet and the repo hold codes (`T1`…`T4`); the names live only in `CONFIG.teachers` in the Apps Script copy, matching the de-identified interviews (Teacher A, Teacher B).

## Nov 14, 2026

- **Intake follows schema.md exactly.** The Nov 12 version asked for client names and contacts, which breaks the README's privacy promise. It now asks for none, and uses schema.md's fields, choice lists and the date-plus-letter `request_id`.
- **The script assigns `request_id`** (for example `2026-11-14-A`, by received date) instead of the teacher typing it, and Form B picks it from a list of open requests. Same format as schema.md, fewer typos.
- **Choices are stored as codes** (`instagram_dm`, `declined_price`) and shown in English and Spanish, so the data doesn't depend on the form's language.
- **Computed `outcome` values:** `open`, `delivered_paid`, `lost`.
- **Skipped stages are never back-filled.** If someone logs Confirmed without a Replied date, the gap stays so `validate.py` can flag it.
- ~~**One setup per teacher.**~~ Replaced on Nov 18 by one shared setup with `teacher_id`.

## Nov 12, 2026

- **Primer Contacto doesn't replace inboxes.** It's the one place requests are logged and measured; no Instagram API or inbox integrations.
- **Proto-persona** built from the problem statement, not interviews; to validate in the interviews and pilot.
