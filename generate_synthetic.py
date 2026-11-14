"""Generate synthetic request logs for Primer Contacto.

Writes the wide CSV format from docs/schema.md (one row per request), so metrics.py and
validate.py can be built and tested before any teacher logs a real request.

    python generate_synthetic.py                         # 80 requests, 3-week pilot from 2026-11-16
    python generate_synthetic.py --n 400 --weeks 52 --start 2025-11-17 --out data/synthetic_year.csv
    python generate_synthetic.py --clean                 # no injected data-quality problems

Everything is invented. No names, handles, phone numbers, emails or addresses are generated.
A sidecar file <out>.issues.json lists the rows with deliberately injected problems, so
tests can check that validate.py catches each one.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import string
from datetime import datetime, timedelta
from pathlib import Path

COLUMNS = [
    "request_id", "received_at", "channel", "request_type", "language", "client_type", "event_zip",
    "replied_at", "quoted_at", "confirmed_at", "delivered_at", "invoiced_at", "paid_at",
    "lost_at", "lost_reason", "quoted_amount", "note",
]
STAGES = ["received", "replied", "quoted", "confirmed", "delivered", "invoiced", "paid"]

# channel: (share, median first-reply delay in hours)
CHANNELS = {
    "instagram_dm": (0.33, 14), "linktree_form": (0.13, 20), "text_message": (0.15, 4),
    "email": (0.10, 30), "referral": (0.13, 10), "phone_call": (0.05, 3),
    "in_person": (0.06, 1), "other": (0.05, 24),
}
# request_type: (share, client types, quote range USD)
TYPES = {
    "private_session": (0.34, ["individual"], (75, 140)),
    "small_group": (0.14, ["individual"], (90, 200)),
    "corporate_session": (0.12, ["company"], (250, 800)),
    "school_event": (0.07, ["school"], (200, 600)),
    "community_event": (0.08, ["nonprofit_community"], (100, 400)),
    "workshop": (0.10, ["studio", "nonprofit_community", "individual"], (60, 400)),
    "class_series": (0.11, ["individual", "studio"], (120, 300)),
    "other": (0.04, ["other", "individual"], (40, 150)),
}
CONTRACTED = {"company", "school", "nonprofit_community"}  # invoiced gigs (docs/metrics.md #11)
LOST_REASONS = {"no_reply_from_client": 0.42, "declined_price": 0.18, "scheduling_conflict": 0.18,
                "went_elsewhere": 0.12, "cancelled": 0.06, "other": 0.04}
CHICAGO_ZIPS = ["60601", "60605", "60607", "60608", "60609", "60612", "60614", "60616",
                "60618", "60622", "60623", "60625", "60629", "60632", "60640", "60647"]
NOTES = {
    "private_session": "Asked about a weekly private session", "small_group": "Group of 4 friends",
    "corporate_session": "Lunchtime session for a team", "school_event": "Wellness day for students",
    "community_event": "Free community class in the park", "workshop": "Weekend workshop",
    "class_series": "6-week beginner series", "other": "",
}


def pick(rng: random.Random, weights: dict):
    keys = list(weights)
    w = [v[0] if isinstance(v, tuple) else v for v in weights.values()]
    return rng.choices(keys, weights=w)[0]


def letters(i: int) -> str:
    out = ""
    while True:
        out = string.ascii_uppercase[i % 26] + out
        i = i // 26 - 1
        if i < 0:
            return out


def arrival(rng: random.Random, days: list[datetime]) -> datetime:
    """Busier Sun/Mon and Sep 15 – Oct 15; quieter in late November and December."""
    def weight(d: datetime) -> float:
        w = 1.4 if d.weekday() in (6, 0) else 0.8 if d.weekday() == 5 else 1.0
        if (d.month, d.day) >= (9, 15) and (d.month, d.day) <= (10, 15):
            w *= 1.8
        elif d.month == 12 or (d.month == 11 and d.day >= 20):
            w *= 0.6
        return w
    day = rng.choices(days, weights=[weight(d) for d in days])[0]
    return day.replace(hour=min(22, max(7, int(rng.gauss(15, 4)))), minute=rng.randrange(60))


def generate(n: int, start: datetime, weeks: int, seed: int, clean: bool):
    rng = random.Random(seed)
    as_of = start + timedelta(weeks=weeks)
    days = [start + timedelta(days=d) for d in range(weeks * 7)]

    rows = []
    for _ in range(n):
        received = arrival(rng, days)
        channel = pick(rng, CHANNELS)
        rtype = pick(rng, TYPES)
        client_type = rng.choice(TYPES[rtype][1])
        r = {c: "" for c in COLUMNS}
        r.update(received_at=received, channel=channel, request_type=rtype,
                 language=rng.choices(["en", "es", "both", "other"], weights=[55, 25, 18, 2])[0],
                 client_type=client_type, note=NOTES[rtype] if rng.random() < 0.6 else "")
        if client_type != "individual" and rng.random() < 0.8:
            r["event_zip"] = rng.choice(CHICAGO_ZIPS)

        # Path through the stages. About 8% never get a reply.
        path, t = [], received
        reply_h = None if rng.random() < 0.08 else CHANNELS[channel][1] * math.exp(rng.gauss(0, 0.9))
        lost_stage = None
        if reply_h is None:
            lost_stage = "received"
        else:
            t += timedelta(hours=reply_h)
            path.append(("replied", t))
            p_yes = 0.48 if reply_h <= 24 else 0.36 if reply_h <= 48 else 0.24
            p_yes += 0.12 if channel == "referral" else 0
            if rng.random() < 0.85:
                t += timedelta(hours=rng.uniform(0, 30))
                path.append(("quoted", t))
                r["quoted_amount"] = max(20, round(rng.uniform(*TYPES[rtype][2]), -1))
                if rng.random() < p_yes / 0.85:
                    t += timedelta(days=rng.uniform(0.2, 5))
                    path.append(("confirmed", t))
                    t += timedelta(days=rng.uniform(1, 12))
                    path.append(("delivered", t))
                    if client_type in CONTRACTED:
                        t += timedelta(hours=rng.uniform(2, 72))
                        path.append(("invoiced", t))
                        t += timedelta(days=rng.expovariate(1 / 12))  # net terms: slower
                    else:
                        t += timedelta(days=rng.expovariate(1 / 1.5))  # paid around the session
                    path.append(("paid", t))
                else:
                    lost_stage = "quoted"
            else:
                lost_stage = "replied"

        last = received
        for stage, when in path:
            if when > as_of:
                break
            r[f"{stage}_at"] = when
            last = when

        # Lost: the teacher records it some days after the request goes quiet or the client says no.
        if lost_stage and not r["confirmed_at"]:
            lost_when = last + timedelta(days=rng.uniform(1, 14))
            if lost_when <= as_of and rng.random() < 0.85:
                r["lost_at"] = lost_when
                r["lost_reason"] = ("no_reply_from_client" if lost_stage == "received"
                                    else pick(rng, LOST_REASONS))
        rows.append(r)

    rows.sort(key=lambda x: x["received_at"])
    per_day: dict[str, int] = {}
    for r in rows:
        day = r["received_at"].strftime("%Y-%m-%d")
        r["request_id"] = f"{day}-{letters(per_day.get(day, 0))}"
        per_day[day] = per_day.get(day, 0) + 1

    issues = {"duplicate_request_id": [], "dates_out_of_order": [], "stage_after_lost": []}
    if not clean and len(rows) >= 20:
        # The same request logged twice
        src = rng.choice(rows[:-5])
        rows.append(dict(src))
        issues["duplicate_request_id"].append(src["request_id"])
        # Paid typed before delivered
        done = [r for r in rows if r["paid_at"] and r["delivered_at"]]
        if done:
            r = rng.choice(done)
            r["paid_at"] = r["delivered_at"] - timedelta(days=2)
            issues["dates_out_of_order"].append(r["request_id"])
        # A reply logged after the request was marked lost
        lost = [r for r in rows if r["lost_at"] and not r["replied_at"]]
        if lost:
            r = rng.choice(lost)
            r["replied_at"] = r["lost_at"] + timedelta(days=1)
            issues["stage_after_lost"].append(r["request_id"])
    return rows, issues, as_of


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=80)
    ap.add_argument("--start", default="2026-11-16")
    ap.add_argument("--weeks", type=int, default=3)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--clean", action="store_true")
    ap.add_argument("--out", default="data/synthetic_requests.csv")
    a = ap.parse_args()

    rows, issues, as_of = generate(a.n, datetime.fromisoformat(a.start), a.weeks, a.seed, a.clean)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({k: (v.strftime("%Y-%m-%d %H:%M") if isinstance(v, datetime) else v)
                        for k, v in r.items()})
    out.with_suffix(".issues.json").write_text(
        json.dumps({"as_of": f"{as_of:%Y-%m-%d}", "seed": a.seed, **issues}, indent=2) + "\n",
        encoding="utf-8")
    print(f"Wrote {len(rows)} rows to {out} (as of {as_of:%Y-%m-%d})")


if __name__ == "__main__":
    main()
