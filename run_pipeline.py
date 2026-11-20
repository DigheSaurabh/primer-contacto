"""Run the whole pipeline: (generate) -> validate -> transform -> 12 metrics.

    python run_pipeline.py                                  # synthetic pilot data (generated if missing)
    python run_pipeline.py --teacher T1 --lang es           # one teacher's view, summary in Spanish
    python run_pipeline.py --input requests.csv --as-of 2026-12-21   # a Requests tab exported as CSV
    python run_pipeline.py --out output                     # also save each metric as a CSV

Results from synthetic data describe the generator's assumptions, not real teachers.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

import metrics as m
import transform
import validate

DEFAULT = Path("data/synthetic_requests.csv")


def heading(text: str) -> None:
    print(f"\n{text}\n{'-' * len(text)}")


def show(obj) -> None:
    text = obj.to_string() if hasattr(obj, "to_string") else str(obj)
    print("  " + text.replace("\n", "\n  "))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", type=Path, default=DEFAULT)
    ap.add_argument("--as-of", help="date the data is 'as of' (default: from the .issues.json, else the latest date)")
    ap.add_argument("--teacher", help="only this teacher_id, e.g. T1")
    ap.add_argument("--lang", choices=["en", "es"], default="en")
    ap.add_argument("--out", type=Path, help="folder to save each metric as CSV")
    a = ap.parse_args(argv)

    # 1. Generate (synthetic default only)
    if not a.input.exists():
        if a.input != DEFAULT:
            print(f"File not found: {a.input}")
            return 2
        print("No synthetic data yet; generating it.")
        subprocess.run([sys.executable, "generate_synthetic.py"], check=True)

    # 2. Validate
    raw = pd.read_csv(a.input, dtype=str)
    try:
        report = validate.validate(raw)
    except validate.SchemaError as e:
        print(f"Can't use this file: {e}")
        return 2
    heading("Validation")
    validate.print_report(report, len(raw))
    df = report.clean
    if a.teacher:
        df = df[df.teacher_id == a.teacher].reset_index(drop=True)
        if df.empty:
            print(f"No clean requests for teacher {a.teacher}.")
            return 2

    issues_file = a.input.with_suffix(".issues.json")
    if a.as_of:
        as_of = pd.Timestamp(a.as_of)
    elif issues_file.exists():
        as_of = pd.Timestamp(json.loads(issues_file.read_text())["as_of"])
    else:
        as_of = df[[c for c in df.columns if c.endswith("_at")]].max().max().normalize() + pd.Timedelta(days=1)

    # 3. Transform
    long = transform.to_long(df)

    # 4. Metrics
    who = f"teacher {a.teacher}" if a.teacher else f"{df.teacher_id.nunique()} teachers"
    print(f"\n{len(df)} clean requests from {who}, as of {as_of.date()}")
    if "synthetic" in a.input.name:
        print("SAMPLE DATA: these patterns come from the generator's assumptions, not real teachers.")

    results = {}
    r = m.first_reply_time(df)
    heading("1. First-reply time (hours)")
    print(f"  median {r['median_h']}, 90th percentile {r['p90_h']}, "
          f"never replied {r['never_replied']} ({r['never_replied_share']:.0%})")
    show(r["by_channel"]); results["1_first_reply_by_channel"] = r["by_channel"]

    r = m.replied_within_24h(df)
    heading("2. Replied within 24 hours")
    print(f"  {r['count']} of {r['total']} ({r['share']:.0%})")

    heading("3. Days in stage (median)")
    results["3_days_in_stage"] = m.days_in_stage(long); show(results["3_days_in_stage"])

    heading("4. Time to confirm (median days, by request type)")
    results["4_time_to_confirm"] = m.time_to_confirm(df); show(results["4_time_to_confirm"])

    r = m.open_request_aging(df, as_of)
    heading("5. Open requests by age (days)")
    show(r["buckets"])
    print(f"  Needs attention today: {len(r['needs_attention'])}")
    show(r["needs_attention"].head(10))
    results["5_needs_attention"] = r["needs_attention"]

    heading("6. Stuck point")
    results["6_stuck_point"] = m.stuck_point(df, as_of); show(results["6_stuck_point"])

    heading("7. Conversion by source")
    results["7_conversion_by_source"] = m.conversion_by_source(df); show(results["7_conversion_by_source"])

    heading("8. Conversion by request type")
    results["8_conversion_by_type"] = m.conversion_by_request_type(df); show(results["8_conversion_by_type"])

    heading("9. Lost reasons")
    results["9_lost_reasons"] = m.lost_reasons(df); show(results["9_lost_reasons"])

    r = m.seasonality(df)
    heading("10. Seasonality")
    if r["covers_full_year"]:
        print(f"  peak week starts {r['peak_week'].date()} ({r['peak_requests']} requests); "
              f"November runs at {r['november_to_peak']} of the peak")
    else:
        print(f"  Only {len(r['weeks'])} weeks of data; seasonality needs 12 months "
              "(try --input data/synthetic_year.csv).")
    results["10_seasonality"] = r["weeks"]

    heading("11. Days to payment (contracted gigs)")
    results["11_days_to_payment"] = m.days_to_payment(df); show(results["11_days_to_payment"])

    heading("12. Weekly summary")
    for line in m.weekly_summary(df, as_of, a.lang):
        print(f"  {line}")

    if a.out:
        a.out.mkdir(parents=True, exist_ok=True)
        for name, table in results.items():
            table.to_csv(a.out / f"{name}.csv")
        report.issues.to_csv(a.out / "validation_issues.csv", index=False)
        print(f"\nSaved {len(results) + 1} CSV files to {a.out}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
