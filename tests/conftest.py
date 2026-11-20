"""A tiny hand-checked request log. Expected values in the tests are worked out by hand from it."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

AS_OF = pd.Timestamp("2026-12-10")

ROWS = [
    # A: Instagram private session, replied in 2 h, delivered and paid (prepaid same day)
    dict(request_id="A", teacher_id="T1", channel="instagram_dm", request_type="private_session",
         client_type="individual", received_at="2026-12-01 09:00", replied_at="2026-12-01 11:00",
         quoted_at="2026-12-01 12:00", confirmed_at="2026-12-03 12:00", delivered_at="2026-12-05 12:00",
         paid_at="2026-12-05 13:00"),
    # B: corporate email, replied in 48 h, delivered and invoiced, not paid yet (open)
    dict(request_id="B", teacher_id="T1", channel="email", request_type="corporate_session",
         client_type="company", received_at="2026-12-01 09:00", replied_at="2026-12-03 09:00",
         quoted_at="2026-12-04 09:00", confirmed_at="2026-12-06 09:00", delivered_at="2026-12-07 09:00",
         invoiced_at="2026-12-07 10:00"),
    # C: Instagram private session, replied in 10 h, lost after the quote
    dict(request_id="C", teacher_id="T2", channel="instagram_dm", request_type="private_session",
         client_type="individual", received_at="2026-12-02 10:00", replied_at="2026-12-02 20:00",
         quoted_at="2026-12-03 10:00", lost_at="2026-12-05 10:00", lost_reason="declined_price"),
    # D: text, never replied, 2 days old
    dict(request_id="D", teacher_id="T2", channel="text_message", request_type="workshop",
         client_type="studio", received_at="2026-12-08 10:00"),
    # E: referral, replied in 2 h, then nothing for 20 days (open, stuck at replied)
    dict(request_id="E", teacher_id="T1", channel="referral", request_type="private_session",
         client_type="individual", received_at="2026-11-20 10:00", replied_at="2026-11-20 12:00"),
    # G: school event by email, invoiced and paid 10 days later
    dict(request_id="G", teacher_id="T2", channel="email", request_type="school_event",
         client_type="school", received_at="2026-11-25 10:00", replied_at="2026-11-25 11:00",
         quoted_at="2026-11-25 12:00", confirmed_at="2026-11-26 10:00", delivered_at="2026-11-28 10:00",
         invoiced_at="2026-11-28 12:00", paid_at="2026-12-08 12:00"),
]


@pytest.fixture
def raw():
    return pd.DataFrame(ROWS)


@pytest.fixture
def clean(raw):
    import validate
    return validate.validate(raw).clean


@pytest.fixture
def as_of():
    return AS_OF
