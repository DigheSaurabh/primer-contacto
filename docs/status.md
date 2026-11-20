# Status

Updated Nov 20, 2026. Update this file at the end of every working session.

## Where things stand

- **Intake:** Form A, Form B and the Request Log are built ([tutorial](tutorial.md)). The no-names version was set up in Google on Nov 18. On Nov 18 a `teacher_id` field was added so all pilot teachers share one set of forms; this version needs one more setup and test run.
- **Synthetic data:** generator and two data files are in the repo. `validate.py` isn't written yet.
- **Next gate:** Gate 2, Nov 20, 2026: public app with every metric.

## Done

- Repo, README, metrics dictionary, schema (Week 1)
- Problem framing, proto-persona (interactive card: https://claude.ai/artifact/D2UeN2FDon8foiqUMjPHR7)
- Intake forms script, matching schema.md (`intake/`)
- Synthetic data generator and data (`generate_synthetic.py`, `data/`)
- Tutorial for setup, daily use and testing (`docs/tutorial.md`)

## Pipeline (Nov 20)

`validate.py`, `transform.py`, `metrics.py` (one function per metric) and `run_pipeline.py` run end to end on the synthetic data, with 20 passing tests. Validation catches every planted problem. Results describe the generator's assumptions, not real teachers.

## Open items

- [ ] Paste the teacher-field script, put the real teacher names in `CONFIG.teachers` (Apps Script only), run `resetSetup` + `setup`, and repeat the checks in the tutorial, including on a phone
- [ ] From now on, apply code changes with `updateForms` (links stay the same); lock the forms before the pilot
- [ ] Tell Dr. Drury about the new `teacher_id` field and the reply question in Form A
- [ ] Later (dbt layer): daily one-tap reply links for unanswered requests; count a request as replied when a later stage exists without a reply time, with the time marked unknown
- [x] `validate.py`, `transform.py`, `metrics.py`, `run_pipeline.py` and tests (Nov 20)
- [ ] Gate 1 status: confirm with Dr. Drury whether it was signed off
- [ ] Teacher interviews (`docs/interviews.md` is still empty) and 3 written pilot agreements
- [ ] Send the weekly status update
- [ ] Update the proto-persona card's KPI list to the 12 metrics in metrics.md
- [ ] Gate 2 (Nov 20): `transform.py`, `metrics.py` with tests, Streamlit app

## Weekly log

| Week | Ending | Done |
|---|---|---|
| 1 | Nov 6 | Repo, README, metrics dictionary, schema |
| 2 | Nov 13 | Problem framing, proto-persona, intake forms built and tested |
| 3 | Nov 20 | Intake aligned to schema, synthetic data, tutorial |
