"""Wide request log -> long stage table (docs/schema.md, "CSV: long format").

One row per stage reached: request_id, stage, stage_order, stage_at, plus the Form A attributes.
"""
from __future__ import annotations

import pandas as pd

STAGES = ["received", "replied", "quoted", "confirmed", "delivered", "invoiced", "paid"]
ATTRIBUTES = ["teacher_id", "channel", "request_type", "language", "client_type"]


def to_long(wide: pd.DataFrame) -> pd.DataFrame:
    cols = [f"{s}_at" for s in STAGES] + ["lost_at"]
    attrs = [c for c in ATTRIBUTES if c in wide.columns]
    long = wide.melt(id_vars=["request_id", *attrs], value_vars=cols, var_name="stage", value_name="stage_at")
    long = long.dropna(subset=["stage_at"])
    long["stage"] = long.stage.str.removesuffix("_at")
    order = {s: i + 1 for i, s in enumerate(STAGES)} | {"lost": 99}
    long["stage_order"] = long.stage.map(order)
    return (long.sort_values(["request_id", "stage_order"])
            [["request_id", "stage", "stage_order", "stage_at", *attrs]]
            .reset_index(drop=True))
