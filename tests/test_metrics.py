"""One test per metric in docs/metrics.md, on the hand-checked log in conftest.py.

Reply hours: A 2, B 48, C 10, E 2, G 1; D never replied.
"""
import pandas as pd
import pytest

import metrics as m
import transform


def test_01_first_reply_time(clean):
    r = m.first_reply_time(clean)
    assert r["median_h"] == 2.0                       # median of 1, 2, 2, 10, 48
    assert r["never_replied"] == 1                    # D
    assert r["never_replied_share"] == pytest.approx(1 / 6, abs=0.001)
    ig = r["by_channel"].loc["instagram_dm"]
    assert (ig.requests, ig.replied, ig.median_h) == (2, 2, 6.0)  # A 2 h, C 10 h


def test_02_replied_within_24h(clean):
    r = m.replied_within_24h(clean)
    assert (r["count"], r["total"]) == (4, 6)         # A, C, E, G; unreplied D counts as not


def test_03_days_in_stage(clean):
    t = m.days_in_stage(transform.to_long(clean)).set_index(["stage", "next_stage"])
    row = t.loc[("replied", "quoted")]
    assert row.n == 4                                  # A 1 h, B 24 h, C 14 h, G 1 h
    assert row.median_days == 0.3                      # 7.5 h


def test_04_time_to_confirm(clean):
    t = m.time_to_confirm(clean)
    assert t.loc["private_session", "median_days"] == 2.1    # A: 2 days 3 h
    assert t.loc["corporate_session", "median_days"] == 5.0  # B
    assert t.loc["school_event", "median_days"] == 1.0       # G


def test_05_open_request_aging(clean, as_of):
    r = m.open_request_aging(clean, as_of)
    assert r["open"] == 3                              # B (invoiced, unpaid), D, E
    assert r["buckets"].to_dict() == {"0-2": 1, "3-7": 0, "8-14": 1, "15+": 1}
    need = r["needs_attention"].set_index("request_id").why.to_dict()
    assert need == {"D": "not replied", "B": "open past 7 days", "E": "open past 7 days"}


def test_06_stuck_point(clean, as_of):
    t = m.stuck_point(clean, as_of).set_index("stage")
    assert t["count"].to_dict() == {"quoted": 1, "replied": 1}   # C lost after quote; E open 20 days
    assert "declined_price" in t.loc["quoted", "top_reasons"]


def test_07_conversion_by_source(clean):
    t = m.conversion_by_source(clean)
    assert t.loc["instagram_dm", ["received", "confirmed"]].tolist() == [2, 1]
    assert t.loc["instagram_dm", "quote_to_confirm"] == 0.5
    assert t.loc["email", "confirmed_rate"] == 1.0
    assert t.loc["text_message", "replied_rate"] == 0.0


def test_08_conversion_by_request_type(clean):
    t = m.conversion_by_request_type(clean)
    assert t.loc["private_session", ["received", "confirmed"]].tolist() == [3, 1]
    assert t.loc["private_session", "confirmed_rate"] == 0.333


def test_09_lost_reasons(clean):
    t = m.lost_reasons(clean)
    assert t.to_dict("index") == {"declined_price": {"count": 1, "share": 1.0}}


def test_10_seasonality():
    weeks = pd.date_range("2025-12-01", periods=52, freq="W-MON")
    received = list(weeks) + [pd.Timestamp("2026-09-15")] * 3     # 4 requests in the week of Sep 14
    df = pd.DataFrame({"received_at": received})
    r = m.seasonality(df)
    assert r["covers_full_year"]
    assert r["peak_requests"] == 4
    assert r["peak_week"] == pd.Timestamp("2026-09-14")
    assert r["november_to_peak"] == 0.25                # 1 per November week / 4
    assert r["weeks"].loc[r["weeks"].week_start == "2026-09-14", "sep15_oct15"].item() is False
    assert r["weeks"].loc[r["weeks"].week_start == "2026-09-21", "sep15_oct15"].item() is True


def test_11_days_to_payment(clean):
    t = m.days_to_payment(clean)
    assert t.loc["school", "median_delivered_to_paid"] == 10.1   # G: 10 days 2 h
    assert t.loc["school", "median_invoiced_to_paid"] == 10.0
    assert t.loc["company", ["delivered", "invoiced", "paid"]].tolist() == [1, 1, 0]  # B unpaid
    assert "individual" not in t.index


def test_12_weekly_summary(clean, as_of):
    en = m.weekly_summary(clean, as_of, "en")
    assert en[:4] == [
        "1 new requests this week.",                     # D
        "You answered 0 of 1 within 24 hours.",
        "2 requests have been open for more than 7 days.",  # B, E
        "This week: 2 confirmed, 2 delivered, 2 paid.",     # A, B | A, B | A, G
    ]
    es = m.weekly_summary(clean, as_of, "es")
    assert es[0] == "1 solicitudes nuevas esta semana."
    assert len(es) == len(en)


def test_transform_has_one_row_per_stage_reached(clean):
    long = transform.to_long(clean)
    a = long[long.request_id == "A"]
    assert a.stage.tolist() == ["received", "replied", "quoted", "confirmed", "delivered", "paid"]
    assert len(long[long.request_id == "C"]) == 4       # received, replied, quoted, lost
