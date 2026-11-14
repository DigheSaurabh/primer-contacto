# Status

Updated Nov 14, 2026. Update this file at the end of every working session.

## Where things stand

- **Intake:** Form A, Form B and the Request Log are built ([tutorial](tutorial.md)). An earlier version was set up and tested in Google on Nov 12; it collected client names, so it was reworked on Nov 14 to match [schema.md](schema.md). The new version needs one more setup and test run.
- **Synthetic data:** generator and two data files are in the repo. `validate.py` isn't written yet.
- **Next gate:** Gate 2, Nov 20, 2026: public app with every metric.

## Done

- Repo, README, metrics dictionary, schema (Week 1)
- Problem framing, proto-persona (interactive card: https://claude.ai/artifact/D2UeN2FDon8foiqUMjPHR7)
- Intake forms script, matching schema.md (`intake/`)
- Synthetic data generator and data (`generate_synthetic.py`, `data/`)
- Tutorial for setup, daily use and testing (`docs/tutorial.md`)

## Open items

- [ ] Re-run setup with the new script and repeat the checks in the tutorial, including on a phone
- [ ] Write `validate.py` (rules in schema.md); it should catch every row in `data/*.issues.json`
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
