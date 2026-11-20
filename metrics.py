"""The 12 metrics in docs/metrics.md. One function per metric.

Every function takes the clean wide table from validate.py (and the long table from
transform.py where the definition says so) and returns plain pandas objects or dicts.
Counts are returned beside every share, because pilot samples are small.
"""
from __future__ import annotations

import pandas as pd

STAGES = ["received", "replied", "quoted", "confirmed", "delivered", "invoiced", "paid"]
CONTRACTED = {"company", "school", "nonprofit_community"}
HOUR = pd.Timedelta(hours=1)
DAY = pd.Timedelta(days=1)


# ---------------------------------------------------------------- shared helpers

def reply_hours(df: pd.DataFrame) -> pd.Series:
    return (df.replied_at - df.received_at) / HOUR


def is_terminal(df: pd.DataFrame) -> pd.Series:
    """Lost, or delivered and paid."""
    return df.lost_at.notna() | (df.delivered_at.notna() & df.paid_at.notna())


def last_stage(df: pd.DataFrame) -> pd.Series:
    def last(r):
        return next(s for s in reversed(STAGES) if pd.notna(r[f"{s}_at"]))
    return df.apply(last, axis=1)


def _share(n: int, total: int) -> float | None:
    return round(n / total, 3) if total else None


# ---------------------------------------------------------------- 1-12

def first_reply_time(df: pd.DataFrame) -> dict:
    """1. replied_at - received_at in hours: median and p90, overall and by channel.
    Unreplied requests are excluded and reported separately."""
    h = reply_hours(df)
    by = (df.assign(h=h).groupby("channel")
          .agg(requests=("request_id", "size"), replied=("h", "count"),
               median_h=("h", "median"), p90_h=("h", lambda s: s.quantile(0.9)))
          .round(1).sort_values("requests", ascending=False))
    return {
        "median_h": round(h.median(), 1) if h.notna().any() else None,
        "p90_h": round(h.quantile(0.9), 1) if h.notna().any() else None,
        "never_replied": int(h.isna().sum()),
        "never_replied_share": _share(int(h.isna().sum()), len(df)),
        "by_channel": by,
    }


def replied_within_24h(df: pd.DataFrame) -> dict:
    """2. Share of requests with first-reply time <= 24 hours (unreplied count as not)."""
    n = int((reply_hours(df) <= 24).sum())
    return {"count": n, "total": len(df), "share": _share(n, len(df))}


def days_in_stage(long: pd.DataFrame) -> pd.DataFrame:
    """3. For each consecutive pair of stages reached: next stage_at - current stage_at, in days.
    Median by stage. Uses the long table; Lost is not a stage to move out of."""
    x = long[long.stage != "lost"].sort_values(["request_id", "stage_order"]).copy()
    x["next_stage"] = x.groupby("request_id").stage.shift(-1)
    x["days"] = (x.groupby("request_id").stage_at.shift(-1) - x.stage_at) / DAY
    x = x.dropna(subset=["next_stage"])
    out = (x.groupby(["stage", "next_stage"]).days.agg(n="count", median_days="median").round(1)
           .reset_index())
    out["order"] = out.stage.map({s: i for i, s in enumerate(STAGES)})
    return out.sort_values("order").drop(columns="order").reset_index(drop=True)


def time_to_confirm(df: pd.DataFrame) -> pd.DataFrame:
    """4. confirmed_at - received_at in days, median by request type."""
    days = (df.confirmed_at - df.received_at) / DAY
    return (df.assign(days=days).groupby("request_type").days
            .agg(confirmed="count", median_days="median").round(1)
            .query("confirmed > 0").sort_values("confirmed", ascending=False))


def open_request_aging(df: pd.DataFrame, as_of: pd.Timestamp) -> dict:
    """5. Open requests (no terminal outcome) by age bucket, plus the 'needs attention today' list:
    open and not replied, or open past 7 days."""
    op = df[~is_terminal(df)].copy()
    op["age_days"] = (as_of - op.received_at) // DAY
    op["bucket"] = pd.cut(op.age_days, [-1, 2, 7, 14, float("inf")], labels=["0-2", "3-7", "8-14", "15+"])
    need = op[op.replied_at.isna() | (op.age_days > 7)].copy()
    need["why"] = need.replied_at.isna().map({True: "not replied", False: "open past 7 days"})
    cols = [c for c in ["request_id", "teacher_id", "channel", "request_type", "age_days", "why"] if c in need]
    return {
        "open": len(op),
        "buckets": op.bucket.value_counts().reindex(["0-2", "3-7", "8-14", "15+"], fill_value=0),
        "needs_attention": need.sort_values(["why", "age_days"], ascending=[True, False])[cols]
        .reset_index(drop=True),
    }


def stuck_point(df: pd.DataFrame, as_of: pd.Timestamp, top: int = 3) -> pd.DataFrame:
    """6. Among requests that are lost or open past 14 days: which last stage holds the most,
    with the top lost reasons at each."""
    age = (as_of - df.received_at) / DAY
    stuck = df[df.lost_at.notna() | (~is_terminal(df) & (age > 14))].copy()
    if stuck.empty:
        return pd.DataFrame(columns=["stage", "count", "share", "top_reasons"])
    stuck["stage"] = last_stage(stuck)
    rows = []
    for stage, g in stuck.groupby("stage"):
        reasons = g.lost_reason.value_counts().head(2)
        rows.append({"stage": stage, "count": len(g), "share": _share(len(g), len(stuck)),
                     "top_reasons": ", ".join(f"{k} ({v})" for k, v in reasons.items())})
    return pd.DataFrame(rows).sort_values("count", ascending=False).head(top).reset_index(drop=True)


def _conversion(df: pd.DataFrame, by: str) -> pd.DataFrame:
    g = df.groupby(by).agg(received=("request_id", "size"), replied=("replied_at", "count"),
                           quoted=("quoted_at", "count"), confirmed=("confirmed_at", "count"))
    g["confirmed_rate"] = (g.confirmed / g.received).round(3)
    g["replied_rate"] = (g.replied / g.received).round(3)
    g["quote_to_confirm"] = (g.confirmed / g.quoted.where(g.quoted > 0)).round(3)
    return g.sort_values("received", ascending=False)


def conversion_by_source(df: pd.DataFrame) -> pd.DataFrame:
    """7. Confirmed / Received per channel, plus Replied / Received and Confirmed / Quoted."""
    return _conversion(df, "channel")


def conversion_by_request_type(df: pd.DataFrame) -> pd.DataFrame:
    """8. Confirmed / Received per request type."""
    return _conversion(df, "request_type")[["received", "confirmed", "confirmed_rate"]]


def lost_reasons(df: pd.DataFrame) -> pd.DataFrame:
    """9. Share of lost requests by reason."""
    lost = df[df.lost_at.notna()]
    counts = lost.lost_reason.fillna("not recorded").value_counts()
    return pd.DataFrame({"count": counts, "share": (counts / counts.sum()).round(3)})


def seasonality(df: pd.DataFrame) -> dict:
    """10. Requests per ISO week over the trailing 12 months. Marks Sep 15 - Oct 15 and gives the
    November average as a ratio to the peak week."""
    end = df.received_at.max()
    x = df[df.received_at > end - pd.DateOffset(months=12)]
    weeks = x.received_at.dt.to_period("W-SUN").value_counts().sort_index()
    weeks = weeks.reindex(pd.period_range(weeks.index.min(), weeks.index.max(), freq="W-SUN"), fill_value=0)
    table = pd.DataFrame({"week_start": weeks.index.start_time, "requests": weeks.values})
    md = table.week_start.dt.month * 100 + table.week_start.dt.day
    table["sep15_oct15"] = (md >= 915) & (md <= 1015)
    nov = table[table.week_start.dt.month == 11].requests
    peak = int(table.requests.max()) if len(table) else 0
    return {
        "weeks": table,
        "covers_full_year": len(table) >= 50,
        "peak_week": table.loc[table.requests.idxmax(), "week_start"] if len(table) else None,
        "peak_requests": peak,
        "november_to_peak": round(nov.mean() / peak, 2) if peak and len(nov) else None,
    }


def days_to_payment(df: pd.DataFrame) -> pd.DataFrame:
    """11. paid_at - delivered_at and paid_at - invoiced_at in days, median by client type.
    Contracted gigs only (company, school, community organization)."""
    c = df[df.client_type.isin(CONTRACTED)].copy()
    c["delivered_to_paid"] = (c.paid_at - c.delivered_at) / DAY
    c["invoiced_to_paid"] = (c.paid_at - c.invoiced_at) / DAY
    return (c.groupby("client_type")
            .agg(delivered=("delivered_at", "count"), invoiced=("invoiced_at", "count"),
                 paid=("paid_at", "count"),
                 median_delivered_to_paid=("delivered_to_paid", "median"),
                 median_invoiced_to_paid=("invoiced_to_paid", "median"))
            .round(1))


SUMMARY_TEXT = {
    "en": {
        "new": "{n} new requests this week.",
        "fast": "You answered {k} of {n} within 24 hours.",
        "open": "{k} requests have been open for more than 7 days.",
        "done": "This week: {c} confirmed, {d} delivered, {p} paid.",
        "median": "Your typical first reply took {h} hours.",
        "median_none": "No replies were logged this week.",
        "stuck": "Most requests that stall stop at: {s}.",
    },
    "es": {
        "new": "{n} solicitudes nuevas esta semana.",
        "fast": "Respondiste {k} de {n} en menos de 24 horas.",
        "open": "{k} solicitudes llevan más de 7 días abiertas.",
        "done": "Esta semana: {c} confirmadas, {d} realizadas, {p} pagadas.",
        "median": "Tu primera respuesta típica tardó {h} horas.",
        "median_none": "No se registraron respuestas esta semana.",
        "stuck": "La mayoría de las solicitudes que se detienen quedan en: {s}.",
    },
}
STAGE_NAMES = {
    "en": {s: s for s in STAGES},
    "es": {"received": "recibida", "replied": "respondida", "quoted": "cotizada", "confirmed": "confirmada",
           "delivered": "realizada", "invoiced": "facturada", "paid": "pagada"},
}


def weekly_summary(df: pd.DataFrame, as_of: pd.Timestamp, lang: str = "en") -> list[str]:
    """12. Plain-language lines for the 7 days before as_of, in English or Spanish."""
    t = SUMMARY_TEXT[lang]
    start = as_of - pd.Timedelta(days=7)
    week = df[(df.received_at >= start) & (df.received_at < as_of)]
    h = reply_hours(week)
    op = df[~is_terminal(df)]
    in_week = lambda col: int(df[col].between(start, as_of, inclusive="left").sum())
    stuck = stuck_point(df, as_of, top=1)
    lines = [
        t["new"].format(n=len(week)),
        t["fast"].format(k=int((h <= 24).sum()), n=len(week)),
        t["open"].format(k=int(((as_of - op.received_at) / DAY > 7).sum())),
        t["done"].format(c=in_week("confirmed_at"), d=in_week("delivered_at"), p=in_week("paid_at")),
        t["median"].format(h=round(h.median(), 1)) if h.notna().any() else t["median_none"],
    ]
    if len(stuck):
        lines.append(t["stuck"].format(s=STAGE_NAMES[lang][stuck.stage.iloc[0]]))
    return lines
