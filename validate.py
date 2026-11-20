"""Schema and data-quality checks for request logs (rules in docs/schema.md).

    python validate.py data/synthetic_requests.csv

Errors remove a row from the clean data; warnings keep it but report it.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field

import pandas as pd

REQUIRED = ["request_id", "received_at", "channel"]
STAGES = ["received", "replied", "quoted", "confirmed", "delivered", "invoiced", "paid"]
DATE_COLUMNS = [f"{s}_at" for s in STAGES] + ["lost_at"]
OPTIONAL = ["teacher_id", "request_type", "language", "client_type", "event_zip",
            "lost_reason", "quoted_amount", "note"]
CHANNELS = {"instagram_dm", "linktree_form", "text_message", "email", "phone_call",
            "in_person", "referral", "other"}
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE = re.compile(r"\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}")


class SchemaError(ValueError):
    """The file can't be checked at all (for example, a required column is missing)."""


@dataclass
class Report:
    clean: pd.DataFrame
    issues: pd.DataFrame = field(default_factory=lambda: pd.DataFrame(
        columns=["request_id", "severity", "rule", "detail"]))
    completeness: pd.Series | None = None

    @property
    def errors(self) -> pd.DataFrame:
        return self.issues[self.issues.severity == "error"]

    @property
    def warnings(self) -> pd.DataFrame:
        return self.issues[self.issues.severity == "warning"]


def load(path: str) -> pd.DataFrame:
    """Read a wide-format CSV and parse its dates and amounts."""
    df = pd.read_csv(path, dtype={"request_id": str, "event_zip": str, "teacher_id": str})
    return coerce(df)


def coerce(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in OPTIONAL + DATE_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    for col in DATE_COLUMNS:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    df["quoted_amount"] = pd.to_numeric(df["quoted_amount"], errors="coerce")
    return df


def validate(df: pd.DataFrame) -> Report:
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise SchemaError(f"Missing required column(s): {', '.join(missing)}")
    df = coerce(df)
    df = df.reset_index(drop=True)
    issues: list[tuple] = []  # (row, request_id, severity, rule, detail)

    def add(mask, severity, rule, detail):
        for i in df.index[mask]:
            rid = df.at[i, "request_id"]
            issues.append((i, "(no id)" if pd.isna(rid) else rid, severity, rule, detail))

    # Required values
    for col in REQUIRED:
        blank = df[col].isna() | (df[col].astype(str).str.strip() == "")
        add(blank, "error", "missing_value", f"{col} is blank")

    # Unique request_id: keep the first, flag the rest
    dup = df.request_id.duplicated(keep="first") & df.request_id.notna()
    add(dup, "error", "duplicate_request_id", "request_id appears more than once (first copy kept)")

    # Dates in order: received <= replied <= ... <= paid
    for i, r in df.iterrows():
        filled = [(s, r[f"{s}_at"]) for s in STAGES if pd.notna(r[f"{s}_at"])]
        for (a, ta), (b, tb) in zip(filled, filled[1:]):
            if tb < ta:
                issues.append((i, r.request_id, "error", "dates_out_of_order", f"{b}_at is before {a}_at"))
                break
        if pd.notna(r.lost_at):
            late = [s for s, t in filled if t > r.lost_at]
            if late:
                issues.append((i, r.request_id, "error", "stage_after_lost",
                               f"{', '.join(late)} recorded after lost_at"))
            if pd.isna(r.lost_reason):
                issues.append((i, r.request_id, "warning", "lost_without_reason", "lost_at set but no lost_reason"))

    # Warnings: kept in the clean data, but worth fixing
    unknown = ~df.channel.isin(CHANNELS) & df.channel.notna()
    add(unknown, "warning", "unknown_channel", "channel is not on the Form A list")
    note = df.note.fillna("").astype(str)
    contact = note.str.contains(EMAIL) | note.str.contains(PHONE)
    add(contact, "warning", "note_may_contain_contact",
        "note looks like it contains an email or phone number")
    for i, s in enumerate(STAGES[2:], start=2):
        skipped = df[f"{s}_at"].notna() & df[f"{STAGES[i - 1]}_at"].isna() & (STAGES[i - 1] != "invoiced")
        add(skipped, "warning", "skipped_stage",
            f"{s}_at is set but {STAGES[i - 1]}_at is blank")

    issues_df = pd.DataFrame(issues, columns=["row", "request_id", "severity", "rule", "detail"])
    error_rows = set(issues_df.loc[issues_df.severity == "error", "row"])
    clean = df.drop(index=list(error_rows)).reset_index(drop=True)
    issues_df = issues_df.drop(columns="row")

    completeness = (df[REQUIRED + [c for c in OPTIONAL + DATE_COLUMNS if c in df.columns]]
                    .notna().mean().round(3))
    return Report(clean=clean, issues=issues_df, completeness=completeness)


def print_report(report: Report, total: int) -> None:
    print(f"Rows checked: {total} | clean: {len(report.clean)} | "
          f"errors: {len(report.errors)} | warnings: {len(report.warnings)}")
    if len(report.issues):
        print(report.issues.sort_values(["severity", "rule"]).to_string(index=False))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv")
    a = ap.parse_args(argv)
    df = pd.read_csv(a.csv, dtype=str)
    try:
        report = validate(df)
    except SchemaError as e:
        print(f"Can't check this file: {e}")
        return 2
    print_report(report, len(df))
    return 1 if len(report.errors) else 0


if __name__ == "__main__":
    sys.exit(main())
