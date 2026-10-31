# Primer Contacto ("First Contact")

**A free, bilingual inquiry-to-booking pipeline tracker for independent wellness teachers.**
Built by Saurabh Prakash Dighe as a fellowship project with the [Chicago Education Advocacy Cooperative (ChiEAC)](https://chieac.org).

> 🔗 **Live app:** _coming in Week 4_
> 🎥 **Demo video:** _coming in Week 7_

---

## The problem
Independent yoga, Pilates and wellness teachers get requests through Instagram DMs, Linktree forms, texts and referrals. There is no CRM, no shared inbox, and no record of how fast they replied, where a request stalled, or why it was lost.

## What it does
Primer Contacto reads a teacher's request log (from a 2-minute intake form or a booking-tool CSV) and shows:
- How fast requests get answered, by channel
- Where requests get stuck in the pipeline
- Which sources and request types convert to bookings
- When demand peaks during the year
- How long it takes to get paid

English and Spanish labels throughout.

## Status
| Gate | Date | Status |
|---|---|---|
| Gate 1: Intake forms + validated synthetic data | Nov 6, 2026 | ⬜ |
| Gate 2: Public app with every metric | Nov 20, 2026 | ⬜ |
| Gate 3: Pilot confirmed + Power BI demo | Dec 4, 2026 | ⬜ |
| Gate 4: Handoff accepted by ChiEAC | Dec 11, 2026 | ⬜ |

## Tech stack
Google Forms & Sheets · Python (pandas, NumPy) · DuckDB (optional SQL layer) · Plotly · Streamlit · Streamlit Community Cloud · Faker · pytest · Power BI Desktop · GitHub

## Repository layout
```
primer-contacto/
├── app.py                  # Streamlit entry point (Week 4)
├── pages/                  # App pages (Week 4)
├── generate_synthetic.py   # Synthetic data generator (Week 2)
├── validate.py             # Schema and data-quality checks (Week 2)
├── transform.py            # Wide → long stage-transition table (Week 3)
├── metrics.py              # One function per KPI (Week 3)
├── labels.py               # English / Spanish labels (Week 4)
├── data/                   # Synthetic demo data only, never real pilot data
├── docs/
│   ├── metrics.md          # Metrics dictionary (the contract)
│   ├── schema.md           # Intake form fields and CSV schemas
│   └── interviews.md       # De-identified teacher interview notes
├── notebooks/              # Metric exploration (Week 3)
├── tests/                  # pytest tests and fixtures
└── powerbi/                # Power BI demo dashboard (Week 6)
```

## Run locally
```bash
git clone https://github.com/DigheSaurabh/primer-contacto.git
cd primer-contacto
python -m venv .venv
# Windows: .venv\Scripts\activate    Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
pytest
```

## Privacy
No client names, phone numbers, emails, handles or street addresses are collected anywhere: not in the forms, the Sheet, the app, the logs or this repository. Requests are identified only by a short ID. The app processes uploads in memory and stores nothing.

## Metric definitions
See [docs/metrics.md](docs/metrics.md).

## Later (out of scope for version 1)
- Phase 2: a human-reviewed model that suggests request type and urgency from the request note
- _Add ideas here instead of building them_

## Credits
Built by [Saurabh Prakash Dighe](https://www.linkedin.com/in/saurabh-dighe-9b84a637a/) with the Chicago Education Advocacy Cooperative and Dr. Benjamin M. Drury.

## License
[MIT](LICENSE)
