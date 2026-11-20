import json
from pathlib import Path

import pandas as pd
import pytest

import validate

ROOT = Path(__file__).resolve().parents[1]


def rules(report):
    return set(zip(report.issues.request_id, report.issues.rule))


def test_clean_fixture_has_no_errors(raw):
    report = validate.validate(raw)
    assert report.errors.empty
    assert len(report.clean) == len(raw)


def test_missing_required_column_stops(raw):
    with pytest.raises(validate.SchemaError):
        validate.validate(raw.drop(columns="channel"))


def test_duplicate_keeps_first_copy(raw):
    report = validate.validate(pd.concat([raw, raw.iloc[[0]]], ignore_index=True))
    assert ("A", "duplicate_request_id") in rules(report)
    assert (report.clean.request_id == "A").sum() == 1


def test_dates_out_of_order_is_an_error(raw):
    raw.loc[raw.request_id == "A", "paid_at"] = "2026-12-04 09:00"  # before delivered
    report = validate.validate(raw)
    assert ("A", "dates_out_of_order") in rules(report)
    assert "A" not in set(report.clean.request_id)


def test_stage_after_lost_is_an_error(raw):
    raw.loc[raw.request_id == "C", "confirmed_at"] = "2026-12-06 10:00"
    assert ("C", "stage_after_lost") in rules(validate.validate(raw))


def test_warnings_keep_the_row(raw):
    raw["note"] = None
    raw.loc[raw.request_id == "D", "note"] = "call me at 312-555-0142"
    raw.loc[raw.request_id == "E", "channel"] = "carrier_pigeon"
    report = validate.validate(raw)
    assert {("D", "note_may_contain_contact"), ("E", "unknown_channel")} <= rules(report)
    assert {"D", "E"} <= set(report.clean.request_id)


def test_catches_every_planted_problem_in_synthetic_data():
    csv = ROOT / "data" / "synthetic_requests.csv"
    planted = json.loads(csv.with_suffix(".issues.json").read_text())
    report = validate.validate(pd.read_csv(csv, dtype=str))
    found = rules(report)
    for rule in ["duplicate_request_id", "dates_out_of_order", "stage_after_lost"]:
        for rid in planted[rule]:
            assert (rid, rule) in found
