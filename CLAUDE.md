# Notes for Claude

Start every session by reading, in order:

1. `docs/status.md`: where the project stands and what's open
2. `docs/decisions.md`: decisions already made
3. `docs/metrics.md` and `docs/schema.md`: the contract. Don't change the stage model.

Rules:
- Never collect or commit client names, handles, phone numbers, emails or street addresses. Only synthetic data goes in `data/`.
- Update `docs/status.md` (and `docs/decisions.md` when something is decided) at the end of each session.
