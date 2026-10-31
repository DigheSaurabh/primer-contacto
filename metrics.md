# Metrics Dictionary (v1)

This file is the contract for the metrics engine. Every metric gets **one function in `metrics.py`** and **one pytest test**. Do not change the stage model after Gate 1 (Nov 6).

## Stage model
| # | Stage | Meaning | Timestamp field |
|---|---|---|---|
| 1 | Received | The request arrived in any channel | `received_at` |
| 2 | Replied | The teacher sent any first reply | `replied_at` |
| 3 | Quoted | A price, package or proposal was sent | `quoted_at` |
| 4 | Confirmed | The client said yes and a date is set | `confirmed_at` |
| 5 | Delivered | The session or event happened | `delivered_at` |
| 6 | Invoiced | An invoice or payment request was sent (contracted gigs) | `invoiced_at` |
| 7 | Paid | Money arrived | `paid_at` |
| – | Lost | Terminal outcome at any stage, with a reason | `lost_at`, `lost_reason` |

## Metrics
| # | Metric | Definition / formula | Notes |
|---|---|---|---|
| 1 | First-reply time | `replied_at − received_at` in hours. Median and 90th percentile, by channel and overall. | Requests with no reply are excluded and reported separately as "never replied" with their share. |
| 2 | Replied within 24 hours | Share of requests with first-reply time ≤ 24 hours. | Headline weekly number. |
| 3 | Days in stage | For each consecutive pair of stages reached: `next stage_at − current stage_at` in days. Median by stage. | Uses the long-format table. |
| 4 | Time to confirm | `confirmed_at − received_at` in days. Median, by request type. | |
| 5 | Aging of open requests | For requests with no terminal outcome: `today − received_at`, bucketed 0–2, 3–7, 8–14, 15+ days. | Feeds the "needs a reply today" list (open and not replied, or open past 7 days). |
| 6 | Stuck point | Stage with the highest share of requests whose last recorded stage is that stage and that are lost or open past 14 days. | Report top 3 stages and the lost reasons at each. |
| 7 | Conversion by source | Confirmed ÷ Received, per channel. | Also report Replied ÷ Received and Confirmed ÷ Quoted per channel. |
| 8 | Conversion by request type | Confirmed ÷ Received, per request type. | |
| 9 | Lost reasons | Share of lost requests by reason. | |
| 10 | Seasonality | Requests received per ISO week over the trailing 12 months. | Mark Sep 15 – Oct 15; show the November drop as a ratio to the peak week. |
| 11 | Days to payment | `paid_at − delivered_at` and `paid_at − invoiced_at` in days. Median by client type. | Contracted gigs only (corporate, school, community organization). |
| 12 | Weekly summary | New requests; replied within 24 h (share); open past 7 days (count); confirmed, delivered, paid (counts); median first-reply time; top stuck point. | One plain-language sentence per line, in English and Spanish. |

## Open questions (update after teacher interviews)
- [ ] Are the channel categories right for Chicago teachers?
- [ ] Is 24 hours the right "fast reply" threshold?
- [ ] Is 14 days the right threshold for "stuck"?
